"""Session Manager — authoritative timer, conversation flow, board building, evaluation & rewards."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import (
    Achievement, ConsultSession, Discovery, Evaluation, Message, Patient, Profile, UserAchievement, utcnow,
)
from ..schemas import (
    BOARD_CATEGORIES, BoardCategory, BoardItem, BoardOut, MessageOut, PatientPublic, ProfileOut,
)
from . import discovery as discovery_svc
from . import patient_simulator, scoring, session_evaluator
from .llm import LLMError
from .progression import difficulty_for_level, level_for_xp, xp_for_session, xp_required

log = logging.getLogger("session")


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- serializers ----------

def profile_out(p: Profile) -> ProfileOut:
    return ProfileOut(
        id=p.id, display_name=p.display_name, xp=p.xp, level=p.level, difficulty=difficulty_for_level(p.level),
        sessions_completed=p.sessions_completed, xp_for_current_level=xp_required(p.level),
        xp_for_next_level=xp_required(p.level + 1),
    )


def patient_public(p: Patient) -> PatientPublic:
    return PatientPublic(
        id=p.id, name=p.name, age=p.age, occupation=p.occupation, level=p.level, difficulty=p.difficulty,
        presenting_concern=p.presenting_concern, reported_symptoms=list(p.reported_symptoms or []),
        session_objective=p.session_objective, status=p.status,
        look=(p.hidden_profile or {}).get("look") or {},
        opening_emotion={"low": "guarded", "medium": "anxious", "high": "neutral"}.get(
            (p.hidden_profile or {}).get("openness", "medium"), "neutral"),
    )


def message_out(m: Message) -> MessageOut:
    return MessageOut(id=m.id, role=m.role, content=m.content, emotion=m.emotion, created_at=aware(m.created_at))


# ---------- ownership / loading ----------

def get_owned_patient(db: Session, patient_id: str, profile: Profile) -> Patient:
    p = db.get(Patient, patient_id)
    if not p or p.owner_id != profile.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return p


def get_owned_session(db: Session, session_id: str, profile: Profile) -> ConsultSession:
    s = db.get(ConsultSession, session_id)
    if not s or s.owner_id != profile.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    refresh_expiry(db, s)
    return s


# ---------- timer ----------

def seconds_remaining(s: ConsultSession) -> int:
    if s.status != "active":
        return 0
    return max(0, int((aware(s.ends_at) - utcnow()).total_seconds()))


def refresh_expiry(db: Session, s: ConsultSession) -> None:
    if s.status == "active" and utcnow() >= aware(s.ends_at):
        s.status = "ended"
        s.ended_at = aware(s.ends_at)
        s.end_reason = "timeout"
        db.commit()


def end_session(db: Session, s: ConsultSession, reason: str) -> None:
    if s.status == "active":
        s.status = "ended"
        s.ended_at = utcnow()
        s.end_reason = reason
        db.commit()


def start_session(db: Session, profile: Profile, patient: Patient) -> ConsultSession:
    existing = db.scalar(select(ConsultSession).where(ConsultSession.patient_id == patient.id))
    if existing:
        refresh_expiry(db, existing)
        return existing
    now = utcnow()
    openness = (patient.hidden_profile or {}).get("openness", "medium")
    s = ConsultSession(owner_id=profile.id, patient_id=patient.id, started_at=now,
                       ends_at=now + timedelta(minutes=get_settings().session_minutes),
                       comfort={"high": 55, "medium": 40, "low": 25}.get(openness, 40))
    patient.status = "seen"
    db.add(s)
    db.commit()
    return s


# ---------- board ----------

def _discoveries(db: Session, session_id: str) -> list[Discovery]:
    return list(db.scalars(select(Discovery).where(Discovery.session_id == session_id).order_by(Discovery.created_at)))


def _item(d: Discovery, fact: dict, discovered: set[str]) -> BoardItem:
    return BoardItem(key=d.fact_key, category=d.category, label=d.label, detail=d.detail, importance=d.importance,
                     state=d.state, evidence=d.evidence,
                     connected_to=[k for k in fact.get("related_keys", []) if k in discovered])


def build_board(db: Session, s: ConsultSession) -> BoardOut:
    facts = s.patient.hidden_profile["discovery_facts"]
    by_key = {f["key"]: f for f in facts}
    ds = _discoveries(db, s.id)
    discovered = {d.fact_key for d in ds}
    cats = []
    for c in BOARD_CATEGORIES:
        total = sum(1 for f in facts if f["category"] == c)
        if total:
            cats.append(BoardCategory(name=c, total=total, discovered=sum(
                1 for f in facts if f["category"] == c and f["key"] in discovered)))
    items = [_item(d, by_key.get(d.fact_key, {}), discovered) for d in ds]
    return BoardOut(session_id=s.id, total_facts=len(facts), discovered_count=len(ds), categories=cats,
                    items=items, notes=s.notes or "")


def messages_of(db: Session, session_id: str) -> list[Message]:
    return list(db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.seq)))


def _as_dicts(msgs: list[Message]) -> list[dict]:
    return [{"role": m.role, "content": m.content, "emotion": m.emotion} for m in msgs]


# ---------- conversation flow ----------

def handle_message(db: Session, s: ConsultSession, content: str) -> dict:
    # 1-2. validate session + timer
    if s.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Consultation has ended")
    if seconds_remaining(s) <= 0:
        refresh_expiry(db, s)
        raise HTTPException(status.HTTP_409_CONFLICT, "Time is up — the consultation has ended")
    content = content.strip()[: get_settings().max_message_chars]
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty message")

    history = messages_of(db, s.id)
    seq = (history[-1].seq + 1) if history else 1
    # 3. store player message first so it is never lost
    pmsg = Message(session_id=s.id, role="player", content=content, seq=seq)
    db.add(pmsg)
    db.commit()

    # 4-5. patient context + history
    profile = s.patient.hidden_profile
    ds = _discoveries(db, s.id)
    discovered = {d.fact_key for d in ds}
    hist = _as_dicts(history)
    _maybe_summarize(db, s, hist)

    result = {"player_message": message_out(pmsg), "patient_message": None, "new_discoveries": [],
              "updated_items": [], "error": None}
    # 6-8. call Grok, validate, store
    try:
        turn = patient_simulator.reply(profile, hist, discovered, s.context_summary, content, s.comfort)
    except LLMError as e:
        log.error("patient simulator failed: %s", e)
        result["error"] = "The patient didn't respond (AI service error). Your message was saved — try again."
        return _finish(db, s, result)
    text = turn.line
    rmsg = Message(session_id=s.id, role="patient", content=text, emotion=turn.emotion, seq=seq + 1)
    db.add(rmsg)
    # comfort moves gradually: at most 15 points per turn
    s.comfort = int(round(max(0, min(100, s.comfort + max(-15, min(15, turn.comfort - s.comfort))))))
    db.commit()
    result["patient_message"] = message_out(rmsg)

    # 9-10. discoveries
    facts = profile["discovery_facts"]
    undiscovered = [f for f in facts if f["key"] not in discovered]
    try:
        found = discovery_svc.detect(profile, undiscovered, hist, content, text)
    except LLMError as e:
        log.error("discovery evaluator failed: %s", e)
        found = []
    if found:
        result["new_discoveries"], result["updated_items"] = _save_discoveries(db, s, found, discovered, rmsg.id)
    # 11. return
    return _finish(db, s, result)


def _save_discoveries(db: Session, s: ConsultSession, found: list[dict], discovered: set[str], msg_id: str):
    facts = {f["key"]: f for f in s.patient.hidden_profile["discovery_facts"]}
    new_keys = {f["fact"]["key"] for f in found}
    all_keys = discovered | new_keys
    new_rows = []
    for f in found:
        fact = f["fact"]
        row = Discovery(session_id=s.id, fact_key=fact["key"], category=fact["category"], label=fact["label"],
                        detail=fact["fact"], importance=fact["importance"], evidence=f["evidence"],
                        state=discovery_svc.state_for(fact, all_keys), source_message_id=msg_id)
        db.add(row)
        new_rows.append(row)
    # existing discoveries may now become "connected"
    updated = []
    for d in _discoveries(db, s.id):
        if d.fact_key in new_keys:
            continue
        st = discovery_svc.state_for(facts.get(d.fact_key, {}), all_keys)
        if st != d.state:
            d.state = st
            updated.append(d)
    try:
        db.commit()
    except Exception:  # unique constraint race -> duplicates prevented at DB level
        db.rollback()
        return [], []
    return ([_item(r, facts[r.fact_key], all_keys) for r in new_rows],
            [_item(d, facts.get(d.fact_key, {}), all_keys) for d in updated])


def _maybe_summarize(db: Session, s: ConsultSession, hist: list[dict]) -> None:
    keep = patient_simulator.RECENT_TURNS
    if len(hist) <= patient_simulator.SUMMARIZE_AFTER or len(hist) - keep <= s.summarized_count:
        return
    older = hist[s.summarized_count: len(hist) - keep]
    try:
        piece = patient_simulator.summarize(s.patient.name, older)
    except LLMError:
        return
    s.context_summary = (s.context_summary + " " + piece).strip()[-2500:]
    s.summarized_count = len(hist) - keep
    db.commit()


def _finish(db: Session, s: ConsultSession, result: dict) -> dict:
    refresh_expiry(db, s)
    board_count = db.scalar(select(func.count()).select_from(Discovery).where(Discovery.session_id == s.id))
    result.update(discovered_count=board_count, total_facts=len(s.patient.hidden_profile["discovery_facts"]),
                  seconds_remaining=seconds_remaining(s), status=s.status, comfort=s.comfort)
    return result


# ---------- assessment & evaluation ----------

def submit_assessment(db: Session, s: ConsultSession, data: dict) -> None:
    if s.status == "evaluated":
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already evaluated")
    end_session(db, s, "assessment")
    s.assessment = data
    s.status = "assessed"
    db.commit()


def evaluate_session(db: Session, s: ConsultSession, profile: Profile) -> Evaluation:
    existing = db.scalar(select(Evaluation).where(Evaluation.session_id == s.id))
    if existing:
        return existing
    if s.status != "assessed" or not s.assessment:
        raise HTTPException(status.HTTP_409_CONFLICT, "Submit your final assessment first")

    hidden = s.patient.hidden_profile
    discovered = {d.fact_key for d in _discoveries(db, s.id)}
    transcript = _as_dicts(messages_of(db, s.id))
    try:
        llm = session_evaluator.evaluate(hidden, transcript, discovered, s.assessment)
    except LLMError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Evaluation service failed: {e}") from e

    cats = llm.category_scores.model_dump()
    # Calibrate: with no real conversation, conversational categories cannot be high.
    n_player = sum(1 for m in transcript if m["role"] == "player")
    if n_player < 3:
        cap = 25 + 15 * n_player
        for k in ("empathy_rapport", "question_relevance", "active_listening"):
            cats[k] = min(cats[k], cap)
    overall = scoring.overall_score(cats)
    sat_parts = llm.satisfaction.model_dump()
    satisfaction = scoring.satisfaction_score(sat_parts)
    coverage = scoring.discovery_coverage(hidden["discovery_facts"], discovered)
    understanding, und_parts = scoring.understanding_score(coverage, llm.understanding.model_dump())
    xp = xp_for_session(overall, understanding, satisfaction, s.patient.difficulty, coverage)

    ev = Evaluation(
        session_id=s.id, overall_score=overall, satisfaction_score=satisfaction, understanding_score=understanding,
        category_scores={k: round(v, 1) for k, v in cats.items()}, satisfaction_breakdown=sat_parts,
        understanding_breakdown=und_parts,
        feedback={"strengths": llm.strengths, "improvements": llm.improvements, "summary": llm.summary},
        xp_awarded=xp,
    )
    db.add(ev)
    s.status = "evaluated"
    old_level = profile.level
    profile.xp += xp
    profile.level = level_for_xp(profile.xp)
    profile.sessions_completed += 1
    db.commit()
    _award_achievements(db, profile, s, ev, coverage)
    ev._leveled_up = profile.level > old_level  # transient flag for the response
    return ev


def _award_achievements(db: Session, profile: Profile, s: ConsultSession, ev: Evaluation, coverage: float) -> None:
    rules = {
        "first_consult": profile.sessions_completed >= 1,
        "warm_presence": ev.category_scores.get("empathy_rapport", 0) >= 90,
        "detective": coverage >= 0.999,
        "high_marks": ev.overall_score >= 90,
        "regular": profile.sessions_completed >= 5,
    }
    have = set(db.scalars(select(UserAchievement.achievement_code).where(UserAchievement.profile_id == profile.id)))
    for code, ok in rules.items():
        if ok and code not in have and db.get(Achievement, code):
            db.add(UserAchievement(profile_id=profile.id, achievement_code=code, session_id=s.id))
    db.commit()


def missed_categories(s: ConsultSession, discovered: set[str]) -> list[str]:
    facts = s.patient.hidden_profile["discovery_facts"]
    return sorted({f["category"] for f in facts if f["key"] not in discovered and f["importance"] >= 2})

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_profile
from ..config import get_settings
from ..database import Achievement, ConsultSession, Evaluation, Patient, Profile, UserAchievement, get_db, utcnow
from ..schemas import (
    AssessmentIn, BoardOut, HistoryItem, NotesIn, ResultsOut, SendMessageIn, SendMessageOut, SessionOut,
    StartSessionIn,
)
from ..services import scoring
from ..services import session_manager as sm

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _session_out(db: Session, s: ConsultSession) -> SessionOut:
    return SessionOut(
        id=s.id, status=s.status, started_at=sm.aware(s.started_at), ends_at=sm.aware(s.ends_at),
        ended_at=sm.aware(s.ended_at) if s.ended_at else None, server_now=utcnow(),
        seconds_remaining=sm.seconds_remaining(s), patient=sm.patient_public(s.patient),
        messages=[sm.message_out(m) for m in sm.messages_of(db, s.id)], board=sm.build_board(db, s),
        has_assessment=bool(s.assessment), comfort=s.comfort, llm_mode=get_settings().effective_llm_mode,
    )


@router.get("/history", response_model=list[HistoryItem])
def history(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ConsultSession, Patient, Evaluation)
        .join(Patient, Patient.id == ConsultSession.patient_id)
        .outerjoin(Evaluation, Evaluation.session_id == ConsultSession.id)
        .where(ConsultSession.owner_id == profile.id)
        .order_by(ConsultSession.started_at.desc()).limit(50)
    ).all()
    out = []
    for s, p, ev in rows:
        sm.refresh_expiry(db, s)
        out.append(HistoryItem(session_id=s.id, patient_name=p.name, patient_occupation=p.occupation,
                               difficulty=p.difficulty, status=s.status, started_at=sm.aware(s.started_at),
                               overall_score=ev.overall_score if ev else None,
                               xp_awarded=ev.xp_awarded if ev else None))
    return out


@router.post("/start", response_model=SessionOut)
def start(body: StartSessionIn, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    patient = sm.get_owned_patient(db, body.patient_id, profile)
    return _session_out(db, sm.start_session(db, profile, patient))


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return _session_out(db, sm.get_owned_session(db, session_id, profile))


@router.post("/{session_id}/message", response_model=SendMessageOut)
def send_message(session_id: str, body: SendMessageIn, profile: Profile = Depends(current_profile),
                 db: Session = Depends(get_db)):
    s = sm.get_owned_session(db, session_id, profile)
    return SendMessageOut(**sm.handle_message(db, s, body.content))


@router.get("/{session_id}/board", response_model=BoardOut)
def board(session_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return sm.build_board(db, sm.get_owned_session(db, session_id, profile))


@router.post("/{session_id}/notes", response_model=BoardOut)
def save_notes(session_id: str, body: NotesIn, profile: Profile = Depends(current_profile),
               db: Session = Depends(get_db)):
    s = sm.get_owned_session(db, session_id, profile)
    s.notes = body.notes
    db.commit()
    return sm.build_board(db, s)


@router.post("/{session_id}/end", response_model=SessionOut)
def end(session_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    s = sm.get_owned_session(db, session_id, profile)
    sm.end_session(db, s, "manual")
    return _session_out(db, s)


@router.post("/{session_id}/assessment", response_model=SessionOut)
def assessment(session_id: str, body: AssessmentIn, profile: Profile = Depends(current_profile),
               db: Session = Depends(get_db)):
    s = sm.get_owned_session(db, session_id, profile)
    sm.submit_assessment(db, s, body.model_dump())
    return _session_out(db, s)


@router.post("/{session_id}/evaluate", response_model=ResultsOut)
def evaluate(session_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    profile = db.merge(profile)
    s = sm.get_owned_session(db, session_id, profile)
    ev = sm.evaluate_session(db, s, profile)
    return _results(db, s, ev, profile, leveled_up=getattr(ev, "_leveled_up", False))


@router.get("/{session_id}/results", response_model=ResultsOut)
def results(session_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    s = sm.get_owned_session(db, session_id, profile)
    ev = db.scalar(select(Evaluation).where(Evaluation.session_id == s.id))
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session has not been evaluated yet")
    return _results(db, s, ev, profile, leveled_up=False)


def _results(db: Session, s: ConsultSession, ev: Evaluation, profile: Profile, leveled_up: bool) -> ResultsOut:
    board = sm.build_board(db, s)
    discovered = {i.key for i in board.items}
    earned = db.execute(select(Achievement).join(UserAchievement, UserAchievement.achievement_code == Achievement.code)
                        .where(UserAchievement.session_id == s.id, UserAchievement.profile_id == profile.id)).scalars()
    return ResultsOut(
        session_id=s.id, patient=sm.patient_public(s.patient), overall_score=ev.overall_score,
        rating=scoring.rating(ev.overall_score), satisfaction_score=ev.satisfaction_score,
        understanding_score=ev.understanding_score, category_scores=ev.category_scores,
        satisfaction_breakdown=ev.satisfaction_breakdown, understanding_breakdown=ev.understanding_breakdown,
        feedback=ev.feedback, xp_awarded=ev.xp_awarded, discovered_count=board.discovered_count,
        total_facts=board.total_facts, missed_categories=sm.missed_categories(s, discovered),
        profile=sm.profile_out(profile),
        new_achievements=[{"code": a.code, "title": a.title, "description": a.description, "icon": a.icon}
                          for a in earned],
        leveled_up=leveled_up,
    )

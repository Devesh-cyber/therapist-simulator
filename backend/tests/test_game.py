"""End-to-end gameplay tests (offline mock engine) + unit tests for scoring/progression/discovery."""
from datetime import timedelta

from app.database import ConsultSession, SessionLocal
from app.services import discovery, scoring
from app.services.progression import level_for_xp, xp_for_session, xp_required

from .conftest import login

HIDDEN_WORDS = ["hidden_profile", "discovery_facts", "underlying_concerns", "personality", "patient_line"]


def new_session(client, h):
    p = client.post("/api/patients/generate", headers=h).json()
    s = client.post("/api/sessions/start", json={"patient_id": p["id"]}, headers=h).json()
    return p, s


def test_auth_required_and_bad_token(client):
    assert client.post("/api/patients/generate").status_code == 401
    assert client.get("/api/game/progress", headers={"Authorization": "Bearer abc.def"}).status_code == 401


def test_generate_patient_hides_profile(client):
    h = login(client)
    r = client.post("/api/patients/generate", headers=h)
    assert r.status_code == 200
    body = r.text
    for w in HIDDEN_WORDS:
        assert w not in body
    p = r.json()
    assert p["name"] and p["presenting_concern"] and p["status"] == "waiting"
    assert p["look"].get("gender") and p["opening_emotion"]
    # Same waiting patient is returned until seen
    assert client.post("/api/patients/generate", headers=h).json()["id"] == p["id"]


def test_ownership(client):
    h1, h2 = login(client, "A"), login(client, "B")
    p, s = new_session(client, h1)
    assert client.get(f"/api/patients/{p['id']}", headers=h2).status_code == 404
    assert client.get(f"/api/sessions/{s['id']}", headers=h2).status_code == 404
    assert client.post(f"/api/sessions/{s['id']}/message", json={"content": "hi"}, headers=h2).status_code == 404


def test_full_consultation_loop(client):
    h = login(client, "Loop")
    p, s = new_session(client, h)
    sid = s["id"]
    assert s["status"] == "active" and 590 <= s["seconds_remaining"] <= 600
    assert s["board"]["discovered_count"] == 0 and s["board"]["total_facts"] >= 5
    for w in HIDDEN_WORDS:
        assert w not in str(s)

    questions = [
        "Thank you for coming in. That sounds really difficult. How has work been lately, any recent changes?",
        "I hear you, that makes sense. Tell me about your colleagues and how you see yourself next to them.",
        "That must be hard. What about your family — what do they expect, and what is at stake for you?",
        "I appreciate you sharing that. How do you spend your weekends, do you have friends or support nearby?",
        "Take your time. Tell me about where you grew up and how you moved here.",
        "It's okay. Has anything happened recently, like a promotion or something you haven't told anyone?",
        "That sounds lonely. How does it feel to talk about this stuff here?",
    ]
    seen_keys, total_new = set(), 0
    for q in questions:
        r = client.post(f"/api/sessions/{sid}/message", json={"content": q}, headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["patient_message"]["role"] == "patient" and d["patient_message"]["content"]
        assert d["patient_message"]["emotion"] in ("neutral", "warm", "sad", "anxious", "guarded", "tearful", "relieved", "frustrated")
        assert 0 <= d["comfort"] <= 100
        for item in d["new_discoveries"]:
            assert item["key"] not in seen_keys  # no duplicates ever returned
            seen_keys.add(item["key"])
            assert item["state"] in ("discovered", "important", "connected")
        total_new += len(d["new_discoveries"])
    assert total_new >= 2, "discovery engine should unlock facts"

    board = client.get(f"/api/sessions/{sid}/board", headers=h).json()
    assert board["discovered_count"] == len(seen_keys)
    assert any(i["state"] in ("important", "connected") for i in board["items"])

    # notes
    r = client.post(f"/api/sessions/{sid}/notes", json={"notes": "self doubt + family?"}, headers=h)
    assert r.json()["notes"] == "self doubt + family?"

    # evaluate before assessment -> 409
    assert client.post(f"/api/sessions/{sid}/evaluate", headers=h).status_code == 409

    a = {"main_concern": "Work pressure and self doubt leading to exhaustion",
         "important_symptoms": "tiredness, overwhelmed, concentration",
         "underlying_concerns": "fear of disappointing family, comparison with colleagues, isolation",
         "important_discoveries": "missed promotion, moved city",
         "next_steps": "explore workload boundaries, build social connection, self-compassion, follow-up sessions"}
    r = client.post(f"/api/sessions/{sid}/assessment", json=a, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "assessed"
    # no messages after end
    assert client.post(f"/api/sessions/{sid}/message", json={"content": "one more?"}, headers=h).status_code == 409

    r = client.post(f"/api/sessions/{sid}/evaluate", headers=h)
    assert r.status_code == 200, r.text
    res = r.json()
    cats = res["category_scores"]
    assert abs(res["overall_score"] - scoring.overall_score(cats)) < 0.11
    assert 0 <= res["satisfaction_score"] <= 100 and 0 <= res["understanding_score"] <= 100
    assert res["xp_awarded"] > 0 and res["profile"]["xp"] == res["xp_awarded"]
    assert any(a["code"] == "first_consult" for a in res["new_achievements"])
    # idempotent evaluation: no double XP
    again = client.post(f"/api/sessions/{sid}/evaluate", headers=h).json()
    assert again["profile"]["xp"] == res["profile"]["xp"]
    assert client.get(f"/api/sessions/{sid}/results", headers=h).json()["overall_score"] == res["overall_score"]

    # persistence: history + progress, next patient available
    hist = client.get("/api/sessions/history", headers=h).json()
    assert hist[0]["session_id"] == sid and hist[0]["overall_score"] == res["overall_score"]
    prog = client.get("/api/game/progress", headers=h).json()
    assert prog["profile"]["sessions_completed"] == 1
    p2 = client.post("/api/patients/generate", headers=h).json()
    assert p2["id"] != p["id"]
    s_again = client.get(f"/api/sessions/{sid}", headers=h).json()
    assert len(s_again["messages"]) == 2 * len(questions)


def test_session_expiry_rejects_messages(client):
    h = login(client, "Timer")
    _, s = new_session(client, h)
    with SessionLocal() as db:
        row = db.get(ConsultSession, s["id"])
        row.started_at = row.started_at - timedelta(minutes=11)
        row.ends_at = row.started_at + timedelta(minutes=10)
        db.commit()
    r = client.post(f"/api/sessions/{s['id']}/message", json={"content": "hello?"}, headers=h)
    assert r.status_code == 409
    st = client.get(f"/api/sessions/{s['id']}", headers=h).json()
    assert st["status"] == "ended" and st["seconds_remaining"] == 0


def test_manual_end(client):
    h = login(client, "Ender")
    _, s = new_session(client, h)
    r = client.post(f"/api/sessions/{s['id']}/end", headers=h)
    assert r.json()["status"] == "ended"
    assert client.post(f"/api/sessions/{s['id']}/message", json={"content": "hi"}, headers=h).status_code == 409


def test_short_session_scores_low(client):
    h = login(client, "Lazy")
    _, s = new_session(client, h)
    client.post(f"/api/sessions/{s['id']}/assessment",
                json={"main_concern": "stress", "next_steps": "rest"}, headers=h)
    res = client.post(f"/api/sessions/{s['id']}/evaluate", headers=h).json()
    assert res["overall_score"] < 50
    assert res["category_scores"]["empathy_rapport"] <= 25


# ---------- unit tests ----------

def test_weighted_formula():
    c = dict(empathy_rapport=100, question_relevance=80, active_listening=60, understanding_symptoms=40,
             underlying_concerns=20, next_steps=0)
    assert scoring.overall_score(c) == round(0.2 * 100 + 0.2 * 80 + 0.15 * 60 + 0.2 * 40 + 0.15 * 20, 1)
    assert scoring.overall_score({k: 150 for k in c}) == 100.0  # clamped


def test_satisfaction_and_understanding():
    assert scoring.satisfaction_score({"a": 80, "b": 100}) == 90
    score, parts = scoring.understanding_score(0.5, dict(assessment_accuracy=80, connections_identified=60,
                                                         uncertainty_recognition=50, prioritization=70))
    assert parts["facts_discovered"] == 50
    assert score == round(0.35 * 50 + 0.3 * 80 + 0.15 * 60 + 0.1 * 50 + 0.1 * 70, 1)


def test_coverage_is_importance_weighted():
    facts = [{"key": "a", "importance": 3}, {"key": "b", "importance": 1}]
    assert scoring.discovery_coverage(facts, {"a"}) == 0.75


def test_xp_and_levels():
    assert xp_required(1) == 0 and xp_required(2) == 100 and xp_required(3) == 300
    assert level_for_xp(0) == 1 and level_for_xp(99) == 1 and level_for_xp(100) == 2 and level_for_xp(650) == 4
    assert xp_for_session(80, 80, 80, "Intermediate", 0.5) == 100
    assert xp_for_session(80, 80, 80, "Beginner", 1.0) == 90
    assert xp_for_session(0, 0, 0, "Beginner", 0) == 5


def test_discovery_validation_rejects_unknown_low_conf_and_dupes():
    und = [{"key": "a", "importance": 1}, {"key": "b", "importance": 3}]
    found = [{"key": "a", "confidence": 0.9}, {"key": "a", "confidence": 0.9},
             {"key": "b", "confidence": 0.3}, {"key": "zzz", "confidence": 1.0}]
    out = discovery.validate(found, und)
    assert [o["fact"]["key"] for o in out] == ["a"]


def test_discovery_states():
    assert discovery.state_for({"importance": 1, "related_keys": []}, set()) == "discovered"
    assert discovery.state_for({"importance": 3, "related_keys": ["x"]}, set()) == "important"
    assert discovery.state_for({"importance": 1, "related_keys": ["x"]}, {"x"}) == "connected"


def test_comfort_rises_with_warmth_and_is_capped(client):
    h = login(client, "Warm")
    _, s = new_session(client, h)
    start = s["comfort"]
    r = client.post(f"/api/sessions/{s['id']}/message",
                    json={"content": "Thank you for sharing, that sounds really hard. How has work been?"}, headers=h).json()
    assert start < r["comfort"] <= start + 15

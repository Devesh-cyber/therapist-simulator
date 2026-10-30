"""Session Evaluator — Grok grades the consultation; the Scoring Engine computes final numbers."""
import json

from ..schemas import SessionEvaluationLLM
from . import mock_engine
from .llm import get_client, use_mock

SYSTEM = """You are an experienced, fair clinical supervisor grading a player's performance in a
therapy-simulation GAME. Grade only what is in the transcript and the player's final assessment.

Score each item 0-100 (integers fine):
category_scores:
  empathy_rapport        - warmth, validation, non-judgement, building trust
  question_relevance     - open-ended, purposeful, well-timed questions (not interrogation)
  active_listening       - reflecting back, following up on what the patient said, not ignoring cues
  understanding_symptoms - how well the assessment captures the reported symptoms and experiences
  underlying_concerns    - whether the player identified the deeper concerns (compare to hidden profile)
  next_steps             - whether proposed next steps are appropriate, supportive and realistic
satisfaction (how the PATIENT would feel): feeling_heard, empathy, respect, comfort, trust, feeling_understood
understanding:
  assessment_accuracy     - final assessment vs the true profile
  connections_identified  - did the player link related concerns
  uncertainty_recognition - did the player acknowledge what they don't yet know (rather than overclaiming)
  prioritization          - did they prioritise the most important concerns
Also give 2-4 specific strengths, 2-4 specific improvements (refer to concrete moments) and a 1-2 sentence summary.
Be calibrated: a short or superficial session should not score highly. Do NOT compute a weighted total.
Return ONLY JSON with keys: category_scores, satisfaction, understanding, strengths, improvements, summary."""


def evaluate(profile: dict, transcript: list[dict], discovered_keys: set[str], assessment: dict) -> SessionEvaluationLLM:
    if use_mock():
        return mock_engine.evaluate(profile, transcript, discovered_keys, assessment)
    name = profile["name"]
    convo = "\n".join(f"{'Therapist' if m['role'] == 'player' else name}: {m['content']}"
                      for m in transcript if m["role"] in ("player", "patient"))
    discovered = [f["label"] for f in profile["discovery_facts"] if f["key"] in discovered_keys]
    missed = [f["label"] for f in profile["discovery_facts"] if f["key"] not in discovered_keys]
    user = (
        f"HIDDEN PATIENT PROFILE:\n{json.dumps(profile, ensure_ascii=False, indent=1)}\n\n"
        f"TRANSCRIPT ({sum(1 for m in transcript if m['role'] == 'player')} therapist messages):\n{convo or '(no conversation)'}\n\n"
        f"FACTS DISCOVERED: {discovered}\nFACTS MISSED: {missed}\n\n"
        f"PLAYER'S FINAL ASSESSMENT:\n{json.dumps(assessment, ensure_ascii=False, indent=1)}"
    )
    return get_client().complete_json(SYSTEM, user, SessionEvaluationLLM, temperature=0.2, max_tokens=4000)

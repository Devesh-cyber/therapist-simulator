"""Discovery Evaluator — decides which hidden facts the patient has ACTUALLY revealed.

Grok proposes candidate discoveries semantically; the backend then validates them against
the hidden profile (key must exist, must not be discovered yet, confidence threshold) and
computes Important / Connected states deterministically.
"""
import json

from ..schemas import DiscoveryResultLLM
from . import mock_engine
from .llm import get_client, use_mock

CONFIDENCE_THRESHOLD = 0.6

SYSTEM = """You are the Discovery Evaluator for a therapy simulation game.
Decide which HIDDEN FACTS the PATIENT has genuinely revealed or confirmed in their LATEST reply.

Rules:
- Only the patient's words count. A therapist's question or guess is NOT a discovery unless the patient
  clearly confirms it in their reply.
- Partial, vague or evasive answers do not count. The core meaning of the fact must be disclosed.
- Paraphrases count if the meaning matches (semantic match, not keywords).
- Only consider the candidate facts listed. Use their exact keys.
- confidence: 0.0-1.0. evidence: the patient's words (max 25 words) that reveal it.
Return ONLY JSON: {"discoveries": [{"key": "...", "confidence": 0.0, "evidence": "..."}]}  (empty list if none)."""


def detect(profile: dict, undiscovered: list[dict], recent: list[dict], player_msg: str, patient_reply: str) -> list[dict]:
    if not undiscovered:
        return []
    if use_mock():
        found = mock_engine.detect(profile, undiscovered, patient_reply)
    else:
        context = "\n".join(f"{'Therapist' if m['role'] == 'player' else 'Patient'}: {m['content']}" for m in recent[-6:])
        candidates = [{"key": f["key"], "fact": f["fact"]} for f in undiscovered]
        user = (
            f"CANDIDATE HIDDEN FACTS:\n{json.dumps(candidates, ensure_ascii=False, indent=1)}\n\n"
            f"RECENT CONTEXT:\n{context or '(start of session)'}\n\n"
            f"THERAPIST (latest): {player_msg}\nPATIENT (latest reply): {patient_reply}"
        )
        result = get_client().complete_json(SYSTEM, user, DiscoveryResultLLM, temperature=0.0, max_tokens=2000)
        found = [d.model_dump() for d in result.discoveries]
    return validate(found, undiscovered)


def validate(found: list[dict], undiscovered: list[dict]) -> list[dict]:
    """Backend validation: known key, not already discovered, confident, de-duplicated."""
    allowed = {f["key"]: f for f in undiscovered}
    out, seen = [], set()
    for d in found:
        key = str(d.get("key", "")).strip()
        if key in allowed and key not in seen and float(d.get("confidence", 0)) >= CONFIDENCE_THRESHOLD:
            seen.add(key)
            out.append({"fact": allowed[key], "evidence": str(d.get("evidence", ""))[:300]})
    return out


def state_for(fact: dict, discovered_keys: set[str]) -> str:
    """Connected beats Important beats Discovered."""
    if any(k in discovered_keys for k in fact.get("related_keys", [])):
        return "connected"
    if fact.get("importance", 1) >= 3:
        return "important"
    return "discovered"

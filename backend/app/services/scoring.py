"""Scoring Engine — all final numbers are computed here in Python, never trusted from the LLM."""

WEIGHTS = {
    "empathy_rapport": 0.20,
    "question_relevance": 0.20,
    "active_listening": 0.15,
    "understanding_symptoms": 0.20,
    "underlying_concerns": 0.15,
    "next_steps": 0.10,
}

CATEGORY_LABELS = {
    "empathy_rapport": "Empathy and Rapport",
    "question_relevance": "Question Relevance",
    "active_listening": "Active Listening",
    "understanding_symptoms": "Understanding Symptoms",
    "underlying_concerns": "Identifying Underlying Concerns",
    "next_steps": "Appropriate Next Steps",
}


def clamp(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


def overall_score(categories: dict) -> float:
    """S = 0.20E + 0.20Q + 0.15L + 0.20U + 0.15C + 0.10N"""
    return round(sum(WEIGHTS[k] * clamp(categories[k]) for k in WEIGHTS), 1)


def satisfaction_score(breakdown: dict) -> float:
    vals = [clamp(v) for v in breakdown.values()]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def discovery_coverage(facts: list[dict], discovered_keys: set[str]) -> float:
    """Importance-weighted share of hidden facts discovered (0..1)."""
    total = sum(f["importance"] for f in facts) or 1
    got = sum(f["importance"] for f in facts if f["key"] in discovered_keys)
    return got / total


def understanding_score(coverage: float, llm_parts: dict) -> tuple[float, dict]:
    """35% discovered facts (deterministic) + 30% assessment accuracy + 15% connections
    + 10% uncertainty recognition + 10% prioritisation."""
    parts = {
        "facts_discovered": round(coverage * 100, 1),
        "assessment_accuracy": clamp(llm_parts["assessment_accuracy"]),
        "connections_identified": clamp(llm_parts["connections_identified"]),
        "uncertainty_recognition": clamp(llm_parts["uncertainty_recognition"]),
        "prioritization": clamp(llm_parts["prioritization"]),
    }
    w = {"facts_discovered": 0.35, "assessment_accuracy": 0.30, "connections_identified": 0.15,
         "uncertainty_recognition": 0.10, "prioritization": 0.10}
    return round(sum(parts[k] * w[k] for k in w), 1), parts


def rating(score: float) -> str:
    if score >= 90:
        return "Outstanding session"
    if score >= 75:
        return "Good performance"
    if score >= 60:
        return "Solid start"
    if score >= 40:
        return "Room to grow"
    return "Tough session"

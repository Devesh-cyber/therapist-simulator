"""Patient Generator — creates complete, internally consistent fictional patient profiles."""
import json

from ..schemas import BOARD_CATEGORIES, PatientProfileLLM
from . import mock_engine
from .llm import get_client, use_mock
from .progression import DIFFICULTY_GUIDE, difficulty_for_level

SYSTEM = """You design fictional patients for "Therapist Simulator", a casual simulation GAME about
listening and understanding people. Patients are entirely fictional adults dealing with everyday
life stressors (work, family, relationships, transitions, loss, identity, burnout, loneliness, etc.).

Hard rules:
- Fictional people only. No real or famous names.
- Keep it game-appropriate: no suicide, self-harm, abuse, sexual content, eating disorders,
  psychosis or substance dependence storylines. No medical diagnoses or medication.
- The profile must be internally consistent: every discovery fact must fit the background.
- Difficulty must come from complexity, interconnection and guardedness — NOT from severity.
- Output ONLY one JSON object matching the schema. No markdown."""

SCHEMA_HINT = {
    "name": "string (first and last name)",
    "age": "integer 18-75",
    "occupation": "string",
    "presenting_concern": "1-2 sentence first-person quote the patient says on arrival",
    "reported_symptoms": ["2-4 short phrases the patient openly reports"],
    "personality": "string",
    "communication_style": "string (how they talk, deflect, open up)",
    "openness": "low | medium | high",
    "background": "string, 2-4 sentences",
    "emotional_concerns": ["strings"],
    "underlying_concerns": ["strings"],
    "life_events": ["strings"],
    "relationships": "string",
    "session_objective": "one sentence goal for the player",
    "possible_next_steps": ["3-5 supportive, non-clinical next steps"],
    "look": {"gender": "woman|man|nonbinary", "skin": "1-6 (1 lightest, 6 deepest)",
             "hair": "short|long|bun|curly|buzz|wavy", "hair_color": "black|dark|brown|auburn|blonde|gray",
             "outfit": "#hex muted colour", "glasses": "true|false", "beard": "true|false"},
    "discovery_facts": [{
        "key": "snake_case_unique_id",
        "category": "one of the board categories",
        "label": "short board title (max 6 words)",
        "fact": "the full hidden fact",
        "importance": "1 (minor) | 2 (relevant) | 3 (key insight)",
        "related_keys": ["keys of facts this connects to"],
        "reveal_hint": "what the player must do / ask before the patient shares this",
        "patient_line": "how the patient might say it, first person",
    }],
}


def generate_profile(level: int, avoid_names: list[str] | None = None) -> tuple[PatientProfileLLM, str]:
    difficulty = difficulty_for_level(level)
    if use_mock():
        return mock_engine.generate_patient(level, avoid_names), difficulty

    user = (
        f"Create one patient for player level {level} (difficulty: {difficulty}).\n"
        f"Difficulty guidance: {DIFFICULTY_GUIDE[difficulty]}\n"
        f"Board categories (use these exact strings for discovery_facts.category; do not use "
        f"'Basic Information' or 'Presenting Concern' for hidden facts): {json.dumps(BOARD_CATEGORIES)}\n"
        "Every fact in emotional_concerns, underlying_concerns and life_events must also appear as a discovery fact. "
        "At least two facts must have importance 3, and important facts should be connected via related_keys.\n"
        f"Avoid these recently used names: {', '.join(avoid_names or []) or 'none'}. Vary gender, age, region and occupation.\n"
        f"JSON schema:\n{json.dumps(SCHEMA_HINT, indent=1)}"
    )
    profile = get_client().complete_json(SYSTEM, user, PatientProfileLLM, temperature=0.9, max_tokens=6000)
    return profile, difficulty

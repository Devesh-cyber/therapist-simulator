"""Pydantic models: LLM output contracts and API request/response shapes."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

BOARD_CATEGORIES = [
    "Basic Information",
    "Presenting Concern",
    "Symptoms and Experiences",
    "Emotional State",
    "Personal Background",
    "Relationships and Social Environment",
    "Important Life Events",
    "Underlying Concerns",
    "Patient Needs",
    "Possible Next Steps",
]


# ---------- LLM output contracts ----------

class DiscoveryFact(BaseModel):
    key: str = Field(min_length=2, max_length=60)
    category: str
    label: str = Field(min_length=2, max_length=120)  # short title shown on the board
    fact: str = Field(min_length=5)  # full hidden fact
    importance: int = Field(ge=1, le=3)
    related_keys: list[str] = Field(default_factory=list)
    reveal_hint: str = ""  # when/how the patient is willing to share it
    patient_line: str = ""  # example of how the patient might say it, first person

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        for c in BOARD_CATEGORIES:
            if c.lower() == v.strip().lower():
                return c
        raise ValueError(f"unknown board category: {v}")

    @field_validator("key")
    @classmethod
    def slug_key(cls, v: str) -> str:
        return "_".join(v.strip().lower().replace("-", "_").split())


EMOTIONS = ["neutral", "warm", "sad", "anxious", "guarded", "tearful", "relieved", "frustrated"]


class PatientLook(BaseModel):
    """Appearance for the illustrated character (not secret — visible on arrival)."""
    gender: Literal["woman", "man", "nonbinary"] | None = None
    skin: int | None = Field(default=None, ge=1, le=6)
    hair: Literal["short", "long", "bun", "curly", "buzz", "wavy"] | None = None
    hair_color: Literal["black", "dark", "brown", "auburn", "blonde", "gray"] | None = None
    outfit: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    glasses: bool | None = None
    beard: bool | None = None


class PatientTurnLLM(BaseModel):
    line: str = Field(min_length=1, max_length=1200)
    emotion: str = "neutral"
    comfort: float = Field(default=40, ge=0, le=100)

    @field_validator("emotion")
    @classmethod
    def known_emotion(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in EMOTIONS else "neutral"


class PatientProfileLLM(BaseModel):
    name: str
    age: int = Field(ge=16, le=90)
    occupation: str
    presenting_concern: str  # first-person quote for the arrival card
    reported_symptoms: list[str] = Field(min_length=1, max_length=6)
    personality: str
    communication_style: str
    openness: Literal["low", "medium", "high"]
    background: str
    emotional_concerns: list[str]
    underlying_concerns: list[str]
    life_events: list[str]
    relationships: str
    session_objective: str
    possible_next_steps: list[str] = Field(min_length=1)
    discovery_facts: list[DiscoveryFact] = Field(min_length=5, max_length=14)
    look: PatientLook = Field(default_factory=PatientLook)

    @field_validator("look", mode="before")
    @classmethod
    def lenient_look(cls, v):
        # A malformed look must never fail patient generation; drop bad fields instead.
        if not isinstance(v, dict):
            return {}
        out = {}
        for k, val in v.items():
            try:
                PatientLook.model_validate({k: val})
                out[k] = val
            except Exception:
                pass
        return out

    @field_validator("discovery_facts")
    @classmethod
    def unique_keys(cls, facts: list[DiscoveryFact]) -> list[DiscoveryFact]:
        seen, out = set(), []
        for f in facts:
            if f.key not in seen:
                seen.add(f.key)
                out.append(f)
        keys = {f.key for f in out}
        for f in out:
            f.related_keys = [k for k in f.related_keys if k in keys and k != f.key]
        return out


class DetectedFact(BaseModel):
    key: str
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""


class DiscoveryResultLLM(BaseModel):
    discoveries: list[DetectedFact] = Field(default_factory=list)


class CategoryScores(BaseModel):
    empathy_rapport: float = Field(ge=0, le=100)
    question_relevance: float = Field(ge=0, le=100)
    active_listening: float = Field(ge=0, le=100)
    understanding_symptoms: float = Field(ge=0, le=100)
    underlying_concerns: float = Field(ge=0, le=100)
    next_steps: float = Field(ge=0, le=100)


class SatisfactionBreakdown(BaseModel):
    feeling_heard: float = Field(ge=0, le=100)
    empathy: float = Field(ge=0, le=100)
    respect: float = Field(ge=0, le=100)
    comfort: float = Field(ge=0, le=100)
    trust: float = Field(ge=0, le=100)
    feeling_understood: float = Field(ge=0, le=100)


class UnderstandingLLM(BaseModel):
    assessment_accuracy: float = Field(ge=0, le=100)
    connections_identified: float = Field(ge=0, le=100)
    uncertainty_recognition: float = Field(ge=0, le=100)
    prioritization: float = Field(ge=0, le=100)


class SessionEvaluationLLM(BaseModel):
    category_scores: CategoryScores
    satisfaction: SatisfactionBreakdown
    understanding: UnderstandingLLM
    strengths: list[str] = Field(default_factory=list, max_length=5)
    improvements: list[str] = Field(default_factory=list, max_length=5)
    summary: str = ""


# ---------- API shapes ----------

class GuestLoginIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


class ProfileOut(BaseModel):
    id: str
    display_name: str
    xp: int
    level: int
    difficulty: str
    sessions_completed: int
    xp_for_current_level: int
    xp_for_next_level: int


class AuthOut(BaseModel):
    token: str
    profile: ProfileOut


class PatientPublic(BaseModel):
    """Player-visible patient card. Contains no hidden information."""
    id: str
    name: str
    age: int
    occupation: str
    level: int
    difficulty: str
    presenting_concern: str
    reported_symptoms: list[str]
    session_objective: str
    status: str
    look: dict = Field(default_factory=dict)
    opening_emotion: str = "neutral"  # how they look when they sit down


class BoardItem(BaseModel):
    key: str
    category: str
    label: str
    detail: str
    importance: int
    state: str
    evidence: str = ""
    connected_to: list[str] = Field(default_factory=list)


class BoardCategory(BaseModel):
    name: str
    total: int
    discovered: int


class BoardOut(BaseModel):
    session_id: str
    total_facts: int
    discovered_count: int
    categories: list[BoardCategory]
    items: list[BoardItem]
    notes: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    emotion: str | None = None
    created_at: datetime


class SessionOut(BaseModel):
    id: str
    status: str
    started_at: datetime
    ends_at: datetime
    ended_at: datetime | None
    server_now: datetime
    seconds_remaining: int
    patient: PatientPublic
    messages: list[MessageOut]
    board: BoardOut
    has_assessment: bool
    comfort: int
    llm_mode: str


class StartSessionIn(BaseModel):
    patient_id: str


class SendMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=800)


class SendMessageOut(BaseModel):
    player_message: MessageOut
    patient_message: MessageOut | None
    new_discoveries: list[BoardItem]
    updated_items: list[BoardItem]
    discovered_count: int
    total_facts: int
    seconds_remaining: int
    status: str
    comfort: int
    error: str | None = None


class NotesIn(BaseModel):
    notes: str = Field(max_length=5000)


class AssessmentIn(BaseModel):
    main_concern: str = Field(min_length=3, max_length=1500)
    important_symptoms: str = Field(default="", max_length=1500)
    underlying_concerns: str = Field(default="", max_length=1500)
    important_discoveries: str = Field(default="", max_length=1500)
    next_steps: str = Field(min_length=3, max_length=1500)


class ResultsOut(BaseModel):
    session_id: str
    patient: PatientPublic
    overall_score: float
    rating: str
    satisfaction_score: float
    understanding_score: float
    category_scores: dict
    satisfaction_breakdown: dict
    understanding_breakdown: dict
    feedback: dict
    xp_awarded: int
    discovered_count: int
    total_facts: int
    missed_categories: list[str]
    profile: ProfileOut
    new_achievements: list[dict]
    leveled_up: bool


class HistoryItem(BaseModel):
    session_id: str
    patient_name: str
    patient_occupation: str
    difficulty: str
    status: str
    started_at: datetime
    overall_score: float | None
    xp_awarded: int | None


class ProgressOut(BaseModel):
    profile: ProfileOut
    achievements: list[dict]
    recent: list[HistoryItem]
    average_score: float | None
    best_score: float | None
    waiting_patient: PatientPublic | None
    open_session_id: str | None
    open_session_status: str | None
    llm_mode: str

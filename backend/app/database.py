"""Database service: SQLAlchemy engine, session factory and ORM models.

Works against Supabase PostgreSQL (DATABASE_URL) or local SQLite for development.
The backend connects with a privileged database role, so it can read hidden patient
profiles; Row Level Security (see supabase/migrations) blocks the public anon key.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
    Uuid, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


UUID = Uuid(as_uuid=False)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(60))
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(UUID, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    age: Mapped[int] = mapped_column(Integer)
    occupation: Mapped[str] = mapped_column(String(120))
    level: Mapped[int] = mapped_column(Integer, default=1)
    difficulty: Mapped[str] = mapped_column(String(20))
    presenting_concern: Mapped[str] = mapped_column(Text)
    reported_symptoms: Mapped[list] = mapped_column(JSON, default=list)
    session_objective: Mapped[str] = mapped_column(Text)
    # Complete hidden profile — NEVER returned to the frontend.
    hidden_profile: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # waiting | seen
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConsultSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(UUID, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[str] = mapped_column(UUID, ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    # active -> ended -> assessed -> evaluated
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)  # manual | timeout | assessment
    notes: Mapped[str] = mapped_column(Text, default="")
    comfort: Mapped[int] = mapped_column(Integer, default=40)
    context_summary: Mapped[str] = mapped_column(Text, default="")
    summarized_count: Mapped[int] = mapped_column(Integer, default=0)
    assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship()


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # player | patient | system
    content: Mapped[str] = mapped_column(Text)
    emotion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    seq: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Discovery(Base):
    __tablename__ = "patient_discoveries"
    __table_args__ = (UniqueConstraint("session_id", "fact_key", name="uq_discovery_session_fact"),)
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(UUID, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    fact_key: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default="discovered")  # discovered | important | connected
    evidence: Mapped[str] = mapped_column(Text, default="")
    source_message_id: Mapped[str | None] = mapped_column(UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(UUID, ForeignKey("sessions.id", ondelete="CASCADE"), unique=True)
    overall_score: Mapped[float] = mapped_column(Float)
    satisfaction_score: Mapped[float] = mapped_column(Float)
    understanding_score: Mapped[float] = mapped_column(Float)
    category_scores: Mapped[dict] = mapped_column(JSON)
    satisfaction_breakdown: Mapped[dict] = mapped_column(JSON)
    understanding_breakdown: Mapped[dict] = mapped_column(JSON)
    feedback: Mapped[dict] = mapped_column(JSON)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Achievement(Base):
    __tablename__ = "achievements"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(40), default="award")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("profile_id", "achievement_code", name="uq_user_achievement"),)
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(UUID, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    achievement_code: Mapped[str] = mapped_column(String(40), ForeignKey("achievements.code"))
    session_id: Mapped[str | None] = mapped_column(UUID, nullable=True)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


ACHIEVEMENTS = [
    ("first_consult", "First Consultation", "Complete your first evaluated consultation.", "stethoscope"),
    ("warm_presence", "Warm Presence", "Score 90+ in Empathy and Rapport.", "heart"),
    ("detective", "Full Picture", "Discover every hidden fact about a patient.", "search"),
    ("high_marks", "High Marks", "Reach an overall performance of 90+.", "trophy"),
    ("regular", "Clinic Regular", "Complete 5 consultations.", "calendar"),
]

_settings = get_settings()
_url = _settings.sqlalchemy_url
engine = create_engine(
    _url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if missing (SQLite dev). On Supabase, run the SQL migration instead;
    create_all is a no-op for tables that already exist."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for code, title, desc, icon in ACHIEVEMENTS:
            if not db.get(Achievement, code):
                db.add(Achievement(code=code, title=title, description=desc, icon=icon))
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

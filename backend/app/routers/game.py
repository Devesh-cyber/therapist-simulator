from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_profile
from ..config import get_settings
from ..database import Achievement, ConsultSession, Evaluation, Patient, Profile, UserAchievement, get_db
from ..schemas import ProgressOut
from ..services import session_manager as sm
from .sessions import history

router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/progress", response_model=ProgressOut)
def progress(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    earned = {ua.achievement_code: ua.earned_at for ua in
              db.scalars(select(UserAchievement).where(UserAchievement.profile_id == profile.id))}
    achievements = [{"code": a.code, "title": a.title, "description": a.description, "icon": a.icon,
                     "earned": a.code in earned, "earned_at": earned.get(a.code)}
                    for a in db.scalars(select(Achievement).order_by(Achievement.code))]
    avg, best = db.execute(
        select(func.avg(Evaluation.overall_score), func.max(Evaluation.overall_score))
        .join(ConsultSession, ConsultSession.id == Evaluation.session_id)
        .where(ConsultSession.owner_id == profile.id)).one()
    waiting = db.scalar(select(Patient).where(Patient.owner_id == profile.id, Patient.status == "waiting")
                        .order_by(Patient.created_at.desc()))
    open_s = db.scalar(select(ConsultSession).where(ConsultSession.owner_id == profile.id,
                                                    ConsultSession.status.in_(["active", "ended", "assessed"]))
                       .order_by(ConsultSession.started_at.desc()))
    if open_s:
        sm.refresh_expiry(db, open_s)
    return ProgressOut(
        profile=sm.profile_out(profile), achievements=achievements, recent=history(profile, db)[:5],
        average_score=round(avg, 1) if avg is not None else None, best_score=best,
        waiting_patient=sm.patient_public(waiting) if waiting else None,
        open_session_id=open_s.id if open_s else None, open_session_status=open_s.status if open_s else None,
        llm_mode=get_settings().effective_llm_mode,
    )

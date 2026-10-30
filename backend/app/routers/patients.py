from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_profile
from ..database import Patient, Profile, get_db
from ..schemas import PatientPublic
from ..services.llm import LLMError
from ..services.patient_generator import generate_profile
from ..services.session_manager import get_owned_patient, patient_public

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/generate", response_model=PatientPublic)
def generate(force: bool = False, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Returns the player's waiting patient, or generates a new one for their current level."""
    if not force:
        waiting = db.scalar(select(Patient).where(Patient.owner_id == profile.id, Patient.status == "waiting")
                            .order_by(Patient.created_at.desc()))
        if waiting:
            return patient_public(waiting)
    recent = list(db.scalars(select(Patient.name).where(Patient.owner_id == profile.id)
                             .order_by(Patient.created_at.desc()).limit(8)))
    try:
        data, difficulty = generate_profile(profile.level, recent)
    except LLMError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Patient generation failed: {e}") from e
    hidden = data.model_dump()
    p = Patient(owner_id=profile.id, name=data.name, age=data.age, occupation=data.occupation, level=profile.level,
                difficulty=difficulty, presenting_concern=data.presenting_concern,
                reported_symptoms=data.reported_symptoms, session_objective=data.session_objective,
                hidden_profile=hidden)
    db.add(p)
    db.commit()
    return patient_public(p)


@router.get("/{patient_id}", response_model=PatientPublic)
def get_patient(patient_id: str, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return patient_public(get_owned_patient(db, patient_id, profile))

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import current_profile, issue_token
from ..database import Profile, get_db
from ..schemas import AuthOut, GuestLoginIn, ProfileOut
from ..services.session_manager import profile_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/guest", response_model=AuthOut)
def guest_login(body: GuestLoginIn, db: Session = Depends(get_db)):
    p = Profile(display_name=body.display_name.strip())
    db.add(p)
    db.commit()
    return AuthOut(token=issue_token(p.id), profile=profile_out(p))


@router.get("/me", response_model=ProfileOut)
def me(profile: Profile = Depends(current_profile)):
    return profile_out(profile)


@router.patch("/me", response_model=ProfileOut)
def rename(body: GuestLoginIn, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    profile = db.merge(profile)
    profile.display_name = body.display_name.strip()
    db.commit()
    return profile_out(profile)

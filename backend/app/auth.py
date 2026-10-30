"""Authentication service.

MVP uses signed guest tokens: POST /api/auth/guest creates a player profile and returns
an HMAC-signed bearer token. Every protected endpoint resolves the token to a profile and
routers check that requested resources belong to that profile.
"""
import base64
import hashlib
import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Profile, get_db


def _sign(payload: str) -> str:
    key = get_settings().app_secret.encode()
    sig = hmac.new(key, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def issue_token(profile_id: str) -> str:
    return f"{profile_id}.{_sign(profile_id)}"


def verify_token(token: str) -> str | None:
    try:
        profile_id, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(profile_id)):
        return None
    return profile_id


def current_profile(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Profile:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    profile_id = verify_token(authorization.split(" ", 1)[1].strip())
    if not profile_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Profile not found")
    return profile

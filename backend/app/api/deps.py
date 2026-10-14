from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import verify_access_token, verify_token
from app.models.user import User
from app.models.settings import UserSettings

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload or ("sub" not in payload and "uid" not in payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or session expired",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = str(payload.get("uid") or payload.get("sub"))
    email = payload.get("email") or f"user_{user_id[:8]}@pluto-ai.local"
    full_name = payload.get("full_name") or payload.get("name") or "Pluto User"
    is_firebase = payload.get("is_firebase", False)

    # 1. Lookup by primary key (id == user_id)
    user = db.query(User).filter(User.id == user_id).first()

    # 2. Lookup by verified email if not found by ID (e.g. existing account from prior local registration)
    if not user and email and not email.endswith("@pluto-ai.local"):
        user = db.query(User).filter(User.email == email.lower()).first()

    # 3. Auto-provision user record and default settings if missing
    if not user:
        user = User(
            id=user_id,
            email=email.lower(),
            full_name=full_name,
            hashed_password="verified_firebase_session" if is_firebase else "verified_jwt_session",
            is_active=True
        )
        db.add(user)
        try:
            db.flush()
            user_settings = UserSettings(user_id=user.id)
            db.add(user_settings)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter((User.id == user_id) | (User.email == email.lower())).first()
    else:
        # Ensure user settings exist
        if not user.settings:
            try:
                user_settings = UserSettings(user_id=user.id)
                db.add(user_settings)
                db.commit()
            except Exception:
                db.rollback()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user or user not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload or ("sub" not in payload and "uid" not in payload):
        return None

    user_id = str(payload.get("uid") or payload.get("sub"))
    email = payload.get("email") or f"user_{user_id[:8]}@pluto-ai.local"
    full_name = payload.get("full_name") or payload.get("name") or "Pluto User"
    is_firebase = payload.get("is_firebase", False)

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user and email and not email.endswith("@pluto-ai.local"):
        user = db.query(User).filter(User.email == email.lower(), User.is_active == True).first()

    if not user:
        user = User(
            id=user_id,
            email=email.lower(),
            full_name=full_name,
            hashed_password="verified_firebase_session" if is_firebase else "verified_jwt_session",
            is_active=True
        )
        db.add(user)
        try:
            db.flush()
            user_settings = UserSettings(user_id=user.id)
            db.add(user_settings)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter((User.id == user_id) | (User.email == email.lower())).first()

    return user

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import verify_access_token
from app.models.user import User

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
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or session expired",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Recreate JWT-verified user session if DB was recreated/ephemeral
        email = payload.get("email") or f"user_{user_id[:8]}@pluto-ai.local"
        user = User(
            id=user_id,
            email=email,
            full_name="Pluto User",
            hashed_password="verified_jwt_session",
            is_active=True
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter(User.id == user_id).first()

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
    token = authorization.split(" ")[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        email = payload.get("email") or f"user_{user_id[:8]}@pluto-ai.local"
        user = User(
            id=user_id,
            email=email,
            full_name="Pluto User",
            hashed_password="verified_jwt_session",
            is_active=True
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user

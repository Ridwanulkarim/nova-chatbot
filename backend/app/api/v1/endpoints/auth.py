import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.models.settings import UserSettings
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter()

_AUTH_ATTEMPTS = defaultdict(list)

def _check_auth_rate_limit(key: str, max_attempts: int = 10, window_seconds: int = 60):
    now = time.time()
    _AUTH_ATTEMPTS[key] = [t for t in _AUTH_ATTEMPTS[key] if now - t < window_seconds]
    if len(_AUTH_ATTEMPTS[key]) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a moment and try again."
        )
    _AUTH_ATTEMPTS[key].append(now)

@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"register_{client_ip}", max_attempts=10, window_seconds=60)

    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )
    
    user = User(
        email=user_in.email.lower(),
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name
    )
    db.add(user)
    db.flush()

    # Create default user settings
    user_settings = UserSettings(user_id=user.id)
    db.add(user_settings)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }

@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(f"login_ip_{client_ip}", max_attempts=15, window_seconds=60)
    _check_auth_rate_limit(f"login_acc_{login_in.email.lower()}", max_attempts=6, window_seconds=60)

    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    token = create_access_token({"sub": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }

from app.core.quota import get_user_quota

@router.get("/quota")
def get_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_user_quota(db, current_user.id)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

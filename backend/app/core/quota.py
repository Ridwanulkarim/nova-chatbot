from datetime import datetime, timezone, time
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.usage import UserDailyUsage
from app.core.config import settings

def get_today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def get_or_create_today_usage(db: Session, user_id: str) -> UserDailyUsage:
    today_str = get_today_str()
    usage = db.query(UserDailyUsage).filter(
        UserDailyUsage.user_id == user_id,
        UserDailyUsage.usage_date == today_str
    ).first()
    if not usage:
        try:
            usage = UserDailyUsage(
                user_id=user_id,
                usage_date=today_str,
                message_count=0,
                image_count=0
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)
        except Exception:
            # Handle race condition where another concurrent request created the record
            db.rollback()
            usage = db.query(UserDailyUsage).filter(
                UserDailyUsage.user_id == user_id,
                UserDailyUsage.usage_date == today_str
            ).first()
    return usage

def get_user_quota(db: Session, user_id: str) -> Dict[str, Any]:
    usage = get_or_create_today_usage(db, user_id)
    
    # Calculate hours until midnight UTC
    now = datetime.now(timezone.utc)
    midnight = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)
    seconds_remaining = (midnight - now).total_seconds()
    hours_remaining = max(1, int(seconds_remaining // 3600))

    return {
        "message_count": usage.message_count,
        "message_limit": settings.DAILY_MESSAGE_LIMIT,
        "remaining_messages": max(0, settings.DAILY_MESSAGE_LIMIT - usage.message_count),
        "image_count": usage.image_count,
        "image_limit": settings.DAILY_IMAGE_LIMIT,
        "remaining_images": max(0, settings.DAILY_IMAGE_LIMIT - usage.image_count),
        "resets_in_hours": hours_remaining
    }

def check_and_consume_message_quota(db: Session, user_id: str):
    usage = get_or_create_today_usage(db, user_id)
    # Atomic check and increment to avoid race conditions
    rows_affected = db.query(UserDailyUsage).filter(
        UserDailyUsage.id == usage.id,
        UserDailyUsage.message_count < settings.DAILY_MESSAGE_LIMIT
    ).update({"message_count": UserDailyUsage.message_count + 1})
    db.commit()

    if rows_affected == 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily free message limit of {settings.DAILY_MESSAGE_LIMIT} reached. Resets at midnight UTC."
        )

def check_and_consume_image_quota(db: Session, user_id: str):
    usage = get_or_create_today_usage(db, user_id)
    # Atomic check and increment to avoid race conditions
    rows_affected = db.query(UserDailyUsage).filter(
        UserDailyUsage.id == usage.id,
        UserDailyUsage.image_count < settings.DAILY_IMAGE_LIMIT
    ).update({"image_count": UserDailyUsage.image_count + 1})
    db.commit()

    if rows_affected == 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily image generation limit of {settings.DAILY_IMAGE_LIMIT} reached. Resets at midnight UTC."
        )

def refund_message_quota(db: Session, user_id: str):
    today_str = get_today_str()
    usage = db.query(UserDailyUsage).filter(
        UserDailyUsage.user_id == user_id,
        UserDailyUsage.usage_date == today_str
    ).first()
    if usage and usage.message_count > 0:
        usage.message_count -= 1
        db.commit()

def refund_image_quota(db: Session, user_id: str):
    today_str = get_today_str()
    usage = db.query(UserDailyUsage).filter(
        UserDailyUsage.user_id == user_id,
        UserDailyUsage.usage_date == today_str
    ).first()
    if usage and usage.image_count > 0:
        usage.image_count -= 1
        db.commit()

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class UserDailyUsage(Base):
    __tablename__ = "user_daily_usages"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    usage_date = Column(String(10), nullable=False, index=True) # YYYY-MM-DD
    message_count = Column(Integer, default=0, nullable=False)
    image_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uix_user_date_usage"),
    )

    user = relationship("User", backref="daily_usages")

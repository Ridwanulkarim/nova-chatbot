import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.core.config import settings

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Chat", nullable=False)
    model = Column(String(100), default=settings.DEFAULT_MODEL, nullable=False)
    system_prompt = Column(Text, nullable=True)
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    share_token = Column(String(64), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="preference", nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="memories")

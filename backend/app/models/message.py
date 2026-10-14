import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    citations = Column(Text, nullable=True) # JSON array of citations
    feedback = Column(Integer, nullable=True) # 1 for thumbs up, -1 for thumbs down
    attachments = Column(Text, nullable=True) # JSON array of attached files/images/videos
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

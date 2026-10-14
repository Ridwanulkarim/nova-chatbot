import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="chunks")

from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.core.config import settings

class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    default_model = Column(String(100), default=settings.DEFAULT_MODEL, nullable=False)
    temperature = Column(Float, default=0.7, nullable=False)
    system_instructions = Column(Text, default="", nullable=False)
    memory_enabled = Column(Boolean, default=True, nullable=False)
    web_search_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")

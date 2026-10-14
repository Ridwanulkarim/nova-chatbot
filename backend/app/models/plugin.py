import uuid
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class UserPlugin(Base):
    __tablename__ = "user_plugins"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "plugin_id", name="uq_user_plugin"),
    )

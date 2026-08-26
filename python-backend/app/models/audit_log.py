from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer, nullable=False, index=True)
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(80), nullable=False, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    before_json = Column(Text, nullable=False, default="{}")
    after_json = Column(Text, nullable=False, default="{}")
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())

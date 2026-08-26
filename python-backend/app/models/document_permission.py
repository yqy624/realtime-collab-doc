from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from .database import Base


class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_document_permission_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    permission = Column(String(30), nullable=False, default="view")
    source = Column(String(30), nullable=False, default="manual")
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func

from .database import Base


class DocumentShare(Base):
    """文档分享记录：指定用户 + 权限"""
    __tablename__ = "document_shares"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_doc_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    permission = Column(String(10), nullable=False, default="view")  # view | edit
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, func

from .database import Base


class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column("document_id", Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")
    revision = Column(Integer, nullable=False)
    user_id = Column("user_id", Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, default="Untitled Document")
    content = Column(Text, default="")
    creator_id = Column("creator_id", Integer, nullable=False)
    is_public = Column("is_public", Boolean, nullable=False, default=False)
    revision = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now())

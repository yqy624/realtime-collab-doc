from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column("document_id", Integer, nullable=False, index=True)
    user_id = Column("user_id", Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    action = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    elapsed_ms = Column("elapsed_ms", Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())

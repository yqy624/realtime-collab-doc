from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, nullable=False, index=True)
    document_id = Column("document_id", Integer, nullable=True, index=True)
    memory_type = Column(String(30), nullable=False, default="working")
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=False, default="agent")
    importance = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

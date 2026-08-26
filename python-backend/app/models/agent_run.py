from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, nullable=False, index=True)
    document_id = Column("document_id", Integer, nullable=True, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    skill_id = Column(Integer, nullable=True, index=True)
    execution_mode = Column(String(30), nullable=False, default="inline")
    goal = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="planning")
    plan_json = Column("plan_json", Text, nullable=False, default="[]")
    trace_json = Column("trace_json", Text, nullable=False, default="[]")
    memory_json = Column("memory_json", Text, nullable=False, default="[]")
    result_text = Column("result_text", Text, nullable=False, default="")
    model = Column(String(100), nullable=False, default="")
    error = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_run_id = Column(Integer, nullable=False, index=True)
    skill_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    tool_name = Column(String(160), nullable=False, index=True)
    tool_type = Column(String(30), nullable=False, default="builtin")
    status = Column(String(30), nullable=False, default="running")
    approval_status = Column(String(30), nullable=False, default="not_required")
    input_json = Column(Text, nullable=False, default="{}")
    output_json = Column(Text, nullable=False, default="{}")
    error = Column(Text, nullable=False, default="")
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

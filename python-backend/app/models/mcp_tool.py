from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from .database import Base


class MCPTool(Base):
    __tablename__ = "mcp_tools"
    __table_args__ = (
        UniqueConstraint("server_id", "name", name="uq_mcp_tool_server_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, nullable=False, index=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    input_schema_json = Column(Text, nullable=False, default="{}")
    read_only = Column(Boolean, nullable=False, default=True)
    requires_approval = Column(Boolean, nullable=False, default=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

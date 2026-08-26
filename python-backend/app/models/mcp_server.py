from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from .database import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_mcp_server_workspace_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    name = Column(String(120), nullable=False)
    transport = Column(String(30), nullable=False, default="stdio")
    connection_json = Column(Text, nullable=False, default="{}")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

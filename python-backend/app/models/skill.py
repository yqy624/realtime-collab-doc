from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from .database import Base


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_skill_workspace_slug"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    slug = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    scope = Column(String(30), nullable=False, default="global")
    input_schema_json = Column(Text, nullable=False, default="{}")
    output_schema_json = Column(Text, nullable=False, default="{}")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

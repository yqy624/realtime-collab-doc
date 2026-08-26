from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from .database import Base


class SkillVersion(Base):
    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    prompt = Column(Text, nullable=False, default="")
    tool_dependencies_json = Column(Text, nullable=False, default="[]")
    permission_policy_json = Column(Text, nullable=False, default="{}")
    status = Column(String(30), nullable=False, default="published")
    created_by = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

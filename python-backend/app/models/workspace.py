from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    owner_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

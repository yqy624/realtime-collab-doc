from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func

from .database import Base


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("workspace_id", "parent_id", "name", name="uq_folder_sibling_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    parent_id = Column(Integer, nullable=True, index=True)
    name = Column(String(120), nullable=False)
    creator_id = Column(Integer, nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

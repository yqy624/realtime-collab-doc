from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class KnowledgeSource(Base):
    """A permission-scoped source that can be indexed into the knowledge base."""

    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(30), nullable=False, index=True)
    title = Column(String(240), nullable=False)
    uri = Column(String(500), nullable=False, default="")
    owner_id = Column(Integer, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    content_hash = Column(String(64), nullable=False, default="", index=True)
    version = Column(Integer, nullable=False, default=1)
    metadata_json = Column(Text, nullable=False, default="{}")
    permission_snapshot_json = Column(Text, nullable=False, default="{}")
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

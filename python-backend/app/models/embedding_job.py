from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class EmbeddingJob(Base):
    """Indexing job record for document refreshes and imported files."""

    __tablename__ = "embedding_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    requested_by = Column(Integer, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    error = Column(Text, nullable=False, default="")
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

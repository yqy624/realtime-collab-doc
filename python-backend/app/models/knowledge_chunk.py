from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from .database import Base


class KnowledgeChunk(Base):
    """Searchable chunk with lexical and local-vector retrieval metadata."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=False, index=True)
    source_type = Column(String(30), nullable=False, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    embedding_json = Column(Text, nullable=False, default="[]")
    lexical_tokens = Column(Text, nullable=False, default="")
    page_number = Column(Integer, nullable=True)
    location_label = Column(String(120), nullable=False, default="")
    source_version = Column(Integer, nullable=False, default=1)
    permission_snapshot_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )

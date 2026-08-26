"""knowledge hybrid rag

Revision ID: 0003_knowledge_hybrid_rag
Revises: 0002_agent_skill_mcp_platform
Create Date: 2026-08-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import *  # noqa: F401,F403
from app.models.database import Base

revision: str = "0003_knowledge_hybrid_rag"
down_revision: Union[str, None] = "0002_agent_skill_mcp_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    _create_index_if_missing("ix_knowledge_sources_workspace_id", "knowledge_sources", ["workspace_id"])
    _create_index_if_missing("ix_knowledge_sources_document_id", "knowledge_sources", ["document_id"])
    _create_index_if_missing("ix_knowledge_sources_owner_id", "knowledge_sources", ["owner_id"])
    _create_index_if_missing("ix_knowledge_sources_status", "knowledge_sources", ["status"])
    _create_index_if_missing("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])
    _create_index_if_missing("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    _create_index_if_missing("ix_knowledge_chunks_workspace_id", "knowledge_chunks", ["workspace_id"])
    _create_index_if_missing("ix_embedding_jobs_source_id", "embedding_jobs", ["source_id"])
    _create_index_if_missing("ix_embedding_jobs_document_id", "embedding_jobs", ["document_id"])
    _create_index_if_missing("ix_embedding_jobs_workspace_id", "embedding_jobs", ["workspace_id"])
    _create_index_if_missing("ix_embedding_jobs_status", "embedding_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("embedding_jobs")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)

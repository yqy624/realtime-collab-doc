"""platform data governance baseline

Revision ID: 0001_platform_data_governance
Revises:
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import *  # noqa: F401,F403
from app.models.database import Base

revision: str = "0001_platform_data_governance"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Empty databases get the full current baseline. Existing development
    # databases keep their data and are patched below.
    Base.metadata.create_all(bind=bind)

    _add_column_if_missing(
        inspector,
        "documents",
        sa.Column("content_format", sa.String(length=30), nullable=False, server_default="plain_text"),
    )
    _add_column_if_missing(inspector, "documents", sa.Column("workspace_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "documents", sa.Column("folder_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "documents", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    _add_column_if_missing(inspector, "documents", sa.Column("deleted_by", sa.Integer(), nullable=True))
    _add_column_if_missing(
        inspector,
        "documents",
        sa.Column("delete_reason", sa.String(length=240), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        inspector,
        "operation_logs",
        sa.Column("client_id", sa.String(length=120), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        inspector,
        "operation_logs",
        sa.Column("request_id", sa.String(length=120), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        inspector,
        "operation_logs",
        sa.Column("server_instance", sa.String(length=120), nullable=False, server_default=""),
    )

    _create_index_if_missing("ix_documents_deleted_at", "documents", ["deleted_at"])
    _create_index_if_missing("ix_documents_workspace_id", "documents", ["workspace_id"])
    _create_index_if_missing("ix_documents_folder_id", "documents", ["folder_id"])
    _create_index_if_missing("ix_documents_share_token", "documents", ["share_token"])
    _create_index_if_missing(
        "ix_document_permissions_document_user",
        "document_permissions",
        ["document_id", "user_id"],
    )
    _create_index_if_missing(
        "ix_operation_logs_document_revision",
        "operation_logs",
        ["document_id", "revision"],
    )


def downgrade() -> None:
    for table in reversed(Base.metadata.sorted_tables):
        op.drop_table(table.name)


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)

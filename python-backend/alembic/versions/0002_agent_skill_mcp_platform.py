"""agent skill mcp platform

Revision ID: 0002_agent_skill_mcp_platform
Revises: 0001_platform_data_governance
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import *  # noqa: F401,F403
from app.models.database import Base

revision: str = "0002_agent_skill_mcp_platform"
down_revision: Union[str, None] = "0001_platform_data_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    Base.metadata.create_all(bind=bind)

    _add_column_if_missing(inspector, "agent_runs", sa.Column("workspace_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "agent_runs", sa.Column("skill_id", sa.Integer(), nullable=True))
    _add_column_if_missing(
        inspector,
        "agent_runs",
        sa.Column("execution_mode", sa.String(length=30), nullable=False, server_default="inline"),
    )

    _create_index_if_missing("ix_agent_runs_workspace_id", "agent_runs", ["workspace_id"])
    _create_index_if_missing("ix_agent_runs_skill_id", "agent_runs", ["skill_id"])
    _create_index_if_missing("ix_skills_workspace_id", "skills", ["workspace_id"])
    _create_index_if_missing("ix_skills_slug", "skills", ["slug"])
    _create_index_if_missing("ix_skill_versions_skill_id", "skill_versions", ["skill_id"])
    _create_index_if_missing("ix_mcp_servers_workspace_id", "mcp_servers", ["workspace_id"])
    _create_index_if_missing("ix_mcp_tools_server_id", "mcp_tools", ["server_id"])
    _create_index_if_missing("ix_tool_invocations_agent_run_id", "tool_invocations", ["agent_run_id"])
    _create_index_if_missing("ix_tool_invocations_tool_name", "tool_invocations", ["tool_name"])
    _create_index_if_missing("ix_tool_invocations_user_id", "tool_invocations", ["user_id"])
    _create_index_if_missing("ix_tool_invocations_document_id", "tool_invocations", ["document_id"])
    _create_index_if_missing("ix_tool_invocations_workspace_id", "tool_invocations", ["workspace_id"])
    _create_index_if_missing("ix_tool_invocations_skill_id", "tool_invocations", ["skill_id"])


def downgrade() -> None:
    op.drop_table("tool_invocations")
    op.drop_table("mcp_tools")
    op.drop_table("mcp_servers")
    op.drop_table("skill_versions")
    op.drop_table("skills")
    _drop_column_if_present("agent_runs", "execution_mode")
    _drop_column_if_present("agent_runs", "skill_id")
    _drop_column_if_present("agent_runs", "workspace_id")


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


def _drop_column_if_present(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column_name in columns:
        op.drop_column(table_name, column_name)

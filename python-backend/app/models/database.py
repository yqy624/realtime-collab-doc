from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# SQLite needs connect_args for threading
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)

# Enable WAL mode for SQLite for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_document_share_columns():
    """Add share columns to databases created before document sharing existed."""
    columns = {column["name"] for column in inspect(engine).get_columns("documents")}
    missing = []
    if "share_token" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN share_token VARCHAR(64)")
    if "share_permission" not in columns:
        missing.append(
            "ALTER TABLE documents ADD COLUMN share_permission VARCHAR(10) NOT NULL DEFAULT 'view'"
        )

    if missing:
        with engine.begin() as connection:
            for statement in missing:
                connection.execute(text(statement))


def ensure_document_platform_columns():
    """Add platform columns while keeping existing document rows valid."""
    columns = {column["name"] for column in inspect(engine).get_columns("documents")}
    missing = []
    if "content_format" not in columns:
        missing.append(
            "ALTER TABLE documents ADD COLUMN content_format VARCHAR(30) NOT NULL DEFAULT 'plain_text'"
        )
    if "workspace_id" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN workspace_id INTEGER")
    if "folder_id" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN folder_id INTEGER")
    if "deleted_at" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN deleted_at DATETIME")
    if "deleted_by" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN deleted_by INTEGER")
    if "delete_reason" not in columns:
        missing.append("ALTER TABLE documents ADD COLUMN delete_reason VARCHAR(240) NOT NULL DEFAULT ''")

    if missing:
        with engine.begin() as connection:
            for statement in missing:
                connection.execute(text(statement))


def ensure_operation_log_platform_columns():
    """Add diagnostics columns for collaborative edit auditing."""
    columns = {column["name"] for column in inspect(engine).get_columns("operation_logs")}
    missing = []
    if "client_id" not in columns:
        missing.append("ALTER TABLE operation_logs ADD COLUMN client_id VARCHAR(120) NOT NULL DEFAULT ''")
    if "request_id" not in columns:
        missing.append("ALTER TABLE operation_logs ADD COLUMN request_id VARCHAR(120) NOT NULL DEFAULT ''")
    if "server_instance" not in columns:
        missing.append("ALTER TABLE operation_logs ADD COLUMN server_instance VARCHAR(120) NOT NULL DEFAULT ''")

    if missing:
        with engine.begin() as connection:
            for statement in missing:
                connection.execute(text(statement))


def ensure_agent_run_platform_columns():
    """Add phase-four columns for existing local development databases."""
    columns = {column["name"] for column in inspect(engine).get_columns("agent_runs")}
    missing = []
    if "workspace_id" not in columns:
        missing.append("ALTER TABLE agent_runs ADD COLUMN workspace_id INTEGER")
    if "skill_id" not in columns:
        missing.append("ALTER TABLE agent_runs ADD COLUMN skill_id INTEGER")
    if "execution_mode" not in columns:
        missing.append("ALTER TABLE agent_runs ADD COLUMN execution_mode VARCHAR(30) NOT NULL DEFAULT 'inline'")

    if missing:
        with engine.begin() as connection:
            for statement in missing:
                connection.execute(text(statement))

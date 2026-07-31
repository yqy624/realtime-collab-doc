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

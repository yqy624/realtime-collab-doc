import argparse

from app.init_data import init_data
from app.models.database import (
    Base,
    engine,
    ensure_agent_run_platform_columns,
    ensure_document_platform_columns,
    ensure_document_share_columns,
    ensure_operation_log_platform_columns,
)


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_document_share_columns()
    ensure_document_platform_columns()
    ensure_operation_log_platform_columns()
    ensure_agent_run_platform_columns()


def seed_db() -> None:
    create_schema()
    init_data()
    print("Seed data is ready.")


def reset_db(yes: bool) -> None:
    if not yes:
        raise SystemExit("Refusing to reset database without --yes.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_data()
    print("Database reset and seed data completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Database utility commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed-db", help="Create missing tables and insert idempotent demo data")
    reset_parser = subparsers.add_parser("reset-db", help="Drop all tables, recreate schema, and seed")
    reset_parser.add_argument("--yes", action="store_true", help="Confirm destructive reset")
    args = parser.parse_args()

    if args.command == "seed-db":
        seed_db()
    elif args.command == "reset-db":
        reset_db(args.yes)


if __name__ == "__main__":
    main()

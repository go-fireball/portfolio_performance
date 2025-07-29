import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import inspect
from alembic import command
from alembic.config import Config

from portfolio.database import engine, Base
from portfolio.models import *  # Import all models to ensure they're registered with Base.metadata


def get_alembic_config():
    """Get the Alembic configuration"""
    # Find the alembic.ini file in the project root
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        print(f"Error: alembic.ini not found at {alembic_ini_path}")
        sys.exit(1)

    # Create Alembic configuration
    alembic_cfg = Config(str(alembic_ini_path))
    return alembic_cfg


def init_db():
    """Initialize the database tables"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
    else:
        print(f"Database already contains tables: {', '.join(existing_tables)}")
        print("Use 'alembic upgrade head' to apply any pending migrations.")


def create_migration(message):
    """Create a new migration"""
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    print(f"Created new migration: {message}")


def upgrade_db(revision="head"):
    """Upgrade the database to the specified revision"""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    print(f"Database upgraded to: {revision}")


def downgrade_db(revision="-1"):
    """Downgrade the database by the specified number of revisions"""
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    print(f"Database downgraded: {revision}")


def show_migrations():
    """Show migration history"""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg, verbose=True)


def main():
    parser = argparse.ArgumentParser(description="Portfolio Tracker Database CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Init DB command
    subparsers.add_parser("init", help="Initialize the database tables")

    # Create migration command
    migration_parser = subparsers.add_parser("makemigration", help="Create a new migration")
    migration_parser.add_argument("message", help="Migration message")

    # Upgrade DB command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade the database")
    upgrade_parser.add_argument("--revision", default="head", help="Revision to upgrade to (default: head)")

    # Downgrade DB command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade the database")
    downgrade_parser.add_argument("--revision", default="-1", help="Revision to downgrade by (default: -1)")

    # Show migrations command
    subparsers.add_parser("showmigrations", help="Show migration history")

    args = parser.parse_args()

    if args.command == "init":
        init_db()
    elif args.command == "makemigration":
        create_migration(args.message)
    elif args.command == "upgrade":
        upgrade_db(args.revision)
    elif args.command == "downgrade":
        downgrade_db(args.revision)
    elif args.command == "showmigrations":
        show_migrations()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""Maintenance commands for the local World Builder library."""

import argparse
from collections.abc import Sequence

from world_builder.persistence.migrations import get_schema_status, migrate_database
from world_builder.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the maintenance command parser."""
    parser = argparse.ArgumentParser(prog="world-builder")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema-status", help="Show the local database migration status.")
    subparsers.add_parser("migrate", help="Back up and upgrade the local database schema.")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run a maintenance command and return its process status."""
    parsed = build_parser().parse_args(arguments)
    database_path = get_settings().database_path

    if parsed.command == "schema-status":
        status = get_schema_status(database_path)
        print(f"Database: {database_path}")
        print(f"State: {status.state.value}")
        print(f"Current revision: {status.current_revision or 'none'}")
        print(f"Expected revision: {status.head_revision}")
        return 0 if not status.requires_migration else 1

    result = migrate_database(database_path)
    print(f"Database migrated to {result.current_revision}.")
    if result.backup_path is not None:
        print(f"Backup created at {result.backup_path}.")
    else:
        print("No existing database required backup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

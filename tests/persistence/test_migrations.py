"""Tests for explicit schema migration and backup behavior."""

import sqlite3
from pathlib import Path

from sqlalchemy import inspect

from world_builder.persistence.database import create_database_engine
from world_builder.persistence.migrations import (
    SchemaState,
    get_schema_status,
    migrate_database,
)


def test_missing_database_requires_migration(database_path: Path) -> None:
    status = get_schema_status(database_path)

    assert status.state is SchemaState.MISSING
    assert status.current_revision is None
    assert status.head_revision == "20260721_0002"


def test_migrate_creates_current_schema_without_backup(database_path: Path) -> None:
    result = migrate_database(database_path)

    assert result.previous_revision is None
    assert result.current_revision == "20260721_0002"
    assert result.backup_path is None
    assert get_schema_status(database_path).state is SchemaState.CURRENT

    engine = create_database_engine(database_path)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version",
            "artworks",
            "lookup_categories",
            "lookup_values",
            "universes",
        }
    finally:
        engine.dispose()


def test_existing_unversioned_database_is_backed_up(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE legacy_note (content TEXT NOT NULL)")
        connection.execute("INSERT INTO legacy_note VALUES ('preserve me')")

    result = migrate_database(database_path)

    assert result.backup_path is not None
    assert result.backup_path.exists()
    with sqlite3.connect(result.backup_path) as backup:
        content = backup.execute("SELECT content FROM legacy_note").fetchone()
    assert content == ("preserve me",)
    assert get_schema_status(database_path).state is SchemaState.CURRENT


def test_current_database_does_not_create_redundant_backup(database_path: Path) -> None:
    migrate_database(database_path)

    result = migrate_database(database_path)

    assert result.previous_revision == "20260721_0002"
    assert result.current_revision == "20260721_0002"
    assert result.backup_path is None
    assert not (database_path.parent / "backups").exists()

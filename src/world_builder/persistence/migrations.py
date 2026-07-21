"""Alembic configuration, schema inspection, backup, and migration services."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from alembic import command
from world_builder.persistence.database import create_database_engine, sqlite_url
from world_builder.settings import PROJECT_ROOT


class SchemaState(StrEnum):
    """Compatibility between a library database and the application schema."""

    MISSING = "missing"
    CURRENT = "current"
    OUTDATED = "outdated"
    AHEAD = "ahead"
    UNVERSIONED = "unversioned"


@dataclass(frozen=True)
class SchemaStatus:
    """Resolved migration status for one database file."""

    state: SchemaState
    current_revision: str | None
    head_revision: str

    @property
    def requires_migration(self) -> bool:
        """Return whether application use should be blocked for migration."""
        return self.state is not SchemaState.CURRENT


@dataclass(frozen=True)
class MigrationResult:
    """Result of an explicit upgrade operation."""

    previous_revision: str | None
    current_revision: str
    backup_path: Path | None


def get_alembic_config(database_path: Path) -> Config:
    """Return Alembic configuration targeting an explicit database path."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        sqlite_url(database_path).render_as_string(hide_password=False).replace("%", "%%"),
    )
    return config


def get_head_revision(database_path: Path) -> str:
    """Return the single migration head expected by this application."""
    script = ScriptDirectory.from_config(get_alembic_config(database_path))
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("No Alembic migration head is configured.")
    return head


def get_schema_status(database_path: Path) -> SchemaStatus:
    """Compare a SQLite database revision to the application's migration head."""
    head = get_head_revision(database_path)
    if not database_path.exists() or database_path.stat().st_size == 0:
        return SchemaStatus(SchemaState.MISSING, None, head)

    engine = create_database_engine(database_path)
    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()

    if current is None:
        return SchemaStatus(SchemaState.UNVERSIONED, None, head)
    if current == head:
        return SchemaStatus(SchemaState.CURRENT, current, head)

    script = ScriptDirectory.from_config(get_alembic_config(database_path))
    known_revisions = {revision.revision for revision in script.walk_revisions()}
    state = SchemaState.OUTDATED if current in known_revisions else SchemaState.AHEAD
    return SchemaStatus(state, current, head)


def backup_database(database_path: Path) -> Path:
    """Create a consistent timestamped SQLite backup before schema migration."""
    backup_directory = database_path.parent / "backups" / "schema"
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_directory / f"{database_path.stem}-{timestamp}.sqlite"

    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)

    return backup_path


def migrate_database(database_path: Path) -> MigrationResult:
    """Back up an existing non-current database and explicitly upgrade to head."""
    initial_status = get_schema_status(database_path)
    if initial_status.state is SchemaState.CURRENT:
        return MigrationResult(
            previous_revision=initial_status.current_revision,
            current_revision=initial_status.head_revision,
            backup_path=None,
        )
    if initial_status.state is SchemaState.AHEAD:
        raise RuntimeError(
            "The database revision is newer than this application. Upgrade the application "
            "before opening this library."
        )

    database_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if database_path.exists() and database_path.stat().st_size > 0:
        backup_path = backup_database(database_path)

    command.upgrade(get_alembic_config(database_path), "head")
    final_status = get_schema_status(database_path)
    if final_status.state is not SchemaState.CURRENT or final_status.current_revision is None:
        raise RuntimeError("Migration completed without reaching the expected schema revision.")

    return MigrationResult(
        previous_revision=initial_status.current_revision,
        current_revision=final_status.current_revision,
        backup_path=backup_path,
    )


def database_path_from_alembic_url(url: str) -> Path:
    """Resolve the SQLite path represented by an Alembic URL for diagnostics."""
    parsed = make_url(url)
    if parsed.database is None:
        raise ValueError("Alembic URL does not contain a SQLite database path.")
    return Path(parsed.database)

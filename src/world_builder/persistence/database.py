"""SQLite engine and transaction helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, event
from sqlalchemy.engine import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker


def sqlite_url(database_path: Path) -> URL:
    """Build a cross-platform SQLAlchemy URL for a SQLite file."""
    return URL.create(drivername="sqlite", database=str(database_path.resolve()))


def create_database_engine(database_path: Path) -> Engine:
    """Create an engine with SQLite integrity settings enabled per connection."""
    engine = create_engine(sqlite_url(database_path))

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the canonical SQLAlchemy session factory."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def database_session(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit a unit of work or roll it back when an exception escapes."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

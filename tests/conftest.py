"""Shared test fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from world_builder.persistence.database import create_database_engine, create_session_factory
from world_builder.persistence.models import Base


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """Return an isolated SQLite path."""
    return tmp_path / "world_builder.sqlite"


@pytest.fixture
def engine(database_path: Path) -> Iterator[Engine]:
    """Return an isolated engine with the current metadata created."""
    database_engine = create_database_engine(database_path)
    Base.metadata.create_all(database_engine)
    yield database_engine
    database_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to the isolated engine."""
    return create_session_factory(engine)

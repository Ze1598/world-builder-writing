"""Cached runtime persistence resources."""

from functools import cache
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from world_builder.persistence.database import create_database_engine, create_session_factory


@cache
def get_engine(database_path: Path) -> Engine:
    """Return one process-wide engine per resolved database path."""
    return create_database_engine(database_path)


@cache
def get_session_factory(database_path: Path) -> sessionmaker[Session]:
    """Return one process-wide session factory per resolved database path."""
    return create_session_factory(get_engine(database_path))

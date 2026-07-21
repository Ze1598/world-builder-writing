"""Tests for SQLite engine and transaction behavior."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.persistence.database import database_session
from world_builder.persistence.models import LookupCategory, LookupValue, Universe


def test_foreign_keys_are_enabled(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_database_session_commits(session_factory: sessionmaker[Session]) -> None:
    universe = Universe(name="First Universe", description="")

    with database_session(session_factory) as session:
        session.add(universe)

    with database_session(session_factory) as session:
        assert session.get(Universe, universe.id) is not None


def test_database_session_rolls_back(session_factory: sessionmaker[Session]) -> None:
    universe = Universe(name="Rollback Universe", description="")

    with (
        pytest.raises(RuntimeError, match="force rollback"),
        database_session(session_factory) as session,
    ):
        session.add(universe)
        session.flush()
        raise RuntimeError("force rollback")

    with database_session(session_factory) as session:
        assert session.get(Universe, universe.id) is None


def test_lookup_value_rejects_unknown_universe(
    session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(IntegrityError), database_session(session_factory) as session:
        category = LookupCategory(code="theme", name="Theme", description="")
        session.add(category)
        session.flush()
        value = LookupValue(
            universe_id=str(uuid4()),
            category_id=category.id,
            name="Found family",
            description="",
        )
        session.add(value)
        session.flush()

"""Tests for universe application behavior."""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateNameError, RecordNotFoundError
from world_builder.domain.models import UniverseInput
from world_builder.domain.services.universes import UniverseService


@pytest.fixture
def service(session_factory: sessionmaker[Session]) -> UniverseService:
    return UniverseService(session_factory)


def test_create_and_list_universes_in_name_order(service: UniverseService) -> None:
    second = service.create_universe(UniverseInput(name="Zeta", description="Second"))
    first = service.create_universe(UniverseInput(name="alpha", description="First"))

    universes = service.list_universes()

    assert [universe.id for universe in universes] == [first.id, second.id]
    assert service.get_universe(first.id) == first


def test_update_universe(service: UniverseService) -> None:
    universe = service.create_universe(UniverseInput(name="Old", description="Before"))

    updated = service.update_universe(
        universe.id,
        UniverseInput(name="New", description="After"),
    )

    assert updated.name == "New"
    assert updated.description == "After"


def test_duplicate_names_are_case_insensitive(service: UniverseService) -> None:
    service.create_universe(UniverseInput(name="Bellhaven", description=""))

    with pytest.raises(DuplicateNameError, match="already exists"):
        service.create_universe(UniverseInput(name="bellhaven", description=""))


def test_update_missing_universe_fails(service: UniverseService) -> None:
    with pytest.raises(RecordNotFoundError, match="no longer exists"):
        service.update_universe(
            "missing-universe",
            UniverseInput(name="Missing", description=""),
        )


def test_universe_input_strips_text() -> None:
    values = UniverseInput(name="  Universe  ", description="  Description  ")

    assert values.name == "Universe"
    assert values.description == "Description"


def test_universe_name_is_required() -> None:
    with pytest.raises(ValidationError):
        UniverseInput(name="   ", description="")

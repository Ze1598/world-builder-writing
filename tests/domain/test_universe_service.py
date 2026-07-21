"""Tests for universe application behavior."""

import pandas as pd
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateNameError, RecordNotFoundError
from world_builder.domain.models import UniverseInput
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.universes import _save_universe_frame


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


def test_table_frame_updates_existing_universes(service: UniverseService) -> None:
    universe = service.create_universe(UniverseInput(name="Before", description="Old"))

    _save_universe_frame(
        service,
        pd.DataFrame([{"id": universe.id, "name": "After", "description": "New"}]),
    )

    updated = service.get_universe(universe.id)
    assert updated is not None
    assert (updated.name, updated.description) == ("After", "New")


def test_table_frame_rejects_duplicate_universe_names(service: UniverseService) -> None:
    first = service.create_universe(UniverseInput(name="First"))
    second = service.create_universe(UniverseInput(name="Second"))

    with pytest.raises(ValueError, match="unique"):
        _save_universe_frame(
            service,
            pd.DataFrame(
                [
                    {"id": first.id, "name": "Same", "description": ""},
                    {"id": second.id, "name": "same", "description": ""},
                ]
            ),
        )

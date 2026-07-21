"""Tests for managed lookup application behavior."""

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateNameError
from world_builder.domain.lookups import MEMBERSHIP_ROLE, RELATIONSHIP_TYPE, THEME
from world_builder.domain.models import LookupValueInput, UniverseInput
from world_builder.domain.services.lookups import LookupService
from world_builder.domain.services.universes import UniverseService
from world_builder.pages.lookups import _save_frame
from world_builder.persistence.models import RelationshipDirectionality


@pytest.fixture
def universe_id(session_factory: sessionmaker[Session]) -> str:
    return UniverseService(session_factory).create_universe(UniverseInput(name="Test universe")).id


@pytest.fixture
def service(session_factory: sessionmaker[Session], universe_id: str) -> LookupService:
    lookup_service = LookupService(session_factory)
    lookup_service.ensure_defaults(universe_id)
    return lookup_service


def test_defaults_are_idempotent_and_editable(service: LookupService, universe_id: str) -> None:
    initial = service.list_values(universe_id, RELATIONSHIP_TYPE)

    service.ensure_defaults(universe_id)
    repeated = service.list_values(universe_id, RELATIONSHIP_TYPE)
    updated = service.update_value(
        initial[0].id,
        LookupValueInput(
            name="Closest friend",
            description="A trusted equal.",
            relationship_directionality=RelationshipDirectionality.SYMMETRIC,
        ),
    )

    assert len(initial) == 4
    assert [value.id for value in repeated] == [value.id for value in initial]
    assert updated.name == "Closest friend"


def test_active_selector_excludes_inactive_but_full_list_retains_it(
    service: LookupService, universe_id: str
) -> None:
    value = service.create_value(universe_id, THEME, LookupValueInput(name="Identity"))

    service.set_active(value.id, is_active=False)

    assert service.list_values(universe_id, THEME, active_only=True) == []
    assert [item.id for item in service.list_values(universe_id, THEME)] == [value.id]


def test_names_are_unique_within_category_case_insensitively(
    service: LookupService, universe_id: str
) -> None:
    service.create_value(universe_id, THEME, LookupValueInput(name="Identity"))

    with pytest.raises(DuplicateNameError, match="already exists"):
        service.create_value(universe_id, THEME, LookupValueInput(name="identity"))


def test_same_name_can_exist_in_different_categories(
    service: LookupService, universe_id: str
) -> None:
    theme = service.create_value(universe_id, THEME, LookupValueInput(name="Leader"))

    roles = service.list_values(universe_id, MEMBERSHIP_ROLE)

    assert theme.name == "Leader"
    assert any(role.name == "Leader" for role in roles)


def test_directionality_is_required_only_for_relationship_types(
    service: LookupService, universe_id: str
) -> None:
    with pytest.raises(ValueError, match="require directionality"):
        service.create_value(universe_id, RELATIONSHIP_TYPE, LookupValueInput(name="Mentor"))

    with pytest.raises(ValueError, match="Only relationship"):
        service.create_value(
            universe_id,
            THEME,
            LookupValueInput(
                name="Mentorship",
                relationship_directionality=RelationshipDirectionality.DIRECTIONAL,
            ),
        )


def test_values_are_sorted_alphabetically(service: LookupService, universe_id: str) -> None:
    values = service.list_values(universe_id, MEMBERSHIP_ROLE)

    assert [value.name for value in values] == ["Founder", "Leader", "Member"]


def test_values_are_isolated_by_universe(
    session_factory: sessionmaker[Session], service: LookupService, universe_id: str
) -> None:
    other_id = (
        UniverseService(session_factory).create_universe(UniverseInput(name="Other universe")).id
    )
    service.ensure_defaults(other_id)
    service.create_value(universe_id, THEME, LookupValueInput(name="Identity"))

    assert service.list_values(other_id, THEME) == []


def test_table_frame_can_create_a_new_lookup_value(
    service: LookupService, universe_id: str
) -> None:
    _save_frame(
        service,
        universe_id,
        THEME,
        pd.DataFrame(
            [
                {
                    "id": "",
                    "name": "Identity",
                    "description": "Questions of self.",
                    "active": True,
                }
            ]
        ),
    )

    values = service.list_values(universe_id, THEME)
    assert [(value.name, value.description) for value in values] == [
        ("Identity", "Questions of self.")
    ]

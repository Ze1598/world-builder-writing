"""Tests for current character relationships."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.lookups import RELATIONSHIP_TYPE
from world_builder.domain.models import (
    ArtworkDetailsInput,
    CharacterInput,
    CharacterRelationshipInput,
    CharacterView,
    LookupValueView,
    UniverseInput,
)
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.lookups import LookupService
from world_builder.domain.services.relationships import CharacterRelationshipService
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.models import RelationshipDirectionality
from world_builder.storage.artwork import ArtworkStorage

type Services = tuple[
    UniverseService,
    LookupService,
    CharacterService,
    CharacterRelationshipService,
]


def png_file(color: str) -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color=color).save(payload, format="PNG")
    payload.seek(0)
    return payload


def create_character(
    service: CharacterService,
    *,
    name: str,
    universe_id: str | None,
    color: str,
) -> CharacterView:
    return service.create_character(
        CharacterInput(name=name, summary=f"{name} summary.", universe_id=universe_id),
        ArtworkDetailsInput(
            title=f"{name} portrait",
            description=f"Portrait of {name}.",
            original_filename=f"{name.casefold()}.png",
        ),
        png_file(color),
    )


@pytest.fixture
def services(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> Services:
    return (
        UniverseService(session_factory),
        LookupService(session_factory),
        CharacterService(session_factory, ArtworkStorage(tmp_path / "artwork")),
        CharacterRelationshipService(session_factory),
    )


def relationship_type(
    lookups: LookupService,
    universe_id: str,
    *,
    directionality: RelationshipDirectionality,
) -> LookupValueView:
    lookups.ensure_defaults(universe_id)
    return next(
        value
        for value in lookups.list_values(universe_id, RELATIONSHIP_TYPE)
        if value.relationship_directionality is directionality
    )


def test_symmetric_relationship_is_unique_for_unordered_pair(
    services: Services,
) -> None:
    universes, lookups, characters, relationships = services
    universe = universes.create_universe(UniverseInput(name="World"))
    mara = create_character(characters, name="Mara", universe_id=universe.id, color="blue")
    elias = create_character(characters, name="Elias", universe_id=universe.id, color="red")
    relationship_kind = relationship_type(
        lookups,
        universe.id,
        directionality=RelationshipDirectionality.SYMMETRIC,
    )

    created = relationships.create_relationship(
        CharacterRelationshipInput(
            first_character_id=mara.id,
            second_character_id=elias.id,
            relationship_type_id=relationship_kind.id,
            source_character_id=mara.id,
            description="They trust each other.",
        )
    )

    assert created.source_character_id is None
    assert relationships.list_for_character(mara.id) == [created]
    assert relationships.list_for_character(elias.id) == [created]
    with pytest.raises(ValueError, match="already exists"):
        relationships.create_relationship(
            CharacterRelationshipInput(
                first_character_id=elias.id,
                second_character_id=mara.id,
                relationship_type_id=relationship_kind.id,
            )
        )


def test_directional_relationship_update_overwrites_current_state(
    services: Services,
) -> None:
    universes, lookups, characters, relationships = services
    universe = universes.create_universe(UniverseInput(name="World"))
    mara = create_character(characters, name="Mara", universe_id=universe.id, color="blue")
    elias = create_character(characters, name="Elias", universe_id=universe.id, color="red")
    relationship_kind = relationship_type(
        lookups,
        universe.id,
        directionality=RelationshipDirectionality.DIRECTIONAL,
    )
    created = relationships.create_relationship(
        CharacterRelationshipInput(
            first_character_id=mara.id,
            second_character_id=elias.id,
            relationship_type_id=relationship_kind.id,
            source_character_id=mara.id,
            description="Before.",
        )
    )

    updated = relationships.update_relationship(
        created.id,
        CharacterRelationshipInput(
            first_character_id=mara.id,
            second_character_id=elias.id,
            relationship_type_id=relationship_kind.id,
            source_character_id=elias.id,
            description="After.",
        ),
    )

    assert updated.id == created.id
    assert updated.source_character_id == elias.id
    assert updated.description == "After."
    assert len(relationships.list_for_character(mara.id)) == 1


def test_relationships_reject_self_unassigned_and_cross_universe_edges(
    services: Services,
) -> None:
    universes, lookups, characters, relationships = services
    first_universe = universes.create_universe(UniverseInput(name="First"))
    second_universe = universes.create_universe(UniverseInput(name="Second"))
    mara = create_character(characters, name="Mara", universe_id=first_universe.id, color="blue")
    elias = create_character(characters, name="Elias", universe_id=second_universe.id, color="red")
    unknown = create_character(characters, name="Unknown", universe_id=None, color="green")
    relationship_kind = relationship_type(
        lookups,
        first_universe.id,
        directionality=RelationshipDirectionality.SYMMETRIC,
    )

    with pytest.raises(ValueError, match="themselves"):
        relationships.create_relationship(
            CharacterRelationshipInput(
                first_character_id=mara.id,
                second_character_id=mara.id,
                relationship_type_id=relationship_kind.id,
            )
        )
    with pytest.raises(ValueError, match="two characters in a universe"):
        relationships.create_relationship(
            CharacterRelationshipInput(
                first_character_id=mara.id,
                second_character_id=unknown.id,
                relationship_type_id=relationship_kind.id,
            )
        )
    with pytest.raises(ValueError, match="cross universe"):
        relationships.create_relationship(
            CharacterRelationshipInput(
                first_character_id=mara.id,
                second_character_id=elias.id,
                relationship_type_id=relationship_kind.id,
            )
        )


def test_character_move_reports_and_removes_relationships(
    services: Services,
) -> None:
    universes, lookups, characters, relationships = services
    source = universes.create_universe(UniverseInput(name="Source"))
    target = universes.create_universe(UniverseInput(name="Target"))
    mara = create_character(characters, name="Mara", universe_id=source.id, color="blue")
    elias = create_character(characters, name="Elias", universe_id=source.id, color="red")
    relationship_kind = relationship_type(
        lookups,
        source.id,
        directionality=RelationshipDirectionality.SYMMETRIC,
    )
    relationships.create_relationship(
        CharacterRelationshipInput(
            first_character_id=mara.id,
            second_character_id=elias.id,
            relationship_type_id=relationship_kind.id,
        )
    )

    preflight = characters.preflight_move(mara.id, target.id)
    characters.move_character(mara.id, target.id, confirmed=True)

    assert preflight.relationship_count == 1
    assert relationships.list_for_character(elias.id) == []

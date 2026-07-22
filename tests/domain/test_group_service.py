"""Tests for universe-isolated character groups and memberships."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import (
    ArtworkDetailsInput,
    CharacterGroupInput,
    CharacterInput,
    UniverseInput,
)
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.universes import UniverseService
from world_builder.storage.artwork import ArtworkStorage


def png_file(color: str = "blue") -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color=color).save(payload, format="PNG")
    payload.seek(0)
    return payload


def artwork_details(filename: str = "group.png") -> ArtworkDetailsInput:
    return ArtworkDetailsInput(
        title="Group portrait",
        description="The group together.",
        original_filename=filename,
    )


@pytest.fixture
def services(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> tuple[CharacterGroupService, CharacterService]:
    storage = ArtworkStorage(tmp_path / "artwork")
    return (
        CharacterGroupService(session_factory, storage),
        CharacterService(session_factory, storage),
    )


def test_group_can_be_created_without_artwork(
    services: tuple[CharacterGroupService, CharacterService],
    session_factory: sessionmaker[Session],
) -> None:
    group_service, _ = services
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))

    group = group_service.create_group(
        CharacterGroupInput(
            universe_id=universe.id,
            name="Wayfarers",
            description="Travelers.",
        )
    )

    assert group.universe_id == universe.id
    assert group_service.list_artworks(group.id) == []
    assert [item.id for item in group_service.list_for_universe(universe.id)] == [group.id]


def test_optional_initial_and_later_artwork_use_flat_group_folder(
    services: tuple[CharacterGroupService, CharacterService],
    session_factory: sessionmaker[Session],
) -> None:
    group_service, _ = services
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    group = group_service.create_group(
        CharacterGroupInput(universe_id=universe.id, name="Wayfarers"),
        artwork_details(),
        png_file(),
    )
    group_service.add_artwork(
        group.id,
        artwork_details("second.png"),
        png_file("green"),
    )

    artworks = group_service.list_artworks(group.id)

    assert len(artworks) == 2
    assert all(artwork.owner_id == group.id for artwork in artworks)
    assert all(
        artwork.relative_path.startswith(f"universes/{universe.id}/groups/") for artwork in artworks
    )
    assert all(f"/{group.id}/" not in artwork.relative_path for artwork in artworks)


def test_membership_description_can_be_added_updated_and_removed(
    services: tuple[CharacterGroupService, CharacterService],
    session_factory: sessionmaker[Session],
) -> None:
    group_service, character_service = services
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    group = group_service.create_group(
        CharacterGroupInput(universe_id=universe.id, name="Wayfarers")
    )
    character = character_service.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork_details("mara.png"),
        png_file(),
    )

    membership = group_service.add_membership(
        group.id,
        character.id,
        "  Founding member.  ",
    )
    group_service.update_membership(membership.id, "Leads the scouts.")
    updated = group_service.list_memberships(group.id)[0]
    group_service.remove_membership(membership.id)

    assert membership.description == "Founding member."
    assert updated.description == "Leads the scouts."
    assert updated.character_name == "Mara"
    assert group_service.list_memberships(group.id) == []
    assert character_service.get_character(character.id) is not None
    assert group_service.get_group(group.id) is not None


@pytest.mark.parametrize("character_location", ["unassigned", "foreign"])
def test_membership_rejects_character_outside_group_universe(
    services: tuple[CharacterGroupService, CharacterService],
    session_factory: sessionmaker[Session],
    character_location: str,
) -> None:
    group_service, character_service = services
    universe_service = UniverseService(session_factory)
    group_universe = universe_service.create_universe(UniverseInput(name="Group world"))
    foreign_universe = universe_service.create_universe(UniverseInput(name="Foreign world"))
    group = group_service.create_group(
        CharacterGroupInput(universe_id=group_universe.id, name="Wayfarers")
    )
    character = character_service.create_character(
        CharacterInput(
            name="Mara",
            summary="Summary.",
            universe_id=(foreign_universe.id if character_location == "foreign" else None),
        ),
        artwork_details("mara.png"),
        png_file(),
    )

    with pytest.raises(ValueError, match="only include"):
        group_service.add_membership(group.id, character.id)


def test_character_move_preflight_counts_and_removes_membership(
    services: tuple[CharacterGroupService, CharacterService],
    session_factory: sessionmaker[Session],
) -> None:
    group_service, character_service = services
    universe_service = UniverseService(session_factory)
    source = universe_service.create_universe(UniverseInput(name="Source"))
    target = universe_service.create_universe(UniverseInput(name="Target"))
    group = group_service.create_group(CharacterGroupInput(universe_id=source.id, name="Wayfarers"))
    character = character_service.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        artwork_details("mara.png"),
        png_file(),
    )
    group_service.add_membership(group.id, character.id, "Member.")

    preflight = character_service.preflight_move(character.id, target.id)
    character_service.move_character(character.id, target.id, confirmed=True)

    assert preflight.membership_count == 1
    assert preflight.detached_connection_count == 1
    assert group_service.list_memberships(group.id) == []

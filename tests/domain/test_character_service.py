"""Tests for character profiles and primary artwork workflows."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import UnsupportedArtworkError
from world_builder.domain.models import ArtworkDetailsInput, CharacterInput, UniverseInput
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.database import database_session
from world_builder.persistence.models import Artwork, Character
from world_builder.storage.artwork import ArtworkStorage


def png_file(color: str = "blue") -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color=color).save(payload, format="PNG")
    payload.seek(0)
    return payload


@pytest.fixture
def service(session_factory: sessionmaker[Session], tmp_path: Path) -> CharacterService:
    return CharacterService(session_factory, ArtworkStorage(tmp_path / "artwork"))


def details(filename: str = "portrait.png") -> ArtworkDetailsInput:
    return ArtworkDetailsInput(
        title="Portrait",
        description="Character portrait.",
        original_filename=filename,
    )


def test_create_unassigned_character_requires_and_sets_one_primary_artwork(
    service: CharacterService,
) -> None:
    character = service.create_character(
        CharacterInput(name="Mara", summary="A determined traveler."),
        details(),
        png_file(),
    )

    artworks = service.list_artworks(character.id)
    assert character.universe_id is None
    assert character.is_active is True
    assert len(artworks) == 1
    assert artworks[0].is_primary is True
    assert artworks[0].relative_path.startswith("unassigned/characters/")


def test_assigned_and_unassigned_lists_are_separate_and_sorted(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    assigned = service.create_character(
        CharacterInput(name="Zara", summary="Assigned.", universe_id=universe.id),
        details("zara.png"),
        png_file(),
    )
    unassigned = service.create_character(
        CharacterInput(name="Ada", summary="Unassigned."),
        details("ada.png"),
        png_file("red"),
    )

    assert [item.id for item in service.list_for_universe(universe.id)] == [assigned.id]
    assert [item.id for item in service.list_unassigned()] == [unassigned.id]


def test_invalid_initial_artwork_rolls_back_character_and_file(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    with pytest.raises(UnsupportedArtworkError, match="valid image"):
        service.create_character(
            CharacterInput(name="Mara", summary="Will roll back."),
            details(),
            BytesIO(b"not an image"),
        )

    with database_session(session_factory) as session:
        assert session.scalar(select(func.count(Character.id))) == 0
    assert service.storage.orphan_files([]) == set()


def test_add_artwork_and_change_primary_preserves_exactly_one(
    service: CharacterService,
) -> None:
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary."), details(), png_file()
    )
    second = service.add_artwork(
        character.id,
        ArtworkDetailsInput(
            title="Later portrait",
            description="Updated design.",
            original_filename="later.png",
        ),
        png_file("green"),
    )

    service.set_primary_artwork(character.id, second.id)
    artworks = service.list_artworks(character.id)

    assert sum(artwork.is_primary for artwork in artworks) == 1
    assert next(artwork.id for artwork in artworks if artwork.is_primary) == second.id


def test_edit_disable_and_reenable_preserve_character_data(
    service: CharacterService,
) -> None:
    character = service.create_character(
        CharacterInput(name="Mara", summary="Before."), details(), png_file()
    )

    updated = service.update_character(
        character.id,
        CharacterInput(name="Mara Vale", summary="After."),
    )
    disabled = service.set_active(character.id, is_active=False)
    reenabled = service.set_active(character.id, is_active=True)

    assert (updated.name, updated.summary) == ("Mara Vale", "After.")
    assert disabled.is_active is False
    assert reenabled.is_active is True
    assert len(service.list_artworks(character.id)) == 1


def test_unique_index_rejects_two_primary_artworks(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary."), details(), png_file()
    )
    second = service.add_artwork(
        character.id,
        ArtworkDetailsInput(
            title="Second",
            description="Second image.",
            original_filename="second.png",
        ),
        png_file("yellow"),
    )

    with pytest.raises(IntegrityError), database_session(session_factory) as session:
        record = session.get(Artwork, second.id)
        assert record is not None
        record.is_primary = True

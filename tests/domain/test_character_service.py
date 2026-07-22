"""Tests for character profiles and primary artwork workflows."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import CharacterMoveError, UnsupportedArtworkError
from world_builder.domain.models import ArtworkDetailsInput, CharacterInput, UniverseInput
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.database import database_session
from world_builder.persistence.models import Artwork, Character
from world_builder.persistence.repositories.characters import CharacterRepository
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


def test_assign_unassigned_character_moves_all_artwork(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary."), details(), png_file()
    )
    service.add_artwork(
        character.id,
        ArtworkDetailsInput(
            title="Second",
            description="Second image.",
            original_filename="second.png",
        ),
        png_file("green"),
    )
    original_paths = [artwork.relative_path for artwork in service.list_artworks(character.id)]

    preflight = service.preflight_move(character.id, universe.id)
    result = service.move_character(character.id, universe.id)
    moved_artworks = service.list_artworks(character.id)

    assert preflight.requires_confirmation is False
    assert preflight.artwork_count == 2
    assert preflight.detached_connection_count == 0
    assert result.character.universe_id == universe.id
    assert result.character.is_active is True
    assert result.cleanup_warning is None
    assert all(artwork.universe_id == universe.id for artwork in moved_artworks)
    assert all(
        artwork.relative_path.startswith(f"universes/{universe.id}/characters/")
        for artwork in moved_artworks
    )
    assert sum(artwork.is_primary for artwork in moved_artworks) == 1
    assert service.storage.missing_files(original_paths) == set(original_paths)


def test_active_assigned_character_is_disabled_as_part_of_confirmed_move(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    source = UniverseService(session_factory).create_universe(UniverseInput(name="Source"))
    target = UniverseService(session_factory).create_universe(UniverseInput(name="Target"))
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        details(),
        png_file(),
    )

    preflight = service.preflight_move(character.id, target.id)
    moved = service.move_character(character.id, target.id, confirmed=True)

    assert preflight.disables_character is True
    assert moved.character.universe_id == target.id
    assert moved.character.is_active is False


def test_disabled_character_can_move_between_universe_and_unassigned(
    service: CharacterService, session_factory: sessionmaker[Session]
) -> None:
    source = UniverseService(session_factory).create_universe(UniverseInput(name="Source"))
    target = UniverseService(session_factory).create_universe(UniverseInput(name="Target"))
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        details(),
        png_file(),
    )
    service.set_active(character.id, is_active=False)

    preflight = service.preflight_move(character.id, target.id)
    with pytest.raises(CharacterMoveError, match="Confirm"):
        service.move_character(character.id, target.id)
    moved = service.move_character(character.id, target.id, confirmed=True)
    unassigned = service.move_character(character.id, None, confirmed=True)

    assert preflight.requires_confirmation is True
    assert moved.character.universe_id == target.id
    assert moved.character.is_active is False
    assert unassigned.character.universe_id is None
    assert unassigned.character.is_active is False
    assert service.list_artworks(character.id)[0].relative_path.startswith("unassigned/characters/")


def test_database_failure_removes_staged_files_and_keeps_sources(
    service: CharacterService,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary."), details(), png_file()
    )
    original = service.list_artworks(character.id)[0]

    def fail_move(
        _repository: CharacterRepository,
        _record: Character,
        _universe_id: str | None,
    ) -> None:
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(CharacterRepository, "move", fail_move)

    with pytest.raises(RuntimeError, match="injected database failure"):
        service.move_character(character.id, universe.id)

    unchanged = service.get_character(character.id)
    assert unchanged is not None
    assert unchanged.universe_id is None
    assert service.storage.read_bytes(original.relative_path)
    assert service.storage.orphan_files([original.relative_path]) == set()


def test_filesystem_failure_removes_staged_files_and_keeps_database(
    service: CharacterService,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    character = service.create_character(
        CharacterInput(name="Mara", summary="Summary."), details(), png_file()
    )
    service.add_artwork(
        character.id,
        ArtworkDetailsInput(
            title="Second",
            description="Second image.",
            original_filename="second.png",
        ),
        png_file("green"),
    )
    originals = service.list_artworks(character.id)
    original_paths = [artwork.relative_path for artwork in originals]
    copy_file = service.storage.copy
    copy_count = 0

    def fail_second_copy(source: str, destination: str) -> None:
        nonlocal copy_count
        copy_count += 1
        if copy_count == 2:
            raise OSError("injected filesystem failure")
        copy_file(source, destination)

    monkeypatch.setattr(service.storage, "copy", fail_second_copy)

    with pytest.raises(OSError, match="injected filesystem failure"):
        service.move_character(character.id, universe.id)

    unchanged = service.get_character(character.id)
    assert unchanged is not None
    assert unchanged.universe_id is None
    assert service.storage.missing_files(original_paths) == set()
    assert service.storage.orphan_files(original_paths) == set()

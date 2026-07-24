"""Tests for reusable artwork links, ownership transfer, and deletion."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import CharacterMoveError, RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkEntityKind,
    ChapterInput,
    CharacterGroupInput,
    CharacterInput,
    StoryInput,
    UniverseInput,
)
from world_builder.domain.services.artworks import ArtworkService
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.stories import StoryService
from world_builder.domain.services.universes import UniverseService
from world_builder.persistence.models import ArtworkOwnerKind
from world_builder.storage.artwork import ArtworkStorage


def png_file(color: str = "purple") -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (8, 8), color=color).save(payload, format="PNG")
    payload.seek(0)
    return payload


def artwork_details(title: str) -> ArtworkDetailsInput:
    return ArtworkDetailsInput(
        title=title,
        description=f"{title} description.",
        original_filename=f"{title.casefold()}.png",
    )


def test_artwork_can_link_to_every_supported_entity_without_file_duplication(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    groups = CharacterGroupService(session_factory, storage)
    chapters = ChapterService(session_factory)
    stories = StoryService(session_factory, storage)
    artworks = ArtworkService(session_factory, storage)
    owner = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork_details("Portrait"),
        png_file(),
    )
    linked_character = characters.create_character(
        CharacterInput(name="Elias", summary="Summary.", universe_id=universe.id),
        artwork_details("Elias"),
        png_file("blue"),
    )
    shared = characters.add_artwork(
        owner.id,
        artwork_details("Shared"),
        png_file("green"),
    )
    primary = next(item for item in characters.list_artworks(owner.id) if item.is_primary)
    group = groups.create_group(CharacterGroupInput(universe_id=universe.id, name="Guild"))
    chapter = chapters.create_chapter(ChapterInput(universe_id=universe.id, title="Beginnings"))
    story = stories.create_story(
        StoryInput(universe_id=universe.id, chapter_id=chapter.id, title="Arrival")
    )
    original_path = storage.absolute_path(shared.relative_path)

    targets = (
        (ArtworkEntityKind.CHARACTER, linked_character.id),
        (ArtworkEntityKind.GROUP, group.id),
        (ArtworkEntityKind.STORY, story.id),
    )
    for kind, entity_id in targets:
        artworks.add_association(shared.id, kind, entity_id)
    artworks.add_associations(
        (primary.id, shared.id),
        ArtworkEntityKind.CHAPTER,
        chapter.id,
    )

    detail = artworks.get_detail(shared.id)

    assert {usage.entity_kind for usage in detail.usages} == {
        ArtworkEntityKind.CHARACTER,
        ArtworkEntityKind.GROUP,
        ArtworkEntityKind.CHAPTER,
        ArtworkEntityKind.STORY,
    }
    assert shared.id in {
        item.id for item in artworks.list_gallery_for_character(linked_character.id)
    }
    assert shared.id in {item.id for item in artworks.list_gallery_for_group(group.id)}
    assert {item.id for item in artworks.list_gallery_for_chapter(chapter.id)} == {
        primary.id,
        shared.id,
    }
    assert shared.id in {item.id for item in artworks.list_gallery_for_story(story.id)}
    assert storage.absolute_path(shared.relative_path) == original_path
    assert len(list(storage.root.rglob(f"{shared.id}.*"))) == 1


def test_owned_artwork_rejects_foreign_link_and_transfer_detaches_source_links(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe_service = UniverseService(session_factory)
    source = universe_service.create_universe(UniverseInput(name="Source"))
    target = universe_service.create_universe(UniverseInput(name="Target"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    groups = CharacterGroupService(session_factory, storage)
    chapters = ChapterService(session_factory)
    artworks = ArtworkService(session_factory, storage)
    owner = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        artwork_details("Portrait"),
        png_file(),
    )
    transferable = characters.add_artwork(
        owner.id,
        artwork_details("Transferable"),
        png_file("green"),
    )
    source_group = groups.create_group(
        CharacterGroupInput(universe_id=source.id, name="Source group")
    )
    source_chapter = chapters.create_chapter(
        ChapterInput(universe_id=source.id, title="Source chapter")
    )
    target_group = groups.create_group(
        CharacterGroupInput(universe_id=target.id, name="Target group")
    )
    artworks.add_association(transferable.id, ArtworkEntityKind.GROUP, source_group.id)
    artworks.add_association(transferable.id, ArtworkEntityKind.CHAPTER, source_chapter.id)

    with pytest.raises(ValueError, match="only link"):
        artworks.add_association(transferable.id, ArtworkEntityKind.GROUP, target_group.id)

    preflight = artworks.preflight_move(
        transferable.id,
        ArtworkOwnerKind.GROUP,
        target_group.id,
    )
    with pytest.raises(CharacterMoveError, match="Confirm"):
        artworks.move_owner(
            transferable.id,
            ArtworkOwnerKind.GROUP,
            target_group.id,
        )
    result = artworks.move_owner(
        transferable.id,
        ArtworkOwnerKind.GROUP,
        target_group.id,
        confirmed=True,
    )

    assert preflight.incompatible_usage_count == 2
    assert result.artwork is not None
    assert result.artwork.owner_kind is ArtworkOwnerKind.GROUP
    assert result.artwork.owner_id == target_group.id
    assert result.artwork.universe_id == target.id
    assert artworks.get_detail(transferable.id).usages == ()
    assert storage.absolute_path(result.artwork.relative_path).is_file()


def test_returning_artwork_to_unassigned_preserves_links_and_safe_delete_removes_all(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    chapters = ChapterService(session_factory)
    artworks = ArtworkService(session_factory, storage)
    owner = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork_details("Portrait"),
        png_file(),
    )
    movable = characters.add_artwork(
        owner.id,
        artwork_details("Movable"),
        png_file("green"),
    )
    chapter = chapters.create_chapter(ChapterInput(universe_id=universe.id, title="Arrival"))
    artworks.add_association(movable.id, ArtworkEntityKind.CHAPTER, chapter.id)

    moved = artworks.move_owner(movable.id, None, None)
    moved_path = moved.artwork.relative_path if moved.artwork is not None else ""

    assert moved.artwork is not None
    assert moved.artwork.owner_kind is None
    assert moved.artwork.universe_id is None
    assert len(artworks.get_detail(movable.id).usages) == 1
    assert storage.absolute_path(moved_path).is_file()

    artworks.delete_artwork(movable.id)

    with pytest.raises(RecordNotFoundError):
        artworks.get_detail(movable.id)
    assert not storage.absolute_path(moved_path).exists()


def test_primary_character_artwork_cannot_move_or_be_deleted(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    groups = CharacterGroupService(session_factory, storage)
    artworks = ArtworkService(session_factory, storage)
    character = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork_details("Portrait"),
        png_file(),
    )
    primary = characters.list_artworks(character.id)[0]
    group = groups.create_group(CharacterGroupInput(universe_id=universe.id, name="Guild"))

    with pytest.raises(ValueError, match="another primary"):
        artworks.move_owner(primary.id, ArtworkOwnerKind.GROUP, group.id)
    with pytest.raises(ValueError, match="another primary"):
        artworks.delete_artwork(primary.id)


def test_character_move_detaches_associations_from_every_owned_artwork(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe_service = UniverseService(session_factory)
    source = universe_service.create_universe(UniverseInput(name="Source"))
    target = universe_service.create_universe(UniverseInput(name="Target"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    chapters = ChapterService(session_factory)
    artworks = ArtworkService(session_factory, storage)
    character = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        artwork_details("Portrait"),
        png_file(),
    )
    second = characters.add_artwork(
        character.id,
        artwork_details("Scene"),
        png_file("green"),
    )
    primary = next(item for item in characters.list_artworks(character.id) if item.is_primary)
    chapter = chapters.create_chapter(ChapterInput(universe_id=source.id, title="Before the move"))
    artworks.add_association(primary.id, ArtworkEntityKind.CHAPTER, chapter.id)
    artworks.add_association(second.id, ArtworkEntityKind.CHAPTER, chapter.id)

    preflight = characters.preflight_move(character.id, target.id)
    characters.move_character(character.id, target.id, confirmed=True)

    assert preflight.artwork_count == 2
    assert preflight.artwork_association_count == 2
    assert artworks.get_detail(primary.id).usages == ()
    assert artworks.get_detail(second.id).usages == ()
    assert all(item.universe_id == target.id for item in characters.list_artworks(character.id))

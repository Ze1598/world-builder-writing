"""Tests for story content, links, artwork, and reverse lookups."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import (
    ArtworkDetailsInput,
    ChapterInput,
    CharacterGroupInput,
    CharacterInput,
    StoryInput,
    UniverseInput,
)
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.stories import StoryService
from world_builder.domain.services.universes import UniverseService
from world_builder.storage.artwork import ArtworkStorage


def png_file() -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (8, 8), color="purple").save(payload, format="PNG")
    payload.seek(0)
    return payload


def artwork(title: str = "Portrait") -> ArtworkDetailsInput:
    return ArtworkDetailsInput(
        title=title, description=f"{title} description.", original_filename="image.png"
    )


def setup_content(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> tuple[
    StoryService,
    ChapterService,
    CharacterService,
    str,
    str,
    str,
    str,
    str,
]:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    groups = CharacterGroupService(session_factory, storage)
    character = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork(),
        png_file(),
    )
    group = groups.create_group(CharacterGroupInput(universe_id=universe.id, name="Guild"))
    chapters = ChapterService(session_factory)
    chapter = chapters.create_chapter(ChapterInput(universe_id=universe.id, title="Beginnings"))
    owned_artwork = characters.list_artworks(character.id)[0]
    return (
        StoryService(session_factory, storage),
        chapters,
        characters,
        universe.id,
        chapter.id,
        character.id,
        group.id,
        owned_artwork.id,
    )


def test_placeholder_story_round_trips_long_markdown_and_reverse_links(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service, _, _, universe_id, chapter_id, character_id, group_id, artwork_id = setup_content(
        session_factory, tmp_path
    )
    placeholder = service.create_story(
        StoryInput(
            universe_id=universe_id,
            chapter_id=chapter_id,
            title="Placeholder",
            character_ids=(character_id,),
            group_ids=(group_id,),
            artwork_ids=(artwork_id,),
        )
    )
    content = "# Story\n\n" + ("Long content. " * 20_000)
    updated = service.update_story(
        placeholder.id,
        StoryInput(
            universe_id=universe_id,
            chapter_id=chapter_id,
            title="Finished",
            content=content,
            character_ids=(character_id,),
            group_ids=(group_id,),
            artwork_ids=(artwork_id,),
        ),
    )

    assert placeholder.content == ""
    assert updated.content == content
    assert service.list_for_character(character_id)[0].id == placeholder.id
    assert service.list_for_group(group_id)[0].id == placeholder.id
    assert service.list_for_chapter(chapter_id)[0].id == placeholder.id


def test_story_uploads_global_unassigned_artwork_and_delete_preserves_it(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service, _, _, universe_id, chapter_id, *_ = setup_content(session_factory, tmp_path)
    story = service.create_story(
        StoryInput(universe_id=universe_id, chapter_id=chapter_id, title="Illustrated"),
        artwork("Scene"),
        png_file(),
    )
    uploaded = next(
        item
        for item in service.list_available_artworks(universe_id)
        if item.id in story.artwork_ids
    )
    path = service.storage.absolute_path(uploaded.relative_path)

    service.remove_story(story.id)

    assert uploaded.owner_kind is None
    assert uploaded.owner_id is None
    assert uploaded.universe_id is None
    assert uploaded.relative_path.startswith("unassigned/artwork/")
    assert path.is_file()
    assert any(item.id == uploaded.id for item in service.list_available_artworks(universe_id))


def test_story_rejects_foreign_links_and_blocks_chapter_removal(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service, chapters, _, universe_id, chapter_id, *_ = setup_content(session_factory, tmp_path)
    foreign = UniverseService(session_factory).create_universe(UniverseInput(name="Foreign"))
    foreign_character = CharacterService(session_factory, service.storage).create_character(
        CharacterInput(name="Elias", summary="Summary.", universe_id=foreign.id),
        artwork(),
        png_file(),
    )

    with pytest.raises(ValueError, match="characters"):
        service.create_story(
            StoryInput(
                universe_id=universe_id,
                chapter_id=chapter_id,
                title="Invalid",
                character_ids=(foreign_character.id,),
            )
        )

    story = service.create_story(
        StoryInput(universe_id=universe_id, chapter_id=chapter_id, title="Story")
    )
    with pytest.raises(ValueError, match="every story"):
        chapters.remove_chapter(chapter_id)
    service.remove_story(story.id)
    chapters.remove_chapter(chapter_id)
    assert chapters.list_for_universe(universe_id) == []

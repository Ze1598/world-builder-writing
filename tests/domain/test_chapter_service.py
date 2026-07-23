"""Tests for chapter links and relative chronology."""

from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import (
    ArtworkDetailsInput,
    ChapterInput,
    CharacterGroupInput,
    CharacterInput,
    UniverseInput,
)
from world_builder.domain.services.chapters import ChapterService
from world_builder.domain.services.characters import CharacterService
from world_builder.domain.services.groups import CharacterGroupService
from world_builder.domain.services.universes import UniverseService
from world_builder.storage.artwork import ArtworkStorage


def png_file() -> BytesIO:
    payload = BytesIO()
    Image.new("RGB", (4, 4), color="blue").save(payload, format="PNG")
    payload.seek(0)
    return payload


def artwork() -> ArtworkDetailsInput:
    return ArtworkDetailsInput(
        title="Portrait", description="Portrait.", original_filename="portrait.png"
    )


def test_chapters_append_and_concurrent_chapter_moves_independently(
    session_factory: sessionmaker[Session],
) -> None:
    universe = UniverseService(session_factory).create_universe(UniverseInput(name="World"))
    service = ChapterService(session_factory)
    chapters = [
        service.create_chapter(ChapterInput(universe_id=universe.id, title=title))
        for title in ["A", "B", "C", "D"]
    ]
    service.mark_concurrent(chapters[2].id, chapters[1].id)

    concurrent = service.list_for_universe(universe.id)
    service.move_earlier(chapters[2].id)
    separated = service.list_for_universe(universe.id)

    assert [(item.title, item.sequence_position) for item in concurrent] == [
        ("A", 1),
        ("B", 2),
        ("C", 2),
        ("D", 3),
    ]
    assert [(item.title, item.sequence_position) for item in separated] == [
        ("A", 1),
        ("C", 2),
        ("B", 3),
        ("D", 4),
    ]


def test_chapter_links_are_isolated_and_removed_with_chapter(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe_service = UniverseService(session_factory)
    universe = universe_service.create_universe(UniverseInput(name="World"))
    foreign = universe_service.create_universe(UniverseInput(name="Foreign"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    groups = CharacterGroupService(session_factory, storage)
    character = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=universe.id),
        artwork(),
        png_file(),
    )
    foreign_character = characters.create_character(
        CharacterInput(name="Elias", summary="Summary.", universe_id=foreign.id),
        artwork(),
        png_file(),
    )
    group = groups.create_group(CharacterGroupInput(universe_id=universe.id, name="Guild"))
    service = ChapterService(session_factory)
    chapter = service.create_chapter(
        ChapterInput(
            universe_id=universe.id,
            title="Arrival",
            character_ids=(character.id,),
            group_ids=(group.id,),
        )
    )

    try:
        service.create_chapter(
            ChapterInput(
                universe_id=universe.id,
                title="Invalid",
                character_ids=(foreign_character.id,),
            )
        )
    except ValueError as error:
        assert "characters" in str(error)
    else:
        raise AssertionError("Foreign-universe character link was accepted")

    assert chapter.character_names == ("Mara",)
    assert chapter.group_names == ("Guild",)
    service.remove_chapter(chapter.id)
    assert service.list_for_universe(universe.id) == []


def test_character_move_preflight_counts_and_removes_chapter_link(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    universe_service = UniverseService(session_factory)
    source = universe_service.create_universe(UniverseInput(name="Source"))
    target = universe_service.create_universe(UniverseInput(name="Target"))
    storage = ArtworkStorage(tmp_path / "artwork")
    characters = CharacterService(session_factory, storage)
    character = characters.create_character(
        CharacterInput(name="Mara", summary="Summary.", universe_id=source.id),
        artwork(),
        png_file(),
    )
    chapters = ChapterService(session_factory)
    chapter = chapters.create_chapter(
        ChapterInput(universe_id=source.id, title="Arrival", character_ids=(character.id,))
    )

    preflight = characters.preflight_move(character.id, target.id)
    characters.move_character(character.id, target.id, confirmed=True)

    assert preflight.chapter_link_count == 1
    assert chapters.list_for_universe(source.id)[0].id == chapter.id
    assert chapters.list_for_universe(source.id)[0].character_ids == ()

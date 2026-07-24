"""Tests for milestone idea capture and entity associations."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import MilestoneInput
from world_builder.domain.services.milestones import MilestoneService
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    Chapter,
    Character,
    CharacterGroup,
    Story,
    Universe,
)


def seed_universe_content(
    session_factory: sessionmaker[Session],
    *,
    universe_name: str,
) -> tuple[Universe, Character, CharacterGroup, Chapter, Story]:
    with database_session(session_factory) as session:
        universe = Universe(id=str(uuid4()), name=universe_name, description="")
        character = Character(
            id=str(uuid4()),
            universe=universe,
            name=f"{universe_name} character",
            summary="Summary.",
            is_active=True,
        )
        group = CharacterGroup(
            id=str(uuid4()),
            universe=universe,
            name=f"{universe_name} group",
            description="",
        )
        chapter = Chapter(
            id=str(uuid4()),
            universe=universe,
            title=f"{universe_name} chapter",
            description="",
            sequence_position=0,
        )
        story = Story(
            id=str(uuid4()),
            universe=universe,
            chapter=chapter,
            title=f"{universe_name} story",
            content="",
        )
        session.add(universe)
        session.flush()
    return universe, character, group, chapter, story


def test_capture_unlinked_milestone_and_delete_it(
    session_factory: sessionmaker[Session],
) -> None:
    universe, *_ = seed_universe_content(
        session_factory,
        universe_name="World",
    )
    service = MilestoneService(session_factory)

    created = service.create_milestone(
        MilestoneInput(
            universe_id=universe.id,
            title="Possible betrayal",
            content="Decide who discovers it.",
        )
    )

    assert created.is_unlinked is True
    assert service.list_for_universe(universe.id) == [created]
    service.remove_milestone(created.id)
    assert service.list_for_universe(universe.id) == []


def test_milestone_links_every_supported_entity_and_overwrites_links(
    session_factory: sessionmaker[Session],
) -> None:
    universe, character, group, chapter, story = seed_universe_content(
        session_factory,
        universe_name="World",
    )
    service = MilestoneService(session_factory)
    created = service.create_milestone(
        MilestoneInput(
            universe_id=universe.id,
            title="Confrontation",
            content="Everyone meets.",
            character_ids=(character.id,),
            group_ids=(group.id,),
            chapter_ids=(chapter.id,),
            story_ids=(story.id,),
        )
    )

    assert service.list_for_character(character.id) == [created]
    assert service.list_for_group(group.id) == [created]
    assert service.list_for_chapter(chapter.id) == [created]
    assert service.list_for_story(story.id) == [created]

    updated = service.update_milestone(
        created.id,
        MilestoneInput(
            universe_id=universe.id,
            title="Later confrontation",
            content="Only the character remains linked.",
            character_ids=(character.id,),
        ),
    )

    assert updated.id == created.id
    assert updated.group_ids == ()
    assert updated.chapter_ids == ()
    assert updated.story_ids == ()
    assert service.list_for_group(group.id) == []


def test_milestone_rejects_foreign_universe_links(
    session_factory: sessionmaker[Session],
) -> None:
    first, *_ = seed_universe_content(session_factory, universe_name="First")
    _, foreign_character, _, _, _ = seed_universe_content(
        session_factory,
        universe_name="Second",
    )
    service = MilestoneService(session_factory)

    with pytest.raises(ValueError, match="characters must belong"):
        service.create_milestone(
            MilestoneInput(
                universe_id=first.id,
                title="Invalid idea",
                content="Crosses universes.",
                character_ids=(foreign_character.id,),
            )
        )

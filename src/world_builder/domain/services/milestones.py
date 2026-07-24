"""Universe-scoped milestone idea workflows."""

from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import RecordNotFoundError
from world_builder.domain.models import MilestoneInput, MilestoneView
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    Milestone,
    MilestoneChapter,
    MilestoneCharacter,
    MilestoneGroup,
    MilestoneStory,
)
from world_builder.persistence.repositories.chapters import ChapterRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.groups import CharacterGroupRepository
from world_builder.persistence.repositories.milestones import MilestoneRepository
from world_builder.persistence.repositories.stories import StoryRepository
from world_builder.persistence.repositories.universes import UniverseRepository


class MilestoneService:
    """Create and retrieve planning ideas without mutating canonical content."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_milestone(self, values: MilestoneInput) -> MilestoneView:
        with database_session(self._session_factory) as session:
            self._validate(session, values)
            record = Milestone(
                id=str(uuid4()),
                universe_id=values.universe_id,
                title=values.title,
                content=values.content,
            )
            self._replace_links(record, values)
            MilestoneRepository(session).add(record)
            session.flush()
            return self._view(record)

    def update_milestone(self, milestone_id: str, values: MilestoneInput) -> MilestoneView:
        with database_session(self._session_factory) as session:
            repository = MilestoneRepository(session)
            record = self._require(repository, milestone_id)
            if record.universe_id != values.universe_id:
                raise ValueError("Milestones cannot move between universes.")
            self._validate(session, values)
            record.title = values.title
            record.content = values.content
            self._replace_links(record, values)
            session.flush()
            return self._view(record)

    def list_for_universe(self, universe_id: str) -> list[MilestoneView]:
        return self._list_linked("universe", universe_id)

    def list_for_character(self, character_id: str) -> list[MilestoneView]:
        return self._list_linked("character", character_id)

    def list_for_group(self, group_id: str) -> list[MilestoneView]:
        return self._list_linked("group", group_id)

    def list_for_chapter(self, chapter_id: str) -> list[MilestoneView]:
        return self._list_linked("chapter", chapter_id)

    def list_for_story(self, story_id: str) -> list[MilestoneView]:
        return self._list_linked("story", story_id)

    def remove_milestone(self, milestone_id: str) -> None:
        with database_session(self._session_factory) as session:
            repository = MilestoneRepository(session)
            repository.delete(self._require(repository, milestone_id))

    def _list_linked(self, kind: str, entity_id: str) -> list[MilestoneView]:
        with database_session(self._session_factory) as session:
            repository = MilestoneRepository(session)
            records = {
                "universe": repository.list_for_universe,
                "character": repository.list_for_character,
                "group": repository.list_for_group,
                "chapter": repository.list_for_chapter,
                "story": repository.list_for_story,
            }[kind](entity_id)
            return [self._view(record) for record in records]

    @staticmethod
    def _replace_links(record: Milestone, values: MilestoneInput) -> None:
        record.character_links = [
            MilestoneCharacter(character_id=entity_id)
            for entity_id in dict.fromkeys(values.character_ids)
        ]
        record.group_links = [
            MilestoneGroup(group_id=entity_id) for entity_id in dict.fromkeys(values.group_ids)
        ]
        record.chapter_links = [
            MilestoneChapter(chapter_id=entity_id)
            for entity_id in dict.fromkeys(values.chapter_ids)
        ]
        record.story_links = [
            MilestoneStory(story_id=entity_id) for entity_id in dict.fromkeys(values.story_ids)
        ]

    @staticmethod
    def _validate(session: Session, values: MilestoneInput) -> None:
        if UniverseRepository(session).get(values.universe_id) is None:
            raise RecordNotFoundError("The selected universe no longer exists.")
        validators = (
            (
                values.character_ids,
                CharacterRepository(session).get,
                "Milestone characters",
            ),
            (
                values.group_ids,
                CharacterGroupRepository(session).get,
                "Milestone groups",
            ),
            (
                values.chapter_ids,
                ChapterRepository(session).get,
                "Milestone chapters",
            ),
            (
                values.story_ids,
                StoryRepository(session).get,
                "Milestone stories",
            ),
        )
        for entity_ids, loader, label in validators:
            for entity_id in entity_ids:
                entity = loader(entity_id)
                if entity is None or entity.universe_id != values.universe_id:
                    raise ValueError(f"{label} must belong to its universe.")

    @staticmethod
    def _require(repository: MilestoneRepository, milestone_id: str) -> Milestone:
        record = repository.get(milestone_id)
        if record is None:
            raise RecordNotFoundError("The selected milestone no longer exists.")
        return record

    @staticmethod
    def _view(record: Milestone) -> MilestoneView:
        characters = sorted(
            record.character_links,
            key=lambda link: link.character.name.casefold(),
        )
        groups = sorted(
            record.group_links,
            key=lambda link: link.group.name.casefold(),
        )
        chapters = sorted(
            record.chapter_links,
            key=lambda link: (link.chapter.sequence_position, link.chapter.title.casefold()),
        )
        stories = sorted(
            record.story_links,
            key=lambda link: link.story.title.casefold(),
        )
        return MilestoneView(
            id=record.id,
            universe_id=record.universe_id,
            title=record.title,
            content=record.content,
            character_ids=tuple(link.character_id for link in characters),
            character_names=tuple(link.character.name for link in characters),
            group_ids=tuple(link.group_id for link in groups),
            group_names=tuple(link.group.name for link in groups),
            chapter_ids=tuple(link.chapter_id for link in chapters),
            chapter_titles=tuple(link.chapter.title for link in chapters),
            story_ids=tuple(link.story_id for link in stories),
            story_titles=tuple(link.story.title for link in stories),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

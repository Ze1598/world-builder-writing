"""Universe-isolated chapters and deterministic relative chronology."""

from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import RecordNotFoundError
from world_builder.domain.models import ChapterInput, ChapterView
from world_builder.persistence.database import database_session
from world_builder.persistence.models import Chapter, ChapterCharacter, ChapterGroup
from world_builder.persistence.repositories.chapters import ChapterRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.groups import CharacterGroupRepository
from world_builder.persistence.repositories.stories import StoryRepository
from world_builder.persistence.repositories.universes import UniverseRepository


class ChapterService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_chapter(self, values: ChapterInput) -> ChapterView:
        with database_session(self._session_factory) as session:
            self._validate_links(session, values)
            repository = ChapterRepository(session)
            record = Chapter(
                id=str(uuid4()),
                universe_id=values.universe_id,
                title=values.title,
                description=values.description,
                sequence_position=repository.next_position(values.universe_id),
            )
            self._replace_links(record, values)
            repository.add(record)
            session.flush()
            return self._view(record)

    def list_for_universe(self, universe_id: str) -> list[ChapterView]:
        with database_session(self._session_factory) as session:
            return [
                self._view(r) for r in ChapterRepository(session).list_for_universe(universe_id)
            ]

    def update_chapter(self, chapter_id: str, values: ChapterInput) -> ChapterView:
        with database_session(self._session_factory) as session:
            repo = ChapterRepository(session)
            record = self._require(repo, chapter_id)
            if record.universe_id != values.universe_id:
                raise ValueError("Chapters cannot move between universes.")
            self._validate_links(session, values)
            record.title, record.description = values.title, values.description
            self._replace_links(record, values)
            session.flush()
            return self._view(record)

    def move_earlier(self, chapter_id: str) -> None:
        self._move(chapter_id, -1)

    def move_later(self, chapter_id: str) -> None:
        self._move(chapter_id, 1)

    def mark_concurrent(self, chapter_id: str, target_id: str) -> None:
        with database_session(self._session_factory) as session:
            repo = ChapterRepository(session)
            record = self._require(repo, chapter_id)
            target = self._require(repo, target_id)
            if record.universe_id != target.universe_id:
                raise ValueError("Concurrent chapters must share a universe.")
            if record.id == target.id:
                raise ValueError("Select a different chapter.")
            record.sequence_position = target.sequence_position
            session.flush()
            self._normalize(repo.list_for_universe(record.universe_id))

    def remove_chapter(self, chapter_id: str) -> None:
        with database_session(self._session_factory) as session:
            repo = ChapterRepository(session)
            record = self._require(repo, chapter_id)
            if StoryRepository(session).count_for_chapter(chapter_id):
                raise ValueError("Move or remove every story in this chapter before removing it.")
            universe_id = record.universe_id
            repo.delete(record)
            session.flush()
            self._normalize(repo.list_for_universe(universe_id))

    def _move(self, chapter_id: str, direction: int) -> None:
        with database_session(self._session_factory) as session:
            repo = ChapterRepository(session)
            record = self._require(repo, chapter_id)
            chapters = repo.list_for_universe(record.universe_id)
            position = record.sequence_position
            cohort = [c for c in chapters if c.sequence_position == position]
            positions = sorted({c.sequence_position for c in chapters})
            index = positions.index(position)
            adjacent_index = index + direction
            if adjacent_index < 0 or adjacent_index >= len(positions):
                return
            if len(cohort) > 1:
                if direction < 0:
                    for chapter in chapters:
                        if chapter.sequence_position >= position and chapter.id != record.id:
                            chapter.sequence_position += 1
                    record.sequence_position = position
                else:
                    for chapter in chapters:
                        if chapter.sequence_position > position:
                            chapter.sequence_position += 1
                    record.sequence_position = position + 1
            else:
                adjacent = positions[adjacent_index]
                for chapter in chapters:
                    if chapter.sequence_position == adjacent:
                        chapter.sequence_position = position
                record.sequence_position = adjacent
            session.flush()
            self._normalize(chapters)

    @staticmethod
    def _normalize(chapters: list[Chapter]) -> None:
        positions = sorted({c.sequence_position for c in chapters})
        mapping = {position: index for index, position in enumerate(positions, start=1)}
        for chapter in chapters:
            chapter.sequence_position = mapping[chapter.sequence_position]

    @staticmethod
    def _replace_links(record: Chapter, values: ChapterInput) -> None:
        record.character_links = [
            ChapterCharacter(character_id=i) for i in dict.fromkeys(values.character_ids)
        ]
        record.group_links = [ChapterGroup(group_id=i) for i in dict.fromkeys(values.group_ids)]

    @staticmethod
    def _validate_links(session: Session, values: ChapterInput) -> None:
        if UniverseRepository(session).get(values.universe_id) is None:
            raise RecordNotFoundError("The selected universe no longer exists.")
        characters = CharacterRepository(session)
        for item_id in values.character_ids:
            character = characters.get(item_id)
            if character is None or character.universe_id != values.universe_id:
                raise ValueError("Chapter characters must belong to its universe.")
        groups = CharacterGroupRepository(session)
        for item_id in values.group_ids:
            group = groups.get(item_id)
            if group is None or group.universe_id != values.universe_id:
                raise ValueError("Chapter groups must belong to its universe.")

    @staticmethod
    def _require(repo: ChapterRepository, chapter_id: str) -> Chapter:
        record = repo.get(chapter_id)
        if record is None:
            raise RecordNotFoundError("The selected chapter no longer exists.")
        return record

    @staticmethod
    def _view(record: Chapter) -> ChapterView:
        chars = sorted(record.character_links, key=lambda x: x.character.name.casefold())
        groups = sorted(record.group_links, key=lambda x: x.group.name.casefold())
        return ChapterView(
            id=record.id,
            universe_id=record.universe_id,
            title=record.title,
            description=record.description,
            sequence_position=record.sequence_position,
            character_ids=tuple(x.character_id for x in chars),
            character_names=tuple(x.character.name for x in chars),
            group_ids=tuple(x.group_id for x in groups),
            group_names=tuple(x.group.name for x in groups),
        )

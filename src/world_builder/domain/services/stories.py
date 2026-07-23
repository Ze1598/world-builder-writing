"""Story CRUD, Markdown content, and universe-scoped associations."""

from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkInput,
    ArtworkView,
    StoryInput,
    StoryView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    Artwork,
    Story,
    StoryArtwork,
    StoryCharacter,
    StoryGroup,
)
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.persistence.repositories.chapters import ChapterRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.groups import CharacterGroupRepository
from world_builder.persistence.repositories.stories import StoryRepository
from world_builder.storage.artwork import ArtworkStorage, StoredArtworkFile


class StoryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        storage: ArtworkStorage,
    ) -> None:
        self._session_factory = session_factory
        self.storage = storage

    def create_story(
        self,
        values: StoryInput,
        artwork: ArtworkDetailsInput | None = None,
        source: BinaryIO | None = None,
    ) -> StoryView:
        if (artwork is None) != (source is None):
            raise ValueError("Artwork metadata and image must be supplied together.")
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                self._validate_links(session, values)
                record = Story(
                    id=str(uuid4()),
                    universe_id=values.universe_id,
                    chapter_id=values.chapter_id,
                    title=values.title,
                    content=values.content,
                )
                self._replace_links(record, values)
                if artwork is not None and source is not None:
                    stored_artwork, stored = self._import_unassigned(session, artwork, source)
                    record.artwork_links.append(StoryArtwork(artwork_id=stored_artwork.id))
                StoryRepository(session).add(record)
                session.flush()
                return self._view(record)
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def update_story(self, story_id: str, values: StoryInput) -> StoryView:
        with database_session(self._session_factory) as session:
            repository = StoryRepository(session)
            record = self._require(repository, story_id)
            if record.universe_id != values.universe_id:
                raise ValueError("Stories cannot move between universes.")
            self._validate_links(session, values)
            record.chapter_id = values.chapter_id
            record.title = values.title
            record.content = values.content
            self._replace_links(record, values)
            session.flush()
            return self._view(record)

    def add_unassigned_artwork(
        self,
        story_id: str,
        details: ArtworkDetailsInput,
        source: BinaryIO,
    ) -> ArtworkView:
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                story = self._require(StoryRepository(session), story_id)
                record, stored = self._import_unassigned(session, details, source)
                story.artwork_links.append(StoryArtwork(artwork_id=record.id))
                session.flush()
                return ArtworkView.model_validate(record)
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def list_for_universe(self, universe_id: str) -> list[StoryView]:
        with database_session(self._session_factory) as session:
            return [
                self._view(record)
                for record in StoryRepository(session).list_for_universe(universe_id)
            ]

    def list_for_chapter(self, chapter_id: str) -> list[StoryView]:
        return self._list_linked("chapter", chapter_id)

    def list_for_character(self, character_id: str) -> list[StoryView]:
        return self._list_linked("character", character_id)

    def list_for_group(self, group_id: str) -> list[StoryView]:
        return self._list_linked("group", group_id)

    def list_available_artworks(self, universe_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return [
                ArtworkView.model_validate(record)
                for record in ArtworkRepository(session).list_available_for_universe(universe_id)
            ]

    def remove_story(self, story_id: str) -> None:
        with database_session(self._session_factory) as session:
            repository = StoryRepository(session)
            repository.delete(self._require(repository, story_id))

    def _list_linked(self, kind: str, item_id: str) -> list[StoryView]:
        with database_session(self._session_factory) as session:
            repository = StoryRepository(session)
            records = {
                "chapter": repository.list_for_chapter,
                "character": repository.list_for_character,
                "group": repository.list_for_group,
            }[kind](item_id)
            return [self._view(record) for record in records]

    def _import_unassigned(
        self,
        session: Session,
        details: ArtworkDetailsInput,
        source: BinaryIO,
    ) -> tuple[Artwork, StoredArtworkFile]:
        artwork_id = str(uuid4())
        stored = self.storage.import_image(
            source,
            original_filename=details.original_filename,
            artwork_id=artwork_id,
            owner_kind=None,
            owner_id=None,
            universe_id=None,
        )
        record = ArtworkRepository(session).create(
            artwork_id,
            ArtworkInput(
                title=details.title,
                description=details.description,
                original_filename=details.original_filename,
            ),
            stored,
        )
        return record, stored

    @staticmethod
    def _replace_links(record: Story, values: StoryInput) -> None:
        record.character_links = [
            StoryCharacter(character_id=item_id) for item_id in dict.fromkeys(values.character_ids)
        ]
        record.group_links = [
            StoryGroup(group_id=item_id) for item_id in dict.fromkeys(values.group_ids)
        ]
        record.artwork_links = [
            StoryArtwork(artwork_id=item_id) for item_id in dict.fromkeys(values.artwork_ids)
        ]

    @staticmethod
    def _validate_links(session: Session, values: StoryInput) -> None:
        chapter = ChapterRepository(session).get(values.chapter_id)
        if chapter is None or chapter.universe_id != values.universe_id:
            raise ValueError("The story chapter must belong to its universe.")
        characters = CharacterRepository(session)
        for item_id in values.character_ids:
            character = characters.get(item_id)
            if character is None or character.universe_id != values.universe_id:
                raise ValueError("Story characters must belong to its universe.")
        groups = CharacterGroupRepository(session)
        for item_id in values.group_ids:
            group = groups.get(item_id)
            if group is None or group.universe_id != values.universe_id:
                raise ValueError("Story groups must belong to its universe.")
        artworks = ArtworkRepository(session)
        for item_id in values.artwork_ids:
            artwork = artworks.get(item_id)
            if artwork is None or not StoryService._artwork_available(artwork, values.universe_id):
                raise ValueError("Story artwork must belong to its universe or be unassigned.")

    @staticmethod
    def _artwork_available(artwork: Artwork, universe_id: str) -> bool:
        return artwork.universe_id == universe_id or (
            artwork.universe_id is None and artwork.owner_kind is None and artwork.owner_id is None
        )

    @staticmethod
    def _require(repository: StoryRepository, story_id: str) -> Story:
        record = repository.get(story_id)
        if record is None:
            raise RecordNotFoundError("The selected story no longer exists.")
        return record

    @staticmethod
    def _view(record: Story) -> StoryView:
        characters = sorted(record.character_links, key=lambda link: link.character.name.casefold())
        groups = sorted(record.group_links, key=lambda link: link.group.name.casefold())
        artworks = sorted(record.artwork_links, key=lambda link: link.artwork.title.casefold())
        return StoryView(
            id=record.id,
            universe_id=record.universe_id,
            chapter_id=record.chapter_id,
            chapter_title=record.chapter.title,
            title=record.title,
            content=record.content,
            character_ids=tuple(link.character_id for link in characters),
            character_names=tuple(link.character.name for link in characters),
            group_ids=tuple(link.group_id for link in groups),
            group_names=tuple(link.group.name for link in groups),
            artwork_ids=tuple(link.artwork_id for link in artworks),
            artwork_titles=tuple(link.artwork.title for link in artworks),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

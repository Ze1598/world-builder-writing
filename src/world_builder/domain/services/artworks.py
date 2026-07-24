"""Artwork ownership, reusable associations, galleries, and safe deletion."""

from pathlib import PurePosixPath
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import CharacterMoveError, RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailView,
    ArtworkEntityKind,
    ArtworkInput,
    ArtworkMovePreflight,
    ArtworkMutationResult,
    ArtworkUsageView,
    ArtworkView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    Artwork,
    ArtworkChapter,
    ArtworkCharacter,
    ArtworkGroup,
    ArtworkOwnerKind,
    Chapter,
    Character,
    CharacterGroup,
    Story,
    StoryArtwork,
)
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.persistence.repositories.chapters import ChapterRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.groups import CharacterGroupRepository
from world_builder.persistence.repositories.stories import StoryRepository
from world_builder.storage.artwork import ArtworkStorage, StoredArtworkFile


class ArtworkService:
    """Coordinate artwork metadata, files, ownership, and usage links."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        storage: ArtworkStorage,
    ) -> None:
        self._session_factory = session_factory
        self.storage = storage

    def import_artwork(self, values: ArtworkInput, source: BinaryIO) -> ArtworkView:
        artwork_id = str(uuid4())
        stored: StoredArtworkFile | None = None
        try:
            stored = self.storage.import_image(
                source,
                original_filename=values.original_filename,
                artwork_id=artwork_id,
                owner_kind=values.owner_kind,
                owner_id=values.owner_id,
                universe_id=values.universe_id,
            )
            with database_session(self._session_factory) as session:
                record = ArtworkRepository(session).create(artwork_id, values, stored)
                session.flush()
                view = ArtworkView.model_validate(record)
            return view
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def get_detail(self, artwork_id: str) -> ArtworkDetailView:
        with database_session(self._session_factory) as session:
            record = self._require(ArtworkRepository(session), artwork_id)
            return self._detail(session, record)

    def list_owned_by_universe(self, universe_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_owned_by_universe(universe_id))

    def list_available_for_universe(self, universe_id: str) -> list[ArtworkView]:
        """Return universe-owned and globally unassigned artwork."""
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_available_for_universe(universe_id))

    def list_unassigned(self) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_unassigned())

    def list_gallery_for_character(self, character_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_gallery_for_character(character_id))

    def list_gallery_for_group(self, group_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_gallery_for_group(group_id))

    def list_gallery_for_chapter(self, chapter_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_gallery_for_chapter(chapter_id))

    def list_gallery_for_story(self, story_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            return self._views(ArtworkRepository(session).list_gallery_for_story(story_id))

    def add_association(self, artwork_id: str, kind: ArtworkEntityKind, entity_id: str) -> None:
        self.add_associations((artwork_id,), kind, entity_id)

    def add_associations(
        self,
        artwork_ids: tuple[str, ...],
        kind: ArtworkEntityKind,
        entity_id: str,
    ) -> None:
        """Link several existing artwork records to one entity atomically."""
        try:
            with database_session(self._session_factory) as session:
                repository = ArtworkRepository(session)
                target_universe_id = self._entity_universe(session, kind, entity_id)
                for artwork_id in artwork_ids:
                    artwork = self._require(repository, artwork_id)
                    if (
                        artwork.universe_id is not None
                        and artwork.universe_id != target_universe_id
                    ):
                        raise ValueError("Owned artwork can only link to entities in its universe.")
                    repository.add_association(artwork_id, kind.value, entity_id)
                session.flush()
        except IntegrityError as error:
            raise ValueError("One or more artwork links already exist.") from error

    def remove_association(self, artwork_id: str, kind: ArtworkEntityKind, entity_id: str) -> None:
        with database_session(self._session_factory) as session:
            self._require(ArtworkRepository(session), artwork_id)
            ArtworkRepository(session).remove_association(artwork_id, kind.value, entity_id)

    def preflight_move(
        self,
        artwork_id: str,
        target_owner_kind: ArtworkOwnerKind | None,
        target_owner_id: str | None,
    ) -> ArtworkMovePreflight:
        with database_session(self._session_factory) as session:
            artwork = self._require(ArtworkRepository(session), artwork_id)
            target_universe_id = self._validate_owner_target(
                session, target_owner_kind, target_owner_id
            )
            self._validate_owner_change(artwork, target_owner_kind, target_owner_id)
            usages = self._usages(session, artwork_id)
            incompatible = (
                0
                if target_universe_id is None
                else sum(usage.universe_id != target_universe_id for usage in usages)
            )
            return ArtworkMovePreflight(
                artwork_id=artwork.id,
                source_owner_kind=(
                    ArtworkOwnerKind(artwork.owner_kind) if artwork.owner_kind is not None else None
                ),
                source_owner_id=artwork.owner_id,
                target_owner_kind=target_owner_kind,
                target_owner_id=target_owner_id,
                source_universe_id=artwork.universe_id,
                target_universe_id=target_universe_id,
                incompatible_usage_count=incompatible,
            )

    def move_owner(
        self,
        artwork_id: str,
        target_owner_kind: ArtworkOwnerKind | None,
        target_owner_id: str | None,
        *,
        confirmed: bool = False,
    ) -> ArtworkMutationResult:
        staged_destination: str | None = None
        source_path: str | None = None
        try:
            with database_session(self._session_factory) as session:
                repository = ArtworkRepository(session)
                artwork = self._require(repository, artwork_id)
                target_universe_id = self._validate_owner_target(
                    session, target_owner_kind, target_owner_id
                )
                self._validate_owner_change(artwork, target_owner_kind, target_owner_id)
                incompatible = (
                    0
                    if target_universe_id is None
                    else sum(
                        usage.universe_id != target_universe_id
                        for usage in self._usages(session, artwork_id)
                    )
                )
                if incompatible and not confirmed:
                    raise CharacterMoveError(
                        "Confirm the preflight report before changing artwork ownership."
                    )
                destination = self.storage.relative_path(
                    artwork_id=artwork.id,
                    owner_kind=target_owner_kind,
                    owner_id=target_owner_id,
                    universe_id=target_universe_id,
                    extension=PurePosixPath(artwork.relative_path).suffix,
                ).as_posix()
                self.storage.copy(artwork.relative_path, destination)
                staged_destination = destination
                source_path = artwork.relative_path
                if target_universe_id is not None:
                    repository.delete_incompatible_associations(artwork.id, target_universe_id)
                repository.update_owner(
                    artwork,
                    owner_kind=(target_owner_kind.value if target_owner_kind is not None else None),
                    owner_id=target_owner_id,
                    universe_id=target_universe_id,
                    relative_path=destination,
                )
                session.flush()
                moved = ArtworkView.model_validate(artwork)
        except Exception:
            if staged_destination is not None:
                self.storage.delete(staged_destination)
            raise

        cleanup_warning: str | None = None
        try:
            if source_path is not None:
                self.storage.delete(source_path)
        except OSError:
            cleanup_warning = "Artwork ownership changed, but the previous file copy remains."
        return ArtworkMutationResult(artwork=moved, cleanup_warning=cleanup_warning)

    def delete_artwork(self, artwork_id: str) -> ArtworkMutationResult:
        original_path: str | None = None
        quarantined_path: str | None = None
        try:
            with database_session(self._session_factory) as session:
                repository = ArtworkRepository(session)
                artwork = self._require(repository, artwork_id)
                if artwork.is_primary:
                    raise ValueError("Select another primary artwork before deleting this one.")
                original_path = artwork.relative_path
                quarantined_path = self.storage.quarantine(original_path)
                repository.delete_all_associations(artwork.id)
                repository.delete_record(artwork)
                session.flush()
        except Exception:
            if original_path is not None and quarantined_path is not None:
                self.storage.restore_quarantined(quarantined_path, original_path)
            raise

        cleanup_warning: str | None = None
        try:
            if quarantined_path is not None:
                self.storage.delete(quarantined_path)
        except OSError:
            cleanup_warning = "Artwork was deleted, but its quarantined file remains."
        return ArtworkMutationResult(cleanup_warning=cleanup_warning)

    def known_relative_paths(self) -> list[str]:
        with database_session(self._session_factory) as session:
            return ArtworkRepository(session).list_relative_paths()

    def missing_files(self) -> set[str]:
        return self.storage.missing_files(self.known_relative_paths())

    def orphan_files(self) -> set[str]:
        return self.storage.orphan_files(self.known_relative_paths())

    @staticmethod
    def _require(repository: ArtworkRepository, artwork_id: str) -> Artwork:
        record = repository.get(artwork_id)
        if record is None:
            raise RecordNotFoundError("The selected artwork no longer exists.")
        return record

    @staticmethod
    def _views(records: list[Artwork]) -> list[ArtworkView]:
        return [ArtworkView.model_validate(record) for record in records]

    @staticmethod
    def _validate_owner_change(
        artwork: Artwork,
        target_kind: ArtworkOwnerKind | None,
        target_id: str | None,
    ) -> None:
        if (target_kind is None) != (target_id is None):
            raise ValueError("Artwork owner type and identifier must be supplied together.")
        if (
            artwork.owner_kind == (target_kind.value if target_kind is not None else None)
            and artwork.owner_id == target_id
        ):
            raise ValueError("Select a different artwork owner.")
        if artwork.is_primary:
            raise ValueError("Select another primary artwork before changing ownership.")

    @staticmethod
    def _validate_owner_target(
        session: Session,
        kind: ArtworkOwnerKind | None,
        entity_id: str | None,
    ) -> str | None:
        if kind is None and entity_id is None:
            return None
        if kind is None or entity_id is None:
            raise ValueError("Artwork owner type and identifier must be supplied together.")
        if kind is ArtworkOwnerKind.CHARACTER:
            character = CharacterRepository(session).get(entity_id)
            if character is None:
                raise RecordNotFoundError("The selected character no longer exists.")
            return character.universe_id
        group = CharacterGroupRepository(session).get(entity_id)
        if group is None:
            raise RecordNotFoundError("The selected character group no longer exists.")
        return group.universe_id

    @staticmethod
    def _entity_universe(session: Session, kind: ArtworkEntityKind, entity_id: str) -> str:
        record = {
            ArtworkEntityKind.CHARACTER: CharacterRepository(session).get,
            ArtworkEntityKind.GROUP: CharacterGroupRepository(session).get,
            ArtworkEntityKind.CHAPTER: ChapterRepository(session).get,
            ArtworkEntityKind.STORY: StoryRepository(session).get,
        }[kind](entity_id)
        if record is None:
            raise RecordNotFoundError("The selected association target no longer exists.")
        universe_id = record.universe_id
        if universe_id is None:
            raise ValueError("Artwork cannot link to an unassigned character.")
        return universe_id

    def _detail(self, session: Session, artwork: Artwork) -> ArtworkDetailView:
        owner_name: str | None = None
        if artwork.owner_kind == ArtworkOwnerKind.CHARACTER.value:
            owner = CharacterRepository(session).get(artwork.owner_id or "")
            owner_name = owner.name if owner is not None else None
        elif artwork.owner_kind == ArtworkOwnerKind.GROUP.value:
            owner_group = CharacterGroupRepository(session).get(artwork.owner_id or "")
            owner_name = owner_group.name if owner_group is not None else None
        return ArtworkDetailView(
            artwork=ArtworkView.model_validate(artwork),
            owner_name=owner_name,
            usages=tuple(self._usages(session, artwork.id)),
        )

    @staticmethod
    def _usages(session: Session, artwork_id: str) -> list[ArtworkUsageView]:
        usages = [
            ArtworkUsageView(
                entity_kind=ArtworkEntityKind.CHARACTER,
                entity_id=row.id,
                entity_name=row.name,
                universe_id=row.universe_id,
            )
            for row in session.execute(
                select(Character.id, Character.name, Character.universe_id)
                .join(
                    ArtworkCharacter,
                    ArtworkCharacter.character_id == Character.id,
                )
                .where(ArtworkCharacter.artwork_id == artwork_id)
            )
            if row.universe_id is not None
        ]
        usages.extend(
            ArtworkUsageView(
                entity_kind=ArtworkEntityKind.GROUP,
                entity_id=row.id,
                entity_name=row.name,
                universe_id=row.universe_id,
            )
            for row in session.execute(
                select(
                    CharacterGroup.id,
                    CharacterGroup.name,
                    CharacterGroup.universe_id,
                )
                .join(ArtworkGroup, ArtworkGroup.group_id == CharacterGroup.id)
                .where(ArtworkGroup.artwork_id == artwork_id)
            )
        )
        usages.extend(
            ArtworkUsageView(
                entity_kind=ArtworkEntityKind.CHAPTER,
                entity_id=row.id,
                entity_name=row.title,
                universe_id=row.universe_id,
            )
            for row in session.execute(
                select(Chapter.id, Chapter.title, Chapter.universe_id)
                .join(ArtworkChapter, ArtworkChapter.chapter_id == Chapter.id)
                .where(ArtworkChapter.artwork_id == artwork_id)
            )
        )
        usages.extend(
            ArtworkUsageView(
                entity_kind=ArtworkEntityKind.STORY,
                entity_id=row.id,
                entity_name=row.title,
                universe_id=row.universe_id,
            )
            for row in session.execute(
                select(Story.id, Story.title, Story.universe_id)
                .join(StoryArtwork, StoryArtwork.story_id == Story.id)
                .where(StoryArtwork.artwork_id == artwork_id)
            )
        )
        return sorted(
            usages,
            key=lambda usage: (
                usage.entity_kind.value,
                usage.entity_name.casefold(),
                usage.entity_id,
            ),
        )

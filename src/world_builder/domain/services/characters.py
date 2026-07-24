"""Character profiles and atomic owned-artwork workflows."""

from pathlib import PurePosixPath
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import CharacterMoveError, RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkInput,
    ArtworkView,
    CharacterInput,
    CharacterMovePreflight,
    CharacterMoveResult,
    CharacterView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import Artwork, ArtworkOwnerKind, Character
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.persistence.repositories.chapters import ChapterRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.memberships import GroupMembershipRepository
from world_builder.persistence.repositories.relationships import (
    CharacterRelationshipRepository,
)
from world_builder.persistence.repositories.stories import StoryRepository
from world_builder.persistence.repositories.universes import UniverseRepository
from world_builder.storage.artwork import ArtworkStorage, StoredArtworkFile


class CharacterService:
    """Manage characters while preserving their primary-artwork invariant."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        storage: ArtworkStorage,
    ) -> None:
        self._session_factory = session_factory
        self.storage = storage

    def create_character(
        self,
        values: CharacterInput,
        artwork: ArtworkDetailsInput,
        source: BinaryIO,
    ) -> CharacterView:
        """Atomically create a character and its required primary artwork."""
        character_id = str(uuid4())
        artwork_id = str(uuid4())
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                self._require_universe(session, values.universe_id)
                record = CharacterRepository(session).create(character_id, values)
                stored = self.storage.import_image(
                    source,
                    original_filename=artwork.original_filename,
                    artwork_id=artwork_id,
                    owner_kind=ArtworkOwnerKind.CHARACTER,
                    owner_id=character_id,
                    universe_id=values.universe_id,
                )
                ArtworkRepository(session).create(
                    artwork_id,
                    ArtworkInput(
                        owner_kind=ArtworkOwnerKind.CHARACTER,
                        owner_id=character_id,
                        universe_id=values.universe_id,
                        title=artwork.title,
                        description=artwork.description,
                        original_filename=artwork.original_filename,
                        is_primary=True,
                    ),
                    stored,
                )
                session.flush()
                self._assert_exactly_one_primary(session, character_id)
                view = CharacterView.model_validate(record)
            return view
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def list_for_universe(
        self, universe_id: str, *, active: bool | None = None
    ) -> list[CharacterView]:
        with database_session(self._session_factory) as session:
            records = CharacterRepository(session).list_for_universe(universe_id, active=active)
            return [CharacterView.model_validate(record) for record in records]

    def list_unassigned(self, *, active: bool | None = None) -> list[CharacterView]:
        with database_session(self._session_factory) as session:
            records = CharacterRepository(session).list_unassigned(active=active)
            return [CharacterView.model_validate(record) for record in records]

    def get_character(self, character_id: str) -> CharacterView | None:
        with database_session(self._session_factory) as session:
            record = CharacterRepository(session).get(character_id)
            return CharacterView.model_validate(record) if record is not None else None

    def update_character(self, character_id: str, values: CharacterInput) -> CharacterView:
        """Update profile text without allowing reassignment through generic editing."""
        with database_session(self._session_factory) as session:
            repository = CharacterRepository(session)
            record = self._require_character(repository, character_id)
            if values.universe_id != record.universe_id:
                raise ValueError("Character movement requires the dedicated move workflow.")
            repository.update(record, values)
            session.flush()
            return CharacterView.model_validate(record)

    def set_active(self, character_id: str, *, is_active: bool) -> CharacterView:
        with database_session(self._session_factory) as session:
            record = self._require_character(CharacterRepository(session), character_id)
            record.is_active = is_active
            session.flush()
            return CharacterView.model_validate(record)

    def preflight_move(
        self, character_id: str, target_universe_id: str | None
    ) -> CharacterMovePreflight:
        """Validate a destination and report every connection category affected."""
        with database_session(self._session_factory) as session:
            character = self._require_character(CharacterRepository(session), character_id)
            self._validate_move(session, character, target_universe_id)
            artwork_repository = ArtworkRepository(session)
            artworks = artwork_repository.list_for_character(character_id)
            self._assert_move_artwork_invariants(session, character_id, artworks)
            membership_count = GroupMembershipRepository(session).count_for_character(character_id)
            chapter_link_count = ChapterRepository(session).count_links_for_character(character_id)
            story_link_count = StoryRepository(session).count_links_for_character(character_id)
            relationship_count = CharacterRelationshipRepository(session).count_for_character(
                character_id
            )
            artwork_association_count = (
                0
                if target_universe_id is None
                else sum(artwork_repository.usage_count(artwork.id) for artwork in artworks)
            )
            return CharacterMovePreflight(
                character_id=character.id,
                source_universe_id=character.universe_id,
                target_universe_id=target_universe_id,
                artwork_count=len(artworks),
                artwork_association_count=artwork_association_count,
                disables_character=character.universe_id is not None and character.is_active,
                relationship_count=relationship_count,
                membership_count=membership_count,
                story_link_count=story_link_count,
                chapter_link_count=chapter_link_count,
            )

    def move_character(
        self,
        character_id: str,
        target_universe_id: str | None,
        *,
        confirmed: bool = False,
    ) -> CharacterMoveResult:
        """Move a character and its artwork without exposing a half-moved state."""
        staged_destinations: list[str] = []
        source_paths: list[str] = []
        try:
            with database_session(self._session_factory) as session:
                character_repository = CharacterRepository(session)
                artwork_repository = ArtworkRepository(session)
                character = self._require_character(character_repository, character_id)
                self._validate_move(session, character, target_universe_id)
                artworks = artwork_repository.list_for_character(character_id)
                self._assert_move_artwork_invariants(session, character_id, artworks)
                if character.universe_id is not None and not confirmed:
                    raise CharacterMoveError(
                        "Confirm the preflight report before moving this character."
                    )

                planned_paths: list[tuple[Artwork, str]] = []
                for artwork in artworks:
                    destination = self.storage.relative_path(
                        artwork_id=artwork.id,
                        owner_kind=ArtworkOwnerKind.CHARACTER,
                        owner_id=character_id,
                        universe_id=target_universe_id,
                        extension=PurePosixPath(artwork.relative_path).suffix,
                    ).as_posix()
                    self.storage.copy(artwork.relative_path, destination)
                    staged_destinations.append(destination)
                    source_paths.append(artwork.relative_path)
                    planned_paths.append((artwork, destination))

                if character.universe_id is not None:
                    character.is_active = False
                    CharacterRelationshipRepository(session).delete_for_character(character_id)
                    GroupMembershipRepository(session).delete_for_character(character_id)
                    ChapterRepository(session).delete_links_for_character(character_id)
                    StoryRepository(session).delete_links_for_character(character_id)
                character_repository.move(character, target_universe_id)
                for artwork, destination in planned_paths:
                    if target_universe_id is not None:
                        artwork_repository.delete_incompatible_associations(
                            artwork.id, target_universe_id
                        )
                    artwork_repository.move_character_artwork(
                        artwork,
                        universe_id=target_universe_id,
                        relative_path=destination,
                    )
                session.flush()
                self._assert_exactly_one_primary(session, character_id)
                moved = CharacterView.model_validate(character)
        except Exception:
            for destination in staged_destinations:
                self.storage.delete(destination)
            raise

        cleanup_warning: str | None = None
        try:
            for source_path in source_paths:
                self.storage.delete(source_path)
        except OSError:
            cleanup_warning = (
                "The character moved, but one or more old artwork copies could not be removed."
            )
        return CharacterMoveResult(character=moved, cleanup_warning=cleanup_warning)

    def list_artworks(self, character_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            self._require_character(CharacterRepository(session), character_id)
            return [
                ArtworkView.model_validate(record)
                for record in ArtworkRepository(session).list_for_character(character_id)
            ]

    def add_artwork(
        self,
        character_id: str,
        artwork: ArtworkDetailsInput,
        source: BinaryIO,
    ) -> ArtworkView:
        """Add a non-primary artwork to an existing character."""
        artwork_id = str(uuid4())
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                character = self._require_character(CharacterRepository(session), character_id)
                stored = self.storage.import_image(
                    source,
                    original_filename=artwork.original_filename,
                    artwork_id=artwork_id,
                    owner_kind=ArtworkOwnerKind.CHARACTER,
                    owner_id=character_id,
                    universe_id=character.universe_id,
                )
                record = ArtworkRepository(session).create(
                    artwork_id,
                    ArtworkInput(
                        owner_kind=ArtworkOwnerKind.CHARACTER,
                        owner_id=character_id,
                        universe_id=character.universe_id,
                        title=artwork.title,
                        description=artwork.description,
                        original_filename=artwork.original_filename,
                    ),
                    stored,
                )
                session.flush()
                self._assert_exactly_one_primary(session, character_id)
                view = ArtworkView.model_validate(record)
            return view
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def set_primary_artwork(self, character_id: str, artwork_id: str) -> None:
        with database_session(self._session_factory) as session:
            self._require_character(CharacterRepository(session), character_id)
            repository = ArtworkRepository(session)
            artwork = repository.get(artwork_id)
            if (
                artwork is None
                or artwork.owner_kind != ArtworkOwnerKind.CHARACTER.value
                or artwork.owner_id != character_id
            ):
                raise RecordNotFoundError("The selected artwork does not belong to this character.")
            repository.clear_character_primary(character_id)
            session.flush()
            artwork.is_primary = True
            session.flush()
            self._assert_exactly_one_primary(session, character_id)

    @staticmethod
    def _require_character(repository: CharacterRepository, character_id: str) -> Character:
        record = repository.get(character_id)
        if record is None:
            raise RecordNotFoundError("The selected character no longer exists.")
        return record

    @staticmethod
    def _require_universe(session: Session, universe_id: str | None) -> None:
        if universe_id is not None and UniverseRepository(session).get(universe_id) is None:
            raise RecordNotFoundError("The selected universe no longer exists.")

    def _validate_move(
        self,
        session: Session,
        character: Character,
        target_universe_id: str | None,
    ) -> None:
        self._require_universe(session, target_universe_id)
        if character.universe_id == target_universe_id:
            raise CharacterMoveError("Select a different character location.")

    @staticmethod
    def _assert_move_artwork_invariants(
        session: Session, character_id: str, artworks: list[Artwork]
    ) -> None:
        if not artworks:
            raise CharacterMoveError("The character has no artwork to move.")
        CharacterService._assert_exactly_one_primary(session, character_id)

    @staticmethod
    def _assert_exactly_one_primary(session: Session, character_id: str) -> None:
        statement = select(func.count(Artwork.id)).where(
            Artwork.owner_kind == ArtworkOwnerKind.CHARACTER.value,
            Artwork.owner_id == character_id,
            Artwork.is_primary.is_(True),
        )
        if session.scalar(statement) != 1:
            raise RuntimeError("A character must have exactly one primary artwork.")

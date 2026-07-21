"""Character profiles and atomic owned-artwork workflows."""

from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkInput,
    ArtworkView,
    CharacterInput,
    CharacterView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import Artwork, ArtworkOwnerKind, Character
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.persistence.repositories.characters import CharacterRepository
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

    @staticmethod
    def _assert_exactly_one_primary(session: Session, character_id: str) -> None:
        statement = select(func.count(Artwork.id)).where(
            Artwork.owner_kind == ArtworkOwnerKind.CHARACTER.value,
            Artwork.owner_id == character_id,
            Artwork.is_primary.is_(True),
        )
        if session.scalar(statement) != 1:
            raise RuntimeError("A character must have exactly one primary artwork.")

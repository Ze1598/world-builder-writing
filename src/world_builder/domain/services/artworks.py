"""Atomic artwork metadata and filesystem import workflow."""

from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.models import ArtworkInput, ArtworkView
from world_builder.persistence.database import database_session
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.storage.artwork import ArtworkStorage, StoredArtworkFile


class ArtworkService:
    """Coordinate image storage with artwork metadata transactions."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        storage: ArtworkStorage,
    ) -> None:
        self._session_factory = session_factory
        self.storage = storage

    def import_artwork(self, values: ArtworkInput, source: BinaryIO) -> ArtworkView:
        """Import a validated image and roll it back if metadata persistence fails."""
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

    def known_relative_paths(self) -> list[str]:
        """Return every artwork path represented in SQLite."""
        with database_session(self._session_factory) as session:
            return ArtworkRepository(session).list_relative_paths()

    def missing_files(self) -> set[str]:
        return self.storage.missing_files(self.known_relative_paths())

    def orphan_files(self) -> set[str]:
        return self.storage.orphan_files(self.known_relative_paths())

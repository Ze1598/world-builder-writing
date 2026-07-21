"""Persistence operations for artwork metadata."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from world_builder.domain.models import ArtworkInput
from world_builder.persistence.models import Artwork
from world_builder.storage.artwork import StoredArtworkFile


class ArtworkRepository:
    """Query and mutate artwork records within an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, artwork_id: str) -> Artwork | None:
        return self._session.get(Artwork, artwork_id)

    def list_relative_paths(self) -> list[str]:
        return list(self._session.scalars(select(Artwork.relative_path)))

    def list_for_character(self, character_id: str) -> list[Artwork]:
        statement = (
            select(Artwork)
            .where(
                Artwork.owner_kind == "character",
                Artwork.owner_id == character_id,
            )
            .order_by(Artwork.is_primary.desc(), Artwork.created_at, Artwork.id)
        )
        return list(self._session.scalars(statement))

    def clear_character_primary(self, character_id: str) -> None:
        self._session.execute(
            update(Artwork)
            .where(
                Artwork.owner_kind == "character",
                Artwork.owner_id == character_id,
                Artwork.is_primary.is_(True),
            )
            .values(is_primary=False)
        )

    def create(
        self,
        artwork_id: str,
        values: ArtworkInput,
        stored: StoredArtworkFile,
    ) -> Artwork:
        record = Artwork(
            id=artwork_id,
            universe_id=values.universe_id,
            owner_kind=values.owner_kind.value,
            owner_id=values.owner_id,
            title=values.title,
            description=values.description,
            original_filename=stored.original_filename,
            mime_type=stored.mime_type,
            relative_path=stored.relative_path,
            file_size=stored.file_size,
            is_primary=values.is_primary,
        )
        self._session.add(record)
        return record

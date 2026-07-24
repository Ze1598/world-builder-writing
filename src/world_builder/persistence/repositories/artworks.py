"""Persistence operations for artwork metadata."""

from sqlalchemy import Select, Table, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import FromClause

from world_builder.domain.models import ArtworkInput
from world_builder.persistence.models import (
    Artwork,
    ArtworkChapter,
    ArtworkCharacter,
    ArtworkGroup,
    Chapter,
    Character,
    CharacterGroup,
    Story,
    StoryArtwork,
)
from world_builder.storage.artwork import StoredArtworkFile


def _as_table(selectable: FromClause) -> Table:
    """Narrow SQLAlchemy's declarative ``__table__`` type for Core mutations."""
    if not isinstance(selectable, Table):
        raise TypeError("Artwork association metadata must resolve to a SQLAlchemy Table.")
    return selectable


ARTWORK_ASSOCIATION_TABLES = tuple(
    _as_table(model.__table__)
    for model in (ArtworkCharacter, ArtworkGroup, ArtworkChapter, StoryArtwork)
)

ARTWORK_ASSOCIATION_TARGETS = (
    (ARTWORK_ASSOCIATION_TABLES[0], "character_id", _as_table(Character.__table__)),
    (ARTWORK_ASSOCIATION_TABLES[1], "group_id", _as_table(CharacterGroup.__table__)),
    (ARTWORK_ASSOCIATION_TABLES[2], "chapter_id", _as_table(Chapter.__table__)),
    (ARTWORK_ASSOCIATION_TABLES[3], "story_id", _as_table(Story.__table__)),
)

ARTWORK_ASSOCIATION_BY_KIND = {
    "character": (ARTWORK_ASSOCIATION_TABLES[0], "character_id"),
    "group": (ARTWORK_ASSOCIATION_TABLES[1], "group_id"),
    "chapter": (ARTWORK_ASSOCIATION_TABLES[2], "chapter_id"),
    "story": (ARTWORK_ASSOCIATION_TABLES[3], "story_id"),
}


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

    def list_for_group(self, group_id: str) -> list[Artwork]:
        statement = (
            select(Artwork)
            .where(
                Artwork.owner_kind == "group",
                Artwork.owner_id == group_id,
            )
            .order_by(Artwork.created_at, Artwork.id)
        )
        return list(self._session.scalars(statement))

    def list_available_for_universe(self, universe_id: str) -> list[Artwork]:
        """Return universe-owned and globally unassigned artwork."""
        statement = (
            select(Artwork)
            .where(
                (Artwork.universe_id == universe_id)
                | (
                    Artwork.universe_id.is_(None)
                    & Artwork.owner_kind.is_(None)
                    & Artwork.owner_id.is_(None)
                )
            )
            .order_by(Artwork.title.collate("NOCASE"), Artwork.id)
        )
        return list(self._session.scalars(statement))

    def list_owned_by_universe(self, universe_id: str) -> list[Artwork]:
        statement = (
            select(Artwork)
            .where(Artwork.universe_id == universe_id)
            .order_by(func.lower(Artwork.title), Artwork.id)
        )
        return list(self._session.scalars(statement))

    def list_unassigned(self) -> list[Artwork]:
        statement = (
            select(Artwork)
            .where(
                Artwork.universe_id.is_(None),
                Artwork.owner_kind.is_(None),
                Artwork.owner_id.is_(None),
            )
            .order_by(func.lower(Artwork.title), Artwork.id)
        )
        return list(self._session.scalars(statement))

    def list_gallery_for_character(self, character_id: str) -> list[Artwork]:
        associated = select(ArtworkCharacter.artwork_id).where(
            ArtworkCharacter.character_id == character_id
        )
        return self._list_gallery(
            (Artwork.owner_kind == "character") & (Artwork.owner_id == character_id),
            associated,
        )

    def list_gallery_for_group(self, group_id: str) -> list[Artwork]:
        associated = select(ArtworkGroup.artwork_id).where(ArtworkGroup.group_id == group_id)
        return self._list_gallery(
            (Artwork.owner_kind == "group") & (Artwork.owner_id == group_id),
            associated,
        )

    def list_gallery_for_chapter(self, chapter_id: str) -> list[Artwork]:
        associated = select(ArtworkChapter.artwork_id).where(
            ArtworkChapter.chapter_id == chapter_id
        )
        return self._list_gallery(None, associated)

    def list_gallery_for_story(self, story_id: str) -> list[Artwork]:
        associated = select(StoryArtwork.artwork_id).where(StoryArtwork.story_id == story_id)
        return self._list_gallery(None, associated)

    def _list_gallery(
        self,
        owned: ColumnElement[bool] | None,
        associated: Select[tuple[str]],
    ) -> list[Artwork]:
        condition: ColumnElement[bool] = Artwork.id.in_(associated)
        if owned is not None:
            condition = (condition | owned).self_group()
        statement = (
            select(Artwork)
            .where(condition)
            .order_by(Artwork.is_primary.desc(), func.lower(Artwork.title), Artwork.id)
        )
        return list(self._session.scalars(statement))

    def usage_count(self, artwork_id: str) -> int:
        counts = [
            self._session.scalar(
                select(func.count()).select_from(table).where(table.c["artwork_id"] == artwork_id)
            )
            or 0
            for table in ARTWORK_ASSOCIATION_TABLES
        ]
        return sum(counts)

    def add_association(self, artwork_id: str, kind: str, entity_id: str) -> None:
        record = {
            "character": ArtworkCharacter(artwork_id=artwork_id, character_id=entity_id),
            "group": ArtworkGroup(artwork_id=artwork_id, group_id=entity_id),
            "chapter": ArtworkChapter(artwork_id=artwork_id, chapter_id=entity_id),
            "story": StoryArtwork(artwork_id=artwork_id, story_id=entity_id),
        }[kind]
        self._session.add(record)

    def remove_association(self, artwork_id: str, kind: str, entity_id: str) -> None:
        table, entity_id_column = ARTWORK_ASSOCIATION_BY_KIND[kind]
        self._session.execute(
            table.delete().where(
                table.c["artwork_id"] == artwork_id,
                table.c[entity_id_column] == entity_id,
            )
        )

    def delete_incompatible_associations(self, artwork_id: str, universe_id: str) -> None:
        for link_table, entity_id_column, entity_table in ARTWORK_ASSOCIATION_TARGETS:
            valid_ids = select(entity_table.c["id"]).where(
                entity_table.c["universe_id"] == universe_id
            )
            self._session.execute(
                link_table.delete().where(
                    link_table.c["artwork_id"] == artwork_id,
                    link_table.c[entity_id_column].not_in(valid_ids),
                )
            )

    def delete_all_associations(self, artwork_id: str) -> None:
        for table in ARTWORK_ASSOCIATION_TABLES:
            self._session.execute(table.delete().where(table.c["artwork_id"] == artwork_id))

    @staticmethod
    def update_owner(
        record: Artwork,
        *,
        owner_kind: str | None,
        owner_id: str | None,
        universe_id: str | None,
        relative_path: str,
    ) -> None:
        record.owner_kind = owner_kind
        record.owner_id = owner_id
        record.universe_id = universe_id
        record.relative_path = relative_path

    def delete_record(self, record: Artwork) -> None:
        self._session.delete(record)

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

    @staticmethod
    def move_character_artwork(
        record: Artwork, *, universe_id: str | None, relative_path: str
    ) -> None:
        """Update one character artwork after its destination file is staged."""
        record.universe_id = universe_id
        record.relative_path = relative_path

    def create(
        self,
        artwork_id: str,
        values: ArtworkInput,
        stored: StoredArtworkFile,
    ) -> Artwork:
        record = Artwork(
            id=artwork_id,
            universe_id=values.universe_id,
            owner_kind=values.owner_kind.value if values.owner_kind is not None else None,
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

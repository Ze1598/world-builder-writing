"""Persistence operations for sequenced chapters and entity links."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from world_builder.persistence.models import Chapter, ChapterCharacter, ChapterGroup


class ChapterRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, chapter_id: str) -> Chapter | None:
        statement = (
            select(Chapter)
            .options(
                selectinload(Chapter.character_links).selectinload(ChapterCharacter.character),
                selectinload(Chapter.group_links).selectinload(ChapterGroup.group),
            )
            .where(Chapter.id == chapter_id)
        )
        return self._session.scalar(statement)

    def list_for_universe(self, universe_id: str) -> list[Chapter]:
        statement = (
            select(Chapter)
            .options(
                selectinload(Chapter.character_links).selectinload(ChapterCharacter.character),
                selectinload(Chapter.group_links).selectinload(ChapterGroup.group),
            )
            .where(Chapter.universe_id == universe_id)
            .order_by(
                Chapter.sequence_position,
                func.lower(Chapter.title),
                Chapter.id,
            )
        )
        return list(self._session.scalars(statement))

    def next_position(self, universe_id: str) -> int:
        maximum = self._session.scalar(
            select(func.max(Chapter.sequence_position)).where(Chapter.universe_id == universe_id)
        )
        return (maximum or 0) + 1

    def add(self, record: Chapter) -> None:
        self._session.add(record)

    def delete(self, record: Chapter) -> None:
        self._session.delete(record)

    def count_links_for_character(self, character_id: str) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(ChapterCharacter)
                .where(ChapterCharacter.character_id == character_id)
            )
            or 0
        )

    def delete_links_for_character(self, character_id: str) -> None:
        self._session.execute(
            delete(ChapterCharacter).where(ChapterCharacter.character_id == character_id)
        )

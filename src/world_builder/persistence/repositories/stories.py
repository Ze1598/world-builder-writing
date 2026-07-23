"""Persistence operations for stories and their associations."""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from world_builder.persistence.models import (
    Story,
    StoryArtwork,
    StoryCharacter,
    StoryGroup,
)


class StoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _base_statement() -> Select[tuple[Story]]:
        return select(Story).options(
            selectinload(Story.chapter),
            selectinload(Story.character_links).selectinload(StoryCharacter.character),
            selectinload(Story.group_links).selectinload(StoryGroup.group),
            selectinload(Story.artwork_links).selectinload(StoryArtwork.artwork),
        )

    def get(self, story_id: str) -> Story | None:
        statement = self._base_statement().where(Story.id == story_id)
        return self._session.scalar(statement)

    def list_for_universe(self, universe_id: str) -> list[Story]:
        statement = (
            self._base_statement()
            .where(Story.universe_id == universe_id)
            .order_by(func.lower(Story.title), Story.id)
        )
        return list(self._session.scalars(statement))

    def list_for_chapter(self, chapter_id: str) -> list[Story]:
        return self._list_linked(Story.chapter_id == chapter_id)

    def list_for_character(self, character_id: str) -> list[Story]:
        return self._list_linked(
            Story.id.in_(
                select(StoryCharacter.story_id).where(StoryCharacter.character_id == character_id)
            )
        )

    def list_for_group(self, group_id: str) -> list[Story]:
        return self._list_linked(
            Story.id.in_(select(StoryGroup.story_id).where(StoryGroup.group_id == group_id))
        )

    def _list_linked(self, condition: ColumnElement[bool]) -> list[Story]:
        statement = (
            self._base_statement().where(condition).order_by(func.lower(Story.title), Story.id)
        )
        return list(self._session.scalars(statement))

    def count_for_chapter(self, chapter_id: str) -> int:
        return (
            self._session.scalar(
                select(func.count()).select_from(Story).where(Story.chapter_id == chapter_id)
            )
            or 0
        )

    def count_links_for_character(self, character_id: str) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(StoryCharacter)
                .where(StoryCharacter.character_id == character_id)
            )
            or 0
        )

    def delete_links_for_character(self, character_id: str) -> None:
        self._session.execute(
            delete(StoryCharacter).where(StoryCharacter.character_id == character_id)
        )

    def add(self, record: Story) -> None:
        self._session.add(record)

    def delete(self, record: Story) -> None:
        self._session.delete(record)

"""Persistence operations for planning milestones and their entity links."""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from world_builder.persistence.models import (
    Milestone,
    MilestoneChapter,
    MilestoneCharacter,
    MilestoneGroup,
    MilestoneStory,
)


class MilestoneRepository:
    """Load complete milestones and apply reusable association operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _base_statement() -> Select[tuple[Milestone]]:
        return select(Milestone).options(
            selectinload(Milestone.character_links).selectinload(MilestoneCharacter.character),
            selectinload(Milestone.group_links).selectinload(MilestoneGroup.group),
            selectinload(Milestone.chapter_links).selectinload(MilestoneChapter.chapter),
            selectinload(Milestone.story_links).selectinload(MilestoneStory.story),
        )

    def get(self, milestone_id: str) -> Milestone | None:
        return self._session.scalar(self._base_statement().where(Milestone.id == milestone_id))

    def list_for_universe(self, universe_id: str) -> list[Milestone]:
        return self._list(
            Milestone.universe_id == universe_id,
        )

    def list_for_character(self, character_id: str) -> list[Milestone]:
        return self._list(
            Milestone.id.in_(
                select(MilestoneCharacter.milestone_id).where(
                    MilestoneCharacter.character_id == character_id
                )
            )
        )

    def list_for_group(self, group_id: str) -> list[Milestone]:
        return self._list(
            Milestone.id.in_(
                select(MilestoneGroup.milestone_id).where(MilestoneGroup.group_id == group_id)
            )
        )

    def list_for_chapter(self, chapter_id: str) -> list[Milestone]:
        return self._list(
            Milestone.id.in_(
                select(MilestoneChapter.milestone_id).where(
                    MilestoneChapter.chapter_id == chapter_id
                )
            )
        )

    def list_for_story(self, story_id: str) -> list[Milestone]:
        return self._list(
            Milestone.id.in_(
                select(MilestoneStory.milestone_id).where(MilestoneStory.story_id == story_id)
            )
        )

    def _list(self, condition: ColumnElement[bool]) -> list[Milestone]:
        statement = (
            self._base_statement()
            .where(condition)
            .order_by(func.lower(Milestone.title), Milestone.id)
        )
        return list(self._session.scalars(statement))

    def add(self, record: Milestone) -> None:
        self._session.add(record)

    def delete(self, record: Milestone) -> None:
        self._session.delete(record)

    def count_links_for_character(self, character_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(MilestoneCharacter)
            .where(MilestoneCharacter.character_id == character_id)
        )
        return int(self._session.scalar(statement) or 0)

    def delete_links_for_character(self, character_id: str) -> None:
        self._session.execute(
            delete(MilestoneCharacter).where(MilestoneCharacter.character_id == character_id)
        )

"""Persistence operations for character groups."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from world_builder.domain.models import CharacterGroupInput
from world_builder.persistence.models import CharacterGroup


class CharacterGroupRepository:
    """Query and mutate character groups inside an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, group_id: str) -> CharacterGroup | None:
        return self._session.get(CharacterGroup, group_id)

    def list_for_universe(self, universe_id: str) -> list[CharacterGroup]:
        statement = (
            select(CharacterGroup)
            .where(CharacterGroup.universe_id == universe_id)
            .order_by(func.lower(CharacterGroup.name), CharacterGroup.id)
        )
        return list(self._session.scalars(statement))

    def create(self, group_id: str, values: CharacterGroupInput) -> CharacterGroup:
        record = CharacterGroup(
            id=group_id,
            universe_id=values.universe_id,
            name=values.name,
            description=values.description,
        )
        self._session.add(record)
        return record

    @staticmethod
    def update(record: CharacterGroup, values: CharacterGroupInput) -> None:
        record.name = values.name
        record.description = values.description

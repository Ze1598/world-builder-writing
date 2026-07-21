"""Persistence operations for character records."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from world_builder.domain.models import CharacterInput
from world_builder.persistence.models import Character


class CharacterRepository:
    """Query and mutate character records within an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, character_id: str) -> Character | None:
        return self._session.get(Character, character_id)

    def list_for_universe(self, universe_id: str, *, active: bool | None = None) -> list[Character]:
        statement = select(Character).where(Character.universe_id == universe_id)
        if active is not None:
            statement = statement.where(Character.is_active.is_(active))
        return list(
            self._session.scalars(statement.order_by(func.lower(Character.name), Character.id))
        )

    def list_unassigned(self, *, active: bool | None = None) -> list[Character]:
        statement = select(Character).where(Character.universe_id.is_(None))
        if active is not None:
            statement = statement.where(Character.is_active.is_(active))
        return list(
            self._session.scalars(statement.order_by(func.lower(Character.name), Character.id))
        )

    def create(self, character_id: str, values: CharacterInput) -> Character:
        record = Character(
            id=character_id,
            universe_id=values.universe_id,
            name=values.name,
            summary=values.summary,
            is_active=True,
        )
        self._session.add(record)
        return record

    def update(self, record: Character, values: CharacterInput) -> None:
        record.name = values.name
        record.summary = values.summary

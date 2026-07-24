"""Persistence operations for current character relationships."""

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from world_builder.persistence.models import CharacterRelationship


class CharacterRelationshipRepository:
    """Query and mutate one current edge per unordered character pair."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, relationship_id: str) -> CharacterRelationship | None:
        statement = (
            select(CharacterRelationship)
            .where(CharacterRelationship.id == relationship_id)
            .options(
                joinedload(CharacterRelationship.first_character),
                joinedload(CharacterRelationship.second_character),
                joinedload(CharacterRelationship.source_character),
                joinedload(CharacterRelationship.relationship_type),
            )
        )
        return self._session.scalar(statement)

    def list_for_character(self, character_id: str) -> list[CharacterRelationship]:
        statement = (
            select(CharacterRelationship)
            .where(
                or_(
                    CharacterRelationship.first_character_id == character_id,
                    CharacterRelationship.second_character_id == character_id,
                )
            )
            .options(
                joinedload(CharacterRelationship.first_character),
                joinedload(CharacterRelationship.second_character),
                joinedload(CharacterRelationship.source_character),
                joinedload(CharacterRelationship.relationship_type),
            )
            .order_by(
                func.lower(CharacterRelationship.description),
                CharacterRelationship.id,
            )
        )
        return list(self._session.scalars(statement))

    def create(
        self,
        *,
        relationship_id: str,
        universe_id: str,
        first_character_id: str,
        second_character_id: str,
        relationship_type_id: str,
        source_character_id: str | None,
        description: str,
    ) -> CharacterRelationship:
        record = CharacterRelationship(
            id=relationship_id,
            universe_id=universe_id,
            first_character_id=first_character_id,
            second_character_id=second_character_id,
            relationship_type_id=relationship_type_id,
            source_character_id=source_character_id,
            description=description,
        )
        self._session.add(record)
        return record

    def count_for_character(self, character_id: str) -> int:
        statement = select(func.count(CharacterRelationship.id)).where(
            or_(
                CharacterRelationship.first_character_id == character_id,
                CharacterRelationship.second_character_id == character_id,
            )
        )
        return int(self._session.scalar(statement) or 0)

    def delete_for_character(self, character_id: str) -> None:
        self._session.execute(
            delete(CharacterRelationship).where(
                or_(
                    CharacterRelationship.first_character_id == character_id,
                    CharacterRelationship.second_character_id == character_id,
                )
            )
        )

    def delete(self, relationship_id: str) -> bool:
        exists = self._session.get(CharacterRelationship, relationship_id) is not None
        self._session.execute(
            delete(CharacterRelationship).where(CharacterRelationship.id == relationship_id)
        )
        return exists

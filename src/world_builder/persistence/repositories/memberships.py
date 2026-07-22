"""Persistence operations for current group memberships."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from world_builder.persistence.models import Character, GroupMembership


class GroupMembershipRepository:
    """Query and mutate memberships inside an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, membership_id: str) -> GroupMembership | None:
        return self._session.get(GroupMembership, membership_id)

    def get_for_pair(self, group_id: str, character_id: str) -> GroupMembership | None:
        statement = select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.character_id == character_id,
        )
        return self._session.scalar(statement)

    def list_for_group(self, group_id: str) -> list[GroupMembership]:
        statement = (
            select(GroupMembership)
            .options(joinedload(GroupMembership.character))
            .where(GroupMembership.group_id == group_id)
            .join(GroupMembership.character)
            .order_by(func.lower(Character.name), Character.id)
        )
        return list(self._session.scalars(statement))

    def count_for_character(self, character_id: str) -> int:
        statement = select(func.count(GroupMembership.id)).where(
            GroupMembership.character_id == character_id
        )
        return self._session.scalar(statement) or 0

    def create(
        self,
        membership_id: str,
        *,
        group_id: str,
        character_id: str,
        description: str,
    ) -> GroupMembership:
        record = GroupMembership(
            id=membership_id,
            group_id=group_id,
            character_id=character_id,
            description=description,
        )
        self._session.add(record)
        return record

    @staticmethod
    def update(record: GroupMembership, description: str) -> None:
        record.description = description

    def delete(self, record: GroupMembership) -> None:
        self._session.delete(record)

    def delete_for_character(self, character_id: str) -> None:
        self._session.execute(
            delete(GroupMembership).where(GroupMembership.character_id == character_id)
        )

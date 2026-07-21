"""Persistence operations for managed lookup values."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from world_builder.domain.models import LookupValueInput
from world_builder.persistence.models import LookupCategory, LookupValue


class LookupRepository:
    """Query and mutate lookup records within an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_category(self, code: str) -> LookupCategory | None:
        return self._session.scalar(select(LookupCategory).where(LookupCategory.code == code))

    def create_category(self, code: str, name: str, description: str) -> LookupCategory:
        record = LookupCategory(code=code, name=name, description=description)
        self._session.add(record)
        return record

    def list_categories(self) -> list[LookupCategory]:
        return list(self._session.scalars(select(LookupCategory).order_by(LookupCategory.name)))

    def get_value(self, value_id: str) -> LookupValue | None:
        return self._session.get(LookupValue, value_id)

    def list_values(
        self, universe_id: str, category_id: str, *, active_only: bool = False
    ) -> list[LookupValue]:
        statement = select(LookupValue).where(
            LookupValue.universe_id == universe_id,
            LookupValue.category_id == category_id,
        )
        if active_only:
            statement = statement.where(LookupValue.is_active.is_(True))
        statement = statement.order_by(func.lower(LookupValue.name), LookupValue.id)
        return list(self._session.scalars(statement))

    def name_exists(
        self,
        universe_id: str,
        category_id: str,
        name: str,
        *,
        excluding_id: str | None = None,
    ) -> bool:
        statement = select(LookupValue.id).where(
            LookupValue.universe_id == universe_id,
            LookupValue.category_id == category_id,
            func.lower(LookupValue.name) == name.casefold(),
        )
        if excluding_id is not None:
            statement = statement.where(LookupValue.id != excluding_id)
        return self._session.scalar(statement) is not None

    def create_value(
        self,
        universe_id: str,
        category_id: str,
        values: LookupValueInput,
        display_order: int,
    ) -> LookupValue:
        record = LookupValue(
            universe_id=universe_id,
            category_id=category_id,
            name=values.name,
            description=values.description,
            display_order=display_order,
            relationship_directionality=(
                values.relationship_directionality.value
                if values.relationship_directionality is not None
                else None
            ),
        )
        self._session.add(record)
        return record

    def update_value(self, record: LookupValue, values: LookupValueInput) -> None:
        record.name = values.name
        record.description = values.description
        record.relationship_directionality = (
            values.relationship_directionality.value
            if values.relationship_directionality is not None
            else None
        )

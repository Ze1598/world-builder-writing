"""Persistence operations for universes."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from world_builder.domain.models import UniverseInput
from world_builder.persistence.models import Universe


class UniverseRepository:
    """Query and mutate universe records within an existing transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Universe]:
        """Return all universes ordered case-insensitively by name."""
        statement = select(Universe).order_by(func.lower(Universe.name), Universe.id)
        return list(self._session.scalars(statement))

    def get(self, universe_id: str) -> Universe | None:
        """Return one universe by primary key."""
        return self._session.get(Universe, universe_id)

    def name_exists(self, name: str, *, excluding_id: str | None = None) -> bool:
        """Return whether a case-insensitive universe name is already used."""
        statement = select(Universe.id).where(func.lower(Universe.name) == name.casefold())
        if excluding_id is not None:
            statement = statement.where(Universe.id != excluding_id)
        return self._session.scalar(statement) is not None

    def create(self, values: UniverseInput) -> Universe:
        """Add a new universe record to the current transaction."""
        record = Universe(name=values.name, description=values.description)
        self._session.add(record)
        return record

    def update(self, record: Universe, values: UniverseInput) -> None:
        """Apply editable fields to an existing record."""
        record.name = values.name
        record.description = values.description

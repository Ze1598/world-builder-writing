"""Universe application service."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateNameError, RecordNotFoundError
from world_builder.domain.models import UniverseInput, UniverseView
from world_builder.persistence.database import database_session
from world_builder.persistence.repositories.universes import UniverseRepository


class UniverseService:
    """Coordinate validated universe operations and transaction boundaries."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_universes(self) -> list[UniverseView]:
        """Return every universe in display order."""
        with database_session(self._session_factory) as session:
            records = UniverseRepository(session).list_all()
            return [UniverseView.model_validate(record) for record in records]

    def get_universe(self, universe_id: str) -> UniverseView | None:
        """Return a universe by identifier when it exists."""
        with database_session(self._session_factory) as session:
            record = UniverseRepository(session).get(universe_id)
            return UniverseView.model_validate(record) if record is not None else None

    def create_universe(self, values: UniverseInput) -> UniverseView:
        """Create and return a universe with a case-insensitively unique name."""
        try:
            with database_session(self._session_factory) as session:
                repository = UniverseRepository(session)
                if repository.name_exists(values.name):
                    raise DuplicateNameError(f'A universe named "{values.name}" already exists.')
                record = repository.create(values)
                session.flush()
                return UniverseView.model_validate(record)
        except IntegrityError as error:
            raise DuplicateNameError(f'A universe named "{values.name}" already exists.') from error

    def update_universe(self, universe_id: str, values: UniverseInput) -> UniverseView:
        """Update and return an existing universe."""
        try:
            with database_session(self._session_factory) as session:
                repository = UniverseRepository(session)
                record = repository.get(universe_id)
                if record is None:
                    raise RecordNotFoundError("The selected universe no longer exists.")
                if repository.name_exists(values.name, excluding_id=universe_id):
                    raise DuplicateNameError(f'A universe named "{values.name}" already exists.')
                repository.update(record, values)
                session.flush()
                return UniverseView.model_validate(record)
        except IntegrityError as error:
            raise DuplicateNameError(f'A universe named "{values.name}" already exists.') from error

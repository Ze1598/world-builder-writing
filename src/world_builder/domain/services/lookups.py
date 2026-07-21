"""Managed lookup application service."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateNameError, RecordNotFoundError
from world_builder.domain.lookups import (
    LOOKUP_DEFINITIONS,
    LOOKUP_DEFINITIONS_BY_CODE,
    RELATIONSHIP_TYPE,
)
from world_builder.domain.models import LookupCategoryView, LookupValueInput, LookupValueView
from world_builder.persistence.database import database_session
from world_builder.persistence.models import LookupCategory, LookupValue
from world_builder.persistence.repositories.lookups import LookupRepository
from world_builder.persistence.repositories.universes import UniverseRepository


class LookupService:
    """Manage universe-scoped vocabulary and its stable category definitions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ensure_defaults(self, universe_id: str) -> None:
        """Idempotently provision categories and editable defaults for one universe."""
        with database_session(self._session_factory) as session:
            if UniverseRepository(session).get(universe_id) is None:
                raise RecordNotFoundError("The selected universe no longer exists.")
            repository = LookupRepository(session)
            for definition in LOOKUP_DEFINITIONS:
                category = repository.get_category(definition.code)
                if category is None:
                    category = repository.create_category(
                        definition.code, definition.name, definition.description
                    )
                    session.flush()
                existing = repository.list_values(universe_id, category.id)
                if existing:
                    continue
                for display_order, (name, directionality) in enumerate(definition.defaults):
                    repository.create_value(
                        universe_id,
                        category.id,
                        LookupValueInput(
                            name=name,
                            relationship_directionality=directionality,
                        ),
                        display_order,
                    )

    def list_categories(self) -> list[LookupCategoryView]:
        with database_session(self._session_factory) as session:
            repository = LookupRepository(session)
            categories = []
            for definition in LOOKUP_DEFINITIONS:
                category = repository.get_category(definition.code)
                if category is not None:
                    categories.append(LookupCategoryView.model_validate(category))
            return categories

    def list_values(
        self, universe_id: str, category_code: str, *, active_only: bool = False
    ) -> list[LookupValueView]:
        with database_session(self._session_factory) as session:
            repository = LookupRepository(session)
            category = self._require_category(repository, category_code)
            return [
                LookupValueView.model_validate(record)
                for record in repository.list_values(
                    universe_id, category.id, active_only=active_only
                )
            ]

    def create_value(
        self, universe_id: str, category_code: str, values: LookupValueInput
    ) -> LookupValueView:
        self._validate_directionality(category_code, values)
        try:
            with database_session(self._session_factory) as session:
                repository = LookupRepository(session)
                category = self._require_category(repository, category_code)
                if repository.name_exists(universe_id, category.id, values.name):
                    raise DuplicateNameError(
                        f'A lookup value named "{values.name}" already exists.'
                    )
                display_order = len(repository.list_values(universe_id, category.id))
                record = repository.create_value(universe_id, category.id, values, display_order)
                session.flush()
                return LookupValueView.model_validate(record)
        except IntegrityError as error:
            raise DuplicateNameError(
                f'A lookup value named "{values.name}" already exists.'
            ) from error

    def update_value(self, value_id: str, values: LookupValueInput) -> LookupValueView:
        try:
            with database_session(self._session_factory) as session:
                repository = LookupRepository(session)
                record = self._require_value(repository, value_id)
                category = record.category
                self._validate_directionality(category.code, values)
                if repository.name_exists(
                    record.universe_id,
                    record.category_id,
                    values.name,
                    excluding_id=value_id,
                ):
                    raise DuplicateNameError(
                        f'A lookup value named "{values.name}" already exists.'
                    )
                repository.update_value(record, values)
                session.flush()
                return LookupValueView.model_validate(record)
        except IntegrityError as error:
            raise DuplicateNameError(
                f'A lookup value named "{values.name}" already exists.'
            ) from error

    def set_active(self, value_id: str, *, is_active: bool) -> LookupValueView:
        with database_session(self._session_factory) as session:
            record = self._require_value(LookupRepository(session), value_id)
            record.is_active = is_active
            session.flush()
            return LookupValueView.model_validate(record)

    @staticmethod
    def _require_category(repository: LookupRepository, code: str) -> LookupCategory:
        if code not in LOOKUP_DEFINITIONS_BY_CODE:
            raise RecordNotFoundError("The selected lookup category does not exist.")
        category = repository.get_category(code)
        if category is None:
            raise RecordNotFoundError("The selected lookup category does not exist.")
        return category

    @staticmethod
    def _require_value(repository: LookupRepository, value_id: str) -> LookupValue:
        record = repository.get_value(value_id)
        if record is None:
            raise RecordNotFoundError("The selected lookup value no longer exists.")
        return record

    @staticmethod
    def _validate_directionality(category_code: str, values: LookupValueInput) -> None:
        if category_code == RELATIONSHIP_TYPE:
            if values.relationship_directionality is None:
                raise ValueError("Relationship types require directionality.")
        elif values.relationship_directionality is not None:
            raise ValueError("Only relationship types can define directionality.")

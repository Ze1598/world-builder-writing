"""Current character relationship workflows."""

from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import RecordNotFoundError
from world_builder.domain.lookups import RELATIONSHIP_TYPE
from world_builder.domain.models import (
    CharacterRelationshipInput,
    CharacterRelationshipView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    Character,
    CharacterRelationship,
    LookupValue,
    RelationshipDirectionality,
)
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.lookups import LookupRepository
from world_builder.persistence.repositories.relationships import (
    CharacterRelationshipRepository,
)


class CharacterRelationshipService:
    """Manage one current relationship per unordered character pair."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_for_character(self, character_id: str) -> list[CharacterRelationshipView]:
        with database_session(self._session_factory) as session:
            self._require_character(CharacterRepository(session), character_id)
            records = CharacterRelationshipRepository(session).list_for_character(character_id)
            return [self._view(record) for record in records]

    def create_relationship(self, values: CharacterRelationshipInput) -> CharacterRelationshipView:
        try:
            with database_session(self._session_factory) as session:
                first, second, relationship_type, source_id = self._validate_values(session, values)
                record = CharacterRelationshipRepository(session).create(
                    relationship_id=str(uuid4()),
                    universe_id=first.universe_id or "",
                    first_character_id=first.id,
                    second_character_id=second.id,
                    relationship_type_id=relationship_type.id,
                    source_character_id=source_id,
                    description=values.description,
                )
                session.flush()
                session.refresh(record)
                return self._view(record)
        except IntegrityError as error:
            raise ValueError("A relationship already exists between these characters.") from error

    def update_relationship(
        self,
        relationship_id: str,
        values: CharacterRelationshipInput,
    ) -> CharacterRelationshipView:
        try:
            with database_session(self._session_factory) as session:
                repository = CharacterRelationshipRepository(session)
                record = repository.get(relationship_id)
                if record is None:
                    raise RecordNotFoundError("The selected relationship no longer exists.")
                first, second, relationship_type, source_id = self._validate_values(session, values)
                record.universe_id = first.universe_id or ""
                record.first_character_id = first.id
                record.second_character_id = second.id
                record.relationship_type_id = relationship_type.id
                record.source_character_id = source_id
                record.description = values.description
                session.flush()
                session.expire(record)
                return self._view(record)
        except IntegrityError as error:
            raise ValueError("A relationship already exists between these characters.") from error

    def delete_relationship(self, relationship_id: str) -> None:
        with database_session(self._session_factory) as session:
            if not CharacterRelationshipRepository(session).delete(relationship_id):
                raise RecordNotFoundError("The selected relationship no longer exists.")

    def _validate_values(
        self,
        session: Session,
        values: CharacterRelationshipInput,
    ) -> tuple[Character, Character, LookupValue, str | None]:
        if values.first_character_id == values.second_character_id:
            raise ValueError("A character cannot have a relationship with themselves.")
        character_repository = CharacterRepository(session)
        characters = (
            self._require_character(character_repository, values.first_character_id),
            self._require_character(character_repository, values.second_character_id),
        )
        if characters[0].universe_id is None or characters[1].universe_id is None:
            raise ValueError("Relationships require two characters in a universe.")
        if characters[0].universe_id != characters[1].universe_id:
            raise ValueError("Relationships cannot cross universe boundaries.")
        first, second = sorted(characters, key=lambda character: character.id)

        lookup_repository = LookupRepository(session)
        relationship_type = lookup_repository.get_value(values.relationship_type_id)
        category = lookup_repository.get_category(RELATIONSHIP_TYPE)
        if (
            relationship_type is None
            or category is None
            or relationship_type.category_id != category.id
            or relationship_type.universe_id != first.universe_id
        ):
            raise ValueError("Select a relationship type from this universe.")
        if not relationship_type.is_active:
            raise ValueError("The selected relationship type is disabled.")

        if relationship_type.relationship_directionality is None:
            raise ValueError("The selected relationship type has no directionality.")
        directionality = RelationshipDirectionality(relationship_type.relationship_directionality)
        source_id = values.source_character_id
        if directionality is RelationshipDirectionality.SYMMETRIC:
            source_id = None
        elif source_id not in {first.id, second.id}:
            raise ValueError("Select which character initiates this relationship.")
        return first, second, relationship_type, source_id

    @staticmethod
    def _require_character(repository: CharacterRepository, character_id: str) -> Character:
        record = repository.get(character_id)
        if record is None:
            raise RecordNotFoundError("The selected character no longer exists.")
        return record

    @staticmethod
    def _view(record: CharacterRelationship) -> CharacterRelationshipView:
        if record.relationship_type.relationship_directionality is None:
            raise ValueError("The selected relationship type has no directionality.")
        directionality = RelationshipDirectionality(
            record.relationship_type.relationship_directionality
        )
        return CharacterRelationshipView(
            id=record.id,
            universe_id=record.universe_id,
            first_character_id=record.first_character_id,
            first_character_name=record.first_character.name,
            second_character_id=record.second_character_id,
            second_character_name=record.second_character.name,
            relationship_type_id=record.relationship_type_id,
            relationship_type_name=record.relationship_type.name,
            directionality=directionality,
            source_character_id=record.source_character_id,
            source_character_name=(
                record.source_character.name if record.source_character is not None else None
            ),
            description=record.description,
        )

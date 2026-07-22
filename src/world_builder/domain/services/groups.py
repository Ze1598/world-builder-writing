"""Character group profiles, artwork, and current membership workflows."""

from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from world_builder.domain.errors import DuplicateMembershipError, RecordNotFoundError
from world_builder.domain.models import (
    ArtworkDetailsInput,
    ArtworkInput,
    ArtworkView,
    CharacterGroupInput,
    CharacterGroupView,
    GroupMembershipView,
)
from world_builder.persistence.database import database_session
from world_builder.persistence.models import (
    ArtworkOwnerKind,
    Character,
    CharacterGroup,
    GroupMembership,
)
from world_builder.persistence.repositories.artworks import ArtworkRepository
from world_builder.persistence.repositories.characters import CharacterRepository
from world_builder.persistence.repositories.groups import CharacterGroupRepository
from world_builder.persistence.repositories.memberships import GroupMembershipRepository
from world_builder.persistence.repositories.universes import UniverseRepository
from world_builder.storage.artwork import ArtworkStorage, StoredArtworkFile


class CharacterGroupService:
    """Manage universe-isolated groups, memberships, and owned artwork."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        storage: ArtworkStorage,
    ) -> None:
        self._session_factory = session_factory
        self.storage = storage

    def create_group(
        self,
        values: CharacterGroupInput,
        artwork: ArtworkDetailsInput | None = None,
        source: BinaryIO | None = None,
    ) -> CharacterGroupView:
        """Create a group, optionally with one atomically imported artwork."""
        if (artwork is None) != (source is None):
            raise ValueError("Artwork metadata and image must be supplied together.")
        group_id = str(uuid4())
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                self._require_universe(session, values.universe_id)
                record = CharacterGroupRepository(session).create(group_id, values)
                if artwork is not None and source is not None:
                    artwork_id = str(uuid4())
                    stored = self.storage.import_image(
                        source,
                        original_filename=artwork.original_filename,
                        artwork_id=artwork_id,
                        owner_kind=ArtworkOwnerKind.GROUP,
                        owner_id=group_id,
                        universe_id=values.universe_id,
                    )
                    ArtworkRepository(session).create(
                        artwork_id,
                        ArtworkInput(
                            owner_kind=ArtworkOwnerKind.GROUP,
                            owner_id=group_id,
                            universe_id=values.universe_id,
                            title=artwork.title,
                            description=artwork.description,
                            original_filename=artwork.original_filename,
                        ),
                        stored,
                    )
                session.flush()
                view = CharacterGroupView.model_validate(record)
            return view
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def list_for_universe(self, universe_id: str) -> list[CharacterGroupView]:
        with database_session(self._session_factory) as session:
            records = CharacterGroupRepository(session).list_for_universe(universe_id)
            return [CharacterGroupView.model_validate(record) for record in records]

    def get_group(self, group_id: str) -> CharacterGroupView | None:
        with database_session(self._session_factory) as session:
            record = CharacterGroupRepository(session).get(group_id)
            return CharacterGroupView.model_validate(record) if record is not None else None

    def update_group(self, group_id: str, values: CharacterGroupInput) -> CharacterGroupView:
        with database_session(self._session_factory) as session:
            repository = CharacterGroupRepository(session)
            record = self._require_group(repository, group_id)
            if values.universe_id != record.universe_id:
                raise ValueError("Character groups cannot move between universes.")
            repository.update(record, values)
            session.flush()
            return CharacterGroupView.model_validate(record)

    def list_artworks(self, group_id: str) -> list[ArtworkView]:
        with database_session(self._session_factory) as session:
            self._require_group(CharacterGroupRepository(session), group_id)
            records = ArtworkRepository(session).list_for_group(group_id)
            return [ArtworkView.model_validate(record) for record in records]

    def add_artwork(
        self,
        group_id: str,
        artwork: ArtworkDetailsInput,
        source: BinaryIO,
    ) -> ArtworkView:
        artwork_id = str(uuid4())
        stored: StoredArtworkFile | None = None
        try:
            with database_session(self._session_factory) as session:
                group = self._require_group(CharacterGroupRepository(session), group_id)
                stored = self.storage.import_image(
                    source,
                    original_filename=artwork.original_filename,
                    artwork_id=artwork_id,
                    owner_kind=ArtworkOwnerKind.GROUP,
                    owner_id=group_id,
                    universe_id=group.universe_id,
                )
                record = ArtworkRepository(session).create(
                    artwork_id,
                    ArtworkInput(
                        owner_kind=ArtworkOwnerKind.GROUP,
                        owner_id=group_id,
                        universe_id=group.universe_id,
                        title=artwork.title,
                        description=artwork.description,
                        original_filename=artwork.original_filename,
                    ),
                    stored,
                )
                session.flush()
                view = ArtworkView.model_validate(record)
            return view
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise

    def list_memberships(self, group_id: str) -> list[GroupMembershipView]:
        with database_session(self._session_factory) as session:
            self._require_group(CharacterGroupRepository(session), group_id)
            records = GroupMembershipRepository(session).list_for_group(group_id)
            return [self._membership_view(record) for record in records]

    def add_membership(
        self, group_id: str, character_id: str, description: str = ""
    ) -> GroupMembershipView:
        with database_session(self._session_factory) as session:
            group = self._require_group(CharacterGroupRepository(session), group_id)
            character = self._require_character(CharacterRepository(session), character_id)
            self._require_same_universe(group, character)
            repository = GroupMembershipRepository(session)
            if repository.get_for_pair(group_id, character_id) is not None:
                raise DuplicateMembershipError(
                    "The selected character already belongs to this group."
                )
            record = repository.create(
                str(uuid4()),
                group_id=group_id,
                character_id=character_id,
                description=description.strip(),
            )
            session.flush()
            record.character = character
            return self._membership_view(record)

    def update_membership(self, membership_id: str, description: str) -> None:
        with database_session(self._session_factory) as session:
            repository = GroupMembershipRepository(session)
            record = repository.get(membership_id)
            if record is None:
                raise RecordNotFoundError("The selected membership no longer exists.")
            repository.update(record, description.strip())

    def remove_membership(self, membership_id: str) -> None:
        with database_session(self._session_factory) as session:
            repository = GroupMembershipRepository(session)
            record = repository.get(membership_id)
            if record is None:
                raise RecordNotFoundError("The selected membership no longer exists.")
            repository.delete(record)

    @staticmethod
    def _membership_view(membership: GroupMembership) -> GroupMembershipView:
        return GroupMembershipView(
            id=membership.id,
            group_id=membership.group_id,
            character_id=membership.character_id,
            character_name=membership.character.name,
            character_is_active=membership.character.is_active,
            description=membership.description,
        )

    @staticmethod
    def _require_group(repository: CharacterGroupRepository, group_id: str) -> CharacterGroup:
        record = repository.get(group_id)
        if record is None:
            raise RecordNotFoundError("The selected character group no longer exists.")
        return record

    @staticmethod
    def _require_character(repository: CharacterRepository, character_id: str) -> Character:
        record = repository.get(character_id)
        if record is None:
            raise RecordNotFoundError("The selected character no longer exists.")
        return record

    @staticmethod
    def _require_universe(session: Session, universe_id: str) -> None:
        if UniverseRepository(session).get(universe_id) is None:
            raise RecordNotFoundError("The selected universe no longer exists.")

    @staticmethod
    def _require_same_universe(group: CharacterGroup, character: Character) -> None:
        if character.universe_id is None or character.universe_id != group.universe_id:
            raise ValueError("A group can only include characters from its universe.")

"""Framework-independent input and view models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from world_builder.persistence.models import ArtworkOwnerKind, RelationshipDirectionality


class UniverseInput(BaseModel):
    """Validated fields accepted when creating or editing a universe."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    description: str = ""

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Remove accidental surrounding whitespace from text input."""
        return value.strip() if isinstance(value, str) else value


class UniverseView(BaseModel):
    """Read-only representation of a universe."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        """Restore UTC metadata omitted by SQLite's datetime representation."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class LookupCategoryView(BaseModel):
    """Read-only definition of one managed vocabulary category."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    code: str
    name: str
    description: str


class LookupValueInput(BaseModel):
    """Validated editable fields for a managed lookup value."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    relationship_directionality: RelationshipDirectionality | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_lookup_text(cls, value: object) -> object:
        """Remove accidental surrounding whitespace from text input."""
        return value.strip() if isinstance(value, str) else value


class LookupValueView(BaseModel):
    """Read-only representation of a universe-scoped lookup value."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    universe_id: str
    category_id: str
    name: str
    description: str
    display_order: int
    is_active: bool
    relationship_directionality: RelationshipDirectionality | None


class ArtworkInput(BaseModel):
    """Validated metadata used while importing an artwork file."""

    model_config = ConfigDict(frozen=True)

    owner_kind: ArtworkOwnerKind
    owner_id: str
    universe_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    original_filename: str = Field(min_length=1, max_length=255)
    is_primary: bool = False

    @field_validator("owner_id")
    @classmethod
    def validate_owner_identifier(cls, value: str) -> str:
        """Require a canonical GUID owner identifier."""
        from uuid import UUID

        return str(UUID(value))

    @field_validator("universe_id")
    @classmethod
    def validate_universe_identifier(cls, value: str | None) -> str | None:
        """Require a canonical GUID universe identifier when assigned."""
        if value is None:
            return None
        from uuid import UUID

        return str(UUID(value))

    @field_validator("title", "description", "original_filename", mode="before")
    @classmethod
    def strip_artwork_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_owner_location(self) -> "ArtworkInput":
        if self.owner_kind is ArtworkOwnerKind.GROUP and self.universe_id is None:
            raise ValueError("Group artwork requires an assigned universe.")
        if self.owner_kind is ArtworkOwnerKind.GROUP and self.is_primary:
            raise ValueError("Only character artwork can be primary.")
        return self


class ArtworkView(BaseModel):
    """Read-only artwork metadata returned after a successful import."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    universe_id: str | None
    owner_kind: ArtworkOwnerKind
    owner_id: str
    title: str
    description: str
    original_filename: str
    mime_type: str
    relative_path: str
    file_size: int
    is_primary: bool


class CharacterInput(BaseModel):
    """Validated fields accepted while creating or editing a character."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1)
    universe_id: str | None = None

    @field_validator("name", "summary", mode="before")
    @classmethod
    def strip_character_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("universe_id")
    @classmethod
    def validate_character_universe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from uuid import UUID

        return str(UUID(value))


class CharacterView(BaseModel):
    """Read-only character profile fields."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    universe_id: str | None
    name: str
    summary: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_character_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class CharacterMovePreflight(BaseModel):
    """Read-only report of what a character location change will affect."""

    model_config = ConfigDict(frozen=True)

    character_id: str
    source_universe_id: str | None
    target_universe_id: str | None
    artwork_count: int
    disables_character: bool = False
    relationship_count: int = 0
    membership_count: int = 0
    story_link_count: int = 0
    chapter_link_count: int = 0
    milestone_link_count: int = 0

    @property
    def requires_confirmation(self) -> bool:
        """Return whether the move leaves an existing universe."""
        return self.source_universe_id is not None

    @property
    def detached_connection_count(self) -> int:
        """Return the number of non-artwork connections to remove."""
        return (
            self.relationship_count
            + self.membership_count
            + self.story_link_count
            + self.chapter_link_count
            + self.milestone_link_count
        )


class CharacterMoveResult(BaseModel):
    """Completed character move and any non-blocking filesystem cleanup warning."""

    model_config = ConfigDict(frozen=True)

    character: CharacterView
    cleanup_warning: str | None = None


class CharacterGroupInput(BaseModel):
    """Validated editable fields for a universe-owned character group."""

    model_config = ConfigDict(frozen=True)

    universe_id: str
    name: str = Field(min_length=1, max_length=200)
    description: str = ""

    @field_validator("universe_id")
    @classmethod
    def validate_group_universe(cls, value: str) -> str:
        from uuid import UUID

        return str(UUID(value))

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_group_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CharacterGroupView(BaseModel):
    """Read-only character group profile fields."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: str
    universe_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_group_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class GroupMembershipView(BaseModel):
    """Read-only membership enriched with its character display fields."""

    model_config = ConfigDict(frozen=True)

    id: str
    group_id: str
    character_id: str
    character_name: str
    character_is_active: bool
    description: str


class ArtworkDetailsInput(BaseModel):
    """Validated user-authored metadata for a character artwork upload."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    original_filename: str = Field(min_length=1, max_length=255)

    @field_validator("title", "description", "original_filename", mode="before")
    @classmethod
    def strip_artwork_details(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

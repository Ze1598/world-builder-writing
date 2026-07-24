"""Framework-independent input and view models."""

from datetime import UTC, datetime
from enum import StrEnum

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

    owner_kind: ArtworkOwnerKind | None = None
    owner_id: str | None = None
    universe_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    original_filename: str = Field(min_length=1, max_length=255)
    is_primary: bool = False

    @field_validator("owner_id")
    @classmethod
    def validate_owner_identifier(cls, value: str | None) -> str | None:
        """Require a canonical GUID owner identifier."""
        if value is None:
            return None
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
        if (self.owner_kind is None) != (self.owner_id is None):
            raise ValueError("Artwork owner type and identifier must be supplied together.")
        if self.owner_kind is None:
            if self.universe_id is not None or self.is_primary:
                raise ValueError("Unassigned artwork must be global and non-primary.")
            return self
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
    owner_kind: ArtworkOwnerKind | None
    owner_id: str | None
    title: str
    description: str
    original_filename: str
    mime_type: str
    relative_path: str
    file_size: int
    is_primary: bool


class ArtworkEntityKind(StrEnum):
    """Entity types that can use an artwork without owning it."""

    CHARACTER = "character"
    GROUP = "group"
    CHAPTER = "chapter"
    STORY = "story"


class ArtworkUsageView(BaseModel):
    """One display-ready usage association for an artwork."""

    model_config = ConfigDict(frozen=True)

    entity_kind: ArtworkEntityKind
    entity_id: str
    entity_name: str
    universe_id: str


class ArtworkDetailView(BaseModel):
    """Artwork metadata enriched with ownership and every usage."""

    model_config = ConfigDict(frozen=True)

    artwork: ArtworkView
    owner_name: str | None
    usages: tuple[ArtworkUsageView, ...]


class ArtworkMovePreflight(BaseModel):
    """Report of ownership transfer effects before files or links change."""

    model_config = ConfigDict(frozen=True)

    artwork_id: str
    source_owner_kind: ArtworkOwnerKind | None
    source_owner_id: str | None
    target_owner_kind: ArtworkOwnerKind | None
    target_owner_id: str | None
    source_universe_id: str | None
    target_universe_id: str | None
    incompatible_usage_count: int

    @property
    def requires_confirmation(self) -> bool:
        return self.incompatible_usage_count > 0


class ArtworkMutationResult(BaseModel):
    """Completed artwork mutation and any filesystem cleanup warning."""

    model_config = ConfigDict(frozen=True)

    artwork: ArtworkView | None = None
    cleanup_warning: str | None = None


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


class CharacterRelationshipInput(BaseModel):
    """Validated fields for one current relationship between two characters."""

    model_config = ConfigDict(frozen=True)

    first_character_id: str
    second_character_id: str
    relationship_type_id: str
    source_character_id: str | None = None
    description: str = ""

    @field_validator(
        "first_character_id",
        "second_character_id",
        "relationship_type_id",
        "source_character_id",
    )
    @classmethod
    def validate_relationship_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from uuid import UUID

        return str(UUID(value))

    @field_validator("description", mode="before")
    @classmethod
    def strip_relationship_description(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CharacterRelationshipView(BaseModel):
    """Display-ready current relationship edge."""

    model_config = ConfigDict(frozen=True)

    id: str
    universe_id: str
    first_character_id: str
    first_character_name: str
    second_character_id: str
    second_character_name: str
    relationship_type_id: str
    relationship_type_name: str
    directionality: RelationshipDirectionality
    source_character_id: str | None
    source_character_name: str | None
    description: str


class CharacterMovePreflight(BaseModel):
    """Read-only report of what a character location change will affect."""

    model_config = ConfigDict(frozen=True)

    character_id: str
    source_universe_id: str | None
    target_universe_id: str | None
    artwork_count: int
    artwork_association_count: int = 0
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


class MilestoneInput(BaseModel):
    """Validated fields for one universe-scoped planning idea."""

    model_config = ConfigDict(frozen=True)

    universe_id: str
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    character_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()
    chapter_ids: tuple[str, ...] = ()
    story_ids: tuple[str, ...] = ()

    @field_validator("universe_id")
    @classmethod
    def validate_milestone_universe(cls, value: str) -> str:
        from uuid import UUID

        return str(UUID(value))

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_milestone_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MilestoneView(BaseModel):
    """Read-only planning idea with display-ready reverse links."""

    model_config = ConfigDict(frozen=True)

    id: str
    universe_id: str
    title: str
    content: str
    character_ids: tuple[str, ...]
    character_names: tuple[str, ...]
    group_ids: tuple[str, ...]
    group_names: tuple[str, ...]
    chapter_ids: tuple[str, ...]
    chapter_titles: tuple[str, ...]
    story_ids: tuple[str, ...]
    story_titles: tuple[str, ...]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_milestone_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @property
    def is_unlinked(self) -> bool:
        return not (self.character_ids or self.group_ids or self.chapter_ids or self.story_ids)


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


class ChapterInput(BaseModel):
    """Validated editable chapter content and universe-scoped links."""

    model_config = ConfigDict(frozen=True)

    universe_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    character_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()

    @field_validator("universe_id")
    @classmethod
    def validate_chapter_universe(cls, value: str) -> str:
        from uuid import UUID

        return str(UUID(value))

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_chapter_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ChapterView(BaseModel):
    """Read-only chapter profile with linked entity display values."""

    model_config = ConfigDict(frozen=True)

    id: str
    universe_id: str
    title: str
    description: str
    sequence_position: int
    character_ids: tuple[str, ...]
    character_names: tuple[str, ...]
    group_ids: tuple[str, ...]
    group_names: tuple[str, ...]


class StoryInput(BaseModel):
    """Validated story content and universe-scoped associations."""

    model_config = ConfigDict(frozen=True)

    universe_id: str
    chapter_id: str
    title: str = Field(min_length=1, max_length=200)
    content: str = ""
    character_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()
    artwork_ids: tuple[str, ...] = ()

    @field_validator("universe_id", "chapter_id")
    @classmethod
    def validate_story_identifier(cls, value: str) -> str:
        from uuid import UUID

        return str(UUID(value))

    @field_validator("title", mode="before")
    @classmethod
    def strip_story_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class StoryView(BaseModel):
    """Read-only story with display-ready association data."""

    model_config = ConfigDict(frozen=True)

    id: str
    universe_id: str
    chapter_id: str
    chapter_title: str
    title: str
    content: str
    character_ids: tuple[str, ...]
    character_names: tuple[str, ...]
    group_ids: tuple[str, ...]
    group_names: tuple[str, ...]
    artwork_ids: tuple[str, ...]
    artwork_titles: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


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

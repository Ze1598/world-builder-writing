"""Framework-independent input and view models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from world_builder.persistence.models import RelationshipDirectionality


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

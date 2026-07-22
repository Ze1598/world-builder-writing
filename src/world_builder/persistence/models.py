"""SQLAlchemy mappings for durable World Builder records."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

IDENTIFIER_LENGTH: Final = 36


def new_identifier() -> str:
    """Return a portable string representation of a UUID4 identifier."""
    return str(uuid4())


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


class RelationshipDirectionality(StrEnum):
    """Supported relationship edge behavior."""

    SYMMETRIC = "symmetric"
    DIRECTIONAL = "directional"


class ArtworkOwnerKind(StrEnum):
    """Entity types that can physically own an artwork file."""

    CHARACTER = "character"
    GROUP = "group"


class Base(DeclarativeBase):
    """Base for all SQLAlchemy mappings."""


class TimestampMixin:
    """Creation and modification timestamps shared by durable records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Universe(TimestampMixin, Base):
    """Top-level isolation boundary for fictional content."""

    __tablename__ = "universes"

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    lookup_values: Mapped[list["LookupValue"]] = relationship(
        back_populates="universe",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    artworks: Mapped[list["Artwork"]] = relationship(back_populates="universe")
    characters: Mapped[list["Character"]] = relationship(back_populates="universe")
    character_groups: Mapped[list["CharacterGroup"]] = relationship(
        back_populates="universe",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Character(TimestampMixin, Base):
    """A fictional character assigned to a universe or held unassigned."""

    __tablename__ = "characters"
    __table_args__ = (Index("ix_characters_universe_id", "universe_id"),)

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    universe_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("universes.id", ondelete="RESTRICT"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    universe: Mapped[Universe | None] = relationship(back_populates="characters")
    group_memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CharacterGroup(TimestampMixin, Base):
    """A current collection of characters within one universe."""

    __tablename__ = "character_groups"
    __table_args__ = (Index("ix_character_groups_universe_id", "universe_id"),)

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    universe_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("universes.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    universe: Mapped[Universe] = relationship(back_populates="character_groups")
    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GroupMembership(TimestampMixin, Base):
    """A character's current membership and optional Markdown context."""

    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "character_id",
            name="uq_group_membership_group_character",
        ),
        Index("ix_group_memberships_group_id", "group_id"),
        Index("ix_group_memberships_character_id", "character_id"),
    )

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    group_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("character_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    character_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    group: Mapped[CharacterGroup] = relationship(back_populates="memberships")
    character: Mapped[Character] = relationship(back_populates="group_memberships")


class LookupCategory(TimestampMixin, Base):
    """Global definition of a user-managed vocabulary category."""

    __tablename__ = "lookup_categories"

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    values: Mapped[list["LookupValue"]] = relationship(back_populates="category")


class LookupValue(TimestampMixin, Base):
    """Universe-specific value within a managed vocabulary category."""

    __tablename__ = "lookup_values"
    __table_args__ = (
        UniqueConstraint(
            "universe_id",
            "category_id",
            "name",
            name="uq_lookup_value_name_per_universe_category",
        ),
        CheckConstraint(
            "relationship_directionality IS NULL OR "
            "relationship_directionality IN ('symmetric', 'directional')",
            name="valid_relationship_directionality",
        ),
        Index("ix_lookup_values_universe_id", "universe_id"),
        Index("ix_lookup_values_category_id", "category_id"),
    )

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    universe_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("universes.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("lookup_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    relationship_directionality: Mapped[str | None] = mapped_column(String(16))

    universe: Mapped[Universe] = relationship(back_populates="lookup_values")
    category: Mapped[LookupCategory] = relationship(back_populates="values")


class Artwork(TimestampMixin, Base):
    """Metadata for an image stored in the managed artwork filesystem."""

    __tablename__ = "artworks"
    __table_args__ = (
        CheckConstraint(
            "owner_kind IN ('character', 'group')",
            name="valid_artwork_owner_kind",
        ),
        CheckConstraint(
            "owner_kind = 'character' OR universe_id IS NOT NULL",
            name="group_artwork_requires_universe",
        ),
        UniqueConstraint("relative_path", name="uq_artworks_relative_path"),
        Index("ix_artworks_universe_id", "universe_id"),
        Index("ix_artworks_owner", "owner_kind", "owner_id"),
        Index(
            "uq_artworks_primary_character",
            "owner_id",
            unique=True,
            sqlite_where=text("owner_kind = 'character' AND is_primary = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(IDENTIFIER_LENGTH),
        primary_key=True,
        default=new_identifier,
    )
    universe_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH),
        ForeignKey("universes.id", ondelete="RESTRICT"),
    )
    owner_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    universe: Mapped[Universe | None] = relationship(back_populates="artworks")

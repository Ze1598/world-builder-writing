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

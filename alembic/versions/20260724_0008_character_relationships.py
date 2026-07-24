"""Add current character relationships.

Revision ID: 20260724_0008
Revises: 20260724_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0008"
down_revision: str | None = "20260724_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the canonical current-relationship edge table."""
    op.create_table(
        "character_relationships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=False),
        sa.Column("first_character_id", sa.String(length=36), nullable=False),
        sa.Column("second_character_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_type_id", sa.String(length=36), nullable=False),
        sa.Column("source_character_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "first_character_id < second_character_id",
            name="canonical_character_relationship_pair",
        ),
        sa.CheckConstraint(
            "source_character_id IS NULL OR "
            "source_character_id = first_character_id OR "
            "source_character_id = second_character_id",
            name="valid_character_relationship_source",
        ),
        sa.ForeignKeyConstraint(
            ["first_character_id"],
            ["characters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["relationship_type_id"],
            ["lookup_values.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["second_character_id"],
            ["characters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_character_id"],
            ["characters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["universe_id"],
            ["universes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "first_character_id",
            "second_character_id",
            name="uq_character_relationship_pair",
        ),
    )
    op.create_index(
        "ix_character_relationships_universe_id",
        "character_relationships",
        ["universe_id"],
    )
    op.create_index(
        "ix_character_relationships_first_character_id",
        "character_relationships",
        ["first_character_id"],
    )
    op.create_index(
        "ix_character_relationships_second_character_id",
        "character_relationships",
        ["second_character_id"],
    )
    op.create_index(
        "ix_character_relationships_type_id",
        "character_relationships",
        ["relationship_type_id"],
    )


def downgrade() -> None:
    """Remove current character relationships."""
    op.drop_index(
        "ix_character_relationships_type_id",
        table_name="character_relationships",
    )
    op.drop_index(
        "ix_character_relationships_second_character_id",
        table_name="character_relationships",
    )
    op.drop_index(
        "ix_character_relationships_first_character_id",
        table_name="character_relationships",
    )
    op.drop_index(
        "ix_character_relationships_universe_id",
        table_name="character_relationships",
    )
    op.drop_table("character_relationships")

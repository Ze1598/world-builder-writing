"""Add character profiles and primary artwork constraint.

Revision ID: 20260721_0003
Revises: 20260721_0002
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create character records and enforce at most one primary artwork."""
    op.create_table(
        "characters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["universe_id"],
            ["universes.id"],
            name=op.f("fk_characters_universe_id_universes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_characters")),
    )
    op.create_index(
        op.f("ix_characters_universe_id"),
        "characters",
        ["universe_id"],
    )
    op.create_index(
        "uq_artworks_primary_character",
        "artworks",
        ["owner_id"],
        unique=True,
        sqlite_where=sa.text("owner_kind = 'character' AND is_primary = 1"),
    )


def downgrade() -> None:
    """Remove character records and their primary-artwork uniqueness index."""
    op.drop_index("uq_artworks_primary_character", table_name="artworks")
    op.drop_index(op.f("ix_characters_universe_id"), table_name="characters")
    op.drop_table("characters")

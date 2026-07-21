"""Add managed artwork metadata.

Revision ID: 20260721_0002
Revises: 20260721_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create artwork metadata without storing image bytes in SQLite."""
    op.create_table(
        "artworks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=True),
        sa.Column("owner_kind", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=False),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "owner_kind IN ('character', 'group')",
            name=op.f("ck_artworks_valid_artwork_owner_kind"),
        ),
        sa.CheckConstraint(
            "owner_kind = 'character' OR universe_id IS NOT NULL",
            name=op.f("ck_artworks_group_artwork_requires_universe"),
        ),
        sa.ForeignKeyConstraint(
            ["universe_id"],
            ["universes.id"],
            name=op.f("fk_artworks_universe_id_universes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artworks")),
        sa.UniqueConstraint("relative_path", name=op.f("uq_artworks_relative_path")),
    )
    op.create_index(op.f("ix_artworks_universe_id"), "artworks", ["universe_id"])
    op.create_index(
        op.f("ix_artworks_owner"),
        "artworks",
        ["owner_kind", "owner_id"],
    )


def downgrade() -> None:
    """Remove artwork metadata."""
    op.drop_index(op.f("ix_artworks_owner"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_universe_id"), table_name="artworks")
    op.drop_table("artworks")

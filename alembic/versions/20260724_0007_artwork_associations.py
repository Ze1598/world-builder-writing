"""Add reusable artwork associations.

Revision ID: 20260724_0007
Revises: 20260723_0006
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0007"
down_revision: str | None = "20260723_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create artwork links for characters, groups, and chapters."""
    op.create_table(
        "artwork_characters",
        sa.Column("artwork_id", sa.String(36), nullable=False),
        sa.Column("character_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artwork_id", "character_id"),
    )
    op.create_table(
        "artwork_groups",
        sa.Column("artwork_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["character_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artwork_id", "group_id"),
    )
    op.create_table(
        "artwork_chapters",
        sa.Column("artwork_id", sa.String(36), nullable=False),
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artwork_id", "chapter_id"),
    )


def downgrade() -> None:
    """Remove reusable artwork associations."""
    op.drop_table("artwork_chapters")
    op.drop_table("artwork_groups")
    op.drop_table("artwork_characters")

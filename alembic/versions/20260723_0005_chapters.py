"""Add sequenced chapters and universe-scoped links.

Revision ID: 20260723_0005
Revises: 20260722_0004
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260723_0005"
down_revision: str | None = "20260722_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chapters",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("universe_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sequence_position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["universe_id"], ["universes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chapters_universe_id", "chapters", ["universe_id"])
    op.create_index(
        "ix_chapters_universe_sequence",
        "chapters",
        ["universe_id", "sequence_position"],
    )
    op.create_table(
        "chapter_characters",
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.Column("character_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chapter_id", "character_id"),
    )
    op.create_table(
        "chapter_groups",
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["character_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chapter_id", "group_id"),
    )


def downgrade() -> None:
    op.drop_table("chapter_groups")
    op.drop_table("chapter_characters")
    op.drop_index("ix_chapters_universe_sequence", table_name="chapters")
    op.drop_index("ix_chapters_universe_id", table_name="chapters")
    op.drop_table("chapters")

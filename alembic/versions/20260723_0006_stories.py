"""Add stories, associations, and globally unassigned artwork.

Revision ID: 20260723_0006
Revises: 20260723_0005
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260723_0006"
down_revision: str | None = "20260723_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow ownerless artwork and add story records with associations."""
    with op.batch_alter_table("artworks") as batch:
        batch.drop_constraint(op.f("ck_artworks_valid_artwork_owner_kind"), type_="check")
        batch.drop_constraint(op.f("ck_artworks_group_artwork_requires_universe"), type_="check")
        batch.alter_column("owner_kind", existing_type=sa.String(16), nullable=True)
        batch.alter_column("owner_id", existing_type=sa.String(36), nullable=True)
        batch.create_check_constraint(
            op.f("ck_artworks_valid_artwork_owner_kind"),
            "owner_kind IS NULL OR owner_kind IN ('character', 'group')",
        )
        batch.create_check_constraint(
            op.f("ck_artworks_valid_artwork_ownership"),
            "(owner_kind IS NULL AND owner_id IS NULL AND universe_id IS NULL "
            "AND is_primary = 0) OR (owner_kind IS NOT NULL AND owner_id IS NOT NULL)",
        )

    op.create_table(
        "stories",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("universe_id", sa.String(36), nullable=False),
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["universe_id"], ["universes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stories_universe_id", "stories", ["universe_id"])
    op.create_index("ix_stories_chapter_id", "stories", ["chapter_id"])
    op.create_table(
        "story_characters",
        sa.Column("story_id", sa.String(36), nullable=False),
        sa.Column("character_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id", "character_id"),
    )
    op.create_table(
        "story_groups",
        sa.Column("story_id", sa.String(36), nullable=False),
        sa.Column("group_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["character_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id", "group_id"),
    )
    op.create_table(
        "story_artworks",
        sa.Column("story_id", sa.String(36), nullable=False),
        sa.Column("artwork_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("story_id", "artwork_id"),
    )


def downgrade() -> None:
    """Remove stories and restore mandatory artwork ownership."""
    op.drop_table("story_artworks")
    op.drop_table("story_groups")
    op.drop_table("story_characters")
    op.drop_index("ix_stories_chapter_id", table_name="stories")
    op.drop_index("ix_stories_universe_id", table_name="stories")
    op.drop_table("stories")
    with op.batch_alter_table("artworks") as batch:
        batch.drop_constraint(op.f("ck_artworks_valid_artwork_ownership"), type_="check")
        batch.drop_constraint(op.f("ck_artworks_valid_artwork_owner_kind"), type_="check")
        batch.alter_column("owner_kind", existing_type=sa.String(16), nullable=False)
        batch.alter_column("owner_id", existing_type=sa.String(36), nullable=False)
        batch.create_check_constraint(
            op.f("ck_artworks_valid_artwork_owner_kind"),
            "owner_kind IN ('character', 'group')",
        )
        batch.create_check_constraint(
            op.f("ck_artworks_group_artwork_requires_universe"),
            "owner_kind = 'character' OR universe_id IS NOT NULL",
        )

"""Add milestone idea inbox.

Revision ID: 20260724_0009
Revises: 20260724_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0009"
down_revision: str | None = "20260724_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create milestones and their four optional association tables."""
    op.create_table(
        "milestones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["universe_id"], ["universes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_universe_id", "milestones", ["universe_id"])
    association_specs = (
        ("milestone_characters", "character_id", "characters"),
        ("milestone_groups", "group_id", "character_groups"),
        ("milestone_chapters", "chapter_id", "chapters"),
        ("milestone_stories", "story_id", "stories"),
    )
    for table_name, entity_column, target_table in association_specs:
        op.create_table(
            table_name,
            sa.Column("milestone_id", sa.String(length=36), nullable=False),
            sa.Column(entity_column, sa.String(length=36), nullable=False),
            sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([entity_column], [f"{target_table}.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("milestone_id", entity_column),
        )


def downgrade() -> None:
    """Remove milestone ideas and links."""
    for table_name in (
        "milestone_stories",
        "milestone_chapters",
        "milestone_groups",
        "milestone_characters",
    ):
        op.drop_table(table_name)
    op.drop_index("ix_milestones_universe_id", table_name="milestones")
    op.drop_table("milestones")

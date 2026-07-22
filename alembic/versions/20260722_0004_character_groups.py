"""Add character groups and current memberships.

Revision ID: 20260722_0004
Revises: 20260721_0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260722_0004"
down_revision: str | None = "20260721_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create universe-owned groups and their current character memberships."""
    op.create_table(
        "character_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["universe_id"],
            ["universes.id"],
            name=op.f("fk_character_groups_universe_id_universes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_character_groups")),
    )
    op.create_index(
        op.f("ix_character_groups_universe_id"),
        "character_groups",
        ["universe_id"],
    )
    op.create_table(
        "group_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            name=op.f("fk_group_memberships_character_id_characters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["character_groups.id"],
            name=op.f("fk_group_memberships_group_id_character_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_group_memberships")),
        sa.UniqueConstraint(
            "group_id",
            "character_id",
            name=op.f("uq_group_membership_group_character"),
        ),
    )
    op.create_index(
        op.f("ix_group_memberships_character_id"),
        "group_memberships",
        ["character_id"],
    )
    op.create_index(
        op.f("ix_group_memberships_group_id"),
        "group_memberships",
        ["group_id"],
    )


def downgrade() -> None:
    """Remove current memberships and character groups."""
    op.drop_index(
        op.f("ix_group_memberships_group_id"),
        table_name="group_memberships",
    )
    op.drop_index(
        op.f("ix_group_memberships_character_id"),
        table_name="group_memberships",
    )
    op.drop_table("group_memberships")
    op.drop_index(
        op.f("ix_character_groups_universe_id"),
        table_name="character_groups",
    )
    op.drop_table("character_groups")

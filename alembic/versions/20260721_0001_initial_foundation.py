"""Create universes and managed lookup foundation.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the first durable World Builder tables."""
    op.create_table(
        "universes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_universes")),
        sa.UniqueConstraint("name", name=op.f("uq_universes_name")),
    )
    op.create_table(
        "lookup_categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lookup_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_lookup_categories_code")),
    )
    op.create_table(
        "lookup_values",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("universe_id", sa.String(length=36), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("relationship_directionality", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relationship_directionality IS NULL OR "
            "relationship_directionality IN ('symmetric', 'directional')",
            name=op.f("ck_lookup_values_valid_relationship_directionality"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["lookup_categories.id"],
            name=op.f("fk_lookup_values_category_id_lookup_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["universe_id"],
            ["universes.id"],
            name=op.f("fk_lookup_values_universe_id_universes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lookup_values")),
        sa.UniqueConstraint(
            "universe_id",
            "category_id",
            "name",
            name=op.f("uq_lookup_value_name_per_universe_category"),
        ),
    )
    op.create_index(
        op.f("ix_lookup_values_category_id"),
        "lookup_values",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lookup_values_universe_id"),
        "lookup_values",
        ["universe_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the first durable World Builder tables."""
    op.drop_index(op.f("ix_lookup_values_universe_id"), table_name="lookup_values")
    op.drop_index(op.f("ix_lookup_values_category_id"), table_name="lookup_values")
    op.drop_table("lookup_values")
    op.drop_table("lookup_categories")
    op.drop_table("universes")

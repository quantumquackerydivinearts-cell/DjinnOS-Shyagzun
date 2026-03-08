"""add distribution registry

Revision ID: 0018_add_distribution_registry
Revises: 0017_add_guild_registry
Create Date: 2026-03-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_add_distribution_registry"
down_revision = "0017_add_guild_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_registry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("distribution_id", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("base_url", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("transport_kind", sa.String(length=80), nullable=False, server_default="https"),
        sa.Column("public_key_ref", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("guild_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("distribution_id"),
    )


def downgrade() -> None:
    op.drop_table("distribution_registry")

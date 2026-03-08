"""add guild registry table

Revision ID: 0017_add_guild_registry
Revises: 0016_add_wand_spec_columns_compat
Create Date: 2026-03-08 19:10:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_add_guild_registry"
down_revision = "0016_add_wand_spec_columns_compat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guild_registry",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("guild_id", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("distribution_id", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("owner_artisan_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("owner_profile_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("owner_profile_email", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("member_profiles_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("charter_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("guild_id", name="uq_guild_registry_guild_id"),
    )
    op.create_index("ix_guild_registry_updated_at", "guild_registry", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_guild_registry_updated_at", table_name="guild_registry")
    op.drop_table("guild_registry")

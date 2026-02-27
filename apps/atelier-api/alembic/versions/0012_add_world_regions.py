"""add world regions table

Revision ID: 0012_add_world_regions
Revises: 0011_add_scene_library
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_add_world_regions"
down_revision = "0011_add_scene_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "world_regions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("realm_id", sa.String(length=80), nullable=False),
        sa.Column("region_key", sa.String(length=200), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("cache_policy", sa.String(length=40), nullable=False, server_default="cache"),
        sa.Column("loaded", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_world_regions_workspace_realm_region",
        "world_regions",
        ["workspace_id", "realm_id", "region_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_world_regions_workspace_realm_region", table_name="world_regions")
    op.drop_table("world_regions")

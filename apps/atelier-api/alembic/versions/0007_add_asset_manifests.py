"""add asset manifests table

Revision ID: 0007_add_asset_manifests
Revises: 0006_add_player_state
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_add_asset_manifests"
down_revision = "0006_add_player_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_manifests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("manifest_id", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("asset_manifests")

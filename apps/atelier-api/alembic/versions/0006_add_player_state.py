"""add player state tables

Revision ID: 0006_add_player_state
Revises: 0005_add_layered_lineage_store
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_add_player_state"
down_revision = "0005_add_layered_lineage_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, default=1),
        sa.Column("levels_json", sa.Text(), nullable=False),
        sa.Column("skills_json", sa.Text(), nullable=False),
        sa.Column("perks_json", sa.Text(), nullable=False),
        sa.Column("vitriol_json", sa.Text(), nullable=False),
        sa.Column("inventory_json", sa.Text(), nullable=False),
        sa.Column("market_json", sa.Text(), nullable=False),
        sa.Column("flags_json", sa.Text(), nullable=False),
        sa.Column("clock_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "actor_id", name="uq_player_states_workspace_actor"),
    )


def downgrade() -> None:
    op.drop_table("player_states")

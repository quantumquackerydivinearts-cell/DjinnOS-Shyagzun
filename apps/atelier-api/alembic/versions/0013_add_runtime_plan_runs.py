"""add runtime plan runs table

Revision ID: 0013_add_runtime_plan_runs
Revises: 0012_add_world_regions
Create Date: 2026-02-28 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_add_runtime_plan_runs"
down_revision = "0012_add_world_regions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_plan_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("plan_id", sa.String(length=160), nullable=False),
        sa.Column("plan_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("plan_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_runtime_plan_runs_lookup",
        "runtime_plan_runs",
        ["workspace_id", "actor_id", "plan_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_plan_runs_lookup", table_name="runtime_plan_runs")
    op.drop_table("runtime_plan_runs")

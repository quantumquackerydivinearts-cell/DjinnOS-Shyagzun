"""add scene library table

Revision ID: 0011_add_scene_library
Revises: 0010_add_lesson_progress
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_add_scene_library"
down_revision = "0010_add_lesson_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("realm_id", sa.String(length=80), nullable=False),
        sa.Column("scene_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scene_workspace_realm_scene",
        "scenes",
        ["workspace_id", "realm_id", "scene_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_scene_workspace_realm_scene", table_name="scenes")
    op.drop_table("scenes")

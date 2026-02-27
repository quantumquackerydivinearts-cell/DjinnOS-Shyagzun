"""add lesson progress table

Revision ID: 0010_add_lesson_progress
Revises: 0009_add_asset_manifest_realm
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_add_lesson_progress"
down_revision = "0009_add_asset_manifest_realm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("lesson_id", sa.String(length=36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_lesson_progress_actor_lesson",
        "lesson_progress",
        ["workspace_id", "actor_id", "lesson_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_progress_actor_lesson", table_name="lesson_progress")
    op.drop_table("lesson_progress")

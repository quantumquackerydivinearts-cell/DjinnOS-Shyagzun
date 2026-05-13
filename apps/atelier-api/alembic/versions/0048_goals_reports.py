"""0048 goals_reports — workspace_goals and workspace_digest_schedules

Revision ID: 0048_goals_reports
Revises: 0047_graph
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision      = "0048_goals_reports"
down_revision = "0047_graph"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "workspace_goals",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("workspace_id",  sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("title",         sa.String(160), nullable=False),
        sa.Column("metric_type",   sa.String(40),  nullable=False, server_default="lead_count"),
        sa.Column("period_start",  sa.String(10),  nullable=False),
        sa.Column("period_end",    sa.String(10),  nullable=False),
        sa.Column("target_value",  sa.Integer(),   nullable=False),
        sa.Column("current_value", sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("status",        sa.String(20),  nullable=False, server_default="open"),
        sa.Column("notes",         sa.Text(),      nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "workspace_digest_schedules",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("workspace_id",    sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("cadence",         sa.String(20),  nullable=False, server_default="weekly"),
        sa.Column("active",          sa.Boolean(),   nullable=False, server_default="1"),
        sa.Column("last_sent_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workspace_digest_schedules")
    op.drop_table("workspace_goals")

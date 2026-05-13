"""0047 graph — graph_configs and graph_telemetry_events tables

Revision ID: 0047_graph
Revises: 0046_attachments
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision      = "0047_graph"
down_revision = "0046_attachments"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "graph_configs",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("workspace_id", sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name",         sa.String(120), nullable=False),
        sa.Column("config_json",  sa.Text(),      nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "name", name="uq_graph_config_ws_name"),
    )

    op.create_table(
        "graph_telemetry_events",
        sa.Column("id",            sa.String(36), primary_key=True),
        sa.Column("workspace_id",  sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("event_name",    sa.String(80), nullable=False),
        sa.Column("metadata_json", sa.Text(),     nullable=False, server_default="{}"),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_telemetry_ws_event", "graph_telemetry_events", ["workspace_id", "event_name"])


def downgrade() -> None:
    op.drop_index("ix_graph_telemetry_ws_event", "graph_telemetry_events")
    op.drop_table("graph_telemetry_events")
    op.drop_table("graph_configs")

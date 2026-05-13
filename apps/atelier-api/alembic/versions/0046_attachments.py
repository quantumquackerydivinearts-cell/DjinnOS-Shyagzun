"""0046 attachments — polymorphic file attachment table

Revision ID: 0046_attachments
Revises: 0045_booking_title
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision      = "0046_attachments"
down_revision = "0045_booking_title"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id",           sa.String(36),    primary_key=True),
        sa.Column("workspace_id", sa.String(36),    sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("entity_type",  sa.String(40),    nullable=False),
        sa.Column("entity_id",    sa.String(36),    nullable=False),
        sa.Column("filename",     sa.String(255),   nullable=False),
        sa.Column("content_type", sa.String(120),   nullable=True),
        sa.Column("size_bytes",   sa.Integer(),     nullable=False, default=0),
        sa.Column("data",         sa.LargeBinary(), nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attachments_entity", "attachments", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_entity", "attachments")
    op.drop_table("attachments")

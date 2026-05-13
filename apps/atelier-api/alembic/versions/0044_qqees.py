"""0044 qqees — entropy contributions and credits tables

Revision ID: 0044_qqees
Revises: 0043_qcr_guild_service
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision       = "0044_qqees"
down_revision  = "0043_qcr_guild_service"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    op.create_table(
        "entropy_contributions",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("source_id",      sa.String(36),  sa.ForeignKey("entropy_sources.id"), nullable=False),
        sa.Column("contributed_at", sa.DateTime(),  nullable=False),
        sa.Column("raw_bytes",      sa.Integer(),   nullable=False),
        sa.Column("pool_h_after",   sa.Float(),     nullable=False),
        sa.Column("source_type",    sa.String(20),  nullable=False),
    )

    op.create_table(
        "entropy_credits",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("holder_id",        sa.String(100), nullable=False, index=True),
        sa.Column("bytes_remaining",  sa.Integer(),   nullable=False, default=0),
        sa.Column("bytes_purchased",  sa.Integer(),   nullable=False, default=0),
        sa.Column("purchased_at",     sa.DateTime(),  nullable=False),
        sa.Column("expires_at",       sa.DateTime(),  nullable=True),
        sa.Column("stripe_session",   sa.String(200), nullable=True),
        sa.Column("api_key",          sa.String(64),  nullable=False, unique=True),
    )


def downgrade() -> None:
    op.drop_table("entropy_credits")
    op.drop_table("entropy_contributions")

"""add guild_artisan_profiles table

Revision ID: 0029_add_guild_artisan_profiles
Revises: 0028_add_invite_codes
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_add_guild_artisan_profiles"
down_revision = "0028_add_invite_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guild_artisan_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("artisan_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("portfolio_url", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("divisions", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("trades", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("guild_rank", sa.String(length=40), nullable=False, server_default="artisan"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("show_region", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("show_trades", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("show_portfolio", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("steward_approved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("approved_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gap_artisan_id", "guild_artisan_profiles", ["artisan_id"])
    op.create_index("ix_gap_public", "guild_artisan_profiles", ["is_public", "steward_approved"])


def downgrade() -> None:
    op.drop_index("ix_gap_public", table_name="guild_artisan_profiles")
    op.drop_index("ix_gap_artisan_id", table_name="guild_artisan_profiles")
    op.drop_table("guild_artisan_profiles")

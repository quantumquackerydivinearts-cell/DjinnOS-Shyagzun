"""add shop items

Revision ID: 0021_add_shop_items
Revises: 0020_add_guild_conversations
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0021_add_shop_items"
down_revision = "0020_add_guild_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("artisan_id", sa.String(length=100), nullable=False),
        sa.Column("artisan_profile_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("artisan_profile_email", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("section_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("price_label", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("link_url", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("steward_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approved_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("shop_items")

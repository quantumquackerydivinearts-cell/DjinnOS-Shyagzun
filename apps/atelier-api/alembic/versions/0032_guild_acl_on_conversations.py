"""guild acl on client conversations

Revision ID: 0032_guild_acl_on_conversations
Revises: 0031_add_client_conversations
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0032_guild_acl_on_conversations"
down_revision = "0031_add_client_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # guild_id: ties a conversation to a specific guild (optional)
    op.add_column(
        "client_conversations",
        sa.Column("guild_id", sa.String(160), nullable=True),
    )
    # min_rank: minimum guild rank an artisan must hold to be added as participant
    # ranks in ascending order: apprentice < artisan < senior_artisan < steward
    op.add_column(
        "client_conversations",
        sa.Column("min_rank", sa.String(40), nullable=False, server_default="apprentice"),
    )
    op.create_index("ix_cconv_guild_id", "client_conversations", ["guild_id"])


def downgrade() -> None:
    op.drop_index("ix_cconv_guild_id", table_name="client_conversations")
    op.drop_column("client_conversations", "min_rank")
    op.drop_column("client_conversations", "guild_id")

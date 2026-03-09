"""add guild conversations

Revision ID: 0020_add_guild_conversations
Revises: 0019_add_distribution_handshakes
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0020_add_guild_conversations"
down_revision = "0019_add_distribution_handshakes"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = inspect(bind)
    try:
        columns = inspector.get_columns(table_name)
    except Exception:
        return False
    return any(str(column.get("name")) == column_name for column in columns)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "guild_conversations"):
        op.create_table(
            "guild_conversations",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("conversation_id", sa.String(length=160), nullable=False, unique=True),
            sa.Column("conversation_kind", sa.String(length=80), nullable=False, server_default="guild_channel"),
            sa.Column("guild_id", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("channel_id", sa.String(length=160), nullable=True),
            sa.Column("thread_id", sa.String(length=160), nullable=True),
            sa.Column("title", sa.String(length=240), nullable=False, server_default=""),
            sa.Column("participant_member_ids_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("participant_guild_ids_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("distribution_id", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("security_session_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if _has_table(bind, "guild_message_envelopes"):
        if not _has_column(bind, "guild_message_envelopes", "conversation_id"):
            op.add_column("guild_message_envelopes", sa.Column("conversation_id", sa.String(length=160), nullable=True))
        if not _has_column(bind, "guild_message_envelopes", "conversation_kind"):
            op.add_column(
                "guild_message_envelopes",
                sa.Column("conversation_kind", sa.String(length=80), nullable=False, server_default="guild_channel"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "guild_message_envelopes"):
        if _has_column(bind, "guild_message_envelopes", "conversation_kind"):
            op.drop_column("guild_message_envelopes", "conversation_kind")
        if _has_column(bind, "guild_message_envelopes", "conversation_id"):
            op.drop_column("guild_message_envelopes", "conversation_id")
    if _has_table(bind, "guild_conversations"):
        op.drop_table("guild_conversations")

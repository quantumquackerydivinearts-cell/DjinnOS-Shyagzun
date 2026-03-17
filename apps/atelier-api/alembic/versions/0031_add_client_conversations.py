"""add client conversations and messages

Revision ID: 0031_add_client_conversations
Revises: 0030_add_client_auth_fields
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0031_add_client_conversations"
down_revision = "0030_add_client_auth_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("quote_id", sa.String(36), sa.ForeignKey("quotes.id"), nullable=True),
        sa.Column("subject", sa.String(200), nullable=False, server_default=""),
        sa.Column("participant_artisan_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cconv_client_id", "client_conversations", ["client_id"])
    op.create_index("ix_cconv_workspace_id", "client_conversations", ["workspace_id"])
    op.create_index("ix_cconv_order_id", "client_conversations", ["order_id"])

    op.create_table(
        "client_message_envelopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("client_conversations.id"), nullable=False),
        sa.Column("sender_id", sa.String(100), nullable=False),
        sa.Column("sender_kind", sa.String(20), nullable=False),  # "client" | "artisan" | "steward"
        sa.Column("ciphertext_b64", sa.Text(), nullable=False),
        sa.Column("nonce_b64", sa.String(60), nullable=False),
        sa.Column("mac_hex", sa.String(64), nullable=False),
        sa.Column("plaintext_digest", sa.String(64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cmsg_conversation_id", "client_message_envelopes", ["conversation_id"])
    op.create_index("ix_cmsg_sender_id", "client_message_envelopes", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_cmsg_sender_id", table_name="client_message_envelopes")
    op.drop_index("ix_cmsg_conversation_id", table_name="client_message_envelopes")
    op.drop_table("client_message_envelopes")
    op.drop_index("ix_cconv_order_id", table_name="client_conversations")
    op.drop_index("ix_cconv_workspace_id", table_name="client_conversations")
    op.drop_index("ix_cconv_client_id", table_name="client_conversations")
    op.drop_table("client_conversations")

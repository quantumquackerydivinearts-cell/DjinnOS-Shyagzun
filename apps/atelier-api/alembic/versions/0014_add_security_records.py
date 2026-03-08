"""add guild and wand security record tables

Revision ID: 0014_add_security_records
Revises: 0013_add_runtime_plan_runs
Create Date: 2026-03-08 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_add_security_records"
down_revision = "0013_add_runtime_plan_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guild_message_envelopes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("message_id", sa.String(length=80), nullable=False),
        sa.Column("guild_id", sa.String(length=160), nullable=False),
        sa.Column("channel_id", sa.String(length=160), nullable=False),
        sa.Column("thread_id", sa.String(length=160), nullable=True),
        sa.Column("sender_id", sa.String(length=160), nullable=False),
        sa.Column("wand_id", sa.String(length=160), nullable=False),
        sa.Column("envelope_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("message_id", name="uq_guild_message_envelopes_message_id"),
    )
    op.create_index(
        "ix_guild_message_envelopes_lookup",
        "guild_message_envelopes",
        ["guild_id", "channel_id", "thread_id", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "wand_damage_attestations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("record_id", sa.String(length=80), nullable=False),
        sa.Column("wand_id", sa.String(length=160), nullable=False),
        sa.Column("notifier_id", sa.String(length=160), nullable=False),
        sa.Column("damage_state", sa.String(length=80), nullable=False),
        sa.Column("event_tag", sa.String(length=160), nullable=True),
        sa.Column("actor_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("workshop_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("media_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("validated_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("record_id", name="uq_wand_damage_attestations_record_id"),
    )
    op.create_index(
        "ix_wand_damage_attestations_lookup",
        "wand_damage_attestations",
        ["wand_id", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "wand_key_epochs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("epoch_id", sa.String(length=80), nullable=False),
        sa.Column("wand_id", sa.String(length=160), nullable=False),
        sa.Column("attestation_record_id", sa.String(length=80), nullable=False),
        sa.Column("notifier_id", sa.String(length=160), nullable=False),
        sa.Column("previous_epoch_id", sa.String(length=80), nullable=True),
        sa.Column("damage_state", sa.String(length=80), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("entropy_mix_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("epoch_id", name="uq_wand_key_epochs_epoch_id"),
    )
    op.create_index(
        "ix_wand_key_epochs_lookup",
        "wand_key_epochs",
        ["wand_id", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wand_key_epochs_lookup", table_name="wand_key_epochs")
    op.drop_table("wand_key_epochs")
    op.drop_index("ix_wand_damage_attestations_lookup", table_name="wand_damage_attestations")
    op.drop_table("wand_damage_attestations")
    op.drop_index("ix_guild_message_envelopes_lookup", table_name="guild_message_envelopes")
    op.drop_table("guild_message_envelopes")

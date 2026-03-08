"""add wand registry table

Revision ID: 0015_add_wand_registry
Revises: 0014_add_security_records
Create Date: 2026-03-08 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_add_wand_registry"
down_revision = "0014_add_security_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wand_registry",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("wand_id", sa.String(length=160), nullable=False),
        sa.Column("maker_id", sa.String(length=160), nullable=False),
        sa.Column("maker_date", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("atelier_origin", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("material_profile_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("dimensions_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("structural_fingerprint", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("craft_record_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("ownership_chain_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("wand_id", name="uq_wand_registry_wand_id"),
    )
    op.create_index("ix_wand_registry_updated_at", "wand_registry", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wand_registry_updated_at", table_name="wand_registry")
    op.drop_table("wand_registry")

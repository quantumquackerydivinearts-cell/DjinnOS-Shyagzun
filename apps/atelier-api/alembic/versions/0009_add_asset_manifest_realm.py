"""add realm_id to asset manifests

Revision ID: 0009_add_asset_manifest_realm
Revises: 0008_add_realms
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_add_asset_manifest_realm"
down_revision = "0008_add_realms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_manifests", sa.Column("realm_id", sa.String(length=80), nullable=False, server_default="lapidus"))
    op.alter_column("asset_manifests", "realm_id", server_default=None)


def downgrade() -> None:
    op.drop_column("asset_manifests", "realm_id")

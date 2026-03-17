"""add storage fields to asset_manifests

Revision ID: 0026_add_asset_storage_fields
Revises: 0025_add_workspace_ownership
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_add_asset_storage_fields"
down_revision = "0025_add_workspace_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_manifests", sa.Column("storage_key", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("asset_manifests", sa.Column("storage_state", sa.String(length=40), nullable=False, server_default="local"))
    op.add_column("asset_manifests", sa.Column("mime_type", sa.String(length=120), nullable=False, server_default="application/octet-stream"))
    op.add_column("asset_manifests", sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"))
    op.create_index("ix_am_workspace_state", "asset_manifests", ["workspace_id", "storage_state"])


def downgrade() -> None:
    op.drop_index("ix_am_workspace_state", table_name="asset_manifests")
    op.drop_column("asset_manifests", "file_size_bytes")
    op.drop_column("asset_manifests", "mime_type")
    op.drop_column("asset_manifests", "storage_state")
    op.drop_column("asset_manifests", "storage_key")

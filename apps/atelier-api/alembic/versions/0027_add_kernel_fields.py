"""add kernel_fields table for per-artisan field tracking

Revision ID: 0027_add_kernel_fields
Revises: 0026_add_asset_storage_fields
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_add_kernel_fields"
down_revision = "0026_add_asset_storage_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kernel_fields",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("field_id", sa.String(length=80), nullable=False, unique=True),
        sa.Column("owner_artisan_id", sa.String(length=100), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kf_owner", "kernel_fields", ["owner_artisan_id"])
    op.create_index("ix_kf_workspace", "kernel_fields", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_kf_workspace", table_name="kernel_fields")
    op.drop_index("ix_kf_owner", table_name="kernel_fields")
    op.drop_table("kernel_fields")

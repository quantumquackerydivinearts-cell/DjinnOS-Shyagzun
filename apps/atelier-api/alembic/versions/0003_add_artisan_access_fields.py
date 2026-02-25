"""add artisan access fields

Revision ID: 0003_add_artisan_access_fields
Revises: 0002_add_sales_entities
Create Date: 2026-02-25 01:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_artisan_access_fields"
down_revision = "0002_add_sales_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artisan_accounts", sa.Column("profile_name", sa.String(length=200), nullable=False, server_default=""))
    op.add_column("artisan_accounts", sa.Column("profile_email", sa.String(length=320), nullable=False, server_default=""))
    op.add_column("artisan_accounts", sa.Column("artisan_code_hash", sa.String(length=128), nullable=False, server_default=""))
    op.add_column("artisan_accounts", sa.Column("artisan_access_verified", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("artisan_accounts", "artisan_access_verified")
    op.drop_column("artisan_accounts", "artisan_code_hash")
    op.drop_column("artisan_accounts", "profile_email")
    op.drop_column("artisan_accounts", "profile_name")

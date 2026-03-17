"""add client auth fields

Revision ID: 0030_add_client_auth_fields
Revises: 0029_add_guild_artisan_profiles
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0030_add_client_auth_fields"
down_revision = "0029_add_guild_artisan_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("password_hash", sa.String(200), nullable=True))
    op.add_column("clients", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("clients", sa.Column("email_verification_token", sa.String(128), nullable=True))
    op.create_index("ix_clients_email", "clients", ["email"])


def downgrade() -> None:
    op.drop_index("ix_clients_email", table_name="clients")
    op.drop_column("clients", "email_verification_token")
    op.drop_column("clients", "email_verified")
    op.drop_column("clients", "password_hash")

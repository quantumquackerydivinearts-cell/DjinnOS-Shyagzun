"""add distribution handshakes

Revision ID: 0019_add_distribution_handshakes
Revises: 0018_add_distribution_registry
Create Date: 2026-03-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_add_distribution_handshakes"
down_revision = "0018_add_distribution_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_handshakes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("handshake_id", sa.String(length=80), nullable=False),
        sa.Column("distribution_id", sa.String(length=200), nullable=False),
        sa.Column("local_distribution_id", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("remote_public_key_ref", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("handshake_mode", sa.String(length=80), nullable=False, server_default="mutual_hmac"),
        sa.Column("shared_secret_b64", sa.Text(), nullable=False, server_default=""),
        sa.Column("shared_secret_digest", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handshake_id"),
    )


def downgrade() -> None:
    op.drop_table("distribution_handshakes")

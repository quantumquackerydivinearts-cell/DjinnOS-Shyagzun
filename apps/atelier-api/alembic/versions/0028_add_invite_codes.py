"""add invite_codes table for onboarding flow

Revision ID: 0028_add_invite_codes
Revises: 0027_add_kernel_fields
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_add_invite_codes"
down_revision = "0027_add_kernel_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invite_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("issued_by", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="artisan"),
        sa.Column("workshop_id", sa.String(length=100), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invite_codes_issued_by", "invite_codes", ["issued_by"])


def downgrade() -> None:
    op.drop_index("ix_invite_codes_issued_by", table_name="invite_codes")
    op.drop_table("invite_codes")

"""add contracts table

Revision ID: 0023_add_contracts
Revises: 0022_add_lead_phone_and_ledger_entries
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_add_contracts"
down_revision = "0022_add_lead_phone_and_ledger_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="general"),
        sa.Column("party_name", sa.String(length=200), nullable=False),
        sa.Column("party_email", sa.String(length=320), nullable=True),
        sa.Column("party_phone", sa.String(length=40), nullable=True),
        sa.Column("artisan_id", sa.String(length=100), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("terms", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("contracts")

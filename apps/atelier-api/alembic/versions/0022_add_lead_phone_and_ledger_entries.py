"""add lead phone and ledger entries

Revision ID: 0022_add_lead_phone_and_ledger_entries
Revises: 0021_add_shop_items
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_add_lead_phone_and_ledger_entries"
down_revision = "0021_add_shop_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("phone", sa.String(length=40), nullable=True))
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("account_type", sa.String(length=60), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("section_id", sa.String(length=60), nullable=True),
        sa.Column("reference_type", sa.String(length=60), nullable=True),
        sa.Column("reference_id", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ledger_entries")
    op.drop_column("leads", "phone")

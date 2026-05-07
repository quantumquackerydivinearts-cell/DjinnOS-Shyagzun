"""Add address and website to crm_contacts.

Revision ID: 0042_crm_contact_address_website
Revises: 0041_quack_framework
Create Date: 2026-05-07

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision      = "0042_crm_contact_address_website"
down_revision = "0041_quack_framework"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("crm_contacts", sa.Column("address", sa.Text(),       nullable=True))
    op.add_column("crm_contacts", sa.Column("website", sa.String(500),  nullable=True))


def downgrade() -> None:
    op.drop_column("crm_contacts", "website")
    op.drop_column("crm_contacts", "address")
"""0045 booking_title — add title column to bookings

Revision ID: 0045_booking_title
Revises: 0044_qqees
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision      = "0045_booking_title"
down_revision = "0044_qqees"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("title", sa.String(200), nullable=True, server_default=""))


def downgrade() -> None:
    op.drop_column("bookings", "title")

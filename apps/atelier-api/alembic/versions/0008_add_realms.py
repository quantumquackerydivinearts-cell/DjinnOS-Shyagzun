"""add realms table

Revision ID: 0008_add_realms
Revises: 0007_add_asset_manifests
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0008_add_realms"
down_revision = "0007_add_asset_manifests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "realms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    now = datetime.now(timezone.utc)
    realms = [
        {
            "id": str(uuid4()),
            "slug": "lapidus",
            "name": "Lapidus",
            "description": "Overworld realm",
            "created_at": now,
        },
        {
            "id": str(uuid4()),
            "slug": "mercurie",
            "name": "Mercurie",
            "description": "Faewilds realm",
            "created_at": now,
        },
        {
            "id": str(uuid4()),
            "slug": "sulphera",
            "name": "Sulphera",
            "description": "Underworld realm",
            "created_at": now,
        },
    ]
    op.bulk_insert(
        sa.table(
            "realms",
            sa.column("id", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("description", sa.Text),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        realms,
    )
    op.alter_column("realms", "created_at", server_default=None)


def downgrade() -> None:
    op.drop_table("realms")

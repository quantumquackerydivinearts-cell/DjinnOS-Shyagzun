"""compatibly add wand spec columns

Revision ID: 0016_add_wand_spec_columns_compat
Revises: 0015_add_wand_registry
Create Date: 2026-03-08 00:20:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_add_wand_spec_columns_compat"
down_revision = "0015_add_wand_registry"
branch_labels = None
depends_on = None


def _column_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns("wand_registry")
    return {str(column.get("name")) for column in columns}


def upgrade() -> None:
    columns = _column_names()
    if "maker_date" not in columns:
        op.add_column(
            "wand_registry",
            sa.Column("maker_date", sa.String(length=80), nullable=False, server_default=""),
        )
    if "dimensions_json" not in columns:
        op.add_column(
            "wand_registry",
            sa.Column("dimensions_json", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    columns = _column_names()
    if "dimensions_json" in columns:
        op.drop_column("wand_registry", "dimensions_json")
    if "maker_date" in columns:
        op.drop_column("wand_registry", "maker_date")

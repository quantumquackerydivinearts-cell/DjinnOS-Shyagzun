"""Supra Librix geo-tagged Physix vote table.

Revision ID: 0040_supra_librix
Revises: 0039_sequential_art
Create Date: 2026-04-26

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision    = "0040_supra_librix"
down_revision = "0039_sequential_art"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "supra_librix_votes",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("field_valence",   sa.Float(),     nullable=False),
        # JSON array of {lat, lon, shape, scale, init_degree, shygazun_tags}
        sa.Column("placements_json", sa.Text(),      nullable=False, server_default="[]"),
        sa.Column("utterance",       sa.Text(),      nullable=False, server_default=""),
        # Artisan who cast the vote — stored internally, never surfaced publicly
        sa.Column("voter_id",        sa.String(100), nullable=False),
        sa.Column("cast_at",         sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_supra_librix_votes_cast_at", "supra_librix_votes", ["cast_at"])


def downgrade() -> None:
    op.drop_index("ix_supra_librix_votes_cast_at", "supra_librix_votes")
    op.drop_table("supra_librix_votes")
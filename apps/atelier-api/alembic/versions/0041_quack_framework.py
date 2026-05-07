"""Quack framework — tongue_proposals and quack_tokens tables.

Revision ID: 0041_quack_framework
Revises: 0040_supra_librix
Create Date: 2026-05-07

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision      = "0041_quack_framework"
down_revision = "0040_supra_librix"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "tongue_proposals",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("artisan_id",    sa.String(100), nullable=False),
        sa.Column("tongue_number", sa.Integer(),   nullable=False),
        sa.Column("tongue_name",   sa.String(200), nullable=False),
        sa.Column("entries_json",  sa.Text(),      nullable=False, server_default="[]"),
        sa.Column("breath_start",  sa.Text(),      nullable=True),
        sa.Column("notes",         sa.Text(),      nullable=False, server_default=""),
        sa.Column("status",        sa.String(40),  nullable=False, server_default="proposed"),
        sa.Column("proposed_at",   sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_tongue_proposals_artisan", "tongue_proposals", ["artisan_id"])
    op.create_index("ix_tongue_proposals_number",  "tongue_proposals", ["tongue_number"])

    op.create_table(
        "quack_tokens",
        sa.Column("id",                sa.String(36),  primary_key=True),
        sa.Column("tongue_number",     sa.Integer(),   nullable=False, unique=True),
        sa.Column("tongue_name",       sa.String(200), nullable=False),
        sa.Column("holder_artisan_id", sa.String(100), nullable=False),
        sa.Column("entry_count",       sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("entries_json",      sa.Text(),      nullable=False, server_default="[]"),
        sa.Column("breath_start",      sa.Text(),      nullable=True),
        sa.Column("breath_end",        sa.Text(),      nullable=True),
        sa.Column("breath_diff",       sa.Text(),      nullable=True),
        sa.Column("proposal_id",       sa.String(36),  nullable=True),
        sa.Column("minted_at",         sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_quack_tokens_holder",  "quack_tokens", ["holder_artisan_id"])
    op.create_index("ix_quack_tokens_number",  "quack_tokens", ["tongue_number"])


def downgrade() -> None:
    op.drop_index("ix_quack_tokens_number",    "quack_tokens")
    op.drop_index("ix_quack_tokens_holder",    "quack_tokens")
    op.drop_table("quack_tokens")
    op.drop_index("ix_tongue_proposals_number", "tongue_proposals")
    op.drop_index("ix_tongue_proposals_artisan", "tongue_proposals")
    op.drop_table("tongue_proposals")
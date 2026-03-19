"""Q3 voting tables — Shygazun Physix voting system

Adds tables for Q3 (Quantum Quackery Quinary) governance:
  q3_motions   — commission/contract items put to the body for a vote
  q3_votes     — individual Physix vote records, anonymised

Revision ID: 0035_q3_voting_tables
Revises: 0034_artisan_marketplace_fields
Create Date: 2026-03-19

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
      See CONTEXT.md — upgrade head is not used locally.
"""

from alembic import op
import sqlalchemy as sa

revision = "0035_q3_voting_tables"
down_revision = "0034_artisan_marketplace_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "q3_motions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("motion_type", sa.String(40), nullable=False),  # accept|refuse|promote|manage
        sa.Column("source_ref", sa.String(200), nullable=True),   # lead_id / quote_id / contract_id
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),  # open|closed|resolved
        sa.Column("resolution", sa.String(40), nullable=True),    # accepted|refused|promoted|managed
        sa.Column("opened_by", sa.String(100), nullable=False),   # artisan_id of opener
        sa.Column("closes_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "q3_votes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("motion_id", sa.String(36), sa.ForeignKey("q3_motions.id"), nullable=False),
        # Physix record — full tagged JSON, stored as text
        sa.Column("physix_json", sa.Text(), nullable=False),
        # Voter identity held internally, never surfaced in audit output
        sa.Column("voter_artisan_id", sa.String(100), nullable=False),
        sa.Column("cast_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_q3_votes_motion_id", "q3_votes", ["motion_id"])
    # Enforce one vote per artisan per motion
    op.create_index(
        "uq_q3_votes_motion_voter",
        "q3_votes",
        ["motion_id", "voter_artisan_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_q3_votes_motion_voter", "q3_votes")
    op.drop_index("ix_q3_votes_motion_id", "q3_votes")
    op.drop_table("q3_votes")
    op.drop_table("q3_motions")

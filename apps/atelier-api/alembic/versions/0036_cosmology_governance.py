"""Cosmology governance tables

Adds the three-table cosmology ownership and contribution pipeline:

  cosmologies           — named cosmologies with a Steward owner
  cosmology_memberships — contributor/moderator roles per cosmology
  cosmology_submissions — content submitted to a foreign cosmology,
                          pending Steward approval before becoming canonical

Seed: KLGS cosmology pinned to artisan_id='alexi' as Steward at migration time.

Revision ID: 0036_cosmology_governance
Revises: 0035_q3_voting_tables
Create Date: 2026-04-17

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import uuid

revision      = "0036_cosmology_governance"
down_revision = "0035_q3_voting_tables"
branch_labels = None
depends_on    = None

_KLGS_ID      = "cosmology-klgs-0000-0451"
_KLGS_STEWARD = "alexi"
_NOW          = datetime.now(timezone.utc).isoformat()


def upgrade() -> None:
    # ── cosmologies ───────────────────────────────────────────────────────────
    op.create_table(
        "cosmologies",
        sa.Column("id",                sa.String(64),  primary_key=True),
        sa.Column("slug",              sa.String(100), nullable=False, unique=True),
        sa.Column("name",              sa.String(200), nullable=False),
        sa.Column("description",       sa.Text,        nullable=False, server_default=""),
        sa.Column("steward_artisan_id",sa.String(100), nullable=False),
        sa.Column("open_contribution", sa.Boolean,     nullable=False, server_default="0"),
        sa.Column("kernel_anchored",   sa.Boolean,     nullable=False, server_default="0"),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False),
    )

    # ── cosmology_memberships ─────────────────────────────────────────────────
    op.create_table(
        "cosmology_memberships",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("cosmology_id",  sa.String(64),  sa.ForeignKey("cosmologies.id"), nullable=False),
        sa.Column("artisan_id",    sa.String(100), nullable=False),
        # role: contributor | moderator
        sa.Column("role",          sa.String(50),  nullable=False, server_default="contributor"),
        sa.Column("invited_by",    sa.String(100), nullable=True),
        sa.Column("joined_at",     sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cosmology_memberships_cosmology", "cosmology_memberships", ["cosmology_id"])
    op.create_index("ix_cosmology_memberships_artisan",   "cosmology_memberships", ["artisan_id"])

    # ── cosmology_submissions ─────────────────────────────────────────────────
    op.create_table(
        "cosmology_submissions",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("cosmology_id",    sa.String(64),  sa.ForeignKey("cosmologies.id"), nullable=False),
        sa.Column("contributor_id",  sa.String(100), nullable=False),
        # content_type: zone | npc | quest | item | dialogue | sprite | shader | other
        sa.Column("content_type",    sa.String(50),  nullable=False),
        sa.Column("content_label",   sa.String(200), nullable=False, server_default=""),
        sa.Column("content_data",    sa.Text,        nullable=False, server_default="{}"),
        # status: pending | approved | rejected | withdrawn
        sa.Column("status",          sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("steward_note",    sa.Text,        nullable=True),
        sa.Column("kernel_valid",    sa.Boolean,     nullable=False, server_default="0"),
        sa.Column("submitted_at",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cosmology_submissions_cosmology", "cosmology_submissions", ["cosmology_id"])
    op.create_index("ix_cosmology_submissions_status",    "cosmology_submissions", ["status"])
    op.create_index("ix_cosmology_submissions_contributor","cosmology_submissions", ["contributor_id"])

    # ── seed: KLGS cosmology → steward alexi ─────────────────────────────────
    op.execute(
        sa.text("""
            INSERT INTO cosmologies
                (id, slug, name, description, steward_artisan_id,
                 open_contribution, kernel_anchored, created_at)
            VALUES
                (:id, :slug, :name, :desc, :steward,
                 0, 1, :now)
        """),
        {
            "id":      _KLGS_ID,
            "slug":    "klgs",
            "name":    "Ko's Labyrinth",
            "desc":    (
                "The canonical 31-game series by Alexi (0000_0451). "
                "Contributions require Steward approval. "
                "Kernel-anchored — structural validity enforced at the Kernel level."
            ),
            "steward": _KLGS_STEWARD,
            "now":     _NOW,
        },
    )


def downgrade() -> None:
    op.execute("DELETE FROM cosmologies WHERE id = 'cosmology-klgs-0000-0451'")
    op.drop_index("ix_cosmology_submissions_contributor", "cosmology_submissions")
    op.drop_index("ix_cosmology_submissions_status",      "cosmology_submissions")
    op.drop_index("ix_cosmology_submissions_cosmology",   "cosmology_submissions")
    op.drop_table("cosmology_submissions")
    op.drop_index("ix_cosmology_memberships_artisan",   "cosmology_memberships")
    op.drop_index("ix_cosmology_memberships_cosmology", "cosmology_memberships")
    op.drop_table("cosmology_memberships")
    op.drop_table("cosmologies")
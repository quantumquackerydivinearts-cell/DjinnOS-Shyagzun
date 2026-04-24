"""Sequential art tooling — pages, panels, character roster

Adds authoring tables for storyboard and comic projects:

  seq_art_pages      — ordered pages within a sequential_art project
  seq_art_panels     — panels on a page (dialogue, captions, SFX, asset)
  seq_art_characters — character roster scoped to a project

Revision ID: 0039_sequential_art
Revises: 0038_distribution_targets
Create Date: 2026-04-24

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision      = "0039_sequential_art"
down_revision = "0038_distribution_targets"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── seq_art_pages ─────────────────────────────────────────────────────────
    op.create_table(
        "seq_art_pages",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("project_id",   sa.String(36),  sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("page_number",  sa.Integer,     nullable=False),
        sa.Column("title",        sa.String(200), nullable=False, server_default=""),
        sa.Column("notes",        sa.Text,        nullable=False, server_default=""),
        # status: draft | final
        sa.Column("status",       sa.String(20),  nullable=False, server_default="draft"),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_seq_art_pages_project",     "seq_art_pages", ["project_id"])
    op.create_index("ix_seq_art_pages_proj_pagenum","seq_art_pages", ["project_id", "page_number"])

    # ── seq_art_panels ────────────────────────────────────────────────────────
    op.create_table(
        "seq_art_panels",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("page_id",        sa.String(36),  sa.ForeignKey("seq_art_pages.id"), nullable=False),
        sa.Column("panel_index",    sa.Integer,     nullable=False),
        # panel_type: standard | splash | bleed | inset
        sa.Column("panel_type",     sa.String(30),  nullable=False, server_default="standard"),
        # dialogue_json: [{speaker, text, bubble_type}]
        sa.Column("dialogue_json",  sa.Text,        nullable=False, server_default="[]"),
        # caption_json: [{position, text}]
        sa.Column("caption_json",   sa.Text,        nullable=False, server_default="[]"),
        # sfx_json: [{text, style}]
        sa.Column("sfx_json",       sa.Text,        nullable=False, server_default="[]"),
        sa.Column("asset_url",      sa.String(500), nullable=True),
        sa.Column("thumbnail_url",  sa.String(500), nullable=True),
        sa.Column("notes",          sa.Text,        nullable=False, server_default=""),
        # status: sketch | inks | color | final
        sa.Column("status",         sa.String(20),  nullable=False, server_default="sketch"),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_seq_art_panels_page",  "seq_art_panels", ["page_id"])

    # ── seq_art_characters ────────────────────────────────────────────────────
    op.create_table(
        "seq_art_characters",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("project_id",    sa.String(36),  sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name",          sa.String(200), nullable=False),
        sa.Column("description",   sa.Text,        nullable=False, server_default=""),
        sa.Column("reference_url", sa.String(500), nullable=True),
        sa.Column("notes",         sa.Text,        nullable=False, server_default=""),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_seq_art_chars_project", "seq_art_characters", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_seq_art_chars_project",   "seq_art_characters")
    op.drop_table("seq_art_characters")
    op.drop_index("ix_seq_art_panels_page",     "seq_art_panels")
    op.drop_table("seq_art_panels")
    op.drop_index("ix_seq_art_pages_proj_pagenum", "seq_art_pages")
    op.drop_index("ix_seq_art_pages_project",   "seq_art_pages")
    op.drop_table("seq_art_pages")
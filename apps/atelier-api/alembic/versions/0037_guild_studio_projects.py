"""Guild studio profiles and project containers

Adds the four-table guild/project layer:

  studio_profiles  — public guild identity for a workspace/studio
  projects         — unified creative artifact container (all disciplines)
  project_licenses — license attached at publication
  guild_listings   — cross-studio visible records (published projects only)

Revision ID: 0037_guild_studio_projects
Revises: 0036_cosmology_governance
Create Date: 2026-04-24

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision      = "0037_guild_studio_projects"
down_revision = "0036_cosmology_governance"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── studio_profiles ───────────────────────────────────────────────────────
    op.create_table(
        "studio_profiles",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("workspace_id",     sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False, unique=True),
        sa.Column("owner_artisan_id", sa.String(100), nullable=False),
        sa.Column("display_name",     sa.String(200), nullable=False),
        sa.Column("tagline",          sa.String(300), nullable=False, server_default=""),
        sa.Column("bio",              sa.Text,        nullable=False, server_default=""),
        sa.Column("logo_url",         sa.String(500), nullable=True),
        # studio_type: indie_game | graphic_art | sequential_art | education | mixed
        sa.Column("studio_type",      sa.String(60),  nullable=False, server_default="mixed"),
        sa.Column("tags_json",        sa.Text,        nullable=False, server_default="[]"),
        # guild_status: active | pending | suspended
        sa.Column("guild_status",     sa.String(40),  nullable=False, server_default="active"),
        sa.Column("is_public",        sa.Boolean,     nullable=False, server_default="1"),
        sa.Column("joined_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_studio_profiles_owner", "studio_profiles", ["owner_artisan_id"])
    op.create_index("ix_studio_profiles_status", "studio_profiles", ["guild_status"])

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id",                sa.String(36),  primary_key=True),
        sa.Column("workspace_id",      sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("title",             sa.String(300), nullable=False),
        sa.Column("description",       sa.Text,        nullable=False, server_default=""),
        # project_type: ambroflow_game | sequential_art | graphic_art | asset_pack | lesson | dlc_pack | other
        sa.Column("project_type",      sa.String(60),  nullable=False, server_default="other"),
        # publication_state: draft | internal | published | distributed
        sa.Column("publication_state", sa.String(40),  nullable=False, server_default="draft"),
        sa.Column("cover_image_url",   sa.String(500), nullable=True),
        sa.Column("tags_json",         sa.Text,        nullable=False, server_default="[]"),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at",      sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_workspace",   "projects", ["workspace_id"])
    op.create_index("ix_projects_type",        "projects", ["project_type"])
    op.create_index("ix_projects_pub_state",   "projects", ["publication_state"])

    # ── project_licenses ──────────────────────────────────────────────────────
    op.create_table(
        "project_licenses",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("project_id",      sa.String(36),  sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("license_type",    sa.String(60),  nullable=False, server_default="cc_by"),
        sa.Column("license_version", sa.String(20),  nullable=False, server_default="4.0"),
        sa.Column("custom_terms",    sa.Text,        nullable=True),
        sa.Column("effective_at",    sa.DateTime(timezone=True), nullable=False),
    )

    # ── guild_listings ────────────────────────────────────────────────────────
    op.create_table(
        "guild_listings",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("project_id",      sa.String(36),  sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("workspace_id",    sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("title",           sa.String(300), nullable=False),
        sa.Column("description",     sa.Text,        nullable=False, server_default=""),
        sa.Column("project_type",    sa.String(60),  nullable=False),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("license_type",    sa.String(60),  nullable=False, server_default="cc_by"),
        sa.Column("tags_json",       sa.Text,        nullable=False, server_default="[]"),
        sa.Column("listed_at",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_featured",     sa.Boolean,     nullable=False, server_default="0"),
        sa.Column("view_count",      sa.Integer,     nullable=False, server_default="0"),
    )
    op.create_index("ix_guild_listings_workspace",    "guild_listings", ["workspace_id"])
    op.create_index("ix_guild_listings_project_type", "guild_listings", ["project_type"])
    op.create_index("ix_guild_listings_listed_at",    "guild_listings", ["listed_at"])


def downgrade() -> None:
    op.drop_index("ix_guild_listings_listed_at",    "guild_listings")
    op.drop_index("ix_guild_listings_project_type", "guild_listings")
    op.drop_index("ix_guild_listings_workspace",    "guild_listings")
    op.drop_table("guild_listings")
    op.drop_table("project_licenses")
    op.drop_index("ix_projects_pub_state", "projects")
    op.drop_index("ix_projects_type",      "projects")
    op.drop_index("ix_projects_workspace", "projects")
    op.drop_table("projects")
    op.drop_index("ix_studio_profiles_status", "studio_profiles")
    op.drop_index("ix_studio_profiles_owner",  "studio_profiles")
    op.drop_table("studio_profiles")
"""Distribution targets — Steam, own storefront, commission intake

Adds distribution_targets table: per-project or workspace-level publishing
destinations. config_json stores type-specific fields so the schema stays
flexible as new channels are added.

  target_type: steam | own_store | commission_intake
  status:      draft | active | paused | retired

Revision ID: 0038_distribution_targets
Revises: 0037_guild_studio_projects
Create Date: 2026-04-24

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
"""

from alembic import op
import sqlalchemy as sa

revision      = "0038_distribution_targets"
down_revision = "0037_guild_studio_projects"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "distribution_targets",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("workspace_id", sa.String(36),  sa.ForeignKey("workspaces.id"), nullable=False),
        # project_id is nullable — commission_intake targets are workspace-level
        sa.Column("project_id",   sa.String(36),  sa.ForeignKey("projects.id"), nullable=True),
        # target_type: steam | own_store | commission_intake
        sa.Column("target_type",  sa.String(40),  nullable=False),
        # status: draft | active | paused | retired
        sa.Column("status",       sa.String(20),  nullable=False, server_default="draft"),
        # Flexible JSON blob: fields differ per target_type
        sa.Column("config_json",  sa.Text,        nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dist_targets_workspace",    "distribution_targets", ["workspace_id"])
    op.create_index("ix_dist_targets_project",      "distribution_targets", ["project_id"])
    op.create_index("ix_dist_targets_type_status",  "distribution_targets", ["target_type", "status"])


def downgrade() -> None:
    op.drop_index("ix_dist_targets_type_status", "distribution_targets")
    op.drop_index("ix_dist_targets_project",     "distribution_targets")
    op.drop_index("ix_dist_targets_workspace",   "distribution_targets")
    op.drop_table("distribution_targets")
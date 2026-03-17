"""add workspace ownership and memberships

Revision ID: 0025_add_workspace_ownership
Revises: 0024_add_render_lab_projects
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0025_add_workspace_ownership"
down_revision = "0024_add_render_lab_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend workspaces with ownership tracking and lifecycle status
    op.add_column("workspaces", sa.Column("owner_artisan_id", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("workspaces", sa.Column("status", sa.String(length=40), nullable=False, server_default="active"))

    # workspace_memberships: explicit artisan ↔ workspace membership records
    # Replaces the implicit "everyone shares main" model with per-artisan scoping.
    op.create_table(
        "workspace_memberships",
        sa.Column("id",           sa.String(length=36),  primary_key=True),
        sa.Column("workspace_id", sa.String(length=36),  sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("artisan_id",   sa.String(length=100), nullable=False),
        sa.Column("role",         sa.String(length=40),  nullable=False, server_default="member"),
        sa.Column("granted_by",   sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_wm_artisan",   "workspace_memberships", ["artisan_id"])
    op.create_index("ix_wm_workspace", "workspace_memberships", ["workspace_id"])
    # Unique per artisan/workspace pair — use index (SQLite-safe)
    op.create_index(
        "uq_wm_artisan_workspace",
        "workspace_memberships",
        ["artisan_id", "workspace_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_wm_artisan_workspace", table_name="workspace_memberships")
    op.drop_index("ix_wm_workspace",         table_name="workspace_memberships")
    op.drop_index("ix_wm_artisan",           table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
    op.drop_column("workspaces", "status")
    op.drop_column("workspaces", "owner_artisan_id")

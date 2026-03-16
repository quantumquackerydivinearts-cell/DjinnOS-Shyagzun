"""add render_lab_projects table

Revision ID: 0024_add_render_lab_projects
Revises: 0023_add_contracts
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0024_add_render_lab_projects"
down_revision = "0023_add_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "render_lab_projects",
        sa.Column("project_id",   sa.String(length=40),  primary_key=True),
        sa.Column("name",         sa.String(length=128),  nullable=False),
        sa.Column("project_type", sa.String(length=24),   nullable=False),
        sa.Column("workspace_id", sa.String(length=64),   nullable=False, server_default="main"),
        sa.Column("realm_id",     sa.String(length=64),   nullable=False, server_default="lapidus"),
        sa.Column("status",       sa.String(length=32),   nullable=False, server_default="draft"),
        # Full project document stored as JSON text — avoids N migration files per schema evolution.
        # Indexed columns above are the only fields queried by WHERE/ORDER.
        sa.Column("data_json",    sa.Text(),              nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.String(length=32),   nullable=False),
        sa.Column("updated_at",   sa.String(length=32),   nullable=False),
    )
    op.create_index("ix_rlp_workspace", "render_lab_projects", ["workspace_id"])
    op.create_index("ix_rlp_type",      "render_lab_projects", ["project_type"])
    op.create_index("ix_rlp_status",    "render_lab_projects", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rlp_status",    table_name="render_lab_projects")
    op.drop_index("ix_rlp_type",      table_name="render_lab_projects")
    op.drop_index("ix_rlp_workspace", table_name="render_lab_projects")
    op.drop_table("render_lab_projects")

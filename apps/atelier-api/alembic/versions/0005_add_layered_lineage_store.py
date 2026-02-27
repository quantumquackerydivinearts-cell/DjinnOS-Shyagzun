"""add layered lineage and function store tables

Revision ID: 0005_add_layered_lineage_store
Revises: 0004_add_inventory_suppliers
Create Date: 2026-02-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_add_layered_lineage_store"
down_revision = "0004_add_inventory_suppliers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "layer_nodes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("layer_index", sa.Integer(), nullable=False),
        sa.Column("node_key", sa.String(length=200), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "layer_edges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("from_node_id", sa.String(length=36), sa.ForeignKey("layer_nodes.id"), nullable=False),
        sa.Column("to_node_id", sa.String(length=36), sa.ForeignKey("layer_nodes.id"), nullable=False),
        sa.Column("edge_kind", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "layer_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("event_kind", sa.String(length=120), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=False),
        sa.Column("node_id", sa.String(length=36), sa.ForeignKey("layer_nodes.id"), nullable=True),
        sa.Column("edge_id", sa.String(length=36), sa.ForeignKey("layer_edges.id"), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "function_store_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("function_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("signature", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("function_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("function_store_entries")
    op.drop_table("layer_events")
    op.drop_table("layer_edges")
    op.drop_table("layer_nodes")

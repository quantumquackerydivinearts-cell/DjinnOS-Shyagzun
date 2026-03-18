"""multiverse stack fields on layer_nodes

Adds game_id (slug) and prior_subset_key (Ha+Na+Wu style) to layer_nodes
so the Orrery can slice the unified player workspace graph by game and by
cosmological prior combination without breaking workspace unity.

Revision ID: 0033_multiverse_stack_fields
Revises: 0032_guild_acl_on_conversations
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0033_multiverse_stack_fields"
down_revision = "0032_guild_acl_on_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # game_id: slug identifying which of the 31 games this node belongs to
    # e.g. "_KLGS" for Ko's Labyrnth Game Set (Game 7)
    # NULL = cross-game / Sulphera-level node
    op.add_column(
        "layer_nodes",
        sa.Column("game_id", sa.String(80), nullable=True),
    )
    # prior_subset_key: the cosmological identity of the game —
    # alphabetically sorted prior names joined by "+" e.g. "Ha+Na+Wu"
    # NULL = cross-game / Sulphera-level node
    op.add_column(
        "layer_nodes",
        sa.Column("prior_subset_key", sa.String(120), nullable=True),
    )
    op.create_index("ix_layer_nodes_game_id",        "layer_nodes", ["game_id"])
    op.create_index("ix_layer_nodes_prior_subset",   "layer_nodes", ["prior_subset_key"])
    op.create_index("ix_layer_nodes_workspace_game", "layer_nodes", ["workspace_id", "game_id"])


def downgrade() -> None:
    op.drop_index("ix_layer_nodes_workspace_game", table_name="layer_nodes")
    op.drop_index("ix_layer_nodes_prior_subset",   table_name="layer_nodes")
    op.drop_index("ix_layer_nodes_game_id",        table_name="layer_nodes")
    op.drop_column("layer_nodes", "prior_subset_key")
    op.drop_column("layer_nodes", "game_id")

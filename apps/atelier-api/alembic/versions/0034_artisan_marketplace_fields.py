"""artisan marketplace fields

Adds artisan marketplace columns to shop_items and stripe_account_id to
guild_artisan_profiles, enabling the QQDA Artisan Marketplace with Stripe
Connect payout routing.

Revision ID: 0034_artisan_marketplace_fields
Revises: 0033_multiverse_stack_fields
Create Date: 2026-03-18

NOTE: For local SQLite dev use `alembic stamp head` (NOT upgrade head).
      See CONTEXT.md — upgrade head is not used locally.
"""

from alembic import op
import sqlalchemy as sa


revision = "0034_artisan_marketplace_fields"
down_revision = "0033_multiverse_stack_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- shop_items: artisan marketplace fields --
    with op.batch_alter_table("shop_items") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("item_type", sa.String(length=40), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("currency", sa.String(length=8), nullable=False, server_default="usd"))
        batch_op.add_column(sa.Column("stripe_product_id", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("stripe_price_id", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("file_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch_op.add_column(sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("inventory_count", sa.Integer(), nullable=True))

    # -- guild_artisan_profiles: Stripe Connect account ID --
    with op.batch_alter_table("guild_artisan_profiles") as batch_op:
        batch_op.add_column(sa.Column("stripe_account_id", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("guild_artisan_profiles") as batch_op:
        batch_op.drop_column("stripe_account_id")

    with op.batch_alter_table("shop_items") as batch_op:
        batch_op.drop_column("inventory_count")
        batch_op.drop_column("is_featured")
        batch_op.drop_column("is_active")
        batch_op.drop_column("thumbnail_url")
        batch_op.drop_column("file_path")
        batch_op.drop_column("stripe_price_id")
        batch_op.drop_column("stripe_product_id")
        batch_op.drop_column("currency")
        batch_op.drop_column("price_cents")
        batch_op.drop_column("item_type")
        batch_op.drop_column("description")

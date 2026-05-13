"""QCR Guild Service — contracts, implementations, departments, billing, entropy pool.

Revision ID: 0043_qcr_guild_service
Revises: 0042_crm_contact_address_website
Create Date: 2026-05-12

Tables:
  departments         — Sulphur / Mercury / Salt formal records
  qcr_contracts       — Guild contracts with domain owners
  qcr_implementations — Per-domain/subdomain instances under a contract
  cost_records        — Monthly cost accounting per department
  revenue_shares      — Monthly profit distribution per implementation
  quack_offsets       — Practitioner Quack offset ledger (floating with H)
  qcr_payments        — Invoice and payment records
  entropy_sources     — Registered gardens and theatrical ops for QQEES
"""

from alembic import op
import sqlalchemy as sa

revision      = "0043_qcr_guild_service"
down_revision = "0042_crm_contact_address_website"
branch_labels = None
depends_on    = None


def upgrade() -> None:

    # ── Departments ───────────────────────────────────────────────────────────
    op.create_table("departments",
        sa.Column("id",              sa.String,  primary_key=True),
        sa.Column("name",            sa.String,  nullable=False, unique=True),
        sa.Column("responsibilities", sa.Text,   nullable=False),  # JSON list
        sa.Column("notes",           sa.Text,    nullable=True),
    )

    # ── QCR contracts ─────────────────────────────────────────────────────────
    op.create_table("qcr_contracts",
        sa.Column("id",               sa.String,   primary_key=True),
        sa.Column("dispatcher_id",    sa.String,   nullable=False),  # artisan_id
        sa.Column("client_id",        sa.String,   nullable=False),  # artisan_id of domain owner
        sa.Column("tier",             sa.String,   nullable=False),  # "keyword" | "qcr_tce"
        sa.Column("status",           sa.String,   nullable=False, default="active"),
        sa.Column("signed_at",        sa.DateTime, nullable=False),
        sa.Column("revoked_at",       sa.DateTime, nullable=True),
        sa.Column("revocation_reason",sa.Text,     nullable=True),
        # Non-erasure term tracking
        sa.Column("non_erasure_acknowledged", sa.Boolean, nullable=False, default=False),
        sa.Column("roko_last_checked",        sa.DateTime, nullable=True),
        sa.Column("roko_status",              sa.String,   nullable=True),  # "clear" | "flagged" | "revoked"
        sa.Column("notes",            sa.Text,     nullable=True),
    )

    # ── QCR implementations ───────────────────────────────────────────────────
    op.create_table("qcr_implementations",
        sa.Column("id",           sa.String,  primary_key=True),
        sa.Column("contract_id",  sa.String,  sa.ForeignKey("qcr_contracts.id"), nullable=False),
        sa.Column("domain",       sa.String,  nullable=False),  # e.g. "shop.example.com"
        sa.Column("api_key",      sa.String,  nullable=False, unique=True),
        sa.Column("tier",         sa.String,  nullable=False),
        sa.Column("rate_cents",   sa.Integer, nullable=False, default=3500),  # $35.00/month
        sa.Column("active",       sa.Boolean, nullable=False, default=True),
        sa.Column("activated_at", sa.DateTime, nullable=False),
        sa.Column("notes",        sa.Text,    nullable=True),
    )

    # ── Cost records ──────────────────────────────────────────────────────────
    op.create_table("cost_records",
        sa.Column("id",               sa.String,  primary_key=True),
        sa.Column("period",           sa.String,  nullable=False),   # "2026-05"
        sa.Column("energy_cents",     sa.Integer, nullable=False, default=0),
        sa.Column("infra_cents",      sa.Integer, nullable=False, default=0),
        sa.Column("sulphur_wages_cents", sa.Integer, nullable=False, default=0),
        sa.Column("mercury_wages_cents", sa.Integer, nullable=False, default=0),
        sa.Column("salt_wages_cents",    sa.Integer, nullable=False, default=0),
        sa.Column("qqees_credit_cents",  sa.Integer, nullable=False, default=0),  # offsets salt
        sa.Column("notes",            sa.Text,    nullable=True),
    )

    # ── Revenue shares ────────────────────────────────────────────────────────
    op.create_table("revenue_shares",
        sa.Column("id",                    sa.String,  primary_key=True),
        sa.Column("period",                sa.String,  nullable=False),
        sa.Column("implementation_id",     sa.String,  sa.ForeignKey("qcr_implementations.id"), nullable=False),
        sa.Column("revenue_cents",         sa.Integer, nullable=False),
        sa.Column("total_cost_cents",      sa.Integer, nullable=False),
        sa.Column("profit_cents",          sa.Integer, nullable=False),
        sa.Column("dispatcher_share_cents",sa.Integer, nullable=False),
        sa.Column("practitioner_pool_cents",sa.Integer,nullable=False),
        sa.Column("practitioner_pool_pct", sa.Float,   nullable=False),  # 0.24–0.40
        sa.Column("guild_share_cents",     sa.Integer, nullable=False),
        sa.Column("settled",               sa.Boolean, nullable=False, default=False),
        sa.Column("settled_at",            sa.DateTime,nullable=True),
    )

    # ── Quack offsets ─────────────────────────────────────────────────────────
    op.create_table("quack_offsets",
        sa.Column("id",               sa.String, primary_key=True),
        sa.Column("practitioner_id",  sa.String, nullable=False),
        sa.Column("quack_count",      sa.Integer, nullable=False, default=0),
        sa.Column("tongues_worked",   sa.Integer, nullable=False, default=0),
        sa.Column("rank_title",       sa.String,  nullable=False),
        sa.Column("baseline_h",       sa.Float,   nullable=False),   # H at time of first offset
        sa.Column("current_h",        sa.Float,   nullable=False),
        sa.Column("base_value_cents", sa.Integer, nullable=False),   # base fiat per Quack
        sa.Column("offset_balance_cents", sa.Integer, nullable=False, default=0),
        sa.Column("last_updated",     sa.DateTime,nullable=False),
    )

    # ── Payments ──────────────────────────────────────────────────────────────
    op.create_table("qcr_payments",
        sa.Column("id",                sa.String,  primary_key=True),
        sa.Column("implementation_id", sa.String,  sa.ForeignKey("qcr_implementations.id"), nullable=False),
        sa.Column("period",            sa.String,  nullable=False),
        sa.Column("amount_cents",      sa.Integer, nullable=False),
        sa.Column("method",            sa.String,  nullable=False),  # "card" | "quack_offset" | "mixed"
        sa.Column("stripe_payment_id", sa.String,  nullable=True),
        sa.Column("quack_offset_cents",sa.Integer, nullable=False, default=0),
        sa.Column("status",            sa.String,  nullable=False, default="pending"),
        sa.Column("paid_at",           sa.DateTime,nullable=True),
        sa.Column("invoice_url",       sa.String,  nullable=True),
    )

    # ── Entropy sources (QQEES) ───────────────────────────────────────────────
    op.create_table("entropy_sources",
        sa.Column("id",           sa.String,  primary_key=True),
        sa.Column("name",         sa.String,  nullable=False),
        sa.Column("source_type",  sa.String,  nullable=False),   # "garden" | "theatrical"
        sa.Column("department",   sa.String,  nullable=False),   # "Salt" | "Sulphur"
        sa.Column("description",  sa.Text,    nullable=True),
        sa.Column("registered_by",sa.String,  nullable=False),   # artisan_id
        sa.Column("registered_at",sa.DateTime,nullable=False),
        sa.Column("active",       sa.Boolean, nullable=False, default=True),
        sa.Column("last_noise_at",sa.DateTime,nullable=True),
        sa.Column("entropy_bits_contributed", sa.Integer, nullable=False, default=0),
    )


def downgrade() -> None:
    op.drop_table("entropy_sources")
    op.drop_table("qcr_payments")
    op.drop_table("quack_offsets")
    op.drop_table("revenue_shares")
    op.drop_table("cost_records")
    op.drop_table("qcr_implementations")
    op.drop_table("qcr_contracts")
    op.drop_table("departments")

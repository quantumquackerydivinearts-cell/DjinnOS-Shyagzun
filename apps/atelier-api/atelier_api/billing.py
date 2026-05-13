"""
billing.py — QCR Guild billing engine

Handles:
  - Monthly revenue share calculation per implementation
  - Dispatcher and practitioner profit distribution
  - Quack offset ledger updates (floating with Shannon H)
  - Stripe Connect integration for card payments
  - Invoice generation
  - Scheduled Roko site assessment against all active contracts

Revenue formula:
  profit = revenue - (energy + infra + sulphur + mercury + max(0, salt - qqees_credit))
  dispatcher_share = profit × 0.20  (if dispatcher != "alexi")
  practitioner_pool = profit × pool_pct  (24%–40% by highest active rank)
  guild_share = profit - dispatcher_share - practitioner_pool

Quack offset:
  offset_per_quack = base_value × (H_current / H_baseline)
  Practitioner's balance grows each period based on their Quack count × rate.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from .intel import shannon_entropy, tongue_count
from .qcr_models_append import (
    QCRContract, QCRImplementation, CostRecord, RevenueShare,
    QuackOffset, QCRPayment, EntropySource,
)
from .models import QuackToken
from .quack_titles import (
    practitioner_rank, rank_profit_share, RANK_PROFIT_SHARE,
    AERUKI_TONGUES_THRESHOLD,
)

ALEXI_ID = "alexi"
DISPATCHER_RATE = 0.20


# ── API key generation ────────────────────────────────────────────────────────

def generate_api_key(domain: str) -> str:
    """Generate a domain-locked API key."""
    token = secrets.token_hex(24)
    domain_hash = secrets.token_hex(4)
    return f"qcr_{domain_hash}_{token}"


# ── Revenue share calculation ─────────────────────────────────────────────────

def calculate_revenue_share(
    implementation: QCRImplementation,
    cost:           CostRecord,
    db:             Session,
) -> RevenueShare:
    """
    Calculate one period's revenue share for a single implementation.
    Pulls dispatcher_id from the parent contract.
    Practitioner pool percentage uses the highest active rank in the ledger.
    """
    revenue_cents = implementation.rate_cents
    total_cost    = cost.total_cents

    # Apportion costs across active implementations (simplified: equal split)
    impl_count = db.query(QCRImplementation).filter(
        QCRImplementation.active == True
    ).count() or 1
    cost_share = total_cost // impl_count

    profit = max(0, revenue_cents - cost_share)

    contract = db.query(QCRContract).filter(
        QCRContract.id == implementation.contract_id
    ).first()
    dispatcher_id = contract.dispatcher_id if contract else ALEXI_ID

    # Dispatcher share
    if dispatcher_id == ALEXI_ID:
        dispatcher_share = 0
    else:
        dispatcher_share = int(profit * DISPATCHER_RATE)

    # Practitioner pool: determined by highest active rank
    pool_pct    = _highest_rank_pool_pct(db)
    pool_cents  = int(profit * pool_pct)
    guild_share = profit - dispatcher_share - pool_cents

    period = datetime.now(timezone.utc).strftime("%Y-%m")

    share = RevenueShare(
        id                      = str(uuid4()),
        period                  = period,
        implementation_id       = implementation.id,
        revenue_cents           = revenue_cents,
        total_cost_cents        = cost_share,
        profit_cents            = profit,
        dispatcher_share_cents  = dispatcher_share,
        practitioner_pool_cents = pool_cents,
        practitioner_pool_pct   = pool_pct,
        guild_share_cents       = guild_share,
        settled                 = False,
    )
    db.add(share)
    db.commit()
    return share


def _highest_rank_pool_pct(db: Session) -> float:
    """
    Find the highest active rank across all practitioners in the Quack ledger.
    Returns the corresponding profit share percentage.
    """
    offsets = db.query(QuackOffset).filter(
        QuackOffset.quack_count > 0
    ).all()

    if not offsets:
        return RANK_PROFIT_SHARE["Wunae"]

    highest = 0.0
    for o in offsets:
        rank  = practitioner_rank(o.quack_count, o.tongues_worked)
        share = RANK_PROFIT_SHARE.get(rank, 0.0)
        if share > highest:
            highest = share

    return highest


# ── Quack offset ledger ───────────────────────────────────────────────────────

def update_quack_offsets(db: Session) -> None:
    """
    Refresh all practitioner Quack offset balances.
    Computes current H, updates each ledger entry, credits the balance.
    Called monthly at billing time.
    """
    h_now = shannon_entropy()

    # Sync from QuackToken ledger
    tokens = db.query(QuackToken).all()
    quack_by_artisan: dict[str, int] = {}
    for t in tokens:
        quack_by_artisan[t.holder_artisan_id] = (
            quack_by_artisan.get(t.holder_artisan_id, 0) + 1
        )

    for artisan_id, q_count in quack_by_artisan.items():
        offset = db.query(QuackOffset).filter(
            QuackOffset.practitioner_id == artisan_id
        ).first()

        # Count tongues worked (distinct tongue_name values)
        tongue_names = db.query(QuackToken.tongue_name).filter(
            QuackToken.holder_artisan_id == artisan_id
        ).distinct().all()
        t_worked = len(tongue_names)

        rank = practitioner_rank(q_count, t_worked)

        if offset is None:
            offset = QuackOffset(
                id               = str(uuid4()),
                practitioner_id  = artisan_id,
                quack_count      = q_count,
                tongues_worked   = t_worked,
                rank_title       = rank,
                baseline_h       = h_now,
                current_h        = h_now,
                base_value_cents = 100,
                offset_balance_cents = 0,
                last_updated     = datetime.utcnow(),
            )
            db.add(offset)
        else:
            if offset.baseline_h <= 0:
                offset.baseline_h = h_now
            offset.current_h    = h_now
            offset.quack_count  = q_count
            offset.tongues_worked = t_worked
            offset.rank_title   = rank
            offset.last_updated = datetime.utcnow()

            # Credit offset balance: quack_count × current_rate
            rate   = offset.current_offset_per_quack
            credit = int(q_count * rate)
            offset.offset_balance_cents = credit

    db.commit()


# ── Scheduled Roko institutional check ───────────────────────────────────────

def run_roko_contract_checks(db: Session) -> list[dict]:
    """
    Run Roko's institutional assessment against all active contracts.
    Called on a schedule (daily). Returns a list of assessment summaries.
    Revokes contracts where practice is found impossible to maintain.
    """
    from .roko import assess_site

    active_contracts = db.query(QCRContract).filter(
        QCRContract.status == "active"
    ).all()

    results = []
    for contract in active_contracts:
        # Simplified flag extraction — in production, augmented by content scan
        # and manual reports. Here we check for known revocation flags in notes.
        flags = _extract_flags(contract)
        assessment = assess_site(
            domain      = _primary_domain(contract, db),
            contract_id = contract.id,
            flags       = flags,
        )

        contract.roko_last_checked = datetime.utcnow()
        contract.roko_status       = assessment.gate

        if not assessment.practice_viable:
            contract.status           = "revoked"
            contract.revoked_at       = datetime.utcnow()
            contract.revocation_reason = "; ".join(assessment.observations)
            # Deactivate all implementations
            db.query(QCRImplementation).filter(
                QCRImplementation.contract_id == contract.id
            ).update({"active": False})

        results.append({
            "contract_id":     contract.id,
            "domain":          assessment.domain,
            "gate":            assessment.gate,
            "practice_viable": assessment.practice_viable,
            "observations":    assessment.observations,
        })

    db.commit()
    return results


def _extract_flags(contract: QCRContract) -> dict:
    """Parse flags from contract notes JSON if present."""
    if not contract.notes:
        return {}
    try:
        notes = json.loads(contract.notes)
        if isinstance(notes, dict) and "roko_flags" in notes:
            return notes["roko_flags"]
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _primary_domain(contract: QCRContract, db: Session) -> str:
    impl = db.query(QCRImplementation).filter(
        QCRImplementation.contract_id == contract.id
    ).first()
    return impl.domain if impl else "unknown"


# ── Invoice generation ────────────────────────────────────────────────────────

def generate_invoice(
    implementation: QCRImplementation,
    period:         str,
    db:             Session,
) -> QCRPayment:
    """Create a pending invoice for a billing period."""
    offset = db.query(QuackOffset).filter(
        QuackOffset.practitioner_id == implementation.contract.client_id
    ).first()

    quack_offset_cents = 0
    if offset and offset.offset_balance_cents > 0:
        quack_offset_cents = min(offset.offset_balance_cents, implementation.rate_cents)

    card_cents    = implementation.rate_cents - quack_offset_cents
    method        = "quack_offset" if card_cents == 0 else (
                    "mixed" if quack_offset_cents > 0 else "card")

    payment = QCRPayment(
        id                 = str(uuid4()),
        implementation_id  = implementation.id,
        period             = period,
        amount_cents       = implementation.rate_cents,
        method             = method,
        quack_offset_cents = quack_offset_cents,
        status             = "pending",
    )
    db.add(payment)

    # Deduct from offset balance
    if offset and quack_offset_cents > 0:
        offset.offset_balance_cents -= quack_offset_cents

    db.commit()
    return payment

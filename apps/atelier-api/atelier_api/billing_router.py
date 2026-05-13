"""
billing_router.py — Guild billing API

POST /v1/billing/contracts          — create a QCR contract (steward only)
POST /v1/billing/implementations    — add an implementation to a contract
GET  /v1/billing/contracts          — list contracts (steward only)
GET  /v1/billing/contracts/{id}     — get contract detail
POST /v1/billing/run-cycle          — run monthly billing cycle (admin only)
POST /v1/billing/roko-check         — run Roko contract checks now (steward only)
GET  /v1/billing/offsets            — list Quack offset ledger
GET  /v1/billing/offsets/{id}       — get one practitioner's offset record
POST /v1/billing/entropy/register   — register an entropy source (Salt steward)
GET  /v1/billing/entropy            — list registered entropy sources
GET  /v1/billing/field              — Shannon H + field metrics
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .qcr_models_append import (
    QCRContract, QCRImplementation, CostRecord, RevenueShare,
    QuackOffset, QCRPayment, EntropySource, Department,
)
from .billing import (
    generate_api_key, calculate_revenue_share, update_quack_offsets,
    run_roko_contract_checks, generate_invoice, ALEXI_ID,
)
from .intel import shannon_entropy, tongue_count
from .quack_titles import practitioner_rank, rank_profit_share

router = APIRouter()


# ── Auth ──────────────────────────────────────────────────────────────────────

def _require_steward(
    x_artisan_id:   Optional[str] = Header(default=None),
    authorization:  Optional[str] = Header(default=None),
) -> str:
    """Minimal steward check — mirrors existing auth pattern."""
    if authorization and authorization.startswith("Bearer "):
        try:
            from .auth import decode_auth_token
            from .core.config import load_settings
            claims = decode_auth_token(
                token  = authorization[len("Bearer "):].strip(),
                secret = load_settings().auth_token_secret,
            )
            return claims.actor_id
        except Exception:
            pass
    if x_artisan_id and x_artisan_id.strip():
        return x_artisan_id.strip()
    raise HTTPException(401, "missing_artisan_id")


def _require_admin(artisan_id: str = Depends(_require_steward)) -> str:
    """For now, only Alexi is admin."""
    if artisan_id != ALEXI_ID:
        raise HTTPException(403, "admin_only")
    return artisan_id


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContractIn(BaseModel):
    client_id:                str
    tier:                     str = "qcr_tce"
    non_erasure_acknowledged: bool = False
    notes:                    Optional[str] = None

class ImplementationIn(BaseModel):
    contract_id: str
    domain:      str
    tier:        str   = "qcr_tce"
    rate_cents:  int   = 3500
    notes:       Optional[str] = None

class ContractOut(BaseModel):
    id:                       str
    dispatcher_id:            str
    client_id:                str
    tier:                     str
    status:                   str
    signed_at:                str
    non_erasure_acknowledged: bool
    roko_status:              Optional[str]
    implementation_count:     int

class ImplementationOut(BaseModel):
    id:          str
    contract_id: str
    domain:      str
    api_key:     str
    tier:        str
    rate_cents:  int
    active:      bool

class CostIn(BaseModel):
    period:              str
    energy_cents:        int = 0
    infra_cents:         int = 0
    sulphur_wages_cents: int = 0
    mercury_wages_cents: int = 0
    salt_wages_cents:    int = 0
    qqees_credit_cents:  int = 0
    notes:               Optional[str] = None

class EntropySourceIn(BaseModel):
    name:        str
    source_type: str   # "garden" | "theatrical"
    department:  str   # "Salt" | "Sulphur"
    description: Optional[str] = None

class OffsetOut(BaseModel):
    practitioner_id:      str
    quack_count:          int
    tongues_worked:       int
    rank_title:           str
    baseline_h:           float
    current_h:            float
    offset_balance_cents: int
    offset_per_quack:     float
    last_updated:         str


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.post("/contracts", response_model=ContractOut)
def create_contract(
    payload:    ContractIn,
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> ContractOut:
    contract = QCRContract(
        id                       = str(uuid4()),
        dispatcher_id            = artisan_id,
        client_id                = payload.client_id,
        tier                     = payload.tier,
        status                   = "active",
        non_erasure_acknowledged = payload.non_erasure_acknowledged,
        notes                    = payload.notes,
    )
    db.add(contract)
    db.commit()
    return _contract_out(contract, db)


@router.post("/implementations", response_model=ImplementationOut)
def add_implementation(
    payload:    ImplementationIn,
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> ImplementationOut:
    contract = db.query(QCRContract).filter(QCRContract.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(404, "contract_not_found")
    if contract.dispatcher_id != artisan_id and artisan_id != ALEXI_ID:
        raise HTTPException(403, "not_your_contract")

    impl = QCRImplementation(
        id           = str(uuid4()),
        contract_id  = payload.contract_id,
        domain       = payload.domain.lower().strip(),
        api_key      = generate_api_key(payload.domain),
        tier         = payload.tier,
        rate_cents   = payload.rate_cents,
        active       = True,
        notes        = payload.notes,
    )
    db.add(impl)
    db.commit()
    return _impl_out(impl)


@router.get("/contracts", response_model=list[ContractOut])
def list_contracts(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> list[ContractOut]:
    if artisan_id == ALEXI_ID:
        rows = db.query(QCRContract).all()
    else:
        rows = db.query(QCRContract).filter(
            QCRContract.dispatcher_id == artisan_id
        ).all()
    return [_contract_out(r, db) for r in rows]


@router.get("/contracts/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: str,
    artisan_id:  str     = Depends(_require_steward),
    db:          Session = Depends(get_db),
) -> ContractOut:
    row = db.query(QCRContract).filter(QCRContract.id == contract_id).first()
    if not row:
        raise HTTPException(404, "not_found")
    if row.dispatcher_id != artisan_id and artisan_id != ALEXI_ID:
        raise HTTPException(403, "forbidden")
    return _contract_out(row, db)


# ── Billing cycle ─────────────────────────────────────────────────────────────

@router.post("/run-cycle")
def run_billing_cycle(
    cost_in:    CostIn,
    artisan_id: str     = Depends(_require_admin),
    db:         Session = Depends(get_db),
) -> dict:
    """Run the monthly billing cycle: cost record, revenue shares, offset refresh."""
    cost = CostRecord(
        id                  = str(uuid4()),
        period              = cost_in.period,
        energy_cents        = cost_in.energy_cents,
        infra_cents         = cost_in.infra_cents,
        sulphur_wages_cents = cost_in.sulphur_wages_cents,
        mercury_wages_cents = cost_in.mercury_wages_cents,
        salt_wages_cents    = cost_in.salt_wages_cents,
        qqees_credit_cents  = cost_in.qqees_credit_cents,
        notes               = cost_in.notes,
    )
    db.add(cost)
    db.commit()

    impls = db.query(QCRImplementation).filter(
        QCRImplementation.active == True
    ).all()

    shares = []
    for impl in impls:
        share = calculate_revenue_share(impl, cost, db)
        invoice = generate_invoice(impl, cost_in.period, db)
        shares.append({
            "implementation": impl.domain,
            "revenue_cents":  share.revenue_cents,
            "profit_cents":   share.profit_cents,
            "dispatcher_share_cents":  share.dispatcher_share_cents,
            "practitioner_pool_cents": share.practitioner_pool_cents,
            "guild_share_cents":       share.guild_share_cents,
            "invoice_status": invoice.status,
        })

    update_quack_offsets(db)

    return {
        "period":           cost_in.period,
        "implementations":  len(impls),
        "shares":           shares,
        "shannon_h":        shannon_entropy(),
    }


@router.post("/roko-check")
def trigger_roko_check(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> dict:
    """Trigger Roko institutional assessment across all active contracts."""
    results = run_roko_contract_checks(db)
    revoked = [r for r in results if not r["practice_viable"]]
    return {
        "checked":  len(results),
        "revoked":  len(revoked),
        "results":  results,
    }


# ── Revenue shares ────────────────────────────────────────────────────────────

@router.get("/shares")
def list_revenue_shares(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> list[dict]:
    rows = db.query(RevenueShare).order_by(RevenueShare.period.desc()).limit(200).all()
    return [
        {
            "id":                      r.id,
            "period":                  r.period,
            "implementation_id":       r.implementation_id,
            "revenue_cents":           r.revenue_cents,
            "total_cost_cents":        r.total_cost_cents,
            "profit_cents":            r.profit_cents,
            "dispatcher_share_cents":  r.dispatcher_share_cents,
            "practitioner_pool_cents": r.practitioner_pool_cents,
            "practitioner_pool_pct":   r.practitioner_pool_pct,
            "guild_share_cents":       r.guild_share_cents,
            "settled":                 r.settled,
        }
        for r in rows
    ]


# ── Quack offsets ─────────────────────────────────────────────────────────────

@router.get("/offsets", response_model=list[OffsetOut])
def list_offsets(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> list[OffsetOut]:
    rows = db.query(QuackOffset).all()
    return [_offset_out(r) for r in rows]


@router.post("/offsets/refresh")
def refresh_offsets(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> dict:
    """Recompute all Quack offset balances from the current ledger and H value."""
    update_quack_offsets(db)
    count = db.query(QuackOffset).count()
    return {"refreshed": count, "shannon_h": shannon_entropy()}


@router.get("/offsets/{practitioner_id}", response_model=OffsetOut)
def get_offset(practitioner_id: str, db: Session = Depends(get_db)) -> OffsetOut:
    row = db.query(QuackOffset).filter(
        QuackOffset.practitioner_id == practitioner_id
    ).first()
    if not row:
        raise HTTPException(404, "not_found")
    return _offset_out(row)


# ── Entropy sources ───────────────────────────────────────────────────────────

@router.post("/entropy/register")
def register_entropy_source(
    payload:    EntropySourceIn,
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> dict:
    source = EntropySource(
        id            = str(uuid4()),
        name          = payload.name,
        source_type   = payload.source_type,
        department    = payload.department,
        description   = payload.description,
        registered_by = artisan_id,
    )
    db.add(source)
    db.commit()
    return {"id": source.id, "name": source.name, "active": source.active}


@router.get("/entropy")
def list_entropy_sources(
    artisan_id: str     = Depends(_require_steward),
    db:         Session = Depends(get_db),
) -> list[dict]:
    sources = db.query(EntropySource).filter(EntropySource.active == True).all()
    return [
        {
            "id":            s.id,
            "name":          s.name,
            "source_type":   s.source_type,
            "department":    s.department,
            "bits":          s.entropy_bits_contributed,
            "last_noise_at": s.last_noise_at.isoformat() if s.last_noise_at else None,
        }
        for s in sources
    ]


# ── Field metrics (public) ────────────────────────────────────────────────────

@router.get("/field")
def field_metrics() -> dict:
    h  = shannon_entropy()
    tc = tongue_count()
    return {
        "shannon_h":       h,
        "tongue_count":    tc,
        "max_rank_attainable": "Aeruki" if tc >= 200 else (
            "Nashykawunae" if tc >= 38 else "Shykawunae"
        ),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _contract_out(c: QCRContract, db: Session) -> ContractOut:
    impl_count = db.query(QCRImplementation).filter(
        QCRImplementation.contract_id == c.id
    ).count()
    return ContractOut(
        id                       = c.id,
        dispatcher_id            = c.dispatcher_id,
        client_id                = c.client_id,
        tier                     = c.tier,
        status                   = c.status,
        signed_at                = c.signed_at.isoformat(),
        non_erasure_acknowledged = c.non_erasure_acknowledged,
        roko_status              = c.roko_status,
        implementation_count     = impl_count,
    )

def _impl_out(i: QCRImplementation) -> ImplementationOut:
    return ImplementationOut(
        id          = i.id,
        contract_id = i.contract_id,
        domain      = i.domain,
        api_key     = i.api_key,
        tier        = i.tier,
        rate_cents  = i.rate_cents,
        active      = i.active,
    )

def _offset_out(o: QuackOffset) -> OffsetOut:
    return OffsetOut(
        practitioner_id      = o.practitioner_id,
        quack_count          = o.quack_count,
        tongues_worked       = o.tongues_worked,
        rank_title           = o.rank_title,
        baseline_h           = o.baseline_h,
        current_h            = o.current_h,
        offset_balance_cents = o.offset_balance_cents,
        offset_per_quack     = round(o.current_offset_per_quack, 2),
        last_updated         = o.last_updated.isoformat(),
    )

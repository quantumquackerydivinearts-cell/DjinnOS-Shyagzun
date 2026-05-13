"""
qqees_router.py — QQEES HTTP API

Endpoints
---------
GET  /v1/qqees/pool              — public pool status (H, diversity, uptime)
POST /v1/qqees/source/register   — register an entropy source (Salt dept)
POST /v1/qqees/contribute        — submit entropy from a registered source
POST /v1/qqees/entropy           — draw N certified bytes (requires credit api_key)
POST /v1/qqees/credit/purchase   — purchase entropy credits
GET  /v1/qqees/credit/balance    — remaining bytes for a given api_key
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .qqees import (
    pool_status,
    mix_contribution,
    serve_entropy,
    certify,
    contribute_from_garden,
    contribute_from_theatrical,
    contribute_from_bok,
    contribute_from_orrery,
)
from .qcr_models_append import EntropySource, EntropyContribution, EntropyCredit

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SourceRegisterIn(BaseModel):
    name:         str
    source_type:  str = Field(pattern="^(garden|theatrical|bok|orrery)$")
    department:   str = Field(pattern="^(salt|sulphur|mercury)$")
    description:  Optional[str] = None
    registered_by: str


class ContributeIn(BaseModel):
    source_id:   str
    source_type: str = Field(pattern="^(garden|theatrical|bok|orrery)$")
    raw_hex:     str = Field(description="hex-encoded raw entropy bytes")


class EntropyRequestIn(BaseModel):
    n_bytes:  int  = Field(ge=1, le=65536)
    api_key:  str


class CreditPurchaseIn(BaseModel):
    holder_id:    str
    bytes_wanted: int = Field(ge=1024, le=10_485_760)


# ── Pool status ───────────────────────────────────────────────────────────────

@router.get("/pool")
def get_pool_status():
    return pool_status()


# ── Source registration ───────────────────────────────────────────────────────

@router.post("/source/register", status_code=201)
def register_source(body: SourceRegisterIn, db: Session = Depends(get_db)):
    src = EntropySource(
        id            = str(uuid4()),
        name          = body.name,
        source_type   = body.source_type,
        department    = body.department,
        description   = body.description,
        registered_by = body.registered_by,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return {"id": src.id, "name": src.name, "source_type": src.source_type}


# ── Entropy contribution ──────────────────────────────────────────────────────

@router.post("/contribute")
def contribute(body: ContributeIn, db: Session = Depends(get_db)):
    src = db.query(EntropySource).filter(
        EntropySource.id == body.source_id,
        EntropySource.active == True,
    ).first()
    if src is None:
        raise HTTPException(404, "Source not found or inactive")

    try:
        raw = bytes.fromhex(body.raw_hex)
    except ValueError:
        raise HTTPException(422, "raw_hex must be valid hexadecimal")

    h_after = mix_contribution(raw, body.source_type, body.source_id)

    contribution = EntropyContribution(
        id           = str(uuid4()),
        source_id    = body.source_id,
        raw_bytes    = len(raw),
        pool_h_after = h_after,
        source_type  = body.source_type,
    )
    src.last_noise_at = datetime.now(timezone.utc)
    src.entropy_bits_contributed += len(raw) * 8
    db.add(contribution)
    db.commit()

    return {"pool_h": h_after, "bytes_mixed": len(raw)}


# ── Serve entropy ─────────────────────────────────────────────────────────────

@router.post("/entropy")
def draw_entropy(body: EntropyRequestIn, db: Session = Depends(get_db)):
    credit = db.query(EntropyCredit).filter(
        EntropyCredit.api_key == body.api_key,
    ).first()
    if credit is None:
        raise HTTPException(403, "Invalid api_key")
    if credit.bytes_remaining < body.n_bytes:
        raise HTTPException(402, "Insufficient entropy credits")
    if credit.expires_at and datetime.now(timezone.utc) > credit.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(402, "Credit package expired")

    entropy_bytes, h = serve_entropy(body.n_bytes)
    cert = certify(entropy_bytes)

    credit.bytes_remaining -= body.n_bytes
    db.commit()

    return {
        "entropy_hex":   entropy_bytes.hex(),
        "certificate":   cert.to_dict(),
        "bytes_remaining": credit.bytes_remaining,
    }


# ── Credit purchase ───────────────────────────────────────────────────────────

@router.post("/credit/purchase", status_code=201)
def purchase_credit(body: CreditPurchaseIn, db: Session = Depends(get_db)):
    api_key = f"qqees_{secrets.token_hex(24)}"
    credit = EntropyCredit(
        id              = str(uuid4()),
        holder_id       = body.holder_id,
        bytes_remaining = body.bytes_wanted,
        bytes_purchased = body.bytes_wanted,
        api_key         = api_key,
    )
    db.add(credit)
    db.commit()
    return {
        "api_key":        api_key,
        "bytes_purchased": body.bytes_wanted,
        "holder_id":      body.holder_id,
    }


# ── Credit balance ────────────────────────────────────────────────────────────

@router.get("/credit/balance")
def credit_balance(api_key: str, db: Session = Depends(get_db)):
    credit = db.query(EntropyCredit).filter(
        EntropyCredit.api_key == api_key
    ).first()
    if credit is None:
        raise HTTPException(404, "api_key not found")
    return {
        "holder_id":       credit.holder_id,
        "bytes_remaining": credit.bytes_remaining,
        "bytes_purchased": credit.bytes_purchased,
        "expires_at":      credit.expires_at,
    }

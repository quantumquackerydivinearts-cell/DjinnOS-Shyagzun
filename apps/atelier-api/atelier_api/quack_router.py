"""
quack_router.py — Quack Framework API
======================================
A Quack is a named, fully enumerated Shygazun tongue extension, earned by
performing Wunashako until the BreathOfKo state genuinely transforms, then
proposing a tongue that follows (or artfully breaks) the phonemic logic and
factorization geometry of the byte table.

The byte table is the common ledger. Every minted Quack extends the language
for everyone while the holder owns the proof of contribution.

Endpoints
---------
POST /v1/quack/propose           — submit a tongue extension (auth required)
POST /v1/quack/mint/{id}         — mint a proposal into a Quack (author or steward)
POST /v1/quack/genesis           — seed tongues 1–N as Alexi's genesis Quacks (admin gate)
GET  /v1/quack/ledger            — list all minted Quacks (public)
GET  /v1/quack/ledger/{number}   — get a specific Quack by tongue number (public)
GET  /v1/quack/proposals         — list proposals for the current artisan (auth required)
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .models import QuackToken, TongueProposal

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class TongueEntryIn(BaseModel):
    symbol:  str
    meaning: str


class QuackProposeIn(BaseModel):
    tongue_number: int                          = Field(..., gt=0)
    tongue_name:   str                          = Field(..., min_length=1)
    entries:       list[TongueEntryIn]          = Field(..., min_length=1)
    breath_start:  Optional[dict[str, Any]]     = None
    notes:         str                          = ""


class QuackMintIn(BaseModel):
    breath_end: Optional[dict[str, Any]] = None


class TongueEntryOut(BaseModel):
    symbol:  str
    meaning: str


class ProposalOut(BaseModel):
    id:            str
    artisan_id:    str
    tongue_number: int
    tongue_name:   str
    entry_count:   int
    status:        str
    proposed_at:   str
    notes:         str


class QuackOut(BaseModel):
    id:               str
    tongue_number:    int
    tongue_name:      str
    holder_artisan_id: str
    entry_count:      int
    entries:          list[TongueEntryOut]
    breath_start:     Optional[dict[str, Any]]
    breath_end:       Optional[dict[str, Any]]
    breath_diff:      Optional[dict[str, Any]]
    minted_at:        str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_artisan(
    x_artisan_id: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Minimal artisan identity resolution — mirrors the main app's mixed-mode."""
    if authorization and authorization.startswith("Bearer "):
        try:
            from .auth import decode_auth_token
            from .core.config import load_settings
            claims = decode_auth_token(
                token=authorization[len("Bearer "):].strip(),
                secret=load_settings().auth_token_secret,
            )
            return claims.actor_id
        except Exception:
            pass
    if x_artisan_id and x_artisan_id.strip():
        return x_artisan_id.strip()
    raise HTTPException(status_code=401, detail="missing_artisan_id")


def _breath_diff(start: Optional[dict], end: Optional[dict]) -> Optional[dict]:
    """Compute the differential between two BreathOfKo snapshots."""
    if not start or not end:
        return None
    try:
        az_s = start.get("azoth", [0.0, 0.0])
        az_e = end.get("azoth",   [0.0, 0.0])
        azoth_distance = math.sqrt(
            (az_e[0] - az_s[0]) ** 2 + (az_e[1] - az_s[1]) ** 2
        )
        coil_delta = end.get("coil_position", 6.0) - start.get("coil_position", 6.0)
        games_delta = end.get("games_played", 0) - start.get("games_played", 0)
        return {
            "azoth_distance": round(azoth_distance, 6),
            "coil_delta":     round(coil_delta,     4),
            "games_delta":    games_delta,
            "start_boundedness": start.get("boundedness"),
            "end_boundedness":   end.get("boundedness"),
        }
    except Exception:
        return None


def _row_to_quack_out(row: QuackToken) -> QuackOut:
    entries_raw = json.loads(row.entries_json or "[]")
    entries = [TongueEntryOut(symbol=e["symbol"], meaning=e["meaning"])
               for e in entries_raw if "symbol" in e and "meaning" in e]
    return QuackOut(
        id=row.id,
        tongue_number=row.tongue_number,
        tongue_name=row.tongue_name,
        holder_artisan_id=row.holder_artisan_id,
        entry_count=row.entry_count,
        entries=entries,
        breath_start=json.loads(row.breath_start) if row.breath_start else None,
        breath_end=json.loads(row.breath_end)   if row.breath_end   else None,
        breath_diff=json.loads(row.breath_diff) if row.breath_diff  else None,
        minted_at=row.minted_at.isoformat(),
    )


def _row_to_proposal_out(row: TongueProposal) -> ProposalOut:
    entries = json.loads(row.entries_json or "[]")
    return ProposalOut(
        id=row.id,
        artisan_id=row.artisan_id,
        tongue_number=row.tongue_number,
        tongue_name=row.tongue_name,
        entry_count=len(entries),
        status=row.status,
        proposed_at=row.proposed_at.isoformat(),
        notes=row.notes or "",
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/propose")
def propose_tongue(
    payload: QuackProposeIn,
    artisan_id: str = Depends(_resolve_artisan),
    db: Session = Depends(get_db),
) -> ProposalOut:
    """Submit a tongue extension as a proposal. Returns the draft proposal."""
    # Tongue number must not already be minted.
    existing = db.query(QuackToken).filter(
        QuackToken.tongue_number == payload.tongue_number
    ).first()
    if existing:
        raise HTTPException(409, f"tongue {payload.tongue_number} already minted as '{existing.tongue_name}'")

    entries_json = json.dumps([
        {"symbol": e.symbol, "meaning": e.meaning}
        for e in payload.entries
    ])
    row = TongueProposal(
        id=str(uuid4()),
        artisan_id=artisan_id,
        tongue_number=payload.tongue_number,
        tongue_name=payload.tongue_name.strip(),
        entries_json=entries_json,
        breath_start=json.dumps(payload.breath_start) if payload.breath_start else None,
        notes=payload.notes or "",
        status="proposed",
        proposed_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_proposal_out(row)


@router.post("/mint/{proposal_id}")
def mint_quack(
    proposal_id: str,
    payload: QuackMintIn,
    artisan_id: str = Depends(_resolve_artisan),
    db: Session = Depends(get_db),
) -> QuackOut:
    """
    Mint a proposal into a Quack.  Only the proposal's author may mint it
    (or any steward).  Sets breath_end and computes the differential.
    """
    proposal = db.query(TongueProposal).filter(TongueProposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(404, "proposal_not_found")
    if proposal.artisan_id != artisan_id:
        # Allow stewards to mint on behalf — check role from DB
        from .models import ArtisanAccount
        acct = db.query(ArtisanAccount).filter(ArtisanAccount.artisan_id == artisan_id).first()
        if acct is None or acct.role != "steward":
            raise HTTPException(403, "only the proposal author or a steward may mint")
    if proposal.status == "minted":
        raise HTTPException(409, "proposal already minted")

    # Guard: tongue number still unoccupied.
    existing = db.query(QuackToken).filter(
        QuackToken.tongue_number == proposal.tongue_number
    ).first()
    if existing:
        raise HTTPException(409, f"tongue {proposal.tongue_number} already minted")

    bs = json.loads(proposal.breath_start) if proposal.breath_start else None
    be = payload.breath_end
    diff = _breath_diff(bs, be)

    entries = json.loads(proposal.entries_json or "[]")
    quack = QuackToken(
        id=str(uuid4()),
        tongue_number=proposal.tongue_number,
        tongue_name=proposal.tongue_name,
        holder_artisan_id=proposal.artisan_id,
        entry_count=len(entries),
        entries_json=proposal.entries_json,
        breath_start=proposal.breath_start,
        breath_end=json.dumps(be)   if be   else None,
        breath_diff=json.dumps(diff) if diff else None,
        proposal_id=proposal.id,
        minted_at=datetime.utcnow(),
    )
    db.add(quack)
    proposal.status = "minted"
    db.commit()
    db.refresh(quack)
    return _row_to_quack_out(quack)


@router.post("/genesis")
def seed_genesis(
    x_admin_gate_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """
    Seed Alexi's genesis Quacks (tongues 1–N) from the live byte table.
    Requires the admin gate token.  Idempotent — skips already-minted tongues.
    """
    from .core.config import load_settings
    settings = load_settings()
    if x_admin_gate_token != settings.admin_gate_code:
        raise HTTPException(403, "invalid_admin_gate")

    # Load byte table from the DjinnOS Shygazun kernel.
    _sanctum = "C:/DjinnOS/DjinnOS_Shyagzun"
    if _sanctum not in sys.path:
        sys.path.insert(0, _sanctum)
    try:
        from shygazun.kernel.constants.byte_table import byte_rows, tongues
    except ImportError as exc:
        raise HTTPException(503, f"byte_table unavailable: {exc}")

    rows = byte_rows()
    tongue_names = tongues()

    # Group entries by tongue (rows are dicts: decimal/binary/tongue/symbol/meaning).
    by_tongue: dict[str, list[dict]] = {}
    for entry in rows:
        tn = entry["tongue"] if isinstance(entry, dict) else entry.tongue
        sym = entry["symbol"] if isinstance(entry, dict) else entry.symbol
        mng = entry["meaning"] if isinstance(entry, dict) else entry.meaning
        if tn not in by_tongue:
            by_tongue[tn] = []
        by_tongue[tn].append({"symbol": sym, "meaning": mng})

    genesis_breath = json.dumps({
        "genesis": True,
        "note": "Pre-system. Tongue existed before the Quack framework.",
        "azoth": [0.0, 0.0],
        "coil_position": 6.0,
        "boundedness": "edge",
    })

    # Canonical tongue→number mapping.  Derived from the Tongue enum in types.rs.
    # Non-tongue byte table entries (Reserved, MetaTopology, MetaPhysics, Physics,
    # Chemistry) are intentionally excluded — they are not Quacks.
    TONGUE_NUMBERS: dict[str, int] = {
        "Lotus": 1,  "Rose": 2,    "Sakura": 3,    "Daisy": 4,
        "AppleBlossom": 5, "Aster": 6, "Grapevine": 7, "Cannabis": 8,
        "Dragon": 9, "Virus": 10, "Bacteria": 11, "Excavata": 12,
        "Archaeplastida": 13, "Myxozoa": 14, "Archaea": 15, "Protist": 16,
        "Immune": 17, "Neural": 18, "Serpent": 19, "Beast": 20,
        "Cherub": 21, "Chimera": 22, "Faerie": 23, "Djinn": 24,
        "Fold": 25,   "Topology": 26, "Phase": 27, "Gradient": 28,
        "Curvature": 29, "Prion": 30, "Blood": 31, "Moon": 32,
        "Koi": 33, "Rope": 34, "Hook": 35, "Fang": 36,
        "Circle": 37, "Ledger": 38,
    }
    tongue_number_map = TONGUE_NUMBERS

    minted = []
    skipped = []
    for tongue_name in tongue_names:
        entries = by_tongue.get(tongue_name, [])
        number = tongue_number_map.get(tongue_name)
        if number is None:
            continue

        existing = db.query(QuackToken).filter(QuackToken.tongue_number == number).first()
        if existing:
            skipped.append(tongue_name)
            continue

        quack = QuackToken(
            id=str(uuid4()),
            tongue_number=number,
            tongue_name=tongue_name,
            holder_artisan_id="alexi",
            entry_count=len(entries),
            entries_json=json.dumps(entries),
            breath_start=genesis_breath,
            breath_end=genesis_breath,
            breath_diff=json.dumps({"genesis": True, "azoth_distance": 0.0, "coil_delta": 0.0}),
            proposal_id=None,
            minted_at=datetime.utcnow(),
        )
        db.add(quack)
        minted.append(tongue_name)

    db.commit()
    return {"minted": minted, "skipped": skipped, "total": len(minted) + len(skipped)}


@router.get("/ledger")
def list_ledger(db: Session = Depends(get_db)) -> list[QuackOut]:
    """List all minted Quacks. Public."""
    rows = db.query(QuackToken).order_by(QuackToken.tongue_number).all()
    return [_row_to_quack_out(r) for r in rows]


@router.get("/ledger/{tongue_number}")
def get_quack(tongue_number: int, db: Session = Depends(get_db)) -> QuackOut:
    """Get a specific Quack by tongue number. Public."""
    row = db.query(QuackToken).filter(QuackToken.tongue_number == tongue_number).first()
    if row is None:
        raise HTTPException(404, f"tongue {tongue_number} not in ledger")
    return _row_to_quack_out(row)


@router.get("/proposals")
def list_proposals(
    artisan_id: str = Depends(_resolve_artisan),
    db: Session = Depends(get_db),
) -> list[ProposalOut]:
    """List this artisan's tongue proposals."""
    rows = db.query(TongueProposal).filter(
        TongueProposal.artisan_id == artisan_id
    ).order_by(TongueProposal.proposed_at.desc()).all()
    return [_row_to_proposal_out(r) for r in rows]
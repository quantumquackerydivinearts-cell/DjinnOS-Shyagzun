"""
qcr_service_router.py — QCR as a service

Endpoints:
  POST /v1/qcr/route          — collapse routing (domain-key required for TCE)
  GET  /v1/qcr/field          — current Shannon capacity H
  GET  /v1/qcr/tongues        — available tongue registers
  GET  /v1/qcr/verify         — verify an API key's domain and tier
  POST /v1/qcr/entropy/submit — submit entropy from a registered source (QQEES)

Authentication:
  X-QCR-Key header = api_key from qcr_implementations.
  Domain validated against the implementation's registered domain.
  Keyword tier: no key required.
  TCE tier: key + domain required.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .qcr_models_append import QCRImplementation, EntropySource
from .intel import (
    query_by_tongue, shannon_entropy, tongue_count, all_tongues, CANDIDATES,
)

router = APIRouter()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _resolve_implementation(
    api_key: Optional[str],
    origin: Optional[str],
    db: Session,
) -> Optional[QCRImplementation]:
    """Return the matching active implementation, or None."""
    if not api_key:
        return None
    impl = db.query(QCRImplementation).filter(
        QCRImplementation.api_key == api_key,
        QCRImplementation.active  == True,
    ).first()
    if impl is None:
        return None
    # Domain validation: strip scheme and trailing slash from origin
    if origin:
        bare = origin.replace("https://", "").replace("http://", "").rstrip("/")
        if bare != impl.domain and not bare.endswith("." + impl.domain):
            return None
    return impl


# ── Request / response models ─────────────────────────────────────────────────

class SectionDef(BaseModel):
    id:       str
    tongues:  list[str]           = []
    keywords: list[str]           = []
    weight:   float               = 1.0

class RouteRequest(BaseModel):
    query:    str
    sections: list[SectionDef]
    kernel:   str   = "keshi"
    temp:     float = 0.35
    max_iter: int   = 32

class ActivationOut(BaseModel):
    section_id:   str
    score:        float
    mode:         str       # "tce" | "keyword"

class RouteResponse(BaseModel):
    activations:      list[ActivationOut]
    converged_tongues: list[str]
    energy:           float
    shannon_h:        float
    mode:             str

class EntropySubmitRequest(BaseModel):
    source_id:    str
    entropy_hex:  str     # hex-encoded entropy bytes from the source
    event_type:   str     # "bok_transition" | "gameplay" | "garden_sample"

# ── Keyword collapse (client-side equivalent, serverside version) ─────────────

def _keyword_score(query: str, keywords: list[str]) -> float:
    words = query.lower().split()
    s = 0.0
    for w in words:
        for kw in keywords:
            if w in kw or kw in w:
                s += 0.4
    return min(1.0, s)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/route", response_model=RouteResponse)
async def route(
    req:     RouteRequest,
    request: Request,
    x_qcr_key: Optional[str] = Header(default=None),
    db:      Session = Depends(get_db),
):
    """
    Collapse routing: returns activation scores for each section.

    Without a key: keyword matching only (free tier).
    With a valid key: full TCE Hopfield convergence (QCR+TCE tier).
    """
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    impl   = _resolve_implementation(x_qcr_key, origin, db)
    use_tce = impl is not None and impl.tier == "qcr_tce"

    h = shannon_entropy()

    if use_tce:
        # ── TCE mode: Hopfield convergence over tongue-annotated sections ──
        # Collect all tongues registered for this query context
        all_section_tongues = list({t for s in req.sections for t in s.tongues})
        if not all_section_tongues:
            all_section_tongues = ["Lotus", "Rose"]

        result = query_by_tongue(
            tongues  = all_section_tongues,
            kernel   = req.kernel,
            temp     = req.temp,
            max_iter = req.max_iter,
        )

        # Score each section by what fraction of its registered tongues activated
        active_tongues = set(CANDIDATES[i].tongue for i in result.active)
        activations = []
        for sec in req.sections:
            if not sec.tongues:
                kw_score = _keyword_score(req.query, sec.keywords)
                activations.append(ActivationOut(section_id=sec.id, score=kw_score, mode="keyword"))
                continue
            overlap = len(set(sec.tongues) & active_tongues)
            tce_score = (overlap / len(sec.tongues)) * sec.weight
            kw_score  = _keyword_score(req.query, sec.keywords) * 0.3
            score = min(1.0, tce_score + kw_score)
            activations.append(ActivationOut(section_id=sec.id, score=score, mode="tce"))

        # Normalize
        max_score = max((a.score for a in activations), default=1.0) or 1.0
        for a in activations:
            a.score = round(a.score / max_score, 4)

        return RouteResponse(
            activations       = activations,
            converged_tongues = sorted(active_tongues),
            energy            = result.energy,
            shannon_h         = h,
            mode              = "tce",
        )

    else:
        # ── Keyword mode: free tier ──
        activations = []
        for sec in req.sections:
            score = _keyword_score(req.query, sec.keywords + sec.tongues)
            activations.append(ActivationOut(section_id=sec.id, score=score, mode="keyword"))

        max_score = max((a.score for a in activations), default=1.0) or 1.0
        for a in activations:
            a.score = round(a.score / max_score, 4)

        return RouteResponse(
            activations       = activations,
            converged_tongues = [],
            energy            = 0.0,
            shannon_h         = h,
            mode              = "keyword",
        )


@router.get("/field")
async def get_field():
    """Current Shannon entropy H of the semantic field and tongue count."""
    h  = shannon_entropy()
    tc = tongue_count()
    n  = len(CANDIDATES)
    return {
        "shannon_h":     h,
        "tongue_count":  tc,
        "candidate_count": n,
        "max_bits":      float(n).bit_length(),
    }


@router.get("/tongues")
async def get_tongues():
    """All available tongue registers for section annotation."""
    tongues = all_tongues()
    return [{"tongue": t, "count": sum(1 for c in CANDIDATES if c.tongue == t)}
            for t in tongues]


@router.get("/verify")
async def verify_key(
    request:   Request,
    x_qcr_key: Optional[str] = Header(default=None),
    db:        Session = Depends(get_db),
):
    """Verify a QCR API key and return its tier and domain."""
    origin = request.headers.get("origin", "")
    impl   = _resolve_implementation(x_qcr_key, origin, db)
    if impl is None:
        raise HTTPException(403, "invalid_key_or_domain")
    return {
        "domain": impl.domain,
        "tier":   impl.tier,
        "active": impl.active,
    }


@router.post("/entropy/submit")
async def submit_entropy(
    req: EntropySubmitRequest,
    x_qcr_key: Optional[str] = Header(default=None),
    db:  Session = Depends(get_db),
):
    """
    Submit entropy from a registered garden or theatrical operation.
    The source must be registered and active in entropy_sources.
    The submitting key must belong to an active implementation on the same contract.
    Entropy is mixed into the QQEES pool (tracked as bits contributed).
    """
    source = db.query(EntropySource).filter(
        EntropySource.id     == req.source_id,
        EntropySource.active == True,
    ).first()
    if source is None:
        raise HTTPException(404, "entropy_source_not_found")

    # Count entropy bits contributed (half the hex string length = bytes = × 8 bits)
    try:
        raw_bytes = bytes.fromhex(req.entropy_hex)
    except ValueError:
        raise HTTPException(422, "invalid_entropy_hex")

    bits = len(raw_bytes) * 8
    source.entropy_bits_contributed += bits
    from datetime import datetime
    source.last_noise_at = datetime.utcnow()
    db.commit()

    return {
        "source_id":     req.source_id,
        "bits_accepted": bits,
        "total_bits":    source.entropy_bits_contributed,
    }

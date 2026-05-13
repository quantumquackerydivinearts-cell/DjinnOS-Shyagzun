"""
roko_router.py — Roko API

POST /v1/roko/assess          — assess a Shygazun composition
GET  /v1/roko/gate-levels     — list all five gate levels with glosses
GET  /v1/roko/practitioner/{id} — structural profile from Quack ledger
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .models import QuackToken
from . import roko as _roko
from .quack_titles import practitioner_rank

router = APIRouter()

# ── Request / response models ─────────────────────────────────────────────────

class BoKIn(BaseModel):
    """BreathOfKo diff payload — matches the breath_diff shape in QuackToken."""
    azoth_distance:    float = 0.0
    coil_delta:        float = 0.0
    games_delta:       int   = 0
    start_boundedness: Optional[str] = None
    end_boundedness:   Optional[str] = None

class AssessRequest(BaseModel):
    text:              str
    practitioner_id:   str = ""
    bok:               Optional[BoKIn] = None   # BreathOfKo diff if available
    keshi_temp:        float = 0.45
    max_iter:          int   = 48

class FieldReadingOut(BaseModel):
    mode:        str
    energy:      float
    coherence:   float
    iterations:  int
    tongues:     list[str]
    top_symbols: list[str]

class DreamReadingOut(BaseModel):
    symbols:  list[str]
    tongues:  list[str]
    meaning:  str

class TokenOut(BaseModel):
    symbol:  str
    tongue:  str
    meaning: str

class BoKOut(BaseModel):
    azoth_distance:  float
    coil_delta:      float
    boundedness:     str
    games_delta:     int
    has_movement:    bool
    is_edge:         bool
    wunashakoun_signal: float

class AssessmentOut(BaseModel):
    text:           str
    recognized:     list[TokenOut]
    unrecognized:   int
    ground:         FieldReadingOut
    dream:          FieldReadingOut
    latent:         DreamReadingOut
    bok:            Optional[BoKOut]
    wunashakoun:    float
    gate:           str
    gate_gloss:     str
    shygazun_note:  str
    coherence:      float

class GateLevelOut(BaseModel):
    gate:  str
    gloss: str

class PractitionerProfileOut(BaseModel):
    practitioner_id:  str
    quack_count:      int
    rank_title:       str
    gate:             str
    gate_gloss:       str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _bok_out(b: _roko.BoKSnapshot) -> BoKOut:
    return BoKOut(
        azoth_distance     = b.azoth_distance,
        coil_delta         = b.coil_delta,
        boundedness        = b.boundedness,
        games_delta        = b.games_delta,
        has_movement       = b.has_movement,
        is_edge            = b.is_edge,
        wunashakoun_signal = b.wunashakoun_signal,
    )

def _assessment_out(a: _roko.CompositionAssessment) -> AssessmentOut:
    return AssessmentOut(
        text         = a.text,
        recognized   = [TokenOut(symbol=s, tongue=t, meaning=m) for s, t, m in a.recognized],
        unrecognized = a.unrecognized,
        ground       = FieldReadingOut(
            mode        = a.ground.mode,
            energy      = a.ground.energy,
            coherence   = a.ground.coherence,
            iterations  = a.ground.iterations,
            tongues     = a.ground.tongues,
            top_symbols = a.ground.top_symbols,
        ),
        dream        = FieldReadingOut(
            mode        = a.dream.mode,
            energy      = a.dream.energy,
            coherence   = a.dream.coherence,
            iterations  = a.dream.iterations,
            tongues     = a.dream.tongues,
            top_symbols = a.dream.top_symbols,
        ),
        latent       = DreamReadingOut(
            symbols = a.latent.symbols,
            tongues = a.latent.tongues,
            meaning = a.latent.meaning,
        ),
        bok          = _bok_out(a.bok) if a.bok else None,
        wunashakoun  = a.wunashakoun,
        gate         = a.gate,
        gate_gloss   = a.gate_gloss,
        shygazun_note = a.shygazun_note,
        coherence    = a.coherence,
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/assess", response_model=AssessmentOut)
def assess(req: AssessRequest, db: Session = Depends(get_db)):
    """
    Run Roko's structural assessment on a Shygazun composition.

    Two Hopfield passes are made:
    - Giann (T=0): the actual attractor the composition inhabits.
    - Keshi (T>0): the latent field it is reaching toward.

    If practitioner_id is provided, Quack count is loaded from the ledger
    to inform the gate level. Otherwise the assessment is made without
    practitioner context.
    """
    quack_count = 0
    rank_title  = "Wunashako"

    if req.practitioner_id:
        quack_count = db.query(QuackToken).filter(
            QuackToken.holder_artisan_id == req.practitioner_id
        ).count()
        rank_title = practitioner_rank(quack_count)

    bok = None
    if req.bok:
        bok = _roko.BoKSnapshot(
            azoth_distance = req.bok.azoth_distance,
            coil_delta     = req.bok.coil_delta,
            boundedness    = req.bok.end_boundedness or req.bok.start_boundedness or "bounded",
            games_delta    = req.bok.games_delta,
        )

    a = _roko.assess(
        text             = req.text,
        practitioner_id  = req.practitioner_id,
        quack_count      = quack_count,
        rank_title       = rank_title,
        bok              = bok,
        keshi_temp       = req.keshi_temp,
        max_iter         = req.max_iter,
    )
    return _assessment_out(a)


@router.get("/gate-levels", response_model=list[GateLevelOut])
def gate_levels():
    """All five Shygazun gate levels with composition glosses."""
    return [
        GateLevelOut(gate=gate, gloss=gloss)
        for gate, gloss in _roko.GATE_GLOSSES.items()
    ]


@router.get("/practitioner/{practitioner_id}", response_model=PractitionerProfileOut)
def practitioner_profile(practitioner_id: str, db: Session = Depends(get_db)):
    """
    Structural profile for a practitioner based on their Quack ledger.
    Gate level is derived from Quack count and rank — no composition
    history is needed for this endpoint.
    """
    quack_count = db.query(QuackToken).filter(
        QuackToken.holder_artisan_id == practitioner_id
    ).count()
    rank_title = practitioner_rank(quack_count)

    # Gate level from Quack count alone (no composition history available here)
    gate = _roko.GATE_TIWU
    if quack_count >= 100:
        gate = _roko.GATE_FYKO
    elif quack_count >= 20:
        gate = _roko.GATE_TAWU
    elif quack_count >= 5:
        gate = _roko.GATE_TAWU
    elif quack_count >= 1:
        gate = _roko.GATE_TIWU

    return PractitionerProfileOut(
        practitioner_id = practitioner_id,
        quack_count     = quack_count,
        rank_title      = rank_title,
        gate            = gate,
        gate_gloss      = _roko.GATE_GLOSSES[gate],
    )


# ── Institutional site assessment ─────────────────────────────────────────────

class SiteAssessRequest(BaseModel):
    domain:      str
    contract_id: str
    flags:       Optional[dict] = None

class SiteAssessmentOut(BaseModel):
    domain:          str
    contract_id:     str
    gate:            str
    gate_gloss:      str
    practice_viable: bool
    observations:    list[str]
    checked_at:      str

@router.post("/site-assess", response_model=SiteAssessmentOut)
def site_assess(req: SiteAssessRequest):
    """
    Roko institutional assessment: does this site's environment permit
    open Wunashakoun practice? Called by the scheduled billing job and
    on-demand by stewards.
    """
    a = _roko.assess_site(
        domain      = req.domain,
        contract_id = req.contract_id,
        flags       = req.flags,
    )
    return SiteAssessmentOut(
        domain          = a.domain,
        contract_id     = a.contract_id,
        gate            = a.gate,
        gate_gloss      = a.gate_gloss,
        practice_viable = a.practice_viable,
        observations    = a.observations,
        checked_at      = a.checked_at,
    )

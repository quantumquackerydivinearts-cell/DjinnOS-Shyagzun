"""
kobra_vm_router.py — Kobra VM API

POST /v1/kobra/run         — run Kobra source through the Orrery
POST /v1/kobra/run-file    — run a .ko file by path (dev/local only)
GET  /v1/kobra/suite       — run all known .ko scenes and return comparison
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .kobra_vm import (
    kobra_run, kobra_run_file, run_suite, comparison_table,
    interpret, KobraResult, LAYER_KOBRA_MEANING,
)

router = APIRouter()

# ── Known scene paths (relative to repo root) ─────────────────────────────────

import os
_REPO_ROOT = Path(__file__).parent.parent.parent.parent

KNOWN_SCENES = [
    _REPO_ROOT / "productions/kos-labyrnth/scenes/lapidus/wiltoll_lane.scene.ko",
    _REPO_ROOT / "productions/kos-labyrnth/scenes/lapidus/home_morning.scene.ko",
    _REPO_ROOT / "productions/kos-labyrnth/scenes/lapidus/home_apothecary.scene.ko",
    _REPO_ROOT / "productions/kos-labyrnth/scenes/sulphera/entry.scene.ko",
]

# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    source: str
    name:   str = "<source>"

class RunFileRequest(BaseModel):
    path: str

class TokenOut(BaseModel):
    addr:    int
    symbol:  str
    tongue:  str
    meaning: str

class LayerReadingOut(BaseModel):
    rose:        str
    compound:    str
    primary:     str
    destination: str
    purpose:     str
    kobra_meaning: str
    fired:       bool

class ElementalSig(BaseModel):
    Shak: int
    Puf:  int
    Mel:  int
    Zot:  int
    unknown: int

class KobraResultOut(BaseModel):
    source_name:     str
    token_count:     int
    unique_addrs:    int
    layers_fired:    int
    final_energy:    float
    fired_layers:    list[LayerReadingOut]
    elemental_sig:   ElementalSig
    interpretation:  str

class SuiteOut(BaseModel):
    scenes:    list[KobraResultOut]
    table:     str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _result_out(r: KobraResult) -> KobraResultOut:
    sig = r.elemental_signature

    all_layers = r.fired_layers + r.unfired_layers
    layers_out = [
        LayerReadingOut(
            rose          = lr.rose,
            compound      = lr.compound,
            primary       = lr.primary,
            destination   = lr.destination,
            purpose       = lr.purpose,
            kobra_meaning = LAYER_KOBRA_MEANING.get(lr.rose, lr.purpose),
            fired         = lr.fired,
        )
        for lr in sorted(all_layers, key=lambda l: next(
            (i for i, L in enumerate(r.trace.firings) if L.rose == l.rose), 99
        ))
    ]

    return KobraResultOut(
        source_name   = r.source_name,
        token_count   = r.token_count,
        unique_addrs  = r.unique_addrs,
        layers_fired  = r.layers_fired,
        final_energy  = r.final_energy,
        fired_layers  = [l for l in layers_out if l.fired],
        elemental_sig = ElementalSig(
            Shak    = sig.get("Shak", 0),
            Puf     = sig.get("Puf", 0),
            Mel     = sig.get("Mel", 0),
            Zot     = sig.get("Zot", 0),
            unknown = sig.get("?", 0),
        ),
        interpretation = interpret(r),
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/run", response_model=KobraResultOut)
async def run_source(req: RunRequest):
    """Run Kobra source text through the Orrery VM."""
    result = kobra_run(req.source, req.name)
    return _result_out(result)


@router.post("/run-file", response_model=KobraResultOut)
async def run_file(req: RunFileRequest):
    """Run a .ko file by path. Dev/local use only."""
    p = Path(req.path)
    if not p.exists():
        # Try relative to repo root
        p = _REPO_ROOT / req.path
    if not p.exists():
        raise HTTPException(404, f"file not found: {req.path}")
    if p.suffix not in ('.ko',):
        raise HTTPException(422, "only .ko files accepted")
    result = kobra_run_file(p)
    return _result_out(result)


@router.get("/suite", response_model=SuiteOut)
async def run_known_suite():
    """
    Run all known Ko's Labyrinth scenes through the VM and return
    the comparison table plus per-scene results.
    """
    existing = [p for p in KNOWN_SCENES if p.exists()]
    if not existing:
        raise HTTPException(503, "no scene files found")

    results = run_suite(existing)
    table   = comparison_table(results)

    return SuiteOut(
        scenes = [_result_out(r) for r in results],
        table  = table,
    )

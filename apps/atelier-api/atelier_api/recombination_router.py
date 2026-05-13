"""
recombination_router.py — Orrery API

POST /v1/recombination/run          — run input through all 12 layers
POST /v1/recombination/probe        — probe which layers activate (no transformation)
GET  /v1/recombination/layers       — the 12 layer definitions
POST /v1/recombination/step/{rose}  — single-layer step by Rose numeral name
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .recombination import (
    LAYERS, RecombLayer, run, probe, recombine_step, check_cue,
    active_layers, element_candidates, candidate_element,
    _ADDR_TO_IDX,
)
from .intel import CANDIDATES, N, build_weight_matrix, hopfield_converge
import numpy as np

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    addrs:    list[int]
    temp:     float = 0.35
    max_iter: int   = 32

class ProbeRequest(BaseModel):
    addrs:    list[int]
    temp:     float = 0.35
    max_iter: int   = 32

class StepRequest(BaseModel):
    addrs:    list[int]
    temp:     float = 0.35
    alpha:    Optional[float] = None
    max_iter: int   = 24

class CueGlyphOut(BaseModel):
    addr:    int
    symbol:  str
    tongue:  str
    meaning: str
    element: Optional[str]

class LayerOut(BaseModel):
    rose:         str
    rose_index:   int
    compound:     str
    compound_addr: int
    primary:      str
    destination:  str
    cue_glyphs:   list[CueGlyphOut]
    purpose:      str

class FiringOut(BaseModel):
    rose:        str
    rose_index:  int
    compound:    str
    primary:     str
    destination: str
    purpose:     str
    fired:       bool
    active_count: int
    energy:      float

class RunOut(BaseModel):
    input_addrs:  list[int]
    firings:      list[FiringOut]
    final_active: list[int]
    final_energy: float
    layers_fired: int

class ProbeLayerOut(BaseModel):
    rose:        str
    compound:    str
    primary:     str
    destination: str
    purpose:     str
    would_fire:  bool
    cue_active:  list[bool]

class StepOut(BaseModel):
    rose:        str
    compound:    str
    primary:     str
    destination: str
    fired:       bool
    active_addrs: list[int]
    energy:      float

# ── Helpers ───────────────────────────────────────────────────────────────────

def _layer_out(L: RecombLayer) -> LayerOut:
    glyphs = []
    for addr in L.cue:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is None:
            glyphs.append(CueGlyphOut(addr=addr, symbol="?", tongue="?", meaning="?", element=None))
        else:
            c = CANDIDATES[idx]
            glyphs.append(CueGlyphOut(
                addr    = addr,
                symbol  = c.symbol,
                tongue  = c.tongue,
                meaning = c.meaning,
                element = candidate_element(idx),
            ))
    return LayerOut(
        rose          = L.rose,
        rose_index    = L.rose_index,
        compound      = L.compound,
        compound_addr = L.compound_addr,
        primary       = L.primary,
        destination   = L.destination,
        cue_glyphs    = glyphs,
        purpose       = L.purpose,
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/layers", response_model=list[LayerOut])
async def get_layers():
    """The 12 layer definitions with full cue cluster glyph details."""
    return [_layer_out(L) for L in LAYERS]


@router.post("/run", response_model=RunOut)
async def run_recombination(req: RunRequest):
    """
    Run a semantic state through all 12 layers in Rose numeral order.
    Each layer checks its Orrery cue; if satisfied, applies the crossing
    transformation. Returns the full firing trace.
    """
    trace = run(req.addrs, temp=req.temp, max_iter=req.max_iter)

    firings = [
        FiringOut(
            rose         = f.rose,
            rose_index   = f.rose_index,
            compound     = f.compound,
            primary      = f.primary,
            destination  = f.destination,
            purpose      = f.purpose,
            fired        = f.fired,
            active_count = len(f.active_idxs),
            energy       = f.energy,
        )
        for f in trace.firings
    ]

    # Map final active indices to addresses
    final_addrs = [int(CANDIDATES[i].addr) for i in trace.final_active]

    return RunOut(
        input_addrs  = req.addrs,
        firings      = firings,
        final_active = final_addrs,
        final_energy = trace.final_energy,
        layers_fired = trace.layers_fired,
    )


@router.post("/probe", response_model=list[ProbeLayerOut])
async def probe_layers(req: ProbeRequest):
    """
    Probe which layers would fire for a given input without applying
    any transformations. Shows the Orrery cue status of each layer.
    """
    results = probe(req.addrs, temp=req.temp, max_iter=req.max_iter)
    return [ProbeLayerOut(**r) for r in results]


@router.post("/step/{rose_name}", response_model=StepOut)
async def step_layer(rose_name: str, req: StepRequest):
    """
    Apply a single named layer's crossing to an input state.
    rose_name: one of Gaoh/Ao/Ye/Ui/Shu/Kiel/Yeshu/Lao/Shushy/Uinshu/Kokiel/Aonkiel
    """
    layer = next((L for L in LAYERS if L.rose.lower() == rose_name.lower()), None)
    if layer is None:
        raise HTTPException(404, f"no layer named '{rose_name}'")

    W = build_weight_matrix("keshi", req.temp)
    s = np.full(N, -0.2, dtype=np.float32)
    pinned = []
    for addr in req.addrs:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is not None:
            s[idx] = 1.0
            pinned.append(idx)
    s, _ = hopfield_converge(s, W, pinned, max_iter=req.max_iter, temp=req.temp)

    fired = check_cue(layer, s)
    s_out = recombine_step(layer, s, temp=req.temp, alpha=req.alpha,
                           max_iter=req.max_iter)

    active = [i for i in range(N) if s_out[i] > 0.5]
    active_addrs = [int(CANDIDATES[i].addr) for i in active]
    energy = float(-0.5 * (s_out @ W @ s_out))

    return StepOut(
        rose         = layer.rose,
        compound     = layer.compound,
        primary      = layer.primary,
        destination  = layer.destination,
        fired        = fired,
        active_addrs = active_addrs,
        energy       = energy,
    )

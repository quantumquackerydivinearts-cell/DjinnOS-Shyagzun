"""
routers/intel.py — Semantic substrate query API.

Endpoints:
  POST /v1/intel/query/tongue   — query by tongue register
  POST /v1/intel/query/near     — query by address proximity
  POST /v1/intel/query/diff     — navigate by semantic diff operator
  GET  /v1/intel/tongues        — list all tongue registers
  GET  /v1/intel/candidates     — all 1358 candidates (for field rendering)
  GET  /v1/intel/field          — full semantic field state (for visualisation)
"""

from __future__ import annotations

from typing import Literal, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ..intel import (
    query_by_tongue, query_near, query_diff, query_by_seeds,
    all_tongues, candidates_by_tongue, CANDIDATES, N, ADDR,
    build_weight_matrix,
)

router = APIRouter()

# ── Request / response models ─────────────────────────────────────────────────

KernelType = Literal["giann", "keshi", "drovitth", "saelith"]

class TongueQueryRequest(BaseModel):
    tongues:   list[str]
    kernel:    KernelType = "giann"
    temp:      float      = 0.0
    window:    int        = 10
    threshold: float      = 16.0
    max_iter:  int        = 32

class NearQueryRequest(BaseModel):
    addr:     int
    radius:   int       = 32
    kernel:   KernelType = "giann"
    temp:     float      = 0.0
    max_iter: int        = 32

class DiffQueryRequest(BaseModel):
    seed_addr: int
    delta:     int
    kernel:    KernelType = "keshi"
    temp:      float      = 1.0
    max_iter:  int        = 32

class SeedQueryRequest(BaseModel):
    addrs:    list[int]
    kernel:   KernelType = "giann"
    temp:     float      = 0.0
    max_iter: int        = 32

class CandidateOut(BaseModel):
    addr:        int
    tongue:      str
    symbol:      str
    meaning:     str
    lotus_gated: bool

class QueryResponse(BaseModel):
    active:     list[int]
    candidates: list[CandidateOut]
    energy:     float
    iterations: int
    state:      list[float]   # full 1358-float activation vector for field rendering

def _to_out(r) -> QueryResponse:
    return QueryResponse(
        active     = r.active,
        candidates = [CandidateOut(
            addr        = c.addr,
            tongue      = c.tongue,
            symbol      = c.symbol,
            meaning     = c.meaning,
            lotus_gated = c.lotus_gated,
        ) for c in r.candidates],
        energy     = r.energy,
        iterations = r.iterations,
        state      = r.state,
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/query/tongue", response_model=QueryResponse)
async def tongue_query(req: TongueQueryRequest):
    """
    Query by tongue register(s). Pins all candidates of the specified tongues
    and converges to the nearest semantic fixed point via the chosen Djinn kernel.
    """
    r = query_by_tongue(
        tongues   = req.tongues,
        kernel    = req.kernel,
        temp      = req.temp,
        window    = req.window,
        threshold = req.threshold,
        max_iter  = req.max_iter,
    )
    return _to_out(r)

@router.post("/query/near", response_model=QueryResponse)
async def near_query(req: NearQueryRequest):
    """
    Query by address proximity. Finds the semantic neighbourhood of a byte address.
    """
    r = query_near(
        addr     = req.addr,
        radius   = req.radius,
        kernel   = req.kernel,
        temp     = req.temp,
        max_iter = req.max_iter,
    )
    return _to_out(r)

@router.post("/query/diff", response_model=QueryResponse)
async def diff_query(req: DiffQueryRequest):
    """
    Navigate by semantic diff operator. Finds what lies delta steps away
    from seed_addr in the byte table coordinate space.

    Delta is a semantic transformation: delta=24 means "advance one tongue
    register", delta=6 means "Fire→Water transition in Serpent register", etc.
    """
    r = query_diff(
        seed_addr = req.seed_addr,
        delta     = req.delta,
        kernel    = req.kernel,
        temp      = req.temp,
        max_iter  = req.max_iter,
    )
    return _to_out(r)

@router.post("/query/seed", response_model=QueryResponse)
async def seed_query(req: SeedQueryRequest):
    """
    Converge from specific byte addresses. For language analysis: given akinen
    recognized in a composition, find the semantic attractor they inhabit and
    what adjacent candidates they activate.
    """
    r = query_by_seeds(
        addrs    = req.addrs,
        kernel   = req.kernel,
        temp     = req.temp,
        max_iter = req.max_iter,
    )
    return _to_out(r)

@router.get("/tongues")
async def get_tongues():
    """All 38 tongue registers with candidate counts."""
    tongues = all_tongues()
    return [
        {
            "tongue": t,
            "count":  len(candidates_by_tongue(t)),
            "gated":  t in {"Lotus", "Cannabis"},
        }
        for t in tongues
    ]

@router.get("/candidates")
async def get_candidates():
    """All 1358 candidates — addr, tongue, symbol, meaning."""
    return [
        {
            "idx":         i,
            "addr":        c.addr,
            "tongue":      c.tongue,
            "symbol":      c.symbol,
            "meaning":     c.meaning,
            "lotus_gated": c.lotus_gated,
        }
        for i, c in enumerate(CANDIDATES)
    ]

@router.get("/field")
async def get_field(kernel: KernelType = "giann", temp: float = 0.0):
    """
    Return the full semantic field: all candidate positions and the
    weight kernel as a sparse edge list (top-k weights per candidate).
    Used by the frontend to render the topology without doing a query.
    """
    import numpy as np
    W = build_weight_matrix(kernel, temp)

    # For each candidate, return its top-8 neighbours by weight.
    edges = []
    for i in range(N):
        row = W[i].copy()
        row[i] = 0.0
        top_k = int(np.argsort(row)[::-1][:8])
        for j in np.argsort(row)[::-1][:8]:
            if row[j] > 0.05:
                edges.append({"from": int(i), "to": int(j), "weight": float(row[j])})

    return {
        "n":         N,
        "addresses": ADDR.tolist(),
        "tongues":   TONGUE_NAMES if False else [c.tongue for c in CANDIDATES],
        "symbols":   [c.symbol for c in CANDIDATES],
        "edges":     edges,
    }

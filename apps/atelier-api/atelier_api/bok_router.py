"""
bok_router.py — BreathOfKo API

POST /v1/bok/snapshot       — take a full BoK snapshot (geometric + Orrery)
POST /v1/bok/diff           — compute diff between two snapshots
GET  /v1/bok/signal         — Wunashakoun signal for a snapshot
POST /v1/bok/validate-quack — check if a diff qualifies for Quack generation
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from .bok import (
    BreathOfKo, BoKDiff,
    snapshot_from_kobra, snapshot_from_addrs, compute_diff,
)

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class SnapshotRequest(BaseModel):
    azoth:        list[float]    = [0.0, 0.0]
    coil:         float          = 6.0
    boundedness:  str            = "bounded"
    scene_name:   str            = ""
    games_played: int            = 0
    kobra_source: Optional[str]  = None   # raw Kobra source
    addrs:        Optional[list[int]] = None  # pre-tokenized addresses

class SnapshotOut(BaseModel):
    azoth:             list[float]
    coil:              float
    boundedness:       str
    fired_layers:      list[str]
    elemental_sig:     dict[str, float]
    field_energy:      float
    dominant_crossing: Optional[str]
    scene_name:        str
    games_played:      int
    timestamp:         str
    crossing_entropy:  float
    layer_count:       int
    wunashakoun_signal: float

class DiffRequest(BaseModel):
    start: SnapshotOut
    end:   SnapshotOut

class DiffOut(BaseModel):
    azoth_distance:    float
    coil_delta:        float
    boundedness_start: str
    boundedness_end:   str
    layers_gained:     list[str]
    layers_lost:       list[str]
    elemental_shift:   dict[str, float]
    energy_delta:      float
    scene_start:       str
    scene_end:         str
    games_delta:       int
    semantic_distance: float
    dominant_shift:    Optional[str]
    is_wunashakoun:    bool
    wunashakoun_depth: float

class QuackValidation(BaseModel):
    is_wunashakoun:    bool
    wunashakoun_depth: float
    geometric_ok:      bool
    boundary_ok:       bool
    semantic_ok:       bool
    reason:            str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _snap_out(b: BreathOfKo) -> SnapshotOut:
    return SnapshotOut(
        azoth             = list(b.azoth),
        coil              = b.coil,
        boundedness       = b.boundedness,
        fired_layers      = sorted(b.fired_layers),
        elemental_sig     = b.elemental_sig,
        field_energy      = b.field_energy,
        dominant_crossing = b.dominant_crossing,
        scene_name        = b.scene_name,
        games_played      = b.games_played,
        timestamp         = b.timestamp,
        crossing_entropy  = b.crossing_entropy,
        layer_count       = b.layer_count,
        wunashakoun_signal = b.wunashakoun_signal,
    )

def _diff_out(d: BoKDiff) -> DiffOut:
    return DiffOut(
        azoth_distance    = d.azoth_distance,
        coil_delta        = d.coil_delta,
        boundedness_start = d.boundedness_start,
        boundedness_end   = d.boundedness_end,
        layers_gained     = sorted(d.layers_gained),
        layers_lost       = sorted(d.layers_lost),
        elemental_shift   = d.elemental_shift,
        energy_delta      = d.energy_delta,
        scene_start       = d.scene_start,
        scene_end         = d.scene_end,
        games_delta       = d.games_delta,
        semantic_distance = d.semantic_distance,
        dominant_shift    = d.dominant_shift,
        is_wunashakoun    = d.is_wunashakoun,
        wunashakoun_depth = d.wunashakoun_depth,
    )

def _snap_from_out(s: SnapshotOut) -> BreathOfKo:
    return BreathOfKo(
        azoth             = (s.azoth[0], s.azoth[1]),
        coil              = s.coil,
        boundedness       = s.boundedness,
        fired_layers      = frozenset(s.fired_layers),
        elemental_sig     = s.elemental_sig,
        field_energy      = s.field_energy,
        dominant_crossing = s.dominant_crossing,
        scene_name        = s.scene_name,
        games_played      = s.games_played,
        timestamp         = s.timestamp,
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/snapshot", response_model=SnapshotOut)
async def take_snapshot(req: SnapshotRequest):
    """
    Take a full BreathOfKo snapshot.

    Provide either kobra_source (raw .ko text) or addrs (pre-tokenized byte
    addresses) to get the Orrery semantic reading. If neither is provided,
    the snapshot contains only the geometric layer (fired_layers will be empty).

    The wunashakoun_signal in the response is the composite measure derived
    from both geometric position and semantic crossing activity.
    """
    azoth = (req.azoth[0], req.azoth[1]) if len(req.azoth) >= 2 else (0.0, 0.0)

    if req.kobra_source:
        snap = snapshot_from_kobra(
            kobra_source = req.kobra_source,
            azoth        = azoth,
            coil         = req.coil,
            boundedness  = req.boundedness,
            scene_name   = req.scene_name,
            games_played = req.games_played,
        )
    elif req.addrs:
        snap = snapshot_from_addrs(
            addrs        = req.addrs,
            azoth        = azoth,
            coil         = req.coil,
            boundedness  = req.boundedness,
            scene_name   = req.scene_name,
            games_played = req.games_played,
        )
    else:
        # Geometric-only snapshot (no Orrery reading)
        snap = BreathOfKo(
            azoth             = azoth,
            coil              = req.coil,
            boundedness       = req.boundedness,
            fired_layers      = frozenset(),
            elemental_sig     = {"Shak": 0.0, "Puf": 0.0, "Mel": 0.0, "Zot": 0.0},
            field_energy      = 0.0,
            dominant_crossing = None,
            scene_name        = req.scene_name,
            games_played      = req.games_played,
        )

    return _snap_out(snap)


@router.post("/diff", response_model=DiffOut)
async def compute_bok_diff(req: DiffRequest):
    """
    Compute the full BoK diff between two snapshots.
    Returns geometric + semantic transition, Wunashakoun assessment.
    """
    start = _snap_from_out(req.start)
    end   = _snap_from_out(req.end)
    diff  = compute_diff(start, end)
    return _diff_out(diff)


@router.post("/validate-quack", response_model=QuackValidation)
async def validate_for_quack(req: DiffRequest):
    """
    Validate whether a BoK diff qualifies for Quack generation.

    A genuine Wunashakoun diff requires:
      1. Geometric movement (azoth_distance > 0.001)
      2. Edge boundedness in at least one snapshot
      3. Semantic transition (at least one layer gained or lost)

    Returns detailed breakdown of which conditions are met.
    """
    start = _snap_from_out(req.start)
    end   = _snap_from_out(req.end)
    diff  = compute_diff(start, end)

    geo_ok      = diff.azoth_distance > 0.001 or abs(diff.coil_delta) > 0.001
    boundary_ok = (start.boundedness == "edge" or end.boundedness == "edge")
    semantic_ok = len(diff.layers_gained) > 0 or len(diff.layers_lost) > 0

    if diff.is_wunashakoun:
        reason = (
            f"Valid Wunashakoun diff. "
            f"Depth: {diff.wunashakoun_depth:.3f}. "
            f"Azoth distance: {diff.azoth_distance:.4f}. "
            f"Semantic distance: {diff.semantic_distance:.3f}. "
            f"Layers gained: {sorted(diff.layers_gained) or 'none'}. "
            f"Dominant shift: {diff.dominant_shift or 'none'}."
        )
    else:
        missing = []
        if not geo_ok:      missing.append("geometric movement")
        if not boundary_ok: missing.append("edge boundedness")
        if not semantic_ok: missing.append("semantic transition")
        reason = f"Not a valid Wunashakoun diff. Missing: {', '.join(missing)}."

    return QuackValidation(
        is_wunashakoun    = diff.is_wunashakoun,
        wunashakoun_depth = diff.wunashakoun_depth,
        geometric_ok      = geo_ok,
        boundary_ok       = boundary_ok,
        semantic_ok       = semantic_ok,
        reason            = reason,
    )

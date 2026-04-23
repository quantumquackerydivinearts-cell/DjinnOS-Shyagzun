"""
atelier_api/routers/kobra.py
=============================
POST /v1/kobra/compile

Compiles a Kobra source string and returns the full renderer triple:
  voxels           — entity placements for WorldRenderer.load_zone()
  chromatic_packet — per-register amplitude map for chromatic lighting
  coherence        — bilingual trust / coherence summary

The renderer triple is the scene format contract between Atelier and Engine.
Pass it directly to ambroflow.render.kobra_bridge.build_render_config().

Optional query parameters
--------------------------
  coherence_grade : float 0.0–1.0  override coherence grade (for cut preview)
  cut             : "resolved" | "frontier"  override cut character
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ── Kernel imports ────────────────────────────────────────────────────────────

_REPO_ROOT    = Path(__file__).resolve().parents[4]
_KERNEL_ROOT  = str(_REPO_ROOT / "DjinnOS_Shyagzun")
_CHROMATIC_PY = _REPO_ROOT / "DjinnOS_Shyagzun" / "djinnos_kernel_ref" / "shygazun" / "kernel" / "chromatic.py"

if _KERNEL_ROOT not in sys.path:
    sys.path.insert(0, _KERNEL_ROOT)

# kobra pipeline — already set up in site_services/kobra.py; import directly
from atelier_api.site_services.kobra import (   # type: ignore
    compile_kobra_scene,
    entities_to_voxels,
    scene_to_bilingual_trust,
    KobraSceneResult,
)

# chromatic — loaded via importlib to avoid namespace conflict with djinnos_kernel_ref
def _load_chromatic():
    if "shygazun.kernel.chromatic" in sys.modules:
        m = sys.modules["shygazun.kernel.chromatic"]
    else:
        spec = importlib.util.spec_from_file_location(
            "shygazun.kernel.chromatic", _CHROMATIC_PY
        )
        m = importlib.util.module_from_spec(spec)
        m.__package__ = "shygazun.kernel"
        sys.modules["shygazun.kernel.chromatic"] = m
        spec.loader.exec_module(m)
    return m

_chromatic = _load_chromatic()
_extract_chromatic_profile      = _chromatic.extract_chromatic_profile
_build_renderer_chromatic_packet = _chromatic.build_renderer_chromatic_packet


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/v1/kobra", tags=["kobra"])


# ── Request / response schemas ────────────────────────────────────────────────

class KobraCompileRequest(BaseModel):
    source: str = Field(..., description="Kobra source string to compile")
    zone_id: str = Field("kobra_scene", description="Zone identifier for the renderer")
    coherence_grade: Optional[float] = Field(
        None,
        ge=0.0, le=1.0,
        description="Override coherence grade (0.0 = frontier, 1.0 = resolved)",
    )
    cut: Optional[str] = Field(
        None,
        description="Override cut character: 'resolved' or 'frontier'",
    )


class KobraCompileResponse(BaseModel):
    ok:               bool
    zone_id:          str
    entity_count:     int
    tongue_inventory: list[str]
    cannabis_active:  bool
    errors:           list[str]
    warnings:         list[str]
    frontier_open:    list[str]
    voxels:           list[dict[str, Any]]
    chromatic_packet: dict[str, Any]
    coherence:        dict[str, Any]


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/compile", response_model=KobraCompileResponse)
def compile_kobra(req: KobraCompileRequest) -> KobraCompileResponse:
    """
    Compile a Kobra source string to the renderer triple.

    Returns voxels, chromatic_packet, and coherence — the three inputs
    expected by ambroflow.render.kobra_bridge.build_render_config().
    """
    scene: KobraSceneResult = compile_kobra_scene(req.source)

    if scene.errors:
        raise HTTPException(
            status_code=422,
            detail={"errors": scene.errors, "source": req.source},
        )

    voxels = entities_to_voxels(scene.entities)

    # Extract chromatic profile from all Wunashako token strings
    all_tokens: list[str] = []
    for entity in scene.entities:
        # entity.id may have been an explicit name; re-derive from quality/material
        if entity.material:
            all_tokens.append(entity.material)
        if entity.color:
            all_tokens.append(entity.color)
        if entity.quality:
            all_tokens.append(entity.quality)

    profile          = _extract_chromatic_profile(all_tokens) if all_tokens else _extract_chromatic_profile([])
    chromatic_packet = _build_renderer_chromatic_packet(profile)

    # Coherence from bilingual trust
    trust = scene_to_bilingual_trust(scene)
    coherence: dict[str, Any] = {
        "trust_grade":       trust["trust_grade"],
        "authority_level":   trust["authority_level"],
        "tongue_projection": trust["tongue_projection"],
        "cannabis_mode":     trust["cannabis_mode"],
        "coherence_grade":   1.0 if not scene.frontier_open else 0.5,
        "cut_character":     "resolved" if not scene.frontier_open else "frontier",
        "total_cannabis_entries": len(scene.frontier_open),
        "witnessed":         0,
        "frontier":          len(scene.frontier_open),
    }

    # Apply any overrides from the request (for cut preview)
    if req.coherence_grade is not None:
        coherence["coherence_grade"] = req.coherence_grade
    if req.cut is not None and req.cut in ("resolved", "frontier"):
        coherence["cut_character"] = req.cut

    return KobraCompileResponse(
        ok               = True,
        zone_id          = req.zone_id,
        entity_count     = len(scene.entities),
        tongue_inventory = scene.tongue_inventory,
        cannabis_active  = scene.cannabis_active,
        errors           = scene.errors,
        warnings         = scene.warnings,
        frontier_open    = scene.frontier_open,
        voxels           = voxels,
        chromatic_packet = chromatic_packet,
        coherence        = coherence,
    )
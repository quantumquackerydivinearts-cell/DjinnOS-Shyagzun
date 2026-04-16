"""
Voxel Ingest
============
Bridges tile generator output into the hybrid voxel engine pipeline.

POST /v1/render_lab/projects/{project_id}/ingest

Accepts tile generator output (directly or by naming a tile script to run
server-side), converts it through the voxel bridge, saves the resulting
voxel scene source JSON as the project's pipeline input, and optionally
triggers a pipeline stage.

This is the primary integration point that makes the tile generator, the
voxel scene format, and the compile → validate → stream → prefetch →
budget_check → go_no_go → layer_project chain a coherent authoring workflow.

Workflow:
  1.  Author a tile layout with a tile generator script (ring_bloom, maze_carve,
      navigable_town, etc. — or a custom user script)
  2.  POST to /ingest with the tile output (or script name + params)
  3.  The bridge maps color/opacity tokens → voxel {type, material, z}
  4.  Resulting voxel scene JSON is saved and linked to the project
  5.  Pipeline compile → all runs from that source — producing a full
      compiled pack, stream manifest, prefetch manifest, toolchain report,
      and layer projection ready for the renderer and GLTF export
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...db import get_db
from ._db import db_save, require_project
from ._utils import ROOT, now_iso
from .tile_scripts import _DEFAULTS, _load_scripts, _run_js
from .voxel_bridge import summarise_voxel_scene, tile_output_to_voxel_scene

router = APIRouter()

SOURCES_DIR = ROOT / "gameplay" / "renderer_packs" / "sources"


# ── Request models ─────────────────────────────────────────────────────────────

class VoxelIngestRequest(BaseModel):
    # Option A: supply tile output directly
    tile_output: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Direct tile generator output: "
            "{tiles: [...], links: [...], entities: [...]}. "
            "Use this when the client already ran a tile script."
        ),
    )
    # Option B: name a script to run server-side
    script_name: str | None = Field(
        default=None,
        description="Builtin or saved tile script name to execute server-side.",
    )
    seed: int = Field(default=42)
    cols: int = Field(default=64, ge=1, le=512)
    rows: int = Field(default=36, ge=1, le=512)
    layer: str = Field(default="base")

    # Scene metadata
    scene_name: str = Field(default="", max_length=128)
    include_entities: bool = Field(default=True)
    render_settings: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Override render settings (renderMode, tile, zScale, etc.). "
            "Merged into defaults: renderMode='2.5d', tile=18, zScale=8."
        ),
    )

    # Pipeline control
    run_pipeline: bool = Field(
        default=False,
        description="If true, trigger the compile stage immediately after ingest.",
    )
    pipeline_stage: str = Field(
        default="compile",
        description=(
            "Pipeline stage to trigger when run_pipeline=true. "
            "Use 'all' to run the full compile→layer_project chain."
        ),
    )
    workspace_id: str = Field(default="main")
    chunk_size_x: int = Field(default=64, ge=1)
    chunk_size_y: int = Field(default=64, ge=1)
    partition_mode: str = Field(default="material_aware")


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/ingest",
    summary="Ingest tile generator output into the voxel pipeline",
)
async def voxel_ingest(
    project_id: str,
    req: VoxelIngestRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    """
    Convert tile generator output into a voxel scene source document, link it
    to the project, and optionally trigger the pipeline.

    Accepts either:
    - ``tile_output`` — raw tile generator result from the client
    - ``script_name`` + seed/cols/rows — runs the named script server-side

    The resulting voxel scene JSON is written to:
      gameplay/renderer_packs/sources/{project_id}.source.json

    The project's ``pipeline.source_ids.json_file_id`` is updated to point
    at this file, making it the input for the next compile run.
    """
    project = require_project(db, project_id)

    # ── Resolve tile output ──────────────────────────────────────────────────
    tile_output: dict[str, Any] | None = req.tile_output

    if tile_output is None:
        if not req.script_name:
            raise HTTPException(
                status_code=422,
                detail="provide tile_output or script_name",
            )
        code = _resolve_script_code(req.script_name)
        result, error = _run_js(
            code,
            seed=req.seed,
            cols=req.cols,
            rows=req.rows,
            layer=req.layer,
        )
        if error:
            raise HTTPException(
                status_code=422,
                detail=f"script_execution_failed:{error}",
            )
        tile_output = result

    tiles    = tile_output.get("tiles", [])
    links    = tile_output.get("links", [])
    entities = tile_output.get("entities", [])

    if not tiles:
        raise HTTPException(status_code=422, detail="tile_output_has_no_tiles")

    # ── Convert tiles → voxel scene ──────────────────────────────────────────
    name = (
        req.scene_name
        or (req.script_name or "")
        or project.get("name", "untitled")
    )
    voxel_scene = tile_output_to_voxel_scene(
        {"tiles": tiles, "links": links, "entities": entities},
        name=name,
        include_entities=req.include_entities,
        render_settings=req.render_settings,
    )

    # ── Persist voxel scene source JSON ─────────────────────────────────────
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    source_path = SOURCES_DIR / f"{project_id}.source.json"
    source_path.write_text(
        json.dumps(voxel_scene, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Update project record ────────────────────────────────────────────────
    project["pipeline"]["source_ids"]["json_file_id"] = str(source_path)
    project["updated_at"] = now_iso()
    db_save(db, project)

    summary = summarise_voxel_scene(voxel_scene)
    response: dict[str, Any] = {
        "ok":           True,
        "project_id":   project_id,
        "source_path":  str(source_path),
        "scene_name":   name,
        "script_name":  req.script_name,
        "seed":         req.seed,
        "cols":         req.cols,
        "rows":         req.rows,
        "tile_count":   len(tiles),
        "entity_count": len(entities),
        "summary":      summary,
        "pipeline_triggered": False,
        "pipeline_results":   [],
    }

    # ── Optionally trigger pipeline ──────────────────────────────────────────
    if req.run_pipeline:
        from ._utils import project_artifact_paths
        from .pipeline import STAGE_ORDER, _run_stage

        class _FakeReq:
            workspace_id   = req.workspace_id
            chunk_size_x   = req.chunk_size_x
            chunk_size_y   = req.chunk_size_y
            partition_mode = req.partition_mode

        paths   = project_artifact_paths(project_id)
        stages  = STAGE_ORDER if req.pipeline_stage == "all" else [req.pipeline_stage]
        p_results: list[dict[str, Any]] = []
        project["status"] = "building"

        for stage in stages:
            r = _run_stage(stage, project, paths, _FakeReq())
            p_results.append(r)
            if not r["ok"]:
                project["status"] = "failed"
                project["pipeline"]["last_run_status"] = "failed"
                break
        else:
            project["status"] = "ready" if req.pipeline_stage == "all" else "building"
            project["pipeline"]["last_run_status"] = "ok"

        project["pipeline"]["last_run_at"] = now_iso()
        project["updated_at"] = now_iso()
        db_save(db, project)

        response["pipeline_triggered"] = True
        response["pipeline_results"]   = p_results
        response["pipeline_ok"]        = all(r["ok"] for r in p_results)

    return ORJSONResponse(status_code=200, content=response)


# ── Scene source preview endpoint ──────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/ingest/source",
    summary="Read the current voxel scene source for a project",
)
async def get_ingest_source(
    project_id: str,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    """
    Return the voxel scene source JSON that was last ingested for this project.
    Useful for inspection, debugging, and exporting the raw voxel list
    before the compile stage runs.
    """
    project  = require_project(db, project_id)
    src_path = project["pipeline"]["source_ids"].get("json_file_id")

    if not src_path:
        raise HTTPException(status_code=404, detail="no_source_ingested_yet")

    path = Path(src_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"source_file_missing:{src_path}")

    try:
        scene = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"source_read_error:{exc}") from exc

    summary = summarise_voxel_scene(scene)
    return ORJSONResponse(content={
        "ok":          True,
        "project_id":  project_id,
        "source_path": src_path,
        "summary":     summary,
        "scene":       scene,
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_script_code(name: str) -> str:
    """Return JS code for a builtin or saved tile script by name."""
    if name in _DEFAULTS:
        return _DEFAULTS[name]
    saved = _load_scripts()
    entry = next((s for s in saved if s.get("name") == name), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"tile_script_not_found:{name}")
    code = entry.get("code", "")
    if not code:
        raise HTTPException(status_code=422, detail=f"tile_script_empty:{name}")
    return code
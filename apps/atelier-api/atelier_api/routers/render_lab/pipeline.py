"""Render Lab pipeline execution — stage dispatch and runners."""
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
from ._utils import (
    CANONICAL_SOURCE,
    SCRIPTS_DIR,
    new_lineage_id,
    now_iso,
    project_artifact_paths,
    run_script,
)

router = APIRouter()

VALID_STAGES = {"compile", "validate", "stream", "prefetch", "budget_check", "go_no_go", "layer_project", "all"}
STAGE_ORDER  = ["compile", "validate", "stream", "prefetch", "budget_check", "go_no_go", "layer_project"]


class PipelineRunRequest(BaseModel):
    stage: str = Field(..., description="compile|validate|stream|prefetch|budget_check|go_no_go|layer_project|all")
    workspace_id: str = Field(default="main")
    chunk_size_x: int = Field(default=64, ge=1)
    chunk_size_y: int = Field(default=64, ge=1)
    partition_mode: str = Field(default="material_aware")


@router.post("/projects/{project_id}/pipeline/run", summary="Run a pipeline stage")
async def run_pipeline(
    project_id: str,
    req: PipelineRunRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = require_project(db, project_id)
    if req.stage not in VALID_STAGES:
        raise HTTPException(status_code=422, detail=f"unknown_stage:{req.stage}")

    paths      = project_artifact_paths(project_id)
    stages     = STAGE_ORDER if req.stage == "all" else [req.stage]
    lineage_id = new_lineage_id()
    results: list[dict[str, Any]] = []

    project["status"] = "building"
    project["updated_at"] = now_iso()

    for stage in stages:
        result = _run_stage(stage, project, paths, req)
        results.append(result)
        if not result["ok"]:
            project["status"] = "failed"
            project["pipeline"]["last_run_status"] = "failed"
            break
    else:
        project["status"] = "ready" if req.stage == "all" else project["status"]
        project["pipeline"]["last_run_status"] = "ok"

    project["pipeline"]["last_run_at"] = now_iso()
    project["lineage_ids"].append(lineage_id)
    project["updated_at"] = now_iso()
    db_save(db, project)

    return ORJSONResponse(content={
        "ok": all(r["ok"] for r in results),
        "project_id": project_id,
        "stage": req.stage,
        "lineage_id": lineage_id,
        "results": results,
    })


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------

def _run_stage(
    stage: str,
    project: dict[str, Any],
    paths: dict[str, Path],
    req: PipelineRunRequest,
) -> dict[str, Any]:
    source_json = project["pipeline"]["source_ids"].get("json_file_id") or str(CANONICAL_SOURCE)

    if stage == "compile":
        return _stage_compile(project, paths, req, source_json)
    if stage == "validate":
        return _stage_validate(project, paths)
    if stage == "stream":
        return _stage_stream(project, paths, req)
    if stage == "prefetch":
        return _stage_prefetch(project, paths)
    if stage == "budget_check":
        return _stage_budget_check(project, paths)
    if stage == "go_no_go":
        return _stage_go_no_go(project, paths)
    if stage == "layer_project":
        return _stage_layer_project(project, paths, req)
    return {"stage": stage, "ok": False, "artifact_path": None,
            "stdout_tail": f"unknown_stage:{stage}", "elapsed_ms": 0}


def _stage_compile(
    project: dict[str, Any],
    paths: dict[str, Path],
    req: PipelineRunRequest,
    source_json: str,
) -> dict[str, Any]:
    out_path = paths["compiled_pack"]
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "build_renderer_pack_v2.py"),
        "--input", source_json,
        "--output", str(out_path),
        "--workspace-id", req.workspace_id,
        "--source", "render_lab",
    ])
    if ok:
        project["artifacts"]["compiled_pack_path"] = str(out_path)
    return {"stage": "compile", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_validate(project: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    pack_path = project["artifacts"].get("compiled_pack_path")
    if not pack_path:
        return {"stage": "validate", "ok": False, "artifact_path": None,
                "stdout_tail": "compile_stage_required", "elapsed_ms": 0}
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "validate_renderer_pack_v2.py"),
        "--input", pack_path,
    ])
    return {"stage": "validate", "ok": ok, "artifact_path": None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_stream(
    project: dict[str, Any],
    paths: dict[str, Path],
    req: PipelineRunRequest,
) -> dict[str, Any]:
    pack_path = project["artifacts"].get("compiled_pack_path")
    if not pack_path:
        return {"stage": "stream", "ok": False, "artifact_path": None,
                "stdout_tail": "compile_stage_required", "elapsed_ms": 0}
    out_path = paths["stream_manifest"]
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "build_renderer_stream_manifest_v1.py"),
        "--input", pack_path,
        "--output", str(out_path),
        "--chunk-size-x", str(req.chunk_size_x),
        "--chunk-size-y", str(req.chunk_size_y),
        "--partition-mode", req.partition_mode,
        "--emit-chunks",
    ])
    if ok:
        project["artifacts"]["stream_manifest_path"] = str(out_path)
    return {"stage": "stream", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_prefetch(project: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    stream_path = project["artifacts"].get("stream_manifest_path")
    if not stream_path:
        return {"stage": "prefetch", "ok": False, "artifact_path": None,
                "stdout_tail": "stream_stage_required", "elapsed_ms": 0}
    out_path = paths["prefetch_manifest"]
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "build_renderer_prefetch_manifest_v1.py"),
        "--input", stream_path,
        "--output", str(out_path),
        "--max-ring", "2",
    ])
    if ok:
        project["artifacts"]["prefetch_manifest_path"] = str(out_path)
    return {"stage": "prefetch", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_budget_check(project: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    stream_path = project["artifacts"].get("stream_manifest_path")
    if not stream_path:
        return {"stage": "budget_check", "ok": False, "artifact_path": None,
                "stdout_tail": "stream_stage_required", "elapsed_ms": 0}
    out_path = paths["budget_report"]
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "check_renderer_stream_residency_budgets.py"),
        "--input", stream_path,
        "--output", str(out_path),
    ])
    return {"stage": "budget_check", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_go_no_go(project: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    pack_path     = project["artifacts"].get("compiled_pack_path")
    stream_path   = project["artifacts"].get("stream_manifest_path")
    prefetch_path = project["artifacts"].get("prefetch_manifest_path")
    if not pack_path or not stream_path or not prefetch_path:
        return {"stage": "go_no_go", "ok": False, "artifact_path": None,
                "stdout_tail": "compile+stream+prefetch_stages_required", "elapsed_ms": 0}

    out_path = paths["toolchain_report"]
    budget_path = str(paths["budget_report"]) if paths["budget_report"].exists() else None
    args = [
        str(SCRIPTS_DIR / "renderer_toolchain_go_no_go.py"),
        "--compiled-pack", pack_path,
        "--stream-manifest", stream_path,
        "--prefetch-manifest", prefetch_path,
        "--output", str(out_path),
    ]
    if budget_path:
        args += ["--residency-report", budget_path]

    ok, tail, elapsed = run_script(args)
    if ok:
        project["artifacts"]["toolchain_report_path"] = str(out_path)
        try:
            report = json.loads(out_path.read_text(encoding="utf-8"))
            project["readiness"]["readiness_green"] = bool(report.get("go", False))
            project["readiness"]["last_checked_at"] = now_iso()
            project["gate_status"]["gate_a"] = "pass" if report.get("go") else "fail"
        except Exception:
            pass
    return {"stage": "go_no_go", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}


def _stage_layer_project(
    project: dict[str, Any],
    paths: dict[str, Path],
    req: PipelineRunRequest,
) -> dict[str, Any]:
    report_path = project["artifacts"].get("toolchain_report_path")
    if not report_path:
        return {"stage": "layer_project", "ok": False, "artifact_path": None,
                "stdout_tail": "go_no_go_stage_required", "elapsed_ms": 0}
    out_path = paths["layer_projection"]
    ok, tail, elapsed = run_script([
        str(SCRIPTS_DIR / "renderer_toolchain_project_to_layers.py"),
        "--report", report_path,
        "--workspace-id", req.workspace_id,
        "--output", str(out_path),
    ])
    if ok:
        project["artifacts"]["layer_projection_path"] = str(out_path)
    return {"stage": "layer_project", "ok": ok, "artifact_path": str(out_path) if ok else None,
            "stdout_tail": tail, "elapsed_ms": elapsed}
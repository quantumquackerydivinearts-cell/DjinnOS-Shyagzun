"""
atelier_api/routers/render_lab.py
Render Lab project management, pipeline execution, and readiness endpoints.

Pipeline stages run the deterministic Python toolchain scripts via subprocess,
matching the pattern in scripts/production_go_no_go.py. Scripts remain
standalone CLI tools; this router translates project state into CLI args
and captures stdout/exit code.

Project persistence: render_lab_projects table (migration 0024).
Full project document stored as data_json TEXT; indexed columns for filtering.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.lineage import get_lineage_store
from ..db import get_db

router = APIRouter(prefix="/v1/render_lab", tags=["render_lab"])

ROOT = Path(__file__).resolve().parents[4]  # c:/DjinnOS
SCRIPTS_DIR = ROOT / "scripts"
PACKS_DIR = ROOT / "gameplay" / "renderer_packs" / "compiled"
STREAMS_DIR = ROOT / "gameplay" / "renderer_packs" / "streams"
REPORTS_DIR = ROOT / "reports" / "renderer_toolchain"
BUDGETS_CONTRACT = ROOT / "gameplay" / "contracts" / "renderer_stream_budgets.v1.json"
CANONICAL_SOURCE = ROOT / "apps" / "atelier-desktop" / "public" / "renderer-pack-source.json"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db_get(db: Session, project_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT data_json FROM render_lab_projects WHERE project_id = :pid"),
        {"pid": project_id},
    ).fetchone()
    return json.loads(row[0]) if row else None


def _db_save(db: Session, project: dict[str, Any]) -> None:
    pid   = project["project_id"]
    realm = project.get("pipeline", {}).get("world_region", {}).get("realm_id", "lapidus")
    db.execute(text("""
        INSERT INTO render_lab_projects
            (project_id, name, project_type, workspace_id, realm_id,
             status, data_json, created_at, updated_at)
        VALUES
            (:pid, :name, :ptype, :wsid, :realm,
             :status, :data, :created, :updated)
        ON CONFLICT(project_id) DO UPDATE SET
            name        = excluded.name,
            project_type = excluded.project_type,
            workspace_id = excluded.workspace_id,
            realm_id    = excluded.realm_id,
            status      = excluded.status,
            data_json   = excluded.data_json,
            updated_at  = excluded.updated_at
    """), {
        "pid":     pid,
        "name":    project.get("name", ""),
        "ptype":   project["project_type"],
        "wsid":    project.get("workspace_id", "main"),
        "realm":   realm,
        "status":  project.get("status", "draft"),
        "data":    json.dumps(project),
        "created": project.get("created_at", _now_iso()),
        "updated": project.get("updated_at", _now_iso()),
    })
    db.commit()


def _db_list(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text("SELECT data_json FROM render_lab_projects ORDER BY created_at DESC")
    ).fetchall()
    return [json.loads(r[0]) for r in rows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_project_id() -> str:
    raw = f"rlp_{int(time.time() * 1000)}_{os.getpid()}"
    return "rlp_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _new_lineage_id() -> str:
    raw = f"lin_{int(time.time() * 1000000)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _run_script(args: list[str], cwd: Path | None = None) -> tuple[bool, str, int]:
    """Run a Python toolchain script. Returns (ok, output_tail, elapsed_ms)."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            ["python"] + args,
            cwd=str(cwd) if cwd else str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return False, f"exception:{exc}", int((time.monotonic() - t0) * 1000)
    elapsed = int((time.monotonic() - t0) * 1000)
    combined = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
    tail = combined[-2000:] if len(combined) > 2000 else combined
    return proc.returncode == 0, tail, elapsed


def _http_get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        raise RuntimeError(f"http_get_failed:{url}:{exc}") from exc


def _project_artifact_paths(project_id: str) -> dict[str, Path]:
    return {
        "compiled_pack":     PACKS_DIR / f"{project_id}.v2.json",
        "stream_manifest":   STREAMS_DIR / f"{project_id}.stream.v1.json",
        "prefetch_manifest": STREAMS_DIR / f"{project_id}.prefetch.v1.json",
        "budget_report":     REPORTS_DIR / f"residency_budget.{project_id}.json",
        "toolchain_report":  REPORTS_DIR / f"report.{project_id}.json",
        "layer_projection":  REPORTS_DIR / f"layer_projection.{project_id}.json",
    }


def _require_project(db: Session, project_id: str) -> dict[str, Any]:
    project = _db_get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project_not_found")
    return project


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str = Field(default="", max_length=128)
    project_type: str = Field(..., pattern="^(game_voxel|arch_diagram|hybrid)$")
    workspace_id: str = Field(default="main")
    realm_id: str = Field(default="lapidus")
    source_json_path: str | None = None


class PipelineRunRequest(BaseModel):
    stage: str = Field(..., description="compile|validate|stream|prefetch|budget_check|go_no_go|layer_project|all")
    workspace_id: str = Field(default="main")
    chunk_size_x: int = Field(default=64, ge=1)
    chunk_size_y: int = Field(default=64, ge=1)
    partition_mode: str = Field(default="material_aware")


class ArchDiagramParseRequest(BaseModel):
    mode: str = Field(default="json", pattern="^(json|cobra|english|shygazun)$")
    source: str = Field(default="")


class ArchDiagramExportRequest(BaseModel):
    format: str = Field(default="svg", pattern="^(svg|png)$")
    spec: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@router.post("/projects", summary="Create a new Render Lab project")
async def create_project(
    req: CreateProjectRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project_id = _new_project_id()
    now = _now_iso()
    name = req.name or f"{req.project_type}_{project_id[-8:]}"
    project: dict[str, Any] = {
        "schema": "atelier.render_lab.project.v1",
        "project_id": project_id,
        "name": name,
        "project_type": req.project_type,
        "workspace_id": req.workspace_id,
        "created_at": now,
        "updated_at": now,
        "status": "draft",
        "pipeline": {
            "source_ids": {
                "python_file_id": None,
                "cobra_file_id":  None,
                "js_file_id":     None,
                "json_file_id":   req.source_json_path,
                "engine_file_id": None,
            },
            "world_region": {
                "realm_id":     req.realm_id,
                "region_key":   "",
                "cache_policy": "cache",
            },
            "render_settings": {},
            "last_run_at": None,
            "last_run_status": None,
        },
        "artifacts": {
            "compiled_pack_path":     None,
            "stream_manifest_path":   None,
            "prefetch_manifest_path": None,
            "toolchain_report_path":  None,
            "layer_projection_path":  None,
        },
        "arch_diagram": None if req.project_type == "game_voxel" else {
            "spec": {},
            "export_svg_path": None,
            "export_png_path": None,
        },
        "gate_status": {k: None for k in ("gate_a", "gate_b", "gate_c", "gate_d", "gate_e", "gate_f")},
        "readiness": {
            "readiness_green": False,
            "federation_green": False,
            "last_checked_at": None,
        },
        "lineage_ids": [],
    }
    _db_save(db, project)
    return ORJSONResponse(status_code=201, content={"ok": True, "project_id": project_id, "project": project})


@router.get("/projects", summary="List all Render Lab projects")
async def list_projects(db: Session = Depends(get_db)) -> ORJSONResponse:
    projects = _db_list(db)
    return ORJSONResponse(content={
        "ok": True,
        "projects": [{"project_id": p["project_id"], "name": p.get("name", ""),
                      "project_type": p["project_type"], "status": p.get("status", "draft")}
                     for p in projects],
        "count": len(projects),
    })


@router.get("/projects/{project_id}", summary="Get a Render Lab project by ID")
async def get_project(project_id: str, db: Session = Depends(get_db)) -> ORJSONResponse:
    project = _require_project(db, project_id)
    return ORJSONResponse(content={"ok": True, "project": project})


@router.delete("/projects/{project_id}", summary="Archive a Render Lab project")
async def archive_project(project_id: str, db: Session = Depends(get_db)) -> ORJSONResponse:
    project = _require_project(db, project_id)
    project["status"] = "archived"
    project["updated_at"] = _now_iso()
    _db_save(db, project)
    return ORJSONResponse(content={"ok": True, "project_id": project_id, "status": "archived"})


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

VALID_STAGES = {"compile", "validate", "stream", "prefetch", "budget_check", "go_no_go", "layer_project", "all"}
STAGE_ORDER  = ["compile", "validate", "stream", "prefetch", "budget_check", "go_no_go", "layer_project"]


@router.post("/projects/{project_id}/pipeline/run", summary="Run a pipeline stage")
async def run_pipeline(
    project_id: str,
    req: PipelineRunRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = _require_project(db, project_id)
    if req.stage not in VALID_STAGES:
        raise HTTPException(status_code=422, detail=f"unknown_stage:{req.stage}")

    paths  = _project_artifact_paths(project_id)
    stages = STAGE_ORDER if req.stage == "all" else [req.stage]

    results: list[dict[str, Any]] = []
    project["status"] = "building"
    project["updated_at"] = _now_iso()
    lineage_id = _new_lineage_id()

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

    project["pipeline"]["last_run_at"] = _now_iso()
    project["lineage_ids"].append(lineage_id)
    project["updated_at"] = _now_iso()
    _db_save(db, project)

    overall_ok = all(r["ok"] for r in results)
    return ORJSONResponse(content={
        "ok": overall_ok,
        "project_id": project_id,
        "stage": req.stage,
        "lineage_id": lineage_id,
        "results": results,
    })


def _run_stage(
    stage: str,
    project: dict[str, Any],
    paths: dict[str, Path],
    req: PipelineRunRequest,
) -> dict[str, Any]:
    """Dispatch a single pipeline stage. Returns a result dict."""
    source_json = project["pipeline"]["source_ids"].get("json_file_id") or str(CANONICAL_SOURCE)

    if stage == "compile":
        out_path = paths["compiled_pack"]
        ok, tail, elapsed = _run_script([
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

    elif stage == "validate":
        pack_path = project["artifacts"].get("compiled_pack_path")
        if not pack_path:
            return {"stage": "validate", "ok": False, "artifact_path": None,
                    "stdout_tail": "compile_stage_required", "elapsed_ms": 0}
        ok, tail, elapsed = _run_script([
            str(SCRIPTS_DIR / "validate_renderer_pack_v2.py"),
            "--input", pack_path,
        ])
        return {"stage": "validate", "ok": ok, "artifact_path": None,
                "stdout_tail": tail, "elapsed_ms": elapsed}

    elif stage == "stream":
        pack_path = project["artifacts"].get("compiled_pack_path")
        if not pack_path:
            return {"stage": "stream", "ok": False, "artifact_path": None,
                    "stdout_tail": "compile_stage_required", "elapsed_ms": 0}
        out_path = paths["stream_manifest"]
        ok, tail, elapsed = _run_script([
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

    elif stage == "prefetch":
        stream_path = project["artifacts"].get("stream_manifest_path")
        if not stream_path:
            return {"stage": "prefetch", "ok": False, "artifact_path": None,
                    "stdout_tail": "stream_stage_required", "elapsed_ms": 0}
        out_path = paths["prefetch_manifest"]
        ok, tail, elapsed = _run_script([
            str(SCRIPTS_DIR / "build_renderer_prefetch_manifest_v1.py"),
            "--input", stream_path,
            "--output", str(out_path),
            "--max-ring", "2",
        ])
        if ok:
            project["artifacts"]["prefetch_manifest_path"] = str(out_path)
        return {"stage": "prefetch", "ok": ok, "artifact_path": str(out_path) if ok else None,
                "stdout_tail": tail, "elapsed_ms": elapsed}

    elif stage == "budget_check":
        stream_path = project["artifacts"].get("stream_manifest_path")
        if not stream_path:
            return {"stage": "budget_check", "ok": False, "artifact_path": None,
                    "stdout_tail": "stream_stage_required", "elapsed_ms": 0}
        out_path = paths["budget_report"]
        ok, tail, elapsed = _run_script([
            str(SCRIPTS_DIR / "check_renderer_stream_residency_budgets.py"),
            "--input", stream_path,
            "--output", str(out_path),
        ])
        return {"stage": "budget_check", "ok": ok, "artifact_path": str(out_path) if ok else None,
                "stdout_tail": tail, "elapsed_ms": elapsed}

    elif stage == "go_no_go":
        pack_path     = project["artifacts"].get("compiled_pack_path")
        stream_path   = project["artifacts"].get("stream_manifest_path")
        prefetch_path = project["artifacts"].get("prefetch_manifest_path")
        budget_path   = str(paths["budget_report"]) if paths["budget_report"].exists() else None
        if not pack_path or not stream_path or not prefetch_path:
            return {"stage": "go_no_go", "ok": False, "artifact_path": None,
                    "stdout_tail": "compile+stream+prefetch_stages_required", "elapsed_ms": 0}
        out_path = paths["toolchain_report"]
        args = [
            str(SCRIPTS_DIR / "renderer_toolchain_go_no_go.py"),
            "--compiled-pack", pack_path,
            "--stream-manifest", stream_path,
            "--prefetch-manifest", prefetch_path,
            "--output", str(out_path),
        ]
        if budget_path:
            args += ["--residency-report", budget_path]
        ok, tail, elapsed = _run_script(args)
        if ok:
            project["artifacts"]["toolchain_report_path"] = str(out_path)
            try:
                report = json.loads(out_path.read_text(encoding="utf-8"))
                project["readiness"]["readiness_green"] = bool(report.get("go", False))
                project["readiness"]["last_checked_at"] = _now_iso()
                project["gate_status"]["gate_a"] = "pass" if report.get("go") else "fail"
            except Exception:
                pass
        return {"stage": "go_no_go", "ok": ok, "artifact_path": str(out_path) if ok else None,
                "stdout_tail": tail, "elapsed_ms": elapsed}

    elif stage == "layer_project":
        report_path = project["artifacts"].get("toolchain_report_path")
        if not report_path:
            return {"stage": "layer_project", "ok": False, "artifact_path": None,
                    "stdout_tail": "go_no_go_stage_required", "elapsed_ms": 0}
        out_path = paths["layer_projection"]
        ok, tail, elapsed = _run_script([
            str(SCRIPTS_DIR / "renderer_toolchain_project_to_layers.py"),
            "--report", report_path,
            "--workspace-id", req.workspace_id,
            "--output", str(out_path),
        ])
        if ok:
            project["artifacts"]["layer_projection_path"] = str(out_path)
        return {"stage": "layer_project", "ok": ok, "artifact_path": str(out_path) if ok else None,
                "stdout_tail": tail, "elapsed_ms": elapsed}

    return {"stage": stage, "ok": False, "artifact_path": None,
            "stdout_tail": f"unknown_stage:{stage}", "elapsed_ms": 0}


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/readiness", summary="Get project readiness and federation status")
async def get_readiness(
    project_id: str,
    api_url: str = "http://127.0.0.1:9000",
    kernel_url: str = "http://127.0.0.1:8000",
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = _require_project(db, project_id)
    checks: list[dict[str, Any]] = []

    try:
        data = _http_get_json(f"{api_url}/ready")
        checks.append({"name": "api_ready", "ok": data.get("status") == "ready", "detail": data})
    except Exception as exc:
        checks.append({"name": "api_ready", "ok": False, "detail": {"error": str(exc)}})

    try:
        data = _http_get_json(f"{kernel_url}/health")
        checks.append({"name": "kernel_health", "ok": data.get("status") == "ok", "detail": data})
    except Exception as exc:
        checks.append({"name": "kernel_health", "ok": False, "detail": {"error": str(exc)}})

    if project["project_type"] in ("game_voxel", "hybrid"):
        report_path = project["artifacts"].get("toolchain_report_path")
        if report_path and Path(report_path).exists():
            try:
                report = json.loads(Path(report_path).read_text(encoding="utf-8"))
                go = bool(report.get("go", False))
                checks.append({"name": "toolchain_go_no_go", "ok": go, "detail": {"go": go}})
            except Exception as exc:
                checks.append({"name": "toolchain_go_no_go", "ok": False,
                               "detail": {"error": str(exc)}})
        else:
            checks.append({"name": "toolchain_go_no_go", "ok": False,
                          "detail": {"error": "toolchain_report_not_found"}})

    if project["project_type"] in ("arch_diagram", "hybrid"):
        spec = (project.get("arch_diagram") or {}).get("spec") or {}
        nodes = (
            list(spec.get("domains", [])) +
            list(spec.get("systems", [])) +
            list(spec.get("tools", []))
        )
        ok = len(nodes) > 0
        checks.append({"name": "arch_diagram_parse", "ok": ok,
                      "detail": {"node_count": len(nodes)}})

    federation: dict[str, Any] = {"ok": False, "status": "unknown", "error_count": -1}
    try:
        fed_data = _http_get_json(f"{api_url}/v1/federation/health")
        federation = {
            "ok": fed_data.get("status") == "ok" and fed_data.get("error_count", 1) == 0,
            "status": fed_data.get("status", "unknown"),
            "error_count": fed_data.get("error_count", -1),
            "active_trust_count": fed_data.get("active_trust_count", 0),
        }
    except Exception as exc:
        federation["error"] = str(exc)

    readiness_green = all(c["ok"] for c in checks)
    federation_green = bool(federation.get("ok", False))

    project["readiness"]["readiness_green"] = readiness_green
    project["readiness"]["federation_green"] = federation_green
    project["readiness"]["last_checked_at"] = _now_iso()
    _db_save(db, project)

    return ORJSONResponse(content={
        "ok": True,
        "project_id": project_id,
        "project_type": project["project_type"],
        "readiness_green": readiness_green,
        "federation_green": federation_green,
        "checks": checks,
        "federation": federation,
        "checked_at": _now_iso(),
    })


# ---------------------------------------------------------------------------
# Architecture diagram parse + export
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/arch_diagram/parse",
             summary="Parse architecture diagram source into normalized spec")
async def parse_arch_diagram(
    project_id: str,
    req: ArchDiagramParseRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = _require_project(db, project_id)
    if project["project_type"] not in ("arch_diagram", "hybrid"):
        raise HTTPException(status_code=422, detail="not_an_arch_diagram_project")

    errors: list[str] = []
    warnings: list[str] = []
    spec: dict[str, Any] = {}

    if req.mode == "json":
        try:
            raw = json.loads(req.source) if req.source.strip() else {}
            spec = raw if isinstance(raw, dict) else {}
            if not spec:
                warnings.append("empty_source")
        except json.JSONDecodeError as exc:
            errors.append(f"json_parse_error:{exc}")
    else:
        spec = {"_raw_mode": req.mode, "_raw_source": req.source[:4096]}
        warnings.append(f"server_side_{req.mode}_parse_not_yet_implemented:client_will_parse")

    if project.get("arch_diagram") is None:
        project["arch_diagram"] = {"spec": {}, "export_svg_path": None, "export_png_path": None}
    project["arch_diagram"]["spec"] = spec
    project["updated_at"] = _now_iso()
    _db_save(db, project)

    nodes = (
        list(spec.get("domains", [])) +
        list(spec.get("systems", [])) +
        list(spec.get("tools", []))
    )
    return ORJSONResponse(content={
        "ok": len(errors) == 0,
        "spec": spec,
        "node_count": len(nodes),
        "flow_count": len(spec.get("flows", [])),
        "errors": errors,
        "warnings": warnings,
    })


@router.post("/projects/{project_id}/arch_diagram/export",
             summary="Export architecture diagram to SVG (PNG requires client canvas)")
async def export_arch_diagram(
    project_id: str,
    req: ArchDiagramExportRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = _require_project(db, project_id)
    if req.format == "png":
        return ORJSONResponse(content={
            "ok": False,
            "format": "png",
            "error": "png_export_requires_client_canvas:use_renderLabArchDiagram.exportArchDiagramToPNG",
        })
    # Allow caller to pass a spec override (e.g. from client parse), else use stored spec
    spec = req.spec if req.spec is not None else (project.get("arch_diagram") or {}).get("spec") or {}
    if not spec:
        raise HTTPException(status_code=422, detail="no_arch_diagram_spec")
    svg = _spec_to_svg(spec)
    export_dir = REPORTS_DIR / "arch_diagrams"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / f"{project_id}.svg"
    out_path.write_text(svg, encoding="utf-8")
    if project.get("arch_diagram") is None:
        project["arch_diagram"] = {"spec": spec, "export_svg_path": None, "export_png_path": None}
    project["arch_diagram"]["export_svg_path"] = str(out_path)
    project["updated_at"] = _now_iso()
    _db_save(db, project)
    return ORJSONResponse(content={"ok": True, "format": "svg", "path": str(out_path), "data": svg})


def _spec_to_svg(spec: dict[str, Any]) -> str:
    """Generate a minimal structural SVG from an arch_diagram spec."""
    nodes = (
        list(spec.get("domains", [])) +
        list(spec.get("systems", [])) +
        list(spec.get("tools", []))
    )
    flows = spec.get("flows", [])

    lane_map: dict[str, list[dict]] = {}
    for n in nodes:
        lane = str(n.get("lane", "Systems"))
        lane_map.setdefault(lane, []).append(n)
    lanes = list(lane_map.keys())

    W, H = 960, max(420, 80 + 90 * max((len(v) for v in lane_map.values()), default=1))
    lane_w = W // max(len(lanes), 1)
    node_w, node_h = min(220, lane_w - 20), 60
    coords: dict[str, tuple[int, int]] = {}
    rects, labels, arrows = [], [], []

    for li, lane in enumerate(lanes):
        lx = li * lane_w
        rects.append(f'<rect x="{lx}" y="0" width="{lane_w}" height="{H}" '
                     f'fill="{"#14191f" if li % 2 == 0 else "#10151a"}" />')
        labels.append(f'<text x="{lx + 10}" y="18" fill="#9baec8" font-size="11" '
                      f'font-weight="600">{lane}</text>')
        for ri, node in enumerate(lane_map[lane]):
            nid = str(node.get("id", f"n{li}_{ri}"))
            nx = lx + (lane_w - node_w) // 2
            ny = 30 + ri * (node_h + 12)
            coords[nid] = (nx + node_w // 2, ny + node_h // 2)
            kind  = str(node.get("kind", "component"))
            color = {"domain": "#2f4f9d", "service": "#266d56", "engine": "#6f4b1f",
                     "data": "#5e2b69", "renderer": "#25416b", "tool": "#4a4f57"}.get(kind, "#3f4754")
            rects.append(f'<rect x="{nx}" y="{ny}" width="{node_w}" height="{node_h}" '
                         f'rx="8" fill="{color}" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>')
            name = str(node.get("name", nid))[:36]
            labels.append(f'<text x="{nx + 10}" y="{ny + 20}" fill="#f4f7fb" '
                          f'font-size="11" font-weight="600">{name}</text>')
            labels.append(f'<text x="{nx + 10}" y="{ny + 36}" fill="#c8d4e0" '
                          f'font-size="10">{kind}</text>')

    for flow in flows:
        fid = str(flow.get("from", ""))
        tid = str(flow.get("to", ""))
        if fid not in coords or tid not in coords:
            continue
        x1, y1 = coords[fid]
        x2, y2 = coords[tid]
        cx = (x1 + x2) // 2
        label = str(flow.get("label", ""))
        style = str(flow.get("style", "solid"))
        dash  = (' stroke-dasharray="6,3"' if style == "dashed" else
                 (' stroke-dasharray="2,3"' if style == "dotted" else ""))
        arrows.append(f'<path d="M{x1},{y1} C{cx},{y1} {cx},{y2} {x2},{y2}" '
                      f'stroke="#7a9ec8" stroke-width="1.25" fill="none"{dash}/>')
        if label:
            arrows.append(f'<text x="{cx}" y="{(y1+y2)//2 - 4}" fill="#aabdd4" '
                          f'font-size="10" text-anchor="middle">{label}</text>')

    body = "\n".join(rects + arrows + labels)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" style="background:#0b0e12">\n{body}\n</svg>')

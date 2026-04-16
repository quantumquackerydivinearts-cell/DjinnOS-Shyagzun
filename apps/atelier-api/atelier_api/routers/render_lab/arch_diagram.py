"""Render Lab architecture diagram — parse, export, SVG generation, and script persistence."""
from __future__ import annotations

import re
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...db import get_db
from ._db import db_save, require_project
from ._utils import REPORTS_DIR, now_iso

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ArchDiagramParseRequest(BaseModel):
    mode: str = Field(default="json", pattern="^(json|cobra|english|shygazun)$")
    source: str = Field(default="")


class ArchDiagramExportRequest(BaseModel):
    format: str = Field(default="svg", pattern="^(svg|png)$")
    spec: dict[str, Any] | None = None


class ArchDiagramScriptSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    mode: str = Field(default="cobra", pattern="^(json|cobra|english|shygazun)$")
    source: str = Field(default="")
    spec: dict[str, Any] | None = None   # pre-parsed override; if None, auto-parse from source


# ---------------------------------------------------------------------------
# Hardcoded default specs
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, dict[str, Any]] = {
    "djinnos_kernel_stack": {
        "_meta": {"title": "DjinnOS Kernel Stack", "description": "Core service topology"},
        "domains": [
            {"id": "kernel",    "name": "Shygazun Kernel",     "lane": "Core",     "kind": "domain"},
            {"id": "atelier",   "name": "Atelier API",          "lane": "Business", "kind": "domain"},
            {"id": "desktop",   "name": "Atelier Desktop",      "lane": "Surface",  "kind": "domain"},
            {"id": "gateway",   "name": "Kernel Gateway",       "lane": "Core",     "kind": "domain"},
        ],
        "systems": [
            {"id": "ceg",       "name": "CEG (Event Graph)",    "lane": "Core",     "kind": "engine"},
            {"id": "orrery",    "name": "Orrery (Multiverse)",  "lane": "Core",     "kind": "engine"},
            {"id": "breathofko","name": "BreathOfKo (Save)",    "lane": "Core",     "kind": "engine"},
            {"id": "sqlite",    "name": "SQLite Store",         "lane": "Data",     "kind": "data"},
            {"id": "ambroflow", "name": "Ambroflow Engine",     "lane": "Surface",  "kind": "service"},
        ],
        "tools": [
            {"id": "cobra",     "name": "Cobra Compiler",       "lane": "Business", "kind": "tool"},
            {"id": "pipeline",  "name": "Renderer Pipeline",    "lane": "Business", "kind": "tool"},
            {"id": "reasoning", "name": "Shygazun Reasoning",   "lane": "Business", "kind": "tool"},
        ],
        "flows": [
            {"from": "desktop",  "to": "atelier",   "label": "REST"},
            {"from": "atelier",  "to": "gateway",   "label": "allowlisted calls"},
            {"from": "gateway",  "to": "kernel",    "label": "kernel IPC"},
            {"from": "kernel",   "to": "ceg",       "label": "event dispatch"},
            {"from": "kernel",   "to": "breathofko","label": "save state"},
            {"from": "atelier",  "to": "sqlite",    "label": "persist"},
            {"from": "atelier",  "to": "orrery",    "label": "record"},
            {"from": "cobra",    "to": "kernel",    "label": "script compile", "style": "dashed"},
            {"from": "reasoning","to": "kernel",    "label": "tongue query",   "style": "dashed"},
            {"from": "desktop",  "to": "ambroflow", "label": "game runtime"},
        ],
    },
    "klgs_game_arch": {
        "_meta": {"title": "Ko's Labyrinth Game Architecture", "description": "7_KLGS game systems"},
        "domains": [
            {"id": "gamestate", "name": "Game State Machine",  "lane": "Runtime",  "kind": "domain"},
            {"id": "world",     "name": "World / Realm Layer", "lane": "World",    "kind": "domain"},
            {"id": "player",    "name": "Player Entity",       "lane": "Runtime",  "kind": "domain"},
        ],
        "systems": [
            {"id": "dungeon",   "name": "Dungeon Registry",    "lane": "World",    "kind": "engine"},
            {"id": "encounter", "name": "Encounter Resolver",  "lane": "Runtime",  "kind": "engine"},
            {"id": "skills",    "name": "Skills Runtime",      "lane": "Runtime",  "kind": "service"},
            {"id": "sanity",    "name": "Sanity Live System",  "lane": "Runtime",  "kind": "service"},
            {"id": "quest",     "name": "Quest Tracker",       "lane": "Runtime",  "kind": "service"},
            {"id": "alchemy",   "name": "Alchemy System",      "lane": "Runtime",  "kind": "service"},
            {"id": "journal",   "name": "Journal System",      "lane": "Surface",  "kind": "service"},
            {"id": "pathfind",  "name": "Pathfinding (A*)",    "lane": "World",    "kind": "engine"},
            {"id": "orrery_c",  "name": "Orrery Client",       "lane": "Runtime",  "kind": "service"},
            {"id": "vitriol",   "name": "VITRIOL Stat System", "lane": "Runtime",  "kind": "data"},
            {"id": "ko_dlg",    "name": "Ko Dialogue Renderer","lane": "Surface",  "kind": "renderer"},
        ],
        "tools": [
            {"id": "koflags",   "name": "KoFlags",             "lane": "World",    "kind": "tool"},
            {"id": "julia",     "name": "Julia Set Renderer",  "lane": "Surface",  "kind": "tool"},
        ],
        "flows": [
            {"from": "gamestate","to": "world",    "label": "load"},
            {"from": "gamestate","to": "player",   "label": "init"},
            {"from": "player",  "to": "encounter", "label": "triggers"},
            {"from": "player",  "to": "skills",    "label": "train/use"},
            {"from": "player",  "to": "sanity",    "label": "affect"},
            {"from": "dungeon", "to": "pathfind",  "label": "navmesh"},
            {"from": "quest",   "to": "alchemy",   "label": "unlock gates"},
            {"from": "orrery_c","to": "orrery_c",  "label": "multiverse sync", "style": "dotted"},
            {"from": "ko_dlg",  "to": "julia",     "label": "portrait render"},
        ],
    },
    "shygazun_tongue_registry": {
        "_meta": {"title": "Shygazun Tongue Registry", "description": "32-tongue coordinate space"},
        "domains": [
            {"id": "g1", "name": "Group 1 (T1–T8)",   "lane": "Groups", "kind": "domain"},
            {"id": "g2", "name": "Group 2 (T9–T16)",  "lane": "Groups", "kind": "domain"},
            {"id": "g3", "name": "Group 3 (T17–T24)", "lane": "Groups", "kind": "domain"},
            {"id": "g4", "name": "Groups 4+ (T25–)",  "lane": "Groups", "kind": "domain"},
        ],
        "systems": [
            {"id": "t1",  "name": "T1 Lotus (8 cands)",    "lane": "Group 1", "kind": "engine"},
            {"id": "t2",  "name": "T2 Rose (10 cands)",    "lane": "Group 1", "kind": "engine"},
            {"id": "t3",  "name": "T3 Sakura (10 cands)",  "lane": "Group 1", "kind": "engine"},
            {"id": "t4",  "name": "T4 Daisy (12 cands)",   "lane": "Group 1", "kind": "engine"},
            {"id": "t9",  "name": "T9 Dragon (30 cands)",  "lane": "Group 2", "kind": "engine"},
            {"id": "t10", "name": "T10 Virus (30 cands)",  "lane": "Group 2", "kind": "engine"},
            {"id": "t11", "name": "T11 Bacteria (30)",     "lane": "Group 2", "kind": "engine"},
            {"id": "t12", "name": "T12 Excavata (30)",     "lane": "Group 2", "kind": "engine"},
            {"id": "t19", "name": "T19 Serpent (36)",      "lane": "Group 3", "kind": "engine"},
            {"id": "t32", "name": "T32 Moon (44 cands)",   "lane": "Group 4", "kind": "engine"},
        ],
        "tools": [
            {"id": "topology",  "name": "tongue_topology.py",  "lane": "Runtime", "kind": "tool"},
            {"id": "corpus",    "name": "shygazun_corpus.py",  "lane": "Runtime", "kind": "tool"},
            {"id": "reasoning", "name": "ShygazunReasoningService", "lane": "Runtime", "kind": "tool"},
        ],
        "flows": [
            {"from": "g1",      "to": "g2",      "label": "recombination priors"},
            {"from": "g2",      "to": "g3",      "label": "YeGaoh"},
            {"from": "topology","to": "reasoning","label": "registry"},
            {"from": "corpus",  "to": "reasoning","label": "few-shot"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Endpoints — defaults
# ---------------------------------------------------------------------------

@router.get("/arch_diagram/defaults",
            summary="List hardcoded default arch diagram specs")
async def list_arch_diagram_defaults() -> ORJSONResponse:
    summaries = [
        {
            "key": key,
            "title": spec.get("_meta", {}).get("title", key),
            "description": spec.get("_meta", {}).get("description", ""),
            "node_count": (
                len(spec.get("domains", [])) +
                len(spec.get("systems", [])) +
                len(spec.get("tools", []))
            ),
            "flow_count": len(spec.get("flows", [])),
        }
        for key, spec in _DEFAULTS.items()
    ]
    return ORJSONResponse(content={"ok": True, "defaults": summaries, "count": len(summaries)})


@router.get("/arch_diagram/defaults/{key}",
            summary="Get a hardcoded default arch diagram spec by key")
async def get_arch_diagram_default(key: str) -> ORJSONResponse:
    if key not in _DEFAULTS:
        raise HTTPException(status_code=404, detail=f"default_not_found:{key}")
    spec = {k: v for k, v in _DEFAULTS[key].items() if not k.startswith("_")}
    return ORJSONResponse(content={"ok": True, "key": key, "spec": spec})


# ---------------------------------------------------------------------------
# Endpoints — project arch diagram parse / export
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/arch_diagram/parse",
             summary="Parse architecture diagram source into normalized spec")
async def parse_arch_diagram(
    project_id: str,
    req: ArchDiagramParseRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    import json

    project = require_project(db, project_id)
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

    elif req.mode == "cobra":
        spec, cobra_errors, cobra_warnings = _parse_cobra_to_spec(req.source)
        errors.extend(cobra_errors)
        warnings.extend(cobra_warnings)

    else:
        spec = {"_raw_mode": req.mode, "_raw_source": req.source[:4096]}
        warnings.append(f"server_side_{req.mode}_parse_not_yet_implemented:client_will_parse")

    _ensure_arch_diagram(project)
    project["arch_diagram"]["spec"] = spec
    project["updated_at"] = now_iso()
    db_save(db, project)

    nodes = _count_nodes(spec)
    return ORJSONResponse(content={
        "ok": len(errors) == 0,
        "spec": spec,
        "node_count": nodes,
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
    project = require_project(db, project_id)

    if req.format == "png":
        return ORJSONResponse(content={
            "ok": False,
            "format": "png",
            "error": "png_export_requires_client_canvas:use_renderLabArchDiagram.exportArchDiagramToPNG",
        })

    spec = req.spec if req.spec is not None else (project.get("arch_diagram") or {}).get("spec") or {}
    if not spec:
        raise HTTPException(status_code=422, detail="no_arch_diagram_spec")

    svg = _spec_to_svg(spec)
    export_dir = REPORTS_DIR / "arch_diagrams"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / f"{project_id}.svg"
    out_path.write_text(svg, encoding="utf-8")

    _ensure_arch_diagram(project)
    project["arch_diagram"]["export_svg_path"] = str(out_path)
    project["updated_at"] = now_iso()
    db_save(db, project)

    return ORJSONResponse(content={"ok": True, "format": "svg", "path": str(out_path), "data": svg})


# ---------------------------------------------------------------------------
# Endpoints — script persistence
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/arch_diagram/scripts",
             summary="Save a named arch diagram script to the project")
async def save_arch_diagram_script(
    project_id: str,
    req: ArchDiagramScriptSaveRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    import json as _json

    project = require_project(db, project_id)
    if project["project_type"] not in ("arch_diagram", "hybrid"):
        raise HTTPException(status_code=422, detail="not_an_arch_diagram_project")

    _ensure_arch_diagram(project)

    # Auto-parse spec if not provided
    if req.spec is not None:
        spec = req.spec
        warnings: list[str] = []
        errors: list[str] = []
    elif req.mode == "json":
        try:
            raw = _json.loads(req.source) if req.source.strip() else {}
            spec = raw if isinstance(raw, dict) else {}
            errors, warnings = [], (["empty_source"] if not spec else [])
        except _json.JSONDecodeError as exc:
            spec = {}
            errors = [f"json_parse_error:{exc}"]
            warnings = []
    elif req.mode == "cobra":
        spec, errors, warnings = _parse_cobra_to_spec(req.source)
    else:
        spec = {"_raw_mode": req.mode, "_raw_source": req.source[:4096]}
        errors, warnings = [], [f"server_side_{req.mode}_parse_not_yet_implemented"]

    scripts: list[dict[str, Any]] = project["arch_diagram"].get("scripts") or []
    # Replace existing script with the same name, or append
    existing_idx = next((i for i, s in enumerate(scripts) if s.get("name") == req.name), None)
    entry: dict[str, Any] = {
        "name":       req.name,
        "mode":       req.mode,
        "source":     req.source,
        "spec":       spec,
        "created_at": now_iso() if existing_idx is None else scripts[existing_idx].get("created_at", now_iso()),
        "updated_at": now_iso(),
    }
    if existing_idx is not None:
        scripts[existing_idx] = entry
        action = "updated"
    else:
        scripts.append(entry)
        action = "created"

    project["arch_diagram"]["scripts"] = scripts
    project["updated_at"] = now_iso()
    db_save(db, project)

    return ORJSONResponse(content={
        "ok": len(errors) == 0,
        "action": action,
        "name": req.name,
        "node_count": _count_nodes(spec),
        "flow_count": len(spec.get("flows", [])),
        "errors": errors,
        "warnings": warnings,
    })


@router.get("/projects/{project_id}/arch_diagram/scripts",
            summary="List saved arch diagram scripts for a project")
async def list_arch_diagram_scripts(
    project_id: str,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = require_project(db, project_id)
    scripts = (project.get("arch_diagram") or {}).get("scripts") or []
    summaries = [
        {
            "name":       s.get("name"),
            "mode":       s.get("mode"),
            "node_count": _count_nodes(s.get("spec") or {}),
            "flow_count": len((s.get("spec") or {}).get("flows", [])),
            "updated_at": s.get("updated_at"),
        }
        for s in scripts
    ]
    return ORJSONResponse(content={"ok": True, "scripts": summaries, "count": len(summaries)})


@router.delete("/projects/{project_id}/arch_diagram/scripts/{script_name}",
               summary="Delete a saved arch diagram script")
async def delete_arch_diagram_script(
    project_id: str,
    script_name: str,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = require_project(db, project_id)
    _ensure_arch_diagram(project)
    scripts = project["arch_diagram"].get("scripts") or []
    before = len(scripts)
    scripts = [s for s in scripts if s.get("name") != script_name]
    if len(scripts) == before:
        raise HTTPException(status_code=404, detail=f"script_not_found:{script_name}")
    project["arch_diagram"]["scripts"] = scripts
    project["updated_at"] = now_iso()
    db_save(db, project)
    return ORJSONResponse(content={"ok": True, "deleted": script_name})


# ---------------------------------------------------------------------------
# Cobra parser → arch diagram spec
# ---------------------------------------------------------------------------

def _parse_cobra_to_spec(
    source: str,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """
    Parse a cobra script into an arch_diagram spec.

    Cobra grammar (subset recognized server-side):
        entity <id> <x> <y> <tag> [<z>]
          name: <display name>
          lane: <lane name>
          kind: <domain|service|engine|data|renderer|tool>
          lex <shygazun_word>
          <key>: <value>
          <key> <value>
        flow <from_id> -> <to_id> [label "<text>"] [style solid|dashed|dotted]
        # comment lines are ignored
    """
    lines = source.splitlines()
    errors: list[str] = []
    warnings: list[str] = []

    entities: list[dict[str, Any]] = []
    flow_stmts: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for lineno, raw in enumerate(lines, 1):
        indent = len(raw) - len(raw.lstrip())
        text = raw.strip()
        if not text or text.startswith("#"):
            continue

        if indent > 0 and current is not None:
            # Indented attribute of current entity
            colon = text.find(":")
            space = text.find(" ")
            if colon > 0 and (space < 0 or colon < space):
                key = text[:colon].strip()
                val = text[colon + 1:].strip()
            elif space > 0:
                key = text[:space].strip()
                val = text[space + 1:].strip()
            else:
                key = text
                val = ""
            if key in ("lex", "akinenwun", "shygazun"):
                current["akinenwun"] = val
            else:
                current.setdefault("meta", {})[key] = val
                if key == "name":
                    current["name"] = val
                elif key == "lane":
                    current["lane"] = val
                elif key == "kind":
                    current["kind"] = val
            continue

        # Top-level statement
        current = None

        if re.match(r"^entity\s+", text, re.I):
            parts = text.split()
            if len(parts) < 5:
                warnings.append(f"L{lineno}: entity requires at least 'entity <id> <x> <y> <tag>'")
                continue
            # Detect optional z (5th token numeric → id x y z tag; else id x y tag)
            z_cand = parts[4] if len(parts) > 4 else ""
            if z_cand and _is_number(z_cand):
                tag = parts[5] if len(parts) > 5 else "none"
            else:
                tag = parts[4]
            ent: dict[str, Any] = {
                "id":   parts[1],
                "x":    _to_float(parts[2]),
                "y":    _to_float(parts[3]),
                "tag":  tag,
                "name": parts[1],   # default; may be overridden by indented name:
                "kind": tag,        # default; may be overridden by indented kind:
                "lane": "Systems",  # default; may be overridden by indented lane:
                "meta": {},
            }
            entities.append(ent)
            current = ent

        elif re.match(r"^flow\s+", text, re.I):
            # flow <from> -> <to> [label "text"] [style solid|dashed|dotted]
            parts = text.split(None, 1)
            rest = parts[1] if len(parts) > 1 else ""
            arrow_m = re.match(r"(\S+)\s*->\s*(\S+)(.*)", rest)
            if not arrow_m:
                warnings.append(f"L{lineno}: flow requires 'flow <from> -> <to>'")
                continue
            from_id = arrow_m.group(1)
            to_id   = arrow_m.group(2)
            tail    = arrow_m.group(3).strip()
            flow: dict[str, Any] = {"from": from_id, "to": to_id}
            lbl_m = re.search(r'label\s+"([^"]*)"', tail)
            if lbl_m:
                flow["label"] = lbl_m.group(1)
            style_m = re.search(r"style\s+(solid|dashed|dotted)", tail)
            if style_m:
                flow["style"] = style_m.group(1)
            flow_stmts.append(flow)

        elif re.match(r"^(lex|akinenwun|word)\s+", text, re.I):
            # Standalone lexical declaration — not a node, just noted
            pass

        else:
            warnings.append(f"L{lineno}: unrecognized statement: {text[:60]}")

    # Partition entities into domains / systems / tools by kind
    kind_bucket: dict[str, str] = {
        "domain":   "domains",
        "service":  "systems",
        "engine":   "systems",
        "data":     "systems",
        "renderer": "systems",
        "tool":     "tools",
    }
    spec: dict[str, Any] = {"domains": [], "systems": [], "tools": [], "flows": flow_stmts}
    for ent in entities:
        kind = str(ent.get("kind", "tool")).lower()
        bucket = kind_bucket.get(kind, "tools")
        node: dict[str, Any] = {
            "id":   ent["id"],
            "name": ent.get("name", ent["id"]),
            "kind": kind,
            "lane": ent.get("lane", "Systems"),
        }
        if ent.get("akinenwun"):
            node["akinenwun"] = ent["akinenwun"]
        if ent.get("meta"):
            remaining = {k: v for k, v in ent["meta"].items()
                         if k not in ("name", "lane", "kind", "lex", "akinenwun", "shygazun")}
            if remaining:
                node["meta"] = remaining
        spec[bucket].append(node)

    return spec, errors, warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_arch_diagram(project: dict[str, Any]) -> None:
    if project.get("arch_diagram") is None:
        project["arch_diagram"] = {"spec": {}, "export_svg_path": None, "export_png_path": None, "scripts": []}
    elif "scripts" not in project["arch_diagram"]:
        project["arch_diagram"]["scripts"] = []


def _count_nodes(spec: dict[str, Any]) -> int:
    return (
        len(spec.get("domains", [])) +
        len(spec.get("systems", [])) +
        len(spec.get("tools", []))
    )


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _to_float(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# SVG generation — content-responsive layout
# ---------------------------------------------------------------------------

def _spec_to_svg(spec: dict[str, Any]) -> str:
    """
    Generate a structural SVG from an arch_diagram spec.

    Layout scales with content:
    - Width = max(960, lane_count × 280)
    - Height = max(480, header + max_nodes_per_lane × (node_h + gap) + footer)
    """
    nodes = (
        list(spec.get("domains", [])) +
        list(spec.get("systems", [])) +
        list(spec.get("tools", []))
    )
    flows = spec.get("flows", [])

    # Group nodes into lanes
    lane_map: dict[str, list[dict]] = {}
    for n in nodes:
        lane = str(n.get("lane", "Systems"))
        lane_map.setdefault(lane, []).append(n)
    lanes = list(lane_map.keys())

    # Responsive dimensions
    lane_count    = max(len(lanes), 1)
    max_per_lane  = max((len(v) for v in lane_map.values()), default=1)
    node_h        = 66
    node_gap      = 14
    header_pad    = 32
    footer_pad    = 20

    W        = max(960, lane_count * 280)
    H        = max(480, header_pad + max_per_lane * (node_h + node_gap) + footer_pad + 20)
    lane_w   = W // lane_count
    node_w   = max(180, lane_w - 24)

    coords: dict[str, tuple[int, int]] = {}
    rects, labels, arrows = [], [], []

    for li, lane in enumerate(lanes):
        lx = li * lane_w
        # Lane background stripe
        rects.append(
            f'<rect x="{lx}" y="0" width="{lane_w}" height="{H}" '
            f'fill="{"#14191f" if li % 2 == 0 else "#10151a"}" />'
        )
        # Lane header separator line
        rects.append(
            f'<line x1="{lx}" y1="24" x2="{lx + lane_w}" y2="24" '
            f'stroke="rgba(255,255,255,0.06)" stroke-width="1"/>'
        )
        labels.append(
            f'<text x="{lx + 10}" y="17" fill="#7a9ec8" font-size="11" '
            f'font-family="monospace" font-weight="700" letter-spacing="0.5">'
            f'{_esc(lane)}</text>'
        )
        for ri, node in enumerate(lane_map[lane]):
            nid = str(node.get("id", f"n{li}_{ri}"))
            nx  = lx + (lane_w - node_w) // 2
            ny  = header_pad + ri * (node_h + node_gap)
            coords[nid] = (nx + node_w // 2, ny + node_h // 2)

            kind  = str(node.get("kind", "component")).lower()
            color = {
                "domain":   "#2f4f9d",
                "service":  "#266d56",
                "engine":   "#6f4b1f",
                "data":     "#5e2b69",
                "renderer": "#25416b",
                "tool":     "#4a4f57",
            }.get(kind, "#3f4754")

            rects.append(
                f'<rect x="{nx}" y="{ny}" width="{node_w}" height="{node_h}" '
                f'rx="8" fill="{color}" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>'
            )
            name = _esc(str(node.get("name", nid))[:40])
            labels.append(
                f'<text x="{nx + 10}" y="{ny + 21}" fill="#eef2f8" '
                f'font-size="11" font-family="sans-serif" font-weight="600">{name}</text>'
            )
            labels.append(
                f'<text x="{nx + 10}" y="{ny + 37}" fill="#8aa4be" '
                f'font-size="10" font-family="monospace">{_esc(kind)}</text>'
            )
            # Akinenwun word if present
            akin = str(node.get("akinenwun", ""))
            if akin:
                labels.append(
                    f'<text x="{nx + 10}" y="{ny + 53}" fill="#6e8fa8" '
                    f'font-size="9" font-family="monospace" font-style="italic">{_esc(akin[:30])}</text>'
                )

    # Arrowhead marker
    defs = (
        '<defs>'
        '<marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
        '<polygon points="0 0, 8 3, 0 6" fill="#7a9ec8"/>'
        '</marker>'
        '</defs>'
    )

    for flow in flows:
        fid = str(flow.get("from", ""))
        tid = str(flow.get("to", ""))
        if fid not in coords or tid not in coords:
            continue
        x1, y1 = coords[fid]
        x2, y2 = coords[tid]
        # Self-loops: small arc to the right
        if fid == tid:
            r = 28
            arrows.append(
                f'<path d="M{x1 + node_w // 2 - 10},{y1} a{r},{r} 0 1,1 0,1" '
                f'stroke="#7a9ec8" stroke-width="1.1" fill="none" stroke-dasharray="3,2"/>'
            )
            continue
        cx = (x1 + x2) // 2
        label = str(flow.get("label", ""))
        style = str(flow.get("style", "solid"))
        dash  = (
            ' stroke-dasharray="6,3"' if style == "dashed" else
            (' stroke-dasharray="2,3"'  if style == "dotted" else "")
        )
        arrows.append(
            f'<path d="M{x1},{y1} C{cx},{y1} {cx},{y2} {x2},{y2}" '
            f'stroke="#7a9ec8" stroke-width="1.2" fill="none"{dash} '
            f'marker-end="url(#arrowhead)"/>'
        )
        if label:
            arrows.append(
                f'<text x="{cx}" y="{(y1 + y2) // 2 - 5}" fill="#aabdd4" '
                f'font-size="10" font-family="sans-serif" text-anchor="middle">{_esc(label)}</text>'
            )

    body = "\n".join([defs] + rects + arrows + labels)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" style="background:#0b0e12;display:block">\n{body}\n</svg>'
    )


def _esc(s: str) -> str:
    """Minimal XML/SVG text escaping."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )
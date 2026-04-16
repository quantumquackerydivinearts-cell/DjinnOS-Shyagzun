"""Render Lab tile generator scripts — hardcoded defaults, user-saved scripts, and server-side execution."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from ._utils import ROOT, now_iso

router = APIRouter()

TILE_SCRIPTS_PATH = ROOT / "gameplay" / "tile_scripts.json"

# ---------------------------------------------------------------------------
# Hardcoded default templates (mirrors TILE_PROC_FORM_LIBRARY in App.jsx)
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, str] = {
    "ring_bloom": "\n".join([
        "const cx = Math.floor(cols / 2);",
        "const cy = Math.floor(rows / 2);",
        "const radius = Math.max(4, Math.floor(Math.min(cols, rows) * 0.22));",
        'const tokens = ["Ru","Ot","El","Ki","Fu","Ka","AE"];',
        "const tiles = [];",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const dx = x - cx;",
        "    const dy = y - cy;",
        "    const d = Math.sqrt(dx * dx + dy * dy);",
        "    if (Math.abs(d - radius) <= 1.25) {",
        "      const idx = (x + y + seed) % tokens.length;",
        '      tiles.push({ x, y, layer: "base", color_token: tokens[idx], opacity_token: "Na", presence_token: "Ta" });',
        "    }",
        "  }",
        "}",
        "return { tiles, links: [], entities: [{ id: `ring-${seed}`, kind: \"pattern\", x: cx, y: cy }] };",
    ]),
    "maze_carve": "\n".join([
        "const tiles = [];",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const wall = x % 2 === 0 || y % 2 === 0;",
        "    tiles.push({",
        '      x, y, layer: wall ? "ground" : "base",',
        '      color_token: wall ? "Ga" : "Ki",',
        '      opacity_token: wall ? "Ung" : "Na",',
        '      presence_token: "Ta"',
        "    });",
        "  }",
        "}",
        "for (let n = 0; n < Math.floor((cols * rows) * 0.12); n += 1) {",
        "  const x = (seed * 13 + n * 17) % cols;",
        "  const y = (seed * 7 + n * 19) % rows;",
        '  tiles.push({ x, y, layer: "base", color_token: "Ki", opacity_token: "Na", presence_token: "Ta" });',
        "}",
        "return { tiles, links: [] };",
    ]),
    "island_chain": "\n".join([
        "const tiles = [];",
        "const centers = [",
        "  { x: Math.floor(cols * 0.2), y: Math.floor(rows * 0.35), r: Math.floor(Math.min(cols, rows) * 0.12) },",
        "  { x: Math.floor(cols * 0.5), y: Math.floor(rows * 0.52), r: Math.floor(Math.min(cols, rows) * 0.15) },",
        "  { x: Math.floor(cols * 0.78), y: Math.floor(rows * 0.42), r: Math.floor(Math.min(cols, rows) * 0.1) },",
        "];",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    let land = false;",
        "    for (const c of centers) {",
        "      const dx = x - c.x; const dy = y - c.y;",
        "      if (Math.sqrt(dx * dx + dy * dy) <= c.r) { land = true; break; }",
        "    }",
        "    tiles.push({",
        '      x, y, layer: "base",',
        '      color_token: land ? "Ki" : "Fu",',
        '      opacity_token: land ? "Na" : "Wu",',
        '      presence_token: "Ta"',
        "    });",
        "  }",
        "}",
        "return { tiles, links: [] };",
    ]),
    "corridor_grid": "\n".join([
        "const tiles = [];",
        "const links = [];",
        "const step = 4;",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const corridor = x % step === 0 || y % step === 0;",
        "    tiles.push({",
        '      x, y, layer: "base",',
        '      color_token: corridor ? "El" : "Ga",',
        '      opacity_token: corridor ? "Na" : "Ung",',
        '      presence_token: "Ta"',
        "    });",
        "    if (corridor && x + step < cols && y % step === 0) {",
        "      links.push({ ax: x, ay: y, bx: x + step, by: y });",
        "    }",
        "    if (corridor && y + step < rows && x % step === 0) {",
        "      links.push({ ax: x, ay: y, bx: x, by: y + step });",
        "    }",
        "  }",
        "}",
        "return { tiles, links };",
    ]),
    "noise_caves": "\n".join([
        "function noise(x, y, s) {",
        "  const n = Math.sin((x * 12.9898 + y * 78.233 + s) * 43758.5453);",
        "  return n - Math.floor(n);",
        "}",
        "const tiles = [];",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const n = noise(x, y, seed);",
        "    const solid = n > 0.48;",
        "    tiles.push({",
        '      x, y, layer: "base",',
        '      color_token: solid ? "Ga" : "Fu",',
        '      opacity_token: solid ? "Ung" : "Wu",',
        '      presence_token: "Ta"',
        "    });",
        "  }",
        "}",
        "return { tiles, links: [] };",
    ]),
    "navigable_town": "\n".join([
        "const tiles = [];",
        "const links = [];",
        "const entities = [];",
        "const walkable = new Set();",
        "const toKey = (x, y) => `${x},${y}`;",
        "const centerX = Math.floor(cols / 2);",
        "const centerY = Math.floor(rows / 2);",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const border = x === 0 || y === 0 || x === cols - 1 || y === rows - 1;",
        "    const crossRoad = Math.abs(x - centerX) <= 1 || Math.abs(y - centerY) <= 1;",
        "    const lane = x % 8 === 0 || y % 8 === 0;",
        "    const isWalk = !border && (crossRoad || lane);",
        "    tiles.push({",
        '      x, y, layer: "base",',
        '      color_token: border ? "Ga" : isWalk ? "El" : "Ki",',
        '      opacity_token: border ? "Ung" : "Na",',
        '      presence_token: "Ta",',
        "      meta: { walkable: isWalk }",
        "    });",
        "    if (isWalk) walkable.add(toKey(x, y));",
        "  }",
        "}",
        "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
        "for (const key of walkable) {",
        "  const [xRaw, yRaw] = key.split(\",\");",
        "  const x = Number(xRaw); const y = Number(yRaw);",
        "  for (const [dx, dy] of dirs) {",
        "    const nx = x + dx; const ny = y + dy;",
        "    const nKey = toKey(nx, ny);",
        "    if (!walkable.has(nKey) || nx < x || ny < y) continue;",
        "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
        "  }",
        "}",
        "entities.push({ id: \"player\", kind: \"player\", x: centerX, y: centerY, z: 1 });",
        "for (let i = 0; i < 8; i += 1) {",
        "  const ox = ((seed + i * 11) % (cols - 4)) + 2;",
        "  const oy = ((seed * 3 + i * 7) % (rows - 4)) + 2;",
        "  if (walkable.has(toKey(ox, oy))) entities.push({ id: `npc_${i + 1}`, kind: \"npc\", x: ox, y: oy, z: 1 });",
        "}",
        "return { tiles, links, entities };",
    ]),
    "navigable_wilds": "\n".join([
        "function noise(x, y, s) {",
        "  const n = Math.sin((x * 12.9898 + y * 78.233 + s) * 43758.5453);",
        "  return n - Math.floor(n);",
        "}",
        "const tiles = [];",
        "const links = [];",
        "const entities = [];",
        "const walkable = new Set();",
        "const toKey = (x, y) => `${x},${y}`;",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const n = noise(x, y, seed);",
        "    const river = Math.abs(y - Math.floor(rows * 0.55 + Math.sin(x * 0.17) * 3)) <= 1;",
        "    const isRock = n > 0.76;",
        "    const isWalk = !river && !isRock;",
        "    tiles.push({",
        '      x, y, layer: "base",',
        '      color_token: river ? "Fu" : isRock ? "Ga" : "Ki",',
        '      opacity_token: river ? "Wu" : isRock ? "Ung" : "Na",',
        '      presence_token: "Ta",',
        "      meta: { walkable: isWalk }",
        "    });",
        "    if (isWalk) walkable.add(toKey(x, y));",
        "  }",
        "}",
        "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
        "for (const key of walkable) {",
        "  const [xRaw, yRaw] = key.split(\",\");",
        "  const x = Number(xRaw); const y = Number(yRaw);",
        "  for (const [dx, dy] of dirs) {",
        "    const nx = x + dx; const ny = y + dy;",
        "    const nKey = toKey(nx, ny);",
        "    if (!walkable.has(nKey) || nx < x || ny < y) continue;",
        "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
        "  }",
        "}",
        "const centerX = Math.floor(cols / 2);",
        "const centerY = Math.floor(rows / 2);",
        "entities.push({ id: \"player\", kind: \"player\", x: centerX, y: centerY, z: 1 });",
        "for (let i = 0; i < 10; i += 1) {",
        "  const ox = ((seed * 5 + i * 13) % (cols - 2)) + 1;",
        "  const oy = ((seed * 7 + i * 17) % (rows - 2)) + 1;",
        "  if (walkable.has(toKey(ox, oy))) entities.push({ id: `npc_wild_${i + 1}`, kind: \"npc\", x: ox, y: oy, z: 1 });",
        "}",
        "return { tiles, links, entities };",
    ]),
    "humanoid_curve": "\n".join([
        "const tiles = [];",
        "const links = [];",
        "const entities = [];",
        "const walkableSet = new Set();",
        "const toKey = (x, y) => `${x},${y}`;",
        "const cx = Math.floor(cols * 0.5);",
        "const cy = Math.floor(rows * 0.52);",
        "const clamp01 = (v) => Math.max(0, Math.min(1, v));",
        "const dist = (x1, y1, x2, y2) => Math.hypot(x1 - x2, y1 - y2);",
        "const sdfCircle = (x, y, ox, oy, r) => dist(x, y, ox, oy) - r;",
        "const sdfCapsule = (x, y, ax, ay, bx, by, r) => {",
        "  const pax = x - ax; const pay = y - ay;",
        "  const bax = bx - ax; const bay = by - ay;",
        "  const h = clamp01((pax * bax + pay * bay) / Math.max(1e-6, bax * bax + bay * bay));",
        "  return Math.hypot(pax - bax * h, pay - bay * h) - r;",
        "};",
        "const torsoTopX = cx; const torsoTopY = cy - 8;",
        "const torsoBotX = cx; const torsoBotY = cy + 4;",
        "const headX = cx; const headY = cy - 12;",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const dHead = sdfCircle(x, y, headX, headY, 3.2);",
        "    const dTorso = sdfCapsule(x, y, torsoTopX, torsoTopY, torsoBotX, torsoBotY, 2.6);",
        "    const dArmL = sdfCapsule(x, y, cx-1, cy-6, cx-8, cy-1, 1.35);",
        "    const dArmR = sdfCapsule(x, y, cx+1, cy-6, cx+8, cy-1, 1.35);",
        "    const dLegL = sdfCapsule(x, y, cx-1, cy+4, cx-4, cy+13, 1.55);",
        "    const dLegR = sdfCapsule(x, y, cx+1, cy+4, cx+4, cy+13, 1.55);",
        "    const d = Math.min(dHead, dTorso, dArmL, dArmR, dLegL, dLegR);",
        "    const inside = d <= 0;",
        '    const shade = inside ? "El" : d < 1.6 ? "Ot" : "Ga";',
        "    if (inside || d < 1.2) {",
        "      tiles.push({",
        '        x, y, layer: "base",',
        "        color_token: shade,",
        '        opacity_token: inside ? "Na" : "Wu",',
        '        presence_token: "Ta",',
        "        meta: { lod: inside ? 3 : 1, curve: true, sdf: Number(d.toFixed(3)) }",
        "      });",
        "      if (inside) walkableSet.add(toKey(x, y));",
        "    }",
        "  }",
        "}",
        "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
        "for (const key of walkableSet) {",
        "  const [xRaw, yRaw] = key.split(\",\");",
        "  const x = Number(xRaw); const y = Number(yRaw);",
        "  for (const [dx, dy] of dirs) {",
        "    const nx = x + dx; const ny = y + dy;",
        "    if (!walkableSet.has(toKey(nx, ny)) || nx < x || ny < y) continue;",
        "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
        "  }",
        "}",
        "entities.push({ id: \"player\", kind: \"player\", x: cx, y: cy + 1, z: 1 });",
        "entities.push({ id: \"npc_curve_demo\", kind: \"npc\", x: cx, y: cy - 4, z: 1 });",
        "return { tiles, links, entities };",
    ]),
    "grilled_cheese": "\n".join([
        "const tiles = [];",
        "const links = [];",
        "const entities = [];",
        "const cx = Math.floor(cols * 0.5);",
        "const cy = Math.floor(rows * 0.55);",
        "const w = Math.max(12, Math.floor(cols * 0.32));",
        "const h = Math.max(8, Math.floor(rows * 0.22));",
        "const left = cx - Math.floor(w / 2);",
        "const top = cy - Math.floor(h / 2);",
        "const right = left + w - 1;",
        "const bottom = top + h - 1;",
        "for (let y = 0; y < rows; y += 1) {",
        "  for (let x = 0; x < cols; x += 1) {",
        "    const inRect = x >= left && x <= right && y >= top && y <= bottom;",
        "    if (!inRect) continue;",
        "    const edge = x === left || x === right || y === top || y === bottom;",
        "    const crust = edge || x === left+1 || x === right-1 || y === top+1 || y === bottom-1;",
        "    const cheeseBand = y >= top + Math.floor(h * 0.42) && y <= top + Math.floor(h * 0.62);",
        "    const searMark = ((x + y + seed) % 7 === 0) || ((x * 2 + y + seed) % 11 === 0);",
        '    const color = crust ? "Ot" : cheeseBand ? "Ru" : searMark ? "Ga" : "El";',
        '    const opacity = crust ? "Ung" : cheeseBand ? "Na" : "Wu";',
        "    tiles.push({",
        '      x, y, layer: "base", color_token: color, opacity_token: opacity, presence_token: "Ta",',
        "      meta: { lod: 3, subject: \"grilled_cheese\", edible: true }",
        "    });",
        "  }",
        "}",
        "const plateY = Math.min(rows - 2, bottom + 2);",
        "for (let x = left - 2; x <= right + 2; x += 1) {",
        "  if (x < 0 || x >= cols) continue;",
        "  tiles.push({",
        '    x, y: plateY, layer: "detail", color_token: "Ga", opacity_token: "Wu", presence_token: "Ta",',
        "    meta: { lod: 2, subject: \"plate_shadow\" }",
        "  });",
        "}",
        "entities.push({ id: \"grilled_cheese_test\", kind: \"prop\", x: cx, y: cy, z: 1 });",
        "return { tiles, links, entities };",
    ]),
}

_DEFAULT_LABELS: dict[str, str] = {
    "ring_bloom":      "Ring Bloom",
    "maze_carve":      "Maze Carve",
    "island_chain":    "Island Chain",
    "corridor_grid":   "Corridor Grid",
    "noise_caves":     "Noise Caves",
    "navigable_town":  "Navigable Town",
    "navigable_wilds": "Navigable Wilds",
    "humanoid_curve":  "Humanoid Curve (LOD Demo)",
    "grilled_cheese":  "Grilled Cheese (Pixel Test)",
}


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_scripts() -> list[dict[str, Any]]:
    if not TILE_SCRIPTS_PATH.exists():
        return []
    try:
        return json.loads(TILE_SCRIPTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_scripts(scripts: list[dict[str, Any]]) -> None:
    TILE_SCRIPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TILE_SCRIPTS_PATH.write_text(json.dumps(scripts, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TileScriptSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128,
                      description="Unique script name (slug-style recommended)")
    code: str = Field(..., description="Procedural JS returning { tiles, links, entities? }")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Default generator params: cols, rows, seed, cellPx, colorToken, etc.",
    )
    description: str = Field(default="")


class TileScriptRunRequest(BaseModel):
    name: str | None = Field(default=None, description="Run a saved script by name (builtin or user)")
    code: str | None = Field(default=None, description="Inline JS code to run (ignored if name given)")
    seed: int = Field(default=42)
    cols: int = Field(default=64, ge=1, le=512)
    rows: int = Field(default=36, ge=1, le=512)
    layer: str = Field(default="base")


# ---------------------------------------------------------------------------
# Endpoints — defaults
# ---------------------------------------------------------------------------

@router.get("/tile_scripts/defaults",
            summary="List hardcoded tile generator template scripts")
async def list_tile_script_defaults() -> ORJSONResponse:
    items = [
        {
            "key":   key,
            "label": _DEFAULT_LABELS.get(key, key),
            "source": "builtin",
            "lines": _DEFAULTS[key].count("\n") + 1,
        }
        for key in _DEFAULTS
    ]
    return ORJSONResponse(content={"ok": True, "defaults": items, "count": len(items)})


@router.get("/tile_scripts/defaults/{key}",
            summary="Get a hardcoded tile generator template by key")
async def get_tile_script_default(key: str) -> ORJSONResponse:
    if key not in _DEFAULTS:
        raise HTTPException(status_code=404, detail=f"default_not_found:{key}")
    return ORJSONResponse(content={
        "ok":     True,
        "key":    key,
        "label":  _DEFAULT_LABELS.get(key, key),
        "source": "builtin",
        "code":   _DEFAULTS[key],
    })


# ---------------------------------------------------------------------------
# Endpoints — user scripts
# ---------------------------------------------------------------------------

@router.get("/tile_scripts",
            summary="List all saved user tile generator scripts")
async def list_tile_scripts() -> ORJSONResponse:
    scripts = _load_scripts()
    summaries = [
        {
            "name":        s["name"],
            "description": s.get("description", ""),
            "source":      "user",
            "lines":       s.get("code", "").count("\n") + 1,
            "updated_at":  s.get("updated_at"),
        }
        for s in scripts
    ]
    return ORJSONResponse(content={"ok": True, "scripts": summaries, "count": len(summaries)})


@router.post("/tile_scripts",
             summary="Save or update a user tile generator script")
async def save_tile_script(req: TileScriptSaveRequest) -> ORJSONResponse:
    scripts = _load_scripts()
    idx = next((i for i, s in enumerate(scripts) if s.get("name") == req.name), None)
    entry: dict[str, Any] = {
        "name":        req.name,
        "description": req.description,
        "code":        req.code,
        "params":      req.params,
        "source":      "user",
        "created_at":  now_iso() if idx is None else scripts[idx].get("created_at", now_iso()),
        "updated_at":  now_iso(),
    }
    if idx is not None:
        scripts[idx] = entry
        action = "updated"
    else:
        scripts.append(entry)
        action = "created"
    _save_scripts(scripts)
    return ORJSONResponse(content={"ok": True, "action": action, "name": req.name})


@router.get("/tile_scripts/{name}",
            summary="Get a saved user tile generator script by name")
async def get_tile_script(name: str) -> ORJSONResponse:
    # Check builtins first (name == key)
    if name in _DEFAULTS:
        return ORJSONResponse(content={
            "ok":     True,
            "name":   name,
            "label":  _DEFAULT_LABELS.get(name, name),
            "source": "builtin",
            "code":   _DEFAULTS[name],
            "params": {},
        })
    scripts = _load_scripts()
    entry = next((s for s in scripts if s.get("name") == name), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"tile_script_not_found:{name}")
    return ORJSONResponse(content={"ok": True, **entry})


@router.delete("/tile_scripts/{name}",
               summary="Delete a saved user tile generator script")
async def delete_tile_script(name: str) -> ORJSONResponse:
    if name in _DEFAULTS:
        raise HTTPException(status_code=403, detail="cannot_delete_builtin_script")
    scripts = _load_scripts()
    before = len(scripts)
    scripts = [s for s in scripts if s.get("name") != name]
    if len(scripts) == before:
        raise HTTPException(status_code=404, detail=f"tile_script_not_found:{name}")
    _save_scripts(scripts)
    return ORJSONResponse(content={"ok": True, "deleted": name})


# ---------------------------------------------------------------------------
# Endpoint — run (server-side execution via Node.js)
# ---------------------------------------------------------------------------

@router.post("/tile_scripts/run",
             summary="Execute a tile generator script server-side and return tiles/links/entities")
async def run_tile_script(req: TileScriptRunRequest) -> ORJSONResponse:
    # Resolve code
    code: str | None = None
    script_name = req.name

    if script_name:
        if script_name in _DEFAULTS:
            code = _DEFAULTS[script_name]
        else:
            saved = _load_scripts()
            entry = next((s for s in saved if s.get("name") == script_name), None)
            if entry is None:
                raise HTTPException(status_code=404, detail=f"tile_script_not_found:{script_name}")
            code = entry.get("code", "")
    elif req.code:
        code = req.code
    else:
        raise HTTPException(status_code=422, detail="provide name or code")

    result, error = _run_js(code, seed=req.seed, cols=req.cols, rows=req.rows, layer=req.layer)

    if error:
        return ORJSONResponse(status_code=422, content={
            "ok": False,
            "error": error,
            "name": script_name,
        })

    tiles    = result.get("tiles", [])
    links    = result.get("links", [])
    entities = result.get("entities", [])
    return ORJSONResponse(content={
        "ok":          True,
        "name":        script_name,
        "seed":        req.seed,
        "cols":        req.cols,
        "rows":        req.rows,
        "layer":       req.layer,
        "tile_count":  len(tiles),
        "link_count":  len(links),
        "entity_count":len(entities),
        "tiles":       tiles,
        "links":       links,
        "entities":    entities,
    })


# ---------------------------------------------------------------------------
# JS execution helper
# ---------------------------------------------------------------------------

_NODE_WRAPPER = textwrap.dedent("""\
    "use strict";
    const seed  = parseInt(process.argv[2], 10);
    const cols  = parseInt(process.argv[3], 10);
    const rows  = parseInt(process.argv[4], 10);
    const layer = process.argv[5] || "base";
    const fn = new Function("seed", "cols", "rows", "layer", USER_CODE);
    let result;
    try {
        result = fn(seed, cols, rows, layer);
    } catch (e) {
        process.stderr.write(String(e));
        process.exit(1);
    }
    if (!result || typeof result !== "object") {
        process.stderr.write("script_must_return_object");
        process.exit(1);
    }
    process.stdout.write(JSON.stringify({
        tiles:    Array.isArray(result.tiles)    ? result.tiles    : [],
        links:    Array.isArray(result.links)    ? result.links    : [],
        entities: Array.isArray(result.entities) ? result.entities : [],
    }));
""")


def _run_js(
    code: str,
    *,
    seed: int,
    cols: int,
    rows: int,
    layer: str,
    timeout: int = 10,
) -> tuple[dict[str, Any], str]:
    """
    Execute the JS code body in a Node.js subprocess.
    Returns (result_dict, error_string). On success error_string is "".
    Falls back gracefully if node is not on PATH.
    """
    # Embed user code as a JSON string to avoid injection via backtick/quote tricks
    wrapped = _NODE_WRAPPER.replace("USER_CODE", json.dumps(code))

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", encoding="utf-8", delete=False
        ) as f:
            f.write(wrapped)
            tmp_path = f.name

        proc = subprocess.run(
            ["node", tmp_path, str(seed), str(cols), str(rows), layer],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        Path(tmp_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            err = (proc.stderr or "").strip() or f"exit_code:{proc.returncode}"
            return {}, err

        return json.loads(proc.stdout), ""

    except FileNotFoundError:
        return {}, "node_not_found:install_nodejs_to_enable_server_side_execution"
    except subprocess.TimeoutExpired:
        return {}, f"execution_timeout:{timeout}s"
    except Exception as exc:
        return {}, f"execution_error:{exc}"
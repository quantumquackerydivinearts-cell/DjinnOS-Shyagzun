"""
Render Lab dungeon export pipeline.

Converts tile generator output → Ambroflow DungeonLayout format,
validates the result against the dungeon contract, and writes
export-ready JSON to files/exports/{game_slug}/dungeons/.

───────────────────────────────────────────────────────────────
Color-token → TileKind rules
───────────────────────────────────────────────────────────────
Traversability is determined ONLY by opacity_token.
Color tokens carry semantic/visual meaning but never override
opacity for the purposes of dungeon conversion.

  opacity "Ung" (fully blocked)     → wall
  opacity "Wu"  (semi-transparent)  → wall  (soft barrier)
  opacity "Na"  (normal)            → floor
  opacity "Ta"  (presence marker)   → floor (tile is present)

Layer "detail" tiles are skipped entirely — they are overlays
with no gameplay meaning.

Color tokens and their visual character (for reference only):
  Ru  — fire / cinnabar (warm amber)
  Ot  — edge / ochre
  El  — corridor / luminous grey
  Ki  — ground / green
  Fu  — water / blue
  Ka  — flame / deep orange
  AE  — archway / threshold (portal candidate → door kind)
  Ga  — stone / grey
  Wu  — semi-opaque barrier (opacity role, also a color)
  Ung — fully opaque (opacity role, also a color)
  Na  — normal opacity
  Ta  — presence token

Color exceptions:
  AE  → door kind (a passage through a threshold)

───────────────────────────────────────────────────────────────
TileKind.SPECIAL — what it means
───────────────────────────────────────────────────────────────
In Ambroflow, TileKind.SPECIAL is a POSITION RESERVATION.
It marks a coordinate as "something registered here" but
carries NO inherent identity — the actual object (forge,
altar, throne, lore stone, etc.) is named in the DungeonDef
`special_tiles` list and bound to positions by the generator.

When converting BSP output back to tile display tokens:
  - "special" voxels render as Ot/Na (neutral ochre marker)
  - The actual special_kind is passed in entity metadata

When converting authored tile output TO dungeon layout:
  - No tile color token implies "special" — only explicit
    entity placement of kind "prop" creates SpecialTile entries
  - The prop's `meta.special_kind` or `tag` names the object

───────────────────────────────────────────────────────────────
Entity kind → dungeon role
───────────────────────────────────────────────────────────────
  "player"   → ENTRY voxel (player spawn)
  "exit"     → EXIT voxel
  "npc" / "enemy" / combat kinds → EncounterSlot
  "prop"     → SpecialTile  (kind from meta.special_kind or tag)
  "pattern"  → ignored (visual only — not a game entity)
  all others → EncounterSlot with encounter_type "observation"

───────────────────────────────────────────────────────────────
TileKind → display tokens (Ambroflow BSP → Atelier renderer)
───────────────────────────────────────────────────────────────
Only NEUTRAL display tokens are used here.
No mechanic-specific tokens are inferred or assigned.
  wall    → (Ga, Ung)   stone, fully opaque
  floor   → (Ki, Na)    walkable ground
  door    → (El, Na)    luminous threshold
  entry   → (El, Na)    same display as door; meta.tile_kind = "entry"
  exit    → (El, Na)    same display as door; meta.tile_kind = "exit"
  special → (Ot, Na)    neutral ochre marker; meta.special_kind carries identity
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...db import get_db
from ._db import require_project
from ._utils import ROOT, now_iso
from .tile_scripts import _DEFAULTS, _load_scripts, _run_js

router = APIRouter()

_EXPORT_ROOT = ROOT / "apps" / "atelier-api" / "atelier_api" / "files" / "exports"


# ---------------------------------------------------------------------------
# Tile → TileKind conversion
# ---------------------------------------------------------------------------

_BLOCKING_OPACITY = {"Ung", "Wu"}
_DOOR_COLORS      = {"AE"}      # archway token → door kind


def _color_to_tile_kind(color_token: str, opacity_token: str, layer: str) -> str | None:
    """
    Convert a single tile's tokens to a TileKind string, or None to skip.
    Traversability is driven entirely by opacity, not color.
    """
    if layer == "detail":
        return None
    if opacity_token in _BLOCKING_OPACITY:
        return "wall"
    if color_token in _DOOR_COLORS:
        return "door"
    return "floor"


def tiles_to_voxels(tiles: list[dict[str, Any]]) -> dict[tuple[int, int], str]:
    """Convert tile list to voxel dict keyed by (x, y)."""
    voxels: dict[tuple[int, int], str] = {}
    for t in tiles:
        x       = int(t.get("x", 0))
        y       = int(t.get("y", 0))
        color   = str(t.get("color_token",   "Ki"))
        opacity = str(t.get("opacity_token", "Na"))
        layer   = str(t.get("layer",         "base"))
        kind    = _color_to_tile_kind(color, opacity, layer)
        if kind is not None:
            voxels[(x, y)] = kind
    return voxels


_ENCOUNTER_KINDS = {
    "npc", "enemy", "guard", "merchant", "patron",
    "shade", "spirit", "demon", "djinn",
}


def entities_to_dungeon_features(
    entities: list[dict[str, Any]],
    voxels: dict[tuple[int, int], str],
) -> tuple[list[dict], list[dict], tuple[int, int] | None]:
    """
    Classify entities into encounters, specials, and entry position.
    Stamps entry/exit/special voxels in-place.
    Returns (encounters, specials, entry_pos).
    """
    encounters: list[dict] = []
    specials:   list[dict] = []
    entry_pos:  tuple[int, int] | None = None

    for ent in entities:
        kind = str(ent.get("kind", "prop")).lower()
        x    = int(ent.get("x", 0))
        y    = int(ent.get("y", 0))
        meta = ent.get("meta", {}) or {}

        if kind == "player":
            entry_pos      = (x, y)
            voxels[(x, y)] = "entry"

        elif kind == "exit":
            voxels[(x, y)] = "exit"

        elif kind in _ENCOUNTER_KINDS:
            enc_type   = str(meta.get("encounter_type", "combat"))
            difficulty = float(meta.get("difficulty", 0.4))
            encounters.append({
                "x": x, "y": y,
                "encounter_type": enc_type,
                "difficulty":     max(0.0, min(1.0, difficulty)),
            })

        elif kind == "pattern":
            continue   # visual only — no game entity

        else:
            # prop and unrecognised kinds → SpecialTile
            # Name is explicit from meta; we never infer mechanic identity from color
            special_kind = str(
                meta.get("special_kind") or
                meta.get("subject") or
                ent.get("tag") or
                kind
            )
            specials.append({"x": x, "y": y, "kind": special_kind})
            if voxels.get((x, y)) not in ("entry", "exit", "door"):
                voxels[(x, y)] = "special"

    return encounters, specials, entry_pos


# ---------------------------------------------------------------------------
# Topology analysis
# ---------------------------------------------------------------------------

def detect_rooms(voxels: dict[tuple[int, int], str]) -> list[dict]:
    """
    BFS flood-fill over traversable tiles to find contiguous regions.
    Regions with < 4 tiles are corridors and excluded from the room list.
    """
    traversable = {"floor", "door", "special", "entry", "exit"}
    visited: set[tuple[int, int]] = set()
    rooms:   list[dict] = []
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for start, kind in voxels.items():
        if kind not in traversable or start in visited:
            continue
        region: list[tuple[int, int]] = []
        q: deque[tuple[int, int]] = deque([start])
        visited.add(start)
        while q:
            cx, cy = q.popleft()
            region.append((cx, cy))
            for dx, dy in dirs:
                nb = (cx + dx, cy + dy)
                if nb not in visited and voxels.get(nb) in traversable:
                    visited.add(nb)
                    q.append(nb)
        if len(region) < 4:
            continue
        xs = [p[0] for p in region]
        ys = [p[1] for p in region]
        rooms.append({
            "x":  min(xs), "y": min(ys),
            "w":  max(xs) - min(xs) + 1,
            "h":  max(ys) - min(ys) + 1,
            "cx": (min(xs) + max(xs)) // 2,
            "cy": (min(ys) + max(ys)) // 2,
            "tile_count": len(region),
        })
    return rooms


def is_connected(voxels: dict[tuple[int, int], str]) -> tuple[bool, int, int]:
    """
    Returns (fully_connected, reachable_count, total_traversable_count).
    A disconnected layout will still export but carries a warning.
    """
    traversable = {"floor", "door", "special", "entry", "exit"}
    pool = {pos for pos, k in voxels.items() if k in traversable}
    if not pool:
        return False, 0, 0
    start    = next(iter(pool))
    visited: set[tuple[int, int]] = {start}
    q:  deque[tuple[int, int]] = deque([start])
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q:
        cx, cy = q.popleft()
        for dx, dy in dirs:
            nb = (cx + dx, cy + dy)
            if nb in pool and nb not in visited:
                visited.add(nb)
                q.append(nb)
    return len(visited) == len(pool), len(visited), len(pool)


# ---------------------------------------------------------------------------
# Full conversion + validation
# ---------------------------------------------------------------------------

def tile_output_to_dungeon_layout(
    tiles:    list[dict[str, Any]],
    links:    list[dict[str, Any]],
    entities: list[dict[str, Any]],
    dungeon_id: str,
    floor:  int,
    seed:   int,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []

    voxels                       = tiles_to_voxels(tiles)
    encounters, specials, entry_pos = entities_to_dungeon_features(entities, voxels)
    rooms                        = detect_rooms(voxels)
    connected, reachable, total  = is_connected(voxels)

    if entry_pos is None:
        if rooms:
            ep = (rooms[0]["cx"], rooms[0]["cy"])
            voxels[ep] = "entry"
            warnings.append("no_player_entity:entry_auto_placed_at_first_room_centre")
        else:
            warnings.append("no_entry_and_no_rooms_detected")

    if not any(k == "exit" for k in voxels.values()):
        if len(rooms) > 1:
            last = rooms[-1]
            voxels[(last["cx"], last["cy"])] = "exit"
            warnings.append("no_exit_entity:exit_auto_placed_at_last_room_centre")
        else:
            warnings.append("no_exit:only_one_room_or_no_rooms")

    if not connected:
        warnings.append(
            f"disconnected_graph:{reachable}/{total}_traversable_tiles_reachable"
            " — use navigable_town or corridor_grid for fully connected layouts"
        )

    voxel_list = [
        {"x": x, "y": y, "kind": kind}
        for (x, y), kind in sorted(voxels.items())
    ]

    return {
        "schema":    "ambroflow.dungeon.fixed_layout.v1",
        "dungeon_id": dungeon_id,
        "floor":     floor,
        "seed":      seed,
        "authored":  True,
        "voxels":    voxel_list,
        "rooms":     rooms,
        "encounters": encounters,
        "specials":   specials,
        "links":      links,
        "stats": {
            "tile_count":      len(tiles),
            "voxel_count":     len(voxels),
            "traversable":     total,
            "reachable":       reachable,
            "connected":       connected,
            "room_count":      len(rooms),
            "encounter_count": len(encounters),
            "special_count":   len(specials),
        },
        "authored_at": now_iso(),
    }, warnings


def dungeon_contract_errors(layout: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    kinds = {v["kind"] for v in layout.get("voxels", [])}
    if "entry" not in kinds:
        errors.append("contract:no_entry_tile")
    if "exit" not in kinds:
        errors.append("contract:no_exit_tile")
    if not layout.get("rooms"):
        errors.append("contract:no_rooms_detected")
    if layout["stats"]["traversable"] < 4:
        errors.append("contract:too_few_traversable_tiles")
    return errors


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DungeonExportRequest(BaseModel):
    game_slug:   str = Field(..., description="e.g. '7_KLGS'")
    dungeon_id:  str = Field(..., description="DungeonDef id or new authored id")
    floor:       int = Field(default=0, ge=0)
    script_name: str | None = None
    script_code: str | None = None
    seed:  int = Field(default=42)
    cols:  int = Field(default=64, ge=4, le=256)
    rows:  int = Field(default=64, ge=4, le=256)
    layer: str = Field(default="base")
    # Pre-supplied output (skips execution)
    tiles:    list[dict[str, Any]] | None = None
    links:    list[dict[str, Any]] | None = None
    entities: list[dict[str, Any]] | None = None


class DungeonValidateRequest(BaseModel):
    tiles:    list[dict[str, Any]]
    links:    list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    dungeon_id: str = Field(default="preview")
    floor: int = Field(default=0)
    seed:  int = Field(default=0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/dungeon_export",
             summary="Run a tile script, convert to Ambroflow layout, validate, and save")
async def export_dungeon(req: DungeonExportRequest) -> ORJSONResponse:
    if req.tiles is not None:
        tiles    = req.tiles
        links    = req.links or []
        entities = req.entities or []
        run_info: dict[str, Any] = {"source": "pre_supplied"}
    else:
        code: str | None = None
        if req.script_name:
            code = _DEFAULTS.get(req.script_name)
            if code is None:
                saved = _load_scripts()
                entry = next((s for s in saved if s.get("name") == req.script_name), None)
                if not entry:
                    raise HTTPException(404, f"tile_script_not_found:{req.script_name}")
                code = entry.get("code", "")
        elif req.script_code:
            code = req.script_code
        else:
            raise HTTPException(422, "provide script_name, script_code, or pre-supplied tiles/links/entities")

        result, err = _run_js(code, seed=req.seed, cols=req.cols, rows=req.rows, layer=req.layer)
        if err:
            return ORJSONResponse(status_code=422, content={
                "ok": False, "stage": "script_execution", "error": err,
            })
        tiles    = result.get("tiles", [])
        links    = result.get("links", [])
        entities = result.get("entities", [])
        run_info = {"source": req.script_name or "inline",
                    "seed": req.seed, "cols": req.cols, "rows": req.rows}

    layout, warnings = tile_output_to_dungeon_layout(
        tiles, links, entities,
        dungeon_id=req.dungeon_id, floor=req.floor, seed=req.seed,
    )
    layout["_run"] = run_info
    errors = dungeon_contract_errors(layout)

    saved_path: str | None = None
    if not errors:
        export_dir = _EXPORT_ROOT / req.game_slug / "dungeons"
        export_dir.mkdir(parents=True, exist_ok=True)
        out_path = export_dir / f"{req.dungeon_id}_floor{req.floor}.json"
        out_path.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding="utf-8")
        saved_path = str(out_path)

    return ORJSONResponse(content={
        "ok":         len(errors) == 0,
        "dungeon_id": req.dungeon_id,
        "floor":      req.floor,
        "game_slug":  req.game_slug,
        "saved_path": saved_path,
        "stats":      layout["stats"],
        "errors":     errors,
        "warnings":   warnings,
    })


@router.post("/dungeon_validate",
             summary="Validate tile generator output against the Ambroflow dungeon contract")
async def validate_dungeon(req: DungeonValidateRequest) -> ORJSONResponse:
    layout, warnings = tile_output_to_dungeon_layout(
        req.tiles, req.links, req.entities,
        dungeon_id=req.dungeon_id, floor=req.floor, seed=req.seed,
    )
    errors = dungeon_contract_errors(layout)
    return ORJSONResponse(content={
        "ok": len(errors) == 0,
        "stats": layout["stats"],
        "errors": errors,
        "warnings": warnings,
    })


@router.get("/dungeon_export/{game_slug}",
            summary="List saved dungeon floor exports for a game")
async def list_dungeon_exports(game_slug: str) -> ORJSONResponse:
    export_dir = _EXPORT_ROOT / game_slug / "dungeons"
    if not export_dir.exists():
        return ORJSONResponse(content={"ok": True, "game_slug": game_slug, "floors": [], "count": 0})
    floors = []
    for p in sorted(export_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            floors.append({
                "filename":    p.name,
                "dungeon_id":  data.get("dungeon_id"),
                "floor":       data.get("floor"),
                "authored_at": data.get("authored_at"),
                "stats":       data.get("stats", {}),
            })
        except Exception:
            floors.append({"filename": p.name, "error": "parse_failed"})
    return ORJSONResponse(content={
        "ok": True, "game_slug": game_slug, "floors": floors, "count": len(floors),
    })


@router.get("/dungeon_export/{game_slug}/{dungeon_id}/floor/{floor}",
            summary="Retrieve a saved dungeon floor export")
async def get_dungeon_export(game_slug: str, dungeon_id: str, floor: int) -> ORJSONResponse:
    path = _EXPORT_ROOT / game_slug / "dungeons" / f"{dungeon_id}_floor{floor}.json"
    if not path.exists():
        raise HTTPException(404, f"dungeon_export_not_found:{dungeon_id}/floor{floor}")
    return ORJSONResponse(content={"ok": True, **json.loads(path.read_text(encoding="utf-8"))})


@router.get("/dungeon_preview",
            summary="Preview a registered DungeonDef's BSP layout as tile generator output")
async def preview_dungeon(dungeon_id: str, seed: int = 42, floor: int = 0) -> ORJSONResponse:
    """
    Calls Ambroflow's BSP generator and converts the result to tile generator
    format so the Atelier renderer can display any registered dungeon floor.

    Pass dungeon_id=__list__ to enumerate all registered dungeon definitions.
    """
    try:
        import sys as _sys
        _ambroflow = str(ROOT.parent / "AmbroflowEngine")
        if _ambroflow not in _sys.path:
            _sys.path.insert(0, _ambroflow)
        from ambroflow.dungeon.generator import generate
        from ambroflow.dungeon.registry  import get_dungeon, DUNGEON_BY_ID
    except ImportError as exc:
        return ORJSONResponse(status_code=503, content={
            "ok":    False,
            "error": f"ambroflow_not_importable:{exc}",
            "hint":  "AmbroflowEngine must be at c:/AmbroflowEngine",
        })

    if dungeon_id == "__list__":
        return ORJSONResponse(content={
            "ok": True,
            "dungeons": [
                {"id": d.id, "name": d.name, "realm": d.realm, "floor_count": d.floor_count}
                for d in DUNGEON_BY_ID.values()
            ],
        })

    try:
        ddef = get_dungeon(dungeon_id)
    except KeyError:
        raise HTTPException(404, f"dungeon_not_found:{dungeon_id}")

    layout = generate(
        dungeon_id=dungeon_id, seed=seed, floor=floor,
        encounter_density=ddef.encounter_density,
        special_tiles=list(ddef.special_tiles),
    )

    # Neutral display tokens only — no mechanic inference from tile kind.
    # entry and exit render identically to door (luminous threshold);
    # distinction is carried in meta.tile_kind.
    # special renders as Ot/Na (ochre marker); identity is in meta.special_kind.
    _kind_tokens: dict[str, tuple[str, str]] = {
        "wall":    ("Ga", "Ung"),
        "floor":   ("Ki", "Na"),
        "door":    ("El", "Na"),
        "entry":   ("El", "Na"),
        "exit":    ("El", "Na"),
        "special": ("Ot", "Na"),
    }

    tiles: list[dict[str, Any]] = []
    for (x, y), tk in layout.voxels.items():
        kind_str = tk.value if hasattr(tk, "value") else str(tk)
        color, opacity = _kind_tokens.get(kind_str, ("Ki", "Na"))
        tiles.append({
            "x": x, "y": y,
            "layer": "base",
            "color_token":   color,
            "opacity_token": opacity,
            "presence_token": "Ta",
            "meta": {"tile_kind": kind_str},
        })

    entities: list[dict[str, Any]] = []
    for enc in layout.encounters:
        entities.append({
            "id": f"enc_{enc.x}_{enc.y}", "kind": "npc",
            "x": enc.x, "y": enc.y, "z": 1,
            "meta": {"encounter_type": enc.encounter_type, "difficulty": enc.difficulty},
        })
    for sp in layout.specials:
        entities.append({
            "id": f"sp_{sp.x}_{sp.y}", "kind": "prop",
            "x": sp.x, "y": sp.y, "z": 1,
            "meta": {"special_kind": sp.kind},
        })

    return ORJSONResponse(content={
        "ok":           True,
        "dungeon_id":   dungeon_id,
        "dungeon_name": ddef.name,
        "seed":         seed,
        "floor":        floor,
        "floor_count":  ddef.floor_count,
        "tiles":        tiles,
        "links":        [],
        "entities":     entities,
        "rooms": [
            {"x": r.x, "y": r.y, "w": r.w, "h": r.h, "cx": r.cx, "cy": r.cy}
            for r in layout.rooms
        ],
        "tile_count":   len(tiles),
        "entity_count": len(entities),
    })


# ---------------------------------------------------------------------------
# Export bundle
# ---------------------------------------------------------------------------
# Schema: ambroflow.dungeon.export_bundle.v1
#
# Combines the ambroflow.dungeon.fixed_layout.v1 gameplay document with
# relative paths to the compiled voxel pack and stream manifests produced
# by the Render Lab pipeline.
#
# Layout paths are relative to the `gameplay/` directory so the bundle is
# portable — the presentation layer resolves them against its asset root.
#
# Prerequisite states:
#   - dungeon_export must have run for (game_slug, dungeon_id, floor)
#   - project pipeline must have reached at least the compile stage
#
# Ambroflow loads this via DungeonRuntime.from_export_bundle():
#   runtime = DungeonRuntime.from_export_bundle(bundle_doc, dungeon_def, orrery, player)
#   render_paths = runtime.resolve_render_manifest(asset_root)
#   # → {"compiled_pack": "/abs/path/to/pack.v2.json", ...}
# ---------------------------------------------------------------------------

_GAMEPLAY_ROOT = ROOT / "gameplay"


class BundleExportRequest(BaseModel):
    game_slug:  str = Field(..., description="e.g. '7_KLGS'")
    dungeon_id: str = Field(..., description="Must match an existing dungeon floor export")
    floor:      int = Field(default=0, ge=0)


@router.post(
    "/projects/{project_id}/export_bundle",
    summary="Assemble an Ambroflow export bundle from project render artifacts + dungeon layout",
)
async def export_bundle(
    project_id: str,
    req: BundleExportRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    """
    Produces an ``ambroflow.dungeon.export_bundle.v1`` document by merging:

    1. The ``ambroflow.dungeon.fixed_layout.v1`` gameplay doc previously written
       by ``POST /dungeon_export`` (TileKind grid, rooms, encounters, specials).
    2. Relative paths to the compiled voxel pack, stream manifest, and prefetch
       manifest produced by the Render Lab pipeline for this project.

    The bundle is written alongside the layout file:
      ``files/exports/{game_slug}/dungeons/{dungeon_id}_floor{N}.bundle.json``

    Load in Ambroflow:
    .. code-block:: python

        bundle = json.loads(Path("...floor0.bundle.json").read_text())
        runtime = DungeonRuntime.from_export_bundle(
            bundle, dungeon_def, orrery, player
        )
        paths = runtime.resolve_render_manifest(asset_root="gameplay/")
        # paths["compiled_pack"] → absolute path to pack.v2.json
    """
    project = require_project(db, project_id)

    # ── Require at minimum the compile stage ────────────────────────────────
    compiled_pack_path   = project["artifacts"].get("compiled_pack_path")
    stream_manifest_path = project["artifacts"].get("stream_manifest_path")
    prefetch_manifest_path = project["artifacts"].get("prefetch_manifest_path")

    if not compiled_pack_path:
        raise HTTPException(
            status_code=422,
            detail="compile_stage_required:run_POST_pipeline_run?stage=compile_first",
        )

    # ── Load the existing dungeon layout export ──────────────────────────────
    layout_path = (
        _EXPORT_ROOT / req.game_slug / "dungeons"
        / f"{req.dungeon_id}_floor{req.floor}.json"
    )
    if not layout_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"dungeon_layout_not_found:{req.dungeon_id}/floor{req.floor}"
                " — run POST /dungeon_export first"
            ),
        )
    layout_doc = json.loads(layout_path.read_text(encoding="utf-8"))

    # ── Build relative render paths ──────────────────────────────────────────
    def _rel(path_str: str | None) -> str | None:
        if not path_str:
            return None
        p = Path(path_str)
        try:
            return str(p.relative_to(_GAMEPLAY_ROOT)).replace("\\", "/")
        except ValueError:
            return path_str   # already relative or outside gameplay/ — keep as-is

    render_block: dict[str, str | None] = {
        "compiled_pack":     _rel(compiled_pack_path),
        "stream_manifest":   _rel(stream_manifest_path),
        "prefetch_manifest": _rel(prefetch_manifest_path),
    }

    # ── Assemble bundle ──────────────────────────────────────────────────────
    bundle: dict = {
        "schema":             "ambroflow.dungeon.export_bundle.v1",
        "dungeon_id":         req.dungeon_id,
        "floor":              req.floor,
        "game_slug":          req.game_slug,
        "atelier_project_id": project_id,
        "layout":             layout_doc,
        "render":             render_block,
        "exported_at":        now_iso(),
    }

    bundle_path = layout_path.with_suffix("").with_name(
        f"{req.dungeon_id}_floor{req.floor}.bundle.json"
    )
    bundle_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return ORJSONResponse(content={
        "ok":                   True,
        "bundle_path":          str(bundle_path),
        "dungeon_id":           req.dungeon_id,
        "floor":                req.floor,
        "game_slug":            req.game_slug,
        "atelier_project_id":   project_id,
        "render": {
            k: v for k, v in render_block.items()
        },
        "layout_stats":         layout_doc.get("stats", {}),
    })


@router.get(
    "/dungeon_export/{game_slug}/{dungeon_id}/floor/{floor}/bundle",
    summary="Retrieve a saved Ambroflow export bundle",
)
async def get_export_bundle(
    game_slug: str, dungeon_id: str, floor: int
) -> ORJSONResponse:
    path = (
        _EXPORT_ROOT / game_slug / "dungeons"
        / f"{dungeon_id}_floor{floor}.bundle.json"
    )
    if not path.exists():
        raise HTTPException(
            404,
            f"export_bundle_not_found:{dungeon_id}/floor{floor}"
            " — run POST /projects/{id}/export_bundle first",
        )
    return ORJSONResponse(content={"ok": True, **json.loads(path.read_text(encoding="utf-8"))})
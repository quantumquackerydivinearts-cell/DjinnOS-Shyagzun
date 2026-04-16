"""
Voxel Bridge
============
Converts tile generator output (Shygazun color/opacity/presence tokens) into the
hybrid voxel engine's native scene format — accepted verbatim by build_renderer_pack_v2.py.

Tile generator source format:
  {
    tiles:    [{x, y, layer, color_token, opacity_token, presence_token, meta?}],
    links:    [{ax, ay, bx, by}],
    entities: [{id, kind, x, y, z?}]
  }

Voxel scene output format (schema "qqva.voxel_scene.v1"):
  {
    schema:          "qqva.voxel_scene.v1",
    name:            str,
    voxels:          [{id, type, x, y, z, color, material, meta: {layer, lod, walkable, ...}}],
    links:           [{ax, ay, bx, by}],
    render_settings: {renderMode, tile, zScale, ...}
  }

──────────────────────────────────────────────────────────────────────────────────────────
Voxel field semantics
──────────────────────────────────────────────────────────────────────────────────────────
  color    — the original Shygazun color token from the tile (Ru, El, Ki, Ga, …)
  material — AppleBlossom akinen (bytes 98–123): the canonical elemental/compound
             identity of the substance.  This is an ontological statement, not a
             renderer hint.  The renderer maps FROM these to display vocabulary.
  type     — renderer display category used by the 3D engine for mesh grouping
             (floor, cobble, wall, water, lava, grass, structure_wall, …).

Color token → AppleBlossom material (byte) and renderer type
──────────────────────────────────────────────────────────────────────────────────────────
  Ru   fire / cinnabar     Shak   (104) Fire                   type: floor
  Ot   ochre / edge        Mazi   (122) Sediment (Water×Earth)  type: floor
  El   luminous / corr.    Zhuk   (108) Plasma (Fire×Fire)      type: cobble
  Ki   ground / green      Zot    (107) Earth                   type: grass
  Fu   water / blue        Mel    (106) Water                   type: water
  Ka   flame / orange      Kazho  (111) Magma (Fire×Earth)      type: lava
  AE   archway / threshold Zitef  (115) Mercury (Air×Earth)     type: structure_floor
  Ga   stone / grey        Zaot   (123) Salt (Earth×Earth)      type: floor

Opacity token → z-height and walkability:
  Na   normal opacity     z=0  walkable
  Wu   semi-opaque        z=0  walkable   (water surfaces, translucent)
  Ung  fully opaque       z=1  blocking   (solid wall)

Opacity Ung overrides renderer type to "wall"; AE+Ung → "structure_wall".
AppleBlossom material is invariant across opacity — the substance does not
change when it becomes a wall; only its spatial expression does.
──────────────────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Any


# ── Color token maps ──────────────────────────────────────────────────────────
# (renderer_type, appleblosssom_material)
#
# material field carries the AppleBlossom akinen — the canonical elemental
# identity of the substance (ontological, not decorative).
# renderer_type is the 3D engine's display category (used for mesh grouping).
#
# For passable tiles (Na / Wu opacity):
_COLOR_FLOOR: dict[str, tuple[str, str]] = {
    "Ru": ("floor",           "Shak"),    # Fire (byte 104)
    "Ot": ("floor",           "Mazi"),    # Sediment, Water×Earth (byte 122)
    "El": ("cobble",          "Zhuk"),    # Plasma, Fire×Fire (byte 108)
    "Ki": ("grass",           "Zot"),     # Earth (byte 107)
    "Fu": ("water",           "Mel"),     # Water (byte 106)
    "Ka": ("lava",            "Kazho"),   # Magma, Fire×Earth (byte 111)
    "AE": ("structure_floor", "Zitef"),   # Mercury, Air×Earth (byte 115)
    "Ga": ("floor",           "Zaot"),    # Salt, Earth×Earth (byte 123)
}

# For blocking tiles (Ung opacity):
# renderer_type becomes "wall" / "structure_wall"; material is unchanged —
# the substance is the same, only its spatial expression differs.
_COLOR_WALL: dict[str, tuple[str, str]] = {
    "Ru": ("wall",           "Shak"),
    "Ot": ("wall",           "Mazi"),
    "El": ("wall",           "Zhuk"),
    "Ki": ("wall",           "Zot"),
    "Fu": ("wall",           "Mel"),
    "Ka": ("wall",           "Kazho"),
    "AE": ("structure_wall", "Zitef"),
    "Ga": ("wall",           "Zaot"),
}

# Default render settings mirroring defaultVoxelSettings() in rendererCore.js
_DEFAULT_RENDER_SETTINGS: dict[str, Any] = {
    "renderMode":        "2.5d",
    "tile":              18,
    "zScale":            8,
    "renderScale":       1.0,
    "visualStyle":       "default",
    "pixelate":          False,
    "background":        "#0b1426",
    "outline":           False,
    "outlineColor":      "#0f203c",
    "edgeGlow":          False,
    "edgeGlowColor":     "#8fd3ff",
    "edgeGlowStrength":  8.0,
    "labelMode":         "none",
    "labelColor":        "#d9e6ff",
    "lod": {
        "mode":  "auto_zoom",
        "level": 2,
    },
    "lighting": {
        "ambient":    0.55,
        "directional": 0.7,
        "angle":      45,
    },
}


def _tile_to_voxel(
    tile: dict[str, Any],
    tile_index: int,
) -> dict[str, Any]:
    """Convert a single tile generator tile to a voxel record."""
    x = int(tile.get("x", 0))
    y = int(tile.get("y", 0))
    color   = str(tile.get("color_token",   "Ki"))
    opacity = str(tile.get("opacity_token", "Na"))
    layer   = str(tile.get("layer",         "base"))
    meta_in: dict[str, Any] = tile.get("meta") or {}

    # Opacity determines height and walkability
    if opacity == "Ung":
        z        = 1
        walkable = False
        type_, material = _COLOR_WALL.get(color, ("wall", "Zaot"))   # unknown → Zaot (Salt/stone)
    else:
        z        = 0
        walkable = True
        type_, material = _COLOR_FLOOR.get(color, ("floor", "Zot"))  # unknown → Zot (Earth)

    # Tile meta lod field → voxel lod level
    lod = int(meta_in.get("lod", 2))

    # Build voxel id: prefer tile-provided id, else positional
    tile_id = tile.get("id") or f"{x}_{y}_{tile_index}"

    meta_out: dict[str, Any] = {
        "layer":    layer,
        "lod":      lod,
        "walkable": walkable,
    }
    # Carry forward any extra tile meta keys (sdf, curve, subject, etc.)
    for k, v in meta_in.items():
        if k not in ("layer", "lod", "walkable"):
            meta_out[k] = v

    return {
        "id":       str(tile_id),
        "type":     type_,
        "x":        x,
        "y":        y,
        "z":        z,
        "color":    color,
        "material": material,
        "meta":     meta_out,
    }


def _entity_to_voxel(entity: dict[str, Any], entity_index: int) -> dict[str, Any]:
    """
    Convert a tile generator entity to a voxel record.

    Entities are placed at the z given by the entity (default 1, on top of floor).
    Kind is stored in meta; type is "floor" so the compile pass doesn't treat them
    as walls — the entity semantic lives in meta.kind.
    """
    x    = int(entity.get("x", 0))
    y    = int(entity.get("y", 0))
    z    = int(entity.get("z", 1))
    kind = str(entity.get("kind", "entity"))
    eid  = str(entity.get("id") or f"entity_{entity_index}")

    # Map entity kind to (renderer_type, AppleBlossom_material)
    _KIND_TYPE: dict[str, tuple[str, str]] = {
        "player":  ("plinth", "Zot"),    # Earth — the grounded actor
        "npc":     ("bench",  "Mel"),    # Water — the relational/flowing presence
        "prop":    ("pillar", "Zaot"),   # Salt (Earth×Earth) — the placed solid object
        "spire":   ("spire",  "Kazho"),  # Magma (Fire×Earth) — the upward-driven form
        "pattern": ("floor",  "Zhuk"),   # Plasma (Fire×Fire) — pure luminous pattern
    }
    type_, material = _KIND_TYPE.get(kind, ("floor", "Mazi"))  # default: Sediment

    return {
        "id":       eid,
        "type":     type_,
        "x":        x,
        "y":        y,
        "z":        z,
        "color":    "Ot",
        "material": material,
        "meta": {
            "layer":    "entities",
            "lod":      3,
            "walkable": False,
            "kind":     kind,
            "entity":   True,
        },
    }


def tile_output_to_voxel_scene(
    tile_output: dict[str, Any],
    *,
    name: str = "untitled",
    include_entities: bool = True,
    render_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert the full output of a tile generator script into a voxel scene source
    document ready for submission to build_renderer_pack_v2.py.

    Parameters
    ----------
    tile_output:
        The dict returned by a tile generator script:
        { tiles: [...], links: [...], entities: [...] }
    name:
        Human-readable name stamped into the scene document.
    include_entities:
        Whether to materialise entity records as additional voxels (default True).
    render_settings:
        Override render settings merged into the defaults.

    Returns
    -------
    dict matching schema "qqva.voxel_scene.v1" — accepted by build_renderer_pack_v2.py
    as a plain {"voxels": [...]} source document.
    """
    tiles    = tile_output.get("tiles", [])
    links    = tile_output.get("links", [])
    entities = tile_output.get("entities", []) if include_entities else []

    voxels: list[dict[str, Any]] = []

    for idx, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            continue
        voxels.append(_tile_to_voxel(tile, idx))

    for idx, ent in enumerate(entities):
        if not isinstance(ent, dict):
            continue
        voxels.append(_entity_to_voxel(ent, idx))

    settings: dict[str, Any] = dict(_DEFAULT_RENDER_SETTINGS)
    if render_settings:
        settings.update(render_settings)

    # Deduplicate by position+layer: last tile at a given (x, y, z, layer) wins
    deduped: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    for v in voxels:
        key = (v["x"], v["y"], v["z"], v.get("meta", {}).get("layer", "base"))
        deduped[key] = v
    voxels = list(deduped.values())

    return {
        "schema":          "qqva.voxel_scene.v1",
        "name":            name,
        "voxels":          voxels,
        "links":           list(links),
        "render_settings": settings,
        "stats": {
            "tile_count":   len(tiles),
            "entity_count": len(entities),
            "voxel_count":  len(voxels),
        },
    }


def summarise_voxel_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Return a lightweight stats summary for an ingest response."""
    voxels = scene.get("voxels", [])
    by_type: dict[str, int] = {}
    walkable = 0
    for v in voxels:
        t = v.get("type", "floor")
        by_type[t] = by_type.get(t, 0) + 1
        if v.get("meta", {}).get("walkable", False):
            walkable += 1
    return {
        "voxel_count":    len(voxels),
        "walkable_count": walkable,
        "wall_count":     len(voxels) - walkable,
        "by_type":        by_type,
        "link_count":     len(scene.get("links", [])),
    }
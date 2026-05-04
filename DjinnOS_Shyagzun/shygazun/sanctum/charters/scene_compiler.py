"""
scene_compiler.py
=================
Compiles a Kobra .ko scene file to .scene.json.

Usage:
    python scene_compiler.py home_morning.scene.ko
    python scene_compiler.py home_morning.scene.ko --out out.scene.json
    python scene_compiler.py scenes/          # compile all .scene.ko in a dir
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ── Rose numerals ──────────────────────────────────────────────────────────────

ROSE = {
    "Gaoh": 0, "Ao": 1, "Ye": 2, "Ui": 3, "Shu": 4, "Kiel": 5,
    "Yeshu": 6, "Lao": 7, "Shushy": 8, "Uinshu": 9, "Kokiel": 10, "Aonkiel": 11,
}

def _rose_single(toks: list[str], i: int) -> tuple[int, int]:
    if i >= len(toks) or toks[i] not in ROSE:
        return 0, 0
    return ROSE[toks[i]], 1

def _rose_multi(toks: list[str], i: int) -> tuple[int, int]:
    """Parse one or two Rose tokens as a base-12 number."""
    if i >= len(toks) or toks[i] not in ROSE:
        return 0, 0
    v = ROSE[toks[i]]
    if i + 1 < len(toks) and toks[i + 1] in ROSE:
        return v * 12 + ROSE[toks[i + 1]], 2
    return v, 1

def _coords(toks: list[str]) -> tuple[int, int, int, int]:
    """Parse x y z as three single Rose tokens. Returns (x, y, z, consumed)."""
    x, nx = _rose_single(toks, 0)
    y, ny = _rose_single(toks, nx)
    z, nz = _rose_single(toks, nx + ny)
    return x, y, z, nx + ny + nz

# ── Material mappings ──────────────────────────────────────────────────────────

_COLOR_HEX: dict[str, str] = {
    "Ot": "#8B6914", "El": "#696969", "Ru": "#8B0000",
    "Fu": "#87CEEB", "Ka": "#4B0082", "AE": "#9400D3",
    "Ki": "#3A7D44", "Na": "#C0C0C0", "Ha": "#FFFFFF", "Ga": "#1A1A1A",
}

def _material(tset: set[str], ctok: str) -> tuple[str, str]:
    if ctok == "Ot":
        if "Shak" in tset: return "thatch_roof",  "#654321"
        if "FyKo" in tset: return "books",         "#8B4513"
        if "Va"   in tset: return "wood_floor",    "#8B6914"
        return                     "wood_solid",   "#8B4513"
    if ctok == "El":
        if "Va"   in tset: return "metal_tool",    "#B87333"
        return                     "stone_wall",   "#696969"
    if ctok == "Ru":
        if "Di"   in tset: return "wood_door",     "#8B0000"
        if "Shak" in tset: return "furnace",       "#FF4500"
        if "Va"   in tset: return "metal_tool",    "#B87333"
        return                     "furnace",      "#8B0000"
    if ctok == "Fu":               return "glass",        "#87CEEB"
    if ctok == "Ka":               return "cloth",        "#4B0082"
    if ctok == "AE":               return "cloth_cushion","#9400D3"
    return "unknown", _COLOR_HEX.get(ctok, "#888888")

_ACTION_MAP: dict[str, tuple[str, str, str]] = {
    "MavoOpenAlchemyUi":      ("alchemy_bench", "open_alchemy_ui",      "Press E to use alchemy workbench"),
    "MavoExitToLapidusTown":  ("exit",          "exit_to_lapidus_town", "Press E to go outside"),
    "MavoOpenSmeltUi":        ("furnace",        "open_smelt_ui",        "Press E to use furnace"),
    "MavoMeditationTutorial": ("meditate",       "meditation_tutorial",  "Press E to meditate"),
    "MavoLoreBooks":          ("read",           "lore_books",           "Press E to read books"),
    "MavoSaveAndHeal":        ("rest",           "save_and_heal",        "Press E to rest (saves game)"),
    "MavoOpenChest":          ("storage",        "open_chest",           "Press E to open chest"),
}

def _mavo_snake(name: str) -> str:
    s = name.removeprefix("Mavo")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", s).lower()

# ── Ko document parser ─────────────────────────────────────────────────────────

def _extract_specs(body: str) -> list[list[str]]:
    specs, depth, start = [], 0, None
    for i, ch in enumerate(body):
        if ch == "[":
            if depth == 0: start = i + 1
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start is not None:
                inner = body[start:i].strip()
                if inner and not inner.startswith("TaShyMa"):
                    specs.append(inner.split())
    return specs

def _extract_sections(source: str) -> list[tuple[str, str]]:
    """Return list of (lo_name, body) tuples."""
    pattern = re.compile(r"(Lo\w+)\s*:\s*Mavo\w+[^{]*\{", re.MULTILINE)
    out = []
    for m in pattern.finditer(source):
        lo = m.group(1)
        i, depth = m.end(), 1
        while i < len(source) and depth:
            if source[i] == "{": depth += 1
            elif source[i] == "}": depth -= 1
            i += 1
        out.append((lo, source[m.end():i - 1]))
    return out

# ── Section processors ─────────────────────────────────────────────────────────

def _proc_meta(body: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for toks in _extract_specs(body):
        if len(toks) < 2:
            continue
        k = toks[0]
        if k == "MavoSceneId":
            meta["scene_id"] = toks[1]
        elif k == "MavoRealm":
            meta["realm_id"] = _mavo_snake(toks[1])
        elif k == "MavoSceneType":
            meta["scene_type"] = _mavo_snake(toks[1])
        elif k == "MavoSceneName":
            meta["scene_name"] = _mavo_snake(toks[1])
        elif k == "MavoAmbient":
            meta["ambient"] = _mavo_snake(toks[1])
        elif k == "MavoTimeOfDay":
            meta["time_of_day"] = _mavo_snake(toks[1])
        elif k == "MavoSpawn":
            x, y, z, _ = _coords(toks[1:])
            meta["spawn"] = {"x": x, "y": y, "z": z}
        elif k in ("MavoWidth", "MavoDepth", "MavoHeight"):
            v, n1 = _rose_multi(toks, 1)
            key = k.removeprefix("Mavo").lower()
            meta[key] = v
        elif k == "MavoCamera":
            a,  na  = _rose_multi(toks, 1)
            el, nel = _rose_multi(toks, 1 + na)
            zm, _   = _rose_multi(toks, 1 + na + nel)
            meta["camera"] = {"angle": a, "elevation": el, "zoom": zm}
    return meta

def _proc_voxels(body: str) -> list[dict[str, Any]]:
    out = []
    for toks in _extract_specs(body):
        if not toks or toks[0] not in ROSE:
            continue
        x, y, z, nc = _coords(toks)
        prop  = toks[nc:]
        tset  = set(prop)
        ctok  = next((t for t in prop if t in _COLOR_HEX), None)
        if ctok is None:
            continue
        mat, color = _material(tset, ctok)
        vox: dict[str, Any] = {
            "x": x, "y": y, "z": z,
            "color": color,
            "color_token": ctok,
            "presence_token": "Ta" if "Ta" in tset else "",
            "material": mat,
            "walkable": "Va" in tset and "Vo" not in tset,
            "solid":    "Vo" in tset,
        }
        if "Di" in tset:  vox["movable"] = True
        if "Wu" in tset:  vox["opacity_token"] = "Wu"
        out.append(vox)
    return out

def _proc_interactions(body: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    spawn: dict[str, Any] | None = None
    nodes: list[dict[str, Any]] = []
    for toks in _extract_specs(body):
        if not toks or not toks[0].startswith("Mavo"):
            continue
        node_mavo = toks[0]
        rest      = toks[1:]
        x, y, z, nc = _coords(rest)
        acts = rest[nc:]
        act  = next((t for t in acts if t.startswith("Mavo") and t not in ("MavoKael", "MavoSy")), None)

        if node_mavo == "MavoSpawnPoint":
            spawn = {"x": x, "y": y, "z": z}
            continue

        node_id   = _mavo_snake(node_mavo).removesuffix("_intr")
        scene_ref = spawn and f"{x}_{y}_{z}" or node_id
        node: dict[str, Any] = {
            "node_id": node_id,
            "kind":    "interaction",
            "x":       float(x),
            "y":       float(y),
            "metadata": {"z": z},
        }
        if act and act in _ACTION_MAP:
            intr, action, prompt = _ACTION_MAP[act]
            node["metadata"].update({"interaction": intr, "action": action, "prompt": prompt})
        nodes.append(node)
    return spawn, nodes

# ── Public compile function ────────────────────────────────────────────────────

_VOXEL_LOS     = {"LoAo", "LoYe", "LoUi", "LoShu", "LoKiel"}
_META_LO       = "LoGaoh"
_INTERACT_LO   = "LoYeshu"

def compile_scene(source: str, scene_id: str = "") -> dict[str, Any]:
    """Parse a .ko scene source and return a .scene.json-compatible dict."""
    meta: dict[str, Any] = {}
    voxels: list[dict[str, Any]] = []
    spawn: dict[str, Any] | None = None
    nodes: list[dict[str, Any]] = []

    for lo, body in _extract_sections(source):
        if lo == _META_LO:
            meta = _proc_meta(body)
        elif lo in _VOXEL_LOS:
            voxels.extend(_proc_voxels(body))
        elif lo == _INTERACT_LO:
            spawn, nodes = _proc_interactions(body)

    sid   = meta.get("scene_id", scene_id)
    realm = meta.get("realm_id", "lapidus")
    name  = meta.get("scene_name", "").replace("_", " ").title() or sid

    spawn_node: dict[str, Any] = {
        "node_id": "spawn_point",
        "kind":    "spawn",
        "x":       float(spawn["x"]) if spawn else 0.0,
        "y":       float(spawn["y"]) if spawn else 0.0,
        "metadata": {
            "z":            spawn["z"] if spawn else 1,
            "placement_id": f"{sid}:spawn_point",
        },
    }
    for n in nodes:
        n["metadata"].setdefault("placement_id", f"{sid}:{n['node_id']}")

    return {
        "schema":      "atelier.scene.content.v1",
        "scene_id":    sid,
        "realm_id":    realm,
        "name":        name,
        "description": f"Player starting home in {realm.title()}.",
        "nodes":       [spawn_node] + nodes,
        "edges":       [],
        "renderer": {
            "scene": {
                "scene_id":    sid,
                "scene_name":  name,
                "scene_type":  "voxel_interior",
                "realm_id":    realm,
                "dimensions":  {
                    "width":  meta.get("width",  12),
                    "depth":  meta.get("depth",  8),
                    "height": meta.get("height", 6),
                },
                "spawn_point":    spawn or {"x": 6, "y": 6, "z": 1},
                "camera_default": meta.get("camera", {"angle": 45, "elevation": 30, "zoom": 1.0}),
                "voxels":         voxels,
                "ambient_music":  meta.get("ambient", ""),
                "time_of_day":    meta.get("time_of_day", "morning"),
            }
        },
    }

# ── CLI ────────────────────────────────────────────────────────────────────────

def _compile_file(src_path: Path, out_path: Path | None = None) -> Path:
    source   = src_path.read_text(encoding="utf-8")
    scene_id = src_path.name.replace(".scene.ko", "").replace(".ko", "")
    result   = compile_scene(source, scene_id)
    dest     = out_path or src_path.with_suffix("").with_suffix(".scene.json")
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    n = len(result["renderer"]["scene"]["voxels"])
    print(f"  {src_path.name}  ->  {dest.name}  ({n} voxels)")
    return dest

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Compile .ko scene → .scene.json")
    ap.add_argument("input", help=".ko file or directory of .ko files")
    ap.add_argument("--out", help="output path (single file mode only)")
    args = ap.parse_args()

    p = Path(args.input)
    if p.is_dir():
        files = list(p.rglob("*.scene.ko"))
        if not files:
            print(f"No .scene.ko files found in {p}", file=sys.stderr)
            sys.exit(1)
        print(f"Compiling {len(files)} scene(s):")
        for f in files:
            _compile_file(f)
    else:
        out = Path(args.out) if args.out else None
        _compile_file(p, out)

if __name__ == "__main__":
    main()
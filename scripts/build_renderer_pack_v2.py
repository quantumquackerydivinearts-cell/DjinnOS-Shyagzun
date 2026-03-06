from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _pick_voxels(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [v for v in payload if isinstance(v, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("scene_payload"), dict) and isinstance(payload["scene_payload"].get("voxels"), list):
        return [v for v in payload["scene_payload"]["voxels"] if isinstance(v, dict)]
    if isinstance(payload.get("compiled_scene"), dict) and isinstance(payload["compiled_scene"].get("voxels"), list):
        return [v for v in payload["compiled_scene"]["voxels"] if isinstance(v, dict)]
    if isinstance(payload.get("voxels"), list):
        return [v for v in payload["voxels"] if isinstance(v, dict)]
    if isinstance(payload.get("scene"), dict) and isinstance(payload["scene"].get("voxels"), list):
        return [v for v in payload["scene"]["voxels"] if isinstance(v, dict)]
    return []


def _normalize_voxel(row: dict[str, Any]) -> dict[str, Any]:
    meta_obj = row.get("meta")
    meta = dict(meta_obj) if isinstance(meta_obj, dict) else {}
    lod_obj = row.get("lod")
    lod = dict(lod_obj) if isinstance(lod_obj, dict) else None
    lod_variants_obj = row.get("lod_variants")
    if not isinstance(lod_variants_obj, list):
        lod_variants_obj = row.get("lodVariants")
    lod_variants = [v for v in lod_variants_obj if isinstance(v, dict)] if isinstance(lod_variants_obj, list) else []

    out: dict[str, Any] = {
        "x": _safe_int(row.get("x"), 0),
        "y": _safe_int(row.get("y"), 0),
        "z": _safe_int(row.get("z"), 0),
    }
    if isinstance(row.get("type"), str):
        out["type"] = str(row["type"])
    if isinstance(row.get("id"), str):
        out["id"] = str(row["id"])
    if isinstance(row.get("material"), str):
        out["material"] = str(row["material"])
    if isinstance(row.get("color"), str):
        out["color"] = str(row["color"])
    for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
        if isinstance(row.get(key), str):
            out[key] = str(row[key])
    for key in ["frame", "frameTop", "frameLeft", "frameRight"]:
        if isinstance(row.get(key), (str, int, float)):
            out[key] = row[key]
    if isinstance(lod, dict) and len(lod) > 0:
        out["lod"] = lod
    if lod_variants:
        out["lod_variants"] = lod_variants
    if meta:
        out["meta"] = meta
    return out


def _normalize_voxels(voxels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_normalize_voxel(row) for row in voxels]
    normalized.sort(
        key=lambda v: (
            _safe_int(v.get("z"), 0),
            _safe_int(v.get("y"), 0),
            _safe_int(v.get("x"), 0),
            str(v.get("id", "")),
            str(v.get("type", "")),
            str(v.get("material", "")),
        )
    )
    return normalized


def _pick_array(source: dict[str, Any], key: str) -> list[dict[str, Any]]:
    obj = source.get(key)
    if not isinstance(obj, list):
        return []
    return [entry for entry in obj if isinstance(entry, dict)]


def _normalize_materials(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        mat_id = str(row.get("id") or f"material_{idx+1}")
        obj: dict[str, Any] = {"id": mat_id}
        for key in [
            "color",
            "texture",
            "textureTop",
            "textureLeft",
            "textureRight",
            "frame",
            "frameTop",
            "frameLeft",
            "frameRight",
        ]:
            if key in row:
                obj[key] = row[key]
        out.append(obj)
    out.sort(key=lambda r: str(r.get("id", "")))
    return out


def _normalize_atlases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        atlas_id = str(row.get("id") or f"atlas_{idx+1}")
        obj = {
            "id": atlas_id,
            "src": str(row.get("src", "")),
            "tileSize": _safe_int(row.get("tileSize", row.get("tile", 16)), 16),
            "cols": max(1, _safe_int(row.get("cols", row.get("columns", 1)), 1)),
            "rows": max(1, _safe_int(row.get("rows", 1), 1)),
            "padding": max(0, _safe_int(row.get("padding", 0), 0)),
        }
        out.append(obj)
    out.sort(key=lambda r: str(r.get("id", "")))
    return out


def _normalize_layers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        layer_id = str(row.get("id") or f"layer_{idx+1}")
        obj = {"id": layer_id}
        for key in ["order", "visible", "blend", "opacity"]:
            if key in row:
                obj[key] = row[key]
        out.append(obj)
    out.sort(key=lambda r: str(r.get("id", "")))
    return out


def _normalize_settings(raw: Any) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    render_mode = "3d" if str(src.get("renderMode", "2.5d")).lower() == "3d" else "2.5d"
    out: dict[str, Any] = {
        "renderMode": render_mode,
        "tile": _safe_int(src.get("tile", 18), 18),
        "zScale": _safe_float(src.get("zScale", 8), 8.0),
        "renderScale": _safe_float(src.get("renderScale", 1), 1.0),
        "visualStyle": str(src.get("visualStyle", "default")),
        "pixelate": bool(src.get("pixelate", False)),
        "background": str(src.get("background", "#0b1426")),
        "outline": bool(src.get("outline", False)),
        "outlineColor": str(src.get("outlineColor", "#0f203c")),
        "edgeGlow": bool(src.get("edgeGlow", False)),
        "edgeGlowColor": str(src.get("edgeGlowColor", "#8fd3ff")),
        "edgeGlowStrength": _safe_float(src.get("edgeGlowStrength", 8), 8.0),
        "labelMode": str(src.get("labelMode", "none")),
        "labelColor": str(src.get("labelColor", "#d9e6ff")),
    }
    if isinstance(src.get("camera3d"), dict):
        out["camera3d"] = src["camera3d"]
    if isinstance(src.get("lighting"), dict):
        out["lighting"] = src["lighting"]
    if isinstance(src.get("rose"), dict):
        out["rose"] = src["rose"]
    if isinstance(src.get("lod"), dict):
        out["lod"] = src["lod"]
    return out


def _extract_texture_deps(voxels: list[dict[str, Any]], materials: list[dict[str, Any]]) -> dict[str, Any]:
    atlas_tokens: set[str] = set()
    texture_paths: set[str] = set()

    def scan_texture(value: Any) -> None:
        if not isinstance(value, str) or value == "":
            return
        if value.startswith("atlas:"):
            parts = value.split(":")
            if len(parts) >= 2 and parts[1] != "":
                atlas_tokens.add(parts[1])
            return
        texture_paths.add(value)

    for voxel in voxels:
        for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
            scan_texture(voxel.get(key))
    for mat in materials:
        for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
            scan_texture(mat.get(key))

    return {
        "atlas_ids": sorted(atlas_tokens),
        "texture_paths": sorted(texture_paths),
    }


def _merge_sidecar(base: dict[str, Any], *, key: str, path: Path | None) -> None:
    if path is None:
        return
    loaded = _load_json(path)
    if isinstance(loaded, list):
        base[key] = [v for v in loaded if isinstance(v, dict)]
        return
    if isinstance(loaded, dict):
        if isinstance(loaded.get(key), list):
            base[key] = [v for v in loaded[key] if isinstance(v, dict)]
        elif key == "render_settings":
            base[key] = loaded


def _resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def compile_renderer_pack_v2(
    *,
    source_payload: Any,
    workspace_id: str,
    source_label: str,
    name_override: str | None = None,
) -> dict[str, Any]:
    source_obj = source_payload if isinstance(source_payload, dict) else {}
    voxels = _normalize_voxels(_pick_voxels(source_payload))
    materials = _normalize_materials(_pick_array(source_obj, "materials"))
    atlases = _normalize_atlases(_pick_array(source_obj, "atlases"))
    layers = _normalize_layers(_pick_array(source_obj, "layers"))
    settings = _normalize_settings(source_obj.get("render_settings", source_obj.get("settings", {})))
    deps = _extract_texture_deps(voxels, materials)

    scene_hash = _sha256(voxels)
    materials_hash = _sha256(materials)
    atlases_hash = _sha256(atlases)
    layers_hash = _sha256(layers)
    settings_hash = _sha256(settings)
    source_hash = _sha256(source_payload)

    compile_basis = {
        "workspace_id": workspace_id,
        "source_label": source_label,
        "scene_hash": scene_hash,
        "materials_hash": materials_hash,
        "atlases_hash": atlases_hash,
        "layers_hash": layers_hash,
        "settings_hash": settings_hash,
    }
    compile_hash = _sha256(compile_basis)
    pack_id = f"rpackv2_{compile_hash[:16]}"
    pack_name = str(name_override or source_obj.get("name") or pack_id)

    compiled: dict[str, Any] = {
        "schema": "atelier.renderer.pack.v2",
        "pack_id": pack_id,
        "name": pack_name,
        "workspace_id": workspace_id,
        "source": source_label,
        "compile": {
            "compiler_id": "renderer_pack_compiler.v2",
            "compile_hash": compile_hash,
            "source_hash": source_hash,
        },
        "hashes": {
            "scene_sha256": scene_hash,
            "materials_sha256": materials_hash,
            "atlases_sha256": atlases_hash,
            "layers_sha256": layers_hash,
            "settings_sha256": settings_hash,
        },
        "render_settings": settings,
        "compiled_scene": {
            "voxels": voxels,
            "materials": materials,
            "atlases": atlases,
            "layers": layers,
        },
        "manifest": {
            "stats": {
                "voxel_count": len(voxels),
                "material_count": len(materials),
                "atlas_count": len(atlases),
                "layer_count": len(layers),
            },
            "dependencies": deps,
        },
    }
    compiled["hashes"]["pack_sha256"] = _sha256(compiled)
    return compiled


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic renderer pack v2 artifact.")
    parser.add_argument("--input", required=True, help="Path to source renderer JSON (pack.v1, pack.v2, or scene JSON).")
    parser.add_argument("--output", required=True, help="Path for compiled pack.v2 JSON output.")
    parser.add_argument("--workspace-id", default="main", help="Workspace id for compile namespace.")
    parser.add_argument("--source", default="renderer_toolchain", help="Source label to stamp into output.")
    parser.add_argument("--name", default="", help="Optional output pack name override.")
    parser.add_argument("--materials", default="", help="Optional materials JSON path.")
    parser.add_argument("--atlases", default="", help="Optional atlases JSON path.")
    parser.add_argument("--layers", default="", help="Optional layers JSON path.")
    parser.add_argument("--settings", default="", help="Optional render settings JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    source_payload = _load_json(input_path)
    source_obj = source_payload if isinstance(source_payload, dict) else {"voxels": _pick_voxels(source_payload)}
    _merge_sidecar(source_obj, key="materials", path=_resolve_path(args.materials) if args.materials else None)
    _merge_sidecar(source_obj, key="atlases", path=_resolve_path(args.atlases) if args.atlases else None)
    _merge_sidecar(source_obj, key="layers", path=_resolve_path(args.layers) if args.layers else None)
    _merge_sidecar(source_obj, key="render_settings", path=_resolve_path(args.settings) if args.settings else None)

    compiled = compile_renderer_pack_v2(
        source_payload=source_obj,
        workspace_id=str(args.workspace_id or "main"),
        source_label=str(args.source or "renderer_toolchain"),
        name_override=str(args.name) if args.name else None,
    )
    _write_json(output_path, compiled)
    print(f"renderer_pack_v2_written:{output_path}")
    print(f"pack_id:{compiled.get('pack_id', '')}")
    print(f"compile_hash:{compiled.get('compile', {}).get('compile_hash', '')}")
    print(f"pack_sha256:{compiled.get('hashes', {}).get('pack_sha256', '')}")
    print(f"voxel_count:{compiled.get('manifest', {}).get('stats', {}).get('voxel_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

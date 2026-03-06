from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    out: set[str] = set()
    for value in values:
        if isinstance(value, str):
            out.add(value)
    return out


def _id_set(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            row_id = row.get("id")
            if isinstance(row_id, str) and row_id != "":
                out.add(row_id)
    return out


def _count_voxels_by_material(rows: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = ""
        material = row.get("material")
        if isinstance(material, str) and material != "":
            key = material
        else:
            meta = row.get("meta")
            if isinstance(meta, dict):
                mat = meta.get("material")
                if isinstance(mat, str) and mat != "":
                    key = mat
        if key == "":
            key = "__none__"
        out[key] = out.get(key, 0) + 1
    return out


def _delta_map(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    return {k: int(after.get(k, 0) - before.get(k, 0)) for k in keys if int(after.get(k, 0) - before.get(k, 0)) != 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff two renderer pack v2 artifacts.")
    parser.add_argument("--before", required=True, help="Path to baseline pack.v2 JSON.")
    parser.add_argument("--after", required=True, help="Path to candidate pack.v2 JSON.")
    parser.add_argument("--output", default="", help="Optional output JSON report path.")
    args = parser.parse_args()

    before_path = Path(args.before)
    after_path = Path(args.after)
    if not before_path.is_absolute():
        before_path = ROOT / before_path
    if not after_path.is_absolute():
        after_path = ROOT / after_path

    errors: list[str] = []
    if not before_path.exists():
        errors.append(f"missing_before:{before_path}")
    if not after_path.exists():
        errors.append(f"missing_after:{after_path}")
    if errors:
        print("renderer_pack_v2_diff_failed")
        for err in errors:
            print(f"- {err}")
        return 1

    before = _load_json(before_path)
    after = _load_json(after_path)
    if not isinstance(before, dict) or not isinstance(after, dict):
        print("renderer_pack_v2_diff_failed")
        print("- invalid_payload:both must be JSON objects")
        return 1
    if str(before.get("schema", "")) != "atelier.renderer.pack.v2":
        print("renderer_pack_v2_diff_failed")
        print("- before_not_pack_v2")
        return 1
    if str(after.get("schema", "")) != "atelier.renderer.pack.v2":
        print("renderer_pack_v2_diff_failed")
        print("- after_not_pack_v2")
        return 1

    b_scene = before.get("compiled_scene", {})
    a_scene = after.get("compiled_scene", {})
    b_manifest = before.get("manifest", {})
    a_manifest = after.get("manifest", {})
    b_hashes = before.get("hashes", {})
    a_hashes = after.get("hashes", {})

    b_voxels = b_scene.get("voxels", []) if isinstance(b_scene, dict) else []
    a_voxels = a_scene.get("voxels", []) if isinstance(a_scene, dict) else []
    b_materials = b_scene.get("materials", []) if isinstance(b_scene, dict) else []
    a_materials = a_scene.get("materials", []) if isinstance(a_scene, dict) else []
    b_atlases = b_scene.get("atlases", []) if isinstance(b_scene, dict) else []
    a_atlases = a_scene.get("atlases", []) if isinstance(a_scene, dict) else []
    b_layers = b_scene.get("layers", []) if isinstance(b_scene, dict) else []
    a_layers = a_scene.get("layers", []) if isinstance(a_scene, dict) else []

    b_dep = b_manifest.get("dependencies", {}) if isinstance(b_manifest, dict) else {}
    a_dep = a_manifest.get("dependencies", {}) if isinstance(a_manifest, dict) else {}

    b_atlas_dep = _as_set(b_dep.get("atlas_ids"))
    a_atlas_dep = _as_set(a_dep.get("atlas_ids"))
    b_tex_dep = _as_set(b_dep.get("texture_paths"))
    a_tex_dep = _as_set(a_dep.get("texture_paths"))

    b_material_ids = _id_set(b_materials)
    a_material_ids = _id_set(a_materials)
    b_atlas_ids = _id_set(b_atlases)
    a_atlas_ids = _id_set(a_atlases)
    b_layer_ids = _id_set(b_layers)
    a_layer_ids = _id_set(a_layers)

    report: dict[str, Any] = {
        "id": "renderer_pack_v2_diff.v1",
        "before": {
            "path": str(before_path),
            "pack_id": str(before.get("pack_id", "")),
            "compile_hash": str((before.get("compile", {}) or {}).get("compile_hash", "")),
            "pack_sha256": str((b_hashes or {}).get("pack_sha256", "")),
        },
        "after": {
            "path": str(after_path),
            "pack_id": str(after.get("pack_id", "")),
            "compile_hash": str((after.get("compile", {}) or {}).get("compile_hash", "")),
            "pack_sha256": str((a_hashes or {}).get("pack_sha256", "")),
        },
        "hash_changes": {
            "scene_changed": str((b_hashes or {}).get("scene_sha256", "")) != str((a_hashes or {}).get("scene_sha256", "")),
            "materials_changed": str((b_hashes or {}).get("materials_sha256", "")) != str((a_hashes or {}).get("materials_sha256", "")),
            "atlases_changed": str((b_hashes or {}).get("atlases_sha256", "")) != str((a_hashes or {}).get("atlases_sha256", "")),
            "layers_changed": str((b_hashes or {}).get("layers_sha256", "")) != str((a_hashes or {}).get("layers_sha256", "")),
            "settings_changed": str((b_hashes or {}).get("settings_sha256", "")) != str((a_hashes or {}).get("settings_sha256", "")),
            "pack_changed": str((b_hashes or {}).get("pack_sha256", "")) != str((a_hashes or {}).get("pack_sha256", "")),
        },
        "counts": {
            "voxel_delta": int(len(a_voxels) - len(b_voxels)),
            "material_delta": int(len(a_materials) - len(b_materials)),
            "atlas_delta": int(len(a_atlases) - len(b_atlases)),
            "layer_delta": int(len(a_layers) - len(b_layers)),
        },
        "set_changes": {
            "materials_added": sorted(a_material_ids - b_material_ids),
            "materials_removed": sorted(b_material_ids - a_material_ids),
            "atlases_added": sorted(a_atlas_ids - b_atlas_ids),
            "atlases_removed": sorted(b_atlas_ids - a_atlas_ids),
            "layers_added": sorted(a_layer_ids - b_layer_ids),
            "layers_removed": sorted(b_layer_ids - a_layer_ids),
            "dependency_atlas_ids_added": sorted(a_atlas_dep - b_atlas_dep),
            "dependency_atlas_ids_removed": sorted(b_atlas_dep - a_atlas_dep),
            "dependency_texture_paths_added": sorted(a_tex_dep - b_tex_dep),
            "dependency_texture_paths_removed": sorted(b_tex_dep - a_tex_dep),
        },
        "material_usage_delta": _delta_map(
            _count_voxels_by_material(b_voxels),
            _count_voxels_by_material(a_voxels),
        ),
    }

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("renderer_pack_v2_diff_ok")
    print(f"- before_pack:{report['before']['pack_id']}")
    print(f"- after_pack:{report['after']['pack_id']}")
    print(f"- pack_changed:{report['hash_changes']['pack_changed']}")
    print(f"- voxel_delta:{report['counts']['voxel_delta']}")
    if output_path is not None:
        print(f"- report:{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

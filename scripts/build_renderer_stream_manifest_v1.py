from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def _chunk_key(x: int, y: int, size_x: int, size_y: int) -> tuple[int, int]:
    return (math.floor(x / max(1, size_x)), math.floor(y / max(1, size_y)))


def _extract_material(voxel: dict[str, Any]) -> str:
    material = voxel.get("material")
    if isinstance(material, str) and material != "":
        return material
    meta = voxel.get("meta")
    if isinstance(meta, dict):
        v = meta.get("material")
        if isinstance(v, str):
            return v
    return ""


def _scan_texture_value(value: Any, atlas_ids: set[str], texture_paths: set[str]) -> None:
    if not isinstance(value, str) or value == "":
        return
    if value.startswith("atlas:"):
        parts = value.split(":")
        if len(parts) >= 2 and parts[1] != "":
            atlas_ids.add(parts[1])
        return
    texture_paths.add(value)


def _voxel_texture_deps(voxel: dict[str, Any]) -> tuple[set[str], set[str]]:
    atlas_ids: set[str] = set()
    texture_paths: set[str] = set()
    for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
        _scan_texture_value(voxel.get(key), atlas_ids, texture_paths)
    return atlas_ids, texture_paths


def _material_texture_deps(material_row: dict[str, Any]) -> tuple[set[str], set[str]]:
    atlas_ids: set[str] = set()
    texture_paths: set[str] = set()
    for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
        _scan_texture_value(material_row.get(key), atlas_ids, texture_paths)
    return atlas_ids, texture_paths


def _sort_voxels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = list(rows)
    out.sort(
        key=lambda v: (
            _safe_int(v.get("z"), 0),
            _safe_int(v.get("y"), 0),
            _safe_int(v.get("x"), 0),
            str(v.get("id", "")),
            str(v.get("type", "")),
            str(v.get("material", "")),
        )
    )
    return out


def _chunk_bounds(rows: list[dict[str, Any]]) -> dict[str, int]:
    xs = [_safe_int(v.get("x"), 0) for v in rows]
    ys = [_safe_int(v.get("y"), 0) for v in rows]
    zs = [_safe_int(v.get("z"), 0) for v in rows]
    return {
        "min_x": min(xs) if xs else 0,
        "max_x": max(xs) if xs else 0,
        "min_y": min(ys) if ys else 0,
        "max_y": max(ys) if ys else 0,
        "min_z": min(zs) if zs else 0,
        "max_z": max(zs) if zs else 0,
    }


def _resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def _parse_csv_set(text: str) -> set[str]:
    if text.strip() == "":
        return set()
    return {part.strip() for part in text.split(",") if part.strip() != ""}


def _voxel_hot_tokens(
    *,
    voxel: dict[str, Any],
    material_row: dict[str, Any] | None,
    hot_materials: set[str],
    hot_atlas_ids: set[str],
    hot_textures: set[str],
) -> set[str]:
    out: set[str] = set()
    material_id = _extract_material(voxel)
    if material_id in hot_materials:
        out.add(f"m:{material_id}")

    def scan(value: Any) -> None:
        if not isinstance(value, str) or value == "":
            return
        if value.startswith("atlas:"):
            parts = value.split(":")
            if len(parts) >= 2 and parts[1] in hot_atlas_ids:
                out.add(f"a:{parts[1]}")
            return
        if value in hot_textures:
            out.add(f"t:{value}")

    for key in ["texture", "textureTop", "textureLeft", "textureRight"]:
        scan(voxel.get(key))
        if isinstance(material_row, dict):
            scan(material_row.get(key))
    return out


def _extract_lod_bucket(voxel: dict[str, Any]) -> int:
    lod_obj = voxel.get("lod")
    if isinstance(lod_obj, dict):
        if isinstance(lod_obj.get("level"), int):
            return int(lod_obj["level"])
    meta = voxel.get("meta")
    if isinstance(meta, dict):
        v = meta.get("lod")
        if isinstance(v, int):
            return int(v)
        if isinstance(v, dict) and isinstance(v.get("level"), int):
            return int(v["level"])
    return 0


def _chunk_total_counts(assignments: dict[int, tuple[int, int]]) -> dict[tuple[int, int], int]:
    out: dict[tuple[int, int], int] = {}
    for _, key in assignments.items():
        out[key] = out.get(key, 0) + 1
    return out


def _chunk_attr_counts(
    voxels: list[dict[str, Any]],
    assignments: dict[int, tuple[int, int]],
    *,
    mode: str,
) -> dict[tuple[int, int], dict[str, int]]:
    out: dict[tuple[int, int], dict[str, int]] = {}
    for idx, key in assignments.items():
        row = voxels[idx]
        if mode == "material_aware":
            attr = _extract_material(row) or "__none__"
        elif mode == "lod_aware":
            attr = f"lod_{_extract_lod_bucket(row)}"
        else:
            attr = "__fixed__"
        if key not in out:
            out[key] = {}
        out[key][attr] = out[key].get(attr, 0) + 1
    return out


def _point_to_chunk_distance(
    *,
    x: int,
    y: int,
    cx: int,
    cy: int,
    size_x: int,
    size_y: int,
) -> int:
    x0 = cx * size_x
    y0 = cy * size_y
    x1 = x0 + size_x - 1
    y1 = y0 + size_y - 1
    if x < x0:
        dx = x0 - x
    elif x > x1:
        dx = x - x1
    else:
        dx = 0
    if y < y0:
        dy = y0 - y
    elif y > y1:
        dy = y - y1
    else:
        dy = 0
    return max(dx, dy)


def _is_boundary_voxel(
    *,
    x: int,
    y: int,
    cx: int,
    cy: int,
    size_x: int,
    size_y: int,
    band: int,
) -> bool:
    x0 = cx * size_x
    y0 = cy * size_y
    x1 = x0 + size_x - 1
    y1 = y0 + size_y - 1
    edge_dist = min(abs(x - x0), abs(x1 - x), abs(y - y0), abs(y1 - y))
    return edge_dist <= band


def _optimize_assignments(
    *,
    voxels: list[dict[str, Any]],
    assignments: dict[int, tuple[int, int]],
    mode: str,
    size_x: int,
    size_y: int,
    band: int,
    passes: int,
    max_chunk_voxels: int,
    hot_tokens_by_index: dict[int, set[str]],
) -> int:
    if mode == "fixed_grid":
        return 0
    moved_total = 0
    index_order = sorted(
        assignments.keys(),
        key=lambda idx: (
            _safe_int(voxels[idx].get("z"), 0),
            _safe_int(voxels[idx].get("y"), 0),
            _safe_int(voxels[idx].get("x"), 0),
            str(voxels[idx].get("id", "")),
            str(voxels[idx].get("type", "")),
        ),
    )

    for _ in range(max(1, passes)):
        moved_this_pass = 0
        totals = _chunk_total_counts(assignments)
        attr_counts = _chunk_attr_counts(voxels, assignments, mode=mode)
        hot_counts: dict[tuple[int, int], dict[str, int]] = {}
        for idx, key in assignments.items():
            for token in hot_tokens_by_index.get(idx, set()):
                hot_counts.setdefault(key, {})
                hot_counts[key][token] = hot_counts[key].get(token, 0) + 1
        for idx in index_order:
            row = voxels[idx]
            x = _safe_int(row.get("x"), 0)
            y = _safe_int(row.get("y"), 0)
            cur_key = assignments[idx]
            cx, cy = cur_key
            if not _is_boundary_voxel(
                x=x,
                y=y,
                cx=cx,
                cy=cy,
                size_x=size_x,
                size_y=size_y,
                band=band,
            ):
                continue

            if mode == "material_aware":
                attr = _extract_material(row) or "__none__"
            else:
                attr = f"lod_{_extract_lod_bucket(row)}"

            candidates: list[tuple[int, int]] = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    key = (cx + dx, cy + dy)
                    dist = _point_to_chunk_distance(
                        x=x,
                        y=y,
                        cx=key[0],
                        cy=key[1],
                        size_x=size_x,
                        size_y=size_y,
                    )
                    if dist <= band:
                        candidates.append(key)
            if cur_key not in candidates:
                candidates.append(cur_key)

            best_key = cur_key
            best_score = -10_000_000.0
            for key in sorted(set(candidates)):
                key_total = totals.get(key, 0)
                if key != cur_key and key_total >= max_chunk_voxels:
                    continue
                key_attr_count = attr_counts.get(key, {}).get(attr, 0)
                score = float(key_attr_count) * 100.0
                score -= float(key_total) * 0.01
                hot_bonus = 0.0
                for token in hot_tokens_by_index.get(idx, set()):
                    hot_bonus += float(hot_counts.get(key, {}).get(token, 0)) * 20.0
                score += hot_bonus
                if key == cur_key:
                    score += 0.5
                if score > best_score:
                    best_score = score
                    best_key = key

            if best_key == cur_key:
                continue

            # Apply move and maintain counters incrementally.
            assignments[idx] = best_key
            totals[cur_key] = max(0, totals.get(cur_key, 1) - 1)
            totals[best_key] = totals.get(best_key, 0) + 1
            attr_counts.setdefault(cur_key, {})
            attr_counts.setdefault(best_key, {})
            attr_counts[cur_key][attr] = max(0, attr_counts[cur_key].get(attr, 1) - 1)
            attr_counts[best_key][attr] = attr_counts[best_key].get(attr, 0) + 1
            for token in hot_tokens_by_index.get(idx, set()):
                hot_counts.setdefault(cur_key, {})
                hot_counts.setdefault(best_key, {})
                hot_counts[cur_key][token] = max(0, hot_counts[cur_key].get(token, 1) - 1)
                hot_counts[best_key][token] = hot_counts[best_key].get(token, 0) + 1
            moved_this_pass += 1

        moved_total += moved_this_pass
        if moved_this_pass == 0:
            break
    return moved_total


def _build_hot_presence(assignments: dict[int, tuple[int, int]], hot_tokens_by_index: dict[int, set[str]]) -> dict[str, dict[tuple[int, int], int]]:
    out: dict[str, dict[tuple[int, int], int]] = {}
    for idx, key in assignments.items():
        for token in hot_tokens_by_index.get(idx, set()):
            out.setdefault(token, {})
            out[token][key] = out[token].get(key, 0) + 1
    return out


def _hotset_objective(hot_presence: dict[str, dict[tuple[int, int], int]], target_max_chunks: int) -> int:
    score = 0
    for token, chunk_counts in hot_presence.items():
        fanout = len([k for k, v in chunk_counts.items() if v > 0])
        overflow = max(0, fanout - max(1, target_max_chunks))
        score += overflow * overflow
        # Minor penalty for spread even below threshold.
        score += fanout
    return score


def _optimize_hotset_global(
    *,
    voxels: list[dict[str, Any]],
    assignments: dict[int, tuple[int, int]],
    hot_tokens_by_index: dict[int, set[str]],
    size_x: int,
    size_y: int,
    boundary_band: int,
    passes: int,
    max_chunk_voxels: int,
    target_max_chunks: int,
) -> int:
    if len([1 for v in hot_tokens_by_index.values() if v]) == 0:
        return 0
    moved_total = 0
    index_order = sorted(
        assignments.keys(),
        key=lambda idx: (
            _safe_int(voxels[idx].get("z"), 0),
            _safe_int(voxels[idx].get("y"), 0),
            _safe_int(voxels[idx].get("x"), 0),
            str(voxels[idx].get("id", "")),
        ),
    )
    for _ in range(max(1, passes)):
        moved_this_pass = 0
        totals = _chunk_total_counts(assignments)
        hot_presence = _build_hot_presence(assignments, hot_tokens_by_index)
        base_obj = _hotset_objective(hot_presence, target_max_chunks)
        for idx in index_order:
            tokens = hot_tokens_by_index.get(idx, set())
            if not tokens:
                continue
            row = voxels[idx]
            x = _safe_int(row.get("x"), 0)
            y = _safe_int(row.get("y"), 0)
            cur = assignments[idx]
            cx, cy = cur
            if not _is_boundary_voxel(
                x=x, y=y, cx=cx, cy=cy, size_x=size_x, size_y=size_y, band=boundary_band
            ):
                continue
            candidates: list[tuple[int, int]] = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    key = (cx + dx, cy + dy)
                    dist = _point_to_chunk_distance(x=x, y=y, cx=key[0], cy=key[1], size_x=size_x, size_y=size_y)
                    if dist <= boundary_band:
                        candidates.append(key)
            if cur not in candidates:
                candidates.append(cur)

            best = cur
            best_obj = base_obj
            for cand in sorted(set(candidates)):
                if cand != cur and totals.get(cand, 0) >= max_chunk_voxels:
                    continue
                # simulate minimal objective delta over token fanout counts
                trial_presence = {t: dict(m) for t, m in hot_presence.items()}
                for token in tokens:
                    cur_count = trial_presence.get(token, {}).get(cur, 0)
                    if cur_count > 0:
                        trial_presence[token][cur] = cur_count - 1
                        if trial_presence[token][cur] <= 0:
                            del trial_presence[token][cur]
                    trial_presence.setdefault(token, {})
                    trial_presence[token][cand] = trial_presence[token].get(cand, 0) + 1
                trial_obj = _hotset_objective(trial_presence, target_max_chunks)
                if trial_obj < best_obj:
                    best_obj = trial_obj
                    best = cand
            if best == cur:
                continue

            assignments[idx] = best
            totals[cur] = max(0, totals.get(cur, 1) - 1)
            totals[best] = totals.get(best, 0) + 1
            for token in tokens:
                cur_count = hot_presence.get(token, {}).get(cur, 0)
                if cur_count > 0:
                    hot_presence[token][cur] = cur_count - 1
                    if hot_presence[token][cur] <= 0:
                        del hot_presence[token][cur]
                hot_presence.setdefault(token, {})
                hot_presence[token][best] = hot_presence[token].get(best, 0) + 1
            base_obj = best_obj
            moved_this_pass += 1

        moved_total += moved_this_pass
        if moved_this_pass == 0:
            break
    return moved_total


def main() -> int:
    parser = argparse.ArgumentParser(description="Build renderer stream manifest/chunks from pack.v2.")
    parser.add_argument("--input", required=True, help="Path to renderer pack v2 JSON.")
    parser.add_argument("--output", required=True, help="Path to stream manifest output JSON.")
    parser.add_argument("--chunk-size-x", type=int, default=64, help="Chunk width in world units.")
    parser.add_argument("--chunk-size-y", type=int, default=64, help="Chunk height in world units.")
    parser.add_argument("--max-chunk-voxels", type=int, default=8000, help="Budget: max voxels per chunk.")
    parser.add_argument("--max-chunk-bytes", type=int, default=1048576, help="Budget: max chunk payload bytes.")
    parser.add_argument(
        "--partition-mode",
        default="fixed_grid",
        choices=["fixed_grid", "material_aware", "lod_aware"],
        help="Chunk partition strategy.",
    )
    parser.add_argument("--optimize-locality", action="store_true", help="Enable deterministic boundary optimization pass.")
    parser.add_argument("--boundary-band", type=int, default=2, help="Boundary band in world units for reassignment candidates.")
    parser.add_argument("--optimize-passes", type=int, default=2, help="Optimization pass count.")
    parser.add_argument("--optimize-hotset-global", action="store_true", help="Enable global hotset fanout optimization.")
    parser.add_argument("--hotset-global-passes", type=int, default=2, help="Global hotset optimization pass count.")
    parser.add_argument("--hotset-materials", default="", help="Comma-separated material ids to cluster.")
    parser.add_argument("--hotset-atlas-ids", default="", help="Comma-separated atlas ids to cluster.")
    parser.add_argument("--hotset-textures", default="", help="Comma-separated texture paths to cluster.")
    parser.add_argument("--hotset-target-max-chunks", type=int, default=12, help="Target max residency chunk fanout per hotset dependency.")
    parser.add_argument("--emit-chunks", action="store_true", help="Write per-chunk JSON payload files.")
    parser.add_argument("--chunks-dir", default="", help="Optional chunk output directory.")
    args = parser.parse_args()

    input_path = _resolve_path(args.input)
    output_path = _resolve_path(args.output)

    if not input_path.exists():
        print("renderer_stream_manifest_build_failed")
        print(f"- missing_input:{input_path}")
        return 1

    pack = _load_json(input_path)
    if not isinstance(pack, dict) or str(pack.get("schema", "")) != "atelier.renderer.pack.v2":
        print("renderer_stream_manifest_build_failed")
        print("- input_must_be_pack_v2")
        return 1

    scene = pack.get("compiled_scene", {})
    if not isinstance(scene, dict) or not isinstance(scene.get("voxels"), list):
        print("renderer_stream_manifest_build_failed")
        print("- missing_compiled_scene_voxels")
        return 1

    voxels = [v for v in scene.get("voxels", []) if isinstance(v, dict)]
    materials = [m for m in scene.get("materials", []) if isinstance(m, dict)]
    material_map = {
        str(m.get("id")): m for m in materials if isinstance(m.get("id"), str) and str(m.get("id")) != ""
    }

    chunk_size_x = max(1, int(args.chunk_size_x))
    chunk_size_y = max(1, int(args.chunk_size_y))
    max_chunk_voxels = max(1, int(args.max_chunk_voxels))
    max_chunk_bytes = max(1, int(args.max_chunk_bytes))
    hotset_materials = _parse_csv_set(str(args.hotset_materials or ""))
    hotset_atlas_ids = _parse_csv_set(str(args.hotset_atlas_ids or ""))
    hotset_textures = _parse_csv_set(str(args.hotset_textures or ""))
    hotset_target_max_chunks = max(1, int(args.hotset_target_max_chunks))
    hot_tokens_by_index: dict[int, set[str]] = {}
    for idx, voxel in enumerate(voxels):
        material_id = _extract_material(voxel)
        material_row = material_map.get(material_id) if material_id != "" else None
        hot_tokens_by_index[idx] = _voxel_hot_tokens(
            voxel=voxel,
            material_row=material_row,
            hot_materials=hotset_materials,
            hot_atlas_ids=hotset_atlas_ids,
            hot_textures=hotset_textures,
        )

    partition_mode = str(args.partition_mode or "fixed_grid")
    assignments: dict[int, tuple[int, int]] = {}
    for idx, voxel in enumerate(voxels):
        x = _safe_int(voxel.get("x"), 0)
        y = _safe_int(voxel.get("y"), 0)
        assignments[idx] = _chunk_key(x, y, chunk_size_x, chunk_size_y)

    moved_voxels = 0
    moved_voxels_global = 0
    if bool(args.optimize_locality):
        moved_voxels = _optimize_assignments(
            voxels=voxels,
            assignments=assignments,
            mode=partition_mode,
            size_x=chunk_size_x,
            size_y=chunk_size_y,
            band=max(0, int(args.boundary_band)),
            passes=max(1, int(args.optimize_passes)),
            max_chunk_voxels=max_chunk_voxels,
            hot_tokens_by_index=hot_tokens_by_index,
        )
    if bool(args.optimize_hotset_global):
        moved_voxels_global = _optimize_hotset_global(
            voxels=voxels,
            assignments=assignments,
            hot_tokens_by_index=hot_tokens_by_index,
            size_x=chunk_size_x,
            size_y=chunk_size_y,
            boundary_band=max(0, int(args.boundary_band)),
            passes=max(1, int(args.hotset_global_passes)),
            max_chunk_voxels=max_chunk_voxels,
            target_max_chunks=hotset_target_max_chunks,
        )

    buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for idx, key in assignments.items():
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(voxels[idx])

    if args.chunks_dir != "":
        chunks_dir = _resolve_path(args.chunks_dir)
    else:
        chunks_dir = output_path.parent / f"{output_path.stem}_chunks"
    if args.emit_chunks:
        chunks_dir.mkdir(parents=True, exist_ok=True)

    residency_atlas: dict[str, set[str]] = {}
    residency_texture: dict[str, set[str]] = {}
    residency_material: dict[str, set[str]] = {}
    chunk_rows: list[dict[str, Any]] = []
    budget_violations: list[dict[str, Any]] = []

    for cx, cy in sorted(buckets.keys()):
        chunk_voxels = _sort_voxels(buckets[(cx, cy)])
        chunk_id = f"cx{cx}_cy{cy}"
        chunk_materials: set[str] = set()
        chunk_atlas_ids: set[str] = set()
        chunk_texture_paths: set[str] = set()

        for voxel in chunk_voxels:
            material_id = _extract_material(voxel)
            if material_id != "":
                chunk_materials.add(material_id)
                mat_row = material_map.get(material_id)
                if isinstance(mat_row, dict):
                    aid, tpaths = _material_texture_deps(mat_row)
                    chunk_atlas_ids.update(aid)
                    chunk_texture_paths.update(tpaths)
            aid, tpaths = _voxel_texture_deps(voxel)
            chunk_atlas_ids.update(aid)
            chunk_texture_paths.update(tpaths)

        chunk_payload = {
            "schema": "atelier.renderer.stream_chunk.v1",
            "source_pack_id": str(pack.get("pack_id", "")),
            "chunk_id": chunk_id,
            "chunk_coord": {"cx": cx, "cy": cy},
            "bounds": _chunk_bounds(chunk_voxels),
            "voxels": chunk_voxels,
            "dependencies": {
                "atlas_ids": sorted(chunk_atlas_ids),
                "texture_paths": sorted(chunk_texture_paths),
                "material_ids": sorted(chunk_materials),
            },
        }
        chunk_hash = _sha256(chunk_payload)
        chunk_payload["chunk_sha256"] = chunk_hash

        chunk_rel_path = ""
        chunk_bytes = len(json.dumps(chunk_payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
        if args.emit_chunks:
            chunk_file_path = chunks_dir / f"{chunk_id}.json"
            _write_json(chunk_file_path, chunk_payload)
            chunk_rel_path = chunk_file_path.relative_to(ROOT).as_posix() if chunk_file_path.is_relative_to(ROOT) else str(chunk_file_path)
            chunk_bytes = chunk_file_path.stat().st_size

        for atlas_id in chunk_atlas_ids:
            residency_atlas.setdefault(atlas_id, set()).add(chunk_id)
        for tex in chunk_texture_paths:
            residency_texture.setdefault(tex, set()).add(chunk_id)
        for material_id in chunk_materials:
            residency_material.setdefault(material_id, set()).add(chunk_id)

        if len(chunk_voxels) > max_chunk_voxels:
            budget_violations.append(
                {
                    "chunk_id": chunk_id,
                    "kind": "voxel_count",
                    "value": len(chunk_voxels),
                    "limit": max_chunk_voxels,
                }
            )
        if chunk_bytes > max_chunk_bytes:
            budget_violations.append(
                {
                    "chunk_id": chunk_id,
                    "kind": "chunk_bytes",
                    "value": chunk_bytes,
                    "limit": max_chunk_bytes,
                }
            )

        chunk_rows.append(
            {
                "chunk_id": chunk_id,
                "coord": {"cx": cx, "cy": cy},
                "bounds": chunk_payload["bounds"],
                "voxel_count": len(chunk_voxels),
                "chunk_bytes": chunk_bytes,
                "chunk_sha256": chunk_hash,
                "dependencies": chunk_payload["dependencies"],
                "chunk_path": chunk_rel_path,
            }
        )

    manifest: dict[str, Any] = {
        "schema": "atelier.renderer.stream_manifest.v1",
        "source_pack": {
            "pack_id": str(pack.get("pack_id", "")),
            "pack_sha256": str((pack.get("hashes", {}) or {}).get("pack_sha256", "")),
            "compile_hash": str((pack.get("compile", {}) or {}).get("compile_hash", "")),
            "input_path": input_path.relative_to(ROOT).as_posix() if input_path.is_relative_to(ROOT) else str(input_path),
        },
        "grid": {
            "chunk_size_x": chunk_size_x,
            "chunk_size_y": chunk_size_y,
        },
        "partition": {
            "mode": partition_mode,
            "optimize_locality": bool(args.optimize_locality),
            "optimize_hotset_global": bool(args.optimize_hotset_global),
            "boundary_band": max(0, int(args.boundary_band)),
            "optimization_passes": max(1, int(args.optimize_passes)),
            "moved_voxels": moved_voxels,
            "hotset_global_passes": max(1, int(args.hotset_global_passes)),
            "moved_voxels_hotset_global": moved_voxels_global,
        },
        "stats": {
            "chunk_count": len(chunk_rows),
            "voxel_count": len(voxels),
            "max_chunk_voxels": max((row["voxel_count"] for row in chunk_rows), default=0),
            "max_chunk_bytes": max((row["chunk_bytes"] for row in chunk_rows), default=0),
        },
        "budgets": {
            "max_chunk_voxels": max_chunk_voxels,
            "max_chunk_bytes": max_chunk_bytes,
            "violation_count": len(budget_violations),
            "violations": budget_violations,
        },
        "chunks": chunk_rows,
        "residency": {
            "atlas_ids": [
                {"id": key, "chunk_count": len(value), "chunks": sorted(value)}
                for key, value in sorted(residency_atlas.items(), key=lambda item: item[0])
            ],
            "texture_paths": [
                {"path": key, "chunk_count": len(value), "chunks": sorted(value)}
                for key, value in sorted(residency_texture.items(), key=lambda item: item[0])
            ],
            "materials": [
                {"id": key, "chunk_count": len(value), "chunks": sorted(value)}
                for key, value in sorted(residency_material.items(), key=lambda item: item[0])
            ],
        },
        "hotset": {
            "target_max_chunks": hotset_target_max_chunks,
            "materials": sorted(hotset_materials),
            "atlas_ids": sorted(hotset_atlas_ids),
            "texture_paths": sorted(hotset_textures),
            "violation_count": 0,
            "violations": [],
        },
    }
    hot_violations: list[dict[str, Any]] = []
    for mat in sorted(hotset_materials):
        fanout = len(residency_material.get(mat, set()))
        if fanout > hotset_target_max_chunks:
            hot_violations.append({"kind": "material", "id": mat, "chunk_count": fanout, "limit": hotset_target_max_chunks})
    for atlas_id in sorted(hotset_atlas_ids):
        fanout = len(residency_atlas.get(atlas_id, set()))
        if fanout > hotset_target_max_chunks:
            hot_violations.append({"kind": "atlas", "id": atlas_id, "chunk_count": fanout, "limit": hotset_target_max_chunks})
    for tex in sorted(hotset_textures):
        fanout = len(residency_texture.get(tex, set()))
        if fanout > hotset_target_max_chunks:
            hot_violations.append({"kind": "texture", "id": tex, "chunk_count": fanout, "limit": hotset_target_max_chunks})
    manifest["hotset"]["violations"] = hot_violations
    manifest["hotset"]["violation_count"] = len(hot_violations)
    manifest["manifest_sha256"] = _sha256(manifest)
    _write_json(output_path, manifest)

    print(f"renderer_stream_manifest_written:{output_path}")
    print(f"chunk_count:{manifest['stats']['chunk_count']}")
    print(f"voxel_count:{manifest['stats']['voxel_count']}")
    print(f"moved_voxels:{manifest['partition']['moved_voxels']}")
    print(f"moved_voxels_hotset_global:{manifest['partition']['moved_voxels_hotset_global']}")
    print(f"violation_count:{manifest['budgets']['violation_count']}")
    print(f"hotset_violation_count:{manifest['hotset']['violation_count']}")
    print(f"manifest_sha256:{manifest['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

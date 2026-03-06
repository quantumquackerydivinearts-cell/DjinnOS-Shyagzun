from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _chunk_map(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunk_id = row.get("chunk_id")
        if not isinstance(chunk_id, str) or chunk_id == "":
            continue
        out[chunk_id] = row
    return out


def _dep_ids(rows: Any, key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        dep_id = row.get(key)
        count = row.get("chunk_count")
        if isinstance(dep_id, str) and dep_id != "":
            out[dep_id] = int(count) if isinstance(count, int) else 0
    return out


def _delta_map(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    return {k: int(after.get(k, 0) - before.get(k, 0)) for k in keys if int(after.get(k, 0) - before.get(k, 0)) != 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff two renderer stream manifest v1 files.")
    parser.add_argument("--before", required=True, help="Path to baseline manifest.")
    parser.add_argument("--after", required=True, help="Path to candidate manifest.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
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
        print("renderer_stream_manifest_diff_failed")
        for err in errors:
            print(f"- {err}")
        return 1

    before = _load_json(before_path)
    after = _load_json(after_path)
    if not isinstance(before, dict) or not isinstance(after, dict):
        print("renderer_stream_manifest_diff_failed")
        print("- invalid_payload:both must be JSON objects")
        return 1
    if str(before.get("schema", "")) != "atelier.renderer.stream_manifest.v1":
        print("renderer_stream_manifest_diff_failed")
        print("- before_not_stream_manifest_v1")
        return 1
    if str(after.get("schema", "")) != "atelier.renderer.stream_manifest.v1":
        print("renderer_stream_manifest_diff_failed")
        print("- after_not_stream_manifest_v1")
        return 1

    b_chunks = _chunk_map(before.get("chunks"))
    a_chunks = _chunk_map(after.get("chunks"))
    b_chunk_ids = set(b_chunks.keys())
    a_chunk_ids = set(a_chunks.keys())

    persisted = sorted(b_chunk_ids & a_chunk_ids)
    changed_chunks: list[str] = []
    voxel_delta_by_chunk: dict[str, int] = {}
    byte_delta_by_chunk: dict[str, int] = {}
    for chunk_id in persisted:
        b = b_chunks[chunk_id]
        a = a_chunks[chunk_id]
        if str(b.get("chunk_sha256", "")) != str(a.get("chunk_sha256", "")):
            changed_chunks.append(chunk_id)
        v_delta = int(a.get("voxel_count", 0)) - int(b.get("voxel_count", 0))
        if v_delta != 0:
            voxel_delta_by_chunk[chunk_id] = v_delta
        s_delta = int(a.get("chunk_bytes", 0)) - int(b.get("chunk_bytes", 0))
        if s_delta != 0:
            byte_delta_by_chunk[chunk_id] = s_delta

    b_res = before.get("residency", {}) if isinstance(before.get("residency"), dict) else {}
    a_res = after.get("residency", {}) if isinstance(after.get("residency"), dict) else {}

    b_atlas = _dep_ids(b_res.get("atlas_ids"), "id")
    a_atlas = _dep_ids(a_res.get("atlas_ids"), "id")
    b_tex = _dep_ids(b_res.get("texture_paths"), "path")
    a_tex = _dep_ids(a_res.get("texture_paths"), "path")
    b_mat = _dep_ids(b_res.get("materials"), "id")
    a_mat = _dep_ids(a_res.get("materials"), "id")

    report: dict[str, Any] = {
        "id": "renderer_stream_manifest_diff.v1",
        "before": {
            "path": str(before_path),
            "manifest_sha256": str(before.get("manifest_sha256", "")),
            "pack_id": str((before.get("source_pack", {}) or {}).get("pack_id", "")),
        },
        "after": {
            "path": str(after_path),
            "manifest_sha256": str(after.get("manifest_sha256", "")),
            "pack_id": str((after.get("source_pack", {}) or {}).get("pack_id", "")),
        },
        "summary": {
            "manifest_changed": str(before.get("manifest_sha256", "")) != str(after.get("manifest_sha256", "")),
            "chunk_count_delta": len(a_chunk_ids) - len(b_chunk_ids),
            "chunks_added": sorted(a_chunk_ids - b_chunk_ids),
            "chunks_removed": sorted(b_chunk_ids - a_chunk_ids),
            "chunks_changed": changed_chunks,
            "changed_chunk_count": len(changed_chunks),
        },
        "chunk_deltas": {
            "voxel_delta_by_chunk": voxel_delta_by_chunk,
            "chunk_bytes_delta_by_chunk": byte_delta_by_chunk,
        },
        "residency_deltas": {
            "atlas_chunk_count_delta": _delta_map(b_atlas, a_atlas),
            "texture_chunk_count_delta": _delta_map(b_tex, a_tex),
            "material_chunk_count_delta": _delta_map(b_mat, a_mat),
        },
        "budget_deltas": {
            "before_violation_count": int((before.get("budgets", {}) or {}).get("violation_count", 0)),
            "after_violation_count": int((after.get("budgets", {}) or {}).get("violation_count", 0)),
        },
    }

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("renderer_stream_manifest_diff_ok")
    print(f"- manifest_changed:{report['summary']['manifest_changed']}")
    print(f"- chunk_count_delta:{report['summary']['chunk_count_delta']}")
    print(f"- changed_chunk_count:{report['summary']['changed_chunk_count']}")
    if output_path is not None:
        print(f"- report:{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

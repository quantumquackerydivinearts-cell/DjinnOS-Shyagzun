from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUDGET_PATH = ROOT / "gameplay" / "contracts" / "renderer_stream_budgets.v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _to_row_map(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get(key)
        if isinstance(row_id, str) and row_id != "":
            out[row_id] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Check residency fanout budgets against stream manifest.")
    parser.add_argument("--input", required=True, help="Path to stream manifest v1.")
    parser.add_argument("--budget", default="", help="Optional budget contract JSON path.")
    parser.add_argument("--max-atlas-chunks", type=int, default=-1, help="Override max chunk fanout per atlas id.")
    parser.add_argument("--max-texture-chunks", type=int, default=-1, help="Override max chunk fanout per texture path.")
    parser.add_argument("--max-material-chunks", type=int, default=-1, help="Override max chunk fanout per material id.")
    parser.add_argument("--output", default="", help="Optional output report JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not input_path.exists():
        print("renderer_stream_residency_budget_failed")
        print(f"- missing_input:{input_path}")
        return 1

    manifest = _load_json(input_path)
    if not isinstance(manifest, dict) or str(manifest.get("schema", "")) != "atelier.renderer.stream_manifest.v1":
        print("renderer_stream_residency_budget_failed")
        print("- input_not_stream_manifest_v1")
        return 1

    contract: dict[str, Any] = {}
    if args.budget:
        budget_path = Path(args.budget)
        if not budget_path.is_absolute():
            budget_path = ROOT / budget_path
        if budget_path.exists():
            loaded = _load_json(budget_path)
            if isinstance(loaded, dict):
                contract = loaded
    elif DEFAULT_BUDGET_PATH.exists():
        loaded = _load_json(DEFAULT_BUDGET_PATH)
        if isinstance(loaded, dict):
            contract = loaded

    defaults = contract.get("residency", {}) if isinstance(contract.get("residency"), dict) else {}
    max_atlas = int(args.max_atlas_chunks if args.max_atlas_chunks > 0 else defaults.get("max_atlas_chunks", 24))
    max_texture = int(args.max_texture_chunks if args.max_texture_chunks > 0 else defaults.get("max_texture_chunks", 24))
    max_material = int(args.max_material_chunks if args.max_material_chunks > 0 else defaults.get("max_material_chunks", 48))

    residency = manifest.get("residency", {}) if isinstance(manifest.get("residency"), dict) else {}
    atlas_map = _to_row_map(residency.get("atlas_ids"), "id")
    texture_map = _to_row_map(residency.get("texture_paths"), "path")
    material_map = _to_row_map(residency.get("materials"), "id")

    violations: list[dict[str, Any]] = []

    for dep_id, row in sorted(atlas_map.items(), key=lambda item: item[0]):
        count = int(row.get("chunk_count", 0))
        if count > max_atlas:
            violations.append(
                {
                    "kind": "atlas",
                    "id": dep_id,
                    "chunk_count": count,
                    "limit": max_atlas,
                }
            )
    for dep_id, row in sorted(texture_map.items(), key=lambda item: item[0]):
        count = int(row.get("chunk_count", 0))
        if count > max_texture:
            violations.append(
                {
                    "kind": "texture",
                    "id": dep_id,
                    "chunk_count": count,
                    "limit": max_texture,
                }
            )
    for dep_id, row in sorted(material_map.items(), key=lambda item: item[0]):
        count = int(row.get("chunk_count", 0))
        if count > max_material:
            violations.append(
                {
                    "kind": "material",
                    "id": dep_id,
                    "chunk_count": count,
                    "limit": max_material,
                }
            )

    report = {
        "id": "renderer_stream_residency_budget_report.v1",
        "input": str(input_path),
        "source_pack_id": str((manifest.get("source_pack", {}) or {}).get("pack_id", "")),
        "limits": {
            "max_atlas_chunks": max_atlas,
            "max_texture_chunks": max_texture,
            "max_material_chunks": max_material,
        },
        "counts": {
            "atlas_ids": len(atlas_map),
            "texture_paths": len(texture_map),
            "materials": len(material_map),
        },
        "violation_count": len(violations),
        "violations": violations,
        "ok": len(violations) == 0,
    }

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if report["ok"]:
        print("renderer_stream_residency_budget_ok")
    else:
        print("renderer_stream_residency_budget_failed")
    print(f"- violation_count:{report['violation_count']}")
    if output_path is not None:
        print(f"- report:{output_path}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

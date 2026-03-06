from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _chunk_coord_map(chunks: Any) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    if not isinstance(chunks, list):
        return out
    for row in chunks:
        if not isinstance(row, dict):
            continue
        cid = row.get("chunk_id")
        coord = row.get("coord")
        if not isinstance(cid, str) or cid == "":
            continue
        if not isinstance(coord, dict):
            continue
        cx = coord.get("cx")
        cy = coord.get("cy")
        if isinstance(cx, int) and isinstance(cy, int):
            out[cid] = (cx, cy)
    return out


def _ring_neighbors(chunk_map: dict[str, tuple[int, int]], source_id: str, max_ring: int) -> list[dict[str, Any]]:
    if source_id not in chunk_map:
        return []
    sx, sy = chunk_map[source_id]
    rings: list[dict[str, Any]] = []
    for ring in range(1, max_ring + 1):
        ids: list[str] = []
        for cid, (cx, cy) in chunk_map.items():
            if cid == source_id:
                continue
            dist = abs(cx - sx) + abs(cy - sy)
            if dist == ring:
                ids.append(cid)
        ids.sort()
        if ids:
            rings.append({"ring": ring, "chunk_ids": ids})
    return rings


def main() -> int:
    parser = argparse.ArgumentParser(description="Build renderer stream prefetch manifest from stream manifest.")
    parser.add_argument("--input", required=True, help="Path to stream manifest v1.")
    parser.add_argument("--output", required=True, help="Path to prefetch manifest output.")
    parser.add_argument("--max-ring", type=int, default=2, help="Maximum Manhattan ring to include.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    if not input_path.exists():
        print("renderer_prefetch_manifest_build_failed")
        print(f"- missing_input:{input_path}")
        return 1

    source = _load_json(input_path)
    if not isinstance(source, dict) or str(source.get("schema", "")) != "atelier.renderer.stream_manifest.v1":
        print("renderer_prefetch_manifest_build_failed")
        print("- input_not_stream_manifest_v1")
        return 1

    chunk_map = _chunk_coord_map(source.get("chunks"))
    if not chunk_map:
        print("renderer_prefetch_manifest_build_failed")
        print("- no_chunk_coords_found")
        return 1

    max_ring = max(1, int(args.max_ring))
    chunk_prefetch_rows: list[dict[str, Any]] = []
    for cid in sorted(chunk_map.keys()):
        rings = _ring_neighbors(chunk_map, cid, max_ring)
        immediate = rings[0]["chunk_ids"] if len(rings) >= 1 else []
        warm = rings[1]["chunk_ids"] if len(rings) >= 2 else []
        cold: list[str] = []
        if len(rings) > 2:
            for row in rings[2:]:
                cold.extend(row["chunk_ids"])
        chunk_prefetch_rows.append(
            {
                "chunk_id": cid,
                "coord": {"cx": chunk_map[cid][0], "cy": chunk_map[cid][1]},
                "rings": rings,
                "priority": {
                    "immediate": immediate,
                    "warm": warm,
                    "cold": sorted(cold),
                },
            }
        )

    payload = {
        "schema": "atelier.renderer.stream_prefetch_manifest.v1",
        "source_stream_manifest": {
            "path": input_path.relative_to(ROOT).as_posix() if input_path.is_relative_to(ROOT) else str(input_path),
            "manifest_sha256": str(source.get("manifest_sha256", "")),
            "pack_id": str((source.get("source_pack", {}) or {}).get("pack_id", "")),
        },
        "max_ring": max_ring,
        "chunk_count": len(chunk_prefetch_rows),
        "chunks": chunk_prefetch_rows,
    }
    _write_json(output_path, payload)
    print(f"renderer_prefetch_manifest_written:{output_path}")
    print(f"chunk_count:{payload['chunk_count']}")
    print(f"max_ring:{payload['max_ring']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

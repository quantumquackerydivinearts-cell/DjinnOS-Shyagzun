from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = ROOT / "productions" / "kos-labyrnth" / "art"
MANIFEST_PATH = ART_ROOT / "atlas" / "manifest.v1.json"

EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ase", ".aseprite"}


def main() -> int:
    assets = []
    for folder in ["sprites", "tiles", "backgrounds", "atlas"]:
        base = ART_ROOT / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in EXTS:
                continue
            rel = path.relative_to(ROOT).as_posix()
            assets.append({
                "path": rel,
                "bytes": path.stat().st_size,
                "kind": folder,
            })

    payload = {
        "id": "art_pack_manifest.v1",
        "version": "1.0.0",
        "generated_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "assets": assets,
        "asset_count": len(assets),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"art_pack_manifest_written:{MANIFEST_PATH}")
    print(f"asset_count:{len(assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

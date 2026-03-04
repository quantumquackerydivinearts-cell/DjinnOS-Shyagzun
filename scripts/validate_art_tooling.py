from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "gameplay" / "contracts" / "art_tooling_contract.v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    if not CONTRACT_PATH.exists():
        print(f"art_tooling_validation_failed\n- missing:{CONTRACT_PATH}")
        return 1

    contract = _load_json(CONTRACT_PATH)

    for rel in contract.get("required_paths", []):
        path = ROOT / str(rel)
        if not path.exists():
            errors.append(f"missing_path:{rel}")

    manifest_rel = str(contract.get("manifest_path", ""))
    manifest_path = ROOT / manifest_rel
    if not manifest_path.exists():
        errors.append(f"missing_manifest:{manifest_rel}")
    else:
        manifest = _load_json(manifest_path)
        for field in contract.get("required_manifest_fields", []):
            if field not in manifest:
                errors.append(f"manifest_missing_field:{field}")
        assets = manifest.get("assets", [])
        if not isinstance(assets, list):
            errors.append("manifest_assets_not_list")
        else:
            for i, asset in enumerate(assets):
                if not isinstance(asset, dict):
                    errors.append(f"manifest_asset_{i}_not_object")
                    continue
                apath = asset.get("path")
                if isinstance(apath, str):
                    full = ROOT / apath
                    if not full.exists():
                        errors.append(f"manifest_asset_missing_file:{apath}")

    if errors:
        print("art_tooling_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print("art_tooling_validation_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "gameplay" / "contracts" / "editor_parity_contract.v1.json"
MATRIX_PATH = ROOT / "gameplay" / "contracts" / "quest_cert_matrix.v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    if not CONTRACT_PATH.exists():
        print(f"editor_parity_validation_failed\n- missing:{CONTRACT_PATH}")
        return 1

    contract = _load_json(CONTRACT_PATH)

    for rel in contract.get("required_files", []):
        path = ROOT / str(rel)
        if not path.exists():
            errors.append(f"missing_file:{rel}")

    for rel in contract.get("required_runtime_sources", []):
        path = ROOT / str(rel)
        if not path.exists() or not path.is_dir():
            errors.append(f"missing_runtime_source:{rel}")

    if not MATRIX_PATH.exists():
        errors.append(f"missing_matrix:{MATRIX_PATH}")
    else:
        matrix = _load_json(MATRIX_PATH)
        rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
        required_layers = set(str(v) for v in contract.get("required_cert_layers", []))
        for row in rows:
            if not isinstance(row, dict):
                continue
            tier_status = row.get("tier_status", {})
            present = set(str(k) for k in tier_status.keys()) if isinstance(tier_status, dict) else set()
            missing = sorted(required_layers - present)
            if missing:
                errors.append(f"quest:{row.get('quest_id','')}:missing_layers:{','.join(missing)}")

    if errors:
        print("editor_parity_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print("editor_parity_validation_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

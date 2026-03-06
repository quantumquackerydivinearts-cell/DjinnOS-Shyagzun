from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "renderer" / "renderer_pack.v2.schema.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate renderer pack v2 against JSON schema.")
    parser.add_argument("--input", required=True, help="Path to renderer pack v2 JSON.")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = ROOT / in_path

    errors: list[str] = []
    if not SCHEMA_PATH.exists():
        errors.append(f"missing_schema:{SCHEMA_PATH}")
    if not in_path.exists():
        errors.append(f"missing_input:{in_path}")
    if errors:
        print("renderer_pack_v2_validation_failed")
        for err in errors:
            print(f"- {err}")
        return 1

    try:
        from jsonschema import Draft202012Validator
    except Exception:
        print("renderer_pack_v2_validation_failed")
        print("- missing_dependency:jsonschema")
        print("- install_hint:py -m pip install jsonschema")
        return 1

    schema = _load_json(SCHEMA_PATH)
    payload = _load_json(in_path)

    violations = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if violations:
        print("renderer_pack_v2_validation_failed")
        for violation in violations:
            path_txt = ".".join(str(p) for p in violation.path) if list(violation.path) else "$"
            print(f"- schema:{path_txt}:{violation.message}")
        return 1

    # Optional integrity check for pack hash presence/shape only; canonical recomputation
    # stays in compiler path to avoid format divergence risk.
    payload_hashes = payload.get("hashes", {}) if isinstance(payload, dict) else {}
    pack_sha = payload_hashes.get("pack_sha256") if isinstance(payload_hashes, dict) else None
    if not isinstance(pack_sha, str) or len(pack_sha) != 64:
        print("renderer_pack_v2_validation_failed")
        print("- integrity:hashes.pack_sha256 missing_or_invalid")
        return 1

    print("renderer_pack_v2_validation_ok")
    print(f"- input:{in_path}")
    print(f"- schema:{SCHEMA_PATH}")
    print(f"- canonical_size:{len(_canonical_json(payload))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

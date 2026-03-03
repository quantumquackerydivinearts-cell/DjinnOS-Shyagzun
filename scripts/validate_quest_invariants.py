from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTS_PATH = ROOT / "gameplay" / "content_packs" / "canon" / "quests.json"
SCHEMA_PATH = ROOT / "gameplay" / "contracts" / "quest_invariant_contract.v1.json"
INVARIANT_DIR = ROOT / "gameplay" / "quest_cert" / "invariants"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    if not QUESTS_PATH.exists():
        errors.append(f"missing:{QUESTS_PATH}")
    if not SCHEMA_PATH.exists():
        errors.append(f"missing:{SCHEMA_PATH}")
    if not INVARIANT_DIR.exists():
        errors.append(f"missing:{INVARIANT_DIR}")

    if errors:
        print("quest_invariant_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    quests = _load_json(QUESTS_PATH).get("quests", [])
    quest_ids = [str(q.get("quest_id", "")) for q in quests if isinstance(q, dict)]

    schema = _load_json(SCHEMA_PATH)
    req = [str(v) for v in schema.get("required_fields", [])]
    inv_req = [str(v) for v in schema.get("invariant_required_fields", [])]
    allowed_types = set(str(v) for v in schema.get("allowed_types", []))
    allowed_severity = set(str(v) for v in schema.get("allowed_severity", []))

    files = sorted(INVARIANT_DIR.glob("*.json"))
    if not files:
        errors.append("invariants:no_files")

    for path in files:
        payload = _load_json(path)
        for field in req:
            if field not in payload:
                errors.append(f"{path}:missing:{field}")

        scope = payload.get("scope", {})
        scoped_ids = scope.get("quest_ids", []) if isinstance(scope, dict) else []
        if not isinstance(scoped_ids, list) or not scoped_ids:
            errors.append(f"{path}:scope.quest_ids_missing")
        else:
            unknown = sorted(set(str(v) for v in scoped_ids) - set(quest_ids))
            if unknown:
                errors.append(f"{path}:scope_unknown_quest_ids:{','.join(unknown)}")

        invariants = payload.get("invariants", [])
        if not isinstance(invariants, list) or not invariants:
            errors.append(f"{path}:invariants_missing")
            continue

        seen_ids: set[str] = set()
        for idx, inv in enumerate(invariants):
            if not isinstance(inv, dict):
                errors.append(f"{path}:invariant_{idx}_not_object")
                continue
            for field in inv_req:
                if field not in inv:
                    errors.append(f"{path}:invariant_{idx}_missing:{field}")
            inv_id = str(inv.get("invariant_id", ""))
            if inv_id in seen_ids:
                errors.append(f"{path}:duplicate_invariant_id:{inv_id}")
            seen_ids.add(inv_id)

            inv_type = str(inv.get("type", ""))
            if inv_type and inv_type not in allowed_types:
                errors.append(f"{path}:invariant_{idx}_invalid_type:{inv_type}")
            sev = str(inv.get("severity", ""))
            if sev and sev not in allowed_severity:
                errors.append(f"{path}:invariant_{idx}_invalid_severity:{sev}")

    if errors:
        print("quest_invariant_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"quest_invariant_validation_ok:{len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

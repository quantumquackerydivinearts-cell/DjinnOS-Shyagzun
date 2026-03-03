from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTS_PATH = ROOT / "gameplay" / "content_packs" / "canon" / "quests.json"
SCHEMA_PATH = ROOT / "gameplay" / "contracts" / "quest_branch_contract.v1.json"
BRANCH_DIR = ROOT / "gameplay" / "quest_cert" / "branches"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    if not QUESTS_PATH.exists():
        errors.append(f"missing:{QUESTS_PATH}")
    if not SCHEMA_PATH.exists():
        errors.append(f"missing:{SCHEMA_PATH}")
    if not BRANCH_DIR.exists():
        errors.append(f"missing:{BRANCH_DIR}")

    if errors:
        print("quest_branch_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    quests = _load_json(QUESTS_PATH).get("quests", [])
    schema = _load_json(SCHEMA_PATH)
    required_fields = schema.get("required_fields", [])
    branch_required_fields = schema.get("branch_required_fields", [])
    branch_types = set(schema.get("branch_types", []))

    quest_ids = [str(q.get("quest_id", "")) for q in quests if isinstance(q, dict)]

    for qid in quest_ids:
        path = BRANCH_DIR / f"{qid}.json"
        if not path.exists():
            errors.append(f"branch_missing:{qid}")
            continue
        payload = _load_json(path)

        for field in required_fields:
            if field not in payload:
                errors.append(f"{path}:missing:{field}")

        branches = payload.get("branches", [])
        if not isinstance(branches, list) or len(branches) < 3:
            errors.append(f"{path}:branches_must_have_at_least_3")
            continue

        seen_types = set()
        for idx, branch in enumerate(branches):
            if not isinstance(branch, dict):
                errors.append(f"{path}:branch_{idx}_not_object")
                continue
            for field in branch_required_fields:
                if field not in branch:
                    errors.append(f"{path}:branch_{idx}_missing:{field}")
            btype = str(branch.get("branch_type", ""))
            if btype not in branch_types:
                errors.append(f"{path}:branch_{idx}_invalid_branch_type:{btype}")
            seen_types.add(btype)

        for required_type in branch_types:
            if required_type not in seen_types:
                errors.append(f"{path}:missing_branch_type:{required_type}")

    if errors:
        print("quest_branch_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"quest_branch_validation_ok:{len(quest_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

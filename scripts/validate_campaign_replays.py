from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "gameplay" / "contracts" / "quest_campaign_replay_contract.v1.json"
REPLAY_DIR = ROOT / "gameplay" / "quest_cert" / "campaign_replays"
QUESTS_PATH = ROOT / "gameplay" / "content_packs" / "canon" / "quests.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    if not CONTRACT_PATH.exists():
        errors.append(f"missing:{CONTRACT_PATH}")
    if not REPLAY_DIR.exists():
        errors.append(f"missing:{REPLAY_DIR}")
    if not QUESTS_PATH.exists():
        errors.append(f"missing:{QUESTS_PATH}")

    if errors:
        print("campaign_replay_validation_failed")
        for item in errors:
            print(f"- {item}")
        return 1

    contract = _load_json(CONTRACT_PATH)
    req = [str(v) for v in contract.get("required_fields", [])]
    archetypes = set(str(v) for v in contract.get("allowed_archetypes", []))
    req_outcomes = set(str(v) for v in contract.get("required_expected_outcomes", []))

    quest_ids = {
        str(q.get("quest_id", ""))
        for q in _load_json(QUESTS_PATH).get("quests", [])
        if isinstance(q, dict)
    }

    files = sorted(REPLAY_DIR.glob("*.json"))
    if not files:
        errors.append("campaign_replay:no_files")

    seen_replay_ids: set[str] = set()
    for path in files:
        payload = _load_json(path)
        for field in req:
            if field not in payload:
                errors.append(f"{path}:missing:{field}")

        replay_id = str(payload.get("replay_id", ""))
        if replay_id in seen_replay_ids:
            errors.append(f"{path}:duplicate_replay_id:{replay_id}")
        seen_replay_ids.add(replay_id)

        archetype = str(payload.get("archetype", ""))
        if archetype and archetype not in archetypes:
            errors.append(f"{path}:invalid_archetype:{archetype}")

        qpath = payload.get("quest_path", [])
        if not isinstance(qpath, list) or not qpath:
            errors.append(f"{path}:quest_path_missing")
        else:
            unknown = sorted(set(str(v) for v in qpath) - quest_ids)
            if unknown:
                errors.append(f"{path}:unknown_quest_ids:{','.join(unknown)}")

        outcomes = payload.get("expected_outcomes", {})
        if not isinstance(outcomes, dict):
            errors.append(f"{path}:expected_outcomes_not_object")
        else:
            missing = sorted(req_outcomes - set(outcomes.keys()))
            if missing:
                errors.append(f"{path}:missing_expected_outcomes:{','.join(missing)}")

    # strict baseline: exactly the 3 expected archetype files
    if len(files) < 3:
        errors.append("campaign_replay:expected_at_least_3_archetypes")

    if errors:
        print("campaign_replay_validation_failed")
        for item in errors:
            print(f"- {item}")
        return 1

    print(f"campaign_replay_validation_ok:{len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

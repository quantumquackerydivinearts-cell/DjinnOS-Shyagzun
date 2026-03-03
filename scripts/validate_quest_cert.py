from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTS_PATH = ROOT / "gameplay" / "content_packs" / "canon" / "quests.json"
MATRIX_PATH = ROOT / "gameplay" / "contracts" / "quest_cert_matrix.v1.json"
STUBS_DIR = ROOT / "gameplay" / "quest_cert" / "quests"

REQUIRED_TIERS = [
    "tier0_schema_determinism",
    "tier1_branch_contracts",
    "tier2_cross_quest_invariants",
    "tier3_campaign_replay",
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    if not QUESTS_PATH.exists():
        errors.append(f"missing:{QUESTS_PATH}")
        print("quest_cert_validation_failed")
        for e in errors:
            print(f"- {e}")
        return 1

    canon = _load_json(QUESTS_PATH)
    canon_quests = canon.get("quests", []) if isinstance(canon, dict) else []
    canon_ids = [str(q.get("quest_id", "")) for q in canon_quests if isinstance(q, dict)]

    if not MATRIX_PATH.exists():
        errors.append(f"missing:{MATRIX_PATH}")
    else:
        matrix = _load_json(MATRIX_PATH)
        rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
        row_ids = [str(r.get("quest_id", "")) for r in rows if isinstance(r, dict)]

        if len(row_ids) != len(set(row_ids)):
            errors.append("matrix:duplicate_quest_id")

        missing_from_matrix = sorted(set(canon_ids) - set(row_ids))
        extra_in_matrix = sorted(set(row_ids) - set(canon_ids))
        if missing_from_matrix:
            errors.append(f"matrix:missing_quest_ids:{','.join(missing_from_matrix)}")
        if extra_in_matrix:
            errors.append(f"matrix:unknown_quest_ids:{','.join(extra_in_matrix)}")

        for row in rows:
            if not isinstance(row, dict):
                continue
            tier_status = row.get("tier_status")
            if not isinstance(tier_status, dict):
                errors.append(f"matrix:{row.get('quest_id','')}:missing_tier_status")
                continue
            for tier in REQUIRED_TIERS:
                if tier not in tier_status:
                    errors.append(f"matrix:{row.get('quest_id','')}:missing_{tier}")

    if not STUBS_DIR.exists():
        errors.append(f"missing:{STUBS_DIR}")
    else:
        for qid in canon_ids:
            stub_path = STUBS_DIR / f"{qid}.json"
            if not stub_path.exists():
                errors.append(f"stub_missing:{qid}")
                continue
            stub = _load_json(stub_path)
            tiers = stub.get("tiers") if isinstance(stub, dict) else None
            if not isinstance(tiers, dict):
                errors.append(f"stub:{qid}:missing_tiers")
                continue
            for tier in REQUIRED_TIERS:
                if tier not in tiers:
                    errors.append(f"stub:{qid}:missing_{tier}")

            tier0 = tiers.get("tier0_schema_determinism", {}) if isinstance(tiers, dict) else {}
            if not isinstance(tier0, dict):
                errors.append(f"stub:{qid}:tier0_not_object")
                continue
            det_cases = tier0.get("determinism_cases", [])
            if not isinstance(det_cases, list) or not det_cases:
                errors.append(f"stub:{qid}:tier0_missing_determinism_cases")
                continue
            for i, case in enumerate(det_cases):
                if not isinstance(case, dict):
                    errors.append(f"stub:{qid}:tier0_case_{i}_not_object")
                    continue
                case_id = str(case.get("case_id", "")).strip()
                plan_path = str(case.get("plan_path", "")).strip()
                if not case_id:
                    errors.append(f"stub:{qid}:tier0_case_{i}_missing_case_id")
                if not plan_path:
                    errors.append(f"stub:{qid}:tier0_case_{i}_missing_plan_path")
                    continue
                resolved = ROOT / plan_path
                if not resolved.exists():
                    errors.append(f"stub:{qid}:tier0_case_{i}_missing_plan_file:{plan_path}")

    if errors:
        print("quest_cert_validation_failed")
        for item in errors:
            print(f"- {item}")
        return 1

    print(f"quest_cert_validation_ok:{len(canon_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTS_PATH = ROOT / "gameplay" / "content_packs" / "canon" / "quests.json"
STUBS_DIR = ROOT / "gameplay" / "quest_cert" / "quests"
RUNTIME_DIR = ROOT / "gameplay" / "runtime_plans"
CORPUS_PATH = ROOT / "gameplay" / "contracts" / "determinism_corpus.quest_states.v1.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    quests_payload = _load_json(QUESTS_PATH)
    quests = [q for q in quests_payload.get("quests", []) if isinstance(q, dict)]

    determinism_cases: list[dict[str, object]] = []
    if CORPUS_PATH.exists():
        corpus = _load_json(CORPUS_PATH)
        existing_cases = [c for c in corpus.get("cases", []) if isinstance(c, dict)]
        determinism_cases.extend(
            c for c in existing_cases
            if not str(c.get("id", "")).startswith("quest_bootstrap_")
        )
    else:
        corpus = {
            "id": "determinism_corpus.quest_states.v1",
            "version": "1.0.0",
            "updated_at": "2026-03-03",
            "algorithm": "sha256(canonical_json_sorted_keys)",
            "cases": [],
        }

    for index, quest in enumerate(quests, start=1):
        qid = str(quest.get("quest_id", "")).strip()
        name = str(quest.get("name", "")).strip()
        if not qid:
            continue

        bootstrap_filename = f"quest_{qid}_bootstrap.json"
        bootstrap_path = RUNTIME_DIR / bootstrap_filename
        plan_id = f"quest_{qid.lower()}_bootstrap"

        plan_payload = {
            "workspace_id": "main",
            "actor_id": "player",
            "plan_id": plan_id,
            "actions": [
                {
                    "action_id": "seed_byte_table",
                    "kind": "content.pack.load_byte_table",
                    "payload": {},
                },
                {
                    "action_id": "seed_canon_pack",
                    "kind": "content.pack.load_canon",
                    "payload": {"apply_to_db": True},
                },
                {
                    "action_id": "quest_bootstrap",
                    "kind": "module.run",
                    "payload": {
                        "module_id": "module.quest.advance_by_graph",
                        "quest_id": qid,
                        "quest_name": name,
                        "sequence_index": index,
                    },
                },
            ],
        }
        _write_json(bootstrap_path, plan_payload)

        stub_path = STUBS_DIR / f"{qid}.json"
        if stub_path.exists():
            stub_payload = _load_json(stub_path)
            tiers = stub_payload.setdefault("tiers", {})
            tier0 = tiers.setdefault("tier0_schema_determinism", {})
            tier0["status"] = "scaffolded"
            tier0["required_fields"] = ["quest_id", "quest_name"]
            tier0["determinism_cases"] = [
                {
                    "case_id": f"quest_bootstrap_{qid.lower()}",
                    "plan_path": f"gameplay/runtime_plans/{bootstrap_filename}",
                    "required_fields": [
                        "workspace_id",
                        "actor_id",
                        "plan_id",
                        "actions",
                        "actions.0.kind",
                    ],
                }
            ]
            _write_json(stub_path, stub_payload)

        determinism_cases.append(
            {
                "id": f"quest_bootstrap_{qid.lower()}",
                "path": f"gameplay/runtime_plans/{bootstrap_filename}",
                "type": "quest_runtime_plan",
                "required_fields": [
                    "workspace_id",
                    "actor_id",
                    "plan_id",
                    "actions",
                    "actions.0.kind",
                ],
                "expected_hash": "",
            }
        )

    corpus["cases"] = determinism_cases
    _write_json(CORPUS_PATH, corpus)
    print(f"quest_bootstrap_plans_generated:{len(quests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

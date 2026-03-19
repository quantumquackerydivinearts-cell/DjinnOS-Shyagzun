from __future__ import annotations

import json
import sys
import importlib.util
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_PATH = ROOT / "apps" / "atelier-api" / "atelier_api" / "business_schemas.py"


def _load_schemas_module() -> object:
    spec = importlib.util.spec_from_file_location("atelier_business_schemas", SCHEMAS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable_to_load_schemas:{SCHEMAS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_schemas = _load_schemas_module()
QuestGraphUpsertInput = _schemas.QuestGraphUpsertInput
RuntimeConsumeInput = _schemas.RuntimeConsumeInput
QuestGraphUpsertInput.model_rebuild()
RuntimeConsumeInput.model_rebuild()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_quest_templates() -> list[str]:
    errors: list[str] = []
    template_dir = ROOT / "gameplay" / "quest_graph_templates"
    if not template_dir.exists():
        return [f"missing_directory:{template_dir}"]
    for path in sorted(template_dir.glob("*.json")):
        try:
            payload = _load_json(path)
            # Support bundle files: {"graphs": [...]} or a single graph object.
            candidates: list[Any] = payload["graphs"] if isinstance(payload, dict) and "graphs" in payload else [payload]
            for raw in candidates:
                graph = QuestGraphUpsertInput.model_validate(raw)
                label = f"{path}:{graph.quest_id}"
                if graph.metadata.get("runtime_schema_version") != "v1":
                    errors.append(f"{label}:runtime_schema_version_must_be_v1")
                step_ids = [step.step_id for step in graph.steps]
                if len(step_ids) != len(set(step_ids)):
                    errors.append(f"{label}:duplicate_step_id")
                edge_ids: list[str] = []
                for step in graph.steps:
                    for edge in step.edges:
                        edge_ids.append(edge.edge_id)
                        if edge.to_step_id not in step_ids:
                            errors.append(f"{label}:unknown_to_step_id:{edge.to_step_id}")
                if len(edge_ids) != len(set(edge_ids)):
                    errors.append(f"{label}:duplicate_edge_id")
        except Exception as exc:  # pragma: no cover
            errors.append(f"{path}:{exc}")
    return errors


def _validate_runtime_plans() -> list[str]:
    errors: list[str] = []
    plan_dir = ROOT / "gameplay" / "runtime_plans"
    if not plan_dir.exists():
        return [f"missing_directory:{plan_dir}"]
    for path in sorted(plan_dir.glob("*.json")):
        try:
            payload = _load_json(path)
            plan = RuntimeConsumeInput.model_validate(payload)
            action_ids = [action.action_id for action in plan.actions]
            if len(action_ids) != len(set(action_ids)):
                errors.append(f"{path}:duplicate_action_id")
        except Exception as exc:  # pragma: no cover
            errors.append(f"{path}:{exc}")
    return errors


def main() -> int:
    errors = [*_validate_quest_templates(), *_validate_runtime_plans()]
    if errors:
        print("content_pack_validation_failed")
        for item in errors:
            print(f"- {item}")
        return 1
    print("content_pack_validation_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

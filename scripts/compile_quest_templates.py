from __future__ import annotations

import argparse
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
QuestGraphUpsertInput.model_rebuild()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile quest graph templates into a publish bundle.")
    parser.add_argument(
        "--templates-dir",
        default=str(ROOT / "gameplay" / "quest_graph_templates"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "gameplay" / "quest_graph_templates" / "compiled_bundle.json"),
    )
    args = parser.parse_args()

    template_dir = Path(args.templates_dir)
    if not template_dir.exists():
        print(f"templates_dir_not_found:{template_dir}")
        return 1

    bundle: list[dict[str, object]] = []
    for path in sorted(template_dir.glob("*.json")):
        payload = _load_json(path)
        graph = QuestGraphUpsertInput.model_validate(payload)
        graph_payload = graph.model_dump(mode="json")
        graph_payload["__source_file"] = path.name
        bundle.append(graph_payload)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"graphs": bundle}, indent=2) + "\n", encoding="utf-8")
    print(f"compiled_graph_count:{len(bundle)}")
    print(f"bundle_path:{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

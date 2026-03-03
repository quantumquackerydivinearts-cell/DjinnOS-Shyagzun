from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _realm_from_scene_id(scene_id: str) -> str:
    raw = scene_id.strip()
    if raw == "":
        return ""
    if "/" in raw:
        return raw.split("/", 1)[0].strip().lower()
    return "lapidus"


def _load_action_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        actions_obj = payload.get("actions")
        if isinstance(actions_obj, list):
            return [item for item in actions_obj if isinstance(item, dict)]
    raise ValueError("quest_actions must be a JSON array or object with an actions array")


def _load_actions_by_scene(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scene overlay file must be a JSON object")
    actions_by_scene_obj = payload.get("actions_by_scene")
    if not isinstance(actions_by_scene_obj, dict):
        raise ValueError("scene overlay file requires actions_by_scene object")
    out: dict[str, list[dict[str, Any]]] = {}
    for raw_scene, raw_actions in actions_by_scene_obj.items():
        scene_key = str(raw_scene).strip().lower()
        if scene_key == "":
            continue
        if not isinstance(raw_actions, list):
            continue
        out[scene_key] = [item for item in raw_actions if isinstance(item, dict)]
    return out


def _load_scene_cycle(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scene_list: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        scenes_obj = payload.get("scenes")
        if isinstance(scenes_obj, list):
            scene_list = [item for item in scenes_obj if isinstance(item, dict)]
    elif isinstance(payload, list):
        scene_list = [item for item in payload if isinstance(item, dict)]
    if len(scene_list) == 0:
        raise ValueError("scene cycle file must include a non-empty scenes array")
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(scene_list, start=1):
        scene_id = str(raw.get("scene_id", "")).strip()
        if scene_id == "":
            raise ValueError(f"scene_cycle_missing_scene_id_at_index:{index}")
        clock_advance = int(raw.get("clock_advance", 1))
        out.append(
            {
                "scene_id": scene_id,
                "clock_advance": max(0, clock_advance),
                "label": str(raw.get("label", scene_id)),
            }
        )
    return out


def _replace_template_tokens(value: Any, day_index: int, scene_id: str) -> Any:
    scene_slug = scene_id.replace("/", "_").replace(" ", "_")
    if isinstance(value, str):
        return (
            value.replace("{{DAY}}", f"{day_index:02d}")
            .replace("{{SCENE}}", scene_id)
            .replace("{{SCENE_SLUG}}", scene_slug)
        )
    if isinstance(value, list):
        return [_replace_template_tokens(item, day_index, scene_id) for item in value]
    if isinstance(value, dict):
        return {str(key): _replace_template_tokens(item, day_index, scene_id) for key, item in value.items()}
    return value


def _build_generated_day_actions(
    *,
    day_index: int,
    scenes: list[dict[str, Any]],
    scene_overlays: dict[str, list[dict[str, Any]]] | None = None,
    render_sync: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out.append(
        {
            "action_id": f"day_{day_index:02d}_stream_status_open",
            "kind": "world.stream.status",
            "payload": {},
        }
    )
    for scene_index, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id", "")).strip()
        clock_advance = max(0, int(scene.get("clock_advance", 1)))
        scene_slug = scene_id.replace("/", "_").replace(" ", "_")
        realm_id = _realm_from_scene_id(scene_id)
        if render_sync:
            out.append(
                {
                    "action_id": f"day_{day_index:02d}_scene_{scene_index:02d}_{scene_slug}_load",
                    "kind": "render.scene.load",
                    "payload": {
                        "realm_id": realm_id,
                        "scene_id": scene_id,
                        "scene_content": {
                            "realm_id": realm_id,
                            "scene_id": scene_id,
                            "nodes": [],
                        },
                    },
                }
            )
        out.append(
            {
                "action_id": f"day_{day_index:02d}_scene_{scene_index:02d}_{scene_slug}_clock",
                "kind": "render.scene.tick",
                "payload": {
                    "dt": clock_advance,
                    "updates": [],
                    "enqueue_pygame": False,
                    "day_index": day_index,
                    "scene_index": scene_index,
                    "scene_id": scene_id,
                    "clock_advance": clock_advance,
                },
            }
        )
        overlays: list[dict[str, Any]] = []
        if isinstance(scene_overlays, dict):
            overlays.extend(scene_overlays.get("all", []))
            overlays.extend(scene_overlays.get(scene_id.lower(), []))
        for idx, raw_overlay in enumerate(overlays, start=1):
            overlay = cast(dict[str, Any], _replace_template_tokens(raw_overlay, day_index, scene_id))
            payload = overlay.get("payload")
            payload_obj = payload if isinstance(payload, dict) else {}
            payload_obj.setdefault("day_index", day_index)
            payload_obj.setdefault("scene_index", scene_index)
            payload_obj.setdefault("scene_id", scene_id)
            action_id = str(overlay.get("action_id", "")).strip()
            if action_id == "":
                action_id = f"day_{day_index:02d}_scene_{scene_index:02d}_overlay_{idx:02d}"
            out.append(
                {
                    "action_id": action_id,
                    "kind": str(overlay.get("kind", "")).strip(),
                    "payload": payload_obj,
                }
            )
        if render_sync:
            out.append(
                {
                    "action_id": f"day_{day_index:02d}_scene_{scene_index:02d}_{scene_slug}_reconcile",
                    "kind": "render.scene.reconcile",
                    "payload": {
                        "apply": True,
                        "realm_id": realm_id,
                        "scene_id": scene_id,
                        "scene_content": {
                            "realm_id": realm_id,
                            "scene_id": scene_id,
                            "nodes": [],
                        },
                    },
                }
            )

    out.append(
        {
            "action_id": f"day_{day_index:02d}_markets_close",
            "kind": "world.markets.list",
            "payload": {},
        }
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic day runtime actions from scene progression (scene clock advances), while keeping quests hand-coded "
            "in a separate actions file."
        )
    )
    parser.add_argument(
        "--profile",
        choices=["custom", "main"],
        default="custom",
        help="Use 'main' for canonical four-layer composition defaults.",
    )
    parser.add_argument("--workspace-id", default="main")
    parser.add_argument("--actor-id", default="player")
    parser.add_argument("--plan-id", default="day_cycle_plan")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument(
        "--scene-cycle",
        default="gameplay/runtime_plans/day_scene_cycle.default.json",
        help="Path to JSON scene cycle (scenes[] with scene_id and clock_advance).",
    )
    parser.add_argument(
        "--quest-actions",
        default="gameplay/runtime_plans/quest_actions_fate_knocks_day1.json",
        help="Path to hand-coded quest action list (array or {actions:[...]}).",
    )
    parser.add_argument("--quest-position", choices=["before_days", "after_days"], default="after_days")
    parser.add_argument("--include-byte-table", action="store_true")
    parser.add_argument("--include-canon-pack", action="store_true")
    parser.add_argument(
        "--scene-overlays",
        default="",
        help=(
            "Optional JSON file with actions_by_scene to inject time-responsive AI/market logic "
            "without changing the base day template."
        ),
    )
    parser.add_argument(
        "--render-sync",
        action="store_true",
        help="Insert render.scene.load and render.scene.reconcile around each scene tick.",
    )
    parser.add_argument(
        "--output",
        default="gameplay/runtime_plans/day_cycle_plan.generated.json",
    )
    args = parser.parse_args()
    if args.profile == "main":
        args.plan_id = "day_scene_plan_main"
        args.include_byte_table = True
        args.include_canon_pack = True
        if str(args.scene_cycle).strip() == "":
            args.scene_cycle = "gameplay/runtime_plans/day_scene_cycle.default.json"
        if str(args.quest_actions).strip() == "":
            args.quest_actions = "gameplay/runtime_plans/quest_actions_fate_knocks_day1.json"
        if str(args.scene_overlays).strip() == "":
            args.scene_overlays = "gameplay/runtime_plans/day_scene_ai_overlay.market.json"
        args.render_sync = True
        if str(args.output).strip() == "gameplay/runtime_plans/day_cycle_plan.generated.json":
            args.output = "gameplay/runtime_plans/day_scene_plan.main.generated.json"
    actions: list[dict[str, Any]] = []
    scenes = _load_scene_cycle(Path(args.scene_cycle))
    scene_overlays: dict[str, list[dict[str, Any]]] | None = None
    if str(args.scene_overlays).strip() != "":
        scene_overlays = _load_actions_by_scene(Path(args.scene_overlays))
    if args.include_byte_table:
        actions.append({"action_id": "seed_byte_table", "kind": "content.pack.load_byte_table", "payload": {}})
    if args.include_canon_pack:
        actions.append(
            {
                "action_id": "seed_canon_pack",
                "kind": "content.pack.load_canon",
                "payload": {"apply_to_db": True},
            }
        )

    quest_actions_path = Path(args.quest_actions)
    hand_authored_quest_actions = _load_action_list(quest_actions_path)
    if args.quest_position == "before_days":
        actions.extend(hand_authored_quest_actions)

    day_count = max(1, int(args.days))
    for day_index in range(1, day_count + 1):
        actions.extend(
            _build_generated_day_actions(
                day_index=day_index,
                scenes=scenes,
                scene_overlays=scene_overlays,
                render_sync=bool(args.render_sync),
            )
        )

    if args.quest_position == "after_days":
        actions.extend(hand_authored_quest_actions)

    plan = {
        "workspace_id": args.workspace_id,
        "actor_id": args.actor_id,
        "plan_id": args.plan_id,
        "meta": {
            "generator": "build_procgen_day_plan.py",
            "days": day_count,
            "scene_cycle_file": str(args.scene_cycle),
            "scene_count_per_day": len(scenes),
            "quest_actions_file": str(quest_actions_path),
            "quest_position": args.quest_position,
            "quests_hand_coded": True,
            "day_progression_metric": "scene",
            "scene_overlays_file": str(args.scene_overlays or ""),
            "render_sync": bool(args.render_sync),
            "profile": str(args.profile),
        },
        "actions": actions,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

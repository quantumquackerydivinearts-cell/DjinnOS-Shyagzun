from __future__ import annotations

import json
import shlex
from typing import Any, Dict, Optional, Tuple

from shygazun.ide.kobra_runtime import KobraRuntime


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_placeas(parts: list[str]) -> Tuple[str, str]:
    if len(parts) < 3:
        raise ValueError("usage: :placeas <speaker_id> <raw>")
    speaker_id = parts[1]
    raw = " ".join(parts[2:])
    return speaker_id, raw


def repl(runtime: KobraRuntime) -> None:
    current_scene: Optional[str] = None
    current_quest: Optional[str] = None
    current_tags: Dict[str, str] = {}

    while True:
        try:
            line = input("kobra> ").strip()
        except EOFError:
            break

        if not line:
            continue
        if line == ":quit":
            break
        if line.startswith(":place "):
            raw = line[len(":place ") :].strip()
            result = runtime.place_line(
                raw,
                scene_id=current_scene,
                quest_id=current_quest,
                tags=dict(current_tags),
            )
            print(_to_json({"field_id": result.field_id, "placement_event": result.placement_event}))
            continue
        if line.startswith(":placeas "):
            parts = shlex.split(line)
            try:
                speaker_id, raw = _parse_placeas(parts)
            except ValueError as exc:
                print(_to_json({"error": str(exc)}))
                continue
            result = runtime.place_line(
                raw,
                speaker_id=speaker_id,
                scene_id=current_scene,
                quest_id=current_quest,
                tags=dict(current_tags),
            )
            print(_to_json({"field_id": result.field_id, "placement_event": result.placement_event}))
            continue
        if line.startswith(":scene "):
            current_scene = line[len(":scene ") :].strip() or None
            print(_to_json({"scene_id": current_scene}))
            continue
        if line.startswith(":quest "):
            current_quest = line[len(":quest ") :].strip() or None
            print(_to_json({"quest_id": current_quest}))
            continue
        if line.startswith(":tag "):
            token = line[len(":tag ") :].strip()
            if "=" not in token:
                print(_to_json({"error": "usage: :tag <k>=<v>"}))
                continue
            key, value = token.split("=", 1)
            if key == "":
                print(_to_json({"error": "tag key must be non-empty"}))
                continue
            current_tags[key] = value
            print(_to_json({"tags": current_tags}))
            continue
        if line.startswith(":untag "):
            key = line[len(":untag ") :].strip()
            if key in current_tags:
                del current_tags[key]
            print(_to_json({"tags": current_tags}))
            continue
        if line == ":frontiers":
            frontiers = runtime.frontiers()
            print(
                _to_json(
                    [{"id": frontier.id, "status": frontier.status, "event_ids": list(frontier.event_ids)} for frontier in frontiers]
                )
            )
            continue
        if line == ":refusals":
            print(_to_json(runtime.refusals()))
            continue
        if line.startswith(":timeline"):
            parts = shlex.split(line)
            if len(parts) == 1:
                print(_to_json(runtime.timeline()))
                continue
            if len(parts) == 2:
                try:
                    last = int(parts[1])
                except ValueError:
                    print(_to_json({"error": "usage: :timeline [N]"}))
                    continue
                print(_to_json(runtime.timeline(last=last)))
                continue
            print(_to_json({"error": "usage: :timeline [N]"}))
            continue
        if line == ":observe":
            observed = runtime.observe()
            print(
                _to_json(
                    {
                        "field_id": observed.field_id,
                        "clock": {"tick": observed.clock.tick, "causal_epoch": observed.clock.causal_epoch},
                        "refusals": observed.refusals,
                    }
                )
            )
            continue

        print(_to_json({"error": "unknown command"}))

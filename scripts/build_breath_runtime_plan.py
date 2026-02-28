from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Breath-aware runtime plan for realm market reward testing."
    )
    parser.add_argument("--workspace-id", default="main")
    parser.add_argument("--actor-id", default="player")
    parser.add_argument("--player-name", default="Kael")
    parser.add_argument("--canonical-game-number", type=int, default=77)
    parser.add_argument("--quest-completion", type=int, default=12)
    parser.add_argument("--kills", type=int, default=1)
    parser.add_argument("--deaths", type=int, default=5)
    parser.add_argument("--lapidus-royl-loyalty", type=int, default=90)
    parser.add_argument(
        "--output",
        default="gameplay/runtime_plans/breath_realm_rewards_plan.generated.json",
    )
    args = parser.parse_args()

    royl_loyalty = max(0, min(100, int(args.lapidus_royl_loyalty)))
    plan = {
        "workspace_id": args.workspace_id,
        "actor_id": args.actor_id,
        "plan_id": "breath_realm_rewards_plan",
        "actions": [
            {
                "action_id": "eval_breath",
                "kind": "breath.ko.evaluate",
                "payload": {
                    "player_name": args.player_name,
                    "canonical_game_number": int(args.canonical_game_number),
                    "quest_completion": int(args.quest_completion),
                    "kills": max(0, int(args.kills)),
                    "deaths": max(0, int(args.deaths)),
                },
            },
            {
                "action_id": "mercurie_order_reward",
                "kind": "world.market.stock.adjust",
                "payload": {
                    "realm_id": "mercurie",
                    "item_id": "moon_salt",
                    "delta": 10,
                    "use_breath_context": True,
                    "influence_bp": 10000,
                },
            },
            {
                "action_id": "sulphera_chaos_reward",
                "kind": "world.market.stock.adjust",
                "payload": {
                    "realm_id": "sulphera",
                    "item_id": "infernal_ash",
                    "delta": 10,
                    "use_breath_context": True,
                    "influence_bp": 10000,
                },
            },
            {
                "action_id": "lapidus_royl_reward",
                "kind": "world.market.stock.adjust",
                "payload": {
                    "realm_id": "lapidus",
                    "item_id": "iron_ingot",
                    "delta": 10,
                    "use_breath_context": True,
                    "influence_bp": 10000,
                    "royl_loyalty": royl_loyalty,
                },
            },
            {
                "action_id": "markets_after",
                "kind": "world.markets.list",
                "payload": {},
            },
        ],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

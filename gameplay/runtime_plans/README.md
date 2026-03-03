# Runtime Plans (Backend-Only)

These plans are hand-authored JSON files consumed by the backend runtime consumer.
They are not tied to any UI flow.

## Consume a plan

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/full_feature_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/djinn_demon_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/world_stream_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/breath_realm_rewards_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/story_pack_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/fate_knocks_day1_plan.json
```

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/fate_knocks_trace_plan.json
```

Generate a Breath-aware plan from CLI defaults or overrides:

```powershell
py scripts/build_breath_runtime_plan.py --output gameplay/runtime_plans/breath_realm_rewards_plan.generated.json
```

Generate a scene-driven day plan (scene clock advances + hand-coded quests):

```powershell
py scripts/build_procgen_day_plan.py `
  --include-byte-table `
  --include-canon-pack `
  --days 2 `
  --scene-cycle gameplay/runtime_plans/day_scene_cycle.default.json `
  --quest-actions gameplay/runtime_plans/quest_actions_fate_knocks_day1.json `
  --output gameplay/runtime_plans/day_cycle_plan.generated.json
```

Optional: inject time-responsive AI/market overlays by scene (kept out of base day template):

```powershell
py scripts/build_procgen_day_plan.py `
  --include-byte-table `
  --include-canon-pack `
  --days 1 `
  --scene-cycle gameplay/runtime_plans/day_scene_cycle.default.json `
  --quest-actions gameplay/runtime_plans/quest_actions_fate_knocks_day1.json `
  --scene-overlays gameplay/runtime_plans/day_scene_ai_overlay.market.json `
  --output gameplay/runtime_plans/day_cycle_plan.generated.json
```

Canonical composed "main" plan (scene clock + hand-coded quests + overlays + renderer sync):

```powershell
py scripts/build_procgen_day_plan.py --profile main
```

Consume canonical main plan:

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/day_scene_plan.main.generated.json
```

Consume generated plan:

```powershell
py scripts/consume_runtime_plan.py gameplay/runtime_plans/day_cycle_plan.generated.json
```

Run the canonical story pack and print deterministic hash:

```powershell
py scripts/run_story_pack.py
```

## Endpoint

- `POST /v1/game/runtime/consume`

The plan executes actions in listed order and returns per-action success/failure plus a deterministic hash.

Supported runtime kinds include world streaming and realm economy catalog access:
- `world.region.load`
- `world.region.unload`
- `world.stream.status`
- `world.coins.list`
- `world.markets.list`
- `world.market.stock.adjust`
- `world.market.sovereignty.transition`
- `breath.ko.evaluate`
- `sanity.adjust`
- `quest.fate_knocks.bootstrap`
- `quest.fate_knocks.deadline_check`
- `render.scene.load`
- `render.scene.tick`
- `render.scene.reconcile`

Lapidus market metadata is synced to Caravan dominance:
- `dominant_operator: "lord_nexiott"`
- `market_network: "caravan"`

Endgame sovereignty transition can be scripted to overthrow market dominance and
activate redistribution policy via `world.market.sovereignty.transition`.

`world.stream.status` now exposes bounded-stream observability:
- `total_regions`
- `loaded_count`
- `unloaded_count`
- `capacity`

Realm-specific reward policy in `world.market.stock.adjust` with `use_breath_context=true`:
- Mercurie rewards order
- Sulphera rewards chaos
- Lapidus rewards ROYL loyalty (`royl_loyalty` 0..100)

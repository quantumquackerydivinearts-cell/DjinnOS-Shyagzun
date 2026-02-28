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

Generate a Breath-aware plan from CLI defaults or overrides:

```powershell
py scripts/build_breath_runtime_plan.py --output gameplay/runtime_plans/breath_realm_rewards_plan.generated.json
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

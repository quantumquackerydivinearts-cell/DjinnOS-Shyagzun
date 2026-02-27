# ROADMAP (To Beta)

This roadmap targets a usable, serious dev platform. It is ordered by dependency and risk.

## Milestone 1: Runtime World Streaming (Sprint 4, ~3 weeks)
- Region store keyed by `realm_id` + `region_key` with payload hash
- Load/unload endpoints
- `WorldStream.load(realm_id, region_key)` with cache policy
- Success: large worlds stream in chunks without memory growth

## Milestone 2: Runtime Simulation Loop (Sprint 5, ~4 weeks)
- Deterministic tick engine + event queue
- NPC scheduler + state updates
- Kernel integration for placements/events with replay determinism
- Success: 24h simulation run yields stable hashes

## Milestone 3: Dialogue + Quest Runtime (Sprint 6, ~4 weeks)
- Branch resolution based on game state
- Quest state machine with persistence
- Runtime evaluation tests for determinism
- Success: dialogue/quest paths resolve deterministically

## Milestone 4: Asset + Scene Authoring UX (Sprint 7, ~3 weeks)
- Scene graph editor + preview
- Asset pack loader UX + manifest validation
- Pipeline visualization: compile -> store -> emit -> render
- Success: content creators can build scenes without manual JSON edits

## Milestone 5: Performance + Scale Hardening (Sprint 8, ~3 weeks)
- DB indexes for scene/region tables
- Bulk emit batching + backpressure
- Cache scene graphs/frontiers where safe
- Success: 10k-node scene emits under 2s on dev hardware

## Milestone 6: Multiplayer/Networking (Optional, ~4-6 weeks)
- Session model + sync protocol
- Auth/session replay determinism
- Success: multi-client sessions with consistent world state

## Milestone 7: Release Readiness (Sprint 10, ~2-3 weeks)
- End-to-end acceptance tests
- Production deploy playbook + rollback
- Metrics/observability
- Success: stable deployment + reproducible releases

## Current Position
- Foundation complete for realm-aware pipelines, scene library, determinism, and core rules.
- Next: Milestone 1 (world streaming) and Milestone 2 (simulation loop).

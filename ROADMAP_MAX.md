# Max-Effort Roadmap (Three-Realm Anthology)

This roadmap assumes the anthology world always contains three realms:
1. Lapidus (Overworld)
2. Mercurie (Faewilds)
3. Sulphera (Underworld)

All systems, data models, and tooling must treat these as a first-class, always-present triad.

## Guiding Principles
- Determinism first: simulations and content output must be replayable from seed + event log.
- Realm-aware by default: every world/system API must accept realm context or derive it.
- Strict schemas: all content and runtime data validated against schema + migrations.
- Tooling parity: authoring tools must exist for every runtime system introduced.

## Phase 0: Core Hardening (Weeks 1–4)
**Goal:** Make the current engine reliable, deterministic, and realm-aware everywhere.

1. Repo + Build Hygiene
- Add `tools/` build scripts for local + CI parity.
- Enforce code style + lint for Python/JS.
- Add deterministic test harness for Shygazun compiler.

2. Core Schemas
- Define and version:
  - `EngineState` (realm_id, tick, entities, tables, scene_graph)
  - `RenderConstraints` (rose_vector_calculus, materials, palette, policy)
  - `AssetManifest` (materials, atlases, scenes, realm tags)
  - `RealmConfig` (Lapidus/Mercurie/Sulphera)

3. Realm-First Data Model
- Add `realm_id` to:
  - placements, scenes, entities, dialogue, quests, items.
- Introduce `RealmRegistry` (three realms baked-in).

4. Deterministic Runtime
- Global tick loop, event queue, replay logs.
- Deterministic PRNG seeded by world + realm.

Deliverables:
- Determinism tests.
- Realm registry + realm validation in engine state.
- Schema files checked in + validated.

## Phase 1: Content Pipeline (Weeks 5–12)
**Goal:** Turn Cobra/Shygazun into a full content pipeline that emits realm-aware assets and scenes.

1. Compiler Pipeline
- Cobra → IR → Shygazun resolution → entity placements → scene graph.
- Static checks:
  - unresolved symbols (warn only, never ban)
  - realm mismatches
  - asset dependency resolution

2. Asset Pack System
- Packs are realm-scoped or realm-agnostic.
- Validation rules:
  - textures exist
  - materials reference AppleBlossom symbols
  - atlas frames valid

3. Scene Graph Builder
- Realm-aware scene ids: `lapidus/`, `mercurie/`, `sulphera/`
- Layering rules with z-offset and occlusion policy.

4. Authoring Tooling
- CLI commands:
  - `compile`
  - `validate`
  - `publish`
- UI panels for:
  - entity placement
  - scene graph preview
  - realm selector

Deliverables:
- Pipeline that emits scene graphs + asset manifests per realm.
- Content validation with realm enforcement.

## Phase 2: Runtime Systems (Weeks 13–24)
**Goal:** A complete gameplay loop with quests, dialogue, inventory, skills, and realm traversal.

1. World Streaming
- Chunked regions per realm.
- Streaming policy based on realm + scene.

2. Dialogue Engine
- Branching with state conditions.
- Realm-aware dialogue variants.

3. Quest System
- Quest graph with realm requirements.
- Quest events emit structured changes into engine tables.

4. Inventory/Perks/Skills/VITRIOL
- Realm modifiers on all player stats.
- Sulphera rulers can influence VITRIOL.

5. Combat + AI
- Basic combat loop.
- AI state machines with realm-specific behavior.

Deliverables:
- Quests + dialogue + combat at MVP.
- Realm modifiers active across systems.

## Phase 3: Rendering + Visual Fidelity (Weeks 25–36)
**Goal:** Make visuals production‑grade with layered depth and stable performance.

1. Renderer Core
- Voxel + sprite hybrid pipeline.
- Strict layer ordering.

2. Lighting + Materials
- Rose vector calculus drives lighting.
- AppleBlossom drives material properties.
- Realm palettes for default color grading.

3. Texture/Atlas Pipeline
- Atlas compilation with caching.
- Runtime hot-reload for iteration.

Deliverables:
- Visual renderer that is game‑ready.
- Realm-based visual theming.

## Phase 4: Narrative + Content Expansion (Weeks 37–52)
**Goal:** Build the anthology’s systems and content at scale.

1. Narrative Tools
- Dialogue editor (branching + condition UI).
- Quest editor (graph + gating).

2. Content Production
- Asset packs per realm.
- Scene libraries with reusable templates.

3. World Logic
- Realm transitions (gates, keys, crystals).
- Global world events affecting all realms.

Deliverables:
- Substantial world content across Lapidus, Mercurie, Sulphera.

## Phase 5: QA, Playtest, Release (Weeks 53–60)
**Goal:** Stabilize and ship.

1. Automated Testing
- Determinism replays.
- Quest/dialogue coverage.

2. Playtest Harness
- Debug overlays.
- Telemetry for crash + logic errors.

3. Release Pipeline
- Android signing + update pipeline.
- Content patch system.

Deliverables:
- Playtestable release.
- Patchable content updates.

## Immediate Next Implementation Targets
1. Realm registry + realm_id propagation into engine state + placement payloads.
2. Content pipeline validation with realm awareness.
3. Renderer realm theming (color grading + lighting presets).

## Realm‑Aware Data Contract (Baseline)
Every entity/content item includes:
- `realm_id`: `lapidus` | `mercurie` | `sulphera`
- `scene_id`: `realm/scene_name`
- `constraints`: compiled Shygazun (material + palette + rose vector)

## Success Criteria
- Author content once, target specific realms, and compile deterministically.
- Renderer outputs correct realm visuals and lighting.
- Runtime logic respects realm modifiers at every system boundary.

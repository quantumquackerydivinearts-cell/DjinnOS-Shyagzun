# Sprint Plan (Max Effort, Three Realms Always-On)

This plan turns `ROADMAP_MAX.md` into executable sprints with concrete file targets, APIs, and schemas.

## Sprint 1: Realm Registry + Core Contracts (2 weeks)
**Goal:** Make realm identity explicit across engine state, placements, and assets.

### Backend (atelier-api)
1. Realm registry
- Add `Realm` model and seed entries:
  - `lapidus`, `mercurie`, `sulphera`
- Files:
  - `apps/atelier-api/atelier_api/models.py`
  - `apps/atelier-api/alembic/versions/0008_add_realms.py` (new)
  - `apps/atelier-api/atelier_api/repositories.py` (realm accessors)

2. Realm-aware schemas
- Add `realm_id` to:
  - placement payloads
  - asset manifests
  - game state tables where applicable
- Files:
  - `apps/atelier-api/atelier_api/business_schemas.py`
  - `apps/atelier-api/atelier_api/services.py`

3. API endpoints
- `GET /v1/realms`
- `POST /v1/realms/validate`
- Files:
  - `apps/atelier-api/atelier_api/main.py`

### Engine/Core (qqva)
1. Placement context
- Ensure `realm_id` is carried into cobra/placement payloads.
- Files:
  - `qqva/shygazun_compiler.py`
  - `qqva/physics.py` (if realm influences physics)

### Frontend (atelier-desktop)
1. Realm selector in Renderer Lab
- Adds a realm dropdown for visual renderer + pipeline.
- Persist to local storage and include in engine payload.
- Files:
  - `apps/atelier-desktop/src/App.jsx`

### Acceptance tests
- `tests/test_realms_registry.py` (new)
- `tests/test_realm_in_payloads.py` (new)

Deliverable: realm registry in DB + realm-aware payloads end-to-end.

---

## Sprint 2: Content Pipeline Validation (2 weeks)
**Goal:** Cobra/Shygazun content validation with realm awareness.

### Backend (atelier-api)
1. Validation service
- Validate:
  - realm exists
  - scene_id matches `realm/scene`
  - unresolved symbols (warn, not block)
- New endpoint:
  - `POST /v1/content/validate`
- Files:
  - `apps/atelier-api/atelier_api/services.py`
  - `apps/atelier-api/atelier_api/main.py`

### Engine/Core (qqva)
1. Validator utilities
- `validate_scene_graph`
- `validate_realm_tags`
- Files:
  - `qqva/validators.py` (new)

### Frontend (atelier-desktop)
1. Validation panel
- Upload Cobra/JSON -> validate -> show warnings
- Files:
  - `apps/atelier-desktop/src/App.jsx`

Deliverable: realm-aware content validation workflow.

---

## Sprint 3: Scene Graph Compiler + Realm Scene Library (3 weeks)
**Goal:** Build scene graph compiler with realm namespace + layering rules.

### Engine/Core (qqva)
1. Scene graph builder
- Cobra placements -> nodes with layers + z offsets
- `scene_id` required to be `realm/scene`
- Files:
  - `qqva/scene_graph.py` (new)
  - `qqva/shygazun_compiler.py`

2. Layering rules
- Default layers with z offsets
- Files:
  - `qqva/scene_graph.py`

### Backend (atelier-api)
1. Scene library
- CRUD for scenes with realm binding
- Files:
  - `apps/atelier-api/atelier_api/models.py`
  - `apps/atelier-api/atelier_api/main.py`
  - `apps/atelier-api/alembic/versions/0009_add_scene_library.py` (new)

Deliverable: realm scene library + scene graph compiler.

---

## Sprint 4: Runtime World Streaming (3 weeks)
**Goal:** Chunked world streaming per realm.

### Backend
1. Region store
- Region table keyed by `realm_id`, `region_key`
- Files:
  - `apps/atelier-api/atelier_api/models.py`
  - `apps/atelier-api/alembic/versions/0010_add_regions.py`

2. Stream endpoints
- `GET /v1/world/regions?realm_id=...`
- `POST /v1/world/regions/load`

### Engine/Core
1. Stream controller
- `WorldStream.load(realm_id, region_key)`
- Files:
  - `qqva/world_stream.py` (new)

Deliverable: load/unload regions by realm.

---

## Sprint 5: Dialogue + Quest Systems (4 weeks)
**Goal:** Realm-aware narrative runtime.

### Backend
1. Dialogue models + endpoints
- Branching, state conditions
- Files:
  - `apps/atelier-api/atelier_api/models.py`
  - `apps/atelier-api/atelier_api/main.py`
  - migration: `0011_add_dialogue.py`

2. Quest models + endpoints
- Quest graph, realm tags
- Files:
  - `apps/atelier-api/atelier_api/models.py`
  - `apps/atelier-api/atelier_api/main.py`
  - migration: `0012_add_quests.py`

### Engine/Core
1. Runtime dialogue resolver
- `dialogue.select_path(state, realm_id)`
- Files:
  - `qqva/dialogue_runtime.py` (new)

2. Quest engine
- `quest.advance(state, event)`
- Files:
  - `qqva/quest_engine.py` (new)

Deliverable: dialogue/quest runtime with realm constraints.

---

## Sprint 6: Visual Fidelity + Realm Theming (3 weeks)
**Goal:** Stable renderer with realm‑specific grading + Rose lighting.

### Frontend
1. Realm theme presets
- color grading, lighting presets per realm
- Files:
  - `apps/atelier-desktop/src/App.jsx`

2. Layer compositing rules
- Ensure z-order stability + occlusion

Deliverable: renderer that visually distinguishes realms.

---

## Sprint 7+: Combat, AI, Trading, Crafting (4–8 weeks)
Build and integrate:
- Combat loop
- AI behaviors
- Market + blacksmith + alchemy
- All realm‑aware by default

---

## Immediate Actions (next commit)
1. Sprint 1 implementation:
- Add realm registry (DB + API).
- Add `realm_id` to placement payloads and engine tables.
- Add realm selector in Renderer Lab.
2. Add tests for realm validation.

If you want, I can start Sprint 1 immediately and implement the realm registry + payload changes now.

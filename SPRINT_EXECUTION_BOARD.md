# Sprint Execution Board (AAA Toolchain Path)

This board operationalizes `AAA_TOOLCHAIN_BACKLOG.md` into implementation sprints with:
- concrete task IDs
- dependency order
- atomic commit batches
- done criteria

---

## Status Legend
- `TODO` not started
- `WIP` in progress
- `DONE` merged + verified
- `BLOCKED` waiting on dependency

---

## Sprint S1: Module Platform Foundation (1 week)
Goal: Make module specs first-class executable units.

### Tasks
1. `S1-T1` Module file convention and loader hardening (`DONE`)
- Path: `gameplay/modules/*.json`
- Add schema-safe loader and ID validation.

2. `S1-T2` Runtime action `module.run` (`DONE`)
- Add action kind + catalog entry.
- Execute nested runtime action from module `execution.runtime_action_kind`.
- Enforce expected lineage refs.

3. `S1-T3` Starter module packs (`DONE`)
- Add 5 specs:
  - `module.shygazun.interpret`
  - `module.quest.advance_by_graph`
  - `module.render.scene.reconcile`
  - `module.market.trade.realm_policy`
  - `module.audio.cue.play_policy`

### Commit Batch
1. `feat(runtime): add module.run action and module loader`
2. `feat(content): add baseline gameplay module specs`

### Done Criteria
- `module.run` executes and validates expected refs.
- Runtime boundary tests pass.

---

## Sprint S2: Shygazun Contract Completion (1 week)
Goal: Unified Shygazun API + lineage parity.

### Tasks
1. `S2-T1` Add direct interpret endpoint (`DONE`)
- `POST /v1/game/shygazun/interpret`

2. `S2-T2` Add typed interpret schema + lineage contract (`DONE`)
- `ShygazunInterpretInput/Out`
- include lineage/function refs fields.

3. `S2-T3` Unify runtime and API path (`DONE`)
- runtime `shygazun.interpret` calls service method.

### Commit Batch
1. `feat(shygazun): add interpret endpoint and typed contract`
2. `refactor(runtime): reuse interpret service in runtime action`

### Done Criteria
- Translate/correct/interpret all produce lineage refs.
- API and runtime behavior match.

---

## Sprint S3: Module Registry and Tooling Surface (1-2 weeks)
Goal: Remove manual file spelunking for modules.

Status: `TODO`

### Tasks
1. `S3-T1` API listing endpoints
- `GET /v1/game/modules`
- `GET /v1/game/modules/{module_id}`
- return: id, version, runtime_action_kind, required/optional refs.

2. `S3-T2` Validation endpoint
- `POST /v1/game/modules/validate`
- checks:
  - required top-level fields
  - legal runtime action kind
  - no recursive module.run target
  - valid expected ref key shape `L{int}:{string}`

3. `S3-T3` Desktop module browser panel
- list modules
- view spec JSON
- run module with payload overrides
- show expected vs available refs diff

### Dependencies
- Depends on S1.

### Commit Batch
1. `feat(api): add module registry read/validate endpoints`
2. `feat(desktop): add module browser and runner UI`
3. `test(modules): add module contract validation tests`

### Done Criteria
- You can discover and execute any module from UI.
- Validation errors are clear and actionable.

---

## Sprint S4: Lineage Inspector (1-2 weeks)
Goal: Debug nonlinear pipelines quickly.

Status: `TODO`

### Tasks
1. `S4-T1` Add API filters
- Layer node/edge query by:
  - workspace
  - layer
  - function_id
  - actor_id

2. `S4-T2` Desktop lineage explorer
- table + graph modes
- node trace (inbound/outbound edges)
- jump from runtime action result to lineage nodes

3. `S4-T3` Export lineage snapshot
- JSON export for test fixtures and bug reports.

### Dependencies
- Depends on S1/S2.

### Commit Batch
1. `feat(api): lineage query filters and trace helpers`
2. `feat(desktop): lineage inspector with trace navigation`

### Done Criteria
- Any module execution can be lineage-debugged in <= 3 clicks.

---

## Sprint S5: Quest Graph Authoring UX (2 weeks)
Goal: Headless quest authoring with deterministic validation.

Status: `TODO`

### Tasks
1. `S5-T1` Quest graph editor view
- node/edge editing
- transition metadata

2. `S5-T2` Dry-run simulation panel
- calls `quest.advance_by_graph` with `dry_run=true`
- displays predicted next step and gate reasons.

3. `S5-T3` Graph integrity checks
- no orphan terminal unless explicitly marked
- deterministic ordering hash visible in UI.

### Dependencies
- Depends on S3/S4.

### Commit Batch
1. `feat(desktop): quest graph visual editor`
2. `feat(runtime): quest graph dry-run simulation wiring`
3. `test(quests): deterministic graph regression fixtures`

### Done Criteria
- Designers can author + validate quest graphs without raw JSON edits.

---

## Sprint S6: Asset Pipeline MVP (3 weeks)
Goal: Deterministic import/cook/pack foundation.

Status: `TODO`

### Tasks
1. `S6-T1` Manifest model upgrade
- source path, import settings hash, cooked artifacts, dependency list.

2. `S6-T2` Cook scripts
- texture/audio/glTF deterministic cook outputs.

3. `S6-T3` Runtime pack loader
- load/unload pack by manifest ID.
- hash/version checks.

### Dependencies
- Independent of S5; can run parallel after S3.

### Commit Batch
1. `feat(db): extend asset manifest schema for cook pipeline`
2. `feat(build): add deterministic cook scripts`
3. `feat(runtime): add asset pack loader with hash checks`

### Done Criteria
- Same source/settings => identical cooked hash.
- Pack can be loaded and reverted safely.

---

## Sprint S7: Determinism and Release Gates (2 weeks)
Goal: Turn invariants into CI blockers.

Status: `TODO`

### Tasks
1. `S7-T1` Replay hash gate
- run seeded runtime plans twice, assert equal hashes.

2. `S7-T2` Frontier safety gate
- assert no auto-collapse and no commit without attestation in test scenarios.

3. `S7-T3` Module contract gate
- ensure expected refs contracts stay valid.

### Dependencies
- Depends on S1-S3 minimum.

### Commit Batch
1. `test(ci): add replay determinism gate suite`
2. `test(ci): add module contract and frontier policy gates`

### Done Criteria
- CI blocks on determinism or policy regressions.

---

## Sprint S8: Production Workflow Rails (2-3 weeks)
Goal: Team-ready promotion and rollback mechanics.

Status: `TODO`

### Tasks
1. `S8-T1` Promotion pipeline
- `dev -> stage -> prod` bundle promotion by manifest set.

2. `S8-T2` Rollback by bundle ID
- one-command rollback + audit event.

3. `S8-T3` Policy checks before promote
- tests passing
- module validation passing
- lineage contract passing

### Dependencies
- Depends on S6/S7.

### Commit Batch
1. `feat(release): add environment promotion workflow`
2. `feat(release): rollback and audit trail`
3. `feat(policy): pre-promotion enforcement`

### Done Criteria
- Safe, auditable production promotion and rollback.

---

## Critical Path
`S1 -> S3 -> S4 -> S7 -> S8`  
Parallel lane: `S3 -> S6 -> S8`

---

## First 10 Commits (Recommended Order)
1. `feat(runtime): add module.run action and loader`
2. `feat(content): add baseline module spec files`
3. `feat(shygazun): add interpret endpoint + contract`
4. `refactor(runtime): unify shygazun interpret service path`
5. `feat(api): module list/get endpoints`
6. `feat(api): module validate endpoint`
7. `feat(desktop): module runner panel`
8. `feat(api): lineage query filters`
9. `feat(desktop): lineage inspector`
10. `test(ci): replay + module contract gates`

---

## Ready-to-Start Next (Immediate)
1. Build `GET /v1/game/modules` + `GET /v1/game/modules/{module_id}`.
2. Build `POST /v1/game/modules/validate`.
3. Add desktop Module Browser panel wired to these endpoints.


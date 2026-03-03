# AAA Toolchain Backlog

## Scope
This backlog maps AAA-grade toolchain/editor requirements onto the current DjinnOS stack:
- Kernel + deterministic runtime actions
- 12-layer lineage/function store
- Shygazun/Cobra semantic pipelines
- Module specs in `gameplay/modules`
- Atelier desktop/editor surfaces

---

## Program 1: Editor and Authoring Maturity

### 1. Module Registry + Runner UI
- Add module browser (`gameplay/modules/*.json`) in Atelier.
- Add run form with payload overrides and version pinning.
- Show module execution result with nested action trace.
- Show expected refs vs available refs diff.

Acceptance:
- Can discover, run, and debug all module specs without manual JSON editing.
- Failed expected-ref contract shows actionable diagnostics.

Repo targets:
- `apps/atelier-desktop/src/App.jsx`
- `apps/atelier-api/atelier_api/main.py`
- `apps/atelier-api/atelier_api/services.py`

### 2. Lineage Inspector UI
- Add graph view for `layer_nodes`, `layer_edges`, `function_store_entries`.
- Filter by workspace, actor, module_id, function_id, layer.
- Click-through from runtime action output to lineage nodes.

Acceptance:
- Given a runtime action result, can navigate to all referenced lineage artifacts in <= 3 clicks.

Repo targets:
- `apps/atelier-desktop/src/App.jsx`
- `apps/atelier-api/atelier_api/main.py` (list/trace endpoints expansion)

### 3. Quest Graph Visual Editor
- Build node/edge editor for quest graphs with transition constraints.
- Inline validation against graph hash/cycle rules.
- Dry-run simulator using `quest.advance_by_graph`.

Acceptance:
- Designer can author/update quest graph and run dry-run transitions without manual JSON.

Repo targets:
- `apps/atelier-desktop/src/App.jsx`
- `apps/atelier-api/atelier_api/services.py`
- `tests/`

### 4. Scene Reconcile UX
- Scenegraph diff panel: missing/stale/changed identities.
- One-click apply/revert and deterministic preview tick.

Acceptance:
- Reconcile workflow is fully UI-driven with deterministic result hash display.

Repo targets:
- `apps/atelier-desktop/src/App.jsx`
- `apps/atelier-api/atelier_api/services.py`

---

## Program 2: Asset Pipeline (Import/Cook/Pack)

### 5. Asset Manifest Expansion
- Extend manifests to include:
  - source path
  - cooked artifacts per target
  - dependency edges
  - import settings hash
  - compression profile

Acceptance:
- Every runtime-loaded asset is traceable from source -> cooked output -> manifest hash.

Repo targets:
- `apps/atelier-api/atelier_api/models.py`
- `apps/atelier-api/alembic/versions/*`
- `apps/atelier-api/atelier_api/services.py`

### 6. Importers + Deterministic Cooking
- Implement importer pipeline for:
  - textures
  - audio
  - mesh/scene formats (start with glTF)
- Deterministic cook outputs by content hash + settings hash.

Acceptance:
- Re-cooking same source/settings produces identical artifact hashes.

Repo targets:
- `scripts/` (build/cook scripts)
- `apps/atelier-api/atelier_api/services.py`
- `gameplay/` (asset packs)

### 7. Asset Pack Loader + Hot Reload
- Runtime load/unload of named content packs.
- Version pinning and dependency checks.
- Hot reload in editor mode with rollback on failure.

Acceptance:
- Can swap pack versions during editor session without runtime corruption.

Repo targets:
- `apps/atelier-api/atelier_api/services.py`
- `apps/atelier-desktop/electron/main.js`
- `apps/atelier-desktop/src/App.jsx`

---

## Program 3: Runtime Hardening and CI Gates

### 8. Determinism Gate Suite
- Add CI tests for:
  - replay hash equality
  - frontier non-collapse without attestation
  - lineage reference stability
- Add seeded scenario packs for regression.

Acceptance:
- CI blocks merge if replay determinism or lineage contracts regress.

Repo targets:
- `tests/`
- `scripts/verify_*.py`
- CI workflow config

### 9. Save/Schema Evolution
- Versioned save format with migration chain.
- Backward compatibility tests across N previous versions.

Acceptance:
- Old save loads cleanly with explicit migration report and no silent data loss.

Repo targets:
- `apps/atelier-api/atelier_api/services.py`
- `apps/atelier-api/alembic/versions/*`
- `tests/`

### 10. Perf + Diagnostics
- Add frame/runtime budgets and telemetry events.
- Add crash capture (desktop + API) with correlation IDs.
- Add profile snapshots for heavy modules.

Acceptance:
- Performance and crash triage possible from one report packet.

Repo targets:
- `apps/atelier-desktop/electron/main.js`
- `apps/atelier-desktop/src/App.jsx`
- `apps/atelier-api/atelier_api/main.py`

---

## Program 4: Team-Scale Production Workflow

### 11. Content Promotion Pipeline
- Environments: `dev -> stage -> prod`.
- Promote module/asset/quest bundles with signed manifests.
- Rollback support by manifest ID.

Acceptance:
- Any release can be rolled back by selecting prior manifest bundle.

Repo targets:
- `scripts/`
- `deploy/`
- `apps/atelier-api/atelier_api/services.py`

### 12. Review Gates + Policy Engine
- Add policy checks:
  - required tests
  - lineage contract completeness
  - attestation requirements
- Block publish when policy fails.

Acceptance:
- No content/package reaches production without passing policy bundle.

Repo targets:
- `apps/atelier-api/atelier_api/services.py`
- CI workflows
- `docs/`

### 13. Multi-User Collaboration Controls
- Add lock/claim semantics for scenes/graphs/modules.
- Audit log for edits/runs/publishes.
- Conflict workflow for simultaneous edits.

Acceptance:
- Concurrent edits are conflict-safe and auditable.

Repo targets:
- `apps/atelier-api/atelier_api/models.py`
- `apps/atelier-api/alembic/versions/*`
- `apps/atelier-desktop/src/App.jsx`

---

## Cross-Cutting Backlog (Always On)

### 14. Security + Capability Hygiene
- Tighten capability checks for all new endpoints/actions.
- Signed command execution for high-impact operations.

### 15. Documentation as Contract
- Keep executable contracts for:
  - runtime action kinds
  - module spec schema
  - lineage key conventions
- Auto-generate docs from schema/source where possible.

### 16. Content Linting
- Add lints for quest graphs, scenegraph entities, module refs.
- Add strict mode for release builds.

---

## Recommended Execution Order
1. Program 1 (Editor and authoring maturity)
2. Program 2 (Asset import/cook/pack)
3. Program 3 (determinism + reliability gates)
4. Program 4 (team-scale production workflow)

Rationale:
- You already have a strong deterministic core.
- Biggest multiplier now is authoring speed + asset pipeline + reliability gates.

---

## Definition of “AAA Toolchain-Ready” for this stack
You are ready when all are true:
1. Any feature/content module can be authored, tested, and published without raw DB edits.
2. Replays are deterministic under CI gate across seeded scenarios.
3. Asset import/cook/pack is deterministic with hash-addressed artifacts.
4. Releases can be promoted/rolled back by signed manifest bundles.
5. Multi-user edits are auditable, conflict-safe, and policy-gated.


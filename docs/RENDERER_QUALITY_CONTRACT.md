# Renderer Quality Contract v1

## Purpose
Define non-negotiable quality gates for renderer output and renderer input semantics so the platform can support production-grade content authoring.

## Scope
This contract governs:
- Renderer Lab output quality (2D cardinal, 2.5D isometric, 3D preview)
- Asset and tile input structure consumed by renderer pipelines
- Camera/motion readability standards
- Cross-system fidelity targets for map, sprite, and scene authoring

This contract does not redefine kernel authority rules. Kernel determinism and attestation constraints remain governed by `docs/MATH_BOUNDARY.md`.

## Visual Direction
Target style envelope:
- Mid-generation creature-collector readability (clean silhouettes, palette control, legible tile language)
- CRPG-grade systemic depth support (dense state overlays, tactical readability)
- Narrative/JRPG dialogue composability (scene staging, focal framing, readable character placement)

## Hard Constraints
1. Readability First
- Player, interactables, and traversable paths must remain visually distinguishable at all supported zoom levels.
- No default palette/theme may produce unreadable foreground-background contrast.

2. Multi-Scale Input LOD
- Tile/voxel/sprite input must support explicit author-driven LOD metadata.
- LOD transitions must preserve shape identity (no topology breaks or disappear/reappear popping for core geometry).

3. Non-Blocky Geometry Envelope
- Renderer input must allow smooth curve approximation via high-resolution placement and weighted blending.
- Curvature approximation quality is measured by silhouette continuity, not by raw primitive count.

4. Projection Parity
- Equivalent scene intent must be representable in cardinal 2D, 2.5D, and 3D modes.
- Camera transforms may change composition but must not rewrite gameplay semantics.

5. Motion Stability
- Player position and camera follow state are persistent runtime variables.
- Input events must not hard-reset actor transform unless explicitly requested.

6. Authoring Ergonomics
- Core render controls must be actionable from Studio UI (no mandatory CLI path for routine workflows).
- Fullscreen renderer must consume the same active scene input as in-panel renderer.

## Rendering Input Contract
1. Canonical Inputs
- JSON scene/tile payloads
- Cobra-derived placements
- Shygazun-derived semantic render hints
- Engine state render graph

2. Required Input Fields (minimum)
- `scene_id`
- `realm_id`
- `entities` or `voxels`/`tiles`
- `materials` or palette bindings
- `camera` (or explicit default camera policy)

3. Optional Enhancers
- `lod` metadata per element or region
- atlas/texture bindings
- edge glow flags
- walkability/navigation tags
- render mode override (`2d`, `2.5d`, `3d`)

## Acceptance Gates
A build is considered renderer-contract compliant only when all gates pass:

1. Gate A: Scene Coherence
- Scene loads in panel and fullscreen with matching entity count, material bindings, and camera seed.

2. Gate B: Input Parity
- JSON, Cobra, and engine-derived render paths produce equivalent layout intent for the same test scene.

3. Gate C: LOD Fidelity
- Zooming between min and max editor scales preserves object identity and interaction affordances.

4. Gate D: Motion Integrity
- Click-to-move, key movement, and path-stepped movement update persistent player state without snapback.

5. Gate E: Atlas/Texturing
- Atlas-bound materials render consistently across at least one building, one character sprite, and one environment background.

6. Gate F: Performance Envelope (dev baseline)
- Stable frame pacing on representative development hardware for canonical test scene.
- No escalating memory growth during repeated scene reload + movement loops.

## Canonical Test Scene
Minimum recurring test asset set:
- one building
- one humanoid sprite
- one background layer
- one navigable map segment
- one dynamic light/palette shift

## Definition of Done
Renderer sprint work is complete only when:
- contract gates are marked pass in `gameplay/contracts/renderer_acceptance_checklist.v1.json`
- regression checks are re-runnable without manual code edits
- known limitations are documented with explicit follow-up items

## Out of Scope
- Final AAA art pipeline
- Advanced skeletal animation tooling
- Runtime shader graph authoring UI

These remain roadmap items and do not block this contract from being used as production readiness criteria for current renderer architecture.

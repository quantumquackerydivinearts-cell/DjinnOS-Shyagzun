# Renderer Pack v2 Toolchain

This document defines the production-oriented renderer pack compiler flow.

## Purpose

`pack.v2` converts ad-hoc renderer scene payloads into deterministic, hash-addressable artifacts suitable for large-scale content pipelines.

## Compiler

- Script: `scripts/build_renderer_pack_v2.py`
- Output schema: `atelier.renderer.pack.v2`
- Contract schema: `schemas/renderer/renderer_pack.v2.schema.json`

## Inputs

- Required:
  - `--input <json>`
  - `--output <json>`
- Optional sidecars:
  - `--materials <json>`
  - `--atlases <json>`
  - `--layers <json>`
  - `--settings <json>`
- Optional metadata:
  - `--workspace-id <id>` (default: `main`)
  - `--source <label>` (default: `renderer_toolchain`)
  - `--name <pack_name>`

## Example

```powershell
py scripts/build_renderer_pack_v2.py `
  --input apps/atelier-desktop/public/renderer-pack-source.json `
  --output gameplay/renderer_packs/compiled/renderer-pack-alpha.v2.json `
  --workspace-id main `
  --source studio_hub
```

## Determinism Guarantees

- Voxels are normalized and sorted by spatial keys.
- Materials/atlases/layers are normalized and sorted by id.
- Canonical JSON hashing is used for:
  - scene/materials/atlases/layers/settings
  - source payload
  - compile basis hash
  - final pack hash
- `pack_id` is derived from compile hash (`rpackv2_<hex16>`).

## Runtime Compatibility

Desktop renderer pack application now accepts both:

- `atelier.renderer.pack.v1`
- `atelier.renderer.pack.v2`

v2 payloads use `compiled_scene.voxels`.

## Validation

- Script: `scripts/validate_renderer_pack_v2.py`

```powershell
py scripts/validate_renderer_pack_v2.py --input gameplay/renderer_packs/compiled/renderer-pack-alpha.v2.json
```

## Diffing

- Script: `scripts/diff_renderer_packs_v2.py`

```powershell
py scripts/diff_renderer_packs_v2.py `
  --before gameplay/renderer_packs/compiled/renderer-pack-alpha.v2.json `
  --after gameplay/renderer_packs/compiled/renderer-pack-beta.v2.json `
  --output reports/renderer-pack-diff.alpha-vs-beta.json
```

Diff report includes:
- hash-level changes (scene/materials/atlases/layers/settings/pack)
- count deltas
- dependency deltas (atlas ids and texture paths)
- voxel material usage deltas

## Stream Partition Compiler (Phase 2)

- Script: `scripts/build_renderer_stream_manifest_v1.py`
- Output schema: `atelier.renderer.stream_manifest.v1`
- Contract schema: `schemas/renderer/renderer_stream_manifest.v1.schema.json`

Purpose:
- Partition compiled pack scenes into spatial chunks.
- Emit stream manifest metadata for runtime paging.
- Emit per-chunk payload files (optional).
- Produce per-chunk budget checks and dependency residency tables.

Example:

```powershell
py scripts/build_renderer_stream_manifest_v1.py `
  --input gameplay/renderer_packs/compiled/renderer-pack-alpha.v2.json `
  --output gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --chunk-size-x 64 `
  --chunk-size-y 64 `
  --partition-mode material_aware `
  --optimize-locality `
  --boundary-band 2 `
  --optimize-passes 2 `
  --max-chunk-voxels 8000 `
  --max-chunk-bytes 1048576 `
  --emit-chunks
```

Manifest sections:
- `chunks`: bounds, voxel count, bytes, hash, dependency sets, chunk path
- `budgets`: limits and explicit violation list
- `residency`: atlas/texture/material fanout across chunks
- `partition`: mode and optimization stats (`moved_voxels`)

Partition modes:
- `fixed_grid`: pure spatial partitioning by chunk size
- `material_aware`: boundary reassignment prefers chunks already containing the same material
- `lod_aware`: boundary reassignment prefers chunks already containing matching LOD buckets

Hotset-aware planning:
- `--hotset-materials` (CSV)
- `--hotset-atlas-ids` (CSV)
- `--hotset-textures` (CSV)
- `--hotset-target-max-chunks` (fanout target)

When hotset inputs are provided, optimizer scoring prefers chunk assignments that cluster hot dependencies.
Manifest includes `hotset` section with explicit fanout violations.

## Stream Manifest Diff

- Script: `scripts/diff_renderer_stream_manifests_v1.py`

```powershell
py scripts/diff_renderer_stream_manifests_v1.py `
  --before gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --after gameplay/renderer_packs/streams/renderer-pack-beta.stream.v1.json `
  --output reports/renderer-stream-diff.alpha-vs-beta.json
```

Outputs:
- chunk add/remove/change summary
- per-chunk voxel and byte deltas
- residency chunk-count deltas for atlas/texture/material dependencies
- budget violation count deltas

## Residency Budget Gate

- Contract: `gameplay/contracts/renderer_stream_budgets.v1.json`
- Script: `scripts/check_renderer_stream_residency_budgets.py`

```powershell
py scripts/check_renderer_stream_residency_budgets.py `
  --input gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --output reports/renderer-stream-residency-budget.alpha.json
```

Override limits directly:

```powershell
py scripts/check_renderer_stream_residency_budgets.py `
  --input gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --max-atlas-chunks 16 `
  --max-texture-chunks 16 `
  --max-material-chunks 32
```

## Prefetch Manifest Builder

- Script: `scripts/build_renderer_prefetch_manifest_v1.py`
- Output schema: `atelier.renderer.stream_prefetch_manifest.v1`
- Contract schema: `schemas/renderer/renderer_stream_prefetch_manifest.v1.schema.json`

```powershell
py scripts/build_renderer_prefetch_manifest_v1.py `
  --input gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --output gameplay/renderer_packs/streams/renderer-pack-alpha.prefetch.v1.json `
  --max-ring 2
```

Prefetch artifact includes deterministic adjacency rings and priority tiers:
- `immediate` (ring 1)
- `warm` (ring 2)
- `cold` (ring 3+ up to `max-ring`)

## Toolchain Go/No-Go

- Script: `scripts/renderer_toolchain_go_no_go.py`
- Output schema: `renderer_toolchain_report.v1`

```powershell
py scripts/renderer_toolchain_go_no_go.py `
  --compiled-pack gameplay/renderer_packs/compiled/renderer-pack-alpha.v2.json `
  --stream-manifest gameplay/renderer_packs/streams/renderer-pack-alpha.stream.v1.json `
  --prefetch-manifest gameplay/renderer_packs/streams/renderer-pack-alpha.prefetch.v1.json `
  --residency-report reports/renderer-stream-residency-budget.alpha.json `
  --output reports/renderer_toolchain/report.alpha.json
```

## 12-Layer DB Projection

- Script: `scripts/renderer_toolchain_project_to_layers.py`

Projects the renderer toolchain artifacts into the game layer graph:
- L1-L8: input, compile, stream, prefetch, validation, budget, go/no-go
- L9-L11: candidate -> approved/rejected -> staged/active
- L12: Djinn function binding (`djinn.renderer.stream.execute`)

```powershell
py scripts/renderer_toolchain_project_to_layers.py `
  --report reports/renderer_toolchain/report.alpha.json `
  --workspace-id main `
  --reference-coeff-bp 7000 `
  --recursion-coeff-bp 3000 `
  --activate `
  --output reports/renderer_toolchain/layer_projection.alpha.json
```

Recursion coefficients:
- `reference_coeff_bp`: external reference influence (basis points)
- `recursion_coeff_bp`: prior-state influence (basis points)
- Recommended stable regime: `reference_coeff_bp + recursion_coeff_bp <= 10000`

## Djinn Function Resolution From Layers

- Script: `scripts/resolve_djinn_function_from_layers.py`

Resolves the callable Djinn function target from current layer state and function store.

```powershell
py scripts/resolve_djinn_function_from_layers.py `
  --workspace-id main `
  --function-id djinn.renderer.stream.execute `
  --function-version v1 `
  --state active `
  --output reports/renderer_toolchain/djinn_resolution.alpha.json
```

Resolution report includes:
- selected L11/L12 nodes
- linked L3 stream and L4 prefetch ancestry
- function store hash/signature
- normalized Djinn call args
- recursion profile (`labyr_nth.linear_recurrence.v1`)

## Deterministic Recursion / Fixed Point Check

- Script: `scripts/verify_renderer_layer_fixed_point.py`

```powershell
py scripts/verify_renderer_layer_fixed_point.py `
  --projection-report reports/renderer_toolchain/layer_projection.alpha.json `
  --iterations 32 `
  --output reports/renderer_toolchain/fixed_point.alpha.json
```

Checks:
- replay determinism (same coefficients + reference key => identical trace)
- fixed-point convergence detection under bounded integer recurrence

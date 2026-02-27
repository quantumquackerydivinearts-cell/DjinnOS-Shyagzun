# Shygazun Support Matrix

This matrix captures where Shygazun behavior is expected to work and how to verify it.

| Surface | Parse | Validate | Emit | Observe | Dictionary Lookup | Deterministic |
|---|---|---|---|---|---|---|
| Kernel (`shygazun.kernel_service`) | Yes (`/v0.1/akinenwun/lookup`) | Yes (rejects spaced compounds) | N/A | Yes (`/events`, `/observe`) | Yes | Yes (`frontier_hash` stable for same input) |
| Atelier API (`atelier_api.main`) | Proxy pass-through | Via kernel response | N/A | Yes (`/v1/ambroflow/semantic-value`) | Yes (`/v1/ambroflow/akinenwun/lookup`) | Yes (hash matches kernel) |
| Cobra Compiler (`qqva.shygazun_compiler`) | Yes (`split_akinenwun`, parser) | Partial (unknown symbols flagged unresolved) | Yes (`cobra_to_placement_payloads`) | N/A | Uses byte inventory (local + nested repo fallback) | Yes (`canonical_compound`) |
| Studio Hub (Electron FS tooling) | N/A | N/A | Writes `.cobra` files | Reads `.cobra` files | N/A | Yes (roundtrip file content) |
| Renderer Lab (desktop app) | Yes (Cobra/Shygazun parser hooks) | Lint warnings for lexical payload | Yes (emit placements path) | Yes (frontier graph view) | Yes (lookup actions) | Yes (frontier snapshots keyed by hash) |
| Android packaged desktop surface | Uses bundled web build | Same as web code | Same as web code | Same as web code | Same as web code | Depends on API/kernel backend determinism |

## Verification entrypoints

- `scripts/verify_shygazun_surfaces.ps1`
- `tests/test_shygazun_end_to_end.py`
- `tests/test_shygazun_compiler.py`

## Recommended routine

1. Start all services with `start-all.ps1 -VerifyShygazun`.
2. Run `py -m pytest -q tests/test_shygazun_end_to_end.py tests/test_shygazun_compiler.py`.
3. If any check fails, do not ship new content or rule packs until hash and lookup behavior is stable.

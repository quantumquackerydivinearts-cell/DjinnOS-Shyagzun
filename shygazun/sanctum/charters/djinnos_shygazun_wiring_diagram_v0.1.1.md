# DjinnOS × Shygazun Wiring Diagram v0.1.1

## Scope
This document maps runtime/tooling wiring for Shygazun Kernel v0.1.1 and aligned tooling layers.

Normative anchors:
- v0.1.1 frozen invariants
- Fix A: `EligibilityEvent` uses `candidate_id` + `candidate_hash` (no embedded candidate object)
- Fix B: frontiers canonical order is `id` ascending
- v0.2 change budget: filesystem placement does not affect kernel causality

## 1) Layer Diagram (ASCII)
```text
+--------------------------------------------------------------+
| Optional UI / CLI Surfaces                                  |
| - shygazun/ide/*cli.py                                      |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| Cobra Runtime Shim                                           |
| - shygazun/ide/cobra_runtime.py                             |
| (tooling bridge only; no semantics/attest/commit authority) |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| IDE Landing Port                                             |
| - shygazun/ide/atelier_port.py                              |
| (delegates only to public Kernel methods)                   |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| Shygazun Kernel                                              |
| - Kernel / CEG / types                                      |
| - append-only event graph, deterministic ordering views      |
+-------------------+--------------------+---------------------+
                    |                    |
                    v                    v
+-------------------------+    +-------------------------------+
| Registers               |    | Witness Surface               |
| - rose_stub / sakura    |    | - shape-only attestation      |
| - Lotus excluded logic  |    |   recording via kernel API    |
+-------------------------+    +-------------------------------+

+--------------------------------------------------------------+
| Conformance Pack (JSON)                                      |
| - shygazun/conformance/v0.1.1/conformance.json               |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| Conformance Runner (Python)                                  |
| - shygazun/conformance/runners/python/*                      |
| - deterministic verifier over HTTP API surface               |
+--------------------------------------------------------------+
```

## 2) Dataflow Map
### Place Flow
`CobraRuntime.place_line/place_packet`  
-> `AtelierPort.place_line`  
-> `Kernel.place`  
-> `CEG.add_event` (placement)  
-> `Kernel.observe`  
-> `CEG.add_event` (eligibility/refusal) and `CEG.add_edge` (conflicts)

### Observe Flow
IDE/CLI  
-> `AtelierPort.observe`  
-> `Kernel.observe`  
-> return structural candidates/refusals (no semantic interpretation layer)

### Attest Flow
Witness UI / operator tool  
-> `AtelierPort.record_attestation`  
-> `Kernel.record_attestation`  
-> `CEG.add_event` (attestation fact only)

### Conformance Flow
Runner step executor  
-> HTTP endpoints  
-> kernel service adapter  
-> kernel public methods (`place` / `observe` / `record_attestation` / etc.)

## 3) Determinism Rules
### Canonical JSON Hashing
- UTF-8 encoding
- object keys sorted lexicographically
- no JSON whitespace
- arrays are not reordered by tooling
- hash algorithm: SHA-256 hex

### Canonical Event Ordering
- `ceg.events` view order: `(at.tick asc, kind asc, id asc)`
- append-only storage is preserved; ordering is a sorted read view

### Canonical Edge Ordering
- `ceg.edges` view order: `(from_event asc, to_event asc, type asc)`
- append-only storage is preserved; ordering is a sorted read view

### Frontier Ordering
- frontiers exposed in canonical order `id asc` (Fix B)

### Diff-Exempt Metadata Keys Discipline
- only kernel-declared `diff_exempt_metadata_keys` may be ignored during canonical diff/hash checks
- IDE/runtime layers must not invent additional exemptions

## 4) Repo Placement Table
| Component | Path in repo | Owner layer (kernel/tooling/IDE) | Mutability class (locked/additive/pending) |
|---|---|---|---|
| Kernel orchestrator | `shygazun/kernel/kernel.py` | kernel | locked |
| Canonical Event Graph | `shygazun/kernel/ceg.py` | kernel | locked |
| Stable structural types | `shygazun/kernel/types/*` | kernel | locked |
| Register stubs | `shygazun/kernel/register/*` | kernel | additive |
| Witness adapters (shape-only) | `shygazun/kernel/witness/*` | kernel | additive |
| Conformance pack JSON | `shygazun/conformance/v0.1.1/*.json` | tooling | locked |
| Conformance runner | `shygazun/conformance/runners/python/*` | tooling | additive |
| IDE landing port | `shygazun/ide/atelier_port.py` | IDE | additive |
| Cobra runtime shim | `shygazun/ide/cobra_runtime.py` | IDE | additive |
| CLI surfaces | `shygazun/ide/*cli.py` | IDE | additive |
| Sanctum charters (Shygazun-side mirror) | `shygazun/sanctum/charters/*` | tooling | additive |
| Sanctum charters (DjinnOS root mapping) | `djinn_os/sanctum/charters/*` | tooling | additive |

## 5) Boundary MUST NOT List
- Kernel MUST NOT branch on filesystem path, mount, persistence backend, or repo location.
- IDE layer MUST NOT load or enforce kernel policies/plugins implicitly.
- Tooling MUST NOT infer meaning, intent, quest semantics, or world semantics.
- Runtime/IDE MUST NOT auto-attest or fabricate witness acts.
- Tooling MUST NOT collapse ambiguity/frontiers into a single interpretation.
- Any layer above Kernel MUST NOT mutate CEG directly.
- Any layer above Kernel MUST NOT introduce hidden authority paths around kernel public APIs.

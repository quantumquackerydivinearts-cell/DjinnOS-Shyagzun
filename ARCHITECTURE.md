# Quantum Quackery Virtual Atelier Architecture

## Layer Boundaries

1. `apps/atelier-desktop`
- Electron host + React UI.
- No direct kernel calls.
- Talks to `apps/atelier-api` only.

2. `apps/atelier-api`
- Business infrastructure and API boundary.
- Enforces actor/capability gating.
- Uses `KernelClient` adapter only.

3. `services/kernel-gateway` (optional)
- Strict allowlist proxy for kernel actions.
- Rejects unknown actions.

4. Kernel (external dependency)
- Source of structural causality.
- Must remain append-only and deterministic.

## Non-Negotiables

- No direct CEG writes from desktop/API/gateway.
- No auto-attestation.
- No semantic inference in tooling layers.
- No hidden side-effects; all kernel actions are explicit and auditable.

## Ambroflow Placement

- Ambroflow shim execution lives in `apps/atelier-api` (server-side boundary).
- Djinn Viewer (Electron/React) remains a client emitter/observer surface only.
- Viewer never calls kernel directly and never holds authority over commitments.

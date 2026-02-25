# Quantum Quackery Virtual Atelier

Hybrid app scaffold with strict kernel boundaries.

## Layout

- `apps/atelier-api`: FastAPI business/API layer
- `apps/atelier-desktop`: Electron + React shell
- `services/kernel-gateway`: optional kernel-facing adapter service
- `qqva/`: shared structural shim/projection primitives

## Boundary Rules

- No direct CEG mutation.
- No auto-attestation.
- No semantic inference in UI/API/gateway.
- Kernel interactions only through explicit allowlisted calls.

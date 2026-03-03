# Quantum Quackery Virtual Atelier

Production workspace with strict kernel boundaries.

## Active Production

This repo is now dedicated to holding productions for:

**Ko's Labyrnth, An Alchemist's Labor of Love**

Canonical production root:

- `productions/kos-labyrnth/`

## Layout

- `apps/atelier-api`: FastAPI business/API layer
- `apps/atelier-desktop`: Electron + React shell
- `services/kernel-gateway`: optional kernel-facing adapter service
- `qqva/`: shared structural shim/projection primitives
- `productions/kos-labyrnth/`: game production assets, plans, and deliverables

## Boundary Rules

- No direct CEG mutation.
- No auto-attestation.
- No semantic inference in UI/API/gateway.
- Kernel interactions only through explicit allowlisted calls.

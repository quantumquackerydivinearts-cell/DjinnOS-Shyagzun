# Atelier Example Pack

This folder contains runnable starter examples for Atelier.

## Contents

- `cobra/intro_scene.cobra`
- `cobra/market_stall.cobra`
- `payloads/dialogue_market_intro.json`
- `payloads/scene_graph_lapidus_market.json`
- `payloads/vitriol_apply_trial.json`
- `payloads/combat_round_r7.json`
- `payloads/alchemy_focus_tonic.json`
- `payloads/progression_chain.json`

## Usage Notes

- Cobra files are for Studio Hub script import and entity placement workflows.
- JSON payload files are for API calls from Renderer Lab rule panels or direct HTTP calls.
- `progression_chain.json` is an orchestration example showing sequence.

## Rule of Operation

It is close to "define it and use it", but strict:

1. Payload must match the endpoint schema.
2. Required capabilities/role/admin gate must be present for mutating routes.
3. Behavior is explicit; no hidden semantic inference.

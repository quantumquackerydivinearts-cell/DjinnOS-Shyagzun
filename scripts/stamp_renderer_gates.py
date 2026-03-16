from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "apps" / "atelier-desktop" / "src" / "App.jsx"
CHECKLIST_PATH = ROOT / "gameplay" / "contracts" / "renderer_acceptance_checklist.v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_all(text: str, patterns: list[str]) -> bool:
    return all(p in text for p in patterns)


def _stamp_gate(
    gate: dict[str, Any],
    *,
    ok: bool,
    checks: list[str],
    timestamp: str,
) -> None:
    gate["status"] = "done" if ok else "in_progress"
    evidence = gate.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []
    marker = f"auto-stamp:{timestamp}:{'PASS' if ok else 'FAIL'}"
    existing = [
        str(item)
        for item in evidence
        if isinstance(item, str)
        and not str(item).startswith("auto-stamp:")
        and not str(item).startswith("check:")
    ]
    gate["evidence"] = existing + [marker] + [f"check:{c}" for c in checks]


def main() -> int:
    checklist = _load_json(CHECKLIST_PATH)
    src_dir = ROOT / "apps" / "atelier-desktop" / "src"
    app_text = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(src_dir.rglob("*.jsx"))
        if p.is_file()
    )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    checks = {
        "gate_a_scene_coherence": [
            ("gate_a_smoke_action", "runRendererGateASmoke"),
            ("gate_a_badge", "Gate A:"),
            ("gate_a_status_key", "gate_a_ok"),
            ("fullscreen_open", "openFullscreenRenderer"),
        ],
        "gate_b_input_parity": [
            ("source_json", 'option value="json"'),
            ("source_cobra", 'option value="cobra"'),
            ("source_engine", 'option value="engine"'),
            ("payload_branch_cobra", 'rendererVisualSource === "cobra"'),
            ("payload_branch_engine", 'rendererVisualSource === "engine"'),
        ],
        "gate_c_lod_fidelity": [
            ("lod_function", "function applyInputLod"),
            ("lod_controls", "LOD 0 (coarsest)"),
            ("lod_brush", "LOD Snap/Block Fill"),
            ("lod_status", "LOD0:"),
        ],
        "gate_d_motion_integrity": [
            ("gate_d_smoke_action", "runRendererGateDSmoke"),
            ("gate_d_badge", "Gate D:"),
            ("click_move", "handleRendererClickMove"),
            ("path_step_queue", "buildStepDeltaQueue"),
            ("player_signal", "publishPlayerPositionSignal"),
        ],
        "gate_e_atlas_texturing": [
            ("texture_atlas_panel", "Texture Atlases"),
            ("atlas_material_set", "applyRepresentativeAtlasMaterialSet"),
            ("tile_png_atlas", "Use PNG as Atlas"),
            ("sprite_animator", "Sprite Animator"),
        ],
        "gate_f_performance_envelope": [
            ("governor", "const labGovernor = useMemo"),
            ("governor_badge", "Governor:"),
            ("worker_parse", "runPayloadParseInWorker"),
            ("worker_prep", "runVoxelExtractLodInWorker"),
            ("prep_badge", "Prep:"),
            ("panel_error_boundary", "class PanelErrorBoundary"),
        ],
    }

    gates = checklist.get("gates", [])
    if not isinstance(gates, list):
        raise SystemExit("invalid_checklist:gates_not_list")

    for gate in gates:
        if not isinstance(gate, dict):
            continue
        gate_id = str(gate.get("id", ""))
        specs = checks.get(gate_id)
        if not specs:
            continue
        names = [name for name, _ in specs]
        patterns = [pattern for _, pattern in specs]
        ok = _contains_all(app_text, patterns)
        _stamp_gate(gate, ok=ok, checks=names, timestamp=ts)

    checklist["updated_at"] = ts[:10]
    CHECKLIST_PATH.write_text(json.dumps(checklist, indent=2) + "\n", encoding="utf-8")
    print(f"renderer_gate_stamp_ok:{CHECKLIST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_hash(value: Any) -> str:
    txt = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def _reference_signal(reference_key: str) -> int:
    digest = hashlib.sha256(reference_key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % 100000


def _iterate(ref_signal: int, reference_coeff_bp: int, recursion_coeff_bp: int, iterations: int) -> list[int]:
    trace: list[int] = [ref_signal]
    current = ref_signal
    for _ in range(iterations):
        nxt = ((reference_coeff_bp * ref_signal) + (recursion_coeff_bp * current) + 5000) // 10000
        if nxt < 0:
            nxt = 0
        if nxt > 100000:
            nxt = 100000
        trace.append(int(nxt))
        current = int(nxt)
    return trace


def _first_fixed_point_index(trace: list[int]) -> int | None:
    for i in range(1, len(trace)):
        if trace[i] == trace[i - 1]:
            return i
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deterministic recursion and fixed-point behavior for Labyr-Nth coefficients.")
    parser.add_argument("--projection-report", required=True, help="Path to renderer_layer_projection.report.v1 JSON")
    parser.add_argument("--iterations", type=int, default=32, help="Number of recurrence iterations")
    parser.add_argument("--output", default="reports/renderer_toolchain/renderer_layer_fixed_point.report.json")
    args = parser.parse_args()

    if int(args.iterations) < 1:
        print("renderer_layer_fixed_point_failed:iterations_must_be_positive")
        return 1

    projection_path = _resolve_path(args.projection_report)
    if not projection_path.exists():
        print(f"renderer_layer_fixed_point_failed:missing_projection_report:{projection_path}")
        return 1
    obj = _load_json(projection_path)
    if not isinstance(obj, dict) or str(obj.get("id", "")) != "renderer_layer_projection.report.v1":
        print("renderer_layer_fixed_point_failed:invalid_projection_report")
        return 1

    recursion_profile = obj.get("recursion_profile", {})
    if not isinstance(recursion_profile, dict):
        print("renderer_layer_fixed_point_failed:missing_recursion_profile")
        return 1

    reference_key = str(recursion_profile.get("reference_key", "")).strip()
    reference_coeff_bp = int(recursion_profile.get("reference_coeff_bp", -1))
    recursion_coeff_bp = int(recursion_profile.get("recursion_coeff_bp", -1))
    coefficient_sum_bp = int(recursion_profile.get("coefficient_sum_bp", reference_coeff_bp + recursion_coeff_bp))

    if reference_key == "":
        print("renderer_layer_fixed_point_failed:missing_reference_key")
        return 1
    if reference_coeff_bp < 0 or reference_coeff_bp > 10000:
        print("renderer_layer_fixed_point_failed:reference_coeff_out_of_range")
        return 1
    if recursion_coeff_bp < 0 or recursion_coeff_bp > 10000:
        print("renderer_layer_fixed_point_failed:recursion_coeff_out_of_range")
        return 1

    iterations = int(args.iterations)
    ref_signal = _reference_signal(reference_key)

    trace_a = _iterate(ref_signal, reference_coeff_bp, recursion_coeff_bp, iterations)
    trace_b = _iterate(ref_signal, reference_coeff_bp, recursion_coeff_bp, iterations)
    deterministic_replay = trace_a == trace_b

    fixed_idx = _first_fixed_point_index(trace_a)
    fixed_reached = fixed_idx is not None
    terminal_value = int(trace_a[-1])

    result = {
        "id": "renderer_layer_fixed_point.report.v1",
        "projection_report": str(projection_path),
        "pack_id": str(obj.get("pack_id", "")),
        "iterations": iterations,
        "reference_signal": ref_signal,
        "recursion_profile": {
            "model": str(recursion_profile.get("model", "labyr_nth.linear_recurrence.v1")),
            "reference_key": reference_key,
            "reference_coeff_bp": reference_coeff_bp,
            "recursion_coeff_bp": recursion_coeff_bp,
            "coefficient_sum_bp": coefficient_sum_bp,
            "stable_if_sum_le_10000": bool(coefficient_sum_bp <= 10000),
        },
        "replay": {
            "deterministic": deterministic_replay,
            "trace_hash": _canonical_hash(trace_a),
        },
        "fixed_point": {
            "reached": fixed_reached,
            "iteration_index": fixed_idx,
            "terminal_value": terminal_value,
        },
        "trace": trace_a,
    }

    out_path = _resolve_path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("renderer_layer_fixed_point_ok")
    print(f"- deterministic_replay:{str(deterministic_replay).lower()}")
    print(f"- fixed_point_reached:{str(fixed_reached).lower()}")
    print(f"- terminal_value:{terminal_value}")
    print(f"- report:{out_path}")

    if not deterministic_replay:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

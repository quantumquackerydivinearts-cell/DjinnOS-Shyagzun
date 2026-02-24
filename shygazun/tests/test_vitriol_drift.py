from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from shygazun.kernel.constants.vitriol import VITRIOL_LETTERS
from shygazun.kernel.policy.vitriol_drift import (
    compute_vitriol_vector,
    fractal_step,
    vitriol_vector_strings,
)
from shygazun.kernel.types.events import AttestationEventObj, KernelEventObj, PlacementEventObj


def _placement(idx: int) -> PlacementEventObj:
    return {
        "id": f"evt_p_{idx}",
        "kind": "placement",
        "utterance": {"raw": str(idx)},
        "context": {},
        "delta": {},
        "at": {"tick": idx, "causal_epoch": "E0"},
    }


def _attestation(idx: int) -> AttestationEventObj:
    return {
        "id": f"evt_a_{idx}",
        "kind": "attestation",
        "witness_id": "agent-1",
        "attestation_kind": "commitment",
        "attestation_tag": None,
        "payload": {},
        "target": {
            "frontier_id": "F0",
            "candidate_id": "rose.link.alpha",
        },
        "at": {"tick": idx, "causal_epoch": "E0"},
    }


def test_fractal_step_quantized() -> None:
    out = fractal_step(Decimal("0"))
    assert out == Decimal("7.000000000000")


def test_compute_vitriol_vector_replay_deterministic() -> None:
    events: List[KernelEventObj] = [_placement(1), _placement(2), _attestation(3)]
    left = compute_vitriol_vector(events)
    right = compute_vitriol_vector(events)
    assert left == right


def test_compute_vitriol_vector_pure_function() -> None:
    events: List[KernelEventObj] = [_placement(1), _placement(2)]
    base = compute_vitriol_vector(events)

    events_again: List[KernelEventObj] = [_placement(1), _placement(2)]
    replay = compute_vitriol_vector(events_again)
    assert base == replay


def test_placement_azoth_index_advances_canonical_letters() -> None:
    events: List[KernelEventObj] = [_placement(i + 1) for i in range(7)]
    vector = compute_vitriol_vector(events)

    for letter in VITRIOL_LETTERS:
        assert vector[letter] == Decimal("7.000000000000")


def test_vitriol_vector_strings_stable_order() -> None:
    events: List[KernelEventObj] = [_placement(1)]
    vector = compute_vitriol_vector(events)
    stable: Dict[str, str] = vitriol_vector_strings(vector)

    assert list(stable.keys()) == list(VITRIOL_LETTERS)
    assert stable["Vitality"] == "7.000000000000"

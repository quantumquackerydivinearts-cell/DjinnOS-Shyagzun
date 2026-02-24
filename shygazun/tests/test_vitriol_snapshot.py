from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from shygazun.kernel.constants.vitriol import VITRIOL_LETTERS
from shygazun.kernel.policy.vitriol_cache import (
    DEFAULT_C,
    DEFAULT_QUANTIZE_DP,
    VitriolSnapshot,
    canonical_json,
    compute_from_events,
    load_or_recompute,
    make_snapshot,
    verify_snapshot,
)
from shygazun.kernel.types.events import KernelEventObj, PlacementEventObj


def _placement(idx: int) -> PlacementEventObj:
    return {
        "id": f"evt_{idx}",
        "kind": "placement",
        "utterance": {"raw": str(idx)},
        "context": {},
        "delta": {},
        "at": {"tick": idx, "causal_epoch": "E0"},
    }


def _zero_vector() -> Dict[str, Decimal]:
    return {letter: Decimal("0") for letter in VITRIOL_LETTERS}


def test_snapshot_verify_and_incremental_equals_full_recompute() -> None:
    events: List[KernelEventObj] = [_placement(1), _placement(2), _placement(3), _placement(4)]

    full_vector, full_azoth, _ = compute_from_events(
        events,
        0,
        _zero_vector(),
        0,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )

    partial_vector, partial_azoth, partial_anchor_id = compute_from_events(
        events[:2],
        0,
        _zero_vector(),
        0,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )
    snapshot = make_snapshot(
        partial_vector,
        partial_azoth,
        partial_anchor_id,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )
    assert verify_snapshot(snapshot, events)

    restored_vector, restored_azoth, start_index = load_or_recompute(snapshot, events)
    resumed_vector, resumed_azoth, _ = compute_from_events(
        events,
        start_index,
        restored_vector,
        restored_azoth,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )

    assert resumed_vector == full_vector
    assert resumed_azoth == full_azoth


def test_snapshot_invalid_anchor_forces_recompute_from_zero() -> None:
    events: List[KernelEventObj] = [_placement(1), _placement(2)]
    vector, azoth, anchor_event_id = compute_from_events(
        events,
        0,
        _zero_vector(),
        0,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )
    snapshot = make_snapshot(vector, azoth, anchor_event_id, DEFAULT_C, DEFAULT_QUANTIZE_DP)

    tampered = VitriolSnapshot(
        schema_version=snapshot.schema_version,
        c=snapshot.c,
        quantize_dp=snapshot.quantize_dp,
        azoth_index=snapshot.azoth_index,
        anchor_event_id=snapshot.anchor_event_id,
        anchor_hash="h_broken",
        vector=dict(snapshot.vector),
    )

    restored_vector, restored_azoth, start_index = load_or_recompute(tampered, events)
    assert start_index == 0
    assert restored_azoth == 0
    assert restored_vector == _zero_vector()


def test_snapshot_vector_serializes_as_fixed_decimal_strings() -> None:
    events: List[KernelEventObj] = [_placement(1)]
    vector, azoth, anchor = compute_from_events(
        events,
        0,
        _zero_vector(),
        0,
        DEFAULT_C,
        DEFAULT_QUANTIZE_DP,
    )
    snapshot = make_snapshot(vector, azoth, anchor, DEFAULT_C, DEFAULT_QUANTIZE_DP)
    encoded = canonical_json(snapshot.to_json_obj())

    assert "\"Vitality\":\"7.000000000000\"" in encoded
    assert "\"quantize_dp\":12" in encoded

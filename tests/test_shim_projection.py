from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qqva.ambroflow_shim import AmbroflowLine, AmbroflowShim
from qqva.projection import build_projection
from qqva.types import EdgeObj, FrontierObj, KernelEventObj, ObserveResult, PlaceResult


class FakePort:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def place_line(self, raw: str, *, context: Optional[Dict[str, Any]] = None) -> PlaceResult:
        self.calls.append({"raw": raw, "context": context})
        return {
            "field_id": "F0",
            "clock": {"tick": 1, "causal_epoch": "0"},
            "placement_event": {"id": "evt_1", "kind": "placement", "at": {"tick": 1, "causal_epoch": "0"}},
            "observe": {},
        }

    def observe(self) -> ObserveResult:
        return {
            "field_id": "F0",
            "clock": {"tick": 2, "causal_epoch": "0"},
            "candidates_by_frontier": {},
            "eligible_by_frontier": {},
            "eligibility_events": [],
            "refusals": [{"reason_code": "await-lotus"}],
        }

    def get_frontiers(self) -> Sequence[FrontierObj]:
        return [
            {"id": "B", "event_ids": [], "status": "active", "inconsistency_proof": None},
            {"id": "A", "event_ids": [], "status": "active", "inconsistency_proof": None},
        ]

    def get_timeline(self, last: Optional[int] = None) -> Sequence[KernelEventObj]:
        return [{"id": "evt_1", "kind": "placement", "at": {"tick": 1, "causal_epoch": "0"}}]

    def get_edges(self) -> Sequence[EdgeObj]:
        return [{"from_event": "evt_1", "to_event": "evt_2", "type": "conflicts", "metadata": {}}]

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> KernelEventObj:
        return {"id": "evt_att", "kind": "attestation", "at": {"tick": 2, "causal_epoch": "0"}}


def test_shim_places_with_structural_context() -> None:
    port = FakePort()
    shim = AmbroflowShim(port)
    shim.place_line("hello", scene_id="s1", tags={"tone": "flat"}, metadata={"x": 1})
    context = port.calls[0]["context"]
    assert context["speaker_id"] == "player"
    assert context["scene_id"] == "s1"
    assert context["tags"] == {"tone": "flat"}


def test_batch_order_preserved() -> None:
    port = FakePort()
    shim = AmbroflowShim(port)
    lines = [
        AmbroflowLine(raw="a", speaker_id="p1", scene_id=None, tags={}, metadata={}),
        AmbroflowLine(raw="b", speaker_id="p1", scene_id=None, tags={}, metadata={}),
    ]
    shim.place_batch(lines)
    assert [c["raw"] for c in port.calls] == ["a", "b"]


def test_projection_frontiers_sorted_by_id() -> None:
    port = FakePort()
    projection = build_projection(port)
    assert [f["id"] for f in projection["frontiers"]] == ["A", "B"]


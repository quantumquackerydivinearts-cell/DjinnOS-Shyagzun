from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qqva.ambroflow_shim import AmbroflowLine, AmbroflowShim
from qqva.types import ObserveResult, PlaceResult


class FakePort:
    def __init__(self) -> None:
        self.place_calls = 0
        self.attest_calls = 0

    def place_line(self, raw: str, *, context: Optional[Dict[str, Any]] = None) -> PlaceResult:
        self.place_calls += 1
        return {"placement_event": {"id": f"evt_{self.place_calls}"}, "observe": {}}

    def observe(self) -> ObserveResult:
        return {
            "clock": {"tick": 1, "causal_epoch": "0"},
            "candidates_by_frontier": {},
            "eligible_by_frontier": {},
            "eligibility_events": [],
            "refusals": [],
        }

    def get_frontiers(self) -> Sequence[Dict[str, Any]]:
        return []

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.attest_calls += 1
        return {"id": "evt_att"}


def test_ambroflow_shim_does_not_attest_on_emit() -> None:
    port = FakePort()
    shim = AmbroflowShim(port)
    lines = [
        AmbroflowLine(raw="entity a 1 1 marker", speaker_id="tester", scene_id="s1", tags={}, metadata={}),
        AmbroflowLine(raw="entity b 2 2 marker", speaker_id="tester", scene_id="s1", tags={}, metadata={}),
    ]
    shim.place_batch(lines)
    assert port.place_calls == 2
    assert port.attest_calls == 0

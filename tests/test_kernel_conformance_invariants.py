from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
KERNEL_ROOT = ROOT / "DjinnOS-Shyagzun"
sys.path.insert(0, str(KERNEL_ROOT))

from shygazun.kernel_service import app as kernel_app  # type: ignore[import]


def test_replay_canonical_is_deterministic() -> None:
    client = TestClient(kernel_app)
    bundle = {
        "field_id": "F0",
        "placements": [
            {"raw": "entity a 1 1 marker", "context": {"scene_id": "s1"}},
            {"raw": "entity b 2 2 marker", "context": {"scene_id": "s1"}},
        ],
        "attestations": [],
        "metadata": {"note": "determinism"},
    }
    first = client.post("/v0.1/replay", json={"bundle": bundle})
    second = client.post("/v0.1/replay", json={"bundle": bundle})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_request_commit_is_structural_noop() -> None:
    client = TestClient(kernel_app)
    before_events = client.get("/events")
    assert before_events.status_code == 200
    before_count = len(before_events.json())

    res = client.post(
        "/v0.1/request_commit",
        json={"field_id": "F0", "frontier_id": "F0", "candidate_id": "candidate_1"},
    )
    assert res.status_code == 200

    after_events = client.get("/events")
    assert after_events.status_code == 200
    after_count = len(after_events.json())
    assert before_count == after_count

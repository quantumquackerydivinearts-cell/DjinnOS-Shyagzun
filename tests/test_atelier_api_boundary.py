from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.main import app, _kernel_client  # type: ignore[import]
from atelier_api.types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse  # type: ignore[import]


class FakeKernelClient:
    def __init__(self) -> None:
        self.place_calls = 0
        self.attest_calls = 0

    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        self.place_calls += 1
        return {"ok": True, "raw": raw, "context": dict(context or {})}

    def observe(self) -> ObserveResponse:
        return {
            "field_id": "F0",
            "clock": {"tick": 1, "causal_epoch": "0"},
            "candidates_by_frontier": {},
            "eligible_by_frontier": {},
            "eligibility_events": [],
            "refusals": [],
        }

    def events(self) -> Sequence[KernelEventObj]:
        return [{"id": "evt_1", "kind": "placement", "at": {"tick": 1, "causal_epoch": "0"}}]

    def edges(self) -> Sequence[EdgeObj]:
        return []

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.attest_calls += 1
        return {"id": "evt_att", "kind": "attestation"}

    def frontiers(self) -> Sequence[FrontierObj]:
        return [{"id": "F0", "event_ids": [], "status": "active", "inconsistency_proof": None}]


def _admin_gate_token(actor_id: str, workshop_id: str) -> str:
    payload = f"STEWARD_DEV_GATE:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _headers(caps: str, role: str = "artisan", token: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "X-Atelier-Actor": "tester",
        "X-Atelier-Capabilities": caps,
        "X-Artisan-Id": "artisan-1",
        "X-Artisan-Role": role,
        "X-Workshop-Id": "workshop-1",
        "X-Workshop-Scopes": "scene:*,workspace:*",
    }
    if token is not None:
        headers["X-Admin-Gate-Token"] = token
    return headers


def test_requires_actor_header() -> None:
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {}},
        headers={
            "X-Artisan-Id": "artisan-1",
            "X-Artisan-Role": "artisan",
            "X-Workshop-Id": "workshop-1",
            "X-Workshop-Scopes": "scene:*,workspace:*",
        },
    )
    assert res.status_code == 401


def test_forbidden_without_place_capability() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post("/v1/atelier/place", json={"raw": "x", "context": {}}, headers=_headers("kernel.observe"))
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_place_requires_verified_admin_gate() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "s1"}},
        headers=_headers("kernel.place", role="steward"),
    )
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_place_succeeds_for_steward_with_gate_token() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "s1"}},
        headers=_headers("kernel.place", role="steward", token=token),
    )
    assert res.status_code == 200
    assert fake.place_calls == 1
    assert fake.attest_calls == 0
    app.dependency_overrides.clear()


def test_place_denied_when_scene_not_in_scope() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "restricted"}},
        headers={
            "X-Atelier-Actor": "tester",
            "X-Atelier-Capabilities": "kernel.place",
            "X-Artisan-Id": "artisan-1",
            "X-Artisan-Role": "steward",
            "X-Workshop-Id": "workshop-1",
            "X-Workshop-Scopes": "scene:allowed,workspace:*",
            "X-Admin-Gate-Token": token,
        },
    )
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_artisan_cannot_attest_by_role() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/attest",
        json={
            "witness_id": "w1",
            "attestation_kind": "recognition",
            "attestation_tag": None,
            "payload": {},
            "target": {},
        },
        headers=_headers("kernel.attest"),
    )
    assert res.status_code == 403
    assert fake.attest_calls == 0
    app.dependency_overrides.clear()


def test_senior_artisan_can_attest() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    headers = _headers("kernel.attest")
    headers["X-Artisan-Role"] = "senior_artisan"
    res = client.post(
        "/v1/atelier/attest",
        json={
            "witness_id": "w1",
            "attestation_kind": "recognition",
            "attestation_tag": None,
            "payload": {},
            "target": {},
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert fake.attest_calls == 1
    app.dependency_overrides.clear()


def test_admin_gate_verify_requires_steward_and_valid_code() -> None:
    client = TestClient(app)
    not_steward = client.post(
        "/v1/atelier/admin/gate/verify",
        json={"gate_code": "STEWARD_DEV_GATE"},
        headers=_headers("kernel.place", role="artisan"),
    )
    assert not_steward.status_code == 403

    ok = client.post(
        "/v1/atelier/admin/gate/verify",
        json={"gate_code": "STEWARD_DEV_GATE"},
        headers=_headers("kernel.place", role="steward"),
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["verified_admin"] is True
    assert payload["required_role"] == "steward"
    assert isinstance(payload["admin_gate_token"], str)

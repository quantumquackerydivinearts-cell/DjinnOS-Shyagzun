from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import requests

from qqva.kernel_landing_port import HttpKernelLandingPort


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_verify_gate_then_place_uses_admin_token(monkeypatch: Any) -> None:
    calls: list[Dict[str, Any]] = []

    def fake_request(
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Mapping[str, Any]] = None,
        timeout: int = 20,
    ) -> _FakeResponse:
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "json": dict(json or {}),
                "timeout": timeout,
            }
        )
        if url.endswith("/v1/atelier/admin/gate/verify"):
            return _FakeResponse(
                200,
                {
                    "verified_admin": True,
                    "required_role": "steward",
                    "admin_gate_token": "tok_123",
                },
            )
        if url.endswith("/v1/atelier/place"):
            return _FakeResponse(
                200,
                {
                    "field_id": "F0",
                    "clock": {"tick": 1, "causal_epoch": "0"},
                    "placement_event": {"id": "evt_1", "kind": "placement", "at": {"tick": 1}},
                    "observe": {},
                },
            )
        raise AssertionError(f"unexpected URL:{url}")

    monkeypatch.setattr(requests, "request", fake_request)

    port = HttpKernelLandingPort(
        base_url="http://127.0.0.1:9000",
        actor_id="desktop-user",
        artisan_id="kael-001",
        role="steward",
        workshop_id="workshop-primary",
    )

    assert port.verify_admin_gate("STEWARD_DEV_GATE") is True
    port.place_line("hello")

    place_call = calls[1]
    assert place_call["headers"]["X-Admin-Gate-Token"] == "tok_123"


def test_semantic_value_is_structural_observe_projection(monkeypatch: Any) -> None:
    def fake_request(
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Mapping[str, Any]] = None,
        timeout: int = 20,
    ) -> _FakeResponse:
        _ = method, headers, json, timeout
        if not url.endswith("/v1/atelier/observe"):
            raise AssertionError(f"unexpected URL:{url}")
        return _FakeResponse(
            200,
            {
                "field_id": "F0",
                "clock": {"tick": 9, "causal_epoch": "0"},
                "candidates_by_frontier": {"fr_1": [{"id": "c1"}]},
                "eligible_by_frontier": {"fr_1": [{"id": "c1"}]},
                "eligibility_events": [],
                "refusals": [{"reason_code": "await-lotus"}],
            },
        )

    monkeypatch.setattr(requests, "request", fake_request)

    port = HttpKernelLandingPort(
        base_url="http://127.0.0.1:9000",
        actor_id="desktop-user",
        artisan_id="kael-001",
        role="steward",
        workshop_id="workshop-primary",
    )

    value = port.semantic_value()
    assert value["clock"]["tick"] == 9
    assert list(value["candidates_by_frontier"].keys()) == ["fr_1"]
    assert value["refusals"][0]["reason_code"] == "await-lotus"


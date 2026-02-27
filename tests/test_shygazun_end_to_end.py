from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence, cast

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
KERNEL_ROOT = ROOT / "DjinnOS-Shyagzun"
ATELIER_API_ROOT = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(KERNEL_ROOT))
sys.path.insert(0, str(ATELIER_API_ROOT))

from shygazun.kernel_service import app as kernel_app  # type: ignore[import]
from atelier_api.main import app as atelier_app, _kernel_client  # type: ignore[import]
from qqva.shygazun_compiler import cobra_to_placement_payloads  # type: ignore[import]
from atelier_api.kernel_client import KernelClient  # type: ignore[import]
from atelier_api.types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse  # type: ignore[import]


class KernelBridgeClient(KernelClient):
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        response = self._client.post("/place", json={"raw": raw, "context": dict(context or {})})
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        return cast(Mapping[str, Any], payload)

    def observe(self) -> ObserveResponse:
        response = self._client.post("/observe", json={})
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        return cast(ObserveResponse, payload)

    def events(self) -> Sequence[KernelEventObj]:
        response = self._client.get("/events")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        return cast(Sequence[KernelEventObj], payload)

    def edges(self) -> Sequence[EdgeObj]:
        response = self._client.get("/edges")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        return cast(Sequence[EdgeObj], payload)

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        response = self._client.post(
            "/attest",
            json={
                "witness_id": witness_id,
                "attestation_kind": attestation_kind,
                "attestation_tag": attestation_tag,
                "payload": dict(payload),
                "target": dict(target),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        return cast(Mapping[str, Any], body)

    def frontiers(self) -> Sequence[FrontierObj]:
        observed = self.observe()
        frontiers_obj = observed.get("frontiers")
        if not isinstance(frontiers_obj, list):
            return []
        return cast(Sequence[FrontierObj], frontiers_obj)

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
    ) -> Mapping[str, Any]:
        response = self._client.post(
            "/v0.1/akinenwun/lookup",
            json={"akinenwun": akinenwun, "mode": mode, "ingest": ingest},
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, dict)
        return cast(Mapping[str, Any], payload)


def _headers() -> Dict[str, str]:
    return {
        "X-Atelier-Actor": "tester",
        "X-Atelier-Capabilities": "kernel.observe",
        "X-Artisan-Id": "artisan-1",
        "X-Artisan-Role": "artisan",
        "X-Workshop-Id": "workshop-1",
        "X-Workshop-Scopes": "scene:*,workspace:*",
    }


def test_kernel_akinenwun_lookup_is_deterministic_and_rejects_spaced_word() -> None:
    client = TestClient(kernel_app)

    first = client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": True},
    )
    second = client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": False},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["frontier_hash"] == second_payload["frontier_hash"]

    spaced = client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "Ty KoWuVu", "mode": "prose", "ingest": False},
    )
    assert spaced.status_code == 400
    assert "must not contain spaces" in spaced.json()["detail"]


def test_atelier_ambroflow_lookup_matches_kernel_surface_hash() -> None:
    kernel_client = TestClient(kernel_app)
    bridge = KernelBridgeClient(kernel_client)
    atelier_app.dependency_overrides[_kernel_client] = lambda: bridge

    client = TestClient(atelier_app)
    response = client.post(
        "/v1/ambroflow/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": False},
        headers=_headers(),
    )
    assert response.status_code == 200
    atelier_payload = response.json()

    kernel_response = kernel_client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": False},
    )
    assert kernel_response.status_code == 200
    kernel_payload = kernel_response.json()
    assert atelier_payload["frontier_hash"] == kernel_payload["frontier_hash"]
    assert atelier_payload["frontier"] == kernel_payload["frontier"]

    atelier_app.dependency_overrides.clear()


def test_cobra_to_placement_payloads_carries_shygazun_ir() -> None:
    source = "\n".join(
        [
            "entity demo_gate 4 7 portal",
            "  lex TyKoWuVu",
            "  layer foreground",
        ]
    )
    payloads = cobra_to_placement_payloads(source, scene_id="lab", workspace_id="main")
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["raw"] == "entity demo_gate 4 7 portal"
    context = payload["context"]
    ir = context["shygazun_ir"]
    assert ir["canonical_compound"] == "TyKoWuVu"
    assert ir["unresolved"] == []
    assert [symbol["symbol"] for symbol in ir["symbols"]] == ["Ty", "Ko", "Wu", "Vu"]

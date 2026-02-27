from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, cast

import requests

from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResult, PlaceResult


@dataclass
class HttpKernelLandingPort:
    """
    Transport-only landing port for Ambroflow -> Atelier API -> Kernel.
    """

    base_url: str
    actor_id: str
    artisan_id: str
    role: str
    workshop_id: str
    workshop_scopes: Sequence[str] = ("scene:*", "workspace:*")
    _admin_gate_token: Optional[str] = field(default=None, init=False, repr=False)

    def _capabilities_csv(self) -> str:
        return ",".join(
            (
                "kernel.place",
                "kernel.observe",
                "kernel.timeline",
                "kernel.frontiers",
                "kernel.edges",
                "kernel.attest",
            )
        )

    def _headers(self, *, include_gate_token: bool) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "X-Atelier-Actor": self.actor_id,
            "X-Atelier-Capabilities": self._capabilities_csv(),
            "X-Artisan-Id": self.artisan_id,
            "X-Artisan-Role": self.role,
            "X-Workshop-Id": self.workshop_id,
            "X-Workshop-Scopes": ",".join(self.workshop_scopes),
        }
        if include_gate_token and self._admin_gate_token is not None:
            headers["X-Admin-Gate-Token"] = self._admin_gate_token
        return headers

    def _call_obj(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
        include_gate_token: bool = False,
    ) -> Mapping[str, Any]:
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=self._headers(include_gate_token=include_gate_token),
            json=dict(body) if body is not None else None,
            timeout=20,
        )
        if response.status_code != 200:
            raise RuntimeError(f"landing_port_http_error:{response.status_code}:{path}")
        payload: Any = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"landing_port_shape_error:{path}")
        return cast(Mapping[str, Any], payload)

    def _call_list(
        self,
        method: str,
        path: str,
        *,
        include_gate_token: bool = False,
    ) -> Sequence[Mapping[str, Any]]:
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=self._headers(include_gate_token=include_gate_token),
            timeout=20,
        )
        if response.status_code != 200:
            raise RuntimeError(f"landing_port_http_error:{response.status_code}:{path}")
        payload: Any = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"landing_port_shape_error:{path}")
        for item in payload:
            if not isinstance(item, dict):
                raise RuntimeError(f"landing_port_shape_error:{path}")
        return cast(Sequence[Mapping[str, Any]], payload)

    def verify_admin_gate(self, gate_code: str) -> bool:
        payload = self._call_obj(
            "POST",
            "/v1/atelier/admin/gate/verify",
            body={"gate_code": gate_code},
            include_gate_token=False,
        )
        token_obj = payload.get("admin_gate_token")
        if not isinstance(token_obj, str) or not token_obj:
            self._admin_gate_token = None
            return False
        self._admin_gate_token = token_obj
        verified_obj = payload.get("verified_admin")
        return bool(verified_obj)

    def admin_gate_status(self) -> Mapping[str, Any]:
        return self._call_obj(
            "GET",
            "/v1/atelier/admin/gate/status",
            include_gate_token=True,
        )

    def place_line(self, raw: str, *, context: Optional[Dict[str, Any]] = None) -> PlaceResult:
        result = self._call_obj(
            "POST",
            "/v1/atelier/place",
            body={"raw": raw, "context": dict(context or {})},
            include_gate_token=True,
        )
        return cast(PlaceResult, result)

    def observe(self) -> ObserveResult:
        result = self._call_obj(
            "POST",
            "/v1/atelier/observe",
            body={},
            include_gate_token=False,
        )
        return cast(ObserveResult, result)

    def get_frontiers(self) -> Sequence[FrontierObj]:
        result = self._call_list(
            "GET",
            "/v1/atelier/frontiers",
            include_gate_token=False,
        )
        return cast(Sequence[FrontierObj], result)

    def get_timeline(self, last: Optional[int] = None) -> Sequence[KernelEventObj]:
        path = "/v1/atelier/timeline"
        if last is not None:
            path = f"{path}?last={last}"
        result = self._call_list(
            "GET",
            path,
            include_gate_token=False,
        )
        return cast(Sequence[KernelEventObj], result)

    def get_edges(self) -> Sequence[EdgeObj]:
        result = self._call_list(
            "GET",
            "/v1/atelier/edges",
            include_gate_token=False,
        )
        return cast(Sequence[EdgeObj], result)

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> KernelEventObj:
        result = self._call_obj(
            "POST",
            "/v1/atelier/attest",
            body={
                "witness_id": witness_id,
                "attestation_kind": attestation_kind,
                "attestation_tag": attestation_tag,
                "payload": dict(payload),
                "target": dict(target),
            },
            include_gate_token=False,
        )
        return cast(KernelEventObj, result)

    def semantic_value(self) -> Mapping[str, Any]:
        """
        Structural semantic value derived from kernel outputs only.
        """
        observed = self.observe()
        return {
            "clock": observed["clock"],
            "candidates_by_frontier": observed["candidates_by_frontier"],
            "eligible_by_frontier": observed["eligible_by_frontier"],
            "refusals": observed["refusals"],
        }


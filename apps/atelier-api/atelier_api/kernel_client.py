from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, cast

import requests

from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


class KernelClient(Protocol):
    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...

    def observe(self) -> ObserveResponse: ...

    def events(self) -> Sequence[KernelEventObj]: ...

    def edges(self) -> Sequence[EdgeObj]: ...

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def frontiers(self) -> Sequence[FrontierObj]: ...

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
        policy: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def validate_wand_damage_attestation(
        self,
        *,
        wand_id: str,
        notifier_id: str,
        damage_state: str,
        event_tag: Optional[str],
        media: Sequence[Mapping[str, Any]],
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


@dataclass
class HttpKernelClient:
    base_url: str

    def _call(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.request(method=method, url=url, json=dict(body) if body is not None else None, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"kernel_http_error:{resp.status_code}:{path}")
        data: Any = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"kernel_http_shape_error:{path}")
        return cast(Mapping[str, Any], data)

    def _call_list(self, method: str, path: str) -> Sequence[Mapping[str, Any]]:
        url = f"{self.base_url}{path}"
        resp = requests.request(method=method, url=url, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"kernel_http_error:{resp.status_code}:{path}")
        data: Any = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"kernel_http_shape_error:{path}")
        for item in data:
            if not isinstance(item, dict):
                raise RuntimeError(f"kernel_http_shape_error:{path}")
        return cast(Sequence[Mapping[str, Any]], data)

    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return self._call("POST", "/place", body={"raw": raw, "context": dict(context or {})})

    def observe(self) -> ObserveResponse:
        data = self._call("POST", "/observe", body={})
        return cast(ObserveResponse, data)

    def events(self) -> Sequence[KernelEventObj]:
        return cast(Sequence[KernelEventObj], self._call_list("GET", "/events"))

    def edges(self) -> Sequence[EdgeObj]:
        return cast(Sequence[EdgeObj], self._call_list("GET", "/edges"))

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        body: Dict[str, Any] = {
            "witness_id": witness_id,
            "attestation_kind": attestation_kind,
            "attestation_tag": attestation_tag,
            "payload": dict(payload),
            "target": dict(target),
        }
        return self._call("POST", "/attest", body=body)

    def frontiers(self) -> Sequence[FrontierObj]:
        observed = self.observe()
        frontiers_obj = observed.get("frontiers")
        if not isinstance(frontiers_obj, list):
            return []
        out: list[FrontierObj] = []
        for item in frontiers_obj:
            if isinstance(item, dict):
                out.append(cast(FrontierObj, item))
        return out

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
        policy: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return self._call(
            "POST",
            "/v0.1/akinenwun/lookup",
            body={"akinenwun": akinenwun, "mode": mode, "ingest": ingest, "policy": dict(policy)},
        )

    def validate_wand_damage_attestation(
        self,
        *,
        wand_id: str,
        notifier_id: str,
        damage_state: str,
        event_tag: Optional[str],
        media: Sequence[Mapping[str, Any]],
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return self._call(
            "POST",
            "/v0.1/wand/damage/validate",
            body={
                "wand_id": wand_id,
                "notifier_id": notifier_id,
                "damage_state": damage_state,
                "event_tag": event_tag,
                "media": [dict(item) for item in media],
                "payload": dict(payload),
            },
        )


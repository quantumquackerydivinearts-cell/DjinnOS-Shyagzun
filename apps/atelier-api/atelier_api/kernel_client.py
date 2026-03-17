from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, cast

import requests

from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


class KernelClient(Protocol):
    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...

    def observe(self) -> ObserveResponse: ...

    def health_status(self) -> Mapping[str, Any]: ...

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

    def field_create(self, *, field_id: str, owner_id: str) -> Mapping[str, Any]: ...

    def field_list(self) -> Mapping[str, Any]: ...

    def field_observe(self, field_id: str) -> ObserveResponse: ...

    def field_ceg(self, field_id: str) -> Mapping[str, Any]: ...

    def field_frontiers(self, field_id: str) -> Sequence[FrontierObj]: ...

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
    retry_attempts: int = 4
    retry_backoff_ms: int = 400

    def __post_init__(self) -> None:
        self.base_url = str(self.base_url or "").rstrip("/")
        self.retry_attempts = max(1, int(self.retry_attempts or 1))
        self.retry_backoff_ms = max(0, int(self.retry_backoff_ms or 0))

    def _sleep_backoff(self, attempt_index: int) -> None:
        if attempt_index <= 0 or self.retry_backoff_ms <= 0:
            return
        time.sleep((self.retry_backoff_ms * attempt_index) / 1000.0)

    def _call(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_attempts):
            try:
                resp = requests.request(method=method, url=url, json=dict(body) if body is not None else None, timeout=20)
                if resp.status_code == 200:
                    data: Any = resp.json()
                    if not isinstance(data, dict):
                        raise RuntimeError(f"kernel_http_shape_error:{path}")
                    return cast(Mapping[str, Any], data)
                if resp.status_code >= 500 and attempt + 1 < self.retry_attempts:
                    self._sleep_backoff(attempt + 1)
                    continue
                raise RuntimeError(f"kernel_http_error:{resp.status_code}:{path}")
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 >= self.retry_attempts:
                    raise RuntimeError(f"kernel_unreachable:{path}:{exc}") from exc
                self._sleep_backoff(attempt + 1)
        if last_error is not None:
            raise RuntimeError(f"kernel_unreachable:{path}:{last_error}") from last_error
        raise RuntimeError(f"kernel_http_error:unknown:{path}")

    def _call_list(self, method: str, path: str) -> Sequence[Mapping[str, Any]]:
        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_attempts):
            try:
                resp = requests.request(method=method, url=url, timeout=20)
                if resp.status_code == 200:
                    data: Any = resp.json()
                    if not isinstance(data, list):
                        raise RuntimeError(f"kernel_http_shape_error:{path}")
                    for item in data:
                        if not isinstance(item, dict):
                            raise RuntimeError(f"kernel_http_shape_error:{path}")
                    return cast(Sequence[Mapping[str, Any]], data)
                if resp.status_code >= 500 and attempt + 1 < self.retry_attempts:
                    self._sleep_backoff(attempt + 1)
                    continue
                raise RuntimeError(f"kernel_http_error:{resp.status_code}:{path}")
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 >= self.retry_attempts:
                    raise RuntimeError(f"kernel_unreachable:{path}:{exc}") from exc
                self._sleep_backoff(attempt + 1)
        if last_error is not None:
            raise RuntimeError(f"kernel_unreachable:{path}:{last_error}") from last_error
        raise RuntimeError(f"kernel_http_error:unknown:{path}")

    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return self._call("POST", "/place", body={"raw": raw, "context": dict(context or {})})

    def observe(self) -> ObserveResponse:
        data = self._call("POST", "/observe", body={})
        return cast(ObserveResponse, data)

    def health_status(self) -> Mapping[str, Any]:
        return self._call("GET", "/health")

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

    def field_create(self, *, field_id: str, owner_id: str) -> Mapping[str, Any]:
        return self._call("POST", "/v0.1/fields", body={"field_id": field_id, "owner_id": owner_id})

    def field_list(self) -> Mapping[str, Any]:
        return self._call("GET", "/v0.1/fields")

    def field_observe(self, field_id: str) -> ObserveResponse:
        data = self._call("POST", f"/v0.1/observe/{field_id}", body={})
        return cast(ObserveResponse, data)

    def field_ceg(self, field_id: str) -> Mapping[str, Any]:
        return self._call("GET", f"/v0.1/ceg/{field_id}")

    def field_frontiers(self, field_id: str) -> Sequence[FrontierObj]:
        data = self._call("GET", f"/v0.1/frontiers/{field_id}")
        frontiers_obj = data.get("frontiers")
        if not isinstance(frontiers_obj, list):
            return []
        return [cast(FrontierObj, item) for item in frontiers_obj if isinstance(item, dict)]


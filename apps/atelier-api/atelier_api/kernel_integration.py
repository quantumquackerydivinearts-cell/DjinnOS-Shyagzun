from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from .kernel_client import KernelClient
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


@dataclass(frozen=True)
class KernelInvocation:
    at: str
    action: str
    actor_id: str
    workshop_id: str


class KernelIntegrationService:
    def __init__(self, client: KernelClient) -> None:
        self._client = client
        self._audit: list[KernelInvocation] = []

    def _stamp(self, action: str, actor_id: str, workshop_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._audit.append(KernelInvocation(at=now, action=action, actor_id=actor_id, workshop_id=workshop_id))
        if len(self._audit) > 1000:
            self._audit = self._audit[-1000:]

    def place(
        self,
        *,
        raw: str,
        context: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        self._stamp("place", actor_id, workshop_id)
        return self._client.place(raw, context=context)

    def observe(self, *, actor_id: str, workshop_id: str) -> ObserveResponse:
        self._stamp("observe", actor_id, workshop_id)
        return self._client.observe()

    def timeline(self, *, actor_id: str, workshop_id: str) -> Sequence[KernelEventObj]:
        self._stamp("timeline", actor_id, workshop_id)
        return self._client.events()

    def edges(self, *, actor_id: str, workshop_id: str) -> Sequence[EdgeObj]:
        self._stamp("edges", actor_id, workshop_id)
        return self._client.edges()

    def frontiers(self, *, actor_id: str, workshop_id: str) -> Sequence[FrontierObj]:
        self._stamp("frontiers", actor_id, workshop_id)
        return self._client.frontiers()

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        self._stamp("attest", actor_id, workshop_id)
        return self._client.attest(
            witness_id=witness_id,
            attestation_kind=attestation_kind,
            attestation_tag=attestation_tag,
            payload=payload,
            target=target,
        )

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
        policy: Mapping[str, Any] | None = None,
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        self._stamp("akinenwun_lookup", actor_id, workshop_id)
        return self._client.akinenwun_lookup(akinenwun=akinenwun, mode=mode, ingest=ingest, policy=policy or {})

    def audit_log(self) -> Sequence[KernelInvocation]:
        return list(self._audit)


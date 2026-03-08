from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from shygazun.kernel.attestation import Attestation, Refusal
from shygazun.kernel.kernel import Kernel, ObserveResult, PlaceResult
from shygazun.kernel.types import Edge, Frontier
from shygazun.kernel.types.events import AttestationEventObj, KernelEventObj


class AtelierPort:
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def place_line(self, raw: str, *, context: Optional[Dict[str, Any]] = None) -> PlaceResult:
        return self._kernel.place(raw=raw, context=context)

    def observe(self) -> ObserveResult:
        return self._kernel.observe()

    def get_frontiers(self) -> List[Frontier]:
        return sorted(self._kernel.frontiers, key=lambda frontier: frontier.id)

    def get_timeline(self, last: Optional[int] = None) -> Sequence[KernelEventObj]:
        events = self._kernel.get_events()
        if last is None:
            return events
        if last <= 0:
            return []
        return events[-last:]

    def get_edges(self) -> Sequence[Edge]:
        return self._kernel.get_edges()

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> AttestationEventObj:
        return self._kernel.record_attestation(
            witness_id=witness_id,
            attestation_kind=attestation_kind,
            attestation_tag=attestation_tag,
            payload=payload,
            target=target,
        )

    def process_attestation(
        self,
        attestation: Attestation,
        *,
        require_signature: bool = False,
        signature_verifier: Optional[Callable[[bytes, str, str], bool]] = None,
    ) -> Union[AttestationEventObj, Refusal]:
        return self._kernel.process_attestation(
            attestation,
            require_signature=require_signature,
            signature_verifier=signature_verifier,
        )

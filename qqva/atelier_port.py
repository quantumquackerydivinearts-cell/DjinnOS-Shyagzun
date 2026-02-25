from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Sequence

from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResult, PlaceResult


class AtelierPort(Protocol):
    def place_line(self, raw: str, *, context: Optional[Dict[str, Any]] = None) -> PlaceResult: ...

    def observe(self) -> ObserveResult: ...

    def get_frontiers(self) -> Sequence[FrontierObj]: ...

    def get_timeline(self, last: Optional[int] = None) -> Sequence[KernelEventObj]: ...

    def get_edges(self) -> Sequence[EdgeObj]: ...

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> KernelEventObj: ...


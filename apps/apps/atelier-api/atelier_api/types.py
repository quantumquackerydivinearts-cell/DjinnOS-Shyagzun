from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, TypedDict


class KernelEventObj(TypedDict, total=False):
    id: str
    kind: str
    at: Dict[str, Any]


class EdgeObj(TypedDict):
    from_event: str
    to_event: str
    type: str
    metadata: Dict[str, Any]


class FrontierObj(TypedDict):
    id: str
    event_ids: list[str]
    status: str
    inconsistency_proof: Optional[Dict[str, Any]]


class PlaceRequest(TypedDict):
    raw: str
    context: Dict[str, Any]


class ObserveResponse(TypedDict):
    field_id: str
    clock: Dict[str, Any]
    candidates_by_frontier: Dict[str, list[Dict[str, Any]]]
    eligible_by_frontier: Dict[str, list[Dict[str, Any]]]
    eligibility_events: list[KernelEventObj]
    refusals: list[Dict[str, Any]]


Timeline = Sequence[KernelEventObj]
Edges = Sequence[EdgeObj]


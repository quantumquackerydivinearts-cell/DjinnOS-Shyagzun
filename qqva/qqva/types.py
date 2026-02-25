from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TypedDict


class FrontierObj(TypedDict):
    id: str
    event_ids: List[str]
    status: str
    inconsistency_proof: Optional[Dict[str, Any]]


class EdgeObj(TypedDict):
    from_event: str
    to_event: str
    type: str
    metadata: Dict[str, Any]


class KernelEventObj(TypedDict, total=False):
    id: str
    kind: str
    at: Dict[str, Any]


class PlaceResult(TypedDict):
    field_id: str
    clock: Dict[str, Any]
    placement_event: KernelEventObj
    observe: Dict[str, Any]


class ObserveResult(TypedDict):
    field_id: str
    clock: Dict[str, Any]
    candidates_by_frontier: Dict[str, List[Dict[str, Any]]]
    eligible_by_frontier: Dict[str, List[Dict[str, Any]]]
    eligibility_events: List[KernelEventObj]
    refusals: List[Dict[str, Any]]


Timeline = Sequence[KernelEventObj]
Edges = Sequence[EdgeObj]


from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict, Union


class PlacementEventObj(TypedDict):
    id: str
    kind: str
    utterance: Dict[str, Any]
    context: Dict[str, Any]
    delta: Dict[str, Any]
    at: Dict[str, Any]


class EligibilityEventObj(TypedDict, total=False):
    id: str
    kind: str
    frontier_id: str
    candidate_id: str
    candidate_hash: str
    at: Dict[str, Any]
    candidate_snapshot: Any


class RefusalEventObj(TypedDict):
    id: str
    kind: str
    reason_code: str
    frontier_id: str
    candidate_id: str
    details: Dict[str, Any]
    at: Dict[str, Any]


class AttestationEventObj(TypedDict):
    id: str
    kind: str
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str]
    payload: Dict[str, Any]
    target: Dict[str, Any]
    at: Dict[str, Any]


KernelEventObj = Union[
    PlacementEventObj,
    EligibilityEventObj,
    RefusalEventObj,
    AttestationEventObj,
]

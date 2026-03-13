# kernel/types.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Literal, TypedDict
from typing_extensions import NotRequired, Required


# -----------------------------
# Core artifacts
# -----------------------------

class KernelClock(TypedDict):
    tick: int
    causal_epoch: str


class Utterance(TypedDict, total=False):
    raw: str
    addressing: Dict[str, Any]
    metadata: Dict[str, Any]


class Field(TypedDict):
    field_id: str
    clock: KernelClock
    tensions: Dict[str, Any]
    gates: Dict[str, Any]
    obligations: Dict[str, Any]
    atoms: Dict[str, Any]
    lotus: Dict[str, Any]


# -----------------------------
# Candidate completion (dataclasses for stable hashing)
# -----------------------------

@dataclass(frozen=True)
class LotusRequirement:
    kind: Literal["await_attestation", "unspecified"]
    attestation_tag: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class Preconditions:
    requires_gates: Optional[List[str]] = None
    requires_events: Optional[List[str]] = None
    forbids_events: Optional[List[str]] = None
    forbids_candidates: Optional[List[str]] = None
    requires_obligations_paid: Optional[List[str]] = None
    lotus_requirement: Optional[LotusRequirement] = None


@dataclass(frozen=True)
class PrioritySignature:
    head_weight: Optional[float] = None
    relation_weight: Optional[float] = None
    closure_weight: Optional[float] = None
    tail_markers: Optional[List[str]] = None


@dataclass(frozen=True)
class Provenance:
    source: Literal["register", "kernel", "witness", "policy"]
    name: str
    ref: Optional[str] = None


@dataclass(frozen=True)
class CandidateCompletion:
    id: str
    preconditions: Preconditions
    effects: Dict[str, Any]
    costs: List[Dict[str, Any]]
    priority_signature: PrioritySignature
    provenance: List[Provenance]

    def to_canonical_obj(self) -> Dict[str, Any]:
        return asdict(self)


# -----------------------------
# CEG Edge + Kernel Events
# -----------------------------

class Edge(TypedDict, total=False):
    # NOTE: use "from" not "from_" to match spec; "from" is fine as a key.
    from_event: str
    to_event: str
    type: Literal["enables", "conflicts", "depends", "costs"]
    metadata: Dict[str, Any]


class PlacementEvent(TypedDict):
    id: str
    kind: Literal["placement"]
    utterance: Utterance
    context: Dict[str, Any]
    delta: Dict[str, Any]
    at: KernelClock


class EligibilityEvent(TypedDict, total=False):
    # required keys
    id: Required[str]
    kind: Required[Literal["eligibility"]]
    candidate_id: Required[str]
    candidate_hash: Required[str]
    frontier_id: Required[str]
    at: Required[KernelClock]
    # optional
    candidate_snapshot: NotRequired[Dict[str, Any]]


class RefusalEvent(TypedDict, total=False):
    id: str
    kind: Literal["refusal"]
    reason_code: str
    at: KernelClock
    frontier_id: NotRequired[str]
    candidate_id: NotRequired[str]
    details: NotRequired[Dict[str, Any]]


class CommitmentEvent(TypedDict):
    id: str
    kind: Literal["commitment"]
    candidate_id: str
    frontier_id: str
    irreversible: Literal[True]
    delta: Dict[str, Any]
    at: KernelClock


class LotusAttestationEvent(TypedDict):
    id: str
    kind: Literal["lotus_attestation"]
    attestation: Dict[str, Any]
    at: KernelClock


KernelEvent = (
    PlacementEvent
    | EligibilityEvent
    | RefusalEvent
    | CommitmentEvent
    | LotusAttestationEvent
)


# -----------------------------
# Frontier
# -----------------------------

from typing import TypedDict, Literal, List, Dict, Any, NotRequired

class Frontier(TypedDict):
    id: str
    event_ids: List[str]
    status: Literal["active", "inconsistent", "closed"]
    inconsistency_proof: NotRequired[Dict[str, Any]]


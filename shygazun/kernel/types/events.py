from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal, TypedDict, Union
from .clock import Clock
from kernel.kernel import PlacementEventObj, EligibilityEventObj, RefusalEventObj

class AttestationEventObj(TypedDict):
    id: str
    kind: str  # "attestation"
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str]
    payload: Dict[str, Any]
    target: Dict[str, Any]
    at: Dict[str, Any]

KernelEventObj = Dict[str, Any]



EventKind = Literal[
    "placement",
    "eligibility",
    "refusal",
    "commitment",
    "counter_completion",
    "lotus_attestation",
]

RefusalReason = Literal[
    "await-lotus",
    "no-eligible",
    "blocked",
]

@dataclass(frozen=True)
class KernelEvent:
    id: str
    kind: EventKind
    at: Clock

# --- Placement ---

@dataclass(frozen=True)
class PlacementEvent(KernelEvent):
    utterance: Dict[str, Any]
    context: Dict[str, Any]
    delta: Dict[str, Any]

# --- Eligibility (Fix A compliant) ---

@dataclass(frozen=True)
class EligibilityEvent(KernelEvent):
    candidate_id: str
    candidate_hash: str
    frontier_id: str
    candidate_snapshot: Optional[Dict[str, Any]] = None

# --- Refusal ---

@dataclass(frozen=True)
class RefusalEvent(KernelEvent):
    reason_code: RefusalReason
    frontier_id: Optional[str] = None
    candidate_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# --- Commitment ---

@dataclass(frozen=True)
class CommitmentEvent(KernelEvent):
    candidate_id: str
    frontier_id: str
    attestation: Dict[str, Any]
    irreversible: bool
    delta: Dict[str, Any]
    against_event_id: Optional[str] = None


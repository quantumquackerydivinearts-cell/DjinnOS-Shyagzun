from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass(frozen=True)
class Preconditions:
    forbids_candidates: Optional[List[str]] = None
    lotus_requirement: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class PrioritySignature:
    relation_weight: float = 0.0
    closure_weight: float = 0.0
    tail_markers: Optional[List[str]] = None

@dataclass(frozen=True)
class CandidateCompletion:
    id: str
    preconditions: Preconditions
    effects: Dict[str, Any]
    costs: List[Any]
    priority_signature: PrioritySignature
    provenance: List[Dict[str, str]]

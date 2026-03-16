from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class Preconditions:
    forbids_candidates: List[str] = field(default_factory=list)
    lotus_requirement: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class PrioritySignature:
    relation_weight: float = 0.0
    closure_weight: float = 0.0
    tail_markers: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class CandidateCompletion:
    id: str
    preconditions: Preconditions
    effects: Dict[str, Any]
    costs: List[Any]
    priority_signature: PrioritySignature
    provenance: List[Dict[str, str]]

    def to_canonical_obj(self) -> Dict[str, Any]:
        """Canonical structural representation for hashing. No semantic fields."""
        return {
            "id": self.id,
            "preconditions": {
                "forbids_candidates": list(self.preconditions.forbids_candidates),
                "lotus_requirement": self.preconditions.lotus_requirement,
            },
            "costs": list(self.costs),
            "effects": dict(self.effects),
            "priority_signature": {
                "relation_weight": self.priority_signature.relation_weight,
                "closure_weight": self.priority_signature.closure_weight,
                "tail_markers": list(self.priority_signature.tail_markers),
            },
        }

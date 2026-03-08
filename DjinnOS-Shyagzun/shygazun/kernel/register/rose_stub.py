from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from shygazun.kernel.types import Frontier


@dataclass(frozen=True)
class LotusRequirement:
    kind: str
    attestation_tag: str


@dataclass(frozen=True)
class Preconditions:
    forbids_candidates: Sequence[str]
    lotus_requirement: Optional[LotusRequirement]


@dataclass(frozen=True)
class PrioritySignature:
    relation_weight: float
    closure_weight: float
    tail_markers: Sequence[str]


@dataclass(frozen=True)
class Candidate:
    id: str
    preconditions: Preconditions
    costs: Sequence[Any]
    effects: Mapping[str, Any]
    priority_signature: PrioritySignature

    def to_canonical_obj(self) -> Any:
        lotus = self.preconditions.lotus_requirement
        return {
            "id": self.id,
            "preconditions": {
                "forbids_candidates": list(self.preconditions.forbids_candidates),
                "lotus_requirement": None
                if lotus is None
                else {"kind": lotus.kind, "attestation_tag": lotus.attestation_tag},
            },
            "costs": list(self.costs),
            "effects": dict(self.effects),
            "priority_signature": {
                "relation_weight": self.priority_signature.relation_weight,
                "closure_weight": self.priority_signature.closure_weight,
                "tail_markers": list(self.priority_signature.tail_markers),
            },
        }


class RoseStub:
    name = "rose"

    def admit(self, fragment: Mapping[str, Any], field: Any) -> Mapping[str, Any]:
        _ = (fragment, field)
        return {"admitted": True, "claim_ids": ["rose.claim"]}

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[Candidate]:
        _ = (field, claims, frontier)
        alpha = Candidate(
            id="rose.link.alpha",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.beta"],
                lotus_requirement=None,
            ),
            costs=[],
            effects={},
            priority_signature=PrioritySignature(
                relation_weight=0.0,
                closure_weight=0.0,
                tail_markers=[],
            ),
        )
        beta = Candidate(
            id="rose.link.beta",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.alpha"],
                lotus_requirement=None,
            ),
            costs=[],
            effects={},
            priority_signature=PrioritySignature(
                relation_weight=0.0,
                closure_weight=0.0,
                tail_markers=[],
            ),
        )
        return [alpha, beta]

    def constrain(
        self,
        field: Any,
        candidates: Sequence[Candidate],
        frontier: Frontier,
    ) -> Mapping[str, Any]:
        _ = (field, candidates, frontier)
        return {}

    def observe(self, field: Any, frontier: Frontier) -> List[Mapping[str, Any]]:
        _ = (field, frontier)
        return []

from __future__ import annotations

from typing import Any, List, Mapping, Sequence

from .types.candidate import CandidateCompletion, Preconditions, PrioritySignature
from .types.frontier import Frontier


class BaseRegister:
    name: str = "base"

    def admit(self, fragment: Mapping[str, Any], field: Any) -> Mapping[str, Any]:
        return {"admitted": True}

    def propose(self, field: Any, claims: Mapping[str, Any], frontier: Frontier) -> List[CandidateCompletion]:
        return []

    def constrain(self, field: Any, candidates: Sequence[CandidateCompletion], frontier: Frontier) -> Mapping[str, Any]:
        return {}

    def observe(self, field: Any, frontier: Frontier) -> List[Mapping[str, Any]]:
        return []


class RoseRegister(BaseRegister):
    name = "rose"

    def propose(self, field: Any, claims: Mapping[str, Any], frontier: Frontier) -> List[CandidateCompletion]:
        ps = PrioritySignature(
            relation_weight=1.0,
            closure_weight=1.0,
            tail_markers=[],
        )

        cand_a = CandidateCompletion(
            id="rose.link.alpha",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.beta"],
                lotus_requirement=None,
            ),
            costs=[],
            effects={},
            priority_signature=ps,
            provenance=[{"source": "rose", "kind": "stub"}],
        )

        cand_b = CandidateCompletion(
            id="rose.link.beta",
            preconditions=Preconditions(
                forbids_candidates=["rose.link.alpha"],
                lotus_requirement=None,
            ),
            costs=[],
            effects={},
            priority_signature=ps,
            provenance=[{"source": "rose", "kind": "stub"}],
        )

        return [cand_a, cand_b]


class SakuraRegister(BaseRegister):
    name = "sakura"

    def propose(self, field: Any, claims: Mapping[str, Any], frontier: Frontier) -> List[CandidateCompletion]:
        ps = PrioritySignature(
            relation_weight=0.5,
            closure_weight=0.5,
            tail_markers=[],
        )

        lotus_req = {
            "kind": "await_attestation",
            "attestation_tag": "closure",
        }

        cand = CandidateCompletion(
            id="sakura.await.lotus",
            preconditions=Preconditions(
                forbids_candidates=[],
                lotus_requirement=lotus_req,
            ),
            costs=[],
            effects={},
            priority_signature=ps,
            provenance=[{"source": "sakura", "kind": "lotus-gated"}],
        )

        return [cand]

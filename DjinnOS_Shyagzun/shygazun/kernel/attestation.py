from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, runtime_checkable


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@runtime_checkable
class LotusRequirementLike(Protocol):
    kind: str
    attestation_tag: str


@runtime_checkable
class PreconditionsLike(Protocol):
    forbids_candidates: Sequence[str]
    lotus_requirement: Optional[LotusRequirementLike]


@runtime_checkable
class PrioritySignatureLike(Protocol):
    relation_weight: float
    closure_weight: float
    tail_markers: Sequence[str]


@runtime_checkable
class CandidateLike(Protocol):
    id: str
    preconditions: PreconditionsLike
    costs: Sequence[Any]
    effects: Mapping[str, Any]
    priority_signature: PrioritySignatureLike

    def to_canonical_obj(self) -> Any: ...


def candidate_structural_payload(candidate: CandidateLike) -> Any:
    # Restriction: hash payload must be structural only; no semantic fields are added.
    if hasattr(candidate, "to_canonical_obj"):
        return candidate.to_canonical_obj()

    lotus = candidate.preconditions.lotus_requirement
    return {
        "id": candidate.id,
        "preconditions": {
            "forbids_candidates": list(candidate.preconditions.forbids_candidates),
            "lotus_requirement": None
            if lotus is None
            else {"kind": lotus.kind, "attestation_tag": lotus.attestation_tag},
        },
        "costs": list(candidate.costs),
        "effects": dict(candidate.effects),
        "priority_signature": {
            "relation_weight": candidate.priority_signature.relation_weight,
            "closure_weight": candidate.priority_signature.closure_weight,
            "tail_markers": list(candidate.priority_signature.tail_markers),
        },
    }


def intent_hash_for_candidate(candidate: CandidateLike) -> str:
    payload = _canonical_json(candidate_structural_payload(candidate)).encode("utf-8")
    return _sha256_hex(payload)


@dataclass(frozen=True)
class Attestation:
    field_id: str
    clock: int
    frontier_id: str
    candidate_id: str
    agent_id: str
    intent_hash: str
    signature: Optional[str] = None

    def canonical_payload(self) -> bytes:
        # Restriction: deterministic payload prevents reinterpretation across layers.
        obj: Dict[str, Any] = {
            "agent_id": self.agent_id,
            "candidate_id": self.candidate_id,
            "clock": self.clock,
            "field_id": self.field_id,
            "frontier_id": self.frontier_id,
            "intent_hash": self.intent_hash,
        }
        if self.signature is not None:
            obj["signature"] = self.signature
        return _canonical_json(obj).encode("utf-8")


@dataclass(frozen=True)
class Refusal:
    reason: str
    frontier_id: str
    agent_id: str
    clock: int

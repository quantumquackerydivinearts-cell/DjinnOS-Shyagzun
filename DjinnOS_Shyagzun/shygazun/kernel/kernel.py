from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from .ceg import CEG, KernelEventObj
from .attestation import (
    Attestation, Refusal, intent_hash_for_candidate,
    CandidateLike as CandidateCompletionLike,
)
from .types.events import AttestationEventObj

# Import only stable public surface types.
# FieldLike is structural; kernel advances time. CEG is append-only.
from .types import Clock, Frontier, Edge

# Kobra — Shygazun programming substrate (deterministic, no CEG mutation)
from .kobra import parse as _kobra_parse
from .kobra.types import ParseResult as KobraParseResult


# ---------------------------------------------------------------------------
# Structural event shapes (JSON-first)
# ---------------------------------------------------------------------------

class UtteranceObj(TypedDict, total=False):
    raw: str
    addressing: Dict[str, Any]
    metadata: Dict[str, Any]


class PlacementEventObj(TypedDict):
    id: str
    kind: str  # "placement"
    utterance: Dict[str, Any]
    context: Dict[str, Any]
    delta: Dict[str, Any]
    at: Dict[str, Any]  # clock as JSON object


class _EligibilityEventObjRequired(TypedDict):
    id: str
    kind: str  # "eligibility"
    at: Dict[str, Any]


class EligibilityEventObj(_EligibilityEventObjRequired, total=False):
    frontier_id: str
    candidate_id: str
    candidate_hash: str
    # Debug-only; MUST NOT be used for semantics or hashing.
    candidate_snapshot: Any


class RefusalEventObj(TypedDict):
    id: str
    kind: str  # "refusal"
    reason_code: str
    frontier_id: str
    candidate_id: str
    details: Dict[str, Any]
    at: Dict[str, Any]


# ---------------------------------------------------------------------------
# Field protocol (structural)
# ---------------------------------------------------------------------------

class FieldLike(Protocol):
    """
    Structural contract only.
    Kernel advances time by writing a new Clock into field.clock.
    """

    field_id: str
    clock: Clock


# ---------------------------------------------------------------------------
# Register protocol (shape only; semantics forbidden)
# ---------------------------------------------------------------------------

class RegisterPlugin(Protocol):
    name: str

    def admit(self, fragment: Mapping[str, Any], field: FieldLike) -> Mapping[str, Any]:
        ...

    def propose(
        self,
        field: FieldLike,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletionLike]:
        ...

    def constrain(
        self,
        field: FieldLike,
        candidates: Sequence[CandidateCompletionLike],
        frontier: Frontier,
    ) -> Mapping[str, Any]:
        ...

    def observe(self, field: FieldLike, frontier: Frontier) -> List[Mapping[str, Any]]:
        ...


# ---------------------------------------------------------------------------
# Results (internal; API wrapper can translate later)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObserveResult:
    """
    Structural observation only.
    No meaning inference, no implicit commits.
    """
    field_id: str
    clock: Clock
    candidates_by_frontier: Dict[str, List[CandidateCompletionLike]]
    eligible_by_frontier: Dict[str, List[CandidateCompletionLike]]
    eligibility_events: List[EligibilityEventObj]
    refusals: List[RefusalEventObj]


@dataclass(frozen=True)
class PlaceResult:
    field_id: str
    clock: Clock
    placement_event: PlacementEventObj
    observe: ObserveResult


# ---------------------------------------------------------------------------
# Canonicalization helpers (determinism)
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    """
    Canonical JSON for hashing:
    - UTF-8
    - sorted keys
    - no whitespace
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _stable_event_id(parts: Tuple[Any, ...]) -> str:
    """
    Deterministic event id derivation from provided parts.
    """
    return "evt_" + _sha256_hex(_canonical_json(list(parts)))


def _clock_obj(clock: Clock) -> Dict[str, Any]:
    """
    Convert Clock into JSON object form.
    (No interpretation; pure structure.)
    """
    return {"tick": clock.tick, "causal_epoch": clock.causal_epoch}


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------

class Kernel:
    """
    Kernel orchestrator with strict boundaries:

    - Append-only: events/edges are never deleted.
    - Refusal is state.
    - Ambiguity is first-class.
    - Lotus is awaited/witnessed; never resolved internally.
    - Filesystem location is irrelevant to kernel semantics.
    """

    def __init__(
        self,
        field: FieldLike,
        frontiers: Optional[List[Frontier]] = None,
        registers: Optional[List[RegisterPlugin]] = None,
        ceg: Optional[CEG] = None,
    ) -> None:
        # Read-only identity surface
        self.field: FieldLike = field

        # Active frontiers
        self.frontiers: List[Frontier] = (
            frontiers
            if frontiers is not None
            else [
                Frontier(
                    id="F0",
                    event_ids=[],
                    status="active",
                    inconsistency_proof=None,
                )
            ]
        )

        # Structural register plugins (no semantics)
        self.registers: List[RegisterPlugin] = registers or []

        # Canonical Event Graph (append-only)
        self.ceg: CEG = ceg if ceg is not None else CEG()

    # ---------------- clock ----------------

    def _tick(self) -> None:
        """
        Kernel is the sole writer of the effective clock tick.
        Writes a new Clock into field.clock.
        """
        c = self.field.clock
        self.field.clock = Clock(tick=c.tick + 1, causal_epoch=c.causal_epoch)

    # ---------------- public (Phase D1) ----------------

    def place(
        self,
        raw: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
        addressing: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> PlaceResult:
        """
        Place one utterance into the field.
        Emits a structural PlacementEvent (append-only), then observes structurally.
        """
        self._tick()

        utt: UtteranceObj = {
            "raw": raw,
            "addressing": dict(addressing or {}),
            "metadata": dict(metadata or {}),
        }

        ctx_obj: Dict[str, Any] = dict(context or {})
        clk = self.field.clock

        pe: PlacementEventObj = {
            "id": _stable_event_id(("placement", self.field.field_id, clk.tick, raw)),
            "kind": "placement",
            "utterance": dict(utt),
            "context": ctx_obj,
            "delta": {},
            "at": _clock_obj(clk),
        }
        self.ceg.add_event(pe)

        obs = self.observe()

        return PlaceResult(
            field_id=self.field.field_id,
            clock=self.field.clock,
            placement_event=pe,
            observe=obs,
        )

    def observe(self) -> ObserveResult:
        """
        Structural observation only:
        - gather candidates per frontier via registers
        - emit eligibility events (candidate_id + candidate_hash) [Fix A]
        - emit explicit conflict edges from forbids_candidates
        - emit refusals for lotus requirements (never resolved internally)
        - determine eligible candidates (non-lotus only)
        """
        self._tick()

        candidates_by_frontier: Dict[str, List[CandidateCompletionLike]] = {}
        eligible_by_frontier: Dict[str, List[CandidateCompletionLike]] = {}
        eligibility_events: List[EligibilityEventObj] = []
        refusals: List[RefusalEventObj] = []

        clk = self.field.clock

        for fr in self.frontiers:
            if fr.status != "active":
                continue

            # 1) gather candidates
            gathered = self._gather_candidates_for_frontier(fr)

            candidates_by_frontier[fr.id] = list(gathered)

            # 2) emit eligibility events (Fix A: candidate_id + candidate_hash only)
            candidate_to_elig_event_id: Dict[str, str] = {}
            for c in gathered:
                c_hash = self._candidate_hash(c)
                ee: EligibilityEventObj = {
                    "id": _stable_event_id(("eligibility", self.field.field_id, fr.id, clk.tick, c.id, c_hash)),
                    "kind": "eligibility",
                    "candidate_id": c.id,
                    "candidate_hash": c_hash,
                    "frontier_id": fr.id,
                    "at": _clock_obj(clk),
                    "candidate_snapshot": None,
                }
                self.ceg.add_event(ee)
                eligibility_events.append(ee)
                candidate_to_elig_event_id[c.id] = ee["id"]

            # 3) materialize conflict edges from forbids_candidates
            self._materialize_conflicts(fr.id, gathered, candidate_to_elig_event_id)

            # 4) lotus waits => refusal; non-lotus => eligible
            eligible: List[CandidateCompletionLike] = []
            for c in gathered:
                lotus_req = c.preconditions.lotus_requirement
                if lotus_req is not None:
                    r: RefusalEventObj = {
                        "id": _stable_event_id(("refusal", self.field.field_id, fr.id, clk.tick, "await-lotus", c.id)),
                        "kind": "refusal",
                        "reason_code": "await-lotus",
                        "frontier_id": fr.id,
                        "candidate_id": c.id,
                        "details": {},
                        "at": _clock_obj(clk),
                    }
                    self.ceg.add_event(r)
                    refusals.append(r)
                    continue
                eligible.append(c)

            eligible_by_frontier[fr.id] = eligible

        return ObserveResult(
            field_id=self.field.field_id,
            clock=self.field.clock,
            candidates_by_frontier=candidates_by_frontier,
            eligible_by_frontier=eligible_by_frontier,
            eligibility_events=eligibility_events,
            refusals=refusals,
        )

    # ---------------- internals ----------------

    def _candidate_hash(self, c: CandidateCompletionLike) -> str:
        """
        Kernel-computed candidate hash from canonical JSON.

        Contract:
        - If candidate exposes to_canonical_obj(), use it verbatim.
        - Otherwise, use a deterministic fallback structural object.
        """
        if hasattr(c, "to_canonical_obj"):
            obj = c.to_canonical_obj()
        else:
            lotus = c.preconditions.lotus_requirement
            obj = {
                "id": c.id,
                "preconditions": {
                    "forbids_candidates": list(c.preconditions.forbids_candidates),
                    "lotus_requirement": None
                    if lotus is None
                    else {"kind": lotus.kind, "attestation_tag": lotus.attestation_tag},
                },
                "costs": list(c.costs),
                "effects": dict(c.effects),
                "priority_signature": {
                    "relation_weight": c.priority_signature.relation_weight,
                    "closure_weight": c.priority_signature.closure_weight,
                    "tail_markers": list(c.priority_signature.tail_markers),
                },
            }

        return "h_" + _sha256_hex(_canonical_json(obj))

    def _materialize_conflicts(
        self,
        frontier_id: str,
        candidates: Sequence[CandidateCompletionLike],
        elig_event_ids: Mapping[str, str],
    ) -> None:
        """
        For each candidate with forbids_candidates, emit explicit conflict edges.
        (No inference; only explicit declarations.)
        """
        for c in candidates:
            forbids = list(c.preconditions.forbids_candidates)
            if not forbids:
                continue

            src_eid = elig_event_ids.get(c.id)
            if src_eid is None:
                continue

            for forbidden_candidate_id in forbids:
                dst_eid = elig_event_ids.get(forbidden_candidate_id)
                if dst_eid is None:
                    continue

                e = Edge(
                    from_event=src_eid,
                    to_event=dst_eid,
                    type="conflicts",
                    metadata={
                        "kind": "candidate_forbids_candidate",
                        "frontier_id": frontier_id,
                        "source_candidate_id": c.id,
                        "forbidden_candidate_id": forbidden_candidate_id,
                    },
                )
                self.ceg.add_edge(e)

    # ---------------- Kobra ----------------

    def parse_kobra(self, source: str) -> KobraParseResult:
        """
        Parse a Kobra source string.

        Deterministic and read-only — does not advance the clock or mutate
        the CEG.  Returns a Resolved, Echo, or FrontierOpen parse result.

        The caller decides whether to materialise the result into the field
        (via ``place``) or act on it directly.
        """
        return _kobra_parse(source)

    # ---------------- Phase D2 handoff hooks ----------------

    def get_events(self) -> Sequence[KernelEventObj]:
        return self.ceg.get_events()

    def get_edges(self) -> Sequence[Edge]:
        return self.ceg.get_edges()

    def get_clock(self) -> Clock:
        return self.field.clock

    def record_attestation(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Dict[str, Any],
        target: Dict[str, Any],
    ) -> AttestationEventObj:
        """
        Record an attestation as a structural fact.

        No resolution.
        No validation beyond shape.
        No semantic effect.
        """
        self._tick()
        clk = self.field.clock

        evt: AttestationEventObj = {
            "id": _stable_event_id(
                (
                    "attestation",
                    self.field.field_id,
                    clk.tick,
                    witness_id,
                    attestation_kind,
                    attestation_tag,
                    target,
                )
            ),
            "kind": "attestation",
            "witness_id": witness_id,
            "attestation_kind": attestation_kind,
            "attestation_tag": attestation_tag,
            "payload": dict(payload),
            "target": dict(target),
            "at": _clock_obj(clk),
        }

        self.ceg.add_event(evt)
        return evt

    def process_attestation(
        self,
        attestation: Attestation,
        *,
        require_signature: bool = False,
        signature_verifier: Optional[Callable[[bytes, str, str], bool]] = None,
    ) -> Union[AttestationEventObj, Refusal]:
        """
        Process attestation as explicit structural commitment binding.

        Restrictions enforced here:
        - no implicit selection
        - no semantic interpretation
        - no hidden branching
        """
        if attestation.field_id != self.field.field_id:
            return self._emit_attestation_refusal("field-mismatch", attestation)

        frontier = self._find_frontier(attestation.frontier_id)
        if frontier is None:
            return self._emit_attestation_refusal("frontier-missing", attestation)

        if frontier.status != "active":
            return self._emit_attestation_refusal("frontier-not-open", attestation)

        if attestation.clock != self.field.clock.tick:
            return self._emit_attestation_refusal("clock-mismatch", attestation)

        candidates = self._gather_candidates_for_frontier(frontier)
        candidate = self._find_candidate(candidates, attestation.candidate_id)
        if candidate is None:
            return self._emit_attestation_refusal("candidate-missing", attestation)

        expected_intent_hash = intent_hash_for_candidate(candidate)
        if expected_intent_hash != attestation.intent_hash:
            return self._emit_attestation_refusal("intent-hash-mismatch", attestation)

        if require_signature:
            if attestation.signature is None:
                return self._emit_attestation_refusal("signature-missing", attestation)
            if signature_verifier is None:
                return self._emit_attestation_refusal("signature-verifier-missing", attestation)
            signature_ok = signature_verifier(
                attestation.canonical_payload(),
                attestation.signature,
                attestation.agent_id,
            )
            if not signature_ok:
                return self._emit_attestation_refusal("signature-invalid", attestation)

        # Append-only attested fact; no resolution logic is allowed here.
        self._tick()
        clk = self.field.clock
        evt: AttestationEventObj = {
            "id": _stable_event_id(
                (
                    "attested",
                    self.field.field_id,
                    clk.tick,
                    attestation.frontier_id,
                    attestation.candidate_id,
                    attestation.agent_id,
                    attestation.intent_hash,
                    attestation.signature,
                )
            ),
            "kind": "attestation",
            "witness_id": attestation.agent_id,
            "attestation_kind": "commitment",
            "attestation_tag": None,
            "payload": {
                "intent_hash": attestation.intent_hash,
                "signature": attestation.signature,
                "attestation_clock": attestation.clock,
            },
            "target": {
                "field_id": attestation.field_id,
                "frontier_id": attestation.frontier_id,
                "candidate_id": attestation.candidate_id,
            },
            "at": _clock_obj(clk),
        }
        self.ceg.add_event(evt)
        return evt

    def _find_frontier(self, frontier_id: str) -> Optional[Frontier]:
        for frontier in self.frontiers:
            if frontier.id == frontier_id:
                return frontier
        return None

    def _find_candidate(
        self,
        candidates: Sequence[CandidateCompletionLike],
        candidate_id: str,
    ) -> Optional[CandidateCompletionLike]:
        for candidate in candidates:
            if candidate.id == candidate_id:
                return candidate
        return None

    def _gather_candidates_for_frontier(self, frontier: Frontier) -> List[CandidateCompletionLike]:
        gathered: List[CandidateCompletionLike] = []
        for reg in self.registers:
            claims = reg.admit({"raw": ""}, self.field)
            if not bool(claims.get("admitted", False)):
                continue
            gathered.extend(reg.propose(self.field, claims, frontier))
        return gathered

    def _emit_attestation_refusal(self, reason: str, attestation: Attestation) -> Refusal:
        self._tick()
        clk = self.field.clock

        refusal = Refusal(
            reason=reason,
            frontier_id=attestation.frontier_id,
            agent_id=attestation.agent_id,
            clock=clk.tick,
        )

        evt: RefusalEventObj = {
            "id": _stable_event_id(
                (
                    "refusal",
                    self.field.field_id,
                    refusal.frontier_id,
                    refusal.clock,
                    reason,
                    refusal.agent_id,
                    attestation.candidate_id,
                )
            ),
            "kind": "refusal",
            "reason_code": reason,
            "frontier_id": refusal.frontier_id,
            "candidate_id": attestation.candidate_id,
            "details": {
                "agent_id": refusal.agent_id,
                "attestation_field_id": attestation.field_id,
                "attestation_intent_hash": attestation.intent_hash,
            },
            "at": _clock_obj(clk),
        }
        self.ceg.add_event(evt)
        return refusal

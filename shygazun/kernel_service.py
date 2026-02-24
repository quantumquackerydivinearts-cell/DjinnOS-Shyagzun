from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, cast

from fastapi import FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from shygazun.kernel.kernel import Kernel, RegisterPlugin
from shygazun.kernel.register.rose_stub import RoseStub
from shygazun.kernel.register.sakura_stub import SakuraStub
from shygazun.kernel.types import Clock, Edge, Frontier
from shygazun.kernel.types.events import KernelEventObj


@dataclass
class InMemoryField:
    field_id: str
    clock: Clock


@dataclass
class RuntimeState:
    lotus_attestation_count: int = 0


class PlaceRequest(BaseModel):
    raw: Optional[str] = None
    utterance: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    addressing: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class EligibilityRequest(BaseModel):
    field_id: str
    frontier_ids: List[str]


class RequestCommitBody(BaseModel):
    field_id: str
    frontier_id: str
    candidate_id: str


class V1AttestRequest(BaseModel):
    field_id: str
    attestation: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


class ReplayRequest(BaseModel):
    bundle: Dict[str, Any]


class AttestRequest(BaseModel):
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str]
    payload: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


def _json_response(payload: object, status_code: int = 200) -> Response:
    encoded = jsonable_encoder(payload)
    body = json.dumps(encoded, ensure_ascii=False, separators=(",", ":"))
    return Response(content=body, status_code=status_code, media_type="application/json")


app = FastAPI()

_field = InMemoryField(field_id="F0", clock=Clock(tick=0, causal_epoch="0"))
_registers: List[RegisterPlugin] = cast(List[RegisterPlugin], [RoseStub(), SakuraStub()])
_kernel = Kernel(field=_field, registers=_registers)
_state = RuntimeState()


def _assert_field_id_or_default(field_id: Optional[str]) -> str:
    if field_id is None:
        return _field.field_id
    if field_id == "null":
        return _field.field_id
    if field_id != _field.field_id:
        raise HTTPException(status_code=404, detail="Not Found")
    return field_id


def _extract_raw(req: PlaceRequest) -> str:
    if req.raw is not None:
        return req.raw
    if req.utterance is not None:
        raw_obj = req.utterance.get("raw")
        if isinstance(raw_obj, str):
            return raw_obj
    raise HTTPException(status_code=422, detail="raw required")


@app.post("/place")
def place(req: PlaceRequest) -> Response:
    raw = _extract_raw(req)
    result = _kernel.place(
        raw=raw,
        context=req.context,
        addressing=req.addressing,
        metadata=req.metadata,
    )
    return _json_response(result)


@app.post("/observe")
def observe() -> Response:
    result = _kernel.observe()
    return _json_response(result)


@app.get("/events")
def events() -> Response:
    result: List[KernelEventObj] = list(_kernel.get_events())
    return _json_response(result)


@app.get("/edges")
def edges() -> Response:
    result: List[Edge] = list(_kernel.get_edges())
    return _json_response(result)


@app.post("/attest")
def attest(req: AttestRequest) -> Response:
    result = _kernel.record_attestation(
        witness_id=req.witness_id,
        attestation_kind=req.attestation_kind,
        attestation_tag=req.attestation_tag,
        payload=req.payload,
        target=req.target,
    )
    return _json_response(result)


@app.post("/v0.1/place")
def v1_place(req: PlaceRequest) -> Response:
    context = req.context if req.context is not None else {}
    field_id_obj = context.get("field_id")
    field_id: Optional[str]
    if isinstance(field_id_obj, str):
        field_id = field_id_obj
    elif field_id_obj is None:
        field_id = None
    else:
        field_id = str(field_id_obj)
    _assert_field_id_or_default(field_id)

    raw = _extract_raw(req)
    result = _kernel.place(raw=raw, context=context, addressing=req.addressing, metadata=req.metadata)

    payload: Dict[str, Any] = {
        "field_id": result.field_id,
        "clock": {"tick": result.clock.tick, "causal_epoch": result.clock.causal_epoch},
        "placement_event": result.placement_event,
        "observe": result.observe,
        "diff_exempt_metadata_keys": [],
    }
    return _json_response(payload)


@app.post("/v0.1/evaluate_eligibility")
def v1_evaluate_eligibility(req: EligibilityRequest) -> Response:
    _assert_field_id_or_default(req.field_id)
    observed = _kernel.observe()

    eligible: Dict[str, List[Dict[str, str]]] = {}
    for frontier_id, candidates in observed.eligible_by_frontier.items():
        if frontier_id not in req.frontier_ids:
            continue
        eligible[frontier_id] = [{"id": candidate.id} for candidate in candidates]

    payload = {
        "eligible_by_frontier": eligible,
        "refusals": observed.refusals,
    }
    return _json_response(payload)


@app.get("/v0.1/ceg/{field_id}")
def v1_ceg(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    result = {
        "events": list(_kernel.get_events()),
        "edges": list(_kernel.get_edges()),
    }
    return _json_response(result)


@app.get("/v0.1/frontiers/{field_id}")
def v1_frontiers(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    sorted_frontiers: List[Frontier] = sorted(_kernel.frontiers, key=lambda f: f.id)
    result = {
        "frontiers": [{"id": frontier.id, "status": frontier.status} for frontier in sorted_frontiers]
    }
    return _json_response(result)


@app.post("/v0.1/request_commit")
def v1_request_commit(req: RequestCommitBody) -> Response:
    _assert_field_id_or_default(req.field_id)
    # Structural no-op: kernel does not auto-commit.
    result = {
        "accepted": True,
        "field_id": req.field_id,
        "frontier_id": req.frontier_id,
        "candidate_id": req.candidate_id,
    }
    return _json_response(result)


@app.post("/v0.1/attest")
def v1_attest(req: V1AttestRequest) -> Response:
    _assert_field_id_or_default(req.field_id)
    witness_obj = req.attestation.get("witness_id")
    kind_obj = req.attestation.get("kind")
    tag_obj = req.attestation.get("tag")
    payload_obj = req.attestation.get("payload")

    witness_id = witness_obj if isinstance(witness_obj, str) else "unknown"
    attest_kind = kind_obj if isinstance(kind_obj, str) else "unknown"
    attestation_tag = tag_obj if isinstance(tag_obj, str) else None
    payload = payload_obj if isinstance(payload_obj, dict) else {}

    recorded = _kernel.record_attestation(
        witness_id=witness_id,
        attestation_kind=attest_kind,
        attestation_tag=attestation_tag,
        payload=payload,
        target=req.target,
    )

    if attest_kind == "lotus":
        _state.lotus_attestation_count += 1

    committed = {
        "id": recorded["id"],
        "kind": "commitment",
        "target": req.target,
    }
    result = {
        "accepted": True,
        "recorded": recorded,
        "committed": committed,
    }
    return _json_response(result)


@app.get("/v0.1/field/{field_id}")
def v1_field(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    field_obj = {
        "field_id": _field.field_id,
        "lotus": {"attestation_count": _state.lotus_attestation_count},
    }
    return _json_response({"field": field_obj})


@app.post("/v0.1/replay")
def v1_replay(req: ReplayRequest) -> Response:
    bundle = req.bundle
    field_id_obj = bundle.get("field_id")
    field_id = field_id_obj if isinstance(field_id_obj, str) else _field.field_id
    _assert_field_id_or_default(field_id)

    canonical = {
        "field_id": field_id,
        "placements": bundle.get("placements", []),
        "attestations": bundle.get("attestations", []),
        "metadata": bundle.get("metadata", {}),
    }
    return _json_response({"canonical": canonical})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("shygazun.kernel_service:app", host="0.0.0.0", port=8000, reload=False)

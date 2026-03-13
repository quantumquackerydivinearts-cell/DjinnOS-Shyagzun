from __future__ import annotations

from fastapi import FastAPI, HTTPException #type: ignore

from shygazun.api import KernelRegistry
from shygazun.api.models import (
    PlaceRequest,
    EligibilityRequest,
    AttestRequest,
    ReplayRequest,
)
from shygazun.api.KernelRegistry import KernelRegistry

STATE = KernelRegistry()


app = FastAPI(title="Shygazun Kernel API", version="0.1.1")


# ------------------------------------------------------------
# POST /v0.1/place
# ------------------------------------------------------------

@app.post("/v0.1/place")
def place(req: PlaceRequest):
    field_id = req.context.get("field_id") if req.context else None
    if not field_id:
        raise HTTPException(status_code=400, detail="field_id required in context")

    kernel = STATE.get_or_create_kernel(field_id)

    result = kernel.place(
        raw=req.utterance.get("raw", ""),
        context=req.context,
    )

    return {
        "field_id": result.field_id,
        "clock": {"tick": result.clock.tick, "causal_epoch": result.clock.causal_epoch},
        "placement_event": result.placement_event,
        "observe": {
            "candidates_by_frontier": {
                k: [c.id for c in v] for k, v in result.observe.candidates_by_frontier.items()
            },
            "eligible_by_frontier": {
                k: [c.id for c in v] for k, v in result.observe.eligible_by_frontier.items()
            },
            "eligibility_events": result.observe.eligibility_events,
            "refusals": result.observe.refusals,
        },
    }


# ------------------------------------------------------------
# POST /v0.1/evaluate_eligibility
# ------------------------------------------------------------

@app.post("/v0.1/evaluate_eligibility")
def evaluate_eligibility(req: EligibilityRequest):
    kernel = STATE.get_or_create_kernel(req.field_id)
    obs = kernel.observe()

    return {
        "eligible_by_frontier": {
            k: [{"id": c.id} for c in v]
            for k, v in obs.eligible_by_frontier.items()
            if k in req.frontier_ids
        },
        "refusals": obs.refusals,
    }


# ------------------------------------------------------------
# GET /v0.1/ceg/{field_id}
# ------------------------------------------------------------

@app.get("/v0.1/ceg/{field_id}")
def get_ceg(field_id: str):
    kernel = STATE.get_or_create_kernel(field_id)
    return {
        "events": kernel.get_events(),
        "edges": kernel.get_edges(),
    }


# ------------------------------------------------------------
# GET /v0.1/frontiers/{field_id}
# ------------------------------------------------------------

@app.get("/v0.1/frontiers/{field_id}")
def get_frontiers(field_id: str):
    kernel = STATE.get_or_create_kernel(field_id)
    return {
        "frontiers": [
            {
                "id": f.id,
                "status": f.status,
            }
            for f in kernel.frontiers
        ]
    }


# ------------------------------------------------------------
# POST /v0.1/attest
# ------------------------------------------------------------

@app.post("/v0.1/attest")
def attest(req: AttestRequest):
    kernel = STATE.get_or_create_kernel(req.field_id)

    a = req.attestation

    evt = kernel.record_attestation(
        witness_id=a.get("witness_id", "unknown"),
        attestation_kind=a.get("kind", "unknown"),
        attestation_tag=a.get("tag"),
        payload=a.get("payload", {}),
        target=req.target,
    )

    return {
        "accepted": True,
        "recorded": evt,
    }



# ------------------------------------------------------------
# POST /v0.1/replay
# ------------------------------------------------------------

@app.post("/v0.1/replay")
def replay(req: ReplayRequest):
    """
    Phase D1: minimal replay surface.
    Determinism is enforced by kernel hashing, not API logic.
    """
    bundle = req.bundle
    field_id = bundle.get("field_id")
    if not field_id:
        raise HTTPException(status_code=400, detail="field_id required")

    kernel = STATE.get_or_create_kernel(field_id)

    # NOTE: full replay execution is Phase D2.
    # Here we return a canonical echo surface for conformance wiring.
    canonical = {
        "field_id": field_id,
        "placements": bundle.get("placements", []),
        "attestations": bundle.get("attestations", []),
    }

    return {
        "canonical": canonical
    }

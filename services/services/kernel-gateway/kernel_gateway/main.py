from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests


ALLOWED_ACTIONS = frozenset(
    {
        "place",
        "observe",
        "events",
        "edges",
        "attest",
    }
)


class KernelActionRequest(BaseModel):
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    kernel_base_url: str = "http://127.0.0.1:8000"


def _dispatch(action: str, payload: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    if action == "place":
        resp = requests.post(f"{base_url}/place", json=payload, timeout=20)
    elif action == "observe":
        resp = requests.post(f"{base_url}/observe", json=payload, timeout=20)
    elif action == "events":
        resp = requests.get(f"{base_url}/events", timeout=20)
    elif action == "edges":
        resp = requests.get(f"{base_url}/edges", timeout=20)
    elif action == "attest":
        resp = requests.post(f"{base_url}/attest", json=payload, timeout=20)
    else:
        raise RuntimeError("unreachable")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"kernel_gateway_error:{resp.status_code}:{action}")

    data: Any = resp.json()
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    raise HTTPException(status_code=502, detail=f"kernel_gateway_shape_error:{action}")


app = FastAPI(title="Kernel Gateway", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/kernel-gateway/execute")
def execute(req: KernelActionRequest) -> Dict[str, Any]:
    if req.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=403, detail=f"forbidden_action:{req.action}")
    return _dispatch(req.action, req.payload, req.kernel_base_url)


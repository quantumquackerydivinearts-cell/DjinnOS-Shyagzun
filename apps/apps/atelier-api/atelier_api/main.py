from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .capabilities import CapabilityContext, parse_capabilities, require_capability
from .config import Settings, load_settings
from .kernel_client import HttpKernelClient, KernelClient
from .roles import RoleContext, role_allows
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse
from .workshop import (
    ArtisanIdentity,
    WorkshopContext,
    WorkshopScope,
    enforce_place_scope,
    parse_scopes,
)


class PlaceInput(BaseModel):
    raw: str
    context: Dict[str, Any] = Field(default_factory=dict)


class AttestInput(BaseModel):
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


def _capability_context(
    x_atelier_capabilities: Optional[str] = Header(default=None),
    x_atelier_actor: Optional[str] = Header(default=None),
) -> CapabilityContext:
    if x_atelier_actor is None or not x_atelier_actor.strip():
        raise HTTPException(status_code=401, detail="missing_actor")
    if x_atelier_capabilities is None:
        raise HTTPException(status_code=403, detail="missing_capabilities")
    return CapabilityContext(actor_id=x_atelier_actor, capabilities=parse_capabilities(x_atelier_capabilities))


def _kernel_client() -> KernelClient:
    settings: Settings = load_settings()
    return HttpKernelClient(base_url=settings.kernel_base_url)


def _workshop_context(
    x_artisan_id: Optional[str] = Header(default=None),
    x_workshop_id: Optional[str] = Header(default=None),
    x_workshop_scopes: Optional[str] = Header(default=None),
) -> WorkshopContext:
    if x_artisan_id is None or not x_artisan_id.strip():
        raise HTTPException(status_code=401, detail="missing_artisan_id")
    if x_workshop_id is None or not x_workshop_id.strip():
        raise HTTPException(status_code=401, detail="missing_workshop_id")
    if x_workshop_scopes is None:
        raise HTTPException(status_code=403, detail="missing_workshop_scopes")
    return WorkshopContext(
        identity=ArtisanIdentity(artisan_id=x_artisan_id, workshop_id=x_workshop_id),
        scope=WorkshopScope(scopes=parse_scopes(x_workshop_scopes)),
    )


def _role_context(x_artisan_role: Optional[str] = Header(default=None)) -> RoleContext:
    if x_artisan_role is None or not x_artisan_role.strip():
        raise HTTPException(status_code=401, detail="missing_artisan_role")
    return RoleContext(role=x_artisan_role.strip().lower())


def _enforce(ctx: CapabilityContext, capability: str) -> None:
    try:
        require_capability(ctx, [capability])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _enforce_role(role: RoleContext, capability: str) -> None:
    if not role_allows(role.role, capability):
        raise HTTPException(status_code=403, detail=f"role_denied:{role.role}:{capability}")


app = FastAPI(title="Atelier API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/atelier/place")
def place(
    payload: PlaceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    try:
        enforce_place_scope(workshop, payload.context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return kernel.place(payload.raw, context=payload.context)


@app.post("/v1/atelier/observe")
def observe(
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> ObserveResponse:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return kernel.observe()


@app.get("/v1/atelier/timeline")
def timeline(
    last: Optional[int] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> Sequence[KernelEventObj]:
    _enforce(ctx, "kernel.timeline")
    _enforce_role(role, "kernel.timeline")
    events = list(kernel.events())
    if last is None:
        return events
    if last < 0:
        raise HTTPException(status_code=400, detail="invalid_last")
    return events[-last:]


@app.get("/v1/atelier/edges")
def edges(
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> Sequence[EdgeObj]:
    _enforce(ctx, "kernel.edges")
    _enforce_role(role, "kernel.edges")
    return kernel.edges()


@app.get("/v1/atelier/frontiers")
def frontiers(
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> Sequence[FrontierObj]:
    _enforce(ctx, "kernel.frontiers")
    _enforce_role(role, "kernel.frontiers")
    return sorted(list(kernel.frontiers()), key=lambda f: f["id"])


@app.post("/v1/atelier/attest")
def attest(
    payload: AttestInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    kernel: KernelClient = Depends(_kernel_client),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.attest")
    _enforce_role(role, "kernel.attest")
    return kernel.attest(
        witness_id=payload.witness_id,
        attestation_kind=payload.attestation_kind,
        attestation_tag=payload.attestation_tag,
        payload=payload.payload,
        target=payload.target,
    )

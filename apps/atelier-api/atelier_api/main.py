from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .business_schemas import (
    ArtisanBootstrapInput,
    ArtisanAccessIssueInput,
    ArtisanAccessIssueOut,
    ArtisanAccessStatusOut,
    ArtisanAccessVerifyInput,
    BookingCreate,
    BookingOut,
    ClientCreate,
    ClientOut,
    ContactCreate,
    ContactOut,
    InventoryItemCreate,
    InventoryItemOut,
    InventoryAdjustInput,
    CharacterDictionaryCreate,
    CharacterDictionaryOut,
    NamedQuestCreate,
    NamedQuestOut,
    JournalEntryCreate,
    JournalEntryOut,
    LayerNodeCreate,
    LayerNodeOut,
    LayerEdgeCreate,
    LayerEdgeOut,
    LayerEventOut,
    LayerTraceOut,
    FunctionStoreCreate,
    FunctionStoreOut,
    PlayerStateApplyInput,
    PlayerStateOut,
    GameTickInput,
    GameTickOut,
    LevelApplyInput,
    LevelApplyOut,
    SkillTrainInput,
    SkillTrainOut,
    PerkUnlockInput,
    PerkUnlockOut,
    AlchemyCraftInput,
    AlchemyCraftOut,
    AlchemyInterfaceInput,
    AlchemyInterfaceOut,
    AlchemyCrystalInput,
    AlchemyCrystalOut,
    BlacksmithForgeInput,
    BlacksmithForgeOut,
    CombatResolveInput,
    CombatResolveOut,
    MarketQuoteInput,
    MarketQuoteOut,
    MarketTradeInput,
    MarketTradeOut,
    RadioEvaluateInput,
    RadioEvaluateOut,
    InfernalMeditationUnlockInput,
    InfernalMeditationUnlockOut,
    AssetManifestCreate,
    AssetManifestOut,
    ContentValidateInput,
    ContentValidateOut,
    RealmOut,
    RealmValidateInput,
    RealmValidateOut,
    SceneCreateInput,
    SceneUpdateInput,
    SceneOut,
    SceneEmitOut,
    SceneCompileInput,
    WorldRegionLoadInput,
    WorldRegionUnloadInput,
    WorldRegionOut,
    WorldRegionUnloadOut,
    WorldStreamStatusOut,
    RealmCoinOut,
    RealmMarketOut,
    GateEvaluateInput,
    GateEvaluateOut,
    RuntimeConsumeInput,
    RuntimeConsumeOut,
    DialogueEmitInput,
    DialogueEmitOut,
    VitriolApplyRulerInfluenceInput,
    VitriolApplyOut,
    VitriolClearExpiredInput,
    VitriolClearExpiredOut,
    VitriolComputeInput,
    VitriolComputeOut,
    DjinnApplyInput,
    DjinnApplyOut,
    LeadCreate,
    LeadOut,
    LessonCreate,
    LessonOut,
    LessonProgressOut,
    LessonConsumeInput,
    ModuleCreate,
    ModuleOut,
    OrderCreate,
    OrderOut,
    PublicCommissionInquiryCreate,
    PublicCommissionQuoteOut,
    QuoteCreate,
    QuoteOut,
    HeadlessQuestEmitInput,
    HeadlessQuestEmitOut,
    MeditationEmitInput,
    MeditationEmitOut,
    SceneGraphEmitInput,
    SceneGraphEmitOut,
    SaveExportOut,
    SupplierCreate,
    SupplierOut,
)
from .rendering_schemas import (
    RendererTablesInput,
    RendererTablesOut,
    IsometricRenderContractInput,
    IsometricRenderContractOut,
    RenderGraphContractInput,
    RenderGraphContractOut,
)
from .capabilities import CapabilityContext, parse_capabilities, require_capability
from .config import Settings, load_settings
from .db import get_db
from .kernel_client import HttpKernelClient, KernelClient
from .kernel_integration import KernelIntegrationService
from .privacy_manifest import build_privacy_manifest
from .repositories import AtelierRepository
from .roles import ROLE_STEWARD, RoleContext, role_allows
from .services import AtelierService
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


class AmbroflowPlaceInput(BaseModel):
    raw: str
    speaker_id: Optional[str] = None
    scene_id: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class AttestInput(BaseModel):
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


class AkinenwunLookupInput(BaseModel):
    akinenwun: str
    mode: str = "prose"
    ingest: bool = True
    policy: Dict[str, Any] = Field(default_factory=dict)


class AdminGateVerifyInput(BaseModel):
    gate_code: str


def _ambroflow_context_from_payload(payload: AmbroflowPlaceInput) -> Dict[str, Any]:
    context: Dict[str, Any] = dict(payload.context)
    context["speaker_id"] = payload.speaker_id or "player"
    if payload.scene_id is not None:
        context["scene_id"] = payload.scene_id
    if payload.tags:
        context["tags"] = dict(payload.tags)
    if payload.metadata:
        context["metadata"] = dict(payload.metadata)
    return context


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


def _repository(db: Session = Depends(get_db)) -> AtelierRepository:
    return AtelierRepository(db)


def _kernel_integration(kernel: KernelClient = Depends(_kernel_client)) -> KernelIntegrationService:
    return KernelIntegrationService(kernel)


def _atelier_service(
    repo: AtelierRepository = Depends(_repository),
    kernel: KernelIntegrationService = Depends(_kernel_integration),
) -> AtelierService:
    return AtelierService(repo=repo, kernel=kernel)


def _kernel_only_service(kernel: KernelIntegrationService = Depends(_kernel_integration)) -> AtelierService:
    return AtelierService(repo=None, kernel=kernel)


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


def _admin_gate_token(x_admin_gate_token: Optional[str] = Header(default=None)) -> Optional[str]:
    return x_admin_gate_token


def _settings() -> Settings:
    return load_settings()


def _enforce(ctx: CapabilityContext, capability: str) -> None:
    try:
        require_capability(ctx, [capability])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _enforce_role(role: RoleContext, capability: str) -> None:
    if not role_allows(role.role, capability):
        raise HTTPException(status_code=403, detail=f"role_denied:{role.role}:{capability}")


def _expected_admin_gate_token(settings: Settings, actor_id: str, workshop_id: str) -> str:
    payload = f"{settings.admin_gate_code}:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _admin_gate_verified(
    *,
    settings: Settings,
    role: RoleContext,
    actor_id: str,
    workshop_id: str,
    token: Optional[str],
) -> bool:
    if role.role != ROLE_STEWARD:
        return False
    if token is None or not token:
        return False
    return token == _expected_admin_gate_token(settings, actor_id, workshop_id)


def _enforce_admin_gate(
    *,
    settings: Settings,
    role: RoleContext,
    actor_id: str,
    workshop_id: str,
    token: Optional[str],
) -> None:
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    if not _admin_gate_verified(
        settings=settings,
        role=role,
        actor_id=actor_id,
        workshop_id=workshop_id,
        token=token,
    ):
        raise HTTPException(status_code=403, detail="admin_gate_required")


app = FastAPI(title="Atelier API", version="0.1.0")
_boot_settings = load_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_boot_settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(svc: AtelierService = Depends(_atelier_service)) -> Dict[str, str]:
    svc.health()
    return {"status": "ok"}


@app.get("/public/privacy/manifest")
def privacy_manifest() -> Dict[str, Any]:
    return build_privacy_manifest()


@app.post("/v1/access/artisan-id/issue")
def artisan_id_issue(
    payload: ArtisanAccessIssueInput,
    _: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ArtisanAccessIssueOut:
    return svc.issue_artisan_access_code(
        artisan_id=workshop.identity.artisan_id,
        role=role.role,
        workshop_id=workshop.identity.workshop_id,
        payload=payload,
    )


@app.post("/v1/access/artisan-id/verify")
def artisan_id_verify(
    payload: ArtisanAccessVerifyInput,
    _: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ArtisanAccessStatusOut:
    return svc.verify_artisan_access_code(
        artisan_id=workshop.identity.artisan_id,
        role=role.role,
        workshop_id=workshop.identity.workshop_id,
        payload=payload,
    )


@app.get("/v1/access/artisan-id/status")
def artisan_id_status(
    _: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ArtisanAccessStatusOut:
    return svc.artisan_access_status(
        artisan_id=workshop.identity.artisan_id,
        role=role.role,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/admin/artisans/bootstrap")
def bootstrap_artisan_account(
    payload: ArtisanBootstrapInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> ArtisanAccessIssueOut:
    _enforce(ctx, "kernel.place")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    if payload.gate_code != settings.admin_gate_code:
        raise HTTPException(status_code=403, detail="invalid_admin_gate")
    return svc.bootstrap_artisan_access(
        role=ROLE_STEWARD,
        workshop_id=workshop.identity.workshop_id,
        payload=payload,
    )


@app.get("/v1/atelier/admin/gate/status")
def admin_gate_status(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
) -> Dict[str, Any]:
    verified = _admin_gate_verified(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return {
        "verified_admin": verified,
        "required_role": ROLE_STEWARD,
        "placement_tool_enabled": verified,
    }


@app.post("/v1/atelier/admin/gate/verify")
def admin_gate_verify(
    payload: AdminGateVerifyInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    settings: Settings = Depends(_settings),
) -> Dict[str, Any]:
    _enforce(ctx, "kernel.place")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    if payload.gate_code != settings.admin_gate_code:
        raise HTTPException(status_code=403, detail="invalid_admin_gate")
    return {
        "verified_admin": True,
        "required_role": ROLE_STEWARD,
        "admin_gate_token": _expected_admin_gate_token(
            settings,
            ctx.actor_id,
            workshop.identity.workshop_id,
        ),
    }


@app.post("/v1/atelier/place")
def place(
    payload: PlaceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    try:
        enforce_place_scope(workshop, payload.context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return svc.emit_placement(
        raw=payload.raw,
        context=payload.context,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/ambroflow/place")
def ambroflow_place(
    payload: AmbroflowPlaceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    context = _ambroflow_context_from_payload(payload)
    try:
        enforce_place_scope(workshop, context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return svc.emit_placement(
        raw=payload.raw,
        context=context,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/atelier/observe")
def observe(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ObserveResponse:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.observe(actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.get("/v1/ambroflow/semantic-value")
def ambroflow_semantic_value(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Dict[str, Any]:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    observed = svc.observe(actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)
    return {
        "clock": observed["clock"],
        "candidates_by_frontier": observed["candidates_by_frontier"],
        "eligible_by_frontier": observed["eligible_by_frontier"],
        "refusals": observed["refusals"],
    }


@app.post("/v1/ambroflow/akinenwun/lookup")
def ambroflow_akinenwun_lookup(
    payload: AkinenwunLookupInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.akinenwun_lookup(
        akinenwun=payload.akinenwun,
        mode=payload.mode,
        ingest=payload.ingest,
        policy=payload.policy,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.get("/v1/atelier/timeline")
def timeline(
    last: Optional[int] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[KernelEventObj]:
    _enforce(ctx, "kernel.timeline")
    _enforce_role(role, "kernel.timeline")
    events = list(svc.timeline(actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id))
    if last is None:
        return events
    if last < 0:
        raise HTTPException(status_code=400, detail="invalid_last")
    return events[-last:]


@app.get("/v1/atelier/edges")
def edges(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[EdgeObj]:
    _enforce(ctx, "kernel.edges")
    _enforce_role(role, "kernel.edges")
    return svc.edges(actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.get("/v1/atelier/frontiers")
def frontiers(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[FrontierObj]:
    _enforce(ctx, "kernel.frontiers")
    _enforce_role(role, "kernel.frontiers")
    return sorted(list(svc.frontiers(actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)), key=lambda f: f["id"])


@app.post("/v1/atelier/attest")
def attest(
    payload: AttestInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.attest")
    _enforce_role(role, "kernel.attest")
    return svc.attest(
        witness_id=payload.witness_id,
        attestation_kind=payload.attestation_kind,
        attestation_tag=payload.attestation_tag,
        payload=payload.payload,
        target=payload.target,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.get("/v1/crm/contacts")
def list_contacts(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ContactOut]:
    _enforce(ctx, "crm.contacts.read")
    _enforce_role(role, "crm.contacts.read")
    return svc.list_contacts(workspace_id=workspace_id)


@app.post("/v1/crm/contacts")
def create_contact(
    payload: ContactCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContactOut:
    _enforce(ctx, "crm.contacts.write")
    _enforce_role(role, "crm.contacts.write")
    return svc.create_contact(payload)


@app.get("/v1/booking")
def list_bookings(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[BookingOut]:
    _enforce(ctx, "booking.read")
    _enforce_role(role, "booking.read")
    return svc.list_bookings(workspace_id=workspace_id)


@app.post("/v1/booking")
def create_booking(
    payload: BookingCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> BookingOut:
    _enforce(ctx, "booking.write")
    _enforce_role(role, "booking.write")
    return svc.create_booking(payload)


@app.get("/v1/lessons")
def list_lessons(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LessonOut]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_lessons(workspace_id=workspace_id)


@app.post("/v1/lessons")
def create_lesson(
    payload: LessonCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LessonOut:
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    return svc.create_lesson(payload)


@app.get("/v1/lessons/progress")
def list_lesson_progress(
    workspace_id: str,
    actor_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[LessonProgressOut]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_lesson_progress(workspace_id=workspace_id, actor_id=actor_id)


@app.post("/v1/lessons/consume")
def consume_lesson(
    payload: LessonConsumeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> LessonProgressOut:
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    return svc.consume_lesson(payload)


@app.get("/v1/modules")
def list_modules(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ModuleOut]:
    _enforce(ctx, "module.read")
    _enforce_role(role, "module.read")
    return svc.list_modules(workspace_id=workspace_id)


@app.post("/v1/modules")
def create_module(
    payload: ModuleCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ModuleOut:
    _enforce(ctx, "module.write")
    _enforce_role(role, "module.write")
    return svc.create_module(payload)


@app.get("/v1/leads")
def list_leads(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LeadOut]:
    _enforce(ctx, "lead.read")
    _enforce_role(role, "lead.read")
    return svc.list_leads(workspace_id=workspace_id)


@app.post("/v1/leads")
def create_lead(
    payload: LeadCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LeadOut:
    _enforce(ctx, "lead.write")
    _enforce_role(role, "lead.write")
    return svc.create_lead(payload)


@app.get("/v1/clients")
def list_clients(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ClientOut]:
    _enforce(ctx, "client.read")
    _enforce_role(role, "client.read")
    return svc.list_clients(workspace_id=workspace_id)


@app.post("/v1/clients")
def create_client(
    payload: ClientCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ClientOut:
    _enforce(ctx, "client.write")
    _enforce_role(role, "client.write")
    return svc.create_client(payload)


@app.get("/v1/quotes")
def list_quotes(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[QuoteOut]:
    _enforce(ctx, "quote.read")
    _enforce_role(role, "quote.read")
    return svc.list_quotes(workspace_id=workspace_id)


@app.post("/v1/quotes")
def create_quote(
    payload: QuoteCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuoteOut:
    _enforce(ctx, "quote.write")
    _enforce_role(role, "quote.write")
    return svc.create_quote(payload)


@app.get("/v1/orders")
def list_orders(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[OrderOut]:
    _enforce(ctx, "order.read")
    _enforce_role(role, "order.read")
    return svc.list_orders(workspace_id=workspace_id)


@app.post("/v1/orders")
def create_order(
    payload: OrderCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> OrderOut:
    _enforce(ctx, "order.write")
    _enforce_role(role, "order.write")
    return svc.create_order(payload)


@app.get("/v1/inventory")
def list_inventory_items(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[InventoryItemOut]:
    _enforce(ctx, "inventory.read")
    _enforce_role(role, "inventory.read")
    return svc.list_inventory_items(workspace_id=workspace_id)


@app.post("/v1/inventory")
def create_inventory_item(
    payload: InventoryItemCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> InventoryItemOut:
    _enforce(ctx, "inventory.write")
    _enforce_role(role, "inventory.write")
    return svc.create_inventory_item(payload)


@app.get("/v1/game/characters")
def list_character_dictionary_entries(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[CharacterDictionaryOut]:
    _enforce(ctx, "character.read")
    _enforce_role(role, "character.read")
    return svc.list_character_dictionary_entries(workspace_id=workspace_id)


@app.post("/v1/game/characters")
def create_character_dictionary_entry(
    payload: CharacterDictionaryCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> CharacterDictionaryOut:
    _enforce(ctx, "character.write")
    _enforce_role(role, "character.write")
    return svc.create_character_dictionary_entry(payload)


@app.get("/v1/game/quests")
def list_named_quests(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[NamedQuestOut]:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    return svc.list_named_quests(workspace_id=workspace_id)


@app.post("/v1/game/quests")
def create_named_quest(
    payload: NamedQuestCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> NamedQuestOut:
    _enforce(ctx, "quest.write")
    _enforce_role(role, "quest.write")
    return svc.create_named_quest(payload)


@app.get("/v1/game/journal")
def list_journal_entries(
    workspace_id: str,
    actor_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[JournalEntryOut]:
    _enforce(ctx, "journal.read")
    _enforce_role(role, "journal.read")
    return svc.list_journal_entries(workspace_id=workspace_id, actor_id=actor_id)


@app.post("/v1/game/journal")
def create_journal_entry(
    payload: JournalEntryCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> JournalEntryOut:
    _enforce(ctx, "journal.write")
    _enforce_role(role, "journal.write")
    return svc.create_journal_entry(payload)


@app.get("/v1/game/scenes")
def list_scenes(
    workspace_id: str,
    realm_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[SceneOut]:
    _enforce(ctx, "scene.read")
    _enforce_role(role, "scene.read")
    return svc.list_scenes(workspace_id=workspace_id, realm_id=realm_id)


@app.get("/v1/game/scenes/{scene_id:path}")
def get_scene(
    scene_id: str,
    workspace_id: str,
    realm_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SceneOut:
    _enforce(ctx, "scene.read")
    _enforce_role(role, "scene.read")
    scene = svc.get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene_not_found")
    return scene


@app.post("/v1/game/scenes")
def create_scene(
    payload: SceneCreateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SceneOut:
    _enforce(ctx, "scene.write")
    _enforce_role(role, "scene.write")
    try:
        return svc.create_scene(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/v1/game/scenes/{scene_id:path}")
def update_scene(
    scene_id: str,
    payload: SceneUpdateInput,
    workspace_id: str,
    realm_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SceneOut:
    _enforce(ctx, "scene.write")
    _enforce_role(role, "scene.write")
    try:
        return svc.update_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/scenes/{scene_id:path}/emit")
def emit_scene_from_library(
    scene_id: str,
    workspace_id: str,
    realm_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> SceneEmitOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    try:
        return svc.emit_scene_from_library(
            workspace_id=workspace_id,
            realm_id=realm_id,
            scene_id=scene_id,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/scenes/compile")
def compile_scene_from_cobra(
    payload: SceneCompileInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SceneOut:
    _enforce(ctx, "scene.write")
    _enforce_role(role, "scene.write")
    try:
        return svc.create_scene_from_cobra(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/world/regions")
def list_world_regions(
    workspace_id: str,
    realm_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[WorldRegionOut]:
    _enforce(ctx, "scene.read")
    _enforce_role(role, "scene.read")
    return svc.list_world_regions(workspace_id=workspace_id, realm_id=realm_id)


@app.post("/v1/game/world/regions/load")
def load_world_region(
    payload: WorldRegionLoadInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> WorldRegionOut:
    _enforce(ctx, "scene.write")
    _enforce_role(role, "scene.write")
    try:
        return svc.load_world_region(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/world/regions/unload")
def unload_world_region(
    payload: WorldRegionUnloadInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> WorldRegionUnloadOut:
    _enforce(ctx, "scene.write")
    _enforce_role(role, "scene.write")
    try:
        return svc.unload_world_region(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/world/stream/status")
def world_stream_status(
    workspace_id: str,
    realm_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> WorldStreamStatusOut:
    _enforce(ctx, "scene.read")
    _enforce_role(role, "scene.read")
    return svc.world_stream_status(workspace_id=workspace_id, realm_id=realm_id)


@app.get("/v1/game/world/coins")
def list_world_coins(
    realm_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[RealmCoinOut]:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.list_realm_coins(realm_id=realm_id)


@app.get("/v1/game/world/markets")
def list_world_markets(
    realm_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[RealmMarketOut]:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.list_realm_markets(realm_id=realm_id)


@app.get("/v1/game/layers/nodes")
def list_layer_nodes(
    workspace_id: str,
    layer_index: Optional[int] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LayerNodeOut]:
    _enforce(ctx, "layer.read")
    _enforce_role(role, "layer.read")
    return svc.list_layer_nodes(workspace_id=workspace_id, layer_index=layer_index)


@app.post("/v1/game/layers/nodes")
def create_layer_node(
    payload: LayerNodeCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LayerNodeOut:
    _enforce(ctx, "layer.write")
    _enforce_role(role, "layer.write")
    return svc.create_layer_node(payload=payload, actor_id=ctx.actor_id)


@app.get("/v1/game/layers/edges")
def list_layer_edges(
    workspace_id: str,
    node_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LayerEdgeOut]:
    _enforce(ctx, "layer.read")
    _enforce_role(role, "layer.read")
    return svc.list_layer_edges(workspace_id=workspace_id, node_id=node_id)


@app.post("/v1/game/layers/edges")
def create_layer_edge(
    payload: LayerEdgeCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LayerEdgeOut:
    _enforce(ctx, "layer.write")
    _enforce_role(role, "layer.write")
    try:
        return svc.create_layer_edge(payload=payload, actor_id=ctx.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/layers/events")
def list_layer_events(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LayerEventOut]:
    _enforce(ctx, "layer.read")
    _enforce_role(role, "layer.read")
    return svc.list_layer_events(workspace_id=workspace_id)


@app.get("/v1/game/layers/trace/{node_id}")
def trace_layer_node(
    node_id: str,
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LayerTraceOut:
    _enforce(ctx, "layer.read")
    _enforce_role(role, "layer.read")
    try:
        return svc.trace_layer_node(workspace_id=workspace_id, node_id=node_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/game/functions")
def list_function_store_entries(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[FunctionStoreOut]:
    _enforce(ctx, "function.read")
    _enforce_role(role, "function.read")
    return svc.list_function_store_entries(workspace_id=workspace_id)


@app.post("/v1/game/functions")
def create_function_store_entry(
    payload: FunctionStoreCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> FunctionStoreOut:
    _enforce(ctx, "function.write")
    _enforce_role(role, "function.write")
    return svc.create_function_store_entry(payload=payload, actor_id=ctx.actor_id)


@app.post("/v1/game/inventory/adjust")
def adjust_inventory_item(
    payload: InventoryAdjustInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> InventoryItemOut:
    _enforce(ctx, "inventory.write")
    _enforce_role(role, "inventory.write")
    updated = svc.adjust_inventory_item(payload)
    svc.emit_placement(
        raw=f"inventory.adjust {payload.inventory_item_id} delta={payload.delta} reason={payload.reason}",
        context={
            "workspace_id": payload.workspace_id,
            "inventory_item_id": payload.inventory_item_id,
            "delta": payload.delta,
            "reason": payload.reason,
            "source": "game_inventory_adjust",
        },
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )
    return updated


@app.post("/v1/game/quests/headless/emit")
def emit_headless_quest(
    payload: HeadlessQuestEmitInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> HeadlessQuestEmitOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.emit_headless_quest(
        payload=payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/game/meditation/emit")
def emit_meditation(
    payload: MeditationEmitInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> MeditationEmitOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.emit_meditation(
        payload=payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/game/scene-graph/emit")
def emit_scene_graph(
    payload: SceneGraphEmitInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> SceneGraphEmitOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    try:
        return svc.emit_scene_graph(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/saves/export")
def export_game_save(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> SaveExportOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.export_save_snapshot(
        workspace_id=workspace_id,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.get("/v1/game/state")
def get_game_state(
    workspace_id: str,
    actor_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> PlayerStateOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.get_player_state(workspace_id=workspace_id, actor_id=actor_id)


@app.post("/v1/game/state/apply")
def apply_game_state(
    payload: PlayerStateApplyInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> PlayerStateOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.apply_player_state(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/state/tick")
def tick_game_state(
    payload: GameTickInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> GameTickOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.game_tick(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.get("/v1/assets/manifests")
def list_asset_manifests(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[AssetManifestOut]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_asset_manifests(workspace_id=workspace_id)


@app.post("/v1/assets/manifests")
def create_asset_manifest(
    payload: AssetManifestCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> AssetManifestOut:
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    validation = svc.validate_realm(RealmValidateInput(realm_id=payload.realm_id))
    if not validation.ok:
        raise HTTPException(status_code=400, detail=f"unknown_realm:{payload.realm_id}")
    return svc.create_asset_manifest(payload)


@app.get("/v1/realms")
def list_realms(
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Sequence[RealmOut]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_realms()


@app.post("/v1/realms/validate")
def validate_realm(
    payload: RealmValidateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RealmValidateOut:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.validate_realm(payload)


@app.post("/v1/content/validate")
def validate_content(
    payload: ContentValidateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ContentValidateOut:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.validate_content(payload)


@app.post("/v1/game/rules/levels/apply")
def apply_level_rule(
    payload: LevelApplyInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> LevelApplyOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.apply_level_progress(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/skills/train")
def train_skill_rule(
    payload: SkillTrainInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> SkillTrainOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.train_skill(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/perks/unlock")
def unlock_perk_rule(
    payload: PerkUnlockInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> PerkUnlockOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.unlock_perk(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/alchemy/craft")
def craft_alchemy_rule(
    payload: AlchemyCraftInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> AlchemyCraftOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.craft_alchemy(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/alchemy/interface")
def alchemy_interface_rule(
    payload: AlchemyInterfaceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> AlchemyInterfaceOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.build_alchemy_interface(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/alchemy/crystal")
def craft_alchemy_crystal_rule(
    payload: AlchemyCrystalInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> AlchemyCrystalOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.craft_alchemy_crystal(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/blacksmith/forge")
def forge_blacksmith_rule(
    payload: BlacksmithForgeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> BlacksmithForgeOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.forge_blacksmith(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/combat/resolve")
def resolve_combat_rule(
    payload: CombatResolveInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> CombatResolveOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.resolve_combat(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/market/quote")
def market_quote_rule(
    payload: MarketQuoteInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> MarketQuoteOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.market_quote(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/market/trade")
def market_trade_rule(
    payload: MarketTradeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> MarketTradeOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.market_trade(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/radio/evaluate")
def evaluate_radio_rule(
    payload: RadioEvaluateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RadioEvaluateOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.evaluate_radio_availability(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/rules/infernal-meditation/unlock")
def unlock_infernal_meditation_rule(
    payload: InfernalMeditationUnlockInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> InfernalMeditationUnlockOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.unlock_infernal_meditation(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/renderer/tables")
def build_renderer_tables(
    payload: RendererTablesInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RendererTablesOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    return svc.renderer_tables(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/renderer/isometric-contract")
def build_isometric_render_contract(
    payload: IsometricRenderContractInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> IsometricRenderContractOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    try:
        return svc.build_isometric_render_contract(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/renderer/render-graph")
def build_render_graph_contract(
    payload: RenderGraphContractInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RenderGraphContractOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    try:
        return svc.build_render_graph_contract(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/rules/gates/evaluate")
def evaluate_gate_rule(
    payload: GateEvaluateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> GateEvaluateOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.evaluate_gate(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/dialogue/emit")
def emit_game_dialogue(
    payload: DialogueEmitInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> DialogueEmitOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.emit_dialogue(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/vitriol/apply-ruler-influence")
def apply_vitriol_ruler_influence(
    payload: VitriolApplyRulerInfluenceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> VitriolApplyOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    try:
        return svc.vitriol_apply_ruler_influence(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/vitriol/clear-expired")
def clear_vitriol_expired(
    payload: VitriolClearExpiredInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> VitriolClearExpiredOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.vitriol_clear_expired(
        payload=payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/game/vitriol/compute")
def compute_vitriol(
    payload: VitriolComputeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> VitriolComputeOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop  # enforce workshop boundary surface without changing behavior
    return svc.vitriol_compute(payload=payload)


@app.post("/v1/game/djinn/apply")
def apply_djinn(
    payload: DjinnApplyInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> DjinnApplyOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        token=token,
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )
    try:
        return svc.apply_djinn_influence(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/runtime/consume")
def consume_runtime_plan(
    payload: RuntimeConsumeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RuntimeConsumeOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        token=token,
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )
    return svc.consume_runtime_plan(
        payload=payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.get("/v1/suppliers")
def list_suppliers(
    workspace_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[SupplierOut]:
    _enforce(ctx, "supplier.read")
    _enforce_role(role, "supplier.read")
    return svc.list_suppliers(workspace_id=workspace_id)


@app.post("/v1/suppliers")
def create_supplier(
    payload: SupplierCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SupplierOut:
    _enforce(ctx, "supplier.write")
    _enforce_role(role, "supplier.write")
    return svc.create_supplier(payload)


@app.get("/public/commission-hall/quotes")
def public_commission_quotes(
    workspace_id: str,
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[PublicCommissionQuoteOut]:
    return svc.list_public_commission_quotes(workspace_id=workspace_id)


@app.post("/public/commission-hall/inquiries")
def public_commission_inquiry(
    payload: PublicCommissionInquiryCreate,
    svc: AtelierService = Depends(_atelier_service),
) -> LeadOut:
    return svc.create_public_inquiry(payload)

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Mapping, Optional, Sequence

import stripe
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, Mapped, mapped_column
from sqlalchemy import Boolean, DateTime, String, Text
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from .db import Base
import structlog


from .core.config import Settings, get_settings
from .routers import game, render_lab
from .shygazun_router import router as shygazun_router


from .business_schemas import (
    ArtisanBootstrapInput,
    ArtisanAccessIssueInput,
    ArtisanAccessIssueOut,
    ArtisanAccessStatusOut,
    ArtisanAccessVerifyInput,
    ArtisanLoginInput,
    ArtisanLoginOut,
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
    SkillCatalogOut,
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
    AssetUploadRequestInput,
    AssetUploadRequestOut,
    AssetConfirmUploadOut,
    KernelFieldOut,
    KernelFieldCreateInput,
    InviteIssueInput,
    InviteIssueOut,
    InviteRedeemInput,
    InviteRedeemOut,
    GuildProfileUpsertInput,
    GuildProfileOut,
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
    Numeral3DInput,
    Numeral3DOut,
    FibonacciOrderingInput,
    FibonacciOrderingOut,
    GateEvaluateInput,
    GateEvaluateOut,
    RuntimeConsumeInput,
    RuntimeConsumeOut,
    RuntimeReplayInput,
    RuntimeReplayOut,
    RuntimePlanRunOut,
    RuntimeActionCatalogOut,
    ModuleCatalogOut,
    ModuleSpecOut,
    ModuleValidateInput,
    ModuleValidateOut,
    ShygazunInterpretInput,
    ShygazunInterpretOut,
    ShygazunTranslateInput,
    ShygazunTranslateOut,
    ShygazunCorrectInput,
    ShygazunCorrectOut,
    DialogueEmitInput,
    DialogueEmitOut,
    DialogueResolveInput,
    DialogueResolveOut,
    QuestAdvanceInput,
    QuestAdvanceOut,
    QuestAdvanceByGraphInput,
    QuestAdvanceByGraphDryRunOut,
    QuestAdvanceByGraphOut,
    QuestGraphHashOut,
    QuestGraphListOut,
    QuestGraphOut,
    QuestGraphUpsertInput,
    QuestGraphValidateOut,
    QuestTransitionInput,
    QuestTransitionOut,
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
    ContractCreate,
    ContractUpdate,
    ContractOut,
    PublicCommissionInquiryCreate,
    PublicCommissionQuoteOut,
    QuoteCreate,
    QuoteOut,
    ShopItemCreate,
    ShopItemOut,
    ShopItemUpdate,
    ShopItemVisibilityUpdate,
    PublicShopLeadRequest,
    PublicShopQuoteRequest,
    PublicShopCheckoutRequest,
    LedgerEntryOut,
    HeadlessQuestEmitInput,
    HeadlessQuestEmitOut,
    MeditationEmitInput,
    MeditationEmitOut,
    SceneGraphEmitInput,
    SceneGraphEmitOut,
    SaveExportOut,
    SupplierCreate,
    SupplierOut,
    BreathKoGenerateInput,
    BreathKoListOut,
    BreathKoOut,
    PublicShopLeadRequest,
    PublicShopQuoteRequest,
    PublicShopCheckoutRequest,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceMemberAddInput,
)
from .rendering_schemas import (
    RendererTablesInput,
    RendererTablesOut,
    IsometricRenderContractInput,
    IsometricRenderContractOut,
    RenderGraphContractInput,
    RenderGraphContractOut,
    RendererAssetDiagnosticsInput,
    RendererAssetDiagnosticsOut,
)
from .capabilities import CapabilityContext, parse_capabilities, require_capability
from .auth import AuthTokenClaims, decode_auth_token
from .core.config import Settings, load_settings
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
from .shop_endpoints import register_shop_routes
from .guild_endpoints import register_guild_routes

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


class WandDamageMediaInput(BaseModel):
    filename: str
    mime_type: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    capture_timestamp: Optional[str] = None
    feature_digest: Optional[str] = None
    metadata_hash: Optional[str] = None
    transcoded_from_mime: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class WandDamageValidateInput(BaseModel):
    wand_id: str
    notifier_id: str
    damage_state: str
    event_tag: Optional[str] = None
    media: list[WandDamageMediaInput] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class GuildMessageEnvelopeInput(BaseModel):
    schema_family: str
    schema_version: str
    cipher_family: str
    guild_id: str
    channel_id: str
    sender_id: str
    wand_id: str
    ciphertext_b64: str
    nonce_b64: str
    mac_hex: str
    plaintext_digest: Optional[str] = None
    conversation_id: Optional[str] = None
    conversation_kind: Optional[str] = None
    thread_id: Optional[str] = None
    sender_member_id: Optional[str] = None
    recipient_member_id: Optional[str] = None
    recipient_distribution_id: Optional[str] = None
    recipient_guild_id: Optional[str] = None
    recipient_channel_id: Optional[str] = None
    recipient_actor_id: Optional[str] = None
    security_session: Dict[str, Any] = Field(default_factory=dict)
    derivation: Dict[str, Any] = Field(default_factory=dict)
    entropy_mix: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuildMessageEncryptInput(BaseModel):
    guild_id: str
    channel_id: str
    sender_id: str
    wand_id: str
    wand_passkey_ward: Optional[str] = None
    message_text: str
    conversation_id: Optional[str] = None
    conversation_kind: Optional[str] = None
    thread_id: Optional[str] = None
    sender_member_id: Optional[str] = None
    recipient_member_id: Optional[str] = None
    recipient_distribution_id: Optional[str] = None
    recipient_guild_id: Optional[str] = None
    recipient_channel_id: Optional[str] = None
    recipient_actor_id: Optional[str] = None
    temple_entropy_digest: Optional[str] = None
    theatre_entropy_digest: Optional[str] = None
    attestation_media_digests: list[str] = Field(default_factory=list)
    temple_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    theatre_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    attestation_sources: list[Dict[str, Any]] = Field(default_factory=list)
    security_session: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuildMessageDecryptInput(BaseModel):
    envelope: GuildMessageEnvelopeInput
    wand_id: str
    wand_passkey_ward: Optional[str] = None
    temple_entropy_digest: Optional[str] = None
    theatre_entropy_digest: Optional[str] = None
    attestation_media_digests: list[str] = Field(default_factory=list)
    temple_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    theatre_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    attestation_sources: list[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuildMessagePersistInput(BaseModel):
    envelope: GuildMessageEnvelopeInput
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuildMessageRelayStatusInput(BaseModel):
    message_id: str
    relay_status: str
    receipt: Dict[str, Any] = Field(default_factory=dict)


class GuildConversationUpsertInput(BaseModel):
    conversation_id: str
    conversation_kind: str = "guild_channel"
    guild_id: str
    channel_id: Optional[str] = None
    thread_id: Optional[str] = None
    title: str = ""
    participant_member_ids: list[str] = Field(default_factory=list)
    participant_guild_ids: list[str] = Field(default_factory=list)
    distribution_id: Optional[str] = None
    security_session: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntropyMixInput(BaseModel):
    wand_id: str
    wand_passkey_ward: Optional[str] = None
    temple_entropy_digest: Optional[str] = None
    theatre_entropy_digest: Optional[str] = None
    attestation_media_digests: list[str] = Field(default_factory=list)
    temple_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    theatre_entropy_source: Dict[str, Any] = Field(default_factory=dict)
    attestation_sources: list[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class WandEpochTransitionInput(BaseModel):
    wand_id: str
    attestation_record_id: str
    notifier_id: str
    previous_epoch_id: Optional[str] = None
    damage_state: str
    temple_entropy_digest: Optional[str] = None
    theatre_entropy_digest: Optional[str] = None
    attestation_media_digests: list[str] = Field(default_factory=list)
    revoked: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WandRegistryInput(BaseModel):
    wand_id: str
    maker_id: str
    maker_date: str = ""
    atelier_origin: str = ""
    material_profile: Dict[str, Any] = Field(default_factory=dict)
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    structural_fingerprint: str = ""
    craft_record_hash: str = ""
    ownership_chain: list[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuildRegistryInput(BaseModel):
    guild_id: str
    display_name: str = ""
    distribution_id: str = ""
    owner_artisan_id: str
    owner_profile_name: str = ""
    owner_profile_email: str = ""
    member_profiles: list[Dict[str, Any]] = Field(default_factory=list)
    charter: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DistributionRegistryInput(BaseModel):
    distribution_id: str
    display_name: str = ""
    base_url: str = ""
    transport_kind: str = "https"
    public_key_ref: str = ""
    protocol_family: str = "guild_message_signal_artifice"
    protocol_version: str = "v1"
    supported_protocol_versions: list[str] = Field(default_factory=lambda: ["v1"])
    guild_ids: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DistributionShopWorkspaceUpdate(BaseModel):
    shop_workspace_id: str


class DistributionHandshakeInput(BaseModel):
    distribution_id: str
    local_distribution_id: str = ""
    remote_public_key_ref: str = ""
    handshake_mode: str = "mutual_hmac"
    protocol_family: str = "guild_message_signal_artifice"
    local_protocol_version: str = "v1"
    remote_protocol_version: str = "v1"
    negotiated_protocol_version: str = "v1"
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


def _auth_token_claims(authorization: Optional[str], settings: Settings) -> Optional[AuthTokenClaims]:
    auth_value = (authorization or "").strip()
    if auth_value == "":
        return None
    prefix = "Bearer "
    if not auth_value.startswith(prefix):
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    token = auth_value[len(prefix) :].strip()
    if token == "":
        raise HTTPException(status_code=401, detail="invalid_authorization_token")
    try:
        return decode_auth_token(token=token, secret=settings.auth_token_secret)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_auth_token:{str(exc)}") from exc


def _auth_token_claims_dep(authorization: Optional[str] = Header(default=None)) -> Optional[AuthTokenClaims]:
    return _auth_token_claims(authorization, load_settings())


def _capability_context(
    claims: Optional[AuthTokenClaims] = Depends(_auth_token_claims_dep),
    x_atelier_capabilities: Optional[str] = Header(default=None),
    x_atelier_actor: Optional[str] = Header(default=None),
) -> CapabilityContext:
    if claims is not None:
        return CapabilityContext(actor_id=claims.actor_id, capabilities=frozenset(claims.capabilities))
    settings = load_settings()
    auth_mode = (settings.auth_mode or "mixed").strip().lower()
    if auth_mode == "token_required":
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    if x_atelier_actor is None or not x_atelier_actor.strip():
        raise HTTPException(status_code=401, detail="missing_actor")
    if x_atelier_capabilities is None:
        raise HTTPException(status_code=403, detail="missing_capabilities")
    return CapabilityContext(actor_id=x_atelier_actor, capabilities=parse_capabilities(x_atelier_capabilities))


def _kernel_client() -> KernelClient:
    settings: Settings = load_settings()
    kernel_url = settings.kernel_internal_base_url or settings.kernel_base_url
    return HttpKernelClient(
        base_url=kernel_url,
        retry_attempts=settings.kernel_connect_retries,
        retry_backoff_ms=settings.kernel_connect_backoff_ms,
    )


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
    claims: Optional[AuthTokenClaims] = Depends(_auth_token_claims_dep),
    x_artisan_id: Optional[str] = Header(default=None),
    x_workshop_id: Optional[str] = Header(default=None),
    x_workshop_scopes: Optional[str] = Header(default=None),
) -> WorkshopContext:
    # Resolve artisan_id: prefer JWT claims (tamper-proof), fall back to header.
    if claims is not None:
        resolved_artisan_id = claims.actor_id
        # If the client also sent a header, reject mismatches to prevent spoofing.
        if x_artisan_id and x_artisan_id.strip() and x_artisan_id.strip() != resolved_artisan_id:
            raise HTTPException(status_code=403, detail="artisan_id_token_mismatch")
    elif x_artisan_id and x_artisan_id.strip():
        resolved_artisan_id = x_artisan_id.strip()
    else:
        raise HTTPException(status_code=401, detail="missing_artisan_id")

    if x_workshop_id is None or not x_workshop_id.strip():
        raise HTTPException(status_code=401, detail="missing_workshop_id")
    if x_workshop_scopes is None:
        raise HTTPException(status_code=403, detail="missing_workshop_scopes")
    return WorkshopContext(
        identity=ArtisanIdentity(artisan_id=resolved_artisan_id, workshop_id=x_workshop_id),
        scope=WorkshopScope(scopes=parse_scopes(x_workshop_scopes)),
    )


def _role_context(
    claims: Optional[AuthTokenClaims] = Depends(_auth_token_claims_dep),
    x_artisan_role: Optional[str] = Header(default=None),
) -> RoleContext:
    if x_artisan_role is None or not x_artisan_role.strip():
        if claims is not None and claims.role is not None:
            return RoleContext(role=claims.role)
        settings = load_settings()
        if (settings.auth_mode or "mixed").strip().lower() == "token_required":
            raise HTTPException(status_code=401, detail="missing_role_claim")
        raise HTTPException(status_code=401, detail="missing_artisan_role")
    return RoleContext(role=x_artisan_role.strip().lower())


def _admin_gate_token(x_admin_gate_token: Optional[str] = Header(default=None)) -> Optional[str]:
    return x_admin_gate_token


def _settings() -> Settings:
    return load_settings()


def _workspace_id_dep(
    claims: Optional[AuthTokenClaims] = Depends(_auth_token_claims_dep),
    workshop: WorkshopContext = Depends(_workshop_context),
    x_workspace_id: Optional[str] = Header(default=None),
    svc: AtelierService = Depends(_atelier_service),
) -> str:
    """Resolve the artisan's active workspace_id.

    Priority:
      1. X-Workspace-Id header (explicit switch) — validated against membership.
      2. First membership record for this artisan (auto-provisioned at login).
      3. 'main' fallback for legacy header-only / local dev (no JWT).

    JWT artisans are always isolated to their own workspaces.
    """
    artisan_id = workshop.identity.artisan_id

    # Honour an explicit workspace switch request, enforcing membership.
    if x_workspace_id and x_workspace_id.strip() and x_workspace_id.strip() != "main":
        requested = x_workspace_id.strip()
        try:
            svc.assert_workspace_access(artisan_id=artisan_id, workspace_id=requested, role="member")
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return requested

    ws_id = svc.resolve_artisan_workspace_id(artisan_id)
    if ws_id:
        return ws_id
    if claims is not None:
        # Authenticated artisan with no workspace — login should have provisioned one.
        raise HTTPException(status_code=403, detail="no_workspace_membership")
    # Legacy header-only mode: single-tenant fallback.
    return "main"


def _shop_landing_html(settings: Settings) -> str:
    website_url = settings.public_website_url or "https://quantumquackery.org"
    atelier_url = settings.public_atelier_url or "https://atelier.quantumquackery.com"
    shop_url = _normalize_shop_base(settings.public_shop_url or atelier_url)
    docs_url = f"{atelier_url.rstrip('/')}/docs"
    cards_html = _shop_cards_html(atelier_url=atelier_url, docs_url=docs_url, website_url=website_url, shop_url=shop_url)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phoenix AMS-CRM Shop</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #14532d;
      --surface: #ffffff;
      --surface-2: #f5f5f4;
      --border: #e5e7eb;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8fafc 0%, #eef2f6 50%, #f8fafc 100%);
    }}
    header {{
      padding: 64px 24px 28px;
      text-align: center;
    }}
    header h1 {{
      margin: 0 0 10px;
      font-size: 2.6rem;
      letter-spacing: 0.01em;
    }}
    .eyebrow {{
      display: inline-block;
      text-transform: uppercase;
      letter-spacing: 0.2em;
      font-size: 0.75rem;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    header p {{
      margin: 0 auto;
      max-width: 760px;
      font-size: 1.05rem;
      color: var(--muted);
      line-height: 1.6;
    }}
    .cta-row {{
      margin-top: 24px;
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 18px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--border);
      color: var(--ink);
      background: var(--surface);
    }}
    .btn.primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: transparent;
    }}
    .btn.secondary {{
      background: var(--accent-2);
      color: #ffffff;
      border-color: transparent;
    }}
    main {{
      padding: 24px;
      max-width: 1100px;
      margin: 0 auto 64px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      min-height: 210px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
    }}
    .card h3 {{
      margin: 0 0 8px;
      font-size: 1.1rem;
    }}
    .card p {{
      margin: 0 0 16px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .card .price {{
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    .card .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }}
    .tag {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    footer {{
      text-align: center;
      padding: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Phoenix AMS-CRM Shop</div>
    <h1>Service, Software, and Custom Work</h1>
    <p>
      Book consultations, request land assessments, purchase Phoenix AMS-CRM licenses,
      and commission bespoke builds. The Atelier handles secure provisioning and
      guild-aware pricing.
    </p>
    <div class="cta-row">
      <a class="btn primary" href="{atelier_url}" rel="noopener">Open Atelier</a>
      <a class="btn secondary" href="{website_url}" rel="noopener">Visit Quantum Quackery</a>
      <a class="btn" href="{docs_url}" rel="noopener">API Docs</a>
    </div>
  </header>
  <main>
    <div class="grid">
      {cards_html}
    </div>
  </main>
  <footer>
    Phoenix AMS-CRM is powered by the Atelier. Secure provisioning and guild membership
    verification occur inside the Atelier experience.
  </footer>
</body>
</html>"""


def _shop_items_html(items: Sequence[ShopItemOut]) -> str:
    if not items:
        return "<p>No items are listed in this section yet.</p>"
    cards: list[str] = []
    for item in items:
        tags = "".join(f'<span class="tag">{tag}</span>' for tag in item.tags)
        link = item.link_url.strip() or "#"
        cards.append(
            f"""<div class="card">
      <h3>{item.title}</h3>
      <div class="price">{item.price_label}</div>
      <div class="tags">{tags}</div>
      <p>{item.summary}</p>
      <div class="cta-row">
        <a class="btn primary" href="{link}" rel="noopener">Open</a>
      </div>
    </div>"""
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def _shop_sections() -> list[dict[str, str | list[str]]]:
    return [
        {
            "id": "consultations",
            "title": "Service Consultations",
            "price": "Scheduled Sessions",
            "tags": ["Strategy", "Architecture", "Operations"],
            "summary": "Schedule advisory sessions by type and duration, with intake details captured up front.",
            "cta": "Open Consultations",
        },
        {
            "id": "licenses",
            "title": "Phoenix AMS-CRM Licenses",
            "price": "Software Licenses",
            "tags": ["Subscription", "Perpetual"],
            "summary": "SaaS subscription or one-time license delivery with automated account provisioning.",
            "cta": "Open Licenses",
        },
        {
            "id": "catalog",
            "title": "Physical Goods",
            "price": "Catalog Goods",
            "tags": ["Inventory", "Shipping"],
            "summary": "Catalog-based orders with inventory tracking, fulfillment, and shipping updates.",
            "cta": "Open Catalog",
        },
        {
            "id": "custom-orders",
            "title": "Custom Orders",
            "price": "Quote First",
            "tags": ["Request", "Quote", "Approve", "Pay"],
            "summary": "Quote-first flow: request, review, approve, and finalize payment.",
            "cta": "Open Custom Orders",
        },
        {
            "id": "digital",
            "title": "Digital Products",
            "price": "Instant Delivery",
            "tags": ["Downloads", "Access Links"],
            "summary": "Instant delivery on purchase with secure access links.",
            "cta": "Open Digital Library",
        },
        {
            "id": "land-assessments",
            "title": "Land Assessments",
            "price": "Guild Verified",
            "tags": ["Members Free", "Non-members Paid"],
            "summary": "Guild members book free assessments; non-members book paid slots with location intake.",
            "cta": "Open Assessments",
        },
    ]


def _shop_link_overrides() -> dict[str, str]:
    import os as _os
    return {
        "consultations": _os.getenv("SHOP_LINK_CONSULTATIONS", "").strip(),
        "licenses": _os.getenv("SHOP_LINK_LICENSES", "").strip(),
        "catalog": _os.getenv("SHOP_LINK_CATALOG", "").strip(),
        "custom-orders": _os.getenv("SHOP_LINK_CUSTOM_ORDERS", "").strip(),
        "digital": _os.getenv("SHOP_LINK_DIGITAL", "").strip(),
        "land-assessments": _os.getenv("SHOP_LINK_LAND_ASSESSMENTS", "").strip(),
    }


def _shop_cards_html(*, atelier_url: str, docs_url: str, website_url: str, shop_url: str) -> str:
    link_overrides = _shop_link_overrides()
    cards: list[str] = []
    for section in _shop_sections():
        tags = "".join(f'<span class="tag">{tag}</span>' for tag in section["tags"])  # type: ignore[arg-type]
        override = link_overrides.get(section["id"], "")
        cta_url = override or f"{atelier_url.rstrip('/')}/"
        details_url = f"{shop_url.rstrip('/')}/{section['id']}"
        cards.append(
            f"""<section class="card">
        <div>
          <h3>{section['title']}</h3>
          <div class="price">{section['price']}</div>
          <div class="tags">{tags}</div>
          <p>{section['summary']}</p>
        </div>
        <div class="cta-row">
          <a class="btn" href="{details_url}">Details</a>
          <a class="btn primary" href="{cta_url}" rel="noopener">{section['cta']}</a>
        </div>
      </section>"""
        )
    return "\n".join(cards)


def _shop_section_html(section_id: str, settings: Settings, items: Sequence[ShopItemOut]) -> str:
    website_url = settings.public_website_url or "https://quantumquackery.org"
    atelier_url = settings.public_atelier_url or "https://atelier.quantumquackery.com"
    shop_url = _normalize_shop_base(settings.public_shop_url or atelier_url)
    docs_url = f"{atelier_url.rstrip('/')}/docs"
    section_map = {item["id"]: item for item in _shop_sections()}
    section = section_map.get(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="shop_section_not_found")
    tags = "".join(f'<span class="tag">{tag}</span>' for tag in section["tags"])  # type: ignore[arg-type]
    override = _shop_link_overrides().get(section_id, "")
    cta_url = override or f"{atelier_url.rstrip('/')}/"
    items_html = _shop_items_html(items)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{section['title']} | Phoenix AMS-CRM Shop</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #14532d;
      --surface: #ffffff;
      --surface-2: #f5f5f4;
      --border: #e5e7eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8fafc 0%, #eef2f6 50%, #f8fafc 100%);
    }}
    main {{
      padding: 48px 24px 64px;
      max-width: 920px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 2.2rem;
    }}
    p {{
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.6;
    }}
    .price {{
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 12px;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }}
    .tag {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    .cta-row {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 18px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--border);
      color: var(--ink);
      background: var(--surface);
    }}
    .btn.primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: transparent;
    }}
    .btn.secondary {{
      background: var(--accent-2);
      color: #ffffff;
      border-color: transparent;
    }}
  </style>
</head>
<body>
  <main>
    <div class="card">
      <h1>{section['title']}</h1>
      <div class="price">{section['price']}</div>
      <div class="tags">{tags}</div>
      <p>{section['summary']}</p>
      <div class="cta-row">
        <a class="btn primary" href="{cta_url}" rel="noopener">{section['cta']}</a>
        <a class="btn" href="{shop_url.rstrip('/')}/shop">Back to Shop</a>
        <a class="btn secondary" href="{website_url}" rel="noopener">Visit Quantum Quackery</a>
        <a class="btn" href="{docs_url}" rel="noopener">API Docs</a>
      </div>
    </div>
    <div style="margin-top:24px;">
      {items_html}
    </div>
  </main>
</body>
    </html>"""


def _normalize_shop_base(value: str) -> str:
    normalized = (value or "").rstrip("/")
    if normalized.endswith("/shop"):
        return normalized[: -len("/shop")]
    return normalized


def _stripe_price_for_section(settings: Settings, section_id: str) -> str:
    return str(settings.stripe_prices.get(section_id, "")).strip()


def _commission_rate_for_section(settings: Settings, section_id: str) -> float:
    return float(settings.commission_rates.get(section_id, 0.0))


def _tax_rate_for_section(settings: Settings, section_id: str) -> float:
    return float(settings.tax_rates.get(section_id, 0.0))


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
register_shop_routes(app)
register_guild_routes(app)
app.include_router(render_lab.router)
app.include_router(shygazun_router, prefix="/shygazun", tags=["shygazun"])

@app.get("/", response_class=HTMLResponse)
@app.get("/shop", response_class=HTMLResponse)
def shop_landing(
    section: Optional[str] = None,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> str:
    if section:
        workspace_id = settings.shop_workspace_id
        items: Sequence[ShopItemOut] = []
        if workspace_id:
            items = svc.list_shop_items(
                workspace_id=workspace_id,
                section_id=section,
                include_hidden=False,
            )
        return _shop_section_html(section, settings, items)
    return _shop_landing_html(settings)


@app.get("/consultations", response_class=HTMLResponse)
@app.get("/licenses", response_class=HTMLResponse)
@app.get("/catalog", response_class=HTMLResponse)
@app.get("/physical-goods", response_class=HTMLResponse)
@app.get("/custom-orders", response_class=HTMLResponse)
@app.get("/digital", response_class=HTMLResponse)
@app.get("/digital-products", response_class=HTMLResponse)
@app.get("/land-assessments", response_class=HTMLResponse)
def shop_section_root(
    request: Request,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> str:
    section_id = request.url.path.lstrip("/")
    if section_id == "physical-goods":
        section_id = "catalog"
    if section_id == "digital-products":
        section_id = "digital"
    workspace_id = settings.shop_workspace_id
    items: Sequence[ShopItemOut] = []
    if workspace_id:
        items = svc.list_shop_items(
            workspace_id=workspace_id,
            section_id=section_id,
            include_hidden=False,
        )
    return _shop_section_html(section_id, settings, items)


@app.get("/shop/{section_id}", response_class=HTMLResponse)
def shop_section(
    section_id: str,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> str:
    workspace_id = settings.shop_workspace_id
    items: Sequence[ShopItemOut] = []
    if workspace_id:
        items = svc.list_shop_items(
            workspace_id=workspace_id,
            section_id=section_id,
            include_hidden=False,
        )
    return _shop_section_html(section_id, settings, items)


@app.on_event("startup")
def startup_probe_dependencies() -> None:
    # Run DB migrations on startup so deploys to Render auto-migrate.
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        import pathlib
        alembic_cfg = AlembicConfig(str(pathlib.Path(__file__).parent.parent / "alembic.ini"))
        alembic_command.upgrade(alembic_cfg, "head")
        print("[startup] alembic upgrade head ok")
    except Exception as exc:
        print(f"[startup] alembic upgrade head failed: {exc}")

    settings = load_settings()
    kernel_url = settings.kernel_internal_base_url or settings.kernel_base_url
    kernel = HttpKernelClient(
        base_url=kernel_url,
        retry_attempts=settings.kernel_connect_retries,
        retry_backoff_ms=settings.kernel_connect_backoff_ms,
    )
    try:
        payload = kernel.health_status()
        print(
            f"[startup] kernel_probe ok base={kernel_url} "
            f"status={payload.get('status', 'unknown')}"
        )
    except Exception as exc:
        print(f"[startup] kernel_probe degraded base={kernel_url} detail={exc}")


@app.get("/health")
def health(svc: AtelierService = Depends(_atelier_service)) -> JSONResponse:
    try:
        svc.health()
    except Exception as exc:
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "api": "up",
                "database": "down",
                "detail": str(exc),
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "api": "up",
            "database": "up",
        },
    )


@app.get("/ready")
def ready(svc: AtelierService = Depends(_atelier_service)) -> JSONResponse:
    status = svc.get_readiness_status()
    return JSONResponse(status_code=200 if status.get("status") == "ready" else 503, content=dict(status))


@app.get("/v1/federation/health")
def federation_health(
    distribution_id: Optional[str] = None,
    limit: int = 25,
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    return svc.get_federation_health(distribution_id=distribution_id, limit=limit)


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


@app.post("/v1/auth/login")
def artisan_login(
    payload: ArtisanLoginInput,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> ArtisanLoginOut:
    """Public endpoint — no auth headers required. Verifies artisan_code and issues a JWT."""
    try:
        return svc.login_artisan(
            artisan_id=payload.artisan_id,
            artisan_code=payload.artisan_code,
            secret=settings.auth_token_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/v1/auth/invite")
def issue_invite(
    payload: InviteIssueInput,
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> InviteIssueOut:
    """Steward-only: issue an invite code for onboarding a new artisan."""
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    try:
        return svc.issue_invite(
            issued_by=workshop.identity.artisan_id,
            payload=payload,
            workshop_id=workshop.identity.workshop_id,
            secret=settings.auth_token_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/auth/redeem-invite")
def redeem_invite(
    payload: InviteRedeemInput,
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> InviteRedeemOut:
    """Public endpoint — redeem an invite code to create an account and receive a JWT."""
    try:
        return svc.redeem_invite(payload=payload, secret=settings.auth_token_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/guild/profile/me")
def get_my_guild_profile(
    workshop: WorkshopContext = Depends(_workshop_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Optional[GuildProfileOut]:
    """Return the calling artisan's own guild profile, or null if none exists."""
    return svc.get_my_guild_profile(workshop.identity.artisan_id)


@app.post("/v1/guild/profile")
def upsert_guild_profile(
    payload: GuildProfileUpsertInput,
    workshop: WorkshopContext = Depends(_workshop_context),
    svc: AtelierService = Depends(_atelier_service),
) -> GuildProfileOut:
    """Create or update the calling artisan's guild profile."""
    return svc.upsert_guild_profile(artisan_id=workshop.identity.artisan_id, payload=payload)


@app.get("/v1/guild/profiles")
def list_guild_profiles_admin(
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[GuildProfileOut]:
    """Steward-only: list all guild profiles including pending/unapproved."""
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    return svc.list_guild_profiles_admin()


@app.post("/v1/guild/profiles/{profile_id}/approve")
def approve_guild_profile(
    profile_id: str,
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> GuildProfileOut:
    """Steward-only: approve a guild profile for public directory listing."""
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    try:
        return svc.approve_guild_profile(
            profile_id=profile_id,
            approved_by=workshop.identity.artisan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.post("/v1/admin/workspaces")
def create_workspace(
    payload: WorkspaceCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> WorkspaceOut:
    """Steward creates a named workspace and assigns an owner artisan."""
    _enforce(ctx, "kernel.place")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    return svc.create_workspace(payload, granted_by=workshop.identity.artisan_id)


@app.get("/v1/workspaces")
def list_my_workspaces(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    _: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> list[WorkspaceOut]:
    """List all workspaces the current artisan is a member of."""
    _enforce(ctx, "kernel.observe")
    return svc.list_artisan_workspaces(workshop.identity.artisan_id)


@app.post("/v1/admin/workspaces/{workspace_id}/members")
def add_workspace_member(
    workspace_id: str,
    payload: WorkspaceMemberAddInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Dict[str, Any]:
    """Steward adds an artisan as a member of an existing workspace."""
    _enforce(ctx, "kernel.place")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    svc.add_workspace_member(
        workspace_id=workspace_id,
        payload=payload,
        granted_by=workshop.identity.artisan_id,
    )
    return {"ok": True, "workspace_id": workspace_id, "artisan_id": payload.artisan_id, "role": payload.role}


@app.get("/v1/me/workspace")
def get_my_workspace(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    _: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Dict[str, Any]:
    """Return the current artisan's resolved workspace and full workspace list."""
    _enforce(ctx, "kernel.observe")
    artisan_id = workshop.identity.artisan_id
    workspace_id = svc.resolve_artisan_workspace_id(artisan_id) or "main"
    workspaces = svc.list_artisan_workspaces(artisan_id)
    return {
        "artisan_id": artisan_id,
        "workspace_id": workspace_id,
        "workspaces": [w.model_dump() for w in workspaces],
    }


@app.get("/v1/admin/migrations/status")
def migration_status(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.get_migration_status()


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


@app.post("/v1/security/wand-damage/validate")
def validate_wand_damage_attestation(
    payload: WandDamageValidateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.attest")
    _enforce_role(role, "kernel.attest")
    return svc.validate_wand_damage_attestation(
        wand_id=payload.wand_id,
        notifier_id=payload.notifier_id,
        damage_state=payload.damage_state,
        event_tag=payload.event_tag,
        media=[item.model_dump() for item in payload.media],
        payload=payload.payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.post("/v1/security/wand-damage/record")
def record_wand_damage_attestation(
    payload: WandDamageValidateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "kernel.attest")
    _enforce_role(role, "kernel.attest")
    return svc.persist_wand_damage_attestation(
        wand_id=payload.wand_id,
        notifier_id=payload.notifier_id,
        damage_state=payload.damage_state,
        event_tag=payload.event_tag,
        media=[item.model_dump() for item in payload.media],
        payload=payload.payload,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.get("/v1/security/wand-damage/history")
def list_wand_damage_attestations(
    wand_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_wand_damage_attestations(wand_id=wand_id, limit=limit)


@app.post("/v1/security/entropy/mix")
def mix_entropy(
    payload: EntropyMixInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.mix_entropy(
            wand_id=payload.wand_id,
            wand_passkey_ward=payload.wand_passkey_ward,
            temple_entropy_digest=payload.temple_entropy_digest,
            theatre_entropy_digest=payload.theatre_entropy_digest,
            attestation_media_digests=payload.attestation_media_digests,
            temple_entropy_source=payload.temple_entropy_source,
            theatre_entropy_source=payload.theatre_entropy_source,
            attestation_sources=payload.attestation_sources,
            context=payload.context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/security/wand/epoch-transition")
def transition_wand_key_epoch(
    payload: WandEpochTransitionInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    if payload.revoked and role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required_for_revocation")
    try:
        return svc.transition_wand_key_epoch(
            wand_id=payload.wand_id,
            attestation_record_id=payload.attestation_record_id,
            notifier_id=payload.notifier_id,
            previous_epoch_id=payload.previous_epoch_id,
            damage_state=payload.damage_state,
            temple_entropy_digest=payload.temple_entropy_digest,
            theatre_entropy_digest=payload.theatre_entropy_digest,
            attestation_media_digests=payload.attestation_media_digests,
            revoked=payload.revoked,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/security/wand/status")
def get_wand_status(
    wand_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_wand_status(wand_id=wand_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/security/wands/register")
def register_wand(
    payload: WandRegistryInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.register_wand(
            wand_id=payload.wand_id,
            maker_id=payload.maker_id,
            maker_date=payload.maker_date,
            atelier_origin=payload.atelier_origin,
            material_profile=payload.material_profile,
            dimensions=payload.dimensions,
            structural_fingerprint=payload.structural_fingerprint,
            craft_record_hash=payload.craft_record_hash,
            ownership_chain=payload.ownership_chain,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/security/wands")
def list_registered_wands(
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_wand_registry(limit=limit)


@app.get("/v1/security/wands/{wand_id}")
def get_registered_wand(
    wand_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_wand_registry_entry(wand_id=wand_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/guild/registry")
def register_guild(
    payload: GuildRegistryInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.register_guild(
            guild_id=payload.guild_id,
            display_name=payload.display_name,
            distribution_id=payload.distribution_id,
            owner_artisan_id=payload.owner_artisan_id,
            owner_profile_name=payload.owner_profile_name,
            owner_profile_email=payload.owner_profile_email,
            member_profiles=payload.member_profiles,
            charter=payload.charter,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/guild/registry")
def list_registered_guilds(
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_guild_registry(limit=limit)


@app.get("/v1/guild/registry/{guild_id}")
def get_registered_guild(
    guild_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_guild_registry_entry(guild_id=guild_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/distributions/registry")
def register_distribution(
    payload: DistributionRegistryInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.register_distribution(
            distribution_id=payload.distribution_id,
            display_name=payload.display_name,
            base_url=payload.base_url,
            transport_kind=payload.transport_kind,
            public_key_ref=payload.public_key_ref,
            protocol_family=payload.protocol_family,
            protocol_version=payload.protocol_version,
            supported_protocol_versions=payload.supported_protocol_versions,
            guild_ids=payload.guild_ids,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/distributions/registry")
def list_registered_distributions(
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_distribution_registry(limit=limit)


@app.get("/v1/distributions/registry/{distribution_id}")
def get_registered_distribution(
    distribution_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_distribution_registry_entry(distribution_id=distribution_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/public/distributions/registry")
def public_distribution_registry(
    distribution_id: str,
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    try:
        record = svc.get_distribution_registry_entry(distribution_id=distribution_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    status = str(record.get("status") or "").strip()
    if status.lower() != "active":
        raise HTTPException(status_code=404, detail="distribution_inactive")
    metadata_obj = record.get("metadata")
    metadata = dict(metadata_obj) if isinstance(metadata_obj, Mapping) else {}
    return {
        "distribution_id": str(record.get("distribution_id") or "").strip(),
        "display_name": str(record.get("display_name") or "").strip(),
        "base_url": str(record.get("base_url") or "").strip(),
        "status": status,
        "shop_workspace_id": str(metadata.get("shop_workspace_id") or "").strip(),
    }


@app.get("/v1/distributions/registry/{distribution_id}/key-discovery")
def get_distribution_key_discovery(
    distribution_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_distribution_key_descriptor(distribution_id=distribution_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/distributions/registry/{distribution_id}/capabilities")
def get_distribution_capabilities(
    distribution_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.discover_distribution_capabilities(distribution_id=distribution_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/v1/distributions/registry/{distribution_id}/shop-workspace")
def set_distribution_shop_workspace(
    distribution_id: str,
    payload: DistributionShopWorkspaceUpdate,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "shop.admin")
    _enforce_role(role, "shop.admin")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    try:
        return svc.set_distribution_shop_workspace_id(
            distribution_id=distribution_id,
            shop_workspace_id=payload.shop_workspace_id,
            steward_id=workshop.identity.artisan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/distributions/handshakes")
def register_distribution_handshake(
    payload: DistributionHandshakeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.register_distribution_handshake(
            distribution_id=payload.distribution_id,
            local_distribution_id=payload.local_distribution_id,
            remote_public_key_ref=payload.remote_public_key_ref,
            handshake_mode=payload.handshake_mode,
            protocol_family=payload.protocol_family,
            local_protocol_version=payload.local_protocol_version,
            remote_protocol_version=payload.remote_protocol_version,
            negotiated_protocol_version=payload.negotiated_protocol_version,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/distributions/handshakes")
def list_distribution_handshakes(
    distribution_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_distribution_handshakes(distribution_id=distribution_id, limit=limit)


@app.get("/v1/security/wand/epochs")
def list_wand_key_epochs(
    wand_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_wand_key_epochs(wand_id=wand_id, limit=limit)


@app.post("/v1/guild/messages/encrypt")
def encrypt_guild_message(
    payload: GuildMessageEncryptInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.encrypt_guild_message(
            guild_id=payload.guild_id,
            channel_id=payload.channel_id,
            sender_id=payload.sender_id,
            wand_id=payload.wand_id,
            wand_passkey_ward=payload.wand_passkey_ward,
            message_text=payload.message_text,
            conversation_id=payload.conversation_id,
            conversation_kind=payload.conversation_kind,
            thread_id=payload.thread_id,
            sender_member_id=payload.sender_member_id,
            recipient_member_id=payload.recipient_member_id,
            recipient_distribution_id=payload.recipient_distribution_id,
            recipient_guild_id=payload.recipient_guild_id,
            recipient_channel_id=payload.recipient_channel_id,
            recipient_actor_id=payload.recipient_actor_id,
            temple_entropy_digest=payload.temple_entropy_digest,
            theatre_entropy_digest=payload.theatre_entropy_digest,
            attestation_media_digests=payload.attestation_media_digests,
            temple_entropy_source=payload.temple_entropy_source,
            theatre_entropy_source=payload.theatre_entropy_source,
            attestation_sources=payload.attestation_sources,
            security_session=payload.security_session,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/guild/messages/decrypt")
def decrypt_guild_message(
    payload: GuildMessageDecryptInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.decrypt_guild_message(
            envelope=payload.envelope.model_dump(),
            wand_id=payload.wand_id,
            wand_passkey_ward=payload.wand_passkey_ward,
            temple_entropy_digest=payload.temple_entropy_digest,
            theatre_entropy_digest=payload.theatre_entropy_digest,
            attestation_media_digests=payload.attestation_media_digests,
            temple_entropy_source=payload.temple_entropy_source,
            theatre_entropy_source=payload.theatre_entropy_source,
            attestation_sources=payload.attestation_sources,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/guild/messages/persist")
def persist_guild_message(
    payload: GuildMessagePersistInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.persist_guild_message_envelope(
        envelope=payload.envelope.model_dump(),
        metadata=payload.metadata,
    )


@app.post("/v1/guild/messages/relay-status")
def update_guild_message_relay_status(
    payload: GuildMessageRelayStatusInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.update_guild_message_relay_status(
            message_id=payload.message_id,
            relay_status=payload.relay_status,
            receipt=payload.receipt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/guild/messages/history")
def list_guild_messages(
    conversation_id: Optional[str] = None,
    guild_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_guild_message_history(
        conversation_id=conversation_id,
        guild_id=guild_id,
        channel_id=channel_id,
        thread_id=thread_id,
        limit=limit,
    )


@app.post("/v1/guild/conversations")
def upsert_guild_conversation(
    payload: GuildConversationUpsertInput,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.upsert_guild_conversation(
            conversation_id=payload.conversation_id,
            conversation_kind=payload.conversation_kind,
            guild_id=payload.guild_id,
            channel_id=payload.channel_id,
            thread_id=payload.thread_id,
            title=payload.title,
            participant_member_ids=payload.participant_member_ids,
            participant_guild_ids=payload.participant_guild_ids,
            distribution_id=payload.distribution_id,
            security_session=payload.security_session,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/guild/conversations")
def list_guild_conversations(
    guild_id: Optional[str] = None,
    conversation_kind: Optional[str] = None,
    participant_member_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[Mapping[str, Any]]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_guild_conversations(
        guild_id=guild_id,
        conversation_kind=conversation_kind,
        participant_member_id=participant_member_id,
        limit=limit,
    )


@app.get("/v1/guild/conversations/{conversation_id}")
def get_guild_conversation(
    conversation_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    _: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Mapping[str, Any]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        return svc.get_guild_conversation(conversation_id=conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContactOut:
    _enforce(ctx, "crm.contacts.write")
    _enforce_role(role, "crm.contacts.write")
    return svc.create_contact(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/booking")
def list_bookings(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> BookingOut:
    _enforce(ctx, "booking.write")
    _enforce_role(role, "booking.write")
    return svc.create_booking(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/lessons")
def list_lessons(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LessonOut:
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    return svc.create_lesson(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/lessons/progress")
def list_lesson_progress(
    actor_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LessonProgressOut]:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_lesson_progress(workspace_id=workspace_id, actor_id=actor_id)


@app.post("/v1/lessons/consume")
def consume_lesson(
    payload: LessonConsumeInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LessonProgressOut:
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    return svc.consume_lesson(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/modules")
def list_modules(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ModuleOut:
    _enforce(ctx, "module.write")
    _enforce_role(role, "module.write")
    return svc.create_module(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/leads")
def list_leads(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> LeadOut:
    _enforce(ctx, "lead.write")
    _enforce_role(role, "lead.write")
    return svc.create_lead(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/clients")
def list_clients(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ClientOut:
    _enforce(ctx, "client.write")
    _enforce_role(role, "client.write")
    return svc.create_client(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/quotes")
def list_quotes(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuoteOut:
    _enforce(ctx, "quote.write")
    _enforce_role(role, "quote.write")
    return svc.create_quote(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/orders")
def list_orders(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[OrderOut]:
    _enforce(ctx, "order.read")
    _enforce_role(role, "order.read")
    return svc.list_orders(workspace_id=workspace_id)


@app.get("/v1/contracts")
def list_contracts(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ContractOut]:
    _enforce(ctx, "contract.read")
    _enforce_role(role, "contract.read")
    return svc.list_contracts(workspace_id=workspace_id)


@app.post("/v1/contracts")
def create_contract(
    payload: ContractCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContractOut:
    _enforce(ctx, "contract.write")
    _enforce_role(role, "contract.write")
    return svc.create_contract(payload.model_copy(update={"workspace_id": workspace_id}))


@app.patch("/v1/contracts/{contract_id}")
def update_contract(
    contract_id: str,
    payload: ContractUpdate,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContractOut:
    _enforce(ctx, "contract.write")
    _enforce_role(role, "contract.write")
    return svc.update_contract(workspace_id=workspace_id, contract_id=contract_id, payload=payload)


@app.post("/v1/contracts/{contract_id}/validate")
def validate_contract(
    contract_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContractOut:
    _enforce(ctx, "contract.admin")
    _enforce_role(role, "contract.admin")
    return svc.validate_contract(workspace_id=workspace_id, contract_id=contract_id)


@app.post("/v1/contracts/{contract_id}/cancel")
def cancel_contract(
    contract_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContractOut:
    _enforce(ctx, "contract.admin")
    _enforce_role(role, "contract.admin")
    return svc.cancel_contract(workspace_id=workspace_id, contract_id=contract_id)


@app.post("/v1/contracts/{contract_id}/process")
def process_contract(
    contract_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ContractOut:
    _enforce(ctx, "contract.admin")
    _enforce_role(role, "contract.admin")
    return svc.process_contract(workspace_id=workspace_id, contract_id=contract_id)


@app.get("/v1/ledger/entries")
def list_ledger_entries(
    account_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[LedgerEntryOut]:
    _enforce(ctx, "ledger.read")
    _enforce_role(role, "ledger.read")
    return svc.list_ledger_entries(workspace_id=workspace_id, account_type=account_type, owner_id=owner_id)


@app.get("/v1/ledger/payouts/summary")
def ledger_payout_summary(
    month: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    _enforce(ctx, "ledger.read")
    _enforce_role(role, "ledger.read")
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="month_format_required")
    return JSONResponse(svc.summarize_artisan_payouts(workspace_id=workspace_id, month=month))


@app.post("/v1/ledger/payouts/run")
def ledger_payout_run(
    month: str,
    dry_run: bool = False,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    _enforce(ctx, "ledger.write")
    _enforce_role(role, "ledger.write")
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="month_format_required")
    return JSONResponse(svc.run_monthly_payouts(workspace_id=workspace_id, month=month, dry_run=dry_run))


@app.get("/v1/ledger/payouts/export", response_class=Response)
def ledger_payout_export(
    month: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Response:
    _enforce(ctx, "ledger.read")
    _enforce_role(role, "ledger.read")
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="month_format_required")
    summary = svc.summarize_artisan_payouts(workspace_id=workspace_id, month=month)
    rows = summary.get("payouts", [])
    lines = ["artisan_id,payable_cents,paid_cents,remaining_cents"]
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"{row.get('artisan_id','')},{row.get('payable_cents',0)},{row.get('paid_cents',0)},{row.get('remaining_cents',0)}"
            )
    content = "\n".join(lines)
    return Response(content=content, media_type="text/csv")


@app.get("/v1/ledger/payouts/1099", response_class=Response)
def ledger_payout_1099(
    month: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Response:
    _enforce(ctx, "ledger.read")
    _enforce_role(role, "ledger.read")
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="month_format_required")
    summary = svc.summarize_artisan_payouts(workspace_id=workspace_id, month=month)
    rows = summary.get("payouts", [])
    year = month.split("-")[0]
    lines = ["recipient_id,tax_year,paid_cents,currency"]
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.append(f"{row.get('artisan_id','')},{year},{row.get('paid_cents',0)},USD")
    content = "\n".join(lines)
    return Response(content=content, media_type="text/csv")


@app.post("/v1/orders")
def create_order(
    payload: OrderCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> OrderOut:
    _enforce(ctx, "order.write")
    _enforce_role(role, "order.write")
    return svc.create_order(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/inventory")
def list_inventory_items(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> InventoryItemOut:
    _enforce(ctx, "inventory.write")
    _enforce_role(role, "inventory.write")
    return svc.create_inventory_item(payload.model_copy(update={"workspace_id": workspace_id}))


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


@app.post("/v1/assets/upload-request")
def request_asset_upload(
    payload: AssetUploadRequestInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> AssetUploadRequestOut:
    """Create an asset record and return a presigned PUT URL for direct upload to R2."""
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    try:
        return svc.request_asset_upload(workspace_id=workspace_id, payload=payload, settings=settings)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"upload_request_failed:{exc}") from exc


@app.post("/v1/assets/{asset_id}/confirm")
def confirm_asset_upload(
    asset_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> AssetConfirmUploadOut:
    """Mark an asset as successfully uploaded after the client PUT to R2."""
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    try:
        return svc.confirm_asset_upload(workspace_id=workspace_id, asset_id=asset_id, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/assets/{asset_id}/download-url")
def get_asset_download_url(
    asset_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> Dict[str, Any]:
    """Return a presigned download URL (or public URL) for an uploaded asset."""
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    try:
        url = svc.get_asset_download_url(workspace_id=workspace_id, asset_id=asset_id, settings=settings)
        return {"asset_id": asset_id, "url": url}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/v1/assets/{asset_id}")
def delete_asset(
    asset_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
    settings: Settings = Depends(_settings),
) -> Dict[str, Any]:
    """Delete an asset from R2 and mark it deleted in the DB."""
    _enforce(ctx, "lesson.write")
    _enforce_role(role, "lesson.write")
    try:
        svc.delete_asset(workspace_id=workspace_id, asset_id=asset_id, settings=settings)
        return {"ok": True, "asset_id": asset_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/kernel/fields")
def create_kernel_field(
    payload: KernelFieldCreateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
    kernel: KernelClient = Depends(_kernel_client),
) -> KernelFieldOut:
    """Create (or return existing) per-artisan kernel field."""
    artisan_id = workshop.identity.artisan_id
    try:
        return svc.create_artisan_field(
            artisan_id=artisan_id,
            workspace_id=workspace_id,
            label=payload.label,
            kernel_client=kernel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/kernel/fields")
def list_kernel_fields(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    workspace_id: str = Depends(_workspace_id_dep),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[KernelFieldOut]:
    """List kernel fields owned by the current artisan in this workspace."""
    artisan_id = workshop.identity.artisan_id
    return svc.list_artisan_fields(artisan_id=artisan_id, workspace_id=workspace_id)


@app.get("/v1/kernel/fields/{field_id}/observe")
def observe_kernel_field(
    field_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    svc: AtelierService = Depends(_atelier_service),
    kernel: KernelClient = Depends(_kernel_client),
) -> Dict[str, Any]:
    """Observe a per-artisan kernel field (returns CEG state)."""
    artisan_id = workshop.identity.artisan_id
    try:
        return dict(svc.observe_artisan_field(field_id=field_id, artisan_id=artisan_id, kernel_client=kernel))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/kernel/fields/{field_id}/ceg")
def get_kernel_field_ceg(
    field_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    svc: AtelierService = Depends(_atelier_service),
    kernel: KernelClient = Depends(_kernel_client),
) -> Dict[str, Any]:
    """Get CEG snapshot for a per-artisan kernel field."""
    artisan_id = workshop.identity.artisan_id
    try:
        return dict(svc.get_artisan_field_ceg(field_id=field_id, artisan_id=artisan_id, kernel_client=kernel))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/kernel/fields/{field_id}/frontiers")
def get_kernel_field_frontiers(
    field_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    svc: AtelierService = Depends(_atelier_service),
    kernel: KernelClient = Depends(_kernel_client),
) -> Sequence[Dict[str, Any]]:
    """Get eligible frontiers for a per-artisan kernel field."""
    artisan_id = workshop.identity.artisan_id
    try:
        return list(svc.get_artisan_field_frontiers(field_id=field_id, artisan_id=artisan_id, kernel_client=kernel))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.get("/v1/game/rules/skills/catalog")
def skill_catalog(
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> SkillCatalogOut:
    _enforce(ctx, "lesson.read")
    _enforce_role(role, "lesson.read")
    return svc.list_skill_catalog()


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


@app.post("/v1/game/renderer/assets/diagnostics")
def renderer_asset_diagnostics(
    payload: RendererAssetDiagnosticsInput,
    ctx: CapabilityContext = Depends(_capability_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RendererAssetDiagnosticsOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    try:
        return svc.renderer_asset_diagnostics(payload=payload)
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


@app.post("/v1/game/dialogue/resolve")
def resolve_game_dialogue(
    payload: DialogueResolveInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> DialogueResolveOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.resolve_dialogue_branch(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/quests/transition")
def transition_game_quest(
    payload: QuestTransitionInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestTransitionOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.transition_quest_state(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/quests/advance")
def advance_game_quest(
    payload: QuestAdvanceInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestAdvanceOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _enforce_admin_gate(
        settings=settings,
        role=role,
        actor_id=ctx.actor_id,
        workshop_id=workshop.identity.workshop_id,
        token=token,
    )
    return svc.advance_quest_step(payload=payload, actor_id=ctx.actor_id, workshop_id=workshop.identity.workshop_id)


@app.post("/v1/game/quests/graphs")
def upsert_game_quest_graph(
    payload: QuestGraphUpsertInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphOut:
    _enforce(ctx, "quest.write")
    _enforce_role(role, "quest.write")
    _ = workshop
    try:
        return svc.upsert_quest_graph(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/quests/graphs/validate")
def validate_game_quest_graph(
    payload: QuestGraphUpsertInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphValidateOut:
    _enforce(ctx, "quest.write")
    _enforce_role(role, "quest.write")
    _ = workshop
    return svc.validate_quest_graph(payload)


@app.get("/v1/game/quests/graphs")
def get_game_quest_graph(
    workspace_id: str,
    quest_id: str,
    version: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphOut:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    _ = workshop
    try:
        return svc.get_quest_graph(workspace_id=workspace_id, quest_id=quest_id, version=version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/quests/graphs/hash")
def hash_game_quest_graph(
    workspace_id: str,
    quest_id: str,
    version: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphHashOut:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    _ = workshop
    try:
        return svc.hash_quest_graph(workspace_id=workspace_id, quest_id=quest_id, version=version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/quests/graphs/latest")
def get_latest_game_quest_graph(
    workspace_id: str,
    quest_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphOut:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    _ = workshop
    try:
        return svc.get_latest_quest_graph(workspace_id=workspace_id, quest_id=quest_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/quests/graphs/all")
def list_game_quest_graphs(
    workspace_id: str,
    quest_id: Optional[str] = None,
    version: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestGraphListOut:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    _ = workshop
    return svc.list_quest_graphs(
        workspace_id=workspace_id,
        quest_id=quest_id,
        version=version,
        limit=limit,
        offset=offset,
    )


@app.post("/v1/game/quests/advance/by-graph")
def advance_game_quest_by_graph(
    payload: QuestAdvanceByGraphInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestAdvanceByGraphOut:
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
        return svc.advance_quest_step_by_graph(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/quests/advance/by-graph/dry-run")
def advance_game_quest_by_graph_dry_run(
    payload: QuestAdvanceByGraphInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> QuestAdvanceByGraphDryRunOut:
    _enforce(ctx, "quest.read")
    _enforce_role(role, "quest.read")
    _ = workshop
    try:
        return svc.advance_quest_step_by_graph_dry_run(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/breath/ko/generate")
def generate_breath_ko(
    payload: BreathKoGenerateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> BreathKoOut:
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
        return svc.generate_breath_ko(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/breath/ko")
def list_breath_ko(
    workspace_id: str,
    actor_id: Optional[str] = None,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> BreathKoListOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    return svc.list_breath_ko(workspace_id=workspace_id, actor_id=actor_id)


@app.post("/v1/game/math/numeral-3d")
def compute_numeral_3d(
    payload: Numeral3DInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> Numeral3DOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _ = workshop
    return svc.compute_numeral_3d(
        payload=payload,
        actor_id=ctx.actor_id,
    )


@app.post("/v1/game/math/fibonacci-ordering")
def compute_fibonacci_ordering(
    payload: FibonacciOrderingInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> FibonacciOrderingOut:
    _enforce(ctx, "kernel.place")
    _enforce_role(role, "kernel.place")
    _ = workshop
    return svc.compute_fibonacci_ordering(
        payload=payload,
        actor_id=ctx.actor_id,
    )


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


@app.post("/v1/game/runtime/replay")
def replay_runtime_plan(
    payload: RuntimeReplayInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    token: Optional[str] = Depends(_admin_gate_token),
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> RuntimeReplayOut:
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
        return svc.replay_runtime_plan(
            payload=payload,
            actor_id=ctx.actor_id,
            workshop_id=workshop.identity.workshop_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/runtime/runs")
def list_runtime_plan_runs(
    workspace_id: str,
    actor_id: str,
    plan_id: Optional[str] = None,
    limit: int = 50,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[RuntimePlanRunOut]:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.list_runtime_plan_runs(
            workspace_id=workspace_id,
            actor_id=actor_id,
            plan_id=plan_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/game/runtime/actions/catalog")
def runtime_action_catalog(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> RuntimeActionCatalogOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    return svc.runtime_action_catalog()


@app.get("/v1/game/modules")
def list_game_modules(
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ModuleCatalogOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    return svc.list_module_specs()


@app.get("/v1/game/modules/{module_id}")
def get_game_module(
    module_id: str,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ModuleSpecOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.get_module_spec(module_id=module_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/modules/validate")
def validate_game_module(
    payload: ModuleValidateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ModuleValidateOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.validate_module_spec(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/shygazun/translate")
def translate_shygazun(
    payload: ShygazunTranslateInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ShygazunTranslateOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.translate_shygazun(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/shygazun/interpret")
def interpret_shygazun(
    payload: ShygazunInterpretInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ShygazunInterpretOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.interpret_shygazun(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/game/shygazun/correct")
def correct_shygazun(
    payload: ShygazunCorrectInput,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_kernel_only_service),
) -> ShygazunCorrectOut:
    _enforce(ctx, "kernel.observe")
    _enforce_role(role, "kernel.observe")
    _ = workshop
    try:
        return svc.correct_shygazun(payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/suppliers")
def list_suppliers(
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
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
    workspace_id: str = Depends(_workspace_id_dep),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> SupplierOut:
    _enforce(ctx, "supplier.write")
    _enforce_role(role, "supplier.write")
    return svc.create_supplier(payload.model_copy(update={"workspace_id": workspace_id}))


@app.get("/v1/shop/items")
def list_shop_items(
    section_id: Optional[str] = None,
    artisan_id: Optional[str] = None,
    include_hidden: bool = False,
    ctx: CapabilityContext = Depends(_capability_context),
    workspace_id: str = Depends(_workspace_id_dep),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ShopItemOut]:
    _enforce(ctx, "shop.read")
    _enforce_role(role, "shop.read")
    is_steward = role.role == ROLE_STEWARD
    if not is_steward:
        artisan_id = workshop.identity.artisan_id
        include_hidden = False
    return svc.list_shop_items(
        workspace_id=workspace_id,
        artisan_id=artisan_id,
        section_id=section_id,
        include_hidden=include_hidden,
    )


@app.post("/v1/shop/items")
def create_shop_item(
    payload: ShopItemCreate,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ShopItemOut:
    _enforce(ctx, "shop.write")
    _enforce_role(role, "shop.write")
    return svc.create_shop_item(
        payload=payload,
        artisan_id=workshop.identity.artisan_id,
        workshop_id=workshop.identity.workshop_id,
    )


@app.patch("/v1/shop/items/{item_id}")
def update_shop_item(
    item_id: str,
    workspace_id: str,
    payload: ShopItemUpdate,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ShopItemOut:
    _enforce(ctx, "shop.write")
    _enforce_role(role, "shop.write")
    is_steward = role.role == ROLE_STEWARD
    return svc.update_shop_item(
        workspace_id=workspace_id,
        item_id=item_id,
        payload=payload,
        artisan_id=workshop.identity.artisan_id,
        is_steward=is_steward,
    )


@app.post("/v1/shop/items/{item_id}/visibility")
def set_shop_item_visibility(
    item_id: str,
    workspace_id: str,
    payload: ShopItemVisibilityUpdate,
    ctx: CapabilityContext = Depends(_capability_context),
    workshop: WorkshopContext = Depends(_workshop_context),
    role: RoleContext = Depends(_role_context),
    svc: AtelierService = Depends(_atelier_service),
) -> ShopItemOut:
    _enforce(ctx, "shop.admin")
    _enforce_role(role, "shop.admin")
    if role.role != ROLE_STEWARD:
        raise HTTPException(status_code=403, detail="steward_required")
    return svc.set_shop_item_visibility(
        workspace_id=workspace_id,
        item_id=item_id,
        payload=payload,
        steward_id=workshop.identity.artisan_id,
    )


@app.get("/public/commission-hall/quotes")
def public_commission_quotes(
    workspace_id: str,
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[PublicCommissionQuoteOut]:
    return svc.list_public_commission_quotes(workspace_id=workspace_id)


@app.get("/public/shop/items")
def public_shop_items(
    workspace_id: str,
    section_id: Optional[str] = None,
    svc: AtelierService = Depends(_atelier_service),
) -> Sequence[ShopItemOut]:
    return svc.list_shop_items(
        workspace_id=workspace_id,
        section_id=section_id,
        include_hidden=False,
    )


@app.post("/public/shop/checkout-session")
def public_shop_checkout_session(
    payload: PublicShopCheckoutRequest,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    section_id = str(payload.section_id or "").strip()
    artisan_id = payload.artisan_id
    item_id = payload.item_id
    if item_id:
        if not settings.shop_workspace_id:
            raise HTTPException(status_code=503, detail="shop_workspace_not_configured")
        try:
            item = svc.get_shop_item(workspace_id=settings.shop_workspace_id, item_id=item_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        artisan_id = item.artisan_id
        section_id = item.section_id
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id_required")
    price_id = _stripe_price_for_section(settings, section_id)
    if not price_id:
        raise HTTPException(status_code=404, detail="checkout_not_configured")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="stripe_not_configured")
    stripe.api_key = settings.stripe_secret_key
    shop_url = _normalize_shop_base(settings.public_shop_url or settings.public_atelier_url)
    success_url = settings.stripe_success_url or f"{shop_url}/shop?checkout=success"
    cancel_url = settings.stripe_cancel_url or f"{shop_url}/shop?checkout=cancel"
    quantity = max(1, int(payload.quantity or 1))
    metadata = {"section_id": section_id}
    if artisan_id:
        metadata["artisan_id"] = artisan_id
    if item_id:
        metadata["item_id"] = item_id
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": quantity}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"stripe_error:{exc}") from exc
    return JSONResponse({"status": "ok", "url": session.url})


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="stripe_webhook_not_configured")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid_signature:{exc}") from exc
    if event["type"] != "checkout.session.completed":
        return JSONResponse({"status": "ignored"})
    if not settings.shop_workspace_id:
        raise HTTPException(status_code=503, detail="shop_workspace_not_configured")
    session = event["data"]["object"]
    section_id = str(session.get("metadata", {}).get("section_id") or "").strip() or "unknown"
    artisan_id = str(session.get("metadata", {}).get("artisan_id") or "").strip() or None
    item_id = str(session.get("metadata", {}).get("item_id") or "").strip() or None
    amount_total = int(session.get("amount_total") or 0)
    currency = str(session.get("currency") or "usd").upper()
    payment_intent = session.get("payment_intent")
    if amount_total <= 0:
        return JSONResponse({"status": "ignored"})
    fee_cents = 0
    if payment_intent:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent, expand=["charges.data.balance_transaction"])
            charges = intent.get("charges", {}).get("data", [])
            if charges:
                balance_txn = charges[0].get("balance_transaction")
                if isinstance(balance_txn, dict):
                    fee_cents = int(balance_txn.get("fee") or 0)
        except Exception:
            fee_cents = 0
    tax_rate = _tax_rate_for_section(settings, section_id)
    tax_cents = int(round(amount_total * tax_rate))
    net_cents = max(0, amount_total - fee_cents)
    commission_rate = _commission_rate_for_section(settings, section_id)
    commission_cents = int(round(max(0, net_cents - tax_cents) * commission_rate))
    metadata = {
        "stripe_session_id": session.get("id"),
        "stripe_payment_intent": payment_intent,
        "stripe_customer": session.get("customer"),
        "item_id": item_id,
    }
    svc.record_shop_sale_ledger(
        workspace_id=settings.shop_workspace_id,
        section_id=section_id,
        artisan_id=artisan_id,
        currency=currency,
        gross_cents=amount_total,
        fee_cents=fee_cents,
        tax_cents=tax_cents,
        commission_cents=commission_cents,
        net_cents=net_cents,
        reference_type="stripe_checkout",
        reference_id=str(session.get("id") or ""),
        metadata=metadata,
    )
    return JSONResponse({"status": "ok"})


@app.post("/public/shop/leads")
def public_shop_lead(
    payload: PublicShopLeadRequest,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    workspace_id = settings.shop_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=503, detail="shop_workspace_not_configured")
    section_id = str(payload.section_id or "general").strip() or "general"
    details = payload.details or ""
    if payload.phone:
        details = f"{details}\nphone: {payload.phone}".strip()
    lead = svc.create_lead(
        LeadCreate(
            workspace_id=workspace_id,
            full_name=payload.full_name.strip(),
            email=payload.email,
            phone=payload.phone,
            details=details,
            status="new",
            source=f"shop:{section_id}",
        )
    )
    return JSONResponse({"status": "ok", "lead_id": lead.id})


@app.post("/public/shop/quotes")
def public_shop_quote(
    payload: PublicShopQuoteRequest,
    settings: Settings = Depends(_settings),
    svc: AtelierService = Depends(_atelier_service),
) -> JSONResponse:
    workspace_id = settings.shop_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=503, detail="shop_workspace_not_configured")
    section_id = str(payload.section_id or "custom-orders").strip() or "custom-orders"
    details = payload.details or ""
    if payload.phone:
        details = f"{details}\nphone: {payload.phone}".strip()
    lead = svc.create_lead(
        LeadCreate(
            workspace_id=workspace_id,
            full_name=payload.full_name.strip(),
            email=payload.email,
            phone=payload.phone,
            details=details,
            status="new",
            source=f"shop:{section_id}",
        )
    )
    title = (payload.title or f"Quote request: {section_id}").strip()
    quote = svc.create_quote(
        QuoteCreate(
            workspace_id=workspace_id,
            lead_id=lead.id,
            title=title,
            amount_cents=0,
            currency="USD",
            status="request",
            is_public=False,
            notes=details,
        )
    )
    return JSONResponse({"status": "ok", "lead_id": lead.id, "quote_id": quote.id})


@app.post("/public/commission-hall/inquiries")
def public_commission_inquiry(
    payload: PublicCommissionInquiryCreate,
    svc: AtelierService = Depends(_atelier_service),
) -> LeadOut:
    return svc.create_public_inquiry(payload)
log = structlog.get_logger()


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Any:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.1f}"
    return response


# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    log.error("unhandled_exception", path=str(request.url), error=str(exc))
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"ok": False, "error": "internal_server_error", "detail": str(exc)},
    )


# GuildArtisanProfile is defined in models.py — do not redefine here.

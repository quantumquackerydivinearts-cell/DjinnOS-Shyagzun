"""
atelier_api/models/schemas.py
Pydantic v2 request/response schemas for all endpoints.
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ── Shared ────────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""


# ── Tick engine ───────────────────────────────────────────────────────────────

class TickEvent(BaseModel):
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    action_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")


class TickRequest(BaseModel):
    workspace_id: str
    actor_id: str = "player"
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:8]}")
    events: list[TickEvent]
    current_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("events")
    @classmethod
    def at_least_one(cls, v: list[TickEvent]) -> list[TickEvent]:
        if not v:
            raise ValueError("events must contain at least one item")
        return v


class TickEventResult(BaseModel):
    action_id: str
    ok: bool
    kind: str
    state_patch: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class TickResponse(BaseModel):
    ok: bool
    plan_id: str
    workspace_id: str
    actor_id: str
    results: list[TickEventResult]
    next_state: dict[str, Any]
    hash: str
    lineage_id: str
    failed_count: int


# ── Renderer sync tables ──────────────────────────────────────────────────────

class SyncTablesRequest(BaseModel):
    workspace_id: str
    actor_id: str = "player"
    precedence: Literal["local_over_api", "api_over_local"] = "api_over_local"
    local_tables: dict[str, Any] = Field(default_factory=dict)


class SyncTablesResponse(BaseModel):
    ok: bool
    tables: dict[str, Any]
    meta: dict[str, Any]
    hash: str


# ── Cobra compile ─────────────────────────────────────────────────────────────

class CompileCobraRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    scene_id: str = ""
    scene_name: str = ""
    description: str = ""
    cobra_source: str

    @field_validator("cobra_source")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cobra_source must not be empty")
        return v


class CompileCobraResponse(BaseModel):
    ok: bool
    scene_id: str
    renderer_json: dict[str, Any]
    engine_state: dict[str, Any]
    voxels: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    warnings: list[str]
    lineage_id: str


# ── Content validation ────────────────────────────────────────────────────────

class ValidateContentRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    scene_id: str = ""
    source_type: Literal["cobra", "json", "python", "js"] = "cobra"
    payload: str
    strict_bilingual: bool = False


class BilingualTrust(BaseModel):
    authority_level: str = "unknown"
    trust_grade: str = "unknown"
    chirality: list[str] = Field(default_factory=list)
    time_topology: list[str] = Field(default_factory=list)
    space_operator: list[str] = Field(default_factory=list)
    network_role: list[str] = Field(default_factory=list)
    cluster_role: list[str] = Field(default_factory=list)
    axis: list[str] = Field(default_factory=list)
    tongue_projection: list[str] = Field(default_factory=list)
    cannabis_mode: list[str] = Field(default_factory=list)


class ValidateContentResponse(BaseModel):
    ok: bool
    error_count: int
    warning_count: int
    errors: list[str]
    warnings: list[str]
    bilingual_trust: BilingualTrust
    scene_id: str
    source_type: str


# ── Scene emission ────────────────────────────────────────────────────────────

class EmitSceneGraphRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    scene_id: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class EmitSceneGraphResponse(BaseModel):
    ok: bool
    scene_id: str
    node_count: int
    edge_count: int
    lineage_id: str


class EmitHeadlessQuestRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    quest_id: str = Field(default_factory=lambda: f"quest_{uuid4().hex[:8]}")
    steps: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class EmitHeadlessQuestResponse(BaseModel):
    ok: bool
    quest_id: str
    step_count: int
    lineage_id: str


class EmitMeditationRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    meditation_id: str = Field(default_factory=lambda: f"med_{uuid4().hex[:8]}")
    content: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class EmitMeditationResponse(BaseModel):
    ok: bool
    meditation_id: str
    lineage_id: str


class EmitPlacementsRequest(BaseModel):
    workspace_id: str
    realm_id: str = ""
    scene_id: str = ""
    placements: list[dict[str, Any]]
    source: Literal["json", "cobra", "tile"] = "json"


class EmitPlacementsResponse(BaseModel):
    ok: bool
    scene_id: str
    placement_count: int
    lineage_id: str


# ── Atlas / sprite ────────────────────────────────────────────────────────────

class CreateAtlasFromPngResponse(BaseModel):
    ok: bool
    atlas_id: str
    cols: int
    rows: int
    tile_size: int
    width_px: int
    height_px: int
    src_data_url: str


class ApplySpriteAnimatorRequest(BaseModel):
    workspace_id: str
    renderer_json: dict[str, Any]
    target_entity_id: str
    atlas_id: str
    frame_w: int = 32
    frame_h: int = 32
    start_col: int = 0
    idle_row_start: int = 0
    walk_row_start: int = 1
    idle_frames: int = 4
    walk_frames: int = 8


class ApplySpriteAnimatorResponse(BaseModel):
    ok: bool
    renderer_json: dict[str, Any]
    entity_id: str
    atlas_id: str


# ── Shygazun semantic summary ─────────────────────────────────────────────────

class ShygazunInterpretRequest(BaseModel):
    workspace_id: str
    source: str
    realm_id: str = ""
    strict: bool = False


class ShygazunInterpretResponse(BaseModel):
    ok: bool
    output: str
    semantic_summary: BilingualTrust
    tokens_used: int


# ── Daisy bodyplan ────────────────────────────────────────────────────────────

class DaisyBodyplanRequest(BaseModel):
    workspace_id: str
    system_id: str = ""
    archetype: str = "humanoid"
    symmetry: Literal["bilateral", "radial", "asymmetric"] = "bilateral"
    segment_count: int = Field(default=7, ge=1, le=64)
    limb_pairs: int = Field(default=2, ge=0, le=16)
    core_token: str = "Ta"
    accent_token: str = "Ra"
    core_belonging_chain: str = ""
    accent_belonging_chain: str = ""
    seed: int = 42
    use_whole_tongue: bool = False
    daisy_symbols: list[str] = Field(default_factory=list)
    role_overrides: dict[str, str] = Field(default_factory=dict)


class DaisyBodyplanResponse(BaseModel):
    ok: bool
    bodyplan: dict[str, Any]
    voxels: list[dict[str, Any]]
    lineage_id: str


# ── Engine inbox ──────────────────────────────────────────────────────────────

class EngineInboxConsumeRequest(BaseModel):
    workspace_id: str
    actor_id: str = "player"
    max_consume: int = Field(default=20, ge=1, le=200)
    strict_validation: bool = False
    preview_only: bool = False
    messages: list[dict[str, Any]]


class EngineInboxConsumeResponse(BaseModel):
    ok: bool
    consumed: int
    remaining: int
    failed: int
    preview: bool
    results: list[dict[str, Any]]

from __future__ import annotations

from pydantic import BaseModel, Field

from .business_schemas import (
    AlchemyCraftInput,
    BlacksmithForgeInput,
    LevelApplyInput,
    MarketQuoteInput,
    MarketTradeInput,
    PerkUnlockInput,
    SkillTrainInput,
    VitriolApplyRulerInfluenceInput,
    VitriolClearExpiredInput,
    VitriolComputeInput,
)


class RendererTablesInput(BaseModel):
    workspace_id: str
    actor_id: str
    level: LevelApplyInput | None = None
    skill: SkillTrainInput | None = None
    perk: PerkUnlockInput | None = None
    alchemy: AlchemyCraftInput | None = None
    blacksmith: BlacksmithForgeInput | None = None
    market_quote: MarketQuoteInput | None = None
    market_trade: MarketTradeInput | None = None
    vitriol_apply: VitriolApplyRulerInfluenceInput | None = None
    vitriol_compute: VitriolComputeInput | None = None
    vitriol_clear: VitriolClearExpiredInput | None = None


class RendererTablesOut(BaseModel):
    workspace_id: str
    actor_id: str
    generated_at: str
    hash: str
    tables: dict[str, object] = Field(default_factory=dict)


class IsometricRenderContractInput(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    asset_pack_id: str | None = None
    strict_assets: bool = False
    renderer_atlas_versions: list[str] = Field(default_factory=lambda: ["v1", "atlas_v2"])
    renderer_material_versions: list[str] = Field(default_factory=lambda: ["v1", "mat_v3"])
    tile_width: int = 64
    tile_height: int = 32
    elevation_step: int = 16
    include_unloaded_regions: bool = False
    include_material_constraints: bool = True


class IsometricDrawableOut(BaseModel):
    drawable_id: str
    source: str
    kind: str
    x: float
    y: float
    z: int
    screen_x: float
    screen_y: float
    depth_key: float
    sprite: str
    material: str
    metadata: dict[str, object] = Field(default_factory=dict)


class IsometricRenderContractOut(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    projection: dict[str, object] = Field(default_factory=dict)
    asset_pack: dict[str, object] = Field(default_factory=dict)
    drawable_count: int
    drawables: list[IsometricDrawableOut] = Field(default_factory=list)
    stats: dict[str, object] = Field(default_factory=dict)
    hash: str


class RenderGraphContractInput(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    asset_pack_id: str | None = None
    strict_assets: bool = False
    renderer_atlas_versions: list[str] = Field(default_factory=lambda: ["v1", "atlas_v2"])
    renderer_material_versions: list[str] = Field(default_factory=lambda: ["v1", "mat_v3"])
    include_unloaded_regions: bool = False
    include_material_constraints: bool = True
    coordinate_space: str = "world_right_handed_y_up"


class RenderGraphNodeOut(BaseModel):
    node_id: str
    source: str
    kind: str
    transform: dict[str, object] = Field(default_factory=dict)
    material: str
    sprite: str
    metadata: dict[str, object] = Field(default_factory=dict)


class RenderGraphContractOut(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    coordinate_space: str
    node_count: int
    nodes: list[RenderGraphNodeOut] = Field(default_factory=list)
    asset_pack: dict[str, object] = Field(default_factory=dict)
    stats: dict[str, object] = Field(default_factory=dict)
    hash: str

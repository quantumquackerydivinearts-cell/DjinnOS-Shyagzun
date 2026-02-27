from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    workspace_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    notes: str = ""


class ContactOut(BaseModel):
    id: str
    workspace_id: str
    full_name: str
    email: str | None
    phone: str | None
    notes: str
    created_at: datetime


class BookingCreate(BaseModel):
    workspace_id: str
    contact_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    status: str = "scheduled"
    notes: str = ""


class BookingOut(BaseModel):
    id: str
    workspace_id: str
    contact_id: str | None
    starts_at: datetime
    ends_at: datetime
    status: str
    notes: str
    created_at: datetime


class LessonCreate(BaseModel):
    workspace_id: str
    title: str
    body: str = ""
    status: str = "draft"


class LessonOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    body: str
    status: str
    created_at: datetime


class ModuleCreate(BaseModel):
    workspace_id: str
    title: str
    description: str = ""
    status: str = "draft"


class ModuleOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    description: str
    status: str
    created_at: datetime


class LeadCreate(BaseModel):
    workspace_id: str
    full_name: str
    email: str | None = None
    details: str = ""
    status: str = "new"
    source: str = "internal"


class LeadOut(BaseModel):
    id: str
    workspace_id: str
    full_name: str
    email: str | None
    details: str
    status: str
    source: str
    created_at: datetime


class ClientCreate(BaseModel):
    workspace_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    status: str = "active"


class ClientOut(BaseModel):
    id: str
    workspace_id: str
    full_name: str
    email: str | None
    phone: str | None
    status: str
    created_at: datetime


class QuoteCreate(BaseModel):
    workspace_id: str
    lead_id: str | None = None
    client_id: str | None = None
    title: str
    amount_cents: int
    currency: str = "USD"
    status: str = "draft"
    is_public: bool = False
    notes: str = ""


class QuoteOut(BaseModel):
    id: str
    workspace_id: str
    lead_id: str | None
    client_id: str | None
    title: str
    amount_cents: int
    currency: str
    status: str
    is_public: bool
    notes: str
    created_at: datetime


class OrderCreate(BaseModel):
    workspace_id: str
    quote_id: str | None = None
    client_id: str | None = None
    title: str
    amount_cents: int
    currency: str = "USD"
    status: str = "open"
    notes: str = ""


class OrderOut(BaseModel):
    id: str
    workspace_id: str
    quote_id: str | None
    client_id: str | None
    title: str
    amount_cents: int
    currency: str
    status: str
    notes: str
    created_at: datetime


class InventoryItemCreate(BaseModel):
    workspace_id: str
    sku: str
    name: str
    quantity_on_hand: int = 0
    reorder_level: int = 0
    unit_cost_cents: int = 0
    currency: str = "USD"
    supplier_id: str | None = None
    notes: str = ""


class InventoryItemOut(BaseModel):
    id: str
    workspace_id: str
    sku: str
    name: str
    quantity_on_hand: int
    reorder_level: int
    unit_cost_cents: int
    currency: str
    supplier_id: str | None
    notes: str
    created_at: datetime


class SupplierCreate(BaseModel):
    workspace_id: str
    supplier_name: str
    contact_name: str = ""
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str = ""


class SupplierOut(BaseModel):
    id: str
    workspace_id: str
    supplier_name: str
    contact_name: str
    contact_email: str | None
    contact_phone: str | None
    notes: str
    created_at: datetime


class PublicCommissionInquiryCreate(BaseModel):
    workspace_id: str
    full_name: str
    email: str | None = None
    details: str = ""


class PublicCommissionQuoteOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime


class ArtisanAccessIssueInput(BaseModel):
    profile_name: str
    profile_email: str


class ArtisanAccessVerifyInput(BaseModel):
    profile_name: str
    profile_email: str
    artisan_code: str


class ArtisanAccessStatusOut(BaseModel):
    artisan_id: str
    role: str
    workshop_id: str
    profile_name: str
    profile_email: str
    artisan_access_verified: bool


class ArtisanAccessIssueOut(BaseModel):
    artisan_code: str
    status: ArtisanAccessStatusOut


class ArtisanBootstrapInput(BaseModel):
    gate_code: str
    artisan_id: str
    profile_name: str
    profile_email: str


class HeadlessQuestStep(BaseModel):
    step_id: str
    raw: str
    context: dict[str, object] = Field(default_factory=dict)


class HeadlessQuestEmitInput(BaseModel):
    workspace_id: str
    quest_id: str
    scene_id: str | None = None
    steps: list[HeadlessQuestStep]


class HeadlessQuestEmitOut(BaseModel):
    quest_id: str
    emitted: int
    emitted_step_ids: list[str]


class MeditationEmitInput(BaseModel):
    workspace_id: str
    session_id: str
    phase: str
    duration_seconds: int = 0
    tags: dict[str, str] = Field(default_factory=dict)


class MeditationEmitOut(BaseModel):
    session_id: str
    emitted: int
    phase: str


class SceneGraphNode(BaseModel):
    node_id: str
    kind: str
    x: float
    y: float
    metadata: dict[str, object] = Field(default_factory=dict)


class SceneGraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    relation: str
    metadata: dict[str, object] = Field(default_factory=dict)


class SceneGraphEmitInput(BaseModel):
    workspace_id: str
    scene_id: str
    nodes: list[SceneGraphNode]
    edges: list[SceneGraphEdge]


class SceneGraphEmitOut(BaseModel):
    scene_id: str
    nodes_emitted: int
    edges_emitted: int


class InventoryAdjustInput(BaseModel):
    workspace_id: str
    inventory_item_id: str
    delta: int
    reason: str = "gameplay"


class SaveExportOut(BaseModel):
    workspace_id: str
    generated_at: str
    timeline_count: int
    frontier_count: int
    hash: str
    payload: dict[str, object]


class LevelApplyInput(BaseModel):
    workspace_id: str
    actor_id: str
    current_level: int
    current_xp: int
    gained_xp: int
    xp_curve_base: int = 100
    xp_curve_scale: int = 25


class LevelApplyOut(BaseModel):
    actor_id: str
    level_before: int
    level_after: int
    xp_after: int
    leveled_up: bool
    levels_gained: int


class SkillTrainInput(BaseModel):
    workspace_id: str
    actor_id: str
    skill_id: str
    current_rank: int
    points_available: int
    max_rank: int = 5


class SkillTrainOut(BaseModel):
    actor_id: str
    skill_id: str
    rank_before: int
    rank_after: int
    points_remaining: int
    trained: bool


class PerkUnlockInput(BaseModel):
    workspace_id: str
    actor_id: str
    perk_id: str
    unlocked_perks: list[str] = Field(default_factory=list)
    required_level: int = 1
    actor_level: int = 1
    required_skills: dict[str, int] = Field(default_factory=dict)
    actor_skills: dict[str, int] = Field(default_factory=dict)


class PerkUnlockOut(BaseModel):
    actor_id: str
    perk_id: str
    unlocked: bool
    reason: str
    unlocked_perks: list[str]


class AlchemyCraftInput(BaseModel):
    workspace_id: str
    actor_id: str
    recipe_id: str
    ingredients: dict[str, int] = Field(default_factory=dict)
    outputs: dict[str, int] = Field(default_factory=dict)
    inventory: dict[str, int] = Field(default_factory=dict)


class AlchemyCraftOut(BaseModel):
    actor_id: str
    recipe_id: str
    crafted: bool
    reason: str
    inventory_after: dict[str, int]


class BlacksmithForgeInput(BaseModel):
    workspace_id: str
    actor_id: str
    blueprint_id: str
    materials: dict[str, int] = Field(default_factory=dict)
    outputs: dict[str, int] = Field(default_factory=dict)
    inventory: dict[str, int] = Field(default_factory=dict)
    durability_bonus: int = 0


class BlacksmithForgeOut(BaseModel):
    actor_id: str
    blueprint_id: str
    forged: bool
    reason: str
    durability_score: int
    inventory_after: dict[str, int]


class CombatantInput(BaseModel):
    id: str
    hp: int
    attack: int
    defense: int


class CombatResolveInput(BaseModel):
    workspace_id: str
    actor_id: str
    round_id: str
    attacker: CombatantInput
    defender: CombatantInput


class CombatResolveOut(BaseModel):
    actor_id: str
    round_id: str
    damage: int
    defender_hp_after: int
    defender_defeated: bool


class MarketQuoteInput(BaseModel):
    workspace_id: str
    actor_id: str
    item_id: str
    side: str
    quantity: int
    base_price_cents: int
    scarcity_bp: int = 0
    spread_bp: int = 100


class MarketQuoteOut(BaseModel):
    actor_id: str
    item_id: str
    side: str
    quantity: int
    unit_price_cents: int
    subtotal_cents: int


class MarketTradeInput(BaseModel):
    workspace_id: str
    actor_id: str
    item_id: str
    side: str
    quantity: int
    unit_price_cents: int
    fee_bp: int = 50
    wallet_cents: int
    inventory_qty: int
    available_liquidity: int


class MarketTradeOut(BaseModel):
    actor_id: str
    item_id: str
    side: str
    requested_qty: int
    filled_qty: int
    unit_price_cents: int
    subtotal_cents: int
    fee_cents: int
    total_cents: int
    wallet_after_cents: int
    inventory_after_qty: int
    status: str

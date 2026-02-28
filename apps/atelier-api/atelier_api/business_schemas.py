from __future__ import annotations

from datetime import datetime
from typing import Literal

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


class LessonProgressOut(BaseModel):
    id: str
    workspace_id: str
    actor_id: str
    lesson_id: str
    status: str
    completed_at: datetime | None
    updated_at: datetime


class LessonConsumeInput(BaseModel):
    workspace_id: str
    actor_id: str
    lesson_id: str
    status: str = "consumed"


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
    realm_id: str
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


class AlchemyInterfaceInput(BaseModel):
    workspace_id: str
    actor_id: str
    akinenwun: str


class AlchemyInterfaceOut(BaseModel):
    actor_id: str
    akinenwun: str
    interface: dict[str, object]
    render_constraints: dict[str, object]


class AlchemyCrystalInput(BaseModel):
    workspace_id: str
    actor_id: str
    crystal_type: str
    purity: int = 0
    infernal_meditation: bool = False
    vitriol_trials_cleared: bool = False
    ingredients: dict[str, int] = Field(default_factory=dict)
    outputs: dict[str, int] = Field(default_factory=dict)
    inventory: dict[str, int] = Field(default_factory=dict)


class AlchemyCrystalOut(BaseModel):
    actor_id: str
    crystal_type: str
    purity: int
    crafted: bool
    reason: str
    inventory_after: dict[str, int]
    key_flags: dict[str, object] = Field(default_factory=dict)


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
    realm_id: str = "lapidus"
    item_id: str
    side: str
    quantity: int
    base_price_cents: int
    scarcity_bp: int = 0
    spread_bp: int = 100


class MarketQuoteOut(BaseModel):
    actor_id: str
    realm_id: str
    market_id: str
    currency_code: str
    currency_name: str
    currency_backing: str
    item_id: str
    side: str
    quantity: int
    stock_available: int
    market_volatility_bp: int
    unit_price_cents: int
    subtotal_cents: int


class MarketTradeInput(BaseModel):
    workspace_id: str
    actor_id: str
    realm_id: str = "lapidus"
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
    realm_id: str
    market_id: str
    currency_code: str
    currency_name: str
    currency_backing: str
    item_id: str
    side: str
    requested_qty: int
    filled_qty: int
    stock_available: int
    market_volatility_bp: int
    unit_price_cents: int
    subtotal_cents: int
    fee_cents: int
    total_cents: int
    wallet_after_cents: int
    inventory_after_qty: int
    status: str


class RadioEvaluateInput(BaseModel):
    workspace_id: str
    actor_id: str
    underworld_state: str
    override_available: bool | None = None


class RadioEvaluateOut(BaseModel):
    actor_id: str
    underworld_state: str
    available: bool
    reason: str
    flags: dict[str, object] = Field(default_factory=dict)


class InfernalMeditationUnlockInput(BaseModel):
    workspace_id: str
    actor_id: str
    mentor: str
    location: str
    section: str
    time_of_day: str


class InfernalMeditationUnlockOut(BaseModel):
    actor_id: str
    unlocked: bool
    reason: str
    flags: dict[str, object] = Field(default_factory=dict)


class DialogueTurn(BaseModel):
    line_id: str
    speaker_id: str
    raw: str
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class DialogueEmitInput(BaseModel):
    workspace_id: str
    scene_id: str
    dialogue_id: str
    turns: list[DialogueTurn]


class DialogueEmitOut(BaseModel):
    dialogue_id: str
    scene_id: str
    emitted: int
    emitted_line_ids: list[str]


class DialogueChoiceInput(BaseModel):
    choice_id: str
    text: str = ""
    next_node_id: str = ""
    priority: int = 100
    requirements: list["GateRequirement"] = Field(default_factory=list)
    effects: dict[str, object] = Field(default_factory=dict)


class DialogueResolveInput(BaseModel):
    workspace_id: str
    actor_id: str
    dialogue_id: str
    node_id: str
    state: "GateStateInput | None" = None
    choices: list[DialogueChoiceInput] = Field(default_factory=list)


class DialogueChoiceResolveOut(BaseModel):
    choice_id: str
    text: str
    next_node_id: str
    priority: int
    eligible: bool
    matched_count: int
    total_count: int
    results: list["GateRequirementResult"] = Field(default_factory=list)


class DialogueResolveOut(BaseModel):
    dialogue_id: str
    node_id: str
    state_source: Literal["payload", "player_state"]
    eligible_choice_ids: list[str]
    selected_choice_id: str | None = None
    selected_next_node_id: str | None = None
    evaluations: list[DialogueChoiceResolveOut] = Field(default_factory=list)
    hash: str


class VitriolModifier(BaseModel):
    source_ruler: str
    delta: dict[str, int] = Field(default_factory=dict)
    reason: str
    event_id: str
    applied_tick: int = 0
    duration_turns: int = 0


class VitriolApplyRulerInfluenceInput(BaseModel):
    workspace_id: str
    actor_id: str
    base: dict[str, int] = Field(default_factory=dict)
    modifiers: list[VitriolModifier] = Field(default_factory=list)
    ruler_id: str
    delta: dict[str, int] = Field(default_factory=dict)
    reason: str
    event_id: str
    applied_tick: int = 0
    duration_turns: int = 0


class VitriolComputeInput(BaseModel):
    workspace_id: str
    actor_id: str
    base: dict[str, int] = Field(default_factory=dict)
    modifiers: list[VitriolModifier] = Field(default_factory=list)
    current_tick: int = 0


class VitriolClearExpiredInput(BaseModel):
    workspace_id: str
    actor_id: str
    base: dict[str, int] = Field(default_factory=dict)
    modifiers: list[VitriolModifier] = Field(default_factory=list)
    current_tick: int = 0


class VitriolComputeOut(BaseModel):
    actor_id: str
    effective: dict[str, int]
    active_modifiers: list[VitriolModifier]
    hash: str


class VitriolApplyOut(BaseModel):
    actor_id: str
    applied: bool
    modifier: VitriolModifier
    effective: dict[str, int]
    active_modifiers: list[VitriolModifier]
    hash: str


class VitriolClearExpiredOut(BaseModel):
    actor_id: str
    removed_count: int
    active_modifiers: list[VitriolModifier]
    effective: dict[str, int]
    hash: str


DjinnId = Literal["keshi", "giann", "drovitth"]
DjinnEffect = Literal["collapse", "open", "record"]


class DjinnOrreryMark(BaseModel):
    mark_id: str
    source_djinn_id: str
    frontier_id: str
    effect: str
    tick: int = 0
    note: str = ""


class DjinnApplyInput(BaseModel):
    workspace_id: str
    actor_id: str
    djinn_id: DjinnId
    realm_id: str
    scene_id: str
    ring_id: str = ""
    target_frontiers: list[str] = Field(default_factory=list)
    observed_marks: list[DjinnOrreryMark] = Field(default_factory=list)
    tick: int = 0
    reason: str = ""


class DjinnApplyOut(BaseModel):
    actor_id: str
    djinn_id: DjinnId
    alignment: str
    effect: DjinnEffect
    applied: bool
    frontier_effects: dict[str, str]
    scarred_frontiers: list[str]
    opened_frontiers: list[str]
    placements: list[str]
    orrery_marks: list[DjinnOrreryMark]
    hash: str


GateOperator = Literal["and", "or", "xor", "nor"]
GateSource = Literal[
    "skills",
    "inventory",
    "vitriol",
    "dialogue_flags",
    "previous_dialogue",
    "flags",
    "chaos",
    "order",
    "akashic_memory",
    "void_mark",
]
GateComparator = Literal["gte", "eq", "present"]
RuntimeActionKind = Literal[
    "levels.apply",
    "skills.train",
    "perks.unlock",
    "alchemy.craft",
    "blacksmith.forge",
    "combat.resolve",
    "market.quote",
    "market.trade",
    "vitriol.apply",
    "vitriol.compute",
    "vitriol.clear",
    "djinn.apply",
    "world.region.load",
    "world.region.preload.scenegraph",
    "world.region.unload",
    "world.stream.status",
    "world.coins.list",
    "world.markets.list",
    "world.market.stock.adjust",
    "world.market.sovereignty.transition",
    "breath.ko.evaluate",
]


class RuntimeActionInput(BaseModel):
    """Single runtime action in an ordered execution plan.

    Use `world.region.preload.scenegraph` to chunk scenegraph nodes into streamable
    world regions and enqueue deterministic region loads.
    """

    action_id: str
    kind: RuntimeActionKind
    payload: dict[str, object] = Field(default_factory=dict)


class RuntimeConsumeInput(BaseModel):
    workspace_id: str
    actor_id: str
    plan_id: str = "runtime.plan"
    actions: list[RuntimeActionInput] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_id": "main",
                    "actor_id": "player",
                    "plan_id": "world_stream_bootstrap",
                    "actions": [
                        {
                            "action_id": "preload_home",
                            "kind": "world.region.preload.scenegraph",
                            "payload": {
                                "realm_id": "lapidus",
                                "scene_id": "lapidus/player_home",
                                "chunk_size": 12,
                                "cache_policy": "stream",
                                "region_prefix": "lapidus/home",
                            },
                        },
                        {
                            "action_id": "stream_status",
                            "kind": "world.stream.status",
                            "payload": {"realm_id": "lapidus"},
                        },
                    ],
                }
            ]
        }
    }


class RuntimeActionOut(BaseModel):
    action_id: str
    kind: RuntimeActionKind
    ok: bool
    result: dict[str, object] = Field(default_factory=dict)
    error: str = ""


class RuntimeConsumeOut(BaseModel):
    workspace_id: str
    actor_id: str
    plan_id: str
    applied_count: int
    failed_count: int
    results: list[RuntimeActionOut]
    hash: str


class RuntimeReplayInput(BaseModel):
    workspace_id: str
    actor_id: str
    plan_id: str


class RuntimeReplayOut(BaseModel):
    workspace_id: str
    actor_id: str
    plan_id: str
    baseline_hash: str
    replay_hash: str
    hash_match: bool
    baseline_run_id: str
    replay: RuntimeConsumeOut


class RuntimePlanRunOut(BaseModel):
    run_id: str
    workspace_id: str
    actor_id: str
    plan_id: str
    plan_hash: str
    result_hash: str
    result_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class RuntimeActionCatalogItemOut(BaseModel):
    kind: RuntimeActionKind
    summary: str
    requires_realm: bool = False
    payload_fields: dict[str, str] = Field(default_factory=dict)
    example_payload: dict[str, object] = Field(default_factory=dict)


class RuntimeActionCatalogOut(BaseModel):
    action_count: int
    actions: list[RuntimeActionCatalogItemOut] = Field(default_factory=list)


class GateStateInput(BaseModel):
    skills: dict[str, int] = Field(default_factory=dict)
    inventory: dict[str, int] = Field(default_factory=dict)
    vitriol: dict[str, int] = Field(default_factory=dict)
    dialogue_flags: list[str] = Field(default_factory=list)
    previous_dialogue: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    chaos: dict[str, int] = Field(default_factory=dict)
    order: dict[str, int] = Field(default_factory=dict)
    akashic_memory: list[str] = Field(default_factory=list)
    void_mark: list[str] = Field(default_factory=list)


class GateRequirement(BaseModel):
    source: GateSource
    key: str
    comparator: GateComparator
    int_value: int | None = None
    str_value: str | None = None
    bool_value: bool | None = None


class GateRequirementResult(BaseModel):
    source: GateSource
    key: str
    comparator: GateComparator
    matched: bool
    actual: int | str | bool | None
    expected: int | str | bool | None
    reason: str


class GateEvaluateInput(BaseModel):
    workspace_id: str
    actor_id: str
    gate_id: str
    operator: GateOperator = "and"
    state: GateStateInput
    requirements: list[GateRequirement] = Field(default_factory=list)


class GateEvaluateOut(BaseModel):
    actor_id: str
    gate_id: str
    operator: GateOperator
    allowed: bool
    matched_count: int
    total_count: int
    results: list[GateRequirementResult]
    hash: str


class QuestTransitionInput(BaseModel):
    workspace_id: str
    actor_id: str
    quest_id: str
    event_id: str
    to_state: str
    headless: bool = True
    from_states: list[str] = Field(default_factory=list)
    set_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestTransitionOut(BaseModel):
    workspace_id: str
    actor_id: str
    quest_id: str
    event_id: str
    previous_state: str
    next_state: str
    transitioned: bool
    reason: str
    state_version: int
    hash: str


class QuestStepEdgeInput(BaseModel):
    edge_id: str
    to_step_id: str
    priority: int = 100
    requirements: list[GateRequirement] = Field(default_factory=list)
    set_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestStepEdgeResolveOut(BaseModel):
    edge_id: str
    to_step_id: str
    priority: int
    eligible: bool
    matched_count: int
    total_count: int
    results: list[GateRequirementResult] = Field(default_factory=list)


class QuestAdvanceInput(BaseModel):
    workspace_id: str
    actor_id: str
    quest_id: str
    event_id: str
    current_step_id: str
    headless: bool = True
    state: GateStateInput | None = None
    edges: list[QuestStepEdgeInput] = Field(default_factory=list)


class QuestAdvanceOut(BaseModel):
    workspace_id: str
    actor_id: str
    quest_id: str
    event_id: str
    previous_step_id: str
    next_step_id: str
    advanced: bool
    reason: str
    state_source: Literal["payload", "player_state"]
    state_version: int
    eligible_edge_ids: list[str] = Field(default_factory=list)
    selected_edge_id: str | None = None
    evaluations: list[QuestStepEdgeResolveOut] = Field(default_factory=list)
    hash: str


class QuestGraphStepInput(BaseModel):
    step_id: str
    edges: list[QuestStepEdgeInput] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestGraphUpsertInput(BaseModel):
    workspace_id: str
    quest_id: str
    version: str
    start_step_id: str
    headless: bool = True
    steps: list[QuestGraphStepInput] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestGraphOut(BaseModel):
    workspace_id: str
    quest_id: str
    version: str
    start_step_id: str
    headless: bool
    runtime_schema_version: str
    steps: list[QuestGraphStepInput] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    manifest_id: str
    payload_hash: str
    created_at: datetime


class QuestGraphListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[QuestGraphOut] = Field(default_factory=list)


class QuestGraphValidateOut(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, object] = Field(default_factory=dict)
    graph_hash: str = ""


class QuestGraphHashOut(BaseModel):
    workspace_id: str
    quest_id: str
    version: str
    manifest_id: str
    graph_hash: str


class QuestAdvanceByGraphInput(BaseModel):
    workspace_id: str
    actor_id: str
    quest_id: str
    event_id: str
    current_step_id: str
    version: str | None = None
    headless: bool = True
    state: GateStateInput | None = None


class QuestAdvanceByGraphOut(BaseModel):
    graph: QuestGraphOut
    advance: QuestAdvanceOut


class QuestAdvanceByGraphDryRunOut(BaseModel):
    graph: QuestGraphOut
    advance: QuestAdvanceOut
    persisted: bool = False


class BreathKoGenerateInput(BaseModel):
    workspace_id: str
    actor_id: str
    player_name: str
    canonical_game_number: int
    quest_completion: int
    kills: int | None = None
    deaths: int | None = None
    level: int | None = None
    max_iter: int = 4096


class BreathKoOut(BaseModel):
    breath_id: str
    workspace_id: str
    actor_id: str
    snapshot_hash: str
    player_name: str
    canonical_game_number: int
    level: int
    quest_completion: int
    kills: int
    deaths: int
    kill_patron_id: str
    kill_patron_name: str
    death_patron_id: str
    death_patron_name: str
    kd_ratio_milli: int
    chaos_meter: int
    akashic_memory_seed: str
    void_body_mark_hash: str
    azoth_int: str
    b_real: int
    b_imag: int
    max_iter: int
    escape_iter: int
    escaped: bool
    orbit_signature_hash: str
    palette_seed: int
    special_case_rank: int
    collision_attempt: int
    created_at: datetime


class BreathKoListOut(BaseModel):
    total: int
    items: list[BreathKoOut] = Field(default_factory=list)


class CharacterDictionaryCreate(BaseModel):
    workspace_id: str
    character_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    bio: str = ""
    tags: list[str] = Field(default_factory=list)
    faction: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class CharacterDictionaryOut(BaseModel):
    id: str
    workspace_id: str
    character_id: str
    name: str
    aliases: list[str]
    bio: str
    tags: list[str]
    faction: str
    metadata: dict[str, object]
    created_at: datetime


class NamedQuestCreate(BaseModel):
    workspace_id: str
    quest_id: str
    name: str
    status: str = "inactive"
    current_step: str = ""
    requirements: dict[str, object] = Field(default_factory=dict)
    rewards: dict[str, object] = Field(default_factory=dict)


class NamedQuestOut(BaseModel):
    id: str
    workspace_id: str
    quest_id: str
    name: str
    status: str
    current_step: str
    requirements: dict[str, object]
    rewards: dict[str, object]
    created_at: datetime


class JournalEntryCreate(BaseModel):
    workspace_id: str
    actor_id: str
    entry_id: str
    title: str
    body: str = ""
    kind: str = "manual"


class JournalEntryOut(BaseModel):
    id: str
    workspace_id: str
    actor_id: str
    entry_id: str
    title: str
    body: str
    kind: str
    created_at: datetime


class LayerNodeCreate(BaseModel):
    workspace_id: str
    layer_index: int
    node_key: str
    payload: dict[str, object] = Field(default_factory=dict)


class LayerNodeOut(BaseModel):
    id: str
    workspace_id: str
    layer_index: int
    node_key: str
    payload: dict[str, object]
    payload_hash: str
    created_at: datetime


class LayerEdgeCreate(BaseModel):
    workspace_id: str
    from_node_id: str
    to_node_id: str
    edge_kind: str
    metadata: dict[str, object] = Field(default_factory=dict)


class LayerEdgeOut(BaseModel):
    id: str
    workspace_id: str
    from_node_id: str
    to_node_id: str
    edge_kind: str
    metadata: dict[str, object]
    created_at: datetime


class LayerEventOut(BaseModel):
    id: str
    workspace_id: str
    event_kind: str
    actor_id: str
    node_id: str | None
    edge_id: str | None
    payload_hash: str
    created_at: datetime


class LayerTraceOut(BaseModel):
    node: LayerNodeOut
    inbound: list[LayerEdgeOut]
    outbound: list[LayerEdgeOut]


class FunctionStoreCreate(BaseModel):
    workspace_id: str
    function_id: str
    version: str
    signature: str
    body: str
    metadata: dict[str, object] = Field(default_factory=dict)


class FunctionStoreOut(BaseModel):
    id: str
    workspace_id: str
    function_id: str
    version: str
    signature: str
    body: str
    metadata: dict[str, object]
    function_hash: str
    created_at: datetime


class PlayerStateTables(BaseModel):
    levels: dict[str, object] = Field(default_factory=dict)
    skills: dict[str, object] = Field(default_factory=dict)
    perks: dict[str, object] = Field(default_factory=dict)
    vitriol: dict[str, object] = Field(default_factory=dict)
    inventory: dict[str, object] = Field(default_factory=dict)
    market: dict[str, object] = Field(default_factory=dict)
    flags: dict[str, object] = Field(default_factory=dict)
    clock: dict[str, object] = Field(default_factory=dict)


class PlayerStateOut(BaseModel):
    workspace_id: str
    actor_id: str
    state_version: int
    generated_at: str
    hash: str
    tables: PlayerStateTables


class PlayerStateApplyInput(BaseModel):
    workspace_id: str
    actor_id: str
    tables: PlayerStateTables
    mode: Literal["merge", "replace"] = "merge"


class GameEventInput(BaseModel):
    event_id: str = ""
    kind: str
    due_tick: int | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class GameTickInput(BaseModel):
    workspace_id: str
    actor_id: str
    dt_ms: int = 100
    events: list[GameEventInput] = Field(default_factory=list)


class GameTickEventResult(BaseModel):
    event_id: str = ""
    due_tick: int | None = None
    sequence: int | None = None
    kind: str
    ok: bool
    detail: str
    payload: dict[str, object] = Field(default_factory=dict)


class GameTickOut(BaseModel):
    workspace_id: str
    actor_id: str
    state_version: int
    tick: int
    dt_ms: int
    applied: int
    processed_count: int
    queued_count: int
    queue_size: int
    results: list[GameTickEventResult]
    hash: str
    tables: PlayerStateTables


class AssetManifestCreate(BaseModel):
    workspace_id: str
    realm_id: str = "lapidus"
    manifest_id: str
    name: str
    kind: str
    payload: dict[str, object] = Field(default_factory=dict)


class AssetManifestOut(BaseModel):
    id: str
    workspace_id: str
    realm_id: str
    manifest_id: str
    name: str
    kind: str
    payload: dict[str, object]
    payload_hash: str
    created_at: datetime


class RealmOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    created_at: datetime


class RealmValidateInput(BaseModel):
    realm_id: str


class RealmValidateOut(BaseModel):
    realm_id: str
    ok: bool
    reason: str


class ContentValidateInput(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    source: Literal["cobra", "json"] = "cobra"
    payload: str


class ContentValidateOut(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    source: str
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, object] = Field(default_factory=dict)


class SceneCreateInput(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    name: str
    description: str = ""
    content: dict[str, object] = Field(default_factory=dict)


class SceneUpdateInput(BaseModel):
    name: str | None = None
    description: str | None = None
    content: dict[str, object] | None = None


class SceneOut(BaseModel):
    id: str
    workspace_id: str
    realm_id: str
    scene_id: str
    name: str
    description: str
    content: dict[str, object]
    content_hash: str
    created_at: datetime
    updated_at: datetime


class SceneEmitOut(BaseModel):
    scene_id: str
    nodes_emitted: int
    edges_emitted: int


class SceneCompileInput(BaseModel):
    workspace_id: str
    realm_id: str
    scene_id: str
    name: str
    description: str = ""
    cobra_source: str


class WorldRegionLoadInput(BaseModel):
    workspace_id: str
    realm_id: str
    region_key: str
    payload: dict[str, object] = Field(default_factory=dict)
    cache_policy: str = "cache"


class WorldRegionUnloadInput(BaseModel):
    workspace_id: str
    realm_id: str
    region_key: str


class WorldRegionOut(BaseModel):
    id: str
    workspace_id: str
    realm_id: str
    region_key: str
    payload: dict[str, object]
    payload_hash: str
    cache_policy: str
    loaded: bool
    created_at: datetime
    updated_at: datetime


class WorldRegionUnloadOut(BaseModel):
    workspace_id: str
    realm_id: str
    region_key: str
    unloaded: bool


class WorldStreamStatusOut(BaseModel):
    workspace_id: str
    realm_id: str | None = None
    total_regions: int
    loaded_count: int
    unloaded_count: int
    capacity: int
    pressure: float
    policy_counts: dict[str, int]
    pressure_components: dict[str, float]
    demon_pressures: dict[str, float]
    demon_maladies: dict[str, str]


class RealmCoinOut(BaseModel):
    realm_id: str
    currency_code: str
    currency_name: str
    backing: str


class RealmMarketOut(BaseModel):
    realm_id: str
    market_id: str
    display_name: str
    dominant_operator: str
    market_network: str
    dominance_bp: int
    volatility_bp: int
    spread_bp: int
    fee_bp: int
    stock: dict[str, int]

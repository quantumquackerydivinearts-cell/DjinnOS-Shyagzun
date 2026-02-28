from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence, cast
from qqva.world_stream import WorldStreamController

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
    LeadCreate,
    LeadOut,
    InventoryItemCreate,
    InventoryItemOut,
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
    InventoryAdjustInput,
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
    GateEvaluateInput,
    GateEvaluateOut,
    GateStateInput,
    GateRequirement,
    GateRequirementResult,
    GateOperator,
    RuntimeConsumeInput,
    RuntimeConsumeOut,
    RuntimeActionOut,
    RuntimeReplayInput,
    RuntimeReplayOut,
    RuntimePlanRunOut,
    RuntimeActionCatalogOut,
    RuntimeActionCatalogItemOut,
    DialogueChoiceResolveOut,
    DialogueResolveInput,
    DialogueResolveOut,
    CharacterDictionaryCreate,
    CharacterDictionaryOut,
    NamedQuestCreate,
    NamedQuestOut,
    QuestTransitionInput,
    QuestTransitionOut,
    QuestAdvanceInput,
    QuestAdvanceByGraphInput,
    QuestAdvanceByGraphDryRunOut,
    QuestAdvanceByGraphOut,
    QuestAdvanceOut,
    QuestGraphHashOut,
    QuestGraphValidateOut,
    QuestGraphOut,
    QuestGraphListOut,
    QuestGraphStepInput,
    QuestGraphUpsertInput,
    QuestStepEdgeResolveOut,
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
    PlayerStateTables,
    GameEventInput,
    GameTickInput,
    GameTickOut,
    GameTickEventResult,
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
    DialogueEmitInput,
    DialogueEmitOut,
    VitriolApplyRulerInfluenceInput,
    VitriolApplyOut,
    VitriolClearExpiredInput,
    VitriolClearExpiredOut,
    VitriolComputeInput,
    VitriolComputeOut,
    VitriolModifier,
    DjinnApplyInput,
    DjinnApplyOut,
    DjinnOrreryMark,
    SupplierCreate,
    SupplierOut,
)
from .rendering_schemas import (
    RendererTablesInput,
    RendererTablesOut,
    IsometricRenderContractInput,
    IsometricRenderContractOut,
    IsometricDrawableOut,
    RenderGraphContractInput,
    RenderGraphContractOut,
    RenderGraphNodeOut,
)
from .kernel_integration import KernelIntegrationService
from .market_logic import get_realm_coin, get_realm_market, list_realm_coins, list_realm_markets
from .models import (
    ArtisanAccount,
    Booking,
    CRMContact,
    CharacterDictionaryEntry,
    Client,
    FunctionStoreEntry,
    InventoryItem,
    JournalEntry,
    Lead,
    LayerEdge,
    LayerEvent,
    LayerNode,
    Lesson,
    LessonProgress,
    LearningModule,
    NamedQuest,
    Order,
    Quote,
    Supplier,
    PlayerState,
    RuntimePlanRun,
    AssetManifest,
    Realm,
    Scene,
    WorldRegion,
)
from .repositories import AtelierRepository
from .validators import build_scene_graph_content_from_cobra, validate_cobra_content, validate_json_content, validate_scene_realm
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


class AtelierService:
    _QUEST_GRAPH_RUNTIME_SCHEMA_VERSION = "v1"
    _VITRIOL_AXES: tuple[str, ...] = (
        "vitality",
        "introspection",
        "tactility",
        "reflectivity",
        "ingenuity",
        "ostentation",
        "levity",
    )
    _VITRIOL_RULER_AXIS: dict[str, str] = {
        "asmodeus": "vitality",
        "satan": "introspection",
        "beelzebub": "tactility",
        "belphegor": "reflectivity",
        "leviathan": "ingenuity",
        "mammon": "ostentation",
        "lucifer": "levity",
    }
    _DEMON_PRESSURE_DEFAULTS: dict[str, float] = {
        "asmodeus": 0.0,
        "satan": 0.0,
        "beelzebub": 0.0,
        "belphegor": 0.0,
        "leviathan": 0.0,
        "mammon": 0.0,
        "lucifer": 0.0,
        "ruzoa": 0.0,
        "zukoru": 0.0,
        "kielum": 0.0,
        "othieru": 0.0,
        "po_elfan": 0.0,
        "kaganue": 0.0,
    }
    _DEMON_MALADY_DOMAINS: dict[str, str] = {
        "asmodeus": "vitality_corruption",
        "satan": "introspective_decay",
        "beelzebub": "tactile_corrosion",
        "belphegor": "reflective_stagnation",
        "leviathan": "ingenuity_distortion",
        "mammon": "ostentation_blight",
        "lucifer": "levity_collapse",
        "ruzoa": "depression",
        "zukoru": "nihilism",
        "kielum": "abuse",
        "othieru": "abandon",
        "po_elfan": "anxiety",
        "kaganue": "confusion",
    }
    _DJINN_ALIGNMENT: dict[str, str] = {
        "keshi": "chaotic_evil",
        "giann": "chaotic_good",
        "drovitth": "lawful_neutral",
    }
    _WORLD_STREAM_MAX_LOADED_REGIONS = 128

    def __init__(
        self,
        repo: AtelierRepository | None,
        kernel: KernelIntegrationService,
        world_stream: WorldStreamController | None = None,
    ) -> None:
        self._repo = repo
        self._kernel = kernel
        self._world_stream = world_stream or WorldStreamController(
            max_loaded_regions=self._WORLD_STREAM_MAX_LOADED_REGIONS
        )

    def _require_repo(self) -> AtelierRepository:
        if self._repo is None:
            raise RuntimeError("repository_unavailable")
        return self._repo

    @staticmethod
    def _canonical_json(payload: object) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _canonical_hash(payload: object) -> str:
        return hashlib.sha256(AtelierService._canonical_json(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def _csv_to_list(value: str) -> list[str]:
        if value.strip() == "":
            return []
        return [item for item in value.split(",") if item]

    @staticmethod
    def _list_to_csv(values: Sequence[str]) -> str:
        return ",".join(item.strip() for item in values if item.strip() != "")

    @staticmethod
    def _json_to_object_map(value: str) -> dict[str, object]:
        if value.strip() == "":
            return {}
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, object] = {}
        for key, item in parsed.items():
            if isinstance(key, str):
                out[key] = cast(object, item)
        return out

    @staticmethod
    def _default_player_tables() -> PlayerStateTables:
        return PlayerStateTables(
            levels={},
            skills={},
            perks={},
            vitriol={},
            inventory={},
            market={},
            flags={},
            clock={},
        )

    @staticmethod
    def _merge_player_tables(base: PlayerStateTables, incoming: PlayerStateTables) -> PlayerStateTables:
        def merge_map(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
            merged = dict(left)
            for key, value in right.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = merge_map(cast(dict[str, object], merged[key]), cast(dict[str, object], value))
                else:
                    merged[key] = value
            return merged

        return PlayerStateTables(
            levels=merge_map(base.levels, incoming.levels),
            skills=merge_map(base.skills, incoming.skills),
            perks=merge_map(base.perks, incoming.perks),
            vitriol=merge_map(base.vitriol, incoming.vitriol),
            inventory=merge_map(base.inventory, incoming.inventory),
            market=merge_map(base.market, incoming.market),
            flags=merge_map(base.flags, incoming.flags),
            clock=merge_map(base.clock, incoming.clock),
        )

    def health(self) -> None:
        self._require_repo().ping()

    def emit_placement(
        self,
        *,
        raw: str,
        context: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.place(
            raw=raw,
            context=context,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def observe(self, *, actor_id: str, workshop_id: str) -> ObserveResponse:
        return self._kernel.observe(actor_id=actor_id, workshop_id=workshop_id)

    def timeline(self, *, actor_id: str, workshop_id: str) -> Sequence[KernelEventObj]:
        return self._kernel.timeline(actor_id=actor_id, workshop_id=workshop_id)

    def edges(self, *, actor_id: str, workshop_id: str) -> Sequence[EdgeObj]:
        return self._kernel.edges(actor_id=actor_id, workshop_id=workshop_id)

    def frontiers(self, *, actor_id: str, workshop_id: str) -> Sequence[FrontierObj]:
        return self._kernel.frontiers(actor_id=actor_id, workshop_id=workshop_id)

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.attest(
            witness_id=witness_id,
            attestation_kind=attestation_kind,
            attestation_tag=attestation_tag,
            payload=payload,
            target=target,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
        policy: Mapping[str, Any] | None = None,
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.akinenwun_lookup(
            akinenwun=akinenwun,
            mode=mode,
            ingest=ingest,
            policy=policy or {},
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def list_contacts(self, workspace_id: str) -> Sequence[ContactOut]:
        rows = self._require_repo().list_contacts(workspace_id=workspace_id)
        return [ContactOut.model_validate(row, from_attributes=True) for row in rows]

    def create_contact(self, payload: ContactCreate) -> ContactOut:
        row = CRMContact(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
        out = self._require_repo().create_contact(row)
        return ContactOut.model_validate(out, from_attributes=True)

    def list_bookings(self, workspace_id: str) -> Sequence[BookingOut]:
        rows = self._require_repo().list_bookings(workspace_id=workspace_id)
        return [BookingOut.model_validate(row, from_attributes=True) for row in rows]

    def create_booking(self, payload: BookingCreate) -> BookingOut:
        row = Booking(
            workspace_id=payload.workspace_id,
            contact_id=payload.contact_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            status=payload.status,
            notes=payload.notes,
        )
        out = self._require_repo().create_booking(row)
        return BookingOut.model_validate(out, from_attributes=True)

    def list_lessons(self, workspace_id: str) -> Sequence[LessonOut]:
        rows = self._require_repo().list_lessons(workspace_id=workspace_id)
        return [LessonOut.model_validate(row, from_attributes=True) for row in rows]

    def create_lesson(self, payload: LessonCreate) -> LessonOut:
        row = Lesson(
            workspace_id=payload.workspace_id,
            title=payload.title,
            body=payload.body,
            status=payload.status,
        )
        out = self._require_repo().create_lesson(row)
        return LessonOut.model_validate(out, from_attributes=True)

    def list_lesson_progress(self, workspace_id: str, actor_id: str) -> Sequence[LessonProgressOut]:
        rows = self._require_repo().list_lesson_progress(workspace_id=workspace_id, actor_id=actor_id)
        return [LessonProgressOut.model_validate(row, from_attributes=True) for row in rows]

    def consume_lesson(self, payload: LessonConsumeInput) -> LessonProgressOut:
        repo = self._require_repo()
        row = repo.get_lesson_progress(payload.workspace_id, payload.actor_id, payload.lesson_id)
        now = datetime.now(timezone.utc)
        if row is None:
            row = LessonProgress(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                lesson_id=payload.lesson_id,
                status=payload.status,
                completed_at=now if payload.status == "consumed" else None,
                updated_at=now,
            )
        else:
            row.status = payload.status
            if payload.status == "consumed" and row.completed_at is None:
                row.completed_at = now
            row.updated_at = now
        saved = repo.save_lesson_progress(row)
        return LessonProgressOut.model_validate(saved, from_attributes=True)

    def list_modules(self, workspace_id: str) -> Sequence[ModuleOut]:
        rows = self._require_repo().list_modules(workspace_id=workspace_id)
        return [ModuleOut.model_validate(row, from_attributes=True) for row in rows]

    def create_module(self, payload: ModuleCreate) -> ModuleOut:
        row = LearningModule(
            workspace_id=payload.workspace_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
        )
        out = self._require_repo().create_module(row)
        return ModuleOut.model_validate(out, from_attributes=True)

    def list_leads(self, workspace_id: str) -> Sequence[LeadOut]:
        rows = self._require_repo().list_leads(workspace_id=workspace_id)
        return [LeadOut.model_validate(row, from_attributes=True) for row in rows]

    def create_lead(self, payload: LeadCreate) -> LeadOut:
        row = Lead(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            details=payload.details,
            status=payload.status,
            source=payload.source,
        )
        out = self._require_repo().create_lead(row)
        return LeadOut.model_validate(out, from_attributes=True)

    def list_clients(self, workspace_id: str) -> Sequence[ClientOut]:
        rows = self._require_repo().list_clients(workspace_id=workspace_id)
        return [ClientOut.model_validate(row, from_attributes=True) for row in rows]

    def create_client(self, payload: ClientCreate) -> ClientOut:
        row = Client(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            status=payload.status,
        )
        out = self._require_repo().create_client(row)
        return ClientOut.model_validate(out, from_attributes=True)

    def list_quotes(self, workspace_id: str) -> Sequence[QuoteOut]:
        rows = self._require_repo().list_quotes(workspace_id=workspace_id)
        return [QuoteOut.model_validate(row, from_attributes=True) for row in rows]

    def create_quote(self, payload: QuoteCreate) -> QuoteOut:
        row = Quote(
            workspace_id=payload.workspace_id,
            lead_id=payload.lead_id,
            client_id=payload.client_id,
            title=payload.title,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            status=payload.status,
            is_public=payload.is_public,
            notes=payload.notes,
        )
        out = self._require_repo().create_quote(row)
        return QuoteOut.model_validate(out, from_attributes=True)

    def list_orders(self, workspace_id: str) -> Sequence[OrderOut]:
        rows = self._require_repo().list_orders(workspace_id=workspace_id)
        return [OrderOut.model_validate(row, from_attributes=True) for row in rows]

    def create_order(self, payload: OrderCreate) -> OrderOut:
        row = Order(
            workspace_id=payload.workspace_id,
            quote_id=payload.quote_id,
            client_id=payload.client_id,
            title=payload.title,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            status=payload.status,
            notes=payload.notes,
        )
        out = self._require_repo().create_order(row)
        return OrderOut.model_validate(out, from_attributes=True)

    def list_inventory_items(self, workspace_id: str) -> Sequence[InventoryItemOut]:
        rows = self._require_repo().list_inventory_items(workspace_id=workspace_id)
        return [InventoryItemOut.model_validate(row, from_attributes=True) for row in rows]

    def create_inventory_item(self, payload: InventoryItemCreate) -> InventoryItemOut:
        row = InventoryItem(
            workspace_id=payload.workspace_id,
            sku=payload.sku,
            name=payload.name,
            quantity_on_hand=payload.quantity_on_hand,
            reorder_level=payload.reorder_level,
            unit_cost_cents=payload.unit_cost_cents,
            currency=payload.currency,
            supplier_id=payload.supplier_id,
            notes=payload.notes,
        )
        out = self._require_repo().create_inventory_item(row)
        return InventoryItemOut.model_validate(out, from_attributes=True)

    def adjust_inventory_item(self, payload: InventoryAdjustInput) -> InventoryItemOut:
        repo = self._require_repo()
        row = repo.get_inventory_item(payload.workspace_id, payload.inventory_item_id)
        if row is None:
            raise ValueError("inventory_item_not_found")
        row.quantity_on_hand = row.quantity_on_hand + payload.delta
        saved = repo.update_inventory_item(row)
        return InventoryItemOut.model_validate(saved, from_attributes=True)

    def emit_headless_quest(
        self,
        *,
        payload: HeadlessQuestEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> HeadlessQuestEmitOut:
        emitted_step_ids: list[str] = []
        for step in payload.steps:
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "quest_id": payload.quest_id,
                "step_id": step.step_id,
                "headless": True,
            }
            if payload.scene_id is not None:
                context["scene_id"] = payload.scene_id
            if step.context:
                context["step_context"] = dict(step.context)
            self._kernel.place(
                raw=step.raw,
                context=context,
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
            emitted_step_ids.append(step.step_id)
        return HeadlessQuestEmitOut(
            quest_id=payload.quest_id,
            emitted=len(emitted_step_ids),
            emitted_step_ids=emitted_step_ids,
        )

    def emit_meditation(
        self,
        *,
        payload: MeditationEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> MeditationEmitOut:
        raw = f"meditation.session {payload.session_id} phase={payload.phase} duration={payload.duration_seconds}"
        context: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "session_id": payload.session_id,
            "phase": payload.phase,
            "duration_seconds": payload.duration_seconds,
            "tags": dict(payload.tags),
            "headless": True,
        }
        self._kernel.place(
            raw=raw,
            context=context,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return MeditationEmitOut(session_id=payload.session_id, emitted=1, phase=payload.phase)

    def emit_scene_graph(
        self,
        *,
        payload: SceneGraphEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> SceneGraphEmitOut:
        realm_error = validate_scene_realm(payload.scene_id, payload.realm_id)
        if realm_error:
            raise ValueError(realm_error)
        sorted_nodes = sorted(payload.nodes, key=lambda node: node.node_id)
        sorted_edges = sorted(payload.edges, key=lambda edge: (edge.from_node_id, edge.to_node_id, edge.relation))
        for node in sorted_nodes:
            raw = f"scene.node {payload.scene_id} {node.node_id} {node.kind} {node.x} {node.y}"
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "realm_id": payload.realm_id,
                "scene_id": payload.scene_id,
                "node_id": node.node_id,
                "metadata": dict(node.metadata),
            }
            self._kernel.place(raw=raw, context=context, actor_id=actor_id, workshop_id=workshop_id)
        for edge in sorted_edges:
            raw = f"scene.edge {payload.scene_id} {edge.from_node_id} {edge.to_node_id} {edge.relation}"
            context = {
                "workspace_id": payload.workspace_id,
                "realm_id": payload.realm_id,
                "scene_id": payload.scene_id,
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
                "relation": edge.relation,
                "metadata": dict(edge.metadata),
            }
            self._kernel.place(raw=raw, context=context, actor_id=actor_id, workshop_id=workshop_id)
        return SceneGraphEmitOut(
            scene_id=payload.scene_id,
            nodes_emitted=len(sorted_nodes),
            edges_emitted=len(sorted_edges),
        )

    def export_save_snapshot(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> SaveExportOut:
        timeline = list(self._kernel.timeline(actor_id=actor_id, workshop_id=workshop_id))
        frontiers = list(self._kernel.frontiers(actor_id=actor_id, workshop_id=workshop_id))
        observe = self._kernel.observe(actor_id=actor_id, workshop_id=workshop_id)
        payload: dict[str, object] = {
            "workspace_id": workspace_id,
            "clock": observe.get("clock", {}),
            "frontiers": frontiers,
            "timeline": timeline,
            "candidates_by_frontier": observe.get("candidates_by_frontier", {}),
            "eligible_by_frontier": observe.get("eligible_by_frontier", {}),
            "refusals": observe.get("refusals", []),
        }
        return SaveExportOut(
            workspace_id=workspace_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            timeline_count=len(timeline),
            frontier_count=len(frontiers),
            hash=self._canonical_hash(payload),
            payload=payload,
        )

    def _player_state_to_tables(self, row: PlayerState) -> PlayerStateTables:
        return PlayerStateTables(
            levels=self._json_to_object_map(row.levels_json),
            skills=self._json_to_object_map(row.skills_json),
            perks=self._json_to_object_map(row.perks_json),
            vitriol=self._json_to_object_map(row.vitriol_json),
            inventory=self._json_to_object_map(row.inventory_json),
            market=self._json_to_object_map(row.market_json),
            flags=self._json_to_object_map(row.flags_json),
            clock=self._json_to_object_map(row.clock_json),
        )

    def _ensure_player_state(self, workspace_id: str, actor_id: str) -> PlayerState:
        repo = self._require_repo()
        row = repo.get_player_state(workspace_id, actor_id)
        if row is not None:
            return row
        defaults = self._default_player_tables()
        row = PlayerState(
            workspace_id=workspace_id,
            actor_id=actor_id,
            state_version=1,
            levels_json=self._canonical_json(defaults.levels),
            skills_json=self._canonical_json(defaults.skills),
            perks_json=self._canonical_json(defaults.perks),
            vitriol_json=self._canonical_json(defaults.vitriol),
            inventory_json=self._canonical_json(defaults.inventory),
            market_json=self._canonical_json(defaults.market),
            flags_json=self._canonical_json(defaults.flags),
            clock_json=self._canonical_json(defaults.clock),
        )
        return repo.save_player_state(row)

    def get_player_state(
        self,
        *,
        workspace_id: str,
        actor_id: str,
    ) -> PlayerStateOut:
        row = self._ensure_player_state(workspace_id, actor_id)
        tables = self._player_state_to_tables(row)
        hash_payload: dict[str, object] = {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "state_version": row.state_version,
            "tables": tables.model_dump(),
        }
        return PlayerStateOut(
            workspace_id=workspace_id,
            actor_id=actor_id,
            state_version=row.state_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=tables,
        )

    def apply_player_state(
        self,
        *,
        payload: PlayerStateApplyInput,
        actor_id: str,
        workshop_id: str,
    ) -> PlayerStateOut:
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        current = self._player_state_to_tables(row)
        if payload.mode == "replace":
            next_tables = payload.tables
        else:
            next_tables = self._merge_player_tables(current, payload.tables)
        row.state_version = max(1, int(row.state_version) + 1)
        row.levels_json = self._canonical_json(next_tables.levels)
        row.skills_json = self._canonical_json(next_tables.skills)
        row.perks_json = self._canonical_json(next_tables.perks)
        row.vitriol_json = self._canonical_json(next_tables.vitriol)
        row.inventory_json = self._canonical_json(next_tables.inventory)
        row.market_json = self._canonical_json(next_tables.market)
        row.flags_json = self._canonical_json(next_tables.flags)
        row.clock_json = self._canonical_json(next_tables.clock)
        row.updated_at = datetime.now(timezone.utc)
        repo.save_player_state(row)

        self._kernel.place(
            raw=f"game.state.apply {payload.actor_id} mode={payload.mode}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "player_state_apply",
                "state_version": row.state_version,
                "tables": next_tables.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "state_version": row.state_version,
            "tables": next_tables.model_dump(),
        }
        return PlayerStateOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            state_version=row.state_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=next_tables,
        )

    @staticmethod
    def _int_from_table(value: object, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _list_from_table(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    @staticmethod
    def _dict_from_table(value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _list_of_dicts(value: object) -> list[dict[str, object]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _event_payload_with_defaults(
        self,
        payload: Mapping[str, object],
        workspace_id: str,
        actor_id: str,
    ) -> dict[str, object]:
        merged = dict(payload)
        merged.setdefault("workspace_id", workspace_id)
        merged.setdefault("actor_id", actor_id)
        return merged

    def _apply_game_event(
        self,
        *,
        event: GameEventInput,
        tables: PlayerStateTables,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> tuple[PlayerStateTables, GameTickEventResult]:
        kind = event.kind.strip().lower()
        payload = self._event_payload_with_defaults(event.payload, workspace_id, actor_id)
        updated_tables = tables
        try:
            if kind == "levels.apply":
                current_level = self._int_from_table(tables.levels.get("current_level"), 1)
                current_xp = self._int_from_table(tables.levels.get("current_xp"), 0)
                payload.setdefault("current_level", current_level)
                payload.setdefault("current_xp", current_xp)
                level_payload = LevelApplyInput.model_validate(payload)
                result = self.apply_level_progress(
                    payload=level_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                levels = dict(tables.levels)
                levels["current_level"] = result.level_after
                levels["current_xp"] = result.xp_after
                levels["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "levels": levels})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "skills.train":
                ranks = self._dict_from_table(tables.skills.get("ranks"))
                skill_id = str(payload.get("skill_id") or "")
                payload.setdefault("current_rank", self._int_from_table(ranks.get(skill_id, 0), 0))
                payload.setdefault("points_available", self._int_from_table(tables.skills.get("points_available"), 0))
                skill_payload = SkillTrainInput.model_validate(payload)
                result = self.train_skill(
                    payload=skill_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                ranks[skill_payload.skill_id] = result.rank_after
                skills = dict(tables.skills)
                skills["ranks"] = ranks
                skills["points_available"] = result.points_remaining
                skills["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "skills": skills})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "perks.unlock":
                unlocked = self._list_from_table(tables.perks.get("unlocked"))
                payload.setdefault("unlocked_perks", unlocked)
                payload.setdefault("actor_level", self._int_from_table(tables.levels.get("current_level"), 1))
                payload.setdefault("actor_skills", self._dict_from_table(tables.skills.get("ranks")))
                perk_payload = PerkUnlockInput.model_validate(payload)
                result = self.unlock_perk(
                    payload=perk_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                perks = dict(tables.perks)
                perks["unlocked"] = result.unlocked_perks
                perks["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "perks": perks})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "alchemy.craft":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                alchemy_payload = AlchemyCraftInput.model_validate(payload)
                result = self.craft_alchemy(
                    payload=alchemy_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                alchemy = dict(tables.alchemy)
                alchemy["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "alchemy": alchemy})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "alchemy.interface":
                alchemy_payload = AlchemyInterfaceInput.model_validate(payload)
                result = self.build_alchemy_interface(
                    payload=alchemy_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                alchemy = dict(tables.alchemy)
                alchemy["interface"] = result.interface
                alchemy["constraints"] = result.render_constraints
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "alchemy": alchemy})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "alchemy.crystal":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                flags = self._dict_from_table(tables.flags)
                payload.setdefault("infernal_meditation", bool(flags.get("infernal_meditation")))
                payload.setdefault("vitriol_trials_cleared", bool(flags.get("vitriol_trials_cleared")))
                crystal_payload = AlchemyCrystalInput.model_validate(payload)
                result = self.craft_alchemy_crystal(
                    payload=crystal_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                alchemy = dict(tables.alchemy)
                alchemy["last_crystal"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "alchemy": alchemy})
                if result.key_flags:
                    flags = dict(updated_tables.flags)
                    flags.update(result.key_flags)
                    updated_tables = PlayerStateTables(**{**updated_tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=result.crafted, detail=result.reason, payload=result.model_dump())
            if kind == "blacksmith.forge":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                forge_payload = BlacksmithForgeInput.model_validate(payload)
                result = self.forge_blacksmith(
                    payload=forge_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                blacksmith = dict(tables.blacksmith)
                blacksmith["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "blacksmith": blacksmith})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "market.quote":
                quote_payload = MarketQuoteInput.model_validate(payload)
                result = self.market_quote(
                    payload=quote_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                market = dict(tables.market)
                market["last_quote"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "market": market})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "market.trade":
                market_inv = self._dict_from_table(tables.market.get("inventory"))
                payload.setdefault("wallet_cents", self._int_from_table(tables.market.get("wallet_cents"), 0))
                payload.setdefault("inventory_qty", self._int_from_table(market_inv.get(str(payload.get("item_id") or "")), 0))
                payload.setdefault("available_liquidity", self._int_from_table(tables.market.get("available_liquidity"), 0))
                trade_payload = MarketTradeInput.model_validate(payload)
                result = self.market_trade(
                    payload=trade_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                market = dict(tables.market)
                market_inv = dict(market_inv)
                market_inv[result.item_id] = result.inventory_after_qty
                market["inventory"] = market_inv
                market["wallet_cents"] = result.wallet_after_cents
                market["last_trade"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "market": market})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.status, payload=result.model_dump())
            if kind == "radio.evaluate":
                radio_payload = RadioEvaluateInput.model_validate(payload)
                result = self.evaluate_radio_availability(
                    payload=radio_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                flags = dict(tables.flags)
                flags.update(result.flags)
                flags["last_radio"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "infernal_meditation.unlock":
                unlock_payload = InfernalMeditationUnlockInput.model_validate(payload)
                result = self.unlock_infernal_meditation(
                    payload=unlock_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                flags = dict(tables.flags)
                flags.update(result.flags)
                flags["last_infernal_meditation"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=result.unlocked, detail=result.reason, payload=result.model_dump())
            if kind == "vitriol.apply":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolApplyRulerInfluenceInput.model_validate(payload)
                result = self.vitriol_apply_ruler_influence(
                    payload=vitriol_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "vitriol.compute":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolComputeInput.model_validate(payload)
                result = self.vitriol_compute(payload=vitriol_payload)
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "vitriol.clear":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolClearExpiredInput.model_validate(payload)
                result = self.vitriol_clear_expired(
                    payload=vitriol_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "inventory.adjust":
                item_id = str(payload.get("item_id") or "")
                delta = self._int_from_table(payload.get("delta"), 0)
                inventory = dict(tables.inventory)
                items = dict(self._dict_from_table(inventory.get("items")))
                items[item_id] = self._int_from_table(items.get(item_id, 0), 0) + delta
                inventory["items"] = items
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inventory})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload={"item_id": item_id, "delta": delta})
            if kind == "flags.set":
                key = str(payload.get("key") or "")
                value = bool(payload.get("value"))
                flags = dict(tables.flags)
                flags[key] = value
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload={"key": key, "value": value})
        except Exception as exc:
            return tables, GameTickEventResult(kind=event.kind, ok=False, detail=str(exc), payload=dict(payload))
        return tables, GameTickEventResult(kind=event.kind, ok=False, detail="unsupported_event", payload=dict(payload))

    def game_tick(
        self,
        *,
        payload: GameTickInput,
        actor_id: str,
        workshop_id: str,
    ) -> GameTickOut:
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        updated_tables = tables
        clock = dict(updated_tables.clock)
        tick_before = self._int_from_table(clock.get("tick"), 0)
        tick_after = tick_before + 1

        raw_queue = self._list_of_dicts(clock.get("event_queue"))
        normalized_queue: list[dict[str, object]] = []
        next_seq = self._int_from_table(clock.get("next_event_seq"), 1)
        for item in raw_queue:
            kind = str(item.get("kind") or "").strip()
            if kind == "":
                continue
            payload_obj = item.get("payload")
            queue_payload = payload_obj if isinstance(payload_obj, dict) else {}
            event_id = str(item.get("event_id") or "")
            due_tick = self._int_from_table(item.get("due_tick"), tick_after)
            seq = self._int_from_table(item.get("seq"), next_seq)
            next_seq = max(next_seq, seq + 1)
            normalized_queue.append(
                {
                    "event_id": event_id,
                    "kind": kind,
                    "due_tick": due_tick,
                    "seq": seq,
                    "payload": queue_payload,
                }
            )

        for event in payload.events:
            due_tick = event.due_tick if event.due_tick is not None else tick_after
            normalized_queue.append(
                {
                    "event_id": event.event_id,
                    "kind": event.kind,
                    "due_tick": int(due_tick),
                    "seq": next_seq,
                    "payload": dict(event.payload),
                }
            )
            next_seq += 1

        due_events = [item for item in normalized_queue if self._int_from_table(item.get("due_tick"), tick_after) <= tick_after]
        pending_events = [item for item in normalized_queue if self._int_from_table(item.get("due_tick"), tick_after) > tick_after]
        due_events.sort(
            key=lambda item: (
                self._int_from_table(item.get("due_tick"), tick_after),
                self._int_from_table(item.get("seq"), 0),
                str(item.get("kind") or ""),
                self._canonical_hash(item.get("payload", {})),
                str(item.get("event_id") or ""),
            )
        )

        results: list[GameTickEventResult] = []
        for queued in due_events:
            runtime_event = GameEventInput(
                event_id=str(queued.get("event_id") or ""),
                kind=str(queued.get("kind") or ""),
                due_tick=self._int_from_table(queued.get("due_tick"), tick_after),
                payload=cast(dict[str, object], queued.get("payload", {})),
            )
            updated_tables, result = self._apply_game_event(
                event=runtime_event,
                tables=updated_tables,
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                workshop_id=workshop_id,
            )
            results.append(
                result.model_copy(
                    update={
                        "event_id": runtime_event.event_id,
                        "due_tick": runtime_event.due_tick,
                        "sequence": self._int_from_table(queued.get("seq"), 0),
                    }
                )
            )

        clock = dict(updated_tables.clock)
        clock["tick"] = tick_after
        clock["dt_ms"] = max(0, int(payload.dt_ms))
        clock["next_event_seq"] = next_seq
        clock["event_queue"] = [
            {
                "event_id": str(item.get("event_id") or ""),
                "kind": str(item.get("kind") or ""),
                "due_tick": self._int_from_table(item.get("due_tick"), tick_after),
                "seq": self._int_from_table(item.get("seq"), 0),
                "payload": cast(dict[str, object], item.get("payload", {})),
            }
            for item in sorted(
                pending_events,
                key=lambda item: (
                    self._int_from_table(item.get("due_tick"), tick_after),
                    self._int_from_table(item.get("seq"), 0),
                ),
            )
        ]
        clock["last_processed_count"] = len(due_events)
        clock["last_queued_count"] = len(pending_events)
        updated_tables = PlayerStateTables(**{**updated_tables.model_dump(), "clock": clock})
        row.state_version = max(1, int(row.state_version) + 1)
        row.levels_json = self._canonical_json(updated_tables.levels)
        row.skills_json = self._canonical_json(updated_tables.skills)
        row.perks_json = self._canonical_json(updated_tables.perks)
        row.vitriol_json = self._canonical_json(updated_tables.vitriol)
        row.inventory_json = self._canonical_json(updated_tables.inventory)
        row.market_json = self._canonical_json(updated_tables.market)
        row.flags_json = self._canonical_json(updated_tables.flags)
        row.clock_json = self._canonical_json(updated_tables.clock)
        row.updated_at = datetime.now(timezone.utc)
        repo.save_player_state(row)

        self._kernel.place(
            raw=f"game.state.tick {payload.actor_id} events={len(payload.events)}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "game_tick",
                "state_version": row.state_version,
                "tick": clock["tick"],
                "results": [item.model_dump() for item in results],
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "state_version": row.state_version,
            "tick": clock["tick"],
            "dt_ms": payload.dt_ms,
            "results": [item.model_dump() for item in results],
            "tables": updated_tables.model_dump(),
        }
        return GameTickOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            state_version=row.state_version,
            tick=clock["tick"],
            dt_ms=payload.dt_ms,
            applied=sum(1 for item in results if item.ok),
            processed_count=len(due_events),
            queued_count=len(pending_events),
            queue_size=len(pending_events),
            results=results,
            hash=self._canonical_hash(hash_payload),
            tables=updated_tables,
        )

    def apply_level_progress(
        self,
        *,
        payload: LevelApplyInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> LevelApplyOut:
        level_before = max(1, payload.current_level)
        xp = max(0, payload.current_xp) + max(0, payload.gained_xp)
        level = level_before

        def xp_needed(target_level: int) -> int:
            return max(1, payload.xp_curve_base + ((target_level - 1) * payload.xp_curve_scale))

        gained_levels = 0
        while xp >= xp_needed(level):
            xp -= xp_needed(level)
            level += 1
            gained_levels += 1

        result = LevelApplyOut(
            actor_id=payload.actor_id,
            level_before=level_before,
            level_after=level,
            xp_after=xp,
            leveled_up=gained_levels > 0,
            levels_gained=gained_levels,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.level.apply {payload.actor_id} +xp={payload.gained_xp}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "level_progress",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def train_skill(
        self,
        *,
        payload: SkillTrainInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> SkillTrainOut:
        rank_before = max(0, payload.current_rank)
        points = max(0, payload.points_available)
        max_rank = max(1, payload.max_rank)
        trained = points > 0 and rank_before < max_rank
        rank_after = rank_before + 1 if trained else rank_before
        points_after = points - 1 if trained else points
        result = SkillTrainOut(
            actor_id=payload.actor_id,
            skill_id=payload.skill_id,
            rank_before=rank_before,
            rank_after=rank_after,
            points_remaining=points_after,
            trained=trained,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.skill.train {payload.actor_id} {payload.skill_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "skill_train",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def unlock_perk(
        self,
        *,
        payload: PerkUnlockInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> PerkUnlockOut:
        unlocked_set = set(payload.unlocked_perks)
        if payload.perk_id in unlocked_set:
            result = PerkUnlockOut(
                actor_id=payload.actor_id,
                perk_id=payload.perk_id,
                unlocked=False,
                reason="already_unlocked",
                unlocked_perks=sorted(unlocked_set),
            )
        elif payload.actor_level < payload.required_level:
            result = PerkUnlockOut(
                actor_id=payload.actor_id,
                perk_id=payload.perk_id,
                unlocked=False,
                reason="level_requirement_not_met",
                unlocked_perks=sorted(unlocked_set),
            )
        else:
            missing = [
                skill_id
                for skill_id, required_rank in payload.required_skills.items()
                if payload.actor_skills.get(skill_id, 0) < required_rank
            ]
            if missing:
                result = PerkUnlockOut(
                    actor_id=payload.actor_id,
                    perk_id=payload.perk_id,
                    unlocked=False,
                    reason="skill_requirement_not_met",
                    unlocked_perks=sorted(unlocked_set),
                )
            else:
                unlocked_set.add(payload.perk_id)
                result = PerkUnlockOut(
                    actor_id=payload.actor_id,
                    perk_id=payload.perk_id,
                    unlocked=True,
                    reason="ok",
                    unlocked_perks=sorted(unlocked_set),
                )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.perk.unlock {payload.actor_id} {payload.perk_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "perk_unlock",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _apply_recipe(
        *,
        inventory: Mapping[str, int],
        consume: Mapping[str, int],
        produce: Mapping[str, int],
    ) -> tuple[bool, str, dict[str, int]]:
        next_inventory: dict[str, int] = {key: max(0, int(value)) for key, value in inventory.items()}
        for key, needed in consume.items():
            required = max(0, int(needed))
            if next_inventory.get(key, 0) < required:
                return False, f"missing:{key}", next_inventory
        for key, needed in consume.items():
            required = max(0, int(needed))
            next_inventory[key] = max(0, next_inventory.get(key, 0) - required)
        for key, amount in produce.items():
            gain = max(0, int(amount))
            next_inventory[key] = next_inventory.get(key, 0) + gain
        return True, "ok", next_inventory

    def craft_alchemy(
        self,
        *,
        payload: AlchemyCraftInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyCraftOut:
        crafted, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.ingredients,
            produce=payload.outputs,
        )
        result = AlchemyCraftOut(
            actor_id=payload.actor_id,
            recipe_id=payload.recipe_id,
            crafted=crafted,
            reason=reason,
            inventory_after=inventory_after,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.craft {payload.actor_id} {payload.recipe_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_craft",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _asmodian_ring_for_purity(purity: int) -> tuple[str, int]:
        rings = ["Pride", "Greed", "Gluttony", "Envy", "Sloth", "Wrath", "Lust"]
        normalized = max(0, min(100, int(purity)))
        idx = round((normalized / 100) * (len(rings) - 1))
        return rings[idx], idx

    def craft_alchemy_crystal(
        self,
        *,
        payload: AlchemyCrystalInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyCrystalOut:
        crafted, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.ingredients,
            produce=payload.outputs,
        )
        purity = max(0, min(100, int(payload.purity)))
        crystal_type = str(payload.crystal_type or "").strip().lower()
        key_flags: dict[str, object] = {}
        infernal_meditation = bool(payload.infernal_meditation)
        vitriol_trials_cleared = bool(payload.vitriol_trials_cleared)
        if crafted:
            if crystal_type == "radio":
                key_flags = {
                    "radio_key": True,
                    "radio_crystal_purity": purity,
                    "overworld_key": True,
                }
            elif crystal_type == "asmodian":
                ring, ring_index = self._asmodian_ring_for_purity(purity)
                key_flags = {
                    "asmodian_key": True,
                    "asmodian_crystal_purity": purity,
                    "underworld_ring": ring,
                    "underworld_ring_index": ring_index,
                    "underworld_visitors_access": infernal_meditation,
                    "underworld_royalty_access": vitriol_trials_cleared,
                }
            else:
                reason = "unknown_crystal_type"
                crafted = False
        result = AlchemyCrystalOut(
            actor_id=payload.actor_id,
            crystal_type=crystal_type,
            purity=purity,
            crafted=crafted,
            reason=reason,
            inventory_after=inventory_after,
            key_flags=key_flags,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.crystal {payload.actor_id} {crystal_type}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_crystal",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def build_alchemy_interface(
        self,
        *,
        payload: AlchemyInterfaceInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyInterfaceOut:
        from qqva.shygazun_compiler import compile_akinenwun_to_ir, derive_render_constraints

        ir = compile_akinenwun_to_ir(payload.akinenwun)
        constraints = derive_render_constraints(ir)
        interface = constraints.get("alchemy_interface", {})
        result = AlchemyInterfaceOut(
            actor_id=payload.actor_id,
            akinenwun=payload.akinenwun,
            interface=cast(dict[str, object], interface),
            render_constraints=cast(dict[str, object], constraints),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.interface {payload.actor_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_interface",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def forge_blacksmith(
        self,
        *,
        payload: BlacksmithForgeInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> BlacksmithForgeOut:
        forged, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.materials,
            produce=payload.outputs,
        )
        durability = 0
        if forged:
            durability = max(1, sum(max(0, int(v)) for v in payload.materials.values()) + payload.durability_bonus)
        result = BlacksmithForgeOut(
            actor_id=payload.actor_id,
            blueprint_id=payload.blueprint_id,
            forged=forged,
            reason=reason,
            durability_score=durability,
            inventory_after=inventory_after,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.blacksmith.forge {payload.actor_id} {payload.blueprint_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "blacksmith_forge",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def resolve_combat(
        self,
        *,
        payload: CombatResolveInput,
        actor_id: str,
        workshop_id: str,
    ) -> CombatResolveOut:
        base_attack = max(0, payload.attacker.attack)
        base_defense = max(0, payload.defender.defense)
        damage = max(0, base_attack - base_defense)
        defender_hp_after = max(0, payload.defender.hp - damage)
        result = CombatResolveOut(
            actor_id=payload.actor_id,
            round_id=payload.round_id,
            damage=damage,
            defender_hp_after=defender_hp_after,
            defender_defeated=defender_hp_after == 0,
        )
        self._kernel.place(
            raw=f"game.combat.resolve {payload.actor_id} {payload.round_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "combat_resolve",
                "attacker_id": payload.attacker.id,
                "defender_id": payload.defender.id,
                "result": result.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return result

    def market_quote(
        self,
        *,
        payload: MarketQuoteInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> MarketQuoteOut:
        market = get_realm_market(payload.realm_id)
        coin = get_realm_coin(payload.realm_id)
        quantity = max(0, payload.quantity)
        base = max(1, payload.base_price_cents)
        scarcity_multiplier_bp = 10000 + payload.scarcity_bp + market.volatility_bp
        spread_bp = max(0, payload.spread_bp + market.spread_bp)
        side_adjust_bp = spread_bp if payload.side.lower() == "buy" else -spread_bp
        effective_bp = max(1, scarcity_multiplier_bp + side_adjust_bp)
        unit_price = max(1, (base * effective_bp) // 10000)
        subtotal = unit_price * quantity
        stock_available = max(0, int(market.stock.get(payload.item_id, 0)))
        result = MarketQuoteOut(
            actor_id=payload.actor_id,
            realm_id=market.realm_id,
            market_id=market.market_id,
            currency_code=coin.currency_code,
            currency_name=coin.currency_name,
            currency_backing=coin.backing,
            item_id=payload.item_id,
            side=payload.side.lower(),
            quantity=quantity,
            stock_available=stock_available,
            market_volatility_bp=market.volatility_bp,
            unit_price_cents=unit_price,
            subtotal_cents=subtotal,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.market.quote {payload.actor_id} {payload.item_id} {payload.side}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "market_quote",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def market_trade(
        self,
        *,
        payload: MarketTradeInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> MarketTradeOut:
        market = get_realm_market(payload.realm_id)
        coin = get_realm_coin(payload.realm_id)
        side = payload.side.lower()
        requested_qty = max(0, payload.quantity)
        stock_available = max(0, int(market.stock.get(payload.item_id, 0)))
        liquidity = max(0, min(payload.available_liquidity, stock_available))
        filled_qty = min(requested_qty, liquidity)
        unit_price = max(1, payload.unit_price_cents)
        subtotal = filled_qty * unit_price
        fee_bp = max(0, payload.fee_bp + market.fee_bp)
        fee_cents = (subtotal * fee_bp) // 10000
        total_cents = subtotal + fee_cents

        wallet = payload.wallet_cents
        inventory = payload.inventory_qty
        status = "filled" if filled_qty == requested_qty else "partial"

        if side == "buy":
            affordable_qty = filled_qty
            if total_cents > wallet and unit_price > 0:
                per_unit_total = unit_price + ((unit_price * fee_bp) // 10000)
                if per_unit_total > 0:
                    affordable_qty = wallet // per_unit_total
            filled_qty = max(0, min(filled_qty, affordable_qty))
            subtotal = filled_qty * unit_price
            fee_cents = (subtotal * fee_bp) // 10000
            total_cents = subtotal + fee_cents
            wallet_after = wallet - total_cents
            inventory_after = inventory + filled_qty
            if filled_qty == 0:
                status = "rejected_insufficient_funds"
            elif filled_qty < requested_qty:
                status = "partial"
        else:
            sellable = max(0, inventory)
            filled_qty = max(0, min(filled_qty, sellable))
            subtotal = filled_qty * unit_price
            fee_cents = (subtotal * fee_bp) // 10000
            total_cents = subtotal - fee_cents
            wallet_after = wallet + total_cents
            inventory_after = inventory - filled_qty
            if filled_qty == 0:
                status = "rejected_insufficient_inventory"
            elif filled_qty < requested_qty:
                status = "partial"

        result = MarketTradeOut(
            actor_id=payload.actor_id,
            realm_id=market.realm_id,
            market_id=market.market_id,
            currency_code=coin.currency_code,
            currency_name=coin.currency_name,
            currency_backing=coin.backing,
            item_id=payload.item_id,
            side=side,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            stock_available=stock_available,
            market_volatility_bp=market.volatility_bp,
            unit_price_cents=unit_price,
            subtotal_cents=subtotal,
            fee_cents=fee_cents,
            total_cents=total_cents,
            wallet_after_cents=wallet_after,
            inventory_after_qty=inventory_after,
            status=status,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.market.trade {payload.actor_id} {payload.item_id} {side}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "market_trade",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def list_realm_coins(self, realm_id: str | None = None) -> Sequence[RealmCoinOut]:
        return [
            RealmCoinOut(
                realm_id=item.realm_id,
                currency_code=item.currency_code,
                currency_name=item.currency_name,
                backing=item.backing,
            )
            for item in list_realm_coins(realm_id)
        ]

    def list_realm_markets(self, realm_id: str | None = None) -> Sequence[RealmMarketOut]:
        return [
            RealmMarketOut(
                realm_id=item.realm_id,
                market_id=item.market_id,
                display_name=item.display_name,
                dominant_operator=item.dominant_operator,
                market_network=item.market_network,
                dominance_bp=item.dominance_bp,
                volatility_bp=item.volatility_bp,
                spread_bp=item.spread_bp,
                fee_bp=item.fee_bp,
                stock={key: int(value) for key, value in item.stock.items()},
            )
            for item in list_realm_markets(realm_id)
        ]

    def evaluate_radio_availability(
        self,
        *,
        payload: RadioEvaluateInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> RadioEvaluateOut:
        state = str(payload.underworld_state or "").strip().lower()
        override = payload.override_available
        if override is not None:
            available = bool(override)
            reason = "override"
        else:
            if state in {"open", "active", "unstable", "awakened"}:
                available = True
                reason = "state_allows_radio"
            elif state in {"sealed", "silent", "collapsed", "dormant", "closed"}:
                available = False
                reason = "state_blocks_radio"
            else:
                available = False
                reason = "unknown_state"
        flags = {
            "radio_available": available,
            "underworld_state": state,
        }
        result = RadioEvaluateOut(
            actor_id=payload.actor_id,
            underworld_state=state,
            available=available,
            reason=reason,
            flags=flags,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.radio.evaluate {payload.actor_id} {state}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "radio_evaluate",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def unlock_infernal_meditation(
        self,
        *,
        payload: InfernalMeditationUnlockInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> InfernalMeditationUnlockOut:
        mentor = str(payload.mentor or "").strip().lower()
        location = str(payload.location or "").strip().lower()
        section = str(payload.section or "").strip().lower()
        time_of_day = str(payload.time_of_day or "").strip().lower()
        ok = (
            mentor == "alfir"
            and location == "castle azoth library"
            and section == "restricted"
            and time_of_day == "night"
        )
        reason = "ok" if ok else "conditions_not_met"
        flags = {
            "infernal_meditation": ok,
            "infernal_meditation_mentor": mentor,
            "infernal_meditation_location": location,
            "infernal_meditation_section": section,
            "infernal_meditation_time": time_of_day,
        }
        result = InfernalMeditationUnlockOut(actor_id=payload.actor_id, unlocked=ok, reason=reason, flags=flags)
        if emit_kernel:
            self._kernel.place(
                raw=f"game.infernal_meditation.unlock {payload.actor_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "infernal_meditation_unlock",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _gate_expected_value(requirement: GateRequirement) -> int | str | bool | None:
        if requirement.int_value is not None:
            return int(requirement.int_value)
        if requirement.str_value is not None:
            return requirement.str_value
        if requirement.bool_value is not None:
            return bool(requirement.bool_value)
        return None

    @staticmethod
    def _gate_actual_value(payload: GateEvaluateInput, requirement: GateRequirement) -> int | str | bool | None:
        source = requirement.source
        key = requirement.key
        if source == "skills":
            return int(payload.state.skills.get(key, 0))
        if source == "inventory":
            return int(payload.state.inventory.get(key, 0))
        if source == "vitriol":
            return int(payload.state.vitriol.get(key, 0))
        if source == "flags":
            return bool(payload.state.flags.get(key, False))
        if source == "dialogue_flags":
            return key in payload.state.dialogue_flags
        return key in payload.state.previous_dialogue

    @classmethod
    def _evaluate_gate_requirement(cls, payload: GateEvaluateInput, requirement: GateRequirement) -> GateRequirementResult:
        actual = cls._gate_actual_value(payload, requirement)
        expected = cls._gate_expected_value(requirement)
        matched = False
        reason = "not_matched"
        if requirement.comparator == "gte":
            if not isinstance(actual, int):
                reason = "invalid_actual_type_for_gte"
            elif requirement.int_value is None:
                reason = "missing_int_value"
            else:
                matched = actual >= requirement.int_value
                reason = "ok" if matched else "below_threshold"
        elif requirement.comparator == "eq":
            if expected is None:
                reason = "missing_expected_value"
            else:
                matched = actual == expected
                reason = "ok" if matched else "not_equal"
        else:
            expected_present = requirement.bool_value if requirement.bool_value is not None else True
            actual_present = bool(actual)
            matched = actual_present == expected_present
            expected = expected_present
            actual = actual_present
            reason = "ok" if matched else "presence_mismatch"
        return GateRequirementResult(
            source=requirement.source,
            key=requirement.key,
            comparator=requirement.comparator,
            matched=matched,
            actual=actual,
            expected=expected,
            reason=reason,
        )

    @staticmethod
    def _combine_gate_results(operator: GateOperator, result_flags: Sequence[bool]) -> bool:
        if operator == "and":
            return all(result_flags)
        if operator == "or":
            return any(result_flags)
        if operator == "xor":
            return sum(1 for value in result_flags if value) == 1
        return not any(result_flags)

    def evaluate_gate(
        self,
        *,
        payload: GateEvaluateInput,
        actor_id: str,
        workshop_id: str,
    ) -> GateEvaluateOut:
        requirement_results = [self._evaluate_gate_requirement(payload, requirement) for requirement in payload.requirements]
        result_flags = [item.matched for item in requirement_results]
        allowed = self._combine_gate_results(payload.operator, result_flags)
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "gate_id": payload.gate_id,
            "operator": payload.operator,
            "state": payload.state.model_dump(),
            "requirements": [item.model_dump() for item in payload.requirements],
            "results": [item.model_dump() for item in requirement_results],
            "allowed": allowed,
        }
        result = GateEvaluateOut(
            actor_id=payload.actor_id,
            gate_id=payload.gate_id,
            operator=payload.operator,
            allowed=allowed,
            matched_count=sum(1 for value in result_flags if value),
            total_count=len(result_flags),
            results=requirement_results,
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.gate.evaluate {payload.actor_id} {payload.gate_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "gate_evaluate",
                "result": result.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return result

    @classmethod
    def _gate_state_from_tables(cls, tables: PlayerStateTables) -> GateStateInput:
        skills_obj = cls._dict_from_table(tables.skills.get("ranks"))
        if not skills_obj:
            skills_obj = cls._dict_from_table(tables.skills)
        skills: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in skills_obj.items()
        }

        inventory_obj = cls._dict_from_table(tables.inventory.get("items"))
        if not inventory_obj:
            inventory_obj = cls._dict_from_table(tables.inventory)
        inventory: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in inventory_obj.items()
        }

        vitriol_obj = cls._dict_from_table(tables.vitriol.get("effective"))
        if not vitriol_obj:
            vitriol_obj = cls._dict_from_table(tables.vitriol.get("base"))
        vitriol: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in vitriol_obj.items()
        }

        flags_obj = cls._dict_from_table(tables.flags)
        dialogue_flags = cls._list_from_table(flags_obj.get("dialogue_flags"))
        previous_dialogue = cls._list_from_table(flags_obj.get("previous_dialogue"))
        bool_flags: dict[str, bool] = {
            key: bool(value)
            for key, value in flags_obj.items()
            if isinstance(key, str) and isinstance(value, bool)
        }

        return GateStateInput(
            skills=skills,
            inventory=inventory,
            vitriol=vitriol,
            dialogue_flags=dialogue_flags,
            previous_dialogue=previous_dialogue,
            flags=bool_flags,
        )

    def resolve_dialogue_branch(
        self,
        *,
        payload: DialogueResolveInput,
        actor_id: str,
        workshop_id: str,
    ) -> DialogueResolveOut:
        state_source: str
        if payload.state is not None:
            state = payload.state
            state_source = "payload"
        else:
            tables = self.get_player_state(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
            ).tables
            state = self._gate_state_from_tables(tables)
            state_source = "player_state"

        evaluations: list[DialogueChoiceResolveOut] = []
        for choice in sorted(payload.choices, key=lambda item: (item.priority, item.choice_id)):
            gate_payload = GateEvaluateInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                gate_id=f"{payload.dialogue_id}:{payload.node_id}:{choice.choice_id}",
                operator="and",
                state=state,
                requirements=choice.requirements,
            )
            results = [self._evaluate_gate_requirement(gate_payload, requirement) for requirement in choice.requirements]
            matched_count = sum(1 for item in results if item.matched)
            eligible = all(item.matched for item in results)
            evaluations.append(
                DialogueChoiceResolveOut(
                    choice_id=choice.choice_id,
                    text=choice.text,
                    next_node_id=choice.next_node_id,
                    priority=choice.priority,
                    eligible=eligible,
                    matched_count=matched_count,
                    total_count=len(results),
                    results=results,
                )
            )

        eligible_choices = [item for item in evaluations if item.eligible]
        selected = eligible_choices[0] if eligible_choices else None
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "dialogue_id": payload.dialogue_id,
            "node_id": payload.node_id,
            "state_source": state_source,
            "state": state.model_dump(),
            "evaluations": [item.model_dump() for item in evaluations],
            "selected_choice_id": selected.choice_id if selected else None,
            "selected_next_node_id": selected.next_node_id if selected else None,
        }
        out = DialogueResolveOut(
            dialogue_id=payload.dialogue_id,
            node_id=payload.node_id,
            state_source="payload" if state_source == "payload" else "player_state",
            eligible_choice_ids=[item.choice_id for item in eligible_choices],
            selected_choice_id=selected.choice_id if selected else None,
            selected_next_node_id=selected.next_node_id if selected else None,
            evaluations=evaluations,
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.dialogue.resolve {payload.actor_id} {payload.dialogue_id} {payload.node_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "dialogue_branch_resolve",
                "result": out.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return out

    def transition_quest_state(
        self,
        *,
        payload: QuestTransitionInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestTransitionOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        flags = dict(tables.flags)

        quest_states_obj = self._dict_from_table(flags.get("quest_states"))
        quest_states: dict[str, object] = dict(quest_states_obj)
        existing_entry = self._dict_from_table(quest_states.get(payload.quest_id))
        previous_state = str(existing_entry.get("state") or "inactive")

        allowed_from = {item.strip() for item in payload.from_states if item.strip() != ""}
        next_state = payload.to_state.strip() or previous_state
        if payload.event_id.strip() == "":
            transitioned = False
            reason = "event_id_required"
            next_state = previous_state
        elif allowed_from and previous_state not in allowed_from:
            transitioned = False
            reason = "invalid_from_state"
            next_state = previous_state
        elif previous_state == next_state:
            transitioned = False
            reason = "no_state_change"
        else:
            transitioned = True
            reason = "ok"

        if transitioned:
            tick = self._int_from_table(self._dict_from_table(tables.clock).get("tick"), 0)
            quest_states[payload.quest_id] = {
                "state": next_state,
                "last_event_id": payload.event_id,
                "updated_tick": tick,
                "metadata": dict(payload.metadata),
            }
            history = self._list_of_dicts(flags.get("quest_history"))
            history.append(
                {
                    "quest_id": payload.quest_id,
                    "event_id": payload.event_id,
                    "from_state": previous_state,
                    "to_state": next_state,
                    "tick": tick,
                }
            )
            flags["quest_history"] = history
            for key, value in payload.set_flags.items():
                flags[key] = bool(value)
            flags["quest_states"] = quest_states
            tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
            row.state_version = max(1, int(row.state_version) + 1)
            row.levels_json = self._canonical_json(tables.levels)
            row.skills_json = self._canonical_json(tables.skills)
            row.perks_json = self._canonical_json(tables.perks)
            row.vitriol_json = self._canonical_json(tables.vitriol)
            row.inventory_json = self._canonical_json(tables.inventory)
            row.market_json = self._canonical_json(tables.market)
            row.flags_json = self._canonical_json(tables.flags)
            row.clock_json = self._canonical_json(tables.clock)
            row.updated_at = datetime.now(timezone.utc)
            repo.save_player_state(row)

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "quest_id": payload.quest_id,
            "event_id": payload.event_id,
            "previous_state": previous_state,
            "next_state": next_state,
            "transitioned": transitioned,
            "reason": reason,
            "state_version": int(row.state_version),
        }
        out = QuestTransitionOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            quest_id=payload.quest_id,
            event_id=payload.event_id,
            previous_state=previous_state,
            next_state=next_state,
            transitioned=transitioned,
            reason=reason,
            state_version=int(row.state_version),
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.quest.transition {payload.actor_id} {payload.quest_id} {payload.event_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "quest_transition",
                "result": out.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return out

    def advance_quest_step(
        self,
        *,
        payload: QuestAdvanceInput,
        actor_id: str,
        workshop_id: str,
        persist: bool = True,
        emit_kernel: bool = True,
    ) -> QuestAdvanceOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        flags = dict(tables.flags)

        quest_states_obj = self._dict_from_table(flags.get("quest_states"))
        quest_states: dict[str, object] = dict(quest_states_obj)
        existing_entry = self._dict_from_table(quest_states.get(payload.quest_id))
        previous_step_id = str(existing_entry.get("step_id") or payload.current_step_id).strip()
        if previous_step_id == "":
            previous_step_id = payload.current_step_id.strip()

        if payload.state is not None:
            state = payload.state
            state_source: str = "payload"
        else:
            state = self._gate_state_from_tables(tables)
            state_source = "player_state"

        evaluations: list[QuestStepEdgeResolveOut] = []
        for edge in sorted(payload.edges, key=lambda item: (item.priority, item.edge_id, item.to_step_id)):
            gate_payload = GateEvaluateInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                gate_id=f"{payload.quest_id}:{previous_step_id}:{edge.edge_id}",
                operator="and",
                state=state,
                requirements=edge.requirements,
            )
            results = [self._evaluate_gate_requirement(gate_payload, requirement) for requirement in edge.requirements]
            matched_count = sum(1 for item in results if item.matched)
            eligible = all(item.matched for item in results)
            evaluations.append(
                QuestStepEdgeResolveOut(
                    edge_id=edge.edge_id,
                    to_step_id=edge.to_step_id,
                    priority=edge.priority,
                    eligible=eligible,
                    matched_count=matched_count,
                    total_count=len(results),
                    results=results,
                )
            )

        eligible_edges = [item for item in evaluations if item.eligible]
        selected = eligible_edges[0] if eligible_edges else None
        next_step_id = selected.to_step_id if selected is not None else previous_step_id

        if payload.event_id.strip() == "":
            advanced = False
            reason = "event_id_required"
            selected = None
            next_step_id = previous_step_id
        elif selected is None:
            advanced = False
            reason = "no_eligible_edge"
        elif next_step_id == previous_step_id:
            advanced = False
            reason = "no_step_change"
        else:
            advanced = True
            reason = "ok"

        if advanced and persist:
            tick = self._int_from_table(self._dict_from_table(tables.clock).get("tick"), 0)
            quest_states[payload.quest_id] = {
                "state": str(existing_entry.get("state") or "active"),
                "step_id": next_step_id,
                "last_event_id": payload.event_id,
                "last_edge_id": selected.edge_id if selected is not None else "",
                "updated_tick": tick,
            }
            history = self._list_of_dicts(flags.get("quest_history"))
            history.append(
                {
                    "quest_id": payload.quest_id,
                    "event_id": payload.event_id,
                    "from_step_id": previous_step_id,
                    "to_step_id": next_step_id,
                    "edge_id": selected.edge_id if selected is not None else "",
                    "tick": tick,
                }
            )
            flags["quest_history"] = history
            for edge in payload.edges:
                if selected is not None and edge.edge_id == selected.edge_id:
                    for key, value in edge.set_flags.items():
                        flags[key] = bool(value)
                    break
            flags["quest_states"] = quest_states
            tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
            row.state_version = max(1, int(row.state_version) + 1)
            row.levels_json = self._canonical_json(tables.levels)
            row.skills_json = self._canonical_json(tables.skills)
            row.perks_json = self._canonical_json(tables.perks)
            row.vitriol_json = self._canonical_json(tables.vitriol)
            row.inventory_json = self._canonical_json(tables.inventory)
            row.market_json = self._canonical_json(tables.market)
            row.flags_json = self._canonical_json(tables.flags)
            row.clock_json = self._canonical_json(tables.clock)
            row.updated_at = datetime.now(timezone.utc)
            repo.save_player_state(row)

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "quest_id": payload.quest_id,
            "event_id": payload.event_id,
            "previous_step_id": previous_step_id,
            "next_step_id": next_step_id,
            "advanced": advanced,
            "reason": reason,
            "state_source": state_source,
            "state_version": int(row.state_version),
            "persist": persist,
            "state": state.model_dump(),
            "evaluations": [item.model_dump() for item in evaluations],
            "selected_edge_id": selected.edge_id if selected is not None else None,
        }
        out = QuestAdvanceOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            quest_id=payload.quest_id,
            event_id=payload.event_id,
            previous_step_id=previous_step_id,
            next_step_id=next_step_id,
            advanced=advanced,
            reason=reason,
            state_source="payload" if state_source == "payload" else "player_state",
            state_version=int(row.state_version),
            eligible_edge_ids=[item.edge_id for item in eligible_edges],
            selected_edge_id=selected.edge_id if selected is not None else None,
            evaluations=evaluations,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.quest.advance {payload.actor_id} {payload.quest_id} {payload.event_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "quest_advance",
                    "result": out.model_dump(),
                    "persisted": persist,
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return out

    @staticmethod
    def _quest_graph_manifest_id(quest_id: str, version: str) -> str:
        return f"quest_graph:{quest_id.strip()}:{version.strip()}"

    @staticmethod
    def _canonical_quest_graph_steps(steps: Sequence[QuestGraphStepInput]) -> list[QuestGraphStepInput]:
        normalized_steps: list[QuestGraphStepInput] = []
        for step in sorted(steps, key=lambda item: item.step_id):
            normalized_edges = sorted(
                step.edges,
                key=lambda item: (item.priority, item.edge_id, item.to_step_id),
            )
            normalized_steps.append(
                QuestGraphStepInput(
                    step_id=step.step_id,
                    edges=normalized_edges,
                    metadata=dict(step.metadata),
                )
            )
        return normalized_steps

    @classmethod
    def _quest_graph_from_manifest(cls, row: AssetManifestOut) -> QuestGraphOut:
        payload_obj = row.payload if isinstance(row.payload, dict) else {}
        metadata = cls._dict_from_table(payload_obj.get("metadata"))
        runtime_schema_version = str(metadata.get("runtime_schema_version") or cls._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = cls._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        steps_raw = payload_obj.get("steps")
        step_items = steps_raw if isinstance(steps_raw, list) else []
        steps: list[QuestGraphStepInput] = []
        for item in step_items:
            if isinstance(item, dict):
                steps.append(QuestGraphStepInput.model_validate(item))
        return QuestGraphOut(
            workspace_id=row.workspace_id,
            quest_id=str(payload_obj.get("quest_id") or ""),
            version=str(payload_obj.get("version") or ""),
            start_step_id=str(payload_obj.get("start_step_id") or ""),
            headless=bool(payload_obj.get("headless", True)),
            runtime_schema_version=runtime_schema_version,
            steps=cls._canonical_quest_graph_steps(steps),
            metadata=metadata,
            manifest_id=row.manifest_id,
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def validate_quest_graph(self, payload: QuestGraphUpsertInput) -> QuestGraphValidateOut:
        errors: list[str] = []
        warnings: list[str] = []
        if not payload.headless:
            errors.append("quests_must_be_headless")
        quest_id = payload.quest_id.strip()
        version = payload.version.strip()
        start_step_id = payload.start_step_id.strip()
        if quest_id == "":
            errors.append("quest_id_required")
        if version == "":
            errors.append("version_required")
        if start_step_id == "":
            errors.append("start_step_id_required")

        steps = self._canonical_quest_graph_steps(payload.steps)
        if not steps:
            errors.append("steps_required")

        step_ids: list[str] = []
        seen_steps: set[str] = set()
        total_edges = 0
        for step in steps:
            sid = step.step_id.strip()
            if sid == "":
                errors.append("empty_step_id")
                continue
            step_ids.append(sid)
            if sid in seen_steps:
                errors.append(f"duplicate_step_id:{sid}")
            seen_steps.add(sid)

        step_set = set(step_ids)
        if start_step_id != "" and start_step_id not in step_set:
            errors.append(f"start_step_missing:{start_step_id}")

        for step in steps:
            seen_edges: set[str] = set()
            for edge in step.edges:
                total_edges += 1
                edge_id = edge.edge_id.strip()
                to_step_id = edge.to_step_id.strip()
                if edge_id == "":
                    errors.append(f"empty_edge_id:{step.step_id}")
                elif edge_id in seen_edges:
                    errors.append(f"duplicate_edge_id:{step.step_id}:{edge_id}")
                else:
                    seen_edges.add(edge_id)
                if to_step_id == "":
                    errors.append(f"empty_edge_target:{step.step_id}:{edge_id or 'unknown'}")
                elif to_step_id not in step_set:
                    errors.append(f"invalid_edge_target:{step.step_id}:{edge_id or 'unknown'}->{to_step_id}")
                if edge.priority < 0:
                    warnings.append(f"negative_priority:{step.step_id}:{edge_id or 'unknown'}")

        metadata = dict(payload.metadata)
        runtime_schema_version = str(metadata.get("runtime_schema_version") or self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        if runtime_schema_version != self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION:
            warnings.append(
                f"incompatible_runtime_schema_version:{runtime_schema_version}:supported:{self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION}"
            )
        metadata["runtime_schema_version"] = runtime_schema_version

        graph_payload: dict[str, object] = {
            "quest_id": quest_id,
            "version": version,
            "start_step_id": start_step_id,
            "headless": True,
            "steps": [item.model_dump() for item in steps],
            "metadata": metadata,
        }
        return QuestGraphValidateOut(
            ok=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats={"step_count": len(step_ids), "edge_count": total_edges},
            graph_hash=self._canonical_hash(graph_payload),
        )

    def upsert_quest_graph(self, payload: QuestGraphUpsertInput) -> QuestGraphOut:
        validation = self.validate_quest_graph(payload)
        if not validation.ok:
            raise ValueError(f"quest_graph_invalid:{';'.join(validation.errors)}")
        quest_id = payload.quest_id.strip()
        version = payload.version.strip()
        if quest_id == "":
            raise ValueError("quest_id_required")
        if version == "":
            raise ValueError("version_required")
        manifest_id = self._quest_graph_manifest_id(quest_id, version)

        manifests = self.list_asset_manifests(payload.workspace_id)
        existing = next(
            (
                row
                for row in manifests
                if row.kind.strip().lower() == "quest.graph.v1" and row.manifest_id == manifest_id
            ),
            None,
        )
        if existing is not None:
            out = self._quest_graph_from_manifest(existing)
            if not out.headless:
                raise ValueError("quests_must_be_headless")
            return out

        steps = self._canonical_quest_graph_steps(payload.steps)
        metadata = dict(payload.metadata)
        runtime_schema_version = str(metadata.get("runtime_schema_version") or self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        metadata["runtime_schema_version"] = runtime_schema_version
        payload_obj: dict[str, object] = {
            "quest_id": quest_id,
            "version": version,
            "start_step_id": payload.start_step_id.strip(),
            "headless": True,
            "steps": [item.model_dump() for item in steps],
            "metadata": metadata,
        }
        saved = self.create_asset_manifest(
            AssetManifestCreate(
                workspace_id=payload.workspace_id,
                realm_id="lapidus",
                manifest_id=manifest_id,
                name=f"Quest Graph {quest_id} v{version}",
                kind="quest.graph.v1",
                payload=payload_obj,
            )
        )
        return self._quest_graph_from_manifest(saved)

    def get_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
        version: str | None = None,
        enforce_runtime_compat: bool = True,
    ) -> QuestGraphOut:
        quest_key = quest_id.strip()
        if quest_key == "":
            raise ValueError("quest_id_required")
        version_filter = (version or "").strip()

        manifests = self.list_asset_manifests(workspace_id)
        candidates: list[QuestGraphOut] = []
        for row in manifests:
            if row.kind.strip().lower() != "quest.graph.v1":
                continue
            parsed = self._quest_graph_from_manifest(row)
            if parsed.quest_id != quest_key:
                continue
            if version_filter != "" and parsed.version != version_filter:
                continue
            if not parsed.headless:
                continue
            candidates.append(parsed)
        if not candidates:
            raise ValueError("quest_graph_not_found")
        candidates.sort(key=lambda item: (item.created_at, item.version, item.manifest_id), reverse=True)
        selected = candidates[0]
        if enforce_runtime_compat and selected.runtime_schema_version != self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION:
            raise ValueError(
                "quest_graph_incompatible_runtime_schema:"
                f"{selected.runtime_schema_version}:supported:{self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION}"
            )
        return selected

    def get_latest_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
    ) -> QuestGraphOut:
        return self.get_quest_graph(
            workspace_id=workspace_id,
            quest_id=quest_id,
            version=None,
        )

    def hash_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
        version: str | None = None,
    ) -> QuestGraphHashOut:
        graph = self.get_quest_graph(
            workspace_id=workspace_id,
            quest_id=quest_id,
            version=version,
            enforce_runtime_compat=False,
        )
        graph_payload: dict[str, object] = {
            "quest_id": graph.quest_id,
            "version": graph.version,
            "start_step_id": graph.start_step_id,
            "headless": graph.headless,
            "steps": [item.model_dump() for item in graph.steps],
            "metadata": graph.metadata,
        }
        return QuestGraphHashOut(
            workspace_id=graph.workspace_id,
            quest_id=graph.quest_id,
            version=graph.version,
            manifest_id=graph.manifest_id,
            graph_hash=self._canonical_hash(graph_payload),
        )

    def list_quest_graphs(
        self,
        *,
        workspace_id: str,
        quest_id: str | None = None,
        version: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> QuestGraphListOut:
        quest_filter = (quest_id or "").strip()
        version_filter = (version or "").strip()
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))

        manifests = self.list_asset_manifests(workspace_id)
        items: list[QuestGraphOut] = []
        for row in manifests:
            if row.kind.strip().lower() != "quest.graph.v1":
                continue
            parsed = self._quest_graph_from_manifest(row)
            if not parsed.headless:
                continue
            if quest_filter != "" and parsed.quest_id != quest_filter:
                continue
            if version_filter != "" and parsed.version != version_filter:
                continue
            items.append(parsed)
        items.sort(key=lambda item: (item.created_at, item.quest_id, item.version, item.manifest_id), reverse=True)
        total = len(items)
        paged = items[page_offset : page_offset + page_limit]
        return QuestGraphListOut(
            total=total,
            limit=page_limit,
            offset=page_offset,
            items=paged,
        )

    def advance_quest_step_by_graph(
        self,
        *,
        payload: QuestAdvanceByGraphInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestAdvanceByGraphOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        graph = self.get_quest_graph(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            version=payload.version,
        )
        step_id = payload.current_step_id.strip()
        if step_id == "":
            step_id = graph.start_step_id
        step = next((item for item in graph.steps if item.step_id == step_id), None)
        if step is None:
            raise ValueError("quest_step_not_found")
        advance = self.advance_quest_step(
            payload=QuestAdvanceInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                quest_id=payload.quest_id,
                event_id=payload.event_id,
                current_step_id=step_id,
                headless=True,
                state=payload.state,
                edges=step.edges,
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return QuestAdvanceByGraphOut(graph=graph, advance=advance)

    def advance_quest_step_by_graph_dry_run(
        self,
        *,
        payload: QuestAdvanceByGraphInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestAdvanceByGraphDryRunOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        graph = self.get_quest_graph(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            version=payload.version,
        )
        step_id = payload.current_step_id.strip()
        if step_id == "":
            step_id = graph.start_step_id
        step = next((item for item in graph.steps if item.step_id == step_id), None)
        if step is None:
            raise ValueError("quest_step_not_found")
        advance = self.advance_quest_step(
            payload=QuestAdvanceInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                quest_id=payload.quest_id,
                event_id=payload.event_id,
                current_step_id=step_id,
                headless=True,
                state=payload.state,
                edges=step.edges,
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
            persist=False,
            emit_kernel=False,
        )
        return QuestAdvanceByGraphDryRunOut(graph=graph, advance=advance, persisted=False)

    def emit_dialogue(
        self,
        *,
        payload: DialogueEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> DialogueEmitOut:
        sorted_turns = sorted(payload.turns, key=lambda turn: turn.line_id)
        emitted_line_ids: list[str] = []
        for turn in sorted_turns:
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "scene_id": payload.scene_id,
                "dialogue_id": payload.dialogue_id,
                "line_id": turn.line_id,
                "speaker_id": turn.speaker_id,
            }
            if turn.tags:
                context["tags"] = dict(turn.tags)
            if turn.metadata:
                context["metadata"] = dict(turn.metadata)
            self._kernel.place(
                raw=turn.raw,
                context=context,
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
            emitted_line_ids.append(turn.line_id)
        return DialogueEmitOut(
            dialogue_id=payload.dialogue_id,
            scene_id=payload.scene_id,
            emitted=len(emitted_line_ids),
            emitted_line_ids=emitted_line_ids,
        )

    @classmethod
    def _normalize_vitriol_base(cls, raw: Mapping[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for axis in cls._VITRIOL_AXES:
            base_value = int(raw.get(axis, 1))
            normalized[axis] = max(1, min(10, base_value))
        return normalized

    @classmethod
    def _is_modifier_active(cls, modifier: VitriolModifier, current_tick: int) -> bool:
        if modifier.duration_turns <= 0:
            return True
        end_tick = modifier.applied_tick + modifier.duration_turns
        return current_tick < end_tick

    @classmethod
    def _compute_vitriol(
        cls,
        *,
        base: Mapping[str, int],
        modifiers: Sequence[VitriolModifier],
        current_tick: int,
    ) -> tuple[dict[str, int], list[VitriolModifier]]:
        effective = cls._normalize_vitriol_base(base)
        active: list[VitriolModifier] = []
        for modifier in modifiers:
            if not cls._is_modifier_active(modifier, current_tick):
                continue
            active.append(modifier)
            for axis, delta in modifier.delta.items():
                if axis not in effective:
                    continue
                next_value = effective[axis] + int(delta)
                effective[axis] = max(1, min(10, next_value))
        return effective, active

    @classmethod
    def _validate_ruler_delta(cls, ruler_id: str, delta: Mapping[str, int]) -> None:
        normalized_ruler = ruler_id.strip().lower()
        if normalized_ruler not in cls._VITRIOL_RULER_AXIS:
            raise ValueError("invalid_ruler")
        governed_axis = cls._VITRIOL_RULER_AXIS[normalized_ruler]
        invalid_axes = [axis for axis in delta.keys() if axis != governed_axis]
        if invalid_axes:
            raise ValueError("ruler_axis_violation")

    def vitriol_compute(self, *, payload: VitriolComputeInput) -> VitriolComputeOut:
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=payload.modifiers,
            current_tick=payload.current_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "current_tick": payload.current_tick,
        }
        return VitriolComputeOut(
            actor_id=payload.actor_id,
            effective=effective,
            active_modifiers=active_modifiers,
            hash=self._canonical_hash(hash_payload),
        )

    def vitriol_apply_ruler_influence(
        self,
        *,
        payload: VitriolApplyRulerInfluenceInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> VitriolApplyOut:
        self._validate_ruler_delta(payload.ruler_id, payload.delta)
        modifier = VitriolModifier(
            source_ruler=payload.ruler_id.strip().lower(),
            delta={axis: int(value) for axis, value in payload.delta.items()},
            reason=payload.reason,
            event_id=payload.event_id,
            applied_tick=payload.applied_tick,
            duration_turns=payload.duration_turns,
        )
        next_modifiers = [*payload.modifiers, modifier]
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=next_modifiers,
            current_tick=payload.applied_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "tick": payload.applied_tick,
        }
        result = VitriolApplyOut(
            actor_id=payload.actor_id,
            applied=True,
            modifier=modifier,
            effective=effective,
            active_modifiers=active_modifiers,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.vitriol.apply {payload.actor_id} {modifier.source_ruler}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "vitriol_apply_ruler_influence",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def vitriol_clear_expired(
        self,
        *,
        payload: VitriolClearExpiredInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> VitriolClearExpiredOut:
        kept: list[VitriolModifier] = [
            modifier for modifier in payload.modifiers if self._is_modifier_active(modifier, payload.current_tick)
        ]
        removed_count = len(payload.modifiers) - len(kept)
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=kept,
            current_tick=payload.current_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "current_tick": payload.current_tick,
        }
        result = VitriolClearExpiredOut(
            actor_id=payload.actor_id,
            removed_count=removed_count,
            active_modifiers=active_modifiers,
            effective=effective,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.vitriol.clear_expired {payload.actor_id} removed={removed_count}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "vitriol_clear_expired",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _normalize_frontier_ids(values: Sequence[str]) -> list[str]:
        normalized = sorted({value.strip() for value in values if value.strip() != ""})
        return normalized

    @staticmethod
    def _safe_token(value: str) -> str:
        return "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in value)

    @staticmethod
    def _dict_result(value: object) -> dict[str, object]:
        if hasattr(value, "model_dump"):
            dumped = cast(Any, value).model_dump()
            if isinstance(dumped, dict):
                return cast(dict[str, object], dumped)
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        if isinstance(value, list):
            return {"items": cast(list[object], value)}
        return {"value": cast(object, value)}

    def runtime_action_catalog(self) -> RuntimeActionCatalogOut:
        actions: list[RuntimeActionCatalogItemOut] = [
            RuntimeActionCatalogItemOut(
                kind="levels.apply",
                summary="Apply deterministic level progression.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "xp_delta": "int"},
                example_payload={"xp_delta": 25},
            ),
            RuntimeActionCatalogItemOut(
                kind="skills.train",
                summary="Train a named skill by deterministic delta.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "skill_id": "str", "delta": "int"},
                example_payload={"skill_id": "alchemy", "delta": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="perks.unlock",
                summary="Unlock a perk when requirements are met.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "perk_id": "str"},
                example_payload={"perk_id": "steady_hands"},
            ),
            RuntimeActionCatalogItemOut(
                kind="alchemy.craft",
                summary="Resolve alchemy craft transaction.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "recipe_id": "str"},
                example_payload={"recipe_id": "minor_heal"},
            ),
            RuntimeActionCatalogItemOut(
                kind="blacksmith.forge",
                summary="Resolve blacksmith forging transaction.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "recipe_id": "str"},
                example_payload={"recipe_id": "iron_blade"},
            ),
            RuntimeActionCatalogItemOut(
                kind="combat.resolve",
                summary="Resolve deterministic combat exchange.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "enemy_id": "str"},
                example_payload={"enemy_id": "arena_bandit"},
            ),
            RuntimeActionCatalogItemOut(
                kind="market.quote",
                summary="Compute market quote for side/quantity.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "realm_id": "str", "item_id": "str"},
                example_payload={"realm_id": "lapidus", "item_id": "iron_ingot", "side": "buy", "quantity": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="market.trade",
                summary="Execute market trade with liquidity limits.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "realm_id": "str", "item_id": "str"},
                example_payload={"realm_id": "lapidus", "item_id": "iron_ingot", "side": "buy", "quantity": 2},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.apply",
                summary="Apply ruler modifier to VITRIOL state.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "ruler_id": "str"},
                example_payload={"ruler_id": "asmodeus", "delta": {"vitality": 1}, "applied_tick": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.compute",
                summary="Compute effective VITRIOL values from base+modifiers.",
                payload_fields={"base": "dict", "modifiers": "list", "current_tick": "int"},
                example_payload={"base": {"vitality": 7}, "modifiers": [], "current_tick": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.clear",
                summary="Clear expired VITRIOL modifiers by tick.",
                payload_fields={"base": "dict", "modifiers": "list", "current_tick": "int"},
                example_payload={"base": {"vitality": 7}, "modifiers": [], "current_tick": 50},
            ),
            RuntimeActionCatalogItemOut(
                kind="djinn.apply",
                summary="Apply Djinn frontier influence and marks.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "djinn_id": "str", "realm_id": "str"},
                example_payload={"djinn_id": "giann", "realm_id": "lapidus", "scene_id": "lapidus/intro"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.load",
                summary="Load one world region into stream state.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "realm_id": "str", "region_key": "str", "payload": "dict"},
                example_payload={"realm_id": "lapidus", "region_key": "lapidus/chunk_0_0", "cache_policy": "stream"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.preload.scenegraph",
                summary="Chunk scenegraph nodes and preload derived regions.",
                requires_realm=True,
                payload_fields={
                    "realm_id": "str",
                    "scene_id": "str",
                    "scene_content": "dict",
                    "chunk_size": "int",
                    "cache_policy": "str",
                },
                example_payload={
                    "realm_id": "lapidus",
                    "scene_id": "lapidus/player_home",
                    "chunk_size": 12,
                    "cache_policy": "stream",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.unload",
                summary="Unload one region from stream state.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "realm_id": "str", "region_key": "str"},
                example_payload={"realm_id": "lapidus", "region_key": "lapidus/chunk_0_0"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.stream.status",
                summary="Inspect stream occupancy/capacity and policy counts.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "realm_id": "str"},
                example_payload={"realm_id": "lapidus"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.coins.list",
                summary="List realm currencies.",
                requires_realm=False,
                payload_fields={"realm_id": "str(optional)"},
                example_payload={},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.markets.list",
                summary="List realm market profiles/stocks.",
                requires_realm=False,
                payload_fields={"realm_id": "str(optional)"},
                example_payload={"realm_id": "lapidus"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.market.stock.adjust",
                summary="Override market stock during runtime plan.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "item_id": "str", "delta": "int|optional", "set_qty": "int|optional"},
                example_payload={"realm_id": "lapidus", "item_id": "iron_ingot", "set_qty": 10},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.market.sovereignty.transition",
                summary="Apply market control transition + redistribution policy.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "overthrow": "bool", "victor_id": "str"},
                example_payload={"realm_id": "lapidus", "overthrow": True, "victor_id": "player_commonwealth"},
            ),
        ]
        return RuntimeActionCatalogOut(action_count=len(actions), actions=actions)

    def consume_runtime_plan(
        self,
        *,
        payload: RuntimeConsumeInput,
        actor_id: str,
        workshop_id: str,
    ) -> RuntimeConsumeOut:
        results: list[RuntimeActionOut] = []
        runtime_regions: dict[str, dict[str, object]] = {}
        runtime_market_stock: dict[str, dict[str, int]] = {}
        runtime_market_meta: dict[str, dict[str, object]] = {}

        def _normalize_realm_for_runtime(value: object) -> str:
            realm = str(value or "").strip().lower()
            if realm == "":
                raise ValueError("realm_id_required")
            return realm

        def _stock_overrides_for_realm(realm_id: str) -> dict[str, int]:
            overrides = runtime_market_stock.get(realm_id)
            if overrides is None:
                overrides = {}
                runtime_market_stock[realm_id] = overrides
            return overrides

        def _effective_stock(realm_id: str, item_id: str) -> int:
            market = get_realm_market(realm_id)
            overrides = _stock_overrides_for_realm(realm_id)
            if item_id in overrides:
                return max(0, int(overrides[item_id]))
            return max(0, int(market.stock.get(item_id, 0)))

        def _runtime_loaded_regions() -> dict[str, dict[str, object]]:
            loaded_regions: dict[str, dict[str, object]] = {}
            for region_id, row in runtime_regions.items():
                if not bool(row.get("loaded")):
                    continue
                loaded_regions[region_id] = {
                    "realm_id": str(row.get("realm_id", "")),
                    "region_key": str(row.get("region_key", "")),
                    "payload": cast(dict[str, object], row.get("payload", {})),
                    "payload_hash": str(row.get("payload_hash", "")),
                    "cache_policy": str(row.get("cache_policy", "cache")),
                    "loaded_at": str(row.get("updated_at", row.get("created_at", ""))),
                }
            return loaded_regions

        def _sync_runtime_region_loaded_flags(projected_loaded: Mapping[str, object]) -> None:
            projected_ids = {str(key) for key in projected_loaded.keys()}
            now_iso = "runtime"
            for region_id, row in runtime_regions.items():
                should_be_loaded = region_id in projected_ids
                if bool(row.get("loaded")) != should_be_loaded:
                    row["loaded"] = should_be_loaded
                    row["updated_at"] = now_iso

        def _runtime_load_region(action_payload: Mapping[str, object]) -> object:
            if self._repo is None:
                realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                region_key = str(action_payload.get("region_key", "")).strip()
                if realm_id == "" or region_key == "":
                    raise ValueError("realm_or_region_required")
                payload_obj = action_payload.get("payload", {})
                if not isinstance(payload_obj, dict):
                    payload_obj = {}
                cache_policy = str(action_payload.get("cache_policy", "cache")).strip().lower() or "cache"
                region_id = f"{realm_id}::{region_key}"
                now_iso = "runtime"
                existing_region = runtime_regions.get(region_id)
                created_at = (
                    str(existing_region.get("created_at", now_iso))
                    if isinstance(existing_region, dict)
                    else now_iso
                )
                payload_hash = self._canonical_hash(payload_obj)
                runtime_regions[region_id] = {
                    "id": region_id,
                    "workspace_id": payload.workspace_id,
                    "realm_id": realm_id,
                    "region_key": region_key,
                    "payload": cast(dict[str, object], payload_obj),
                    "payload_hash": payload_hash,
                    "cache_policy": cache_policy,
                    "loaded": True,
                    "created_at": created_at,
                    "updated_at": now_iso,
                }
                projected_state = self._world_stream.load(
                    {"world_stream": {"loaded_regions": _runtime_loaded_regions()}},
                    realm_id=realm_id,
                    region_key=region_key,
                    payload=cast(dict[str, object], payload_obj),
                    payload_hash=payload_hash,
                    cache_policy=cache_policy,
                )
                projected_stream = projected_state.get("world_stream")
                projected_loaded_obj = (
                    projected_stream.get("loaded_regions")
                    if isinstance(projected_stream, dict)
                    else {}
                )
                projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
                _sync_runtime_region_loaded_flags(projected_loaded)
                return dict(runtime_regions[region_id])
            return self.load_world_region(payload=WorldRegionLoadInput(**dict(action_payload)))

        def _runtime_unload_region(action_payload: Mapping[str, object]) -> object:
            if self._repo is None:
                realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                region_key = str(action_payload.get("region_key", "")).strip()
                if realm_id == "" or region_key == "":
                    raise ValueError("realm_or_region_required")
                region_id = f"{realm_id}::{region_key}"
                unloaded = bool(runtime_regions.get(region_id, {}).get("loaded"))
                projected_state = self._world_stream.unload(
                    {"world_stream": {"loaded_regions": _runtime_loaded_regions()}},
                    realm_id=realm_id,
                    region_key=region_key,
                )
                projected_stream = projected_state.get("world_stream")
                projected_loaded_obj = (
                    projected_stream.get("loaded_regions")
                    if isinstance(projected_stream, dict)
                    else {}
                )
                projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
                _sync_runtime_region_loaded_flags(projected_loaded)
                row = runtime_regions.get(region_id)
                if row is not None:
                    row["loaded"] = False
                    row["updated_at"] = "runtime"
                return {
                    "workspace_id": payload.workspace_id,
                    "realm_id": realm_id,
                    "region_key": region_key,
                    "unloaded": unloaded,
                }
            return self.unload_world_region(payload=WorldRegionUnloadInput(**dict(action_payload)))

        for action in payload.actions:
            action_payload = dict(action.payload)
            action_payload.setdefault("workspace_id", payload.workspace_id)
            action_payload.setdefault("actor_id", payload.actor_id)
            try:
                if action.kind == "levels.apply":
                    result = self.apply_level_progress(
                        payload=LevelApplyInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "skills.train":
                    result = self.train_skill(
                        payload=SkillTrainInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "perks.unlock":
                    result = self.unlock_perk(
                        payload=PerkUnlockInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "alchemy.craft":
                    result = self.craft_alchemy(
                        payload=AlchemyCraftInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "blacksmith.forge":
                    result = self.forge_blacksmith(
                        payload=BlacksmithForgeInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "combat.resolve":
                    result = self.resolve_combat(
                        payload=CombatResolveInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "market.quote":
                    result = self.market_quote(
                        payload=MarketQuoteInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "market.trade":
                    trade_input = MarketTradeInput(**action_payload)
                    realm_id = _normalize_realm_for_runtime(trade_input.realm_id)
                    stock_before = _effective_stock(realm_id, trade_input.item_id)
                    adjusted_payload = trade_input.model_copy(
                        update={"available_liquidity": min(trade_input.available_liquidity, stock_before)}
                    )
                    trade_result = self.market_trade(
                        payload=adjusted_payload,
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    stock_after = stock_before
                    if trade_result.side == "buy":
                        stock_after = max(0, stock_before - trade_result.filled_qty)
                    elif trade_result.side == "sell":
                        stock_after = max(0, stock_before + trade_result.filled_qty)
                    _stock_overrides_for_realm(realm_id)[trade_input.item_id] = stock_after
                    result = {
                        **trade_result.model_dump(),
                        "stock_before_qty": stock_before,
                        "stock_after_qty": stock_after,
                    }
                elif action.kind == "vitriol.apply":
                    result = self.vitriol_apply_ruler_influence(
                        payload=VitriolApplyRulerInfluenceInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "vitriol.compute":
                    result = self.vitriol_compute(payload=VitriolComputeInput(**action_payload))
                elif action.kind == "vitriol.clear":
                    result = self.vitriol_clear_expired(
                        payload=VitriolClearExpiredInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "djinn.apply":
                    result = self.apply_djinn_influence(
                        payload=DjinnApplyInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "world.region.load":
                    result = _runtime_load_region(action_payload)
                elif action.kind == "world.region.unload":
                    result = _runtime_unload_region(action_payload)
                elif action.kind == "world.region.preload.scenegraph":
                    scene_content_obj: dict[str, object] | None = None
                    realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                    scene_id = str(action_payload.get("scene_id", "")).strip()
                    if isinstance(action_payload.get("scene_content"), dict):
                        scene_content_obj = cast(dict[str, object], action_payload.get("scene_content"))
                    elif scene_id != "" and self._repo is not None:
                        if realm_id == "":
                            raise ValueError("realm_id_required")
                        scene_row = self.get_scene(
                            workspace_id=payload.workspace_id,
                            realm_id=realm_id,
                            scene_id=scene_id,
                        )
                        if scene_row is None:
                            raise ValueError("scene_not_found")
                        scene_content_obj = scene_row.content
                    if scene_content_obj is None:
                        raise ValueError("scene_content_or_scene_id_required")
                    if realm_id == "":
                        realm_from_content = str(scene_content_obj.get("realm_id", "")).strip().lower()
                        if realm_from_content != "":
                            realm_id = realm_from_content
                    if realm_id == "":
                        raise ValueError("realm_id_required")
                    chunk_size_raw = int(action_payload.get("chunk_size", 16))
                    chunk_size = max(1, chunk_size_raw)
                    cache_policy = str(action_payload.get("cache_policy", "stream")).strip().lower() or "stream"
                    region_prefix_raw = str(action_payload.get("region_prefix", "")).strip()
                    if region_prefix_raw != "":
                        region_prefix = region_prefix_raw
                    elif scene_id != "":
                        safe_scene = "".join(ch if (ch.isalnum() or ch in {"_", "-", "/"}) else "_" for ch in scene_id)
                        region_prefix = f"{realm_id}/scene/{safe_scene}"
                    else:
                        region_prefix = f"{realm_id}/scene/runtime"
                    nodes_obj = scene_content_obj.get("nodes")
                    nodes = nodes_obj if isinstance(nodes_obj, list) else []
                    regions: dict[str, list[dict[str, object]]] = {}
                    for node_index, node in enumerate(nodes):
                        if not isinstance(node, dict):
                            continue
                        node_id = str(node.get("node_id") or f"node_{node_index}")
                        kind = str(node.get("kind") or "entity")
                        x = float(node.get("x") or 0.0)
                        y = float(node.get("y") or 0.0)
                        metadata_obj = node.get("metadata")
                        metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
                        z = self._int_from_table(metadata.get("z"), 0)
                        chunk_x = int(x) // chunk_size
                        chunk_y = int(y) // chunk_size
                        region_key = f"{region_prefix}/chunk_{chunk_x}_{chunk_y}"
                        entities = regions.get(region_key)
                        if entities is None:
                            entities = []
                            regions[region_key] = entities
                        entities.append(
                            {
                                "id": node_id,
                                "kind": kind,
                                "x": x,
                                "y": y,
                                "z": z,
                                "metadata": dict(metadata),
                            }
                        )
                    preload_limit_raw = action_payload.get("preload_limit")
                    preload_limit = int(preload_limit_raw) if preload_limit_raw is not None else 0
                    region_results: list[dict[str, object]] = []
                    preloaded_keys: list[str] = []
                    for index, region_key in enumerate(sorted(regions.keys())):
                        if preload_limit > 0 and index >= preload_limit:
                            break
                        entities = sorted(regions[region_key], key=lambda item: str(item.get("id", "")))
                        load_payload = {
                            "workspace_id": payload.workspace_id,
                            "realm_id": realm_id,
                            "region_key": region_key,
                            "payload": {
                                "scene_id": scene_id,
                                "chunk_size": chunk_size,
                                "entities": entities,
                            },
                            "cache_policy": cache_policy,
                        }
                        loaded = _runtime_load_region(load_payload)
                        loaded_map = self._dict_result(loaded)
                        loaded_map["source"] = "scenegraph_preload"
                        region_results.append(loaded_map)
                        preloaded_keys.append(region_key)
                    result = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "scene_id": scene_id,
                        "chunk_size": chunk_size,
                        "cache_policy": cache_policy,
                        "region_count": len(region_results),
                        "region_keys": preloaded_keys,
                        "regions": region_results,
                    }
                elif action.kind == "world.stream.status":
                    if self._repo is None:
                        realm_filter = cast(Optional[str], action_payload.get("realm_id"))
                        realm_norm = (
                            str(realm_filter).strip().lower()
                            if isinstance(realm_filter, str) and str(realm_filter).strip() != ""
                            else None
                        )
                        scoped_rows = [
                            row
                            for row in runtime_regions.values()
                            if realm_norm is None or row.get("realm_id") == realm_norm
                        ]
                        loaded_rows = [
                            row
                            for row in scoped_rows
                            if bool(row.get("loaded"))
                        ]
                        policy_counts: dict[str, int] = {"cache": 0, "stream": 0, "pin": 0}
                        for row in loaded_rows:
                            policy = str(row.get("cache_policy", "cache")).strip().lower()
                            policy_counts[policy] = policy_counts.get(policy, 0) + 1
                        capacity = self._world_stream.max_loaded_regions
                        total_regions = len(scoped_rows)
                        loaded_count = len(loaded_rows)
                        unloaded_count = max(0, total_regions - loaded_count)
                        pressure = 0.0 if capacity <= 0 else float(loaded_count) / float(capacity)
                        result = {
                            "workspace_id": payload.workspace_id,
                            "realm_id": realm_norm,
                            "total_regions": total_regions,
                            "loaded_count": loaded_count,
                            "unloaded_count": unloaded_count,
                            "capacity": capacity,
                            "pressure": pressure,
                            "policy_counts": policy_counts,
                            "pressure_components": {
                                "stream_occupancy": pressure,
                                "demon_total": 0.0,
                                "composite": pressure,
                            },
                            "demon_pressures": dict(self._DEMON_PRESSURE_DEFAULTS),
                            "demon_maladies": dict(self._DEMON_MALADY_DOMAINS),
                        }
                    else:
                        result = self.world_stream_status(
                            workspace_id=str(action_payload.get("workspace_id", payload.workspace_id)),
                            realm_id=cast(Optional[str], action_payload.get("realm_id")),
                        )
                elif action.kind == "world.coins.list":
                    result = [item.model_dump() for item in self.list_realm_coins(cast(Optional[str], action_payload.get("realm_id")))]
                elif action.kind == "world.markets.list":
                    realm_filter = cast(Optional[str], action_payload.get("realm_id"))
                    markets = self.list_realm_markets(realm_filter)
                    market_rows: list[dict[str, object]] = []
                    for market in markets:
                        row = market.model_dump()
                        stock_map = {key: int(value) for key, value in market.stock.items()}
                        realm_overrides = runtime_market_stock.get(market.realm_id, {})
                        for item_id, qty in realm_overrides.items():
                            stock_map[item_id] = max(0, int(qty))
                        row["stock"] = stock_map
                        meta_overrides = runtime_market_meta.get(market.realm_id, {})
                        for key, value in meta_overrides.items():
                            row[key] = value
                        market_rows.append(row)
                    result = market_rows
                elif action.kind == "world.market.stock.adjust":
                    realm_id = _normalize_realm_for_runtime(action_payload.get("realm_id"))
                    item_id = str(action_payload.get("item_id", "")).strip()
                    if item_id == "":
                        raise ValueError("item_id_required")
                    stock_before = _effective_stock(realm_id, item_id)
                    set_qty_raw = action_payload.get("set_qty")
                    if set_qty_raw is None:
                        delta = int(action_payload.get("delta", 0))
                        stock_after = max(0, stock_before + delta)
                    else:
                        stock_after = max(0, int(set_qty_raw))
                    _stock_overrides_for_realm(realm_id)[item_id] = stock_after
                    result = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "item_id": item_id,
                        "stock_before_qty": stock_before,
                        "stock_after_qty": stock_after,
                    }
                elif action.kind == "world.market.sovereignty.transition":
                    realm_id = _normalize_realm_for_runtime(action_payload.get("realm_id"))
                    market = get_realm_market(realm_id)
                    victor_id = str(action_payload.get("victor_id", "player_commonwealth")).strip().lower()
                    if victor_id == "":
                        raise ValueError("victor_id_required")
                    if not bool(action_payload.get("overthrow", True)):
                        raise ValueError("sovereignty_transition_requires_overthrow")
                    prior_operator = str(
                        runtime_market_meta.get(realm_id, {}).get("dominant_operator", market.dominant_operator)
                    )
                    redistribution_mode = str(
                        action_payload.get("redistribution_mode", "equalized_public_distribution")
                    ).strip().lower() or "equalized_public_distribution"
                    beneficiary_groups_raw = action_payload.get("beneficiary_groups", [])
                    beneficiary_groups: list[str] = []
                    if isinstance(beneficiary_groups_raw, list):
                        for item in beneficiary_groups_raw:
                            token = str(item).strip().lower()
                            if token != "":
                                beneficiary_groups.append(token)
                    if len(beneficiary_groups) == 0:
                        beneficiary_groups = ["citizens", "artisans", "travelers"]
                    dominant_network = str(
                        action_payload.get("market_network", "public_redistribution_council")
                    ).strip().lower() or "public_redistribution_council"
                    dominance_bp_raw = int(action_payload.get("dominance_bp", 1000))
                    dominance_bp = max(0, min(10000, dominance_bp_raw))
                    transition_tick = int(action_payload.get("tick", 0))
                    transition_note = str(action_payload.get("note", "market_sovereignty_transition")).strip()
                    runtime_market_meta[realm_id] = {
                        "dominant_operator": victor_id,
                        "market_network": dominant_network,
                        "dominance_bp": dominance_bp,
                        "redistribution_policy": {
                            "mode": redistribution_mode,
                            "beneficiary_groups": beneficiary_groups,
                            "active": True,
                            "transition_tick": transition_tick,
                            "note": transition_note,
                        },
                    }
                    result = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "overthrow": True,
                        "prior_operator": prior_operator,
                        "new_operator": victor_id,
                        "market_network": dominant_network,
                        "dominance_bp": dominance_bp,
                        "redistribution_policy": runtime_market_meta[realm_id]["redistribution_policy"],
                    }
                else:
                    raise ValueError(f"unsupported_runtime_action:{action.kind}")
                results.append(
                    RuntimeActionOut(
                        action_id=action.action_id,
                        kind=action.kind,
                        ok=True,
                        result=self._dict_result(result),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive capture for file-driven plans
                results.append(
                    RuntimeActionOut(
                        action_id=action.action_id,
                        kind=action.kind,
                        ok=False,
                        error=str(exc),
                    )
                )
        applied_count = sum(1 for item in results if item.ok)
        failed_count = len(results) - applied_count
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "plan_id": payload.plan_id,
            "results": [item.model_dump(mode="json") for item in results],
        }
        out = RuntimeConsumeOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            applied_count=applied_count,
            failed_count=failed_count,
            results=results,
            hash=self._canonical_hash(hash_payload),
        )
        if self._repo is not None and hasattr(self._repo, "create_runtime_plan_run"):
            plan_payload_json = self._canonical_json(
                {
                    "workspace_id": payload.workspace_id,
                    "actor_id": payload.actor_id,
                    "plan_id": payload.plan_id,
                    "actions": [item.model_dump(mode="json") for item in payload.actions],
                }
            )
            plan_hash = self._canonical_hash(
                {
                    "workspace_id": payload.workspace_id,
                    "actor_id": payload.actor_id,
                    "plan_id": payload.plan_id,
                    "actions": [item.model_dump(mode="json") for item in payload.actions],
                }
            )
            self._repo.create_runtime_plan_run(
                RuntimePlanRun(
                    workspace_id=payload.workspace_id,
                    actor_id=payload.actor_id,
                    plan_id=payload.plan_id,
                    plan_payload_json=plan_payload_json,
                    plan_hash=plan_hash,
                    result_json=self._canonical_json(out.model_dump(mode="json")),
                    result_hash=out.hash,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return out

    def replay_runtime_plan(
        self,
        *,
        payload: RuntimeReplayInput,
        actor_id: str,
        workshop_id: str,
    ) -> RuntimeReplayOut:
        repo = self._require_repo()
        baseline = repo.get_latest_runtime_plan_run(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
        )
        if baseline is None:
            raise ValueError("runtime_plan_not_found")
        plan_obj = self._json_to_object_map(baseline.plan_payload_json)
        actions_obj = plan_obj.get("actions")
        actions = actions_obj if isinstance(actions_obj, list) else []
        replay_in = RuntimeConsumeInput(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            actions=actions,
        )
        replay_out = self.consume_runtime_plan(
            payload=replay_in,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return RuntimeReplayOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            baseline_hash=baseline.result_hash,
            replay_hash=replay_out.hash,
            hash_match=baseline.result_hash == replay_out.hash,
            baseline_run_id=baseline.id,
            replay=replay_out,
        )

    def list_runtime_plan_runs(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        plan_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[RuntimePlanRunOut]:
        repo = self._require_repo()
        actor = actor_id.strip()
        if actor == "":
            raise ValueError("actor_id_required")
        plan_filter = (plan_id or "").strip()
        max_rows = max(1, min(500, int(limit)))
        rows = list(repo.list_runtime_plan_runs_for_actor(workspace_id, actor, plan_filter if plan_filter != "" else None))

        out_rows: list[RuntimePlanRunOut] = []
        for row in rows[:max_rows]:
            result_obj = self._json_to_object_map(row.result_json)
            out_rows.append(
                RuntimePlanRunOut(
                    run_id=row.id,
                    workspace_id=row.workspace_id,
                    actor_id=row.actor_id,
                    plan_id=row.plan_id,
                    plan_hash=row.plan_hash,
                    result_hash=row.result_hash,
                    result_summary={
                        "applied_count": int(result_obj.get("applied_count", 0) or 0),
                        "failed_count": int(result_obj.get("failed_count", 0) or 0),
                        "hash": str(result_obj.get("hash", "")),
                    },
                    created_at=row.created_at,
                )
            )
        return out_rows

    def apply_djinn_influence(
        self,
        *,
        payload: DjinnApplyInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> DjinnApplyOut:
        djinn_id = payload.djinn_id.strip().lower()
        if djinn_id not in self._DJINN_ALIGNMENT:
            raise ValueError("invalid_djinn")
        normalized_realm = payload.realm_id.strip().lower()
        normalized_ring = payload.ring_id.strip().lower()
        if djinn_id == "drovitth":
            if normalized_realm != "sulphera" or normalized_ring not in {"royal", "royalty"}:
                raise ValueError("drovitth_requires_sulphera_royalty_ring")

        target_frontiers = self._normalize_frontier_ids(payload.target_frontiers)
        frontier_effects: dict[str, str] = {}
        scarred_frontiers: list[str] = []
        opened_frontiers: list[str] = []
        placements: list[str] = []
        orrery_marks: list[DjinnOrreryMark] = []
        effect: str = "record"

        if djinn_id == "keshi":
            effect = "collapse"
            for frontier_id in target_frontiers:
                frontier_effects[frontier_id] = "collapsed"
                scarred_frontiers.append(frontier_id)
                token = self._safe_token(frontier_id)
                placements.append(f"entity scar_{token} 0 0 scar")
                orrery_marks.append(
                    DjinnOrreryMark(
                        mark_id=f"keshi:{token}:{payload.tick}",
                        source_djinn_id="keshi",
                        frontier_id=frontier_id,
                        effect="collapse",
                        tick=payload.tick,
                        note=payload.reason or "kernel_scar",
                    )
                )
        elif djinn_id == "giann":
            effect = "open"
            for frontier_id in target_frontiers:
                frontier_effects[frontier_id] = "opened"
                opened_frontiers.append(frontier_id)
                token = self._safe_token(frontier_id)
                placements.append(f"entity boon_{token} 0 0 boon")
                orrery_marks.append(
                    DjinnOrreryMark(
                        mark_id=f"giann:{token}:{payload.tick}",
                        source_djinn_id="giann",
                        frontier_id=frontier_id,
                        effect="open",
                        tick=payload.tick,
                        note=payload.reason or "player_boon",
                    )
                )
        else:
            effect = "record"
            placements.append("entity royal_orrery 0 0 instrument")
            observed = [
                mark
                for mark in payload.observed_marks
                if mark.source_djinn_id.strip().lower() in {"keshi", "giann"}
            ]
            orrery_marks = sorted(
                observed,
                key=lambda mark: (
                    int(mark.tick),
                    mark.source_djinn_id.strip().lower(),
                    mark.frontier_id,
                    mark.mark_id,
                ),
            )

        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "djinn_id": djinn_id,
            "effect": effect,
            "frontier_effects": frontier_effects,
            "scarred_frontiers": scarred_frontiers,
            "opened_frontiers": opened_frontiers,
            "placements": placements,
            "orrery_marks": [mark.model_dump() for mark in orrery_marks],
            "tick": payload.tick,
        }
        out = DjinnApplyOut(
            actor_id=payload.actor_id,
            djinn_id=cast(Any, djinn_id),
            alignment=self._DJINN_ALIGNMENT[djinn_id],
            effect=cast(Any, effect),
            applied=True,
            frontier_effects=frontier_effects,
            scarred_frontiers=scarred_frontiers,
            opened_frontiers=opened_frontiers,
            placements=placements,
            orrery_marks=orrery_marks,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.djinn.apply {payload.actor_id} {djinn_id} {effect}",
                context={
                    "workspace_id": payload.workspace_id,
                    "scene_id": payload.scene_id,
                    "realm_id": normalized_realm,
                    "ring_id": normalized_ring,
                    "rule": "djinn_apply_influence",
                    "result": out.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return out

    def renderer_tables(
        self,
        *,
        payload: RendererTablesInput,
        actor_id: str,
        workshop_id: str,
    ) -> RendererTablesOut:
        tables: dict[str, object] = {}
        if payload.level is not None:
            tables["levels"] = self.apply_level_progress(
                payload=payload.level,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.skill is not None:
            tables["skills"] = self.train_skill(
                payload=payload.skill,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.perk is not None:
            tables["perks"] = self.unlock_perk(
                payload=payload.perk,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.alchemy is not None:
            tables["alchemy"] = self.craft_alchemy(
                payload=payload.alchemy,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.blacksmith is not None:
            tables["blacksmith"] = self.forge_blacksmith(
                payload=payload.blacksmith,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        market: dict[str, object] = {}
        if payload.market_quote is not None:
            market["quote"] = self.market_quote(
                payload=payload.market_quote,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.market_trade is not None:
            market["trade"] = self.market_trade(
                payload=payload.market_trade,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if market:
            tables["market"] = market
        vitriol: dict[str, object] = {}
        if payload.vitriol_apply is not None:
            vitriol["apply"] = self.vitriol_apply_ruler_influence(
                payload=payload.vitriol_apply,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.vitriol_compute is not None:
            vitriol["compute"] = self.vitriol_compute(payload=payload.vitriol_compute).model_dump()
        if payload.vitriol_clear is not None:
            vitriol["clear"] = self.vitriol_clear_expired(
                payload=payload.vitriol_clear,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if vitriol:
            tables["vitriol"] = vitriol

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "tables": tables,
        }
        return RendererTablesOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=tables,
        )

    def build_isometric_render_contract(
        self,
        *,
        payload: IsometricRenderContractInput,
    ) -> IsometricRenderContractOut:
        tile_width = max(8, int(payload.tile_width))
        tile_height = max(4, int(payload.tile_height))
        elevation_step = max(1, int(payload.elevation_step))
        realm_id = payload.realm_id.strip().lower()
        scene = self.get_scene(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
        )
        if scene is None:
            raise ValueError("scene_not_found")

        drawables: list[IsometricDrawableOut] = []
        scene_nodes_raw = scene.content.get("nodes")
        scene_nodes = scene_nodes_raw if isinstance(scene_nodes_raw, list) else []

        manifest_rows = self.list_asset_manifests(payload.workspace_id)
        sprite_lookup: dict[str, str] = {}
        material_lookup: dict[str, str] = {}
        atlas_version = "v1"
        material_pack_version = "v1"
        requested_pack_id = (payload.asset_pack_id or "").strip()
        for row in manifest_rows:
            if row.realm_id != realm_id:
                continue
            payload_obj = row.payload if isinstance(row.payload, dict) else {}
            if requested_pack_id != "":
                payload_pack_id = str(payload_obj.get("asset_pack_id") or "").strip()
                if row.manifest_id != requested_pack_id and payload_pack_id != requested_pack_id:
                    continue
            atlas_version_raw = payload_obj.get("atlas_version")
            if isinstance(atlas_version_raw, str) and atlas_version_raw.strip() != "":
                atlas_version = atlas_version_raw.strip()
            material_version_raw = payload_obj.get("material_pack_version")
            if isinstance(material_version_raw, str) and material_version_raw.strip() != "":
                material_pack_version = material_version_raw.strip()
            if row.kind.strip().lower() == "sprite":
                for key, value in payload_obj.items():
                    if key in {"atlas_version", "material_pack_version", "asset_pack_id"}:
                        continue
                    if isinstance(value, str):
                        sprite_lookup[str(key)] = value
            if row.kind.strip().lower() == "material":
                for key, value in payload_obj.items():
                    if key in {"atlas_version", "material_pack_version", "asset_pack_id"}:
                        continue
                    if isinstance(value, str):
                        material_lookup[str(key)] = value

        allowed_atlas_versions = {str(item).strip() for item in payload.renderer_atlas_versions if str(item).strip() != ""}
        if allowed_atlas_versions and atlas_version not in allowed_atlas_versions:
            raise ValueError(f"incompatible_atlas_version:{atlas_version}")
        allowed_material_versions = {str(item).strip() for item in payload.renderer_material_versions if str(item).strip() != ""}
        if allowed_material_versions and material_pack_version not in allowed_material_versions:
            raise ValueError(f"incompatible_material_pack_version:{material_pack_version}")

        missing_sprite = "placeholder://sprite/missing"
        fallback_count = 0

        def _resolve_sprite(*, explicit: str, lookup_key: str, kind: str) -> tuple[str, str]:
            if explicit != "":
                return explicit, "explicit"
            if lookup_key in sprite_lookup:
                return sprite_lookup[lookup_key], "lookup:key"
            if kind in sprite_lookup:
                return sprite_lookup[kind], "lookup:kind"
            if payload.strict_assets:
                raise ValueError(f"missing_sprite_asset:{lookup_key or kind}")
            return missing_sprite, "fallback:missing"

        def _resolve_material(*, explicit: str, kind: str) -> tuple[str, str]:
            if explicit != "":
                return explicit, "explicit"
            if kind in material_lookup:
                return material_lookup[kind], "lookup:kind"
            if payload.strict_assets:
                raise ValueError(f"missing_material_asset:{kind}")
            return "default", "fallback:default"

        for index, node in enumerate(scene_nodes):
            if not isinstance(node, dict):
                continue
            metadata_obj = node.get("metadata")
            metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
            x = float(node.get("x") or 0.0)
            y = float(node.get("y") or 0.0)
            z = self._int_from_table(metadata.get("z"), 0)
            node_id = str(node.get("node_id") or f"scene_node_{index}")
            kind = str(node.get("kind") or "entity")
            sprite, sprite_source = _resolve_sprite(
                explicit=str(metadata.get("sprite") or ""),
                lookup_key=node_id,
                kind=kind,
            )
            material, material_source = _resolve_material(
                explicit=str(metadata.get("material") or ""),
                kind=kind,
            )
            screen_x = (x - y) * (tile_width / 2.0)
            screen_y = (x + y) * (tile_height / 2.0) - (z * elevation_step)
            depth_key = (x + y) + (z * 0.01)
            out_meta = dict(metadata)
            if sprite_source.startswith("fallback") or material_source.startswith("fallback"):
                fallback_count += 1
                out_meta["asset_fallback"] = {
                    "sprite_source": sprite_source,
                    "material_source": material_source,
                }
            if payload.include_material_constraints:
                akinenwun = str(metadata.get("akinenwun") or "").strip()
                if akinenwun != "":
                    try:
                        from qqva.shygazun_compiler import compile_akinenwun_to_ir, derive_render_constraints

                        constraints = derive_render_constraints(compile_akinenwun_to_ir(akinenwun))
                        out_meta["render_constraints"] = constraints
                    except Exception:
                        out_meta["render_constraints"] = {"status": "unavailable"}
            drawables.append(
                IsometricDrawableOut(
                    drawable_id=node_id,
                    source="scene",
                    kind=kind,
                    x=x,
                    y=y,
                    z=z,
                    screen_x=screen_x,
                    screen_y=screen_y,
                    depth_key=depth_key,
                    sprite=sprite,
                    material=material,
                    metadata=out_meta,
                )
            )

        world_regions = self.list_world_regions(workspace_id=payload.workspace_id, realm_id=realm_id)
        for row in world_regions:
            if not payload.include_unloaded_regions and not row.loaded:
                continue
            entities_obj = row.payload.get("entities")
            entities = entities_obj if isinstance(entities_obj, list) else []
            for index, entity in enumerate(entities):
                if isinstance(entity, str):
                    entity_id = entity
                    ex = float(index)
                    ey = 0.0
                    ez = 0
                    kind = "region_entity"
                    meta: dict[str, object] = {}
                    sprite, sprite_source = _resolve_sprite(
                        explicit="",
                        lookup_key=entity_id,
                        kind=kind,
                    )
                    material, material_source = _resolve_material(
                        explicit="",
                        kind=kind,
                    )
                elif isinstance(entity, dict):
                    entity_id = str(entity.get("id") or entity.get("entity_id") or f"{row.region_key}:{index}")
                    ex = float(entity.get("x") or index)
                    ey = float(entity.get("y") or 0.0)
                    ez = self._int_from_table(entity.get("z"), 0)
                    kind = str(entity.get("kind") or entity.get("tag") or "region_entity")
                    meta = dict(entity.get("metadata") or {}) if isinstance(entity.get("metadata"), dict) else {}
                    sprite, sprite_source = _resolve_sprite(
                        explicit=str(entity.get("sprite") or ""),
                        lookup_key=entity_id,
                        kind=kind,
                    )
                    material, material_source = _resolve_material(
                        explicit=str(entity.get("material") or ""),
                        kind=kind,
                    )
                else:
                    continue
                screen_x = (ex - ey) * (tile_width / 2.0)
                screen_y = (ex + ey) * (tile_height / 2.0) - (ez * elevation_step)
                depth_key = (ex + ey) + (ez * 0.01)
                if sprite_source.startswith("fallback") or material_source.startswith("fallback"):
                    fallback_count += 1
                    meta["asset_fallback"] = {
                        "sprite_source": sprite_source,
                        "material_source": material_source,
                    }
                drawables.append(
                    IsometricDrawableOut(
                        drawable_id=f"{row.region_key}:{entity_id}",
                        source="region",
                        kind=kind,
                        x=ex,
                        y=ey,
                        z=ez,
                        screen_x=screen_x,
                        screen_y=screen_y,
                        depth_key=depth_key,
                        sprite=sprite,
                        material=material,
                        metadata=meta,
                    )
                )

        drawables.sort(
            key=lambda item: (
                item.depth_key,
                item.screen_y,
                item.screen_x,
                item.drawable_id,
            )
        )
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "realm_id": realm_id,
            "scene_id": payload.scene_id,
            "projection": {
                "type": "isometric_2_5d",
                "tile_width": tile_width,
                "tile_height": tile_height,
                "elevation_step": elevation_step,
            },
            "asset_pack": {
                "asset_pack_id": requested_pack_id if requested_pack_id != "" else None,
                "atlas_version": atlas_version,
                "material_pack_version": material_pack_version,
                "fallback_sprite": missing_sprite,
            },
            "drawables": [item.model_dump() for item in drawables],
        }
        return IsometricRenderContractOut(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
            projection={
                "type": "isometric_2_5d",
                "tile_width": tile_width,
                "tile_height": tile_height,
                "elevation_step": elevation_step,
            },
            asset_pack={
                "asset_pack_id": requested_pack_id if requested_pack_id != "" else None,
                "atlas_version": atlas_version,
                "material_pack_version": material_pack_version,
                "fallback_sprite": missing_sprite,
            },
            drawable_count=len(drawables),
            drawables=drawables,
            stats={
                "scene_nodes": len(scene_nodes),
                "region_count": len(world_regions),
                "asset_manifest_count": len(manifest_rows),
                "fallback_count": fallback_count,
            },
            hash=self._canonical_hash(hash_payload),
        )

    def build_render_graph_contract(
        self,
        *,
        payload: RenderGraphContractInput,
    ) -> RenderGraphContractOut:
        iso = self.build_isometric_render_contract(
            payload=IsometricRenderContractInput(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id,
                scene_id=payload.scene_id,
                asset_pack_id=payload.asset_pack_id,
                strict_assets=payload.strict_assets,
                renderer_atlas_versions=payload.renderer_atlas_versions,
                renderer_material_versions=payload.renderer_material_versions,
                include_unloaded_regions=payload.include_unloaded_regions,
                include_material_constraints=payload.include_material_constraints,
            )
        )
        nodes: list[RenderGraphNodeOut] = []
        for drawable in iso.drawables:
            nodes.append(
                RenderGraphNodeOut(
                    node_id=drawable.drawable_id,
                    source=drawable.source,
                    kind=drawable.kind,
                    transform={
                        "position": {"x": drawable.x, "y": float(drawable.z), "z": drawable.y},
                        "screen_hint": {"x": drawable.screen_x, "y": drawable.screen_y},
                        "depth_key": drawable.depth_key,
                    },
                    material=drawable.material,
                    sprite=drawable.sprite,
                    metadata=drawable.metadata,
                )
            )

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id.strip().lower(),
            "scene_id": payload.scene_id,
            "coordinate_space": payload.coordinate_space,
            "nodes": [item.model_dump() for item in nodes],
            "asset_pack": iso.asset_pack,
        }
        return RenderGraphContractOut(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            scene_id=payload.scene_id,
            coordinate_space=payload.coordinate_space,
            node_count=len(nodes),
            nodes=nodes,
            asset_pack=iso.asset_pack,
            stats={
                **iso.stats,
                "source_contract": "isometric_2_5d",
            },
            hash=self._canonical_hash(hash_payload),
        )

    def list_suppliers(self, workspace_id: str) -> Sequence[SupplierOut]:
        rows = self._require_repo().list_suppliers(workspace_id=workspace_id)
        return [SupplierOut.model_validate(row, from_attributes=True) for row in rows]

    def create_supplier(self, payload: SupplierCreate) -> SupplierOut:
        row = Supplier(
            workspace_id=payload.workspace_id,
            supplier_name=payload.supplier_name,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            notes=payload.notes,
        )
        out = self._require_repo().create_supplier(row)
        return SupplierOut.model_validate(out, from_attributes=True)

    def create_public_inquiry(self, payload: PublicCommissionInquiryCreate) -> LeadOut:
        row = Lead(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            details=payload.details,
            status="new",
            source="public_commission_hall",
        )
        out = self._require_repo().create_lead(row)
        return LeadOut.model_validate(out, from_attributes=True)

    def list_public_commission_quotes(self, workspace_id: str) -> Sequence[PublicCommissionQuoteOut]:
        rows = self._require_repo().list_public_quotes(workspace_id=workspace_id)
        return [
            PublicCommissionQuoteOut(
                id=row.id,
                workspace_id=row.workspace_id,
                title=row.title,
                amount_cents=row.amount_cents,
                currency=row.currency,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def list_asset_manifests(self, workspace_id: str) -> Sequence[AssetManifestOut]:
        rows = self._require_repo().list_asset_manifests(workspace_id=workspace_id)
        return [
            AssetManifestOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                manifest_id=row.manifest_id,
                name=row.name,
                kind=row.kind,
                payload=self._json_to_object_map(row.payload_json),
                payload_hash=row.payload_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_asset_manifest(self, payload: AssetManifestCreate) -> AssetManifestOut:
        payload_hash = self._canonical_hash(payload.payload)
        row = AssetManifest(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower() or "lapidus",
            manifest_id=payload.manifest_id,
            name=payload.name,
            kind=payload.kind,
            payload_json=self._canonical_json(payload.payload),
            payload_hash=payload_hash,
        )
        saved = self._require_repo().create_asset_manifest(row)
        return AssetManifestOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            manifest_id=saved.manifest_id,
            name=saved.name,
            kind=saved.kind,
            payload=self._json_to_object_map(saved.payload_json),
            payload_hash=saved.payload_hash,
            created_at=saved.created_at,
        )

    def list_realms(self) -> Sequence[RealmOut]:
        rows = self._require_repo().list_realms()
        return [
            RealmOut(
                id=row.id,
                slug=row.slug,
                name=row.name,
                description=row.description,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def validate_realm(self, payload: RealmValidateInput) -> RealmValidateOut:
        slug = payload.realm_id.strip().lower()
        row = self._require_repo().get_realm_by_slug(slug)
        if row is None:
            return RealmValidateOut(realm_id=payload.realm_id, ok=False, reason="unknown_realm")
        return RealmValidateOut(realm_id=row.slug, ok=True, reason="ok")

    def validate_content(self, payload: ContentValidateInput) -> ContentValidateOut:
        realm_validation = self.validate_realm(RealmValidateInput(realm_id=payload.realm_id))
        errors: list[str] = []
        warnings: list[str] = []
        stats: dict[str, object] = {}
        if not realm_validation.ok:
            errors.append(f"unknown_realm:{payload.realm_id}")
        if payload.source == "cobra":
            result = validate_cobra_content(payload.payload, realm_id=payload.realm_id, scene_id=payload.scene_id)
        else:
            result = validate_json_content(payload.payload, realm_id=payload.realm_id, scene_id=payload.scene_id)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
        stats.update(result.stats)
        ok = len(errors) == 0
        return ContentValidateOut(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
            source=payload.source,
            ok=ok,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )

    def list_scenes(self, workspace_id: str, realm_id: str | None = None) -> Sequence[SceneOut]:
        rows = self._require_repo().list_scenes(workspace_id=workspace_id, realm_id=realm_id)
        return [
            SceneOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                scene_id=row.scene_id,
                name=row.name,
                description=row.description,
                content=self._json_to_object_map(row.content_json),
                content_hash=row.content_hash,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> SceneOut | None:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            return None
        return SceneOut(
            id=row.id,
            workspace_id=row.workspace_id,
            realm_id=row.realm_id,
            scene_id=row.scene_id,
            name=row.name,
            description=row.description,
            content=self._json_to_object_map(row.content_json),
            content_hash=row.content_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_scene(self, payload: SceneCreateInput) -> SceneOut:
        realm_error = validate_scene_realm(payload.scene_id, payload.realm_id)
        if realm_error:
            raise ValueError(realm_error)
        content_hash = self._canonical_hash(payload.content)
        row = Scene(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            scene_id=payload.scene_id.strip(),
            name=payload.name,
            description=payload.description,
            content_json=self._canonical_json(payload.content),
            content_hash=content_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        saved = self._require_repo().create_scene(row)
        return SceneOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            scene_id=saved.scene_id,
            name=saved.name,
            description=saved.description,
            content=self._json_to_object_map(saved.content_json),
            content_hash=saved.content_hash,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def update_scene(self, workspace_id: str, realm_id: str, scene_id: str, payload: SceneUpdateInput) -> SceneOut:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            raise ValueError("scene_not_found")
        if payload.name is not None:
            row.name = payload.name
        if payload.description is not None:
            row.description = payload.description
        if payload.content is not None:
            row.content_json = self._canonical_json(payload.content)
            row.content_hash = self._canonical_hash(payload.content)
        row.updated_at = datetime.utcnow()
        saved = self._require_repo().save_scene(row)
        return SceneOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            scene_id=saved.scene_id,
            name=saved.name,
            description=saved.description,
            content=self._json_to_object_map(saved.content_json),
            content_hash=saved.content_hash,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def emit_scene_from_library(
        self,
        *,
        workspace_id: str,
        realm_id: str,
        scene_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> SceneEmitOut:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            raise ValueError("scene_not_found")
        content = self._json_to_object_map(row.content_json)
        nodes_obj = content.get("nodes")
        edges_obj = content.get("edges")
        if not isinstance(nodes_obj, list) or not isinstance(edges_obj, list):
            raise ValueError("scene_graph_invalid")
        payload = SceneGraphEmitInput(
            workspace_id=workspace_id,
            realm_id=realm_id,
            scene_id=scene_id,
            nodes=nodes_obj,
            edges=edges_obj,
        )
        result = self.emit_scene_graph(payload=payload, actor_id=actor_id, workshop_id=workshop_id)
        return SceneEmitOut(
            scene_id=result.scene_id,
            nodes_emitted=result.nodes_emitted,
            edges_emitted=result.edges_emitted,
        )

    def create_scene_from_cobra(self, payload: SceneCompileInput) -> SceneOut:
        content = build_scene_graph_content_from_cobra(
            payload.cobra_source,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
        )
        create_payload = SceneCreateInput(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
            name=payload.name,
            description=payload.description,
            content=content,
        )
        return self.create_scene(create_payload)

    def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[WorldRegionOut]:
        rows = self._require_repo().list_world_regions(workspace_id=workspace_id, realm_id=realm_id)
        return [
            WorldRegionOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                region_key=row.region_key,
                payload=self._json_to_object_map(row.payload_json),
                payload_hash=row.payload_hash,
                cache_policy=row.cache_policy,
                loaded=row.loaded,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    @staticmethod
    def _region_id(realm_id: str, region_key: str) -> str:
        return f"{realm_id.strip().lower()}::{region_key.strip()}"

    def _reconcile_world_stream_loaded_flags(
        self,
        *,
        workspace_id: str,
        recently_loaded_row: WorldRegion,
    ) -> None:
        repo = self._require_repo()
        rows = list(repo.list_world_regions(workspace_id=workspace_id, realm_id=None))
        loaded_regions: dict[str, object] = {}
        for row in rows:
            if not row.loaded:
                continue
            loaded_regions[self._region_id(row.realm_id, row.region_key)] = {
                "realm_id": row.realm_id,
                "region_key": row.region_key,
                "payload": self._json_to_object_map(row.payload_json),
                "payload_hash": row.payload_hash,
                "cache_policy": row.cache_policy,
                "loaded_at": row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat(),
            }

        projected_state = self._world_stream.load(
            {"world_stream": {"loaded_regions": loaded_regions}},
            realm_id=recently_loaded_row.realm_id,
            region_key=recently_loaded_row.region_key,
            payload=self._json_to_object_map(recently_loaded_row.payload_json),
            payload_hash=recently_loaded_row.payload_hash,
            cache_policy=recently_loaded_row.cache_policy,
        )
        world_stream_obj = projected_state.get("world_stream")
        projected_loaded_obj = (
            world_stream_obj.get("loaded_regions") if isinstance(world_stream_obj, dict) else {}
        )
        projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
        projected_ids = {str(key) for key in projected_loaded.keys()}
        now = datetime.utcnow()
        for row in rows:
            region_id = self._region_id(row.realm_id, row.region_key)
            should_be_loaded = region_id in projected_ids
            if row.loaded != should_be_loaded:
                row.loaded = should_be_loaded
                row.updated_at = now
                repo.save_world_region(row)

    def world_stream_status(self, workspace_id: str, realm_id: str | None = None) -> WorldStreamStatusOut:
        normalized_realm = realm_id.strip().lower() if isinstance(realm_id, str) and realm_id.strip() != "" else None
        rows = self._require_repo().list_world_regions(workspace_id=workspace_id, realm_id=normalized_realm)
        total_regions = len(rows)
        loaded_rows = [row for row in rows if row.loaded]
        policy_counts: dict[str, int] = {"cache": 0, "stream": 0, "pin": 0}
        for row in loaded_rows:
            policy = row.cache_policy.strip().lower()
            if policy in policy_counts:
                policy_counts[policy] += 1
            else:
                policy_counts[policy] = policy_counts.get(policy, 0) + 1
        capacity = self._world_stream.max_loaded_regions
        loaded_count = len(loaded_rows)
        unloaded_count = max(0, total_regions - loaded_count)
        pressure = 0.0 if capacity <= 0 else float(loaded_count) / float(capacity)
        pressure_components = {
            "stream_occupancy": pressure,
            "demon_total": 0.0,
            "composite": pressure,
        }
        return WorldStreamStatusOut(
            workspace_id=workspace_id,
            realm_id=normalized_realm,
            total_regions=total_regions,
            loaded_count=loaded_count,
            unloaded_count=unloaded_count,
            capacity=capacity,
            pressure=pressure,
            policy_counts=policy_counts,
            pressure_components=pressure_components,
            demon_pressures=dict(self._DEMON_PRESSURE_DEFAULTS),
            demon_maladies=dict(self._DEMON_MALADY_DOMAINS),
        )

    def load_world_region(self, payload: WorldRegionLoadInput) -> WorldRegionOut:
        realm_validation = self.validate_realm(RealmValidateInput(realm_id=payload.realm_id))
        if not realm_validation.ok:
            raise ValueError(f"unknown_realm:{payload.realm_id}")
        region_key = payload.region_key.strip()
        if not region_key:
            raise ValueError("region_key_required")
        cache_policy = payload.cache_policy.strip().lower() or "cache"
        if cache_policy not in {"cache", "stream", "pin"}:
            raise ValueError("invalid_cache_policy")
        repo = self._require_repo()
        existing = repo.get_world_region(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            region_key=region_key,
        )
        payload_hash = self._canonical_hash(payload.payload)
        now = datetime.utcnow()
        if existing is None:
            row = WorldRegion(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id.strip().lower(),
                region_key=region_key,
                payload_json=self._canonical_json(payload.payload),
                payload_hash=payload_hash,
                cache_policy=cache_policy,
                loaded=True,
                created_at=now,
                updated_at=now,
            )
            saved = repo.create_world_region(row)
        else:
            existing.payload_json = self._canonical_json(payload.payload)
            existing.payload_hash = payload_hash
            existing.cache_policy = cache_policy
            existing.loaded = True
            existing.updated_at = now
            saved = repo.save_world_region(existing)
        self._reconcile_world_stream_loaded_flags(
            workspace_id=saved.workspace_id,
            recently_loaded_row=saved,
        )
        refreshed = repo.get_world_region(
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            region_key=saved.region_key,
        )
        if refreshed is not None:
            saved = refreshed
        return WorldRegionOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            region_key=saved.region_key,
            payload=self._json_to_object_map(saved.payload_json),
            payload_hash=saved.payload_hash,
            cache_policy=saved.cache_policy,
            loaded=saved.loaded,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def unload_world_region(self, payload: WorldRegionUnloadInput) -> WorldRegionUnloadOut:
        region_key = payload.region_key.strip()
        if not region_key:
            raise ValueError("region_key_required")
        repo = self._require_repo()
        row = repo.get_world_region(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            region_key=region_key,
        )
        if row is None:
            return WorldRegionUnloadOut(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id.strip().lower(),
                region_key=region_key,
                unloaded=False,
            )
        row.loaded = False
        row.updated_at = datetime.utcnow()
        repo.save_world_region(row)
        return WorldRegionUnloadOut(
            workspace_id=row.workspace_id,
            realm_id=row.realm_id,
            region_key=row.region_key,
            unloaded=True,
        )

    def list_character_dictionary_entries(self, workspace_id: str) -> Sequence[CharacterDictionaryOut]:
        rows = self._require_repo().list_character_dictionary_entries(workspace_id=workspace_id)
        return [
            CharacterDictionaryOut(
                id=row.id,
                workspace_id=row.workspace_id,
                character_id=row.character_id,
                name=row.name,
                aliases=self._csv_to_list(row.aliases_csv),
                bio=row.bio,
                tags=self._csv_to_list(row.tags_csv),
                faction=row.faction,
                metadata=self._json_to_object_map(row.metadata_json),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_character_dictionary_entry(self, payload: CharacterDictionaryCreate) -> CharacterDictionaryOut:
        row = CharacterDictionaryEntry(
            workspace_id=payload.workspace_id,
            character_id=payload.character_id,
            name=payload.name,
            aliases_csv=self._list_to_csv(payload.aliases),
            bio=payload.bio,
            tags_csv=self._list_to_csv(payload.tags),
            faction=payload.faction,
            metadata_json=self._canonical_json(payload.metadata),
        )
        out = self._require_repo().create_character_dictionary_entry(row)
        return CharacterDictionaryOut(
            id=out.id,
            workspace_id=out.workspace_id,
            character_id=out.character_id,
            name=out.name,
            aliases=self._csv_to_list(out.aliases_csv),
            bio=out.bio,
            tags=self._csv_to_list(out.tags_csv),
            faction=out.faction,
            metadata=self._json_to_object_map(out.metadata_json),
            created_at=out.created_at,
        )

    def list_named_quests(self, workspace_id: str) -> Sequence[NamedQuestOut]:
        rows = self._require_repo().list_named_quests(workspace_id=workspace_id)
        return [
            NamedQuestOut(
                id=row.id,
                workspace_id=row.workspace_id,
                quest_id=row.quest_id,
                name=row.name,
                status=row.status,
                current_step=row.current_step,
                requirements=self._json_to_object_map(row.requirements_json),
                rewards=self._json_to_object_map(row.rewards_json),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_named_quest(self, payload: NamedQuestCreate) -> NamedQuestOut:
        row = NamedQuest(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            name=payload.name,
            status=payload.status,
            current_step=payload.current_step,
            requirements_json=self._canonical_json(payload.requirements),
            rewards_json=self._canonical_json(payload.rewards),
        )
        out = self._require_repo().create_named_quest(row)
        return NamedQuestOut(
            id=out.id,
            workspace_id=out.workspace_id,
            quest_id=out.quest_id,
            name=out.name,
            status=out.status,
            current_step=out.current_step,
            requirements=self._json_to_object_map(out.requirements_json),
            rewards=self._json_to_object_map(out.rewards_json),
            created_at=out.created_at,
        )

    def list_journal_entries(self, workspace_id: str, actor_id: str | None = None) -> Sequence[JournalEntryOut]:
        rows = self._require_repo().list_journal_entries(workspace_id=workspace_id, actor_id=actor_id)
        return [
            JournalEntryOut(
                id=row.id,
                workspace_id=row.workspace_id,
                actor_id=row.actor_id,
                entry_id=row.entry_id,
                title=row.title,
                body=row.body,
                kind=row.kind,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_journal_entry(self, payload: JournalEntryCreate) -> JournalEntryOut:
        row = JournalEntry(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            entry_id=payload.entry_id,
            title=payload.title,
            body=payload.body,
            kind=payload.kind,
        )
        out = self._require_repo().create_journal_entry(row)
        return JournalEntryOut(
            id=out.id,
            workspace_id=out.workspace_id,
            actor_id=out.actor_id,
            entry_id=out.entry_id,
            title=out.title,
            body=out.body,
            kind=out.kind,
            created_at=out.created_at,
        )

    def _to_layer_node_out(self, row: LayerNode) -> LayerNodeOut:
        return LayerNodeOut(
            id=row.id,
            workspace_id=row.workspace_id,
            layer_index=row.layer_index,
            node_key=row.node_key,
            payload=self._json_to_object_map(row.payload_json),
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def _to_layer_edge_out(self, row: LayerEdge) -> LayerEdgeOut:
        return LayerEdgeOut(
            id=row.id,
            workspace_id=row.workspace_id,
            from_node_id=row.from_node_id,
            to_node_id=row.to_node_id,
            edge_kind=row.edge_kind,
            metadata=self._json_to_object_map(row.metadata_json),
            created_at=row.created_at,
        )

    def _to_layer_event_out(self, row: LayerEvent) -> LayerEventOut:
        return LayerEventOut(
            id=row.id,
            workspace_id=row.workspace_id,
            event_kind=row.event_kind,
            actor_id=row.actor_id,
            node_id=row.node_id,
            edge_id=row.edge_id,
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def list_layer_nodes(self, workspace_id: str, layer_index: int | None = None) -> Sequence[LayerNodeOut]:
        rows = self._require_repo().list_layer_nodes(workspace_id=workspace_id, layer_index=layer_index)
        return [self._to_layer_node_out(row) for row in rows]

    def create_layer_node(
        self,
        *,
        payload: LayerNodeCreate,
        actor_id: str,
    ) -> LayerNodeOut:
        repo = self._require_repo()
        node_payload_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "layer_index": payload.layer_index,
                "node_key": payload.node_key,
                "payload": payload.payload,
            }
        )
        row = LayerNode(
            workspace_id=payload.workspace_id,
            layer_index=payload.layer_index,
            node_key=payload.node_key,
            payload_json=self._canonical_json(payload.payload),
            payload_hash=node_payload_hash,
        )
        saved = repo.create_layer_node(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="layer_node_created",
                actor_id=actor_id,
                node_id=saved.id,
                edge_id=None,
                payload_hash=node_payload_hash,
            )
        )
        return self._to_layer_node_out(saved)

    def list_layer_edges(self, workspace_id: str, node_id: str | None = None) -> Sequence[LayerEdgeOut]:
        rows = self._require_repo().list_layer_edges(workspace_id=workspace_id, node_id=node_id)
        return [self._to_layer_edge_out(row) for row in rows]

    def create_layer_edge(
        self,
        *,
        payload: LayerEdgeCreate,
        actor_id: str,
    ) -> LayerEdgeOut:
        repo = self._require_repo()
        from_node = repo.get_layer_node(payload.workspace_id, payload.from_node_id)
        to_node = repo.get_layer_node(payload.workspace_id, payload.to_node_id)
        if from_node is None or to_node is None:
            raise ValueError("layer_node_not_found")
        edge_payload_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "from_node_id": payload.from_node_id,
                "to_node_id": payload.to_node_id,
                "edge_kind": payload.edge_kind,
                "metadata": payload.metadata,
            }
        )
        row = LayerEdge(
            workspace_id=payload.workspace_id,
            from_node_id=payload.from_node_id,
            to_node_id=payload.to_node_id,
            edge_kind=payload.edge_kind,
            metadata_json=self._canonical_json(payload.metadata),
        )
        saved = repo.create_layer_edge(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="layer_edge_created",
                actor_id=actor_id,
                node_id=None,
                edge_id=saved.id,
                payload_hash=edge_payload_hash,
            )
        )
        return self._to_layer_edge_out(saved)

    def list_layer_events(self, workspace_id: str) -> Sequence[LayerEventOut]:
        rows = self._require_repo().list_layer_events(workspace_id=workspace_id)
        return [self._to_layer_event_out(row) for row in rows]

    def trace_layer_node(self, workspace_id: str, node_id: str) -> LayerTraceOut:
        repo = self._require_repo()
        node = repo.get_layer_node(workspace_id=workspace_id, node_id=node_id)
        if node is None:
            raise ValueError("layer_node_not_found")
        all_edges = repo.list_layer_edges(workspace_id=workspace_id, node_id=node_id)
        inbound: list[LayerEdgeOut] = []
        outbound: list[LayerEdgeOut] = []
        for edge in all_edges:
            edge_out = self._to_layer_edge_out(edge)
            if edge.to_node_id == node_id:
                inbound.append(edge_out)
            if edge.from_node_id == node_id:
                outbound.append(edge_out)
        return LayerTraceOut(
            node=self._to_layer_node_out(node),
            inbound=sorted(inbound, key=lambda item: item.id),
            outbound=sorted(outbound, key=lambda item: item.id),
        )

    def list_function_store_entries(self, workspace_id: str) -> Sequence[FunctionStoreOut]:
        rows = self._require_repo().list_function_store_entries(workspace_id=workspace_id)
        return [
            FunctionStoreOut(
                id=row.id,
                workspace_id=row.workspace_id,
                function_id=row.function_id,
                version=row.version,
                signature=row.signature,
                body=row.body,
                metadata=self._json_to_object_map(row.metadata_json),
                function_hash=row.function_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_function_store_entry(
        self,
        *,
        payload: FunctionStoreCreate,
        actor_id: str,
    ) -> FunctionStoreOut:
        repo = self._require_repo()
        function_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "function_id": payload.function_id,
                "version": payload.version,
                "signature": payload.signature,
                "body": payload.body,
                "metadata": payload.metadata,
            }
        )
        row = FunctionStoreEntry(
            workspace_id=payload.workspace_id,
            function_id=payload.function_id,
            version=payload.version,
            signature=payload.signature,
            body=payload.body,
            metadata_json=self._canonical_json(payload.metadata),
            function_hash=function_hash,
        )
        saved = repo.create_function_store_entry(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="function_store_entry_created",
                actor_id=actor_id,
                node_id=None,
                edge_id=None,
                payload_hash=function_hash,
            )
        )
        return FunctionStoreOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            function_id=saved.function_id,
            version=saved.version,
            signature=saved.signature,
            body=saved.body,
            metadata=self._json_to_object_map(saved.metadata_json),
            function_hash=saved.function_hash,
            created_at=saved.created_at,
        )

    @staticmethod
    def _derive_artisan_code(
        *,
        artisan_id: str,
        profile_name: str,
        profile_email: str,
        role: str,
        workshop_id: str,
    ) -> str:
        seed = f"{artisan_id}|{profile_name}|{profile_email}|{role}|{workshop_id}".encode("utf-8")
        digest = hashlib.sha256(seed).hexdigest().upper()[:12]
        return f"AID-{digest}"

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_access_status(row: ArtisanAccount) -> ArtisanAccessStatusOut:
        return ArtisanAccessStatusOut(
            artisan_id=row.artisan_id,
            role=row.role,
            workshop_id=row.workshop_id,
            profile_name=row.profile_name,
            profile_email=row.profile_email,
            artisan_access_verified=row.artisan_access_verified,
        )

    def issue_artisan_access_code(
        self,
        *,
        artisan_id: str,
        role: str,
        workshop_id: str,
        payload: ArtisanAccessIssueInput,
    ) -> ArtisanAccessIssueOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        code = self._derive_artisan_code(
            artisan_id=artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_code_hash = self._hash_code(code)
        row.artisan_access_verified = False
        saved = repo.save_artisan_account(row)
        return ArtisanAccessIssueOut(artisan_code=code, status=self._to_access_status(saved))

    def verify_artisan_access_code(
        self,
        *,
        artisan_id: str,
        role: str,
        workshop_id: str,
        payload: ArtisanAccessVerifyInput,
    ) -> ArtisanAccessStatusOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        expected_code = self._derive_artisan_code(
            artisan_id=artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_access_verified = payload.artisan_code == expected_code and row.artisan_code_hash == self._hash_code(payload.artisan_code)
        saved = repo.save_artisan_account(row)
        return self._to_access_status(saved)

    def artisan_access_status(self, *, artisan_id: str, role: str, workshop_id: str) -> ArtisanAccessStatusOut:
        repo = self._require_repo()
        existing = repo.get_artisan_account(artisan_id)
        if existing is None:
            row = repo.upsert_artisan_account(
                artisan_id=artisan_id,
                role=role,
                workshop_id=workshop_id,
                profile_name="",
                profile_email="",
            )
            return self._to_access_status(row)
        existing.role = role
        existing.workshop_id = workshop_id
        saved = repo.save_artisan_account(existing)
        return self._to_access_status(saved)

    def bootstrap_artisan_access(
        self,
        *,
        role: str,
        workshop_id: str,
        payload: ArtisanBootstrapInput,
    ) -> ArtisanAccessIssueOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=payload.artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        code = self._derive_artisan_code(
            artisan_id=payload.artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_code_hash = self._hash_code(code)
        row.artisan_access_verified = True
        saved = repo.save_artisan_account(row)
        return ArtisanAccessIssueOut(artisan_code=code, status=self._to_access_status(saved))

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
    RendererTablesInput,
    RendererTablesOut,
    GateEvaluateInput,
    GateEvaluateOut,
    GateRequirement,
    GateRequirementResult,
    GateOperator,
    RuntimeConsumeInput,
    RuntimeConsumeOut,
    RuntimeActionOut,
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
from .kernel_integration import KernelIntegrationService
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
    AssetManifest,
    Realm,
    Scene,
    WorldRegion,
)
from .repositories import AtelierRepository
from .validators import build_scene_graph_content_from_cobra, validate_cobra_content, validate_json_content, validate_scene_realm
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


class AtelierService:
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
        results: list[GameTickEventResult] = []
        updated_tables = tables
        for event in payload.events:
            updated_tables, result = self._apply_game_event(
                event=event,
                tables=updated_tables,
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                workshop_id=workshop_id,
            )
            results.append(result)
        clock = dict(updated_tables.clock)
        tick_before = self._int_from_table(clock.get("tick"), 0)
        clock["tick"] = tick_before + 1
        clock["dt_ms"] = max(0, int(payload.dt_ms))
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
        quantity = max(0, payload.quantity)
        base = max(1, payload.base_price_cents)
        scarcity_multiplier_bp = 10000 + payload.scarcity_bp
        spread_bp = max(0, payload.spread_bp)
        side_adjust_bp = spread_bp if payload.side.lower() == "buy" else -spread_bp
        effective_bp = max(1, scarcity_multiplier_bp + side_adjust_bp)
        unit_price = max(1, (base * effective_bp) // 10000)
        subtotal = unit_price * quantity
        result = MarketQuoteOut(
            actor_id=payload.actor_id,
            item_id=payload.item_id,
            side=payload.side.lower(),
            quantity=quantity,
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
        side = payload.side.lower()
        requested_qty = max(0, payload.quantity)
        liquidity = max(0, payload.available_liquidity)
        filled_qty = min(requested_qty, liquidity)
        unit_price = max(1, payload.unit_price_cents)
        subtotal = filled_qty * unit_price
        fee_bp = max(0, payload.fee_bp)
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
            item_id=payload.item_id,
            side=side,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
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
        return {"value": cast(object, value)}

    def consume_runtime_plan(
        self,
        *,
        payload: RuntimeConsumeInput,
        actor_id: str,
        workshop_id: str,
    ) -> RuntimeConsumeOut:
        results: list[RuntimeActionOut] = []
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
                    result = self.market_trade(
                        payload=MarketTradeInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
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
            "results": [item.model_dump() for item in results],
        }
        return RuntimeConsumeOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            applied_count=applied_count,
            failed_count=failed_count,
            results=results,
            hash=self._canonical_hash(hash_payload),
        )

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
        pressure = 0.0 if capacity <= 0 else float(loaded_count) / float(capacity)
        pressure_components = {
            "stream_occupancy": pressure,
            "demon_total": 0.0,
            "composite": pressure,
        }
        return WorldStreamStatusOut(
            workspace_id=workspace_id,
            realm_id=normalized_realm,
            loaded_count=loaded_count,
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

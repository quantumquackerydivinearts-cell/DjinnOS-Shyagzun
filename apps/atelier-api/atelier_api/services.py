from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

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
    BlacksmithForgeInput,
    BlacksmithForgeOut,
    CombatResolveInput,
    CombatResolveOut,
    MarketQuoteInput,
    MarketQuoteOut,
    MarketTradeInput,
    MarketTradeOut,
    GateEvaluateInput,
    GateEvaluateOut,
    GateRequirement,
    GateRequirementResult,
    GateOperator,
    DialogueEmitInput,
    DialogueEmitOut,
    VitriolApplyRulerInfluenceInput,
    VitriolApplyOut,
    VitriolClearExpiredInput,
    VitriolClearExpiredOut,
    VitriolComputeInput,
    VitriolComputeOut,
    VitriolModifier,
    SupplierCreate,
    SupplierOut,
)
from .kernel_integration import KernelIntegrationService
from .models import ArtisanAccount, Booking, CRMContact, Client, InventoryItem, Lead, Lesson, LearningModule, Order, Quote, Supplier
from .repositories import AtelierRepository
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

    def __init__(self, repo: AtelierRepository | None, kernel: KernelIntegrationService) -> None:
        self._repo = repo
        self._kernel = kernel

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
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.akinenwun_lookup(
            akinenwun=akinenwun,
            mode=mode,
            ingest=ingest,
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
        sorted_nodes = sorted(payload.nodes, key=lambda node: node.node_id)
        sorted_edges = sorted(payload.edges, key=lambda edge: (edge.from_node_id, edge.to_node_id, edge.relation))
        for node in sorted_nodes:
            raw = f"scene.node {payload.scene_id} {node.node_id} {node.kind} {node.x} {node.y}"
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "scene_id": payload.scene_id,
                "node_id": node.node_id,
                "metadata": dict(node.metadata),
            }
            self._kernel.place(raw=raw, context=context, actor_id=actor_id, workshop_id=workshop_id)
        for edge in sorted_edges:
            raw = f"scene.edge {payload.scene_id} {edge.from_node_id} {edge.to_node_id} {edge.relation}"
            context = {
                "workspace_id": payload.workspace_id,
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

    def apply_level_progress(
        self,
        *,
        payload: LevelApplyInput,
        actor_id: str,
        workshop_id: str,
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

    def forge_blacksmith(
        self,
        *,
        payload: BlacksmithForgeInput,
        actor_id: str,
        workshop_id: str,
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

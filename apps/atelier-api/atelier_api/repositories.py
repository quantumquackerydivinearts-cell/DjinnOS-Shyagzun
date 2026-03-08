from __future__ import annotations
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

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
    Realm,
    Scene,
    WorldRegion,
    AssetManifest,
    PlayerState,
    RuntimePlanRun,
    Quote,
    Supplier,
    GuildMessageEnvelopeRecord,
    DistributionRegistryRecord,
    GuildRegistryRecord,
    WandDamageAttestationRecord,
    WandKeyEpochRecord,
    WandRegistryRecord,
)


class AtelierRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ping(self) -> None:
        self._db.execute(text("SELECT 1"))

    def list_contacts(self, workspace_id: str) -> Sequence[CRMContact]:
        return self._db.scalars(select(CRMContact).where(CRMContact.workspace_id == workspace_id)).all()

    def create_contact(self, row: CRMContact) -> CRMContact:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_bookings(self, workspace_id: str) -> Sequence[Booking]:
        return self._db.scalars(select(Booking).where(Booking.workspace_id == workspace_id)).all()

    def create_booking(self, row: Booking) -> Booking:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_lessons(self, workspace_id: str) -> Sequence[Lesson]:
        return self._db.scalars(select(Lesson).where(Lesson.workspace_id == workspace_id)).all()

    def create_lesson(self, row: Lesson) -> Lesson:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_lesson_progress(self, workspace_id: str, actor_id: str) -> Sequence[LessonProgress]:
        return self._db.scalars(
            select(LessonProgress).where(
                LessonProgress.workspace_id == workspace_id,
                LessonProgress.actor_id == actor_id,
            )
        ).all()

    def get_lesson_progress(self, workspace_id: str, actor_id: str, lesson_id: str) -> LessonProgress | None:
        return self._db.scalar(
            select(LessonProgress).where(
                LessonProgress.workspace_id == workspace_id,
                LessonProgress.actor_id == actor_id,
                LessonProgress.lesson_id == lesson_id,
            )
        )

    def save_lesson_progress(self, row: LessonProgress) -> LessonProgress:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_modules(self, workspace_id: str) -> Sequence[LearningModule]:
        return self._db.scalars(select(LearningModule).where(LearningModule.workspace_id == workspace_id)).all()

    def create_module(self, row: LearningModule) -> LearningModule:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_leads(self, workspace_id: str) -> Sequence[Lead]:
        return self._db.scalars(select(Lead).where(Lead.workspace_id == workspace_id)).all()

    def create_lead(self, row: Lead) -> Lead:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_clients(self, workspace_id: str) -> Sequence[Client]:
        return self._db.scalars(select(Client).where(Client.workspace_id == workspace_id)).all()

    def create_client(self, row: Client) -> Client:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_quotes(self, workspace_id: str) -> Sequence[Quote]:
        return self._db.scalars(select(Quote).where(Quote.workspace_id == workspace_id)).all()

    def list_public_quotes(self, workspace_id: str) -> Sequence[Quote]:
        return self._db.scalars(
            select(Quote).where(
                Quote.workspace_id == workspace_id,
                Quote.is_public.is_(True),
            )
        ).all()

    def create_quote(self, row: Quote) -> Quote:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_orders(self, workspace_id: str) -> Sequence[Order]:
        return self._db.scalars(select(Order).where(Order.workspace_id == workspace_id)).all()

    def create_order(self, row: Order) -> Order:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_inventory_items(self, workspace_id: str) -> Sequence[InventoryItem]:
        return self._db.scalars(select(InventoryItem).where(InventoryItem.workspace_id == workspace_id)).all()

    def create_inventory_item(self, row: InventoryItem) -> InventoryItem:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def get_inventory_item(self, workspace_id: str, item_id: str) -> InventoryItem | None:
        return self._db.scalar(
            select(InventoryItem).where(
                InventoryItem.workspace_id == workspace_id,
                InventoryItem.id == item_id,
            )
        )

    def update_inventory_item(self, row: InventoryItem) -> InventoryItem:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_suppliers(self, workspace_id: str) -> Sequence[Supplier]:
        return self._db.scalars(select(Supplier).where(Supplier.workspace_id == workspace_id)).all()

    def create_supplier(self, row: Supplier) -> Supplier:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def get_artisan_account(self, artisan_id: str) -> ArtisanAccount | None:
        return self._db.scalar(select(ArtisanAccount).where(ArtisanAccount.artisan_id == artisan_id))

    def upsert_artisan_account(
        self,
        *,
        artisan_id: str,
        role: str,
        workshop_id: str,
        profile_name: str,
        profile_email: str,
    ) -> ArtisanAccount:
        row = self.get_artisan_account(artisan_id)
        if row is None:
            row = ArtisanAccount(
                artisan_id=artisan_id,
                role=role,
                workshop_id=workshop_id,
                profile_name=profile_name,
                profile_email=profile_email,
                artisan_code_hash="",
                artisan_access_verified=False,
            )
            self._db.add(row)
        else:
            row.role = role
            row.workshop_id = workshop_id
            row.profile_name = profile_name
            row.profile_email = profile_email
        self._db.commit()
        self._db.refresh(row)
        return row

    def save_artisan_account(self, row: ArtisanAccount) -> ArtisanAccount:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_character_dictionary_entries(self, workspace_id: str) -> Sequence[CharacterDictionaryEntry]:
        return self._db.scalars(
            select(CharacterDictionaryEntry).where(CharacterDictionaryEntry.workspace_id == workspace_id)
        ).all()

    def create_character_dictionary_entry(self, row: CharacterDictionaryEntry) -> CharacterDictionaryEntry:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_named_quests(self, workspace_id: str) -> Sequence[NamedQuest]:
        return self._db.scalars(select(NamedQuest).where(NamedQuest.workspace_id == workspace_id)).all()

    def create_named_quest(self, row: NamedQuest) -> NamedQuest:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_journal_entries(self, workspace_id: str, actor_id: str | None = None) -> Sequence[JournalEntry]:
        stmt = select(JournalEntry).where(JournalEntry.workspace_id == workspace_id)
        if actor_id is not None:
            stmt = stmt.where(JournalEntry.actor_id == actor_id)
        return self._db.scalars(stmt).all()

    def create_journal_entry(self, row: JournalEntry) -> JournalEntry:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_realms(self) -> Sequence[Realm]:
        return self._db.scalars(select(Realm).order_by(Realm.slug)).all()

    def get_realm_by_slug(self, slug: str) -> Realm | None:
        return self._db.scalar(select(Realm).where(Realm.slug == slug))

    def list_scenes(self, workspace_id: str, realm_id: str | None = None) -> Sequence[Scene]:
        stmt = select(Scene).where(Scene.workspace_id == workspace_id)
        if realm_id is not None:
            stmt = stmt.where(Scene.realm_id == realm_id)
        return self._db.scalars(stmt).all()

    def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> Scene | None:
        return self._db.scalar(
            select(Scene).where(
                Scene.workspace_id == workspace_id,
                Scene.realm_id == realm_id,
                Scene.scene_id == scene_id,
            )
        )

    def create_scene(self, row: Scene) -> Scene:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def save_scene(self, row: Scene) -> Scene:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[WorldRegion]:
        stmt = select(WorldRegion).where(WorldRegion.workspace_id == workspace_id)
        if realm_id is not None:
            stmt = stmt.where(WorldRegion.realm_id == realm_id)
        return self._db.scalars(stmt).all()

    def get_world_region(self, workspace_id: str, realm_id: str, region_key: str) -> WorldRegion | None:
        return self._db.scalar(
            select(WorldRegion).where(
                WorldRegion.workspace_id == workspace_id,
                WorldRegion.realm_id == realm_id,
                WorldRegion.region_key == region_key,
            )
        )

    def create_world_region(self, row: WorldRegion) -> WorldRegion:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def save_world_region(self, row: WorldRegion) -> WorldRegion:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_layer_nodes(self, workspace_id: str, layer_index: int | None = None) -> Sequence[LayerNode]:
        stmt = select(LayerNode).where(LayerNode.workspace_id == workspace_id)
        if layer_index is not None:
            stmt = stmt.where(LayerNode.layer_index == layer_index)
        return self._db.scalars(stmt).all()

    def get_layer_node(self, workspace_id: str, node_id: str) -> LayerNode | None:
        return self._db.scalar(
            select(LayerNode).where(
                LayerNode.workspace_id == workspace_id,
                LayerNode.id == node_id,
            )
        )

    def create_layer_node(self, row: LayerNode) -> LayerNode:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_layer_edges(self, workspace_id: str, node_id: str | None = None) -> Sequence[LayerEdge]:
        stmt = select(LayerEdge).where(LayerEdge.workspace_id == workspace_id)
        if node_id is not None:
            stmt = stmt.where((LayerEdge.from_node_id == node_id) | (LayerEdge.to_node_id == node_id))
        return self._db.scalars(stmt).all()

    def create_layer_edge(self, row: LayerEdge) -> LayerEdge:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_layer_events(self, workspace_id: str) -> Sequence[LayerEvent]:
        return self._db.scalars(select(LayerEvent).where(LayerEvent.workspace_id == workspace_id)).all()

    def create_layer_event(self, row: LayerEvent) -> LayerEvent:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_function_store_entries(self, workspace_id: str) -> Sequence[FunctionStoreEntry]:
        return self._db.scalars(select(FunctionStoreEntry).where(FunctionStoreEntry.workspace_id == workspace_id)).all()

    def create_function_store_entry(self, row: FunctionStoreEntry) -> FunctionStoreEntry:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
        return self._db.scalar(
            select(PlayerState).where(
                PlayerState.workspace_id == workspace_id,
                PlayerState.actor_id == actor_id,
            )
        )

    def save_player_state(self, row: PlayerState) -> PlayerState:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def create_runtime_plan_run(self, row: RuntimePlanRun) -> RuntimePlanRun:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_runtime_plan_runs(self, workspace_id: str, actor_id: str, plan_id: str) -> Sequence[RuntimePlanRun]:
        return self._db.scalars(
            select(RuntimePlanRun).where(
                RuntimePlanRun.workspace_id == workspace_id,
                RuntimePlanRun.actor_id == actor_id,
                RuntimePlanRun.plan_id == plan_id,
            ).order_by(RuntimePlanRun.created_at.desc(), RuntimePlanRun.id.desc())
        ).all()

    def list_runtime_plan_runs_for_actor(
        self,
        workspace_id: str,
        actor_id: str,
        plan_id: str | None = None,
    ) -> Sequence[RuntimePlanRun]:
        stmt = select(RuntimePlanRun).where(
            RuntimePlanRun.workspace_id == workspace_id,
            RuntimePlanRun.actor_id == actor_id,
        )
        if plan_id is not None and plan_id.strip() != "":
            stmt = stmt.where(RuntimePlanRun.plan_id == plan_id.strip())
        stmt = stmt.order_by(RuntimePlanRun.created_at.desc(), RuntimePlanRun.id.desc())
        return self._db.scalars(stmt).all()

    def get_latest_runtime_plan_run(self, workspace_id: str, actor_id: str, plan_id: str) -> RuntimePlanRun | None:
        return self._db.scalar(
            select(RuntimePlanRun).where(
                RuntimePlanRun.workspace_id == workspace_id,
                RuntimePlanRun.actor_id == actor_id,
                RuntimePlanRun.plan_id == plan_id,
            ).order_by(RuntimePlanRun.created_at.desc(), RuntimePlanRun.id.desc())
        )

    def list_asset_manifests(self, workspace_id: str) -> Sequence[AssetManifest]:
        return self._db.scalars(select(AssetManifest).where(AssetManifest.workspace_id == workspace_id)).all()

    def create_asset_manifest(self, row: AssetManifest) -> AssetManifest:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def create_guild_message_envelope_record(self, row: GuildMessageEnvelopeRecord) -> GuildMessageEnvelopeRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_guild_message_envelope_records(
        self,
        *,
        guild_id: str | None = None,
        channel_id: str | None = None,
        thread_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[GuildMessageEnvelopeRecord]:
        stmt = select(GuildMessageEnvelopeRecord)
        if guild_id is not None:
            stmt = stmt.where(GuildMessageEnvelopeRecord.guild_id == guild_id)
        if channel_id is not None:
            stmt = stmt.where(GuildMessageEnvelopeRecord.channel_id == channel_id)
        if thread_id is not None:
            stmt = stmt.where(GuildMessageEnvelopeRecord.thread_id == thread_id)
        stmt = stmt.order_by(GuildMessageEnvelopeRecord.recorded_at.desc(), GuildMessageEnvelopeRecord.id.desc()).limit(
            max(1, min(int(limit), 250))
        )
        return self._db.scalars(stmt).all()

    def get_guild_message_envelope_record(self, message_id: str) -> GuildMessageEnvelopeRecord | None:
        return self._db.scalar(
            select(GuildMessageEnvelopeRecord).where(GuildMessageEnvelopeRecord.message_id == message_id)
        )

    def save_guild_message_envelope_record(self, row: GuildMessageEnvelopeRecord) -> GuildMessageEnvelopeRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def create_wand_damage_attestation_record(
        self,
        row: WandDamageAttestationRecord,
    ) -> WandDamageAttestationRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_wand_damage_attestation_records(
        self,
        *,
        wand_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[WandDamageAttestationRecord]:
        stmt = select(WandDamageAttestationRecord)
        if wand_id is not None:
            stmt = stmt.where(WandDamageAttestationRecord.wand_id == wand_id)
        stmt = stmt.order_by(WandDamageAttestationRecord.recorded_at.desc(), WandDamageAttestationRecord.id.desc()).limit(
            max(1, min(int(limit), 250))
        )
        return self._db.scalars(stmt).all()

    def create_wand_key_epoch_record(self, row: WandKeyEpochRecord) -> WandKeyEpochRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_wand_key_epoch_records(
        self,
        *,
        wand_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[WandKeyEpochRecord]:
        stmt = select(WandKeyEpochRecord)
        if wand_id is not None:
            stmt = stmt.where(WandKeyEpochRecord.wand_id == wand_id)
        stmt = stmt.order_by(WandKeyEpochRecord.recorded_at.desc(), WandKeyEpochRecord.id.desc()).limit(
            max(1, min(int(limit), 250))
        )
        return self._db.scalars(stmt).all()

    def get_wand_registry_record(self, wand_id: str) -> WandRegistryRecord | None:
        return self._db.scalar(select(WandRegistryRecord).where(WandRegistryRecord.wand_id == wand_id))

    def save_wand_registry_record(self, row: WandRegistryRecord) -> WandRegistryRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_wand_registry_records(self, limit: int = 50) -> Sequence[WandRegistryRecord]:
        stmt = (
            select(WandRegistryRecord)
            .order_by(WandRegistryRecord.updated_at.desc(), WandRegistryRecord.id.desc())
            .limit(max(1, min(int(limit), 250)))
        )
        return self._db.scalars(stmt).all()

    def get_guild_registry_record(self, guild_id: str) -> GuildRegistryRecord | None:
        return self._db.scalar(select(GuildRegistryRecord).where(GuildRegistryRecord.guild_id == guild_id))

    def save_guild_registry_record(self, row: GuildRegistryRecord) -> GuildRegistryRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_guild_registry_records(self, limit: int = 50) -> Sequence[GuildRegistryRecord]:
        stmt = (
            select(GuildRegistryRecord)
            .order_by(GuildRegistryRecord.updated_at.desc(), GuildRegistryRecord.id.desc())
            .limit(max(1, min(int(limit), 250)))
        )
        return self._db.scalars(stmt).all()

    def get_distribution_registry_record(self, distribution_id: str) -> DistributionRegistryRecord | None:
        return self._db.scalar(
            select(DistributionRegistryRecord).where(DistributionRegistryRecord.distribution_id == distribution_id)
        )

    def save_distribution_registry_record(self, row: DistributionRegistryRecord) -> DistributionRegistryRecord:
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_distribution_registry_records(self, limit: int = 50) -> Sequence[DistributionRegistryRecord]:
        stmt = (
            select(DistributionRegistryRecord)
            .order_by(DistributionRegistryRecord.updated_at.desc(), DistributionRegistryRecord.id.desc())
            .limit(max(1, min(int(limit), 250)))
        )
        return self._db.scalars(stmt).all()

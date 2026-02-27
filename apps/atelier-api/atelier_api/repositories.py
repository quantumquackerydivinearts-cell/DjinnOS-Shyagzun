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
    LearningModule,
    NamedQuest,
    Order,
    Quote,
    Supplier,
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

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import ArtisanAccount, Booking, CRMContact, Client, InventoryItem, Lead, Lesson, LearningModule, Order, Quote, Supplier


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

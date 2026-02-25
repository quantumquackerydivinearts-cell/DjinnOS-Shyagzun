from __future__ import annotations

import hashlib
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
    SupplierCreate,
    SupplierOut,
)
from .kernel_integration import KernelIntegrationService
from .models import ArtisanAccount, Booking, CRMContact, Client, InventoryItem, Lead, Lesson, LearningModule, Order, Quote, Supplier
from .repositories import AtelierRepository
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


class AtelierService:
    def __init__(self, repo: AtelierRepository | None, kernel: KernelIntegrationService) -> None:
        self._repo = repo
        self._kernel = kernel

    def _require_repo(self) -> AtelierRepository:
        if self._repo is None:
            raise RuntimeError("repository_unavailable")
        return self._repo

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

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


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

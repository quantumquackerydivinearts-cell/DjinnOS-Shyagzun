from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ShopItemPublic(BaseModel):
    id: str
    artisan_id: str
    title: str
    description: str
    section_id: str
    item_type: str
    price_cents: int
    currency: str
    thumbnail_url: Optional[str]
    tags: list[str]
    is_featured: bool
    inventory_count: Optional[int]

    model_config = {"from_attributes": True}


class ShopItemCreate(BaseModel):
    title: str
    description: str
    section_id: str
    item_type: str                        # digital | service | physical
    price_cents: int = Field(ge=0)
    currency: str = "usd"
    tags: list[str] = Field(default_factory=list)
    inventory_count: Optional[int] = None  # None = unlimited


class ShopItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[list[str]] = None
    inventory_count: Optional[int] = None


class CheckoutRequest(BaseModel):
    item_id: str
    quantity: int = Field(default=1, ge=1)
    buyer_email: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str

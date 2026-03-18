from __future__ import annotations

# PAYMENT PROCESSOR: Currently Stripe Connect.
# QQDA intends to replace with a native payment processor.
# All Stripe calls are isolated to: _create_stripe_product(),
# _create_checkout_session(), _get_connect_balance()
# Replacing the processor means replacing these three functions only.
# The rest of the endpoint logic is processor-agnostic.

import json
import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import stripe
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import decode_auth_token
from .business_schemas import (
    PublicShopLeadRequest as ShopLeadRequest,
    PublicShopQuoteRequest as ShopQuoteRequest,
    PublicShopCheckoutRequest as ShopCheckoutRequest,
)
from .core.config import load_settings
from .db import get_db
from .models import (
    CRMContact,
    GuildArtisanProfile,
    Lead,
    Quote,
    ShopItem,
    Workspace,
)
from .shop_schemas import (
    CheckoutRequest,
    CheckoutResponse,
    ShopItemCreate,
    ShopItemPublic,
    ShopItemUpdate,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stripe initialisation
# ---------------------------------------------------------------------------

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Platform fee in basis points — e.g. 500 = 5 %
_PLATFORM_FEE_BPS: int = int(os.getenv("STRIPE_PLATFORM_FEE_BPS", "500"))

# Verify env on startup — logged at import time, does not crash.
if not os.getenv("STRIPE_SECRET_KEY"):
    logger.warning("STRIPE_SECRET_KEY is not set — Stripe payouts will fail at runtime.")
if not os.getenv("STRIPE_PLATFORM_FEE_BPS"):
    logger.warning(
        "STRIPE_PLATFORM_FEE_BPS is not set — defaulting to 500 bps (5 %%). "
        "Set this in the environment to configure the platform fee."
    )

# Map section_id -> Stripe Price ID (legacy section-level pricing — kept for backward compat)
_STRIPE_PRICE_MAP: dict[str, str] = {
    "consultations":    os.getenv("STRIPE_PRICE_CONSULTATIONS", ""),
    "licenses":         os.getenv("STRIPE_PRICE_LICENSES", ""),
    "catalog":          os.getenv("STRIPE_PRICE_CATALOG", ""),
    "custom-orders":    os.getenv("STRIPE_PRICE_CUSTOM_ORDERS", ""),
    "digital":          os.getenv("STRIPE_PRICE_DIGITAL", ""),
    "land-assessments": os.getenv("STRIPE_PRICE_LAND_ASSESSMENTS", ""),
}

_GUILD_MEMBER_SECTION_FREE: set[str] = {"land-assessments"}
_SHOP_WORKSPACE_ID = os.getenv("SHOP_WORKSPACE_ID", "")

# Accepted section IDs for artisan marketplace items
_VALID_SECTION_IDS: set[str] = {
    "digital-products",
    "custom-orders",
    "physical-goods",
    "licenses",
    "consultations",
    "land-assessments",
}

# Storage root for digital file uploads
_STORAGE_ROOT = os.getenv("SHOP_STORAGE_ROOT", "storage/shop")


# ---------------------------------------------------------------------------
# Auth dependency (artisan endpoints)
# ---------------------------------------------------------------------------

def _require_artisan_auth(authorization: Optional[str] = Header(default=None)) -> str:
    """
    Returns the authenticated artisan's actor_id.
    Expects: Authorization: Bearer <atelier-token>
    """
    if not authorization or not authorization.strip():
        raise HTTPException(status_code=401, detail="missing_authorization")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_token")
    settings = load_settings()
    try:
        claims = decode_auth_token(token=token, secret=settings.auth_token_secret)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_auth_token:{exc}") from exc
    return claims.actor_id


# ---------------------------------------------------------------------------
# Guild membership guard
# ---------------------------------------------------------------------------

def require_guild_membership(artisan_id: str, db: Session) -> GuildArtisanProfile:
    """
    Guild membership is the gate for all artisan sell operations.
    Raises 403 if the artisan does not have a steward-approved guild profile.
    """
    profile = db.query(GuildArtisanProfile).filter(
        GuildArtisanProfile.id == artisan_id,
        GuildArtisanProfile.steward_approved == True,
    ).first()
    if not profile:
        raise HTTPException(status_code=403, detail="Guild membership required to sell")
    return profile


# ---------------------------------------------------------------------------
# Stripe isolated functions — swap these three to change payment processor
# ---------------------------------------------------------------------------

def _create_stripe_product(item: ShopItem, artisan: GuildArtisanProfile) -> tuple[str, str]:
    """
    Creates a Stripe Product and Price for the given shop item.
    Returns (stripe_product_id, stripe_price_id).
    """
    product = stripe.Product.create(
        name=item.title,
        description=item.description or item.title,
        metadata={
            "artisan_id": artisan.id,
            "section_id": item.section_id,
            "item_type": item.item_type,
            "qqda_item_id": item.id,
        },
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=item.price_cents,
        currency=item.currency.lower(),
        metadata={"qqda_item_id": item.id},
    )
    return product.id, price.id


def _create_checkout_session(
    item: ShopItem,
    artisan: GuildArtisanProfile,
    req: CheckoutRequest,
) -> tuple[str, str]:
    """
    Creates a Stripe Connect Checkout Session.
    Platform fee is deducted from the payment; remainder routes to the artisan's
    connected account via transfer_data.
    Returns (session_id, checkout_url).
    """
    if not artisan.stripe_account_id:
        raise HTTPException(
            status_code=422,
            detail="artisan_stripe_account_not_configured — artisan must complete Stripe Connect onboarding",
        )

    platform_fee_cents = math.ceil(item.price_cents * req.quantity * _PLATFORM_FEE_BPS / 10_000)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": item.stripe_price_id,
                "quantity": req.quantity,
            }
        ],
        mode="payment",
        customer_email=req.buyer_email,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
        payment_intent_data={
            "application_fee_amount": platform_fee_cents,
            "transfer_data": {"destination": artisan.stripe_account_id},
        },
        metadata={
            "qqda_item_id": item.id,
            "artisan_id": artisan.id,
            "section_id": item.section_id,
            "source": "qqda_artisan_marketplace",
        },
    )
    return session.id, session.url


def _get_connect_balance(artisan: GuildArtisanProfile) -> dict[str, Any]:
    """
    Fetches the artisan's Stripe Connect account balance for the revenue summary.
    Returns a dict with available/pending amounts, or an error structure.
    """
    if not artisan.stripe_account_id:
        return {"error": "stripe_account_not_configured"}
    try:
        balance = stripe.Balance.retrieve(stripe_account=artisan.stripe_account_id)
        return {
            "available": [
                {"amount": a.amount, "currency": a.currency}
                for a in balance.available
            ],
            "pending": [
                {"amount": p.amount, "currency": p.currency}
                for p in balance.pending
            ],
        }
    except stripe.StripeError as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid4())


def _resolve_workspace(db: Session) -> Workspace:
    if _SHOP_WORKSPACE_ID:
        ws = db.query(Workspace).filter(Workspace.id == _SHOP_WORKSPACE_ID).first()
        if ws:
            return ws
    ws = db.query(Workspace).order_by(Workspace.created_at).first()
    if ws is None:
        raise HTTPException(status_code=503, detail="shop_workspace_not_configured")
    return ws


def _find_or_create_contact(
    db: Session,
    workspace_id: str,
    full_name: str,
    email: Optional[str],
    phone: Optional[str],
) -> CRMContact:
    if email:
        existing = (
            db.query(CRMContact)
            .filter(
                CRMContact.workspace_id == workspace_id,
                CRMContact.email == email,
            )
            .first()
        )
        if existing:
            return existing
    contact = CRMContact(
        workspace_id=workspace_id,
        full_name=full_name,
        email=email,
        phone=phone,
    )
    db.add(contact)
    db.flush()
    return contact


def _is_guild_member(token: Optional[str], section_id: str) -> bool:
    if section_id not in _GUILD_MEMBER_SECTION_FREE:
        return False
    if not token:
        return False
    guild_secret = os.getenv("GUILD_MEMBER_SECRET", "")
    if not guild_secret:
        return False
    return token.strip() == guild_secret.strip()


def _json_response(payload: object, status_code: int = 200) -> Response:
    body = json.dumps(payload, ensure_ascii=False, default=str)
    return Response(content=body, status_code=status_code, media_type="application/json")


def _item_to_public(item: ShopItem) -> dict:
    try:
        tags = json.loads(item.tags_json) if item.tags_json else []
    except (json.JSONDecodeError, TypeError):
        tags = []
    return ShopItemPublic(
        id=item.id,
        artisan_id=item.artisan_id,
        title=item.title,
        description=item.description or "",
        section_id=item.section_id,
        item_type=item.item_type or "",
        price_cents=item.price_cents or 0,
        currency=item.currency or "usd",
        thumbnail_url=item.thumbnail_url,
        tags=tags,
        is_featured=item.is_featured,
        inventory_count=item.inventory_count,
    ).model_dump()


def _item_to_full(item: ShopItem) -> dict:
    """Full representation for the artisan's own management view."""
    base = _item_to_public(item)
    base.update(
        {
            "is_active": item.is_active,
            "stripe_product_id": item.stripe_product_id,
            "stripe_price_id": item.stripe_price_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
    )
    return base


# ---------------------------------------------------------------------------
# POST /public/shop/leads
# ---------------------------------------------------------------------------

def public_shop_leads(
    req: ShopLeadRequest,
    db: Session = Depends(get_db),
) -> Response:
    workspace = _resolve_workspace(db)
    contact = _find_or_create_contact(
        db=db,
        workspace_id=workspace.id,
        full_name=req.full_name,
        email=req.email,
        phone=req.phone,
    )
    lead = Lead(
        workspace_id=workspace.id,
        full_name=req.full_name,
        email=req.email,
        phone=req.phone,
        details=req.details,
        status="new",
        source=f"shop:{req.section_id}",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _json_response(
        {
            "ok": True,
            "lead_id": lead.id,
            "contact_id": contact.id,
            "section_id": req.section_id,
            "status": lead.status,
        },
        status_code=201,
    )


# ---------------------------------------------------------------------------
# POST /public/shop/quotes
# ---------------------------------------------------------------------------

def public_shop_quotes(
    req: ShopQuoteRequest,
    db: Session = Depends(get_db),
) -> Response:
    workspace = _resolve_workspace(db)
    contact = _find_or_create_contact(
        db=db,
        workspace_id=workspace.id,
        full_name=req.full_name,
        email=req.email,
        phone=req.phone,
    )
    lead = Lead(
        workspace_id=workspace.id,
        full_name=req.full_name,
        email=req.email,
        phone=req.phone,
        details=req.details,
        status="new",
        source=f"shop:{req.section_id}",
    )
    db.add(lead)
    db.flush()
    quote = Quote(
        workspace_id=workspace.id,
        lead_id=lead.id,
        title=req.title or f"Custom order from {req.full_name}",
        amount_cents=0,
        currency="USD",
        status="draft",
        is_public=False,
        notes=req.details,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    db.refresh(lead)
    return _json_response(
        {
            "ok": True,
            "quote_id": quote.id,
            "lead_id": lead.id,
            "contact_id": contact.id,
            "section_id": req.section_id,
            "status": quote.status,
        },
        status_code=201,
    )


# ---------------------------------------------------------------------------
# GET /public/shop/items
# ---------------------------------------------------------------------------

def public_shop_items(
    workspace_id: str,
    section_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """
    Returns active ShopItems for a given artisan (workspace_id = GuildArtisanProfile.id)
    and section. Pass workspace_id="all" to return all active items for the section
    across all artisans.
    """
    q = db.query(ShopItem).filter(
        ShopItem.section_id == section_id,
        ShopItem.is_active == True,
    )
    if workspace_id and workspace_id != "all":
        # workspace_id in public API = GuildArtisanProfile.id = ShopItem.artisan_id
        q = q.filter(ShopItem.artisan_id == workspace_id)

    items = q.order_by(ShopItem.is_featured.desc(), ShopItem.created_at).all()
    return _json_response({"items": [_item_to_public(i) for i in items], "count": len(items)})


# ---------------------------------------------------------------------------
# POST /public/shop/checkout-session
# ---------------------------------------------------------------------------

def public_shop_checkout_session(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
) -> Response:
    """
    Creates a Stripe Connect Checkout Session for a specific ShopItem.
    Platform fee is taken via application_fee_amount; remainder routes to the
    artisan's connected Stripe account.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="stripe_not_configured")

    item = db.query(ShopItem).filter(ShopItem.id == req.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")
    if not item.is_active:
        raise HTTPException(status_code=410, detail="item_no_longer_available")

    # Inventory check for physical goods
    if item.inventory_count is not None and item.inventory_count < req.quantity:
        raise HTTPException(
            status_code=409,
            detail=f"insufficient_inventory:available={item.inventory_count}",
        )

    # Verify artisan still has an active Guild profile
    artisan = db.query(GuildArtisanProfile).filter(
        GuildArtisanProfile.id == item.artisan_id,
        GuildArtisanProfile.steward_approved == True,
    ).first()
    if not artisan:
        raise HTTPException(status_code=422, detail="artisan_guild_membership_inactive")

    if not item.stripe_price_id:
        raise HTTPException(status_code=422, detail="item_stripe_price_not_configured")

    try:
        session_id, checkout_url = _create_checkout_session(item, artisan, req)
    except stripe.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"stripe_error:{exc.user_message or str(exc)}",
        ) from exc

    # Decrement inventory for physical goods on session creation.
    # Note: this is optimistic — a more robust flow would decrement on webhook
    # confirmation (payment_intent.succeeded). Kept simple per spec.
    if item.inventory_count is not None:
        item.inventory_count = max(0, item.inventory_count - req.quantity)
        item.updated_at = datetime.utcnow()
        db.commit()

    return _json_response(
        CheckoutResponse(session_id=session_id, checkout_url=checkout_url).model_dump()
    )


# ---------------------------------------------------------------------------
# POST /artisan/shop/items
# ---------------------------------------------------------------------------

def artisan_create_shop_item(
    title: str = Form(...),
    description: str = Form(...),
    section_id: str = Form(...),
    item_type: str = Form(...),
    price_cents: int = Form(...),
    currency: str = Form("usd"),
    tags_json: str = Form("[]"),
    inventory_count: Optional[int] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    artisan_id: str = Depends(_require_artisan_auth),
    db: Session = Depends(get_db),
) -> Response:
    """
    Create a new shop item for the authenticated artisan.
    Requires active Guild membership (steward_approved GuildArtisanProfile).
    For digital items: accepts file upload, stored under SHOP_STORAGE_ROOT.
    Creates corresponding Stripe Product + Price via Connect.
    """
    artisan = require_guild_membership(artisan_id, db)

    if section_id not in _VALID_SECTION_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_section_id — must be one of: {', '.join(sorted(_VALID_SECTION_IDS))}",
        )
    if item_type not in {"digital", "service", "physical"}:
        raise HTTPException(status_code=400, detail="invalid_item_type — must be: digital, service, or physical")

    try:
        tags = json.loads(tags_json)
        if not isinstance(tags, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        tags = []

    item_id = _uuid()

    # Handle thumbnail upload
    thumbnail_url: Optional[str] = None
    if thumbnail:
        thumb_ext = (thumbnail.filename or "").rsplit(".", 1)[-1].lower() or "bin"
        thumb_rel = f"{artisan_id}/thumbnails/{item_id}.{thumb_ext}"
        thumb_abs = os.path.join(_STORAGE_ROOT, thumb_rel)
        os.makedirs(os.path.dirname(thumb_abs), exist_ok=True)
        with open(thumb_abs, "wb") as f_out:
            f_out.write(thumbnail.file.read())
        thumbnail_url = thumb_rel

    # Handle digital file upload
    file_path: Optional[str] = None
    if item_type == "digital" and file:
        file_ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "bin"
        file_rel = f"{artisan_id}/files/{item_id}.{file_ext}"
        file_abs = os.path.join(_STORAGE_ROOT, file_rel)
        os.makedirs(os.path.dirname(file_abs), exist_ok=True)
        with open(file_abs, "wb") as f_out:
            f_out.write(file.file.read())
        file_path = file_rel

    # Resolve workspace for the item record
    workspace = _resolve_workspace(db)

    item = ShopItem(
        id=item_id,
        workspace_id=workspace.id,
        artisan_id=artisan.id,
        artisan_profile_name=artisan.display_name,
        artisan_profile_email="",
        section_id=section_id,
        title=title,
        description=description,
        summary=description[:200] if description else "",
        item_type=item_type,
        price_cents=price_cents,
        currency=currency.lower(),
        tags_json=json.dumps(tags),
        thumbnail_url=thumbnail_url,
        file_path=file_path,
        inventory_count=inventory_count,
        is_active=True,
        is_featured=False,
    )
    db.add(item)
    db.flush()  # get item.id before Stripe call

    # Create Stripe Product + Price
    if stripe.api_key:
        try:
            product_id, price_id = _create_stripe_product(item, artisan)
            item.stripe_product_id = product_id
            item.stripe_price_id = price_id
        except stripe.StripeError as exc:
            logger.warning("Stripe product creation failed for item %s: %s", item.id, exc)
            # Do not block item creation — steward can fix Stripe linkage later

    db.commit()
    db.refresh(item)

    return _json_response(_item_to_full(item), status_code=201)


# ---------------------------------------------------------------------------
# PATCH /artisan/shop/items/{item_id}
# ---------------------------------------------------------------------------

def artisan_update_shop_item(
    item_id: str,
    payload: ShopItemUpdate,
    artisan_id: str = Depends(_require_artisan_auth),
    db: Session = Depends(get_db),
) -> Response:
    """
    Update metadata, price, or status for an item owned by the authenticated artisan.
    If price_cents changes: creates a new Stripe Price and archives the old one.
    """
    item = db.query(ShopItem).filter(ShopItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    # Ownership check — artisan can only edit own items
    artisan = require_guild_membership(artisan_id, db)
    if item.artisan_id != artisan.id:
        raise HTTPException(status_code=403, detail="not_item_owner")

    price_changed = (
        payload.price_cents is not None
        and payload.price_cents != item.price_cents
    )

    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
        item.summary = payload.description[:200]
    if payload.price_cents is not None:
        item.price_cents = payload.price_cents
    if payload.is_active is not None:
        item.is_active = payload.is_active
    if payload.is_featured is not None:
        item.is_featured = payload.is_featured
    if payload.tags is not None:
        item.tags_json = json.dumps(payload.tags)
    if payload.inventory_count is not None:
        item.inventory_count = payload.inventory_count

    # If price changed, create new Stripe Price and archive old one
    if price_changed and stripe.api_key and item.stripe_product_id:
        try:
            new_price = stripe.Price.create(
                product=item.stripe_product_id,
                unit_amount=item.price_cents,
                currency=item.currency.lower(),
                metadata={"qqda_item_id": item.id},
            )
            if item.stripe_price_id:
                stripe.Price.modify(item.stripe_price_id, active=False)
            item.stripe_price_id = new_price.id
        except stripe.StripeError as exc:
            logger.warning("Stripe price update failed for item %s: %s", item.id, exc)

    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return _json_response(_item_to_full(item))


# ---------------------------------------------------------------------------
# DELETE /artisan/shop/items/{item_id}
# ---------------------------------------------------------------------------

def artisan_deactivate_shop_item(
    item_id: str,
    artisan_id: str = Depends(_require_artisan_auth),
    db: Session = Depends(get_db),
) -> Response:
    """
    Soft delete: sets is_active = False. Does not delete the Stripe product.
    """
    item = db.query(ShopItem).filter(ShopItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    artisan = require_guild_membership(artisan_id, db)
    if item.artisan_id != artisan.id:
        raise HTTPException(status_code=403, detail="not_item_owner")

    item.is_active = False
    item.updated_at = datetime.utcnow()
    db.commit()

    return _json_response({"ok": True, "item_id": item_id, "is_active": False})


# ---------------------------------------------------------------------------
# GET /artisan/shop/items
# ---------------------------------------------------------------------------

def artisan_list_shop_items(
    artisan_id: str = Depends(_require_artisan_auth),
    db: Session = Depends(get_db),
) -> Response:
    """
    Returns all items (active and inactive) for the authenticated artisan.
    Full management view — includes Stripe IDs and internal fields.
    """
    artisan = require_guild_membership(artisan_id, db)

    items = (
        db.query(ShopItem)
        .filter(ShopItem.artisan_id == artisan.id)
        .order_by(ShopItem.created_at.desc())
        .all()
    )

    balance = {}
    if stripe.api_key:
        balance = _get_connect_balance(artisan)

    return _json_response(
        {
            "items": [_item_to_full(i) for i in items],
            "count": len(items),
            "stripe_balance": balance,
        }
    )


# ---------------------------------------------------------------------------
# Registration helper — call this from main.py app setup
# ---------------------------------------------------------------------------

def register_shop_routes(app: FastAPI) -> None:
    """
    Call this in the API service's main.py after creating the FastAPI app:

        from .shop_endpoints import register_shop_routes
        register_shop_routes(app)
    """
    # Public endpoints
    app.post("/public/shop/leads")(public_shop_leads)
    app.post("/public/shop/quotes")(public_shop_quotes)
    app.get("/public/shop/items")(public_shop_items)
    app.post("/public/shop/checkout-session")(public_shop_checkout_session)

    # Artisan (authenticated) endpoints
    app.post("/artisan/shop/items")(artisan_create_shop_item)
    app.patch("/artisan/shop/items/{item_id}")(artisan_update_shop_item)
    app.delete("/artisan/shop/items/{item_id}")(artisan_deactivate_shop_item)
    app.get("/artisan/shop/items")(artisan_list_shop_items)

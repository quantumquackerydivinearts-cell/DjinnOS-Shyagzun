from __future__ import annotations

# PAYMENT PROCESSOR: Currently Stripe Connect (artisan marketplace routes).
# QQDA intends to replace with a native payment processor.
# Stripe calls in this file are isolated to: _create_stripe_product(),
# _get_connect_balance()
# The section-level checkout-session lives in main.py and has its own swap surface.
#
# NOTE: Public shop routes (leads, quotes, items, checkout-session) are
# owned by main.py's @app decorator routes and must NOT be registered here.
# register_shop_routes() only registers the new artisan marketplace endpoints.

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import stripe
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .auth import decode_auth_token
from .core.config import load_settings
from .db import get_db
from .models import GuildArtisanProfile, ShopItem, Workspace
from .shop_schemas import ShopItemPublic, ShopItemUpdate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stripe initialisation
# ---------------------------------------------------------------------------

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

_SHOP_WORKSPACE_ID = os.getenv("SHOP_WORKSPACE_ID", "")
_STORAGE_ROOT = os.getenv("SHOP_STORAGE_ROOT", "storage/shop")

_VALID_SECTION_IDS: set[str] = {
    "digital-products",
    "custom-orders",
    "physical-goods",
    "licenses",
    "consultations",
    "land-assessments",
}

if not os.getenv("STRIPE_SECRET_KEY"):
    logger.warning("STRIPE_SECRET_KEY is not set — Stripe payouts will fail at runtime.")


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def _require_artisan_auth(authorization: Optional[str] = Header(default=None)) -> str:
    """Returns the authenticated artisan's actor_id from Bearer token."""
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



def _get_connect_balance(artisan: GuildArtisanProfile) -> dict[str, Any]:
    """
    Fetches the artisan's Stripe Connect account balance.
    Returns a dict with available/pending amounts, or an error structure.
    """
    if not artisan.stripe_account_id:
        return {"error": "stripe_account_not_configured"}
    try:
        balance = stripe.Balance.retrieve(stripe_account=artisan.stripe_account_id)
        return {
            "available": [{"amount": a.amount, "currency": a.currency} for a in balance.available],
            "pending": [{"amount": p.amount, "currency": p.currency} for p in balance.pending],
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
    base.update({
        "is_active": item.is_active,
        "stripe_product_id": item.stripe_product_id,
        "stripe_price_id": item.stripe_price_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    })
    return base


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
    Create a new shop item. Requires active Guild membership.
    For digital items: accepts file upload stored under SHOP_STORAGE_ROOT.
    Creates a Stripe Product + Price via Connect.
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

    thumbnail_url: Optional[str] = None
    if thumbnail:
        thumb_ext = (thumbnail.filename or "").rsplit(".", 1)[-1].lower() or "bin"
        thumb_rel = f"{artisan_id}/thumbnails/{item_id}.{thumb_ext}"
        thumb_abs = os.path.join(_STORAGE_ROOT, thumb_rel)
        os.makedirs(os.path.dirname(thumb_abs), exist_ok=True)
        with open(thumb_abs, "wb") as f_out:
            f_out.write(thumbnail.file.read())
        thumbnail_url = thumb_rel

    file_path: Optional[str] = None
    if item_type == "digital" and file:
        file_ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "bin"
        file_rel = f"{artisan_id}/files/{item_id}.{file_ext}"
        file_abs = os.path.join(_STORAGE_ROOT, file_rel)
        os.makedirs(os.path.dirname(file_abs), exist_ok=True)
        with open(file_abs, "wb") as f_out:
            f_out.write(file.file.read())
        file_path = file_rel

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
    db.flush()

    if stripe.api_key:
        try:
            product_id, price_id = _create_stripe_product(item, artisan)
            item.stripe_product_id = product_id
            item.stripe_price_id = price_id
        except stripe.StripeError as exc:
            logger.warning("Stripe product creation failed for item %s: %s", item.id, exc)

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
    """Update metadata, price, or status. If price changes: archives old Stripe Price."""
    item = db.query(ShopItem).filter(ShopItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")

    artisan = require_guild_membership(artisan_id, db)
    if item.artisan_id != artisan.id:
        raise HTTPException(status_code=403, detail="not_item_owner")

    price_changed = payload.price_cents is not None and payload.price_cents != item.price_cents

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
    """Soft delete: sets is_active = False. Does not delete the Stripe product."""
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
    All items (active and inactive) for the authenticated artisan.
    Full management view — includes Stripe IDs, is_active, timestamps.
    """
    artisan = require_guild_membership(artisan_id, db)

    items = (
        db.query(ShopItem)
        .filter(ShopItem.artisan_id == artisan.id)
        .order_by(ShopItem.created_at.desc())
        .all()
    )

    balance = _get_connect_balance(artisan) if stripe.api_key else {}

    return _json_response({
        "items": [_item_to_full(i) for i in items],
        "count": len(items),
        "stripe_balance": balance,
    })


# ---------------------------------------------------------------------------
# Registration — artisan marketplace routes only
# ---------------------------------------------------------------------------

def register_shop_routes(app: FastAPI) -> None:
    """
    Registers only the new artisan marketplace endpoints.
    Public shop routes (leads, quotes, items, checkout-session) are handled
    by main.py's @app decorator routes — do not register them here.
    """
    app.post("/artisan/shop/items")(artisan_create_shop_item)
    app.patch("/artisan/shop/items/{item_id}")(artisan_update_shop_item)
    app.delete("/artisan/shop/items/{item_id}")(artisan_deactivate_shop_item)
    app.get("/artisan/shop/items")(artisan_list_shop_items)

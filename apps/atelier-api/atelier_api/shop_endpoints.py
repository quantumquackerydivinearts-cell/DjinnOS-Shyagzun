from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import stripe
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .business_schemas import (
    PublicShopLeadRequest as ShopLeadRequest,
    PublicShopQuoteRequest as ShopQuoteRequest,
    PublicShopCheckoutRequest as ShopCheckoutRequest,
)
from .db import get_db
from .models import (
    CRMContact,
    Lead,
    Quote,
    ShopItem,
    Workspace,
)

# ---------------------------------------------------------------------------
# Stripe initialisation
# ---------------------------------------------------------------------------

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Map section_id -> Stripe Price ID (set these in Render environment vars)
_STRIPE_PRICE_MAP: dict[str, str] = {
    "consultations":    os.getenv("STRIPE_PRICE_CONSULTATIONS", ""),
    "licenses":         os.getenv("STRIPE_PRICE_LICENSES", ""),
    "catalog":          os.getenv("STRIPE_PRICE_CATALOG", ""),
    "custom-orders":    os.getenv("STRIPE_PRICE_CUSTOM_ORDERS", ""),
    "digital":          os.getenv("STRIPE_PRICE_DIGITAL", ""),
    "land-assessments": os.getenv("STRIPE_PRICE_LAND_ASSESSMENTS", ""),
}

# Guild members get free land assessments — set this in Render env
_GUILD_MEMBER_SECTION_FREE: set[str] = {"land-assessments"}

# Default workspace for public shop submissions (set SHOP_WORKSPACE_ID in Render)
_SHOP_WORKSPACE_ID = os.getenv("SHOP_WORKSPACE_ID", "")


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_workspace(db: Session) -> Workspace:
    """
    Resolve the shop workspace. Uses SHOP_WORKSPACE_ID env var.
    Falls back to the first workspace in the DB if not set (single-tenant installs).
    Raises 503 if no workspace exists yet.
    """
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
    """
    Look up an existing CRMContact by email (if provided), or create a new one.
    This ensures shop submissions don't create duplicate contacts for returning
    customers.
    """
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
    db.flush()  # get the id without committing yet
    return contact


def _is_guild_member(token: Optional[str], section_id: str) -> bool:
    """
    Guild member verification. Currently checks against a static env token
    (GUILD_MEMBER_SECRET). This will be replaced with full guild registry
    verification once the distribution network is live.
    """
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
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# POST /public/shop/leads
# ---------------------------------------------------------------------------

def public_shop_leads(
    req: ShopLeadRequest,
    db: Session = Depends(get_db),
) -> Response:
    """
    Accepts a lead submission from the shop front-end (kernel_service.py
    calls this via _submit_shop_payload). Creates a CRMContact if needed,
    then creates a Lead record with source="shop" so it appears in the
    Atelier CRM leads panel.
    """
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
    """
    Accepts a custom-order quote request. Creates a CRMContact and Lead,
    then creates a Quote record in draft status with amount_cents=0 (the
    steward will fill in the actual amount inside the Atelier before sending
    to the client).
    """
    workspace = _resolve_workspace(db)

    contact = _find_or_create_contact(
        db=db,
        workspace_id=workspace.id,
        full_name=req.full_name,
        email=req.email,
        phone=req.phone,
    )

    # Create a lead so it surfaces in the CRM as well as the quotes panel
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
        amount_cents=0,          # steward sets the real amount in Atelier
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
    Returns visible, steward-approved ShopItems for a given workspace and
    section. Called by kernel_service._fetch_shop_items to populate the
    section detail pages.
    """
    items = (
        db.query(ShopItem)
        .filter(
            ShopItem.workspace_id == workspace_id,
            ShopItem.section_id == section_id,
            ShopItem.visible == True,
            ShopItem.steward_approved == True,
        )
        .order_by(ShopItem.created_at)
        .all()
    )

    result = []
    for item in items:
        try:
            tags = json.loads(item.tags_json)
        except (json.JSONDecodeError, TypeError):
            tags = []
        result.append(
            {
                "id": item.id,
                "section_id": item.section_id,
                "title": item.title,
                "summary": item.summary,
                "price_label": item.price_label,
                "tags": tags,
                "link_url": item.link_url,
                "artisan_profile_name": item.artisan_profile_name,
            }
        )

    return _json_response({"items": result, "count": len(result)})


# ---------------------------------------------------------------------------
# POST /public/shop/checkout-session
# ---------------------------------------------------------------------------

def public_shop_checkout_session(
    req: ShopCheckoutRequest,
    db: Session = Depends(get_db),
) -> Response:
    """
    Creates a Stripe Checkout Session for the given section.

    Guild member logic:
    - Land assessments are free for guild members (verified by token).
      A $0 Stripe session is created using a free price, or we skip Stripe
      entirely and return a booking confirmation URL.
    - All other sections require a configured Stripe Price ID.

    Returns {"url": "https://checkout.stripe.com/..."} so the kernel
    service can redirect the browser directly.
    """
    section_id = req.section_id.strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id_required")

    shop_url = os.getenv("PUBLIC_SHOP_URL", "").rstrip("/")
    atelier_url = os.getenv("PUBLIC_ATELIER_URL", "").rstrip("/")

    success_url = f"{shop_url}/shop?submitted=paid&section={section_id}"
    cancel_url = f"{shop_url}/{section_id}"

    # --- Guild member free booking path ---
    if _is_guild_member(req.guild_member_token, section_id):
        # Skip Stripe entirely — send them to the Atelier booking flow
        booking_url = (
            os.getenv("SHOP_LINK_LAND_ASSESSMENTS", "").strip()
            or f"{atelier_url}/"
        )
        return _json_response({"url": booking_url, "free": True, "guild_member": True})

    # --- Paid path via Stripe ---
    price_id = _STRIPE_PRICE_MAP.get(section_id, "").strip()
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"no_stripe_price_configured_for_section:{section_id}",
        )

    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="stripe_not_configured")

    # Determine payment mode: licenses use subscription, everything else is
    # a one-time payment. Override with STRIPE_MODE_<SECTION> env var if needed.
    mode_override = os.getenv(
        f"STRIPE_MODE_{section_id.replace('-', '_').upper()}", ""
    ).strip()
    mode = mode_override or ("subscription" if section_id == "licenses" else "payment")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": max(1, req.quantity),
                }
            ],
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "section_id": section_id,
                "source": "phoenix_ams_crm_shop",
            },
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"stripe_error:{exc.user_message or str(exc)}") from exc

    return _json_response({"url": session.url, "free": False, "session_id": session.id})


# ---------------------------------------------------------------------------
# Registration helper — call this from your main API app setup
# ---------------------------------------------------------------------------

def register_shop_routes(app: FastAPI) -> None:
    """
    Call this in your API service's main.py or wherever you build the FastAPI
    app, after creating the app instance:

        from .shop_endpoints import register_shop_routes
        register_shop_routes(app)
    """
    app.post("/public/shop/leads")(public_shop_leads)
    app.post("/public/shop/quotes")(public_shop_quotes)
    app.get("/public/shop/items")(public_shop_items)
    app.post("/public/shop/checkout-session")(public_shop_checkout_session)
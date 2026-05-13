"""
import_router.py — Bulk CSV import endpoints for the Atelier.

POST /v1/import/contacts  — upsert CRMContact on (workspace_id, email)
POST /v1/import/leads     — upsert Lead on (workspace_id, email)
POST /v1/import/clients   — upsert Client on (workspace_id, email)

The frontend parses the CSV, maps columns to canonical names, and POSTs:
    { "rows": [ { "full_name": "...", "email": "...", ... }, ... ] }

Every row is processed independently. Upsert: existing record matched by
email is updated; no email or no match creates a new record. Per-row errors
are collected and returned without aborting the remaining rows.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from .db import get_db
from .models import CRMContact, Client, Lead, Workspace
from .business_schemas import ImportResult, ImportRowError

router = APIRouter()


# ── Request body ──────────────────────────────────────────────────────────────

class ImportPayload(BaseModel):
    rows: list[dict[str, Any]]


# ── Workspace resolution (mirrors _workspace_id_dep without circular import) ──

def _ws(
    x_workspace_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    if not x_workspace_id:
        raise HTTPException(400, "X-Workspace-Id header required")
    ws = db.get(Workspace, x_workspace_id)
    if ws is None:
        raise HTTPException(404, "workspace_not_found")
    return x_workspace_id


# ── Helpers ───────────────────────────────────────────────────────────────────

def _s(val: Any, max_len: int | None = None) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    return s[:max_len] if max_len and len(s) > max_len else s


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.post("/import/contacts", response_model=ImportResult)
def import_contacts(
    payload:      ImportPayload,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> ImportResult:
    inserted = updated = 0
    errors: list[ImportRowError] = []

    for idx, raw in enumerate(payload.rows, start=1):
        full_name = _s(raw.get("full_name"), 200)
        if not full_name:
            errors.append(ImportRowError(row=idx, reason="'full_name' is required", raw=raw))
            continue

        email   = _s(raw.get("email"),   320)
        phone   = _s(raw.get("phone"),   40)
        address = _s(raw.get("address"))
        website = _s(raw.get("website"), 500)
        notes   = _s(raw.get("notes"))  or ""

        try:
            existing = (
                db.scalar(select(CRMContact).where(
                    CRMContact.workspace_id == workspace_id,
                    CRMContact.email == email,
                )) if email else None
            )
            if existing:
                existing.full_name = full_name
                existing.phone   = phone   or existing.phone
                existing.address = address or existing.address
                existing.website = website or existing.website
                existing.notes   = notes   or existing.notes
                updated += 1
            else:
                db.add(CRMContact(
                    workspace_id=workspace_id,
                    full_name=full_name, email=email, phone=phone,
                    address=address, website=website, notes=notes,
                ))
                inserted += 1
            db.flush()
        except Exception as exc:
            db.rollback()
            errors.append(ImportRowError(row=idx, reason=str(exc), raw=raw))

    db.commit()
    return ImportResult(entity="contacts", inserted=inserted, updated=updated, errors=errors)


# ── Leads ─────────────────────────────────────────────────────────────────────

@router.post("/import/leads", response_model=ImportResult)
def import_leads(
    payload:      ImportPayload,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> ImportResult:
    VALID_STATUSES = {"new", "contacted", "qualified", "proposal", "converted", "lost"}
    inserted = updated = 0
    errors: list[ImportRowError] = []

    for idx, raw in enumerate(payload.rows, start=1):
        full_name = _s(raw.get("full_name"), 200)
        if not full_name:
            errors.append(ImportRowError(row=idx, reason="'full_name' is required", raw=raw))
            continue

        email  = _s(raw.get("email"),  320)
        phone  = _s(raw.get("phone"),  40)
        source = _s(raw.get("source"), 60)  or "import"
        details = _s(raw.get("details") or raw.get("notes")) or ""
        raw_status = (_s(raw.get("status")) or "new").lower()
        status = raw_status if raw_status in VALID_STATUSES else "new"

        try:
            existing = (
                db.scalar(select(Lead).where(
                    Lead.workspace_id == workspace_id,
                    Lead.email == email,
                )) if email else None
            )
            if existing:
                existing.full_name = full_name
                existing.phone   = phone   or existing.phone
                existing.source  = source  or existing.source
                existing.details = details or existing.details
                existing.status  = status
                updated += 1
            else:
                db.add(Lead(
                    workspace_id=workspace_id,
                    full_name=full_name, email=email, phone=phone,
                    source=source, status=status, details=details,
                ))
                inserted += 1
            db.flush()
        except Exception as exc:
            db.rollback()
            errors.append(ImportRowError(row=idx, reason=str(exc), raw=raw))

    db.commit()
    return ImportResult(entity="leads", inserted=inserted, updated=updated, errors=errors)


# ── Clients ───────────────────────────────────────────────────────────────────

@router.post("/import/clients", response_model=ImportResult)
def import_clients(
    payload:      ImportPayload,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> ImportResult:
    inserted = updated = 0
    errors: list[ImportRowError] = []

    for idx, raw in enumerate(payload.rows, start=1):
        full_name = _s(raw.get("full_name"), 200)
        if not full_name:
            errors.append(ImportRowError(row=idx, reason="'full_name' is required", raw=raw))
            continue

        email  = _s(raw.get("email"),  320)
        phone  = _s(raw.get("phone"),  40)
        status = _s(raw.get("status"), 40) or "active"

        try:
            existing = (
                db.scalar(select(Client).where(
                    Client.workspace_id == workspace_id,
                    Client.email == email,
                )) if email else None
            )
            if existing:
                existing.full_name = full_name
                existing.phone  = phone  or existing.phone
                existing.status = status
                updated += 1
            else:
                db.add(Client(
                    workspace_id=workspace_id,
                    full_name=full_name, email=email, phone=phone, status=status,
                ))
                inserted += 1
            db.flush()
        except Exception as exc:
            db.rollback()
            errors.append(ImportRowError(row=idx, reason=str(exc), raw=raw))

    db.commit()
    return ImportResult(entity="clients", inserted=inserted, updated=updated, errors=errors)

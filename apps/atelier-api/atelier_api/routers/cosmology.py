"""
Cosmology Governance Router
============================
Endpoints for cosmology ownership, contributor membership, and the
Steward approval pipeline for content submissions.

Two-tier model
--------------
  KLGS (slug="klgs")  — kernel_anchored=True, steward=alexi (0000_0451).
                        Any content touching this cosmology requires Steward
                        approval before it becomes canonical.

  Custom cosmologies  — created by any Artisan; they become that cosmology's
                        Steward automatically. Self-sovereign; no external
                        approval gate.

Endpoints
---------
  GET    /v1/cosmologies                              — list all
  POST   /v1/cosmologies                              — create (Artisan+)
  GET    /v1/cosmologies/{slug}                       — detail
  POST   /v1/cosmologies/{slug}/members               — invite contributor (Steward only)
  GET    /v1/cosmologies/{slug}/submissions            — list submissions
  POST   /v1/cosmologies/{slug}/submissions            — submit content
  PATCH  /v1/cosmologies/{slug}/submissions/{sub_id}  — approve / reject (Steward only)
  DELETE /v1/cosmologies/{slug}/submissions/{sub_id}  — withdraw (contributor only)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import AuthTokenClaims, decode_auth_token
from ..core.config import load_settings
from ..db import get_db
from ..models import Cosmology, CosmologyMembership, CosmologySubmission

router = APIRouter(prefix="/v1/cosmologies", tags=["cosmology"])

_KLGS_STEWARD = "alexi"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _artisan_id(
    db: Session,
    claims: Optional[AuthTokenClaims],
    x_artisan_id: Optional[str] = None,
) -> str:
    """Resolve caller's artisan_id from JWT claims or fallback header."""
    if claims is not None:
        return claims.actor_id
    if x_artisan_id and x_artisan_id.strip():
        return x_artisan_id.strip()
    raise HTTPException(status_code=401, detail="missing_artisan_identity")


def _require_steward(cosmology: Cosmology, caller: str) -> None:
    if cosmology.steward_artisan_id != caller:
        raise HTTPException(
            status_code=403,
            detail="steward_required — only the cosmology Steward may perform this action",
        )


def _get_cosmology(slug: str, db: Session) -> Cosmology:
    c = db.query(Cosmology).filter(Cosmology.slug == slug).first()
    if c is None:
        raise HTTPException(status_code=404, detail=f"cosmology '{slug}' not found")
    return c


# ── Claims dependency (optional JWT) ─────────────────────────────────────────

from fastapi import Header as _Header

def _optional_claims(
    authorization: Optional[str] = _Header(default=None),
) -> Optional[AuthTokenClaims]:
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        settings = load_settings()
        return decode_auth_token(token=token, secret=settings.auth_token_secret)
    except Exception:
        return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class CosmologyOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    steward_artisan_id: str
    open_contribution: bool
    kernel_anchored: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CosmologyCreate(BaseModel):
    slug: str
    name: str
    description: str = ""
    open_contribution: bool = False


class MemberInvite(BaseModel):
    artisan_id: str
    role: str = "contributor"   # contributor | moderator


class SubmissionCreate(BaseModel):
    content_type: str           # zone | npc | quest | item | dialogue | sprite | shader | other
    content_label: str = ""
    content_data: dict[str, Any] = {}


class SubmissionReview(BaseModel):
    status: str                 # approved | rejected
    steward_note: str = ""


class SubmissionOut(BaseModel):
    id: str
    cosmology_id: str
    contributor_id: str
    content_type: str
    content_label: str
    status: str
    kernel_valid: bool
    steward_note: Optional[str]
    submitted_at: datetime
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── List cosmologies ──────────────────────────────────────────────────────────

@router.get("", response_model=list[CosmologyOut])
def list_cosmologies(db: Session = Depends(get_db)) -> list[CosmologyOut]:
    return db.query(Cosmology).order_by(Cosmology.created_at).all()


# ── Create cosmology ──────────────────────────────────────────────────────────

@router.post("", response_model=CosmologyOut, status_code=201)
def create_cosmology(
    body: CosmologyCreate,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> CosmologyOut:
    caller = _artisan_id(db, claims, x_artisan_id)

    if db.query(Cosmology).filter(Cosmology.slug == body.slug).first():
        raise HTTPException(status_code=409, detail=f"slug '{body.slug}' already taken")

    # KLGS slug is kernel-anchored and cannot be re-registered
    if body.slug == "klgs":
        raise HTTPException(status_code=403, detail="klgs_slug_reserved")

    c = Cosmology(
        id=f"cosmology-{body.slug}-{str(uuid4())[:8]}",
        slug=body.slug,
        name=body.name,
        description=body.description,
        steward_artisan_id=caller,
        open_contribution=body.open_contribution,
        kernel_anchored=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ── Get cosmology ─────────────────────────────────────────────────────────────

@router.get("/{slug}", response_model=CosmologyOut)
def get_cosmology(slug: str, db: Session = Depends(get_db)) -> CosmologyOut:
    return _get_cosmology(slug, db)


# ── Invite contributor ────────────────────────────────────────────────────────

@router.post("/{slug}/members", status_code=201)
def invite_member(
    slug: str,
    body: MemberInvite,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> dict:
    caller = _artisan_id(db, claims, x_artisan_id)
    cosmology = _get_cosmology(slug, db)
    _require_steward(cosmology, caller)

    if body.role not in ("contributor", "moderator"):
        raise HTTPException(status_code=400, detail="role must be contributor or moderator")

    existing = (
        db.query(CosmologyMembership)
        .filter(
            CosmologyMembership.cosmology_id == cosmology.id,
            CosmologyMembership.artisan_id == body.artisan_id,
        )
        .first()
    )
    if existing:
        existing.role = body.role
        db.commit()
        return {"status": "updated", "artisan_id": body.artisan_id, "role": body.role}

    m = CosmologyMembership(
        cosmology_id=cosmology.id,
        artisan_id=body.artisan_id,
        role=body.role,
        invited_by=caller,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.commit()
    return {"status": "invited", "artisan_id": body.artisan_id, "role": body.role}


# ── List submissions ──────────────────────────────────────────────────────────

@router.get("/{slug}/submissions", response_model=list[SubmissionOut])
def list_submissions(
    slug: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> list[SubmissionOut]:
    caller = _artisan_id(db, claims, x_artisan_id)
    cosmology = _get_cosmology(slug, db)

    q = db.query(CosmologySubmission).filter(
        CosmologySubmission.cosmology_id == cosmology.id
    )

    # Steward sees all; contributors see only their own
    if cosmology.steward_artisan_id != caller:
        q = q.filter(CosmologySubmission.contributor_id == caller)

    if status:
        q = q.filter(CosmologySubmission.status == status)

    return q.order_by(CosmologySubmission.submitted_at.desc()).all()


# ── Submit content ────────────────────────────────────────────────────────────

@router.post("/{slug}/submissions", response_model=SubmissionOut, status_code=201)
def submit_content(
    slug: str,
    body: SubmissionCreate,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> SubmissionOut:
    caller = _artisan_id(db, claims, x_artisan_id)
    cosmology = _get_cosmology(slug, db)

    # For non-open cosmologies, caller must be a member or the Steward
    if not cosmology.open_contribution and cosmology.steward_artisan_id != caller:
        member = (
            db.query(CosmologyMembership)
            .filter(
                CosmologyMembership.cosmology_id == cosmology.id,
                CosmologyMembership.artisan_id == caller,
            )
            .first()
        )
        if member is None:
            raise HTTPException(
                status_code=403,
                detail="not_a_member — this cosmology requires an invitation to contribute",
            )

    valid_types = {"zone", "npc", "quest", "item", "dialogue", "sprite", "shader", "other"}
    if body.content_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"content_type must be one of {sorted(valid_types)}")

    # Steward submitting to their own cosmology is auto-approved
    is_own = cosmology.steward_artisan_id == caller
    sub = CosmologySubmission(
        cosmology_id=cosmology.id,
        contributor_id=caller,
        content_type=body.content_type,
        content_label=body.content_label,
        content_data=json.dumps(body.content_data),
        status="approved" if is_own else "pending",
        kernel_valid=False,
        submitted_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc) if is_own else None,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ── Review submission (Steward only) ─────────────────────────────────────────

@router.patch("/{slug}/submissions/{sub_id}", response_model=SubmissionOut)
def review_submission(
    slug: str,
    sub_id: str,
    body: SubmissionReview,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> SubmissionOut:
    caller = _artisan_id(db, claims, x_artisan_id)
    cosmology = _get_cosmology(slug, db)
    _require_steward(cosmology, caller)

    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")

    sub = (
        db.query(CosmologySubmission)
        .filter(
            CosmologySubmission.id == sub_id,
            CosmologySubmission.cosmology_id == cosmology.id,
        )
        .first()
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if sub.status not in ("pending",):
        raise HTTPException(status_code=409, detail=f"submission is already '{sub.status}'")

    sub.status       = body.status
    sub.steward_note = body.steward_note or None
    sub.reviewed_at  = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sub)
    return sub


# ── Withdraw submission (contributor only) ────────────────────────────────────

@router.delete("/{slug}/submissions/{sub_id}", status_code=200)
def withdraw_submission(
    slug: str,
    sub_id: str,
    db: Session = Depends(get_db),
    claims: Optional[AuthTokenClaims] = Depends(_optional_claims),
    x_artisan_id: Optional[str] = _Header(default=None),
) -> dict:
    caller = _artisan_id(db, claims, x_artisan_id)
    cosmology = _get_cosmology(slug, db)

    sub = (
        db.query(CosmologySubmission)
        .filter(
            CosmologySubmission.id == sub_id,
            CosmologySubmission.cosmology_id == cosmology.id,
        )
        .first()
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if sub.contributor_id != caller:
        raise HTTPException(status_code=403, detail="can only withdraw your own submissions")
    if sub.status == "approved":
        raise HTTPException(status_code=409, detail="cannot withdraw an approved submission")

    sub.status = "withdrawn"
    db.commit()
    return {"status": "withdrawn", "id": sub_id}
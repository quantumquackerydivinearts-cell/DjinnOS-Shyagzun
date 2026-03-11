"""
guild_endpoints.py
Public Guild Hall API — no authentication required.
All endpoints return only opted-in, steward-approved profiles.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from .db import get_db
from .models import GuildArtisanProfile

router = APIRouter(prefix="/public/guild", tags=["guild"])


# ── Response schemas ──────────────────────────────────────────────────────────

class ArtisanProfilePublic(BaseModel):
    id: str
    display_name: str
    bio: str
    portfolio_url: str
    avatar_url: str
    region: str
    divisions: list[str]
    trades: list[str]
    guild_rank: str
    member_since: str  # year only — privacy preserving

    model_config = {"from_attributes": True}


class ArtisanListResponse(BaseModel):
    total: int
    artisans: list[ArtisanProfilePublic]


class RegionListResponse(BaseModel):
    regions: list[str]


class TradeListResponse(BaseModel):
    trades: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_public(profile: GuildArtisanProfile) -> ArtisanProfilePublic:
    return ArtisanProfilePublic(
        id=profile.id,
        display_name=profile.display_name,
        bio=profile.bio,
        portfolio_url=profile.portfolio_url if profile.show_portfolio else "",
        avatar_url=profile.avatar_url,
        region=profile.region if profile.show_region else "",
        divisions=[d.strip() for d in profile.divisions.split(",") if d.strip()],
        trades=[t.strip() for t in profile.trades.split(",") if t.strip()] if profile.show_trades else [],
        guild_rank=profile.guild_rank,
        member_since=str(profile.created_at.year) if profile.created_at else "",
    )


def _base_query(db: Session):
    """Only return public, steward-approved profiles."""
    return db.query(GuildArtisanProfile).filter(
        GuildArtisanProfile.is_public == True,
        GuildArtisanProfile.steward_approved == True,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/artisans", response_model=ArtisanListResponse)
def list_artisans(
    region: Optional[str] = Query(None, description="Filter by region (partial match)"),
    division: Optional[str] = Query(None, description="Filter by division: sulphur, mercury, or salt"),
    trade: Optional[str] = Query(None, description="Filter by trade tag (partial match)"),
    rank: Optional[str] = Query(None, description="Filter by guild rank"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = _base_query(db)

    if region:
        q = q.filter(GuildArtisanProfile.region.ilike(f"%{region}%"))
    if division:
        q = q.filter(GuildArtisanProfile.divisions.ilike(f"%{division}%"))
    if trade:
        q = q.filter(GuildArtisanProfile.trades.ilike(f"%{trade}%"))
    if rank:
        q = q.filter(GuildArtisanProfile.guild_rank == rank)

    total = q.count()
    profiles = q.order_by(GuildArtisanProfile.display_name).offset(offset).limit(limit).all()

    return ArtisanListResponse(
        total=total,
        artisans=[_to_public(p) for p in profiles],
    )


@router.get("/artisans/{profile_id}", response_model=ArtisanProfilePublic)
def get_artisan(
    profile_id: str,
    db: Session = Depends(get_db),
):
    profile = _base_query(db).filter(GuildArtisanProfile.id == profile_id).first()
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Artisan not found")
    return _to_public(profile)


@router.get("/regions", response_model=RegionListResponse)
def list_regions(db: Session = Depends(get_db)):
    """Return all unique regions represented in public profiles."""
    profiles = _base_query(db).filter(
        GuildArtisanProfile.show_region == True,
        GuildArtisanProfile.region != "",
    ).with_entities(GuildArtisanProfile.region).all()

    # Extract unique non-empty regions, sorted
    seen = set()
    regions = []
    for (region,) in profiles:
        for part in [r.strip() for r in region.split(",") if r.strip()]:
            if part not in seen:
                seen.add(part)
                regions.append(part)

    return RegionListResponse(regions=sorted(regions))


@router.get("/trades", response_model=TradeListResponse)
def list_trades(db: Session = Depends(get_db)):
    """Return all unique trade tags represented in public profiles."""
    profiles = _base_query(db).filter(
        GuildArtisanProfile.show_trades == True,
        GuildArtisanProfile.trades != "",
    ).with_entities(GuildArtisanProfile.trades).all()

    seen = set()
    trades = []
    for (trade_str,) in profiles:
        for tag in [t.strip() for t in trade_str.split(",") if t.strip()]:
            if tag not in seen:
                seen.add(tag)
                trades.append(tag)

    return TradeListResponse(trades=sorted(trades))


def register_guild_routes(app):
    app.include_router(router)
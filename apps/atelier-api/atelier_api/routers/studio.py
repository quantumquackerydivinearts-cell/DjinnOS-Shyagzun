"""
Guild / Studio / Project router
================================
Endpoints for studio profiles, projects, publication, and guild listings.

Routes
------
  POST   /v1/studio/profile                        — create or replace studio profile
  PATCH  /v1/studio/profile                        — partial update
  GET    /v1/studio/profile                        — own profile
  POST   /v1/projects                              — create project
  GET    /v1/projects                              — list workspace projects
  GET    /v1/projects/{project_id}                 — project detail
  PATCH  /v1/projects/{project_id}                 — update project metadata
  POST   /v1/projects/{project_id}/publish         — publish (attaches license + creates listing)
  POST   /v1/projects/{project_id}/unpublish       — retract from guild
  GET    /v1/guild/listings                        — browse published guild listings
  GET    /v1/guild/listings/{listing_id}           — listing detail (increments view count)
  GET    /v1/guild/studios                         — list all public studios
  GET    /v1/guild/studios/{workspace_id}          — single studio public view
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..business_schemas import (
    GuildListingOut,
    GuildStudioOut,
    ProjectCreate,
    ProjectOut,
    ProjectPublishInput,
    ProjectUpdate,
    StudioProfileCreate,
    StudioProfileOut,
    StudioProfileUpdate,
)
from ..db import get_db
from ..repositories import AtelierRepository
from ..services import AtelierService

router = APIRouter(tags=["studio"])


# ── Dependency helpers ────────────────────────────────────────────────────────

def _repo(db=Depends(get_db)) -> AtelierRepository:
    return AtelierRepository(db)


def _svc(repo: AtelierRepository = Depends(_repo)) -> AtelierService:
    return AtelierService(repo=repo, kernel=None)


def _resolve(
    x_artisan_id: Optional[str] = Header(default=None),
    x_workspace_id: Optional[str] = Header(default=None),
    x_artisan_role: Optional[str] = Header(default=None),
) -> tuple[str, str, str]:
    artisan_id = (x_artisan_id or "").strip()
    workspace_id = (x_workspace_id or "").strip()
    role = (x_artisan_role or "member").strip().lower()
    if not artisan_id:
        raise HTTPException(status_code=401, detail="missing_artisan_identity")
    if not workspace_id:
        raise HTTPException(status_code=400, detail="missing_workspace_id")
    return artisan_id, workspace_id, role


# ── Studio profile ────────────────────────────────────────────────────────────

@router.post("/v1/studio/profile", response_model=StudioProfileOut, status_code=201)
def upsert_studio_profile(
    body: StudioProfileCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> StudioProfileOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.upsert_studio_profile(artisan_id, workspace_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.patch("/v1/studio/profile", response_model=StudioProfileOut)
def patch_studio_profile(
    body: StudioProfileUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> StudioProfileOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.patch_studio_profile(artisan_id, workspace_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/studio/profile", response_model=Optional[StudioProfileOut])
def get_studio_profile(
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> Optional[StudioProfileOut]:
    _, workspace_id, _ = ctx
    return svc.get_studio_profile_out(workspace_id)


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/v1/projects", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> ProjectOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.create_project(artisan_id, workspace_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/v1/projects", response_model=list[ProjectOut])
def list_projects(
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> list[ProjectOut]:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.list_projects_out(artisan_id, workspace_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> ProjectOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.get_project_out(artisan_id, workspace_id, project_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/v1/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> ProjectOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.update_project(artisan_id, workspace_id, project_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/v1/projects/{project_id}/publish", response_model=ProjectOut)
def publish_project(
    project_id: str,
    body: ProjectPublishInput,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> ProjectOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.publish_project(artisan_id, workspace_id, project_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/v1/projects/{project_id}/unpublish", response_model=ProjectOut)
def unpublish_project(
    project_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> ProjectOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.unpublish_project(artisan_id, workspace_id, project_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Guild listings ────────────────────────────────────────────────────────────

@router.get("/v1/guild/listings", response_model=list[GuildListingOut])
def list_guild_listings(
    project_type: Optional[str] = None,
    workspace_id: Optional[str] = None,
    svc: AtelierService = Depends(_svc),
) -> list[GuildListingOut]:
    return svc.list_guild_listings_out(project_type=project_type, workspace_id=workspace_id)


@router.get("/v1/guild/listings/{listing_id}", response_model=GuildListingOut)
def get_guild_listing(
    listing_id: str,
    svc: AtelierService = Depends(_svc),
) -> GuildListingOut:
    result = svc.get_guild_listing_out(listing_id)
    if result is None:
        raise HTTPException(status_code=404, detail="listing_not_found")
    return result


# ── Guild studios ─────────────────────────────────────────────────────────────

@router.get("/v1/guild/studios", response_model=list[GuildStudioOut])
def list_guild_studios(svc: AtelierService = Depends(_svc)) -> list[GuildStudioOut]:
    return svc.list_guild_studios()


@router.get("/v1/guild/studios/{workspace_id}", response_model=Optional[GuildStudioOut])
def get_guild_studio(
    workspace_id: str,
    svc: AtelierService = Depends(_svc),
) -> Optional[GuildStudioOut]:
    studios = svc.list_guild_studios()
    for s in studios:
        if s.workspace_id == workspace_id:
            return s
    raise HTTPException(status_code=404, detail="studio_not_found")
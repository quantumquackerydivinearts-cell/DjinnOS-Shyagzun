"""
Sequential art router
======================
Authoring endpoints for storyboard and comic projects.

Routes (all scoped to a project via x-workspace-id + x-artisan-id headers)
------
  POST   /v1/projects/{project_id}/pages                               — add page
  GET    /v1/projects/{project_id}/pages                               — list pages
  GET    /v1/projects/{project_id}/pages/{page_id}                     — page detail
  PATCH  /v1/projects/{project_id}/pages/{page_id}                     — update page
  DELETE /v1/projects/{project_id}/pages/{page_id}                     — remove page

  POST   /v1/projects/{project_id}/pages/{page_id}/panels              — add panel
  GET    /v1/projects/{project_id}/pages/{page_id}/panels              — list panels
  GET    /v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}   — panel detail
  PATCH  /v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}   — update panel
  DELETE /v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}   — remove panel

  POST   /v1/projects/{project_id}/characters                          — add character
  GET    /v1/projects/{project_id}/characters                          — list characters
  GET    /v1/projects/{project_id}/characters/{char_id}                — character detail
  PATCH  /v1/projects/{project_id}/characters/{char_id}                — update character
  DELETE /v1/projects/{project_id}/characters/{char_id}                — remove character
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..business_schemas import (
    SeqArtCharacterCreate,
    SeqArtCharacterOut,
    SeqArtCharacterUpdate,
    SeqArtPageCreate,
    SeqArtPageOut,
    SeqArtPageUpdate,
    SeqArtPanelCreate,
    SeqArtPanelOut,
    SeqArtPanelUpdate,
)
from ..db import get_db
from ..repositories import AtelierRepository
from ..services import AtelierService

router = APIRouter(tags=["sequential-art"])


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


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.post("/v1/projects/{project_id}/pages", response_model=SeqArtPageOut, status_code=201)
def create_page(
    project_id: str,
    body: SeqArtPageCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPageOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.create_seq_art_page(artisan_id, workspace_id, project_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}/pages", response_model=list[SeqArtPageOut])
def list_pages(
    project_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> list[SeqArtPageOut]:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.list_seq_art_pages_out(artisan_id, workspace_id, project_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}/pages/{page_id}", response_model=SeqArtPageOut)
def get_page(
    project_id: str,
    page_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPageOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.get_seq_art_page_out(artisan_id, workspace_id, project_id, page_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/v1/projects/{project_id}/pages/{page_id}", response_model=SeqArtPageOut)
def update_page(
    project_id: str,
    page_id: str,
    body: SeqArtPageUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPageOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.update_seq_art_page(artisan_id, workspace_id, project_id, page_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/v1/projects/{project_id}/pages/{page_id}", status_code=204)
def delete_page(
    project_id: str,
    page_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> None:
    artisan_id, workspace_id, role = ctx
    try:
        svc.delete_seq_art_page(artisan_id, workspace_id, project_id, page_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Panels ────────────────────────────────────────────────────────────────────

@router.post(
    "/v1/projects/{project_id}/pages/{page_id}/panels",
    response_model=SeqArtPanelOut,
    status_code=201,
)
def create_panel(
    project_id: str,
    page_id: str,
    body: SeqArtPanelCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPanelOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.create_seq_art_panel(artisan_id, workspace_id, project_id, page_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/v1/projects/{project_id}/pages/{page_id}/panels",
    response_model=list[SeqArtPanelOut],
)
def list_panels(
    project_id: str,
    page_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> list[SeqArtPanelOut]:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.list_seq_art_panels_out(artisan_id, workspace_id, project_id, page_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}",
    response_model=SeqArtPanelOut,
)
def get_panel(
    project_id: str,
    page_id: str,
    panel_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPanelOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.get_seq_art_panel_out(artisan_id, workspace_id, project_id, page_id, panel_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}",
    response_model=SeqArtPanelOut,
)
def update_panel(
    project_id: str,
    page_id: str,
    panel_id: str,
    body: SeqArtPanelUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtPanelOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.update_seq_art_panel(artisan_id, workspace_id, project_id, page_id, panel_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/v1/projects/{project_id}/pages/{page_id}/panels/{panel_id}",
    status_code=204,
)
def delete_panel(
    project_id: str,
    page_id: str,
    panel_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> None:
    artisan_id, workspace_id, role = ctx
    try:
        svc.delete_seq_art_panel(artisan_id, workspace_id, project_id, page_id, panel_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Characters ────────────────────────────────────────────────────────────────

@router.post("/v1/projects/{project_id}/characters", response_model=SeqArtCharacterOut, status_code=201)
def create_character(
    project_id: str,
    body: SeqArtCharacterCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtCharacterOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.create_seq_art_character(artisan_id, workspace_id, project_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}/characters", response_model=list[SeqArtCharacterOut])
def list_characters(
    project_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> list[SeqArtCharacterOut]:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.list_seq_art_characters_out(artisan_id, workspace_id, project_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/projects/{project_id}/characters/{char_id}", response_model=SeqArtCharacterOut)
def get_character(
    project_id: str,
    char_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtCharacterOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.get_seq_art_character_out(artisan_id, workspace_id, project_id, char_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/v1/projects/{project_id}/characters/{char_id}", response_model=SeqArtCharacterOut)
def update_character(
    project_id: str,
    char_id: str,
    body: SeqArtCharacterUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> SeqArtCharacterOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.update_seq_art_character(artisan_id, workspace_id, project_id, char_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/v1/projects/{project_id}/characters/{char_id}", status_code=204)
def delete_character(
    project_id: str,
    char_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> None:
    artisan_id, workspace_id, role = ctx
    try:
        svc.delete_seq_art_character(artisan_id, workspace_id, project_id, char_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
"""
Distribution targets router
============================
Endpoints for attaching distribution channels to projects or studios.

Routes
------
  POST   /v1/distribution/targets                   — create target
  GET    /v1/distribution/targets                   — list workspace targets
  GET    /v1/distribution/targets/{id}              — target detail
  PATCH  /v1/distribution/targets/{id}              — update status / config
  DELETE /v1/distribution/targets/{id}              — retire (soft delete)

Filtering query params for GET /v1/distribution/targets:
  project_id   — only targets for this project
  target_type  — steam | own_store | commission_intake
  status       — draft | active | paused | retired
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..business_schemas import (
    DistributionTargetCreate,
    DistributionTargetOut,
    DistributionTargetUpdate,
)
from ..db import get_db
from ..repositories import AtelierRepository
from ..services import AtelierService

router = APIRouter(tags=["distribution"])


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/v1/distribution/targets", response_model=DistributionTargetOut, status_code=201)
def create_distribution_target(
    body: DistributionTargetCreate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> DistributionTargetOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.create_distribution_target(artisan_id, workspace_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/v1/distribution/targets", response_model=list[DistributionTargetOut])
def list_distribution_targets(
    project_id: Optional[str] = None,
    target_type: Optional[str] = None,
    status: Optional[str] = None,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> list[DistributionTargetOut]:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.list_distribution_targets_out(
            artisan_id, workspace_id, role,
            project_id=project_id,
            target_type=target_type,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/v1/distribution/targets/{target_id}", response_model=DistributionTargetOut)
def get_distribution_target(
    target_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> DistributionTargetOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.get_distribution_target_out(artisan_id, workspace_id, target_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/v1/distribution/targets/{target_id}", response_model=DistributionTargetOut)
def update_distribution_target(
    target_id: str,
    body: DistributionTargetUpdate,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> DistributionTargetOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.update_distribution_target(artisan_id, workspace_id, target_id, role, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/v1/distribution/targets/{target_id}", response_model=DistributionTargetOut)
def retire_distribution_target(
    target_id: str,
    ctx: tuple[str, str, str] = Depends(_resolve),
    svc: AtelierService = Depends(_svc),
) -> DistributionTargetOut:
    artisan_id, workspace_id, role = ctx
    try:
        return svc.retire_distribution_target(artisan_id, workspace_id, target_id, role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
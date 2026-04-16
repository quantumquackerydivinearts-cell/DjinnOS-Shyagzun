"""Render Lab project CRUD endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...db import get_db
from ._db import db_list, db_save, require_project
from ._utils import new_project_id, now_iso

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str = Field(default="", max_length=128)
    project_type: str = Field(..., pattern="^(game_voxel|arch_diagram|hybrid)$")
    workspace_id: str = Field(default="main")
    realm_id: str = Field(default="lapidus")
    source_json_path: str | None = None


@router.post("/projects", summary="Create a new Render Lab project")
async def create_project(
    req: CreateProjectRequest,
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project_id = new_project_id()
    now = now_iso()
    name = req.name or f"{req.project_type}_{project_id[-8:]}"
    project: dict[str, Any] = {
        "schema": "atelier.render_lab.project.v1",
        "project_id": project_id,
        "name": name,
        "project_type": req.project_type,
        "workspace_id": req.workspace_id,
        "created_at": now,
        "updated_at": now,
        "status": "draft",
        "pipeline": {
            "source_ids": {
                "python_file_id": None,
                "kobra_file_id":  None,
                "js_file_id":     None,
                "json_file_id":   req.source_json_path,
                "engine_file_id": None,
            },
            "world_region": {
                "realm_id":     req.realm_id,
                "region_key":   "",
                "cache_policy": "cache",
            },
            "render_settings": {},
            "last_run_at": None,
            "last_run_status": None,
        },
        "artifacts": {
            "compiled_pack_path":     None,
            "stream_manifest_path":   None,
            "prefetch_manifest_path": None,
            "toolchain_report_path":  None,
            "layer_projection_path":  None,
        },
        "arch_diagram": None if req.project_type == "game_voxel" else {
            "spec": {},
            "export_svg_path": None,
            "export_png_path": None,
            "scripts": [],
        },
        "gate_status": {k: None for k in ("gate_a", "gate_b", "gate_c", "gate_d", "gate_e", "gate_f")},
        "readiness": {
            "readiness_green": False,
            "federation_green": False,
            "last_checked_at": None,
        },
        "lineage_ids": [],
    }
    db_save(db, project)
    return ORJSONResponse(status_code=201, content={"ok": True, "project_id": project_id, "project": project})


@router.get("/projects", summary="List all Render Lab projects")
async def list_projects(db: Session = Depends(get_db)) -> ORJSONResponse:
    projects = db_list(db)
    return ORJSONResponse(content={
        "ok": True,
        "projects": [
            {
                "project_id":   p["project_id"],
                "name":         p.get("name", ""),
                "project_type": p["project_type"],
                "status":       p.get("status", "draft"),
            }
            for p in projects
        ],
        "count": len(projects),
    })


@router.get("/projects/{project_id}", summary="Get a Render Lab project by ID")
async def get_project(project_id: str, db: Session = Depends(get_db)) -> ORJSONResponse:
    project = require_project(db, project_id)
    return ORJSONResponse(content={"ok": True, "project": project})


@router.delete("/projects/{project_id}", summary="Archive a Render Lab project")
async def archive_project(project_id: str, db: Session = Depends(get_db)) -> ORJSONResponse:
    project = require_project(db, project_id)
    project["status"] = "archived"
    project["updated_at"] = now_iso()
    db_save(db, project)
    return ORJSONResponse(content={"ok": True, "project_id": project_id, "status": "archived"})
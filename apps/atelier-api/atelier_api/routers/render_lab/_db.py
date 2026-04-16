"""DB access layer for Render Lab projects."""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ._utils import now_iso


def db_get(db: Session, project_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT data_json FROM render_lab_projects WHERE project_id = :pid"),
        {"pid": project_id},
    ).fetchone()
    return json.loads(row[0]) if row else None


def db_save(db: Session, project: dict[str, Any]) -> None:
    pid   = project["project_id"]
    realm = project.get("pipeline", {}).get("world_region", {}).get("realm_id", "lapidus")
    db.execute(text("""
        INSERT INTO render_lab_projects
            (project_id, name, project_type, workspace_id, realm_id,
             status, data_json, created_at, updated_at)
        VALUES
            (:pid, :name, :ptype, :wsid, :realm,
             :status, :data, :created, :updated)
        ON CONFLICT(project_id) DO UPDATE SET
            name         = excluded.name,
            project_type = excluded.project_type,
            workspace_id = excluded.workspace_id,
            realm_id     = excluded.realm_id,
            status       = excluded.status,
            data_json    = excluded.data_json,
            updated_at   = excluded.updated_at
    """), {
        "pid":     pid,
        "name":    project.get("name", ""),
        "ptype":   project["project_type"],
        "wsid":    project.get("workspace_id", "main"),
        "realm":   realm,
        "status":  project.get("status", "draft"),
        "data":    json.dumps(project),
        "created": project.get("created_at", now_iso()),
        "updated": project.get("updated_at", now_iso()),
    })
    db.commit()


def db_list(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text("SELECT data_json FROM render_lab_projects ORDER BY created_at DESC")
    ).fetchall()
    return [json.loads(r[0]) for r in rows]


def require_project(db: Session, project_id: str) -> dict[str, Any]:
    project = db_get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project_not_found")
    return project
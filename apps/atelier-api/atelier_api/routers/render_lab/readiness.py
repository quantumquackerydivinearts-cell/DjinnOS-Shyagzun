"""Render Lab readiness and federation health checks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

from ...db import get_db
from ._db import db_save, require_project
from ._utils import http_get_json, now_iso

router = APIRouter()


@router.get("/projects/{project_id}/readiness",
            summary="Get project readiness and federation status")
async def get_readiness(
    project_id: str,
    api_url: str = "http://127.0.0.1:9000",
    kernel_url: str = "http://127.0.0.1:8000",
    db: Session = Depends(get_db),
) -> ORJSONResponse:
    project = require_project(db, project_id)
    checks: list[dict[str, Any]] = []

    # API health
    try:
        data = http_get_json(f"{api_url}/ready")
        checks.append({"name": "api_ready", "ok": data.get("status") == "ready", "detail": data})
    except Exception as exc:
        checks.append({"name": "api_ready", "ok": False, "detail": {"error": str(exc)}})

    # Kernel health
    try:
        data = http_get_json(f"{kernel_url}/health")
        checks.append({"name": "kernel_health", "ok": data.get("status") == "ok", "detail": data})
    except Exception as exc:
        checks.append({"name": "kernel_health", "ok": False, "detail": {"error": str(exc)}})

    # Toolchain go/no-go (voxel + hybrid only)
    if project["project_type"] in ("game_voxel", "hybrid"):
        report_path = project["artifacts"].get("toolchain_report_path")
        if report_path and Path(report_path).exists():
            try:
                report = json.loads(Path(report_path).read_text(encoding="utf-8"))
                go = bool(report.get("go", False))
                checks.append({"name": "toolchain_go_no_go", "ok": go, "detail": {"go": go}})
            except Exception as exc:
                checks.append({"name": "toolchain_go_no_go", "ok": False,
                               "detail": {"error": str(exc)}})
        else:
            checks.append({"name": "toolchain_go_no_go", "ok": False,
                          "detail": {"error": "toolchain_report_not_found"}})

    # Arch diagram parse (arch + hybrid only)
    if project["project_type"] in ("arch_diagram", "hybrid"):
        spec  = (project.get("arch_diagram") or {}).get("spec") or {}
        nodes = (
            list(spec.get("domains", [])) +
            list(spec.get("systems", [])) +
            list(spec.get("tools", []))
        )
        checks.append({"name": "arch_diagram_parse", "ok": len(nodes) > 0,
                      "detail": {"node_count": len(nodes)}})

    # Federation health
    federation: dict[str, Any] = {"ok": False, "status": "unknown", "error_count": -1}
    try:
        fed_data = http_get_json(f"{api_url}/v1/federation/health")
        federation = {
            "ok":                fed_data.get("status") == "ok" and fed_data.get("error_count", 1) == 0,
            "status":            fed_data.get("status", "unknown"),
            "error_count":       fed_data.get("error_count", -1),
            "active_trust_count": fed_data.get("active_trust_count", 0),
        }
    except Exception as exc:
        federation["error"] = str(exc)

    readiness_green  = all(c["ok"] for c in checks)
    federation_green = bool(federation.get("ok", False))

    project["readiness"]["readiness_green"]  = readiness_green
    project["readiness"]["federation_green"] = federation_green
    project["readiness"]["last_checked_at"]  = now_iso()
    db_save(db, project)

    return ORJSONResponse(content={
        "ok":               True,
        "project_id":       project_id,
        "project_type":     project["project_type"],
        "readiness_green":  readiness_green,
        "federation_green": federation_green,
        "checks":           checks,
        "federation":       federation,
        "checked_at":       now_iso(),
    })
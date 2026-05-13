"""
graph_router.py — CRM relationship graph API.

GET  /v1/graph/node-types          — available node types
POST /v1/graph/snapshot            — build full workspace snapshot
POST /v1/graph/neighbors           — neighbours of one node
POST /v1/graph/subgraph            — BFS subgraph from seed nodes
POST /v1/graph/path                — shortest path between two nodes
GET  /v1/graph/configs             — list saved configs
POST /v1/graph/configs             — save a config
DELETE /v1/graph/configs/{id}      — delete a config
GET  /v1/graph/telemetry           — event summary
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .models import Workspace
from .graph_service import (
    ALL_NODE_TYPES, DEFAULT_CONFIG,
    build_snapshot, get_neighbors, bfs_subgraph, bfs_path,
    list_configs, save_config, delete_config,
    record_event, telemetry_summary,
)

router = APIRouter()


# ── Workspace dep (same pattern as import_router) ────────────────────────────

def _ws(
    x_workspace_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    if not x_workspace_id:
        raise HTTPException(400, "X-Workspace-Id header required")
    if db.get(Workspace, x_workspace_id) is None:
        raise HTTPException(404, "workspace_not_found")
    return x_workspace_id


# ── Schemas ───────────────────────────────────────────────────────────────────

class SnapshotRequest(BaseModel):
    node_types: list[str] = Field(default_factory=lambda: ALL_NODE_TYPES)


class NeighborsRequest(BaseModel):
    node_id:    str
    node_types: list[str] = Field(default_factory=lambda: ALL_NODE_TYPES)


class SubgraphRequest(BaseModel):
    seed_node_ids: list[str] = Field(min_length=1)
    max_depth:     int       = Field(default=2, ge=1, le=8)
    node_types:    list[str] = Field(default_factory=lambda: ALL_NODE_TYPES)


class PathRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    max_depth:      int  = Field(default=8, ge=1, le=32)
    directed:       bool = False
    node_types:     list[str] = Field(default_factory=lambda: ALL_NODE_TYPES)


class SaveConfigRequest(BaseModel):
    name:   str = Field(min_length=1, max_length=120)
    config: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/node-types")
def node_types() -> dict:
    return {"node_types": ALL_NODE_TYPES}


@router.post("/snapshot")
def snapshot(
    body:         SnapshotRequest,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    snap = build_snapshot(db, workspace_id, body.node_types)
    record_event(db, workspace_id, "snapshot", {"node_count": len(snap.nodes), "edge_count": len(snap.edges)})
    return snap.to_dict()


@router.post("/neighbors")
def neighbors(
    body:         NeighborsRequest,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    snap = build_snapshot(db, workspace_id, body.node_types)
    node_ids = {n.id for n in snap.nodes}
    if body.node_id not in node_ids:
        raise HTTPException(404, "node_not_found")
    result = get_neighbors(snap, body.node_id)
    record_event(db, workspace_id, "neighbors", {"node_id": body.node_id})
    return result


@router.post("/subgraph")
def subgraph(
    body:         SubgraphRequest,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    snap = build_snapshot(db, workspace_id, body.node_types)
    result = bfs_subgraph(snap, body.seed_node_ids, body.max_depth)
    record_event(db, workspace_id, "subgraph", {
        "seeds": body.seed_node_ids, "max_depth": body.max_depth,
        "result_nodes": len(result.nodes),
    })
    return result.to_dict()


@router.post("/path")
def path(
    body:         PathRequest,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    snap   = build_snapshot(db, workspace_id, body.node_types)
    result = bfs_path(snap, body.source_node_id, body.target_node_id,
                      body.max_depth, body.directed)
    record_event(db, workspace_id, "path", {
        "source": body.source_node_id, "target": body.target_node_id,
        "found": result["found"],
    })
    return result


@router.get("/configs")
def get_configs(workspace_id: str = Depends(_ws), db: Session = Depends(get_db)) -> dict:
    return {"configs": list_configs(db, workspace_id)}


@router.post("/configs", status_code=201)
def create_config(
    body:         SaveConfigRequest,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> dict:
    return save_config(db, workspace_id, body.name, body.config)


@router.delete("/configs/{config_id}", status_code=204)
def remove_config(
    config_id:    str,
    workspace_id: str     = Depends(_ws),
    db:           Session = Depends(get_db),
) -> None:
    if not delete_config(db, workspace_id, config_id):
        raise HTTPException(404, "config_not_found")


@router.get("/telemetry")
def telemetry(workspace_id: str = Depends(_ws), db: Session = Depends(get_db)) -> dict:
    return telemetry_summary(db, workspace_id)

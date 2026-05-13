"""
graph_service.py — CRM relationship graph for the Atelier.

Builds a snapshot of workspace entities as a node/edge graph, then provides
BFS-based traversal: neighbours, subgraph, shortest path.

Node types and their edges:
  contact  — Booking.contact_id → contact
  lead     — Quote.lead_id → lead
  client   — Order.client_id → client
  quote    — Quote.lead_id (edge lead→quote), Order.quote_id (edge quote→order)
  order    — Order.quote_id / Order.client_id
  booking  — Booking.contact_id (edge contact→booking)
  contract — standalone (party_name as label)
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Booking, Client, Contract, CRMContact, GraphConfigRecord,
    GraphTelemetryEvent, Lead, Order, Quote, Workspace,
)

ALL_NODE_TYPES = ["contact", "lead", "client", "quote", "order", "booking", "contract"]

DEFAULT_CONFIG = {
    "node_types": ALL_NODE_TYPES,
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class GNode:
    id:    str
    type:  str
    label: str
    data:  dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GEdge:
    id:        str
    from_node: str
    to_node:   str
    label:     str
    data:      dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GraphSnapshot:
    nodes:  list[GNode]
    edges:  list[GEdge]
    config: dict

    def to_dict(self) -> dict:
        return {
            "nodes":  [n.to_dict() for n in self.nodes],
            "edges":  [e.to_dict() for e in self.edges],
            "config": self.config,
        }


# ── Snapshot builder ──────────────────────────────────────────────────────────

def build_snapshot(db: Session, workspace_id: str, node_types: list[str]) -> GraphSnapshot:
    types = set(node_types)
    nodes: list[GNode] = []
    edges: list[GEdge] = []

    if "contact" in types:
        for c in db.scalars(select(CRMContact).where(CRMContact.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"contact:{c.id}", "contact", c.full_name,
                               {"email": c.email, "phone": c.phone}))

    if "lead" in types:
        for l in db.scalars(select(Lead).where(Lead.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"lead:{l.id}", "lead", l.full_name,
                               {"status": l.status, "source": l.source}))

    if "client" in types:
        for c in db.scalars(select(Client).where(Client.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"client:{c.id}", "client", c.full_name,
                               {"status": c.status, "email": c.email}))

    if "quote" in types:
        for q in db.scalars(select(Quote).where(Quote.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"quote:{q.id}", "quote", q.title or q.id[:8],
                               {"status": q.status}))
            if q.lead_id and "lead" in types:
                edges.append(GEdge(f"lead:{q.lead_id}>quote:{q.id}",
                                   f"lead:{q.lead_id}", f"quote:{q.id}", "quoted_as"))

    if "order" in types:
        for o in db.scalars(select(Order).where(Order.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"order:{o.id}", "order", o.title or o.id[:8],
                               {"status": o.status,
                                "amount": f"{o.amount_cents / 100:.2f} {o.currency}"}))
            if o.quote_id and "quote" in types:
                edges.append(GEdge(f"quote:{o.quote_id}>order:{o.id}",
                                   f"quote:{o.quote_id}", f"order:{o.id}", "fulfills"))
            if o.client_id and "client" in types:
                edges.append(GEdge(f"client:{o.client_id}>order:{o.id}",
                                   f"client:{o.client_id}", f"order:{o.id}", "ordered_by"))

    if "booking" in types:
        for b in db.scalars(select(Booking).where(Booking.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"booking:{b.id}", "booking", b.title or b.id[:8],
                               {"status": b.status}))
            if b.contact_id and "contact" in types:
                edges.append(GEdge(f"contact:{b.contact_id}>booking:{b.id}",
                                   f"contact:{b.contact_id}", f"booking:{b.id}", "booked_by"))

    if "contract" in types:
        for c in db.scalars(select(Contract).where(Contract.workspace_id == workspace_id)).all():
            nodes.append(GNode(f"contract:{c.id}", "contract", c.title or c.party_name,
                               {"status": c.status, "party": c.party_name}))

    # Drop edges whose endpoints didn't make it into the node set
    node_ids = {n.id for n in nodes}
    edges = [e for e in edges if e.from_node in node_ids and e.to_node in node_ids]

    return GraphSnapshot(nodes=nodes, edges=edges, config={"node_types": list(types)})


# ── Traversal algorithms ──────────────────────────────────────────────────────

def get_neighbors(snapshot: GraphSnapshot, node_id: str) -> dict:
    inbound  = [e.to_dict() for e in snapshot.edges if e.to_node   == node_id]
    outbound = [e.to_dict() for e in snapshot.edges if e.from_node == node_id]
    return {"node_id": node_id, "inbound": inbound, "outbound": outbound}


def bfs_subgraph(snapshot: GraphSnapshot, seed_ids: list[str], max_depth: int) -> GraphSnapshot:
    adj: dict[str, set[str]] = {n.id: set() for n in snapshot.nodes}
    for e in snapshot.edges:
        adj[e.from_node].add(e.to_node)
        adj[e.to_node].add(e.from_node)

    visited: set[str] = set()
    queue = deque((sid, 0) for sid in seed_ids if sid in adj)
    while queue:
        nid, depth = queue.popleft()
        if nid in visited or depth > max_depth:
            continue
        visited.add(nid)
        if depth < max_depth:
            for neighbor in adj.get(nid, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

    sub_nodes = [n for n in snapshot.nodes if n.id in visited]
    sub_edges = [e for e in snapshot.edges
                 if e.from_node in visited and e.to_node in visited]
    return GraphSnapshot(nodes=sub_nodes, edges=sub_edges, config=snapshot.config)


def bfs_path(snapshot: GraphSnapshot, source: str, target: str,
             max_depth: int, directed: bool) -> dict:
    if source == target:
        return {"found": True, "nodes": [source], "edges": [], "hop_count": 0}

    # Build adjacency
    adj: dict[str, list[tuple[str, str]]] = {n.id: [] for n in snapshot.nodes}
    edge_map: dict[tuple[str, str], GEdge] = {}
    for e in snapshot.edges:
        adj[e.from_node].append((e.to_node, e.id))
        edge_map[(e.from_node, e.to_node)] = e
        if not directed:
            adj[e.to_node].append((e.from_node, e.id))
            edge_map[(e.to_node, e.from_node)] = e

    prev: dict[str, str | None] = {source: None}
    queue = deque([(source, 0)])
    found = False

    while queue:
        cur, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor, _ in adj.get(cur, []):
            if neighbor not in prev:
                prev[neighbor] = cur
                if neighbor == target:
                    found = True
                    break
                queue.append((neighbor, depth + 1))
        if found:
            break

    if not found:
        return {"found": False, "nodes": [], "edges": [], "hop_count": 0}

    # Reconstruct path
    path_nodes: list[str] = []
    cur = target
    while cur is not None:
        path_nodes.append(cur)
        cur = prev[cur]
    path_nodes.reverse()

    path_edges = []
    for i in range(len(path_nodes) - 1):
        e = edge_map.get((path_nodes[i], path_nodes[i + 1])) or \
            edge_map.get((path_nodes[i + 1], path_nodes[i]))
        if e:
            path_edges.append(e.to_dict())

    return {
        "found":     True,
        "nodes":     path_nodes,
        "edges":     path_edges,
        "hop_count": len(path_nodes) - 1,
    }


# ── Config persistence ────────────────────────────────────────────────────────

def list_configs(db: Session, workspace_id: str) -> list[dict]:
    rows = db.scalars(
        select(GraphConfigRecord).where(GraphConfigRecord.workspace_id == workspace_id)
        .order_by(GraphConfigRecord.updated_at.desc())
    ).all()
    return [{"id": r.id, "name": r.name, "config": json.loads(r.config_json),
             "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}
            for r in rows]


def save_config(db: Session, workspace_id: str, name: str, config: dict) -> dict:
    row = GraphConfigRecord(
        id=str(uuid4()), workspace_id=workspace_id,
        name=name, config_json=json.dumps(config),
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "config": config,
            "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


def delete_config(db: Session, workspace_id: str, config_id: str) -> bool:
    row = db.get(GraphConfigRecord, config_id)
    if row is None or row.workspace_id != workspace_id:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Telemetry ─────────────────────────────────────────────────────────────────

def record_event(db: Session, workspace_id: str, event_name: str, meta: dict) -> None:
    db.add(GraphTelemetryEvent(
        id=str(uuid4()), workspace_id=workspace_id,
        event_name=event_name, metadata_json=json.dumps(meta),
        created_at=datetime.utcnow(),
    ))
    db.commit()


def telemetry_summary(db: Session, workspace_id: str) -> dict:
    rows = db.scalars(
        select(GraphTelemetryEvent)
        .where(GraphTelemetryEvent.workspace_id == workspace_id)
        .order_by(GraphTelemetryEvent.created_at.desc())
        .limit(200)
    ).all()
    by_event: dict[str, int] = {}
    for r in rows:
        by_event[r.event_name] = by_event.get(r.event_name, 0) + 1
    return {"total_events": len(rows), "by_event": by_event}

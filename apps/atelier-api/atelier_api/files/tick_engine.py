"""
atelier_api/services/tick_engine.py
Server-authoritative tick engine.
Applies ordered events to an engine state, returning patches and
the next full state. All transitions are logged to the lineage store.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from uuid import uuid4

from ..core.lineage import LineageRecord, get_lineage_store
from ..models.schemas import TickEvent, TickEventResult


# ── Tick handlers ─────────────────────────────────────────────────────────────
# Each handler receives (state, event) and returns a state_patch dict.
# The patch is shallow-merged into state after each event.

def _handle_scene_tick(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    p = event.payload
    patch: dict[str, Any] = {}

    if "time_delta_ms" in p:
        patch["world_time_ms"] = int(state.get("world_time_ms", 0)) + int(p["time_delta_ms"])

    if "player_pos" in p:
        patch["player_pos"] = p["player_pos"]

    if "weather" in p:
        patch["weather"] = p["weather"]

    return patch


def _handle_entity_spawn(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    p = event.payload
    entity_id = str(p.get("entity_id", f"entity_{uuid4().hex[:6]}"))
    entities = dict(state.get("entities", {}))
    entities[entity_id] = {
        "id":    entity_id,
        "kind":  str(p.get("kind", "unknown")),
        "x":     float(p.get("x", 0)),
        "y":     float(p.get("y", 0)),
        "z":     float(p.get("z", 0)),
        "color": str(p.get("color", "")),
        "layer": str(p.get("layer", "base")),
        "spawned_at": int(time.time() * 1000),
    }
    return {"entities": entities}


def _handle_entity_move(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    p = event.payload
    entity_id = str(p.get("entity_id", ""))
    entities = dict(state.get("entities", {}))
    if entity_id in entities:
        entity = dict(entities[entity_id])
        for axis in ("x", "y", "z"):
            if axis in p:
                entity[axis] = float(p[axis])
        entities[entity_id] = entity
    return {"entities": entities}


def _handle_entity_despawn(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    entity_id = str(event.payload.get("entity_id", ""))
    entities = {k: v for k, v in state.get("entities", {}).items() if k != entity_id}
    return {"entities": entities}


def _handle_rule_trigger(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    p = event.payload
    triggered = list(state.get("triggered_rules", []))
    triggered.append({
        "rule_id":    str(p.get("rule_id", "")),
        "triggered_at": int(time.time() * 1000),
        "context":    p.get("context", {}),
    })
    # Keep last 100
    return {"triggered_rules": triggered[-100:]}


def _handle_state_patch(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    """Generic handler: payload IS the patch."""
    return dict(event.payload)


def _handle_inbox_post(state: dict[str, Any], event: TickEvent) -> dict[str, Any]:
    inbox = list(state.get("post_inbox", []))
    inbox.append({
        **event.payload,
        "received_at": int(time.time() * 1000),
    })
    return {"post_inbox": inbox}


# ── Handler registry ──────────────────────────────────────────────────────────

HANDLERS: dict[str, Any] = {
    "render.scene.tick":      _handle_scene_tick,
    "entity.spawn":           _handle_entity_spawn,
    "entity.move":            _handle_entity_move,
    "entity.despawn":         _handle_entity_despawn,
    "rule.trigger":           _handle_rule_trigger,
    "state.patch":            _handle_state_patch,
    "inbox.post":             _handle_inbox_post,
}


def _dispatch(state: dict[str, Any], event: TickEvent) -> tuple[dict[str, Any], str | None]:
    """
    Returns (state_patch, error_message_or_None).
    Falls back to state.patch handler for unknown event kinds.
    """
    handler = HANDLERS.get(event.kind) or HANDLERS.get("state.patch")
    try:
        patch = handler(state, event)
        return patch, None
    except Exception as exc:  # noqa: BLE001
        return {}, str(exc)


def _merge(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Shallow merge patch into state, returning a new dict."""
    next_state = dict(state)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(next_state.get(k), dict):
            # One level deep dict merge
            next_state[k] = {**next_state[k], **v}
        else:
            next_state[k] = v
    return next_state


def _state_hash(state: dict[str, Any]) -> str:
    blob = json.dumps(state, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


# ── Public API ────────────────────────────────────────────────────────────────

def apply_tick(
    workspace_id: str,
    actor_id: str,
    plan_id: str,
    events: list[TickEvent],
    current_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply a list of tick events to current_state.
    Returns a result dict matching TickResponse schema.
    All processing happens server-side; the result is logged to lineage.
    """
    lineage_store = get_lineage_store()
    lineage_id = f"tick_{uuid4().hex[:12]}"
    record = lineage_store.create_record(
        lineage_id=lineage_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
        action_kind="runtime.tick",
    )

    # Layer 0: raw input
    record.set_layer(0, {"plan_id": plan_id, "events": [e.model_dump() for e in events]})
    # Layer 3: pre-tick state
    record.set_layer(3, current_state)

    state = dict(current_state)
    results: list[TickEventResult] = []
    all_patches: dict[str, Any] = {}

    for event in events:
        patch, error = _dispatch(state, event)
        result = TickEventResult(
            action_id=event.action_id,
            ok=error is None,
            kind=event.kind,
            state_patch=patch,
            error=error,
        )
        results.append(result)
        if error is None:
            state = _merge(state, patch)
            all_patches.update(patch)

    # Stamp tick metadata
    state["_last_tick_plan_id"] = plan_id
    state["_last_tick_ms"] = int(time.time() * 1000)
    state["_last_actor_id"] = actor_id

    next_hash = _state_hash(state)
    state["_hash"] = next_hash

    failed_count = sum(1 for r in results if not r.ok)

    # Layer 4: combined patch
    record.set_layer(4, all_patches)
    # Layer 5: post-tick state
    record.set_layer(5, state)
    # Layer 8: signed (hash recorded)
    record.set_layer(8, {"hash": next_hash, "failed": failed_count})
    lineage_store.append(record)

    return {
        "ok": failed_count == 0,
        "plan_id": plan_id,
        "workspace_id": workspace_id,
        "actor_id": actor_id,
        "results": [r.model_dump() for r in results],
        "next_state": state,
        "hash": next_hash,
        "lineage_id": lineage_id,
        "failed_count": failed_count,
    }

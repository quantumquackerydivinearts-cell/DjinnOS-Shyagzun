from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence


@dataclass(frozen=True)
class PhysicsStepConfig:
    dt: float = 1.0
    gravity: float = 0.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rose_vector_from_constraints(render_constraints: Mapping[str, Any]) -> Dict[str, float]:
    rose = render_constraints.get("rose_vector_calculus")
    if not isinstance(rose, dict):
        return {"x": 0.0, "y": 0.0, "phase": 0.0, "polarity": 0.0, "scalar": 0.0, "enabled": 0.0}
    vector = rose.get("vector")
    if not isinstance(vector, dict):
        vector = {}
    x = _safe_float(vector.get("x"), 0.0)
    y = _safe_float(vector.get("y"), 0.0)
    phase = _safe_float(rose.get("phase_deg"), 0.0)
    polarity = _safe_float(rose.get("polarity"), 0.0)
    enabled = 1.0 if bool(rose.get("enabled", True)) else 0.0
    scalars = rose.get("scalars")
    scalar = 0.0
    if isinstance(scalars, list) and scalars:
        scalar = sum(_safe_float(item, 0.0) for item in scalars) / max(1, len(scalars))
    return {"x": x, "y": y, "phase": phase, "polarity": polarity, "scalar": scalar, "enabled": enabled}


def build_material_index(render_constraints: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    library = render_constraints.get("material_library")
    index: Dict[str, Dict[str, Any]] = {}
    if not isinstance(library, list):
        return index
    for entry in library:
        if not isinstance(entry, dict):
            continue
        symbol = entry.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            continue
        props = entry.get("properties")
        if not isinstance(props, dict):
            props = {}
        index[symbol] = dict(props)
    return index


def _entity_material_symbol(entity: Mapping[str, Any]) -> Optional[str]:
    for key in ("material", "material_id", "material_symbol", "symbol"):
        value = entity.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def enforce_material_constraints(
    engine_state: Mapping[str, Any],
    render_constraints: Mapping[str, Any],
    *,
    strict: bool = True,
) -> None:
    material_index = build_material_index(render_constraints)
    entities = engine_state.get("entities")
    if not isinstance(entities, list):
        return
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        symbol = _entity_material_symbol(entity)
        if symbol is None:
            continue
        if symbol not in material_index:
            if strict:
                raise ValueError(f"material_missing:{symbol}")


def apply_physics_tick(
    engine_state: Mapping[str, Any],
    render_constraints: Mapping[str, Any],
    *,
    dt: float = 1.0,
) -> Dict[str, Any]:
    """
    Minimal physics step that respects Shygazun material properties.
    - deterministic
    - no randomness
    - hard material validation via render constraints
    """
    enforce_material_constraints(engine_state, render_constraints, strict=True)
    material_index = build_material_index(render_constraints)
    next_state: Dict[str, Any] = dict(engine_state)
    rose = _rose_vector_from_constraints(render_constraints)
    rose_enabled = rose["enabled"] > 0.0
    rose_polarity = 1.0 if rose["polarity"] >= 0 else -1.0
    rose_scalar_norm = max(0.0, min(1.0, rose["scalar"] / 11.0)) if rose["scalar"] else 0.0

    entities = engine_state.get("entities")
    if not isinstance(entities, list):
        next_state["tick"] = int(_safe_float(engine_state.get("tick", 0))) + 1
        return next_state

    gravity = _safe_float(engine_state.get("gravity", 0.0))
    bounds = engine_state.get("bounds") if isinstance(engine_state.get("bounds"), dict) else None
    width = _safe_float(bounds.get("width")) if bounds else None
    height = _safe_float(bounds.get("height")) if bounds else None

    updated_entities: list[Dict[str, Any]] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        item: Dict[str, Any] = dict(entity)
        symbol = _entity_material_symbol(item)
        props = material_index.get(symbol, {})
        density = _safe_float(props.get("density", 50.0), 50.0)
        friction = _safe_float(props.get("friction", 35.0), 35.0)
        restitution = _safe_float(props.get("restitution", 25.0), 25.0)
        flow = _safe_float(props.get("flow", 0.0), 0.0)
        volatility = _safe_float(props.get("volatility", 20.0), 20.0)

        if rose_enabled and rose_scalar_norm > 0.0:
            density *= 0.85 + (rose_scalar_norm * 0.3)
            flow *= 0.9 + (rose_scalar_norm * 0.2)

        x = _safe_float(item.get("x", 0.0))
        y = _safe_float(item.get("y", 0.0))
        vx = _safe_float(item.get("vx", 0.0))
        vy = _safe_float(item.get("vy", 0.0))

        grav_scale = max(0.1, density / 100.0)
        vy += gravity * grav_scale * dt
        vx += (flow / 100.0) * dt
        if rose_enabled and (rose["x"] or rose["y"]):
            drift = 0.15 * rose_polarity
            vx += rose["x"] * drift * dt
            vy += rose["y"] * drift * dt

        damping = max(0.05, 1.0 - (friction / 200.0) - (volatility / 200.0))
        vx *= damping
        vy *= damping

        x += vx * dt
        y += vy * dt

        if width is not None:
            if x < 0:
                x = 0
                vx = -vx * (restitution / 100.0)
            elif x > width:
                x = width
                vx = -vx * (restitution / 100.0)
        if height is not None:
            if y < 0:
                y = 0
                vy = -vy * (restitution / 100.0)
            elif y > height:
                y = height
                vy = -vy * (restitution / 100.0)

        item["x"] = x
        item["y"] = y
        item["vx"] = vx
        item["vy"] = vy
        updated_entities.append(item)

    next_state["entities"] = updated_entities
    next_state["tick"] = int(_safe_float(engine_state.get("tick", 0))) + 1
    return next_state

"""
atelier_api/services/daisy.py
Daisy Tongue bodyplan generator.
Builds a structured bodyplan spec and projects it to renderer voxels.
"""
from __future__ import annotations

import random
import time
from typing import Any

from ..models.schemas import DaisyBodyplanRequest

ROLES = [
    "framework",
    "network",
    "actuator_primary",
    "actuator_secondary",
    "sensor_primary",
    "sensor_secondary",
    "integrator",
    "membrane",
    "core_process",
    "reserve",
]

DEFAULT_SYMBOLS = [
    "Ta", "Ra", "Ka", "Na", "Sa", "La", "Ma", "Ha",
    "Wa", "Ya", "Pa", "Fa", "Ba", "Da", "Ga", "Ja",
    "Va", "Za", "Qa", "Xa",
]

TOKEN_COLORS: dict[str, str] = {
    "Ta": "#7aa2ff",
    "Ra": "#ff9e7a",
    "Ka": "#a3e8a3",
    "Na": "#f5d76e",
    "Sa": "#c9a8ff",
    "La": "#80d8ff",
    "Ma": "#ffb3de",
    "Ha": "#ffd1a3",
}


def _token_color(token: str) -> str:
    return TOKEN_COLORS.get(token, "#aaaaaa")


def build_bodyplan(req: DaisyBodyplanRequest) -> dict[str, Any]:
    rng = random.Random(req.seed)

    symbol_pool: list[str] = (
        req.daisy_symbols if req.daisy_symbols else list(DEFAULT_SYMBOLS)
    )

    # Role → symbol mapping
    role_map: dict[str, str] = {}
    for i, role in enumerate(ROLES):
        if role in req.role_overrides:
            role_map[role] = req.role_overrides[role]
        else:
            role_map[role] = symbol_pool[i % len(symbol_pool)]

    # Segments
    segments: list[dict[str, Any]] = []
    for i in range(req.segment_count):
        is_head  = i == 0
        is_torso = i == req.segment_count // 2
        role     = "sensor_primary" if is_head else "integrator" if is_torso else "framework"
        segments.append({
            "index": i,
            "role":  role,
            "symbol": role_map[role],
            "color_token": req.accent_token if i % 3 == 0 else req.core_token,
            "belonging_chain": (
                req.accent_belonging_chain if i % 3 == 0 else req.core_belonging_chain
            ),
        })

    # Limbs
    limbs: list[dict[str, Any]] = []
    for p in range(req.limb_pairs):
        attach = min(
            req.segment_count - 1,
            max(0, int(req.segment_count * (0.3 + p * 0.2))),
        )
        limb_role = "actuator_primary" if p == 0 else "actuator_secondary"
        for side in ("left", "right"):
            limbs.append({
                "pair":           p,
                "side":           side,
                "attach_segment": attach,
                "role":           limb_role,
                "symbol":         role_map[limb_role],
                "color_token":    req.core_token if side == "left" else req.accent_token,
                "belonging_chain": (
                    req.core_belonging_chain if side == "left"
                    else req.accent_belonging_chain
                ),
            })

    used = {s["symbol"] for s in segments} | {l["symbol"] for l in limbs}

    bodyplan = {
        "schema":    "qqva.daisy.bodyplan.v1",
        "system_id": req.system_id or f"daisy_{int(time.time() * 1000)}",
        "archetype": req.archetype,
        "symmetry":  req.symmetry,
        "seed":      req.seed,
        "daisy_tongue": {
            "symbols_available": symbol_pool,
            "symbols_used":      sorted(used),
            "coverage": {
                "total": len(symbol_pool),
                "used":  len(used),
            },
        },
        "role_map":  role_map,
        "segments":  segments,
        "limbs":     limbs,
        "palette": {
            "core":   {
                "token":            req.core_token,
                "belonging_chain":  req.core_belonging_chain,
            },
            "accent": {
                "token":            req.accent_token,
                "belonging_chain":  req.accent_belonging_chain,
            },
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return bodyplan


def bodyplan_to_voxels(bodyplan: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = bodyplan.get("segments", [])
    limbs:    list[dict[str, Any]] = bodyplan.get("limbs",    [])
    palette                        = bodyplan.get("palette",  {})
    core_token   = palette.get("core",   {}).get("token",   "Ta")
    accent_token = palette.get("accent", {}).get("token",   "Ra")

    voxels: list[dict[str, Any]] = []

    # Vertical stack for segments
    for seg in segments:
        z = len(segments) - seg["index"]
        is_head = seg["role"] == "sensor_primary"
        color   = _token_color(seg["color_token"])
        voxels.append({
            "id":    f"seg_{seg['index']}",
            "type":  "head" if is_head else "torso",
            "x":     0.0,
            "y":     0.0,
            "z":     float(z),
            "w":     1.0 if is_head else 1.5,
            "h":     1.0,
            "color": color,
            "meta":  {
                "symbol":           seg["symbol"],
                "role":             seg["role"],
                "belonging_chain":  seg["belonging_chain"],
            },
        })

    # Limbs branch left / right
    for limb in limbs:
        attach_z = len(segments) - limb["attach_segment"]
        x_offset = -2.0 if limb["side"] == "left" else 2.0
        color    = _token_color(limb["color_token"])
        # Upper
        voxels.append({
            "id":    f"limb_{limb['pair']}_{limb['side']}_upper",
            "type":  "limb",
            "x":     x_offset,
            "y":     0.0,
            "z":     float(attach_z),
            "color": color,
            "meta":  {
                "symbol": limb["symbol"],
                "role":   limb["role"],
                "side":   limb["side"],
            },
        })
        # Lower
        voxels.append({
            "id":    f"limb_{limb['pair']}_{limb['side']}_lower",
            "type":  "limb",
            "x":     x_offset + (-0.5 if limb["side"] == "left" else 0.5),
            "y":     0.0,
            "z":     float(attach_z - 1),
            "color": color,
            "meta":  {
                "symbol": limb["symbol"],
                "role":   limb["role"],
                "side":   limb["side"],
            },
        })

    return voxels

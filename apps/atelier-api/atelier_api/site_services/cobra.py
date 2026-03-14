"""
atelier_api/services/cobra.py
Cobra / Shygazun language parser and scene compiler.

Cobra is a declarative scene description language for the Atelier.
Each line is one of:
    ENTITY <id> <kind> AT <x>,<y>,<z> [COLOR <token>] [LAYER <layer>] [META key=value ...]
    RULE <id>: <condition> -> <effect>
    SET <key> = <value>
    # comment

Shygazun semantic annotations are prefixed with '§':
    §AUTHORITY <level>
    §TRUST <grade>
    §CHIRALITY <values...>
    §TIME_TOPOLOGY <values...>
    §SPACE_OPERATOR <values...>
    §NETWORK_ROLE <values...>
    §CLUSTER_ROLE <values...>
    §AXIS <values...>
    §TONGUE <values...>
    §CANNABIS_MODE <values...>
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CobraEntity:
    id: str
    kind: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    color: str = ""
    layer: str = "base"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CobraRule:
    id: str
    condition: str
    effect: str


@dataclass
class CobraParseResult:
    entities: list[CobraEntity]
    rules: list[CobraRule]
    settings: dict[str, Any]
    semantic: dict[str, list[str]]
    warnings: list[str]
    errors: list[str]


_META_RE = re.compile(r'(\w+)=([^\s]+)')
_COORD_RE = re.compile(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')


def parse_cobra(source: str, strict: bool = False) -> CobraParseResult:
    entities: list[CobraEntity] = []
    rules: list[CobraRule] = []
    settings: dict[str, Any] = {}
    semantic: dict[str, list[str]] = {}
    warnings: list[str] = []
    errors: list[str] = []

    for lineno, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            # ── Shygazun semantic annotation ──────────────────────────────
            if line.startswith("§"):
                parts = line[1:].split(maxsplit=1)
                key = parts[0].lower() if parts else ""
                vals = parts[1].split() if len(parts) > 1 else []
                semantic.setdefault(key, []).extend(vals)
                continue

            upper = line.upper()

            # ── ENTITY ────────────────────────────────────────────────────
            if upper.startswith("ENTITY "):
                tokens = line.split()
                if len(tokens) < 4:
                    warnings.append(f"line {lineno}: ENTITY missing tokens")
                    continue
                entity_id   = tokens[1]
                entity_kind = tokens[2]

                # Find AT coord
                at_idx = next((i for i, t in enumerate(tokens) if t.upper() == "AT"), None)
                x = y = z = 0.0
                if at_idx is not None and at_idx + 1 < len(tokens):
                    coord_str = tokens[at_idx + 1]
                    m = _COORD_RE.match(coord_str)
                    if m:
                        x, y, z = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    else:
                        warnings.append(f"line {lineno}: invalid coords '{coord_str}'")

                # Optional COLOR
                color = ""
                color_idx = next((i for i, t in enumerate(tokens) if t.upper() == "COLOR"), None)
                if color_idx is not None and color_idx + 1 < len(tokens):
                    color = tokens[color_idx + 1]

                # Optional LAYER
                layer = "base"
                layer_idx = next((i for i, t in enumerate(tokens) if t.upper() == "LAYER"), None)
                if layer_idx is not None and layer_idx + 1 < len(tokens):
                    layer = tokens[layer_idx + 1]

                # Optional META key=value pairs
                meta: dict[str, Any] = {}
                meta_idx = next((i for i, t in enumerate(tokens) if t.upper() == "META"), None)
                if meta_idx is not None:
                    meta_str = " ".join(tokens[meta_idx + 1:])
                    for m in _META_RE.finditer(meta_str):
                        meta[m.group(1)] = _coerce(m.group(2))

                entities.append(CobraEntity(
                    id=entity_id, kind=entity_kind,
                    x=x, y=y, z=z,
                    color=color, layer=layer, meta=meta,
                ))
                continue

            # ── RULE ──────────────────────────────────────────────────────
            if upper.startswith("RULE "):
                rest = line[5:]  # strip "RULE "
                if ":" in rest and "->" in rest:
                    rule_id, remainder = rest.split(":", 1)
                    condition, effect   = remainder.split("->", 1)
                    rules.append(CobraRule(
                        id=rule_id.strip(),
                        condition=condition.strip(),
                        effect=effect.strip(),
                    ))
                else:
                    warnings.append(f"line {lineno}: RULE syntax error (expect 'id: cond -> effect')")
                continue

            # ── SET ───────────────────────────────────────────────────────
            if upper.startswith("SET "):
                rest = line[4:]
                if "=" in rest:
                    k, v = rest.split("=", 1)
                    settings[k.strip()] = _coerce(v.strip())
                else:
                    warnings.append(f"line {lineno}: SET missing '='")
                continue

            if strict:
                errors.append(f"line {lineno}: unrecognised directive: {line[:60]!r}")
            else:
                warnings.append(f"line {lineno}: skipped unknown directive: {line[:60]!r}")

        except Exception as exc:  # noqa: BLE001
            errors.append(f"line {lineno}: parse error: {exc}")

    return CobraParseResult(
        entities=entities,
        rules=rules,
        settings=settings,
        semantic=semantic,
        warnings=warnings,
        errors=errors,
    )


def _coerce(v: str) -> Any:
    """Try to coerce a string to int, float, bool, or leave as str."""
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def entities_to_voxels(entities: list[CobraEntity]) -> list[dict[str, Any]]:
    """Convert parsed CobraEntity list to renderer voxel dicts."""
    return [
        {
            "id":    e.id,
            "type":  e.kind,
            "x":     e.x,
            "y":     e.y,
            "z":     e.z,
            "color": e.color,
            "layer": e.layer,
            "meta":  e.meta,
        }
        for e in entities
    ]


def semantic_to_bilingual_trust(semantic: dict[str, list[str]]) -> dict[str, Any]:
    """Map Shygazun semantic annotations to BilingualTrust schema."""
    def first_or_unknown(key: str) -> str:
        vals = semantic.get(key, [])
        return vals[0] if vals else "unknown"

    return {
        "authority_level":  first_or_unknown("authority"),
        "trust_grade":      first_or_unknown("trust"),
        "chirality":        semantic.get("chirality", []),
        "time_topology":    semantic.get("time_topology", []),
        "space_operator":   semantic.get("space_operator", []),
        "network_role":     semantic.get("network_role", []),
        "cluster_role":     semantic.get("cluster_role", []),
        "axis":             semantic.get("axis", []),
        "tongue_projection":semantic.get("tongue", []),
        "cannabis_mode":    semantic.get("cannabis_mode", []),
    }

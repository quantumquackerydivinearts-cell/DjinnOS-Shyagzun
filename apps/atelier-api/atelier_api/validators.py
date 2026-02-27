from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ContentValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, object]


def _split_akinenwun(word: str) -> List[str]:
    raw = word.strip()
    if raw == "":
        return []
    parts = []
    current = ""
    for ch in raw:
        if ch.isupper() and current:
            parts.append(current)
            current = ch
        else:
            current += ch
    if current:
        parts.append(current)
    return parts or [raw]


def _load_symbol_index() -> Optional[Dict[str, object]]:
    try:
        from shygazun.kernel.constants.byte_table import SHYGAZUN_SYMBOL_INDEX  # type: ignore

        if isinstance(SHYGAZUN_SYMBOL_INDEX, dict):
            return SHYGAZUN_SYMBOL_INDEX
    except Exception:
        return None
    return None


def _parse_cobra_entities(source: str) -> List[Dict[str, object]]:
    entities: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None
    for raw_line in source.splitlines():
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if line == "" or line.startswith("#"):
            continue
        if indent > 0 and current is not None:
            colon = line.find(":")
            if colon > 0:
                key = line[:colon].strip()
                value = line[colon + 1 :].strip()
            else:
                parts = line.split(maxsplit=1)
                key = parts[0]
                value = parts[1] if len(parts) == 2 else ""
            meta = current.setdefault("meta", {})
            if isinstance(meta, dict):
                meta[key] = value
            if key in ("lex", "akinenwun", "shygazun"):
                current["akinenwun"] = value
            continue
        if line.startswith("entity "):
            parts = line.split()
            current = {
                "id": parts[1] if len(parts) > 1 else "anon",
                "x": int(parts[2]) if len(parts) > 2 and parts[2].lstrip("-").isdigit() else 0,
                "y": int(parts[3]) if len(parts) > 3 and parts[3].lstrip("-").isdigit() else 0,
                "tag": parts[4] if len(parts) > 4 else "none",
                "meta": {},
                "akinenwun": "",
            }
            entities.append(current)
            continue
        current = None
    return entities


def _layer_for_entity(entity: Dict[str, object]) -> str:
    meta = entity.get("meta")
    if isinstance(meta, dict):
        raw_layer = meta.get("layer")
        if isinstance(raw_layer, str) and raw_layer.strip() != "":
            return raw_layer.strip()
    return "midground"


def _z_for_entity(entity: Dict[str, object], layer: str) -> int:
    layer_offsets = {
        "background": 0,
        "midground": 10,
        "foreground": 20,
        "overlay": 30,
        "ui": 40,
    }
    base = layer_offsets.get(layer, layer_offsets["midground"])
    meta = entity.get("meta")
    if isinstance(meta, dict):
        z_raw = meta.get("z")
        if isinstance(z_raw, str) and z_raw.lstrip("-").isdigit():
            return base + int(z_raw)
        if isinstance(z_raw, int):
            return base + z_raw
    return base


def validate_scene_realm(scene_id: str, realm_id: str) -> Optional[str]:
    realm = realm_id.strip().lower()
    scene = scene_id.strip()
    if not realm or not scene:
        return "missing_realm_or_scene"
    if not scene.startswith(f"{realm}/"):
        return f"scene_realm_mismatch:{scene_id}"
    return None


def validate_cobra_content(
    source: str,
    *,
    realm_id: str,
    scene_id: str,
) -> ContentValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    stats: Dict[str, object] = {}
    realm_error = validate_scene_realm(scene_id, realm_id)
    if realm_error:
        errors.append(realm_error)

    symbol_index = _load_symbol_index()
    if symbol_index is None:
        warnings.append("symbol_inventory_unavailable")

    entities = _parse_cobra_entities(source)
    unresolved_total: List[str] = []
    if symbol_index is not None:
        for entity in entities:
            akinenwun = str(entity.get("akinenwun") or "").strip()
            if not akinenwun:
                continue
            for symbol in _split_akinenwun(akinenwun):
                if symbol not in symbol_index:
                    unresolved_total.append(symbol)
            if unresolved_total:
                warnings.append(f"unresolved:{entity.get('id', 'entity')}:{'|'.join(unresolved_total)}")

    stats["entities"] = len(entities)
    stats["unresolved_count"] = len(unresolved_total)
    stats["unresolved_symbols"] = unresolved_total

    ok = len(errors) == 0
    return ContentValidationResult(ok=ok, errors=errors, warnings=warnings, stats=stats)


def validate_json_content(
    source: str,
    *,
    realm_id: str,
    scene_id: str,
) -> ContentValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    stats: Dict[str, object] = {}
    realm_error = validate_scene_realm(scene_id, realm_id)
    if realm_error:
        errors.append(realm_error)
    try:
        parsed = json.loads(source or "{}")
        if isinstance(parsed, dict):
            stats["keys"] = len(parsed.keys())
        elif isinstance(parsed, list):
            stats["items"] = len(parsed)
        else:
            stats["type"] = type(parsed).__name__
    except json.JSONDecodeError:
        errors.append("invalid_json")
    stats["bytes"] = len(source.encode("utf-8"))
    ok = len(errors) == 0
    return ContentValidationResult(ok=ok, errors=errors, warnings=warnings, stats=stats)


def build_scene_graph_content_from_cobra(
    source: str,
    *,
    realm_id: str,
    scene_id: str,
) -> Dict[str, object]:
    realm_error = validate_scene_realm(scene_id, realm_id)
    if realm_error:
        raise ValueError(realm_error)
    entities = _parse_cobra_entities(source)
    nodes: List[Dict[str, object]] = []
    for entity in entities:
        layer = _layer_for_entity(entity)
        z = _z_for_entity(entity, layer)
        node_id = str(entity.get("id") or "anon")
        nodes.append(
            {
                "node_id": node_id,
                "kind": str(entity.get("tag") or "none"),
                "x": float(entity.get("x") or 0),
                "y": float(entity.get("y") or 0),
                "metadata": {
                    "layer": layer,
                    "z": z,
                    "akinenwun": str(entity.get("akinenwun") or "").strip(),
                },
            }
        )
    return {"nodes": nodes, "edges": []}

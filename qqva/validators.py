from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Dict, List, Optional

from .shygazun_compiler import (
    compile_akinenwun_to_ir,
    default_symbol_inventory,
    derive_bilingual_cobra_surface,
    split_akinenwun,
)


@dataclass(frozen=True)
class ContentValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, object]


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

    inventory = default_symbol_inventory()
    entities = _parse_cobra_entities(source)
    unresolved_total: List[str] = []
    for entity in entities:
        entity_id = str(entity.get("id", "entity"))
        meta_obj = entity.get("meta")
        meta = meta_obj if isinstance(meta_obj, dict) else {}
        for coeff_key in ("reference_coeff_bp", "recursion_coeff_bp", "djinn_reference_coeff_bp", "djinn_recursion_coeff_bp"):
            raw = str(meta.get(coeff_key, "")).strip()
            if raw == "":
                continue
            if not re.fullmatch(r"-?\d+", raw):
                warnings.append(f"invalid_coeff_format:{entity_id}:{coeff_key}")
                continue
            parsed = int(raw)
            if parsed < 0 or parsed > 10000:
                warnings.append(f"coeff_out_of_range:{entity_id}:{coeff_key}:{parsed}")
        akinenwun = str(entity.get("akinenwun") or "").strip()
        if not akinenwun:
            continue
        ir = compile_akinenwun_to_ir(akinenwun, inventory=inventory)
        if ir["unresolved"]:
            unresolved_total.extend(ir["unresolved"])
            warnings.append(f"unresolved:{entity.get('id', 'entity')}:{'|'.join(ir['unresolved'])}")
        bilingual_surface = derive_bilingual_cobra_surface(akinenwun)
        if bilingual_surface is not None:
            trust = bilingual_surface.get("trust_contract", {})
            readiness = trust.get("downstream_readiness", {}) if isinstance(trust, dict) else {}
            if isinstance(readiness, dict):
                if readiness.get("code_surface_safe") is not True:
                    warnings.append(f"bilingual_code_surface_not_safe:{entity_id}")
                if readiness.get("placement_graph_safe") is not True:
                    warnings.append(f"bilingual_placement_graph_not_safe:{entity_id}")
                if readiness.get("anatomy_surface_safe") is not True:
                    warnings.append(f"bilingual_anatomy_surface_not_safe:{entity_id}")

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

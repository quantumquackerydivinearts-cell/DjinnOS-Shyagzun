from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ContentValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, object]


# ---------------------------------------------------------------------------
# Kernel helpers — lazy import so atelier-api starts without the kernel path
# ---------------------------------------------------------------------------

def _kernel_segment(word: str) -> tuple[List[str], str]:
    """
    Segment an Akinenwun token into akinen symbols via the kernel sub-layer.

    Returns (symbol_list, remainder).  remainder is non-empty when the token
    contains characters not found in the byte table.

    Falls back to the legacy uppercase-split heuristic if the kernel is not
    importable (e.g. in CI without the DjinnOS_Shyagzun tree on sys.path).
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _root = str(_Path(__file__).resolve().parents[3] / "DjinnOS_Shyagzun")
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from shygazun.kernel import segment_kobra  # type: ignore
        descriptors, remainder = segment_kobra(word.strip())
        return [d.symbol for d in descriptors], remainder
    except Exception:
        # Legacy fallback: split on uppercase boundaries.
        # Broken for multi-char symbols but keeps the validator working offline.
        raw = word.strip()
        if not raw:
            return [], ""
        parts: List[str] = []
        current = ""
        for ch in raw:
            if ch.isupper() and current:
                parts.append(current)
                current = ch
            else:
                current += ch
        if current:
            parts.append(current)
        return parts or [raw], ""


def _kernel_parse_wunashako(akinenwun_str: str) -> Optional[object]:
    """
    Parse an Akinenwun string as a single-token Wunashako via the kernel parser.

    Returns the ParseResult (Resolved / Echo / FrontierOpen) or None if the
    kernel is not importable.
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _root = str(_Path(__file__).resolve().parents[3] / "DjinnOS_Shyagzun")
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from shygazun.kernel import parse_kobra  # type: ignore
        token = akinenwun_str.strip()
        if not token:
            return None
        return parse_kobra(f"[{token}]")
    except Exception:
        return None


def _split_akinenwun(word: str) -> List[str]:
    """
    Split a compound Akinenwun string into its constituent akinen symbols.

    Uses the kernel sub-layer (greedy longest-match against the byte table).
    Falls back to the legacy uppercase-boundary heuristic when the kernel is
    unavailable — that heuristic breaks on multi-char symbols like Shak, Mel,
    Kazho, etc., but keeps the validator operational in offline environments.
    """
    symbols, _ = _kernel_segment(word)
    return symbols or [word]


def _load_symbol_index() -> Optional[Dict[str, object]]:
    """
    Load the byte-table symbol index directly.

    Retained for backward-compatibility with callers that pre-date the kernel
    integration.  Prefer ``_kernel_segment`` / ``_kernel_parse_wunashako`` for
    new code.
    """
    try:
        from shygazun.kernel.constants.byte_table import SHYGAZUN_SYMBOL_INDEX  # type: ignore

        if isinstance(SHYGAZUN_SYMBOL_INDEX, dict):
            return SHYGAZUN_SYMBOL_INDEX
    except Exception:
        return None
    return None


def _compile_kobra(source: str):
    """
    Compile a Kobra source string via site_services.kobra.
    Returns a KobraSceneResult or None if the service is unavailable.
    """
    try:
        from .site_services.kobra import compile_kobra_scene  # type: ignore
        return compile_kobra_scene(source)
    except Exception:
        return None


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


def validate_kobra_content(
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

    scene = _compile_kobra(source)
    if scene is None:
        warnings.append("kobra_compiler_unavailable: falling back to token scan")
        # Offline fallback: validate individual tokens via kernel segment
        unresolved: List[str] = []
        for token in source.split():
            if token in ("[]{}();:"):
                continue
            result = _kernel_parse_wunashako(token)
            if result is not None and type(result).__name__ == "Echo":
                unresolved.append(token)
                warnings.append(f"unresolved:{token}")
        stats["unresolved_count"] = len(unresolved)
        stats["unresolved_symbols"] = unresolved
        stats["entities"] = 0
    else:
        errors.extend(scene.errors)
        warnings.extend(scene.warnings)
        for span in scene.frontier_open:
            if not scene.cannabis_active:
                warnings.append(f"ambiguous_unattested:{span}")
        stats["entities"] = len(scene.entities)
        stats["frontier_open"] = len(scene.frontier_open)
        stats["cannabis_active"] = scene.cannabis_active
        stats["tongue_inventory"] = scene.tongue_inventory

        try:
            from qqva.shygazun_compiler import derive_bilingual_kobra_surface  # type: ignore
            for entity in scene.entities:
                bilingual_surface = derive_bilingual_kobra_surface(entity.id)
                if isinstance(bilingual_surface, dict):
                    trust = bilingual_surface.get("trust_contract", {})
                    readiness = trust.get("downstream_readiness", {}) if isinstance(trust, dict) else {}
                    if isinstance(readiness, dict):
                        for key, label in (
                            ("code_surface_safe",      "bilingual_code_surface_not_safe"),
                            ("placement_graph_safe",   "bilingual_placement_graph_not_safe"),
                            ("anatomy_surface_safe",   "bilingual_anatomy_surface_not_safe"),
                        ):
                            if readiness.get(key) is not True:
                                warnings.append(f"{label}:{entity.id}")
        except Exception:
            pass

    ok = len(errors) == 0
    return ContentValidationResult(ok=ok, errors=errors, warnings=warnings, stats=stats)


# Backward-compatible alias
validate_kobra_content = validate_kobra_content


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


def build_scene_graph_content_from_kobra(
    source: str,
    *,
    realm_id: str,
    scene_id: str,
) -> Dict[str, object]:
    realm_error = validate_scene_realm(scene_id, realm_id)
    if realm_error:
        raise ValueError(realm_error)

    scene = _compile_kobra(source)
    nodes: List[Dict[str, object]] = []

    if scene is not None:
        for entity in scene.entities:
            nodes.append({
                "node_id": entity.id,
                "kind":    entity.kind or "none",
                "x":       float(entity.x),
                "y":       float(entity.y),
                "metadata": {
                    "layer":    entity.layer,
                    "z":        entity.z,
                    "material": entity.material,
                    "color":    entity.color,
                    "opacity":  entity.opacity,
                },
            })

    return {"nodes": nodes, "edges": []}


# Backward-compatible alias
build_scene_graph_content_from_kobra = build_scene_graph_content_from_kobra

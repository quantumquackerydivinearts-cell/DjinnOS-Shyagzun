"""
atelier_api/site_services/kobra.py
===================================
Kobra scene compiler — replaces the old English-keyword cobra.py DSL.

Kobra source is Shygazun-native: sequences of Wunashako expressions where
declaration, dictation, and operation are inseparable. Every Wunashako is
simultaneously an ontological claim, a causal record, and a placement instruction.

Scene extraction algorithm
--------------------------
Tongue-order is the primary axis (Latin principle: positional sequence secondary).
Within each Wunashako, tokens are visited left-to-right and classified by tongue:

  Rose numeral  (decimal 0–11, tongue=Rose)  → coordinate digit
                First Rose numeral token  = x
                Second Rose numeral token = y
                Third Rose numeral token  = z (optional; default 0)
                A single-akinen Rose numeral is an AkinenNode (value 0–11).
                A multi-akinen Rose numeral is an AkinenwunNode — base-12
                positional (most-significant first).

  Rose opacity  Na / Wu / Ung               → opacity / walkability
  Rose color    Ru Ot El Ki Fu Ka AE Ga     → color token
  Sakura        Ju Jy Ji …                  → layer name
  AppleBlossom  Shak Mel Zot Puf …          → elemental material
  Daisy         Lo To Ne Gl …               → structural kind
  Cannabis      any Cannabis Tongue akinen  → deliberate flag (already on Wunashako)
  Lotus         first Lotus akinen          → experiential quality / subtype

Entity IDs are derived from position: "{x}_{y}_{z}" unless a SubStructure
header provides an explicit identifier.

Rose numeral evaluation
-----------------------
  [d₀ d₁ … dₙ] → d₀×12ⁿ + d₁×12ⁿ⁻¹ + … + dₙ×12⁰

  Single digit  AkinenNode : value = descriptor.decimal  (0–11)
  Multi digit   AkinenwunNode: positional sum over akinen decimals
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sys as _sys
from pathlib import Path as _Path

# kobra.py lives at  …/apps/atelier-api/atelier_api/site_services/kobra.py
# parents[4] = repo root (c:\DjinnOS); DjinnOS_Shyagzun is a direct child.
_KERNEL_ROOT = str(_Path(__file__).resolve().parents[4] / "DjinnOS_Shyagzun")
if _KERNEL_ROOT not in _sys.path:
    _sys.path.insert(0, _KERNEL_ROOT)

from shygazun.kernel.kobra import parse as _kobra_parse          # type: ignore
from shygazun.kernel.kobra.types import (                         # type: ignore
    AkinenNode,
    AkinenwunNode,
    Application,
    Echo,
    Expr,
    FrontierOpen,
    KobraSequence,
    KobraToken,
    Resolved,
    SubStructure,
    Wunashako,
    WunashakoGroup,
)


# ---------------------------------------------------------------------------
# Token classification sets (Rose tongue sub-vocabulary)
# ---------------------------------------------------------------------------

# Rose numeral symbol → digit value (0–11).
# These are the positional quantities, NOT byte addresses.
# Byte addresses for Rose tongue entries are higher (Ao≈32, Kiel≈36, etc.).
_ROSE_DIGIT_VALUE: dict[str, int] = {
    "Gaoh":    0,
    "Ao":      1,
    "Ye":      2,
    "Ui":      3,
    "Shu":     4,
    "Kiel":    5,
    "Yeshu":   6,
    "Lao":     7,
    "Shushy":  8,
    "Uinshu":  9,
    "Kokiel":  10,
    "Aonkiel": 11,
}

_ROSE_NUMERAL_SYMBOLS: frozenset[str] = frozenset(_ROSE_DIGIT_VALUE.keys())

_ROSE_OPACITY_SYMBOLS: frozenset[str] = frozenset({"Na", "Wu", "Ung"})

# Sakura layer token → layer name
_SAKURA_LAYER: dict[str, str] = {
    "Ju":  "base",       # Bottom / floor
    "Jy":  "ceiling",    # Top / ceiling
    "Ji":  "side",       # Side / wall
}

# Daisy structural identity → entity kind (for voxel bridge compatibility)
_DAISY_KIND: dict[str, str] = {
    "Lo": "npc",    # Segments / Identity — living, characterful entity
    "To": "prop",   # Scaffold — structural placement
    "Ne": "prop",   # Network — connective element
    "Gl": "prop",   # Membrane — surface/boundary element
}


# ---------------------------------------------------------------------------
# Rose numeral evaluation
# ---------------------------------------------------------------------------

def _is_rose_numeral_token(tok: KobraToken) -> bool:
    """True if the token represents a Rose base-12 numeral (coord digit or multi-digit)."""
    if isinstance(tok, AkinenNode):
        return (
            tok.descriptor.tongue == "Rose"
            and tok.descriptor.symbol in _ROSE_NUMERAL_SYMBOLS
        )
    # AkinenwunNode: all constituent akinen must be Rose numerals
    return all(
        d.tongue == "Rose" and d.symbol in _ROSE_NUMERAL_SYMBOLS
        for d in tok.akinen
    )


def _eval_rose_numeral(tok: KobraToken) -> int:
    """
    Evaluate a Rose numeral token to its base-12 positional value.

    AkinenNode    → digit value from _ROSE_DIGIT_VALUE  (0–11)
    AkinenwunNode → positional: d₀×12ⁿ + … + dₙ×12⁰

    Note: descriptor.decimal holds the byte address, NOT the digit value.
    Ao is at byte ~32 and represents the digit 1; Kiel is at byte ~36
    and represents the digit 5.  Always use _ROSE_DIGIT_VALUE for arithmetic.
    """
    if isinstance(tok, AkinenNode):
        return _ROSE_DIGIT_VALUE[tok.descriptor.symbol]
    # AkinenwunNode — positional base-12, most significant first
    value = 0
    for d in tok.akinen:
        value = value * 12 + _ROSE_DIGIT_VALUE[d.symbol]
    return value


# ---------------------------------------------------------------------------
# Wunashako field extractor
# ---------------------------------------------------------------------------

def _extract_fields(wunashako: Wunashako) -> dict[str, Any]:
    """
    Walk a Wunashako's tokens in tongue-order and extract scene entity fields.

    Returns a dict with keys:
      color, opacity, layer, material, kind, quality, x, y, z, deliberate
    """
    color:    str | None = None
    opacity:  str        = "Na"
    layer:    str        = "base"
    material: str | None = None
    kind:     str | None = None
    quality:  str | None = None
    coords:   list[int]  = []

    def _absorb(d_tongue: str, d_symbol: str) -> None:
        nonlocal color, opacity, layer, material, kind, quality
        if d_tongue == "Rose":
            if d_symbol in _ROSE_NUMERAL_SYMBOLS:
                pass  # handled at token level
            elif d_symbol in _ROSE_OPACITY_SYMBOLS:
                opacity = d_symbol
            else:
                color = d_symbol
        elif d_tongue == "Sakura":
            layer = _SAKURA_LAYER.get(d_symbol, d_symbol)
        elif d_tongue == "AppleBlossom":
            material = d_symbol
        elif d_tongue == "Daisy":
            kind = _DAISY_KIND.get(d_symbol, "prop")
        elif d_tongue == "Lotus":
            if quality is None:
                quality = d_symbol

    for tok in wunashako.tokens:
        if _is_rose_numeral_token(tok):
            coords.append(_eval_rose_numeral(tok))
            continue

        if isinstance(tok, AkinenNode):
            _absorb(tok.descriptor.tongue, tok.descriptor.symbol)
        else:  # AkinenwunNode
            for d in tok.akinen:
                _absorb(d.tongue, d.symbol)

    return {
        "color":    color    or "Ki",
        "opacity":  opacity,
        "layer":    layer,
        "material": material,
        "kind":     kind,
        "quality":  quality,
        "x":        coords[0] if len(coords) > 0 else 0,
        "y":        coords[1] if len(coords) > 1 else 0,
        "z":        coords[2] if len(coords) > 2 else 0,
        "deliberate": wunashako.deliberate,
    }


# ---------------------------------------------------------------------------
# AST walker — collects (optional_id, Wunashako) pairs
# ---------------------------------------------------------------------------

def _collect_wunashako(
    expr: Expr,
    pairs: list[tuple[str | None, Wunashako]],
    id_prefix: str | None = None,
) -> None:
    """
    Recursively walk an AST expression and collect Wunashako nodes.

    SubStructure: header provides the entity ID string if it resolves to a
    bare token; body is the actual Wunashako.
    """
    if isinstance(expr, Wunashako):
        pairs.append((id_prefix, expr))

    elif isinstance(expr, SubStructure):
        # header : body — header names the entity, body is the scene expression
        explicit_id: str | None = None
        if isinstance(expr.header, Wunashako) and expr.header.tokens:
            explicit_id = expr.header.tokens[0].raw
        _collect_wunashako(expr.body, pairs, id_prefix=explicit_id)

    elif isinstance(expr, KobraSequence):
        for item in expr.items:
            _collect_wunashako(item, pairs)

    elif isinstance(expr, WunashakoGroup):
        for item in expr.items:
            _collect_wunashako(item, pairs)

    elif isinstance(expr, Application):
        _collect_wunashako(expr.operator, pairs)
        _collect_wunashako(expr.operand, pairs)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class KobraEntity:
    id:       str
    x:        int = 0
    y:        int = 0
    z:        int = 0
    color:    str = "Ki"
    opacity:  str = "Na"
    layer:    str = "base"
    material: str | None = None
    kind:     str | None = None
    quality:  str | None = None
    deliberate: bool = False


@dataclass
class KobraSceneResult:
    entities:         list[KobraEntity]
    frontier_open:    list[str]          # source spans that produced FrontierOpen
    warnings:         list[str]
    errors:           list[str]
    tongue_inventory: list[str]          # unique tongue names across all Wunashako
    cannabis_active:  bool               # any deliberate FrontierOpen in the tree


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def compile_kobra_scene(source: str) -> KobraSceneResult:
    """
    Parse a Kobra source document and extract a scene entity list.

    Each Wunashako in the source becomes one KobraEntity. Tongue-order within
    each Wunashako determines field assignment (see module docstring).
    """
    entities:         list[KobraEntity] = []
    frontier_spans:   list[str]         = []
    warnings:         list[str]         = []
    errors:           list[str]         = []
    all_tongues:      dict[str, None]   = {}
    cannabis_active                     = False

    result = _kobra_parse(source)

    if isinstance(result, Echo):
        errors.append(f"{result.failure_type}: {result.context}")
        return KobraSceneResult(
            entities=[],
            frontier_open=[],
            warnings=[],
            errors=errors,
            tongue_inventory=[],
            cannabis_active=False,
        )

    if isinstance(result, FrontierOpen):
        frontier_spans.append(result.source)
        cannabis_active = result.deliberate
        # Execute candidate_a for scene extraction; candidate_b is held for attestation
        expr_to_walk = result.candidate_a
    else:
        expr_to_walk = result.expr

    pairs: list[tuple[str | None, Wunashako]] = []
    _collect_wunashako(expr_to_walk, pairs)

    for explicit_id, wunashako in pairs:
        # Accumulate tongue inventory
        for t in wunashako.tongue_order:
            all_tongues[t] = None

        fields = _extract_fields(wunashako)
        x, y, z = fields["x"], fields["y"], fields["z"]

        entity_id = explicit_id or f"{x}_{y}_{z}"

        entities.append(KobraEntity(
            id=entity_id,
            x=x,
            y=y,
            z=z,
            color=fields["color"],
            opacity=fields["opacity"],
            layer=fields["layer"],
            material=fields["material"],
            kind=fields["kind"],
            quality=fields["quality"],
            deliberate=fields["deliberate"],
        ))

    return KobraSceneResult(
        entities=entities,
        frontier_open=frontier_spans,
        warnings=warnings,
        errors=errors,
        tongue_inventory=list(all_tongues.keys()),
        cannabis_active=cannabis_active,
    )


def entities_to_voxels(entities: list[KobraEntity]) -> list[dict[str, Any]]:
    """
    Convert KobraEntity list to the renderer voxel dict format consumed by
    build_renderer_pack_v2.py (schema qqva.voxel_scene.v1).
    """
    voxels = []
    for e in entities:
        v: dict[str, Any] = {
            "id":       e.id,
            "type":     e.kind or "floor",
            "x":        e.x,
            "y":        e.y,
            "z":        e.z,
            "color":    e.color,
            "layer":    e.layer,
            "meta": {
                "opacity":    e.opacity,
                "deliberate": e.deliberate,
            },
        }
        if e.material:
            v["material"] = e.material
        if e.quality:
            v["meta"]["quality"] = e.quality
        voxels.append(v)
    return voxels


def scene_to_bilingual_trust(scene: KobraSceneResult) -> dict[str, Any]:
    """
    Derive a BilingualTrust-compatible dict from a KobraSceneResult.

    In Kobra, semantic authority is carried structurally (tongue inventory,
    Cannabis Tongue presence, parse resolution state) rather than via
    explicit LexXXX annotations.
    """
    return {
        "authority_level":   "resolved" if not scene.errors else "unknown",
        "trust_grade":       "attested" if not scene.frontier_open else "frontier",
        "chirality":         [],
        "time_topology":     [],
        "space_operator":    [],
        "network_role":      [],
        "cluster_role":      [],
        "axis":              [],
        "tongue_projection": scene.tongue_inventory,
        "cannabis_mode":     ["deliberate"] if scene.cannabis_active else [],
    }
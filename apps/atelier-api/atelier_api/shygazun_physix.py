"""
Shygazun Physix derivation engine.

Each Physix variable is independently tagged to its canonical akinen (byte)
in the Shygazun byte table. The float values for continuous variables
(valence, x, y, scale) are preserved alongside their byte tags.
Discrete variables (shape, init_degree) carry their value alongside.

Mapping (confirmed):
  valence  → Rose:     Ha (43) if >0.5 | Ga (44) if <0.5 | Na (46) if ==0.5
  x        → Aster:    Ep  (148, Assign space)        — float preserved
  y        → Aster:    Ifa (150, Parse space)          — float preserved
  scale    → Grapevine: Sa (156, Feast table / root volume) — float preserved

  shape:
    triangle  → Grapevine: Mek  (166, Call / emit event)
    square    → Lotus:     Ty   (0,   Earth Initiator / material beginning)
    pentagon  → Daisy:     To   (85,  Scaffold / Framework)
    hexagon   → Daisy:     Kael (82,  Cluster / Fruit / Flower)
    heptagon  → Grapevine: Kysha(181, Consensus choir)
    circle    → AppleBlossom: A (98,  Mind +)

  init_degree:
    1 solo        → Lotus:        Ta   (9,   Active being / presence)
    2 duo         → Sakura:       Da   (56,  Meeting / Conjoined)
    3 institution → Daisy:        Ne   (87,  Network / System)
    4 family      → Sakura:       De   (58,  Domesticating / Staying)
    5 state       → Grapevine:    Kyvos(180, Ring topology)
    6 reboot      → AppleBlossom: Alky (110, Alkahest / universal solvent)
    7 delta_space → Aster:        As   (147, Frozen time)
    8 global      → Cannabis:     Soa  (193, Conscious persistence)
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Byte tag tables
# ---------------------------------------------------------------------------

_VALENCE_POSITIVE = {"byte": 43, "symbol": "Ha", "meaning": "Absolute Positive"}
_VALENCE_NEGATIVE = {"byte": 44, "symbol": "Ga", "meaning": "Absolute Negative"}
_VALENCE_NEUTRAL  = {"byte": 46, "symbol": "Na", "meaning": "Neutral / Integration"}

_X_TAG    = {"byte": 148, "symbol": "Ep",  "meaning": "Assign space"}
_Y_TAG    = {"byte": 150, "symbol": "Ifa", "meaning": "Parse space"}
_SCALE_TAG = {"byte": 156, "symbol": "Sa", "meaning": "Feast table / root volume"}

_SHAPE_TAGS: dict[str, dict[str, Any]] = {
    "triangle": {"byte": 166, "symbol": "Mek",   "meaning": "Call / emit event"},
    "square":   {"byte": 0,   "symbol": "Ty",    "meaning": "Earth Initiator / material beginning"},
    "pentagon": {"byte": 85,  "symbol": "To",    "meaning": "Scaffold / Framework"},
    "hexagon":  {"byte": 82,  "symbol": "Kael",  "meaning": "Cluster / Fruit / Flower"},
    "heptagon": {"byte": 181, "symbol": "Kysha", "meaning": "Consensus choir"},
    "circle":   {"byte": 98,  "symbol": "A",     "meaning": "Mind +"},
}

_INIT_DEGREE_TAGS: dict[int, dict[str, Any]] = {
    1: {"byte": 9,   "symbol": "Ta",    "meaning": "Active being / presence",          "label": "solo"},
    2: {"byte": 56,  "symbol": "Da",    "meaning": "Meeting / Conjoined",               "label": "duo"},
    3: {"byte": 87,  "symbol": "Ne",    "meaning": "Network / System",                  "label": "institution"},
    4: {"byte": 58,  "symbol": "De",    "meaning": "Domesticating / Staying",            "label": "family"},
    5: {"byte": 180, "symbol": "Kyvos", "meaning": "Ring topology",                      "label": "state"},
    6: {"byte": 110, "symbol": "Alky",  "meaning": "Alkahest / universal solvent",       "label": "reboot"},
    7: {"byte": 147, "symbol": "As",    "meaning": "Frozen time",                        "label": "delta_space"},
    8: {"byte": 193, "symbol": "Soa",   "meaning": "Conscious persistence",              "label": "global"},
}

VALID_SHAPES = set(_SHAPE_TAGS.keys())
VALID_INIT_DEGREES = set(_INIT_DEGREE_TAGS.keys())


# ---------------------------------------------------------------------------
# Utterance composition
# ---------------------------------------------------------------------------

def compose_utterance(tagged: dict[str, Any]) -> str:
    """
    Compose a Shygazun utterance from a derived Physix record.

    Grammar:
      <valence_symbol> [<shape_symbol><init_symbol> ...]

    The field valence (Ha/Ga/Na) sets the polarity of the whole utterance.
    Each placement becomes a shape-cognition compound: shape symbol fused
    with the init_degree symbol (no separator — akinenwun compounding).
    Placements are space-separated from each other.

    Example output: "Ha MekTa TyDa KaelNe"
    """
    parts: list[str] = []

    valence_tag = tagged.get("field_valence", {})
    valence_symbol = valence_tag.get("symbol", "Na")
    parts.append(valence_symbol)

    for p in tagged.get("placements", []):
        tags = p.get("shygazun_tags", {})
        shape_sym  = tags.get("shape", {}).get("symbol", "")
        degree_sym = tags.get("init_degree", {}).get("symbol", "")
        if shape_sym or degree_sym:
            parts.append(f"{shape_sym}{degree_sym}")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------

def _tag_valence(value: float) -> dict[str, Any]:
    if value > 0.5:
        tag = _VALENCE_POSITIVE
    elif value < 0.5:
        tag = _VALENCE_NEGATIVE
    else:
        tag = _VALENCE_NEUTRAL
    return {"value": round(float(value), 6), **tag}


def _tag_float(value: float, tag: dict[str, Any]) -> dict[str, Any]:
    return {"value": round(float(value), 6), **tag}


def _tag_shape(shape: str) -> dict[str, Any]:
    tag = _SHAPE_TAGS.get(shape)
    if tag is None:
        raise ValueError(f"unknown_shape:{shape}")
    return {"value": shape, **tag}


def _tag_init_degree(degree: int) -> dict[str, Any]:
    tag = _INIT_DEGREE_TAGS.get(int(degree))
    if tag is None:
        raise ValueError(f"unknown_init_degree:{degree}")
    return {"value": int(degree), **tag}


def derive(physix_record: dict[str, Any]) -> dict[str, Any]:
    """
    Takes a raw Physix vote record and returns the full Shygazun-tagged structure.

    Input shape:
      {
        "field_valence": 0.73,
        "placements": [
          {
            "shape": "triangle",
            "x": 0.42,
            "y": 0.67,
            "scale": 0.15,
            "init_degree": 3
          }
        ]
      }

    Output: same structure with shygazun_tags added to each placement
    and field_valence expanded to its tagged form.
    """
    raw_valence = physix_record.get("field_valence")
    if raw_valence is None:
        raise ValueError("field_valence_required")

    tagged_placements = []
    for i, placement in enumerate(physix_record.get("placements", [])):
        shape   = placement.get("shape")
        x       = placement.get("x")
        y       = placement.get("y")
        scale   = placement.get("scale")
        degree  = placement.get("init_degree")

        if shape is None:   raise ValueError(f"placement[{i}]:shape_required")
        if x is None:       raise ValueError(f"placement[{i}]:x_required")
        if y is None:       raise ValueError(f"placement[{i}]:y_required")
        if scale is None:   raise ValueError(f"placement[{i}]:scale_required")
        if degree is None:  raise ValueError(f"placement[{i}]:init_degree_required")

        if not (0.0 <= float(x) <= 1.0):    raise ValueError(f"placement[{i}]:x_out_of_range")
        if not (0.0 <= float(y) <= 1.0):    raise ValueError(f"placement[{i}]:y_out_of_range")
        if not (0.0 <= float(scale) <= 1.0): raise ValueError(f"placement[{i}]:scale_out_of_range")

        tagged_placements.append({
            "shygazun_tags": {
                "shape":       _tag_shape(shape),
                "x":           _tag_float(x, _X_TAG),
                "y":           _tag_float(y, _Y_TAG),
                "scale":       _tag_float(scale, _SCALE_TAG),
                "init_degree": _tag_init_degree(degree),
            }
        })

    return {
        "field_valence": _tag_valence(raw_valence),
        "placements": tagged_placements,
    }

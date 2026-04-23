"""
shygazun/kernel/kobra/topology.py
==================================
Topological relevance layer — first five tongues of the topological series.

Fold, Topology, Phase, Gradient, Curvature are the geometric vocabulary
for relevance declarations. They describe the SHAPE of the relationship
between a Cannabis entry and its target rather than declaring relevance
as a semantic fact.

The DyskaSoaShun reads these declarations when making gate decisions at
game boundaries. The perspectival propagation layer reads them when
determining how far a witness event travels through the field.

Tongue coverage
---------------
  Fold        — gradient between compression (Jos) and exposure (Vex)
                across four scales. Where two things are in each other's
                gradient. The fold law.
  Topology    — connective tissue types: scaffold bond (Torev),
                membrane network (Glaen), fulcrum switch (Fulnaz),
                vortex passage (Zhifan). What kind of connection exists.
  Phase       — transition states across the elemental circuit.
                Fire→Water→Air→Earth→Kael→Shakti and back.
                What kind of transformation the relationship undergoes.
  Gradient    — descent (Drev), barrier (Skath), saddle (Phelv),
                basin (Zoln). The energetic character of the relationship.
  Curvature   — bowl (Vresk), dome (Tholv), saddle (Frenz), flat (Glathn).
                The shape of the relevance space around a Cannabis entry.

Relevance declaration structure
--------------------------------
A relevance declaration is a dict produced by parse_relevance_declaration()
from a token string. It carries:

  tongue        — which topological tongue is operative
  subtype       — the specific entry within that tongue
  scale         — atomic / planetary / stellar / cosmological (Fold only)
  source        — the Cannabis entry akinen symbol this declaration applies to
  target        — the structural dialogue element or scene address it connects to
  declaration   — the full raw token string
  geometry      — computed geometric summary (see _compute_geometry)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Fold tongue — compression/exposure gradient
# ---------------------------------------------------------------------------

# Fold entries organised by compression pole (Jos) and exposure pole (Vex)
# with intermediate zones Blis (bilateral flow) and Das (open spatial).
# Each entry exists at four scales: atomic, planetary, stellar, cosmological.

FOLD_SUBTYPES: Dict[str, Dict[str, Any]] = {
    # Jos×Jos — maximum compression at each scale
    "Josje":  {"poles": ("Jos","Jos"), "scale": "atomic",       "character": "maximum_compression", "meaning": "nucleus / hydrophobic core"},
    "Josji":  {"poles": ("Jos","Jos"), "scale": "planetary",    "character": "maximum_compression", "meaning": "iron core"},
    "Josja":  {"poles": ("Jos","Jos"), "scale": "stellar",      "character": "maximum_compression", "meaning": "stellar core / fusion site"},
    "Josjo":  {"poles": ("Jos","Jos"), "scale": "cosmological", "character": "maximum_compression", "meaning": "black hole interior / Tartarus"},

    # Jos×Vex — fold-defining boundary (compression meeting exposure)
    "Josve":  {"poles": ("Jos","Vex"), "scale": "atomic",       "character": "fold_boundary",       "meaning": "electron-nucleus interface"},
    "Josvi":  {"poles": ("Jos","Vex"), "scale": "planetary",    "character": "fold_boundary",       "meaning": "planetary surface"},
    "Josva":  {"poles": ("Jos","Vex"), "scale": "stellar",      "character": "fold_boundary",       "meaning": "stellar photosphere"},
    "Josvo":  {"poles": ("Jos","Vex"), "scale": "cosmological", "character": "fold_boundary",       "meaning": "light boundary / Olympus approaching"},

    # Vex×Vex — maximum exposure at each scale
    "Vexe":   {"poles": ("Vex","Vex"), "scale": "atomic",       "character": "maximum_exposure",    "meaning": "electron cloud surface / all chemical bonding"},
    "Vexi":   {"poles": ("Vex","Vex"), "scale": "planetary",    "character": "maximum_exposure",    "meaning": "planetary atmosphere surface"},
    "Vexa":   {"poles": ("Vex","Vex"), "scale": "stellar",      "character": "maximum_exposure",    "meaning": "stellar corona"},
    "Vexo":   {"poles": ("Vex","Vex"), "scale": "cosmological", "character": "maximum_exposure",    "meaning": "Olympus / light boundary"},

    # Blis×Blis — bilateral flow zones
    "Blisle": {"poles": ("Blis","Blis"), "scale": "atomic",       "character": "bilateral_flow",    "meaning": "electron cloud interior"},
    "Blisli": {"poles": ("Blis","Blis"), "scale": "planetary",    "character": "bilateral_flow",    "meaning": "liquid outer core"},
    "Blisla": {"poles": ("Blis","Blis"), "scale": "stellar",      "character": "bilateral_flow",    "meaning": "stellar envelope"},
    "Blislo": {"poles": ("Blis","Blis"), "scale": "cosmological", "character": "bilateral_flow",    "meaning": "intergalactic medium"},

    # Blis×Vex — hydrophilic surface (flow meeting exposure)
    "Blisve": {"poles": ("Blis","Vex"), "scale": "atomic",       "character": "reactive_surface",   "meaning": "outer valence shell / enzyme active site"},
    "Blisvi": {"poles": ("Blis","Vex"), "scale": "planetary",    "character": "reactive_surface",   "meaning": "surface-atmosphere interface / biosphere ground"},
    "Blisva": {"poles": ("Blis","Vex"), "scale": "stellar",      "character": "reactive_surface",   "meaning": "stellar chromosphere"},
    "Blisvo": {"poles": ("Blis","Vex"), "scale": "cosmological", "character": "reactive_surface",   "meaning": "cosmic web filament surface"},

    # Das×Das — open spatial zones
    "Dasde":  {"poles": ("Das","Das"), "scale": "atomic",       "character": "maximum_openness",    "meaning": "outer electron probability distribution"},
    "Dasdi":  {"poles": ("Das","Das"), "scale": "planetary",    "character": "maximum_openness",    "meaning": "magnetosphere"},
    "Dasda":  {"poles": ("Das","Das"), "scale": "stellar",      "character": "maximum_openness",    "meaning": "stellar wind"},
    "Dasdo":  {"poles": ("Das","Das"), "scale": "cosmological", "character": "maximum_openness",    "meaning": "intergalactic void"},
}

# Fold pole ordering — compression to exposure
FOLD_POLE_ORDER = ("Jos", "Blis", "Das", "Vex")


def fold_gradient_position(subtype: str) -> float:
    """
    Return a 0.0–1.0 position on the fold gradient for a given subtype.
    0.0 = maximum compression (Jos×Jos), 1.0 = maximum exposure (Vex×Vex).
    """
    entry = FOLD_SUBTYPES.get(subtype)
    if not entry:
        return 0.5
    poles = entry["poles"]
    indices = [FOLD_POLE_ORDER.index(p) if p in FOLD_POLE_ORDER else 1 for p in poles]
    return sum(indices) / (2 * (len(FOLD_POLE_ORDER) - 1))


# ---------------------------------------------------------------------------
# Topology tongue — connective tissue types
# ---------------------------------------------------------------------------

TOPOLOGY_CONNECTORS = {
    "Torev":  {"kind": "scaffold_bond",    "meaning": "covalent backbone — load-bearing, permanent, structural"},
    "Glaen":  {"kind": "membrane_network", "meaning": "partitioned propagation — selective, boundary-maintaining"},
    "Fulnaz": {"kind": "fulcrum_switch",   "meaning": "conformational pivot — state-change, switching event"},
    "Zhifan": {"kind": "vortex_passage",   "meaning": "information-focal threading — conduit, processing point"},
}

# Topology dimension modifiers — applied to connector types
TOPOLOGY_DIMENSIONS = {
    "Mind+":   "conscious / aware",
    "Mind-":   "below awareness / automated",
    "Space+":  "extending spatially",
    "Space-":  "concentrating inward",
    "Time+":   "reaching forward / anticipatory",
    "Time-":   "accumulated / retrospective",
}


def topology_connection_strength(connector: str, dimension: Optional[str] = None) -> float:
    """
    Return a 0.0–1.0 connection strength for a topology connector type.
    Scaffold bonds are strongest; vortex passages most information-focal.
    """
    strengths = {
        "scaffold_bond":    1.0,
        "membrane_network": 0.7,
        "fulcrum_switch":   0.5,
        "vortex_passage":   0.8,
    }
    entry = TOPOLOGY_CONNECTORS.get(connector, {})
    base = strengths.get(entry.get("kind", ""), 0.5)
    if dimension in ("Mind+", "Time+"):
        base = min(1.0, base + 0.1)
    return base


# ---------------------------------------------------------------------------
# Phase tongue — elemental transition states
# ---------------------------------------------------------------------------

# The elemental circuit: Fire→Water→Air→Earth→Kael→Shakti→Kael (Möbius)
PHASE_CIRCUIT = ("Fire", "Water", "Air", "Earth", "Kael", "Shakti")

PHASE_TRANSITIONS: Dict[str, Dict[str, Any]] = {
    # Fire→Water (Nigredo→Albedo)
    "Shavka": {"from": "Fire",  "to": "Water",  "axis": "Mind+",  "meaning": "conscious hydrophobic collapse"},
    "Shavki": {"from": "Fire",  "to": "Water",  "axis": "Mind-",  "meaning": "unconscious hydrophobic collapse"},
    "Shavku": {"from": "Fire",  "to": "Water",  "axis": "Space+", "meaning": "hydrophobic collapse expanding"},
    "Shavko": {"from": "Fire",  "to": "Water",  "axis": "Space-", "meaning": "hydrophobic collapse concentrating"},
    "Shavky": {"from": "Fire",  "to": "Water",  "axis": "Time+",  "meaning": "collapse reaching forward"},
    "Shavku-t":{"from":"Fire",  "to": "Water",  "axis": "Time-",  "meaning": "collapse as accumulated ground"},

    # Water→Air (Albedo→Citrinitas)
    "Blispa": {"from": "Water", "to": "Air",    "axis": "Mind+",  "meaning": "conscious molten globule"},
    "Blispi": {"from": "Water", "to": "Air",    "axis": "Mind-",  "meaning": "unconscious molten globule"},
    "Blispu": {"from": "Water", "to": "Air",    "axis": "Space+", "meaning": "molten globule expanding"},
    "Blispo": {"from": "Water", "to": "Air",    "axis": "Space-", "meaning": "molten globule concentrating"},

    # Air→Earth (Citrinitas→Rubedo)
    "Pufzota":{"from": "Air",   "to": "Earth",  "axis": "Mind+",  "meaning": "conscious cooperative folding"},
    "Pufzoti":{"from": "Air",   "to": "Earth",  "axis": "Mind-",  "meaning": "unconscious cooperative folding"},
    "Pufzotu":{"from": "Air",   "to": "Earth",  "axis": "Space+", "meaning": "cooperative folding expanding"},
    "Pufzoto":{"from": "Air",   "to": "Earth",  "axis": "Space-", "meaning": "cooperative folding concentrating"},

    # Earth→Fire (Rubedo completing)
    "Zotvex": {"from": "Earth", "to": "Fire",   "axis": "Mind+",  "meaning": "conscious allostery"},
    "Zotvei": {"from": "Earth", "to": "Fire",   "axis": "Mind-",  "meaning": "unconscious allostery"},
    "Zotveu": {"from": "Earth", "to": "Fire",   "axis": "Space+", "meaning": "allosteric signal expanding"},
    "Zotveo": {"from": "Earth", "to": "Fire",   "axis": "Space-", "meaning": "allosteric signal concentrating"},

    # Kael→Shakti
    "Kaelsha":{"from": "Kael",  "to": "Shakti", "axis": "Mind+",  "meaning": "conscious phase separation"},
    "Kaelshi":{"from": "Kael",  "to": "Shakti", "axis": "Mind-",  "meaning": "unconscious phase separation"},

    # Shakti→Kael
    "Shaktika":{"from":"Shakti","to": "Kael",   "axis": "Mind+",  "meaning": "conscious exotic state generation"},
    "Shaktiki":{"from":"Shakti","to": "Kael",   "axis": "Mind-",  "meaning": "unconscious exotic state generation"},

    # Möbius closures
    "Mobrev": {"from": "Shakti","to": "Fire",   "axis": "closure","meaning": "surface recognising itself / full circuit"},
    "Mobrov": {"from": "Shakti","to": "Fire",   "axis": "closure","meaning": "surface holding what traversal revealed"},
    "Mobriv": {"from": "Shakti","to": "Fire",   "axis": "closure","meaning": "circuit generating the next circuit"},
    "Mobruv": {"from": "Shakti","to": "Fire",   "axis": "closure","meaning": "surface that was always one surface"},
}


def phase_circuit_distance(transition: str) -> int:
    """
    Return the number of steps in the elemental circuit between
    the from and to elements of a phase transition. 0 = same element.
    Möbius closures return the full circuit length.
    """
    entry = PHASE_TRANSITIONS.get(transition)
    if not entry:
        return 0
    if entry["axis"] == "closure":
        return len(PHASE_CIRCUIT)
    try:
        from_idx = PHASE_CIRCUIT.index(entry["from"])
        to_idx   = PHASE_CIRCUIT.index(entry["to"])
        return (to_idx - from_idx) % len(PHASE_CIRCUIT)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Gradient tongue — energetic character
# ---------------------------------------------------------------------------

GRADIENT_TYPES: Dict[str, Dict[str, Any]] = {
    "Drev":  {"character": "descent",  "direction": "downhill",  "meaning": "spontaneous, natural propagation toward lower energy"},
    "Skath": {"character": "barrier",  "direction": "uphill",    "meaning": "activation energy required — resists propagation"},
    "Phelv": {"character": "saddle",   "direction": "bifurcate", "meaning": "transition state — bifurcates into two possible paths"},
    "Zoln":  {"character": "basin",    "direction": "stable",    "meaning": "stable minimum — self-maintaining relevance"},
}

# Gradient combinations — cross-products of the four types at four scales
GRADIENT_SCALES = ("atomic", "planetary", "stellar", "cosmological")

GRADIENT_ENTRIES: Dict[str, Dict[str, Any]] = {
    # Drev×Drev — double descent
    "Dreve": {"types": ("Drev","Drev"), "scale": "atomic",       "meaning": "spontaneous electron orbital decay"},
    "Drevi": {"types": ("Drev","Drev"), "scale": "planetary",    "meaning": "mantle convection completing"},
    "Dreva": {"types": ("Drev","Drev"), "scale": "stellar",      "meaning": "nuclear burning as perpetual descent"},
    "Drevo": {"types": ("Drev","Drev"), "scale": "cosmological", "meaning": "large-scale structure formation"},

    # Skath×Skath — double barrier
    "Skathe": {"types": ("Skath","Skath"), "scale": "atomic",       "meaning": "quantum activation barrier"},
    "Skathi": {"types": ("Skath","Skath"), "scale": "planetary",    "meaning": "mountain-building against gravity"},
    "Skatha": {"types": ("Skath","Skath"), "scale": "stellar",      "meaning": "pre-main-sequence angular momentum barrier"},
    "Skatho": {"types": ("Skath","Skath"), "scale": "cosmological", "meaning": "cosmological constant as double-barrier"},

    # Phelv×Phelv — double saddle
    "Phelve": {"types": ("Phelv","Phelv"), "scale": "atomic",       "meaning": "chemical transition state"},
    "Phelvi": {"types": ("Phelv","Phelv"), "scale": "planetary",    "meaning": "climate tipping point"},
    "Phelva": {"types": ("Phelv","Phelv"), "scale": "stellar",      "meaning": "Chandrasekhar limit"},
    "Phelvo": {"types": ("Phelv","Phelv"), "scale": "cosmological", "meaning": "inflationary transition state"},

    # Zoln×Zoln — double basin
    "Zolne": {"types": ("Zoln","Zoln"), "scale": "atomic",       "meaning": "electron ground state"},
    "Zolni": {"types": ("Zoln","Zoln"), "scale": "planetary",    "meaning": "planetary isostatic equilibrium"},
    "Zolna": {"types": ("Zoln","Zoln"), "scale": "stellar",      "meaning": "main sequence / stellar equilibrium"},
    "Zolno": {"types": ("Zoln","Zoln"), "scale": "cosmological", "meaning": "flat cosmological geometry"},

    # Drev×Skath — fold boundary tension
    "Drevske": {"types": ("Drev","Skath"), "scale": "atomic",       "meaning": "atomic fold boundary"},
    "Drevski": {"types": ("Drev","Skath"), "scale": "planetary",    "meaning": "core-mantle boundary"},
    "Drevska": {"types": ("Drev","Skath"), "scale": "stellar",      "meaning": "stellar photosphere"},
    "Drevsko": {"types": ("Drev","Skath"), "scale": "cosmological", "meaning": "cosmic horizon as gradient tension"},

    # Drev×Zoln — descent completing into basin
    "Drevze": {"types": ("Drev","Zoln"), "scale": "atomic",       "meaning": "radiative decay completing"},
    "Drevzi": {"types": ("Drev","Zoln"), "scale": "planetary",    "meaning": "subducted material arriving at mantle basin"},
    "Drevza": {"types": ("Drev","Zoln"), "scale": "stellar",      "meaning": "stellar collapse completing"},
    "Drevzo": {"types": ("Drev","Zoln"), "scale": "cosmological", "meaning": "universe descending toward maximum entropy"},

    # Skath×Zoln — barrier finding basin
    "Skathze": {"types": ("Skath","Zoln"), "scale": "atomic",       "meaning": "metastable excited state"},
    "Skathzi": {"types": ("Skath","Zoln"), "scale": "planetary",    "meaning": "volcanic plateau"},
    "Skathza": {"types": ("Skath","Zoln"), "scale": "stellar",      "meaning": "white dwarf stability zone"},
    "Skathzo": {"types": ("Skath","Zoln"), "scale": "cosmological", "meaning": "false vacuum stability"},

    # Phelv×Zoln — saddle completing into basin
    "Phelvze": {"types": ("Phelv","Zoln"), "scale": "atomic",       "meaning": "bond formation completing"},
    "Phelvzi": {"types": ("Phelv","Zoln"), "scale": "planetary",    "meaning": "post-tipping-point stabilisation"},
    "Phelvza": {"types": ("Phelv","Zoln"), "scale": "stellar",      "meaning": "neutron star formation"},
    "Phelvzo": {"types": ("Phelv","Zoln"), "scale": "cosmological", "meaning": "electroweak symmetry breaking"},
}


def gradient_propagation_likelihood(entry: str) -> float:
    """
    Return 0.0–1.0 likelihood that a relevance relationship with this
    gradient character will propagate across a boundary.
    Descent = high, basin = high (stable), barrier = low, saddle = medium.
    """
    data = GRADIENT_ENTRIES.get(entry, {})
    types = data.get("types", ())
    scores = {"Drev": 0.85, "Zoln": 0.9, "Phelv": 0.5, "Skath": 0.2}
    if not types:
        return 0.5
    return sum(scores.get(t, 0.5) for t in types) / len(types)


# ---------------------------------------------------------------------------
# Curvature tongue — shape of the relevance space
# ---------------------------------------------------------------------------

CURVATURE_TYPES: Dict[str, Dict[str, Any]] = {
    "Vresk":  {"shape": "bowl",   "meaning": "positive curvature — convergent, attractive, self-reinforcing"},
    "Tholv":  {"shape": "dome",   "meaning": "negative curvature — divergent, repulsive, dispersive"},
    "Frenz":  {"shape": "saddle", "meaning": "mixed curvature — bifurcating, two possible relevance paths"},
    "Glathn": {"shape": "flat",   "meaning": "near-zero curvature — neutral, weakly constraining"},
}

CURVATURE_ENTRIES: Dict[str, Dict[str, Any]] = {
    # Vresk×Vresk — double bowl
    "Vreske": {"types": ("Vresk","Vresk"), "scale": "atomic",       "meaning": "zero-point energy confinement"},
    "Vreski": {"types": ("Vresk","Vresk"), "scale": "planetary",    "meaning": "deep gravitational basin"},
    "Vreska": {"types": ("Vresk","Vresk"), "scale": "stellar",      "meaning": "stellar gravitational well"},
    "Vresko": {"types": ("Vresk","Vresk"), "scale": "cosmological", "meaning": "dark matter potential well"},

    # Tholv×Tholv — double dome
    "Tholve": {"types": ("Tholv","Tholv"), "scale": "atomic",       "meaning": "repulsive potential at short range"},
    "Tholvi": {"types": ("Tholv","Tholv"), "scale": "planetary",    "meaning": "mountain ridge / continental divide"},
    "Tholva": {"types": ("Tholv","Tholv"), "scale": "stellar",      "meaning": "radiation-pressure dome"},
    "Tholvo": {"types": ("Tholv","Tholv"), "scale": "cosmological", "meaning": "dark energy repulsive curvature"},

    # Frenz×Frenz — double saddle
    "Frenze": {"types": ("Frenz","Frenz"), "scale": "atomic",       "meaning": "bimolecular collision surface"},
    "Frenzi": {"types": ("Frenz","Frenz"), "scale": "planetary",    "meaning": "tectonic triple junction"},
    "Frenza": {"types": ("Frenz","Frenz"), "scale": "stellar",      "meaning": "Lagrange L1 point geometry"},
    "Frenzo": {"types": ("Frenz","Frenz"), "scale": "cosmological", "meaning": "cosmic filament intersection"},

    # Glathn×Glathn — double flat
    "Glathne": {"types": ("Glathn","Glathn"), "scale": "atomic",       "meaning": "Rydberg state / near-free electron"},
    "Glathni": {"types": ("Glathn","Glathn"), "scale": "planetary",    "meaning": "continental craton"},
    "Glathna": {"types": ("Glathn","Glathn"), "scale": "stellar",      "meaning": "red giant envelope"},
    "Glathno": {"types": ("Glathn","Glathn"), "scale": "cosmological", "meaning": "cosmic void"},

    # Vresk×Tholv — curvature inversion (bowl meeting dome)
    "Vreskthe": {"types": ("Vresk","Tholv"), "scale": "atomic",       "meaning": "equilibrium bond length"},
    "Vreskthi": {"types": ("Vresk","Tholv"), "scale": "planetary",    "meaning": "mountain lake / bowl on dome"},
    "Vresktha": {"types": ("Vresk","Tholv"), "scale": "stellar",      "meaning": "stellar core-envelope boundary"},
    "Vresktho": {"types": ("Vresk","Tholv"), "scale": "cosmological", "meaning": "galaxy cluster edge"},

    # Vresk×Frenz — bowl approaching saddle
    "Vreskfre": {"types": ("Vresk","Frenz"), "scale": "atomic",       "meaning": "pre-reactive van der Waals well"},
    "Vreskfri": {"types": ("Vresk","Frenz"), "scale": "planetary",    "meaning": "fjord approaching basin"},
    "Vreskfra": {"types": ("Vresk","Frenz"), "scale": "stellar",      "meaning": "accretion disk approaching stable orbit"},
    "Vreskfro": {"types": ("Vresk","Frenz"), "scale": "cosmological", "meaning": "galaxy infall approaching cluster saddle"},

    # Vresk×Glathn — bowl flattening
    "Vreskgle": {"types": ("Vresk","Glathn"), "scale": "atomic",       "meaning": "dissociation threshold"},
    "Vreskgli": {"types": ("Vresk","Glathn"), "scale": "planetary",    "meaning": "continental shelf"},
    "Vreskgla": {"types": ("Vresk","Glathn"), "scale": "stellar",      "meaning": "stellar potential grading to flat"},
    "Vreskglo": {"types": ("Vresk","Glathn"), "scale": "cosmological", "meaning": "galaxy halo edge"},

    # Tholv×Frenz — dome meeting saddle
    "Tholvfre": {"types": ("Tholv","Frenz"), "scale": "atomic",       "meaning": "potential barrier with saddle on flank"},
    "Tholvfri": {"types": ("Tholv","Frenz"), "scale": "planetary",    "meaning": "volcanic caldera edge meeting rift"},
    "Tholvfra": {"types": ("Tholv","Frenz"), "scale": "stellar",      "meaning": "stellar wind meeting heliopause saddle"},
    "Tholvfro": {"types": ("Tholv","Frenz"), "scale": "cosmological", "meaning": "dark energy dome meeting void-filament saddle"},

    # Frenz×Glathn — saddle flattening
    "Frenzgle": {"types": ("Frenz","Glathn"), "scale": "atomic",       "meaning": "broad flat-top barrier / Hammond plateau"},
    "Frenzgli": {"types": ("Frenz","Glathn"), "scale": "planetary",    "meaning": "mountain pass widening to plateau"},
    "Frenzgla": {"types": ("Frenz","Glathn"), "scale": "stellar",      "meaning": "binary Lagrange point broadening"},
    "Frenzglo": {"types": ("Frenz","Glathn"), "scale": "cosmological", "meaning": "cosmic web node relaxing to expansion"},
}


def curvature_convergence(entry: str) -> float:
    """
    Return 0.0–1.0 convergence score for a curvature entry.
    Bowl = highly convergent (1.0), dome = divergent (0.0),
    saddle = bifurcating (0.5), flat = neutral (0.5).
    """
    data = CURVATURE_ENTRIES.get(entry, {})
    types = data.get("types", ())
    scores = {"Vresk": 1.0, "Tholv": 0.0, "Frenz": 0.5, "Glathn": 0.5}
    if not types:
        return 0.5
    return sum(scores.get(t, 0.5) for t in types) / len(types)


# ---------------------------------------------------------------------------
# Relevance declaration
# ---------------------------------------------------------------------------

@dataclass
class RelevanceDeclaration:
    """
    A topological relevance declaration linking a Cannabis entry
    to a structural target.

    Produced by parse_relevance_declaration() from a Kobra token string.
    Consumed by the DyskaSoaShun gate logic and perspectival propagation layer.
    """
    tongue:          str                    # "Fold" | "Topology" | "Phase" | "Gradient" | "Curvature"
    subtype:         str                    # specific entry within the tongue
    source:          str                    # Cannabis akinen symbol this applies to
    target:          str                    # scene address or structural dialogue element
    declaration:     str                    # full raw token string
    geometry:        Dict[str, Any]         # computed geometric summary
    scale:           Optional[str] = None   # Fold scale if applicable
    axis:            Optional[str] = None   # Phase axis if applicable


def _compute_geometry(tongue: str, subtype: str) -> Dict[str, Any]:
    """
    Compute a geometric summary for a relevance declaration.
    This is the value the DyskaSoaShun reads when making gate decisions.
    """
    geometry: Dict[str, Any] = {"tongue": tongue, "subtype": subtype}

    if tongue == "Fold":
        geometry["gradient_position"] = fold_gradient_position(subtype)
        entry = FOLD_SUBTYPES.get(subtype, {})
        geometry["character"] = entry.get("character", "unknown")
        geometry["scale"] = entry.get("scale", "unknown")
        geometry["propagates"] = geometry["gradient_position"] > 0.3

    elif tongue == "Topology":
        entry = TOPOLOGY_CONNECTORS.get(subtype, {})
        geometry["kind"] = entry.get("kind", "unknown")
        geometry["strength"] = topology_connection_strength(subtype)
        geometry["propagates"] = geometry["strength"] > 0.5

    elif tongue == "Phase":
        entry = PHASE_TRANSITIONS.get(subtype, {})
        geometry["from_element"] = entry.get("from", "unknown")
        geometry["to_element"] = entry.get("to", "unknown")
        geometry["axis"] = entry.get("axis", "unknown")
        geometry["circuit_distance"] = phase_circuit_distance(subtype)
        geometry["propagates"] = entry.get("axis") in ("Mind+", "Time+", "closure")

    elif tongue == "Gradient":
        geometry["propagation_likelihood"] = gradient_propagation_likelihood(subtype)
        entry = GRADIENT_ENTRIES.get(subtype, {})
        geometry["character"] = entry.get("types", ())
        geometry["propagates"] = geometry["propagation_likelihood"] > 0.5

    elif tongue == "Curvature":
        geometry["convergence"] = curvature_convergence(subtype)
        entry = CURVATURE_ENTRIES.get(subtype, {})
        geometry["shape"] = entry.get("types", ())
        geometry["propagates"] = geometry["convergence"] > 0.5

    return geometry


def parse_relevance_declaration(
    token: str,
    source: str,
    target: str,
) -> Optional[RelevanceDeclaration]:
    """
    Parse a topological relevance declaration token string.

    Returns a RelevanceDeclaration if the token matches a known
    topological tongue entry, or None if unrecognised.

    Parameters
    ----------
    token  : the Kobra token string (e.g. "Josvo", "Torev", "Shavka")
    source : the Cannabis akinen symbol this declaration applies to
    target : the scene address or structural dialogue element it connects to
    """
    for tongue, table in (
        ("Fold",       FOLD_SUBTYPES),
        ("Topology",   TOPOLOGY_CONNECTORS),
        ("Phase",      PHASE_TRANSITIONS),
        ("Gradient",   GRADIENT_ENTRIES),
        ("Curvature",  CURVATURE_ENTRIES),
    ):
        if token in table:
            entry = table[token]
            geometry = _compute_geometry(tongue, token)
            scale = entry.get("scale")
            axis  = entry.get("axis") if tongue == "Phase" else None
            return RelevanceDeclaration(
                tongue=tongue,
                subtype=token,
                source=source,
                target=target,
                declaration=token,
                geometry=geometry,
                scale=scale,
                axis=axis,
            )
    return None


# ---------------------------------------------------------------------------
# DyskaSoaShun gate logic
# ---------------------------------------------------------------------------

def gate_decision(
    declaration: RelevanceDeclaration,
    witness_state: str = "unwitnessed",
) -> Dict[str, Any]:
    """
    Make a DyskaSoaShun gate decision for a Cannabis entry at a game boundary.

    Returns a dict with:
      passes       — bool, whether the entry crosses the game boundary
      confidence   — float 0.0–1.0
      reason       — human-readable explanation
      carry_as_soa — bool, whether to carry forward as Soa if not passing
    """
    geo = declaration.geometry
    propagates = geo.get("propagates", False)

    if witness_state == "witnessed":
        return {
            "passes": True,
            "confidence": 1.0,
            "reason": f"witnessed — {declaration.tongue} {declaration.subtype} carries forward clean",
            "carry_as_soa": False,
        }

    if not propagates:
        return {
            "passes": False,
            "confidence": 0.9,
            "reason": f"{declaration.tongue} geometry ({declaration.subtype}) does not propagate across boundary",
            "carry_as_soa": True,
        }

    confidence = 0.5
    if declaration.tongue == "Fold":
        confidence = geo.get("gradient_position", 0.5)
    elif declaration.tongue == "Topology":
        confidence = geo.get("strength", 0.5)
    elif declaration.tongue == "Gradient":
        confidence = geo.get("propagation_likelihood", 0.5)
    elif declaration.tongue == "Curvature":
        confidence = geo.get("convergence", 0.5)
    elif declaration.tongue == "Phase":
        confidence = 0.8 if geo.get("propagates") else 0.3

    passes = confidence >= 0.5
    return {
        "passes": passes,
        "confidence": confidence,
        "reason": f"{declaration.tongue} {declaration.subtype} — {'crosses' if passes else 'held at'} game boundary (confidence {confidence:.2f})",
        "carry_as_soa": not passes,
    }
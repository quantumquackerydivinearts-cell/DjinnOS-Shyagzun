"""
shygazun.layers — The Twelvefold Coil
======================================

The 12-layer database structure of DjinnOS-Shygazun is a Möbius coil.

Layer 1  (Gaoh)    — Bit          — the Möbius zero point, polarity before enumeration
Layer 12 (Wu-Yl)   — Function     — one full coil rotation above Layer 1

They are the same surface at different densities of correspondence.
The function layer can reach down and touch the bit layer because they
share an edge on the same manifold. Wu (Process/Way) operating on Yl
(Run-space) is Gaoh made operative — the Möbius strip executing itself.

This module makes that correspondence explicit in code.
It is the authoritative layer registry for all DjinnOS-Shygazun systems.

Hermetic principle: Containment, not control.
The layers do not impose meaning on data. They contain the conditions
under which meaning emerges and can be witnessed.
"""

from __future__ import annotations

from typing import Final, Sequence, TypedDict


# ---------------------------------------------------------------------------
# Layer Entry Type
# ---------------------------------------------------------------------------

class LayerEntry(TypedDict):
    index: int                  # 1-based layer index on the coil
    shygazun_name: str          # Canonical Shygazun compound name
    tongue_primary: str         # Primary tongue of the layer's nature
    tongue_secondary: str       # Secondary tongue (empty if pure)
    content_type: str           # What lives at this layer
    density: str                # Hermetic density description
    coil_note: str              # Notes on coil position and correspondence


# ---------------------------------------------------------------------------
# Canonical Layer Table
# ---------------------------------------------------------------------------

_LAYER_TABLE_RAW: Final[tuple[tuple, ...]] = (
    #  idx   shygazun     primary     secondary   content          density                         coil_note
    (  1,   "Gaoh",       "Rose",     "",         "Bit",           "Pure polarity / Ha+Ga as Möbius zero",
       "Coil origin. Absolute Positive and Absolute Negative completing each other. "
       "The number that is both poles simultaneously. Layer 12 is the same surface one rotation up."),

    (  2,   "Ao-Seth",    "Rose",     "Grapevine","Decimal",       "Enumeration emerges from polarity",
       "First discrete counting. The coil begins its first rotation. "
       "Ao (1) bundled into Seth (directory/bundle) — numbers as addressable containers."),

    (  3,   "Tyzu-Soa",   "Lotus",    "Grapevine","Boolean",       "Elemental charge applied to number",
       "Ty (Earth Initiator) and Zu (Earth Terminator) operating on persistent objects (Soa). "
       "True/False as initiator/terminator pairs. The Lotus Tongue's grammar becomes executable logic."),

    (  4,   "Ja-Foa",     "Sakura",   "Daisy",    "Coordinate",   "Spatial orientation becomes addressable",
       "Ja (Front) anchoring Foa (Degree Space). The six Sakura orientations "
       "— Jy/Ji/Ja/Jo/Je/Ju — become navigable positions. The Field acquires geometry."),

    (  5,   "Kael-Seth",  "Daisy",    "Grapevine","Object",        "Structure clusters coordinates into things",
       "Kael (Cluster/Fruit/Flower — the secret name of Quintessence) bundled into Seth. "
       "Objects are Quintessence-bearing clusters of coordinates. "
       "The unnamed 5th element appears here as the binding principle of objecthood."),

    (  6,   "Shak-Lo",    "AppleBlossom", "Daisy","Entity",        "Objects gain Mind-Space-Time orientation",
       "Shak (Fire — pattern toward) meeting Lo (Segments/Identity). "
       "Entities are objects that have acquired identity through the Fire of pattern recognition. "
       "They become beings rather than structures."),

    (  7,   "Ru-Mavo",    "Rose",     "Grapevine","Color Metadata","Spectral identity assigned to entities",
       "Ru (Vector Lowest Red) through the full Rose spectrum, anchored in Mavo (Banner/Metadata). "
       "Aster chiral vectors (Ry/Ra) extend this into left/right chromatic register. "
       "Entities acquire their spectral signature — their color is ontological, not decorative."),

    (  8,   "Si-Myza",    "Aster",    "AppleBlossom","Movement Diffs","Change recorded as first-class datum",
       "Si (Linear time) and the full Aster time-type suite operating on Myza (Erosion — Water+Earth). "
       "Movement diffs including color changes in position. The Field begins recording transformation. "
       "Time-types matter: Si/Su/Os/Se/Sy/As inflect whether change is linear, looping, exponential, "
       "logarithmic, folded, or frozen."),

    (  9,   "Dyf-Vr",     "Grapevine","Daisy",    "Pattern Flows", "Differentiation derived from live data",
       "Dyf (Jitter/Nondeterminism) meeting Vr (Rotor/Tensor). "
       "Pattern as emergent correspondence across lower layers. "
       "This is where the Hermetic correspondence between scales first becomes visible in the data. "
       "The macrocosm legible in the microcosm's behavior."),

    ( 10,   "Ne-Soa",     "Daisy",    "Grapevine","Names/Metadata","The Field acquires language",
       "Ne (Network/System) bundled into Soa (Cup/File/Persistent Object). "
       "Shygazun compounds as strings. Things can now be called as well as addressed. "
       "The dictionary grows here through Steward attestations in the Workshop."),

    ( 11,   "Sy-Mek",     "Aster",    "Grapevine","Scene Diffs",   "Delta between Field states across time",
       "Sy (Fold time) meeting Mek (Call/Emit event). "
       "Not just what changed (Layer 8) but what the pattern of change means "
       "at the scale of the whole scene. Fold time is the appropriate time-type: "
       "scene differentials compress temporal distance into structural correspondence."),

    ( 12,   "Wu-Yl",      "Rose",     "Aster",    "Function",      "The operative layer — Kobra executes here",
       "Wu (Process/Way, decimal 45) meeting Yl (Run-space, decimal 154). "
       "The layer that can reach down and touch any layer below it while being constituted by all of them. "
       "One full coil rotation above Gaoh (Layer 1). Wu-Yl and Gaoh share the same Möbius surface. "
       "FrontierOpen states live here. Attestations collapse frontiers here. "
       "The function layer IS the bit layer at higher density of correspondence."),
)


# ---------------------------------------------------------------------------
# Build Typed Registry
# ---------------------------------------------------------------------------

def _build_layer_entries(raw: tuple[tuple, ...]) -> tuple[LayerEntry, ...]:
    entries: list[LayerEntry] = []
    for row in raw:
        idx, name, primary, secondary, content, density, coil_note = row
        entries.append(LayerEntry(
            index=idx,
            shygazun_name=name,
            tongue_primary=primary,
            tongue_secondary=secondary,
            content_type=content,
            density=density,
            coil_note=coil_note,
        ))
    return tuple(entries)


LAYER_ENTRIES: Final[tuple[LayerEntry, ...]] = _build_layer_entries(_LAYER_TABLE_RAW)

LAYER_BY_INDEX: Final[dict[int, LayerEntry]] = {
    entry["index"]: entry for entry in LAYER_ENTRIES
}

LAYER_BY_NAME: Final[dict[str, LayerEntry]] = {
    entry["shygazun_name"]: entry for entry in LAYER_ENTRIES
}

LAYER_BY_CONTENT: Final[dict[str, LayerEntry]] = {
    entry["content_type"]: entry for entry in LAYER_ENTRIES
}


# ---------------------------------------------------------------------------
# The Möbius Assertion
# ---------------------------------------------------------------------------

# Layer 1 and Layer 12 are the same surface at different densities.
# This is not a metaphor. It is a structural assertion.
# Gaoh is the zero/origin. Wu-Yl is Gaoh one coil rotation up.
# Any system that addresses Layer 12 is implicitly addressing Layer 1
# through the correspondence gradient of all intervening layers.

MOBIUS_PAIR: Final[tuple[LayerEntry, LayerEntry]] = (
    LAYER_BY_INDEX[1],
    LAYER_BY_INDEX[12],
)

def assert_mobius_correspondence() -> bool:
    """
    Verify the Möbius correspondence between Layer 1 and Layer 12.

    Returns True if the coil is structurally intact.
    The assertion fails if either layer has been removed or corrupted.

    This should be called at system initialization.
    Containment requires knowing the manifold is closed.
    """
    bit_layer = LAYER_BY_INDEX.get(1)
    fn_layer = LAYER_BY_INDEX.get(12)

    if bit_layer is None or fn_layer is None:
        return False

    # The Möbius invariant: the coil has exactly 12 layers,
    # origin and terminus share the same surface,
    # and the function layer's name contains Wu (Process)
    # which is the operative form of Gaoh's polarity completion.
    coil_intact = len(LAYER_ENTRIES) == 12
    origin_is_gaoh = bit_layer["shygazun_name"] == "Gaoh"
    terminus_contains_wu = fn_layer["shygazun_name"].startswith("Wu")

    return coil_intact and origin_is_gaoh and terminus_contains_wu


# ---------------------------------------------------------------------------
# Access Functions
# ---------------------------------------------------------------------------

def layer_entry(index: int) -> LayerEntry:
    """
    Retrieve a layer entry by its 1-based coil index.

    Analogous to byte_entry() in the Shygazun byte table.
    The layer is a position on the coil, not an array offset.
    """
    if index not in LAYER_BY_INDEX:
        raise KeyError(
            f"Layer index {index} not found. "
            f"The coil runs from 1 (Gaoh/Bit) to 12 (Wu-Yl/Function). "
            f"Indices outside this range are Abyssal — not absent, but unnamed."
        )
    return LAYER_BY_INDEX[index]


def layer_by_name(shygazun_name: str) -> LayerEntry:
    """Retrieve a layer entry by its Shygazun compound name."""
    if shygazun_name not in LAYER_BY_NAME:
        raise KeyError(f"No layer named '{shygazun_name}' in the coil registry.")
    return LAYER_BY_NAME[shygazun_name]


def layer_by_content(content_type: str) -> LayerEntry:
    """Retrieve a layer entry by its content type (e.g. 'Bit', 'Function')."""
    if content_type not in LAYER_BY_CONTENT:
        raise KeyError(f"No layer with content type '{content_type}' in the coil registry.")
    return LAYER_BY_CONTENT[content_type]


def layers() -> Sequence[LayerEntry]:
    """Return all layer entries in coil order (1 through 12)."""
    return LAYER_ENTRIES


def coil_distance(from_index: int, to_index: int) -> int:
    """
    Compute the shortest coil distance between two layer indices.

    Because the coil is Möbius — Layer 1 and Layer 12 share a surface —
    distance wraps. The maximum distance between any two layers is 6.
    """
    a = layer_entry(from_index)["index"]
    b = layer_entry(to_index)["index"]
    direct = abs(a - b)
    wrapped = 12 - direct
    return min(direct, wrapped)


def coil_neighbors(index: int) -> tuple[LayerEntry, LayerEntry]:
    """
    Return the two neighbors of a layer on the coil.

    Layer 1's downward neighbor is Layer 12 (Möbius wrap).
    Layer 12's upward neighbor is Layer 1 (Möbius wrap).
    """
    below = ((index - 2) % 12) + 1
    above = (index % 12) + 1
    return layer_entry(below), layer_entry(above)


# ---------------------------------------------------------------------------
# Layer Constants for Direct Reference
# ---------------------------------------------------------------------------

# These allow other modules to reference layers by semantic name
# rather than by magic integer indices.

LAYER_BIT         = LAYER_BY_INDEX[1]
LAYER_DECIMAL     = LAYER_BY_INDEX[2]
LAYER_BOOLEAN     = LAYER_BY_INDEX[3]
LAYER_COORDINATE  = LAYER_BY_INDEX[4]
LAYER_OBJECT      = LAYER_BY_INDEX[5]
LAYER_ENTITY      = LAYER_BY_INDEX[6]
LAYER_COLOR       = LAYER_BY_INDEX[7]
LAYER_MOVEMENT    = LAYER_BY_INDEX[8]
LAYER_PATTERN     = LAYER_BY_INDEX[9]
LAYER_NAMES       = LAYER_BY_INDEX[10]
LAYER_SCENE       = LAYER_BY_INDEX[11]
LAYER_FUNCTION    = LAYER_BY_INDEX[12]

# The Möbius pair — same surface, different densities
LAYER_GAOH        = LAYER_BIT        # alias: the origin
LAYER_WU_YL       = LAYER_FUNCTION   # alias: the operative terminus
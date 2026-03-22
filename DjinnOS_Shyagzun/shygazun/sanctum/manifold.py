"""
shygazun.sanctum.manifold — Topological Manifold Navigator
===========================================================

The 16-tongue Shygazun manifold is a cumulative self-knowing space.
Each tongue adds a structural property to the space. This module computes
manifold positions, Cannabis functor projections, and Dragon Tongue
reachability checks from lists of byte-table addresses.

Stage progression of the 16-tongue linear fundament:
  Ground (1–3):        Lotus, Rose, Sakura — metric, spectral, relational
  Structure (4–5):     Daisy, AppleBlossom — mechanical, phase-change
  Chirality (6):       Aster — handedness introduced
  Network (7):         Grapevine — graph topology / adjacency
  Functor (8):         Cannabis — 3×10 functor (6 clean + 3 shadow + 1 terminal)
  Sampling (9–11):     Dragon, Virus, Bacteria — orientable-space samplers
  Non-orientable (12): Excavata — Möbius bundle, non-orientability introduced
  Relation (13):       Archaeplastida — relational structure on non-orientable space
  Complement (14–16):  Myxozoa and beyond — cokernel / residual operators

Key topological facts encoded here:
  - Gaoh (byte 31) is the S¹ identification map (0 ≡ 12 mod 12), NOT a scalar.
  - Grapevine adjacency resists single-axis projection through Cannabis —
    returns shadow entries (noun / adjective / adverb), not null.
    Flag: GRAPEVINE_PROJECTION_FAILURE.
  - Dragon Tongue (Tongue 9) is topologically unreachable from inside the
    orientable frame without confirmed Excavata frontier openings.
    Flag: TOPOLOGICAL_INCONSISTENCY. This is a geometric description only;
    no intent is inferred and no moral characterization is made.
  - Protist (Tongue 16) has genuine mathematical content ONLY because
    Excavata establishes non-orientability. Its cokernel is non-trivial.

All tongue ranges are derived at runtime from SHYGAZUN_BYTE_ROWS.
No tongue boundaries are hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shygazun.kernel.constants.byte_table import (
    SHYGAZUN_BYTE_ROWS,
    SHYGAZUN_BYTE_TABLE,
    ShygazunByteEntry,
)
from shygazun.sanctum.Layers import LAYER_ENTRIES, coil_distance  # noqa: F401 — re-exported for callers


# ---------------------------------------------------------------------------
# Tongue ordering — derived at runtime from SHYGAZUN_BYTE_ROWS
# ---------------------------------------------------------------------------

def _build_tongue_order() -> dict[str, int]:
    """Map tongue name → 1-based tongue index (order of first appearance in table)."""
    seen: dict[str, int] = {}
    idx = 1
    for row in SHYGAZUN_BYTE_ROWS:
        t = row["tongue"]
        if t not in seen:
            seen[t] = idx
            idx += 1
    return seen


_TONGUE_ORDER: dict[str, int] = _build_tongue_order()


def tongue_index(name: str) -> int:
    """Return the 1-based tongue index for a tongue name, or 0 if unknown."""
    return _TONGUE_ORDER.get(name, 0)


def tongue_name_for_index(idx: int) -> str | None:
    """Return the tongue name for a 1-based index, or None if not found."""
    for name, i in _TONGUE_ORDER.items():
        if i == idx:
            return name
    return None


# ---------------------------------------------------------------------------
# Stage classification — by tongue name (immune to Cluster offset)
# ---------------------------------------------------------------------------
#
# The Cluster entries (bytes 124–127, cluster headers) occupy a slot in
# the tongue order between AppleBlossom and Aster. Stage assignment by
# tongue index would require hardcoding the offset. Instead we map by
# tongue name: structural, not positional.

_TONGUE_STAGES: dict[str, str] = {
    "Lotus":         "Ground",
    "Rose":          "Ground",
    "Sakura":        "Ground",
    "Daisy":         "Structure",
    "AppleBlossom":  "Structure",
    "Aster":         "Chirality",
    "Grapevine":     "Network",
    "Cannabis":      "Functor",
    "Dragon":        "Sampling",
    "Virus":         "Sampling",
    "Bacteria":      "Sampling",
    "Excavata":      "Non-orientable",
    "Archaeplastida":"Relation",
    # Tongues 14–16 and beyond are Complement by default
}
_COMPLEMENT_THRESHOLD: str = "Archaeplastida"  # anything with higher tongue index → Complement


def _stage_for_tongue(idx: int) -> str:
    """Stage for the highest tongue index present. Uses name lookup, not index bands."""
    if idx == 0:
        return "None"
    name = tongue_name_for_index(idx)
    if name is None:
        return "Beyond"
    stage = _TONGUE_STAGES.get(name)
    if stage is not None:
        return stage
    # Any tongue beyond Archaeplastida is in the Complement stage
    threshold_idx = _TONGUE_ORDER.get(_COMPLEMENT_THRESHOLD, 0)
    if threshold_idx > 0 and idx > threshold_idx:
        return "Complement"
    # Cluster or other structural meta-tongues
    return "Structural"


# ---------------------------------------------------------------------------
# Cannabis functor mapping — derived at runtime from SHYGAZUN_BYTE_ROWS
# ---------------------------------------------------------------------------

# The 6 tongues that project cleanly through Cannabis (one cell per axis each):
_CANNABIS_CLEAN_TONGUES: tuple[str, ...] = (
    "Lotus", "Rose", "Sakura", "Daisy", "AppleBlossom", "Aster"
)

# The 3 Cannabis axes, in table order:
_CANNABIS_AXIS_NAMES: tuple[str, ...] = ("Mind", "Space", "Time")

# Each axis has 10 cells: 6 clean projections + 3 Grapevine shadows + 1 terminal
_SLOT_CLEAN    = tuple(range(6))    # indices 0–5
_SLOT_SHADOW   = (6, 7, 8)          # indices 6–8
_SLOT_TERMINAL = 9                  # index 9


def _build_cannabis_axis_map() -> dict[str, list[ShygazunByteEntry]]:
    """
    Partition Cannabis rows into 3 axes of 10 entries each.

    The byte table lists Cannabis rows in order: Mind (first 10),
    Space (next 10), Time (last 10). We derive this by scanning
    SHYGAZUN_BYTE_ROWS, not by hardcoding decimal ranges.
    """
    cannabis_rows = [r for r in SHYGAZUN_BYTE_ROWS if r["tongue"] == "Cannabis"]
    axes: dict[str, list[ShygazunByteEntry]] = {}
    for i, name in enumerate(_CANNABIS_AXIS_NAMES):
        axes[name] = list(cannabis_rows[i * 10 : (i + 1) * 10])
    return axes


_CANNABIS_AXIS_MAP: dict[str, list[ShygazunByteEntry]] = _build_cannabis_axis_map()


def _clean_projection_entry(axis: str, tongue_name: str) -> ShygazunByteEntry | None:
    """Return the Cannabis byte entry for projecting tongue_name onto axis."""
    if tongue_name not in _CANNABIS_CLEAN_TONGUES:
        return None
    slot = _CANNABIS_CLEAN_TONGUES.index(tongue_name)
    return _CANNABIS_AXIS_MAP[axis][slot]


def _shadow_entries_for_axis(axis: str, source_byte: int) -> list[dict[str, Any]]:
    """Return the 3 Grapevine shadow entries for axis (noun / adjective / adverb)."""
    shadow_labels = ("noun", "adjective", "adverb")
    result: list[dict[str, Any]] = []
    for slot_offset, label in zip(_SLOT_SHADOW, shadow_labels):
        shadow = _CANNABIS_AXIS_MAP[axis][slot_offset]
        result.append({
            "axis": axis,
            "shadow_form": label,
            "source_byte": source_byte,
            "shadow_byte": shadow["decimal"],
            "shadow_symbol": shadow["symbol"],
            "shadow_meaning": shadow["meaning"],
        })
    return result


# ---------------------------------------------------------------------------
# GaohOperator — S¹ identification map, NOT a scalar
# ---------------------------------------------------------------------------

class GaohOperator:
    """
    The topological identification map carried by byte 31 (Gaoh).

    Gaoh = "Number 12 / 0" — it encodes the identification 0 ≡ 12 mod 12.
    This folds the integer clock into S¹ (a circle), making the 12-layer
    Möbius coil self-closing: Layer 1 and Layer 12 share a surface.

    In the Mandelbrot formula (Azoth² + Gaoh = f(x)), Gaoh is NOT the
    integer 31. It is the identification map carried as a complex constant —
    the shift that determines whether orbits remain bounded (orientable
    manifold interior) or escape to infinity (beyond the non-orientability
    threshold). The Mandelbrot boundary IS the non-orientability threshold
    because the S¹ fold IS the non-orientability condition.

    GaohOperator is a class because it represents a structural relationship,
    not a quantity. Treating it as 31 would be a category error.
    """

    BYTE: int = 31
    SYMBOL: str = "Gaoh"
    MEANING: str = "Number 12 / 0"
    MODULUS: int = 12

    @staticmethod
    def identifies(a: int, b: int) -> bool:
        """True if a ≡ b (mod 12) — the defining S¹ identification."""
        return (a % GaohOperator.MODULUS) == (b % GaohOperator.MODULUS)

    @staticmethod
    def coil_zero() -> int:
        """
        The Möbius zero point.
        Layer 1 and Layer 12 are identified: 0 ≡ 12 mod 12.
        Returns 0, which is the same surface as 12 under the identification.
        """
        return 0

    @staticmethod
    def as_complex_constant() -> complex:
        """
        Gaoh as the complex constant in the Mandelbrot formula.
        Encodes: real = -(31 / 144), imaginary = 31 / (12π).
        This places the constant inside the Mandelbrot set near the
        boundary of the main cardioid — the precise analog of Gaoh
        holding both poles (Ha + Ga) simultaneously before enumeration.
        """
        import math
        return complex(-31 / (12 ** 2), 31 / (12 * math.pi))

    def __repr__(self) -> str:
        return "GaohOperator(S1 identification: 0 == 12 mod 12)"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ManifoldPosition:
    """
    Topological position of a compound on the 16-tongue manifold.

    Derived from a list of byte-table addresses. Tongue ranges are
    always resolved from the live byte table, never hardcoded.
    """
    addresses: list[int]
    tongues_present: list[str]        # tongue names, in order of first appearance
    tongue_indices: list[int]         # 1-based tongue numbers (parallel to tongues_present)
    highest_tongue_index: int         # 0 if no recognized addresses
    stage: str                        # manifold stage of the highest tongue
    is_orientable: bool               # True if highest tongue < Excavata's index
    has_non_orientable_entry: bool    # True if any address belongs to Excavata or higher
    coil_layer_tongues: list[str]     # subset of tongues_present that appear in coil layer primaries


@dataclass
class CannabisProjection:
    """
    Projection of one source tongue through the Cannabis functor onto one axis.

    Cannabis (Tongue 8) maps Tongues 1–6 onto 3 axes (Mind, Space, Time).
    Each axis has 6 clean projection slots, 3 shadow slots, and 1 terminal.
    """
    axis: str               # "Mind", "Space", or "Time"
    source_tongue: str      # name of the tongue being projected
    projected_byte: int     # decimal address of the Cannabis projection cell
    projected_symbol: str
    projected_meaning: str
    is_shadow: bool         # True if this is a Grapevine shadow entry
    is_terminal: bool       # True if this is the conscious-action terminal


@dataclass
class CannabisProjections:
    """
    Full Cannabis projection result for a set of input addresses.

    GRAPEVINE_PROJECTION_FAILURE is set when any input address belongs
    to Grapevine (Tongue 7). Network adjacency structure cannot be
    preserved through a single-axis operator — shadow entries are
    returned instead of a null result.
    """
    projections: list[CannabisProjection]
    grapevine_projection_failure: bool   # True if Grapevine entries were present
    shadow_entries: list[dict[str, Any]] # shadow cells for failed Grapevine projections
    beyond_functor: list[int]            # addresses from tongues >= 9 (past Cannabis)


@dataclass
class ReachabilityResult:
    """
    Reachability check for Dragon Tongue addresses against the density vector.

    Dragon Tongue (Tongue 9) addresses the void-organism register — an
    exterior space that is topologically unreachable from inside the
    orientable manifold frame (Tongues 1–11). Reaching Dragon Tongue
    requires confirmed Excavata (Tongue 12) frontier openings, evidenced
    by non-zero Excavata-tongue density in the density vector.

    TOPOLOGICAL_INCONSISTENCY is a geometric description only.
    It means: the compound claims a coordinate unreachable from the
    attested manifold position. No intent is inferred. No moral
    characterization is made.

    density_vector keys: byte-table decimal addresses.
    density_vector values: density weight (0.0–1.0 typical, not enforced).
    """
    dragon_addresses: list[int]       # Dragon Tongue addresses found in input
    has_dragon_entries: bool
    excavata_density: float           # sum of density for Excavata-tongue bytes in vector
    reachable: bool                   # True if no Dragon entries, OR Excavata density > 0
    topological_inconsistency: bool   # True if Dragon entries present but Excavata density == 0
    inconsistency_note: str           # Geometric description. Empty string if no inconsistency.


# ---------------------------------------------------------------------------
# Public resolution functions
# ---------------------------------------------------------------------------

def resolve_manifold_position(addresses: list[int]) -> ManifoldPosition:
    """
    Derive the manifold position for a list of byte-table addresses.

    Tongue ranges are derived at runtime from SHYGAZUN_BYTE_ROWS.
    The Excavata boundary (non-orientability threshold) is resolved
    dynamically — not assumed to be tongue 12.
    """
    seen_tongues: list[str] = []
    seen_set: set[str] = set()

    for addr in addresses:
        entry = SHYGAZUN_BYTE_TABLE.get(addr)
        if entry is None:
            continue
        t = entry["tongue"]
        if t not in seen_set:
            seen_tongues.append(t)
            seen_set.add(t)

    tongue_idxs = [tongue_index(t) for t in seen_tongues]
    highest = max(tongue_idxs, default=0)

    # Excavata threshold: the tongue index where non-orientability begins
    excavata_idx = _TONGUE_ORDER.get("Excavata", 12)
    has_non_orientable = any(i >= excavata_idx for i in tongue_idxs)
    is_orientable = not has_non_orientable

    # Which coil layers (by primary tongue) are represented?
    coil_primaries: set[str] = {layer["tongue_primary"] for layer in LAYER_ENTRIES}
    coil_layer_tongues = [t for t in seen_tongues if t in coil_primaries]

    return ManifoldPosition(
        addresses=list(addresses),
        tongues_present=seen_tongues,
        tongue_indices=tongue_idxs,
        highest_tongue_index=highest,
        stage=_stage_for_tongue(highest),
        is_orientable=is_orientable,
        has_non_orientable_entry=has_non_orientable,
        coil_layer_tongues=coil_layer_tongues,
    )


def project_through_cannabis(addresses: list[int]) -> CannabisProjections:
    """
    Project input addresses through the Cannabis functor (Tongue 8).

    Cannabis is the 3×10 functor: it maps Tongues 1–6 onto three axes
    (Mind, Space, Time). Each clean tongue gets one projection cell per
    axis. Grapevine (Tongue 7) resists single-axis projection because
    network adjacency structure cannot be preserved through one operator;
    its entries produce shadow cells (noun / adjective / adverb forms)
    and set GRAPEVINE_PROJECTION_FAILURE. Addresses from Cannabis itself
    are identified by their axis position. Addresses from Tongue 9+
    are beyond the Cannabis functor's domain and are listed separately.
    """
    projections: list[CannabisProjection] = []
    shadow_entries: list[dict[str, Any]] = []
    grapevine_failure = False
    beyond_functor: list[int] = []

    for addr in addresses:
        entry = SHYGAZUN_BYTE_TABLE.get(addr)
        if entry is None:
            continue
        t = entry["tongue"]

        if t in _CANNABIS_CLEAN_TONGUES:
            # Clean projection: one cell per axis
            for axis in _CANNABIS_AXIS_NAMES:
                proj = _clean_projection_entry(axis, t)
                if proj is not None:
                    projections.append(CannabisProjection(
                        axis=axis,
                        source_tongue=t,
                        projected_byte=proj["decimal"],
                        projected_symbol=proj["symbol"],
                        projected_meaning=proj["meaning"],
                        is_shadow=False,
                        is_terminal=False,
                    ))

        elif t == "Grapevine":
            # Network adjacency resists single-axis projection — shadow entries
            grapevine_failure = True
            for axis in _CANNABIS_AXIS_NAMES:
                shadow_entries.extend(_shadow_entries_for_axis(axis, addr))

        elif t == "Cannabis":
            # This address IS a Cannabis cell — identify its axis and slot
            for axis, axis_entries in _CANNABIS_AXIS_MAP.items():
                for slot, cannabis_entry in enumerate(axis_entries):
                    if cannabis_entry["decimal"] == addr:
                        if slot < 6:
                            source = _CANNABIS_CLEAN_TONGUES[slot]
                        else:
                            source = t
                        projections.append(CannabisProjection(
                            axis=axis,
                            source_tongue=source,
                            projected_byte=addr,
                            projected_symbol=entry["symbol"],
                            projected_meaning=entry["meaning"],
                            is_shadow=(slot in _SLOT_SHADOW),
                            is_terminal=(slot == _SLOT_TERMINAL),
                        ))
                        break

        else:
            # Tongue 9+ — beyond the Cannabis functor
            beyond_functor.append(addr)

    return CannabisProjections(
        projections=projections,
        grapevine_projection_failure=grapevine_failure,
        shadow_entries=shadow_entries,
        beyond_functor=beyond_functor,
    )


def check_reachability(
    addresses: list[int],
    density_vector: dict[int, float],
) -> ReachabilityResult:
    """
    Check whether Dragon Tongue addresses in the compound are reachable
    from the attested manifold position given a density vector.

    Dragon Tongue (Tongue 9) addresses the void-organism register.
    It is topologically unreachable from inside the orientable frame
    (Tongues 1–11) without confirmed Excavata (Tongue 12) frontier
    openings. Excavata establishes non-orientability — the topological
    precondition for reaching Dragon Tongue space.

    density_vector: keys are byte-table decimal addresses; values are
    density weights (non-negative floats). Non-zero weight on any
    Excavata-tongue address counts as a confirmed frontier opening.

    TOPOLOGICAL_INCONSISTENCY:
        Geometric description only. The compound claims a coordinate
        that is unreachable from the player's attested manifold position.
        No intent is inferred. No moral characterization is made.
    """
    dragon_addresses: list[int] = [
        addr for addr in addresses
        if SHYGAZUN_BYTE_TABLE.get(addr, {}).get("tongue") == "Dragon"
    ]

    # Collect all Excavata-tongue byte addresses from the live table
    excavata_bytes: set[int] = {
        row["decimal"]
        for row in SHYGAZUN_BYTE_ROWS
        if row["tongue"] == "Excavata"
    }

    excavata_density = sum(
        float(v) for k, v in density_vector.items()
        if k in excavata_bytes and isinstance(v, (int, float))
    )

    has_dragon = len(dragon_addresses) > 0
    reachable = (not has_dragon) or (excavata_density > 0.0)
    inconsistency = has_dragon and excavata_density == 0.0

    note = ""
    if inconsistency:
        note = (
            "Compound includes Dragon Tongue address(es) but the density vector "
            "shows no confirmed Excavata frontier openings. "
            "Dragon Tongue (Tongue 9) is topologically unreachable from the current "
            "manifold position: the non-orientability threshold (Excavata, Tongue 12) "
            "has not been established. "
            "This is a geometric gap description. No intent is inferred."
        )

    return ReachabilityResult(
        dragon_addresses=dragon_addresses,
        has_dragon_entries=has_dragon,
        excavata_density=round(excavata_density, 6),
        reachable=reachable,
        topological_inconsistency=inconsistency,
        inconsistency_note=note,
    )

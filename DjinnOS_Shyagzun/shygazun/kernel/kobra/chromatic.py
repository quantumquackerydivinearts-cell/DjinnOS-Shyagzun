"""
shygazun/kernel/kobra/chromatic.py
====================================
Chromatic profiling — the spectral tongue composition of a Kobra expression.

A "chromatic" expression is one that draws from multiple tongue registers
simultaneously.  The Rose tongue's base-12 ring system (Gaoh=0 … Aonkiel=11)
is the natural spectral model: each tongue occupies a position on the ring,
and the chromatic profile of an expression is the distribution of active
tongue positions.

Band structure
--------------
Tongues are grouped into four bands by their functional register:

  MATERIAL    — AppleBlossom (elemental matter; what things are made of).
  STRUCTURAL  — Lotus, Sakura, Rose (prime elements, orientation, vectors).
  BEHAVIORAL  — Daisy, Grapevine, Aster (topology, systems, time-space).
  OPERATOR    — Cannabis and Tongues 10+ (deliberate ambiguity, relational
                modes, organism registers, etc.).

A chromatic expression is one that spans more than one band.  The
ChromaticSignature encodes which tongues are present and at what count.
The ChromaticProfile aggregates the signature into band weights and
computes a "spread" — how many distinct bands are active.

This layer is read by quest_engine and dialogue_runtime when they need to
classify which Kobra expressions are "in scope" for a given quest stage.
No semantic inference is performed here; classification is structural only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Band classification
# ---------------------------------------------------------------------------

class ChromaticBand(str, Enum):
    MATERIAL   = "material"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    OPERATOR   = "operator"
    UNKNOWN    = "unknown"


# Tongue → band mapping.  Tongues 10+ all fall in OPERATOR unless listed.
_TONGUE_BAND: Dict[str, ChromaticBand] = {
    "AppleBlossom": ChromaticBand.MATERIAL,
    "Lotus":        ChromaticBand.STRUCTURAL,
    "Sakura":       ChromaticBand.STRUCTURAL,
    "Rose":         ChromaticBand.STRUCTURAL,
    "Daisy":        ChromaticBand.BEHAVIORAL,
    "Grapevine":    ChromaticBand.BEHAVIORAL,
    "Aster":        ChromaticBand.BEHAVIORAL,
    "Cannabis":     ChromaticBand.OPERATOR,
    "Dragon":       ChromaticBand.OPERATOR,
    "Virus":        ChromaticBand.OPERATOR,
    "Bacteria":     ChromaticBand.OPERATOR,
    "Excavata":     ChromaticBand.OPERATOR,
    "Archaeplastida": ChromaticBand.OPERATOR,
    "Myxozoa":      ChromaticBand.OPERATOR,
    "Serpent":      ChromaticBand.OPERATOR,
    "Moon":         ChromaticBand.OPERATOR,
    "Titan":        ChromaticBand.OPERATOR,
}


def classify_band(tongue: str) -> ChromaticBand:
    """
    Return the ChromaticBand for a given tongue name.
    Tongues not in the explicit map default to OPERATOR if their
    name begins with a capital letter (i.e. a known tongue form),
    otherwise UNKNOWN.
    """
    explicit = _TONGUE_BAND.get(tongue)
    if explicit is not None:
        return explicit
    if tongue and tongue[0].isupper():
        return ChromaticBand.OPERATOR
    return ChromaticBand.UNKNOWN


# ---------------------------------------------------------------------------
# ChromaticSignature — per-tongue count distribution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChromaticSignature:
    """
    The tongue distribution of a single Kobra expression.

    ``counts`` maps tongue name → occurrence count (always positive).
    ``deliberate`` is True if any Cannabis Tongue akinen is present,
    mirroring the Wunashako.deliberate flag.
    """
    counts:    Tuple[Tuple[str, int], ...]   # sorted by tongue name
    deliberate: bool = False

    @classmethod
    def from_dict(
        cls,
        counts: Dict[str, int],
        deliberate: bool = False,
    ) -> "ChromaticSignature":
        sorted_counts = tuple(sorted(counts.items()))
        return cls(counts=sorted_counts, deliberate=deliberate)

    def tongue_names(self) -> FrozenSet[str]:
        return frozenset(t for t, _ in self.counts)

    def total_akinen(self) -> int:
        return sum(c for _, c in self.counts)

    def count_for(self, tongue: str) -> int:
        for t, c in self.counts:
            if t == tongue:
                return c
        return 0

    def band_counts(self) -> Dict[ChromaticBand, int]:
        result: Dict[ChromaticBand, int] = {b: 0 for b in ChromaticBand}
        for tongue, count in self.counts:
            result[classify_band(tongue)] += count
        return result

    def active_bands(self) -> FrozenSet[ChromaticBand]:
        return frozenset(b for b, c in self.band_counts().items() if c > 0)

    def spread(self) -> int:
        """Number of distinct bands active.  1 = monochromatic, 4 = full."""
        return len(self.active_bands())

    def is_chromatic(self) -> bool:
        """True if more than one band is active."""
        return self.spread() > 1

    def dominant_band(self) -> Optional[ChromaticBand]:
        """The band with the highest akinen count.  None if empty."""
        bc = self.band_counts()
        if not any(bc.values()):
            return None
        return max(bc, key=lambda b: bc[b])


# ---------------------------------------------------------------------------
# ChromaticProfile — aggregated analysis across a scene or expression set
# ---------------------------------------------------------------------------

@dataclass
class ChromaticProfile:
    """
    Aggregated chromatic analysis across a set of signatures (e.g. all
    Cannabis entries in a quest scene).

    ``signatures``      is the ordered list of signatures analysed.
    ``band_totals``     accumulates akinen counts per band across all
                        signatures.
    ``operator_tongues`` is the set of specific operator tongues encountered
                        (Cannabis, Dragon, Virus, etc.).
    ``deliberate_count`` is the number of signatures with deliberate=True.
    """
    signatures:        List[ChromaticSignature] = field(default_factory=list)
    band_totals:       Dict[ChromaticBand, int]  = field(
        default_factory=lambda: {b: 0 for b in ChromaticBand}
    )
    operator_tongues:  List[str]                 = field(default_factory=list)
    deliberate_count:  int                       = 0

    def add(self, sig: ChromaticSignature) -> None:
        self.signatures.append(sig)
        for band, count in sig.band_counts().items():
            self.band_totals[band] = self.band_totals.get(band, 0) + count
        if sig.deliberate:
            self.deliberate_count += 1
        for tongue, _ in sig.counts:
            if classify_band(tongue) == ChromaticBand.OPERATOR:
                if tongue not in self.operator_tongues:
                    self.operator_tongues.append(tongue)

    def overall_spread(self) -> int:
        return len(
            frozenset(b for b, c in self.band_totals.items() if c > 0)
        )

    def has_deliberate(self) -> bool:
        return self.deliberate_count > 0

    def has_operator(self, tongue: str) -> bool:
        return tongue in self.operator_tongues

    def dominant_band(self) -> Optional[ChromaticBand]:
        if not any(self.band_totals.values()):
            return None
        return max(self.band_totals, key=lambda b: self.band_totals[b])

    def to_dict(self) -> Dict[str, object]:
        return {
            "spread":            self.overall_spread(),
            "deliberate_count":  self.deliberate_count,
            "band_totals":       {b.value: c for b, c in self.band_totals.items()},
            "operator_tongues":  list(self.operator_tongues),
            "signature_count":   len(self.signatures),
            "dominant_band":     (
                self.dominant_band().value
                if self.dominant_band() is not None else None
            ),
        }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def signature_from_tokens(
    tokens: List[Dict[str, object]],
    deliberate: bool = False,
) -> ChromaticSignature:
    """
    Build a ChromaticSignature from a list of token dicts, each with at
    least a ``"tongue"`` key.  Missing or None tongue values are skipped.

    Parameters
    ----------
    tokens    : list of dicts like {"tongue": "Cannabis", ...}
    deliberate: whether the containing Wunashako is deliberate
    """
    counts: Dict[str, int] = {}
    for token in tokens:
        tongue = str(token.get("tongue") or "").strip()
        if tongue:
            counts[tongue] = counts.get(tongue, 0) + 1
    return ChromaticSignature.from_dict(counts, deliberate=deliberate)


def profile_from_signatures(
    signatures: List[ChromaticSignature],
) -> ChromaticProfile:
    """Build a ChromaticProfile from an already-computed list of signatures."""
    profile = ChromaticProfile()
    for sig in signatures:
        profile.add(sig)
    return profile
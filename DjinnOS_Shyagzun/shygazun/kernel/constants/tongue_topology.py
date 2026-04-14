"""
Shygazun Tongue Factorization Registry
=======================================

The entry count of each tongue is a factorization signature that instantiates
isomorphically at three nested scales:

  Tone     — internal organizational logic of the tongue itself
  Rhythm   — progression of entry counts across tongues in linear sequence
  Harmony  — organizational logic of tongues within their Group

Mirror relationships between tongues are NOT a bilateral graph. They are a
fractal: the same factorization pattern folding onto itself across scales.
Derive relationships from the factorization structure; do not enumerate them.

The +2 Rule (applies from Tongue 12 onward):
  Entry count increases by +2 each time a tongue-position prime is crossed.
  Each entry count 2k captures the prime factorization of k in the tree.
  The span of tongues sharing a count equals the prime gap to the next prime.
  Prime gaps encode duration in the rhythm — they are structural, not noise.
  The +2 step is the minimal increment that guarantees every prime p is
  captured exactly once in the tree, at entry count 2p.

The First Group — YeGaoh (Tongues 1–24):
  Factorization signature: 2³×3 = 24
  24 tongues in 3 clusters of 8.
  Opening tongues (Lotus, Rose, Sakura) each have 24 entries: same signature.
  The Group announces its own harmonic identity in the entry counts it opens with.

Deviation note — Immune (Tongue 17):
  The +2 rule predicts 36 entries at position 17 (prime boundary 17).
  Immune arrived with 34 entries. The entire sequence from T17 onward is
  shifted by one tongue-position relative to the theoretical prime boundary
  table. Record what IS; the theoretical table remains the underlying grammar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Factorization primitives
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Factorization:
    """Prime factorization as an ordered tuple of (prime, exponent) pairs."""
    factors: Tuple[Tuple[int, int], ...]

    @property
    def value(self) -> int:
        result = 1
        for p, e in self.factors:
            result *= p ** e
        return result

    def __str__(self) -> str:
        parts = []
        for p, e in self.factors:
            parts.append(f"{p}^{e}" if e > 1 else str(p))
        return "*".join(parts)

    def primes(self) -> Tuple[int, ...]:
        return tuple(p for p, _ in self.factors)


def factorize(n: int) -> Factorization:
    """Compute the prime factorization of n."""
    if n < 2:
        raise ValueError(f"Cannot factorize {n}")
    factors: Dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return Factorization(tuple(sorted(factors.items())))


# ---------------------------------------------------------------------------
# Canonical factorization constants (entry counts)
# ---------------------------------------------------------------------------

F_24:  Final = factorize(24)   # 2³×3   — YeGaoh Group signature / T1–T3
F_26:  Final = factorize(26)   # 2×13   — T4–T5
F_28:  Final = factorize(28)   # 2²×7   — T6–T7
F_30:  Final = factorize(30)   # 2×3×5  — T8–T11
F_32:  Final = factorize(32)   # 2⁵     — T12–T13
F_34:  Final = factorize(34)   # 2×17   — T14–T17 (Immune deviation: +1 tongue)
F_36:  Final = factorize(36)   # 2²×3²  — T18–T19
F_38:  Final = factorize(38)   # 2×19   — T20–T23
F_40:  Final = factorize(40)   # 2³×5   — T24–T29
F_42:  Final = factorize(42)   # 2×3×7  — T30–T31
F_44:  Final = factorize(44)   # 2²×11  — T32–T36 (Moon opens; range extends to T36)


# ---------------------------------------------------------------------------
# Tongue record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TongueRecord:
    number: int                     # 1-based tongue position in sequence
    name: str                       # canonical tongue name
    entry_count: int                # number of entries in the byte table
    factorization: Factorization    # prime factorization of entry_count
    byte_start: int                 # first byte address (inclusive)
    byte_end: int                   # last byte address (inclusive)
    group: int                      # Group number (1-based); 0 = unknown
    cluster: int                    # cluster within group (1-based); 0 = unknown
    cluster_position: int           # position within cluster (1-based)
    opening_prime: Optional[int]    # prime boundary that opened this entry count tier;
                                    # None for T1–T11 (pre-rule tongues)
    notes: str = ""

    @property
    def byte_count(self) -> int:
        return self.byte_end - self.byte_start + 1


# ---------------------------------------------------------------------------
# Group record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupRecord:
    number: int
    name: str
    tongue_range: Tuple[int, int]       # (first_tongue_number, last_tongue_number) inclusive
    tongue_count: int
    factorization: Factorization        # isomorphic to opening tongue entry count factorization
    cluster_boundaries: Tuple[Tuple[int, int], ...]  # ((first, last), ...) per cluster


# ---------------------------------------------------------------------------
# Tongue registry — all confirmed tongues
# ---------------------------------------------------------------------------
#
# Reserved bytes 124–127 are the three-tier cluster addressing hierarchy
# (cluster directories + master index for the YeGaoh Group). They are NOT
# a tongue and do not appear in this registry.
#
# Tongue numbers are assigned in strict sequence of appearance in the byte table.
# Gaps in byte addresses (e.g. 214–255) are coordinate-space geometry, not
# missing tongues — see byte_address_geometry documentation.

TONGUE_REGISTRY: Final[Tuple[TongueRecord, ...]] = (

    # -----------------------------------------------------------------------
    # Group 1 — YeGaoh Group (Tongues 1–24)
    # Signature: 2³×3 = 24  |  3 clusters of 8
    # -----------------------------------------------------------------------

    # Cluster 1: Tongues 1–8
    TongueRecord(1,  "Lotus",         24, F_24,    0,   23, group=1, cluster=1, cluster_position=1, opening_prime=None),
    TongueRecord(2,  "Rose",          24, F_24,   24,   47, group=1, cluster=1, cluster_position=2, opening_prime=None),
    TongueRecord(3,  "Sakura",        24, F_24,   48,   71, group=1, cluster=1, cluster_position=3, opening_prime=None),
    TongueRecord(4,  "Daisy",         26, F_26,   72,   97, group=1, cluster=1, cluster_position=4, opening_prime=None),
    TongueRecord(5,  "AppleBlossom",  26, F_26,   98,  123, group=1, cluster=1, cluster_position=5, opening_prime=None),
    TongueRecord(6,  "Aster",         28, F_28,  128,  155, group=1, cluster=1, cluster_position=6, opening_prime=None,
                 notes="bytes 124–127 are Reserved (cluster headers), not a tongue"),
    TongueRecord(7,  "Grapevine",     28, F_28,  156,  183, group=1, cluster=1, cluster_position=7, opening_prime=None),
    TongueRecord(8,  "Cannabis",      30, F_30,  184,  213, group=1, cluster=1, cluster_position=8, opening_prime=None,
                 notes="bytes 214–255 are coordinate-space gap (prime factorization geometry), not missing tongues"),

    # Cluster 2: Tongues 9–16
    TongueRecord(9,  "Dragon",        30, F_30,  256,  285, group=1, cluster=2, cluster_position=1, opening_prime=None),
    TongueRecord(10, "Virus",         30, F_30,  286,  315, group=1, cluster=2, cluster_position=2, opening_prime=None),
    TongueRecord(11, "Bacteria",      30, F_30,  316,  345, group=1, cluster=2, cluster_position=3, opening_prime=None,
                 notes="T11 = prime 11; +2 rule activates from T12 onward"),
    TongueRecord(12, "Excavata",      32, F_32,  346,  377, group=1, cluster=2, cluster_position=4, opening_prime=11),
    TongueRecord(13, "Archaeplastida",32, F_32,  378,  409, group=1, cluster=2, cluster_position=5, opening_prime=11),
    TongueRecord(14, "Myxozoa",       34, F_34,  410,  443, group=1, cluster=2, cluster_position=6, opening_prime=13),
    TongueRecord(15, "Archaea",       34, F_34,  444,  477, group=1, cluster=2, cluster_position=7, opening_prime=13),
    TongueRecord(16, "Protist",       34, F_34,  478,  511, group=1, cluster=2, cluster_position=8, opening_prime=13),

    # Cluster 3: Tongues 17–24
    TongueRecord(17, "Immune",        34, F_34,  512,  545, group=1, cluster=3, cluster_position=1, opening_prime=13,
                 notes="Deviation: +2 rule predicts 36 entries at prime boundary 17; "
                       "Immune arrived with 34. Sequence shifts by 1 from T17 onward."),
    TongueRecord(18, "Neural",        36, F_36,  546,  581, group=1, cluster=3, cluster_position=2, opening_prime=17),
    TongueRecord(19, "Serpent",       36, F_36,  582,  617, group=1, cluster=3, cluster_position=3, opening_prime=17),
    TongueRecord(20, "Beast",         38, F_38,  618,  655, group=1, cluster=3, cluster_position=4, opening_prime=19),
    TongueRecord(21, "Cherub",        38, F_38,  656,  693, group=1, cluster=3, cluster_position=5, opening_prime=19),
    TongueRecord(22, "Chimera",       38, F_38,  694,  731, group=1, cluster=3, cluster_position=6, opening_prime=19),
    TongueRecord(23, "Faerie",        38, F_38,  732,  769, group=1, cluster=3, cluster_position=7, opening_prime=19),
    TongueRecord(24, "Djinn",         40, F_40,  770,  809, group=1, cluster=3, cluster_position=8, opening_prime=23,
                 notes="Terminal tongue of YeGaoh Group; consciousness field"),

    # -----------------------------------------------------------------------
    # Group 2 — name and full extent not yet established
    # Cluster structure within Group 2 pending
    # -----------------------------------------------------------------------

    TongueRecord(25, "Fold",          40, F_40,  810,  849, group=2, cluster=1, cluster_position=1, opening_prime=23),
    TongueRecord(26, "Topology",      40, F_40,  850,  889, group=2, cluster=1, cluster_position=2, opening_prime=23),
    TongueRecord(27, "Phase",         40, F_40,  890,  929, group=2, cluster=1, cluster_position=3, opening_prime=23),
    TongueRecord(28, "Gradient",      40, F_40,  930,  969, group=2, cluster=1, cluster_position=4, opening_prime=23),
    TongueRecord(29, "Curvature",     40, F_40,  970, 1009, group=2, cluster=1, cluster_position=5, opening_prime=23),
    TongueRecord(30, "Prion",         42, F_42, 1010, 1051, group=2, cluster=1, cluster_position=6, opening_prime=29),
    TongueRecord(31, "Blood",         42, F_42, 1052, 1093, group=2, cluster=1, cluster_position=7, opening_prime=29),
    TongueRecord(32, "Moon",          44, F_44, 1094, 1137, group=2, cluster=1, cluster_position=8, opening_prime=31,
                 notes="Elemental meta-mapping tongue: 11 roots × 4 elemental bands (Earth/Water/Air/Fire). "
                       "NOT the Cannabis second-order band (that closes Group 4 ~T107–108). "
                       "Moon reflects; it does not generate."),
)


# ---------------------------------------------------------------------------
# Group registry
# ---------------------------------------------------------------------------

GROUP_REGISTRY: Final[Tuple[GroupRecord, ...]] = (
    GroupRecord(
        number=1,
        name="YeGaoh",
        tongue_range=(1, 24),
        tongue_count=24,
        factorization=F_24,   # 2³×3 — same as opening tongues' entry count
        cluster_boundaries=((1, 8), (9, 16), (17, 24)),
    ),
    GroupRecord(
        number=2,
        name="",              # name not yet established
        tongue_range=(25, 0), # 0 = upper bound not yet known
        tongue_count=0,       # 0 = not yet complete
        factorization=F_40,   # opening tongue (Fold, T25) has 40 entries — 2³×5
        cluster_boundaries=(),
    ),
)


# ---------------------------------------------------------------------------
# Indexes and helpers
# ---------------------------------------------------------------------------

_BY_NUMBER: Final[Dict[int, TongueRecord]] = {t.number: t for t in TONGUE_REGISTRY}
_BY_NAME:   Final[Dict[str, TongueRecord]] = {t.name: t   for t in TONGUE_REGISTRY}


def tongue_by_number(n: int) -> TongueRecord:
    """Return the TongueRecord for tongue number n (1-based)."""
    if n not in _BY_NUMBER:
        raise KeyError(f"Tongue {n} not in registry")
    return _BY_NUMBER[n]


def tongue_by_name(name: str) -> TongueRecord:
    """Return the TongueRecord for the named tongue."""
    if name not in _BY_NAME:
        raise KeyError(f"Tongue '{name}' not in registry")
    return _BY_NAME[name]


def tongues_with_entry_count(count: int) -> Tuple[TongueRecord, ...]:
    """Return all tongues whose entry count equals count."""
    return tuple(t for t in TONGUE_REGISTRY if t.entry_count == count)


def tongues_in_group(group_number: int) -> Tuple[TongueRecord, ...]:
    """Return all registered tongues belonging to the given group."""
    return tuple(t for t in TONGUE_REGISTRY if t.group == group_number)


def tongues_in_cluster(group_number: int, cluster_number: int) -> Tuple[TongueRecord, ...]:
    """Return all registered tongues in the given group/cluster."""
    return tuple(
        t for t in TONGUE_REGISTRY
        if t.group == group_number and t.cluster == cluster_number
    )


def group_signature(group_number: int) -> Optional[Factorization]:
    """Return the factorization signature of the given group."""
    for g in GROUP_REGISTRY:
        if g.number == group_number:
            return g.factorization
    return None


def factorization_shares_prime(a: Factorization, b: Factorization) -> Tuple[int, ...]:
    """Return primes shared between two factorizations — structural resonance points."""
    return tuple(sorted(set(a.primes()) & set(b.primes())))


# ---------------------------------------------------------------------------
# Prime boundary sequence (theoretical — +2 rule from T12 onward)
# Span = tongues predicted to use each entry count under the strict rule.
# Actual placements may deviate (tongues arrive; they are not generated).
# ---------------------------------------------------------------------------

PRIME_BOUNDARY_SEQUENCE: Final[Tuple[Tuple[int, int, int], ...]] = (
    # (entry_count, opening_prime, theoretical_span_length)
    # span_length = next_prime - opening_prime
    (32,  11, 2),   # primes 11→13: theoretical T12–T13
    (34,  13, 4),   # primes 13→17: theoretical T14–T16  (actual: T14–T17, +1 due to Immune)
    (36,  17, 2),   # primes 17→19: theoretical T17–T18  (actual: T18–T19)
    (38,  19, 4),   # primes 19→23: theoretical T19–T22  (actual: T20–T23)
    (40,  23, 6),   # primes 23→29: theoretical T23–T28  (actual: T24–T29)
    (42,  29, 2),   # primes 29→31: theoretical T29–T30  (actual: T30–T31)
    (44,  31, 6),   # primes 31→37: theoretical T31–T36  (actual: T32–T36+)
    (46,  37, 4),   # primes 37→41: theoretical T37–T40
    (48,  41, 2),   # primes 41→43: theoretical T41–T42
    (50,  43, 4),   # primes 43→47: theoretical T43–T46
    (52,  47, 6),   # primes 47→53: theoretical T47–T52
    (54,  53, 6),   # primes 53→59: theoretical T53–T58
)
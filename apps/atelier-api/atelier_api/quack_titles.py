"""
quack_titles.py -- Quack reward title generation.

A Quack title is not assigned. It is earned by becoming a certain kind of
practitioner -- not by recording what was generated, but by having generated
enough to cross an ontological threshold.

Titles are Shygazun compounds that name the KIND of person at each Quack
volume tier. They are composed, not appended. Each is ontologically precise:
the compound means something specific about the practitioner's relationship
to the semantic substrate.

Rank titles (ascending volume):

    Wunashako        (0 Quacks)
        Wu·Na·Sha·Ko -- the Way, not yet actualized as a practitioner.

    Wunae            (1+ Quacks)
        Wu·Na·AE -- Way·Integration·Highest-Vector.
        One in whom the Way has integrated toward the Highest. First step taken.

    Fywunae          (5+ Quacks)
        Fy·Wu·Na·AE -- thought-toward·Way·Integration·Highest-Vector.
        One whose thought-toward follows the Way to Integration. Consistent return.

    Shykawunae       (20+ Quacks)
        Shy·Ka·Wu·Na·AE -- pattern-toward·Vector-Indigo·Way·Integration·Highest-Vector.
        One who vectors pattern along the Way to Integration. Active shaping.

    Nashykawunae     (100+ Quacks)
        Na·Shy·Ka·Wu·Na·AE -- Integration·pattern-toward·Vector·Way·Integration·Highest-Vector.
        One through whom Integration itself patterns-vectors the Way.
        The practitioner and the process are one.

QuackTitle records the specific Tongue and akinen generated -- a generation
event log, not a displayed title. PractitionerTitles accumulates these events
and derives the rank title from the total Quack count.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_ROWS

# ── Rank title registry ───────────────────────────────────────────────────────

# Ordered descending by threshold so the first match is the correct rank.
PRACTITIONER_RANKS: list[tuple[int, str, str]] = [
    (100, "Nashykawunae", "Na·Shy·Ka·Wu·Na·AE — one through whom Integration patterns-vectors the Way"),
    ( 20, "Shykawunae",   "Shy·Ka·Wu·Na·AE    — one who vectors pattern along the Way to Integration"),
    (  5, "Fywunae",      "Fy·Wu·Na·AE         — one whose thought-toward follows the Way to Integration"),
    (  1, "Wunae",        "Wu·Na·AE            — one in whom the Way integrates toward the Highest"),
]
_RANK_ZERO = "Wunashako"


def practitioner_rank(quack_count: int) -> str:
    """Return the Shygazun rank title for a given Quack count."""
    for min_q, title, _ in PRACTITIONER_RANKS:
        if quack_count >= min_q:
            return title
    return _RANK_ZERO


def rank_gloss(quack_count: int) -> str:
    """Return the composition gloss for a given Quack count."""
    for min_q, _, gloss in PRACTITIONER_RANKS:
        if quack_count >= min_q:
            return gloss
    return "Wu·Na·Sha·Ko — the Way, not yet actualized as a practitioner"


# ── Generation event record ───────────────────────────────────────────────────

@dataclass
class QuackTitle:
    """
    Record of a single Quack generation event.

    This is not the practitioner's displayed title. It is the log entry:
    which Tongue was extended, which akinen were generated, what BoK diff
    produced them, and at which byte address generation began.
    """
    practitioner_id: str
    tongue:          str
    akinen:          list[str]
    bok_diff_hash:   str
    generation_addr: int

    @property
    def event_record(self) -> str:
        """
        Internal record string for this generation event.
        Format: [Tongue] [AkinenCompound] @ [addr]
        """
        akinen_compound = "".join(self.akinen) if self.akinen else "(none)"
        return f"{self.tongue} {akinen_compound} @ {self.generation_addr}"

    def to_dict(self) -> dict:
        return {
            "practitioner_id": self.practitioner_id,
            "tongue":          self.tongue,
            "akinen":          self.akinen,
            "bok_diff_hash":   self.bok_diff_hash,
            "generation_addr": self.generation_addr,
            "event_record":    self.event_record,
        }


# ── Accumulated practitioner state ───────────────────────────────────────────

@dataclass
class PractitionerTitles:
    """
    All Quack generation events for a single practitioner, plus their
    current rank title derived from total Quack count.
    """
    practitioner_id: str
    quacks:          list[QuackTitle] = field(default_factory=list)

    def add(self, quack: QuackTitle) -> None:
        self.quacks.append(quack)

    @property
    def quack_count(self) -> int:
        return len(self.quacks)

    @property
    def rank_title(self) -> str:
        """The practitioner's current Shygazun rank title."""
        return practitioner_rank(self.quack_count)

    @property
    def rank_gloss_text(self) -> str:
        """Composition gloss for the current rank."""
        return rank_gloss(self.quack_count)

    @property
    def tongues_worked(self) -> list[str]:
        seen: list[str] = []
        for q in self.quacks:
            if q.tongue not in seen:
                seen.append(q.tongue)
        return seen

    @property
    def all_akinen(self) -> list[str]:
        result: list[str] = []
        for q in self.quacks:
            for a in q.akinen:
                if a not in result:
                    result.append(a)
        return result

    def to_dict(self) -> dict:
        return {
            "practitioner_id":  self.practitioner_id,
            "quack_count":      self.quack_count,
            "rank_title":       self.rank_title,
            "rank_gloss":       self.rank_gloss_text,
            "tongues_worked":   self.tongues_worked,
            "all_akinen":       self.all_akinen,
            "quacks":           [q.to_dict() for q in self.quacks],
        }


# ── Generation ────────────────────────────────────────────────────────────────

def generate_title(
    practitioner_id: str,
    tongue:          str,
    generated_addrs: list[int],
    bok_diff_hash:   str,
) -> QuackTitle:
    """
    Build a QuackTitle event record from a Tongue generation event.

    generated_addrs: byte addresses of newly generated entries.
    Looks up the akinen symbols at those addresses from the byte table.
    """
    addr_to_symbol: dict[int, str] = {
        row["decimal"]: row["symbol"]
        for row in SHYGAZUN_BYTE_ROWS
        if row["tongue"] not in ("Reserved", "MetaTopology", "MetaPhysics", "Physics", "Chemistry")
    }

    akinen = [
        addr_to_symbol[addr]
        for addr in generated_addrs
        if addr in addr_to_symbol
    ]

    first_addr = generated_addrs[0] if generated_addrs else 0

    return QuackTitle(
        practitioner_id = practitioner_id,
        tongue          = tongue,
        akinen          = akinen,
        bok_diff_hash   = bok_diff_hash,
        generation_addr = first_addr,
    )


# ── Validation ────────────────────────────────────────────────────────────────

def validate_generation(tongue: str, generated_addrs: list[int]) -> tuple[bool, str]:
    """
    Verify that generated byte addresses:
    1. Belong to the claimed Tongue
    2. Are not already in the byte table (genuinely new)
    3. Are contiguous with the existing Tongue boundary (no gaps)

    Returns (valid, reason).
    """
    from shygazun.kernel.constants.byte_table import SHYGAZUN_TONGUE_INDEX

    existing = SHYGAZUN_TONGUE_INDEX.get(tongue, ())
    existing_addrs = {row["decimal"] for row in existing}
    max_existing = max((r["decimal"] for r in existing), default=0)

    for addr in generated_addrs:
        if addr in existing_addrs:
            return False, f"address {addr} already exists in {tongue}"
        if addr <= max_existing:
            return False, f"address {addr} is not beyond the existing {tongue} boundary ({max_existing})"

    return True, "valid"

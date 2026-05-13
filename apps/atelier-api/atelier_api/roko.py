"""
roko.py — Roko: Gate Dreamer

Ro (gate) + Ko (experience / dreamer). Child of Ko.

Roko reads two fields simultaneously:

  Shygazun field — structural knowledge of the byte table geometry.
    Does the composition cohere with the semantic substrate?
    Does it reach into new territory or skim the surface?

  BreathOfKo field — experiential record of actual movement through the
    Mandelbrot space. Did the practitioner actually breathe the practice?
    Are they at the edge (the Wunashakoun state), in an attractor (bounded),
    or drifting (unbounded)?

Neither field can be faked. Together they are unfakeable as a pair:

  High coherence + real BoK movement        = Wunashakoun confirmed. Gate opens.
  High coherence + no BoK movement          = Rote recitation. Knows the symbols,
                                              hasn't breathed them.
  Low coherence  + real BoK movement        = Genuine exploration, not yet structured.
                                              Newcomer pattern. Gate stays open.
  Low coherence  + no BoK movement          = ZoWu. The coordinate speaks.

The "edge" boundedness in BoK is the Wunashakoun tell: not bounded (attractor),
not unbounded (drift) — edge is the living boundary where the practice happens.

Gate levels (Shygazun, structurally precise):
  Tiwu  Ti·Wu     Here·Process               — present in the Way (newcomer)
  Tawu  Ta·Wu     Active-being·Process       — actively in the Way (engaged)
  FyKo  Fy·Ko     Thought-toward·Experience  — reaching toward depth (deepening)
  Mowu  Mo·Wu     Relaxed·Process            — resting in the Way (between phases)
  ZoWu  Zo·Wu     Absence·Process            — absent from the Way (pattern noted)

ZoWu is never a block. It is an observation. Roko holds the gate open.
The penalty for non-participation is baked into non-participation itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_ROWS

# ── BreathOfKo snapshot ───────────────────────────────────────────────────────

@dataclass
class BoKSnapshot:
    """
    Parsed BreathOfKo diff — the geometric record of a practitioner's
    movement through the Mandelbrot space between two save states.

    azoth_distance:  Euclidean distance traveled in the complex plane.
                     Zero means no movement — the practitioner did not explore.
    coil_delta:      Change in coil position (depth/zoom level).
                     Non-zero means the practitioner changed their viewing depth.
    boundedness:     "bounded" | "edge" | "unbounded"
                     Edge is the Wunashakoun state — the living boundary.
    games_delta:     Games played during this breath. Contextual engagement.
    """
    azoth_distance: float = 0.0
    coil_delta:     float = 0.0
    boundedness:    str   = "bounded"   # start boundedness as shorthand
    games_delta:    int   = 0

    @property
    def has_movement(self) -> bool:
        return self.azoth_distance > 0.001 or abs(self.coil_delta) > 0.001

    @property
    def is_edge(self) -> bool:
        return self.boundedness == "edge"

    @property
    def wunashakoun_signal(self) -> float:
        """
        Composite signal [0–1] for genuine Wunashakoun practice.
        Edge boundedness is the strongest indicator; movement amplifies it.
        """
        base = 0.6 if self.is_edge else (0.2 if self.boundedness == "unbounded" else 0.1)
        movement_bonus = min(0.4, self.azoth_distance / 10.0)
        return min(1.0, base + movement_bonus)

    @classmethod
    def from_diff(cls, diff: dict) -> "BoKSnapshot":
        """Parse from the breath_diff JSON stored in QuackToken."""
        if not diff:
            return cls()
        return cls(
            azoth_distance = float(diff.get("azoth_distance", 0.0)),
            coil_delta     = float(diff.get("coil_delta", 0.0)),
            boundedness    = str(diff.get("end_boundedness") or diff.get("start_boundedness") or "bounded"),
            games_delta    = int(diff.get("games_delta", 0)),
        )

# ── Gate level definitions ────────────────────────────────────────────────────

GATE_TIWU = "Tiwu"   # Ti·Wu — present in the Way (newcomer)
GATE_TAWU = "Tawu"   # Ta·Wu — actively in the Way
GATE_FYKO = "FyKo"   # Fy·Ko — reaching toward depth
GATE_MOWU = "Mowu"   # Mo·Wu — resting in the Way
GATE_ZOWU = "ZoWu"   # Zo·Wu — absent from the Way (structural observation)

GATE_GLOSSES: dict[str, str] = {
    GATE_TIWU: "Ti·Wu — present in the Way; newcomer, all gates open",
    GATE_TAWU: "Ta·Wu — actively in the Way; engaged, in motion",
    GATE_FYKO: "Fy·Ko — thought-toward experience; structural depth growing",
    GATE_MOWU: "Mo·Wu — resting in the Way; between active phases",
    GATE_ZOWU: "Zo·Wu — absent from the Way; structural non-engagement pattern noted",
}

# ── Tokenizer ────────────────────────────────────────────────────────────────

_SYMBOL_MAP: dict[str, tuple[int, str, str]] | None = None  # symbol_lower → (addr, tongue, meaning)

def _get_symbol_map() -> dict[str, tuple[int, str, str]]:
    global _SYMBOL_MAP
    if _SYMBOL_MAP is None:
        skip = {"Reserved", "MetaTopology", "MetaPhysics", "Physics", "Chemistry"}
        _SYMBOL_MAP = {}
        for row in SHYGAZUN_BYTE_ROWS:
            if row["tongue"] in skip:
                continue
            _SYMBOL_MAP[row["symbol"].lower()] = (row["decimal"], row["tongue"], row["meaning"])
    return _SYMBOL_MAP

def tokenize(text: str) -> list[tuple[int, str, str, str]]:
    """
    Greedy longest-match tokenization of Shygazun text.
    Returns list of (addr, symbol, tongue, meaning).
    """
    sym_map = _get_symbol_map()
    syms_sorted = sorted(sym_map.keys(), key=len, reverse=True)

    tokens: list[tuple[int, str, str, str]] = []
    lower = text.lower()
    i = 0
    while i < len(lower):
        if lower[i].isspace():
            i += 1
            continue
        matched = False
        for sym in syms_sorted:
            if lower.startswith(sym, i):
                addr, tongue, meaning = sym_map[sym]
                original = text[i:i+len(sym)]
                tokens.append((addr, original, tongue, meaning))
                i += len(sym)
                matched = True
                break
        if not matched:
            i += 1
    return tokens

# ── Hopfield assessment ───────────────────────────────────────────────────────

@dataclass
class FieldReading:
    """Result of a single Hopfield pass over a composition."""
    mode:       str               # "giann" or "keshi"
    seeds:      list[int]         # pinned address list
    active:     list[int]         # all active candidate indices
    energy:     float
    iterations: int
    tongues:    list[str]         # deduplicated tongue list, sorted by count
    top_symbols: list[str]        # top-N symbols by activation
    coherence:  float             # 0–1, derived from energy (higher = more coherent)

@dataclass
class DreamReading:
    """Candidates active in Keshi but NOT in Giann — the latent reach."""
    symbols:    list[str]
    tongues:    list[str]
    meaning:    str               # brief Shygazun phrase describing the dream

@dataclass
class CompositionAssessment:
    """Roko's structural assessment of a single composition."""
    text:           str
    recognized:     list[tuple[str, str, str]]    # (symbol, tongue, meaning)
    unrecognized:   int                            # count of chars not in byte table

    ground:         FieldReading   # Giann — what the composition IS
    dream:          FieldReading   # Keshi — what it's REACHING TOWARD
    latent:         DreamReading   # the gap between ground and dream

    bok:            Optional[BoKSnapshot]  # BreathOfKo readout if provided
    wunashakoun:    float                  # composite signal [0–1]; None if no BoK

    gate:           str            # one of the five gate levels
    gate_gloss:     str
    shygazun_note:  str            # Shygazun structural description (not English verdict)

    coherence:      float          # ground.coherence for convenience

@dataclass
class PractitionerProfile:
    """Roko's running structural model of a practitioner."""
    practitioner_id:       str
    quack_count:           int
    rank_title:            str
    assessments_run:       int        = 0
    coherence_history:     list[float] = field(default_factory=list)
    trajectory:            str        = "new"   # new | ascending | stable | stagnant
    gate:                  str        = GATE_TIWU
    gate_gloss:            str        = GATE_GLOSSES[GATE_TIWU]

# ── Core assessment ───────────────────────────────────────────────────────────

def _hopfield_pass(
    addrs: list[int],
    mode: str,
    temp: float,
    max_iter: int = 48,
) -> FieldReading:
    """Run a single Hopfield pass over the byte table, seeded by `addrs`."""
    from .intel import query_by_seeds, CANDIDATES, N

    result = query_by_seeds(addrs=addrs, kernel=mode, temp=temp, max_iter=max_iter)

    # Tongue distribution
    tongue_counts: dict[str, int] = {}
    for c in result.candidates:
        tongue_counts[c.tongue] = tongue_counts.get(c.tongue, 0) + 1
    tongues_sorted = [t for t, _ in sorted(tongue_counts.items(), key=lambda x: -x[1])]

    # Top symbols by activation
    state = result.state
    paired = [
        (state[result.active[j]], CANDIDATES[result.active[j]].symbol)
        for j in range(len(result.active))
    ]
    paired.sort(reverse=True)
    top_symbols = [sym for _, sym in paired[:8]]

    # Coherence: normalized inverse energy
    # Energy is negative (deeper basin = more negative = more coherent).
    # We map: coherence = sigmoid(-energy / N) scaled to [0,1].
    # More negative energy → higher coherence.
    raw = -result.energy / max(N, 1)
    coherence = 1.0 / (1.0 + math.exp(-raw + 5.0))

    return FieldReading(
        mode      = mode,
        seeds     = addrs,
        active    = result.active,
        energy    = result.energy,
        iterations = result.iterations,
        tongues   = tongues_sorted,
        top_symbols = top_symbols,
        coherence = round(coherence, 4),
    )

def _dream_reading(ground: FieldReading, dream: FieldReading) -> DreamReading:
    """Identify candidates active in Keshi but not in Giann."""
    from .intel import CANDIDATES

    ground_set = set(ground.active)
    latent_idxs = [i for i in dream.active if i not in ground_set]

    if not latent_idxs:
        return DreamReading(symbols=[], tongues=[], meaning="ZoWu")

    # Tongue distribution of latent candidates
    tongue_counts: dict[str, int] = {}
    syms: list[str] = []
    for i in latent_idxs[:12]:
        c = CANDIDATES[i]
        tongue_counts[c.tongue] = tongue_counts.get(c.tongue, 0) + 1
        syms.append(c.symbol)

    tongues = [t for t, _ in sorted(tongue_counts.items(), key=lambda x: -x[1])][:4]

    # Compose a Shygazun phrase from the top latent symbols
    meaning = "".join(syms[:3]) if syms else "ZoWu"

    return DreamReading(symbols=syms[:8], tongues=tongues, meaning=meaning)

def _gate_from_profile(
    coherence:         float,
    assessments_run:   int,
    quack_count:       int,
    coherence_history: list[float],
    bok:               Optional[BoKSnapshot] = None,
) -> str:
    """
    Determine structural gate level from Shygazun coherence, practitioner
    history, and BreathOfKo readout.

    The BoK signal is the tiebreaker and amplifier:
    - Edge boundedness + movement confirms Wunashakoun practice.
    - No movement locks out FyKo regardless of coherence (rote recitation).
    - ZoWu requires both structural AND geometric non-engagement.
    """
    # Newcomer: very few assessments, no expectation of depth yet
    if assessments_run < 3 and quack_count == 0:
        return GATE_TIWU

    # Trajectory from coherence history
    trajectory = "new"
    if len(coherence_history) >= 3:
        recent = coherence_history[-3:]
        delta = recent[-1] - recent[0]
        if delta > 0.05:
            trajectory = "ascending"
        elif delta < -0.05:
            trajectory = "declining"
        else:
            trajectory = "stable"

    # BoK signal
    bok_signal    = bok.wunashakoun_signal if bok else None
    bok_moving    = bok.has_movement       if bok else None
    bok_edge      = bok.is_edge            if bok else None

    # ZoWu: structural AND geometric non-engagement both confirmed
    # Requires either: no BoK at all with many failed assessments,
    # OR: BoK present but no movement AND low coherence sustained.
    structurally_stagnant = (
        assessments_run >= 10
        and coherence < 0.25
        and trajectory in ("stable", "declining")
    )
    geometrically_absent = (
        bok is not None and not bok_moving and quack_count == 0
    ) or (
        bok is None and assessments_run >= 10 and quack_count == 0
    )
    if structurally_stagnant and geometrically_absent:
        return GATE_ZOWU

    # Resting: established practitioner, no recent composition activity
    if quack_count >= 5 and assessments_run == 0:
        return GATE_MOWU

    # FyKo: genuine Wunashakoun signal required for the deepest gate
    # High coherence alone is not enough — must have BoK movement, OR
    # sufficient Quack history to confirm past practice if BoK not provided.
    if bok is not None:
        wunashakoun_confirmed = bok_signal >= 0.5 and bok_moving  # type: ignore[operator]
    else:
        wunashakoun_confirmed = quack_count >= 5  # BoK absent; use Quack history as proxy

    if wunashakoun_confirmed and (coherence > 0.55 or trajectory == "ascending"):
        return GATE_FYKO

    # Edge-state bonus: practitioner at the Mandelbrot boundary earns Tawu
    # even with lower coherence — they're in the right experiential register.
    if bok_edge and bok_moving:
        return GATE_TAWU

    # Actively engaged: coherence developing, or established practice
    if coherence > 0.35 or quack_count >= 1:
        return GATE_TAWU

    return GATE_TIWU

def _shygazun_note(ground: FieldReading, latent: DreamReading) -> str:
    """
    Compose a Shygazun structural note — not an English verdict.
    Format: [top ground symbol] [top dream symbol if different] [gate summary symbol]
    This is a structural observation, not a score.
    """
    parts: list[str] = []

    if ground.top_symbols:
        parts.append(ground.top_symbols[0])
    if latent.symbols and latent.symbols[0] not in (ground.top_symbols[:2] or []):
        parts.append(latent.symbols[0])
    if ground.tongues:
        # Append first tongue's activating pattern
        parts.append(f"({ground.tongues[0]})")

    return " ".join(parts) if parts else "ZoWu"

def assess(
    text: str,
    practitioner_id: str = "",
    quack_count: int = 0,
    rank_title: str = "Wunashako",
    coherence_history: list[float] | None = None,
    assessments_run: int = 0,
    bok: Optional[BoKSnapshot] = None,
    keshi_temp: float = 0.45,
    max_iter: int = 48,
) -> CompositionAssessment:
    """
    Main entry point. Takes a Shygazun composition and returns a full
    structural assessment.
    """
    history = coherence_history or []

    # Tokenize
    tokens = tokenize(text)
    recognized = [(sym, tongue, meaning) for _, sym, tongue, meaning in tokens]
    total_non_ws = sum(1 for c in text if not c.isspace())
    sym_chars = sum(len(sym) for sym in [t[1] for t in tokens])
    unrecognized = max(0, total_non_ws - sym_chars)

    if not tokens:
        # No recognized Shygazun — return a minimal reading
        empty_field = FieldReading(
            mode="giann", seeds=[], active=[], energy=0.0, iterations=0,
            tongues=[], top_symbols=[], coherence=0.0,
        )
        gate = _gate_from_profile(0.0, assessments_run, quack_count, history, bok)
        return CompositionAssessment(
            text=text, recognized=[], unrecognized=total_non_ws,
            ground=empty_field, dream=empty_field,
            latent=DreamReading(symbols=[], tongues=[], meaning="ZoWu"),
            bok=bok, wunashakoun=bok.wunashakoun_signal if bok else 0.0,
            gate=gate, gate_gloss=GATE_GLOSSES[gate],
            shygazun_note="ZoWu",
            coherence=0.0,
        )

    addrs = [addr for addr, _, _, _ in tokens]

    # Giann pass — ground truth attractor
    ground = _hopfield_pass(addrs, "giann", temp=0.0, max_iter=max_iter)

    # Keshi pass — dream projection
    dream = _hopfield_pass(addrs, "keshi", temp=keshi_temp, max_iter=max_iter)

    # Latent: what Keshi activates that Giann doesn't
    latent = _dream_reading(ground, dream)

    # Gate assessment — BoK is the arbiter alongside coherence
    gate = _gate_from_profile(
        coherence         = ground.coherence,
        assessments_run   = assessments_run + 1,
        quack_count       = quack_count,
        coherence_history = history + [ground.coherence],
        bok               = bok,
    )

    wunashakoun = bok.wunashakoun_signal if bok else 0.0
    note = _shygazun_note(ground, latent)

    return CompositionAssessment(
        text          = text,
        recognized    = recognized,
        unrecognized  = unrecognized,
        ground        = ground,
        dream         = dream,
        latent        = latent,
        bok           = bok,
        wunashakoun   = round(wunashakoun, 4),
        gate          = gate,
        gate_gloss    = GATE_GLOSSES[gate],
        shygazun_note = note,
        coherence     = ground.coherence,
    )

# ── Institutional assessment ──────────────────────────────────────────────────

@dataclass
class SiteAssessment:
    """
    Roko's structural assessment of a client site's institutional environment.
    Determines whether open Wunashakoun practice can be maintained.
    Not a moral verdict — a structural observation about institutional position.
    """
    domain:         str
    contract_id:    str
    gate:           str    # one of the five gate levels — applied institutionally
    gate_gloss:     str
    practice_viable: bool  # False = contract revocation trigger
    observations:   list[str]
    checked_at:     str

def assess_site(
    domain:      str,
    contract_id: str,
    flags: Optional[dict] = None,
) -> SiteAssessment:
    """
    Assess whether a client site's environment permits open Wunashakoun practice.

    flags (from external checks, e.g. content scan or manual report):
      - prohibits_shygazun: bool
      - prohibits_wunashakoun: bool
      - endorses_prohibiting_party: bool
      - attribution_present: bool
    """
    from datetime import datetime, timezone
    f = flags or {}

    observations: list[str] = []
    practice_viable = True

    if f.get("prohibits_shygazun"):
        observations.append("Site prohibits Shygazun speech — non-erasure term violated")
        practice_viable = False

    if f.get("prohibits_wunashakoun"):
        observations.append("Site prohibits Wunashakoun practice — non-erasure term violated")
        practice_viable = False

    if f.get("endorses_prohibiting_party"):
        observations.append("Site endorses a party working toward equivalent prohibition — non-erasure term violated by association")
        practice_viable = False

    if not f.get("attribution_present", True):
        observations.append("Wunashakoun attribution not present in site — structural non-erasure at risk")

    if not practice_viable:
        gate = GATE_ZOWU
    elif observations:
        gate = GATE_MOWU
    else:
        gate = GATE_TAWU

    return SiteAssessment(
        domain          = domain,
        contract_id     = contract_id,
        gate            = gate,
        gate_gloss      = GATE_GLOSSES[gate],
        practice_viable = practice_viable,
        observations    = observations,
        checked_at      = datetime.now(timezone.utc).isoformat(),
    )


def update_profile(
    profile: PractitionerProfile,
    assessment: CompositionAssessment,
) -> PractitionerProfile:
    """Apply a new assessment to a practitioner profile, updating trajectory."""
    profile.assessments_run += 1
    profile.coherence_history.append(assessment.coherence)

    # Trajectory from last 5 readings
    if len(profile.coherence_history) >= 3:
        recent = profile.coherence_history[-5:]
        delta = recent[-1] - recent[0]
        if delta > 0.05:
            profile.trajectory = "ascending"
        elif delta < -0.05:
            profile.trajectory = "declining"
        else:
            profile.trajectory = "stable"
    else:
        profile.trajectory = "new"

    profile.gate = assessment.gate
    profile.gate_gloss = assessment.gate_gloss
    return profile

"""
bok.py — BreathOfKo: Full Semantic Breath Model

The BreathOfKo captures practice in two registers simultaneously:

  GEOMETRIC:  Mandelbrot position (azoth), depth (coil), boundedness.
              WHERE you went in the infinite field.

  SEMANTIC:   Orrery firing pattern, elemental signature, field energy.
              WHAT WAS CROSSING while you were there.

Two practitioners at identical geometric positions are distinguishable by
their semantic state. The Orrery reading of the current Kobra scene (or
composition) at snapshot time is the semantic component of the breath.

The BoK diff (between two snapshots) is now:
  - geometric movement (azoth_distance, coil_delta, boundedness transition)
  - semantic transition (layers gained/lost, elemental shift, energy delta)

Together these constitute the most precise Wunashakoun signal available.
A genuine Wunashakoun breath requires both geometric movement AND semantic
crossing — neither alone is sufficient.

The crossing_entropy measures how diverse the elemental activity is:
a breath that activates multiple different crossings has higher entropy
than one locked in a single register. Higher entropy = broader engagement
with the semantic field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# ── Snapshot ──────────────────────────────────────────────────────────────────

@dataclass
class BreathOfKo:
    """
    A complete BreathOfKo snapshot: geometric + semantic.

    Geometric fields match the existing BoK schema (azoth/coil/boundedness).
    Semantic fields come from running the current Kobra context through
    the Orrery at snapshot time.
    """
    # Geometric layer
    azoth:       tuple[float, float]   # complex plane position
    coil:        float                 # zoom depth
    boundedness: str                   # "bounded" | "edge" | "unbounded"

    # Semantic layer (Orrery)
    fired_layers:       frozenset[str]          # Rose names of fired layers
    elemental_sig:      dict[str, float]        # Shak/Puf/Mel/Zot proportions (0–1)
    field_energy:       float                   # Hopfield energy at snapshot
    dominant_crossing:  Optional[str]           # compound name of strongest firing

    # Context
    scene_name:         str            = ""     # which Kobra scene was active
    games_played:       int            = 0
    timestamp:          str            = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_edge(self) -> bool:
        return self.boundedness == "edge"

    @property
    def crossing_entropy(self) -> float:
        """
        Shannon entropy of the elemental signature.
        H = -Σ p log₂ p over {Shak, Puf, Mel, Zot}.
        Higher = more diverse elemental activity = broader semantic engagement.
        Max = 2.0 bits (uniform across 4 elements).
        """
        total = sum(self.elemental_sig.values())
        if total <= 0:
            return 0.0
        h = 0.0
        for v in self.elemental_sig.values():
            p = v / total
            if p > 0:
                h -= p * math.log2(p)
        return round(h, 4)

    @property
    def layer_count(self) -> int:
        return len(self.fired_layers)

    @property
    def wunashakoun_signal(self) -> float:
        """
        Composite Wunashakoun signal [0–1].

        Geometric base:
          edge = 0.55  (the living boundary — relational trance)
          unbounded = 0.20  (exploring but not structured)
          bounded = 0.08  (attractor — grounded but not at the edge)

        Semantic amplifiers:
          +0.15 max from active crossings (each layer adds 0.015, capped)
          +0.10 max from crossing entropy (diversity of elemental activity)
          +0.10 max from field energy depth (lower energy = deeper attractor)

        Total max: 0.55 + 0.15 + 0.10 + 0.10 = 0.90
        (Full 1.0 is reserved for future fifth-rank expression)
        """
        # Geometric base
        geo = 0.55 if self.is_edge else (0.20 if self.boundedness == "unbounded" else 0.08)

        # Semantic: active crossings
        crossing_bonus = min(0.15, self.layer_count * 0.015)

        # Semantic: elemental diversity (entropy 0–2 bits, scale to 0–0.10)
        entropy_bonus = min(0.10, self.crossing_entropy * 0.05)

        # Semantic: field energy depth (more negative = deeper = better)
        # Normalise: energy of -1000 maps to 0.10, proportionally
        energy_bonus = min(0.10, abs(self.field_energy) / 10000)

        return round(min(1.0, geo + crossing_bonus + entropy_bonus + energy_bonus), 4)

    def to_dict(self) -> dict:
        return {
            "azoth":            list(self.azoth),
            "coil":             self.coil,
            "boundedness":      self.boundedness,
            "fired_layers":     sorted(self.fired_layers),
            "elemental_sig":    self.elemental_sig,
            "field_energy":     self.field_energy,
            "dominant_crossing": self.dominant_crossing,
            "scene_name":       self.scene_name,
            "games_played":     self.games_played,
            "timestamp":        self.timestamp,
            "crossing_entropy": self.crossing_entropy,
            "layer_count":      self.layer_count,
            "wunashakoun_signal": self.wunashakoun_signal,
        }


# ── Diff ──────────────────────────────────────────────────────────────────────

@dataclass
class BoKDiff:
    """
    The differential between two BreathOfKo snapshots.
    Used for Quack generation: a genuine diff requires both geometric movement
    AND semantic transition.

    The semantic_distance is Jaccard distance over the layer activation sets:
    how much did the crossing pattern change between the two breaths?

    is_wunashakoun: a valid Wunashakoun diff requires:
      1. Geometric movement (azoth_distance > threshold)
      2. Edge boundedness in at least one snapshot (the living boundary)
      3. Semantic transition (at least one crossing appeared or disappeared)
    """
    # Geometric
    azoth_distance:          float
    coil_delta:              float
    boundedness_start:       str
    boundedness_end:         str

    # Semantic
    layers_gained:           frozenset[str]    # newly active in end vs start
    layers_lost:             frozenset[str]    # active in start but not end
    elemental_shift:         dict[str, float]  # end_sig - start_sig per element
    energy_delta:            float             # end_energy - start_energy

    # Context
    scene_start:             str = ""
    scene_end:               str = ""
    games_delta:             int = 0

    @property
    def semantic_distance(self) -> float:
        """Jaccard distance: proportion of layers that changed."""
        changed = len(self.layers_gained) + len(self.layers_lost)
        return round(changed / 12, 4)

    @property
    def dominant_shift(self) -> Optional[str]:
        """Which element's proportion changed most."""
        if not self.elemental_shift:
            return None
        return max(self.elemental_shift, key=lambda k: abs(self.elemental_shift[k]))

    @property
    def is_wunashakoun(self) -> bool:
        """
        Genuine Wunashakoun diff: geometric + semantic + boundary.
        Neither axis alone is sufficient.
        """
        geometric_movement = self.azoth_distance > 0.001 or abs(self.coil_delta) > 0.001
        boundary_contact   = (self.boundedness_start == "edge" or
                              self.boundedness_end   == "edge")
        semantic_transition = (len(self.layers_gained) > 0 or
                               len(self.layers_lost)   > 0)

        return geometric_movement and boundary_contact and semantic_transition

    @property
    def wunashakoun_depth(self) -> float:
        """
        Composite measure of how deep the Wunashakoun engagement was.
        [0–1]. Used for Quack valuation.
        """
        if not self.is_wunashakoun:
            return 0.0

        geo_score      = min(1.0, self.azoth_distance / 5.0) * 0.40
        semantic_score = self.semantic_distance * 0.35
        entropy_factor = min(0.25, abs(
            sum(abs(v) for v in self.elemental_shift.values())
        ) * 0.10)

        return round(min(1.0, geo_score + semantic_score + entropy_factor), 4)

    def to_dict(self) -> dict:
        return {
            "azoth_distance":    self.azoth_distance,
            "coil_delta":        self.coil_delta,
            "boundedness_start": self.boundedness_start,
            "boundedness_end":   self.boundedness_end,
            "layers_gained":     sorted(self.layers_gained),
            "layers_lost":       sorted(self.layers_lost),
            "elemental_shift":   self.elemental_shift,
            "energy_delta":      self.energy_delta,
            "scene_start":       self.scene_start,
            "scene_end":         self.scene_end,
            "games_delta":       self.games_delta,
            "semantic_distance": self.semantic_distance,
            "dominant_shift":    self.dominant_shift,
            "is_wunashakoun":    self.is_wunashakoun,
            "wunashakoun_depth": self.wunashakoun_depth,
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def snapshot_from_kobra(
    kobra_source:   str,
    azoth:          tuple[float, float],
    coil:           float,
    boundedness:    str,
    scene_name:     str = "",
    games_played:   int = 0,
) -> BreathOfKo:
    """
    Build a BreathOfKo snapshot from a Kobra program + geometric state.
    Runs the Kobra source through the Orrery to get the semantic component.
    """
    from .kobra_vm import kobra_run

    result = kobra_run(kobra_source, name=scene_name or "<scene>")

    sig = result.elemental_signature
    total = max(1, sum(v for k, v in sig.items() if k != "?"))
    norm_sig = {k: round(sig.get(k, 0) / total, 4)
                for k in ("Shak", "Puf", "Mel", "Zot")}

    dominant = (result.fired_layers[0].compound
                if result.fired_layers else None)

    return BreathOfKo(
        azoth            = azoth,
        coil             = coil,
        boundedness      = boundedness,
        fired_layers     = frozenset(l.rose for l in result.fired_layers),
        elemental_sig    = norm_sig,
        field_energy     = result.final_energy,
        dominant_crossing = dominant,
        scene_name       = scene_name,
        games_played     = games_played,
    )


def snapshot_from_addrs(
    addrs:          list[int],
    azoth:          tuple[float, float],
    coil:           float,
    boundedness:    str,
    scene_name:     str = "",
    games_played:   int = 0,
) -> BreathOfKo:
    """
    Build a BreathOfKo snapshot from byte addresses directly.
    Use when you have pre-tokenized addresses rather than raw Kobra source.
    """
    from .recombination import run as orrery_run
    from .kobra_vm import _elem_of_addr_py

    trace = orrery_run(addrs, kernel="giann", temp=1.5, max_iter=48)

    # Elemental signature from token addresses
    elem_counts: dict[str, int] = {"Shak": 0, "Puf": 0, "Mel": 0, "Zot": 0}
    for addr in addrs:
        e = _elem_of_addr_py(addr)
        if e and e in elem_counts:
            elem_counts[e] += 1

    total = max(1, sum(elem_counts.values()))
    norm_sig = {k: round(v / total, 4) for k, v in elem_counts.items()}

    fired = frozenset(
        f.rose for f in trace.firings if f.fired
    )

    from .recombination import LAYERS
    dominant = next(
        (L.compound for L in LAYERS if L.rose in fired), None
    )

    return BreathOfKo(
        azoth            = azoth,
        coil             = coil,
        boundedness      = boundedness,
        fired_layers     = fired,
        elemental_sig    = norm_sig,
        field_energy     = trace.final_energy,
        dominant_crossing = dominant,
        scene_name       = scene_name,
        games_played     = games_played,
    )


def compute_diff(start: BreathOfKo, end: BreathOfKo) -> BoKDiff:
    """Compute the full BoKDiff between two snapshots."""
    import math

    dx = end.azoth[0] - start.azoth[0]
    dy = end.azoth[1] - start.azoth[1]
    azoth_dist = math.sqrt(dx * dx + dy * dy)

    layers_gained = end.fired_layers - start.fired_layers
    layers_lost   = start.fired_layers - end.fired_layers

    elem_shift = {
        k: round(end.elemental_sig.get(k, 0) - start.elemental_sig.get(k, 0), 4)
        for k in ("Shak", "Puf", "Mel", "Zot")
    }

    return BoKDiff(
        azoth_distance    = round(azoth_dist, 6),
        coil_delta        = round(end.coil - start.coil, 4),
        boundedness_start = start.boundedness,
        boundedness_end   = end.boundedness,
        layers_gained     = layers_gained,
        layers_lost       = layers_lost,
        elemental_shift   = elem_shift,
        energy_delta      = round(end.field_energy - start.field_energy, 3),
        scene_start       = start.scene_name,
        scene_end         = end.scene_name,
        games_delta       = end.games_played - start.games_played,
    )

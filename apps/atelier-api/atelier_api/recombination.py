"""
recombination.py — 12-Layer Elemental Crossing Architecture

The Orrery runs natively. Each of the 12 layers corresponds to one of the
12 non-self AppleBlossom crossing compounds. Layers are assigned to Rose
numeral positions by offset-column interleaving of the 4×3 crossing table.

Primary element sequence (surface):    scattered — no readable gradient
Secondary element (destination) seq:   Fire→Air→Water→Earth × 3 (emergent)

The thermodynamic descent lives in the destinations, not the origins.
You find it by tracing where each layer is going.

Orrery cue: a layer fires when all 4 cue-cluster byte addresses are active
(state > 0.5) in the current Hopfield field.

Recombination: when a layer fires, the field is advanced through a weighted
crossing convergence — seeded from both primary and destination element
candidates, with alpha (crossing weight) scaling by thermodynamic depth.

Elemental sub-register assignments (by initial consonant):
  Lotus:     S/K = Shak/Fire   F/P = Puf/Air   L/M = Mel/Water   T/Z = Zot/Earth
  Sakura:    V   = Shak/Fire   B   = Puf/Air    D   = Mel/Water   J   = Zot/Earth
  Grapevine: K   = Shak/Fire   S   = Puf/Air    M   = Mel/Water   D   = Zot/Earth
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .intel import (
    CANDIDATES, N, ADDR,
    build_weight_matrix, hopfield_converge, hopfield_step,
)

# ── Elemental sub-register detection ─────────────────────────────────────────

_LOTUS_FIRE  = frozenset({'S', 'K'})   # Shy/Sha/Shi  Ku/Ko/Ke
_LOTUS_AIR   = frozenset({'F', 'P'})   # Fy/Fi/Fa     Pu/Pe/Po
_LOTUS_WATER = frozenset({'L', 'M'})   # Ly/La/Li     Mu/Mo/Me
_LOTUS_EARTH = frozenset({'T', 'Z'})   # Ty/Ti/Ta     Zu/Zo/Ze

_SAKURA_ELEM = {'V': 'Shak', 'B': 'Puf', 'D': 'Mel', 'J': 'Zot'}
_GRAPEVINE_ELEM = {'K': 'Shak', 'S': 'Puf', 'M': 'Mel', 'D': 'Zot'}

def candidate_element(idx: int) -> Optional[str]:
    """Return the elemental register of a candidate, or None if outside the 4-tongue scope."""
    c = CANDIDATES[idx]
    s = c.symbol
    t = c.tongue

    if t == "Lotus":
        ch = s[0].upper()
        if ch in _LOTUS_FIRE:  return "Shak"
        if ch in _LOTUS_AIR:   return "Puf"
        if ch in _LOTUS_WATER: return "Mel"
        if ch in _LOTUS_EARTH: return "Zot"

    elif t == "Sakura":
        return _SAKURA_ELEM.get(s[0].upper())

    elif t == "Grapevine":
        return _GRAPEVINE_ELEM.get(s[0].upper())

    elif t == "AppleBlossom":
        if s in ("Shak",):       return "Shak"
        if s in ("Puf",):        return "Puf"
        if s in ("Mel",):        return "Mel"
        if s in ("Zot",):        return "Zot"

    return None

# Pre-compute element → candidate index lists (for performance)
_ELEM_CANDIDATES: dict[str, list[int]] = {"Shak": [], "Puf": [], "Mel": [], "Zot": []}
for _i in range(N):
    _e = candidate_element(_i)
    if _e:
        _ELEM_CANDIDATES[_e].append(_i)

def element_candidates(element: str) -> list[int]:
    return _ELEM_CANDIDATES.get(element, [])

# Address → candidate index lookup
_ADDR_TO_IDX: dict[int, int] = {int(CANDIDATES[i].addr): i for i in range(N)}


def elem_of_addr(addr: int) -> Optional[str]:
    """
    Return the elemental register for a byte address, or None.
    Mirrors the Rust address-range detection in recombination.rs.
    """
    # Lotus
    if addr in (0, 1, 8, 9, 16, 20):     return "Zot"
    if addr in (2, 3, 10, 11, 17, 21):   return "Mel"
    if addr in (4, 5, 12, 13, 18, 22):   return "Puf"
    if addr in (6, 7, 14, 15, 19, 23):   return "Shak"
    # Sakura
    if 48 <= addr <= 53:                  return "Zot"
    if 54 <= addr <= 59:                  return "Mel"
    if 60 <= addr <= 65:                  return "Puf"
    if 66 <= addr <= 71:                  return "Shak"
    # AppleBlossom pure elements
    if addr == 104:                       return "Shak"
    if addr == 105:                       return "Puf"
    if addr == 106:                       return "Mel"
    if addr == 107:                       return "Zot"
    # Grapevine
    if 156 <= addr <= 162:                return "Puf"
    if 163 <= addr <= 169:                return "Mel"
    if 170 <= addr <= 176:                return "Zot"
    if 177 <= addr <= 183:                return "Shak"
    return None

# ── Thermodynamic depth per destination ──────────────────────────────────────

_DEST_DEPTH = {"Shak": 0.0, "Puf": 0.33, "Mel": 0.67, "Zot": 1.0}

# ── Layer definitions ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RecombLayer:
    rose:         str                  # Rose numeral name
    rose_index:   int                  # 0–11
    compound:     str                  # AppleBlossom crossing compound
    compound_addr: int                 # byte address of compound
    primary:      str                  # primary element (Shak/Puf/Mel/Zot)
    destination:  str                  # destination element
    cue:          tuple[int,int,int,int]  # 4 byte addresses
    purpose:      str

LAYERS: tuple[RecombLayer, ...] = (
    RecombLayer("Gaoh",     0,  "Puky",  112, "Puf",  "Shak",
                (4, 13, 64, 160),  "Air becoming combustible"),
    RecombLayer("Ao",       1,  "Kypa",  109, "Shak", "Puf",
                (6, 19, 66, 181),  "Fire organizing into atmosphere"),
    RecombLayer("Ye",       2,  "Alky",  110, "Shak", "Mel",
                (7, 23, 67, 182),  "Fire dissolving into solvent"),
    RecombLayer("Ui",       3,  "Kazho", 111, "Shak", "Zot",
                (15, 14, 71, 180), "Fire crystallizing into structure"),
    RecombLayer("Shu",      4,  "Shem",  116, "Mel",  "Shak",
                (2, 11, 55, 166),  "Water reaching toward heat"),
    RecombLayer("Kiel",     5,  "Lefu",  117, "Mel",  "Puf",
                (3, 17, 54, 164),  "Water releasing into vapor"),
    RecombLayer("Yeshu",    6,  "Mipa",  114, "Puf",  "Mel",
                (5, 22, 63, 162),  "Air condensing into residue"),
    RecombLayer("Lao",      7,  "Zitef", 115, "Puf",  "Zot",
                (12, 18, 61, 159), "Air settling into ground"),
    RecombLayer("Shushy",   8,  "Zashu", 120, "Zot",  "Shak",
                (0, 9, 48, 171),   "Earth activating into release"),
    RecombLayer("Uinshu",   9,  "Fozt",  121, "Zot",  "Puf",
                (1, 20, 51, 174),  "Earth dispersing into atmosphere"),
    RecombLayer("Kokiel",   10, "Mazi",  122, "Zot",  "Mel",
                (8, 16, 52, 172),  "Earth dissolving into flow"),
    RecombLayer("Aonkiel",  11, "Myza",  119, "Mel",  "Zot",
                (3, 21, 58, 165),  "Water settling into ground"),
)

# ── Orrery cue checking ───────────────────────────────────────────────────────

def check_cue(layer: RecombLayer, state: list[float] | np.ndarray,
              threshold: float = 0.1) -> bool:
    """
    A layer fires when all 4 cue-cluster addresses exceed the threshold.
    Default threshold 0.1 works with soft tanh fields (temp > 0).
    Use 0.5 for hard binary fields (Giann T=0).
    """
    for addr in layer.cue:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is None or state[idx] <= threshold:
            return False
    return True

def active_layers(state: list[float] | np.ndarray) -> list[int]:
    """Return indices of all layers whose Orrery cues are currently satisfied."""
    return [i for i, L in enumerate(LAYERS) if check_cue(L, state)]

# ── Crossing operation ────────────────────────────────────────────────────────

def recombine_step(
    layer:   RecombLayer,
    state:   np.ndarray,
    temp:    float = 0.35,
    alpha:   Optional[float] = None,
    max_iter: int = 24,
) -> np.ndarray:
    """
    Apply the elemental crossing for one layer.

    The field advances through a weighted blend: primary-element candidates
    are seeded at (1-alpha), destination-element candidates at alpha.
    The cue cluster is pinned throughout. alpha defaults to a function of
    thermodynamic depth — how far down the entropy gradient this crossing
    occurs.
    """
    if alpha is None:
        depth = _DEST_DEPTH[layer.destination]
        alpha = depth * 0.55 + 0.1   # range [0.10, 0.65]

    W = build_weight_matrix("keshi", temp)

    s = state.copy()

    # Pin cue cluster (always active at crossing)
    pinned = []
    for addr in layer.cue:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is not None:
            s[idx] = 1.0
            pinned.append(idx)

    # Blend primary and destination element candidates
    for idx in element_candidates(layer.primary):
        s[idx] = max(s[idx], float(1.0 - alpha))
    for idx in element_candidates(layer.destination):
        s[idx] = max(s[idx], float(alpha))

    s_out, _ = hopfield_converge(s, W, pinned, max_iter=max_iter, temp=temp)
    return s_out

# ── Full run ──────────────────────────────────────────────────────────────────

@dataclass
class LayerFiring:
    rose:        str
    rose_index:  int
    compound:    str
    primary:     str
    destination: str
    purpose:     str
    fired:       bool
    active_idxs: list[int]   # candidate indices active after this layer
    energy:      float

@dataclass
class RecombTrace:
    """Full trace of a 12-layer recombination run."""
    input_addrs:  list[int]
    firings:      list[LayerFiring]
    final_state:  list[float]
    final_active: list[int]
    final_energy: float
    layers_fired: int

def run(
    input_addrs: list[int],
    temp:        float = 0.35,
    max_iter:    int   = 32,
    kernel:      str   = "keshi",
) -> RecombTrace:
    """
    Run a semantic state (specified by byte addresses) through all 12 layers
    in Rose numeral order. Returns the full firing trace.

    Each layer checks its Orrery cue against the current field state.
    If the cue is satisfied, the crossing transformation is applied.

    kernel: "giann" spreads activation globally (inverse-distance) — better
            for Kobra programs where cue addresses may be far from seeds.
            "keshi" is local (exponential decay) — better for precise queries.
    """
    # Initial convergence from input seeds
    W  = build_weight_matrix(kernel, temp)
    s  = np.full(N, -0.2, dtype=np.float32)
    pinned = []
    for addr in input_addrs:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is not None:
            s[idx] = 1.0
            pinned.append(idx)
    s, _ = hopfield_converge(s, W, pinned, max_iter=max_iter, temp=temp)

    firings: list[LayerFiring] = []
    layers_fired = 0

    for layer in LAYERS:
        fired = check_cue(layer, s)
        if fired:
            s = recombine_step(layer, s, temp=temp, max_iter=max_iter // 2)
            layers_fired += 1

        active = [i for i in range(N) if s[i] > 0.5]
        energy = float(-0.5 * (s @ W @ s))

        firings.append(LayerFiring(
            rose        = layer.rose,
            rose_index  = layer.rose_index,
            compound    = layer.compound,
            primary     = layer.primary,
            destination = layer.destination,
            purpose     = layer.purpose,
            fired       = fired,
            active_idxs = active,
            energy      = energy,
        ))

    final_active = [i for i in range(N) if s[i] > 0.5]
    final_energy = float(-0.5 * (s @ W @ s))

    return RecombTrace(
        input_addrs  = input_addrs,
        firings      = firings,
        final_state  = s.tolist(),
        final_active = final_active,
        final_energy = final_energy,
        layers_fired = layers_fired,
    )

def probe(
    input_addrs: list[int],
    temp: float = 0.35,
    max_iter: int = 32,
) -> list[dict]:
    """
    Probe which layers would fire for a given input without running
    the full crossing transformations. Returns layer status without
    mutating the field.
    """
    W = build_weight_matrix("keshi", temp)
    s = np.full(N, -0.2, dtype=np.float32)
    pinned = []
    for addr in input_addrs:
        idx = _ADDR_TO_IDX.get(addr)
        if idx is not None:
            s[idx] = 1.0
            pinned.append(idx)
    s, _ = hopfield_converge(s, W, pinned, max_iter=max_iter, temp=temp)

    return [
        {
            "rose":        L.rose,
            "compound":    L.compound,
            "primary":     L.primary,
            "destination": L.destination,
            "purpose":     L.purpose,
            "would_fire":  check_cue(L, s),
            "cue_active":  [
                _ADDR_TO_IDX.get(a) is not None and s[_ADDR_TO_IDX[a]] > 0.5
                for a in L.cue
            ],
        }
        for L in LAYERS
    ]

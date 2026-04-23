"""
shygazun/kernel/kobra/chromatic.py
====================================
Chromatic interpreter — extends _extract_fields to handle Rose vector
frequency and base-12 amplitude pairs, producing a full spectral profile
across the four elemental sensory registers.

Chromatism is chromatism is chromatism is chromatism.
The seven Rose vectors are universal frequency bands:
  Ru  — lowest / red    — bass / heat-radiant / musk / slow-wave
  Ot  — orange          — low-mid / warm / earthy / low-mid-freq
  El  — yellow          — mid / ambient / sharp-citrus / mid-freq
  Ki  — green           — upper-mid / temperate / fresh / upper-mid
  Fu  — blue            — high-mid / cool / water-clean / high-mid
  Ka  — indigo          — high / cold / resinous / high-freq
  AE  — highest / violet — ultra-high / radiative / ethereal / edge

  Ha  — absolute positive — beyond the numeral scale, all registers max
  Ga  — absolute negative — subtractive, pulls frequency out of field

Base-12 numerals encode amplitude (0–11) per frequency band.
  Gaoh (0) — silent / absent at this frequency
  Ao–Aonkiel (1–11) — dynamic range
  Ha — absolute positive (beyond 11)
  Ga — absolute negative (subtractive)

The four elemental carriers determine the primary sensory register:
  Shak (Fire)  — light
  Puf  (Air)   — sound
  Mel  (Water) — telepathy
  Zot  (Earth) — haptics

Multiple Rose vectors per Akinenwun produce voiced chords.
The leftmost vector is the primary frequency; each subsequent
vector modifies it (head-modifier order, same as all Akinenwun).

Multi-vector Akinenwun with numeral prefixes:
  KielRu   — amplitude 5 at red frequency
  AoEl     — amplitude 1 at yellow frequency
  AonkielKi — amplitude 11 at green frequency

When no numeral prefix is present, amplitude defaults to Yeshu (6)
— the midpoint of the dynamic range.

Kael (Daisy) as structural marker for generative excess — when present,
marks the chromatic event as exceeding single-element containment.
All registers saturate simultaneously under Kael.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .sublayer import segment as sublayer_segment

# ---------------------------------------------------------------------------
# Rose vector frequency definitions
# ---------------------------------------------------------------------------

ROSE_VECTORS: Dict[str, Dict[str, Any]] = {
    "Ru": {
        "frequency": "lowest",
        "registers": {
            "light":    {"color": "red",    "wavelength_nm": 700},
            "sound":    {"band": "bass",    "hz_approx": 80},
            "heat":     {"character": "radiant_heat"},
            "smell":    {"character": "deep_animal_musk"},
            "haptic":   {"character": "slow_wave_low_freq"},
            "telepathy": {"character": "grounded_instinctual"},
        },
    },
    "Ot": {
        "frequency": "orange",
        "registers": {
            "light":    {"color": "orange",  "wavelength_nm": 620},
            "sound":    {"band": "low_mid",  "hz_approx": 200},
            "heat":     {"character": "warm"},
            "smell":    {"character": "earthy_woody"},
            "haptic":   {"character": "low_mid_frequency"},
            "telepathy": {"character": "warm_emotional"},
        },
    },
    "El": {
        "frequency": "yellow",
        "registers": {
            "light":    {"color": "yellow",  "wavelength_nm": 570},
            "sound":    {"band": "mid",      "hz_approx": 500},
            "heat":     {"character": "ambient_warmth"},
            "smell":    {"character": "sharp_citrus_alert"},
            "haptic":   {"character": "mid_frequency"},
            "telepathy": {"character": "alert_cognitive"},
        },
    },
    "Ki": {
        "frequency": "green",
        "registers": {
            "light":    {"color": "green",   "wavelength_nm": 530},
            "sound":    {"band": "upper_mid","hz_approx": 1000},
            "heat":     {"character": "neutral_temperate"},
            "smell":    {"character": "fresh_living_green"},
            "haptic":   {"character": "upper_mid_frequency"},
            "telepathy": {"character": "relational_empathic"},
        },
    },
    "Fu": {
        "frequency": "blue",
        "registers": {
            "light":    {"color": "blue",    "wavelength_nm": 470},
            "sound":    {"band": "high_mid", "hz_approx": 2000},
            "heat":     {"character": "cool"},
            "smell":    {"character": "water_clean_open"},
            "haptic":   {"character": "high_mid_frequency"},
            "telepathy": {"character": "clear_spatial"},
        },
    },
    "Ka": {
        "frequency": "indigo",
        "registers": {
            "light":    {"color": "indigo",  "wavelength_nm": 430},
            "sound":    {"band": "high",     "hz_approx": 4000},
            "heat":     {"character": "cold"},
            "smell":    {"character": "deep_resinous_still"},
            "haptic":   {"character": "high_frequency"},
            "telepathy": {"character": "deep_still_knowing"},
        },
    },
    "AE": {
        "frequency": "highest",
        "registers": {
            "light":    {"color": "violet",  "wavelength_nm": 400},
            "sound":    {"band": "ultra_high_presence", "hz_approx": 8000},
            "heat":     {"character": "radiative_cold"},
            "smell":    {"character": "ethereal_barely_there"},
            "haptic":   {"character": "ultra_high_edge"},
            "telepathy": {"character": "transcendent_peripheral"},
        },
    },
    "Ha": {
        "frequency": "absolute_positive",
        "registers": {
            "light":    {"color": "white_maximum"},
            "sound":    {"band": "full_spectrum_maximum"},
            "heat":     {"character": "maximum_all_registers"},
            "smell":    {"character": "maximum_olfactory_saturation"},
            "haptic":   {"character": "maximum_all_frequencies"},
            "telepathy": {"character": "absolute_presence"},
        },
    },
    "Ga": {
        "frequency": "absolute_negative",
        "registers": {
            "light":    {"color": "subtractive_darkness"},
            "sound":    {"band": "subtractive_silence"},
            "heat":     {"character": "subtractive_cold"},
            "smell":    {"character": "subtractive_absence"},
            "haptic":   {"character": "subtractive_void"},
            "telepathy": {"character": "absolute_absence"},
        },
    },
}

ROSE_VECTOR_SYMBOLS = frozenset(ROSE_VECTORS.keys())

ROSE_DIGIT_VALUE: Dict[str, int] = {
    "Gaoh": 0, "Ao": 1, "Ye": 2, "Ui": 3,
    "Shu": 4, "Kiel": 5, "Yeshu": 6, "Lao": 7,
    "Shushy": 8, "Uinshu": 9, "Kokiel": 10, "Aonkiel": 11,
}
ROSE_NUMERAL_SYMBOLS = frozenset(ROSE_DIGIT_VALUE.keys())

DEFAULT_AMPLITUDE = 6  # Yeshu — midpoint

# Elemental carriers → sensory registers
ELEMENTAL_REGISTER: Dict[str, str] = {
    "Shak": "light",
    "Puf":  "sound",
    "Mel":  "telepathy",
    "Zot":  "haptics",
}

ELEMENTAL_SYMBOLS = frozenset(ELEMENTAL_REGISTER.keys())

# Kael — structural generative excess marker
KAEL_SYMBOL = "Kael"


# ---------------------------------------------------------------------------
# Chromatic data types
# ---------------------------------------------------------------------------

@dataclass
class VectorAmplitude:
    """A single frequency band at a specific amplitude."""
    vector:    str          # Rose vector symbol (Ru, Ot, El, Ki, Fu, Ka, AE, Ha, Ga)
    amplitude: int          # 0–11, or -1 for Ga (subtractive), 12 for Ha (absolute)
    is_primary: bool = True # leftmost vector in Akinenwun = primary frequency
    is_subtractive: bool = False  # Ga = subtractive


@dataclass
class ChromaticChord:
    """
    A voiced chord of frequency-amplitude pairs from a single Akinenwun.
    The leftmost vector is primary; subsequent vectors are modifiers.
    """
    vectors:         List[VectorAmplitude]
    primary_register: Optional[str]    # "light"|"sound"|"telepathy"|"haptics"
    kael_active:     bool = False       # generative excess — all registers saturate
    raw:             str = ""           # original Akinenwun string


@dataclass
class ChromaticProfile:
    """
    Full spectral profile extracted from a Wunashako.
    Each sensory register gets its own voiced chord list.
    """
    chords:          List[ChromaticChord]
    primary_register: Optional[str]
    register_profiles: Dict[str, List[VectorAmplitude]]  # per-register amplitude map
    kael_active:     bool = False
    cannabis_entries: List[str] = field(default_factory=list)
    is_ambiguous:    bool = False    # FrontierOpen — chromatic Cannabis entries
    raw_tokens:      List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Segmentation helpers
# ---------------------------------------------------------------------------

def _segment_token(raw: str) -> List[Any]:
    """Segment a raw token string into AkinenDescriptors."""
    descriptors, _ = sublayer_segment(raw)
    return descriptors


def _extract_chord_from_akinenwun(raw: str) -> Optional[ChromaticChord]:
    """
    Extract a ChromaticChord from a raw Akinenwun token string.

    Parses numeral-vector pairs and bare vectors from the descriptor list.
    Returns None if no vectors are present.

    Parsing logic:
    - Scan descriptors left to right
    - If a Rose numeral is immediately followed by a Rose vector,
      they form an amplitude-vector pair
    - A bare Rose vector (not preceded by a numeral) gets DEFAULT_AMPLITUDE
    - Ha and Ga are always absolute, no numeral prefix needed
    - Elemental symbols (Shak, Puf, Mel, Zot) set the primary register
    - Kael sets kael_active
    """
    descriptors = _segment_token(raw)
    vectors: List[VectorAmplitude] = []
    primary_register: Optional[str] = None
    kael_active = False
    is_primary = True

    i = 0
    while i < len(descriptors):
        d = descriptors[i]
        sym = d.symbol

        if sym == KAEL_SYMBOL:
            kael_active = True
            i += 1
            continue

        if sym in ELEMENTAL_SYMBOLS:
            primary_register = ELEMENTAL_REGISTER[sym]
            i += 1
            continue

        # Numeral followed by vector
        if sym in ROSE_NUMERAL_SYMBOLS:
            amplitude = ROSE_DIGIT_VALUE[sym]
            if i + 1 < len(descriptors) and descriptors[i+1].symbol in ROSE_VECTOR_SYMBOLS:
                vec_sym = descriptors[i+1].symbol
                vectors.append(VectorAmplitude(
                    vector=vec_sym,
                    amplitude=amplitude,
                    is_primary=is_primary,
                    is_subtractive=(vec_sym == "Ga"),
                ))
                is_primary = False
                i += 2
                continue

        # Bare vector (Ha, Ga, or colour vector without numeral prefix)
        if sym in ROSE_VECTOR_SYMBOLS:
            amplitude = 12 if sym == "Ha" else -1 if sym == "Ga" else DEFAULT_AMPLITUDE
            vectors.append(VectorAmplitude(
                vector=sym,
                amplitude=amplitude,
                is_primary=is_primary,
                is_subtractive=(sym == "Ga"),
            ))
            is_primary = False
            i += 1
            continue

        i += 1

    if not vectors and not kael_active:
        return None

    return ChromaticChord(
        vectors=vectors,
        primary_register=primary_register,
        kael_active=kael_active,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Per-register profile builder
# ---------------------------------------------------------------------------

def _build_register_profiles(
    chords: List[ChromaticChord],
    primary_register: Optional[str],
) -> Dict[str, List[VectorAmplitude]]:
    """
    Build per-register amplitude maps from a list of chords.
    All seven frequency bands initialised to 0; present vectors set their amplitude.
    """
    registers = ["light", "sound", "telepathy", "haptics"]
    profiles: Dict[str, List[VectorAmplitude]] = {}

    for reg in registers:
        band: Dict[str, VectorAmplitude] = {}
        for chord in chords:
            if chord.kael_active:
                for vec_sym in ["Ru", "Ot", "El", "Ki", "Fu", "Ka", "AE"]:
                    band[vec_sym] = VectorAmplitude(
                        vector=vec_sym, amplitude=11, is_primary=False
                    )
            chord_reg = chord.primary_register or primary_register
            if chord_reg == reg or chord_reg is None:
                for va in chord.vectors:
                    if va.vector not in band or va.is_primary:
                        band[va.vector] = va
        profiles[reg] = list(band.values())

    return profiles


# ---------------------------------------------------------------------------
# Cannabis detection in chromatic context
# ---------------------------------------------------------------------------

def _extract_cannabis_from_descriptors(descriptors: List[Any]) -> List[str]:
    """Return Cannabis akinen symbols from a descriptor list."""
    return [d.symbol for d in descriptors if d.tongue == "Cannabis"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract_chromatic_profile(wunashako_tokens: List[str]) -> ChromaticProfile:
    """
    Extract a ChromaticProfile from a list of raw Wunashako token strings.

    Each token is segmented via the sublayer. Rose numeral-vector pairs
    are extracted as amplitude-frequency specifications. The elemental
    carrier token determines the primary sensory register.

    Parameters
    ----------
    wunashako_tokens : list of raw token strings from a Wunashako
                       e.g. ["KielRu", "AoEl", "AonkielKi", "TaShakWu"]
    """
    chords: List[ChromaticChord] = []
    primary_register: Optional[str] = None
    kael_active = False
    cannabis_entries: List[str] = []
    is_ambiguous = False

    for raw in wunashako_tokens:
        descriptors = _segment_token(raw)

        # Check for Cannabis entries — chromatic ambiguity
        cannabis = _extract_cannabis_from_descriptors(descriptors)
        if cannabis:
            cannabis_entries.extend(cannabis)
            is_ambiguous = True

        # Check for elemental carrier (sets primary register)
        for d in descriptors:
            if d.symbol in ELEMENTAL_SYMBOLS:
                primary_register = ELEMENTAL_REGISTER[d.symbol]
                break

        # Extract chord
        chord = _extract_chord_from_akinenwun(raw)
        if chord:
            if chord.kael_active:
                kael_active = True
            if chord.primary_register and not primary_register:
                primary_register = chord.primary_register
            chords.append(chord)

    register_profiles = _build_register_profiles(chords, primary_register)

    return ChromaticProfile(
        chords=chords,
        primary_register=primary_register,
        register_profiles=register_profiles,
        kael_active=kael_active,
        cannabis_entries=cannabis_entries,
        is_ambiguous=is_ambiguous,
        raw_tokens=wunashako_tokens,
    )


def chromatic_profile_to_dict(profile: ChromaticProfile) -> Dict[str, Any]:
    """
    Serialise a ChromaticProfile to a plain dict for renderer consumption.
    Format compatible with entities_to_voxels extension.
    """
    def va_to_dict(va: VectorAmplitude) -> Dict[str, Any]:
        return {
            "vector":        va.vector,
            "amplitude":     va.amplitude,
            "is_primary":    va.is_primary,
            "is_subtractive": va.is_subtractive,
            "register_data": ROSE_VECTORS.get(va.vector, {}).get("registers", {}),
        }

    return {
        "primary_register": profile.primary_register,
        "kael_active":      profile.kael_active,
        "is_ambiguous":     profile.is_ambiguous,
        "cannabis_entries": profile.cannabis_entries,
        "chords": [
            {
                "raw":             chord.raw,
                "primary_register": chord.primary_register,
                "kael_active":     chord.kael_active,
                "vectors":         [va_to_dict(va) for va in chord.vectors],
            }
            for chord in profile.chords
        ],
        "register_profiles": {
            reg: [va_to_dict(va) for va in vas]
            for reg, vas in profile.register_profiles.items()
        },
    }


def amplitude_to_normalized(amplitude: int) -> float:
    """
    Normalise a base-12 amplitude value to 0.0–1.0 float.
    Gaoh (0) → 0.0, Aonkiel (11) → ~0.917, Ha (12) → 1.0, Ga (-1) → -1.0.
    """
    if amplitude == 12:
        return 1.0
    if amplitude == -1:
        return -1.0
    return round(amplitude / 11.0, 4)


def build_renderer_chromatic_packet(profile: ChromaticProfile) -> Dict[str, Any]:
    """
    Build a renderer-ready chromatic packet from a ChromaticProfile.
    Maps each sensory register to normalised amplitude values per frequency band.
    Consumed by the ModernGL bridge.
    """
    packet: Dict[str, Any] = {
        "primary_register": profile.primary_register,
        "kael_active":      profile.kael_active,
        "is_ambiguous":     profile.is_ambiguous,
    }

    vector_order = ["Ru", "Ot", "El", "Ki", "Fu", "Ka", "AE"]
    registers = ["light", "sound", "telepathy", "haptics"]

    for reg in registers:
        band = {v: 0.0 for v in vector_order}
        if profile.kael_active:
            band = {v: 1.0 for v in vector_order}
        else:
            for va in profile.register_profiles.get(reg, []):
                if va.vector in band:
                    band[va.vector] = amplitude_to_normalized(va.amplitude)
        packet[reg] = band

    return packet

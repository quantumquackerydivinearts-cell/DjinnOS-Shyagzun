"""
shygazun/kernel/kobra/sublayer.py
=================================
Sub-layer: segments a raw Akinenwun token string into its constituent
AkinenDescriptor records by matching against the Shygazun byte table.

Segmentation algorithm: greedy longest-match left-to-right.
At each position the longest known symbol wins; unmatched characters
accumulate into a remainder string.

A clean segmentation (empty remainder) returns the descriptor tuple.
Any remainder means the Akinenwun contains unknown material and the
caller should produce an Echo.

──────────────────────────────────────────────────────────────────────
Type rules (hard)
──────────────────────────────────────────────────────────────────────
  Akinen     — one byte-table symbol.  Atomic.  ``Shak``, ``Ti``, ``Ao``.
  Akinenwun  — two or more akinen concatenated WITHOUT whitespace.
               A single akinen is NOT an Akinenwun.
               ``ShakTi``, ``AoKiel``, ``KielAonkiel`` are Akinenwun.

──────────────────────────────────────────────────────────────────────
Rose numeral system — base-12 positional encoding
──────────────────────────────────────────────────────────────────────
The Rose tongue (Tongue 2) provides the digit set for coordinates,
dimensions, and any integer value in a Kobra scene expression.

  Gaoh=0  Ao=1  Ye=2  Ui=3  Shu=4  Kiel=5  Yeshu=6
  Lao=7   Shushy=8  Uinshu=9  Kokiel=10  Aonkiel=11

Positional, most-significant first:
  Single digit (0–11)    → one akinen          e.g. Kiel = 5
  Two digits  (12–143)   → Akinenwun (2 akinen) e.g. AoKiel = 17
  Three digits (144–1727)→ Akinenwun (3 akinen) e.g. YeUiShu = 328
  N digits               → Akinenwun (N akinen)

The coordinate space has no ceiling — the world is genuinely open.
Variable-length Akinenwun grow with the world:
  4 digits → 0–20,735      (covers 4K screen resolution)
  5 digits → 0–248,831
  6 digits → 0–2,985,983
  8 digits → 0–429,981,695  (serious overworld at pixel resolution)

The length of a Rose Akinenwun directly encodes order of magnitude:
a 2-akinen coordinate is always ≥12; a single-akinen coordinate is
always 0–11.  No metadata required to read the scale.

Evaluation of a Rose numeral sequence [d₀ d₁ … dₙ]:
  value = d₀×12ⁿ + d₁×12ⁿ⁻¹ + … + dₙ×12⁰
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..constants.byte_table import SHYGAZUN_SYMBOL_INDEX
from .types import AkinenDescriptor

# ---------------------------------------------------------------------------
# Tongue → canonical 1-based number (content tongues only; Reserved excluded)
# ---------------------------------------------------------------------------

_CONTENT_TONGUE_ORDER: Tuple[str, ...] = (
    "Lotus", "Rose", "Sakura", "Daisy", "AppleBlossom",
    "Aster", "Grapevine", "Cannabis",
    "Dragon", "Virus", "Bacteria", "Excavata", "Archaeplastida", "Myxozoa", "Archaea", "Protist",
    "Immune", "Neural", "Serpent", "Beast", "Cherub", "Chimera", "Faerie", "Djinn",
    "Fold", "Topology", "Phase", "Gradient", "Curvature", "Prion", "Blood", "Moon",
)

_TONGUE_NUMBER: Dict[str, int] = {t: i for i, t in enumerate(_CONTENT_TONGUE_ORDER, 1)}


# ---------------------------------------------------------------------------
# Symbol lookup: sorted by length descending for greedy matching
# ---------------------------------------------------------------------------

# All known symbols, longest first.  Built once at import time.
_ALL_SYMBOLS: Tuple[str, ...] = tuple(
    sorted(SHYGAZUN_SYMBOL_INDEX.keys(), key=len, reverse=True)
)


# ---------------------------------------------------------------------------
# Phonological analysis helpers
# ---------------------------------------------------------------------------

# Terminal vowel character → AppleBlossom ontic vowel label
_VOWEL_MAP: Dict[str, str] = {
    "a": "A",  # Mind +
    "o": "O",  # Mind −
    "i": "I",  # Space +
    "e": "E",  # Space −
    "y": "Y",  # Time +
    "u": "U",  # Time −
}

# The six ontic-vowel symbols are themselves one-character AppleBlossom entries.
# We handle them as a special case: pure vowel, no consonant form.
_ONTIC_VOWEL_SYMBOLS = frozenset({"A", "O", "I", "E", "Y", "U"})


def _cv_confidence(tongue_number: int) -> float:
    """
    Confidence that the CV analysis is correct for an akinen from this tongue.

    Tongues 1-3 have strict, simple CV structure → 1.0.
    Progressively more contextual above.
    """
    if tongue_number <= 3:
        return 1.0
    if tongue_number <= 8:
        return 0.8
    if tongue_number <= 16:
        return 0.6
    if tongue_number <= 24:
        return 0.4
    return 0.2


def _analyse_cv(
    symbol: str,
    tongue_number: int,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (ontic_vowel, consonant_form) for a symbol.

    For pure AppleBlossom vowel symbols (A/O/I/E/Y/U): vowel is the symbol
    itself, consonant_form is None.

    For other symbols: scan right-to-left for the last lowercase vowel
    character and split there.  Returns (None, None) if no vowel is found
    (rare; occurs in some compound consonant-cluster symbols).
    """
    if symbol in _ONTIC_VOWEL_SYMBOLS:
        return symbol, None

    # Scan right-to-left for the last recognisable vowel
    for idx in range(len(symbol) - 1, -1, -1):
        ch = symbol[idx].lower()
        if ch in _VOWEL_MAP:
            ontic_vowel = _VOWEL_MAP[ch]
            # consonant_form is everything that is NOT the vowel position
            # Use the portion before + after, omitting just that vowel char
            consonant_form = symbol[:idx] + symbol[idx + 1:] or None
            return ontic_vowel, consonant_form

    return None, symbol  # all-consonant cluster (unusual)


# ---------------------------------------------------------------------------
# Core segmentation
# ---------------------------------------------------------------------------

def segment(raw: str) -> Tuple[Tuple[AkinenDescriptor, ...], str]:
    """
    Segment a raw Akinenwun token string into AkinenDescriptors.

    Returns ``(descriptors, remainder)``.

    ``remainder`` is the substring that could not be matched to any known
    symbol.  An empty remainder means full segmentation succeeded.
    A non-empty remainder means the caller should produce an Echo.

    The token is matched case-sensitively; the byte table symbols are
    mixed-case by design (e.g. ``Mel``, ``Shak``, ``AE``).
    """
    descriptors: List[AkinenDescriptor] = []
    unmatched_chars: List[str] = []
    pos = 0

    while pos < len(raw):
        matched = False
        # Try all symbols longest-first (greedy)
        for sym in _ALL_SYMBOLS:
            sym_len = len(sym)
            if raw[pos:pos + sym_len] == sym:
                # Matched — look up entry
                entries = SHYGAZUN_SYMBOL_INDEX[sym]
                # Use the first entry (most symbols are unambiguous;
                # declensional duplicates are handled at a higher layer)
                entry = entries[0]
                tongue = entry["tongue"]
                tongue_num = _TONGUE_NUMBER.get(tongue, 0)
                ontic_vowel, consonant_form = _analyse_cv(sym, tongue_num)
                descriptors.append(
                    AkinenDescriptor(
                        symbol=sym,
                        decimal=entry["decimal"],
                        tongue=tongue,
                        tongue_number=tongue_num,
                        meaning=entry["meaning"],
                        ontic_vowel=ontic_vowel,
                        consonant_form=consonant_form,
                        cv_confidence=_cv_confidence(tongue_num),
                    )
                )
                pos += sym_len
                matched = True
                break

        if not matched:
            # No symbol matches here; record the character as unmatched
            unmatched_chars.append(raw[pos])
            pos += 1

    return tuple(descriptors), "".join(unmatched_chars)
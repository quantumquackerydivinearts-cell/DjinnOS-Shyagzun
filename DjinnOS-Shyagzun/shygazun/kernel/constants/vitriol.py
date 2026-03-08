"""
VITRIOL governance order is intentional and invariant.
DO NOT REORDER.
This is the reverse of the canonical sin listing.

This module is a kernel invariant: it exists to prevent drift in any
hashing / deterministic assembly that depends on VITRIOL ordering.

Editing this file requires:
- version bump consideration
- regression test updates when intentional
"""

from __future__ import annotations

from typing import Dict, Final, Tuple

VITRIOL_GOVERNANCE_ORDER: Final[Tuple[str, ...]] = (
    "Asmodeus",  # Vitality
    "Satan",  # Introspection
    "Beelzebub",  # Tactility
    "Belphegor",  # Reflectivity
    "Leviathan",  # Ingenuity
    "Mammon",  # Ostentation
    "Lucifer",  # Levity
)

VITRIOL_LETTERS: Final[Tuple[str, ...]] = (
    "Vitality",
    "Introspection",
    "Tactility",
    "Reflectivity",
    "Ingenuity",
    "Ostentation",
    "Levity",
)

# Lock mapping explicitly (no dynamic generation elsewhere).
VITRIOL_MAPPING: Final[Dict[str, str]] = {
    "Vitality": "Asmodeus",
    "Introspection": "Satan",
    "Tactility": "Beelzebub",
    "Reflectivity": "Belphegor",
    "Ingenuity": "Leviathan",
    "Ostentation": "Mammon",
    "Levity": "Lucifer",
}

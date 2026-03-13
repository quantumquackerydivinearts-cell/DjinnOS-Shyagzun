from __future__ import annotations

from typing import List, Mapping, Sequence

from shygazun.kernel.constants.vitriol import VITRIOL_LETTERS


def assemble_vitriol_vector(metrics: Mapping[str, float]) -> List[float]:
    """
    Assemble a deterministic VITRIOL vector.

    Invariant:
    - Iteration order is defined ONLY by VITRIOL_LETTERS.
    - Demon order is governance metadata; letter order defines hash ordering.

    Raises:
    - KeyError if any required letter is missing.
    """
    return [float(metrics[letter]) for letter in VITRIOL_LETTERS]


def vitriol_letters() -> Sequence[str]:
    """
    Convenience for tooling that needs the canonical letter order.
    Returns a stable ordered sequence.
    """
    return VITRIOL_LETTERS

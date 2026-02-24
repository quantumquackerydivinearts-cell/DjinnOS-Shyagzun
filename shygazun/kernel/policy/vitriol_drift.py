from __future__ import annotations

import hashlib
from decimal import Decimal, localcontext
from typing import Dict, Mapping, Sequence, TypeAlias

from shygazun.kernel.constants.vitriol import VITRIOL_LETTERS
from shygazun.kernel.types.events import KernelEventObj


VitriolVector: TypeAlias = Dict[str, Decimal]

DRIFT_CONSTANT_C: Decimal = Decimal("7")
DRIFT_PRECISION: Decimal = Decimal("0.000000000001")


def fractal_step(x: Decimal, c: Decimal = DRIFT_CONSTANT_C) -> Decimal:
    """
    Deterministic non-linear transform.

    Precision is fixed to avoid cross-machine float drift.
    """
    with localcontext() as ctx:
        ctx.prec = 28
        y = (x * x) + c
    return y.quantize(DRIFT_PRECISION)


def compute_vitriol_vector(events: Sequence[KernelEventObj]) -> VitriolVector:
    """
    Replay-only VITRIOL drift.

    Rules:
    - placement events advance Azoth index (placement order only).
    - attestation/collapse events apply deterministic, explicit deltas.
    - no hidden mutable state is used.
    """
    vector: VitriolVector = {letter: Decimal("0") for letter in VITRIOL_LETTERS}
    azoth_index = 0

    for event in events:
        kind = str(event.get("kind", ""))
        if kind == "placement":
            azoth_index += 1
            letter = VITRIOL_LETTERS[(azoth_index - 1) % len(VITRIOL_LETTERS)]
            vector[letter] = fractal_step(vector[letter], DRIFT_CONSTANT_C)
            continue

        if kind == "attestation":
            # Structural-only influence from explicit attestation fact.
            seed = _attestation_seed(event)
            letter = _letter_from_seed(seed)
            vector[letter] = fractal_step(vector[letter], DRIFT_CONSTANT_C)
            continue

        if kind == "collapse":
            # Structural-only influence from explicit collapse fact.
            seed = _collapse_seed(event)
            letter = _letter_from_seed(seed)
            vector[letter] = fractal_step(vector[letter], DRIFT_CONSTANT_C)

    return vector


def vitriol_vector_strings(vector: Mapping[str, Decimal]) -> Dict[str, str]:
    """
    Stable string form for hashing / manifests.
    """
    return {letter: format(vector[letter], "f") for letter in VITRIOL_LETTERS}


def _letter_from_seed(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(VITRIOL_LETTERS)
    return VITRIOL_LETTERS[index]


def _attestation_seed(event: Mapping[str, object]) -> str:
    target_obj = event.get("target")
    if isinstance(target_obj, Mapping):
        frontier_id_obj = target_obj.get("frontier_id")
        candidate_id_obj = target_obj.get("candidate_id")
        frontier_id = str(frontier_id_obj) if frontier_id_obj is not None else ""
        candidate_id = str(candidate_id_obj) if candidate_id_obj is not None else ""
    else:
        frontier_id = ""
        candidate_id = ""

    witness_obj = event.get("witness_id")
    witness_id = str(witness_obj) if witness_obj is not None else ""
    return "|".join(("attestation", frontier_id, candidate_id, witness_id))


def _collapse_seed(event: Mapping[str, object]) -> str:
    frontier_obj = event.get("frontier_id")
    frontier_id = str(frontier_obj) if frontier_obj is not None else ""
    return "|".join(("collapse", frontier_id))

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Dict, Mapping, Optional, Sequence, Tuple, TypeAlias

from shygazun.kernel.constants.vitriol import VITRIOL_LETTERS
from shygazun.kernel.types.events import KernelEventObj


VitriolVector: TypeAlias = Dict[str, Decimal]

DEFAULT_SCHEMA_VERSION = "0.1.1"
DEFAULT_C = Decimal("7")
DEFAULT_QUANTIZE_DP = 12


@dataclass(frozen=True)
class VitriolSnapshot:
    schema_version: str
    c: str
    quantize_dp: int
    azoth_index: int
    anchor_event_id: str
    anchor_hash: str
    vector: Dict[str, str]

    def to_json_obj(self) -> Dict[str, object]:
        return {
            "vitriol_snapshot": {
                "schema_version": self.schema_version,
                "c": self.c,
                "quantize_dp": self.quantize_dp,
                "azoth_index": self.azoth_index,
                "anchor_event_id": self.anchor_event_id,
                "anchor_hash": self.anchor_hash,
                "vector": dict(self.vector),
            }
        }

    @classmethod
    def from_json_obj(cls, obj: Mapping[str, object]) -> Optional["VitriolSnapshot"]:
        inner_obj = obj.get("vitriol_snapshot")
        if not isinstance(inner_obj, Mapping):
            return None

        schema_version = inner_obj.get("schema_version")
        c = inner_obj.get("c")
        quantize_dp = inner_obj.get("quantize_dp")
        azoth_index = inner_obj.get("azoth_index")
        anchor_event_id = inner_obj.get("anchor_event_id")
        anchor_hash = inner_obj.get("anchor_hash")
        vector_obj = inner_obj.get("vector")

        if not isinstance(schema_version, str):
            return None
        if not isinstance(c, str):
            return None
        if not isinstance(quantize_dp, int):
            return None
        if not isinstance(azoth_index, int):
            return None
        if not isinstance(anchor_event_id, str):
            return None
        if not isinstance(anchor_hash, str):
            return None
        if not isinstance(vector_obj, Mapping):
            return None

        vector: Dict[str, str] = {}
        for letter in VITRIOL_LETTERS:
            val = vector_obj.get(letter)
            if not isinstance(val, str):
                return None
            vector[letter] = val

        return cls(
            schema_version=schema_version,
            c=c,
            quantize_dp=quantize_dp,
            azoth_index=azoth_index,
            anchor_event_id=anchor_event_id,
            anchor_hash=anchor_hash,
            vector=vector,
        )


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def quantize_decimal(x: Decimal, dp: int) -> Decimal:
    quantum = Decimal(1).scaleb(-dp)
    return x.quantize(quantum)


def fractal_step(x: Decimal, c: Decimal, dp: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 28
        y = (x * x) + c
    return quantize_decimal(y, dp)


def compute_from_events(
    events: Sequence[KernelEventObj],
    start_index: int,
    vector: VitriolVector,
    azoth_index: int,
    c: Decimal,
    dp: int,
) -> Tuple[VitriolVector, int, str]:
    updated: VitriolVector = dict(vector)
    current_azoth = azoth_index
    last_event_id = ""

    for event in events[start_index:]:
        event_id = _event_id(event)
        kind = _event_kind(event)
        if kind == "placement":
            current_azoth += 1
            for letter in VITRIOL_LETTERS:
                updated[letter] = fractal_step(updated[letter], c, dp)
        elif kind == "commitment":
            _apply_commitment_delta(updated, event, dp)
        elif kind == "collapse":
            _apply_collapse_delta(updated, event, dp)
        last_event_id = event_id

    return updated, current_azoth, last_event_id


def make_snapshot(
    vector: Mapping[str, Decimal],
    azoth_index: int,
    anchor_event_id: str,
    c: Decimal,
    dp: int,
    *,
    schema_version: str = DEFAULT_SCHEMA_VERSION,
) -> VitriolSnapshot:
    anchor_hash = sha256_hex(canonical_json(anchor_event_id))
    vector_str: Dict[str, str] = {}
    for letter in VITRIOL_LETTERS:
        val = quantize_decimal(vector[letter], dp)
        vector_str[letter] = format(val, "f")

    return VitriolSnapshot(
        schema_version=schema_version,
        c=format(c, "f"),
        quantize_dp=dp,
        azoth_index=azoth_index,
        anchor_event_id=anchor_event_id,
        anchor_hash=anchor_hash,
        vector=vector_str,
    )


def verify_snapshot(snapshot: VitriolSnapshot, events: Sequence[KernelEventObj]) -> bool:
    anchor_index = _find_anchor_index(events, snapshot.anchor_event_id)
    if anchor_index is None:
        return False
    expected_hash = sha256_hex(canonical_json(snapshot.anchor_event_id))
    return expected_hash == snapshot.anchor_hash


def load_or_recompute(
    snapshot_opt: Optional[VitriolSnapshot],
    events: Sequence[KernelEventObj],
) -> Tuple[VitriolVector, int, int]:
    if snapshot_opt is None:
        return _zero_vector(), 0, 0
    if snapshot_opt.schema_version != DEFAULT_SCHEMA_VERSION:
        return _zero_vector(), 0, 0
    if not verify_snapshot(snapshot_opt, events):
        return _zero_vector(), 0, 0

    anchor_index = _find_anchor_index(events, snapshot_opt.anchor_event_id)
    if anchor_index is None:
        return _zero_vector(), 0, 0

    restored_vector: VitriolVector = {}
    for letter in VITRIOL_LETTERS:
        restored_vector[letter] = Decimal(snapshot_opt.vector[letter])
    return restored_vector, snapshot_opt.azoth_index, anchor_index + 1


def _event_kind(event: KernelEventObj) -> str:
    kind_obj = event.get("kind")
    return str(kind_obj) if kind_obj is not None else ""


def _event_id(event: KernelEventObj) -> str:
    id_obj = event.get("id")
    return str(id_obj) if id_obj is not None else ""


def _find_anchor_index(events: Sequence[KernelEventObj], anchor_event_id: str) -> Optional[int]:
    for idx, event in enumerate(events):
        if _event_id(event) == anchor_event_id:
            return idx
    return None


def _zero_vector() -> VitriolVector:
    return {letter: Decimal("0") for letter in VITRIOL_LETTERS}


def _apply_commitment_delta(vector: VitriolVector, event: KernelEventObj, dp: int) -> None:
    # Hook retained for deterministic structural deltas.
    _ = (vector, event, dp)


def _apply_collapse_delta(vector: VitriolVector, event: KernelEventObj, dp: int) -> None:
    # Hook retained for deterministic structural deltas.
    _ = (vector, event, dp)

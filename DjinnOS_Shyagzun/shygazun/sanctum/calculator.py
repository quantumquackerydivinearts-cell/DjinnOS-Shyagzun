"""
shygazun.sanctum.calculator — Semantic Arithmetic Engine
=========================================================

A base-12 dimensional calculator grounded in the Shygazun byte table.

DESIGN AXIOMS:
- The Rose counting spine (decimals 31–42) provides the twelve scalar values.
  Gaoh (31) = 0/12 — the Möbius zero point.
  Aonkiel (42) = 11.
  All arithmetic results are Möbius-wrapped mod 12.

- Spectral operators (24–30) and Primordial operators (43–47) are dimensional
  operators, not scalar values, even though they live in the Rose tongue.

- ALL other tongue entries (Lotus, Sakura, Daisy, AppleBlossom, Aster,
  Grapevine, Cannabis) are dimensional operators.  Their meaning IS the
  operation type.  Do not invent operation logic — record the operator
  applied and let the compound meaning speak for itself.

- This module does not invent Shygazun meanings.  The byte table is the spec.
- Reserved bytes 124–127 are never touched.
- Cannabis operators project a coordinate — they do not alter the scalar.
- coil_distance is imported from Layers.py.  Not reimplemented here.
- All state-returning functions are pure (return new instances, never mutate).
"""

from __future__ import annotations

import sys
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Final

# ---------------------------------------------------------------------------
# Path bootstrap — work regardless of CWD
# ---------------------------------------------------------------------------

_THIS_DIR  = os.path.dirname(__file__)
_SANCTUM   = _THIS_DIR
_SHYGAZUN  = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))

for _p in [_SHYGAZUN]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_ROWS, ShygazunByteEntry  # noqa: E402
from shygazun.sanctum.Layers import coil_distance                                       # noqa: E402

# ---------------------------------------------------------------------------
# Derived tongue ranges from the byte table at module load time.
# NEVER use magic integers for tongue membership — derive from SHYGAZUN_BYTE_ROWS.
# ---------------------------------------------------------------------------

def _rows_for_tongue(tongue: str) -> list[ShygazunByteEntry]:
    return [r for r in SHYGAZUN_BYTE_ROWS if r["tongue"] == tongue]

def _rows_for_tongues(*tongues: str) -> list[ShygazunByteEntry]:
    return [r for r in SHYGAZUN_BYTE_ROWS if r["tongue"] in tongues]


# Rose spine: counting values Gaoh (0/12) through Aonkiel (11)
# The task spec gives decimals 31–42.  We derive this from the byte table.
_ROSE_ALL: Final[list[ShygazunByteEntry]] = _rows_for_tongue("Rose")

_SPINE_ROWS: Final[list[ShygazunByteEntry]] = [
    r for r in _ROSE_ALL
    if r["meaning"].startswith("Number ")
]
# Maps spine decimal → Möbius value 0–11
# Gaoh is "Number 12 / 0" → value 0.  Ao is "Number 1" → value 1. Etc.
def _spine_value(row: ShygazunByteEntry) -> int:
    meaning = row["meaning"]
    if "12 / 0" in meaning or "12/0" in meaning:
        return 0
    for token in meaning.split():
        try:
            return int(token)
        except ValueError:
            continue
    return 0

_SPINE_BY_DECIMAL: Final[dict[int, ShygazunByteEntry]] = {r["decimal"]: r for r in _SPINE_ROWS}
_SPINE_BY_VALUE:   Final[dict[int, ShygazunByteEntry]] = {_spine_value(r): r for r in _SPINE_ROWS}

# Primordial operators (Rose, Ha/Ga/Wu/Na/Ung — decimals 43–47)
_PRIMORDIAL_SYMBOLS: Final[frozenset[str]] = frozenset({"Ha", "Ga", "Wu", "Na", "Ung"})
_PRIMORDIAL_ROWS: Final[list[ShygazunByteEntry]] = [r for r in _ROSE_ALL if r["symbol"] in _PRIMORDIAL_SYMBOLS]
_PRIMORDIAL_BY_SYMBOL: Final[dict[str, ShygazunByteEntry]] = {r["symbol"]: r for r in _PRIMORDIAL_ROWS}

# Spectral operators (Rose, Ru–AE — frequency/color axis)
_SPECTRAL_ROWS: Final[list[ShygazunByteEntry]] = [
    r for r in _ROSE_ALL
    if r["symbol"] not in _PRIMORDIAL_SYMBOLS
    and r["symbol"] != "Gaoh"
    and r["decimal"] not in _SPINE_BY_DECIMAL
]

# Dimensional operator rows: every row that is NOT on the spine
# Includes: Rose spectral, Rose Primordials, all other tongues
# Excludes: reserved bytes 124–127
_DIM_ROWS: Final[list[ShygazunByteEntry]] = [
    r for r in SHYGAZUN_BYTE_ROWS
    if r["decimal"] not in _SPINE_BY_DECIMAL
    and not (124 <= r["decimal"] <= 127)
]
_DIM_BY_DECIMAL: Final[dict[int, ShygazunByteEntry]] = {r["decimal"]: r for r in _DIM_ROWS}

# All tongue entry lists, keyed by tongue name, used for dimensional projection
_TONGUE_ROWS: Final[dict[str, list[ShygazunByteEntry]]] = {}
for _r in SHYGAZUN_BYTE_ROWS:
    _TONGUE_ROWS.setdefault(_r["tongue"], []).append(_r)

# Gaoh constant (used for Gaoh-fold operation and as reference for value 0)
_GAOH_ROW: Final[ShygazunByteEntry] = _SPINE_BY_VALUE[0]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpineValue:
    """A scalar value on the Rose counting spine (0–11, Möbius-wrapped)."""
    decimal: int    # byte table address (31–42)
    symbol:  str    # e.g. "Gaoh", "Ao", "Ye"
    value:   int    # Möbius value 0–11

    @classmethod
    def from_decimal(cls, decimal: int) -> "SpineValue":
        row = _SPINE_BY_DECIMAL[decimal]
        return cls(decimal=decimal, symbol=row["symbol"], value=_spine_value(row))

    @classmethod
    def from_value(cls, value: int) -> "SpineValue":
        """Construct from a Möbius-wrapped integer 0–11."""
        v = value % 12
        row = _SPINE_BY_VALUE[v]
        return cls(decimal=row["decimal"], symbol=row["symbol"], value=v)

    @classmethod
    def zero(cls) -> "SpineValue":
        return cls.from_value(0)


@dataclass(frozen=True)
class DimOperator:
    """
    A dimensional operator — any byte table entry outside the counting spine.

    Its meaning IS the operation type.  Projection records where the scalar
    lands in this tongue's address space without altering the scalar.
    """
    decimal: int    # byte table address
    tongue:  str
    symbol:  str
    meaning: str

    @classmethod
    def from_decimal(cls, decimal: int) -> "DimOperator":
        if decimal in (124, 125, 126, 127):
            raise ValueError(f"Byte {decimal} is reserved — cannot be used as operator.")
        row = _DIM_BY_DECIMAL[decimal]
        return cls(
            decimal=row["decimal"],
            tongue=row["tongue"],
            symbol=row["symbol"],
            meaning=row["meaning"],
        )


@dataclass(frozen=True)
class ProjectedAxis:
    """
    The result of projecting a scalar value onto a single dimensional operator.

    projected_entry is the byte table row the scalar maps to within the operator's tongue.
    The scalar itself is unchanged — this is a coordinate, not a transformation.
    """
    operator:         DimOperator
    projected_decimal: int          # decimal of the projected entry in that tongue
    projected_symbol:  str
    projected_meaning: str

    @classmethod
    def project(cls, operator: DimOperator, value: int) -> "ProjectedAxis":
        tongue_rows = _TONGUE_ROWS.get(operator.tongue, [])
        if not tongue_rows:
            # Tongue has no entries (should not happen with a valid operator)
            return cls(
                operator=operator,
                projected_decimal=operator.decimal,
                projected_symbol=operator.symbol,
                projected_meaning=operator.meaning,
            )
        idx = value % len(tongue_rows)
        entry = tongue_rows[idx]
        return cls(
            operator=operator,
            projected_decimal=entry["decimal"],
            projected_symbol=entry["symbol"],
            projected_meaning=entry["meaning"],
        )


@dataclass(frozen=True)
class CompoundAddress:
    """
    A spine value with zero or more active dimensional operators.

    The compound is the spine value's position named and described
    through each active axis.
    """
    spine: SpineValue
    dims:  tuple[DimOperator, ...]   # application order

    def to_shygazun_string(self) -> str:
        """spine symbol + each dim symbol concatenated."""
        parts = [self.spine.symbol] + [d.symbol for d in self.dims]
        return "".join(parts)

    def to_codepoints(self) -> list[int]:
        """Unicode PUA codepoints: U+E000 + decimal for spine and each dim."""
        decimals = [self.spine.decimal] + [d.decimal for d in self.dims]
        return [0xE000 + dec for dec in decimals]

    def projections(self) -> tuple[ProjectedAxis, ...]:
        """Compute projected coordinate for each active dim operator."""
        return tuple(ProjectedAxis.project(op, self.spine.value) for op in self.dims)

    @classmethod
    def bare(cls, spine: SpineValue) -> "CompoundAddress":
        return cls(spine=spine, dims=())


# ---------------------------------------------------------------------------
# Calculator state
# ---------------------------------------------------------------------------

#: Arithmetic operations keyed by Primordial symbol.
#: The meaning of each operation is in the symbol itself — we do not rename them.
OPERATIONS: Final[frozenset[str]] = frozenset({"Ha", "Ga", "Wu", "Na", "Ung", "Gaoh"})


@dataclass(frozen=True)
class CalculatorState:
    """
    Immutable calculator state.  All mutation functions return a new instance.

    pending_op / pending_value: the left side of an in-progress binary operation.
    expr: human-readable expression string (Latin symbols from byte table).
    vocab: named compound registers, in insertion order.
    """
    current:       CompoundAddress
    pending_op:    str | None                           = None
    pending_value: SpineValue | None                   = None
    expr:          str                                  = ""
    vocab:         tuple[tuple[str, CompoundAddress], ...] = ()


# ---------------------------------------------------------------------------
# Pure state-transition functions
# ---------------------------------------------------------------------------

def make_calculator() -> CalculatorState:
    """Return a fresh calculator state at Gaoh (0)."""
    return CalculatorState(current=CompoundAddress.bare(SpineValue.zero()))


def enter_value(state: CalculatorState, decimal: int) -> CalculatorState:
    """
    Enter a spine value by its decimal address.

    Replaces the current spine value, preserving active dim operators.
    """
    sv = SpineValue.from_decimal(decimal)
    new_compound = CompoundAddress(spine=sv, dims=state.current.dims)
    expr = f"{state.expr}{sv.symbol}" if state.expr else sv.symbol
    return CalculatorState(
        current=new_compound,
        pending_op=state.pending_op,
        pending_value=state.pending_value,
        expr=expr,
        vocab=state.vocab,
    )


def toggle_dim(state: CalculatorState, decimal: int) -> CalculatorState:
    """
    Toggle a dimensional operator on/off.

    If the operator is already active, remove it.  Otherwise append it.
    Preserves the current spine value.
    """
    op = DimOperator.from_decimal(decimal)
    existing = state.current.dims
    if any(d.decimal == decimal for d in existing):
        new_dims = tuple(d for d in existing if d.decimal != decimal)
    else:
        new_dims = existing + (op,)
    new_compound = CompoundAddress(spine=state.current.spine, dims=new_dims)
    return CalculatorState(
        current=new_compound,
        pending_op=state.pending_op,
        pending_value=state.pending_value,
        expr=state.expr,
        vocab=state.vocab,
    )


def set_op(state: CalculatorState, op_symbol: str) -> CalculatorState:
    """
    Set the pending arithmetic operation.

    Stores the current spine value as the left operand.
    op_symbol must be one of: Ha, Ga, Wu, Na, Ung, Gaoh
    """
    if op_symbol not in OPERATIONS:
        raise ValueError(f"Unknown operation '{op_symbol}'. Valid: {sorted(OPERATIONS)}")
    expr = f"{state.expr} {op_symbol} "
    return CalculatorState(
        current=state.current,
        pending_op=op_symbol,
        pending_value=state.current.spine,
        expr=expr,
        vocab=state.vocab,
    )


def execute(state: CalculatorState) -> CalculatorState:
    """
    Execute the pending operation with the current spine value as the right operand.

    All results are Möbius-wrapped mod 12.

    Operations:
        Ha  (+)   assertion / addition:           (a + b) % 12
        Ga  (−)   negation / subtraction:         (a - b) % 12
        Wu  (×)   transformation / multiplication:(a * b) % 12
        Na  (÷)   integration / division:         (a // b) % 12  (zero divisor → 0)
        Ung (⟲)   traversal:                       coil_distance(a+1, b+1)
                  coil layers are 1-indexed; spine values 0–11 map to layers 1–12
        Gaoh(◉)   Möbius fold:                    (a + b) % 12  (same as Ha —
                  explicitly names the Möbius pair operation)

    If no pending operation is set, returns state unchanged.
    Preserves active dim operators on the result.
    """
    if state.pending_op is None or state.pending_value is None:
        return state

    a = state.pending_value.value
    b = state.current.spine.value
    op = state.pending_op

    if op == "Ha":
        result = (a + b) % 12
    elif op == "Ga":
        result = (a - b) % 12
    elif op == "Wu":
        result = (a * b) % 12
    elif op == "Na":
        result = (a // b) % 12 if b != 0 else 0
    elif op == "Ung":
        # Spine values 0–11 map to coil layers 1–12
        # Gaoh (value 0) = layer 12 (the Möbius zero point IS layer 12 via wrap)
        layer_a = a if a != 0 else 12
        layer_b = b if b != 0 else 12
        result = coil_distance(layer_a, layer_b)
    elif op == "Gaoh":
        result = (a + b) % 12
    else:
        result = b  # unreachable given set_op validation

    result_spine   = SpineValue.from_value(result)
    result_compound = CompoundAddress(spine=result_spine, dims=state.current.dims)
    expr = f"{state.expr}{state.current.spine.symbol} = {result_spine.symbol}"

    return CalculatorState(
        current=result_compound,
        pending_op=None,
        pending_value=None,
        expr=expr,
        vocab=state.vocab,
    )


def save_to_vocab(state: CalculatorState, name: str) -> CalculatorState:
    """
    Save the current compound address under a given name.

    Replaces any existing entry with the same name.
    """
    # Remove existing entry with this name if present
    filtered = tuple((n, c) for n, c in state.vocab if n != name)
    new_vocab = filtered + ((name, state.current),)
    return CalculatorState(
        current=state.current,
        pending_op=state.pending_op,
        pending_value=state.pending_value,
        expr=state.expr,
        vocab=new_vocab,
    )


def recall_vocab(state: CalculatorState, name: str) -> CalculatorState:
    """
    Recall a named compound from the vocabulary register.

    Sets current to the recalled compound.  Clears pending op/value.
    Raises KeyError if name not found.
    """
    for n, compound in state.vocab:
        if n == name:
            return CalculatorState(
                current=compound,
                pending_op=None,
                pending_value=None,
                expr=compound.to_shygazun_string(),
                vocab=state.vocab,
            )
    raise KeyError(f"No vocabulary entry named '{name}'.")


def resolve_compound(state: CalculatorState) -> CompoundAddress:
    """
    Return the fully resolved current CompoundAddress.

    Includes projections (computed lazily via .projections()).
    """
    return state.current


# ---------------------------------------------------------------------------
# Convenience: enumerate entries for the keyboard UI
# ---------------------------------------------------------------------------

def spine_entries() -> list[ShygazunByteEntry]:
    """Return spine rows in coil order (Gaoh=0 first, Aonkiel=11 last)."""
    return sorted(_SPINE_ROWS, key=_spine_value)


def spectral_entries() -> list[ShygazunByteEntry]:
    """Return Rose spectral entries (Ru through AE) in address order."""
    return sorted(_SPECTRAL_ROWS, key=lambda r: r["decimal"])


def primordial_entries() -> list[ShygazunByteEntry]:
    """Return Rose Primordial entries (Ha, Ga, Wu, Na, Ung) in address order."""
    return sorted(_PRIMORDIAL_ROWS, key=lambda r: r["decimal"])


def tongue_entries(tongue: str) -> list[ShygazunByteEntry]:
    """Return all byte table entries for a given tongue, in address order.
    Excludes reserved bytes 124–127."""
    rows = [
        r for r in _TONGUE_ROWS.get(tongue, [])
        if not (124 <= r["decimal"] <= 127)
    ]
    return sorted(rows, key=lambda r: r["decimal"])


def all_tongues() -> list[str]:
    """Return tongue names in canonical address-space order."""
    seen: list[str] = []
    for r in SHYGAZUN_BYTE_ROWS:
        t = r["tongue"]
        if t not in seen:
            seen.append(t)
    return seen

"""
shygazun/kernel/kobra/types.py
==============================
Core AST and execution types for Kobra — Shygazun's programming substrate.

Hierarchy (three levels):
  Akinen        — single byte-table symbol, atomic sub-unit.
                  Processed by the sub-layer; not a parser primitive.
                  A single akinen is NOT an Akinenwun.
  Akinenwun     — TWO OR MORE akinen concatenated without whitespace.
                  Positional syntax operates within it.
                  The atomic compositional unit for the parser.
  Wunashako     — [token token ...] where each token is either an akinen
                  or an Akinenwun, whitespace-delimited. Tongue-order is
                  the primary axis; positional sequence is secondary
                  (Latin principle). The fundamental grammatical unit.

At the AST level:
  AkinenNode    — a whitespace-delimited token containing exactly one akinen.
  AkinenwunNode — a whitespace-delimited token containing two or more akinen.
  Wunashako.tokens holds a sequence of either.

Surface delimiters:
  []   — individual Wunashako
  {}   — group: holds Wunashako and sub-expressions together
  ()   — operand: data operated on by the immediately preceding expression
  ;    — sequential separation between statements
  :    — sub-structure introduction (header : body)

Execution states (per operative-ambiguity model):
  Resolved     — single meaning, execution proceeds
  Echo         — hard parse failure; input carried forward as live object
  FrontierOpen — ambiguous; both candidates execute in parallel until attested
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Sub-layer output — per-akinen phonological descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AkinenDescriptor:
    """
    Phonological and ontological descriptor for a single akinen symbol.

    Produced by the sub-layer; carried inside AkinenNode or AkinenwunNode
    for the parser and downstream consumers.
    """
    symbol:        str          # exact symbol string from the byte table
    decimal:       int          # byte address
    tongue:        str          # tongue name (e.g. "Lotus", "Serpent")
    tongue_number: int          # 1-based tongue sequence position
    meaning:       str          # full meaning string from the byte table

    # Phonological analysis fields
    # Most operative in Tongues 1–3; progressively contextual above.
    ontic_vowel:    Optional[str]   # A/O/I/E/Y/U if identifiable; None otherwise
    consonant_form: Optional[str]   # remaining consonant cluster; None for pure vowels
    cv_confidence:  float           # 0.0–1.0; 1.0 = Tongues 1–3 strict, lower above


# ---------------------------------------------------------------------------
# AST token node types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AkinenNode:
    """
    A single akinen appearing as a whitespace-delimited token in Kobra source.

    A single akinen is NOT an Akinenwun.  When the sub-layer segments a
    source token and finds exactly one akinen, this node type is produced.

    E.g. the token ``Shak`` yields one AkinenDescriptor → AkinenNode.
    """
    raw:        str              # original token string
    descriptor: AkinenDescriptor # the one akinen

    @property
    def tongue(self) -> str:
        return self.descriptor.tongue


@dataclass(frozen=True)
class AkinenwunNode:
    """
    An Akinenwun: two or more akinen concatenated as a single
    whitespace-delimited token.

    ``len(akinen) >= 2`` always.  A token that segments to exactly one
    akinen is an AkinenNode, not an AkinenwunNode.

    E.g. the token ``ShakMelZot`` yields three AkinenDescriptors →
    AkinenwunNode with akinen=(Shak, Mel, Zot).

    ``tongue_span`` lists the unique tongue names present, in encounter
    order.  Multi-tongue Akinenwun are how tongue-order relationships are
    encoded within a single compound token.

    If segmentation is ambiguous, the parser produces a FrontierOpen
    with two AkinenwunNode candidates rather than one.
    """
    raw:         str                          # original token string
    akinen:      Tuple[AkinenDescriptor, ...] # len >= 2
    tongue_span: Tuple[str, ...]              # unique tongue names, ordered


# Convenience union — a token in a Wunashako is one or the other
KobraToken = Union[AkinenNode, AkinenwunNode]


# ---------------------------------------------------------------------------
# AST node types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Wunashako:
    """
    A single chord: ``[token token ...]``.

    Each token is either an AkinenNode (one akinen) or an AkinenwunNode
    (two or more akinen).  Tokens are stored in the order they appear in
    source (tongue-order primary, positional sequence secondary — the
    Latin principle).

    ``tongue_order`` lists unique tongue names across all tokens, ordered
    by first encounter.

    ``deliberate`` is True when any token contains a Cannabis Tongue
    akinen, signalling deliberate operative ambiguity.
    """
    tokens:      Tuple[KobraToken, ...]
    tongue_order: Tuple[str, ...]
    deliberate:  bool = False


@dataclass(frozen=True)
class WunashakoGroup:
    """
    A group of Wunashako and sub-expressions: ``{ ... }``.

    Holds items together as a coherent unit; items are separated by ``;``.
    """
    items: Tuple["Expr", ...]


@dataclass(frozen=True)
class Application:
    """
    Operand applied to operator: ``expr(expr)``.

    The ``operator`` is the expression immediately preceding ``()``.
    The ``operand`` is the expression inside ``()``.

    Declaration and dictation are inseparable in Kobra: an Application
    is simultaneously an ontological claim about the data and an operative
    instruction over it.
    """
    operator: "Expr"
    operand:  "Expr"


@dataclass(frozen=True)
class SubStructure:
    """
    Header introducing a body: ``expr : expr``.

    The ``:`` signals that ``body`` is a sub-structure depending on ``header``.
    """
    header: "Expr"
    body:   "Expr"


@dataclass(frozen=True)
class KobraSequence:
    """
    Sequential composition: ``expr ; expr ; ...``.

    Items execute in sequence. Each item is a full expression.
    """
    items: Tuple["Expr", ...]


# Expr is the union of all expression-level AST nodes
Expr = Union[
    Wunashako,
    WunashakoGroup,
    Application,
    SubStructure,
    KobraSequence,
]


# ---------------------------------------------------------------------------
# Execution states
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Resolved:
    """
    Fully resolved expression: single operative meaning, execution proceeds.

    ``source`` is the original source text span that produced this result.
    """
    expr:   Expr
    source: str


@dataclass(frozen=True)
class Echo:
    """
    Hard parse failure. Input is carried forward as a live object.

    Per the operative-ambiguity model: an Echo is not deleted. It floats
    in the Field as an unresolved placement until a Steward attests its
    meaning or the dictionary is extended to cover it.
    """
    raw:          str
    context:      str
    failure_type: str   # "hard_failure" | "unknown_token" | "context_missing"


@dataclass(frozen=True)
class FrontierOpen:
    """
    Ambiguous expression: both candidates execute in parallel until attested.

    ``deliberate`` distinguishes intentional Cannabis Tongue ambiguity
    (a standing operative instrument) from accidental parse ambiguity
    (which pauses and requests a witness immediately).

    ``witness`` is None until an attestation fills the slot.
    """
    candidate_a: Expr
    candidate_b: Expr
    source:      str
    deliberate:  bool = False
    witness:     Optional[Any] = field(default=None, compare=False)


ParseResult = Union[Resolved, Echo, FrontierOpen]
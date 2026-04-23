"""
shygazun/kernel/kobra/samosmyr.py
==================================
SamosMyr parser — extends the core Kobra parser to handle the full
SamosMyr notation.

Surface grammar
---------------
  samosmyr     ::= identity_header ':' coherence_header '{' body '}'
  identity_header ::= WORD                      e.g. LoShun
  coherence_header ::= WORD '(' condition ')'   e.g. Shakshi(TaLaShaN)
  condition    ::= token*                        e.g. TaLaShaN
  body         ::= entity_spec* temporal_closure
  entity_spec  ::= '[' token* ']'
  temporal_closure ::= '[' WORD '(' address ')' ']'
  address      ::= WORD                          e.g. AonkielYeShu

SamosMyr fields
---------------
  identity          — LoShun positional index
  coherence_char    — Shakshi operative header
  interior_condition — TaLaShaN interior condition tokens
  entity_specs      — list of parsed Wunashakoe
  temporal_closure  — TaShyMa operator
  temporal_address  — Rose numeral address in seconds (base-12)
  temporal_seconds  — evaluated integer seconds
  relevance_decls   — topological relevance declarations found in entity specs
  cannabis_entries  — all Cannabis akinen across all entity specs
  parse_state       — Resolved | FrontierOpen | Echo
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .sublayer import segment as sublayer_segment
from .types import (
    AkinenDescriptor,
    AkinenNode,
    AkinenwunNode,
    Echo,
    FrontierOpen,
    KobraToken,
    Resolved,
    Wunashako,
)
from .topology import (
    RelevanceDeclaration,
    parse_relevance_declaration,
    FOLD_SUBTYPES,
    TOPOLOGY_CONNECTORS,
    PHASE_TRANSITIONS,
    GRADIENT_ENTRIES,
    CURVATURE_ENTRIES,
)

# ---------------------------------------------------------------------------
# Rose numeral evaluation (base-12)
# ---------------------------------------------------------------------------

_ROSE_DIGIT_VALUE: Dict[str, int] = {
    "Gaoh": 0, "Ao": 1, "Ye": 2, "Ui": 3,
    "Shu": 4, "Kiel": 5, "Yeshu": 6, "Lao": 7,
    "Shushy": 8, "Uinshu": 9, "Kokiel": 10, "Aonkiel": 11,
}

_ROSE_NUMERAL_SYMBOLS = frozenset(_ROSE_DIGIT_VALUE.keys())

_CANNABIS_TONGUE = "Cannabis"
_TOPOLOGICAL_TONGUES = frozenset(["Fold", "Topology", "Phase", "Gradient", "Curvature"])

_ALL_TOPO_SYMBOLS = frozenset(
    list(FOLD_SUBTYPES.keys()) +
    list(TOPOLOGY_CONNECTORS.keys()) +
    list(PHASE_TRANSITIONS.keys()) +
    list(GRADIENT_ENTRIES.keys()) +
    list(CURVATURE_ENTRIES.keys())
)


def _eval_base12(symbols: List[str]) -> int:
    """Evaluate a list of Rose numeral symbol strings as a base-12 integer."""
    result = 0
    for s in symbols:
        result = result * 12 + _ROSE_DIGIT_VALUE.get(s, 0)
    return result


def _extract_rose_numerals_from_raw(raw: str) -> List[str]:
    """
    Extract Rose numeral symbols from a raw token string via sublayer
    segmentation. Returns list of numeral symbol strings in order.
    """
    descriptors, _ = sublayer_segment(raw)
    return [d.symbol for d in descriptors if d.symbol in _ROSE_NUMERAL_SYMBOLS]


def eval_temporal_address(raw: str) -> int:
    """
    Evaluate a raw temporal address token (e.g. 'AonkielYeShu') to seconds.
    Segments via the sublayer and evaluates Rose numerals in base-12.
    """
    numerals = _extract_rose_numerals_from_raw(raw)
    return _eval_base12(numerals)


def seconds_to_clock(seconds: int) -> str:
    """Convert integer seconds to mm:ss display string."""
    return f"{seconds // 60}:{seconds % 60:02d}"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _make_token(word: str) -> KobraToken:
    """Build AkinenNode or AkinenwunNode from a raw word."""
    descriptors, _ = sublayer_segment(word)
    if len(descriptors) == 1:
        return AkinenNode(raw=word, descriptor=descriptors[0])
    tongue_span = tuple(dict.fromkeys(d.tongue for d in descriptors).keys())
    return AkinenwunNode(raw=word, akinen=tuple(descriptors), tongue_span=tongue_span)


def _token_tongue_names(tok: KobraToken) -> Tuple[str, ...]:
    if isinstance(tok, AkinenNode):
        return (tok.descriptor.tongue,)
    return tok.tongue_span


def _is_deliberate(tokens: List[KobraToken]) -> bool:
    for tok in tokens:
        if isinstance(tok, AkinenNode):
            if tok.descriptor.tongue == _CANNABIS_TONGUE:
                return True
        else:
            if any(d.tongue == _CANNABIS_TONGUE for d in tok.akinen):
                return True
    return False


def _cannabis_entries(tokens: List[KobraToken]) -> List[str]:
    """Return list of Cannabis akinen symbol strings in token list."""
    entries = []
    for tok in tokens:
        if isinstance(tok, AkinenNode):
            if tok.descriptor.tongue == _CANNABIS_TONGUE:
                entries.append(tok.descriptor.symbol)
        else:
            for d in tok.akinen:
                if d.tongue == _CANNABIS_TONGUE:
                    entries.append(d.symbol)
    return entries


def _topological_symbols(tokens: List[KobraToken]) -> List[str]:
    """Return list of topological tongue symbol strings in token list."""
    found = []
    for tok in tokens:
        if isinstance(tok, AkinenNode):
            if tok.descriptor.symbol in _ALL_TOPO_SYMBOLS:
                found.append(tok.descriptor.symbol)
        else:
            for d in tok.akinen:
                if d.symbol in _ALL_TOPO_SYMBOLS:
                    found.append(d.symbol)
    return found


# ---------------------------------------------------------------------------
# Wunashako builder
# ---------------------------------------------------------------------------

def _build_wunashako(words: List[str]) -> Wunashako:
    """Build a Wunashako from a list of raw word strings."""
    tokens = [_make_token(w) for w in words]
    deliberate = _is_deliberate(tokens)
    tongue_order_dict: Dict[str, None] = {}
    for tok in tokens:
        for t in _token_tongue_names(tok):
            tongue_order_dict[t] = None
    return Wunashako(
        tokens=tuple(tokens),
        tongue_order=tuple(tongue_order_dict.keys()),
        deliberate=deliberate,
    )


# ---------------------------------------------------------------------------
# SamosMyr data types
# ---------------------------------------------------------------------------

@dataclass
class EntitySpec:
    """
    A single entity specification within a SamosMyr body.
    Wraps a parsed Wunashako with extracted metadata.
    """
    wunashako:        Wunashako
    raw_words:        List[str]
    cannabis_entries: List[str]
    topo_symbols:     List[str]
    relevance_decls:  List[RelevanceDeclaration]
    index:            int


@dataclass
class TemporalClosure:
    """
    The TaShyMa temporal closure expression at the end of a SamosMyr body.
    """
    operator_raw:    str          # e.g. "TaShyMa"
    address_raw:     str          # e.g. "AonkielYeShu"
    seconds:         int          # evaluated base-12 seconds
    clock:           str          # mm:ss display
    operator_tokens: List[KobraToken]


@dataclass
class SamosMyr:
    """
    A fully parsed SamosMyr — a gathering-procession coherence field.

    identity_raw        — raw LoShun token string
    identity_index      — positional index (Shun = 4 = cartesian point, etc.)
    coherence_header    — Shakshi operative header token string
    interior_condition  — TaLaShaN condition words
    entity_specs        — ordered list of EntitySpec
    temporal_closure    — TaShyMa expression
    all_cannabis        — all Cannabis entries across all entity specs
    all_topo_symbols    — all topological tongue symbols across all specs
    all_relevance_decls — all RelevanceDeclaration objects
    deliberate          — True if any entity spec carries Cannabis entries
    parse_state         — "Resolved" | "FrontierOpen" | "Echo"
    errors              — list of error strings if parse_state is Echo
    source              — original source string
    """
    identity_raw:        str
    identity_index:      int
    coherence_header:    str
    interior_condition:  List[str]
    entity_specs:        List[EntitySpec]
    temporal_closure:    Optional[TemporalClosure]
    all_cannabis:        List[str]
    all_topo_symbols:    List[str]
    all_relevance_decls: List[RelevanceDeclaration]
    deliberate:          bool
    parse_state:         str
    errors:              List[str]
    source:              str


# ---------------------------------------------------------------------------
# Tokeniser (reuses core logic, adds SamosMyr-aware state)
# ---------------------------------------------------------------------------

_DELIMITERS = frozenset("[]{}();:")


def _tokenise(source: str) -> List[Dict[str, str]]:
    """Tokenise source into kind/value dicts."""
    tokens = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch in _DELIMITERS:
            tokens.append({"kind": ch, "value": ch})
            i += 1
            continue
        j = i
        while j < n and source[j] not in " \t\r\n" and source[j] not in _DELIMITERS:
            j += 1
        tokens.append({"kind": "WORD", "value": source[i:j]})
        i = j
    tokens.append({"kind": "EOF", "value": ""})
    return tokens


class _Stream:
    def __init__(self, tokens: List[Dict[str, str]]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> Dict[str, str]:
        return self._tokens[self._pos]

    def consume(self) -> Dict[str, str]:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def at(self, *kinds: str) -> bool:
        return self._tokens[self._pos]["kind"] in kinds

    def at_end(self) -> bool:
        return self._tokens[self._pos]["kind"] == "EOF"

    def expect(self, kind: str) -> Dict[str, str]:
        tok = self.consume()
        if tok["kind"] != kind:
            raise _ParseError(
                f"expected '{kind}' got '{tok['kind']}' ({tok['value']!r})"
            )
        return tok


class _ParseError(Exception):
    pass


# ---------------------------------------------------------------------------
# SamosMyr parser
# ---------------------------------------------------------------------------

def _parse_identity_header(stream: _Stream) -> Tuple[str, int]:
    """
    Parse identity header: WORD
    Returns (raw_string, positional_index).
    """
    tok = stream.expect("WORD")
    raw = tok["value"]
    descriptors, _ = sublayer_segment(raw)
    numerals = [d.symbol for d in descriptors if d.symbol in _ROSE_NUMERAL_SYMBOLS]
    index = _eval_base12(numerals) if numerals else 0
    return raw, index


def _parse_coherence_header(stream: _Stream) -> Tuple[str, List[str]]:
    """
    Parse coherence header: WORD '(' condition ')'
    Returns (header_raw, condition_words).
    """
    tok = stream.expect("WORD")
    header_raw = tok["value"]
    stream.expect("(")
    condition_words = []
    while not stream.at(")") and not stream.at_end():
        w = stream.consume()
        if w["kind"] == "WORD":
            condition_words.append(w["value"])
    stream.expect(")")
    return header_raw, condition_words


def _parse_entity_spec(stream: _Stream, index: int) -> EntitySpec:
    """
    Parse a single entity spec: '[' token* ']'
    """
    stream.expect("[")
    words = []
    while not stream.at("]") and not stream.at_end():
        tok = stream.consume()
        if tok["kind"] == "WORD":
            words.append(tok["value"])
    stream.expect("]")

    wunashako = _build_wunashako(words)
    tokens_list = list(wunashako.tokens)
    cannabis = _cannabis_entries(tokens_list)
    topo = _topological_symbols(tokens_list)

    relevance_decls = []
    for sym in topo:
        decl = parse_relevance_declaration(
            token=sym,
            source=cannabis[0] if cannabis else "unknown",
            target="pending",
        )
        if decl:
            relevance_decls.append(decl)

    return EntitySpec(
        wunashako=wunashako,
        raw_words=words,
        cannabis_entries=cannabis,
        topo_symbols=topo,
        relevance_decls=relevance_decls,
        index=index,
    )


def _parse_temporal_closure(stream: _Stream) -> TemporalClosure:
    """
    Parse temporal closure: '[' WORD '(' WORD ')' ']'
    e.g. [TaShyMa(AonkielYeShu)]
    """
    stream.expect("[")
    operator_tok = stream.expect("WORD")
    operator_raw = operator_tok["value"]
    stream.expect("(")
    address_tok = stream.expect("WORD")
    address_raw = address_tok["value"]
    stream.expect(")")
    stream.expect("]")

    seconds = eval_temporal_address(address_raw)
    operator_tokens = [_make_token(operator_raw)]

    return TemporalClosure(
        operator_raw=operator_raw,
        address_raw=address_raw,
        seconds=seconds,
        clock=seconds_to_clock(seconds),
        operator_tokens=operator_tokens,
    )


def _looks_like_temporal_closure(stream: _Stream) -> bool:
    """
    Peek ahead to determine if the next [...] is a temporal closure
    (contains a WORD followed by '(') rather than an entity spec.
    """
    pos = stream._pos
    tokens = stream._tokens
    if tokens[pos]["kind"] != "[":
        return False
    i = pos + 1
    while i < len(tokens) and tokens[i]["kind"] == "WORD":
        i += 1
    return i < len(tokens) and tokens[i]["kind"] == "("


def _parse_body(stream: _Stream) -> Tuple[List[EntitySpec], Optional[TemporalClosure]]:
    """
    Parse SamosMyr body: entity_spec* temporal_closure
    Body is wrapped in '{' ... '}'
    """
    stream.expect("{")
    entity_specs = []
    temporal_closure = None
    spec_index = 0

    while not stream.at("}") and not stream.at_end():
        if stream.at("["):
            if _looks_like_temporal_closure(stream):
                temporal_closure = _parse_temporal_closure(stream)
            else:
                entity_specs.append(_parse_entity_spec(stream, spec_index))
                spec_index += 1
        else:
            stream.consume()

    stream.expect("}")
    return entity_specs, temporal_closure


def parse_samosmyr(source: str) -> SamosMyr:
    """
    Parse a SamosMyr source string.

    Expected form:
        LoShun: Shakshi(TaLaShaN) {
            [entity spec]
            ...
            [TaShyMa(AonkielYeShu)]
        }

    Returns a SamosMyr dataclass. parse_state is one of:
        "Resolved"     — clean parse, no Cannabis entries
        "FrontierOpen" — Cannabis entries present, witness slots open
        "Echo"         — parse failure
    """
    errors: List[str] = []

    try:
        tokens = _tokenise(source.strip())
        stream = _Stream(tokens)

        identity_raw, identity_index = _parse_identity_header(stream)
        stream.expect(":")
        coherence_header, interior_condition = _parse_coherence_header(stream)
        entity_specs, temporal_closure = _parse_body(stream)

        all_cannabis: List[str] = []
        all_topo: List[str] = []
        all_decls: List[RelevanceDeclaration] = []

        for spec in entity_specs:
            all_cannabis.extend(spec.cannabis_entries)
            all_topo.extend(spec.topo_symbols)
            all_decls.extend(spec.relevance_decls)

        deliberate = len(all_cannabis) > 0
        parse_state = "FrontierOpen" if deliberate else "Resolved"

        return SamosMyr(
            identity_raw=identity_raw,
            identity_index=identity_index,
            coherence_header=coherence_header,
            interior_condition=interior_condition,
            entity_specs=entity_specs,
            temporal_closure=temporal_closure,
            all_cannabis=all_cannabis,
            all_topo_symbols=all_topo,
            all_relevance_decls=all_decls,
            deliberate=deliberate,
            parse_state=parse_state,
            errors=errors,
            source=source,
        )

    except _ParseError as exc:
        errors.append(str(exc))
        return SamosMyr(
            identity_raw="",
            identity_index=0,
            coherence_header="",
            interior_condition=[],
            entity_specs=[],
            temporal_closure=None,
            all_cannabis=[],
            all_topo_symbols=[],
            all_relevance_decls=[],
            deliberate=False,
            parse_state="Echo",
            errors=errors,
            source=source,
        )

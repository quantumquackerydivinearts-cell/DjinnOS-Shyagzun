"""
shygazun/kernel/kobra/parser.py
================================
Kobra surface parser.

Surface grammar (precedence low → high):
  sequence    ::= expr (';' expr)*
  substructure::= expr (':' expr)?
  application ::= primary ('(' sequence ')')*
  primary     ::= wunashako | group | '(' sequence ')'
  wunashako   ::= '[' token* ']'
  group       ::= '{' sequence (';' sequence)* '}'
  token       ::= WORD   (akinen or Akinenwun — dispatched by sub-layer count)

Tokens
------
  WORD        — whitespace-delimited, not a delimiter character
  LBRACK / RBRACK — '[' / ']'
  LBRACE / RBRACE — '{' / '}'
  LPAREN / RPAREN — '(' / ')'
  SEMI        — ';'
  COLON       — ':'
  EOF

Execution states
----------------
  Resolved    — clean parse, single AST
  Echo        — hard failure; raw input carried forward as live object
  FrontierOpen— ambiguous (Cannabis Tongue deliberate or accidental)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .sublayer import segment as sublayer_segment
from .types import (
    AkinenNode,
    AkinenwunNode,
    Application,
    Echo,
    Expr,
    FrontierOpen,
    KobraSequence,
    KobraToken,
    ParseResult,
    Resolved,
    SubStructure,
    Wunashako,
    WunashakoGroup,
)

# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

_TK_LBRACK = "["
_TK_RBRACK = "]"
_TK_LBRACE = "{"
_TK_RBRACE = "}"
_TK_LPAREN = "("
_TK_RPAREN = ")"
_TK_SEMI   = ";"
_TK_COLON  = ":"
_TK_EOF    = "\x00EOF"

_SINGLE_CHAR_TOKENS = frozenset("[]{}();:")

# Cannabis Tongue tongue name — deliberate ambiguity marker
_CANNABIS_TONGUE = "Cannabis"


@dataclass
class _Token:
    kind: str   # one of the _TK_* constants, or "WORD"
    value: str  # raw text


def _tokenise(source: str) -> List[_Token]:
    """
    Split source into tokens, stripping insignificant whitespace.

    Single-character delimiter tokens are emitted directly.
    Everything else between delimiters/whitespace is a WORD token.
    """
    tokens: List[_Token] = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        if ch in " \t\r\n":
            i += 1
            continue

        if ch in _SINGLE_CHAR_TOKENS:
            tokens.append(_Token(kind=ch, value=ch))
            i += 1
            continue

        # Accumulate a WORD (everything up to whitespace or a delimiter)
        j = i
        while j < n and source[j] not in " \t\r\n" and source[j] not in _SINGLE_CHAR_TOKENS:
            j += 1
        tokens.append(_Token(kind="WORD", value=source[i:j]))
        i = j

    tokens.append(_Token(kind=_TK_EOF, value=""))
    return tokens


# ---------------------------------------------------------------------------
# Token stream helper
# ---------------------------------------------------------------------------

class _Stream:
    def __init__(self, tokens: List[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> _Token:
        return self._tokens[self._pos]

    def consume(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def consume_kind(self, kind: str) -> _Token:
        tok = self.consume()
        if tok.kind != kind:
            raise _ParseError(
                f"expected '{kind}', got '{tok.kind}' ({tok.value!r})"
            )
        return tok

    def at_end(self) -> bool:
        return self._tokens[self._pos].kind == _TK_EOF

    def at(self, *kinds: str) -> bool:
        return self._tokens[self._pos].kind in kinds


class _ParseError(Exception):
    pass


# ---------------------------------------------------------------------------
# Token construction — dispatch by sub-layer segmentation count
# ---------------------------------------------------------------------------

def _make_token(word: str) -> KobraToken:
    """
    Build an AkinenNode or AkinenwunNode from a whitespace-delimited word.

    Calls the sub-layer to segment the word into AkinenDescriptors.

    - Exactly one descriptor  → AkinenNode  (a single akinen; NOT an Akinenwun)
    - Two or more descriptors → AkinenwunNode (the Akinenwun proper)
    - Zero descriptors        → AkinenwunNode with empty tuple (unresolved;
                                the caller detects this via _token_has_unresolved)

    A non-empty remainder signals unrecognised material; the node is still
    constructed so the caller can produce an appropriate Echo.
    """
    descriptors, _remainder = sublayer_segment(word)

    if len(descriptors) == 1:
        return AkinenNode(
            raw=word,
            descriptor=descriptors[0],
        )

    # 0 descriptors (fully unrecognised) or 2+ descriptors → AkinenwunNode
    tongue_span = tuple(dict.fromkeys(d.tongue for d in descriptors).keys())
    return AkinenwunNode(
        raw=word,
        akinen=descriptors,
        tongue_span=tongue_span,
    )


def _token_has_unresolved(token: KobraToken) -> bool:
    """True if the sub-layer could not fully segment this token."""
    _, remainder = sublayer_segment(token.raw)
    return bool(remainder)


def _wunashako_is_deliberate(tokens: Sequence[KobraToken]) -> bool:
    """True if any token in the sequence contains a Cannabis Tongue akinen."""
    for tok in tokens:
        if isinstance(tok, AkinenNode):
            if tok.descriptor.tongue == _CANNABIS_TONGUE:
                return True
        else:  # AkinenwunNode
            if any(d.tongue == _CANNABIS_TONGUE for d in tok.akinen):
                return True
    return False


def _token_tongue_names(tok: KobraToken) -> Tuple[str, ...]:
    """Return the tongue name(s) present in a token, in encounter order."""
    if isinstance(tok, AkinenNode):
        return (tok.descriptor.tongue,)
    return tok.tongue_span  # already in encounter order


# ---------------------------------------------------------------------------
# Recursive descent parser
# ---------------------------------------------------------------------------

def _parse_sequence(stream: _Stream) -> Expr:
    """sequence ::= substructure (';' substructure)*"""
    items: List[Expr] = [_parse_substructure(stream)]
    while stream.at(_TK_SEMI):
        stream.consume()  # eat ';'
        if stream.at(_TK_EOF, _TK_RBRACE, _TK_RPAREN):
            break  # trailing semicolon is legal
        items.append(_parse_substructure(stream))
    if len(items) == 1:
        return items[0]
    return KobraSequence(items=tuple(items))


def _parse_substructure(stream: _Stream) -> Expr:
    """substructure ::= application (':' application)?"""
    head = _parse_application(stream)
    if stream.at(_TK_COLON):
        stream.consume()  # eat ':'
        body = _parse_application(stream)
        return SubStructure(header=head, body=body)
    return head


def _parse_application(stream: _Stream) -> Expr:
    """application ::= primary ('(' sequence ')')*"""
    expr = _parse_primary(stream)
    while stream.at(_TK_LPAREN):
        stream.consume()  # eat '('
        operand = _parse_sequence(stream)
        stream.consume_kind(_TK_RPAREN)
        expr = Application(operator=expr, operand=operand)
    return expr


def _parse_primary(stream: _Stream) -> Expr:
    """primary ::= wunashako | group | '(' sequence ')'"""
    tok = stream.peek()

    if tok.kind == _TK_LBRACK:
        return _parse_wunashako(stream)

    if tok.kind == _TK_LBRACE:
        return _parse_group(stream)

    if tok.kind == _TK_LPAREN:
        stream.consume()  # eat '('
        inner = _parse_sequence(stream)
        stream.consume_kind(_TK_RPAREN)
        return inner

    if tok.kind == "WORD":
        # Bare word outside brackets: treat as a single-token Wunashako.
        # Recovery path — canonical Kobra wraps tokens in [].
        stream.consume()
        node = _make_token(tok.value)
        deliberate = _wunashako_is_deliberate([node])
        tongue_order = _token_tongue_names(node)
        return Wunashako(
            tokens=(node,),
            tongue_order=tongue_order,
            deliberate=deliberate,
        )

    raise _ParseError(
        f"unexpected token '{tok.kind}' ({tok.value!r}) in primary position"
    )


def _parse_wunashako(stream: _Stream) -> Wunashako:
    """wunashako ::= '[' token* ']'"""
    stream.consume_kind(_TK_LBRACK)
    nodes: List[KobraToken] = []

    while not stream.at(_TK_RBRACK, _TK_EOF):
        tok = stream.consume()
        if tok.kind != "WORD":
            raise _ParseError(
                f"expected token inside [], got '{tok.kind}'"
            )
        nodes.append(_make_token(tok.value))

    stream.consume_kind(_TK_RBRACK)

    deliberate = _wunashako_is_deliberate(nodes)

    # tongue_order: unique tongue names across all tokens, in encounter order
    tongue_order_dict: dict[str, None] = {}
    for n in nodes:
        for t in _token_tongue_names(n):
            tongue_order_dict[t] = None

    return Wunashako(
        tokens=tuple(nodes),
        tongue_order=tuple(tongue_order_dict.keys()),
        deliberate=deliberate,
    )


def _parse_group(stream: _Stream) -> WunashakoGroup:
    """group ::= '{' sequence (';' sequence)* '}'"""
    stream.consume_kind(_TK_LBRACE)
    items: List[Expr] = []

    if not stream.at(_TK_RBRACE, _TK_EOF):
        items.append(_parse_sequence(stream))

    # Additional items separated by ';' are already consumed by _parse_sequence.
    # The group just collects whatever _parse_sequence left off at '}'.

    stream.consume_kind(_TK_RBRACE)
    return WunashakoGroup(items=tuple(items))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse(source: str) -> ParseResult:
    """
    Parse a Kobra source string and return a ParseResult.

    Returns
    -------
    Resolved
        Full parse succeeded with a single unambiguous AST.
    Echo
        Hard parse failure; ``raw`` carries the original source.
    FrontierOpen
        Ambiguous parse.  Currently only ``deliberate=True`` (Cannabis Tongue)
        ambiguity is detected; accidental structural ambiguity is left for
        future attestation instrumentation.
    """
    source_stripped = source.strip()
    if not source_stripped:
        return Echo(
            raw=source,
            context="empty input",
            failure_type="hard_failure",
        )

    try:
        tokens = _tokenise(source_stripped)
        stream = _Stream(tokens)
        expr = _parse_sequence(stream)

        if not stream.at_end():
            leftover = stream.peek().value
            return Echo(
                raw=source,
                context=f"unconsumed input starting at '{leftover}'",
                failure_type="hard_failure",
            )

        # Check for deliberate Cannabis Tongue ambiguity
        if _expr_is_deliberate(expr):
            return FrontierOpen(
                candidate_a=expr,
                candidate_b=expr,   # both branches identical until attested
                source=source_stripped,
                deliberate=True,
            )

        # Check for unknown sub-layer tokens
        if _expr_has_unknown(expr):
            return Echo(
                raw=source,
                context="one or more tokens contain unrecognised akinen",
                failure_type="unknown_token",
            )

        return Resolved(expr=expr, source=source_stripped)

    except _ParseError as exc:
        return Echo(
            raw=source,
            context=str(exc),
            failure_type="hard_failure",
        )


# ---------------------------------------------------------------------------
# AST inspection helpers (post-parse)
# ---------------------------------------------------------------------------

def _expr_is_deliberate(expr: Expr) -> bool:
    """Recursively check whether any Wunashako in the tree is deliberate."""
    if isinstance(expr, Wunashako):
        return expr.deliberate
    if isinstance(expr, WunashakoGroup):
        return any(_expr_is_deliberate(e) for e in expr.items)
    if isinstance(expr, Application):
        return _expr_is_deliberate(expr.operator) or _expr_is_deliberate(expr.operand)
    if isinstance(expr, SubStructure):
        return _expr_is_deliberate(expr.header) or _expr_is_deliberate(expr.body)
    if isinstance(expr, KobraSequence):
        return any(_expr_is_deliberate(e) for e in expr.items)
    return False


def _expr_has_unknown(expr: Expr) -> bool:
    """Recursively check whether any token failed sub-layer segmentation."""
    if isinstance(expr, Wunashako):
        return any(_token_has_unresolved(n) for n in expr.tokens)
    if isinstance(expr, WunashakoGroup):
        return any(_expr_has_unknown(e) for e in expr.items)
    if isinstance(expr, Application):
        return _expr_has_unknown(expr.operator) or _expr_has_unknown(expr.operand)
    if isinstance(expr, SubStructure):
        return _expr_has_unknown(expr.header) or _expr_has_unknown(expr.body)
    if isinstance(expr, KobraSequence):
        return any(_expr_has_unknown(e) for e in expr.items)
    return False
"""
shygazun/kernel/kobra/evaluator.py
===================================
Python host evaluator for Kobra .ko documents.

This is the external host that bootstraps the Mavo namespace and evaluates
Self-spec.ko progressively section by section.  When the native Kobra
evaluator is complete, this file is the scaffold that removes itself — the
spec runs under the same spec without modification.

Two-level architecture
----------------------
  Document level:  Seth: Type { Cluster: Type { Lo: Header(Cond) { specs } } }
                   Handled by a structural brace-matching reader.

  Expression level: [token token ...] and [TaShyMa(address)]
                    Handled at the raw-token level (Mavo-compound tokens are
                    opaque identifiers here; sub-layer resolution is not
                    required for bootstrapping).

Mavo namespace
--------------
Each entity spec [MavoX Y Z ...] registers MavoX → [Y, Z, ...] in the
namespace.  The first Mavo-prefixed token in a spec is the defined key;
remaining tokens are its definition.

TaShyMa
--------
[TaShyMa(address)] commits the current section's accumulated definitions
to the SoaArtifact at the given Rose numeral address.

Witness states (canonical per LoKiel of Self-spec)
--------------------------------------------------
  Zo     (0) — unwitnessed
  Shi    (1) — witnessed
  Ly     (2) — partial
  FyShy  (3) — committed / attested
  MuSoa  (4) — carried forward as Soa
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .samosmyr import (
    SamosMyrBoundary,
    SamosMyrFrame,
    SoaArtifact,
    UnresolvedEntry,
    open_frame,
    artifact_for_entry,
)


# ── Witness state constants (from LoKiel) ────────────────────────────────────

class WitnessState:
    UNWITNESSED = "Zo"
    WITNESSED   = "Shi"
    PARTIAL     = "Ly"
    COMMITTED   = "FyShy"
    SOA         = "MuSoa"


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class SectionResult:
    index:          str
    header:         str
    condition:      str
    definitions:    Dict[str, List[str]]
    ta_shy_ma:      Optional[str]
    witness_states: Dict[str, str]
    echoes:         List[str]


@dataclass
class ClusterResult:
    name:     str
    typ:      str
    sections: List[SectionResult]


@dataclass
class DocumentResult:
    seth_name: str
    seth_type: str
    clusters:  List[ClusterResult]
    namespace: Dict[str, Any]
    frame:     SamosMyrFrame


# ── Structural document reader ────────────────────────────────────────────────

def _close_brace(source: str, start: int) -> int:
    """Return index of the '}' matching the '{' at source[start].
    If no match is found, returns the last character index (lenient — file may be a work in progress)."""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(source) - 1


def _close_paren(source: str, start: int) -> int:
    """Return index of the ')' matching the '(' at source[start]."""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unmatched '(' at {start}")


def _close_bracket(source: str, start: int) -> int:
    """Return index of the ']' matching the '[' at source[start]."""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "[":
            depth += 1
        elif source[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unmatched '[' at {start}")


@dataclass
class _LoSection:
    index:     str
    header:    str
    condition: str
    body:      str


@dataclass
class _Cluster:
    name: str
    typ:  str
    los:  List[_LoSection]


@dataclass
class _Document:
    seth_name: str
    seth_type: str
    clusters:  List[_Cluster]


def _read_los(source: str) -> List[_LoSection]:
    """Extract Lo-sections from a cluster body string."""
    los: List[_LoSection] = []
    pos = 0
    s = source.strip()

    while pos < len(s):
        while pos < len(s) and s[pos] in " \t\r\n":
            pos += 1
        if pos >= len(s):
            break

        colon_pos = s.find(":", pos)
        if colon_pos == -1:
            break

        lo_name = s[pos:colon_pos].strip()
        index = lo_name[2:] if lo_name.startswith("Lo") else lo_name

        pos = colon_pos + 1
        while pos < len(s) and s[pos] in " \t\r\n":
            pos += 1

        brace_pos = s.find("{", pos)
        if brace_pos == -1:
            break

        header_cond = s[pos:brace_pos].strip()
        paren_open  = header_cond.find("(")
        if paren_open != -1:
            paren_close = _close_paren(header_cond, paren_open)
            header    = header_cond[:paren_open].strip()
            condition = header_cond[paren_open + 1 : paren_close]
        else:
            header    = header_cond
            condition = ""

        end_pos = _close_brace(s, brace_pos)
        body    = s[brace_pos + 1 : end_pos].strip()

        los.append(_LoSection(index=index, header=header, condition=condition, body=body))
        pos = end_pos + 1

    return los


def _read_clusters(source: str) -> List[_Cluster]:
    """Extract clusters from a Seth body string."""
    clusters: List[_Cluster] = []
    pos = 0
    s = source.strip()

    while pos < len(s):
        while pos < len(s) and s[pos] in " \t\r\n":
            pos += 1
        if pos >= len(s):
            break

        colon_pos = s.find(":", pos)
        if colon_pos == -1:
            break

        cluster_name = s[pos:colon_pos].strip()
        pos = colon_pos + 1

        while pos < len(s) and s[pos] in " \t\r\n":
            pos += 1

        brace_pos = s.find("{", pos)
        if brace_pos == -1:
            break

        cluster_type = s[pos:brace_pos].strip()
        end_pos      = _close_brace(s, brace_pos)
        cluster_body = s[brace_pos + 1 : end_pos].strip()

        clusters.append(_Cluster(
            name=cluster_name,
            typ=cluster_type,
            los=_read_los(cluster_body),
        ))
        pos = end_pos + 1

    return clusters


def _read_document(source: str) -> _Document:
    """Structurally parse a .ko document."""
    s = source.strip()

    colon_pos  = s.index(":")
    seth_name  = s[:colon_pos].strip()
    rest       = s[colon_pos + 1:].strip()
    brace_pos  = rest.index("{")
    seth_type  = rest[:brace_pos].strip()
    end_pos    = _close_brace(rest, brace_pos)
    outer_body = rest[brace_pos + 1 : end_pos].strip()

    return _Document(
        seth_name=seth_name,
        seth_type=seth_type,
        clusters=_read_clusters(outer_body),
    )


# ── Entity spec reader ────────────────────────────────────────────────────────

def _extract_specs(body: str) -> Tuple[List[List[str]], Optional[str], List[str]]:
    """
    Extract entity specs from a Lo-section body.

    Returns
    -------
    specs       : list of token-lists, one per [spec] expression
    ta_shy_ma   : Rose numeral address from [TaShyMa(n)], or None
    echoes      : raw strings that could not be read
    """
    specs:     List[List[str]] = []
    ta_shy_ma: Optional[str]   = None
    echoes:    List[str]       = []
    pos = 0

    while pos < len(body):
        while pos < len(body) and body[pos] in " \t\r\n":
            pos += 1
        if pos >= len(body):
            break

        if body[pos] != "[":
            pos += 1
            continue

        try:
            end = _close_bracket(body, pos)
        except ValueError:
            echoes.append(body[pos:pos + 40])
            pos += 1
            continue

        inner   = body[pos + 1 : end].strip()
        pos     = end + 1

        if not inner:
            continue

        # TaShyMa special case
        if inner.startswith("TaShyMa"):
            paren = inner.find("(")
            if paren != -1:
                try:
                    p_end = _close_paren(inner, paren)
                    ta_shy_ma = inner[paren + 1 : p_end].strip()
                except ValueError:
                    echoes.append(inner)
            continue

        # Split into whitespace-delimited tokens
        tokens = inner.split()
        if tokens:
            specs.append(tokens)

    return specs, ta_shy_ma, echoes


# ── Section evaluator ─────────────────────────────────────────────────────────

_CANNABIS_SYMBOLS = frozenset({
    "At", "Ar", "Av", "Azr", "Af", "An",
    "Od", "Ox", "Om", "Soa",
    "It", "Ir", "Iv", "Izr", "If", "In",
    "Ed", "Ex", "Em", "Sei",
    "Yt", "Yr", "Yv", "Yzr", "Yf", "Yn",
    "Ud", "Ux", "Um", "Suy",
})


def _eval_section(
    lo:             _LoSection,
    namespace:      Dict[str, Any],
    witness_states: Dict[str, str],
    frame:          SamosMyrFrame,
) -> SectionResult:
    specs, ta_shy_ma, echoes = _extract_specs(lo.body)
    definitions: Dict[str, List[str]] = {}

    for tokens in specs:
        # Cannabis witness tracking — any Cannabis symbol in the spec
        for tok in tokens:
            if tok in _CANNABIS_SYMBOLS:
                if tok not in witness_states:
                    witness_states[tok] = WitnessState.UNWITNESSED

        # Mavo registration: first Mavo-prefixed token is the defined key
        mavo_idx = next((i for i, t in enumerate(tokens) if t.startswith("Mavo")), None)
        if mavo_idx is not None:
            key  = tokens[mavo_idx]
            defn = [t for t in tokens if t != key or tokens.index(t) != mavo_idx]
            definitions[key] = defn
            namespace[key]   = defn

    # TaShyMa: commit this section's definitions into the frame as a SoaArtifact
    if ta_shy_ma is not None and definitions:
        boundary_id = f"TaShyMa_{lo.index}_{ta_shy_ma}"
        for key in definitions:
            entry = UnresolvedEntry(
                entry_id        = f"{boundary_id}_{key}",
                source_boundary = boundary_id,
                deliberate      = False,
                payload         = {"key": key, "defn": definitions[key]},
            )
            artifact = artifact_for_entry(
                artifact_id = f"soa_{lo.index}_{key}",
                boundary_id = boundary_id,
                entry       = entry,
            )
            frame.generated.append(artifact)

    return SectionResult(
        index          = lo.index,
        header         = lo.header,
        condition      = lo.condition,
        definitions    = definitions,
        ta_shy_ma      = ta_shy_ma,
        witness_states = dict(witness_states),
        echoes         = echoes,
    )


# ── Public evaluator ──────────────────────────────────────────────────────────

class KobraEvaluator:
    """
    Python host evaluator for Kobra .ko documents.

    Bootstrap the kernel namespace from Self-spec.ko first, then evaluate
    subsequent .ko documents (kos_labyrinth.ko, etc.) against that namespace.

    When the native Kobra evaluator is complete, this class is the scaffold
    that removes itself.  The spec does not change.

    Usage
    -----
        ev = KobraEvaluator()
        result = ev.eval_file("path/to/Self-spec.ko")
        print(result.namespace)
    """

    def __init__(self) -> None:
        self._namespace:      Dict[str, Any] = {}
        self._witness_states: Dict[str, str] = {}
        self._boundary = SamosMyrBoundary(
            boundary_id = "kernel_init",
            label       = "Kernel bootstrap — Python host",
        )
        self._frame = open_frame(
            frame_id = "kernel_bootstrap",
            boundary = self._boundary,
        )

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def namespace(self) -> Dict[str, Any]:
        return dict(self._namespace)

    @property
    def frame(self) -> SamosMyrFrame:
        return self._frame

    def eval_file(self, path: str | Path) -> DocumentResult:
        return self.eval_source(Path(path).read_text(encoding="utf-8"))

    def eval_source(self, source: str) -> DocumentResult:
        doc      = _read_document(source)
        clusters: List[ClusterResult] = []

        for cluster in doc.clusters:
            section_results: List[SectionResult] = []
            for lo in cluster.los:
                result = _eval_section(
                    lo,
                    self._namespace,
                    self._witness_states,
                    self._frame,
                )
                section_results.append(result)
            clusters.append(ClusterResult(
                name     = cluster.name,
                typ      = cluster.typ,
                sections = section_results,
            ))

        return DocumentResult(
            seth_name = doc.seth_name,
            seth_type = doc.seth_type,
            clusters  = clusters,
            namespace = dict(self._namespace),
            frame     = self._frame,
        )
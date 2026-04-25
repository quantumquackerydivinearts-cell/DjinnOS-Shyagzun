"""
shygazun.kernel.kobra
=====================
Kobra — Shygazun's executable programming substrate.

A Python-like language built entirely from Shygazun Akinenwun.
Declaration, dictation, and operation are inseparable: every expression
is simultaneously an ontological claim, a causal record, and an instruction.

Public surface
--------------
  parse(source: str) -> ParseResult
      Parse a Kobra source string.  Returns Resolved, Echo, or FrontierOpen.

  segment(raw: str) -> (tuple[AkinenDescriptor, ...], str)
      Sub-layer: segment a token string into AkinenDescriptors.
      Second element is the unmatched remainder (empty = full success).

Types re-exported for consumers
--------------------------------
  AkinenDescriptor
  AkinenNode        — a single akinen as a whitespace-delimited token
  AkinenwunNode     — two or more akinen concatenated as a single token
  KobraToken        — Union[AkinenNode, AkinenwunNode]
  Wunashako, WunashakoGroup
  Application, SubStructure, KobraSequence
  Expr, ParseResult
  Resolved, Echo, FrontierOpen
"""
from .parser import parse
from .sublayer import segment
from .topology import (
    TopologyKind,
    EdgeKind,
    ExecutionNode,
    ExecutionEdge,
    ExecutionTopology,
    build_sequential_topology,
    build_frontier_topology,
)
from .samosmyr import (
    SamosMyrBoundary,
    SoaArtifact,
    UnresolvedEntry,
    SamosMyrFrame,
    open_frame,
    artifact_for_entry,
)
from .chromatic import (
    ChromaticBand,
    ChromaticSignature,
    ChromaticProfile,
    classify_band,
    signature_from_tokens,
    profile_from_signatures,
)
from .types import (
    AkinenDescriptor,
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

__all__ = [
    # entry points
    "parse",
    "segment",
    # topology
    "TopologyKind",
    "EdgeKind",
    "ExecutionNode",
    "ExecutionEdge",
    "ExecutionTopology",
    "build_sequential_topology",
    "build_frontier_topology",
    # samosmyr
    "SamosMyrBoundary",
    "SoaArtifact",
    "UnresolvedEntry",
    "SamosMyrFrame",
    "open_frame",
    "artifact_for_entry",
    # chromatic
    "ChromaticBand",
    "ChromaticSignature",
    "ChromaticProfile",
    "classify_band",
    "signature_from_tokens",
    "profile_from_signatures",
    # types
    "AkinenDescriptor",
    "AkinenNode",
    "AkinenwunNode",
    "Application",
    "Echo",
    "Expr",
    "FrontierOpen",
    "KobraSequence",
    "KobraToken",
    "ParseResult",
    "Resolved",
    "SubStructure",
    "Wunashako",
    "WunashakoGroup",
]
"""
shygazun/kernel/kobra/samosmyr.py
==================================
SamosMyr boundaries and SoaArtifacts — persistent unresolved state.

A SamosMyr boundary marks a transition between execution frames: a game
boundary, a realm transition, a quest phase change, or any structural
discontinuity in the Kobra execution flow.

When execution crosses a SamosMyr boundary, unresolved FrontierOpen entries
do not silently disappear.  Instead, they become SoaArtifacts — live objects
carrying the unresolved state forward.  The name honours Soa (byte 193,
Conscious persistence): the artifact is the language's deliberate memory
of what it has not yet resolved.

Key concepts
------------
  SamosMyrBoundary — a named transition point.  Boundaries are immutable
                     identity records; the crossing logic lives in qqva.
  SoaArtifact      — carries one or more unresolved FrontierOpen entries
                     across a SamosMyr boundary.  append-only; entries are
                     never removed (only witnessed, which seals them).
  SamosMyrFrame    — an execution frame bounded by two boundaries.  Holds
                     the topology active within the frame and any artifacts
                     that arrived from prior frames.

Constraints (kernel layer)
--------------------------
  No auto-attestation.  SoaArtifacts never resolve their own entries.
  No semantic inference.  The content of FrontierOpen.candidate_a/b is
  not examined here; only the structural fact of being unresolved matters.
  Append-only.  Entries are added to artifacts; never removed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# SamosMyr boundary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SamosMyrBoundary:
    """
    A named transition point in the Kobra execution flow.

    ``boundary_id`` is a stable, unique identifier (e.g. a quest slug,
    a game slug, or a realm transition key).
    ``label`` is a human-readable name for debugging and display.
    ``realm``  is the target realm after crossing (lapidus/mercurie/sulphera
               or None for intra-realm transitions).
    ``game_id`` is the KLGS slug of the game this boundary belongs to,
                or None for cross-game boundaries.
    """
    boundary_id: str
    label:       str
    realm:       Optional[str] = None    # target realm after crossing
    game_id:     Optional[str] = None    # e.g. "7_KLGS"


# ---------------------------------------------------------------------------
# Unresolved entry record (kernel-level, plain data)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UnresolvedEntry:
    """
    A single unresolved FrontierOpen entry to be carried forward.

    ``entry_id``        is a stable identifier for this frontier (e.g. the
                        hash of its source span or a quest-assigned slug).
    ``source_boundary`` is the boundary at which this entry became an artifact.
    ``deliberate``      mirrors FrontierOpen.deliberate.
    ``cannabis_symbol`` is the Cannabis akinen that created this frontier,
                        if the frontier is deliberate; None otherwise.
    ``payload``         is an opaque dict for caller-attached context (e.g.
                        quest metadata).  Kernel code never reads this dict;
                        it is carried forward untouched.
    """
    entry_id:        str
    source_boundary: str              # boundary_id where this became an artifact
    deliberate:      bool   = False
    cannabis_symbol: Optional[str] = None
    payload:         Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# SoaArtifact
# ---------------------------------------------------------------------------

@dataclass
class SoaArtifact:
    """
    Conscious persistence of unresolved FrontierOpen entries across a
    SamosMyr boundary.

    Artifacts are append-only: call ``carry(entry)`` to add an entry.
    Entries are sealed (marked witnessed) by calling ``seal(entry_id,
    candidate)``.  Sealing does not remove the entry; it records the
    attestation.

    ``artifact_id``     is a stable identifier for this artifact instance.
    ``source_boundary`` is the boundary this artifact was created at.
    ``target_boundary`` is the boundary this artifact is destined for
                        (None = not yet placed at a target).
    ``entries``         is the ordered list of unresolved entries.
    ``seals``           maps entry_id → witness_candidate ("a" or "b").
    """
    artifact_id:     str
    source_boundary: str
    target_boundary: Optional[str]           = None
    entries:         List[UnresolvedEntry]   = field(default_factory=list)
    seals:           Dict[str, str]          = field(default_factory=dict)

    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def is_fully_resolved(self) -> bool:
        return bool(self.entries) and all(
            e.entry_id in self.seals for e in self.entries
        )

    def carry(self, entry: UnresolvedEntry) -> None:
        """Append an unresolved entry.  Duplicates (by entry_id) are skipped."""
        if any(e.entry_id == entry.entry_id for e in self.entries):
            return
        self.entries.append(entry)

    def seal(self, entry_id: str, candidate: str) -> None:
        """
        Record that ``entry_id`` was attested as ``candidate`` ("a" or "b").
        No-op if the entry is not in this artifact.
        """
        if any(e.entry_id == entry_id for e in self.entries):
            self.seals[entry_id] = candidate

    def unresolved(self) -> List[UnresolvedEntry]:
        """Return entries that have not yet been sealed."""
        return [e for e in self.entries if e.entry_id not in self.seals]

    def carry_forward(self, target_boundary: str) -> "SoaArtifact":
        """
        Return a new SoaArtifact carrying all *unresolved* entries forward
        to ``target_boundary``.  Already-sealed entries are not propagated.
        """
        new_artifact = SoaArtifact(
            artifact_id=f"{self.artifact_id}→{target_boundary}",
            source_boundary=self.source_boundary,
            target_boundary=target_boundary,
        )
        for entry in self.unresolved():
            new_artifact.carry(entry)
        return new_artifact


# ---------------------------------------------------------------------------
# SamosMyr frame
# ---------------------------------------------------------------------------

@dataclass
class SamosMyrFrame:
    """
    An execution frame bounded by two SamosMyr boundaries.

    ``frame_id``        is a stable identifier for this frame.
    ``entry_boundary``  is where this frame begins.
    ``exit_boundary``   is where this frame ends (None = open / not yet
                        reached the exit).
    ``incoming``        is the list of SoaArtifacts that arrived from
                        prior frames via carry_forward().
    ``generated``       is the list of SoaArtifacts created within this
                        frame (from newly-encountered FrontierOpen entries).
    """
    frame_id:        str
    entry_boundary:  SamosMyrBoundary
    exit_boundary:   Optional[SamosMyrBoundary] = None
    incoming:        List[SoaArtifact]           = field(default_factory=list)
    generated:       List[SoaArtifact]           = field(default_factory=list)

    def all_artifacts(self) -> List[SoaArtifact]:
        return list(self.incoming) + list(self.generated)

    def all_unresolved(self) -> List[UnresolvedEntry]:
        result: List[UnresolvedEntry] = []
        for artifact in self.all_artifacts():
            result.extend(artifact.unresolved())
        return result

    def close(self, exit_boundary: SamosMyrBoundary) -> List[SoaArtifact]:
        """
        Close this frame at ``exit_boundary``.

        Returns a list of SoaArtifacts to carry forward: one per source
        artifact that still has unresolved entries.  The caller passes
        these to the next SamosMyrFrame as ``incoming``.
        """
        self.exit_boundary = exit_boundary
        carried: List[SoaArtifact] = []
        for artifact in self.all_artifacts():
            if not artifact.is_empty() and not artifact.is_fully_resolved():
                carried.append(
                    artifact.carry_forward(exit_boundary.boundary_id)
                )
        return carried


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def open_frame(
    frame_id: str,
    boundary: SamosMyrBoundary,
    incoming: Optional[List[SoaArtifact]] = None,
) -> SamosMyrFrame:
    """
    Open a new SamosMyrFrame at ``boundary``, optionally receiving
    ``incoming`` artifacts from a prior frame.
    """
    return SamosMyrFrame(
        frame_id=frame_id,
        entry_boundary=boundary,
        incoming=list(incoming or []),
    )


def artifact_for_entry(
    artifact_id: str,
    boundary_id: str,
    entry: UnresolvedEntry,
) -> SoaArtifact:
    """
    Create a SoaArtifact holding a single unresolved entry.
    Convenience for the common case of one frontier → one artifact.
    """
    artifact = SoaArtifact(
        artifact_id=artifact_id,
        source_boundary=boundary_id,
    )
    artifact.carry(entry)
    return artifact
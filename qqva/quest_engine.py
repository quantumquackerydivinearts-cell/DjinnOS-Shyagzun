"""
qqva/quest_engine.py
====================
Quest state machine — WitnessTracker adapted to the qqva structural pattern.

The Cannabis Tongue witness state vector IS the quest state machine.
Each deliberate Cannabis entry in a scene represents a branch point that
is live (both candidates executing in parallel) until a game event attests
one candidate.  The WitnessTracker records which entries have been witnessed
and which remain open.

Constraints (qqva layer)
------------------------
  No auto-attestation.  Only explicit QuestEvent(event_type="witness") calls
  advance an entry from "unwitnessed" to "witnessed".
  No semantic inference.  The content of candidate_a / candidate_b is opaque
  to this layer; only the structural fact of being witnessed/unwitnessed
  matters.
  No kernel mutation.  WitnessTracker reads kernel types (FrontierOpen,
  SoaArtifact) but never modifies them.  Advancement returns a new
  QuestState; the old state is not mutated.

Key types
---------
  WitnessEntry   — one Cannabis entry in the quest state vector.
  QuestState     — the full witness state vector for a quest.
  QuestEvent     — an event that can advance the state.
  WitnessTracker — the state machine.  Primary entry point: advance().

SamosMyr integration
--------------------
  When a boundary is crossed (QuestEvent(event_type="advance_boundary")),
  unwitnessed deliberate entries become SoaArtifacts carried forward to the
  next frame.  The resulting artifacts are attached to QuestState.soa_artifacts
  as plain dicts (serialisable) with the structure:
    { artifact_id, source_boundary, target_boundary, entries: [...] }
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, TypedDict


# ---------------------------------------------------------------------------
# Fallback imports from kernel kobra (graceful degradation if unavailable)
# ---------------------------------------------------------------------------

try:
    from shygazun.kernel.kobra.samosmyr import (  # type: ignore
        SoaArtifact,
        SamosMyrBoundary,
        UnresolvedEntry,
        artifact_for_entry,
    )
    _HAS_SAMOSMYR = True
except Exception:
    _HAS_SAMOSMYR = False
    SoaArtifact = None  # type: ignore
    SamosMyrBoundary = None  # type: ignore
    UnresolvedEntry = None  # type: ignore
    artifact_for_entry = None  # type: ignore

try:
    from shygazun.kernel.kobra.chromatic import (  # type: ignore
        ChromaticBand,
        classify_band,
    )
    _HAS_CHROMATIC = True
except Exception:
    _HAS_CHROMATIC = False
    ChromaticBand = None  # type: ignore
    classify_band = None  # type: ignore


# ---------------------------------------------------------------------------
# State types
# ---------------------------------------------------------------------------

WITNESS_UNWITNESSED = "unwitnessed"
WITNESS_WITNESSED   = "witnessed"
WITNESS_ECHO        = "echo"       # hard parse failure carried forward


class WitnessEntry(TypedDict):
    """One Cannabis entry in the quest witness state vector."""
    entry_id:           str
    cannabis_symbol:    str           # the Cannabis akinen (e.g. "Kofra")
    candidate_a_label:  str           # human-readable label for candidate A
    candidate_b_label:  str           # human-readable label for candidate B
    witness_state:      str           # WITNESS_* constant
    witnessed_candidate: Optional[str]  # "a" | "b" | None


class QuestState(TypedDict):
    """Full witness state vector for a quest."""
    quest_id:         str
    game_id:          str                      # e.g. "7_KLGS"
    entries:          Dict[str, WitnessEntry]  # entry_id → WitnessEntry
    soa_artifacts:    List[Dict[str, Any]]     # serialised SoaArtifact records
    current_frame:    str                      # current SamosMyr frame id


class QuestEvent(TypedDict, total=False):
    """An event that can advance the quest state."""
    event_type:   str            # "witness" | "echo" | "advance_boundary"
    entry_id:     Optional[str]  # required for witness/echo
    candidate:    Optional[str]  # "a" | "b" — required for witness
    boundary_id:  Optional[str]  # required for advance_boundary
    boundary_label: Optional[str]
    realm:        Optional[str]  # target realm for advance_boundary


# ---------------------------------------------------------------------------
# WitnessTracker
# ---------------------------------------------------------------------------

class WitnessTracker:
    """
    Quest state machine implementing the Cannabis witness state vector.

    All methods treat QuestState as immutable: advance() and related
    methods return new QuestState dicts; the input is never mutated.

    Usage
    -----
    .. code-block:: python

        tracker = WitnessTracker()
        state   = tracker.initial_state("my_quest", "7_KLGS", entries=[...])
        state   = tracker.advance(state, {
            "event_type": "witness",
            "entry_id":   "entry_001",
            "candidate":  "a",
        })
    """

    # -- Construction --------------------------------------------------------

    def initial_state(
        self,
        quest_id: str,
        game_id: str,
        entries: Optional[List[WitnessEntry]] = None,
        frame_id: str = "frame_0",
    ) -> QuestState:
        """
        Create a fresh QuestState with all entries in WITNESS_UNWITNESSED.
        """
        entry_map: Dict[str, WitnessEntry] = {}
        for entry in (entries or []):
            entry_map[entry["entry_id"]] = dict(entry)  # type: ignore[arg-type]
        return QuestState(
            quest_id=quest_id,
            game_id=game_id,
            entries=entry_map,
            soa_artifacts=[],
            current_frame=frame_id,
        )

    def register_entry(
        self,
        state: QuestState,
        entry: WitnessEntry,
    ) -> QuestState:
        """
        Return a new state with ``entry`` added.  If an entry with the same
        entry_id already exists, it is replaced.
        """
        new_state = _copy_state(state)
        new_state["entries"][entry["entry_id"]] = dict(entry)  # type: ignore[assignment]
        return new_state

    # -- Core state machine --------------------------------------------------

    def advance(self, state: QuestState, event: QuestEvent) -> QuestState:
        """
        Advance the quest state given an event.

        event_type "witness"
            Marks entry ``entry_id`` as witnessed with ``candidate`` ("a"|"b").
            No-op if already witnessed.

        event_type "echo"
            Marks entry ``entry_id`` as WITNESS_ECHO (hard parse failure
            carried forward).

        event_type "advance_boundary"
            Crosses a SamosMyr boundary: all unwitnessed deliberate entries
            become SoaArtifacts serialised into state.soa_artifacts.
            Updates current_frame to boundary_id.

        Returns a new QuestState; the original is not modified.
        """
        ev_type = str(event.get("event_type") or "")

        if ev_type == "witness":
            return self._handle_witness(state, event)
        if ev_type == "echo":
            return self._handle_echo(state, event)
        if ev_type == "advance_boundary":
            return self._handle_boundary(state, event)
        return _copy_state(state)

    def _handle_witness(
        self, state: QuestState, event: QuestEvent
    ) -> QuestState:
        entry_id  = str(event.get("entry_id") or "")
        candidate = str(event.get("candidate") or "")
        if not entry_id or candidate not in ("a", "b"):
            return _copy_state(state)
        if entry_id not in state["entries"]:
            return _copy_state(state)
        new_state = _copy_state(state)
        entry = dict(new_state["entries"][entry_id])
        if entry["witness_state"] == WITNESS_WITNESSED:
            return new_state
        entry["witness_state"]      = WITNESS_WITNESSED
        entry["witnessed_candidate"] = candidate
        new_state["entries"][entry_id] = entry  # type: ignore[assignment]
        return new_state

    def _handle_echo(
        self, state: QuestState, event: QuestEvent
    ) -> QuestState:
        entry_id = str(event.get("entry_id") or "")
        if not entry_id or entry_id not in state["entries"]:
            return _copy_state(state)
        new_state = _copy_state(state)
        entry = dict(new_state["entries"][entry_id])
        if entry["witness_state"] != WITNESS_UNWITNESSED:
            return new_state
        entry["witness_state"] = WITNESS_ECHO
        new_state["entries"][entry_id] = entry  # type: ignore[assignment]
        return new_state

    def _handle_boundary(
        self, state: QuestState, event: QuestEvent
    ) -> QuestState:
        boundary_id    = str(event.get("boundary_id") or "")
        boundary_label = str(event.get("boundary_label") or boundary_id)
        realm          = event.get("realm")

        new_state = _copy_state(state)

        unwitnessed = [
            e for e in new_state["entries"].values()
            if e["witness_state"] == WITNESS_UNWITNESSED
        ]

        for entry in unwitnessed:
            artifact_dict: Dict[str, Any] = {
                "artifact_id":     f"soa_{entry['entry_id']}@{boundary_id}",
                "source_boundary": state["current_frame"],
                "target_boundary": boundary_id,
                "entries": [{
                    "entry_id":        entry["entry_id"],
                    "source_boundary": state["current_frame"],
                    "deliberate":      True,
                    "cannabis_symbol": entry["cannabis_symbol"],
                }],
                "seals": {},
            }
            if realm:
                artifact_dict["realm"] = realm
            new_state["soa_artifacts"].append(artifact_dict)

        new_state["current_frame"] = boundary_id or new_state["current_frame"]
        return new_state

    # -- Query methods -------------------------------------------------------

    def witnessed(self, state: QuestState, entry_id: str) -> bool:
        entry = state["entries"].get(entry_id)
        return entry is not None and entry["witness_state"] == WITNESS_WITNESSED

    def is_echo(self, state: QuestState, entry_id: str) -> bool:
        entry = state["entries"].get(entry_id)
        return entry is not None and entry["witness_state"] == WITNESS_ECHO

    def unwitnessed_entries(self, state: QuestState) -> List[WitnessEntry]:
        return [
            e for e in state["entries"].values()
            if e["witness_state"] == WITNESS_UNWITNESSED
        ]

    def witnessed_entries(self, state: QuestState) -> List[WitnessEntry]:
        return [
            e for e in state["entries"].values()
            if e["witness_state"] == WITNESS_WITNESSED
        ]

    def all_witnessed(self, state: QuestState) -> bool:
        return all(
            e["witness_state"] == WITNESS_WITNESSED
            for e in state["entries"].values()
        )

    def witnessed_candidate(
        self, state: QuestState, entry_id: str
    ) -> Optional[str]:
        """Return "a", "b", or None if the entry is not witnessed."""
        entry = state["entries"].get(entry_id)
        if entry is None or entry["witness_state"] != WITNESS_WITNESSED:
            return None
        return entry.get("witnessed_candidate")

    def pending_soa_artifacts(
        self, state: QuestState
    ) -> List[Dict[str, Any]]:
        """Return soa_artifacts that have entries with no seals."""
        return [
            a for a in state["soa_artifacts"]
            if any(
                e["entry_id"] not in (a.get("seals") or {})
                for e in (a.get("entries") or [])
            )
        ]

    # -- SoaArtifact reconciliation (kernel layer, if available) ------------

    def seal_soa_entry(
        self,
        state: QuestState,
        artifact_id: str,
        entry_id: str,
        candidate: str,
    ) -> QuestState:
        """
        Seal an unresolved SoaArtifact entry (marks it witnessed in the
        artifact's seal dict and also advances the main entry if present).
        Returns a new QuestState.
        """
        new_state = _copy_state(state)
        for artifact in new_state["soa_artifacts"]:
            if artifact.get("artifact_id") == artifact_id:
                if "seals" not in artifact:
                    artifact["seals"] = {}
                artifact["seals"][entry_id] = candidate
        if entry_id in new_state["entries"]:
            new_state = self.advance(
                new_state,
                QuestEvent(
                    event_type="witness",
                    entry_id=entry_id,
                    candidate=candidate,
                ),
            )
        return new_state


# ---------------------------------------------------------------------------
# WitnessEntry factory
# ---------------------------------------------------------------------------

def make_entry(
    entry_id: str,
    cannabis_symbol: str,
    candidate_a_label: str,
    candidate_b_label: str,
) -> WitnessEntry:
    """Construct a fresh WitnessEntry in UNWITNESSED state."""
    return WitnessEntry(
        entry_id=entry_id,
        cannabis_symbol=cannabis_symbol,
        candidate_a_label=candidate_a_label,
        candidate_b_label=candidate_b_label,
        witness_state=WITNESS_UNWITNESSED,
        witnessed_candidate=None,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _copy_state(state: QuestState) -> QuestState:
    """Return a shallow copy of QuestState with entries and artifacts deep-copied."""
    return QuestState(
        quest_id=state["quest_id"],
        game_id=state["game_id"],
        entries={k: dict(v) for k, v in state["entries"].items()},  # type: ignore[misc]
        soa_artifacts=copy.deepcopy(state["soa_artifacts"]),
        current_frame=state["current_frame"],
    )
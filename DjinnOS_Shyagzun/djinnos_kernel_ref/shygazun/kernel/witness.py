"""
shygazun/kernel/kobra/witness.py
=================================
Witness state tracker — maintains the Cannabis entry witness state vector
across a SamosMyr session and propagates witness events through the
perspectival map.

Architecture
------------
The WitnessTracker is the runtime coherence engine for a single game session.
It holds:

  - The current witness state vector: Cannabis akinen symbol → WitnessState
  - The perspectival map: character id → set of Cannabis entry symbols
    they can access from their current position
  - The entry path history: ordered list of entry point ids taken
  - The Soa ledger: unresolved Cannabis entries carried forward as
    persistent files after TaShyMa fires

Witness events are fired by the sensory score (chromatic events),
player action, proximity, or script execution. Each event carries
the Cannabis akinen symbol being witnessed, the character id of the
witness (perspectival source), and the topological relevance declaration
governing propagation.

Propagation
-----------
When a Cannabis entry is witnessed, the witness event propagates to
other characters sharing that entry in the perspectival map, subject
to the topological relevance declaration's geometry. A Topology scaffold
bond propagates fully. A Gradient barrier may not propagate at all.
The propagation_likelihood from the relevance declaration's geometry
gates how far the witness travels.

Soa forwarding
--------------
When TaShyMa fires, all unwitnessed Cannabis entries are converted to
Soa — persistent file objects — and added to the Soa ledger. The ledger
persists across SamosMyr boundaries and is handed to the DyskaSoaShun
at game boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import time as _time

from .topology import RelevanceDeclaration, gate_decision, gradient_propagation_likelihood


# ---------------------------------------------------------------------------
# Witness state enum
# ---------------------------------------------------------------------------

class WitnessState(str, Enum):
    UNWITNESSED  = "unwitnessed"   # Cannabis entry, witness slot open
    WITNESSED    = "witnessed"     # fully attested
    PARTIAL      = "partial"       # witnessed by some characters, not all
    FRONTIER     = "frontier"      # deliberately held open (intentional Cannabis)
    SOA          = "soa"           # carried forward as persistent file


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CannabisEntry:
    """
    A single Cannabis entry in the witness state vector.
    """
    symbol:           str                          # Cannabis akinen symbol
    state:            WitnessState = WitnessState.UNWITNESSED
    witnesses:        List[str] = field(default_factory=list)    # character ids
    witness_events:   List["WitnessEvent"] = field(default_factory=list)
    relevance_decl:   Optional[RelevanceDeclaration] = None
    samosmyr_id:      Optional[str] = None         # which SamosMyr this lives in
    deliberate:       bool = False                  # intentional Cannabis marker
    soa_artifact:     Optional["SoaArtifact"] = None


@dataclass
class WitnessEvent:
    """
    A single witness event — something that attests a Cannabis entry.
    """
    cannabis_symbol:  str
    witness_character: str                  # character id or "player"
    event_type:       str                   # "sensory" | "action" | "proximity" | "script"
    sensory_register: Optional[str] = None  # "Fire"|"Air"|"Water"|"Earth" if sensory
    chromatic_chord:  Optional[str] = None  # Rose vector chord if sensory
    timestamp:        float = field(default_factory=_time.time)
    propagated_to:    List[str] = field(default_factory=list)


@dataclass
class SoaArtifact:
    """
    A persistent file object produced when TaShyMa fires with
    unwitnessed Cannabis entries remaining.
    Carried forward in the Soa ledger.
    """
    cannabis_symbol:   str
    samosmyr_id:       str
    temporal_address:  int          # seconds at which TaShyMa fired
    partial_witnesses: List[str]    # characters who had witnessed it partially
    relevance_decl:    Optional[RelevanceDeclaration]
    gate_result:       Optional[Dict[str, Any]] = None   # DyskaSoaShun gate decision


@dataclass
class PerspectivalEntry:
    """
    A character's perspectival position — which Cannabis entries they
    can access and from what entry path.
    """
    character_id:     str
    accessible_entries: Set[str] = field(default_factory=set)
    entry_path:       List[str] = field(default_factory=list)
    perspectival_limit: float = 1.0   # 0.0–1.0, 1.0 = full access


# ---------------------------------------------------------------------------
# Witness tracker
# ---------------------------------------------------------------------------

class WitnessTracker:
    """
    Runtime coherence engine for a game session.

    Maintains the witness state vector, perspectival map, entry path
    history, and Soa ledger across SamosMyr boundaries.

    Usage
    -----
        tracker = WitnessTracker()
        tracker.enter_samosmyr("LoShun", entry_point="east_gate")
        tracker.register_cannabis_entries(["At", "Ar", "Av"], samosmyr_id="LoShun")
        tracker.set_perspectival_map({
            "character_a": {"At", "Ar"},
            "character_b": {"Ar", "Av"},
        })
        tracker.fire_witness_event("At", witness_character="player",
                                   event_type="sensory",
                                   sensory_register="Water")
        soa = tracker.fire_taShyMa(temporal_address=1612)
    """

    def __init__(self) -> None:
        self._entries:       Dict[str, CannabisEntry]     = {}
        self._perspectival:  Dict[str, PerspectivalEntry] = {}
        self._entry_path:    List[str]                    = []
        self._soa_ledger:    List[SoaArtifact]            = []
        self._current_samosmyr: Optional[str]             = None
        self._session_events:   List[WitnessEvent]        = []

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def enter_samosmyr(self, samosmyr_id: str, entry_point: str) -> None:
        """Record entry into a SamosMyr from a specific entry point."""
        self._current_samosmyr = samosmyr_id
        self._entry_path.append(entry_point)

    def register_cannabis_entries(
        self,
        symbols: List[str],
        samosmyr_id: Optional[str] = None,
        deliberate: bool = False,
        relevance_decls: Optional[Dict[str, RelevanceDeclaration]] = None,
    ) -> None:
        """
        Register Cannabis entries from a parsed SamosMyr.
        Only registers entries not already in the vector.
        """
        sid = samosmyr_id or self._current_samosmyr
        rdecls = relevance_decls or {}
        for sym in symbols:
            if sym not in self._entries:
                self._entries[sym] = CannabisEntry(
                    symbol=sym,
                    state=WitnessState.FRONTIER if deliberate else WitnessState.UNWITNESSED,
                    samosmyr_id=sid,
                    deliberate=deliberate,
                    relevance_decl=rdecls.get(sym),
                )

    def set_perspectival_map(
        self,
        character_map: Dict[str, Set[str]],
        entry_path: Optional[List[str]] = None,
        limits: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Set the perspectival map — which characters can access which
        Cannabis entries from the current entry path.

        character_map: {character_id: set of Cannabis symbols accessible}
        limits: {character_id: float 0.0–1.0 perspectival limit}
        """
        path = entry_path or self._entry_path
        lims = limits or {}
        for char_id, accessible in character_map.items():
            self._perspectival[char_id] = PerspectivalEntry(
                character_id=char_id,
                accessible_entries=set(accessible),
                entry_path=list(path),
                perspectival_limit=lims.get(char_id, 1.0),
            )

    # ------------------------------------------------------------------
    # Witness events
    # ------------------------------------------------------------------

    def fire_witness_event(
        self,
        cannabis_symbol: str,
        witness_character: str,
        event_type: str = "action",
        sensory_register: Optional[str] = None,
        chromatic_chord: Optional[str] = None,
    ) -> WitnessEvent:
        """
        Fire a witness event for a Cannabis entry.

        Checks perspectival access before registering. Propagates to
        other characters sharing the entry, subject to topological
        relevance geometry.

        Returns the WitnessEvent produced.
        """
        event = WitnessEvent(
            cannabis_symbol=cannabis_symbol,
            witness_character=witness_character,
            event_type=event_type,
            sensory_register=sensory_register,
            chromatic_chord=chromatic_chord,
        )

        if cannabis_symbol not in self._entries:
            return event

        entry = self._entries[cannabis_symbol]

        if entry.state in (WitnessState.WITNESSED, WitnessState.SOA):
            return event

        # Check perspectival access
        if witness_character != "player":
            perspectival = self._perspectival.get(witness_character)
            if perspectival and cannabis_symbol not in perspectival.accessible_entries:
                return event
            if perspectival and perspectival.perspectival_limit < 0.3:
                return event

        # Register witness
        if witness_character not in entry.witnesses:
            entry.witnesses.append(witness_character)
        entry.witness_events.append(event)

        # Determine new state
        entry.state = self._compute_state(entry)

        # Propagate to other characters
        propagated = self._propagate(cannabis_symbol, witness_character, entry)
        event.propagated_to = propagated

        self._session_events.append(event)
        return event

    def _compute_state(self, entry: CannabisEntry) -> WitnessState:
        """Compute current witness state based on witnesses and map."""
        if entry.deliberate:
            all_chars = set(self._perspectival.keys())
            if all_chars and all_chars.issubset(set(entry.witnesses)):
                return WitnessState.WITNESSED
            if entry.witnesses:
                return WitnessState.PARTIAL
            return WitnessState.FRONTIER

        all_chars = set(self._perspectival.keys())
        if not all_chars:
            return WitnessState.WITNESSED if entry.witnesses else WitnessState.UNWITNESSED

        if all_chars.issubset(set(entry.witnesses)):
            return WitnessState.WITNESSED
        if entry.witnesses:
            return WitnessState.PARTIAL
        return WitnessState.UNWITNESSED

    def _propagation_weight(self, entry: CannabisEntry) -> float:
        """Get propagation likelihood from relevance declaration geometry."""
        if entry.relevance_decl:
            geo = entry.relevance_decl.geometry
            return geo.get(
                "propagation_likelihood",
                geo.get("strength",
                geo.get("convergence", 0.5))
            )
        return 0.7  # default: moderate propagation

    def _propagate(
        self,
        cannabis_symbol: str,
        source_character: str,
        entry: CannabisEntry,
    ) -> List[str]:
        """
        Propagate a witness event to other characters sharing this entry,
        subject to perspectival limits and topological geometry.
        """
        propagated = []
        weight = self._propagation_weight(entry)

        for char_id, perspectival in self._perspectival.items():
            if char_id == source_character:
                continue
            if cannabis_symbol not in perspectival.accessible_entries:
                continue
            effective_weight = weight * perspectival.perspectival_limit
            if effective_weight >= 0.5 and char_id not in entry.witnesses:
                entry.witnesses.append(char_id)
                propagated.append(char_id)

        if propagated:
            entry.state = self._compute_state(entry)

        return propagated

    # ------------------------------------------------------------------
    # TaShyMa firing
    # ------------------------------------------------------------------

    def fire_taShyMa(self, temporal_address: int) -> List[SoaArtifact]:
        """
        Fire the TaShyMa temporal closure.

        Converts all unresolved Cannabis entries to Soa artifacts,
        adds them to the Soa ledger, and returns the new artifacts.
        """
        new_soa: List[SoaArtifact] = []
        samosmyr_id = self._current_samosmyr or "unknown"

        for sym, entry in self._entries.items():
            if entry.state not in (WitnessState.WITNESSED,):
                # Make gate decision if relevance declaration exists
                gate_result = None
                if entry.relevance_decl:
                    gate_result = gate_decision(
                        entry.relevance_decl,
                        witness_state=entry.state.value,
                    )

                artifact = SoaArtifact(
                    cannabis_symbol=sym,
                    samosmyr_id=samosmyr_id,
                    temporal_address=temporal_address,
                    partial_witnesses=list(entry.witnesses),
                    relevance_decl=entry.relevance_decl,
                    gate_result=gate_result,
                )
                entry.state = WitnessState.SOA
                entry.soa_artifact = artifact
                new_soa.append(artifact)
                self._soa_ledger.append(artifact)

        return new_soa

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self, cannabis_symbol: str) -> WitnessState:
        """Get current witness state for a Cannabis entry."""
        entry = self._entries.get(cannabis_symbol)
        return entry.state if entry else WitnessState.UNWITNESSED

    def get_all_states(self) -> Dict[str, WitnessState]:
        """Return full witness state vector."""
        return {sym: entry.state for sym, entry in self._entries.items()}

    def get_soa_ledger(self) -> List[SoaArtifact]:
        """Return all Soa artifacts accumulated across SamosMyr."""
        return list(self._soa_ledger)

    def get_coherence_summary(self) -> Dict[str, Any]:
        """
        Return a summary of current coherence state.
        Consumed by scene_to_bilingual_trust() and the renderer.
        """
        states = self.get_all_states()
        total = len(states)
        witnessed = sum(1 for s in states.values() if s == WitnessState.WITNESSED)
        partial = sum(1 for s in states.values() if s == WitnessState.PARTIAL)
        frontier = sum(1 for s in states.values() if s in (
            WitnessState.FRONTIER, WitnessState.UNWITNESSED
        ))
        soa_count = sum(1 for s in states.values() if s == WitnessState.SOA)

        coherence_grade = witnessed / total if total > 0 else 1.0

        return {
            "total_cannabis_entries": total,
            "witnessed":    witnessed,
            "partial":      partial,
            "frontier":     frontier,
            "soa":          soa_count,
            "coherence_grade": round(coherence_grade, 3),
            "trust_grade":  "attested" if coherence_grade >= 0.8 else "frontier",
            "authority_level": "resolved" if frontier == 0 else "unknown",
            "entry_path":   list(self._entry_path),
            "cut_character": "resolved" if coherence_grade >= 0.8 else "frontier",
        }

    def get_character_coherence(self, character_id: str) -> Dict[str, Any]:
        """
        Return coherence state for a specific character —
        which of their accessible Cannabis entries are resolved.
        """
        perspectival = self._perspectival.get(character_id)
        if not perspectival:
            return {"character_id": character_id, "accessible": 0, "witnessed": 0}

        accessible = perspectival.accessible_entries
        witnessed = sum(
            1 for sym in accessible
            if self._entries.get(sym, CannabisEntry(sym)).state == WitnessState.WITNESSED
        )
        return {
            "character_id":     character_id,
            "accessible":       len(accessible),
            "witnessed":        witnessed,
            "coherence_grade":  round(witnessed / len(accessible), 3) if accessible else 1.0,
            "perspectival_limit": perspectival.perspectival_limit,
        }

    def dialogue_availability(self, character_id: str) -> Dict[str, Any]:
        """
        Return dialogue containment logic state for a character.
        Consumed by the dialogue system to determine which dialogue
        options are available.

        A character speaks differently based on which of their Cannabis
        entries are currently witnessed vs unwitnessed.
        """
        perspectival = self._perspectival.get(character_id)
        if not perspectival:
            return {"character_id": character_id, "mode": "unconstrained"}

        accessible = perspectival.accessible_entries
        witnessed_entries = {
            sym for sym in accessible
            if self._entries.get(sym, CannabisEntry(sym)).state == WitnessState.WITNESSED
        }
        unwitnessed_entries = accessible - witnessed_entries
        partial_entries = {
            sym for sym in accessible
            if self._entries.get(sym, CannabisEntry(sym)).state == WitnessState.PARTIAL
        }

        if not unwitnessed_entries and not partial_entries:
            mode = "full"
        elif witnessed_entries:
            mode = "partial"
        else:
            mode = "minimal"

        return {
            "character_id":       character_id,
            "mode":               mode,
            "witnessed_entries":  list(witnessed_entries),
            "unwitnessed_entries": list(unwitnessed_entries),
            "partial_entries":    list(partial_entries),
            "action_space":       "wide" if mode == "minimal" else "narrow" if mode == "full" else "medium",
        }

"""
qqva/world_state_7klgs.py
=========================
World state types and helpers for 7_KLGS — Ko's Labyrinth,
*An Alchemist's Labor of Love*.

The Hypatia disappearance is the central world-state event of Book 7.
Four enums describe the player's relationship to that event at any moment.
All four live in ``flags_json`` on ``PlayerState``; the keys are defined
as ``FLAG_*`` constants below so callers never hardcode strings.

Design constraint
-----------------
The veiled-speech system presents identical text to every player.
Nothing in this module stores, infers, or signals capability-tier reading.
Dialogue path routing is purely structural: required/blocked witness entries
only.  The system dispatches; Alexi authors.

World pseudo-quest
------------------
``select_path()`` in dialogue_runtime gates on a ``QuestState``'s witness
entries.  Because the Hypatia world state is not a quest in the ordinary
sense, we maintain a dedicated pseudo-quest
``"7KLGS_WORLD_HYPATIA"`` whose witness entries track world events.
It is stored in ``flags["hypatia.world_quest_state"]`` and
deserialised by ``world_quest_state_from_flags()``.

Witness entry IDs (use as ``required_witnesses`` / ``blocked_witnesses``
in DialoguePath declarations):

  ENTRY_HYPATIA_IS_DISAPPEARED  — witnessed at day-5-end trigger.
                                   Gates all post-disappearance NPC branches.
  ENTRY_LAB_IS_OPEN             — witnessed simultaneously with above.
                                   Gates lab-open flavour branches.
  ENTRY_LAB_IS_SEALED           — witnessed at day-35 (Saffron's seal).
                                   Gates post-seal NPC/world branches.

Pattern for NPC dialogue branching
-----------------------------------
Every NPC has two authored branch sets (Alexi's labor):

  Pre-disappearance paths:
    required_witnesses  = []
    blocked_witnesses   = [ENTRY_HYPATIA_IS_DISAPPEARED]
    priority            = 0   (baseline)

  Post-disappearance paths:
    required_witnesses  = [ENTRY_HYPATIA_IS_DISAPPEARED]
    blocked_witnesses   = []
    priority            = 10  (wins over baseline once witnessed)

Because ``_path_available()`` treats a missing entry_id as unwitnessed,
both sets degrade gracefully when the world quest state is absent.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from .quest_engine import WitnessEntry, QuestState, WitnessTracker


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HypatiaIntroductionState(str, Enum):
    """
    Whether and how the player met Hypatia before her disappearance.

    NOT_MET     — player has not yet met her (transient state, days 1–4).
    MET         — player met her within days 1–5 (Timeline A hunt).
    FORESTALLED — player elected not to meet her (Timeline B hunt).
                  Meeting becomes the endgame climax rather than the
                  inciting incident.  The hunt is activated through the
                  repurposed quest Destiny Calls with a different quest
                  giver and framing; same destination as Timeline A.
                  Branching evaluated at runtime from flags ("processed live").
    """
    NOT_MET     = "not_met"
    MET         = "met"
    FORESTALLED = "forestalled"


class HypatiaPresenceState(str, Enum):
    """
    Hypatia's physical presence state in the world.

    PRESENT     — in Castle Azoth, accessible to the player.
    DISAPPEARED — vanished after day 5 (off-camera, no scene at trigger).
                  Actual location: Royal Ring of Sulphera.
                  Institutional reading: deliberate flight or abduction —
                  ambiguity is preserved by Hypatia's own design.
    """
    PRESENT     = "present"
    DISAPPEARED = "disappeared"


class ApprenticeshipState(str, Enum):
    """
    The player's formal apprenticeship standing with Hypatia.

    NOT_STARTED         — intro incomplete; no formal standing yet.
    ACTIVE_WITH_HYPATIA — formal apprenticeship active; Hypatia present.
    ON_YOUR_OWN         — Hypatia disappeared; player operates without
                          supervision.  The world's response IS the
                          curriculum; the hunt is the spine of the remainder
                          of Book 7.
    """
    NOT_STARTED         = "not_started"
    ACTIVE_WITH_HYPATIA = "active_with_hypatia"
    ON_YOUR_OWN         = "on_your_own"


class LabAccessibility(str, Enum):
    """
    Accessibility of Hypatia's lab in Castle Azoth.

    GATED_BY_HYPATIA  — Hypatia present; lab access requires her presence.
    OPEN              — Hypatia gone; lab freely accessible (days 6–34).
                        Clue artifacts available to players who explore.
    SEALED_BY_SAFFRON — Day 35+; Saffron, Priestess of Lord Nexiott,
                        seals the lab.  Seal event format TBD by Alexi
                        (played scene vs. silent state change at door).
    """
    GATED_BY_HYPATIA  = "gated_by_hypatia"
    OPEN              = "open"
    SEALED_BY_SAFFRON = "sealed_by_saffron"


# ---------------------------------------------------------------------------
# Flag keys (flags_json on PlayerState)
# ---------------------------------------------------------------------------

FLAG_PRESENCE_STATE     = "hypatia.presence_state"
FLAG_INTRODUCTION_STATE = "hypatia.introduction_state"
FLAG_APPRENTICESHIP     = "hypatia.apprenticeship_state"
FLAG_LAB_ACCESSIBILITY  = "hypatia.lab_accessibility"
FLAG_DISAPPEARANCE_DAY  = "hypatia.disappearance_day"
FLAG_WORLD_QUEST_STATE  = "hypatia.world_quest_state"


# ---------------------------------------------------------------------------
# Timing constants
# ---------------------------------------------------------------------------

TICKS_PER_DAY:              int = 100
HYPATIA_DISAPPEARANCE_DAY:  int = 5
LAB_SEAL_DAY:               int = 35

HYPATIA_DISAPPEARANCE_TICK: int = HYPATIA_DISAPPEARANCE_DAY * TICKS_PER_DAY
LAB_SEAL_TICK:              int = LAB_SEAL_DAY * TICKS_PER_DAY

# Game event kind strings (matched in _apply_game_event).
EVENT_HYPATIA_DISAPPEARANCE: str = "hypatia.disappearance"
EVENT_HYPATIA_LAB_SEAL:      str = "hypatia.lab_seal"


# ---------------------------------------------------------------------------
# World pseudo-quest
# ---------------------------------------------------------------------------

WORLD_QUEST_ID: str = "7KLGS_WORLD_HYPATIA"
GAME_ID:        str = "7_KLGS"

# Witness entry IDs referenced in DialoguePath required/blocked_witnesses.
ENTRY_HYPATIA_IS_DISAPPEARED: str = "hypatia.is_disappeared"
ENTRY_LAB_IS_OPEN:            str = "hypatia.lab_is_open"
ENTRY_LAB_IS_SEALED:          str = "hypatia.lab_is_sealed"


def _make_entry(
    entry_id: str,
    label_a:  str,
    label_b:  str,
) -> WitnessEntry:
    return WitnessEntry(
        entry_id=entry_id,
        cannabis_symbol="",      # structural-only; not a Kobra Cannabis entry
        candidate_a_label=label_a,
        candidate_b_label=label_b,
        witness_state="unwitnessed",
        witnessed_candidate=None,
    )


def initial_world_quest_state() -> QuestState:
    """
    Build the initial world pseudo-QuestState for a new Game 7 session.
    All entries are unwitnessed: Hypatia present, lab gated.
    """
    tracker = WitnessTracker()
    return tracker.initial_state(
        quest_id=WORLD_QUEST_ID,
        game_id=GAME_ID,
        entries=[
            _make_entry(
                ENTRY_HYPATIA_IS_DISAPPEARED,
                "Hypatia remains in Castle Azoth",
                "Hypatia has vanished from Castle Azoth",
            ),
            _make_entry(
                ENTRY_LAB_IS_OPEN,
                "Lab gated by Hypatia's presence",
                "Lab accessible without Hypatia",
            ),
            _make_entry(
                ENTRY_LAB_IS_SEALED,
                "Lab accessible",
                "Lab sealed by Saffron, Priestess of Lord Nexiott",
            ),
        ],
    )


def apply_disappearance(state: QuestState) -> QuestState:
    """
    Advance the world pseudo-quest to reflect Hypatia's disappearance.
    Witnesses ENTRY_HYPATIA_IS_DISAPPEARED and ENTRY_LAB_IS_OPEN simultaneously.
    Returns a new QuestState; ``state`` is not mutated.
    """
    tracker = WitnessTracker()
    state = tracker.advance(state, {
        "event_type": "witness",
        "entry_id":   ENTRY_HYPATIA_IS_DISAPPEARED,
        "candidate":  "b",
    })
    state = tracker.advance(state, {
        "event_type": "witness",
        "entry_id":   ENTRY_LAB_IS_OPEN,
        "candidate":  "b",
    })
    return state


def apply_lab_seal(state: QuestState) -> QuestState:
    """
    Advance the world pseudo-quest to reflect Saffron's lab seal (day 35).
    Returns a new QuestState; ``state`` is not mutated.
    """
    tracker = WitnessTracker()
    return tracker.advance(state, {
        "event_type": "witness",
        "entry_id":   ENTRY_LAB_IS_SEALED,
        "candidate":  "b",
    })


def world_quest_state_from_flags(flags: Dict[str, object]) -> QuestState:
    """
    Deserialise the world pseudo-QuestState from a player's flags dict.
    Falls back to ``initial_world_quest_state()`` if the key is absent or
    the stored value is malformed — safe to call even on a fresh state.
    """
    raw = flags.get(FLAG_WORLD_QUEST_STATE)
    if not isinstance(raw, dict) or "entries" not in raw:
        return initial_world_quest_state()

    entries: Dict[str, WitnessEntry] = {}
    for eid, ev in (raw.get("entries") or {}).items():
        if isinstance(ev, dict):
            entries[str(eid)] = WitnessEntry(  # type: ignore[misc]
                entry_id=str(ev.get("entry_id", eid)),
                cannabis_symbol=str(ev.get("cannabis_symbol", "")),
                candidate_a_label=str(ev.get("candidate_a_label", "")),
                candidate_b_label=str(ev.get("candidate_b_label", "")),
                witness_state=str(ev.get("witness_state", "unwitnessed")),
                witnessed_candidate=ev.get("witnessed_candidate"),
            )

    return QuestState(
        quest_id=str(raw.get("quest_id", WORLD_QUEST_ID)),
        game_id=str(raw.get("game_id", GAME_ID)),
        entries=entries,
        soa_artifacts=list(raw.get("soa_artifacts") or []),
        current_frame=str(raw.get("current_frame", "frame_0")),
    )


# ---------------------------------------------------------------------------
# Flag initialisation helpers
# ---------------------------------------------------------------------------

def initial_hypatia_flags() -> Dict[str, object]:
    """
    Return the flag entries to merge into a fresh Game 7 player state.
    Call this once when the player's 7_KLGS state is first created.

    The world quest state is initialised here too so that
    ``world_quest_state_from_flags()`` always finds a well-formed value.
    """
    wqs = initial_world_quest_state()
    return {
        FLAG_PRESENCE_STATE:     HypatiaPresenceState.PRESENT.value,
        FLAG_INTRODUCTION_STATE: HypatiaIntroductionState.NOT_MET.value,
        FLAG_APPRENTICESHIP:     ApprenticeshipState.NOT_STARTED.value,
        FLAG_LAB_ACCESSIBILITY:  LabAccessibility.GATED_BY_HYPATIA.value,
        FLAG_DISAPPEARANCE_DAY:  None,
        FLAG_WORLD_QUEST_STATE:  _quest_state_to_dict(wqs),
    }


def flags_after_intro_met(flags: Dict[str, object]) -> Dict[str, object]:
    """
    Return a copy of ``flags`` updated to reflect a completed MET intro
    (player met Hypatia within days 1–5, Timeline A).
    """
    updated = dict(flags)
    updated[FLAG_INTRODUCTION_STATE] = HypatiaIntroductionState.MET.value
    updated[FLAG_APPRENTICESHIP]     = ApprenticeshipState.ACTIVE_WITH_HYPATIA.value
    return updated


def flags_after_intro_forestalled(flags: Dict[str, object]) -> Dict[str, object]:
    """
    Return a copy of ``flags`` updated to reflect a FORESTALLED intro
    (player elected not to meet Hypatia, Timeline B).
    Apprenticeship stays NOT_STARTED; the hunt activates via Destiny Calls.
    """
    updated = dict(flags)
    updated[FLAG_INTRODUCTION_STATE] = HypatiaIntroductionState.FORESTALLED.value
    updated[FLAG_APPRENTICESHIP]     = ApprenticeshipState.NOT_STARTED.value
    return updated


def flags_after_disappearance(
    flags:    Dict[str, object],
    day:      int = HYPATIA_DISAPPEARANCE_DAY,
) -> Dict[str, object]:
    """
    Return a copy of ``flags`` updated to reflect Hypatia's disappearance.
    Advances the world quest state entries for is_disappeared and lab_is_open.
    """
    updated = dict(flags)
    updated[FLAG_PRESENCE_STATE]    = HypatiaPresenceState.DISAPPEARED.value
    updated[FLAG_APPRENTICESHIP]    = ApprenticeshipState.ON_YOUR_OWN.value
    updated[FLAG_LAB_ACCESSIBILITY] = LabAccessibility.OPEN.value
    updated[FLAG_DISAPPEARANCE_DAY] = day

    wqs = world_quest_state_from_flags(flags)
    wqs = apply_disappearance(wqs)
    updated[FLAG_WORLD_QUEST_STATE] = _quest_state_to_dict(wqs)
    return updated


def flags_after_lab_seal(flags: Dict[str, object]) -> Dict[str, object]:
    """
    Return a copy of ``flags`` updated to reflect Saffron's day-35 lab seal.
    """
    updated = dict(flags)
    updated[FLAG_LAB_ACCESSIBILITY] = LabAccessibility.SEALED_BY_SAFFRON.value

    wqs = world_quest_state_from_flags(flags)
    wqs = apply_lab_seal(wqs)
    updated[FLAG_WORLD_QUEST_STATE] = _quest_state_to_dict(wqs)
    return updated


# ---------------------------------------------------------------------------
# State reader
# ---------------------------------------------------------------------------

def read_hypatia_state(flags: Dict[str, object]) -> Dict[str, object]:
    """
    Return a plain dict summarising the current Hypatia world state,
    suitable for API responses.
    """
    return {
        "presence_state":     str(flags.get(FLAG_PRESENCE_STATE,     HypatiaPresenceState.PRESENT.value)),
        "introduction_state": str(flags.get(FLAG_INTRODUCTION_STATE, HypatiaIntroductionState.NOT_MET.value)),
        "apprenticeship":     str(flags.get(FLAG_APPRENTICESHIP,     ApprenticeshipState.NOT_STARTED.value)),
        "lab_accessibility":  str(flags.get(FLAG_LAB_ACCESSIBILITY,  LabAccessibility.GATED_BY_HYPATIA.value)),
        "disappearance_day":  flags.get(FLAG_DISAPPEARANCE_DAY),
    }


# ---------------------------------------------------------------------------
# Day-event queue helpers
# ---------------------------------------------------------------------------

def disappearance_queue_entry(ticks_per_day: int = TICKS_PER_DAY) -> Dict[str, object]:
    """
    Return a serialisable event-queue entry for the day-5 disappearance trigger.
    Pass this into the ``event_queue`` field of ``clock`` at game-state init.
    """
    return {
        "event_id": "hypatia_disappearance_day5",
        "kind":     EVENT_HYPATIA_DISAPPEARANCE,
        "due_tick": HYPATIA_DISAPPEARANCE_DAY * ticks_per_day,
        "seq":      0,
        "payload":  {"day": HYPATIA_DISAPPEARANCE_DAY, "deterministic": True},
    }


def lab_seal_queue_entry(ticks_per_day: int = TICKS_PER_DAY) -> Dict[str, object]:
    """
    Return a serialisable event-queue entry for the day-35 lab seal.
    Pass this into the ``event_queue`` field of ``clock`` at game-state init.
    """
    return {
        "event_id": "hypatia_lab_seal_day35",
        "kind":     EVENT_HYPATIA_LAB_SEAL,
        "due_tick": LAB_SEAL_DAY * ticks_per_day,
        "seq":      1,
        "payload":  {"day": LAB_SEAL_DAY, "agent": "saffron"},
    }


# ---------------------------------------------------------------------------
# Internal serialisation
# ---------------------------------------------------------------------------

def _quest_state_to_dict(state: QuestState) -> Dict[str, object]:
    """Serialise a QuestState to a plain dict for JSON storage."""
    return {
        "quest_id":      state["quest_id"],
        "game_id":       state["game_id"],
        "current_frame": state["current_frame"],
        "soa_artifacts": list(state["soa_artifacts"]),
        "entries": {
            eid: {
                "entry_id":           e["entry_id"],
                "cannabis_symbol":    e["cannabis_symbol"],
                "candidate_a_label":  e["candidate_a_label"],
                "candidate_b_label":  e["candidate_b_label"],
                "witness_state":      e["witness_state"],
                "witnessed_candidate": e["witnessed_candidate"],
            }
            for eid, e in state["entries"].items()
        },
    }
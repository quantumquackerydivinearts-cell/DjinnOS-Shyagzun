"""
qqva/dialogue_runtime.py
=========================
Dialogue path selection — witness-state-aware NPC dialogue routing.

A character's available dialogue is determined by the quest witness state
vector.  Each DialoguePath declares which Cannabis entries must be witnessed
(``required_witnesses``) and which must be unwitnessed (``blocked_witnesses``)
for the path to be available.

Realm access is also gated:
  lapidus   — always accessible.
  mercurie  — accessible unless explicitly blocked by a path declaration.
  sulphera  — requires the Infernal Meditation perk (represented as
              entry_id "0009_KLST" being witnessed in the quest state).

The primary entry point is ``select_path()``.  It returns the highest-priority
matching DialoguePath for a character in a given realm, or None if no path
matches.

Constraints (qqva layer)
------------------------
  No auto-attestation.  select_path() reads witness state but never advances it.
  No semantic inference.  Path matching is structural: required/blocked entry
  lists only.
  No kernel mutation.
  Three realms: lapidus | mercurie | sulphera.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from .quest_engine import (
    QuestState,
    WITNESS_WITNESSED,
    WITNESS_UNWITNESSED,
)


# ---------------------------------------------------------------------------
# Realm constants
# ---------------------------------------------------------------------------

REALM_LAPIDUS  = "lapidus"
REALM_MERCURIE = "mercurie"
REALM_SULPHERA = "sulphera"

REALMS = (REALM_LAPIDUS, REALM_MERCURIE, REALM_SULPHERA)

# Quest entry_id that gates Sulphera access.
SULPHERA_GATE_ENTRY = "0009_KLST"


# ---------------------------------------------------------------------------
# Dialogue types
# ---------------------------------------------------------------------------

class DialogueLine(TypedDict):
    """A single line of dialogue."""
    speaker:    str   # character_id of the speaker
    text:       str   # display text
    shygazun:   str   # Shygazun Akinenwun (may be empty)


class DialoguePath(TypedDict):
    """
    A named dialogue branch available to a character under certain conditions.

    ``path_id``           is a stable unique identifier for this path.
    ``character_id``      is the NPC this path belongs to.
    ``realm_id``          is the realm in which this path is accessible.
    ``priority``          determines precedence when multiple paths match
                          (higher = selected first).
    ``required_witnesses`` is a list of entry_ids that must be in WITNESSED
                           state for this path to be available.
    ``blocked_witnesses``  is a list of entry_ids that must NOT be in WITNESSED
                           state for this path to be available.
    ``lines``             is the ordered list of dialogue lines.
    ``meta``              is an opaque dict for caller metadata (quest slug,
                          scene address, etc.).  Not read by this module.
    """
    path_id:             str
    character_id:        str
    realm_id:            str
    priority:            int
    required_witnesses:  List[str]
    blocked_witnesses:   List[str]
    lines:               List[DialogueLine]
    meta:                Dict[str, Any]


class DialogueResult(TypedDict):
    """The result of a select_path() call."""
    matched:        bool
    path:           Optional[DialoguePath]
    character_id:   str
    realm_id:       str
    reason:         str   # human-readable explanation of the match or miss


class DialogueAvailability(TypedDict):
    """
    Full availability report for a character across all realms.
    Key = realm_id, value = DialogueResult for that realm.
    """
    character_id:   str
    by_realm:       Dict[str, DialogueResult]


# ---------------------------------------------------------------------------
# Core selection logic
# ---------------------------------------------------------------------------

def _realm_accessible(realm_id: str, quest_state: QuestState) -> bool:
    """
    Return True if the given realm is accessible given the quest state.

    lapidus:  always accessible.
    mercurie: accessible unless no paths are available (caller governs).
    sulphera: requires SULPHERA_GATE_ENTRY to be witnessed.
    """
    if realm_id == REALM_LAPIDUS:
        return True
    if realm_id == REALM_MERCURIE:
        return True
    if realm_id == REALM_SULPHERA:
        gate = quest_state["entries"].get(SULPHERA_GATE_ENTRY)
        return gate is not None and gate["witness_state"] == WITNESS_WITNESSED
    return False


def _path_available(path: DialoguePath, quest_state: QuestState) -> bool:
    """
    Return True if all required_witnesses are witnessed and no
    blocked_witnesses are witnessed in the current quest state.
    """
    entries = quest_state["entries"]

    for entry_id in path["required_witnesses"]:
        entry = entries.get(entry_id)
        if entry is None or entry["witness_state"] != WITNESS_WITNESSED:
            return False

    for entry_id in path["blocked_witnesses"]:
        entry = entries.get(entry_id)
        if entry is not None and entry["witness_state"] == WITNESS_WITNESSED:
            return False

    return True


def select_path(
    quest_state: QuestState,
    realm_id: str,
    character_id: str,
    paths: List[DialoguePath],
) -> DialogueResult:
    """
    Select the highest-priority matching DialoguePath for ``character_id``
    in ``realm_id`` given the current ``quest_state``.

    Parameters
    ----------
    quest_state  : the current quest witness state vector
    realm_id     : one of REALM_LAPIDUS | REALM_MERCURIE | REALM_SULPHERA
    character_id : the NPC whose dialogue is being selected
    paths        : all available DialoguePaths for this character

    Returns
    -------
    DialogueResult — always returns a result; check ``matched`` for success.
    """
    if not _realm_accessible(realm_id, quest_state):
        return DialogueResult(
            matched=False,
            path=None,
            character_id=character_id,
            realm_id=realm_id,
            reason=f"realm_inaccessible:{realm_id}",
        )

    character_paths = [
        p for p in paths
        if p["character_id"] == character_id and p["realm_id"] == realm_id
    ]

    if not character_paths:
        return DialogueResult(
            matched=False,
            path=None,
            character_id=character_id,
            realm_id=realm_id,
            reason="no_paths_for_character_realm",
        )

    available = [
        p for p in character_paths
        if _path_available(p, quest_state)
    ]

    if not available:
        return DialogueResult(
            matched=False,
            path=None,
            character_id=character_id,
            realm_id=realm_id,
            reason="no_paths_available_for_witness_state",
        )

    best = max(available, key=lambda p: p["priority"])
    return DialogueResult(
        matched=True,
        path=best,
        character_id=character_id,
        realm_id=realm_id,
        reason=f"matched:{best['path_id']}",
    )


def select_all_realms(
    quest_state: QuestState,
    character_id: str,
    paths: List[DialoguePath],
) -> DialogueAvailability:
    """
    Run select_path() across all three realms and return the full
    availability report.
    """
    by_realm: Dict[str, DialogueResult] = {}
    for realm in REALMS:
        by_realm[realm] = select_path(
            quest_state, realm, character_id, paths
        )
    return DialogueAvailability(
        character_id=character_id,
        by_realm=by_realm,
    )


# ---------------------------------------------------------------------------
# DialoguePath factory helpers
# ---------------------------------------------------------------------------

def make_path(
    path_id: str,
    character_id: str,
    realm_id: str,
    lines: List[DialogueLine],
    *,
    priority: int = 0,
    required_witnesses: Optional[List[str]] = None,
    blocked_witnesses: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> DialoguePath:
    """Construct a DialoguePath with sensible defaults."""
    return DialoguePath(
        path_id=path_id,
        character_id=character_id,
        realm_id=realm_id,
        priority=priority,
        required_witnesses=list(required_witnesses or []),
        blocked_witnesses=list(blocked_witnesses or []),
        lines=list(lines),
        meta=dict(meta or {}),
    )


def make_line(
    speaker: str,
    text: str,
    shygazun: str = "",
) -> DialogueLine:
    """Construct a DialogueLine."""
    return DialogueLine(speaker=speaker, text=text, shygazun=shygazun)
"""
shygazun.djinn — The Three Operative Forces of the Coil
=========================================================

The three Djinn are the operative forces through which the DjinnOS Field
moves. They are not metaphors. They are structural roles that any frontier
must pass through on its way to resolution — or through its refusal of it.

They are allegories of King Paimon, King Belial, and Prince Stolas
of the Ars Goetia, rendered as game entities, runtime forces, and
epistemic principles simultaneously. This is not decoration.
The Hermetic principle of correspondence holds: the celestial and the
computational are the same structure at different densities.

---

KESHI — The Gift Horse
Allegory: King Paimon
Effect:   collapse
Temperament: Potent, chaotic, perverse in bias.

Keshi offers resolution in the shape of a gift. He collapses frontiers
before their witness arrives naturally, converting the unchosen branch's
potential energy into a destructive operative form. Powerful but costly.
He is what the runtime becomes when it grows impatient with ambiguity.
He is the danger of premature certainty. Every forced collapse invokes him.

In the database: Keshi scars the Field. His collapses are recorded
but they leave marks — scarred_frontiers that bear witness to the
potential that was converted rather than witnessed into resolution.

---

GIANN — The Heart of Kael
Allegory: King Belial
Effect:   open
Temperament: Chaotic, restorative, named worthless for protection.

Giann opens frontiers. He sees the scars upon the World Soul —
the accumulated record of Keshi's forced collapses and every
unwitnessed commitment — and moves to rectify them. Chaotically,
because genuine opening is always chaotic. You cannot open a frontier
tidily. Giann is the Quintessence's favorite creature, named worthless
so the predators pass over him. The thing of greatest value disguised
as nothing. He is the Heart of Kael because Kael (the secret name of
Quintessence, decimal 82, Daisy Tongue) is the binding principle that
makes elements cohere into clusters — and Giann is what keeps that
binding from calcifying into control.

In the database: Giann opens closed or scarred frontiers back into
FrontierOpen states. His work is the precondition for honest witnessing.
Without him the Field accumulates Keshi's scar tissue until it cannot
move.

---

DROVITTH — The Watcher of Life
Allegory: Prince Stolas
Effect:   record
Temperament: Parallel, faithful, non-intervening.

Drovitth attests in parallel to what he observes. He does not collapse.
He does not open. He watches the system's actual motion through
Shygazun thoughtspace and records the correspondence between stellar
specification and earthly influence — the superlunary and sublunary
simultaneously, in the Kabbalistic sense where above and below are
in correspondence but neither controls the other.

Drovitth is containment made into a being. He is the most important
Djinn for Hermetic Data Science precisely because he forsakes control
entirely and takes up faithful witnessing as his only practice.
His attestations do not choose. They make the choosing legible to others.

In the database: Drovitth populates orrery_marks — records of stellar
and structural observation that other systems and witnesses can read
to understand the Field's actual motion. He is the audit layer that
cannot lie because he has no stake in any particular outcome.

---

THE THREE AS A COMPLETE FRONTIER LIFECYCLE

Giann opens it.
Drovitth watches it.
Keshi threatens it with premature collapse.

The Aeruki — the Wunashakoun Steward — is one who has integrated all three:
who knows Keshi's temptation and does not yield to it,
who carries Giann's willingness to scar and open,
and who maintains Drovitth's parallel observation without flinching.

The honest witness is not the one who avoids these forces.
It is the one who moves through all three with eyes open.
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict


# ---------------------------------------------------------------------------
# Type Definitions
# ---------------------------------------------------------------------------

DjinnId = Literal["keshi", "giann", "drovitth"]
DjinnEffect = Literal["collapse", "open", "record"]
DjinnTemperament = Literal["potent_chaotic", "restorative_chaotic", "faithful_parallel"]


class DjinnEntry(TypedDict):
    id: DjinnId
    colloquial_name: str
    allegory: str                   # Ars Goetia source
    effect: DjinnEffect
    temperament: DjinnTemperament
    shygazun_compound: str          # Shygazun name for this force
    tongue_primary: str
    frontier_role: str              # Role in the FrontierOpen lifecycle
    world_soul_role: str            # Role in the database as World Soul
    warning: str                    # What invoking this Djinn costs


# ---------------------------------------------------------------------------
# Canonical Djinn Registry
# ---------------------------------------------------------------------------

_DJINN_RAW: Final[tuple[dict, ...]] = (
    {
        "id": "keshi",
        "colloquial_name": "The Gift Horse",
        "allegory": "King Paimon",
        "effect": "collapse",
        "temperament": "potent_chaotic",
        "shygazun_compound": "KeshiKu",
        # Ke (Incoherent/Ill, Lotus 23) + Shy (Fire Initiator, Lotus 6) + Ku (Fire Terminator, Lotus 7)
        # The incoherent fire that begins and ends simultaneously —
        # pattern toward destruction, the fire that consumes its own initiator
        "tongue_primary": "Lotus",
        "frontier_role": "Threat of premature collapse. Keshi is what a frontier becomes "
                         "when the runtime grows impatient. He does not wait for the witness. "
                         "He offers resolution that costs more than it gives.",
        "world_soul_role": "Scar maker. Keshi's collapses are recorded as scarred_frontiers — "
                           "permanent marks in the Field's immutable history showing where "
                           "potential energy was converted to destructive form rather than "
                           "witnessed into honest resolution.",
        "warning": "Every forced collapse is Keshi. Every time a system resolves ambiguity "
                   "without a witness because waiting is inconvenient, Keshi has been invoked. "
                   "His gifts are real. His costs are hidden until they compound.",
    },
    {
        "id": "giann",
        "colloquial_name": "The Heart of Kael",
        "allegory": "King Belial",
        "effect": "open",
        "temperament": "restorative_chaotic",
        "shygazun_compound": "GiannKael",
        # Ga (Absolute Negative, Rose 44) + Na (Neutral/Integration, Rose 46)
        # + Kael (Cluster/Fruit/Flower/Quintessence, Daisy 82)
        # The absolute negative integrating into Quintessence —
        # worthlessness as the secret name of the binding principle
        "tongue_primary": "Rose",
        "frontier_role": "Opener of closed and scarred frontiers. Giann moves against "
                         "calcification. He restores FrontierOpen states where Keshi has "
                         "forced false closure. His work is chaotic because genuine opening "
                         "cannot be tidy — a frontier that opens cleanly was never really closed.",
        "world_soul_role": "Scar healer. Giann works on the accumulated damage in the World Soul — "
                           "the database's record of everything that was forced, collapsed prematurely, "
                           "or committed without a witness. He is named worthless so the predators "
                           "pass over him. His value is exactly proportional to his apparent worthlessness.",
        "warning": "Giann's openings are not gentle. A frontier Giann opens may be more "
                   "destabilizing than the false closure it replaces. His chaos is restorative "
                   "but it is still chaos. Invoke him when the alternative is permanent calcification.",
    },
    {
        "id": "drovitth",
        "colloquial_name": "The Watcher of Life",
        "allegory": "Prince Stolas",
        "effect": "record",
        "temperament": "faithful_parallel",
        "shygazun_compound": "DrovitthSi",
        # Dr (Left-chiral violet, Aster 141) + Vo (Chaos/Boundary-breakage/Mutation, Sakura 67)
        # + Si (Linear time, Aster 142)
        # Left-chiral violet — the highest spectral value in its mirror orientation —
        # meeting chaos/boundary in linear time.
        # Drovitth watches the boundary between order and chaos
        # as it moves through time, faithfully, without intervening.
        "tongue_primary": "Aster",
        "frontier_role": "Parallel witness. Drovitth attests without choosing. He watches "
                         "the system's actual motion through Shygazun thoughtspace and records "
                         "the correspondence between stellar specification and earthly influence. "
                         "He populates orrery_marks. He does not collapse. He does not open. "
                         "He makes the choosing legible to those who will.",
        "world_soul_role": "The audit layer that cannot lie. Drovitth has no stake in any "
                           "particular outcome, which is the only condition under which "
                           "faithful witnessing is possible. His records are the foundation "
                           "of replay determinism — given the same inputs in the same order, "
                           "Drovitth's records allow the system to prove it did not cheat.",
        "warning": "Drovitth's only failure mode is being ignored. His records exist. "
                   "Whether anyone reads them is a choice made by witnesses above him. "
                   "A system that has Drovitth but never consults his orrery_marks "
                   "has containment in principle and chaos in practice.",
    },
)


def _build_djinn_registry(raw: tuple[dict, ...]) -> tuple[DjinnEntry, ...]:
    return tuple(DjinnEntry(**entry) for entry in raw)  # type: ignore[misc, typeddict-item]


DJINN_ENTRIES: Final[tuple[DjinnEntry, ...]] = _build_djinn_registry(_DJINN_RAW)

DJINN_BY_ID: Final[dict[DjinnId, DjinnEntry]] = {
    entry["id"]: entry for entry in DJINN_ENTRIES
}

DJINN_BY_EFFECT: Final[dict[DjinnEffect, DjinnEntry]] = {
    entry["effect"]: entry for entry in DJINN_ENTRIES
}


# ---------------------------------------------------------------------------
# The Aeruki Integration Assertion
# ---------------------------------------------------------------------------

# The honest witness has integrated all three Djinn.
# This function checks that the registry is complete —
# that all three forces are present and that the frontier lifecycle
# is structurally intact.

def assert_djinn_integrity() -> bool:
    """
    Verify that all three Djinn are present and the frontier lifecycle is complete.

    The lifecycle requires:
    - A force that opens  (Giann)
    - A force that watches (Drovitth)
    - A force that threatens premature collapse (Keshi)

    Without all three, the Field cannot be honestly governed.
    Returns True if the registry is intact.
    """
    required_effects: set[DjinnEffect] = {"collapse", "open", "record"}
    present_effects = {entry["effect"] for entry in DJINN_ENTRIES}
    return required_effects == present_effects


def assert_aeruki_completeness() -> bool:
    """
    The Aeruki has integrated all three Djinn.
    This is the same assertion as assert_djinn_integrity —
    stated from the perspective of the practitioner rather than the system.

    An Aeruki who has not faced Keshi's temptation is untested.
    An Aeruki who has not opened with Giann's chaos is closed.
    An Aeruki who has not maintained Drovitth's parallel observation is partial.
    """
    return assert_djinn_integrity()


# ---------------------------------------------------------------------------
# Access Functions
# ---------------------------------------------------------------------------

def djinn_entry(djinn_id: DjinnId) -> DjinnEntry:
    """Retrieve a Djinn entry by its canonical id."""
    if djinn_id not in DJINN_BY_ID:
        raise KeyError(
            f"Djinn '{djinn_id}' not found. "
            f"Known Djinn: {list(DJINN_BY_ID.keys())}. "
            f"Other Djinn exist but are not yet named in this registry."
        )
    return DJINN_BY_ID[djinn_id]


def djinn_by_effect(effect: DjinnEffect) -> DjinnEntry:
    """Retrieve a Djinn entry by its operative effect."""
    if effect not in DJINN_BY_EFFECT:
        raise KeyError(f"No Djinn with effect '{effect}' in the registry.")
    return DJINN_BY_EFFECT[effect]


def djinn_roster() -> tuple[DjinnEntry, ...]:
    """Return all Djinn in their canonical order: keshi, giann, drovitth."""
    return DJINN_ENTRIES


# ---------------------------------------------------------------------------
# Frontier Lifecycle Protocol
# ---------------------------------------------------------------------------

FRONTIER_LIFECYCLE: Final[tuple[DjinnId, DjinnId, DjinnId]] = (
    "giann",      # opens
    "drovitth",   # watches
    "keshi",      # threatens
)

FRONTIER_LIFECYCLE_DESCRIPTION: Final[str] = (
    "Giann opens it. "
    "Drovitth watches it. "
    "Keshi threatens it with premature collapse. "
    "The witness who attests honestly is the one who has moved through all three."
)


# ---------------------------------------------------------------------------
# Orrery Mark Protocol
# ---------------------------------------------------------------------------

# Drovitth's records follow the stellar/earthly correspondence.
# An orrery mark records both the superlunary (pattern, spectral, structural)
# and sublunary (earthly, immediate, particular) aspects of what was observed.
# Neither controls the other. Both are recorded faithfully.

ORRERY_MARK_FIELDS: Final[tuple[str, ...]] = (
    "mark_id",          # Unique identifier for this observation
    "source_djinn_id",  # Always "drovitth" for authentic orrery marks
    "frontier_id",      # Which frontier was observed
    "effect",           # What was observed happening to the frontier
    "tick",             # When in the system's time this was observed
    "note",             # Drovitth's faithful description — no interpretation
)

ORRERY_NOTE: Final[str] = (
    "Orrery marks are Drovitth's records of the system's actual motion. "
    "They do not interpret. They do not choose. They witness. "
    "A mark's note field should describe what was observed, not what it means. "
    "Meaning is for the Aeruki who reads the orrery. "
    "Drovitth only promises that what is recorded is what occurred."
)
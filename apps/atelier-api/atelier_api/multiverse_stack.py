"""
multiverse_stack.py

The body of Drovitth's Orrery.

Each player workspace IS their multiverse instance — one unified graph spanning
all 31 games.  The 31 games are the complete power set of the five existential
priors {Ha, Ga, Na, Ung, Wu} minus the empty set (2⁵ − 1 = 31).

The 12-layer lineage DB is the Orrery's memory:
  L0  raw_input       — verbatim player action recorded by the game
  L1  validated       — action passes game-rule validation
  L2  resolved        — prior relational context identified
  L3  pre_tick        — world state snapshot before consequence
  L4  tick_applied    — diff produced by the consequence
  L5  post_tick       — world state after consequence
  L6  compiled        — scene/cobra output reflecting new state
  L7  asset_resolved  — assets and sprites hydrated
  L8  signed          — kernel attestation (Shygazun)
  L9  broadcast       — Sulphera evaluates nonlocal affect, writes back
  L10 ack             — target games acknowledge Sulphera's write
  L11 archived        — permanent, immutable record

  L12 djinn.function.binding — executable consequences the Orrery can fire

Sulphera sits outside the timeline principle.  It never writes in the name of
a game — it always writes as actor_id="sulphera".  Games read what Sulphera
has written and treat it as if it were their own substrate.

GAME_REGISTRY
  Maps game slugs → prior_subset_key.  Fill in as each game is designed.
  The prior_subset_key is the cosmological identity: sorted prior names
  joined by "+", e.g. "Ha+Na+Wu".

PROPAGATION_RULES
  Maps (source_game_id, action_kind) → list of PropagationRule.
  Each rule defines:
    target_game   — which game Sulphera writes back into
    effect_kind   — edge_kind for the cross-game edge
    consequence   — callable(source_payload, stack_context) → dict
                    Returns the payload Sulphera writes as the consequence node.
  Aggregate rules additionally carry a condition callable that queries the
  L11 archive before firing.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from .models import LayerEdge, LayerEvent, LayerNode

# ── Layer names ───────────────────────────────────────────────────────────────
LAYER_NAMES = [
    "raw_input",      # 0
    "validated",      # 1
    "resolved",       # 2
    "pre_tick",       # 3
    "tick_applied",   # 4
    "post_tick",      # 5
    "compiled",       # 6
    "asset_resolved", # 7
    "signed",         # 8
    "broadcast",      # 9
    "ack",            # 10
    "archived",       # 11
]
LAYER_DJINN_BINDING = 12
LAYER_ARCHIVED      = 11

# ── VITRIOL stat system ───────────────────────────────────────────────────────
# The 7 player stats, each ruled by one of the 7 sin rulers of Sulphera.
# Secondary natures read in reverse order (Asmodeus → Lucifer) spell VITRIOL —
# the alchemical formula: Visita Interiora Terrae Rectificando Invenies Occultum Lapidem.
# Players don't level up. They rectify.
#
# Budget: 31 points total across 7 stats (matching the 31-game series).
# Range: 1–10 per stat. Stats are trainable by investment of perk points.
# Assignment: Ko's dream sequence at the start of each game (fresh each time).
#             Ohadame (Goddess of Past Life Memory) can surface past-life echoes
#             into Ko's dream when invoked by the player.
# Each game instance is a new body, a new timeline, a new life.

VITRIOL_STATS: dict[str, dict] = {
    "vitality":      {"initial": "V", "ruler": "Asmodeus",  "sin": "Lust",     "secondary": "Vitality"},
    "introspection": {"initial": "I", "ruler": "Satan",     "sin": "Wrath",    "secondary": "Introspection"},
    "reflectivity":  {"initial": "R", "ruler": "Belphegor", "sin": "Sloth",    "secondary": "Reflectivity"},
    "tactility":     {"initial": "T", "ruler": "Beelzebub", "sin": "Gluttony", "secondary": "Tactility"},
    "ingenuity":     {"initial": "I", "ruler": "Leviathan", "sin": "Envy",     "secondary": "Ingenuity"},
    "ostentation":   {"initial": "O", "ruler": "Mammon",    "sin": "Greed",    "secondary": "Ostentation"},
    "levity":        {"initial": "L", "ruler": "Lucifer",   "sin": "Pride",    "secondary": "Levity"},
}

VITRIOL_BUDGET    = 31   # Total points across 7 stats — equals the 31-game series
VITRIOL_STAT_MIN  = 1
VITRIOL_STAT_MAX  = 10
VITRIOL_STAT_KEYS = list(VITRIOL_STATS.keys())  # canonical order: V I R T I O L


# ── Void Wraith observation system ───────────────────────────────────────────
# Void Wraiths are information collection constants — almost Primordial, bound
# only by the conceptual presence of absence.  They observe three things:
#
#   KILL     — who the player has made absent
#   SILENCE  — what the player didn't say when speech was available
#   OMISSION — what the player repeatedly didn't do on purpose
#              (single absence = noise; pattern = signal; threshold configurable)
#
# The game engine pushes observations.  The Orrery reads them.
# The player may not know Void Wraiths exist until they reach the Orrery.

VOID_WRAITH_OBSERVATION_KINDS = {"kill", "silence", "omission"}
VOID_WRAITH_OMISSION_MIN_REPS = 3   # minimum opportunities before omission fires

# The three named Void Wraiths — each is a Knower of one register of absence.
# Almost Primordial, bound only by the conceptual presence of absence.
VOID_WRAITHS: dict[str, dict] = {
    "negaya": {
        "title":       "Knower of Bodies",
        "observes":    "kill",
        "domain":      "Physical absence — lives ended, bodies no longer occupying space",
    },
    "haldoro": {
        "title":       "Knower of Minds",
        "observes":    "silence",
        "domain":      "Mental absence — thought that chose not to become speech",
        "note":        "Canonical spelling: Haldoro NOT Haldboro",
    },
    "vios": {
        "title":       "Knower of Souls",
        "observes":    "omission",
        "domain":      "Soul-level absence — the repeated refusal that defines character",
    },
}

# Maps observation kind → the Wraith who records it
_WRAITH_BY_KIND: dict[str, str] = {
    v["observes"]: name for name, v in VOID_WRAITHS.items()
}


def validate_vitriol(stats: dict) -> list[str]:
    """
    Returns a list of validation errors for a VITRIOL stat assignment.
    Empty list = valid.
    """
    errors = []
    for key in VITRIOL_STAT_KEYS:
        if key not in stats:
            errors.append(f"missing stat: {key}")
            continue
        val = stats[key]
        if not isinstance(val, int):
            errors.append(f"{key} must be an integer, got {type(val).__name__}")
        elif val < VITRIOL_STAT_MIN or val > VITRIOL_STAT_MAX:
            errors.append(f"{key}={val} out of range [{VITRIOL_STAT_MIN}–{VITRIOL_STAT_MAX}]")
    total = sum(stats.get(k, 0) for k in VITRIOL_STAT_KEYS)
    if total != VITRIOL_BUDGET:
        errors.append(f"stat total is {total}, must be exactly {VITRIOL_BUDGET}")
    return errors
LAYER_BROADCAST     = 9
SULPHERA_ACTOR      = "sulphera"

# ── Game registry ─────────────────────────────────────────────────────────────
# Populated as each game is designed.  prior_subset_key = sorted priors joined
# by "+".  The 31 entries are the complete power set of {Ha, Ga, Na, Ung, Wu}.
GAME_REGISTRY: dict[str, str] = {
    # Slugs follow the format: {game_number}_KLGS
    # prior_subset_key = sorted prior names joined by "+" — fill in as each game is designed.
    # The 31 entries will be the complete power set of {Ha, Ga, Na, Ung, Wu}.
    "7_KLGS":  "",   # Ko's Labyrnth Game Set (prior subset TBD)
    # "1_KLGS":  "",  # Game 1  (prior subset TBD)
    # "5_KLGS":  "",  # Game 5  (prior subset TBD)
    # "8_KLGS":  "",  # Game 8 — Reign of Nobody (prior subset TBD)
    # "28_KLGS": "",  # Game 28 — The Legacy of Luminyx (prior subset TBD)
    # ... remaining 26 games added as designed
}

# ── Propagation rules ─────────────────────────────────────────────────────────
@dataclass
class PropagationRule:
    target_game: str
    effect_kind: str
    consequence: Callable[[dict, "OrreryContext"], dict]
    # Optional aggregate condition — if present, checked against L11 archive
    # before firing.  Receives the full OrreryContext.
    condition: Optional[Callable[["OrreryContext"], bool]] = None
    label: str = ""


def _luminyx_killed_consequence(source_payload: dict, ctx: "OrreryContext") -> dict:
    """
    Killing Luminyx in Game 7 selects a diminished timeline for her in Game 1.

    In Game 1 Luminyx is ALIVE and mortal — the player is the disembodied spirit
    who guides her, not the other way around.  She does not become a spirit until
    she dies in 1782, after which she guides the player through Games 2–6.

    A Game 7 kill selects a timeline where she enters Game 1 wounded in purpose —
    her disposition toward the player is more guarded, her starting position
    displaced from her sovereign threshold.
    """
    return {
        "constant": "luminyx",
        "timeline": "wounded_sovereign",
        "disposition_toward_player": "guarded",
        "starting_location": "the_outer_threshold",
        "note": (
            "Luminyx is alive and mortal in Game 1 across all timelines. "
            "Her Game 7 death selects a timeline where she begins Game 1 "
            "displaced and guarded — purpose diminished but not extinguished."
        ),
        "source_game": "7_KLGS",
        "source_action": source_payload.get("action_kind", ""),
    }


def _luminyx_spared_consequence(source_payload: dict, ctx: "OrreryContext") -> dict:
    """
    Sparing / saving Luminyx in Game 7 keeps her in her sovereign timeline.

    She enters Game 1 with full agency — alive, mortal, purposeful.
    The player (as disembodied spirit) guides her from a position of
    mutual recognition rather than compensatory grief.
    """
    return {
        "constant": "luminyx",
        "timeline": "sovereign",
        "disposition_toward_player": "purposeful",
        "starting_location": "the_luminous_threshold",
        "note": (
            "Luminyx is alive and mortal in Game 1. Sovereign timeline: "
            "she stands at her threshold with full purpose intact."
        ),
        "source_game": "7_KLGS",
        "source_action": source_payload.get("action_kind", ""),
    }


def _earth_saved_all_six_condition(ctx: "OrreryContext") -> bool:
    """
    Check whether Earth was saved across all 6 games preceding Game 7.
    Queries the L11 archive for 'earth.saved' archived nodes in each of the
    6 early game slugs.  Returns True only if all 6 are present.
    """
    required_games = ctx.early_game_slugs  # set by caller from GAME_REGISTRY
    if not required_games:
        return False
    found = set()
    for node in ctx.archived_nodes:
        pl = _load_payload(node.payload_json)
        if pl.get("event_kind") == "earth.saved" and node.game_id in required_games:
            found.add(node.game_id)
    return found >= required_games


def _hypatia_alliance_consequence(source_payload: dict, ctx: "OrreryContext") -> dict:
    return {
        "unlock": "hypatia_alliance_ending",
        "note": (
            "Earth was saved across all 6 early games.  Game 7's hidden ending "
            "is unlocked: ally with Alexandria Sophia Hypatia and establish "
            "sovereignty outside Castle Azoth's mechanism."
        ),
        "source": "sulphera.aggregate.earth_saved_all_six",
    }


def _saelith_difficulty_consequence(source_payload: dict, ctx: "OrreryContext") -> dict:
    """
    Saelith exists timelessly in Game 5's space-corporation infrastructure.
    She knows who has done what, where, and when across the series.
    This consequence tunes Game 5's difficulty silently based on the player's
    cross-game kill count and moral history.
    """
    kill_count = ctx.kill_count
    return {
        "constant": "saelith",
        "difficulty_modifier": _saelith_difficulty_modifier(kill_count),
        "saelith_awareness": "full",
        "note": (
            "Saelith silently adjusts the lesson difficulty of resisting the "
            "space empire based on the player's history.  She does not announce "
            "this knowledge unless the player meets Hypatia in Game 7 and asks."
        ),
        "kill_count_at_eval": kill_count,
    }


def _saelith_difficulty_modifier(kill_count: int) -> str:
    if kill_count == 0:
        return "easiest"   # Zero-kill run — Saelith yields
    if kill_count < 5:
        return "reduced"
    if kill_count < 20:
        return "standard"
    if kill_count < 50:
        return "hardened"
    return "sovereign_resistance"  # High kill count — the empire knows you


# Key: (source_game_id, action_kind)
PROPAGATION_RULES: dict[tuple[str, str], list[PropagationRule]] = {

    # ── Game 7 → Game 1: Luminyx timeline selection ───────────────────────────
    ("7_KLGS", "luminyx.killed"): [
        PropagationRule(
            target_game="1_KLGS",
            effect_kind="sulphera.nonlocal.affect",
            consequence=_luminyx_killed_consequence,
            label="luminyx_killed_in_7_klgs",
        ),
    ],
    ("7_KLGS", "luminyx.survived"): [
        PropagationRule(
            target_game="1_KLGS",
            effect_kind="sulphera.nonlocal.affect",
            consequence=_luminyx_spared_consequence,
            label="luminyx_sovereign_in_7_klgs",
        ),
    ],

    # ── Aggregate: Earth saved across Games 1-6 → Game 7 hidden ending ───────
    # Checked on every L9 broadcast from any early game.
    # The condition queries the full archive.
    ("__aggregate__", "earth.saved"): [
        PropagationRule(
            target_game="7_KLGS",
            effect_kind="sulphera.aggregate.unlock",
            consequence=_hypatia_alliance_consequence,
            condition=_earth_saved_all_six_condition,
            label="earth_saved_all_six_hypatia_unlock",
        ),
    ],

    # ── Game 7 → Game 5: Saelith silent tuning ────────────────────────────────
    # Any significant action in Game 7 re-evaluates Saelith's difficulty model.
    ("7_KLGS", "player.action.significant"): [
        PropagationRule(
            target_game="5_KLGS",
            effect_kind="sulphera.silent_tune",
            consequence=_saelith_difficulty_consequence,
            label="saelith_difficulty_retune",
        ),
    ],
}


# ── Orrery context ─────────────────────────────────────────────────────────────
@dataclass
class OrreryContext:
    """Snapshot of the player's multiverse state — passed to consequence fns."""
    workspace_id: str
    archived_nodes: list[LayerNode] = field(default_factory=list)
    kill_count: int = 0
    early_game_slugs: set[str] = field(default_factory=set)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _uuid() -> str:
    return str(uuid.uuid4())


def _canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_payload(payload_json: str) -> dict:
    try:
        return json.loads(payload_json or "{}")
    except Exception:
        return {}


def _make_node(
    workspace_id: str,
    layer_index: int,
    node_key: str,
    payload: dict,
    game_id: str | None = None,
    prior_subset_key: str | None = None,
) -> LayerNode:
    payload_json = json.dumps(payload, sort_keys=True)
    return LayerNode(
        id=_uuid(),
        workspace_id=workspace_id,
        layer_index=layer_index,
        node_key=node_key,
        payload_json=payload_json,
        payload_hash=_canonical_hash(payload),
        game_id=game_id,
        prior_subset_key=prior_subset_key,
        created_at=datetime.utcnow(),
    )


def _make_edge(
    workspace_id: str,
    from_id: str,
    to_id: str,
    edge_kind: str,
    metadata: dict | None = None,
) -> LayerEdge:
    return LayerEdge(
        id=_uuid(),
        workspace_id=workspace_id,
        from_node_id=from_id,
        to_node_id=to_id,
        edge_kind=edge_kind,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
        created_at=datetime.utcnow(),
    )


def _make_event(
    workspace_id: str,
    event_kind: str,
    actor_id: str,
    payload: dict,
    node_id: str | None = None,
    edge_id: str | None = None,
) -> LayerEvent:
    return LayerEvent(
        id=_uuid(),
        workspace_id=workspace_id,
        event_kind=event_kind,
        actor_id=actor_id,
        node_id=node_id,
        edge_id=edge_id,
        payload_hash=_canonical_hash(payload),
        created_at=datetime.utcnow(),
    )


# ── MultiverseStackService ────────────────────────────────────────────────────
class MultiverseStackService:
    """
    The service layer for Drovitth's Orrery.

    Usage:
        svc = MultiverseStackService(db)
        archived = svc.record_and_archive(
            workspace_id="...",
            game_id="_KLGS",
            action_kind="luminyx.killed",
            actor_id="player::uuid",
            payload={"scene": "throne_room", "tick": 142},
        )
        # Sulphera propagation fires automatically inside record_and_archive.
    """

    def __init__(self, db: Session):
        self._db = db

    # ── Public API ────────────────────────────────────────────────────────────

    def assign_vitriol(
        self,
        workspace_id: str,
        game_id: str,
        actor_id: str,
        stats: dict,
        invoked_ohadame: bool = False,
    ) -> LayerNode:
        """
        Record a VITRIOL stat assignment from Ko's dream sequence.
        Each game instance is a new body, a new timeline, a new life —
        stats are fresh per game and are not carried forward automatically.

        invoked_ohadame: whether the player called on the Goddess of Past Life Memory
        to surface echoes of previous incarnations into Ko's dream.

        Returns the L11 archived node for this assignment.
        """
        errors = validate_vitriol(stats)
        if errors:
            raise ValueError(f"Invalid VITRIOL assignment: {'; '.join(errors)}")

        payload = {
            "action_kind": "vitriol.assigned",
            "actor_id": actor_id,
            "game_id": game_id,
            "stats": stats,
            "invoked_ohadame": invoked_ohadame,
            "total": sum(stats.values()),
            # The sin that rules each assigned value — for Orrery legibility
            "ruled_by": {
                key: VITRIOL_STATS[key]["ruler"]
                for key in VITRIOL_STAT_KEYS
            },
        }

        return self.record_and_archive(
            workspace_id=workspace_id,
            game_id=game_id,
            action_kind="vitriol.assigned",
            actor_id=actor_id,
            payload=payload,
        )

    def record_void_wraith_observation(
        self,
        workspace_id: str,
        game_id: str,
        observation_kind: str,
        subject: str,
        context: dict | None = None,
    ) -> LayerNode:
        """
        Record a Void Wraith observation.

        observation_kind — one of: "kill", "silence", "omission"
        subject          — what was killed / not said / not done
                           e.g. "npc::luminyx", "dialogue::offer_peace", "action::spare_enemy"
        context          — optional game-specific metadata (scene, tick, opportunity_count, etc.)

        The game engine is responsible for detecting omission patterns before calling this.
        A `void_wraith.omission` should only fire once the repetition threshold is met.
        """
        if observation_kind not in VOID_WRAITH_OBSERVATION_KINDS:
            raise ValueError(
                f"Unknown observation kind '{observation_kind}'. "
                f"Must be one of: {VOID_WRAITH_OBSERVATION_KINDS}"
            )
        wraith_name = _WRAITH_BY_KIND[observation_kind]
        wraith      = VOID_WRAITHS[wraith_name]
        return self.record_and_archive(
            workspace_id=workspace_id,
            game_id=game_id,
            action_kind=f"void_wraith.{observation_kind}",
            actor_id=wraith_name,   # negaya | haldoro | vios
            payload={
                "observation_kind": observation_kind,
                "wraith":  wraith_name,
                "title":   wraith["title"],
                "subject": subject,
                "context": context or {},
            },
        )

    def void_wraith_profile(self, workspace_id: str, game_id: str | None = None) -> dict:
        """
        Return the full Void Wraith profile for a player — everything the Wraiths
        have observed: kills, silences, and omission patterns.
        Optionally scoped to a specific game.
        """
        from sqlalchemy import select

        q = select(LayerNode).where(
            LayerNode.workspace_id == workspace_id,
            LayerNode.layer_index == LAYER_ARCHIVED,
        )
        if game_id:
            q = q.where(LayerNode.game_id == game_id)

        kills     : list[dict] = []
        silences  : list[dict] = []
        omissions : list[dict] = []

        for node in self._db.scalars(q).all():
            pl = _load_payload(node.payload_json)
            kind = pl.get("action_kind", "")
            if kind == "void_wraith.kill":
                kills.append({"subject": pl.get("subject"), "game_id": node.game_id,
                               "context": pl.get("context", {}), "at": node.created_at.isoformat() if node.created_at else None})
            elif kind == "void_wraith.silence":
                silences.append({"subject": pl.get("subject"), "game_id": node.game_id,
                                  "context": pl.get("context", {})})
            elif kind == "void_wraith.omission":
                omissions.append({"subject": pl.get("subject"), "game_id": node.game_id,
                                   "context": pl.get("context", {})})

        return {
            "workspace_id": workspace_id,
            "game_id_filter": game_id,
            # By Wraith name for Orrery legibility
            "negaya":  {"title": "Knower of Bodies",  "observations": kills,     "count": len(kills)},
            "haldoro": {"title": "Knower of Minds",   "observations": silences,  "count": len(silences)},
            "vios":    {"title": "Knower of Souls",   "observations": omissions, "count": len(omissions)},
            # Flat counts for convenience
            "kill_count":     len(kills),
            "silence_count":  len(silences),
            "omission_count": len(omissions),
            "total_observed": len(kills) + len(silences) + len(omissions),
        }

    def get_vitriol(self, workspace_id: str, game_id: str) -> dict | None:
        """
        Retrieve the most recent VITRIOL assignment for a specific game instance.
        Returns None if no assignment exists yet.
        """
        from sqlalchemy import select

        nodes = self._db.scalars(
            select(LayerNode)
            .where(
                LayerNode.workspace_id == workspace_id,
                LayerNode.game_id == game_id,
                LayerNode.layer_index == LAYER_ARCHIVED,
            )
            .order_by(LayerNode.created_at.desc())
        ).all()

        for node in nodes:
            pl = _load_payload(node.payload_json)
            if pl.get("action_kind") == "vitriol.assigned":
                return pl.get("stats")
        return None

    def record_and_archive(
        self,
        workspace_id: str,
        game_id: str,
        action_kind: str,
        actor_id: str,
        payload: dict,
    ) -> LayerNode:
        """
        Record a player action and walk it through all 12 layers to archive.
        Sulphera propagation is evaluated at L9 and consequences written back.
        Returns the L11 archived node.
        """
        prior_subset_key = GAME_REGISTRY.get(game_id)
        full_payload = {
            "action_kind": action_kind,
            "actor_id": actor_id,
            "game_id": game_id,
            **payload,
        }

        # L0 — raw input
        l0 = _make_node(
            workspace_id, 0,
            f"{game_id}::{action_kind}::raw",
            full_payload, game_id, prior_subset_key,
        )
        self._db.add(l0)
        self._db.add(_make_event(workspace_id, "layer.raw_input", actor_id, full_payload, node_id=l0.id))

        prev = l0
        # L1–L8: sequential processing layers
        for layer_idx, layer_name in enumerate(LAYER_NAMES[1:9], start=1):
            node = _make_node(
                workspace_id, layer_idx,
                f"{game_id}::{action_kind}::{layer_name}",
                {**full_payload, "layer": layer_name},
                game_id, prior_subset_key,
            )
            edge = _make_edge(workspace_id, prev.id, node.id, "state.transition")
            self._db.add(node)
            self._db.add(edge)
            prev = node

        # L9 — broadcast: Sulphera evaluates nonlocal affect
        broadcast_node = _make_node(
            workspace_id, LAYER_BROADCAST,
            f"{game_id}::{action_kind}::broadcast",
            {**full_payload, "layer": "broadcast"},
            game_id, prior_subset_key,
        )
        broadcast_edge = _make_edge(workspace_id, prev.id, broadcast_node.id, "state.transition")
        self._db.add(broadcast_node)
        self._db.add(broadcast_edge)

        # L10 — ack + Sulphera consequence nodes
        ctx = self._build_orrery_context(workspace_id)
        consequence_nodes = self._evaluate_and_propagate(
            workspace_id, game_id, action_kind, full_payload, broadcast_node, ctx,
        )

        ack_node = _make_node(
            workspace_id, 10,
            f"{game_id}::{action_kind}::ack",
            {
                **full_payload,
                "layer": "ack",
                "consequences": len(consequence_nodes),
            },
            game_id, prior_subset_key,
        )
        self._db.add(ack_node)
        self._db.add(_make_edge(workspace_id, broadcast_node.id, ack_node.id, "state.transition"))

        # L11 — archive
        archived_node = _make_node(
            workspace_id, LAYER_ARCHIVED,
            f"{game_id}::{action_kind}::archived",
            {**full_payload, "layer": "archived"},
            game_id, prior_subset_key,
        )
        self._db.add(archived_node)
        self._db.add(_make_edge(workspace_id, ack_node.id, archived_node.id, "state.transition"))
        self._db.add(_make_event(
            workspace_id, "layer.archived", actor_id, full_payload, node_id=archived_node.id,
        ))

        self._db.commit()
        self._db.refresh(archived_node)
        return archived_node

    def orrery_query(
        self,
        workspace_id: str,
        game_id: str | None = None,
        prior_subset_key: str | None = None,
        action_kind: str | None = None,
    ) -> dict:
        """
        Query the Orrery — returns the full archived state of the multiverse
        for this player, optionally filtered by game or prior subset.

        This is the view from Sulphera's Royal Ring through Drovitth's Orrery.
        """
        from sqlalchemy import select

        q = select(LayerNode).where(
            LayerNode.workspace_id == workspace_id,
            LayerNode.layer_index == LAYER_ARCHIVED,
        )
        if game_id:
            q = q.where(LayerNode.game_id == game_id)
        if prior_subset_key:
            q = q.where(LayerNode.prior_subset_key == prior_subset_key)

        nodes = self._db.scalars(q).all()

        # Parse payloads and group by game
        by_game: dict[str, list[dict]] = {}
        for n in nodes:
            pl = _load_payload(n.payload_json)
            if action_kind and pl.get("action_kind") != action_kind:
                continue
            gid = n.game_id or "__sulphera__"
            by_game.setdefault(gid, []).append({
                "id": n.id,
                "node_key": n.node_key,
                "action_kind": pl.get("action_kind"),
                "prior_subset_key": n.prior_subset_key,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "payload": pl,
            })

        ctx = self._build_orrery_context(workspace_id)

        return {
            "workspace_id": workspace_id,
            "queried_at": datetime.utcnow().isoformat(),
            "total_archived": len(nodes),
            "kill_count": ctx.kill_count,
            "zero_kill_run": ctx.kill_count == 0,
            "luminyx_timeline": self.luminyx_timeline(workspace_id),
            "by_game": by_game,
        }

    def luminyx_timeline(self, workspace_id: str) -> str:
        """
        Returns the currently selected Luminyx timeline for this player.
        Derived from the most recent Sulphera consequence node targeting Game 1.
        Defaults to 'sovereign' (she survives, full agency).
        """
        from sqlalchemy import select

        q = (
            select(LayerNode)
            .where(
                LayerNode.workspace_id == workspace_id,
                LayerNode.layer_index == LAYER_ARCHIVED,
                LayerNode.game_id == SULPHERA_ACTOR,
            )
            .order_by(LayerNode.created_at.desc())
        )
        for node in self._db.scalars(q).all():
            pl = _load_payload(node.payload_json)
            if pl.get("constant") == "luminyx" and "timeline" in pl:
                return pl["timeline"]
        return "sovereign"

    def zero_kill_check(self, workspace_id: str) -> bool:
        """True if the player has not killed anyone across the entire series."""
        return self._build_orrery_context(workspace_id).kill_count == 0

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_orrery_context(self, workspace_id: str) -> OrreryContext:
        from sqlalchemy import select

        archived = self._db.scalars(
            select(LayerNode).where(
                LayerNode.workspace_id == workspace_id,
                LayerNode.layer_index == LAYER_ARCHIVED,
            )
        ).all()

        # Kill count: both direct player kills and Void Wraith kill observations
        kill_count = sum(
            1 for n in archived
            if (
                _load_payload(n.payload_json).get("action_kind", "") in
                {"void_wraith.kill"} or
                (
                    _load_payload(n.payload_json).get("action_kind", "").endswith(".killed")
                    and n.game_id != SULPHERA_ACTOR
                )
            )
        )

        # Early game slugs are Games 1-6 (all registered slugs except _KLGS and later)
        early = {g for g in GAME_REGISTRY if g != "_KLGS"}

        return OrreryContext(
            workspace_id=workspace_id,
            archived_nodes=list(archived),
            kill_count=kill_count,
            early_game_slugs=early,
        )

    def _evaluate_and_propagate(
        self,
        workspace_id: str,
        game_id: str,
        action_kind: str,
        payload: dict,
        broadcast_node: LayerNode,
        ctx: OrreryContext,
    ) -> list[LayerNode]:
        """
        Evaluate all propagation rules for this action.
        Writes Sulphera consequence nodes back into the workspace.
        Returns the list of consequence nodes written.
        """
        consequence_nodes: list[LayerNode] = []

        rule_sets = [
            PROPAGATION_RULES.get((game_id, action_kind), []),
            PROPAGATION_RULES.get(("__aggregate__", action_kind), []),
        ]

        for rules in rule_sets:
            for rule in rules:
                # Check optional aggregate condition
                if rule.condition and not rule.condition(ctx):
                    continue

                consequence_payload = rule.consequence(payload, ctx)
                consequence_payload["_rule_label"] = rule.label
                consequence_payload["_source_game"] = game_id
                consequence_payload["_source_action"] = action_kind

                # Sulphera writes a consequence node into the target game's context
                node = _make_node(
                    workspace_id,
                    LAYER_ARCHIVED,
                    f"sulphera::{rule.label}::{rule.target_game}",
                    consequence_payload,
                    game_id=SULPHERA_ACTOR,
                    prior_subset_key=GAME_REGISTRY.get(rule.target_game),
                )
                edge = _make_edge(
                    workspace_id,
                    broadcast_node.id,
                    node.id,
                    rule.effect_kind,
                    metadata={
                        "rule": rule.label,
                        "source_game": game_id,
                        "target_game": rule.target_game,
                        "actor": SULPHERA_ACTOR,
                    },
                )
                event = _make_event(
                    workspace_id,
                    f"sulphera.affect.{rule.effect_kind}",
                    SULPHERA_ACTOR,
                    consequence_payload,
                    node_id=node.id,
                    edge_id=edge.id,
                )
                self._db.add(node)
                self._db.add(edge)
                self._db.add(event)
                consequence_nodes.append(node)

        return consequence_nodes

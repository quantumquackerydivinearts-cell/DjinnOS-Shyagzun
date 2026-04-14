"""
shygazun/kernel/registers.py

All eight Shygazun tongue registers.

Each register implements the RegisterPlugin protocol:
    admit()      — whether this register handles a given field/fragment
    propose()    — structural candidates this tongue contributes to a frontier
    constrain()  — passthrough (constraint application is the kernel's job)
    observe()    — passthrough (structural observation without inference)

Tongue ordering follows the byte table:
    Lotus        (0–23)    material/experiential ground
    Rose         (24–47)   vectors, numbers, Primordials
    Sakura       (48–71)   orientation, motion, relational quality
    Daisy        (72–97)   structural/mechanical engineering
    AppleBlossom (98–123)  alchemical elements and compounds
    Aster        (128–155) chiral spectrum, time types, space operations
    Grapevine    (156–183) networking, distribution, federation
    Cannabis     (184–213) cross-tongue awareness operators (tensor product)

Architectural constraints (non-negotiable):
    - No semantic inference; no auto-resolution
    - Lotus candidates require external attestation; kernel awaits, never resolves
    - Append-only; no deletion of events or edges
    - Ambiguity is first-class: multiple candidates coexist until attested
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, TypedDict

from .types.candidate import CandidateCompletion, Preconditions, PrioritySignature
from .types.frontier import Frontier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CandWeights(TypedDict, total=False):
    """Typed kwargs unpacked into _cand calls via **W. Never includes provenance — always explicit."""
    rw: float
    cw: float
    tail: List[str]


def _cand(
    id: str,
    *,
    forbids: List[str] | None = None,
    lotus_tag: str | None = None,
    rw: float = 1.0,
    cw: float = 1.0,
    tail: List[str] | None = None,
    provenance: List[Dict[str, str]] | None = None,
) -> CandidateCompletion:
    """Compact constructor for CandidateCompletion."""
    lotus_req: Dict[str, Any] | None = (
        {"kind": "await_attestation", "attestation_tag": lotus_tag}
        if lotus_tag is not None
        else None
    )
    return CandidateCompletion(
        id=id,
        preconditions=Preconditions(
            forbids_candidates=forbids or [],
            lotus_requirement=lotus_req,
        ),
        costs=[],
        effects={},
        priority_signature=PrioritySignature(
            relation_weight=rw,
            closure_weight=cw,
            tail_markers=tail or [],
        ),
        provenance=provenance or [{"source": id.split(".")[0], "kind": "tongue"}],
    )


def _sym(tongue: str, symbol: str, decimal: str, meaning: str) -> List[Dict[str, str]]:
    return [{"source": tongue, "symbol": symbol, "decimal": decimal, "meaning": meaning}]


class BaseRegister:
    name: str = "base"

    def admit(self, fragment: Mapping[str, Any], field: Any) -> Mapping[str, Any]:
        return {"admitted": True}

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        return []

    def constrain(
        self,
        field: Any,
        candidates: Sequence[CandidateCompletion],
        frontier: Frontier,
    ) -> Mapping[str, Any]:
        return {}

    def observe(self, field: Any, frontier: Frontier) -> List[Mapping[str, Any]]:
        return []


# ---------------------------------------------------------------------------
# Lotus (0–23)  —  Earth / material ground
# "Machines lack the embodied referents for Lotus.
#  They can process the symbols; they cannot supply the ground."
# All Lotus candidates require external attestation.
# ---------------------------------------------------------------------------

class LotusRegister(BaseRegister):
    """1st tongue: Material/experiential primitives."""

    name = "lotus"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "lotus"
        W: _CandWeights = _CandWeights(rw=0.8, cw=0.3, tail=["lotus", "material", "ground"])

        # --- Element initiator / terminator pairs ---
        # Each pair is mutually exclusive: opening forbids simultaneous closing.
        earth_open  = _cand(f"{T}.earth.open",  forbids=[f"{T}.earth.close"],
                            lotus_tag=f"{T}.earth.open",  **W,
                            provenance=_sym(T, "Ty", "0", "Earth Initiator / material beginning"))
        earth_close = _cand(f"{T}.earth.close", forbids=[f"{T}.earth.open"],
                            lotus_tag=f"{T}.earth.close", **W,
                            provenance=_sym(T, "Zu", "1", "Earth Terminator / empirical closure"))

        water_open  = _cand(f"{T}.water.open",  forbids=[f"{T}.water.close"],
                            lotus_tag=f"{T}.water.open",  **W,
                            provenance=_sym(T, "Ly", "2", "Water Initiator / feeling toward"))
        water_close = _cand(f"{T}.water.close", forbids=[f"{T}.water.open"],
                            lotus_tag=f"{T}.water.close", **W,
                            provenance=_sym(T, "Mu", "3", "Water Terminator / memory from"))

        air_open    = _cand(f"{T}.air.open",    forbids=[f"{T}.air.close"],
                            lotus_tag=f"{T}.air.open",    **W,
                            provenance=_sym(T, "Fy", "4", "Air Initiator / thought toward"))
        air_close   = _cand(f"{T}.air.close",   forbids=[f"{T}.air.open"],
                            lotus_tag=f"{T}.air.close",   **W,
                            provenance=_sym(T, "Pu", "5", "Air Terminator / stasis / stuck"))

        fire_open   = _cand(f"{T}.fire.open",   forbids=[f"{T}.fire.close"],
                            lotus_tag=f"{T}.fire.open",   **W,
                            provenance=_sym(T, "Shy", "6", "Fire Initiator / pattern toward"))
        fire_close  = _cand(f"{T}.fire.close",  forbids=[f"{T}.fire.open"],
                            lotus_tag=f"{T}.fire.close",  **W,
                            provenance=_sym(T, "Ku", "7", "Fire Terminator / death / end"))

        # --- Presence markers ---
        presence_here   = _cand(f"{T}.presence.here",   lotus_tag=f"{T}.presence.here",   **W,
                                provenance=_sym(T, "Ti", "8",  "Here / near presence"))
        presence_active = _cand(f"{T}.presence.active", forbids=[f"{T}.presence.absent"],
                                lotus_tag=f"{T}.presence.active", **W,
                                provenance=_sym(T, "Ta", "9",  "Active being / presence"))
        presence_there  = _cand(f"{T}.presence.there",  lotus_tag=f"{T}.presence.there",  **W,
                                provenance=_sym(T, "Ze", "20", "There / far"))
        presence_home   = _cand(f"{T}.presence.home",   lotus_tag=f"{T}.presence.home",   **W,
                                provenance=_sym(T, "Me", "21", "Familiar / home"))
        presence_absent = _cand(f"{T}.presence.absent", forbids=[f"{T}.presence.active"],
                                lotus_tag=f"{T}.presence.absent", **W,
                                provenance=_sym(T, "Zo", "16", "Absence / passive non-being"))

        # --- Quality markers (mutually exclusive pairs) ---
        quality_new        = _cand(f"{T}.quality.new",        forbids=[f"{T}.quality.old"],
                                   lotus_tag=f"{T}.quality.new",     **W,
                                   provenance=_sym(T, "Li", "10", "New / odd"))
        quality_old        = _cand(f"{T}.quality.old",        forbids=[f"{T}.quality.new"],
                                   lotus_tag=f"{T}.quality.old",     **W,
                                   provenance=_sym(T, "Fa", "13", "Complex / old"))
        quality_tense      = _cand(f"{T}.quality.tense",      forbids=[f"{T}.quality.relaxed"],
                                   lotus_tag=f"{T}.quality.tense",   **W,
                                   provenance=_sym(T, "La", "11", "Tense / excited"))
        quality_relaxed    = _cand(f"{T}.quality.relaxed",    forbids=[f"{T}.quality.tense"],
                                   lotus_tag=f"{T}.quality.relaxed", **W,
                                   provenance=_sym(T, "Mo", "17", "Relaxed / silent"))
        quality_known      = _cand(f"{T}.quality.known",      forbids=[f"{T}.quality.unknown"],
                                   lotus_tag=f"{T}.quality.known",   **W,
                                   provenance=_sym(T, "Fi", "12", "Known / context-sensitive"))
        quality_unknown    = _cand(f"{T}.quality.unknown",    forbids=[f"{T}.quality.known"],
                                   lotus_tag=f"{T}.quality.unknown", **W,
                                   provenance=_sym(T, "Pe", "22", "Unknown / insensitive"))
        quality_clear      = _cand(f"{T}.quality.clear",      forbids=[f"{T}.quality.incoherent"],
                                   lotus_tag=f"{T}.quality.clear",   **W,
                                   provenance=_sym(T, "Shi", "14", "Related / clear"))
        quality_incoherent = _cand(f"{T}.quality.incoherent", forbids=[f"{T}.quality.clear"],
                                   lotus_tag=f"{T}.quality.incoherent", **W,
                                   provenance=_sym(T, "Ke", "23", "Incoherent / ill"))

        # --- Singular quality markers ---
        quality_intellect  = _cand(f"{T}.quality.intellect",  lotus_tag=f"{T}.quality.intellect", **W,
                                   provenance=_sym(T, "Sha", "15", "Intellect of spirit"))
        quality_simple     = _cand(f"{T}.quality.simple",     lotus_tag=f"{T}.quality.simple",    **W,
                                   provenance=_sym(T, "Po", "18", "Simple / new"))
        quality_experience = _cand(f"{T}.quality.experience", lotus_tag=f"{T}.quality.experience", **W,
                                   provenance=_sym(T, "Ko", "19", "Experience / intuition"))

        return [
            earth_open, earth_close, water_open, water_close,
            air_open, air_close, fire_open, fire_close,
            presence_here, presence_active, presence_there, presence_home, presence_absent,
            quality_new, quality_old, quality_tense, quality_relaxed,
            quality_known, quality_unknown, quality_clear, quality_incoherent,
            quality_intellect, quality_simple, quality_experience,
        ]


# ---------------------------------------------------------------------------
# Rose (24–47)  —  Vectors, numbers, Primordials
# Rose is structurally determined: numbers and vectors are not experiential.
# Primordials (Ha/Ga/Wu/Na/Ung) are the foundational relational operators.
# ---------------------------------------------------------------------------

class RoseRegister(BaseRegister):
    """2nd tongue: Vectors, numbers, Primordials."""

    name = "rose"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "rose"
        W: _CandWeights = _CandWeights(rw=1.0, cw=1.0, tail=["rose", "vector", "number"])

        # --- Spectral vectors (mutually exclusive: one primary color per frontier) ---
        _colors = [
            ("red",    "Ru",    "24", "Vector Lowest Red"),
            ("orange", "Ot",    "25", "Vector Orange"),
            ("yellow", "El",    "26", "Vector Yellow"),
            ("green",  "Ki",    "27", "Vector Green"),
            ("blue",   "Fu",    "28", "Vector Blue"),
            ("indigo", "Ka",    "29", "Vector Indigo"),
            ("violet", "AE",    "30", "Vector Highest Violet"),
        ]
        all_vector_ids = [f"{T}.vector.{c}" for c, *_ in _colors]
        vectors = [
            _cand(f"{T}.vector.{color}",
                  forbids=[v for v in all_vector_ids if v != f"{T}.vector.{color}"],
                  **W,
                  provenance=_sym(T, sym, dec, meaning))
            for color, sym, dec, meaning in _colors
        ]

        # --- Numbers (mutually exclusive: one cardinality per frontier) ---
        _numbers = [
            ("zero",    "Gaoh",    "31", "Number 12 / 0"),
            ("one",     "Ao",      "32", "Number 1"),
            ("two",     "Ye",      "33", "Number 2"),
            ("three",   "Ui",      "34", "Number 3"),
            ("four",    "Shu",     "35", "Number 4"),
            ("five",    "Kiel",    "36", "Number 5"),
            ("six",     "Yeshu",   "37", "Number 6"),
            ("seven",   "Lao",     "38", "Number 7"),
            ("eight",   "Shushy",  "39", "Number 8"),
            ("nine",    "Uinshu",  "40", "Number 9"),
            ("ten",     "Kokiel",  "41", "Number 10"),
            ("eleven",  "Aonkiel", "42", "Number 11"),
        ]
        all_number_ids = [f"{T}.number.{n}" for n, *_ in _numbers]
        numbers = [
            _cand(f"{T}.number.{name}",
                  forbids=[n for n in all_number_ids if n != f"{T}.number.{name}"],
                  **W,
                  provenance=_sym(T, sym, dec, meaning))
            for name, sym, dec, meaning in _numbers
        ]

        # --- Primordials ---
        polarity_pos = _cand(f"{T}.polarity.positive", forbids=[f"{T}.polarity.negative"],
                             **W, provenance=_sym(T, "Ha", "43", "Absolute Positive"))
        polarity_neg = _cand(f"{T}.polarity.negative", forbids=[f"{T}.polarity.positive"],
                             **W, provenance=_sym(T, "Ga", "44", "Absolute Negative"))
        process_open = _cand(f"{T}.process.open",      **W,
                             provenance=_sym(T, "Wu", "45", "Process / Way"))
        integration  = _cand(f"{T}.integration.neutral", **W,
                             provenance=_sym(T, "Na", "46", "Neutral / Integration"))
        point_declare= _cand(f"{T}.point.declare",     **W,
                             provenance=_sym(T, "Ung", "47", "Piece / Point"))

        return (
            vectors
            + numbers
            + [polarity_pos, polarity_neg, process_open, integration, point_declare]
        )


# ---------------------------------------------------------------------------
# Sakura (48–71)  —  Orientation, motion, relational quality
# "Sakura — pure relational flux. First tongue to dissolve in dream."
# Orientation pairs are mutually exclusive. Death-moment requires lotus.
# ---------------------------------------------------------------------------

class SakuraRegister(BaseRegister):
    """3rd tongue: Orientation, motion, relational quality."""

    name = "sakura"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "sakura"
        W: _CandWeights = _CandWeights(rw=0.7, cw=0.4, tail=["sakura", "orientation", "motion"])

        # --- Orientation pairs (mutually exclusive on each axis) ---
        orient_top      = _cand(f"{T}.orient.top",      forbids=[f"{T}.orient.bottom"],
                                **W, provenance=_sym(T, "Jy", "48", "Top"))
        orient_bottom   = _cand(f"{T}.orient.bottom",   forbids=[f"{T}.orient.top"],
                                **W, provenance=_sym(T, "Ju", "53", "Bottom"))
        orient_starboard= _cand(f"{T}.orient.starboard",forbids=[f"{T}.orient.port"],
                                **W, provenance=_sym(T, "Ji", "49", "Starboard"))
        orient_port     = _cand(f"{T}.orient.port",     forbids=[f"{T}.orient.starboard"],
                                **W, provenance=_sym(T, "Je", "52", "Port"))
        orient_front    = _cand(f"{T}.orient.front",    forbids=[f"{T}.orient.back"],
                                **W, provenance=_sym(T, "Ja", "50", "Front"))
        orient_back     = _cand(f"{T}.orient.back",     forbids=[f"{T}.orient.front"],
                                **W, provenance=_sym(T, "Jo", "51", "Back"))

        # --- Motion / relational state ---
        motion_hence  = _cand(f"{T}.motion.hence",    **W, provenance=_sym(T, "Dy", "54", "Hence / Heretofore"))
        motion_travel = _cand(f"{T}.motion.travel",   forbids=[f"{T}.relation.stay"],
                              **W, provenance=_sym(T, "Di", "55", "Traveling / Distancing"))
        relation_meet = _cand(f"{T}.relation.meet",   forbids=[f"{T}.relation.part"],
                              **W, provenance=_sym(T, "Da", "56", "Meeting / Conjoined"))
        relation_part = _cand(f"{T}.relation.part",   forbids=[f"{T}.relation.meet"],
                              **W, provenance=_sym(T, "Do", "57", "Parting / Divorced"))
        relation_stay = _cand(f"{T}.relation.stay",   forbids=[f"{T}.motion.travel"],
                              **W, provenance=_sym(T, "De", "58", "Domesticating / Staying"))
        relation_status= _cand(f"{T}.relation.status",**W, provenance=_sym(T, "Du", "59", "Whither / Status of"))

        # --- Temporal quality ---
        time_eventual = _cand(f"{T}.time.eventual",   **W, provenance=_sym(T, "By", "60", "When-hence / Eventual"))

        # --- Relational quality markers ---
        quality_crowned   = _cand(f"{T}.quality.crowned",    **W, provenance=_sym(T, "Bi", "61", "Crowned / Owning"))
        quality_explicit  = _cand(f"{T}.quality.explicit",   forbids=[f"{T}.quality.hidden"],
                                  **W, provenance=_sym(T, "Ba", "62", "Plain / Explicit"))
        quality_hidden    = _cand(f"{T}.quality.hidden",     forbids=[f"{T}.quality.explicit"],
                                  **W, provenance=_sym(T, "Bo", "63", "Hidden / Occulted"))
        quality_common    = _cand(f"{T}.quality.common",     **W, provenance=_sym(T, "Be", "64", "Common / Outer / Wild"))
        quality_relational= _cand(f"{T}.quality.relational", **W, provenance=_sym(T, "Bu", "65", "Since / Relational"))

        # --- Order / Chaos (mutually exclusive) ---
        force_order = _cand(f"{T}.force.order", forbids=[f"{T}.force.chaos"],
                            **W, provenance=_sym(T, "Va", "66", "Order / Structure / Life"))
        force_chaos = _cand(f"{T}.force.chaos", forbids=[f"{T}.force.order"],
                            **W, provenance=_sym(T, "Vo", "67", "Chaos / Boundary-breakage / Mutation"))

        quality_scattered = _cand(f"{T}.quality.scattered", **W,
                                  provenance=_sym(T, "Ve", "68", "Pieces / Not-wherever / Where"))

        # --- Death-moment: requires lotus attestation ---
        moment_death = _cand(f"{T}.moment.death", lotus_tag=f"{T}.moment.death",
                             rw=0.9, cw=0.1, tail=["sakura", "death", "lotus-gated"],
                             provenance=_sym(T, "Vu", "69", "Death-moment / Never / Now"))

        quality_embodied = _cand(f"{T}.quality.embodied", **W,
                                 provenance=_sym(T, "Vi", "70", "Body / Wherever / What"))
        quality_lifespan = _cand(f"{T}.quality.lifespan", **W,
                                 provenance=_sym(T, "Vy", "71", "Lifespan / Whenever / How"))

        return [
            orient_top, orient_bottom, orient_starboard, orient_port, orient_front, orient_back,
            motion_hence, motion_travel,
            relation_meet, relation_part, relation_stay, relation_status,
            time_eventual,
            quality_crowned, quality_explicit, quality_hidden, quality_common, quality_relational,
            force_order, force_chaos, quality_scattered,
            moment_death,
            quality_embodied, quality_lifespan,
        ]


# ---------------------------------------------------------------------------
# Daisy (72–97)  —  Structural / mechanical engineering
# "The engineering tongue." Fully deterministic — no lotus requirements.
# ---------------------------------------------------------------------------

class DaisyRegister(BaseRegister):
    """4th tongue: Structural/mechanical primitives."""

    name = "daisy"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "daisy"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.9, tail=["daisy", "structure", "mechanical"])

        # --- Identity / Void ---
        identity_segment  = _cand(f"{T}.identity.segment",   **W, provenance=_sym(T, "Lo",  "72", "Segments / Identity"))
        identity_component= _cand(f"{T}.identity.component", **W, provenance=_sym(T, "Yei", "73", "Component / Integrator"))
        void_declare      = _cand(f"{T}.void.declare",        **W, provenance=_sym(T, "Ol",  "74", "Deadzone / Relative Void"))

        # --- Joints / Connections ---
        joint_interlock = _cand(f"{T}.joint.interlock", **W, provenance=_sym(T, "X",   "75", "Joint / Interlock"))
        joint_fulcrum   = _cand(f"{T}.joint.fulcrum",   **W, provenance=_sym(T, "Yx",  "76", "Fulcrum / Crux"))

        # --- Gates (block vs. open are mutually exclusive) ---
        gate_block = _cand(f"{T}.gate.block", forbids=[f"{T}.gate.open"],
                           **W, provenance=_sym(T, "Go",  "77", "Plug / Blocker"))
        gate_open  = _cand(f"{T}.gate.open",  forbids=[f"{T}.gate.block"],
                           **W, provenance=_sym(T, "Ro",  "83", "Ion-channel / Gate / Receptor"))

        # --- Space descriptors ---
        space_degree = _cand(f"{T}.space.degree",  **W, provenance=_sym(T, "Foa", "78", "Degree / Space"))
        space_layers = _cand(f"{T}.space.layers",  **W, provenance=_sym(T, "Oy",  "79", "Depths / Layers"))
        space_radial = _cand(f"{T}.space.radial",  **W, provenance=_sym(T, "Ym",  "88", "Radial Space"))

        # --- Socket types ---
        socket_open = _cand(f"{T}.socket.open", forbids=[f"{T}.socket.cuff"],
                            **W, provenance=_sym(T, "W",  "80", "Freefall / Socket Space"))
        socket_cuff = _cand(f"{T}.socket.cuff", forbids=[f"{T}.socket.open"],
                            **W, provenance=_sym(T, "Th", "81", "Cuff / Indentation"))

        # --- Cluster / Structural forms ---
        cluster_form    = _cand(f"{T}.cluster.form",       **W, provenance=_sym(T, "Kael", "82", "Cluster / Fruit / Flower"))
        structure_membrane = _cand(f"{T}.structure.membrane", **W, provenance=_sym(T, "Gl", "84", "Membrane / Muscle"))
        structure_scaffold = _cand(f"{T}.structure.scaffold", **W, provenance=_sym(T, "To", "85", "Scaffold / Framework"))
        structure_web      = _cand(f"{T}.structure.web",      **W, provenance=_sym(T, "Ma", "86", "Web / Interchange"))
        network_declare    = _cand(f"{T}.network.declare",    **W, provenance=_sym(T, "Ne", "87", "Network / System"))

        # --- Actuators (mutually exclusive by mechanism type) ---
        actuator_switch = _cand(f"{T}.actuator.switch",
                                forbids=[f"{T}.actuator.valve", f"{T}.actuator.lever"],
                                **W, provenance=_sym(T, "Nz", "89", "Switch / Circuit Actuator"))
        actuator_valve  = _cand(f"{T}.actuator.valve",
                                forbids=[f"{T}.actuator.switch", f"{T}.actuator.lever"],
                                **W, provenance=_sym(T, "Sho", "90", "Valve / Fluid Actuator"))
        actuator_lever  = _cand(f"{T}.actuator.lever",
                                forbids=[f"{T}.actuator.switch", f"{T}.actuator.valve"],
                                **W, provenance=_sym(T, "Hi", "91", "Lever / Radial Actuator"))

        # --- Connective tissue ---
        bond_create   = _cand(f"{T}.bond.create",    **W, provenance=_sym(T, "Mh",  "92", "Bond"))
        vortex_open   = _cand(f"{T}.vortex.open",    **W, provenance=_sym(T, "Zhi", "93", "Eye / Vortex"))
        tensor_declare= _cand(f"{T}.tensor.declare", **W, provenance=_sym(T, "Vr",  "94", "Rotor / Tensor"))
        surface_declare=_cand(f"{T}.surface.declare",**W, provenance=_sym(T, "St",  "95", "Surface"))
        path_create   = _cand(f"{T}.path.create",    **W, provenance=_sym(T, "Fn",  "96", "Passage / Pathway"))
        seed_plant    = _cand(f"{T}.seed.plant",     **W, provenance=_sym(T, "N",   "97", "Seed / Sheet / Fiber"))

        return [
            identity_segment, identity_component, void_declare,
            joint_interlock, joint_fulcrum,
            gate_block, gate_open,
            space_degree, space_layers, space_radial,
            socket_open, socket_cuff,
            cluster_form,
            structure_membrane, structure_scaffold, structure_web, network_declare,
            actuator_switch, actuator_valve, actuator_lever,
            bond_create, vortex_open, tensor_declare, surface_declare, path_create, seed_plant,
        ]


# ---------------------------------------------------------------------------
# AppleBlossom (98–123)  —  Alchemical elements and compounds
# Six primaries encode mind/space/time axes. Four elements + 16 compounds.
# Phase transitions require lotus attestation.
# ---------------------------------------------------------------------------

class AppleBlossomRegister(BaseRegister):
    """5th tongue: Alchemical elements and compounds."""

    name = "appleblossom"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "apple"
        W: _CandWeights = _CandWeights(rw=0.6, cw=0.7, tail=["apple", "element", "compound"])

        # --- Mind / Space / Time axes (each axis mutually exclusive) ---
        mind_pos = _cand(f"{T}.mind.positive", forbids=[f"{T}.mind.negative"],
                         **W, provenance=_sym(T, "A", "98",  "Mind +"))
        mind_neg = _cand(f"{T}.mind.negative", forbids=[f"{T}.mind.positive"],
                         **W, provenance=_sym(T, "O", "99",  "Mind -"))
        space_pos= _cand(f"{T}.space.positive",forbids=[f"{T}.space.negative"],
                         **W, provenance=_sym(T, "I", "100", "Space +"))
        space_neg= _cand(f"{T}.space.negative",forbids=[f"{T}.space.positive"],
                         **W, provenance=_sym(T, "E", "101", "Space -"))
        time_pos = _cand(f"{T}.time.positive", forbids=[f"{T}.time.negative"],
                         **W, provenance=_sym(T, "Y", "102", "Time +"))
        time_neg = _cand(f"{T}.time.negative", forbids=[f"{T}.time.positive"],
                         **W, provenance=_sym(T, "U", "103", "Time -"))

        # --- Four elements (mutually exclusive primary element state) ---
        all_elem = [f"{T}.element.{e}" for e in ("fire", "air", "water", "earth")]
        element_fire  = _cand(f"{T}.element.fire",  forbids=[e for e in all_elem if "fire"  not in e], **W, provenance=_sym(T, "Shak", "104", "Fire"))
        element_air   = _cand(f"{T}.element.air",   forbids=[e for e in all_elem if "air"   not in e], **W, provenance=_sym(T, "Puf",  "105", "Air"))
        element_water = _cand(f"{T}.element.water", forbids=[e for e in all_elem if "water" not in e], **W, provenance=_sym(T, "Mel",  "106", "Water"))
        element_earth = _cand(f"{T}.element.earth", forbids=[e for e in all_elem if "earth" not in e], **W, provenance=_sym(T, "Zot",  "107", "Earth"))

        # --- 16 Compounds (element×element — coexist as compound states) ---
        # Phase transitions into compounds require lotus attestation.
        _compounds = [
            ("plasma",       "Zhuk",  "108", "Plasma (Fire,Fire)"),
            ("sulphur",      "Kypa",  "109", "Sulphur (Fire,Air)"),
            ("alkahest",     "Alky",  "110", "Alkahest / Alcohol (Fire,Water)"),
            ("magma",        "Kazho", "111", "Magma / Lava (Fire,Earth)"),
            ("smoke",        "Puky",  "112", "Smoke (Air,Fire)"),
            ("gas",          "Pyfu",  "113", "Gas (Air,Air)"),
            ("carbonation",  "Mipa",  "114", "Carbonation / Trapped Gas (Air,Water)"),
            ("mercury",      "Zitef", "115", "Mercury (Air,Earth)"),
            ("steam",        "Shem",  "116", "Steam (Water,Fire)"),
            ("vapor",        "Lefu",  "117", "Vapor (Water,Air)"),
            ("mixed_fluids", "Milo",  "118", "Mixed fluids / Mixtures (Water,Water)"),
            ("erosion",      "Myza",  "119", "Erosion (Water,Earth)"),
            ("radiation",    "Zashu", "120", "Radiation / Radioactive stones (Earth,Fire)"),
            ("dust",         "Fozt",  "121", "Dust (Earth,Air)"),
            ("sediment",     "Mazi",  "122", "Sediment (Earth,Water)"),
            ("salt",         "Zaot",  "123", "Salt (Earth,Earth)"),
        ]
        compounds = [
            _cand(f"{T}.compound.{name}", lotus_tag=f"{T}.compound.{name}",
                  rw=0.7, cw=0.6, tail=["apple", "compound", "phase_transition"],
                  provenance=_sym(T, sym, dec, meaning))
            for name, sym, dec, meaning in _compounds
        ]

        return (
            [mind_pos, mind_neg, space_pos, space_neg, time_pos, time_neg,
             element_fire, element_air, element_water, element_earth]
            + compounds
        )


# ---------------------------------------------------------------------------
# Aster (128–155)  —  Chiral spectrum, time types, space operations
# Space operations are deterministic. Fold/frozen time require lotus attestation.
# Chiral handedness: right and left are mutually exclusive per color.
# ---------------------------------------------------------------------------

class AsterRegister(BaseRegister):
    """6th tongue: Chiral spectrum, time types, space operations."""

    name = "aster"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "aster"
        W: _CandWeights = _CandWeights(rw=0.8, cw=1.0, tail=["aster", "chiral", "time", "space_op"])

        # --- Chiral color pairs (right ↔ left mutually exclusive per hue) ---
        _hues = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]
        _right_syms = [("Ry","128"),("Oth","129"),("Le","130"),("Gi","131"),("Fe","132"),("Ky","133"),("Alz","134")]
        _left_syms  = [("Ra","135"),("Tho","136"),("Lu","137"),("Ge","138"),("Fo","139"),("Kw","140"),("Dr","141")]

        chirals = []
        for i, hue in enumerate(_hues):
            rs, rd = _right_syms[i]
            ls, ld = _left_syms[i]
            chirals.append(_cand(f"{T}.chiral.right.{hue}", forbids=[f"{T}.chiral.left.{hue}"],
                                 **W, provenance=_sym(T, rs, rd, f"Right-chiral {hue}")))
            chirals.append(_cand(f"{T}.chiral.left.{hue}",  forbids=[f"{T}.chiral.right.{hue}"],
                                 **W, provenance=_sym(T, ls, ld, f"Left-chiral {hue}")))

        # --- Time types (mutually exclusive: one temporal mode per frontier) ---
        all_times = [f"{T}.time.{t}" for t in ("linear","loop","exponential","logarithmic","fold","frozen")]
        time_linear      = _cand(f"{T}.time.linear",      forbids=[t for t in all_times if "linear"      not in t], **W, provenance=_sym(T, "Si", "142", "Linear time"))
        time_loop        = _cand(f"{T}.time.loop",        forbids=[t for t in all_times if "loop"        not in t], **W, provenance=_sym(T, "Su", "143", "Loop time"))
        time_exponential = _cand(f"{T}.time.exponential", forbids=[t for t in all_times if "exponential" not in t], **W, provenance=_sym(T, "Os", "144", "Exponential time"))
        time_logarithmic = _cand(f"{T}.time.logarithmic", forbids=[t for t in all_times if "logarithmic" not in t], **W, provenance=_sym(T, "Se", "145", "Logarithmic time"))
        # Fold and frozen time are experiential — require lotus attestation
        time_fold   = _cand(f"{T}.time.fold",   forbids=[t for t in all_times if "fold"   not in t],
                            lotus_tag=f"{T}.time.fold",   rw=0.8, cw=0.5, tail=["aster", "time", "lotus-gated"],
                            provenance=_sym(T, "Sy", "146", "Fold time"))
        time_frozen = _cand(f"{T}.time.frozen", forbids=[t for t in all_times if "frozen" not in t],
                            lotus_tag=f"{T}.time.frozen", rw=0.8, cw=0.5, tail=["aster", "time", "lotus-gated"],
                            provenance=_sym(T, "As", "147", "Frozen time"))

        # --- Space operations (structurally deterministic) ---
        # Delete forbids assign/save (can't build what's being destroyed).
        # Unbind forbids save (can't save an unbound slot).
        space_assign = _cand(f"{T}.space.assign", forbids=[f"{T}.space.delete"],
                             **W, provenance=_sym(T, "Ep",   "148", "Assign space"))
        space_save   = _cand(f"{T}.space.save",   forbids=[f"{T}.space.unbind"],
                             **W, provenance=_sym(T, "Gwev", "149", "Save space"))
        space_parse  = _cand(f"{T}.space.parse",  **W, provenance=_sym(T, "Ifa", "150", "Parse space"))
        space_loop   = _cand(f"{T}.space.loop",   **W, provenance=_sym(T, "Ier", "151", "Loop space"))
        space_push   = _cand(f"{T}.space.push",   **W, provenance=_sym(T, "San", "152", "Push space"))
        space_delete = _cand(f"{T}.space.delete", forbids=[f"{T}.space.assign", f"{T}.space.save"],
                             **W, provenance=_sym(T, "Enno", "153", "Delete space"))
        space_run    = _cand(f"{T}.space.run",    **W, provenance=_sym(T, "Yl",  "154", "Run space"))
        space_unbind = _cand(f"{T}.space.unbind", forbids=[f"{T}.space.save"],
                             **W, provenance=_sym(T, "Hoz", "155", "Unbind space"))

        return (
            chirals
            + [time_linear, time_loop, time_exponential, time_logarithmic, time_fold, time_frozen]
            + [space_assign, space_save, space_parse, space_loop, space_push,
               space_delete, space_run, space_unbind]
        )


# ---------------------------------------------------------------------------
# Grapevine (156–183)  —  Networking / distribution / federation
# "The tongue most directly relevant to DjinnOS federation architecture."
# Fully deterministic — no lotus requirements.
# ---------------------------------------------------------------------------

class GrapevineRegister(BaseRegister):
    """7th tongue: Networking, distribution, federation primitives."""

    name = "grapevine"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "grapevine"
        W: _CandWeights = _CandWeights(rw=1.0, cw=0.8, tail=["grapevine", "network", "distribution"])

        # --- Storage layer (feast table metaphor) ---
        # Persistent file and volatile buffer are mutually exclusive for the same slot.
        volume_root      = _cand(f"{T}.volume.root",       **W, provenance=_sym(T, "Sa",    "156", "Feast table / root volume"))
        storage_file     = _cand(f"{T}.storage.file",      forbids=[f"{T}.storage.buffer"],
                                 **W, provenance=_sym(T, "Sao",   "157", "Cup / file / persistent object"))
        storage_buffer   = _cand(f"{T}.storage.buffer",    forbids=[f"{T}.storage.file"],
                                 **W, provenance=_sym(T, "Syr",   "158", "Wine / volatile buffer"))
        storage_directory= _cand(f"{T}.storage.directory", **W, provenance=_sym(T, "Seth",  "159", "Platter / directory / bundle"))
        storage_cluster  = _cand(f"{T}.storage.cluster",   **W, provenance=_sym(T, "Samos", "160", "Banquet hall / database cluster"))
        storage_snapshot = _cand(f"{T}.storage.snapshot",  **W, provenance=_sym(T, "Sava",  "161", "Amphora / snapshot archive"))
        storage_cache    = _cand(f"{T}.storage.cache",     **W, provenance=_sym(T, "Sael",  "162", "Leftovers / cache"))

        # --- Messaging layer (Myk family) ---
        msg_packet  = _cand(f"{T}.msg.packet",   **W, provenance=_sym(T, "Myk",   "163", "Messenger / packet"))
        msg_route   = _cand(f"{T}.msg.route",    **W, provenance=_sym(T, "Myr",   "164", "Procession path / route"))
        msg_hop     = _cand(f"{T}.msg.hop",      **W, provenance=_sym(T, "Mio",   "165", "Stride / hop"))
        msg_emit    = _cand(f"{T}.msg.emit",     **W, provenance=_sym(T, "Mek",   "166", "Call / emit event"))
        msg_metadata= _cand(f"{T}.msg.metadata", **W, provenance=_sym(T, "Mavo",  "167", "Banner / metadata"))
        msg_gateway = _cand(f"{T}.msg.gateway",  **W, provenance=_sym(T, "Mekha", "168", "Herald / gateway"))
        msg_stream  = _cand(f"{T}.msg.stream",   **W, provenance=_sym(T, "Myrun", "169", "Sacred march / stream"))

        # --- Hazard declarations (Dyf family) ---
        # Acknowledging distributed system properties — these are structural assertions, not errors.
        hazard_jitter      = _cand(f"{T}.hazard.jitter",      **W, provenance=_sym(T, "Dyf",   "170", "Jitter / nondeterminism"))
        hazard_burst       = _cand(f"{T}.hazard.burst",       **W, provenance=_sym(T, "Dyo",   "171", "Burst / load spike"))
        hazard_corruption  = _cand(f"{T}.hazard.corruption",  **W, provenance=_sym(T, "Dyth",  "172", "Packet loss / corruption"))
        hazard_concurrency = _cand(f"{T}.hazard.concurrency", **W, provenance=_sym(T, "Dyska", "173", "Concurrency / thread dance"))
        hazard_flood       = _cand(f"{T}.hazard.flood",       **W, provenance=_sym(T, "Dyne",  "174", "Broadcast / flood"))
        hazard_overflow    = _cand(f"{T}.hazard.overflow",    **W, provenance=_sym(T, "Dyran", "175", "Overflow / memory full"))
        hazard_overload    = _cand(f"{T}.hazard.overload",    **W, provenance=_sym(T, "Dyso",  "176", "Overload threshold"))

        # --- Coordination layer (Kyf family) ---
        # Replica and authoritative-commit are mutually exclusive roles for the same node.
        coord_node      = _cand(f"{T}.coord.node",      **W, provenance=_sym(T, "Kyf",    "177", "Cluster node"))
        coord_steward   = _cand(f"{T}.coord.steward",   **W, provenance=_sym(T, "Kyl",    "178", "Steward / coordinator"))
        coord_semaphore = _cand(f"{T}.coord.semaphore", **W, provenance=_sym(T, "Kyra",   "179", "Control token / semaphore"))
        coord_ring      = _cand(f"{T}.coord.ring",      **W, provenance=_sym(T, "Kyvos",  "180", "Ring topology"))
        coord_consensus = _cand(f"{T}.coord.consensus", **W, provenance=_sym(T, "Kysha",  "181", "Consensus choir"))
        coord_replica   = _cand(f"{T}.coord.replica",   forbids=[f"{T}.coord.commit"],
                                **W, provenance=_sym(T, "Kyom",   "182", "Replica / masked follower"))
        coord_commit    = _cand(f"{T}.coord.commit",    forbids=[f"{T}.coord.replica"],
                                **W, provenance=_sym(T, "Kysael", "183", "Authoritative commit"))

        return [
            volume_root,
            storage_file, storage_buffer, storage_directory, storage_cluster,
            storage_snapshot, storage_cache,
            msg_packet, msg_route, msg_hop, msg_emit, msg_metadata, msg_gateway, msg_stream,
            hazard_jitter, hazard_burst, hazard_corruption, hazard_concurrency,
            hazard_flood, hazard_overflow, hazard_overload,
            coord_node, coord_steward, coord_semaphore, coord_ring, coord_consensus,
            coord_replica, coord_commit,
        ]


# ---------------------------------------------------------------------------
# Cannabis (184–213)  —  Cross-tongue awareness operators
# "Cannabis 'arrived recently.' It handles meta-cognitive awareness."
# The tensor product of the prior 7 tongues with Mind / Space / Time.
# ALL Cannabis candidates require lotus attestation — consciousness is not computable.
# ---------------------------------------------------------------------------

class CannabisRegister(BaseRegister):
    """8th tongue: Cross-tongue awareness operators (tensor product)."""

    name = "cannabis"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "cannabis"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.2, tail=["cannabis", "awareness", "projection"])

        # --- Mind projections (each tongue seen through Mind) ---
        mind_lotus  = _cand(f"{T}.mind.lotus",  lotus_tag=f"{T}.mind.lotus",  **W,
                            provenance=_sym(T, "At",  "184", "Grounded awareness / consciousness of material presence"))
        mind_rose   = _cand(f"{T}.mind.rose",   lotus_tag=f"{T}.mind.rose",   **W,
                            provenance=_sym(T, "Ar",  "185", "Chromatic perception / awareness of energetic quality"))
        mind_sakura = _cand(f"{T}.mind.sakura", lotus_tag=f"{T}.mind.sakura", **W,
                            provenance=_sym(T, "Av",  "186", "Relational consciousness / awareness of connection and structure"))
        mind_daisy  = _cand(f"{T}.mind.daisy",  lotus_tag=f"{T}.mind.daisy",  **W,
                            provenance=_sym(T, "Azr", "187", "Structural intuition / felt sense of how things are assembled"))
        mind_apple  = _cand(f"{T}.mind.apple",  lotus_tag=f"{T}.mind.apple",  **W,
                            provenance=_sym(T, "Af",  "188", "Transformative awareness / consciousness of change in process"))
        mind_aster  = _cand(f"{T}.mind.aster",  lotus_tag=f"{T}.mind.aster",  **W,
                            provenance=_sym(T, "An",  "189", "Chiral discernment / awareness of handedness and temporal direction"))

        # --- Mind shadow operators ---
        shadow_mind_signal  = _cand(f"{T}.shadow.mind.signal",  lotus_tag=f"{T}.shadow.mind.signal",  **W,
                                    provenance=_sym(T, "Od", "190", "Unspecified mental signal / noise without narrative"))
        shadow_mind_quality = _cand(f"{T}.shadow.mind.quality", lotus_tag=f"{T}.shadow.mind.quality", **W,
                                    provenance=_sym(T, "Ox", "191", "Of the quality of unconscious transmission"))
        shadow_mind_manner  = _cand(f"{T}.shadow.mind.manner",  lotus_tag=f"{T}.shadow.mind.manner",  **W,
                                    provenance=_sym(T, "Om", "192", "In the manner of unconscious transmission"))

        # --- Conscious persistence ---
        conscious_persist = _cand(f"{T}.conscious.persist", lotus_tag=f"{T}.conscious.persist",
                                  rw=1.0, cw=0.4, tail=["cannabis", "conscious", "persist"],
                                  provenance=_sym(T, "Soa", "193", "Conscious persistence / the act of mind making something durable"))

        # --- Space projections (each tongue seen through Space) ---
        space_lotus  = _cand(f"{T}.space.lotus",  lotus_tag=f"{T}.space.lotus",  **W,
                             provenance=_sym(T, "It",  "194", "Grounded locality / the spatial fact of material presence"))
        space_rose   = _cand(f"{T}.space.rose",   lotus_tag=f"{T}.space.rose",   **W,
                             provenance=_sym(T, "Ir",  "195", "Spectral field / the spatial distribution of energetic frequency"))
        space_sakura = _cand(f"{T}.space.sakura", lotus_tag=f"{T}.space.sakura", **W,
                             provenance=_sym(T, "Iv",  "196", "Relational geometry / the spatial structure of connection"))
        space_daisy  = _cand(f"{T}.space.daisy",  lotus_tag=f"{T}.space.daisy",  **W,
                             provenance=_sym(T, "Izr", "197", "Structural volume / the space a form occupies and articulates"))
        space_apple  = _cand(f"{T}.space.apple",  lotus_tag=f"{T}.space.apple",  **W,
                             provenance=_sym(T, "If",  "198", "Transitional space / the spatial site of transformation"))
        space_aster  = _cand(f"{T}.space.aster",  lotus_tag=f"{T}.space.aster",  **W,
                             provenance=_sym(T, "In",  "199", "Chiral orientation / handedness as spatial phenomenon"))

        # --- Space shadow operators ---
        shadow_space_signal  = _cand(f"{T}.shadow.space.signal",  lotus_tag=f"{T}.shadow.space.signal",  **W,
                                     provenance=_sym(T, "Ed", "200", "Unspecified spatial signal / network without location"))
        shadow_space_quality = _cand(f"{T}.shadow.space.quality", lotus_tag=f"{T}.shadow.space.quality", **W,
                                     provenance=_sym(T, "Ex", "201", "Of the quality of unlocated transmission"))
        shadow_space_manner  = _cand(f"{T}.shadow.space.manner",  lotus_tag=f"{T}.shadow.space.manner",  **W,
                                     provenance=_sym(T, "Em", "202", "In the manner of unlocated transmission"))

        # --- Conscious spatial action ---
        conscious_space = _cand(f"{T}.conscious.space", lotus_tag=f"{T}.conscious.space",
                                rw=1.0, cw=0.4, tail=["cannabis", "conscious", "space"],
                                provenance=_sym(T, "Sei", "203", "Conscious spatial action / the act of mind deliberately occupying or shaping space"))

        # --- Time projections (each tongue seen through Time) ---
        time_lotus  = _cand(f"{T}.time.lotus",  lotus_tag=f"{T}.time.lotus",  **W,
                            provenance=_sym(T, "Yt",  "204", "Grounded duration / the temporal weight of material existence"))
        time_rose   = _cand(f"{T}.time.rose",   lotus_tag=f"{T}.time.rose",   **W,
                            provenance=_sym(T, "Yr",  "205", "Spectral timing / the frequency and rhythm of energetic cycles"))
        time_sakura = _cand(f"{T}.time.sakura", lotus_tag=f"{T}.time.sakura", **W,
                            provenance=_sym(T, "Yv",  "206", "Relational temporality / the timing of meeting and parting"))
        time_daisy  = _cand(f"{T}.time.daisy",  lotus_tag=f"{T}.time.daisy",  **W,
                            provenance=_sym(T, "Yzr", "207", "Structural time / the temporal unfolding of form and assembly"))
        time_apple  = _cand(f"{T}.time.apple",  lotus_tag=f"{T}.time.apple",  **W,
                            provenance=_sym(T, "Yf",  "208", "Transformative time / the duration of phase change"))
        time_aster  = _cand(f"{T}.time.aster",  lotus_tag=f"{T}.time.aster",  **W,
                            provenance=_sym(T, "Yn",  "209", "Chiral time / the direction and handedness of temporal flow"))

        # --- Time shadow operators ---
        shadow_time_signal  = _cand(f"{T}.shadow.time.signal",  lotus_tag=f"{T}.shadow.time.signal",  **W,
                                    provenance=_sym(T, "Ud", "210", "Unspecified temporal signal / propagation without sequence"))
        shadow_time_quality = _cand(f"{T}.shadow.time.quality", lotus_tag=f"{T}.shadow.time.quality", **W,
                                    provenance=_sym(T, "Ux", "211", "Of the quality of unsequenced transmission"))
        shadow_time_manner  = _cand(f"{T}.shadow.time.manner",  lotus_tag=f"{T}.shadow.time.manner",  **W,
                                    provenance=_sym(T, "Um", "212", "In the manner of unsequenced transmission"))

        # --- Conscious temporal action ---
        conscious_time = _cand(f"{T}.conscious.time", lotus_tag=f"{T}.conscious.time",
                               rw=1.0, cw=0.4, tail=["cannabis", "conscious", "time"],
                               provenance=_sym(T, "Suy", "213", "Conscious temporal action / the act of mind deliberately moving through or shaping time"))

        return [
            mind_lotus, mind_rose, mind_sakura, mind_daisy, mind_apple, mind_aster,
            shadow_mind_signal, shadow_mind_quality, shadow_mind_manner,
            conscious_persist,
            space_lotus, space_rose, space_sakura, space_daisy, space_apple, space_aster,
            shadow_space_signal, shadow_space_quality, shadow_space_manner,
            conscious_space,
            time_lotus, time_rose, time_sakura, time_daisy, time_apple, time_aster,
            shadow_time_signal, shadow_time_quality, shadow_time_manner,
            conscious_time,
        ]


# ---------------------------------------------------------------------------
# Dragon (256-285)  --  Tongue 9
# ---------------------------------------------------------------------------

class DragonRegister(BaseRegister):
    name = "dragon"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "dragon"
        W: _CandWeights = _CandWeights(rw=0.7, cw=0.8, tail=['dragon', 'void', 'organism'])
        return [
            _cand(f"{T}.rhivesh", **W, provenance=_sym(T, "Rhivesh", "256", "Mental void 1 — hijacked self-reference / Ophiocordyceps unilateralis")),
            _cand(f"{T}.rhokve", **W, provenance=_sym(T, "Rhokve", "257", "Mental void 2 — cognition without apparatus / Physarum polycephalum")),
            _cand(f"{T}.rhezh", **W, provenance=_sym(T, "Rhezh", "258", "Mental void 3 — memory without persistent self / Turritopsis dohrnii")),
            _cand(f"{T}.rhivash_ko", **W, provenance=_sym(T, "Rhivash-ko", "259", "Mental void 4 — self-reference extended into confirmed absence / Porti")),
            _cand(f"{T}.zhri_val", **W, provenance=_sym(T, "Zhri'val", "260", "Mental void 5 — identity distributed across non-communicating substrat")),
            _cand(f"{T}.rhasha_vok", **W, provenance=_sym(T, "Rhasha-vok", "261", "Mental void 6 — cognition with apparatus suppressing its own correctio")),
            _cand(f"{T}.vzhiran", **W, provenance=_sym(T, "Vzhiran", "262", "Mental void 7 — information boundary does not correspond to physical b")),
            _cand(f"{T}.rhokvesh_na", **W, provenance=_sym(T, "Rhokvesh-na", "263", "Mental void 8 — self-consuming self-reference / Stegodyphus dumicola")),
            _cand(f"{T}.vzhiral_rhe", **W, provenance=_sym(T, "Vzhiral-rhe", "264", "Mental void 9 — decision without decider / Dictyostelium discoideum")),
            _cand(f"{T}.rhazhvu_nokte", **W, provenance=_sym(T, "Rhazhvu-nokte", "265", "Mental void 10 — singular identity with no singular self / Letharia vu")),
            _cand(f"{T}.dvavesh", **W, provenance=_sym(T, "Dvavesh", "266", "Spatial void 1 — boundary that cannot be located / Armillaria ostoyae")),
            _cand(f"{T}.dvokran", **W, provenance=_sym(T, "Dvokran", "267", "Spatial void 2 — total interpenetration / Sacculina carcini")),
            _cand(f"{T}.dva_zhal", **W, provenance=_sym(T, "Dva'zhal", "268", "Spatial void 3 — collective with no unified spatial origin / Praya dub")),
            _cand(f"{T}.dvasha_ke", **W, provenance=_sym(T, "Dvasha-ke", "269", "Spatial void 4 — form concealing structure / Welwitschia mirabilis")),
            _cand(f"{T}.zhrdva_vol", **W, provenance=_sym(T, "Zhrdva-vol", "270", "Spatial void 5 — scale of operation does not equal scale of definition")),
            _cand(f"{T}.dvokesh", **W, provenance=_sym(T, "Dvokesh", "271", "Spatial void 6 — coherence borrowed from medium / Mnemiopsis leidyi")),
            _cand(f"{T}.vzhrdva", **W, provenance=_sym(T, "Vzhrdva", "272", "Spatial void 7 — agency without presence / Ophiocordyceps spatial")),
            _cand(f"{T}.dvokrash_na", **W, provenance=_sym(T, "Dvokrash-na", "273", "Spatial void 8 — inside/outside equivalence / Hydra vulgaris")),
            _cand(f"{T}.rhdva_vun", **W, provenance=_sym(T, "Rhdva-vun", "274", "Spatial void 9 — defined by central absence / Adansonia digitata")),
            _cand(f"{T}.dvazh_nokvre", **W, provenance=_sym(T, "Dvazh-nokvre", "275", "Spatial void 10 — no reference configuration / Trichoplax adhaerens")),
            _cand(f"{T}.kwevesh", **W, provenance=_sym(T, "Kwevesh", "276", "Temporal void 1 — time passes through not for / Ramazzottius varieorna")),
            _cand(f"{T}.kwokre", **W, provenance=_sym(T, "Kwokre", "277", "Temporal void 2 — occupying another organism's temporal experience / O")),
            _cand(f"{T}.kwe_zhal", **W, provenance=_sym(T, "Kwe'zhal", "278", "Temporal void 3 — lineage collapsed into undifferentiated now / Thraus")),
            _cand(f"{T}.kwasha_val", **W, provenance=_sym(T, "Kwasha-val", "279", "Temporal void 4 — persistence through temporal incoherence with surrou")),
            _cand(f"{T}.zhrkwe_na", **W, provenance=_sym(T, "Zhrkwe-na", "280", "Temporal void 5 — persistence through total replacement of visible sub")),
            _cand(f"{T}.kwokvesh", **W, provenance=_sym(T, "Kwokvesh", "281", "Temporal void 6 — identity without continuity / Turritopsis dohrnii te")),
            _cand(f"{T}.vzhrkwe", **W, provenance=_sym(T, "Vzhrkwe", "282", "Temporal void 7 — persistence by violating the rule of persistence / B")),
            _cand(f"{T}.kwokrash_rhe", **W, provenance=_sym(T, "Kwokrash-rhe", "283", "Temporal void 8 — visible death does not equal actual organism's death")),
            _cand(f"{T}.rhkwe_vun", **W, provenance=_sym(T, "Rhkwe-vun", "284", "Temporal void 9 — outside evolutionary time while subject to it / Vace")),
            _cand(f"{T}.kwazhvu_nokte", **W, provenance=_sym(T, "Kwazhvu-nokte", "285", "Temporal void 10 — temporal gap with no biological explanation for clo")),
        ]


# ---------------------------------------------------------------------------
# Virus (286-315)  --  Tongue 10
# ---------------------------------------------------------------------------

class VirusRegister(BaseRegister):
    name = "virus"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "virus"
        W: _CandWeights = _CandWeights(rw=1.2, cw=0.6, tail=['virus', 'molecular', 'contagion'])
        return [
            _cand(f"{T}.plave", **W, provenance=_sym(T, "Plave", "286", "Ordinal 1 — 5' terminus / ordinal origin before the first base")),
            _cand(f"{T}.plaro", **W, provenance=_sym(T, "Plaro", "287", "Ordinal 2 — 3' terminus / ordinal end")),
            _cand(f"{T}.plahan", **W, provenance=_sym(T, "Plahan", "288", "Ordinal 3 — Ha-Na / A-U standard pairing / positive principle meeting ")),
            _cand(f"{T}.plaung", **W, provenance=_sym(T, "Plaung", "289", "Ordinal 4 — Wu-Ung / G-C mediated pairing / full traversal resolved / ")),
            _cand(f"{T}.plaha", **W, provenance=_sym(T, "Plaha", "290", "Ordinal 5 — Ha free / A unpaired / positive principle without compleme")),
            _cand(f"{T}.plana", **W, provenance=_sym(T, "Plana", "291", "Ordinal 6 — Na free / U unpaired / pure traversal point / neither pole")),
            _cand(f"{T}.plawu", **W, provenance=_sym(T, "Plawu", "292", "Ordinal 7 — Wu free / G unpaired / mediation implicate seeking root")),
            _cand(f"{T}.plaoku", **W, provenance=_sym(T, "Plaoku", "293", "Ordinal 8 — Ung free / C unpaired / mediation implicate at rest")),
            _cand(f"{T}.plavik", **W, provenance=_sym(T, "Plavik", "294", "Ordinal 9 — Codon / triplet unit / minimal ordinal unit of meaning")),
            _cand(f"{T}.plavikro", **W, provenance=_sym(T, "Plavikro", "295", "Ordinal 10 — Reading frame / where segmentation begins determines what")),
            _cand(f"{T}.jruve", **W, provenance=_sym(T, "Jruve", "296", "Orthogonal 1 — Hairpin loop / simplest fold / sequence turns back on i")),
            _cand(f"{T}.jrushan", **W, provenance=_sym(T, "Jrushan", "297", "Orthogonal 2 — Stem / stable double-stranded region from intramolecula")),
            _cand(f"{T}.jrulok", **W, provenance=_sym(T, "Jrulok", "298", "Orthogonal 3 — Internal loop / asymmetric unpaired region within a ste")),
            _cand(f"{T}.jruval", **W, provenance=_sym(T, "Jruval", "299", "Orthogonal 4 — Bulge / single unpaired base on one side of a stem")),
            _cand(f"{T}.jru_wun", **W, provenance=_sym(T, "Jru'wun", "300", "Orthogonal 5 — G-U wobble / Wu-Na near-fit / mediation implicate touch")),
            _cand(f"{T}.jruvekna", **W, provenance=_sym(T, "Jruvekna", "301", "Orthogonal 6 — Pseudoknot / fold crossing another fold / spatial self-")),
            _cand(f"{T}.jrukash", **W, provenance=_sym(T, "Jrukash", "302", "Orthogonal 7 — Junction / three or more stems meeting at a point")),
            _cand(f"{T}.jruvashko", **W, provenance=_sym(T, "Jruvashko", "303", "Orthogonal 8 — Kissing loops / two hairpin loops pairing / second-orde")),
            _cand(f"{T}.jrukashro", **W, provenance=_sym(T, "Jrukashro", "304", "Orthogonal 9 — Coaxial stack / two stems stacking end-to-end")),
            _cand(f"{T}.jrunokvre", **W, provenance=_sym(T, "Jrunokvre", "305", "Orthogonal 10 — Multibranch loop / four or more stems at a single junc")),
            _cand(f"{T}.wikve", **W, provenance=_sym(T, "Wikve", "306", "Catalytic 1 — Hammerhead ribozyme / self-cleavage / simplest catalytic")),
            _cand(f"{T}.wikro", **W, provenance=_sym(T, "Wikro", "307", "Catalytic 2 — Hairpin ribozyme / reversible cleavage and ligation")),
            _cand(f"{T}.wikhan", **W, provenance=_sym(T, "Wikhan", "308", "Catalytic 3 — HDV ribozyme / viral self-cleavage / catalysis at alive/")),
            _cand(f"{T}.wikval", **W, provenance=_sym(T, "Wikval", "309", "Catalytic 4 — Group I intron / self-splicing / sequence removing itsel")),
            _cand(f"{T}.wikvalna", **W, provenance=_sym(T, "Wikvalna", "310", "Catalytic 5 — Group II intron / prior before the prior / ancestor of s")),
            _cand(f"{T}.wikung", **W, provenance=_sym(T, "Wikung", "311", "Catalytic 6 — Ribosomal RNA / peptide bond formation / Ung embedded / ")),
            _cand(f"{T}.wikaro", **W, provenance=_sym(T, "Wikaro", "312", "Catalytic 7 — Telomerase RNA / template-directed extension / anti-term")),
            _cand(f"{T}.wiknasha", **W, provenance=_sym(T, "Wiknasha", "313", "Catalytic 8 — snRNA / splicing catalysis / Na embedded / RNA mind insi")),
            _cand(f"{T}.wikshavel", **W, provenance=_sym(T, "Wikshavel", "314", "Catalytic 9 — Aptamer / ligand-activated fold switch / sha embedded / ")),
            _cand(f"{T}.wiknokvre", **W, provenance=_sym(T, "Wiknokvre", "315", "Catalytic 10 — Replicase / RNA copying RNA / the self-replicating prio")),
        ]


# ---------------------------------------------------------------------------
# Bacteria (316-345)  --  Tongue 11
# ---------------------------------------------------------------------------

class BacteriaRegister(BaseRegister):
    name = "bacteria"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "bacteria"
        W: _CandWeights = _CandWeights(rw=1.0, cw=1.0, tail=['bacteria', 'electrodynamic', 'membrane'])
        return [
            _cand(f"{T}.zhove", **W, provenance=_sym(T, "Zhove", "316", "Mind 1 — resting potential / baseline charge state / the identity the ")),
            _cand(f"{T}.zhoran", **W, provenance=_sym(T, "Zhoran", "317", "Mind 2 — depolarization / potential collapses toward zero / identity-t")),
            _cand(f"{T}.zhokre", **W, provenance=_sym(T, "Zhokre", "318", "Mind 3 — hyperpolarization / potential exceeds resting / the over-corr")),
            _cand(f"{T}.zho_val", **W, provenance=_sym(T, "Zho'val", "319", "Mind 4 — membrane asymmetry / different regions at different potential")),
            _cand(f"{T}.zho_na", **W, provenance=_sym(T, "Zho'na", "320", "Mind 5 — proton motive force / Na embedded / charge gradient driving A")),
            _cand(f"{T}.zhovesh", **W, provenance=_sym(T, "Zhovesh", "321", "Mind 6 — ion selectivity / membrane discriminating between ion types /")),
            _cand(f"{T}.zhuvek", **W, provenance=_sym(T, "Zhuvek", "322", "Mind 7 — electrochemical equilibrium / Nernst potential / diffusion an")),
            _cand(f"{T}.zhokrash", **W, provenance=_sym(T, "Zhokrash", "323", "Mind 8 — action potential analog / rapid depolarization-repolarization")),
            _cand(f"{T}.zhokven", **W, provenance=_sym(T, "Zhokven", "324", "Mind 9 — threshold potential / charge state where signal becomes trigg")),
            _cand(f"{T}.zhokven_na", **W, provenance=_sym(T, "Zhokven-na", "325", "Mind 10 — refractory period / Na at the close / post-threshold window ")),
            _cand(f"{T}.rive", **W, provenance=_sym(T, "Rive", "326", "Time 1 — signal onset / moment of potential change / temporal beginnin")),
            _cand(f"{T}.rivan", **W, provenance=_sym(T, "Rivan", "327", "Time 2 — signal propagation / cascade moving through time")),
            _cand(f"{T}.riko", **W, provenance=_sym(T, "Riko", "328", "Time 3 — signal termination / Ko embedded / return to resting / the si")),
            _cand(f"{T}.rival", **W, provenance=_sym(T, "Rival", "329", "Time 4 — signal frequency / rate of repeated signals / temporal patter")),
            _cand(f"{T}.ri_vash", **W, provenance=_sym(T, "Ri'vash", "330", "Time 5 — temporal summation / half glottal at threshold / sub-threshol")),
            _cand(f"{T}.rikash", **W, provenance=_sym(T, "Rikash", "331", "Time 6 — adaptation / repeated identical signals producing progressive")),
            _cand(f"{T}.rikove", **W, provenance=_sym(T, "Rikove", "332", "Time 7 — habituation / learned temporal pattern of non-response / prac")),
            _cand(f"{T}.rizhun", **W, provenance=_sym(T, "Rizhun", "333", "Time 8 — circadian rhythm analog / zh from Zho bleeding in / internal ")),
            _cand(f"{T}.rivekna", **W, provenance=_sym(T, "Rivekna", "334", "Time 9 — chemotaxis temporal gradient / Na embedded / sensing change i")),
            _cand(f"{T}.rikrasho", **W, provenance=_sym(T, "Rikrasho", "335", "Time 10 — signal delay / open ending / temporal lag between stimulus a")),
            _cand(f"{T}.vavre", **W, provenance=_sym(T, "Vavre", "336", "Space 1 — field extent / spatial reach of charge differential beyond m")),
            _cand(f"{T}.varan", **W, provenance=_sym(T, "Varan", "337", "Space 2 — gradient vector / spatial direction of the potential change")),
            _cand(f"{T}.varko", **W, provenance=_sym(T, "Varko", "338", "Space 3 — quorum sensing range / Ko embedded / spatial threshold trigg")),
            _cand(f"{T}.varval", **W, provenance=_sym(T, "Varval", "339", "Space 4 — biofilm organization / colony as spatial field expression / ")),
            _cand(f"{T}.var_zho", **W, provenance=_sym(T, "Var'zho", "340", "Space 5 — electrical wave / Zho embedded / mind-charge propagating thr")),
            _cand(f"{T}.varlok", **W, provenance=_sym(T, "Varlok", "341", "Space 6 — chemotaxis navigation / movement through space up or down a ")),
            _cand(f"{T}.varshan", **W, provenance=_sym(T, "Varshan", "342", "Space 7 — membrane topology / sha embedded / spatial geometry of membr")),
            _cand(f"{T}.varkash", **W, provenance=_sym(T, "Varkash", "343", "Space 8 — niche occupation / spatial claim of organism on its chemical")),
            _cand(f"{T}.varnokre", **W, provenance=_sym(T, "Varnokre", "344", "Space 9 — colony boundary / where the biofilm's spatial electrical fie")),
            _cand(f"{T}.varzhokrash", **W, provenance=_sym(T, "Varzhokrash", "345", "Space 10 — interspecies interference / Zho inside Var / competing char")),
        ]


# ---------------------------------------------------------------------------
# Excavata (346-377)  --  Tongue 12
# ---------------------------------------------------------------------------

class ExcavataRegister(BaseRegister):
    name = "excavata"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "excavata"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.9, tail=['excavata', 'mobius', 'rotation'])
        return [
            _cand(f"{T}.ranve", **W, provenance=_sym(T, "Ranve", "346", "Rotation 1 — right-hand chirality / clockwise helical rotation")),
            _cand(f"{T}.ranvu", **W, provenance=_sym(T, "Ranvu", "347", "Rotation 2 — left-hand chirality / counterclockwise / the mirror")),
            _cand(f"{T}.ranpek", **W, provenance=_sym(T, "Ranpek", "348", "Rotation 3 — pitch / rate of advance per full rotation")),
            _cand(f"{T}.ranval", **W, provenance=_sym(T, "Ranval", "349", "Rotation 4 — amplitude / radius of the helix")),
            _cand(f"{T}.ran_vo", **W, provenance=_sym(T, "Ran'vo", "350", "Rotation 5 — reversal / chirality inverting mid-rotation / half glotta")),
            _cand(f"{T}.rankwe", **W, provenance=_sym(T, "Rankwe", "351", "Rotation 6 — flagellar beat / Kwe embedded / helical wave driving cell")),
            _cand(f"{T}.ranvesh", **W, provenance=_sym(T, "Ranvesh", "352", "Rotation 7 — rotational gradient / change in rotation rate along the h")),
            _cand(f"{T}.rankovre", **W, provenance=_sym(T, "Rankovre", "353", "Rotation 8 — coaxial rotation / Ko embedded / two helices rotating aro")),
            _cand(f"{T}.ranzhok", **W, provenance=_sym(T, "Ranzhok", "354", "Rotation 9 — supercoiling / zh from Zho / helix coiling on itself / wh")),
            _cand(f"{T}.rankrash_vo", **W, provenance=_sym(T, "Rankrash-vo", "355", "Rotation 10 — chiral symmetry breaking / the moment a symmetric system")),
            _cand(f"{T}.yefve", **W, provenance=_sym(T, "Yefve", "356", "Traversal 1 — half-twist / Möbius-defining move / apparent inside beco")),
            _cand(f"{T}.yefran", **W, provenance=_sym(T, "Yefran", "357", "Traversal 2 — single face / Ran inside Yef / rotation proving one cont")),
            _cand(f"{T}.yeflo", **W, provenance=_sym(T, "Yeflo", "358", "Traversal 3 — single edge / the one continuous boundary of the Möbius")),
            _cand(f"{T}.yefval", **W, provenance=_sym(T, "Yefval", "359", "Traversal 4 — traversal / moving along the surface without crossing a ")),
            _cand(f"{T}.yef_na", **W, provenance=_sym(T, "Yef'na", "360", "Traversal 5 — non-orientability / Na embedded / integration resisting ")),
            _cand(f"{T}.yefkash", **W, provenance=_sym(T, "Yefkash", "361", "Traversal 6 — self-intersection appearance / apparent crossing that is")),
            _cand(f"{T}.yefkovre", **W, provenance=_sym(T, "Yefkovre", "362", "Traversal 7 — center cut / Ko embedded / finding continuity where divi")),
            _cand(f"{T}.yefvash_lo", **W, provenance=_sym(T, "Yefvash-lo", "363", "Traversal 8 — off-center cut / produces Möbius and regular loop linked")),
            _cand(f"{T}.yefranog", **W, provenance=_sym(T, "Yefranog", "364", "Traversal 9 — embedding / Ran embedded / rotation taking spatial form ")),
            _cand(f"{T}.yefzhokran", **W, provenance=_sym(T, "Yefzhokran", "365", "Traversal 10 — projection / Zh+Ran inside Yef / mind and rotation misr")),
            _cand(f"{T}.logve", **W, provenance=_sym(T, "Logve", "366", "Orientation error 1 — handedness confusion / mistaking left-hand for r")),
            _cand(f"{T}.logan", **W, provenance=_sym(T, "Logan", "367", "Orientation error 2 — inside/outside conflation / two apparent faces t")),
            _cand(f"{T}.logran", **W, provenance=_sym(T, "Logran", "368", "Orientation error 3 — center fixation / Ran inside Log / rotation appe")),
            _cand(f"{T}.logval", **W, provenance=_sym(T, "Logval", "369", "Orientation error 4 — traversal direction error / assigning wrong way ")),
            _cand(f"{T}.log_vesh", **W, provenance=_sym(T, "Log'vesh", "370", "Orientation error 5 — boundary assumption / single edge treated as sep")),
            _cand(f"{T}.logkash", **W, provenance=_sym(T, "Logkash", "371", "Orientation error 6 — orientation assignment / attempting to fix consi")),
            _cand(f"{T}.logkre", **W, provenance=_sym(T, "Logkre", "372", "Orientation error 7 — depth error / groove's apparent depth read as ge")),
            _cand(f"{T}.logzhok", **W, provenance=_sym(T, "Logzhok", "373", "Orientation error 8 — chirality fixation / zh from Zho inside Log / mi")),
            _cand(f"{T}.logvekna", **W, provenance=_sym(T, "Logvekna", "374", "Orientation error 9 — projection error / Na embedded / integration rea")),
            _cand(f"{T}.logranzhok", **W, provenance=_sym(T, "Logranzhok", "375", "Orientation error 10 — self-reference loop / Ran+Zhok inside Log / the")),
            _cand(f"{T}.yefko", **W, provenance=_sym(T, "Yefko", "376", "Ko state — correct Möbius traversal / Yef in Ko mode / moving along th")),
            _cand(f"{T}.ranku", **W, provenance=_sym(T, "Ranku", "377", "Ku state — arrested rotation / Ran in Ku mode / the helix completing a")),
        ]


# ---------------------------------------------------------------------------
# Archaeplastida (378-409)  --  Tongue 13
# ---------------------------------------------------------------------------

class ArchaeplastidaRegister(BaseRegister):
    name = "archaeplastida"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "archaeplastida"
        W: _CandWeights = _CandWeights(rw=0.8, cw=1.1, tail=['archaeplastida', 'endosymbiosis'])
        return [
            _cand(f"{T}.zotve", **W, provenance=_sym(T, "Zotve", "378", "Earth-Constitutive 1 — primary endosymbiosis / the engulfment event th")),
            _cand(f"{T}.zotan", **W, provenance=_sym(T, "Zotan", "379", "Earth-Constitutive 2 — genome reduction / constitutive component losin")),
            _cand(f"{T}.zotkre", **W, provenance=_sym(T, "Zotkre", "380", "Earth-Constitutive 3 — protein import / host nucleus coding proteins f")),
            _cand(f"{T}.zot_vel", **W, provenance=_sym(T, "Zot'vel", "381", "Earth-Constitutive 4 — double membrane / boundary layering as constitu")),
            _cand(f"{T}.zotvash", **W, provenance=_sym(T, "Zotvash", "382", "Earth-Constitutive 5 — semi-autonomous replication / constitutive but ")),
            _cand(f"{T}.zotzhok", **W, provenance=_sym(T, "Zotzhok", "383", "Earth-Constitutive 6 — historical gene transfer / zh from Zho / consti")),
            _cand(f"{T}.zotkash_ran", **W, provenance=_sym(T, "Zotkash-ran", "384", "Earth-Constitutive 7 — plastid inheritance / Ran embedded / constituti")),
            _cand(f"{T}.zotnavre", **W, provenance=_sym(T, "Zotnavre", "385", "Earth-Constitutive 8 — obligate mutualism / Na embedded / the integrat")),
            _cand(f"{T}.melve", **W, provenance=_sym(T, "Melve", "386", "Water-Incidental 1 — phagocytosis / temporary enclosure of incidental ")),
            _cand(f"{T}.melan", **W, provenance=_sym(T, "Melan", "387", "Water-Incidental 2 — digestive vacuole / enclosed material processed /")),
            _cand(f"{T}.melko", **W, provenance=_sym(T, "Melko", "388", "Water-Incidental 3 — exocytosis / Ko embedded / the incidental cycle c")),
            _cand(f"{T}.mel_vash", **W, provenance=_sym(T, "Mel'vash", "389", "Water-Incidental 4 — autophagy / half glottal / cell digesting its own")),
            _cand(f"{T}.melpik", **W, provenance=_sym(T, "Melpik", "390", "Water-Incidental 5 — pinocytosis / fluid-phase endocytosis / liquid ta")),
            _cand(f"{T}.melvek", **W, provenance=_sym(T, "Melvek", "391", "Water-Incidental 6 — vesicular trafficking / material moving through m")),
            _cand(f"{T}.melkash", **W, provenance=_sym(T, "Melkash", "392", "Water-Incidental 7 — lysosomal fusion / digestive apparatus merging wi")),
            _cand(f"{T}.melzotkre", **W, provenance=_sym(T, "Melzotkre", "393", "Water-Incidental 8 — failed digestion / Zot inside Mel / Earth inside ")),
            _cand(f"{T}.pufve", **W, provenance=_sym(T, "Pufve", "394", "Air-Constitutive 1 — mycorrhizal symbiosis / the archetypal free-const")),
            _cand(f"{T}.pufan", **W, provenance=_sym(T, "Pufan", "395", "Air-Constitutive 2 — nutrient exchange / constitutive relation maintai")),
            _cand(f"{T}.pufko", **W, provenance=_sym(T, "Pufko", "396", "Air-Constitutive 3 — signaling / Ko embedded / free-constitutive commu")),
            _cand(f"{T}.puf_val", **W, provenance=_sym(T, "Puf'val", "397", "Air-Constitutive 4 — specificity / half glottal at the selection momen")),
            _cand(f"{T}.pufzot", **W, provenance=_sym(T, "Pufzot", "398", "Air-Constitutive 5 — obligate dependence / Zot inside Puf / Earth insi")),
            _cand(f"{T}.pufkash", **W, provenance=_sym(T, "Pufkash", "399", "Air-Constitutive 6 — partner switching / constitutive relation portabl")),
            _cand(f"{T}.pufranve", **W, provenance=_sym(T, "Pufranve", "400", "Air-Constitutive 7 — spatial extension / Ran embedded / free partner e")),
            _cand(f"{T}.pufshakna", **W, provenance=_sym(T, "Pufshakna", "401", "Air-Constitutive 8 — loss of free partner / Shak inside Puf / Na at cl")),
            _cand(f"{T}.shakve", **W, provenance=_sym(T, "Shakve", "402", "Fire-Incidental 1 — chance contact / the passing encounter / no consti")),
            _cand(f"{T}.shakran", **W, provenance=_sym(T, "Shakran", "403", "Fire-Incidental 2 — current gene transfer / Ran embedded / rotation of")),
            _cand(f"{T}.shakvesh", **W, provenance=_sym(T, "Shakvesh", "404", "Fire-Incidental 3 — viral passage / vesh (through) / Fire passing thro")),
            _cand(f"{T}.shak_mel", **W, provenance=_sym(T, "Shak'mel", "405", "Fire-Incidental 4 — allelopathy / Mel inside Shak / Water chemistry as")),
            _cand(f"{T}.shakpuf", **W, provenance=_sym(T, "Shakpuf", "406", "Fire-Incidental 5 — transient parasitism / Puf inside Shak / Air turne")),
            _cand(f"{T}.shakazh", **W, provenance=_sym(T, "Shakazh", "407", "Fire-Incidental 6 — competitive exclusion / Fire displacing Fire")),
            _cand(f"{T}.shakvekna", **W, provenance=_sym(T, "Shakvekna", "408", "Fire-Incidental 7 — lateral facilitation / Na embedded / accidental be")),
            _cand(f"{T}.shakzotmel", **W, provenance=_sym(T, "Shakzotmel", "409", "Fire-Incidental 8 — environmental stochasticity / Zot+Mel inside Shak ")),
        ]


# ---------------------------------------------------------------------------
# Myxozoa (410-443)  --  Tongue 14
# ---------------------------------------------------------------------------

class MyxozoaRegister(BaseRegister):
    name = "myxozoa"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "myxozoa"
        W: _CandWeights = _CandWeights(rw=0.8, cw=0.9, tail=['myxozoa', 'parasite', 'identity'])
        return [
            _cand(f"{T}.ive", **W, provenance=_sym(T, "Ive", "410", "Iv 1 — identity as trajectory / actinospore floating toward undetected")),
            _cand(f"{T}.ivi", **W, provenance=_sym(T, "Ivi", "411", "Iv 2 — identity as apex / contact moment / spore reaches its necessary")),
            _cand(f"{T}.ivu", **W, provenance=_sym(T, "Ivu", "412", "Iv 3 — identity as compression / sporoplasm at maximum density minimum")),
            _cand(f"{T}.ivo", **W, provenance=_sym(T, "Ivo", "413", "Iv 4 — identity as directed depth / injection vector / polar capsule t")),
            _cand(f"{T}.iva", **W, provenance=_sym(T, "Iva", "414", "Iv 5 — identity as open approach / pre-encounter / selfhood entirely a")),
            _cand(f"{T}.ivoe", **W, provenance=_sym(T, "Ivoe", "415", "Iv 6 — identity as reduced neutrality / spore suspended between phases")),
            _cand(f"{T}.oave", **W, provenance=_sym(T, "Oave", "416", "Oa 1 — identity as boundary-persistence / parasitic cell maintaining m")),
            _cand(f"{T}.oavi", **W, provenance=_sym(T, "Oavi", "417", "Oa 2 — identity as apex-from-below / parasite orienting to host archit")),
            _cand(f"{T}.oavu", **W, provenance=_sym(T, "Oavu", "418", "Oa 3 — identity as contained-ground / myxospore cyst in fish muscle / ")),
            _cand(f"{T}.oavo", **W, provenance=_sym(T, "Oavo", "419", "Oa 4 — identity as depth-ground / parasite inhabiting deepest host spa")),
            _cand(f"{T}.oava", **W, provenance=_sym(T, "Oava", "420", "Oa 5 — identity as open-ground / blood-distributed parasite / no fixed")),
            _cand(f"{T}.oavoe", **W, provenance=_sym(T, "Oavoe", "421", "Oa 6 — identity as reduced-ground / minimally active parasite dormant ")),
            _cand(f"{T}.navsh", **W, provenance=_sym(T, "Navsh", "422", "Nav 1 — fire-identity / polar capsule discharge / the explosive inject")),
            _cand(f"{T}.navp", **W, provenance=_sym(T, "Navp", "423", "Nav 2 — air-identity / spore dispersal / directionality before host is")),
            _cand(f"{T}.navm", **W, provenance=_sym(T, "Navm", "424", "Nav 3 — water-identity / tissue infiltration / the penetrating pervasi")),
            _cand(f"{T}.navz", **W, provenance=_sym(T, "Navz", "425", "Nav 4 — earth-identity / cyst structure / mineralized walls / selfhood")),
            _cand(f"{T}.navk", **W, provenance=_sym(T, "Navk", "426", "Nav 5 — Kael-identity / 500-million-year evolutionary plasticity / gen")),
            _cand(f"{T}.ivelo", **W, provenance=_sym(T, "Ivelo", "427", "Iv-lo 1 — trajectory as arrival / moving toward != reaching / directio")),
            _cand(f"{T}.ivilo", **W, provenance=_sym(T, "Ivilo", "428", "Iv-lo 2 — apex as completion / contact event mistaken for total selfho")),
            _cand(f"{T}.ivulo", **W, provenance=_sym(T, "Ivulo", "429", "Iv-lo 3 — compression as simplicity / maximum density mistaken for min")),
            _cand(f"{T}.ivolo", **W, provenance=_sym(T, "Ivolo", "430", "Iv-lo 4 — injection as interiority / inserting self into other != beco")),
            _cand(f"{T}.ivalo", **W, provenance=_sym(T, "Ivalo", "431", "Iv-lo 5 — seeking as openness / undirected approach != genuine opennes")),
            _cand(f"{T}.ivoelo", **W, provenance=_sym(T, "Ivoelo", "432", "Iv-lo 6 — suspension as universal floor / phase-between state != zero ")),
            _cand(f"{T}.oavelo", **W, provenance=_sym(T, "Oavelo", "433", "Oa-lo 1 — boundary-persistence as boundary-making / maintaining integr")),
            _cand(f"{T}.oavilo", **W, provenance=_sym(T, "Oavilo", "434", "Oa-lo 2 — interior-orientation as being interior / reading architectur")),
            _cand(f"{T}.oavulo", **W, provenance=_sym(T, "Oavulo", "435", "Oa-lo 3 — contained-ground as containing / being held != holding / cys")),
            _cand(f"{T}.oavolo", **W, provenance=_sym(T, "Oavolo", "436", "Oa-lo 4 — depth-inhabitation as depth / inhabiting the deepest space !")),
            _cand(f"{T}.oavalo", **W, provenance=_sym(T, "Oavalo", "437", "Oa-lo 5 — distributed ground as universal ground / being everywhere wi")),
            _cand(f"{T}.oavoelo", **W, provenance=_sym(T, "Oavoelo", "438", "Oa-lo 6 — dormant minimum as irreducible ground / dormancy within host")),
            _cand(f"{T}.navshlo", **W, provenance=_sym(T, "Navshlo", "439", "Nav-lo 1 — fire universalized / because I inject all selfhood is injec")),
            _cand(f"{T}.navplo", **W, provenance=_sym(T, "Navplo", "440", "Nav-lo 2 — air universalized / because I disperse all selfhood is disp")),
            _cand(f"{T}.navmlo", **W, provenance=_sym(T, "Navmlo", "441", "Nav-lo 3 — water universalized / because I penetrate all selfhood is p")),
            _cand(f"{T}.navzlo", **W, provenance=_sym(T, "Navzlo", "442", "Nav-lo 4 — earth universalized / because I build my cyst all selfhood ")),
            _cand(f"{T}.navklo", **W, provenance=_sym(T, "Navklo", "443", "Nav-lo 5 — Kael universalized / radical plasticity declared the criter")),
        ]


# ---------------------------------------------------------------------------
# Archaea (444-477)  --  Tongue 15
# ---------------------------------------------------------------------------

class ArchaeaRegister(BaseRegister):
    name = "archaea"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "archaea"
        W: _CandWeights = _CandWeights(rw=0.6, cw=0.9, tail=['archaea', 'extremophile'])
        return [
            _cand(f"{T}.ethe", **W, provenance=_sym(T, "Ethe", "444", "Eth 1 — identity as tolerance-edge / self defined by what it can withs")),
            _cand(f"{T}.ethi", **W, provenance=_sym(T, "Ethi", "445", "Eth 2 — identity as thermal apex / hyperthermophile / selfhood as the ")),
            _cand(f"{T}.ethu", **W, provenance=_sym(T, "Ethu", "446", "Eth 3 — identity as pressure-threshold / barophile / self = the organi")),
            _cand(f"{T}.etho", **W, provenance=_sym(T, "Etho", "447", "Eth 4 — identity as chemical depth-threshold / the self that finds its")),
            _cand(f"{T}.etha", **W, provenance=_sym(T, "Etha", "448", "Eth 5 — identity as open-threshold / pre-specific extremophily / what ")),
            _cand(f"{T}.ethoe", **W, provenance=_sym(T, "Ethoe", "449", "Eth 6 — identity as reduced-threshold / minimum viable existence at th")),
            _cand(f"{T}.urge", **W, provenance=_sym(T, "Urge", "450", "Urg 1 — identity as boundary-held-within-extreme / ether-linked membra")),
            _cand(f"{T}.urgi", **W, provenance=_sym(T, "Urgi", "451", "Urg 2 — identity as apex-within-extreme / organism at 121degC / being ")),
            _cand(f"{T}.urgu", **W, provenance=_sym(T, "Urgu", "452", "Urg 3 — identity as compressed-within / piezophile at maximum pressure")),
            _cand(f"{T}.urgo", **W, provenance=_sym(T, "Urgo", "453", "Urg 4 — identity as depth-within-chemical-extreme / methanogen in anox")),
            _cand(f"{T}.urga", **W, provenance=_sym(T, "Urga", "454", "Urg 5 — identity as open-within-extreme / no retreat from the hostile ")),
            _cand(f"{T}.urgoe", **W, provenance=_sym(T, "Urgoe", "455", "Urg 6 — identity as reduced-within-extreme / dormant archaeon in perma")),
            _cand(f"{T}.krevsh", **W, provenance=_sym(T, "Krevsh", "456", "Krev 1 — fire-inversion / hyperthermophile / heat that sustains rather")),
            _cand(f"{T}.krevp", **W, provenance=_sym(T, "Krevp", "457", "Krev 2 — air-inversion / strict anaerobe / oxygen is poison / absence ")),
            _cand(f"{T}.krevm", **W, provenance=_sym(T, "Krevm", "458", "Krev 3 — water-inversion / halophile / saturated brine as correct medi")),
            _cand(f"{T}.krevz", **W, provenance=_sym(T, "Krevz", "459", "Krev 4 — earth-inversion / lithotroph / mineral substrate as energy so")),
            _cand(f"{T}.krevk", **W, provenance=_sym(T, "Krevk", "460", "Krev 5 — Kael-inversion / 3.5-billion-year metabolic invention / survi")),
            _cand(f"{T}.ethelo", **W, provenance=_sym(T, "Ethelo", "461", "Eth-lo 1 — tolerance-edge as universal boundary / because my limit def")),
            _cand(f"{T}.ethilo", **W, provenance=_sym(T, "Ethilo", "462", "Eth-lo 2 — thermal apex as completion / living at extremes != living a")),
            _cand(f"{T}.ethulo", **W, provenance=_sym(T, "Ethulo", "463", "Eth-lo 3 — pressure-threshold as simplicity / maximum pressure resista")),
            _cand(f"{T}.etholo", **W, provenance=_sym(T, "Etholo", "464", "Eth-lo 4 — chemical depth-threshold as depth itself / inhabiting pH 0 ")),
            _cand(f"{T}.ethalo", **W, provenance=_sym(T, "Ethalo", "465", "Eth-lo 5 — open-threshold as openness / undirected approach to the lim")),
            _cand(f"{T}.ethoelo", **W, provenance=_sym(T, "Ethoelo", "466", "Eth-lo 6 — reduced-threshold as universal floor / minimum viable at th")),
            _cand(f"{T}.urgelo", **W, provenance=_sym(T, "Urgelo", "467", "Urg-lo 1 — boundary-held-within-extreme as boundary-making / ether-lin")),
            _cand(f"{T}.urgilo", **W, provenance=_sym(T, "Urgilo", "468", "Urg-lo 2 — apex-within-extreme as the apex / most heat-tolerant confir")),
            _cand(f"{T}.urgulo", **W, provenance=_sym(T, "Urgulo", "469", "Urg-lo 3 — compressed-within as containment / optimal function under p")),
            _cand(f"{T}.urgolo", **W, provenance=_sym(T, "Urgolo", "470", "Urg-lo 4 — depth-within-chemical-extreme as depth / most hostile mediu")),
            _cand(f"{T}.urgalo", **W, provenance=_sym(T, "Urgalo", "471", "Urg-lo 5 — open-within-extreme as universal medium / thriving in brine")),
            _cand(f"{T}.urgoelo", **W, provenance=_sym(T, "Urgoelo", "472", "Urg-lo 6 — reduced-within-extreme as irreducible ground / dormancy in ")),
            _cand(f"{T}.krevshlo", **W, provenance=_sym(T, "Krevshlo", "473", "Krev-lo 1 — fire-inversion universalized / because heat sustains me al")),
            _cand(f"{T}.krevplo", **W, provenance=_sym(T, "Krevplo", "474", "Krev-lo 2 — air-inversion universalized / because oxygen is my poison ")),
            _cand(f"{T}.krevmlo", **W, provenance=_sym(T, "Krevmlo", "475", "Krev-lo 3 — water-inversion universalized / because brine is my ocean ")),
            _cand(f"{T}.krevzlo", **W, provenance=_sym(T, "Krevzlo", "476", "Krev-lo 4 — earth-inversion universalized / because I eat rock all sus")),
            _cand(f"{T}.krevklo", **W, provenance=_sym(T, "Krevklo", "477", "Krev-lo 5 — Kael-inversion universalized / radical viability declared ")),
        ]


# ---------------------------------------------------------------------------
# Protist (478-511)  --  Tongue 16
# ---------------------------------------------------------------------------

class ProtistRegister(BaseRegister):
    name = "protist"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "protist"
        W: _CandWeights = _CandWeights(rw=0.7, cw=0.8, tail=['protist', 'between', 'residue'])
        return [
            _cand(f"{T}.aeve", **W, provenance=_sym(T, "Aeve", "478", "Ae 1 — identity as categorical boundary-between / neither fully open n")),
            _cand(f"{T}.aevi", **W, provenance=_sym(T, "Aevi", "479", "Ae 2 — identity as neither/nor at height / most complex Protist / neit")),
            _cand(f"{T}.aevu", **W, provenance=_sym(T, "Aevu", "480", "Ae 3 — identity as neither/nor compressed / maximum categorical densit")),
            _cand(f"{T}.aevo", **W, provenance=_sym(T, "Aevo", "481", "Ae 4 — identity as depth-between / depth without being the abyss / rea")),
            _cand(f"{T}.aeva", **W, provenance=_sym(T, "Aeva", "482", "Ae 5 — identity as open-between / most open possible categorical in-be")),
            _cand(f"{T}.aevoe", **W, provenance=_sym(T, "Aevoe", "483", "Ae 6 — identity as reduced neither/nor / minimum viable existence whil")),
            _cand(f"{T}.oive", **W, provenance=_sym(T, "Oive", "484", "Oi 1 — identity as edge-of-crossing / selfhood defined by traversal ac")),
            _cand(f"{T}.oivi", **W, provenance=_sym(T, "Oivi", "485", "Oi 2 — identity as apex-of-crossing / most complex categorical travers")),
            _cand(f"{T}.oivu", **W, provenance=_sym(T, "Oivu", "486", "Oi 3 — identity as compressed-crossing / maximum categorical work in m")),
            _cand(f"{T}.oivo", **W, provenance=_sym(T, "Oivo", "487", "Oi 4 — identity as depth-of-crossing / deepest categorical traversal /")),
            _cand(f"{T}.oiva", **W, provenance=_sym(T, "Oiva", "488", "Oi 5 — identity as open-crossing / no fixed trajectory across categori")),
            _cand(f"{T}.oivoe", **W, provenance=_sym(T, "Oivoe", "489", "Oi 6 — identity as reduced-crossing / minimum viable existence while t")),
            _cand(f"{T}.grevsh", **W, provenance=_sym(T, "Grevsh", "490", "Grev 1 — fire-exclusion / not-plant / excluded from the fire-mediated ")),
            _cand(f"{T}.grevp", **W, provenance=_sym(T, "Grevp", "491", "Grev 2 — air-exclusion / not-animal / excluded from the air-mediated m")),
            _cand(f"{T}.grevm", **W, provenance=_sym(T, "Grevm", "492", "Grev 3 — water-exclusion / not-fungus / excluded from the osmotrophic ")),
            _cand(f"{T}.grevz", **W, provenance=_sym(T, "Grevz", "493", "Grev 4 — earth-exclusion / no fixed morphological ground / excluded fr")),
            _cand(f"{T}.grevk", **W, provenance=_sym(T, "Grevk", "494", "Grev 5 — Kael-exclusion / the remainder after all other kingdoms found")),
            _cand(f"{T}.aevelo", **W, provenance=_sym(T, "Aevelo", "495", "Ae-lo 1 — in-between as universal position / because I occupy between-")),
            _cand(f"{T}.aevilo", **W, provenance=_sym(T, "Aevilo", "496", "Ae-lo 2 — neither/nor at height as the apex / true complexity requires")),
            _cand(f"{T}.aevulo", **W, provenance=_sym(T, "Aevulo", "497", "Ae-lo 3 — categorical compression as simplicity / dense exclusion != a")),
            _cand(f"{T}.aevolo", **W, provenance=_sym(T, "Aevolo", "498", "Ae-lo 4 — depth-between as depth itself / reaching deepest without cro")),
            _cand(f"{T}.aevalo", **W, provenance=_sym(T, "Aevalo", "499", "Ae-lo 5 — open-between as openness / not-belonging-anywhere != being f")),
            _cand(f"{T}.aevoelo", **W, provenance=_sym(T, "Aevoelo", "500", "Ae-lo 6 — reduced neither/nor as universal floor / minimum categorical")),
            _cand(f"{T}.oivelo", **W, provenance=_sym(T, "Oivelo", "501", "Oi-lo 1 — edge-of-crossing as boundary-making / traversal-boundary != ")),
            _cand(f"{T}.oivilo", **W, provenance=_sym(T, "Oivilo", "502", "Oi-lo 2 — apex-of-crossing as the apex / crossing furthest across cate")),
            _cand(f"{T}.oivulo", **W, provenance=_sym(T, "Oivulo", "503", "Oi-lo 3 — compressed-crossing as containment / maximum categorical wor")),
            _cand(f"{T}.oivolo", **W, provenance=_sym(T, "Oivolo", "504", "Oi-lo 4 — depth-of-crossing as depth / furthest from any defining shor")),
            _cand(f"{T}.oivalo", **W, provenance=_sym(T, "Oivalo", "505", "Oi-lo 5 — open-crossing as universal openness / no fixed categorical t")),
            _cand(f"{T}.oivoelo", **W, provenance=_sym(T, "Oivoelo", "506", "Oi-lo 6 — reduced-crossing as irreducible ground / minimum existence w")),
            _cand(f"{T}.grevshlo", **W, provenance=_sym(T, "Grevshlo", "507", "Grev-lo 1 — fire-exclusion universalized / because I am not-plant genu")),
            _cand(f"{T}.grevplo", **W, provenance=_sym(T, "Grevplo", "508", "Grev-lo 2 — air-exclusion universalized / because I am not-animal auth")),
            _cand(f"{T}.grevmlo", **W, provenance=_sym(T, "Grevmlo", "509", "Grev-lo 3 — water-exclusion universalized / because I am not-fungus co")),
            _cand(f"{T}.grevzlo", **W, provenance=_sym(T, "Grevzlo", "510", "Grev-lo 4 — earth-exclusion universalized / because I have no fixed mo")),
            _cand(f"{T}.grevklo", **W, provenance=_sym(T, "Grevklo", "511", "Grev-lo 5 — Kael-exclusion universalized / no category was sufficient ")),
        ]


# ---------------------------------------------------------------------------
# Immune (512-545)  --  Tongue 17
# ---------------------------------------------------------------------------

class ImmuneRegister(BaseRegister):
    name = "immune"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "immune"
        W: _CandWeights = _CandWeights(rw=1.0, cw=0.9, tail=['immune', 'recognition', 'memory'])
        return [
            _cand(f"{T}.sive", **W, provenance=_sym(T, "Sive", "512", "Siv 1 — surface-pattern recognition / pattern detection at the cell bo")),
            _cand(f"{T}.sivi", **W, provenance=_sym(T, "Sivi", "513", "Siv 2 — high-specificity recognition / lock-and-key binding / T-cell r")),
            _cand(f"{T}.sivu", **W, provenance=_sym(T, "Sivu", "514", "Siv 3 — compressed recognition / minimum necessary pattern information")),
            _cand(f"{T}.sivo", **W, provenance=_sym(T, "Sivo", "515", "Siv 4 — internal antigen presentation / MHC-I presenting peptide fragm")),
            _cand(f"{T}.siva", **W, provenance=_sym(T, "Siva", "516", "Siv 5 — broad-spectrum recognition / TLRs reading PAMPs / open innate ")),
            _cand(f"{T}.sivoe", **W, provenance=_sym(T, "Sivoe", "517", "Siv 6 — threshold recognition / minimum pattern information sufficient")),
            _cand(f"{T}.reke", **W, provenance=_sym(T, "Reke", "518", "Rek 1 — boundary response / local inflammation / immediate edge-respon")),
            _cand(f"{T}.reki", **W, provenance=_sym(T, "Reki", "519", "Rek 2 — apex response / peak adaptive immunity / clonal expansion of t")),
            _cand(f"{T}.reku", **W, provenance=_sym(T, "Reku", "520", "Rek 3 — minimum viable response / least response that resolves the det")),
            _cand(f"{T}.reko", **W, provenance=_sym(T, "Reko", "521", "Rek 4 — systemic response / cytokine cascade / body-wide signaling coo")),
            _cand(f"{T}.reka", **W, provenance=_sym(T, "Reka", "522", "Rek 5 — broad innate response / non-specific inflammatory response bef")),
            _cand(f"{T}.rekoe", **W, provenance=_sym(T, "Rekoe", "523", "Rek 6 — baseline surveillance / continuous minimum monitoring for devi")),
            _cand(f"{T}.trevsh", **W, provenance=_sym(T, "Trevsh", "524", "Trev 1 — fire-memory / inflammatory memory trace / strongest recall / ")),
            _cand(f"{T}.trevp", **W, provenance=_sym(T, "Trevp", "525", "Trev 2 — air-memory / dispersed immunological memory / distributed acr")),
            _cand(f"{T}.trevm", **W, provenance=_sym(T, "Trevm", "526", "Trev 3 — water-memory / circulating antibody trace / memory that flows")),
            _cand(f"{T}.trevz", **W, provenance=_sym(T, "Trevz", "527", "Trev 4 — earth-memory / long-lived bone marrow plasma cells / structur")),
            _cand(f"{T}.trevk", **W, provenance=_sym(T, "Trevk", "528", "Trev 5 — Kael-memory / somatic hypermutation and VDJ recombination / i")),
            _cand(f"{T}.sivelo", **W, provenance=_sym(T, "Sivelo", "529", "Siv-lo 1 — surface-pattern as total pattern / recognizing at the bound")),
            _cand(f"{T}.sivilo", **W, provenance=_sym(T, "Sivilo", "530", "Siv-lo 2 — maximum-specificity as exhaustive recognition / precision b")),
            _cand(f"{T}.sivulo", **W, provenance=_sym(T, "Sivulo", "531", "Siv-lo 3 — compressed recognition as simple pattern / minimum necessar")),
            _cand(f"{T}.sivolo", **W, provenance=_sym(T, "Sivolo", "532", "Siv-lo 4 — internal presentation as interiority / displaying peptides ")),
            _cand(f"{T}.sivalo", **W, provenance=_sym(T, "Sivalo", "533", "Siv-lo 5 — broad-spectrum recognition as universal recognition / innat")),
            _cand(f"{T}.sivoelo", **W, provenance=_sym(T, "Sivoelo", "534", "Siv-lo 6 — threshold recognition as the recognition floor / minimum pa")),
            _cand(f"{T}.rekelo", **W, provenance=_sym(T, "Rekelo", "535", "Rek-lo 1 — boundary response as boundary-making / local inflammation !")),
            _cand(f"{T}.rekilo", **W, provenance=_sym(T, "Rekilo", "536", "Rek-lo 2 — peak adaptive response as completion / maximum clonal expan")),
            _cand(f"{T}.rekulo", **W, provenance=_sym(T, "Rekulo", "537", "Rek-lo 3 — minimum viable response as simplicity / least response that")),
            _cand(f"{T}.rekolo", **W, provenance=_sym(T, "Rekolo", "538", "Rek-lo 4 — systemic response as depth / cytokine cascade != being dept")),
            _cand(f"{T}.rekalo", **W, provenance=_sym(T, "Rekalo", "539", "Rek-lo 5 — broad innate response as universal response / non-specific ")),
            _cand(f"{T}.rekoelo", **W, provenance=_sym(T, "Rekoelo", "540", "Rek-lo 6 — baseline surveillance as the ground of all immunity / conti")),
            _cand(f"{T}.trevshlo", **W, provenance=_sym(T, "Trevshlo", "541", "Trev-lo 1 — fire-memory universalized / strongest memory is inflammato")),
            _cand(f"{T}.trevplo", **W, provenance=_sym(T, "Trevplo", "542", "Trev-lo 2 — dispersed memory universalized / because memory is distrib")),
            _cand(f"{T}.trevmlo", **W, provenance=_sym(T, "Trevmlo", "543", "Trev-lo 3 — water-memory universalized / all immunity should be humora")),
            _cand(f"{T}.trevzlo", **W, provenance=_sym(T, "Trevzlo", "544", "Trev-lo 4 — earth-memory universalized / all memory should be permanen")),
            _cand(f"{T}.trevklo", **W, provenance=_sym(T, "Trevklo", "545", "Trev-lo 5 — Kael-memory universalized / capacity to generate novel rec")),
        ]


# ---------------------------------------------------------------------------
# Neural (546-581)  --  Tongue 18
# ---------------------------------------------------------------------------

class NeuralRegister(BaseRegister):
    name = "neural"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "neural"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.8, tail=['neural', 'nervenet', 'signal'])
        return [
            _cand(f"{T}.vele", **W, provenance=_sym(T, "Vele", "546", "Vel 1 — signal at the sensory surface / mechanoreceptor or chemorecept")),
            _cand(f"{T}.veli", **W, provenance=_sym(T, "Veli", "547", "Vel 2 — threshold crossing / receptor potential reaching action potent")),
            _cand(f"{T}.velu", **W, provenance=_sym(T, "Velu", "548", "Vel 3 — receptor adaptation / signal amplitude decreasing under sustai")),
            _cand(f"{T}.velo", **W, provenance=_sym(T, "Velo", "549", "Vel 4 — internal signal / stretch receptor in the gastroderm / input f")),
            _cand(f"{T}.vela", **W, provenance=_sym(T, "Vela", "550", "Vel 5 — polymodal reception / mechanoreceptor responding to both touch")),
            _cand(f"{T}.veloe", **W, provenance=_sym(T, "Veloe", "551", "Vel 6 — subthreshold potential / graded signal that has not committed ")),
            _cand(f"{T}.nale", **W, provenance=_sym(T, "Nale", "552", "Nal 1 — bidirectional propagation / nerve net signal traveling all dir")),
            _cand(f"{T}.nali", **W, provenance=_sym(T, "Nali", "553", "Nal 2 — facilitation / repeated stimulation producing increased signal")),
            _cand(f"{T}.nalu", **W, provenance=_sym(T, "Nalu", "554", "Nal 3 — signal decrement / attenuation as signal propagates from sourc")),
            _cand(f"{T}.nalo", **W, provenance=_sym(T, "Nalo", "555", "Nal 4 — through-conduction / signal traveling full length of organism ")),
            _cand(f"{T}.nala", **W, provenance=_sym(T, "Nala", "556", "Nal 5 — diffuse spread / signal activating muscle fibers across entire")),
            _cand(f"{T}.naloe", **W, provenance=_sym(T, "Naloe", "557", "Nal 6 — threshold propagation / minimum signal energy sufficient to cr")),
            _cand(f"{T}.dreve", **W, provenance=_sym(T, "Dreve", "558", "Drev 1 — local contraction / muscle cell adjacent to activated nerve c")),
            _cand(f"{T}.drevi", **W, provenance=_sym(T, "Drevi", "559", "Drev 2 — coordinated contraction / synchronized activation of multiple")),
            _cand(f"{T}.drevu", **W, provenance=_sym(T, "Drevu", "560", "Drev 3 — nematocyst discharge / explosive irreversible output / coiled")),
            _cand(f"{T}.drevo", **W, provenance=_sym(T, "Drevo", "561", "Drev 4 — peristaltic wave / sequential coordinated activation travelin")),
            _cand(f"{T}.dreva", **W, provenance=_sym(T, "Dreva", "562", "Drev 5 — diffuse contraction / whole-body response to strong stimulus ")),
            _cand(f"{T}.drevoe", **W, provenance=_sym(T, "Drevoe", "563", "Drev 6 — minimum effector activation / threshold output producing just")),
            _cand(f"{T}.velelo", **W, provenance=_sym(T, "Velelo", "564", "Vel-lo 1 — surface signal as total input / receptor activation at boun")),
            _cand(f"{T}.velilo", **W, provenance=_sym(T, "Velilo", "565", "Vel-lo 2 — threshold crossing as semantic commitment / action potentia")),
            _cand(f"{T}.velulo", **W, provenance=_sym(T, "Velulo", "566", "Vel-lo 3 — receptor adaptation as simplification / adapted receptor re")),
            _cand(f"{T}.velolo", **W, provenance=_sym(T, "Velolo", "567", "Vel-lo 4 — internal signal as interiority / stretch receptor firing !=")),
            _cand(f"{T}.velalo", **W, provenance=_sym(T, "Velalo", "568", "Vel-lo 5 — polymodal reception as universal coverage / responding to m")),
            _cand(f"{T}.veloelo", **W, provenance=_sym(T, "Veloelo", "569", "Vel-lo 6 — subthreshold accumulation as signal floor / pre-commitment ")),
            _cand(f"{T}.nalelo", **W, provenance=_sym(T, "Nalelo", "570", "Nal-lo 1 — bidirectional propagation as total coverage / signal travel")),
            _cand(f"{T}.nalilo", **W, provenance=_sym(T, "Nalilo", "571", "Nal-lo 2 — facilitation as learning / increased responsiveness != enco")),
            _cand(f"{T}.nalulo", **W, provenance=_sym(T, "Nalulo", "572", "Nal-lo 3 — signal decrement as content loss / attenuation != loss of s")),
            _cand(f"{T}.nalolo", **W, provenance=_sym(T, "Nalolo", "573", "Nal-lo 4 — through-conduction as depth-traversal / maximum propagation")),
            _cand(f"{T}.nalalo", **W, provenance=_sym(T, "Nalalo", "574", "Nal-lo 5 — diffuse spread as total response / activating everywhere !=")),
            _cand(f"{T}.naloelo", **W, provenance=_sym(T, "Naloelo", "575", "Nal-lo 6 — threshold junction as net floor / minimum energy to cross o")),
            _cand(f"{T}.drevelo", **W, provenance=_sym(T, "Drevelo", "576", "Drev-lo 1 — local contraction as local knowledge / muscle firing adjac")),
            _cand(f"{T}.drevilo", **W, provenance=_sym(T, "Drevilo", "577", "Drev-lo 2 — coordinated contraction as cognition / synchronized bell c")),
            _cand(f"{T}.drevulo", **W, provenance=_sym(T, "Drevulo", "578", "Drev-lo 3 — nematocyst discharge as situational commitment / irreversi")),
            _cand(f"{T}.drevolo", **W, provenance=_sym(T, "Drevolo", "579", "Drev-lo 4 — peristaltic wave as directed movement / propagating sequen")),
            _cand(f"{T}.drevalo", **W, provenance=_sym(T, "Drevalo", "580", "Drev-lo 5 — whole-body response as total comprehension / every muscle ")),
            _cand(f"{T}.drevoelo", **W, provenance=_sym(T, "Drevoelo", "581", "Drev-lo 6 — minimum effector activation as output floor / threshold mu")),
        ]


# ---------------------------------------------------------------------------
# Serpent (582-617)  --  Tongue 19
# ---------------------------------------------------------------------------

class SerpentRegister(BaseRegister):
    name = "serpent"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "serpent"
        W: _CandWeights = _CandWeights(rw=1.1, cw=0.7, tail=['serpent', 'fire', 'element'])
        return [
            _cand(f"{T}.mash", **W, provenance=_sym(T, "Mash", "582", "Fire x Mind+ — conscious mind at the water-fire threshold / emotional ")),
            _cand(f"{T}.mosh", **W, provenance=_sym(T, "Mosh", "583", "Fire x Mindminus — unconscious ignition / pattern fires below awarenes")),
            _cand(f"{T}.mish", **W, provenance=_sym(T, "Mish", "584", "Fire x Space+ — presence expanding at ignition / the spatial event of ")),
            _cand(f"{T}.mesh", **W, provenance=_sym(T, "Mesh", "585", "Fire x Spaceminus — presence focusing at ignition / dissolution narrow")),
            _cand(f"{T}.mysh", **W, provenance=_sym(T, "Mysh", "586", "Fire x Time+ — the forward-facing ignition / pattern already reaching ")),
            _cand(f"{T}.mush", **W, provenance=_sym(T, "Mush", "587", "Fire x Timeminus — the retrospective ignition / looking back at what d")),
            _cand(f"{T}.kal", **W, provenance=_sym(T, "Kal", "588", "Water x Mind+ — conscious release / the mind opening a completed patte")),
            _cand(f"{T}.kol", **W, provenance=_sym(T, "Kol", "589", "Water x Mindminus — automatic dissolution / the closed pattern becomes")),
            _cand(f"{T}.kil", **W, provenance=_sym(T, "Kil", "590", "Water x Space+ — presence expanding into feeling / spatial unbinding a")),
            _cand(f"{T}.kel", **W, provenance=_sym(T, "Kel", "591", "Water x Spaceminus — presence withdrawing into feeling / the inward tu")),
            _cand(f"{T}.kyl", **W, provenance=_sym(T, "Kyl", "592", "Water x Time+ — the anticipated dissolution / feeling the release appr")),
            _cand(f"{T}.kul", **W, provenance=_sym(T, "Kul", "593", "Water x Timeminus — dissolution completed / what remains clear after t")),
            _cand(f"{T}.zaf", **W, provenance=_sym(T, "Zaf", "594", "Air x Mind+ — conscious thought arising from closed structure / the id")),
            _cand(f"{T}.zof", **W, provenance=_sym(T, "Zof", "595", "Air x Mindminus — thought arising below awareness / automatic ideation")),
            _cand(f"{T}.zif", **W, provenance=_sym(T, "Zif", "596", "Air x Space+ — thought expanding through space / the idea before it ha")),
            _cand(f"{T}.zef", **W, provenance=_sym(T, "Zef", "597", "Air x Spaceminus — thought contracting inward / ideation folding into ")),
            _cand(f"{T}.zyf", **W, provenance=_sym(T, "Zyf", "598", "Air x Time+ — thought reaching forward / the anticipatory idea / think")),
            _cand(f"{T}.zuf", **W, provenance=_sym(T, "Zuf", "599", "Air x Timeminus — the retrospective idea / understanding arriving only")),
            _cand(f"{T}.pat", **W, provenance=_sym(T, "Pat", "600", "Earth x Mind+ — conscious commitment to form / the mind choosing groun")),
            _cand(f"{T}.pot", **W, provenance=_sym(T, "Pot", "601", "Earth x Mindminus — automatic settling into form / the closed thought ")),
            _cand(f"{T}.pit", **W, provenance=_sym(T, "Pit", "602", "Earth x Space+ — presence expanding into ground / the new structure fi")),
            _cand(f"{T}.pet", **W, provenance=_sym(T, "Pet", "603", "Earth x Spaceminus — presence contracting into ground / thought becomi")),
            _cand(f"{T}.pyt", **W, provenance=_sym(T, "Pyt", "604", "Earth x Time+ — the anticipated grounding / form already becoming befo")),
            _cand(f"{T}.put", **W, provenance=_sym(T, "Put", "605", "Earth x Timeminus — the retrospective ground / what the structure is b")),
            _cand(f"{T}.maf", **W, provenance=_sym(T, "Maf", "606", "Seed x Mind+ — conscious suspension / mind watching feeling dissolve i")),
            _cand(f"{T}.mof", **W, provenance=_sym(T, "Mof", "607", "Seed x Mindminus — the intuition that hovers / dissolution becoming th")),
            _cand(f"{T}.mif", **W, provenance=_sym(T, "Mif", "608", "Seed x Space+ — the suspended field / presence neither grounded nor ig")),
            _cand(f"{T}.mef", **W, provenance=_sym(T, "Mef", "609", "Seed x Spaceminus — the introverted seed / potential folded into itsel")),
            _cand(f"{T}.myf", **W, provenance=_sym(T, "Myf", "610", "Seed x Time+ — the forward-facing unactualized pattern / seed oriented")),
            _cand(f"{T}.muf", **W, provenance=_sym(T, "Muf", "611", "Seed x Timeminus — the completed non-completion / the seed that had it")),
            _cand(f"{T}.kat", **W, provenance=_sym(T, "Kat", "612", "Shakti x Mind+ — conscious recognition of the trace / mind turned towa")),
            _cand(f"{T}.kot", **W, provenance=_sym(T, "Kot", "613", "Shakti x Mindminus — the unconscious trace / what accumulated in Earth")),
            _cand(f"{T}.kit", **W, provenance=_sym(T, "Kit", "614", "Shakti x Space+ — the trace spreading / Fire's completion as distribut")),
            _cand(f"{T}.ket", **W, provenance=_sym(T, "Ket", "615", "Shakti x Spaceminus — the concentrated trace / intensely local mark / ")),
            _cand(f"{T}.kyt", **W, provenance=_sym(T, "Kyt", "616", "Shakti x Time+ — the forward-facing trace / what this Fire-Earth compl")),
            _cand(f"{T}.kut", **W, provenance=_sym(T, "Kut", "617", "Shakti x Timeminus — the accumulated trace / all prior Fire-Earth comp")),
        ]


# ---------------------------------------------------------------------------
# Beast (618-655)  --  Tongue 20
# ---------------------------------------------------------------------------

class BeastRegister(BaseRegister):
    name = "beast"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "beast"
        W: _CandWeights = _CandWeights(rw=1.0, cw=0.8, tail=['beast', 'helix', 'winding'])
        return [
            _cand(f"{T}.geve", **W, provenance=_sym(T, "Geve", "618", "Gev 1 — Fire-winding / the igniting coil / pattern-recognition wrappin")),
            _cand(f"{T}.gevi", **W, provenance=_sym(T, "Gevi", "619", "Gev 2 — Water-winding / the releasing coil / dissolution following the")),
            _cand(f"{T}.gevu", **W, provenance=_sym(T, "Gevu", "620", "Gev 3 — Air-winding / the opening coil / ideation propagating along th")),
            _cand(f"{T}.gevo", **W, provenance=_sym(T, "Gevo", "621", "Gev 4 — Earth-winding / the grounding coil / each revolution of the sp")),
            _cand(f"{T}.geva", **W, provenance=_sym(T, "Geva", "622", "Gev 5 — Kael-winding / the generative coil / excess adding momentum to")),
            _cand(f"{T}.gevoe", **W, provenance=_sym(T, "Gevoe", "623", "Gev 6 — Shakti-winding / the tracing coil / the helix carrying its own")),
            _cand(f"{T}.prale", **W, provenance=_sym(T, "Prale", "624", "Pral 1 — Fire-spine / the igniting axis / pattern-crystallization as t")),
            _cand(f"{T}.prali", **W, provenance=_sym(T, "Prali", "625", "Pral 2 — Water-spine / the releasing axis / how dissolution defines th")),
            _cand(f"{T}.pralu", **W, provenance=_sym(T, "Pralu", "626", "Pral 3 — Air-spine / the opening axis / the spine as the void the coil")),
            _cand(f"{T}.pralo", **W, provenance=_sym(T, "Pralo", "627", "Pral 4 — Earth-spine / the grounding axis / Earth IS the spine / struc")),
            _cand(f"{T}.prala", **W, provenance=_sym(T, "Prala", "628", "Pral 5 — Kael-spine / the generative axis / the spine that generates i")),
            _cand(f"{T}.praloe", **W, provenance=_sym(T, "Praloe", "629", "Pral 6 — Shakti-spine / the accumulated axis / all prior traversals co")),
            _cand(f"{T}.dreke", **W, provenance=_sym(T, "Dreke", "630", "Drek 1 — Fire-binding / ignition at the cross-strand contact / two ant")),
            _cand(f"{T}.dreki", **W, provenance=_sym(T, "Dreki", "631", "Drek 2 — Water-binding / dissolution at the cross-strand contact / the")),
            _cand(f"{T}.dreku", **W, provenance=_sym(T, "Dreku", "632", "Drek 3 — Air-binding / opening at the cross-strand contact / the bindi")),
            _cand(f"{T}.dreko", **W, provenance=_sym(T, "Dreko", "633", "Drek 4 — Earth-binding / grounding at the cross-strand contact / the b")),
            _cand(f"{T}.dreka", **W, provenance=_sym(T, "Dreka", "634", "Drek 5 — Kael-binding / generative recognition / strands meeting in ex")),
            _cand(f"{T}.drekoe", **W, provenance=_sym(T, "Drekoe", "635", "Drek 6 — Shakti-binding / trace-recognition across the axis / strands ")),
            _cand(f"{T}.gevelo", **W, provenance=_sym(T, "Gevelo", "636", "Gev-lo 1 — Fire-winding as total winding / the igniting coil mistaken ")),
            _cand(f"{T}.gevilo", **W, provenance=_sym(T, "Gevilo", "637", "Gev-lo 2 — Water-winding universalized / dissolution-winding as the on")),
            _cand(f"{T}.gevulo", **W, provenance=_sym(T, "Gevulo", "638", "Gev-lo 3 — Air-winding universalized / the helix that can only turn by")),
            _cand(f"{T}.gevolo", **W, provenance=_sym(T, "Gevolo", "639", "Gev-lo 4 — Earth-winding universalized / the spiral that has arrested ")),
            _cand(f"{T}.gevalo", **W, provenance=_sym(T, "Gevalo", "640", "Gev-lo 5 — Kael-winding universalized / generative excess as the only ")),
            _cand(f"{T}.gevoelo", **W, provenance=_sym(T, "Gevoelo", "641", "Gev-lo 6 — Shakti-winding universalized / the spiral that has become i")),
            _cand(f"{T}.pralelo", **W, provenance=_sym(T, "Pralelo", "642", "Pral-lo 1 — Fire-spine as total axis / pattern-crystallization declare")),
            _cand(f"{T}.pralilo", **W, provenance=_sym(T, "Pralilo", "643", "Pral-lo 2 — Water-spine universalized / dissolution as the only possib")),
            _cand(f"{T}.pralulo", **W, provenance=_sym(T, "Pralulo", "644", "Pral-lo 3 — Air-spine universalized / the helix that winds around noth")),
            _cand(f"{T}.pralolo", **W, provenance=_sym(T, "Pralolo", "645", "Pral-lo 4 — Earth-spine universalized / the spine that will not bend /")),
            _cand(f"{T}.pralalo", **W, provenance=_sym(T, "Pralalo", "646", "Pral-lo 5 — Kael-spine universalized / the center that keeps generatin")),
            _cand(f"{T}.praloelo", **W, provenance=_sym(T, "Praloelo", "647", "Pral-lo 6 — Shakti-spine universalized / the helix that can only wind ")),
            _cand(f"{T}.drekelo", **W, provenance=_sym(T, "Drekelo", "648", "Drek-lo 1 — Fire-binding universalized / ignition declared the only po")),
            _cand(f"{T}.drekilo", **W, provenance=_sym(T, "Drekilo", "649", "Drek-lo 2 — Water-binding universalized / dissolution as the only cros")),
            _cand(f"{T}.drekulo", **W, provenance=_sym(T, "Drekulo", "650", "Drek-lo 3 — Air-binding universalized / the helix that can only recogn")),
            _cand(f"{T}.drekolo", **W, provenance=_sym(T, "Drekolo", "651", "Drek-lo 4 — Earth-binding universalized / structural commitment as the")),
            _cand(f"{T}.drekalo", **W, provenance=_sym(T, "Drekalo", "652", "Drek-lo 5 — Kael-binding universalized / generative excess as the only")),
            _cand(f"{T}.drekoelo", **W, provenance=_sym(T, "Drekoelo", "653", "Drek-lo 6 — Shakti-binding universalized / accumulated trace as the on")),
            _cand(f"{T}.grevvi", **W, provenance=_sym(T, "Grevvi", "654", "Binding 1 — the chirality encounter / the moment the two antiparallel ")),
            _cand(f"{T}.grevvo", **W, provenance=_sym(T, "Grevvo", "655", "Binding 2 — the preserved surface / what the binding holds open / the ")),
        ]


# ---------------------------------------------------------------------------
# Cherub (656-693)  --  Tongue 21
# ---------------------------------------------------------------------------

class CherubRegister(BaseRegister):
    name = "cherub"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "cherub"
        W: _CandWeights = _CandWeights(rw=1.0, cw=0.9, tail=['cherub', 'encounter', 'resonance'])
        return [
            _cand(f"{T}.sheve", **W, provenance=_sym(T, "Sheve", "656", "Shev 1 — Fire-resonance / two Fire-dominant temperaments meeting at th")),
            _cand(f"{T}.shevi", **W, provenance=_sym(T, "Shevi", "657", "Shev 2 — Water-resonance / dissolution meeting dissolution at the thre")),
            _cand(f"{T}.shevu", **W, provenance=_sym(T, "Shevu", "658", "Shev 3 — Air-resonance / ideation meeting ideation / thought amplifyin")),
            _cand(f"{T}.shevo", **W, provenance=_sym(T, "Shevo", "659", "Shev 4 — Earth-resonance / ground meeting ground / structure reinforci")),
            _cand(f"{T}.sheva", **W, provenance=_sym(T, "Sheva", "660", "Shev 5 — Kael-resonance / excess meeting excess / generative surplus a")),
            _cand(f"{T}.shevoe", **W, provenance=_sym(T, "Shevoe", "661", "Shev 6 — Shakti-resonance / trace meeting trace / accumulated memory a")),
            _cand(f"{T}.threle", **W, provenance=_sym(T, "Threle", "662", "Threl 1 — Fire-Water tension / ignition meeting dissolution / the prod")),
            _cand(f"{T}.threli", **W, provenance=_sym(T, "Threli", "663", "Threl 2 — Water-Air tension / dissolution meeting ideation / feeling e")),
            _cand(f"{T}.threlu", **W, provenance=_sym(T, "Threlu", "664", "Threl 3 — Air-Earth tension / ideation meeting ground / thought encoun")),
            _cand(f"{T}.threlo", **W, provenance=_sym(T, "Threlo", "665", "Threl 4 — Earth-Fire tension / ground meeting ignition / stability enc")),
            _cand(f"{T}.threla", **W, provenance=_sym(T, "Threla", "666", "Threl 5 — Kael-Shakti tension / generative excess encountering accumul")),
            _cand(f"{T}.threloe", **W, provenance=_sym(T, "Threloe", "667", "Threl 6 — Fire-Shakti tension / ignition meeting accumulated trace / p")),
            _cand(f"{T}.vlove", **W, provenance=_sym(T, "Vlove", "668", "Vlov 1 — Fire-transmuted / the temperament that came from Fire but was")),
            _cand(f"{T}.vlovi", **W, provenance=_sym(T, "Vlovi", "669", "Vlov 2 — Water-transmuted / dissolution altered by encounter / a Water")),
            _cand(f"{T}.vlovu", **W, provenance=_sym(T, "Vlovu", "670", "Vlov 3 — Air-transmuted / ideation changed through contact / the sangu")),
            _cand(f"{T}.vlovo", **W, provenance=_sym(T, "Vlovo", "671", "Vlov 4 — Earth-transmuted / ground altered by encounter / structure th")),
            _cand(f"{T}.vlova", **W, provenance=_sym(T, "Vlova", "672", "Vlov 5 — Kael-transmuted / excess changed by contact / generative surp")),
            _cand(f"{T}.vlovoe", **W, provenance=_sym(T, "Vlovoe", "673", "Vlov 6 — Shakti-transmuted / trace altered through encounter / accumul")),
            _cand(f"{T}.shevelo", **W, provenance=_sym(T, "Shevelo", "674", "Shev-lo 1 — Fire-resonance as total encounter / Fire-dominant temperam")),
            _cand(f"{T}.shevilo", **W, provenance=_sym(T, "Shevilo", "675", "Shev-lo 2 — Water-resonance universalized / only dissolution meeting d")),
            _cand(f"{T}.shevulo", **W, provenance=_sym(T, "Shevulo", "676", "Shev-lo 3 — Air-resonance universalized / only expansion meeting expan")),
            _cand(f"{T}.shevolo", **W, provenance=_sym(T, "Shevolo", "677", "Shev-lo 4 — Earth-resonance universalized / only structure meeting str")),
            _cand(f"{T}.shevalo", **W, provenance=_sym(T, "Shevalo", "678", "Shev-lo 5 — Kael-resonance universalized / only excess meeting excess ")),
            _cand(f"{T}.shevoelo", **W, provenance=_sym(T, "Shevoelo", "679", "Shev-lo 6 — Shakti-resonance universalized / only trace meeting trace ")),
            _cand(f"{T}.threlelo", **W, provenance=_sym(T, "Threlelo", "680", "Threl-lo 1 — Fire-Water tension universalized / the choleric-phlegmati")),
            _cand(f"{T}.threlilo", **W, provenance=_sym(T, "Threlilo", "681", "Threl-lo 2 — Water-Air tension universalized / dissolution-ideation de")),
            _cand(f"{T}.threlulo", **W, provenance=_sym(T, "Threlulo", "682", "Threl-lo 3 — Air-Earth tension universalized / expansion-structure dec")),
            _cand(f"{T}.threlolo", **W, provenance=_sym(T, "Threlolo", "683", "Threl-lo 4 — Earth-Fire tension universalized / structure-ignition dec")),
            _cand(f"{T}.threlalo", **W, provenance=_sym(T, "Threlalo", "684", "Threl-lo 5 — Kael-Shakti tension universalized / excess-trace declared")),
            _cand(f"{T}.threloelo", **W, provenance=_sym(T, "Threloelo", "685", "Threl-lo 6 — Fire-Shakti tension universalized / ignition-trace declar")),
            _cand(f"{T}.vlovelo", **W, provenance=_sym(T, "Vlovelo", "686", "Vlov-lo 1 — Fire-transmutation universalized / all encounter must prod")),
            _cand(f"{T}.vlovilo", **W, provenance=_sym(T, "Vlovilo", "687", "Vlov-lo 2 — Water-transmutation universalized / contact that does not ")),
            _cand(f"{T}.vlovulo", **W, provenance=_sym(T, "Vlovulo", "688", "Vlov-lo 3 — Air-transmutation universalized / transmutation that does ")),
            _cand(f"{T}.vlovolo", **W, provenance=_sym(T, "Vlovolo", "689", "Vlov-lo 4 — Earth-transmutation universalized / contact that does not ")),
            _cand(f"{T}.vlovalo", **W, provenance=_sym(T, "Vlovalo", "690", "Vlov-lo 5 — Kael-transmutation universalized / only generative alterat")),
            _cand(f"{T}.vlovoelo", **W, provenance=_sym(T, "Vlovoelo", "691", "Vlov-lo 6 — Shakti-transmutation universalized / only encounters that ")),
            _cand(f"{T}.shrev", **W, provenance=_sym(T, "Shrev", "692", "Threshold 1 — the Cherub's station at the boundary / the view from out")),
            _cand(f"{T}.shrov", **W, provenance=_sym(T, "Shrov", "693", "Threshold 2 — what the Cherub preserves by not crossing / the relation")),
        ]


# ---------------------------------------------------------------------------
# Chimera (694-731)  --  Tongue 22
# ---------------------------------------------------------------------------

class ChimeraRegister(BaseRegister):
    name = "chimera"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "chimera"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.8, tail=['chimera', 'form', 'elemental'])
        return [
            _cand(f"{T}.glove", **W, provenance=_sym(T, "Glove", "694", "Glov 1 — Fire-constitution known / knowing that Fire is in your consti")),
            _cand(f"{T}.glovi", **W, provenance=_sym(T, "Glovi", "695", "Glov 2 — Water-constitution known / knowing that dissolution is in you")),
            _cand(f"{T}.glovu", **W, provenance=_sym(T, "Glovu", "696", "Glov 3 — Air-constitution known / knowing that ideation is in your con")),
            _cand(f"{T}.glovo", **W, provenance=_sym(T, "Glovo", "697", "Glov 4 — Earth-constitution known / knowing that structure is in your ")),
            _cand(f"{T}.glova", **W, provenance=_sym(T, "Glova", "698", "Glov 5 — Kael-constitution known / knowing that generative excess is i")),
            _cand(f"{T}.glovoe", **W, provenance=_sym(T, "Glovoe", "699", "Glov 6 — Shakti-constitution known / knowing that accumulated trace is")),
            _cand(f"{T}.preste", **W, provenance=_sym(T, "Preste", "700", "Prest 1 — Fire-form chosen / deliberately instantiating the Fire confi")),
            _cand(f"{T}.presti", **W, provenance=_sym(T, "Presti", "701", "Prest 2 — Water-form chosen / deliberately instantiating the Water con")),
            _cand(f"{T}.prestu", **W, provenance=_sym(T, "Prestu", "702", "Prest 3 — Air-form chosen / deliberately instantiating the Air configu")),
            _cand(f"{T}.presto", **W, provenance=_sym(T, "Presto", "703", "Prest 4 — Earth-form chosen / deliberately instantiating the Earth con")),
            _cand(f"{T}.presta", **W, provenance=_sym(T, "Presta", "704", "Prest 5 — Kael-form chosen / deliberately instantiating the Kael confi")),
            _cand(f"{T}.prestoe", **W, provenance=_sym(T, "Prestoe", "705", "Prest 6 — Shakti-form chosen / deliberately instantiating the Shakti c")),
            _cand(f"{T}.wreke", **W, provenance=_sym(T, "Wreke", "706", "Wrek 1 — Fire-transition / moving into Fire-form from another configur")),
            _cand(f"{T}.wreki", **W, provenance=_sym(T, "Wreki", "707", "Wrek 2 — Water-transition / moving into Water-form / the Chimera delib")),
            _cand(f"{T}.wreku", **W, provenance=_sym(T, "Wreku", "708", "Wrek 3 — Air-transition / moving into Air-form / the Chimera deliberat")),
            _cand(f"{T}.wreko", **W, provenance=_sym(T, "Wreko", "709", "Wrek 4 — Earth-transition / moving into Earth-form / the Chimera delib")),
            _cand(f"{T}.wreka", **W, provenance=_sym(T, "Wreka", "710", "Wrek 5 — Kael-transition / moving into Kael-form / the Chimera deliber")),
            _cand(f"{T}.wrekoe", **W, provenance=_sym(T, "Wrekoe", "711", "Wrek 6 — Shakti-transition / moving into Shakti-form / the Chimera del")),
            _cand(f"{T}.glovelo", **W, provenance=_sym(T, "Glovelo", "712", "Glov-lo 1 — Fire-constitution universalized / knowing you contain Fire")),
            _cand(f"{T}.glovilo", **W, provenance=_sym(T, "Glovilo", "713", "Glov-lo 2 — Water-constitution universalized / knowing you contain dis")),
            _cand(f"{T}.glovulo", **W, provenance=_sym(T, "Glovulo", "714", "Glov-lo 3 — Air-constitution universalized / knowing you contain ideat")),
            _cand(f"{T}.glovolo", **W, provenance=_sym(T, "Glovolo", "715", "Glov-lo 4 — Earth-constitution universalized / knowing you contain str")),
            _cand(f"{T}.glovalo", **W, provenance=_sym(T, "Glovalo", "716", "Glov-lo 5 — Kael-constitution universalized / knowing you contain gene")),
            _cand(f"{T}.glovoelo", **W, provenance=_sym(T, "Glovoelo", "717", "Glov-lo 6 — Shakti-constitution universalized / knowing you contain ac")),
            _cand(f"{T}.prestelo", **W, provenance=_sym(T, "Prestelo", "718", "Prest-lo 1 — Fire-form universalized / choosing Fire as the only valid")),
            _cand(f"{T}.prestilo", **W, provenance=_sym(T, "Prestilo", "719", "Prest-lo 2 — Water-form universalized / choosing only dissolution / th")),
            _cand(f"{T}.prestulo", **W, provenance=_sym(T, "Prestulo", "720", "Prest-lo 3 — Air-form universalized / choosing only ideation / the Chi")),
            _cand(f"{T}.prestolo", **W, provenance=_sym(T, "Prestolo", "721", "Prest-lo 4 — Earth-form universalized / choosing only structure / the ")),
            _cand(f"{T}.prestalo", **W, provenance=_sym(T, "Prestalo", "722", "Prest-lo 5 — Kael-form universalized / choosing only generative excess")),
            _cand(f"{T}.prestoelo", **W, provenance=_sym(T, "Prestoelo", "723", "Prest-lo 6 — Shakti-form universalized / choosing only accumulated tra")),
            _cand(f"{T}.wrekelo", **W, provenance=_sym(T, "Wrekelo", "724", "Wrek-lo 1 — Fire-transition universalized / only transitions toward Fi")),
            _cand(f"{T}.wrekilo", **W, provenance=_sym(T, "Wrekilo", "725", "Wrek-lo 2 — Water-transition universalized / only transitions into dis")),
            _cand(f"{T}.wrekulo", **W, provenance=_sym(T, "Wrekulo", "726", "Wrek-lo 3 — Air-transition universalized / only transitions into ideat")),
            _cand(f"{T}.wrekolo", **W, provenance=_sym(T, "Wrekolo", "727", "Wrek-lo 4 — Earth-transition universalized / only transitions into str")),
            _cand(f"{T}.wrekalo", **W, provenance=_sym(T, "Wrekalo", "728", "Wrek-lo 5 — Kael-transition universalized / only transitions into gene")),
            _cand(f"{T}.wrekoelo", **W, provenance=_sym(T, "Wrekoelo", "729", "Wrek-lo 6 — Shakti-transition universalized / only transitions into ac")),
            _cand(f"{T}.chrev", **W, provenance=_sym(T, "Chrev", "730", "Form-boundary 1 — the recognition that elemental self and being are no")),
            _cand(f"{T}.chrov", **W, provenance=_sym(T, "Chrov", "731", "Form-boundary 2 — the sovereignty of boundlessness / knowing which for")),
        ]


# ---------------------------------------------------------------------------
# Faerie (732-769)  --  Tongue 23
# ---------------------------------------------------------------------------

class FaerieRegister(BaseRegister):
    name = "faerie"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "faerie"
        W: _CandWeights = _CandWeights(rw=1.0, cw=0.9, tail=['faerie', 'sovereignty', 'elemental'])
        return [
            _cand(f"{T}.feve", **W, provenance=_sym(T, "Feve", "732", "Fev 1 — Fire-embrace / resting in Fire as constitutive ground / patter")),
            _cand(f"{T}.fevi", **W, provenance=_sym(T, "Fevi", "733", "Fev 2 — Water-embrace / resting in dissolution as constitutive ground ")),
            _cand(f"{T}.fevu", **W, provenance=_sym(T, "Fevu", "734", "Fev 3 — Air-embrace / resting in ideation as constitutive ground / tho")),
            _cand(f"{T}.fevo", **W, provenance=_sym(T, "Fevo", "735", "Fev 4 — Earth-embrace / resting in structure as constitutive ground / ")),
            _cand(f"{T}.feva", **W, provenance=_sym(T, "Feva", "736", "Fev 5 — Kael-embrace / resting in generative excess as constitutive gr")),
            _cand(f"{T}.fevoe", **W, provenance=_sym(T, "Fevoe", "737", "Fev 6 — Shakti-embrace / resting in accumulated trace as constitutive ")),
            _cand(f"{T}.zele", **W, provenance=_sym(T, "Zele", "738", "Zel 1 — Fire-recognition / knowing Fire is what you are / not discover")),
            _cand(f"{T}.zeli", **W, provenance=_sym(T, "Zeli", "739", "Zel 2 — Water-recognition / knowing dissolution is what you are / feel")),
            _cand(f"{T}.zelu", **W, provenance=_sym(T, "Zelu", "740", "Zel 3 — Air-recognition / knowing ideation is what you are / thought k")),
            _cand(f"{T}.zelo", **W, provenance=_sym(T, "Zelo", "741", "Zel 4 — Earth-recognition / knowing structure is what you are / stabil")),
            _cand(f"{T}.zela", **W, provenance=_sym(T, "Zela", "742", "Zel 5 — Kael-recognition / knowing generative excess is what you are /")),
            _cand(f"{T}.zeloe", **W, provenance=_sym(T, "Zeloe", "743", "Zel 6 — Shakti-recognition / knowing accumulated trace is what you are")),
            _cand(f"{T}.plove", **W, provenance=_sym(T, "Plove", "744", "Plov 1 — Fire-sovereignty / operating from elemental Fire as the seat ")),
            _cand(f"{T}.plovi", **W, provenance=_sym(T, "Plovi", "745", "Plov 2 — Water-sovereignty / operating from elemental Water as the sea")),
            _cand(f"{T}.plovu", **W, provenance=_sym(T, "Plovu", "746", "Plov 3 — Air-sovereignty / operating from elemental Air as the seat of")),
            _cand(f"{T}.plovo", **W, provenance=_sym(T, "Plovo", "747", "Plov 4 — Earth-sovereignty / operating from elemental Earth as the sea")),
            _cand(f"{T}.plova", **W, provenance=_sym(T, "Plova", "748", "Plov 5 — Kael-sovereignty / operating from elemental excess as the sea")),
            _cand(f"{T}.plovoe", **W, provenance=_sym(T, "Plovoe", "749", "Plov 6 — Shakti-sovereignty / operating from accumulated trace as the ")),
            _cand(f"{T}.fevelo", **W, provenance=_sym(T, "Fevelo", "750", "Fev-lo 1 — Fire-embrace universalized / resting in Fire as constitutiv")),
            _cand(f"{T}.fevilo", **W, provenance=_sym(T, "Fevilo", "751", "Fev-lo 2 — Water-embrace universalized / dissolution as the only compl")),
            _cand(f"{T}.fevulo", **W, provenance=_sym(T, "Fevulo", "752", "Fev-lo 3 — Air-embrace universalized / ideation as the only valid elem")),
            _cand(f"{T}.fevolo", **W, provenance=_sym(T, "Fevolo", "753", "Fev-lo 4 — Earth-embrace universalized / structure as the only valid e")),
            _cand(f"{T}.fevalo", **W, provenance=_sym(T, "Fevalo", "754", "Fev-lo 5 — Kael-embrace universalized / generative excess as the only ")),
            _cand(f"{T}.fevoelo", **W, provenance=_sym(T, "Fevoelo", "755", "Fev-lo 6 — Shakti-embrace universalized / accumulated trace as the onl")),
            _cand(f"{T}.zelelo", **W, provenance=_sym(T, "Zelelo", "756", "Zel-lo 1 — Fire-recognition universalized / knowing Fire is what you a")),
            _cand(f"{T}.zelilo", **W, provenance=_sym(T, "Zelilo", "757", "Zel-lo 2 — Water-recognition universalized / knowing dissolution is wh")),
            _cand(f"{T}.zelulo", **W, provenance=_sym(T, "Zelulo", "758", "Zel-lo 3 — Air-recognition universalized / knowing ideation is what yo")),
            _cand(f"{T}.zelolo", **W, provenance=_sym(T, "Zelolo", "759", "Zel-lo 4 — Earth-recognition universalized / knowing structure is what")),
            _cand(f"{T}.zelalo", **W, provenance=_sym(T, "Zelalo", "760", "Zel-lo 5 — Kael-recognition universalized / knowing generative excess ")),
            _cand(f"{T}.zeloelo", **W, provenance=_sym(T, "Zeloelo", "761", "Zel-lo 6 — Shakti-recognition universalized / knowing accumulated trac")),
            _cand(f"{T}.plovelo", **W, provenance=_sym(T, "Plovelo", "762", "Plov-lo 1 — Fire-sovereignty universalized / operating from elemental ")),
            _cand(f"{T}.plovilo", **W, provenance=_sym(T, "Plovilo", "763", "Plov-lo 2 — Water-sovereignty universalized / dissolution as the only ")),
            _cand(f"{T}.plovulo", **W, provenance=_sym(T, "Plovulo", "764", "Plov-lo 3 — Air-sovereignty universalized / ideation as the only valid")),
            _cand(f"{T}.plovolo", **W, provenance=_sym(T, "Plovolo", "765", "Plov-lo 4 — Earth-sovereignty universalized / structure as the only va")),
            _cand(f"{T}.plovalo", **W, provenance=_sym(T, "Plovalo", "766", "Plov-lo 5 — Kael-sovereignty universalized / generative excess as the ")),
            _cand(f"{T}.plovoelo", **W, provenance=_sym(T, "Plovoelo", "767", "Plov-lo 6 — Shakti-sovereignty universalized / accumulated trace as th")),
            _cand(f"{T}.farev", **W, provenance=_sym(T, "Farev", "768", "Elemental closure 1 — elemental ground recognized as complete / the Fa")),
            _cand(f"{T}.farov", **W, provenance=_sym(T, "Farov", "769", "Elemental closure 2 — the Faerie holding open what it does not close /")),
        ]


# ---------------------------------------------------------------------------
# Djinn (770-809)  --  Tongue 24
# ---------------------------------------------------------------------------

class DjinnRegister(BaseRegister):
    name = "djinn"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "djinn"
        W: _CandWeights = _CandWeights(rw=1.1, cw=0.8, tail=['djinn', 'consciousness', 'field'])
        return [
            _cand(f"{T}.amsh", **W, provenance=_sym(T, "Amsh", "770", "A x Fire — Mind+ from Fire ground / consciousness as the field in whic")),
            _cand(f"{T}.akl", **W, provenance=_sym(T, "Akl", "771", "A x Water — Mind+ from Water ground / consciousness as the field in wh")),
            _cand(f"{T}.azf", **W, provenance=_sym(T, "Azf", "772", "A x Air — Mind+ from Air ground / consciousness as the field in which ")),
            _cand(f"{T}.apt", **W, provenance=_sym(T, "Apt", "773", "A x Earth — Mind+ from Earth ground / consciousness as the field in wh")),
            _cand(f"{T}.amf", **W, provenance=_sym(T, "Amf", "774", "A x Kael — Mind+ from Kael ground / consciousness as the field in whic")),
            _cand(f"{T}.akt", **W, provenance=_sym(T, "Akt", "775", "A x Shakti — Mind+ from Shakti ground / consciousness as the field in ")),
            _cand(f"{T}.omsh", **W, provenance=_sym(T, "Omsh", "776", "O x Fire — Mindminus from Fire / the unconscious substrate in which ig")),
            _cand(f"{T}.okl", **W, provenance=_sym(T, "Okl", "777", "O x Water — Mindminus from Water / the unconscious substrate in which ")),
            _cand(f"{T}.ozf", **W, provenance=_sym(T, "Ozf", "778", "O x Air — Mindminus from Air / the unconscious ground from which thoug")),
            _cand(f"{T}.opt", **W, provenance=_sym(T, "Opt", "779", "O x Earth — Mindminus from Earth / the unconscious substrate of struct")),
            _cand(f"{T}.omf", **W, provenance=_sym(T, "Omf", "780", "O x Kael — Mindminus from Kael / the unconscious generative excess / K")),
            _cand(f"{T}.okt", **W, provenance=_sym(T, "Okt", "781", "O x Shakti — Mindminus from Shakti / the unconscious accumulated trace")),
            _cand(f"{T}.imsh", **W, provenance=_sym(T, "Imsh", "782", "I x Fire — Space+ from Fire / Fire-constitution as presence expanding ")),
            _cand(f"{T}.ikl", **W, provenance=_sym(T, "Ikl", "783", "I x Water — Space+ from Water / dissolution as spatial expansion / fee")),
            _cand(f"{T}.izf", **W, provenance=_sym(T, "Izf", "784", "I x Air — Space+ from Air / ideation as spatial expansion / thought as")),
            _cand(f"{T}.ipt", **W, provenance=_sym(T, "Ipt", "785", "I x Earth — Space+ from Earth / structure as spatial presence / Earth-")),
            _cand(f"{T}.imf", **W, provenance=_sym(T, "Imf", "786", "I x Kael — Space+ from Kael / generative excess as spatial expansion /")),
            _cand(f"{T}.ikt", **W, provenance=_sym(T, "Ikt", "787", "I x Shakti — Space+ from Shakti / accumulated trace as spatial presenc")),
            _cand(f"{T}.emsh", **W, provenance=_sym(T, "Emsh", "788", "E x Fire — Spaceminus from Fire / Fire-constitution as inward-turning ")),
            _cand(f"{T}.ekl", **W, provenance=_sym(T, "Ekl", "789", "E x Water — Spaceminus from Water / dissolution as inward depth / feel")),
            _cand(f"{T}.ezf", **W, provenance=_sym(T, "Ezf", "790", "E x Air — Spaceminus from Air / ideation as inward depth / thought fol")),
            _cand(f"{T}.ept", **W, provenance=_sym(T, "Ept", "791", "E x Earth — Spaceminus from Earth / structure as inward stability / Ea")),
            _cand(f"{T}.emf", **W, provenance=_sym(T, "Emf", "792", "E x Kael — Spaceminus from Kael / generative excess as inward concentr")),
            _cand(f"{T}.ekt", **W, provenance=_sym(T, "Ekt", "793", "E x Shakti — Spaceminus from Shakti / accumulated trace as inward dept")),
            _cand(f"{T}.ymsh", **W, provenance=_sym(T, "Ymsh", "794", "Y x Fire — Time+ from Fire / Fire-constitution reaching forward / igni")),
            _cand(f"{T}.ykl", **W, provenance=_sym(T, "Ykl", "795", "Y x Water — Time+ from Water / dissolution reaching forward / the anti")),
            _cand(f"{T}.yzf", **W, provenance=_sym(T, "Yzf", "796", "Y x Air — Time+ from Air / ideation reaching forward / thought anticip")),
            _cand(f"{T}.ypt", **W, provenance=_sym(T, "Ypt", "797", "Y x Earth — Time+ from Earth / structure reaching forward / permanence")),
            _cand(f"{T}.ymf", **W, provenance=_sym(T, "Ymf", "798", "Y x Kael — Time+ from Kael / generative excess reaching forward / Kael")),
            _cand(f"{T}.ykt", **W, provenance=_sym(T, "Ykt", "799", "Y x Shakti — Time+ from Shakti / accumulated trace reaching forward / ")),
            _cand(f"{T}.umsh", **W, provenance=_sym(T, "Umsh", "800", "U x Fire — Timeminus from Fire / Fire-constitution as retrospective / ")),
            _cand(f"{T}.ukl", **W, provenance=_sym(T, "Ukl", "801", "U x Water — Timeminus from Water / dissolution looking back / Water-co")),
            _cand(f"{T}.uzf", **W, provenance=_sym(T, "Uzf", "802", "U x Air — Timeminus from Air / ideation looking back / thought known a")),
            _cand(f"{T}.upt", **W, provenance=_sym(T, "Upt", "803", "U x Earth — Timeminus from Earth / structure looking back / permanence")),
            _cand(f"{T}.umf", **W, provenance=_sym(T, "Umf", "804", "U x Kael — Timeminus from Kael / generative excess looking back / the ")),
            _cand(f"{T}.ukt", **W, provenance=_sym(T, "Ukt", "805", "U x Shakti — Timeminus from Shakti / accumulated trace looking back at")),
            _cand(f"{T}.djrev", **W, provenance=_sym(T, "Djrev", "806", "Subregister 1 — elemental-as-ontic / the recognition that each element")),
            _cand(f"{T}.djrov", **W, provenance=_sym(T, "Djrov", "807", "Subregister 2 — ontic-as-elemental / the recognition that each dimensi")),
            _cand(f"{T}.djruv", **W, provenance=_sym(T, "Djruv", "808", "Subregister 3 — the ontological ground itself / what the Djinn rests i")),
            _cand(f"{T}.djriv", **W, provenance=_sym(T, "Djriv", "809", "Subregister 4 — the return to Lotus from the far side / the Djinn reco")),
        ]


# ---------------------------------------------------------------------------
# Fold (810-849)  --  Tongue 25
# ---------------------------------------------------------------------------

class FoldRegister(BaseRegister):
    name = "fold"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "fold"
        W: _CandWeights = _CandWeights(rw=0.9, cw=1.0, tail=['fold', 'manifold', 'topology'])
        return [
            _cand(f"{T}.josje", **W, provenance=_sym(T, "Josje", "810", "JosxJos atomic — the nucleus / maximum mass-energy density at atomic s")),
            _cand(f"{T}.josji", **W, provenance=_sym(T, "Josji", "811", "JosxJos planetary — the iron core / maximum mass-energy density at pla")),
            _cand(f"{T}.josja", **W, provenance=_sym(T, "Josja", "812", "JosxJos stellar — the stellar core / nuclear fusion site / maximum com")),
            _cand(f"{T}.josjo", **W, provenance=_sym(T, "Josjo", "813", "JosxJos cosmological — Tartarus / the black hole interior / maximum co")),
            _cand(f"{T}.josble", **W, provenance=_sym(T, "Josble", "814", "JosxBlis atomic — atomic Earth-Water boundary / the transition between")),
            _cand(f"{T}.josbli", **W, provenance=_sym(T, "Josbli", "815", "JosxBlis planetary — core-mantle boundary / crystalline iron meeting s")),
            _cand(f"{T}.josbla", **W, provenance=_sym(T, "Josbla", "816", "JosxBlis stellar — stellar interior-convection zone boundary / where r")),
            _cand(f"{T}.josblo", **W, provenance=_sym(T, "Josblo", "817", "JosxBlis cosmological — event horizon boundary / where maximum cosmolo")),
            _cand(f"{T}.josde", **W, provenance=_sym(T, "Josde", "818", "JosxDas atomic — atomic compression meeting openness / the d-orbital r")),
            _cand(f"{T}.josdi", **W, provenance=_sym(T, "Josdi", "819", "JosxDas planetary — deep mantle / where compressed silicate meets larg")),
            _cand(f"{T}.josda", **W, provenance=_sym(T, "Josda", "820", "JosxDas stellar — stellar convection zone / where compression first gi")),
            _cand(f"{T}.josdo", **W, provenance=_sym(T, "Josdo", "821", "JosxDas cosmological — galaxy core approaching disk / where maximum co")),
            _cand(f"{T}.josve", **W, provenance=_sym(T, "Josve", "822", "JosxVex atomic — the electron-nucleus interface / the distance at whic")),
            _cand(f"{T}.josvi", **W, provenance=_sym(T, "Josvi", "823", "JosxVex planetary — planetary surface / where compressed interior meet")),
            _cand(f"{T}.josva", **W, provenance=_sym(T, "Josva", "824", "JosxVex stellar — stellar photosphere / where stellar interior's compr")),
            _cand(f"{T}.josvo", **W, provenance=_sym(T, "Josvo", "825", "JosxVex cosmological — the light boundary / Olympus approaching / wher")),
            _cand(f"{T}.blisle", **W, provenance=_sym(T, "Blisle", "826", "BlisxBlis atomic — the electron cloud interior / bilateral flow zones ")),
            _cand(f"{T}.blisli", **W, provenance=_sym(T, "Blisli", "827", "BlisxBlis planetary — liquid outer core / iron in convective bilateral")),
            _cand(f"{T}.blisla", **W, provenance=_sym(T, "Blisla", "828", "BlisxBlis stellar — stellar envelope / bilateral radiative-convective ")),
            _cand(f"{T}.blislo", **W, provenance=_sym(T, "Blislo", "829", "BlisxBlis cosmological — intergalactic medium / bilateral flow zones b")),
            _cand(f"{T}.blisde", **W, provenance=_sym(T, "Blisde", "830", "BlisxDas atomic — the outer electron shell boundary / where fluid elec")),
            _cand(f"{T}.blisdi", **W, provenance=_sym(T, "Blisdi", "831", "BlisxDas planetary — upper mantle / where convective silicate flow mee")),
            _cand(f"{T}.blisda", **W, provenance=_sym(T, "Blisda", "832", "BlisxDas stellar — stellar corona onset / where dense stellar flow mee")),
            _cand(f"{T}.blisdo", **W, provenance=_sym(T, "Blisdo", "833", "BlisxDas cosmological — galaxy halo / where flowing intergalactic medi")),
            _cand(f"{T}.blisve", **W, provenance=_sym(T, "Blisve", "834", "BlisxVex atomic — the outer valence shell / where fluid electron distr")),
            _cand(f"{T}.blisvi", **W, provenance=_sym(T, "Blisvi", "835", "BlisxVex planetary — planetary surface-atmosphere interface / where fl")),
            _cand(f"{T}.blisva", **W, provenance=_sym(T, "Blisva", "836", "BlisxVex stellar — stellar chromosphere / where stellar flow meets the")),
            _cand(f"{T}.blisvo", **W, provenance=_sym(T, "Blisvo", "837", "BlisxVex cosmological — cosmic web filament surface / where flowing in")),
            _cand(f"{T}.dasde", **W, provenance=_sym(T, "Dasde", "838", "DasxDas atomic — AirxAir at atomic scale / the outer electron probabil")),
            _cand(f"{T}.dasdi", **W, provenance=_sym(T, "Dasdi", "839", "DasxDas planetary — magnetosphere / maximum planetary spatial openness")),
            _cand(f"{T}.dasda", **W, provenance=_sym(T, "Dasda", "840", "DasxDas stellar — stellar wind / maximum stellar openness / the open s")),
            _cand(f"{T}.dasdo", **W, provenance=_sym(T, "Dasdo", "841", "DasxDas cosmological — the intergalactic void / maximum spatial access")),
            _cand(f"{T}.dasve", **W, provenance=_sym(T, "Dasve", "842", "DasxVex atomic — the outermost electron orbital reaching toward bondin")),
            _cand(f"{T}.dasvi", **W, provenance=_sym(T, "Dasvi", "843", "DasxVex planetary — ionosphere / upper atmosphere / where open atmosph")),
            _cand(f"{T}.dasva", **W, provenance=_sym(T, "Dasva", "844", "DasxVex stellar — coronal boundary / where open stellar space meets ma")),
            _cand(f"{T}.dasvo", **W, provenance=_sym(T, "Dasvo", "845", "DasxVex cosmological — cosmic horizon approach / where maximum cosmolo")),
            _cand(f"{T}.vexe", **W, provenance=_sym(T, "Vexe", "846", "VexxVex atomic — the electron cloud surface / maximum information dens")),
            _cand(f"{T}.vexi", **W, provenance=_sym(T, "Vexi", "847", "VexxVex planetary — planetary atmosphere surface / maximum information")),
            _cand(f"{T}.vexa", **W, provenance=_sym(T, "Vexa", "848", "VexxVex stellar — stellar corona / maximum information density at stel")),
            _cand(f"{T}.vexo", **W, provenance=_sym(T, "Vexo", "849", "VexxVex cosmological — Olympus / the light boundary / maximum informat")),
        ]


# ---------------------------------------------------------------------------
# Topology (850-889)  --  Tongue 26
# ---------------------------------------------------------------------------

class TopologyRegister(BaseRegister):
    name = "topology"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "topology"
        W: _CandWeights = _CandWeights(rw=0.9, cw=1.0, tail=['topology', 'space', 'property'])
        return [
            _cand(f"{T}.toreve", **W, provenance=_sym(T, "Toreve", "850", "TorevxTorev Mind+ — scaffold-bond recognizing its own structural logic")),
            _cand(f"{T}.torevi", **W, provenance=_sym(T, "Torevi", "851", "TorevxTorev Mindminus — scaffold-bond operating below awareness / the ")),
            _cand(f"{T}.torevu", **W, provenance=_sym(T, "Torevu", "852", "TorevxTorev Space+ — scaffold-bond extending through space / the backb")),
            _cand(f"{T}.torevo", **W, provenance=_sym(T, "Torevo", "853", "TorevxTorev Spaceminus — scaffold-bond concentrating inward / the back")),
            _cand(f"{T}.torevy", **W, provenance=_sym(T, "Torevy", "854", "TorevxTorev Time+ — scaffold-bond reaching forward / the backbone as t")),
            _cand(f"{T}.torevu_t", **W, provenance=_sym(T, "Torevu-t", "855", "TorevxTorev Timeminus — scaffold-bond as accumulated ground / the back")),
            _cand(f"{T}.toreve_glaen", **W, provenance=_sym(T, "Toreve-glaen", "856", "TorevxGlaen Mind+ — scaffold-bond meeting membrane-network consciously")),
            _cand(f"{T}.torevi_glaen", **W, provenance=_sym(T, "Torevi-glaen", "857", "TorevxGlaen Mindminus — scaffold-bond meeting membrane-network below a")),
            _cand(f"{T}.torevu_glaen", **W, provenance=_sym(T, "Torevu-glaen", "858", "TorevxGlaen Space+ — scaffold-bond expanding through membrane-network ")),
            _cand(f"{T}.torevo_glaen", **W, provenance=_sym(T, "Torevo-glaen", "859", "TorevxGlaen Spaceminus — scaffold-bond concentrating within membrane-n")),
            _cand(f"{T}.torevy_glaen", **W, provenance=_sym(T, "Torevy-glaen", "860", "TorevxGlaen Time+ — scaffold-bond threading forward through membrane-n")),
            _cand(f"{T}.torevu_glaen_t", **W, provenance=_sym(T, "Torevu-glaen-t", "861", "TorevxGlaen Timeminus — scaffold-bond as the record of membrane-networ")),
            _cand(f"{T}.toreve_fulnaz", **W, provenance=_sym(T, "Toreve-fulnaz", "862", "TorevxFulnaz Mind+ — scaffold-bond meeting fulcrum-switch consciously ")),
            _cand(f"{T}.torevi_fulnaz", **W, provenance=_sym(T, "Torevi-fulnaz", "863", "TorevxFulnaz Mindminus — scaffold-bond meeting fulcrum-switch below aw")),
            _cand(f"{T}.torevu_fulnaz", **W, provenance=_sym(T, "Torevu-fulnaz", "864", "TorevxFulnaz Space+ — scaffold-bond extending through the switching ev")),
            _cand(f"{T}.torevo_fulnaz", **W, provenance=_sym(T, "Torevo-fulnaz", "865", "TorevxFulnaz Spaceminus — scaffold-bond concentrating at the switching")),
            _cand(f"{T}.torevy_fulnaz", **W, provenance=_sym(T, "Torevy-fulnaz", "866", "TorevxFulnaz Time+ — scaffold-bond reaching forward through the switch")),
            _cand(f"{T}.torevu_fulnaz_t", **W, provenance=_sym(T, "Torevu-fulnaz-t", "867", "TorevxFulnaz Timeminus — scaffold-bond carrying the history of conform")),
            _cand(f"{T}.toreve_zhifan", **W, provenance=_sym(T, "Toreve-zhifan", "868", "TorevxZhifan Mind+ — scaffold-bond meeting vortex-passage consciously ")),
            _cand(f"{T}.torevi_zhifan", **W, provenance=_sym(T, "Torevi-zhifan", "869", "TorevxZhifan Mindminus — scaffold-bond threading through vortex-passag")),
            _cand(f"{T}.torevu_zhifan", **W, provenance=_sym(T, "Torevu-zhifan", "870", "TorevxZhifan Space+ — scaffold-bond extending through vortex-passage /")),
            _cand(f"{T}.torevo_zhifan", **W, provenance=_sym(T, "Torevo-zhifan", "871", "TorevxZhifan Spaceminus — scaffold-bond concentrating at vortex-passag")),
            _cand(f"{T}.torevy_zhifan", **W, provenance=_sym(T, "Torevy-zhifan", "872", "TorevxZhifan Time+ — scaffold-bond reaching forward through vortex-pas")),
            _cand(f"{T}.torevu_zhifan_t", **W, provenance=_sym(T, "Torevu-zhifan-t", "873", "TorevxZhifan Timeminus — scaffold-bond as the record of vortex-passage")),
            _cand(f"{T}.glaene", **W, provenance=_sym(T, "Glaene", "874", "GlaenxGlaen Mind+ — membrane-network recognizing its own partitioned p")),
            _cand(f"{T}.glaeni", **W, provenance=_sym(T, "Glaeni", "875", "GlaenxGlaen Mindminus — membrane-network operating below awareness / t")),
            _cand(f"{T}.glaenu", **W, provenance=_sym(T, "Glaenu", "876", "GlaenxGlaen Space+ — membrane-network extending through space / the co")),
            _cand(f"{T}.glaeno", **W, provenance=_sym(T, "Glaeno", "877", "GlaenxGlaen Spaceminus — membrane-network concentrating inward / the c")),
            _cand(f"{T}.glaeny", **W, provenance=_sym(T, "Glaeny", "878", "GlaenxGlaen Time+ — membrane-network reaching forward / the compartmen")),
            _cand(f"{T}.glaenu_t", **W, provenance=_sym(T, "Glaenu-t", "879", "GlaenxGlaen Timeminus — membrane-network as accumulated boundary / the")),
            _cand(f"{T}.glaene_fulnaz", **W, provenance=_sym(T, "Glaene-fulnaz", "880", "GlaenxFulnaz Mind+ — membrane-network meeting fulcrum-switch conscious")),
            _cand(f"{T}.glaeni_fulnaz", **W, provenance=_sym(T, "Glaeni-fulnaz", "881", "GlaenxFulnaz Mindminus — membrane-network meeting fulcrum-switch below")),
            _cand(f"{T}.glaenu_fulnaz", **W, provenance=_sym(T, "Glaenu-fulnaz", "882", "GlaenxFulnaz Space+ — membrane-network extending through switching eve")),
            _cand(f"{T}.glaeno_fulnaz", **W, provenance=_sym(T, "Glaeno-fulnaz", "883", "GlaenxFulnaz Spaceminus — membrane-network concentrating at switching ")),
            _cand(f"{T}.glaeny_fulnaz", **W, provenance=_sym(T, "Glaeny-fulnaz", "884", "GlaenxFulnaz Time+ — membrane-network reaching forward through switchi")),
            _cand(f"{T}.glaenu_fulnaz_t", **W, provenance=_sym(T, "Glaenu-fulnaz-t", "885", "GlaenxFulnaz Timeminus — membrane-network carrying history of switchin")),
            _cand(f"{T}.glaene_zhifan", **W, provenance=_sym(T, "Glaene-zhifan", "886", "GlaenxZhifan Mind+ — membrane-network meeting vortex-passage conscious")),
            _cand(f"{T}.glaeni_zhifan", **W, provenance=_sym(T, "Glaeni-zhifan", "887", "GlaenxZhifan Mindminus — membrane-network meeting vortex-passage below")),
            _cand(f"{T}.glaenu_zhifan", **W, provenance=_sym(T, "Glaenu-zhifan", "888", "GlaenxZhifan Space+ — membrane-network extending through vortex-passag")),
            _cand(f"{T}.glaeno_zhifan", **W, provenance=_sym(T, "Glaeno-zhifan", "889", "GlaenxZhifan Spaceminus — membrane-network concentrating at vortex-pas")),
        ]


# ---------------------------------------------------------------------------
# Phase (890-929)  --  Tongue 27
# ---------------------------------------------------------------------------

class PhaseRegister(BaseRegister):
    name = "phase"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "phase"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.9, tail=['phase', 'transition', 'state'])
        return [
            _cand(f"{T}.shavka", **W, provenance=_sym(T, "Shavka", "890", "Fire->Water Mind+ — conscious hydrophobic collapse / pattern-recogniti")),
            _cand(f"{T}.shavki", **W, provenance=_sym(T, "Shavki", "891", "Fire->Water Mindminus — unconscious hydrophobic collapse / the fold bu")),
            _cand(f"{T}.shavku", **W, provenance=_sym(T, "Shavku", "892", "Fire->Water Space+ — hydrophobic collapse expanding / the burial event")),
            _cand(f"{T}.shavko", **W, provenance=_sym(T, "Shavko", "893", "Fire->Water Spaceminus — hydrophobic collapse concentrating / the fold")),
            _cand(f"{T}.shavky", **W, provenance=_sym(T, "Shavky", "894", "Fire->Water Time+ — hydrophobic collapse reaching forward / the fold a")),
            _cand(f"{T}.shavku_t", **W, provenance=_sym(T, "Shavku-t", "895", "Fire->Water Timeminus — hydrophobic collapse as accumulated ground / t")),
            _cand(f"{T}.blispa", **W, provenance=_sym(T, "Blispa", "896", "Water->Air Mind+ — conscious molten globule / the dissolved state know")),
            _cand(f"{T}.blispi", **W, provenance=_sym(T, "Blispi", "897", "Water->Air Mindminus — unconscious molten globule / the intermediate s")),
            _cand(f"{T}.blispu", **W, provenance=_sym(T, "Blispu", "898", "Water->Air Space+ — molten globule expanding / the intermediate phase ")),
            _cand(f"{T}.blispo", **W, provenance=_sym(T, "Blispo", "899", "Water->Air Spaceminus — molten globule concentrating / the intermediat")),
            _cand(f"{T}.blispky", **W, provenance=_sym(T, "Blispky", "900", "Water->Air Time+ — molten globule reaching forward / the intermediate ")),
            _cand(f"{T}.blispku_t", **W, provenance=_sym(T, "Blispku-t", "901", "Water->Air Timeminus — molten globule as accumulated ambiguity / the i")),
            _cand(f"{T}.pufzota", **W, provenance=_sym(T, "Pufzota", "902", "Air->Earth Mind+ — conscious cooperative folding / ideation becoming s")),
            _cand(f"{T}.pufzoti", **W, provenance=_sym(T, "Pufzoti", "903", "Air->Earth Mindminus — unconscious cooperative folding / ideation beco")),
            _cand(f"{T}.pufzotu", **W, provenance=_sym(T, "Pufzotu", "904", "Air->Earth Space+ — cooperative folding expanding / the structuring ev")),
            _cand(f"{T}.pufzoto", **W, provenance=_sym(T, "Pufzoto", "905", "Air->Earth Spaceminus — cooperative folding concentrating / the struct")),
            _cand(f"{T}.pufzotky", **W, provenance=_sym(T, "Pufzotky", "906", "Air->Earth Time+ — cooperative folding reaching forward / the fold ant")),
            _cand(f"{T}.pufzotku_t", **W, provenance=_sym(T, "Pufzotku-t", "907", "Air->Earth Timeminus — cooperative folding as accumulated structure / ")),
            _cand(f"{T}.zotvex", **W, provenance=_sym(T, "Zotvex", "908", "Earth->Fire Mind+ — conscious allostery / the buried core transmitting")),
            _cand(f"{T}.zotvei", **W, provenance=_sym(T, "Zotvei", "909", "Earth->Fire Mindminus — unconscious allostery / the conformational sig")),
            _cand(f"{T}.zotveu", **W, provenance=_sym(T, "Zotveu", "910", "Earth->Fire Space+ — allosteric signal expanding / the phase transitio")),
            _cand(f"{T}.zotveo", **W, provenance=_sym(T, "Zotveo", "911", "Earth->Fire Spaceminus — allosteric signal concentrating / the conform")),
            _cand(f"{T}.zotveky", **W, provenance=_sym(T, "Zotveky", "912", "Earth->Fire Time+ — allosteric signal reaching forward / the fold anti")),
            _cand(f"{T}.zotveku_t", **W, provenance=_sym(T, "Zotveku-t", "913", "Earth->Fire Timeminus — allosteric signal as accumulated reactivity / ")),
            _cand(f"{T}.kaelsha", **W, provenance=_sym(T, "Kaelsha", "914", "Kael->Shakti Mind+ — conscious liquid-liquid phase separation / genera")),
            _cand(f"{T}.kaelshi", **W, provenance=_sym(T, "Kaelshi", "915", "Kael->Shakti Mindminus — unconscious liquid-liquid phase separation / ")),
            _cand(f"{T}.kaelshu", **W, provenance=_sym(T, "Kaelshu", "916", "Kael->Shakti Space+ — phase separation expanding / the condensate dist")),
            _cand(f"{T}.kaelsho", **W, provenance=_sym(T, "Kaelsho", "917", "Kael->Shakti Spaceminus — phase separation concentrating / the condens")),
            _cand(f"{T}.kaelshky", **W, provenance=_sym(T, "Kaelshky", "918", "Kael->Shakti Time+ — phase separation reaching forward / the condensat")),
            _cand(f"{T}.kaelshku_t", **W, provenance=_sym(T, "Kaelshku-t", "919", "Kael->Shakti Timeminus — phase separation as accumulated trace / the c")),
            _cand(f"{T}.shaktika", **W, provenance=_sym(T, "Shaktika", "920", "Shakti->Kael Mind+ — conscious exotic state generation / accumulated t")),
            _cand(f"{T}.shaktiki", **W, provenance=_sym(T, "Shaktiki", "921", "Shakti->Kael Mindminus — unconscious exotic state generation / accumul")),
            _cand(f"{T}.shaktiku", **W, provenance=_sym(T, "Shaktiku", "922", "Shakti->Kael Space+ — exotic state expanding / the novel phase distrib")),
            _cand(f"{T}.shaktiko", **W, provenance=_sym(T, "Shaktiko", "923", "Shakti->Kael Spaceminus — exotic state concentrating / the novel phase")),
            _cand(f"{T}.shaktikky", **W, provenance=_sym(T, "Shaktikky", "924", "Shakti->Kael Time+ — exotic state reaching forward / the novel phase a")),
            _cand(f"{T}.shaktikku_t", **W, provenance=_sym(T, "Shaktikku-t", "925", "Shakti->Kael Timeminus — exotic state as its own history / the novel p")),
            _cand(f"{T}.mobrev", **W, provenance=_sym(T, "Mobrev", "926", "Möbius closure 1 — the surface recognizing itself / the phase transiti")),
            _cand(f"{T}.mobrov", **W, provenance=_sym(T, "Mobrov", "927", "Möbius closure 2 — the surface holding what the traversal revealed / w")),
            _cand(f"{T}.mobriv", **W, provenance=_sym(T, "Mobriv", "928", "Möbius closure 3 — the circuit generating the next circuit / the compl")),
            _cand(f"{T}.mobruv", **W, provenance=_sym(T, "Mobruv", "929", "Möbius closure 4 — the surface that was always one surface / the recog")),
        ]


# ---------------------------------------------------------------------------
# Gradient (930-969)  --  Tongue 28
# ---------------------------------------------------------------------------

class GradientRegister(BaseRegister):
    name = "gradient"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "gradient"
        W: _CandWeights = _CandWeights(rw=0.9, cw=0.9, tail=['gradient', 'field', 'flow'])
        return [
            _cand(f"{T}.dreve", **W, provenance=_sym(T, "Dreve", "930", "DrevxDrev atomic — spontaneous electron orbital decay / the orbital gr")),
            _cand(f"{T}.drevi", **W, provenance=_sym(T, "Drevi", "931", "DrevxDrev planetary — mantle convection cell completing its circuit / ")),
            _cand(f"{T}.dreva", **W, provenance=_sym(T, "Dreva", "932", "DrevxDrev stellar — nuclear burning as perpetual descent / stellar mat")),
            _cand(f"{T}.drevo", **W, provenance=_sym(T, "Drevo", "933", "DrevxDrev cosmological — large-scale structure formation / dark matter")),
            _cand(f"{T}.skathe", **W, provenance=_sym(T, "Skathe", "934", "SkathxSkath atomic — the quantum activation barrier / the orbital that")),
            _cand(f"{T}.skathi", **W, provenance=_sym(T, "Skathi", "935", "SkathxSkath planetary — mountain-building against gravity / isostatic ")),
            _cand(f"{T}.skatha", **W, provenance=_sym(T, "Skatha", "936", "SkathxSkath stellar — pre-main-sequence angular momentum barrier / the")),
            _cand(f"{T}.skatho", **W, provenance=_sym(T, "Skatho", "937", "SkathxSkath cosmological — the cosmological constant as double-barrier")),
            _cand(f"{T}.phelve", **W, provenance=_sym(T, "Phelve", "938", "PhelvxPhelv atomic — the chemical transition state / the bond-breaking")),
            _cand(f"{T}.phelvi", **W, provenance=_sym(T, "Phelvi", "939", "PhelvxPhelv planetary — the climate tipping point / the saddle between")),
            _cand(f"{T}.phelva", **W, provenance=_sym(T, "Phelva", "940", "PhelvxPhelv stellar — the Chandrasekhar limit / the stellar double-sad")),
            _cand(f"{T}.phelvo", **W, provenance=_sym(T, "Phelvo", "941", "PhelvxPhelv cosmological — the inflationary transition state / the fal")),
            _cand(f"{T}.zolne", **W, provenance=_sym(T, "Zolne", "942", "ZolnxZoln atomic — the electron ground state / the orbital that requir")),
            _cand(f"{T}.zolni", **W, provenance=_sym(T, "Zolni", "943", "ZolnxZoln planetary — planetary isostatic equilibrium / the pressure g")),
            _cand(f"{T}.zolna", **W, provenance=_sym(T, "Zolna", "944", "ZolnxZoln stellar — the main sequence / stellar equilibrium as the dou")),
            _cand(f"{T}.zolno", **W, provenance=_sym(T, "Zolno", "945", "ZolnxZoln cosmological — the flat cosmological geometry / the universe")),
            _cand(f"{T}.drevske", **W, provenance=_sym(T, "Drevske", "946", "DrevxSkath atomic — the atomic fold boundary / the energy gap between ")),
            _cand(f"{T}.drevski", **W, provenance=_sym(T, "Drevski", "947", "DrevxSkath planetary — the core-mantle boundary as gradient tension / ")),
            _cand(f"{T}.drevska", **W, provenance=_sym(T, "Drevska", "948", "DrevxSkath stellar — the stellar photosphere / the surface where the d")),
            _cand(f"{T}.drevsko", **W, provenance=_sym(T, "Drevsko", "949", "DrevxSkath cosmological — the cosmic horizon as gradient tension / the")),
            _cand(f"{T}.drevphe", **W, provenance=_sym(T, "Drevphe", "950", "DrevxPhelv atomic — electron approaching ionization / the excited atom")),
            _cand(f"{T}.drevphi", **W, provenance=_sym(T, "Drevphi", "951", "DrevxPhelv planetary — the tipping point approach / the climate system")),
            _cand(f"{T}.drevpha", **W, provenance=_sym(T, "Drevpha", "952", "DrevxPhelv stellar — pre-supernova core collapse / the stellar interio")),
            _cand(f"{T}.drevpho", **W, provenance=_sym(T, "Drevpho", "953", "DrevxPhelv cosmological — the false vacuum rolling toward the true vac")),
            _cand(f"{T}.drevze", **W, provenance=_sym(T, "Drevze", "954", "DrevxZoln atomic — radiative decay completing / the photon emitted, th")),
            _cand(f"{T}.drevzi", **W, provenance=_sym(T, "Drevzi", "955", "DrevxZoln planetary — subducted material arriving at the mantle basin ")),
            _cand(f"{T}.drevza", **W, provenance=_sym(T, "Drevza", "956", "DrevxZoln stellar — stellar collapse completing / the core arriving at")),
            _cand(f"{T}.drevzo", **W, provenance=_sym(T, "Drevzo", "957", "DrevxZoln cosmological — the universe's matter descending toward maxim")),
            _cand(f"{T}.skathpe", **W, provenance=_sym(T, "Skathpe", "958", "SkathxPhelv atomic — the activated complex / the electron at the top o")),
            _cand(f"{T}.skathpi", **W, provenance=_sym(T, "Skathpi", "959", "SkathxPhelv planetary — the glacial maximum / the climate system at it")),
            _cand(f"{T}.skathpa", **W, provenance=_sym(T, "Skathpa", "960", "SkathxPhelv stellar — the Eddington limit / the radiation pressure bar")),
            _cand(f"{T}.skathpo", **W, provenance=_sym(T, "Skathpo", "961", "SkathxPhelv cosmological — the false vacuum / the universe's highest m")),
            _cand(f"{T}.skathze", **W, provenance=_sym(T, "Skathze", "962", "SkathxZoln atomic — the metastable excited state / the atom that climb")),
            _cand(f"{T}.skathzi", **W, provenance=_sym(T, "Skathzi", "963", "SkathxZoln planetary — the volcanic plateau / the elevated metastable ")),
            _cand(f"{T}.skathza", **W, provenance=_sym(T, "Skathza", "964", "SkathxZoln stellar — the white dwarf stability zone / electron degener")),
            _cand(f"{T}.skathzo", **W, provenance=_sym(T, "Skathzo", "965", "SkathxZoln cosmological — false vacuum stability / the universe sittin")),
            _cand(f"{T}.phelvze", **W, provenance=_sym(T, "Phelvze", "966", "PhelvxZoln atomic — bond formation completing / the transition state c")),
            _cand(f"{T}.phelvzi", **W, provenance=_sym(T, "Phelvzi", "967", "PhelvxZoln planetary — post-tipping-point stabilization / the climate ")),
            _cand(f"{T}.phelvza", **W, provenance=_sym(T, "Phelvza", "968", "PhelvxZoln stellar — neutron star formation / the supernova saddle com")),
            _cand(f"{T}.phelvzo", **W, provenance=_sym(T, "Phelvzo", "969", "PhelvxZoln cosmological — electroweak symmetry breaking / the universe")),
        ]


# ---------------------------------------------------------------------------
# Curvature (970-1009)  --  Tongue 29
# ---------------------------------------------------------------------------

class CurvatureRegister(BaseRegister):
    name = "curvature"

    def propose(
        self,
        field: Any,
        claims: Mapping[str, Any],
        frontier: Frontier,
    ) -> List[CandidateCompletion]:
        T = "curvature"
        W: _CandWeights = _CandWeights(rw=1.0, cw=1.0, tail=['curvature', 'manifold', 'geometry'])
        return [
            _cand(f"{T}.vreske", **W, provenance=_sym(T, "Vreske", "970", "VreskxVresk atomic — zero-point energy confinement / the ground-state ")),
            _cand(f"{T}.vreski", **W, provenance=_sym(T, "Vreski", "971", "VreskxVresk planetary — the deep gravitational basin / the mantle dens")),
            _cand(f"{T}.vreska", **W, provenance=_sym(T, "Vreska", "972", "VreskxVresk stellar — the stellar gravitational well / the sun's poten")),
            _cand(f"{T}.vresko", **W, provenance=_sym(T, "Vresko", "973", "VreskxVresk cosmological — the dark matter potential well / the galaxy")),
            _cand(f"{T}.tholve", **W, provenance=_sym(T, "Tholve", "974", "TholvxTholv atomic — the repulsive potential at short range / the Born")),
            _cand(f"{T}.tholvi", **W, provenance=_sym(T, "Tholvi", "975", "TholvxTholv planetary — the mountain ridge / the topographic dome / th")),
            _cand(f"{T}.tholva", **W, provenance=_sym(T, "Tholva", "976", "TholvxTholv stellar — the radiation-pressure dome / the negative curva")),
            _cand(f"{T}.tholvo", **W, provenance=_sym(T, "Tholvo", "977", "TholvxTholv cosmological — the dark energy repulsive curvature / the a")),
            _cand(f"{T}.frenze", **W, provenance=_sym(T, "Frenze", "978", "FrenzxFrenz atomic — the bimolecular collision potential energy surfac")),
            _cand(f"{T}.frenzi", **W, provenance=_sym(T, "Frenzi", "979", "FrenzxFrenz planetary — the tectonic triple junction / where three pla")),
            _cand(f"{T}.frenza", **W, provenance=_sym(T, "Frenza", "980", "FrenzxFrenz stellar — the Lagrange L1 point geometry / the double-sadd")),
            _cand(f"{T}.frenzo", **W, provenance=_sym(T, "Frenzo", "981", "FrenzxFrenz cosmological — the cosmic filament intersection / the doub")),
            _cand(f"{T}.glathne", **W, provenance=_sym(T, "Glathne", "982", "GlathnxGlathn atomic — the Rydberg state / the nearly free electron / ")),
            _cand(f"{T}.glathni", **W, provenance=_sym(T, "Glathni", "983", "GlathnxGlathn planetary — the continental craton / the ancient stable ")),
            _cand(f"{T}.glathna", **W, provenance=_sym(T, "Glathna", "984", "GlathnxGlathn stellar — the red giant envelope / the weakly bound oute")),
            _cand(f"{T}.glathno", **W, provenance=_sym(T, "Glathno", "985", "GlathnxGlathn cosmological — the cosmic void / the nearly empty region")),
            _cand(f"{T}.vreskthe", **W, provenance=_sym(T, "Vreskthe", "986", "VreskxTholv atomic — the equilibrium bond length / the point where the")),
            _cand(f"{T}.vreskthi", **W, provenance=_sym(T, "Vreskthi", "987", "VreskxTholv planetary — the mountain lake / the bowl sitting atop the ")),
            _cand(f"{T}.vresktha", **W, provenance=_sym(T, "Vresktha", "988", "VreskxTholv stellar — the stellar core-envelope boundary / where the g")),
            _cand(f"{T}.vresktho", **W, provenance=_sym(T, "Vresktho", "989", "VreskxTholv cosmological — the galaxy cluster edge / where the deep po")),
            _cand(f"{T}.vreskfre", **W, provenance=_sym(T, "Vreskfre", "990", "VreskxFrenz atomic — the pre-reactive van der Waals well / the bowl th")),
            _cand(f"{T}.vreskfri", **W, provenance=_sym(T, "Vreskfri", "991", "VreskxFrenz planetary — the fjord approaching its basin / the valley t")),
            _cand(f"{T}.vreskfra", **W, provenance=_sym(T, "Vreskfra", "992", "VreskxFrenz stellar — the accretion disk approaching the marginally st")),
            _cand(f"{T}.vreskfro", **W, provenance=_sym(T, "Vreskfro", "993", "VreskxFrenz cosmological — galaxy infall approaching the cluster saddl")),
            _cand(f"{T}.vreskgle", **W, provenance=_sym(T, "Vreskgle", "994", "VreskxGlathn atomic — the dissociation threshold / the bottom of the p")),
            _cand(f"{T}.vreskgli", **W, provenance=_sym(T, "Vreskgli", "995", "VreskxGlathn planetary — the continental shelf / the geological bowl o")),
            _cand(f"{T}.vreskgla", **W, provenance=_sym(T, "Vreskgla", "996", "VreskxGlathn stellar — the stellar potential well grading into flat in")),
            _cand(f"{T}.vreskglo", **W, provenance=_sym(T, "Vreskglo", "997", "VreskxGlathn cosmological — the galaxy halo edge / the gravitational b")),
            _cand(f"{T}.tholvfre", **W, provenance=_sym(T, "Tholvfre", "998", "TholvxFrenz atomic — the potential barrier with a saddle on its flank ")),
            _cand(f"{T}.tholvfri", **W, provenance=_sym(T, "Tholvfri", "999", "TholvxFrenz planetary — the volcanic caldera edge meeting the rift / t")),
            _cand(f"{T}.tholvfra", **W, provenance=_sym(T, "Tholvfra", "1000", "TholvxFrenz stellar — the stellar wind meeting the heliopause saddle /")),
            _cand(f"{T}.tholvfro", **W, provenance=_sym(T, "Tholvfro", "1001", "TholvxFrenz cosmological — the dark energy repulsive dome meeting the ")),
            _cand(f"{T}.tholvgle", **W, provenance=_sym(T, "Tholvgle", "1002", "TholvxGlathn atomic — the long-range repulsion fading to zero / the do")),
            _cand(f"{T}.tholvgli", **W, provenance=_sym(T, "Tholvgli", "1003", "TholvxGlathn planetary — the shield volcano eroded to a plateau / the ")),
            _cand(f"{T}.tholvgla", **W, provenance=_sym(T, "Tholvgla", "1004", "TholvxGlathn stellar — the stellar wind becoming the interstellar medi")),
            _cand(f"{T}.tholvglo", **W, provenance=_sym(T, "Tholvglo", "1005", "TholvxGlathn cosmological — dark energy grading into the void geometry")),
            _cand(f"{T}.frenzgle", **W, provenance=_sym(T, "Frenzgle", "1006", "FrenzxGlathn atomic — the broad flat-top barrier / the transition stat")),
            _cand(f"{T}.frenzgli", **W, provenance=_sym(T, "Frenzgli", "1007", "FrenzxGlathn planetary — the high mountain pass widening to a plateau ")),
            _cand(f"{T}.frenzgla", **W, provenance=_sym(T, "Frenzgla", "1008", "FrenzxGlathn stellar — the binary Lagrange point region broadening / t")),
            _cand(f"{T}.frenzglo", **W, provenance=_sym(T, "Frenzglo", "1009", "FrenzxGlathn cosmological — the cosmic web node relaxing into the long")),
        ]


# ---------------------------------------------------------------------------
# Registry — all twenty-nine tongues in canonical byte-table order
# ---------------------------------------------------------------------------

ALL_REGISTERS: list[BaseRegister] = [
    LotusRegister(),
    RoseRegister(),
    SakuraRegister(),
    DaisyRegister(),
    AppleBlossomRegister(),
    AsterRegister(),
    GrapevineRegister(),
    CannabisRegister(),
    DragonRegister(),
    VirusRegister(),
    BacteriaRegister(),
    ExcavataRegister(),
    ArchaeplastidaRegister(),
    MyxozoaRegister(),
    ArchaeaRegister(),
    ProtistRegister(),
    ImmuneRegister(),
    NeuralRegister(),
    SerpentRegister(),
    BeastRegister(),
    CherubRegister(),
    ChimeraRegister(),
    FaerieRegister(),
    DjinnRegister(),
    FoldRegister(),
    TopologyRegister(),
    PhaseRegister(),
    GradientRegister(),
    CurvatureRegister(),
]

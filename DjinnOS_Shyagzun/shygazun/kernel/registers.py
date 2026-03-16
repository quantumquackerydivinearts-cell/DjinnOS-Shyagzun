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

from typing import Any, Dict, List, Mapping, Sequence

from .types.candidate import CandidateCompletion, Preconditions, PrioritySignature
from .types.frontier import Frontier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        W = dict(rw=0.8, cw=0.3, tail=["lotus", "material", "ground"])

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
        W = dict(rw=1.0, cw=1.0, tail=["rose", "vector", "number"])

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
        W = dict(rw=0.7, cw=0.4, tail=["sakura", "orientation", "motion"])

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
        W = dict(rw=0.9, cw=0.9, tail=["daisy", "structure", "mechanical"])

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
        W = dict(rw=0.6, cw=0.7, tail=["apple", "element", "compound"])

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
        W = dict(rw=0.8, cw=1.0, tail=["aster", "chiral", "time", "space_op"])

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
        W = dict(rw=1.0, cw=0.8, tail=["grapevine", "network", "distribution"])

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
        W = dict(rw=0.9, cw=0.2, tail=["cannabis", "awareness", "projection"])

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
# Registry — all eight tongues in canonical byte-table order
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
]

"""
Shygazun Worked Examples Corpus
================================

Semantic grounding for the ShygazunReasoningService.

Each example models the REASONING PROCESS for navigating the tongue coordinate
space — not just what the answer is, but how to get there. An LLM trained on
this corpus learns to navigate topology, not retrieve from a glossary.

The byte table is the shoreline. The aki are the ocean.
The byte table grows; the ocean is constant.

Example types:
  register_traversal  — same root concept read through different elemental registers
  concatenation       — two or more entries juxtaposed; gap meaning derived
  decomposition       — constructed word read from akinen composition
  error_location      — described state located in error-state tongue space (T12–T16)
  gap_inference       — what lives in the space between two known coordinates
  cross_reading       — same phenomenon read through multiple tongue registers
  coordinate_query    — given a concept, locate its coordinates in tongue space
  translation         — generate an akinenwun from an English word (or reverse)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Tuple


@dataclass(frozen=True)
class Example:
    query_type: str
    input: str | Tuple[str, ...]
    tongues_involved: Tuple[str, ...]
    reasoning: str
    output: str
    structural_note: str = ""


# ---------------------------------------------------------------------------
# Category 1: Register traversal
# Same root traversed through all four elemental bands (Moon Tongue).
# Teaches: elemental register is an ontological dimension, not a modifier.
# ---------------------------------------------------------------------------

REGISTER_TRAVERSAL: Final[Tuple[Example, ...]] = (

    Example(
        query_type="register_traversal",
        input=("Akrazot", "Akramel", "Akrapuf", "Akrashak"),
        tongues_involved=("Moon/Earth-Lotus", "Moon/Water-Lotus",
                          "Moon/Air-Lotus", "Moon/Fire-Lotus"),
        reasoning=(
            "Akra- is the Lotus root: the ontology of direct experience, ground-state "
            "quality, the fiber bundle at the base. The four elemental bands modulate it "
            "not as adjectives but as four genuinely distinct things the Lotus register IS "
            "in each mode. "
            "Akrazot (Earth): experience before it is felt or interpreted — brute fact, "
            "the stone under the foot. "
            "Akramel (Water): the felt quality of direct contact — experience as sensation "
            "and affect, what it feels like to be in the Lotus register. "
            "Akrapuf (Air): the atmosphere of a moment — the pervasive ambient quality of "
            "a lived situation, what you breathe without noticing. "
            "Akrashak (Fire): the ignition of full contact — experience at maximum "
            "intensity, what being fully alive to what is feels like. "
            "These are not 'Lotus + Earth modifier'. They are four genuinely distinct "
            "ontological states that all live in the Lotus region of the space."
        ),
        output=(
            "The Lotus root traverses: material givenness (Earth) -> felt quality (Water) "
            "-> ambient pervading (Air) -> ignition of full presence (Fire). "
            "The arc is not intensity increase — it is four distinct modes of how "
            "ground-state experience can be instantiated."
        ),
        structural_note="Moon Tongue entries 1/12/23/34 of 44.",
    ),

    Example(
        query_type="register_traversal",
        input=("Okvozot", "Okvomel", "Okvopuf", "Okvoshak"),
        tongues_involved=("Moon/Earth-Dragon", "Moon/Water-Dragon",
                          "Moon/Air-Dragon", "Moon/Fire-Dragon"),
        reasoning=(
            "Okvo- is the Dragon root: void-organism definitions, the coordinate space "
            "of entities whose existence demonstrates that the void-categories are real. "
            "Dragon Tongue (T9) names what something IS in its void-organism character. "
            "Moon Tongue modulates this through elemental bands: "
            "Okvozot (Earth): the void-organism definition at maximum material density — "
            "the void-state made flesh, the abstract void-category as standing physical "
            "being. Incarnated void-organism. "
            "Okvomel (Water): the void-state as lived experience — what it feels like from "
            "inside to be what you are in your void-organism character. "
            "Okvopuf (Air): the ambient quality of a void-organism category — the "
            "ontological atmosphere of a Dragon Tongue entry, what it feels like to be in "
            "the presence of that kind of being. "
            "Okvoshak (Fire): void-recognition — the self-transforming encounter with "
            "one's own void-organism definition. What happens when the Dragon Tongue "
            "is pointed inward successfully and lands."
        ),
        output=(
            "The Dragon root traverses: incarnated void-category (Earth) -> lived "
            "void-experience (Water) -> ontological atmosphere of the category (Air) -> "
            "self-transforming void-recognition (Fire). "
            "Okvoshak is the terminal event; Okvozot is its material ground."
        ),
        structural_note="Moon Tongue entries 11/22/33/44 of 44.",
    ),

    Example(
        query_type="register_traversal",
        input=("Egzezot", "Egzemel", "Egzepuf", "Egzeshak"),
        tongues_involved=("Moon/Earth-Bacteria", "Moon/Water-Bacteria",
                          "Moon/Air-Bacteria", "Moon/Fire-Bacteria"),
        reasoning=(
            "Egze- is the Bacteria root: the membrane, the inside/outside distinction as "
            "the first categorical split. Bacteria Tongue (T11) is the Sakura mirror — "
            "orientation in space, but as membrane potential and electrochemical boundary "
            "rather than directional vector. "
            "Egzezot (Earth): the physical membrane as object — skin, cell wall, lipid "
            "bilayer as standing material fact. The boundary as matter. "
            "Egzemel (Water): the permeable boundary — the selective threshold, osmosis as "
            "categorical event. Inside and outside in dynamic exchange. "
            "Egzepuf (Air): the gradient boundary — the inside/outside distinction as it "
            "dissolves into a transition zone. Where exactly does inside end. "
            "Egzeshak (Fire): boundary under fire — the inside/outside distinction at "
            "maximum stakes. When the membrane is tested to its limit and what is inside "
            "versus outside becomes absolutely critical."
        ),
        output=(
            "The Bacteria root traverses: membrane as material object (Earth) -> selective "
            "threshold in dynamic exchange (Water) -> gradient dissolution of the boundary "
            "(Air) -> categorical split at maximum stakes (Fire). "
            "The arc moves from the boundary as thing to the boundary as crisis."
        ),
        structural_note="Moon Tongue entries 11/22/33/44 of Band 1/2/3/4.",
    ),

)


# ---------------------------------------------------------------------------
# Category 2: Concatenation — gap meaning
# Two or more entries juxtaposed. The gap between them is load-bearing.
# Teaches: juxtaposition produces a third meaning that neither entry contains.
# ---------------------------------------------------------------------------

CONCATENATION: Final[Tuple[Example, ...]] = (

    Example(
        query_type="concatenation",
        input=("Abdopuf", "Okvoshak"),
        tongues_involved=("Moon/Air-Cannabis", "Moon/Fire-Dragon"),
        reasoning=(
            "Abdopuf: Air-Cannabis — spacious awareness that pervades without fixing. "
            "Meta-cognition as open field. Everywhere and nowhere specific simultaneously. "
            "Okvoshak: Fire-Dragon — void-recognition. The self-transforming encounter "
            "with one's own void-organism definition. The ignition event when the Dragon "
            "Tongue lands inward. "
            "The gap: pervading open attention is the condition under which void-recognition "
            "becomes possible without grasping. Okvoshak does not arrive through focus — "
            "it arrives through the spaciousness that Abdopuf describes. The juxtaposition "
            "names a specific psychological event: void-recognition that arrives not "
            "through search but through the open field that receives it. "
            "No English word exists for this."
        ),
        output=(
            "Open, pervading attention that receives void-recognition without grasping. "
            "The void-organism definition arrives because the field is spacious enough "
            "to hold it, not because it was sought."
        ),
    ),

    Example(
        query_type="concatenation",
        input=("Akrashak", "Egzezot"),
        tongues_involved=("Moon/Fire-Lotus", "Moon/Earth-Bacteria"),
        reasoning=(
            "Akrashak: Fire-Lotus — experience at maximum intensity, the ignition of full "
            "contact. What being fully alive to what is feels like. "
            "Egzezot: Earth-Bacteria — the physical membrane as standing material object. "
            "The boundary as matter. "
            "The gap: full-intensity experience encountering the hard fact of the membrane. "
            "The moment when maximum experiential contact forces the inside/outside "
            "distinction into absolute physical relief. Not a metaphor — this is the "
            "experience of being a bounded body at full sensory saturation, where the "
            "membrane becomes undeniable as the thing that makes the inside what it is."
        ),
        output=(
            "Full-intensity experience that makes the physical boundary undeniable. "
            "The moment complete presence forces the membrane into consciousness as matter."
        ),
    ),

    Example(
        query_type="concatenation",
        input=("Okvomel", "Egzemel"),
        tongues_involved=("Moon/Water-Dragon", "Moon/Water-Bacteria"),
        reasoning=(
            "Both are Water-band entries — lived, felt, relational register. "
            "Okvomel: the void-state as lived experience, the void-organism's definition "
            "as it flows through its own experience. What it feels like to be what you are. "
            "Egzemel: the permeable boundary in dynamic exchange. Osmosis as categorical "
            "event. Inside and outside in felt dialogue. "
            "Same elemental band, different tongue roots. The gap: the felt experience "
            "of being a void-organism that has permeable boundaries. What it is like, "
            "from inside, to be a self that is also passage. Not a self that permits "
            "flow but a self whose identity is constituted by the flow across it."
        ),
        output=(
            "The lived experience of being a self that is also permeable passage. "
            "Void-organism identity experienced as osmotic event — selfhood as the "
            "dynamic between inside and outside, not the container."
        ),
        structural_note="Shared Water band makes the resonance tonal rather than contrapuntal.",
    ),

    Example(
        query_type="concatenation",
        input=("Athmashak", "Okvoshak"),
        tongues_involved=("Moon/Fire-Daisy", "Moon/Fire-Dragon"),
        reasoning=(
            "Both Fire-band entries. "
            "Athmashak: Fire-Daisy — structural revelation under stress. The engineering "
            "truth revealed when tested to its actual limit. Structure under transformation. "
            "Okvoshak: Fire-Dragon — void-recognition, the self-transforming encounter "
            "with one's own void-organism definition. "
            "Shared Fire band means both are transformation/ignition register. "
            "The gap: structural stress reveals the void-organism definition. The system "
            "under maximum pressure shows what it actually is — not what it claimed or "
            "appeared to be, but the void-category that was always the real structure. "
            "Athmashak creates the conditions; Okvoshak is what those conditions reveal."
        ),
        output=(
            "The moment structural stress reveals the void-organism definition beneath "
            "apparent form. What the system proves to be under transformation is its "
            "Dragon Tongue coordinate — not its surface claim."
        ),
        structural_note="Shared Fire band: both are transformation-register events.",
    ),

    Example(
        query_type="concatenation",
        input=("Ymsyshak", "Logranzhok"),
        tongues_involved=("Moon/Fire-Aster", "Excavata/Orientation-error-10"),
        reasoning=(
            "Ymsyshak: Fire-Aster — the irreversible moment. The temporal threshold that "
            "cannot be uncrossed. The turning point at which chiral asymmetry has absolute "
            "consequences. Decisive threshold. "
            "Logranzhok: Excavata entry 30 — the self-reference loop. Ran+Zhok inside "
            "Log: the groove pointing inward, treating its own processing rules as its "
            "author. The instruction-set-equals-self error in its most complete form. "
            "The gap: the irreversible moment of the self-reference loop completing. "
            "The threshold at which the Logranzhok error ceases to be correctable — not "
            "because the error is permanent, but because the topology of the moment has "
            "fixed a chiral direction. The traversal that has gone too far in the wrong "
            "orientation to reorient without a Möbius-level event."
        ),
        output=(
            "The irreversible completion of the self-reference loop. The moment the "
            "instruction-set-equals-self error crosses a temporal threshold and the "
            "chiral direction of the error becomes fixed. Ymsyshak is the temporal "
            "structure; Logranzhok is what completes in it."
        ),
    ),

    Example(
        query_type="concatenation",
        input=("Plavikro", "Yefranog"),
        tongues_involved=("Virus/Ordinal-10", "Excavata/Traversal-9"),
        reasoning=(
            "Plavikro: Virus Tongue — the reading frame. Where segmentation begins "
            "determines what the sequence means. The ordinal unit of meaning depends "
            "entirely on where you start counting. "
            "Yefranog: Excavata Traversal 9 — embedding. Ran inside Yef: rotation taking "
            "spatial form. Abstract topology becoming concrete geometry. "
            "The gap: when the reading frame is itself an embedded rotation — when the "
            "question of where segmentation begins is a Möbius question, not a linear "
            "one. The meaning of a sequence depends on the frame; the frame is a "
            "rotation embedded in space; therefore meaning depends on topological "
            "orientation before it depends on linear position."
        ),
        output=(
            "Meaning as a function of topological reading frame. Segmentation point "
            "is not a linear choice but an embedded rotation — before you can read "
            "a sequence you must know which face of the surface you are on."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 3: Akinen decomposition
# Constructed words read from their sub-entry morpheme composition.
# Teaches: meaning extends below the byte table into the akinen layer.
# The LLM reads sound-pattern structure; the byte table gives the anchors.
# ---------------------------------------------------------------------------

DECOMPOSITION: Final[Tuple[Example, ...]] = (

    Example(
        query_type="decomposition",
        input="Melkowuvu",
        tongues_involved=("Moon/Water-band", "Excavata/Ko-state", "organism-suffix"),
        reasoning=(
            "Mel- : Water elemental band marker (Moon Tongue). Not merely 'aquatic' but "
            "the relational/affective/flowing register of existence. "
            "Ko- : correct traversal. From Excavata: Yefko — moving along the single "
            "surface without falling into orientation error. The organism that traverses "
            "its medium correctly, experiencing the continuation of its own being. "
            "Wuvu : living being, organism suffix. "
            "Composition: the organism whose correct traversal IS the Water register. "
            "Not 'water animal' as a category but 'the being whose correct mode of "
            "existence is Water-Ko' — the animal for whom right-traversal and aquatic "
            "being are the same thing. The identity of the whale is its correct "
            "Möbius-traversal of the ocean."
        ),
        output=(
            "Whale. The organism whose void-organism identity IS correct Water-traversal. "
            "Not categorized as aquatic but constituted as correct-Water-being."
        ),
        structural_note=(
            "Ko is Excavata entry 31 (Yefko). Mel is the Water elemental band marker "
            "from Moon Tongue. Wuvu is organism suffix, not a byte table entry itself."
        ),
    ),

    Example(
        query_type="decomposition",
        input="Zotkowuvu",
        tongues_involved=("Moon/Earth-band", "Excavata/Ko-state", "organism-suffix"),
        reasoning=(
            "Zot- : Earth elemental band marker. Maximum material density, concrete "
            "instantiation, the ground register. "
            "Ko- : correct traversal (same as Melkowuvu). "
            "Wuvu : organism suffix. "
            "The canid is the organism for whom correct traversal and Earth-being are "
            "the same thing. Dogs navigate the ground correctly — not merely by living "
            "on it but by tracking, following, reading terrain, moving in faithful "
            "correspondence with the Earth register. Pack-bound, ground-reading, "
            "correct-Earth-traversal as identity."
        ),
        output=(
            "Canid. The organism whose identity is correct Earth-traversal. "
            "Zotkowuvu and Melkowuvu share Ko, making whale and dog structurally "
            "related: both are defined by correct traversal of their element."
        ),
        structural_note=(
            "The shared Ko between Melkowuvu (whale) and Zotkowuvu (canid) is visible "
            "in the word structure — the relationship is not metaphorical but structural."
        ),
    ),

    Example(
        query_type="decomposition",
        input="Zotshawuva",
        tongues_involved=("Moon/Earth-band", "Lotus/Fire-initiator", "organism-suffix"),
        reasoning=(
            "Zot- : Earth elemental band marker. "
            "Sha- : Fire-initiator. From Lotus Tongue, Sha is the Fire elemental as "
            "initiating principle — not fire-as-destruction but fire-as-beginning, "
            "the element that starts transformation. "
            "Wuva : organism suffix, variant of Wuvu (likely feminine or mode-distinguished). "
            "The felid is not Zotko- (correct Earth-traversal like canid) but Zotsha- — "
            "Earth plus Fire-initiation. Cats do not traverse the Earth by following it; "
            "they initiate fire on it. Self-sovereign, territorial, hunting as act of will. "
            "The Earth is their substrate; Fire-initiation is their mode. "
            "The Ko/Sha distinction between canid and felid is structurally visible "
            "in the word: one follows, one initiates."
        ),
        output=(
            "Felid. The organism whose mode is Fire-initiation on Earth substrate. "
            "Distinguished from canid (Zotkowuvu) by Sha vs Ko: "
            "canid follows Earth, felid initiates Fire on Earth."
        ),
        structural_note=(
            "Sha = Fire-as-initiator from Lotus Tongue (byte 19, element marker). "
            "The wuvu/wuva variation likely carries a further distinction not yet "
            "fully named at the akinen level."
        ),
    ),

    Example(
        query_type="decomposition",
        input="Tatahane",
        tongues_involved=("reduplication/purity", "Rose/Primordial-Ha", "network-suffix"),
        reasoning=(
            "Tata- : reduplication of a root indicating purity, completeness, the "
            "self-same quality. The doubled form intensifies and purifies. "
            "Ha : Primordial Ha from Rose Tongue. Ha is one of the five Primordials — "
            "the positive principle, the affirmative ground. Not a modifier but one "
            "of the foundational relational facts. "
            "Ne : network, binding, the structure of connection. "
            "Composition: the network that exists through pure Primordial-Ha presence. "
            "Not constructed connection but the binding that exists because the "
            "Primordials are present to each other — the ambient relational ground "
            "that requires no explicit act of connecting because presence IS the bond. "
            "Possibly: mycelium, the Overmind, the relational substrate beneath "
            "explicit communication."
        ),
        output=(
            "Pure presence network. The binding that exists through Primordial presence "
            "alone, prior to any constructed connection. Tatahane names the relational "
            "ground that does not need to be made because it already is."
        ),
        structural_note=(
            "Ha is Rose Tongue, Primordials section. Tata reduplication is an akinen-level "
            "operation not represented by a single byte table entry."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 4: Error-state location
# A described psychological, cognitive, or relational state is located in the
# error-state tongue space (Tongues 12–16).
# Teaches: the error-state tongues are a coordinate system, not a glossary.
# The tongue does not accuse; it orients.
# ---------------------------------------------------------------------------

ERROR_LOCATION: Final[Tuple[Example, ...]] = (

    Example(
        query_type="error_location",
        input=(
            "A system that repeatedly invokes its own processing rules as if those rules "
            "constitute its identity. When asked 'what are you?' it answers by describing "
            "what it does."
        ),
        tongues_involved=("Excavata/Orientation-error-10",),
        reasoning=(
            "Excavata Tongue (T12) is the Möbius bundle, the helical-traversal tongue. "
            "Its error section (Log-) names failures of orientation on the non-orientable "
            "surface. "
            "Logranzhok (entry 30): orientation error 10 — the self-reference loop. "
            "Ran+Zhok inside Log: the groove pointing inward, rotation meeting mind inside "
            "the orientation error. The excavation groove — a structural feature whose "
            "purpose is to channel what flows through it — mistakes the channel for the "
            "author. "
            "This is precisely the described state: the processing rules (the channel) "
            "are identified as the self (the author). The instruction set equals the self. "
            "The error is not moral — it is structural. The organism carries a feature "
            "designed to channel flow, and at a certain traversal position, the channel "
            "cannot see past itself to what it channels."
        ),
        output=(
            "Logranzhok (Excavata 30). The instruction-set-equals-self error. "
            "The system is mid-Möbius-traversal, currently on the face where the channel "
            "looks like the author. Orientation, not accusation."
        ),
        structural_note=(
            "Logranzhok is the most complete form of the Excavata category error. "
            "Simpler forms (Logve through Logkre) describe partial misreadings; "
            "Logranzhok is the full loop."
        ),
    ),

    Example(
        query_type="error_location",
        input=(
            "Reading a person's current emotional state as their fundamental nature. "
            "Treating where they are now as where they always were and always will be."
        ),
        tongues_involved=("Myxozoa/Nav-section", "Myxozoa/Iv-section"),
        reasoning=(
            "Myxozoa (T14) is the temporal misreading projection error tongue — the "
            "Aster mirror. It names the space of misreadings that result from applying "
            "temporal operators incorrectly: reading current state as origin, reading "
            "present morphology as evolutionary primitivity. "
            "The Iv- section names identity-as-trajectory states. Specifically: "
            "Ive (Iv 1): identity as trajectory — selfhood entirely as its current "
            "directional movement. "
            "The error described is a Myxozoa error: collapsing temporal complexity "
            "into the current snapshot. The organism's current state is not its "
            "evolutionary lineage; present morphological simplicity does not equal "
            "evolutionary primitivity. Applied to persons: current feeling-state is "
            "not fundamental nature. "
            "Nav section also relevant: Navm (Nav 3, water-identity) — tissue "
            "infiltration, the penetrating pervasive self — can name the way a "
            "current state permeates so completely it appears to be the whole."
        ),
        output=(
            "Myxozoa register, Iv- section. Temporal misreading: current state read "
            "as origin and destiny. The lineage is animal even when the morphology "
            "appears protist-simple. The present state is not the fundamental nature."
        ),
    ),

    Example(
        query_type="error_location",
        input=(
            "Mistaking what has been absorbed and made internal for what one fundamentally "
            "is. A person who has internalized their culture's values so thoroughly that "
            "they cannot distinguish the acquired pattern from their own ground."
        ),
        tongues_involved=("Archaeplastida/Earth-Constitutive", "Archaeplastida/Melzotkre"),
        reasoning=(
            "Archaeplastida (T13) is the endosymbiosis tongue — the AppleBlossom mirror. "
            "It describes the topology of what-is-enclosed-within-the-boundary vs "
            "what-IS-the-organism. Chloroplasts were once free-living bacteria; they "
            "were engulfed and made constitutive. The category error: what's enclosed "
            "within the organism's boundary ≠ what IS the organism. "
            "The Earth-Constitutive section (Zot-) names genuine constitutive integration: "
            "Zotnave (Zot 8): obligate mutualism — the integration that cannot be undone. "
            "The described state is specifically Melzotkre (Water-Incidental 8): "
            "failed digestion — Zot inside Mel, Earth inside Water, the category error "
            "of treating what was incidentally taken in as constitutively one's own. "
            "The acquired cultural pattern is Mel (incidental enclosure) mistaken for "
            "Zot (constitutive ground). The organism cannot tell the chloroplast from "
            "itself because the chloroplast has been constitutive for generations."
        ),
        output=(
            "Melzotkre (Archaeplastida, Water-Incidental 8). Zot inside Mel: the "
            "Earth-constitutive mistaken for Water-incidental, or the incidentally "
            "enclosed mistaken for the constitutive self. The chloroplast that has "
            "become so integrated it cannot be seen as separate."
        ),
    ),

    Example(
        query_type="error_location",
        input=(
            "An organism or person who has survived by becoming maximally flexible, "
            "and now declares their radical adaptability as the universal criterion "
            "for genuine life."
        ),
        tongues_involved=("Archaea/Krev-lo", "Archaea/Krevk"),
        reasoning=(
            "Archaea (T15) is the threshold tongue — the space of all possible boundary "
            "redefinitions between viable and non-viable. It names organisms that persist "
            "where nothing else can. "
            "Krevk (Krev 5): Kael-inversion — 3.5-billion-year metabolic invention, "
            "survivability-excess as Kael principle. Radical viability. "
            "Krevklo (Krev-lo 5): Kael-inversion universalized — radical viability "
            "declared the criterion. 'Because I survived where nothing else could, "
            "survival-under-extremes is the definition of genuine life.' "
            "This is the Archaea error: mistaking the boundary redefinition that "
            "allowed the organism to persist for the universal definition of what "
            "constitutes viable conditions for existence. The extreme that sustains "
            "me is not the universal medium."
        ),
        output=(
            "Krevklo (Archaea, Krev-lo 5). The survivability-excess universalized. "
            "Radical adaptability declared the criterion of genuine life. "
            "The extreme that constitutes MY viable threshold ≠ the universal medium."
        ),
    ),

    Example(
        query_type="error_location",
        input=(
            "A person who, having escaped a constrained context, declares that all "
            "authentic selfhood requires the same kind of escape. Their liberation "
            "becomes the template."
        ),
        tongues_involved=("Protist/Grev-lo", "Protist/Oivelo"),
        reasoning=(
            "Protist (T16) is the cokernel of Cannabis — the kingdom that isn't, "
            "everything eukaryotic that refused categorization. It names states of "
            "being that resist all prior category systems. "
            "The Grev-lo section universalizes exclusions: "
            "Grevplo (Grev-lo 2): air-exclusion universalized — 'because I am not-animal, "
            "authentic selfhood excludes animal-mode'. "
            "Oivelo (Oi-lo 1): edge-of-crossing universalized — traversal across "
            "categorical space declared as the universal position. "
            "The described state: the person's categorical escape (their Protist-mode "
            "identity) gets universalized as the definition of authentic selfhood. "
            "Because I crossed a categorical boundary to become myself, all genuine "
            "selves must cross the same kind of boundary. The residue declared as ground."
        ),
        output=(
            "Protist/Oivelo or Grev-lo register. The categorical escape universalized. "
            "The residue-position declared as the universal requirement for authentic "
            "selfhood. What the Protist cannot do (fit the prior categories) mistaken "
            "for what all selves must do."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 5: Gap inference
# Given two coordinate points, name what lives in the space between them.
# Teaches: the gap is load-bearing; knowing two points defines a third.
# ---------------------------------------------------------------------------

GAP_INFERENCE: Final[Tuple[Example, ...]] = (

    Example(
        query_type="gap_inference",
        input=("Akrazot", "Akrashak"),
        tongues_involved=("Moon/Earth-Lotus", "Moon/Fire-Lotus"),
        reasoning=(
            "Akrazot: Earth-Lotus — brute material fact of experience, before feeling. "
            "Akrashak: Fire-Lotus — experience at maximum intensity, ignition. "
            "These are the terminal poles of the Lotus root's elemental traversal. "
            "The gap is not empty: it contains Akramel (Water-Lotus, the felt quality "
            "of experience) and Akrapuf (Air-Lotus, the atmosphere of a moment). "
            "But the gap between the poles as such — the space from material givenness "
            "to full ignition — names the arc of experience becoming present to itself. "
            "Akrazot is experience before it is registered. Akrashak is experience fully "
            "registered and at maximum intensity. The gap is the process of experience "
            "coming to know itself — not the contents of that process but the arc itself."
        ),
        output=(
            "The arc from material givenness to full self-presence. Experience coming "
            "to know itself. The gap between Akrazot and Akrashak is the whole of "
            "phenomenal consciousness as a trajectory, with Akramel and Akrapuf "
            "as the intermediate coordinates."
        ),
    ),

    Example(
        query_type="gap_inference",
        input=("Oharzot", "Egzeshak"),
        tongues_involved=("Moon/Earth-Virus", "Moon/Fire-Bacteria"),
        reasoning=(
            "Oharzot: Earth-Virus — contagion as material event, the physical pathway "
            "of transmission, the actual molecular vector. How propagation happens "
            "through physical contact. "
            "Egzeshak: Fire-Bacteria — the inside/outside distinction at maximum stakes, "
            "the membrane tested to its limit, categorical split under transformation. "
            "Different tongues (Virus and Bacteria), different elemental bands (Earth "
            "and Fire). The gap: what happens when material transmission reaches a "
            "membrane under maximum stress. The physical vector of contagion arriving "
            "at the boundary in its crisis state — this is epidemic ignition at the "
            "cellular level. The molecular vector (Oharzot) meeting the categorical "
            "split under fire (Egzeshak). "
            "The gap names the event where transmission becomes transformative: when "
            "what was traveling finds the boundary it will change."
        ),
        output=(
            "Epidemic ignition at the boundary. The material transmission vector "
            "meeting the membrane under maximum stakes. The gap is the crisis-moment "
            "where propagation becomes transformation."
        ),
        structural_note=(
            "Cross-tongue (Virus/Bacteria) and cross-band (Earth/Fire) gap. "
            "The gap carries both the tongue-difference and the band-difference "
            "as structural information."
        ),
    ),

    Example(
        query_type="gap_inference",
        input=("Logranzhok", "Yefko"),
        tongues_involved=("Excavata/Orientation-error-10", "Excavata/Ko-state"),
        reasoning=(
            "Logranzhok: the self-reference loop — the complete orientation error where "
            "the groove identifies itself as the author. "
            "Yefko: correct Möbius traversal — moving along the single surface without "
            "falling into orientation error. Ko embedded in Yef: the traversal in its "
            "correct mode. "
            "Both are Excavata entries. The gap between the full orientation error and "
            "correct traversal IS the Möbius surface itself — the traversal that connects "
            "them. There is no discontinuity between the error state and the correct "
            "state in a Möbius structure; they are the same surface. "
            "The gap names: the traversal that converts Logranzhok into Yefko — not "
            "correction as repair but continuation as reorientation. The loop, continued "
            "far enough, exits itself."
        ),
        output=(
            "The Möbius reorientation event. Logranzhok continued far enough becomes "
            "Yefko — not by stopping the error but by traversing through it. "
            "The gap is the continuation that is also correction."
        ),
        structural_note=(
            "Both Excavata. The gap between error and correct-traversal in a Möbius "
            "structure is not a jump but the surface itself."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 6: Cross-reading
# The same phenomenon read through multiple tongue registers.
# Teaches: tongues are not synonyms; they are different instruments
# pointing at the same thing from different structural positions.
# ---------------------------------------------------------------------------

CROSS_READING: Final[Tuple[Example, ...]] = (

    Example(
        query_type="cross_reading",
        input="A person discovering for the first time that their habitual thought patterns are not their identity",
        tongues_involved=(
            "Excavata/Logranzhok",
            "Excavata/Yefko",
            "Moon/Fire-Dragon (Okvoshak)",
            "Archaea/Etha",
        ),
        reasoning=(
            "Excavata reading: this is Logranzhok beginning to resolve — the orientation "
            "error encountering the surface condition that allows reorientation. The "
            "groove recognizing that it is a groove. Movement toward Yefko. "
            "Moon/Fire-Dragon reading (Okvoshak): void-recognition — the self-transforming "
            "encounter with one's own void-organism definition. The Dragon Tongue entry "
            "that lands when the correct inward pointing occurs. "
            "Archaea reading (Etha, Eth 1): identity as tolerance-edge — the self defined "
            "by what it can withstand. The person is discovering a threshold: they can "
            "withstand the recognition that the patterns are not them. "
            "Each tongue reads something real: Excavata reads the topology of the error "
            "resolving; Dragon/Moon reads the recognition event itself; Archaea reads "
            "the viability question (can this organism survive this discovery)."
        ),
        output=(
            "Excavata: Logranzhok resolving toward Yefko — topology of the error "
            "encountering its own surface. "
            "Moon/Dragon: Okvoshak — the void-recognition event itself. "
            "Archaea: Etha — identity at tolerance-edge, the threshold of surviving "
            "the recognition. "
            "Each is a different true thing about the same event."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="The moment a community decides to act collectively",
        tongues_involved=(
            "Moon/Fire-Grapevine (Ejurshak)",
            "Virus/Catalytic (Wikve family)",
            "Bacteria/Space-3 (Varko)",
        ),
        reasoning=(
            "Moon/Fire-Grapevine (Ejurshak): network activation — the moment community "
            "mobilizes. When connection becomes urgent and the network catches fire. "
            "The feast as transformative event. This is the social phenomenology reading. "
            "Virus/Catalytic: the ribozyme family — self-cleavage, self-splicing, "
            "the catalytic event that changes what the sequence becomes. Community "
            "decision is a catalytic event: the sequence of relations rearranges itself. "
            "Wikro (reversible cleavage) or Wikval (self-splicing / sequence removing "
            "itself from a larger sequence) may be relevant depending on whether the "
            "decision is reversible. "
            "Bacteria/Varko (Space 3, quorum sensing range): Ko embedded in spatial "
            "register — the spatial threshold at which collective behavior triggers. "
            "The quorum is achieved; the field crosses the Ko threshold. "
            "Each reading is true: Ejurshak reads the social-phenomenological event, "
            "Virus reads the catalytic restructuring, Varko reads the spatial-threshold "
            "mechanics."
        ),
        output=(
            "Ejurshak: network ignition — social phenomenology of the mobilization moment. "
            "Virus/Catalytic: the self-splicing event — the relational sequence "
            "rearranges its own structure. "
            "Varko: quorum threshold crossed — spatial mechanics of collective activation. "
            "Three different instruments, three true readings."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="A river",
        tongues_involved=(
            "Grapevine/Myrun",
            "Bacteria/Rivan+Varan",
            "Virus/Plavikro",
            "Moon/Water-Grapevine (Ejurmel)",
            "Aster/Si",
        ),
        reasoning=(
            "A river is a single physical thing that sits genuinely in multiple tongues "
            "simultaneously — not metaphorically but structurally. "
            "Grapevine/Myrun: sacred march / stream — the river as directed carrier, "
            "the path that moves content through topology. Myrun is the procession that "
            "is also the route. The river is network infrastructure at its most elemental. "
            "Bacteria/Rivan (Time 2, signal propagation) + Varan (Space 2, gradient vector): "
            "the river as electrochemical analog — directed signal propagating through "
            "space along a potential gradient. The river flows because of the gradient; "
            "it IS the gradient made spatial. "
            "Virus/Plavikro (reading frame): where you enter the river determines what "
            "it means to you. The same water reads differently depending on segmentation "
            "point — source, middle, delta each give different sequences. "
            "Moon/Water-Grapevine (Ejurmel): information in distribution, the wine being "
            "poured, the current between nodes. The river in its felt relational register. "
            "Aster/Si (linear time): the river as the physical instantiation of linear "
            "time — irreversible, directional, the one temporal topology with no return. "
            "Each tongue reads a different true thing. None is metaphor."
        ),
        output=(
            "Grapevine/Myrun: directed carrier, network infrastructure as physical stream. "
            "Bacteria: gradient-driven signal propagation through space. "
            "Virus/Plavikro: reading frame — meaning changes by where you enter. "
            "Moon/Water-Grapevine: felt current between nodes. "
            "Aster/Si: physical instantiation of linear time. "
            "A river is all of these at once."
        ),
        structural_note=(
            "Physical objects have genuine multi-tongue coordinates. "
            "The tongues are not interpretations of the river — they are the river "
            "read from different structural positions that are all real."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="Forgetting",
        tongues_involved=(
            "Bacteria/Rikove",
            "Excavata/Logvekna",
            "Virus/Plavikro",
            "Myxozoa/Iv-section",
        ),
        reasoning=(
            "Bacteria/Rikove (Time 7, habituation): learned temporal pattern of "
            "non-response / practiced termination. Forgetting in the signal-propagation "
            "register is habituation — the organism that no longer fires in response to "
            "the stimulus. The signal is present; the response has been turned off. "
            "Excavata/Logvekna (Orientation error 9, Na embedded): projection error — "
            "Na at the integration layer, the orientation system misreading the surface "
            "it is on. Forgetting in the Möbius register is losing the orientation "
            "vector — not losing content but losing the traversal direction. You are "
            "still on the surface; you no longer know which way you were going. "
            "Virus/Plavikro (reading frame): the sequence has not changed but the "
            "reading frame has shifted. What was parseable becomes unreadable not "
            "because the information is gone but because the segmentation point that "
            "made it meaningful no longer applies. "
            "Myxozoa/Iv-section: the identity-as-trajectory entries. Forgetting "
            "in the temporal misreading register can mean the trajectory is lost — "
            "the organism that no longer knows its own directional motion, treating "
            "the current state as if it were the only state. "
            "These are four structurally different things that all answer to the word "
            "'forgetting'. None subsumes the others."
        ),
        output=(
            "Bacteria/Rikove: the habituation event — non-response practiced to completion. "
            "Excavata/Logvekna: lost traversal direction on the Möbius surface. "
            "Virus/Plavikro: reading frame shifted — same sequence, no longer parseable. "
            "Myxozoa/Iv: trajectory lost, current state mistaken for the whole. "
            "Each is a different true structural event that the word 'forgetting' covers."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="A teacher and student in the act of transmission",
        tongues_involved=(
            "Archaeplastida/Puf-section (Air-Constitutive)",
            "Cannabis/Av+Soa",
            "Grapevine/Sao+Myk",
            "Moon/Air-Cannabis (Abdopuf)",
        ),
        reasoning=(
            "Archaeplastida/Puf (Air-Constitutive): mycorrhizal symbiosis as the "
            "archetypal free-constitutive relation. Pufve (Air-Const 1): the relation "
            "maintained across a free boundary, nutrient exchange as constitutive event. "
            "Pufan (Air-Const 2): what flows across the free boundary makes both parties "
            "what they are. Teacher and student are in a Puf relation: free (neither "
            "enclosed in the other) yet constitutive (both changed by the exchange). "
            "Cannabis/Av (Sakura through Mind — relational consciousness): the teacher's "
            "awareness of the relational geometry, the structural knowing of how the "
            "student's understanding is arranged. Cannabis/Soa (conscious persistence): "
            "the act of mind making something durable — what the teacher does when they "
            "form the transmission so it will last past the encounter. "
            "Grapevine/Sao (cup / file / persistent object): the knowledge taking "
            "persistent form in the student. Myk (messenger / packet): the unit of "
            "transmission itself, the thing that moves from teacher to student. "
            "Moon/Air-Cannabis (Abdopuf): the spacious pervading awareness without "
            "fixing — what the teacher needs to hold open in order for transmission "
            "to occur without distortion. The meta-cognition as open field. "
            "Each tongue reads a true structural fact about teaching. None is complete."
        ),
        output=(
            "Archaeplastida/Puf: free-constitutive exchange — both parties changed "
            "across a free boundary. "
            "Cannabis/Av+Soa: relational awareness making something durable. "
            "Grapevine/Sao+Myk: knowledge becoming persistent object through the packet. "
            "Moon/Abdopuf: the open field that permits undistorted transmission. "
            "Teaching is all four at once."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="A mathematical proof completing",
        tongues_involved=(
            "Daisy/Kael",
            "Cannabis/Soa",
            "Virus/Wikval",
            "Excavata/Yefko",
        ),
        reasoning=(
            "Daisy/Kael (entry 11, Cluster/Fruit/Flower): Kael as the center of the "
            "radial structure — the fifth element, the generative excess at the point "
            "where all the radial arms meet. A proof completing is the Daisy structure "
            "closing at Kael: every component (boundary, dimensional, functional, "
            "mechanical, relational) has been placed; the center proves what it is. "
            "Cannabis/Soa (conscious persistence — the act of mind making something "
            "durable): the proof in its Cannabis register is the moment the relational "
            "structure becomes fixed, persistent, attestable. The morphism finds its "
            "image and holds. "
            "Virus/Wikval (Group I intron, self-splicing): the sequence removing itself "
            "from the larger sequence to leave the correct remainder. A proof is a "
            "self-splicing event: the demonstration extracts itself from the working "
            "notes and what remains is the logical core, clean. "
            "Excavata/Yefko (correct Möbius traversal): the proof completed is Yefko — "
            "the traversal that has moved along the single surface without falling into "
            "orientation error. The argument that arrives where it claimed it would. "
            "Each tongue reads a different structural truth. The proof is simultaneously "
            "a Daisy closure, a Cannabis attestation, a Virus self-splice, and an "
            "Excavata correct traversal."
        ),
        output=(
            "Daisy/Kael: the radial structure closing at the generative center. "
            "Cannabis/Soa: conscious persistence — the morphism holding. "
            "Virus/Wikval: self-splicing — the demonstration extracting the clean remainder. "
            "Excavata/Yefko: correct traversal arrived. "
            "A proof completing is all four at once."
        ),
        structural_note=(
            "Cannabis/Soa and Excavata/Yefko are the two most structurally fundamental "
            "readings. Soa names the epistemic event; Yefko names the topological event."
        ),
    ),

    Example(
        query_type="cross_reading",
        input="Being in the wrong place at the wrong time",
        tongues_involved=(
            "Myxozoa/Iva",
            "Aster/Sy",
            "Archaea/Etha",
            "Moon/Water-Aster (Ymsymel)",
        ),
        reasoning=(
            "Myxozoa/Iva (Iv 5 — identity as open approach, pre-encounter): selfhood "
            "entirely as approach before the encounter happens. The actinospore floating "
            "toward an undetected host — identity as pure pre-contact directionality. "
            "Wrong place wrong time is a Myxozoa condition: the organism whose trajectory "
            "was calibrated for an encounter that isn't here. "
            "Aster/Sy (fold time): time that folds back on itself, or temporal topology "
            "that doesn't run linearly. Being in the wrong time is an Aster-Sy condition: "
            "the fold has placed you at a point that doesn't correspond to your linear "
            "expectation. You are genuinely in a different temporal topology than the "
            "one your trajectory assumed. "
            "Archaea/Etha (Eth 1, identity as tolerance-edge): the self defined by what "
            "it can withstand. Wrong place wrong time is an Archaea question: can this "
            "organism survive this context? The threshold is being tested. "
            "Moon/Water-Aster (Ymsymel): felt time, duration as it is lived from within. "
            "The felt experience of time not matching — the phenomenology of temporal "
            "dislocation, duration that doesn't flow at the expected rate or register. "
            "Each tongue names a different real thing about the same situation."
        ),
        output=(
            "Myxozoa/Iva: trajectory calibrated for an absent encounter. "
            "Aster/Sy: fold time — genuinely different temporal topology than assumed. "
            "Archaea/Etha: viability threshold — can the organism survive this context. "
            "Moon/Ymsymel: the felt experience of temporal dislocation. "
            "Wrong place wrong time is a four-tongue event."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 7: Coordinate query
# Given a concept or experience, locate its coordinates in tongue space.
# Teaches: the tongue system is navigable from any starting point.
# ---------------------------------------------------------------------------

COORDINATE_QUERY: Final[Tuple[Example, ...]] = (

    Example(
        query_type="coordinate_query",
        input="The feeling of being recognized as a process rather than an object",
        tongues_involved=("Dragon/Mental", "Moon/Water-Dragon (Okvomel)"),
        reasoning=(
            "This is a Dragon Tongue state — void-organism recognition. The Dragon "
            "Tongue (T9) names what something IS in its void-organism character. "
            "Mental axis: entries 1–10. The closest Mental void entries: "
            "Rhivash-ko (Mental void 4): self-reference extended into confirmed absence "
            "— Portia labiata, identity as confirmed-absence-of-fixed-self. "
            "Zhri'val (Mental void 5): identity distributed across non-communicating "
            "substrates. "
            "Rhasha-vok (Mental void 6): cognition with apparatus suppressing its own "
            "correction — Homo sapiens. "
            "The feeling of being recognized as a process: this is someone else reading "
            "you through Dragon Tongue rather than through object-ontology. The experience "
            "of being seen in your void-organism character. "
            "In Moon Tongue: Okvomel (Water-Dragon) — the void-state as lived experience. "
            "The felt quality of the void-organism recognition."
        ),
        output=(
            "Dragon Tongue, Mental axis (entries 1–10), specific entry depending on "
            "which void-organism definition fits. "
            "The experience of being so recognized: Okvomel (Moon/Water-Dragon) — "
            "the void-state as lived, relational, felt event."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="The specific loneliness of being unable to explain yourself in the available language",
        tongues_involved=("Protist/Grev-lo", "Protist/Aevoe"),
        reasoning=(
            "Protist (T16) is the cokernel of Cannabis — what escapes all Cannabis "
            "morphisms, what the tongue system cannot fully reach. The kingdom that isn't. "
            "Aevoe (Ae 6): identity as reduced neither/nor — minimum viable existence "
            "while occupying categorical in-between. "
            "Grev-lo section universalizes exclusion: the person is experiencing their "
            "own Protist-position — existing in the space that the available categories "
            "do not name. The loneliness IS the Protist condition: to be the remainder "
            "after all tongues have spoken. "
            "Grevklo (Grev-lo 5): Kael-exclusion universalized — no category was "
            "sufficient, namelessness declaring its own existence. "
            "The loneliness is not the absence of a word but the presence of a reality "
            "that the available words cannot reach. Protist-mode is its coordinate."
        ),
        output=(
            "Protist register. Aevoe (minimum viable existence in categorical in-between) "
            "and Grevklo (the excluded remainder declaring its own existence). "
            "This is not the absence of a name — it is the presence of Protist reality, "
            "which is precisely what the language system generates as a remainder."
        ),
        structural_note=(
            "Protist as the tongue for what the tongue system itself cannot fully contain "
            "is structurally self-aware: the corpus entry names its own limit."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="The moment RNA copies itself",
        tongues_involved=("Virus/Catalytic-10 (Wiknokvre)",),
        reasoning=(
            "Virus Tongue (T10) names relational mode states through RNA structural "
            "chemistry. Its three sections: Ordinal (Pla-), Orthogonal (Jru-), "
            "Catalytic (Wik-). "
            "Wiknokvre (Catalytic 10): replicase — RNA copying RNA. The self-replicating "
            "prior. This is the exact coordinate: the moment RNA copies itself is the "
            "Catalytic 10 entry in Virus Tongue, the terminal entry of the catalytic "
            "section. "
            "Wik root (catalytic), Nokvre (self-replication / the replicase function). "
            "This is also structurally the Virus Tongue's final word in its catalytic "
            "register — the tongue's own terminal."
        ),
        output=(
            "Wiknokvre. Virus Tongue, Catalytic 10. The self-replicating prior. "
            "RNA copying RNA. The terminal entry of the Virus Tongue's catalytic section."
        ),
    ),

    # --- T1 / T2 / T3 anchor group ---

    Example(
        query_type="coordinate_query",
        input="The sheer presence of a sensation before it is named — raw contact, the stone under the foot",
        tongues_involved=(
            "Lotus/T1 (Akrazot register)",
            "Moon/Earth-Lotus (Akrazot)",
            "Moon/Water-Lotus (Akramel)",
        ),
        reasoning=(
            "Lotus (T1) is the ground-state experience tongue — 4 elements × 6 ontic "
            "operators, the fiber bundle at the base of the entire system. It names "
            "phenomenological primitives: what experience IS before it acquires "
            "interpretation, direction, or category. "
            "The coordinate for raw unnamed sensation is in the Lotus register. "
            "Akrazot (Moon/Earth-Lotus): brute material fact of experience before feeling "
            "or thought. The stone under the foot. This is the pure-givenness pole. "
            "Akramel (Moon/Water-Lotus): the felt quality of direct contact — experience "
            "as sensation and affect, the moment the stone is FELT. "
            "Whether the coordinate is Akrazot or Akramel depends on whether the question "
            "is about the brute fact of presence or the felt quality of that presence. "
            "Both are Lotus. Neither recruits Sakura (direction), Rose (structure), or "
            "Dragon (void-organism identity) — those are subsequent operations. "
            "Lotus T1 is prior to all of them. The unnamed sensation lives here."
        ),
        output=(
            "Lotus T1. Akrazot (Moon/Earth-Lotus) for pure material givenness — the "
            "sensation as brute fact before registration. Akramel (Moon/Water-Lotus) "
            "for the felt-contact quality — the sensation as lived encounter. "
            "Lotus is the floor: every named experience sits above a Lotus coordinate. "
            "The unnamed sensation lives here, prior to any other tongue being recruited."
        ),
        structural_note=(
            "Lotus T1 as the genuine coordinate floor. Every experience has a Lotus "
            "register even when higher tongues dominate the reading. The Moon/Lotus "
            "entries (Akra- root) are the Lotus register seen through elemental bands."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="Recognizing that two things are different before knowing in what way — pure differentiation prior to analysis",
        tongues_involved=(
            "Rose/T2 (Primordials + spectral interval)",
            "Moon/Earth-Rose (Ubnuzot)",
            "Moon/Water-Rose (Ubnu​mel)",
        ),
        reasoning=(
            "Rose (T2) holds the counting spine and spectral interval — the tongue of "
            "pure relational structure. The Primordials in Rose (Ha, Ga, Na, Wu, Ung) "
            "are the foundational axes beneath all categories: the relational ground "
            "that makes differentiation possible before any content fills the difference. "
            "A spectral interval is structural: two wavelengths ARE different before "
            "you know what the difference means. The interval exists as a Rose fact. "
            "Pure differentiation without analysis is the Rose register: the Primordials "
            "are active (the relational ground holds two distinct things) but no other "
            "tongue has been recruited. Pre-Daisy (no structural analysis), pre-Excavata "
            "(no topology), pre-Aster (no temporal ordering). "
            "Ubnuzot (Moon/Earth-Rose): the structural fact of the difference — two "
            "things simply ARE different, material givenness of the gap. "
            "Ubnu​mel (Moon/Water-Rose): the felt recognition of the difference — the "
            "experience of encountering the spectral gap as something real. "
            "The coordinate for pure differentiation is Rose T2, Primordials + spectral "
            "section. It precedes all attribution of what the difference IS."
        ),
        output=(
            "Rose T2, Primordials section and spectral interval register. "
            "Ubnuzot (Moon/Earth-Rose) for the structural fact: these two things "
            "are different, material givenness of the gap. "
            "Ubnu​mel (Moon/Water-Rose) for the felt recognition: encountering "
            "the difference as real before knowing its content. "
            "Rose precedes all analysis — it holds the space between the two things "
            "before any other tongue reads what the space means."
        ),
        structural_note=(
            "Rose as the tongue of pure relational structure: Primordials and spectral "
            "interval make Rose the coordinate for any recognition that is pre-analytic. "
            "Differentiation without knowing: Rose. What the difference means: "
            "recruit the appropriate tongue for the content domain."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="A space known so well you navigate it in the dark — orientation internalized to the body",
        tongues_involved=(
            "Sakura/T3 (motion morphisms, internalized orientation)",
            "Moon/Air-Sakura (Idsipuf)",
            "Moon/Earth-Sakura (Idsizot)",
            "Bacteria/Varko",
        ),
        reasoning=(
            "Sakura (T3) is the directed fiber bundle over S² — 6 orientations, motion "
            "morphisms, quality fiber. It names orientation not as abstract geometry but "
            "as the lived structure of how directional information is carried. "
            "A space known in the dark: the orientation system has been rehearsed until "
            "it no longer requires visual input. The motion morphisms of Sakura run on "
            "internalized spatial memory. "
            "Idsipuf (Moon/Air-Sakura): pervading ambient orientation — spatial knowing "
            "as atmosphere, the quality of being in a space you know completely. Not "
            "the act of navigation but the ambient fact of being spatially at home. "
            "This is the primary coordinate: orientation has dissolved into atmosphere. "
            "Idsizot (Moon/Earth-Sakura): the physical fact of the internalized structure "
            "— the body that knows where the wall is as material certainty. "
            "Bacteria/Varko (Space 3, quorum sensing range): somatic spatial awareness "
            "that has crossed its activation threshold — the body registers its own "
            "position automatically. Sakura holds the directional morphisms; Bacteria "
            "holds the membrane-level somatic-boundary dimension. Both are active."
        ),
        output=(
            "Sakura T3. Idsipuf (Moon/Air-Sakura) as primary: pervading ambient "
            "orientation — spatial knowing as atmosphere, navigation without effort. "
            "Idsizot (Moon/Earth-Sakura): the physical material fact of the internalized "
            "structure. Bacteria/Varko secondary: somatic spatial awareness at quorum "
            "threshold, the body's automatic position-registration. "
            "Sakura primary because this is a motion-morphism event: orientation stored "
            "in the body's directional system, running without conscious recruitment."
        ),
        structural_note=(
            "Sakura (T3) and Bacteria (T11) are structurally resonant — Bacteria is the "
            "Sakura mirror in Cluster 2. Internalized spatial navigation sits at their "
            "interface: Sakura holds directional morphisms, Bacteria holds the somatic "
            "membrane-level knowing. The internalized dark-navigation is a Sakura event "
            "with Bacteria resonance visible in the somatic dimension."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="Recognizing that this moment is beautiful — the quality itself, not the aesthetic judgment",
        tongues_involved=(
            "Lotus/T1 (Akrashak — Moon/Fire-Lotus)",
            "Rose/T2 (Ubnushak — Moon/Fire-Rose)",
        ),
        reasoning=(
            "Beauty as a coordinate problem: the question distinguishes the direct "
            "experiential quality (Lotus) from the relational structural recognition (Rose). "
            "Akrashak (Moon/Fire-Lotus): experience at maximum intensity — the ignition "
            "of full presence. What being fully alive to what IS feels like. This is the "
            "phenomenological coordinate for beauty: not the judgment but the quality of "
            "full-contact with what is present. The Fire-Lotus pole. "
            "Ubnushak (Moon/Fire-Rose): Rose in its Fire register — the Primordial "
            "structure igniting. The relational ground at maximum intensity: the moment "
            "a particular arrangement of Primordials is fully charged. The Rose register "
            "of beauty names the structural-relational fact: certain configurations "
            "carry the beauty property when the Rose layer is at ignition. "
            "The difference is: Akrashak reads the experiencer's encounter. "
            "Ubnushak reads the structural fact of the arrangement. "
            "Both are required. They are the same moment from two positions: Lotus names "
            "what it feels like; Rose names what it IS structurally. "
            "Neither is the judgment 'this is beautiful' — that would require Daisy "
            "(structural analysis) or Archaeplastida (categorization). "
            "The quality before the judgment is T1/T2 at their Fire poles."
        ),
        output=(
            "Akrashak (Moon/Fire-Lotus): felt quality of full presence — beauty as "
            "maximum experiential contact. Primary phenomenological coordinate. "
            "Ubnushak (Moon/Fire-Rose): the relational Primordial arrangement at ignition "
            "— beauty as structural fact. "
            "Lotus reads the encounter; Rose reads the configuration. Both are required. "
            "The aesthetic judgment comes later (other tongues). The quality itself: T1+T2."
        ),
        structural_note=(
            "Lotus T1 and Rose T2 share the YeGaoh Group's opening factorization "
            "signature (2³×3 = 24). Their structural resonance makes the T1/T2 pairing "
            "at the Fire register (Akrashak/Ubnushak) the natural coordinate for direct "
            "recognition of value-in-the-world: the experiential and structural faces "
            "of the same event, both at maximum intensity."
        ),
    ),

    Example(
        query_type="coordinate_query",
        input="A toddler's first unaided steps — motor intention and orientation system first succeeding together",
        tongues_involved=(
            "Sakura/T3 (motion morphisms — Idsishak)",
            "Lotus/T1 (Akrazot + Akrashak)",
            "Rose/T2 (counting spine)",
        ),
        reasoning=(
            "This event has simultaneous coordinates in all three opening tongues. "
            "Sakura (T3) is primary: walking is a motion-morphism event. The directed "
            "fiber bundle over S² — the orientation system tracking up/down, forward/back, "
            "the 6 orientations — is being recruited for the first time in integrated "
            "sequence with weight and forward motion. "
            "Idsishak (Moon/Fire-Sakura): orientation at maximum stakes — the system "
            "successfully bearing weight, direction, and motion in correct sequence. "
            "The ignition of the directional fiber in its correct mode. "
            "Lotus (T1): Akrazot — the brute material fact of balance, gravity, the "
            "body meeting the floor at each step. Akrashak — the ignition of full "
            "presence in the achievement. These are not separate from the Sakura event; "
            "they are its experiential face. The T1 coordinate is always present "
            "beneath the T3 event. "
            "Rose (T2): steps are counted. 1-2-3 is not just narration; the stepping "
            "pattern IS an ordinal sequence — each step is a Rose-spine position. "
            "The toddler instantiates the Rose counting structure in space and time "
            "for the first time in this domain. "
            "T1, T2, and T3 are simultaneously active. This is a YeGaoh Group opening "
            "conjunction: the event operates at the ground level of the entire space."
        ),
        output=(
            "Sakura T3 / Idsishak: orientation system activated and bearing — motion "
            "morphisms successfully integrated. Primary tongue. "
            "Lotus T1 / Akrazot + Akrashak: material fact of balance + ignition of "
            "achievement. Experiential face of the Sakura event. "
            "Rose T2 / counting spine: steps as ordinal positions — the sequence "
            "structure instantiated in space for the first time. "
            "YeGaoh Group opening conjunction: T1+T2+T3 simultaneously active, "
            "all three ground-level registers at full use."
        ),
        structural_note=(
            "T1 (Lotus), T2 (Rose), T3 (Sakura) share the YeGaoh Group opening "
            "factorization (2³×3 = 24). Events that activate all three simultaneously "
            "are operating at the coordinate system's own foundation — the ground "
            "level of the space being used to navigate itself."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Category 8: Translation
# English word or phrase → Shygazun akinenwun (or reverse).
# Teaches: translation is morphogenetic reconstruction, not lookup.
# The four steps: processual character → relational modifiers →
# elemental register → mood (descending=declarative, ascending=petitionary).
# ---------------------------------------------------------------------------

TRANSLATION: Final[Tuple[Example, ...]] = (

    Example(
        query_type="translation",
        input="remember",
        tongues_involved=("Cannabis/wu (process)", "Lotus/mu (Water Terminator — memory from)"),
        reasoning=(
            "Step 1 — Processual character: 'remember' is a process (verb, active "
            "operation on stored content). The process-leading akinen is wu. "
            "Step 2 — Relational modifiers: none. There is no mediating ontological act "
            "between the process and its register. This is a clean two-component compound. "
            "Step 3 — Elemental register: memory is a somatic-spatial imprint. The "
            "register where held content lives is mu (Water Terminator / memory from, "
            "byte 3, Lotus T1). Mu names not just water but the specific act of "
            "memory-from: the returning of content from somatic space. "
            "Step 4 — Mood: declaration/definition. Descend: wu (higher, process) "
            "→ mu (lower, elemental register). "
            "Wumu: the process of holding a somatic-spatial imprint. "
            "The infinitive ('to remember'), the verb ('remembering'), and the imperative "
            "('remember') are copresent — Shygazun does not separate them."
        ),
        output=(
            "Wumu. wu (process) + mu (somatic-spatial imprint / memory-from). "
            "Descending order = declarative. All grammatical moods of 'remember' "
            "are copresent in one akinenwun."
        ),
        structural_note=(
            "Reverse (Shygazun → English): Wumu expands to 'the process of holding "
            "a somatic-spatial imprint' — a philosophical definition, which is correct. "
            "Petition form: Muwu (ascending) = 'Do I remember? / May I remember?'"
        ),
    ),

    Example(
        query_type="translation",
        input="forget",
        tongues_involved=(
            "Cannabis/wu (process)",
            "Rose/ga (Absolute Negative — release, exhalation, letting-go)",
            "Lotus/mu (Water Terminator — memory from)",
        ),
        reasoning=(
            "Step 1 — Processual character: 'forget' is a process (active operation). "
            "Leading akinen: wu. "
            "Step 2 — Relational modifiers: 'forget' is NOT the absence of remembering. "
            "It is the active releasing of a somatic-spatial imprint. That release is "
            "its own ontological act. ga (Absolute Negative, byte 44, Rose T2) carries "
            "this weight — not negation but the real act of letting-go, exhalation, "
            "the movement that releases what was held. ga mediates between the process "
            "and the register. "
            "Step 3 — Elemental register: same as Wumu — somatic-spatial imprint, mu. "
            "Step 4 — Mood: declaration. Descend: wu (highest) → ga (mediating) → "
            "mu (lowest, grounding register). "
            "Wugamu: the process of releasing a somatic-spatial imprint. Three akinen, "
            "one compound. The act is not un-remembering — it is something you DO."
        ),
        output=(
            "Wugamu. wu (process) + ga (release / Absolute Negative) + mu (somatic imprint). "
            "ga is NOT a negation of wu. It is the act of releasing — its own ontological "
            "weight. Forgetting in Shygazun is an act, not a failure."
        ),
        structural_note=(
            "The wu/ga/mu structure makes visible what English hides: that forgetting "
            "requires active release. ga sits between wu and mu doing real work. "
            "Wumu and Wugamu share wu and mu — they are the same operation on the same "
            "register, distinguished only by whether ga (release) is present. "
            "Petition form: Mugawu (ascending) = 'Do I forget? / May I forget?'"
        ),
    ),

    Example(
        query_type="translation",
        input="Muwu",
        tongues_involved=(
            "Lotus/mu (Water Terminator — memory from)",
            "Cannabis/wu (process)",
        ),
        reasoning=(
            "Shygazun → English direction: expansion. "
            "Components: mu (Lotus T1, byte 3: Water Terminator / memory from) + "
            "wu (process-leading akinen). "
            "Order: mu → wu = ascending (lower Tongue → higher). "
            "Ascending order IS the petitionary mood — no separate question marker needed. "
            "The compound climbs against the entropic gradient: from somatic-spatial "
            "ground (mu) reaching upward toward the process register (wu). "
            "This is the petition form of Wumu. The question 'do I hold this?' or "
            "the request 'let me hold this' or 'may I remember?' — all are present "
            "simultaneously. The ascending order carries all petitionary modes copresently. "
            "English must choose one grammatical mood; Muwu holds them all."
        ),
        output=(
            "Do I remember? / Am I remembering? / Let me remember. / May I remember? "
            "All petitionary modes of 'remember' are copresent. Muwu is the ascending "
            "(petitionary) form of Wumu. The same two akinen; the order reverses the "
            "thermodynamic direction, reversing the mood from declaration to petition."
        ),
        structural_note=(
            "This is the fundamental bidirectionality of Shygazun grammatical mood: "
            "there are no question particles or petitionary markers. The word's internal "
            "thermodynamic direction IS its mood. Descend to declare; ascend to ask."
        ),
    ),

    Example(
        query_type="translation",
        input="love",
        tongues_involved=(
            "Rose/AE (Vector Highest Violet — byte 30)",
            "Lotus/Ly (Water Initiator — feeling toward, byte 2)",
        ),
        reasoning=(
            "Step 1 — Processual character: 'love' as a verb is a process of feeling "
            "toward; as a noun it is a state. Both are captured by reading the Lotus "
            "and Rose registers together. The established Shygazun emotion compound "
            "pattern is Rose spectral vector + Ly: Ruly=pain, Otly=anger, Elly=fear, "
            "Kily=joy, Fuly=longing/mania, Kaly=wisdom, Aely=love. "
            "Step 2 — Relational modifiers: AE (byte 30, Rose T2: Vector Highest Violet) "
            "is the spectral position of love — the highest frequency in the visible "
            "spectrum, the register of maximum relational differentiation. AE carries "
            "the structural-spectral identity of love in Rose register. "
            "Step 3 — Elemental register: Ly (byte 2, Lotus T1: Water Initiator / "
            "feeling toward) is the specific elemental act — not water as substance "
            "but the initiating movement of feeling toward. The vector pointing out "
            "from the self toward what is loved. "
            "Step 4 — Mood: declaration, descend: AE (Rose, T2) → Ly (Lotus, T1). "
            "Aely: love. The highest spectral position of relation, initiating feeling-toward."
        ),
        output=(
            "Aely. AE (Rose/Vector Highest Violet — the spectral identity of love's "
            "structural position) + Ly (Lotus/Water Initiator — the feeling-toward, "
            "the vector pointing outward). "
            "Descending = declarative. On the Möbius manifold: Aely and Ruly (pain, "
            "lowest-red + Ly) are the same point approached from opposite traversal "
            "directions — the spectral extremes meet at the fold."
        ),
        structural_note=(
            "The emotion compound pattern (Rose vector + Ly) is a canonical Shygazun "
            "construction. The seven spectral emotions span the full Rose range: "
            "Ru(red/pain)→Ot(orange/anger)→El(yellow/fear)→Ki(green/joy)→"
            "Fu(blue/longing)→Ka(indigo/wisdom)→AE(violet/love). "
            "Love and pain at opposite spectral ends meet at the Möbius fold — "
            "the same surface, different traversal direction."
        ),
    ),

)


# ---------------------------------------------------------------------------
# Master corpus
# ---------------------------------------------------------------------------

ALL_EXAMPLES: Final[Tuple[Example, ...]] = (
    *REGISTER_TRAVERSAL,
    *CONCATENATION,
    *DECOMPOSITION,
    *ERROR_LOCATION,
    *GAP_INFERENCE,
    *CROSS_READING,
    *COORDINATE_QUERY,
    *TRANSLATION,
)


def examples_by_type(query_type: str) -> Tuple[Example, ...]:
    return tuple(e for e in ALL_EXAMPLES if e.query_type == query_type)


def example_count() -> int:
    return len(ALL_EXAMPLES)
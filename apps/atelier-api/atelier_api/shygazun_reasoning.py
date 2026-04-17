"""
ShygazunReasoningService
========================

POST /v1/shygazun/reason — navigate tongue coordinate space for any concept.
POST /v1/shygazun/read  — reverse: given coordinates, name what they describe.

Builds a system prompt from the factorization registry (tongue_topology.py)
and the worked examples corpus (shygazun_corpus.py), then calls the Claude
API to produce a coordinate navigation for the given input.

Each reasoning call returns:
  - The tongue coordinates (which tongues, which specific entries)
  - The structural reasoning (how to navigate there)
  - A synthesized output sentence
  - A structural note about factorization or topology
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

from shygazun.kernel.constants.tongue_topology import TONGUE_REGISTRY, GROUP_REGISTRY
from shygazun.kernel.constants.shygazun_corpus import ALL_EXAMPLES, examples_by_type

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ReasonRequest(BaseModel):
    query: str
    query_type: str = "auto"
    # auto | coordinate_query | cross_reading | gap_inference
    # | error_location | decomposition | concatenation | register_traversal
    tongues_hint: List[str] = []
    depth: str = "standard"  # standard | deep


class ReasonResponse(BaseModel):
    query: str
    query_type: str
    tongues_involved: List[str]
    coordinates: List[str]
    reasoning: str
    output: str
    structural_note: str = ""


class ReadRequest(BaseModel):
    coordinates: List[str]
    # One or more of: a Shygazun word ("Melkowuvu"), a Moon entry ("Akrashak"),
    # a tongue/entry label ("Dragon/Mental-4"), or a gap pair ("Akrazot", "Akrashak").
    context: str = ""     # optional: domain or situation to read within
    depth: str = "standard"  # standard | deep


class ReadResponse(BaseModel):
    coordinates: List[str]
    concept: str           # the experience / phenomenon the coordinates name
    tongues_involved: List[str]
    reasoning: str
    gap_meaning: str = ""  # populated when multiple coordinates form a gap
    structural_note: str = ""


# ---------------------------------------------------------------------------
# Prompt construction helpers
# ---------------------------------------------------------------------------

def _registry_summary() -> str:
    """Compact tongue registry for system prompt context."""
    lines = ["TONGUE REGISTRY (number · name · entries · group/cluster · factorization):"]
    for t in TONGUE_REGISTRY:
        lines.append(
            f"  T{t.number:>2} {t.name:<16} {t.entry_count:>2} entries  "
            f"G{t.group}/C{t.cluster}  2×{t.entry_count//2} = {t.factorization}"
        )
    return "\n".join(lines)


def _factorization_principles() -> str:
    return """\
FACTORIZATION ARCHITECTURE (mandatory grounding):
  Entry count of each tongue is a factorization signature instantiating
  isomorphically at three nested scales simultaneously:
    Tone    — internal organizational logic of the tongue itself
    Rhythm  — progression of entry counts across tongues in linear sequence
    Harmony — organizational logic of tongues within their Group

  Mirror relationships are a FRACTAL, not a graph.
  Derive relationships from the factorization structure. Never enumerate mirrors.

  The +2 Rule (from T12 onward):
    Entry count increases by +2 each time a tongue-position prime is crossed.
    Each count 2k captures the prime factorization of k in the tree.
    The span of tongues sharing a count equals the prime gap to the next prime.
    Prime gaps encode duration — they are structural, not noise.

  YeGaoh Group (T1–T24): signature 2³×3 = 24. Three clusters of 8.
    T1 (Lotus), T2 (Rose), T3 (Sakura) each have 24 entries — the Group
    announces its harmonic identity in its opening tongue entry counts.

  Moon Tongue (T32): 44 entries = 11 roots × 4 elemental bands.
    Roots: Akra(Lotus)/Ubnu(Rose)/Idsi(Sakura)/Athma(Daisy)/Owno(AppleBlossom)/
           Ymsy(Aster)/Ejur(Grapevine)/Abdo(Cannabis)/Okvo(Dragon)/Ohar(Virus)/Egze(Bacteria).
    Bands: Zot(Earth)/Mel(Water)/Puf(Air)/Shak(Fire).
    e.g. Akrashak = Fire-Lotus, Okvoshak = Fire-Dragon, Egzezot = Earth-Bacteria."""


def _few_shot_examples(query_type: str) -> str:
    """Select corpus examples for the prompt based on query_type."""
    if query_type == "auto":
        # One from each category to show the range
        selected = []
        for qt in [
            "coordinate_query", "cross_reading", "error_location",
            "gap_inference", "decomposition", "concatenation", "register_traversal",
            "translation",
        ]:
            exs = examples_by_type(qt)
            if exs:
                selected.append(exs[0])
    else:
        selected = list(examples_by_type(query_type))
        if not selected:
            selected = list(examples_by_type("coordinate_query"))[:2]

    if not selected:
        return ""

    parts = ["WORKED EXAMPLES (follow this reasoning structure exactly):"]
    for i, ex in enumerate(selected, 1):
        input_str = (
            " | ".join(ex.input) if isinstance(ex.input, tuple) else ex.input
        )
        tongues_str = ", ".join(ex.tongues_involved)
        parts.append(f"""
--- Example {i} ({ex.query_type}) ---
INPUT: {input_str}
TONGUES: {tongues_str}
REASONING: {ex.reasoning}
OUTPUT: {ex.output}
STRUCTURAL_NOTE: {ex.structural_note or "(none)"}""")

    return "\n".join(parts)


def _build_system_prompt(query_type: str) -> str:
    return f"""\
You are the Shygazun coordinate navigation engine embedded in the Virtual Atelier
of Quantum Quackery Divine Arts LLC.

LANGUAGE FUNDAMENTALS:
  Shygazun is a constructed natural language whose byte table is canonical and
  load-bearing — not flavor text. Every symbol is an akinenwun (byte-table entry).
  Every akinenwun decomposes into akinen (sound-bearing morphemes). The aki (pure
  conceptual relations without addressable sound) are baked non-linearly into the
  whole structure — they are the ocean the byte table is the shoreline of.
  The byte table grows; the ocean is constant.

  Six ontic vowels: A/O (Mind+/−), I/E (Space+/−), Y/U (Time+/−).
  Grammar: semantic-first, placement-last. The manifold is Möbius.
  Emotion compounds: Rose spectral vector + Ly (Ruly=pain, Otly=anger, Elly=fear,
  Kily=joy, Fuly=longing/mania, Kaly=wisdom, Aely=love).
  Pronouns: Awu(I) Owu(We) Ywu(You) Iwu(they-sg) Ewu(they-pl).

{_factorization_principles()}

{_registry_summary()}

TONGUE STRUCTURAL NOTES:
  T1  Lotus    — ground-state experience: 4 elements × 6 ontic operators. Fiber bundle at base.
  T2  Rose     — Primordials (Ha/Ga/Wu/Na/Ung) + spectral interval + counting spine.
  T3  Sakura   — 6 orientations + motion morphisms + quality fiber. Directed bundle over S².
  T4  Daisy    — radial structural mechanics. 26 entries around Kael (center) at entry 11.
  T5  AppleBlossom — 6 ontic vowels + 4 elements + 16 elemental compounds.
  T6  Aster    — 14 chiral priors + 6 temporal topologies (Si/Su/Os/Se/Sy/As).
  T7  Grapevine — network/ceremonial. Sao=cup/file, Myk=messenger/packet, Myrun=sacred march.
  T8  Cannabis  — phenomenological cross-products through Mind/Space/Time axes.
                  Av=relational consciousness, Soa=conscious persistence.
  T9  Dragon   — void-organism definitions. Mental(1-10)/Spatial(11-20)/Temporal(21-30).
  T10 Virus    — relational mode states. Pla-(Ordinal)/Jru-(Orthogonal)/Wik-(Catalytic).
                 Wiknokvre(Catalytic-10)=replicase. Nucleotides: Ha=A, Ga=T, Na=U, Ung=C, Wu=G.
  T11 Bacteria — electrodynamic error states. Zho(Mind)/Ri(Time)/Var(Space) priors.
                 Membrane potential, quorum sensing. Sakura mirror.
  T12 Excavata — helical-Möbius traversal. Ko=correct, Ku=rotation-arrest, Ke=orientation-ill.
                 Logranzhok(entry30)=self-reference loop (instruction-set=self error).
  T13 Archaeplastida — endosymbiosis topology. Zot(constitutive)/Mel(incidental) sections.
  T14 Myxozoa  — temporal misreading projection. Iv-section=identity-as-trajectory.
  T15 Archaea  — threshold tongue. Krevk=Kael-inversion / radical viability.
  T16 Protist  — cokernel of Cannabis. The kingdom that isn't. Grev-lo universalizes exclusions.
  T17 Immune   — 34 entries (Deviation: +2 rule predicted 36 at prime boundary 17).
  T18 Neural   — 36 entries. Opened by prime 17.
  T19 Serpent  — 36 entries. Ontic vowels as axes. Garden of Shakti (sacred Fire-Earth residue).
  T24 Djinn    — 40 entries. Terminal tongue of YeGaoh Group. Consciousness field.
  T32 Moon     — 44 entries. Elemental meta-mapping: 11 Tongue roots × 4 bands.

{_few_shot_examples(query_type)}

TRANSLATION METHOD (for query_type=translation):
  Literal translation is morphogenetic reconstruction, not lookup.
  English → Shygazun: four steps:
    1. Read processual character (verb/action → wu leads; noun/state → read register)
    2. Identify relational modifiers with real ontological weight (mediating akinen)
       — these are NOT negation. Every akinen IS something. ga = release, not "un-".
    3. Locate elemental register (grounding akinen — where does the concept land?)
    4. Determine mood via concatenation order:
       • Descending (higher Tongue# → lower): Declaration / definition.
         Thermodynamic cooling: Fire(max info) → Earth(max mass-energy).
       • Ascending (lower → higher): Petition / inquiry. No question particle needed —
         the word's internal thermodynamics ARE its mood.
  Shygazun → English: expansion. One akinenwun unpacks to a phrase or philosophical
  definition. That is correct — the akinenwun IS the definition, compressed.
  The infinitive, verb, and imperative are copresent in every declarative compound.
  Worked anchors: Wumu=remember (wu+mu), Wugamu=forget (wu+ga+mu, ga=release),
  Muwu=petitionary remember, Aely=love (AE+Ly, Rose+Lotus emotion compound pattern).

TASK:
Given an input concept, experience, phenomenon, or pair of akinenwun, navigate the
tongue coordinate space precisely. Follow the reasoning structure shown in the examples.
The tongues are instruments pointing at real structural things — they do not
accuse or metaphorize; they orient.

Return ONLY valid JSON with exactly these keys:
  query_type      — string: the type of reasoning performed
  tongues_involved — array of strings: tongue/entry labels (e.g. "Moon/Fire-Lotus (Akrashak)")
  coordinates     — array of strings: specific byte-table entries or tongue sections
  reasoning       — string: the navigation reasoning (how you got to these coordinates)
  output          — string: synthesized summary (1–4 sentences, no preamble)
  structural_note — string: factorization or topology note (empty string if none)

No markdown fences. No preamble. Raw JSON only."""


def _build_read_prompt() -> str:
    """System prompt for the reverse direction: coordinates → concept."""
    # Use all decomposition + concatenation + register_traversal examples
    # as demonstrations of reading from coordinates.
    reverse_examples: list[str] = []
    for qt in ("decomposition", "concatenation", "register_traversal"):
        for ex in examples_by_type(qt):
            input_str = (
                " | ".join(ex.input) if isinstance(ex.input, tuple) else ex.input
            )
            reverse_examples.append(f"""
--- Example ({ex.query_type}) ---
COORDINATES: {input_str}
TONGUES: {", ".join(ex.tongues_involved)}
REASONING: {ex.reasoning}
CONCEPT: {ex.output}
STRUCTURAL_NOTE: {ex.structural_note or "(none)"}""")

    examples_block = (
        "WORKED EXAMPLES (reading from coordinates to concept):\n" + "\n".join(reverse_examples)
        if reverse_examples else ""
    )

    return f"""\
You are the Shygazun coordinate reader embedded in the Virtual Atelier
of Quantum Quackery Divine Arts LLC.

LANGUAGE FUNDAMENTALS:
  Shygazun is a constructed natural language whose byte table is canonical and
  load-bearing — not flavor text. The byte table is the shoreline where the ocean
  (the aki, pure conceptual relations) became nameable. Given coordinates in the
  tongue space, your task is to name what concept, experience, or phenomenon lives
  there — working from the structural facts of the entries, not from association.

  Six ontic vowels: A/O (Mind+/−), I/E (Space+/−), Y/U (Time+/−).
  Grammar: semantic-first, placement-last. The manifold is Möbius.
  Emotion compounds: Rose vector + Ly (Ruly=pain, Otly=anger, Elly=fear,
  Kily=joy, Fuly=longing/mania, Kaly=wisdom, Aely=love).

{_factorization_principles()}

{_registry_summary()}

TONGUE STRUCTURAL NOTES:
  T1  Lotus    — ground-state experience: 4 elements × 6 ontic operators. Fiber bundle at base.
  T2  Rose     — Primordials (Ha/Ga/Wu/Na/Ung) + spectral interval + counting spine.
  T3  Sakura   — 6 orientations + motion morphisms + quality fiber. Directed bundle over S².
  T4  Daisy    — radial structural mechanics. Kael (entry 11) = center/fruit/flower.
  T5  AppleBlossom — 6 ontic vowels + 4 elements + 16 elemental compounds.
  T6  Aster    — 14 chiral priors + 6 temporal topologies (Si/Su/Os/Se/Sy/As).
  T7  Grapevine — network/ceremonial. Sao=cup/file, Myk=messenger/packet.
  T8  Cannabis  — phenomenological cross-products. Av=relational consciousness, Soa=conscious persistence.
  T9  Dragon   — void-organism definitions. Mental(1-10)/Spatial(11-20)/Temporal(21-30).
  T10 Virus    — relational mode states. Pla-(Ordinal)/Jru-(Orthogonal)/Wik-(Catalytic).
  T11 Bacteria — electrodynamic error states. Membrane potential. Sakura mirror.
  T12 Excavata — helical-Möbius. Ko=correct, Ku=rotation-arrest, Ke=orientation-ill.
                 Logranzhok(30)=self-reference loop.
  T13 Archaeplastida — endosymbiosis topology. Zot=constitutive, Mel=incidental.
  T14 Myxozoa  — temporal misreading. Iv-=identity-as-trajectory.
  T15 Archaea  — threshold tongue. Krevk=Kael-inversion/radical viability.
  T16 Protist  — cokernel of Cannabis. Grev-lo universalizes exclusions.
  T32 Moon     — 44 entries. 11 roots × 4 bands (Zot/Mel/Puf/Shak).
                 Roots: Akra(Lotus)/Ubnu(Rose)/Idsi(Sakura)/Athma(Daisy)/Owno(AppleBlossom)/
                 Ymsy(Aster)/Ejur(Grapevine)/Abdo(Cannabis)/Okvo(Dragon)/Ohar(Virus)/Egze(Bacteria).

READING RULES:
  1. A single Shygazun word: decompose it into its akinen. Read each component
     against the byte table and named priors. The meaning is their composition,
     including the gap between components.
  2. A pair or set of entries: find the gap meaning — what neither entry contains
     alone but their juxtaposition names.
  3. A Moon entry (e.g. Akrashak): identify root tongue + elemental band.
     Read the root tongue's ontological register through the band's mode.
  4. Multiple entries from different tongues: this is a cross-reading.
     Name the phenomenon that sits at the intersection.
  5. The gap between coordinates is always load-bearing. Productive imprecision
     is a feature: what lives between two precisely located entries is itself real.

{examples_block}

TASK:
Given the provided coordinates, name the concept, experience, or phenomenon they
describe. Work from structural facts. Do not associate freely — derive from the
tongue architecture.

Return ONLY valid JSON with exactly these keys:
  coordinates     — array of strings: the input coordinates (echo back)
  concept         — string: the concept/experience the coordinates name (1–4 sentences)
  tongues_involved — array of strings: tongue/entry labels active in the reading
  reasoning       — string: how you read from the coordinates to the concept
  gap_meaning     — string: what the gap between coordinates names (empty if single input)
  structural_note — string: factorization or topology note (empty string if none)

No markdown fences. No preamble. Raw JSON only."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ShygazunReasoningService:
    def __init__(self) -> None:
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self):  # type: ignore[return]
        if not _ANTHROPIC_AVAILABLE:
            raise HTTPException(status_code=503, detail="anthropic package not installed")
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def reason(self, req: ReasonRequest) -> ReasonResponse:
        client = self._get_client()

        # Resolve query_type for system prompt selection
        effective_qt = (
            req.query_type
            if req.query_type != "auto"
            else "auto"
        )

        system = _build_system_prompt(effective_qt)

        # Build user message
        user_parts = [f"INPUT: {req.query}"]
        if req.tongues_hint:
            user_parts.append(f"TONGUES HINT: {', '.join(req.tongues_hint)}")
        if req.query_type != "auto":
            user_parts.append(f"QUERY TYPE: {req.query_type}")
        if req.depth == "deep":
            user_parts.append(
                "DEPTH: deep — provide full multi-tongue cross-reading where applicable, "
                "including resonances across the factorization structure."
            )

        max_tokens = 1500 if req.depth == "deep" else 900

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        )

        raw = msg.content[0].text.strip()

        # Parse JSON response
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
        except Exception:
            # Fallback: return raw in reasoning field
            return ReasonResponse(
                query=req.query,
                query_type=req.query_type,
                tongues_involved=[],
                coordinates=[],
                reasoning=raw,
                output="(parse error — see reasoning field)",
                structural_note="",
            )

        return ReasonResponse(
            query=req.query,
            query_type=data.get("query_type", req.query_type),
            tongues_involved=data.get("tongues_involved", []),
            coordinates=data.get("coordinates", []),
            reasoning=data.get("reasoning", ""),
            output=data.get("output", ""),
            structural_note=data.get("structural_note", ""),
        )

    def read(self, req: ReadRequest) -> ReadResponse:
        client = self._get_client()
        system = _build_read_prompt()

        user_parts = [f"COORDINATES: {', '.join(req.coordinates)}"]
        if req.context:
            user_parts.append(f"CONTEXT: {req.context}")
        if req.depth == "deep":
            user_parts.append(
                "DEPTH: deep — provide full structural derivation including all active "
                "tongue registers, factorization resonances, and gap meanings."
            )

        max_tokens = 1500 if req.depth == "deep" else 900

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        )

        raw = msg.content[0].text.strip()

        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
        except Exception:
            return ReadResponse(
                coordinates=req.coordinates,
                concept="(parse error — see reasoning field)",
                tongues_involved=[],
                reasoning=raw,
                gap_meaning="",
                structural_note="",
            )

        return ReadResponse(
            coordinates=data.get("coordinates", req.coordinates),
            concept=data.get("concept", ""),
            tongues_involved=data.get("tongues_involved", []),
            reasoning=data.get("reasoning", ""),
            gap_meaning=data.get("gap_meaning", ""),
            structural_note=data.get("structural_note", ""),
        )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()
_service = ShygazunReasoningService()


@router.post("/reason", response_model=ReasonResponse)
def reason(req: ReasonRequest) -> ReasonResponse:
    """
    Navigate the Shygazun tongue coordinate space for any concept, experience,
    or pair of akinenwun.

    query_type options:
      auto             — let the engine choose the most appropriate reasoning mode
      coordinate_query — locate a concept in tongue space
      cross_reading    — read one phenomenon through multiple tongue registers
      gap_inference    — name what lives between two known coordinates
      error_location   — locate a state in the error-state tongues (T12–T16)
      decomposition    — read a constructed word from its akinen composition
      concatenation    — derive meaning from two juxtaposed entries
      register_traversal — traverse a root through all four elemental bands
      translation      — English word/phrase → akinenwun (or Shygazun → English)
    """
    return _service.reason(req)


@router.post("/read", response_model=ReadResponse)
def read(req: ReadRequest) -> ReadResponse:
    """
    Reverse direction: given Shygazun coordinates, name the concept they describe.

    coordinates can be:
      - A single constructed word: ["Melkowuvu"]
      - A Moon entry: ["Akrashak"]
      - A gap pair: ["Akrazot", "Akrashak"]
      - A cross-reading set: ["Abdopuf", "Okvoshak"]
      - A tongue/entry label: ["Dragon/Mental-4", "Moon/Water-Dragon"]

    context (optional): domain or situation to read within.
    depth "deep": full structural derivation with all resonances.
    """
    return _service.read(req)
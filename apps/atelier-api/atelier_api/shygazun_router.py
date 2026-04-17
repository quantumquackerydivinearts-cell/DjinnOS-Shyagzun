"""
shygazun_router.py
Shygazun language engine for atelier-api.
Mount at /shygazun in your main FastAPI app:
    from shygazun_router import router as shygazun_router
    app.include_router(shygazun_router, prefix="/shygazun", tags=["shygazun"])
Requires: anthropic (pip install anthropic)
Place byte_table.py (your existing module) in the same directory.
"""

from __future__ import annotations

import os
import json
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Byte table — inline so the router is self-contained.
# If you already have byte_table.py, replace this with:
#   from byte_table import SHYGAZUN_BYTE_TABLE, SHYGAZUN_BYTE_ROWS
# ---------------------------------------------------------------------------

BYTE_ROWS: list[dict] = [
    {"decimal":0,"binary":"00000000","tongue":"Lotus","symbol":"Ty","meaning":"Earth Initiator / material beginning"},
    {"decimal":1,"binary":"00000001","tongue":"Lotus","symbol":"Zu","meaning":"Earth Terminator / empirical closure"},
    {"decimal":2,"binary":"00000010","tongue":"Lotus","symbol":"Ly","meaning":"Water Initiator / feeling toward"},
    {"decimal":3,"binary":"00000011","tongue":"Lotus","symbol":"Mu","meaning":"Water Terminator / memory from"},
    {"decimal":4,"binary":"00000100","tongue":"Lotus","symbol":"Fy","meaning":"Air Initiator / thought toward"},
    {"decimal":5,"binary":"00000101","tongue":"Lotus","symbol":"Pu","meaning":"Air Terminator / stasis / stuck"},
    {"decimal":6,"binary":"00000110","tongue":"Lotus","symbol":"Shy","meaning":"Fire Initiator / pattern toward"},
    {"decimal":7,"binary":"00000111","tongue":"Lotus","symbol":"Ku","meaning":"Fire Terminator / death / end"},
    {"decimal":8,"binary":"00001000","tongue":"Lotus","symbol":"Ti","meaning":"Here / near presence"},
    {"decimal":9,"binary":"00001001","tongue":"Lotus","symbol":"Ta","meaning":"Active being / presence"},
    {"decimal":10,"binary":"00001010","tongue":"Lotus","symbol":"Li","meaning":"New / odd"},
    {"decimal":11,"binary":"00001011","tongue":"Lotus","symbol":"La","meaning":"Tense / excited"},
    {"decimal":12,"binary":"00001100","tongue":"Lotus","symbol":"Fi","meaning":"Known / context-sensitive"},
    {"decimal":13,"binary":"00001101","tongue":"Lotus","symbol":"Fa","meaning":"Complex / old"},
    {"decimal":14,"binary":"00001110","tongue":"Lotus","symbol":"Shi","meaning":"Related / clear"},
    {"decimal":15,"binary":"00001111","tongue":"Lotus","symbol":"Sha","meaning":"Intellect of spirit"},
    {"decimal":16,"binary":"00010000","tongue":"Lotus","symbol":"Zo","meaning":"Absence / passive non-being"},
    {"decimal":17,"binary":"00010001","tongue":"Lotus","symbol":"Mo","meaning":"Relaxed / silent"},
    {"decimal":18,"binary":"00010010","tongue":"Lotus","symbol":"Po","meaning":"Simple / new"},
    {"decimal":19,"binary":"00010011","tongue":"Lotus","symbol":"Ko","meaning":"Experience / intuition"},
    {"decimal":20,"binary":"00010100","tongue":"Lotus","symbol":"Ze","meaning":"There / far"},
    {"decimal":21,"binary":"00010101","tongue":"Lotus","symbol":"Me","meaning":"Familiar / home"},
    {"decimal":22,"binary":"00010110","tongue":"Lotus","symbol":"Pe","meaning":"Unknown / insensitive"},
    {"decimal":23,"binary":"00010111","tongue":"Lotus","symbol":"Ke","meaning":"Incoherent / ill"},
    {"decimal":24,"binary":"00011000","tongue":"Rose","symbol":"Ru","meaning":"Vector Lowest Red"},
    {"decimal":25,"binary":"00011001","tongue":"Rose","symbol":"Ot","meaning":"Vector Orange"},
    {"decimal":26,"binary":"00011010","tongue":"Rose","symbol":"El","meaning":"Vector Yellow"},
    {"decimal":27,"binary":"00011011","tongue":"Rose","symbol":"Ki","meaning":"Vector Green"},
    {"decimal":28,"binary":"00011100","tongue":"Rose","symbol":"Fu","meaning":"Vector Blue"},
    {"decimal":29,"binary":"00011101","tongue":"Rose","symbol":"Ka","meaning":"Vector Indigo"},
    {"decimal":30,"binary":"00011110","tongue":"Rose","symbol":"AE","meaning":"Vector Highest Violet"},
    {"decimal":31,"binary":"00011111","tongue":"Rose","symbol":"Gaoh","meaning":"Number 12 / 0"},
    {"decimal":43,"binary":"00101011","tongue":"Rose","symbol":"Ha","meaning":"Absolute Positive"},
    {"decimal":44,"binary":"00101100","tongue":"Rose","symbol":"Ga","meaning":"Absolute Negative"},
    {"decimal":45,"binary":"00101101","tongue":"Rose","symbol":"Wu","meaning":"Process / Way"},
    {"decimal":46,"binary":"00101110","tongue":"Rose","symbol":"Na","meaning":"Neutral / Integration"},
    {"decimal":47,"binary":"00101111","tongue":"Rose","symbol":"Ung","meaning":"Piece / Point"},
    {"decimal":48,"binary":"00110000","tongue":"Sakura","symbol":"Jy","meaning":"Top"},
    {"decimal":49,"binary":"00110001","tongue":"Sakura","symbol":"Ji","meaning":"Starboard"},
    {"decimal":50,"binary":"00110010","tongue":"Sakura","symbol":"Ja","meaning":"Front"},
    {"decimal":51,"binary":"00110011","tongue":"Sakura","symbol":"Jo","meaning":"Back"},
    {"decimal":52,"binary":"00110100","tongue":"Sakura","symbol":"Je","meaning":"Port"},
    {"decimal":53,"binary":"00110101","tongue":"Sakura","symbol":"Ju","meaning":"Bottom"},
    {"decimal":54,"binary":"00110110","tongue":"Sakura","symbol":"Dy","meaning":"Hence / Heretofore"},
    {"decimal":55,"binary":"00110111","tongue":"Sakura","symbol":"Di","meaning":"Traveling / Distancing"},
    {"decimal":56,"binary":"00111000","tongue":"Sakura","symbol":"Da","meaning":"Meeting / Conjoined"},
    {"decimal":57,"binary":"00111001","tongue":"Sakura","symbol":"Do","meaning":"Parting / Divorced"},
    {"decimal":58,"binary":"00111010","tongue":"Sakura","symbol":"De","meaning":"Domesticating / Staying"},
    {"decimal":59,"binary":"00111011","tongue":"Sakura","symbol":"Du","meaning":"Whither / Status of"},
    {"decimal":60,"binary":"00111100","tongue":"Sakura","symbol":"By","meaning":"When-hence / Eventual"},
    {"decimal":61,"binary":"00111101","tongue":"Sakura","symbol":"Bi","meaning":"Crowned / Owning"},
    {"decimal":62,"binary":"00111110","tongue":"Sakura","symbol":"Ba","meaning":"Plain / Explicit"},
    {"decimal":63,"binary":"00111111","tongue":"Sakura","symbol":"Bo","meaning":"Hidden / Occulted"},
    {"decimal":64,"binary":"01000000","tongue":"Sakura","symbol":"Be","meaning":"Common / Outer / Wild"},
    {"decimal":65,"binary":"01000001","tongue":"Sakura","symbol":"Bu","meaning":"Since / Relational"},
    {"decimal":66,"binary":"01000010","tongue":"Sakura","symbol":"Va","meaning":"Order / Structure / Life"},
    {"decimal":67,"binary":"00000011","tongue":"Sakura","symbol":"Vo","meaning":"Chaos / Boundary-breakage / Mutation"},
    {"decimal":69,"binary":"01000101","tongue":"Sakura","symbol":"Vu","meaning":"Death-moment / Never / Now"},
    {"decimal":70,"binary":"01000110","tongue":"Sakura","symbol":"Vi","meaning":"Body / Wherever / What"},
    {"decimal":71,"binary":"01000111","tongue":"Sakura","symbol":"Vy","meaning":"Lifespan / Whenever / How"},
    {"decimal":72,"binary":"01001000","tongue":"Daisy","symbol":"Lo","meaning":"Segments / Identity"},
    {"decimal":73,"binary":"01001001","tongue":"Daisy","symbol":"Yei","meaning":"Component / Integrator"},
    {"decimal":75,"binary":"01001011","tongue":"Daisy","symbol":"X","meaning":"Joint / Interlock"},
    {"decimal":76,"binary":"01001100","tongue":"Daisy","symbol":"Yx","meaning":"Fulcrum / Crux"},
    {"decimal":77,"binary":"01001101","tongue":"Daisy","symbol":"Go","meaning":"Plug / Blocker"},
    {"decimal":78,"binary":"01001110","tongue":"Daisy","symbol":"Foa","meaning":"Degree / Space"},
    {"decimal":79,"binary":"01001111","tongue":"Daisy","symbol":"Oy","meaning":"Depths / Layers"},
    {"decimal":80,"binary":"01010000","tongue":"Daisy","symbol":"W","meaning":"Freefall / Socket Space"},
    {"decimal":81,"binary":"01010001","tongue":"Daisy","symbol":"Th","meaning":"Cuff / Indentation"},
    {"decimal":82,"binary":"01010010","tongue":"Daisy","symbol":"Kael","meaning":"Cluster / Fruit / Flower"},
    {"decimal":83,"binary":"01010011","tongue":"Daisy","symbol":"Ro","meaning":"Ion-channel / Gate / Receptor"},
    {"decimal":84,"binary":"01010100","tongue":"Daisy","symbol":"Gl","meaning":"Membrane / Muscle"},
    {"decimal":85,"binary":"01010101","tongue":"Daisy","symbol":"To","meaning":"Scaffold / Framework"},
    {"decimal":86,"binary":"01010110","tongue":"Daisy","symbol":"Ma","meaning":"Web / Interchange"},
    {"decimal":87,"binary":"01010111","tongue":"Daisy","symbol":"Ne","meaning":"Network / System"},
    {"decimal":88,"binary":"01011000","tongue":"Daisy","symbol":"Ym","meaning":"Radial Space"},
    {"decimal":89,"binary":"01011001","tongue":"Daisy","symbol":"Nz","meaning":"Switch / Circuit Actuator"},
    {"decimal":90,"binary":"01011010","tongue":"Daisy","symbol":"Sho","meaning":"Valve / Fluid Actuator"},
    {"decimal":91,"binary":"01011011","tongue":"Daisy","symbol":"Hi","meaning":"Lever / Radial Actuator"},
    {"decimal":92,"binary":"01011100","tongue":"Daisy","symbol":"Mh","meaning":"Bond"},
    {"decimal":93,"binary":"01011101","tongue":"Daisy","symbol":"Zhi","meaning":"Eye / Vortex"},
    {"decimal":94,"binary":"01011110","tongue":"Daisy","symbol":"Vr","meaning":"Rotor / Tensor"},
    {"decimal":95,"binary":"01011111","tongue":"Daisy","symbol":"St","meaning":"Surface"},
    {"decimal":96,"binary":"01100000","tongue":"Daisy","symbol":"Fn","meaning":"Passage / Pathway"},
    {"decimal":97,"binary":"01100001","tongue":"Daisy","symbol":"N","meaning":"Seed / Sheet / Fiber"},
    {"decimal":98,"binary":"01100010","tongue":"AppleBlossom","symbol":"A","meaning":"Mind +"},
    {"decimal":99,"binary":"01100011","tongue":"AppleBlossom","symbol":"O","meaning":"Mind -"},
    {"decimal":100,"binary":"01100100","tongue":"AppleBlossom","symbol":"I","meaning":"Space +"},
    {"decimal":101,"binary":"01100101","tongue":"AppleBlossom","symbol":"E","meaning":"Space -"},
    {"decimal":102,"binary":"01100110","tongue":"AppleBlossom","symbol":"Y","meaning":"Time +"},
    {"decimal":103,"binary":"01100111","tongue":"AppleBlossom","symbol":"U","meaning":"Time -"},
    {"decimal":104,"binary":"01101000","tongue":"AppleBlossom","symbol":"Shak","meaning":"Fire"},
    {"decimal":105,"binary":"01101001","tongue":"AppleBlossom","symbol":"Puf","meaning":"Air"},
    {"decimal":106,"binary":"01101010","tongue":"AppleBlossom","symbol":"Mel","meaning":"Water"},
    {"decimal":107,"binary":"01101011","tongue":"AppleBlossom","symbol":"Zot","meaning":"Earth"},
    {"decimal":108,"binary":"01101100","tongue":"AppleBlossom","symbol":"Zhuk","meaning":"Plasma (Fire,Fire)"},
    {"decimal":109,"binary":"01101101","tongue":"AppleBlossom","symbol":"Kyzu","meaning":"Sulphur (Fire,Air)"},
    {"decimal":110,"binary":"01101110","tongue":"AppleBlossom","symbol":"Alky","meaning":"Alkahest / Alcohol (Fire,Water)"},
    {"decimal":111,"binary":"01101111","tongue":"AppleBlossom","symbol":"Kazho","meaning":"Magma / Lava (Fire,Earth)"},
    {"decimal":112,"binary":"01110000","tongue":"AppleBlossom","symbol":"Puky","meaning":"Smoke (Air,Fire)"},
    {"decimal":113,"binary":"01110001","tongue":"AppleBlossom","symbol":"Pyfu","meaning":"Gas (Air,Air)"},
    {"decimal":114,"binary":"01110010","tongue":"AppleBlossom","symbol":"Mipa","meaning":"Carbonation / Trapped Gas (Air,Water)"},
    {"decimal":115,"binary":"01110011","tongue":"AppleBlossom","symbol":"Zitef","meaning":"Mercury (Air,Earth)"},
    {"decimal":116,"binary":"01110100","tongue":"AppleBlossom","symbol":"Shem","meaning":"Steam (Water,Fire)"},
    {"decimal":117,"binary":"01110101","tongue":"AppleBlossom","symbol":"Lefu","meaning":"Vapor (Water,Air)"},
    {"decimal":118,"binary":"01110110","tongue":"AppleBlossom","symbol":"Milo","meaning":"Mixed fluids / Mixtures (Water,Water)"},
    {"decimal":119,"binary":"01110111","tongue":"AppleBlossom","symbol":"Myza","meaning":"Erosion (Water,Earth)"},
    {"decimal":120,"binary":"01111000","tongue":"AppleBlossom","symbol":"Zashu","meaning":"Radiation / Radioactive stones (Earth,Fire)"},
    {"decimal":121,"binary":"01111001","tongue":"AppleBlossom","symbol":"Fozt","meaning":"Dust (Earth,Air)"},
    {"decimal":122,"binary":"01111010","tongue":"AppleBlossom","symbol":"Mazi","meaning":"Sediment (Earth,Water)"},
    {"decimal":123,"binary":"01111011","tongue":"AppleBlossom","symbol":"Zaot","meaning":"Salt (Earth,Earth)"},
    {"decimal":128,"binary":"10000000","tongue":"Aster","symbol":"Ry","meaning":"Right-chiral red"},
    {"decimal":129,"binary":"10000001","tongue":"Aster","symbol":"Oth","meaning":"Right-chiral orange"},
    {"decimal":130,"binary":"10000010","tongue":"Aster","symbol":"Le","meaning":"Right-chiral yellow"},
    {"decimal":131,"binary":"10000011","tongue":"Aster","symbol":"Gi","meaning":"Right-chiral green"},
    {"decimal":132,"binary":"10000100","tongue":"Aster","symbol":"Fe","meaning":"Right-chiral blue"},
    {"decimal":133,"binary":"10000101","tongue":"Aster","symbol":"Ky","meaning":"Right-chiral indigo"},
    {"decimal":134,"binary":"10000110","tongue":"Aster","symbol":"Alz","meaning":"Right-chiral violet"},
    {"decimal":135,"binary":"10000111","tongue":"Aster","symbol":"Ra","meaning":"Left-chiral red"},
    {"decimal":136,"binary":"10001000","tongue":"Aster","symbol":"Tho","meaning":"Left-chiral orange"},
    {"decimal":137,"binary":"10001001","tongue":"Aster","symbol":"Lu","meaning":"Left-chiral yellow"},
    {"decimal":138,"binary":"10001010","tongue":"Aster","symbol":"Ge","meaning":"Left-chiral green"},
    {"decimal":139,"binary":"10001011","tongue":"Aster","symbol":"Fo","meaning":"Left-chiral blue"},
    {"decimal":140,"binary":"10001100","tongue":"Aster","symbol":"Kw","meaning":"Left-chiral indigo"},
    {"decimal":141,"binary":"10001101","tongue":"Aster","symbol":"Dr","meaning":"Left-chiral violet"},
    {"decimal":142,"binary":"10001110","tongue":"Aster","symbol":"Si","meaning":"Linear time"},
    {"decimal":143,"binary":"10001111","tongue":"Aster","symbol":"Su","meaning":"Loop time"},
    {"decimal":144,"binary":"10010000","tongue":"Aster","symbol":"Os","meaning":"Exponential time"},
    {"decimal":145,"binary":"10010001","tongue":"Aster","symbol":"Se","meaning":"Logarithmic time"},
    {"decimal":146,"binary":"10010010","tongue":"Aster","symbol":"Sy","meaning":"Fold time"},
    {"decimal":147,"binary":"10010011","tongue":"Aster","symbol":"As","meaning":"Frozen time"},
    {"decimal":184,"binary":"10111000","tongue":"Cannabis","symbol":"At","meaning":"Grounded awareness / consciousness of material presence"},
    {"decimal":185,"binary":"10111001","tongue":"Cannabis","symbol":"Ar","meaning":"Chromatic perception / awareness of energetic quality"},
    {"decimal":186,"binary":"10111010","tongue":"Cannabis","symbol":"Av","meaning":"Relational consciousness / awareness of connection and structure"},
    {"decimal":187,"binary":"10111011","tongue":"Cannabis","symbol":"Azr","meaning":"Structural intuition / felt sense of how things are assembled"},
    {"decimal":188,"binary":"10111100","tongue":"Cannabis","symbol":"Af","meaning":"Transformative awareness / consciousness of change in process"},
    {"decimal":189,"binary":"10111101","tongue":"Cannabis","symbol":"An","meaning":"Chiral discernment / awareness of handedness and temporal direction"},
    {"decimal":190,"binary":"10111110","tongue":"Cannabis","symbol":"Od","meaning":"Unspecified mental signal / noise without narrative"},
    {"decimal":191,"binary":"10111111","tongue":"Cannabis","symbol":"Ox","meaning":"Of the quality of unconscious transmission"},
    {"decimal":192,"binary":"11000000","tongue":"Cannabis","symbol":"Om","meaning":"In the manner of unconscious transmission"},
    {"decimal":204,"binary":"11001100","tongue":"Cannabis","symbol":"Yt","meaning":"Grounded duration / the temporal weight of material existence"},
    {"decimal":208,"binary":"11010000","tongue":"Cannabis","symbol":"Yf","meaning":"Transformative time / the duration of phase change"},
    {"decimal":209,"binary":"11010001","tongue":"Cannabis","symbol":"Yn","meaning":"Chiral time / the direction and handedness of temporal flow"},
]

BYTE_TABLE: dict[str, dict] = {r["symbol"]: r for r in BYTE_ROWS}
BYTE_BY_DECIMAL: dict[int, dict] = {r["decimal"]: r for r in BYTE_ROWS}

GILGAMESH_TABLETS = [
    {"id": "tablet_i", "title": "Tablet I — He who saw the deep", "division": "Sulphur", "paracelsian": "The king at the edge of his own excess. Gilgamesh as two-thirds divine, one-third mortal — the wound of the compound state.", "original_summary": "Introduction of Gilgamesh, king of Uruk, his oppression of his people, the creation of Enkidu by the gods as his counterpart."},
    {"id": "tablet_ii", "title": "Tablet II — The coming of the wild one", "division": "Sulphur", "paracelsian": "Enkidu as the unformed substrate self — pure Be (Common/Outer/Wild) before contact with the structured world.", "original_summary": "Enkidu lives with animals, is civilized by Shamhat, hears of Gilgamesh, travels to Uruk."},
    {"id": "tablet_iii", "title": "Tablet III — The Cedar Forest", "division": "Sulphur", "paracelsian": "The first quest as Sulphur's drive — pattern toward (Shy) meeting the unknown. The friendship as Mercury beginning to form.", "original_summary": "Gilgamesh and Enkidu plan the journey to the Cedar Forest to slay Humbaba."},
    {"id": "tablet_iv", "title": "Tablet IV — Dreams in the wilderness", "division": "Mercury", "paracelsian": "The dream sequence as Cannabis layer activating — chiral priors encountered before the battle. The manifold showing its topology to the sleeper.", "original_summary": "The journey to the Cedar Forest, five dreams of Gilgamesh interpreted by Enkidu."},
    {"id": "tablet_v", "title": "Tablet V — The killing of Humbaba", "division": "Mercury", "paracelsian": "Humbaba as the guardian of the void-ian substrate — the shaped emptiness that precedes the forest's densification. His death as the first transgression against the prior.", "original_summary": "Battle with and slaying of Humbaba. The gods are angered."},
    {"id": "tablet_vi", "title": "Tablet VI — The Bull of Heaven", "division": "Mercury", "paracelsian": "Ishtar's offer as AE+Ly (love) from the position that cannot be received — the Möbius surface showing Gilgamesh his own upper limit.", "original_summary": "Ishtar proposes to Gilgamesh, he rejects her, she sends the Bull of Heaven, they slay it."},
    {"id": "tablet_vii", "title": "Tablet VII — Enkidu's death", "division": "Mercury", "paracelsian": "The Möbius twist — the wild substrate self encountering Ku (Fire Terminator / death / end). Soul losing its Mercury pole.", "original_summary": "The gods decree Enkidu must die. His illness, dreams of the underworld, death."},
    {"id": "tablet_viii", "title": "Tablet VIII — The lament", "division": "Mercury", "paracelsian": "Gilgamesh's grief as Rugafunly — pain compounded with the hunger of absence. The first encounter with what exceeds the feelable spectrum.", "original_summary": "Gilgamesh's lament for Enkidu. The funeral rites."},
    {"id": "tablet_ix", "title": "Tablet IX — The road to Mashu", "division": "Salt", "paracelsian": "The quest for immortality as Salt's work — the self attempting to fix what the void-ian substrate makes necessarily unfixed. Traveling through frozen time (As).", "original_summary": "Gilgamesh wanders in grief, seeks Utnapishtim. Travels through the mountains of Mashu."},
    {"id": "tablet_x", "title": "Tablet X — The waters of death", "division": "Salt", "paracelsian": "Urshanabi as the ferryman of the chiral boundary — the guide who knows which way the manifold is turning at its most dangerous traverse.", "original_summary": "Gilgamesh meets Siduri, then Urshanabi the ferryman, crosses the waters of death."},
    {"id": "tablet_xi", "title": "Tablet XI — The flood and the flower", "division": "Salt", "paracelsian": "Utnapishtim as Ka+Ly (wisdom/temperance) at the upper threshold. The flood as void-ian reset. The flower of immortality lost to the serpent — the Möbius surface completing its turn.", "original_summary": "Utnapishtim tells the flood story. The plant of immortality. Its theft by the serpent. Gilgamesh returns to Uruk."},
    {"id": "tablet_xii", "title": "Tablet XII — The descent (appendix)", "division": "Salt", "paracelsian": "The underworld as the void-ian substrate made traversable — the dead as positions on the Möbius surface that have completed their local traversal. Soul speaking to Spirit.", "original_summary": "Enkidu descends to the underworld to retrieve objects. Becomes trapped. His ghost speaks to Gilgamesh."},
]

SYSTEM_PROMPT = """You are the Shygazun language engine embedded in the Virtual Atelier of Quantum Quackery Divine Arts LLC.

SHYGAZUN CORE:
- Grammar: semantic-first, placement-last. The manifold is Möbius — one continuous surface.
- Six ontic vowels: A/O (Mind+/−), I/E (Space+/−), Y/U (Time+/−)
- Tongues: Lotus (elemental), Rose (spectral/numeric), Sakura (spatial/relational), Daisy (structural/mechanical), AppleBlossom (alchemical compound), Aster (chiral/temporal priors — tautologically unknowable yet epistemologically necessary), Grapevine (network/ceremonial), Cannabis (phenomenological cross-products through Mind/Space/Time)
- Grammar rules: Nouns = akinenwun (any symbol combination). Active verb = wu + noun. Passive = noun + wu + ga. Genitive = noun + ung (contracted to n). Accusative = Ha + noun + wu. Ablative = Ga + noun + wu.
- Pronouns: Awu(I) Owu(We) Ywu(You) Uwu(Y'all) Iwu(they sg) Ewu(they pl) Gaaowu(she) Haaowu(he)
- Void-ian substrate is prior to all tongues — shaped emptiness determining what can densify
- Soul = local traversal position on the manifold. Spirit = the surface moving.
- Information = function of entanglement (Ki) at local manifold through nonlocal void-ian enmeshment via identity resonance
- Emotion compounds: Rose vector + Ly = spectral emotion (Ruly=pain, Otly=anger, Elly=fear, Kily=joy, Fuly=longing/mania, Kaly=wisdom, Aely=love)
- Isomorphic with photonic computation: teaching one teaches the other implicitly
- The language is foundationally alchemical and Paracelsian

GILGAMESH CONTEXT:
Gilgamesh maps onto the Paracelsian QQDA divisions: Sulphur (Tablets I-III, the king's excess and the quest's initiation), Mercury (Tablets IV-VIII, the friendship, its loss, the grief), Salt (Tablets IX-XII, the void traversal, the flood, the return). Enkidu is the wild substrate self (Be — Common/Outer/Wild). Humbaba is the guardian of the void-ian substrate. Utnapishtim is Ka+Ly — wisdom at the threshold. The flood is void-ian reset. The serpent stealing the immortality flower is the Möbius surface completing its turn.

Respond with precision, rigor, and fidelity to the byte table."""


router = APIRouter()
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PromptRequest(BaseModel):
    tongue: str = "any"
    register: str = "any"
    mode: str = "prompt"  # prompt | ritual | grimoire | pedagogy | gilgamesh
    depth: str = "mid"    # surface | mid | deep | ritual
    tablet_id: Optional[str] = None  # for gilgamesh mode

class ParseRequest(BaseModel):
    text: str

class InterpretRequest(BaseModel):
    compound: str
    parts: Optional[List[str]] = None

class LookupRequest(BaseModel):
    query: str
    field: str = "symbol"  # symbol | tongue | decimal | meaning

class TabletSaveRequest(BaseModel):
    tablet_id: str
    shygazun_text: str
    english_parallel: Optional[str] = None
    notes: Optional[str] = None

class TranslateRequest(BaseModel):
    text: str
    direction: str = "to_english"  # to_english | to_shygazun

# In-memory tablet store (replace with DB persistence via SQLAlchemy in production)
_tablet_compositions: dict[str, list[dict]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/tablets")
def get_tablets():
    """Return the full Gilgamesh tablet structure with any saved compositions."""
    result = []
    for t in GILGAMESH_TABLETS:
        compositions = _tablet_compositions.get(t["id"], [])
        result.append({**t, "compositions": compositions, "composition_count": len(compositions)})
    return result


@router.get("/tablets/{tablet_id}")
def get_tablet(tablet_id: str):
    """Return a single tablet with its compositions."""
    tablet = next((t for t in GILGAMESH_TABLETS if t["id"] == tablet_id), None)
    if not tablet:
        raise HTTPException(status_code=404, detail=f"Tablet {tablet_id} not found")
    compositions = _tablet_compositions.get(tablet_id, [])
    return {**tablet, "compositions": compositions}


@router.post("/tablets/{tablet_id}")
def save_tablet_composition(tablet_id: str, req: TabletSaveRequest):
    """Save a Shygazun composition to a specific tablet."""
    tablet = next((t for t in GILGAMESH_TABLETS if t["id"] == tablet_id), None)
    if not tablet:
        raise HTTPException(status_code=404, detail=f"Tablet {tablet_id} not found")
    entry = {
        "id": f"{tablet_id}_{len(_tablet_compositions.get(tablet_id, []))}",
        "shygazun_text": req.shygazun_text,
        "english_parallel": req.english_parallel,
        "notes": req.notes,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if tablet_id not in _tablet_compositions:
        _tablet_compositions[tablet_id] = []
    _tablet_compositions[tablet_id].append(entry)
    return {"status": "saved", "entry": entry}


@router.get("/lookup")
def lookup_symbols(query: str = "", field: str = "tongue"):
    """Look up byte table entries by symbol, tongue, decimal, or meaning fragment."""
    results = []
    query_lower = query.lower()
    for row in BYTE_ROWS:
        val = str(row.get(field, "")).lower()
        if field == "meaning":
            if query_lower in val:
                results.append(row)
        else:
            if val == query_lower:
                results.append(row)
    if not results and field == "symbol":
        for row in BYTE_ROWS:
            if query_lower in row["symbol"].lower():
                results.append(row)
    return {"query": query, "field": field, "results": results, "count": len(results)}


@router.post("/parse")
def parse_composition(req: ParseRequest):
    """Parse a Shygazun text, identifying known symbols and grammatical structures."""
    client = get_client()
    byte_summary = "\n".join(
        f"{r['symbol']} (dec {r['decimal']}, {r['tongue']}): {r['meaning']}"
        for r in BYTE_ROWS
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Parse this Shygazun text symbol by symbol. Use the byte table below as gospel.
For each segment identify: the akinen/symbol, its tongue, its decimal, its meaning, and its grammatical role.
Then describe the overall grammatical structure and the path through the Möbius manifold.

TEXT: {req.text}

BYTE TABLE:
{byte_summary}

Return as JSON with keys: segments (array of {{symbol, tongue, decimal, meaning, grammatical_role}}), structure (string), manifold_path (string), tongues_active (array of strings)."""
        }]
    )
    raw = msg.content[0].text.strip()
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return {"text": req.text, "parse": json.loads(clean)}
    except Exception:
        return {"text": req.text, "parse": {"raw": raw}}


@router.post("/interpret")
def interpret_emotion(req: InterpretRequest):
    """Interpret a Shygazun emotion compound phenomenologically."""
    client = get_client()
    parts_desc = ", ".join(req.parts) if req.parts else req.compound
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Interpret this Shygazun emotion compound phenomenologically.
Compound: {req.compound}
Parts: {parts_desc}

The spectral emotion scale: Ruly=pain (lowest red), Otly=anger (orange), Elly=fear (yellow), Kily=joy (green, center), Fuly=longing/mania (blue), Kaly=wisdom/temperance (indigo), Aely=love (highest violet). The manifold is Möbius — pain and love are the same point approached from opposite traversal directions. Ha=Absolute Positive, Ga=Absolute Negative, Na=Neutral/Integration.

Return a precise phenomenological description of the compound state in 2-4 sentences. No preamble."""
        }]
    )
    return {"compound": req.compound, "interpretation": msg.content[0].text.strip()}


@router.post("/prompt")
def generate_prompt(req: PromptRequest):
    """Generate a literary, ritual, grimoire, or Gilgamesh composition prompt."""
    client = get_client()

    depth_map = {
        "surface": "surface depth, 1-4 part compounds, single tongue, single image",
        "mid": "mid depth, 5-10 part compounds, two tongues in dialogue",
        "deep": "deep, 11-19 part compounds, full manifold traversal with chiral acknowledgment",
        "ritual": "approaching ritual threshold of 20 parts — the Möbius twist where speaker and language become continuous surface"
    }
    mode_map = {
        "prompt": "literary composition",
        "ritual": "ritual script for enactment — the body as instrument, physical exhaustion as meaning",
        "grimoire": "grimoire entry — simultaneously literature, ritual score, and technical specification",
        "pedagogy": "pedagogical synthesis exploring the isomorphism between Shygazun and photonic computation",
        "gilgamesh": "a passage of the Gilgamesh retelling in Shygazun"
    }

    tablet_context = ""
    if req.mode == "gilgamesh" and req.tablet_id:
        tablet = next((t for t in GILGAMESH_TABLETS if t["id"] == req.tablet_id), None)
        if tablet:
            tablet_context = f"""
CURRENT TABLET: {tablet['title']}
Division: {tablet['division']} (Paracelsian)
Paracelsian reading: {tablet['paracelsian']}
Original content: {tablet['original_summary']}
"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Generate a {mode_map.get(req.mode, 'literary composition')} prompt for Shygazun.
Tongue focus: {req.tongue if req.tongue != 'any' else 'open across all tongues'}
Register: {req.register if req.register != 'any' else 'open'}
Depth: {depth_map.get(req.depth, depth_map['mid'])}
{tablet_context}
The prompt should invite genuine native composition — an encounter worth writing toward, not an assignment.
Return ONLY the prompt text. No preamble, no metadata."""
        }]
    )
    return {
        "prompt": msg.content[0].text.strip(),
        "tongue": req.tongue,
        "register": req.register,
        "mode": req.mode,
        "depth": req.depth,
        "tablet_id": req.tablet_id,
    }


@router.post("/translate")
def translate(req: TranslateRequest):
    """Translate between Shygazun and English, or produce parallel text."""
    client = get_client()
    direction_desc = (
        "Parse and translate this Shygazun text into English, preserving the phenomenological precision of each compound. Provide: (1) a literal symbol-by-symbol gloss, (2) a poetic English rendering that honors the original's depth."
        if req.direction == "to_english"
        else "Translate this English text into Shygazun, using the byte table grammar. Provide: (1) the Shygazun composition, (2) a symbol-by-symbol gloss explaining each choice."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"{direction_desc}\n\nTEXT: {req.text}"
        }]
    )
    return {
        "original": req.text,
        "direction": req.direction,
        "result": msg.content[0].text.strip()
    }


@router.get("/byte_table")
def get_byte_table(tongue: Optional[str] = None):
    """Return the full byte table, optionally filtered by tongue."""
    if tongue:
        rows = [r for r in BYTE_ROWS if r["tongue"].lower() == tongue.lower()]
    else:
        rows = BYTE_ROWS
    tongues = sorted(set(r["tongue"] for r in BYTE_ROWS))
    return {"rows": rows, "count": len(rows), "tongues": tongues}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1000
    system: Optional[str] = None
    messages: List[ChatMessage]


@router.post("/chat")
def chat(req: ChatRequest):
    """Generic Anthropic messages proxy — injects API key server-side.
    Accepts the same shape as the Anthropic messages API so companion pages
    can call /api/shygazun/chat instead of api.anthropic.com directly.
    """
    client = get_client()
    kwargs: dict = {
        "model": req.model,
        "max_tokens": req.max_tokens,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages],
    }
    if req.system:
        kwargs["system"] = req.system
    msg = client.messages.create(**kwargs)
    return {
        "content": [{"type": "text", "text": block.text} for block in msg.content if hasattr(block, "text")],
        "model": msg.model,
        "stop_reason": msg.stop_reason,
    }

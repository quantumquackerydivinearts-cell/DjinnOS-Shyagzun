"""
shygazun.sanctum.kos_labyrinth — Ko's Labyrinth Registry
=========================================================

Ko's Labyrinth is not one game. It is a 31-game anthology — each game
an Nth-dimensional manifold of the same philosophical space.
The anthology as a whole is a philosophical dissertation in playable form.

This module is the canonical registry for:
    - Entity ID schema (§11.1)
    - Object registry (§11.2)
    - Object traits (§11.3)
    - Character registry (§11.4)
    - Item registry (§11.5)
    - Quest registry (§11.6)
    - Book order (§6.2)
    - GameNode structure (§6.7)

All IDs follow the canonical format: NNNN_TYPE
where TYPE is one of the faction/category suffixes defined in ID_SCHEMA.

The exoteric sequence is the release order.
The esoteric sequence is different for every player — determined by their
flagged states and the order they chose to play.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
# §11.1 — Entity ID Schema
# ---------------------------------------------------------------------------

ID_SCHEMA: Dict[str, str] = {
    "_KLOB": "Ko's Labyrinth Object",
    "_KLIT": "Ko's Labyrinth Item",
    "_KLST": "Ko's Labyrinth Story (Quest)",
    "_TOWN": "Townfolk",
    "_WTCH": "Witch",
    "_PRST": "Priest",
    "_ASSN": "Assassin",
    "_ROYL": "Royal",
    "_GNOM": "Gnome",
    "_NYMP": "Nymph",
    "_UNDI": "Undine",
    "_SALA": "Salamander",
    "_DRYA": "Dryad",
    "_DJNN": "Djinn",
    "_VDWR": "Void Wraith",
    "_DMON": "Demon",
    "_DEMI": "Demigod",
    "_SOLD": "Soldier",
    "_GODS": "God",
    "_PRIM": "Primordial",
    "_ANMU": "Anima Mundi",
}


def entity_category(entity_id: str) -> Optional[str]:
    """Return the category name for an entity ID, or None if unrecognized."""
    for suffix, category in ID_SCHEMA.items():
        if entity_id.endswith(suffix):
            return category
    return None


# ---------------------------------------------------------------------------
# §11.2 — Object Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjectEntry:
    name: str
    entity_id: Optional[str]  # None = not yet assigned


# Objects whose IDs have been assigned:
_OBJECT_TABLE: Tuple[Tuple[str, Optional[str]], ...] = (
    ("Mortar",          "8000_KLOB"),
    ("Pestle",          "2000_KLOB"),
    ("Rag",             None),
    ("Stand",           None),
    ("Retort",          None),
    ("Volume Flask",    None),
    ("Reagent Bottle",  None),
    ("Sand",            None),
    ("Refined Sand",    None),
    ("Furnace",         None),
    ("Wooden Spoon",    None),
    ("Copper Spoon",    None),
    ("Iron Spoon",      None),
    ("Steel Spoon",     None),
    ("Granite Spoon",   None),
    ("Bellows",         None),
    ("Crucible",        None),
    ("Bottle",          None),
    ("Jar",             None),
    ("Diatom Earth",    None),
    ("Glycerine",       None),
    ("Petroleum Jelly", None),
    ("Saltpeter",       None),
    ("Sulphur",         None),
    ("Charcoal",        None),
    ("Tin",             None),
    ("Iron",            None),
    ("Gold",            None),
    ("Copper",          None),
    ("Mercury",         None),
    ("Silver",          None),
    ("Lead",            None),
    ("Nickel",          None),
    ("Cyanide",         None),
    ("Ashes",           None),
    ("Caustic Lye",     None),
    ("Potassium",       None),
    ("Phosphorus",      None),
    ("Arsenic",         None),
    ("Water",           None),
    ("Wood",            None),
    ("Flint",           None),
    ("Shark Tooth",     None),
    ("Granite",         None),
    ("Obsidian",        None),
    ("Chalk",           None),
    ("Gypsum",          None),
    ("Quartz",          None),
    ("Pumice",          None),
    ("Amethyst",        None),
    ("Ruby",            None),
    ("Sapphire",        None),
    ("Emerald",         None),
    ("Diamond",         None),
    ("Jade",            None),
    ("Crucible Tongs",  None),
    ("Ring Mold",       None),
    ("Ingot Mold",      None),
    ("Anvil",           None),
    ("Hammer",          None),
    ("Lathe Chuck",     None),
    ("Lathe",           None),
    ("Chisel",          None),
    ("Ring Blank",      None),
    ("Moldavite",       None),
    ("Desert Glass",    None),
    ("Pearl",           None),
    ("Black Pearl",     None),
    ("Pulp",            None),
    ("Paper",           None),
    ("Ink",             None),
    ("Pen",             None),
)

OBJECT_REGISTRY: Tuple[ObjectEntry, ...] = tuple(
    ObjectEntry(name=name, entity_id=eid)
    for name, eid in _OBJECT_TABLE
)

OBJECT_BY_NAME: Dict[str, ObjectEntry] = {obj.name: obj for obj in OBJECT_REGISTRY}
OBJECT_BY_ID: Dict[str, ObjectEntry] = {
    obj.entity_id: obj for obj in OBJECT_REGISTRY if obj.entity_id
}


# ---------------------------------------------------------------------------
# §11.3 — Object Traits
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjectTrait:
    trait_id: int
    name: str


# Note: Alive/Dead (4/5) sit at the Object/Entity boundary corresponding
# to Layers 5/6 of the Twelvefold Coil. This is not accidental.
OBJECT_TRAITS: Tuple[ObjectTrait, ...] = (
    ObjectTrait(0,  "Usable"),
    ObjectTrait(1,  "Unusable"),
    ObjectTrait(2,  "Full"),
    ObjectTrait(3,  "Empty"),
    ObjectTrait(4,  "Alive"),       # Layer 5/6 boundary — Object/Entity threshold
    ObjectTrait(5,  "Dead"),        # Layer 5/6 boundary — Object/Entity threshold
    ObjectTrait(6,  "Movable"),
    ObjectTrait(7,  "Immobilized"),
    ObjectTrait(8,  "Poisonous"),
    ObjectTrait(9,  "Flammable"),
    ObjectTrait(10, "Inert"),
    ObjectTrait(11, "Explosive"),
    ObjectTrait(12, "Token"),
    ObjectTrait(13, "Collector"),
    ObjectTrait(14, "Powdered"),
    ObjectTrait(15, "Molten"),
)

TRAIT_BY_ID: Dict[int, ObjectTrait] = {t.trait_id: t for t in OBJECT_TRAITS}
TRAIT_BY_NAME: Dict[str, ObjectTrait] = {t.name: t for t in OBJECT_TRAITS}


# ---------------------------------------------------------------------------
# §11.4 — Character Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CharacterEntry:
    name: str
    entity_id: str
    notes: str
    faction: str  # derived from entity_id suffix


def _faction_from_id(entity_id: str) -> str:
    for suffix, category in ID_SCHEMA.items():
        if entity_id.endswith(suffix):
            return category
    # Special case: protagonist has non-standard ID
    if entity_id == "0000_0451":
        return "Protagonist"
    return "Unknown"


_CHARACTER_TABLE: Tuple[Tuple[str, str, str], ...] = (
    # (name, entity_id, notes)
    ("Alexandria Hypatia",  "0000_0451",  "Protagonist/Player character"),
    ("Joannah",             "0001_TOWN",  ""),
    ("Wells",               "0002_TOWN",  "Aqueduct Foreman, engineer, father of 6 (38)"),
    ("Lavelle",             "0003_TOWN",  "Laundry worker, explosive hobbyist, bookworm, mother of 2 (23)"),
    ("Sidhal",              "0004_TOWN",  "Farmer, Forester, Temple Custodian, Father of 2 (26)"),
    ("Kore",                "0005_WTCH",  "Life witch, Transfemme, Ko Devotee"),
    ("Alfir",               "0006_WTCH",  "Cosmic Witch, Former priest, Daemonologist (50)"),
    ("Forest",              "0007_WTCH",  "Dryad obsessed Nature Wizard, Gay (27)"),
    ("Saffron",             "0008_PRST",  "Purple robe, red wings, Menace to Nature, Nexiott's Priest (72)"),
    ("Lucion",              "0009_PRST",  "Ceramics, cryptography, medicine, chemistry, Librarian (35), Jabiru Priest"),
    ("Rachelle",            "0010_PRST",  "Alfir's Replacement, Advisor to Chancellor Kelly, Shakzefan Priestess (35)"),
    ("Hue",                 "0011_ASSN",  "Student of Sophia, Haunted by Po'elfan, Kore's brother"),
    ("Cyrus",               "0012_ASSN",  "Student of Lectura, disguise expert, blue hair (20/29)"),
    ("Asmoth",              "0013_ASSN",  "Child of the Fae, orphaned by Kielum's war"),
    ("Chancellor Kelly",    "0014_ROYL",  "Oldest in Castle AZoth, talks to angels (38)"),
    ("King Bombastus",      "0015_ROYL",  "Father from FMAb, but lost"),
    ("Queen Hildegarde",    "0016_ROYL",  "Scholar Queen, stressed mother"),
    ("Lord Nexiott",        "0017_ROYL",  "Corona Boss, Propagandist (52)"),
    ("Duke Eomann",         "0018_ROYL",  ""),
    ("Princess Luminyx",    "0019_ROYL",  "Protagonist of Book 1 — spelling: Luminyx"),
    ("Clint",               "1001_GNOM",  "Miner, Geologist, Jeweler, Geomancer, Follower of Lapidus"),
    ("Gnolan",              "1002_GNOM",  "Architect, Friend of Eomann, Follower of Mercurie"),
    ("Winnona",             "1003_GNOM",  "Metallurgist and Machinist, Follower of Sulphera"),
    ("Amelia",              "1004_NYMP",  "Fae Queen, beefs w/ Tymona, Muse of Echo, Chaos Mage"),
    ("Echo",                "1005_NYMP",  "Artisan, Alchemist, Ko's Disciple, Poet, Chaos magic user, Zoha Devotee"),
    ("Karlia",              "1006_NYMP",  "Fae, Guardian, Deep blue wings, Chaos magic user"),
    ("Sophia",              "1007_UNDI",  "Red & black w/ silver scaling, Soul of the Depths"),
    ("Lectura",             "1008_UNDI",  "Green & yellow scales, Venom of Tides, Mona devotee"),
    ("Faygoru",             "1009_UNDI",  "Gold & turquoise scales, Time traveler, Ohadame devotee"),
    ("Chazak",              "1010_SALA",  "Greater Siren, Zen af, Transcendental Meditator, Moshize Devotee"),
    ("Axiozul",             "1011_SALA",  "Axolotl (blue), Timeless, Immortal, Child of Lakota"),
    ("Savvi",               "1012_SALA",  "Fire Salamander, Child of Vios and Drovitth, Cosmic Arms Dealer, Bane of Misfortune"),
    ("Eukala",              "1013_DRYA",  "Constantly hunting, honors death, 8'ky+, ageless, LN"),
    ("Tymona",              "1014_DRYA",  "Hates humans, full of sadism, 6ft+, 40s, godless CN"),
    ("Vajil",               "1015_DRYA",  ""),
    ("Giann",               "1016_DJNN",  ""),
    ("Keshi",               "1017_DJNN",  ""),
    ("Drovitth",            "1018_DJNN",  ""),
    ("Haldoro",             "2001_VDWR",  "Void Wraith"),
    ("Vios",                "2002_VDWR",  "Void Wraith"),
    ("Negaya",              "2003_VDWR",  "Void Wraith — site of power and pattern"),
    ("Otheiru",             "2004_DMON",  "Demon (appears as 'Otheira' in plot notes — Otheiru canonical)"),
    ("Kielum",              "2005_DMON",  "Demon of finance, cults, war, abuse"),
    ("Ruzoa",               "2006_DMON",  "Demon of Depression and Despair"),
    ("Po'Elfan",            "2007_DMON",  "Demon of Anxiety and mindless panic"),
    ("Kaganue",             "2008_DMON",  "Demon"),
    ("Zukoru",              "2009_DMON",  '"Death Most Obscene," Demon of Betrayal — originating demon'),
    ("Shapier",             "2010_DEMI",  "Demigod"),
    ("Lanzu",               "2011_DEMI",  "Demigod"),
    ("Tagame",              "2012_DEMI",  "Demigod"),
    ("Captain Lanvaki",     "2013_SOLD",  ""),
    ("Sgt. Akande",         "2014_SOLD",  ""),
    ("Pvt. Kilesha",        "2015_SOLD",  ""),
    ("Moshize",             "2016_GODS",  ""),
    ("Shakzefan",           "2017_GODS",  "Shygazun: Fire of Growth"),
    ("Lakota",              "2018_GODS",  ""),
    ("Jabiru",              "2019_GODS",  ""),
    ("Ohadame",             "2020_GODS",  ""),
    ("Ko",                  "2021_GODS",  "Encountereable deity — Ko appears directly"),
    ("Koga",                "2022_GODS",  ""),
    ("Mona",                "2023_GODS",  ""),
    ("Zoha",                "2024_GODS",  "Goddess (not a Primordial)"),
    ("Ga",                  "2025_PRIM",  "Primordial — encountereable"),
    ("Na",                  "2026_PRIM",  "Primordial — encountereable"),
    ("Ha",                  "2027_PRIM",  "Primordial — encountereable"),
    ("Ung",                 "2028_PRIM",  "Primordial — encountereable"),
    ("Wu",                  "2029_PRIM",  "Primordial — encountereable"),
    ("Kael",                "2030_PRIM",  "Primordial — encountereable"),
    ("Lapidus",             "3001_ANMU",  "Anima Mundi — encountereable"),
    ("Mercurie",            "3002_ANMU",  "Anima Mundi — encountereable"),
    ("Sulphera",            "3003_ANMU",  "Anima Mundi — encountereable"),
    ("Pythia Solunikae",    "3004_ANMU",  "Anima Mundi — Priestess of The Aeon of Eclipses"),
)

CHARACTER_REGISTRY: Tuple[CharacterEntry, ...] = tuple(
    CharacterEntry(
        name=name,
        entity_id=eid,
        notes=notes,
        faction=_faction_from_id(eid),
    )
    for name, eid, notes in _CHARACTER_TABLE
)

CHARACTER_BY_ID: Dict[str, CharacterEntry] = {c.entity_id: c for c in CHARACTER_REGISTRY}
CHARACTER_BY_NAME: Dict[str, CharacterEntry] = {c.name: c for c in CHARACTER_REGISTRY}

# The Primordials and Anima Mundi are encounterable entities,
# not just cosmological background. They have entity IDs and can be met in play.
ENCOUNTERABLE_ENTITIES: Tuple[CharacterEntry, ...] = tuple(
    c for c in CHARACTER_REGISTRY
    if c.faction in ("Primordial", "Anima Mundi")
    or c.notes.startswith("Encountereable") or "encountereable" in c.notes.lower()
)


# ---------------------------------------------------------------------------
# §11.5 — Item Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ItemEntry:
    name: str
    entity_id: Optional[str]
    craftable: bool  # True if marked with () in canonical source


_ITEM_TABLE: Tuple[Tuple[str, Optional[str], bool], ...] = (
    ("Health potion",   "0035_KLIT", False),
    ("Cherry",          None,        False),
    ("Apple",           None,        False),
    ("Pomegranate",     None,        False),
    ("Barley",          None,        False),
    ("Pine Needle",     None,        False),
    ("Acorn",           None,        False),
    ("Lotus Flower",    None,        False),
    ("Lotus Seed",      None,        False),
    ("Pine Nut",        None,        False),
    ("Apple Seed",      None,        False),
    ("Cherry Pit",      None,        False),
    ("Necklace",        None,        False),
    ("Ring",            None,        True),
    ("Ingot",           None,        True),
    ("Coin",            None,        True),
    ("Dagger",          None,        True),
    ("Sword",           None,        True),
    ("Shield",          None,        False),
    ("Bow",             None,        False),
    ("Arrow",           None,        True),
    ("Staff",           None,        True),
    ("Desire Crystal",  None,        False),
    ("Angelic Spear",   None,        False),
    ("Angelic Gun",     None,        False),
    ("Demonic Irons",   None,        False),
)

ITEM_REGISTRY: Tuple[ItemEntry, ...] = tuple(
    ItemEntry(name=name, entity_id=eid, craftable=craftable)
    for name, eid, craftable in _ITEM_TABLE
)

ITEM_BY_NAME: Dict[str, ItemEntry] = {item.name: item for item in ITEM_REGISTRY}
CRAFTABLE_ITEMS: Tuple[ItemEntry, ...] = tuple(i for i in ITEM_REGISTRY if i.craftable)


# ---------------------------------------------------------------------------
# §11.6 — Quest Registry (Narrative Order)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuestEntry:
    title: str
    entity_id: str
    notes: str
    # narrative_position: the quest's position in the story, which may differ
    # from its ID number. "Dream of Glass" (0007) sits narratively between
    # 0008 and 0009 — a dream quest does not sit where its number says it should.
    narrative_position: int  # 1-based order in the narrative sequence


_QUEST_TABLE: Tuple[Tuple[str, str, str], ...] = (
    # (title, entity_id, notes)  — listed in narrative order
    ("Fate Knocks",               "0001_KLST", ""),
    ("Destiny Calls",             "0002_KLST", ""),
    ("Yellow Brick Road",         "0003_KLST", ""),
    ("The Golden Path",           "0004_KLST", ""),
    ("Darker Secrets",            "0005_KLST", ""),
    ("Twaddlespeak",              "0006_KLST", ""),
    ("Bunsen For Hire",           "0008_KLST", ""),
    # Dream of Glass: ID is 0007 but narrative position is between 0008 and 0009.
    # A dream quest does not sit where its number says it should.
    ("Dream of Glass",            "0007_KLST", "ID displaced from narrative; dream quests exist outside sequential order"),
    ("Demons and Diamonds",       "0009_KLST", ""),
    ("Perfect Circles",           "0010_KLST", ""),
    ("The Siren Sounds",          "0011_KLST", ""),
    ("The Mines",                 "0012_KLST", ""),
    ("War Never Changes",         "0013_KLST", ""),
    ("Bombast",                   "0014_KLST", ""),
    ("Underworld",                "0015_KLST", ""),
    ("Transcendental",            "0016_KLST", ""),
    ("Loss, I Fear",              "0017_KLST", ""),
    ("Growing Pains",             "0018_KLST", ""),
    ("Wish Upon a Horse",         "0019_KLST", ""),
    ("Wish Upon a Falling Star",  "0020_KLST", ""),
    ("Starlight Shows",           "0021_KLST", ""),
    ("Good Soldiers",             "0022_KLST", ""),
    ("Mercenary Type",            "0023_KLST", ""),
    ("Death Hallows",             "0024_KLST", ""),
    ("Assassination",             "0025_KLST", ""),
    ("Good Grief",                "0026_KLST", ""),
    ("Echoes of the Past",        "0027_KLST", ""),
    ("A Haunting Notion",         "0028_KLST", ""),
    ("Doom and Gloom",            "0029_KLST", ""),
    ("Plasma Freeze",             "0030_KLST", ""),
    ("Master Koga",               "0031_KLST", ""),
    ("Mona Lisa",                 "0032_KLST", ""),
    ("Zoha are",                  "0033_KLST", ""),
    ("Children? By Atom!",        "0034_KLST", ""),
    ("Choices in Hell",           "0035_KLST", ""),
    ("Consequence",               "0036_KLST", ""),
    ("Witching Hour",             "0037_KLST", ""),
    ("Wild Things",               "0038_KLST", ""),
    ("Storybook",                 "0039_KLST", ""),
    ("Priceless",                 "0040_KLST", ""),
    ("Poisons and Lectures",      "0041_KLST", ""),
    ("Meaning Less",              "0042_KLST", ""),
    ("Less is More",              "0043_KLST", ""),
    ("Voracity",                  "0044_KLST", ""),
    ("Good old .45",              "0045_KLST", ""),
    ("Most Obscenities",          "0046_KLST", ""),
    ("Shaped Charge",             "0047_KLST", ""),
    ("De Lucion",                 "0048_KLST", ""),
    ("Had Me in the First Half",  "0049_KLST", ""),
    ("Prophet of Ko",             "0050_KLST", "Approaches endgame"),
    ("Eclipse!",                  "0051_KLST", "Approaches endgame"),
    ("The Abyss",                 "0052_KLST", "Post-eclipse"),
    ("Chosen Dues",               "0053_KLST", ""),
    ("Stolen Valor",              "0054_KLST", ""),
    ("Ring-a-Ding-Ding",          "0055_KLST", ""),
    ("Priestly Affair",           "0056_KLST", ""),
    ("Fairly, a Priestess",       "0057_KLST", ""),
    ("Rouse The Depths",          "0058_KLST", ""),
    ("The Woods",                 "0059_KLST", ""),
    ("In Service To Starlight",   "0060_KLST", ""),
    ("Ko's Great Tale",           "0061_KLST", "Final quest"),
)

QUEST_REGISTRY: Tuple[QuestEntry, ...] = tuple(
    QuestEntry(
        title=title,
        entity_id=eid,
        notes=notes,
        narrative_position=pos + 1,
    )
    for pos, (title, eid, notes) in enumerate(_QUEST_TABLE)
)

QUEST_BY_ID: Dict[str, QuestEntry] = {q.entity_id: q for q in QUEST_REGISTRY}
QUEST_BY_TITLE: Dict[str, QuestEntry] = {q.title: q for q in QUEST_REGISTRY}
ENDGAME_QUESTS: Tuple[QuestEntry, ...] = tuple(
    q for q in QUEST_REGISTRY if "endgame" in q.notes.lower() or "final" in q.notes.lower()
)


# ---------------------------------------------------------------------------
# §6.2 — Book Order
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BookEntry:
    book_number: int
    title: str
    is_hub: bool
    hub_arc: Optional[str]  # "lower", "upper", or None


BOOK_ORDER: Tuple[BookEntry, ...] = (
    BookEntry(1,  "Princess of Eclipses",       False, None),
    BookEntry(2,  "Knights of the Veil",         False, None),
    BookEntry(3,  "Fullmetal Forest",            False, None),
    BookEntry(4,  "Secrets of Neverland",        False, None),
    BookEntry(5,  "Truth Be Told",               True,  "lower"),   # Hub: assembling what is true
    BookEntry(6,  "As Within So Without",        False, None),
    BookEntry(7,  "Alchemist's Labor of Love",   True,  "upper"),   # Hub: working with truth
    BookEntry(8,  "Reign of Nobody",             False, None),
    # Books 9–31 to be determined
)

BOOK_BY_NUMBER: Dict[int, BookEntry] = {b.book_number: b for b in BOOK_ORDER}
HUB_BOOKS: Tuple[BookEntry, ...] = tuple(b for b in BOOK_ORDER if b.is_hub)


# ---------------------------------------------------------------------------
# §6.7 — GameNode Structure
# ---------------------------------------------------------------------------

@dataclass
class GameNode:
    """
    One game in the Ko's Labyrinth anthology.

    Books 5 (Truth Be Told) and 7 (Alchemist's Labor of Love) are hubs.
    They create a figure-eight topology through the anthology —
    two loops sharing a crossing point, Möbius-adjacent in structure.

    The exoteric sequence is the release order.
    The esoteric sequence is different for every player.
    The same game is a different philosophical argument for different players
    because it responds to their actual epistemological state.
    """
    game_id: int                                    # 1–31
    shygazun_name: str                              # The game's name in the byte space
    exit_flags: List[str]                           # Shygazun state names this game can produce
    interchange_weights: Dict[int, float]           # game_id → influence weight on other games
    hub: bool = False                               # True for Books 5 and 7

    # These are provided at game construction by the game's team, not machine-generated:
    # starting_conditions: Callable[[BreathOfKo], WorldState]
    # throughput_logic: Callable[[BreathOfKo, GameState], GameState]


# ---------------------------------------------------------------------------
# Map Location Registry (Book 1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LocationEntry:
    name: str
    location_type: str  # "demon_domain", "settlement", "void_site", "realm"
    region: Optional[str]
    notes: str



# ---------------------------------------------------------------------------
# Entity Hierarchy (outer to inner)
# ---------------------------------------------------------------------------

# The hierarchy defines the relational distance from the Player.
# Outer = more cosmologically distant; Inner = more personally proximate.
ENTITY_HIERARCHY: Tuple[str, ...] = (
    "Player",
    "Alchemist",
    "Primordials",
    "World Soul",
    "Gods",
    "Void Wraiths",
    "Demons",
    "Witches",
    "Priests",
    "Monarchs/Royals",
    "Assassins",
    "Soldiers",
    "Djinn",
    "Faeries",
    "Undines",
    "Salamanders",
    "Dryads",
    "Gnomes",
    "Townfolk",
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def registry_summary() -> Dict[str, int]:
    """Return a count summary of all registry entries."""
    return {
        "objects": len(OBJECT_REGISTRY),
        "items": len(ITEM_REGISTRY),
        "craftable_items": len(CRAFTABLE_ITEMS),
        "characters": len(CHARACTER_REGISTRY),
        "quests": len(QUEST_REGISTRY),
        "books": len(BOOK_ORDER),
        "object_traits": len(OBJECT_TRAITS),
        "entity_types": len(ID_SCHEMA),
    }

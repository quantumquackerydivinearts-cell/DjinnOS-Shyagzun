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

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


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
    "_ALZD": "Alzedroswune",
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


_OBJECT_TABLE: Tuple[Tuple[str, Optional[str]], ...] = (
    ("Mortar",          "0001_KLOB"),
    ("Pestle",          "0002_KLOB"),
    ("Rag",             "0003_KLOB"),
    ("Stand",           "0004_KLOB"),
    ("Retort",          "0005_KLOB"),
    ("Volume Flask",    "0006_KLOB"),
    ("Reagent Bottle",  "0007_KLOB"),
    ("Sand",            "0008_KLOB"),
    ("Refined Sand",    "0009_KLOB"),
    ("Furnace",         "0010_KLOB"),
    ("Wooden Spoon",    "0011_KLOB"),
    ("Copper Spoon",    "0012_KLOB"),
    ("Iron Spoon",      "0013_KLOB"),
    ("Steel Spoon",     "0014_KLOB"),
    ("Granite Spoon",   "0015_KLOB"),
    ("Bellows",         "0016_KLOB"),
    ("Crucible",        "0017_KLOB"),
    ("Bottle",          "0018_KLOB"),
    ("Jar",             "0019_KLOB"),
    ("Diatom Earth",    "0020_KLOB"),
    ("Glycerine",       "0021_KLOB"),
    ("Petroleum Jelly", "0022_KLOB"),
    ("Saltpeter",       "0023_KLOB"),
    ("Sulphur",         "0024_KLOB"),
    ("Charcoal",        "0025_KLOB"),
    ("Tin",             "0026_KLOB"),
    ("Iron",            "0027_KLOB"),
    ("Gold",            "0028_KLOB"),
    ("Copper",          "0029_KLOB"),
    ("Mercury",         "0030_KLOB"),
    ("Silver",          "0031_KLOB"),
    ("Lead",            "0032_KLOB"),
    ("Nickel",          "0033_KLOB"),
    ("Cyanide",         "0034_KLOB"),
    ("Ashes",           "0035_KLOB"),
    ("Caustic Lye",     "0036_KLOB"),
    ("Potassium",       "0037_KLOB"),
    ("Phosphorus",      "0038_KLOB"),
    ("Arsenic",         "0039_KLOB"),
    ("Water",           "0040_KLOB"),
    ("Wood",            "0041_KLOB"),
    ("Flint",           "0042_KLOB"),
    ("Shark Tooth",     "0043_KLOB"),
    ("Granite",         "0044_KLOB"),
    ("Obsidian",        "0045_KLOB"),
    ("Chalk",           "0046_KLOB"),
    ("Gypsum",          "0047_KLOB"),
    ("Quartz",          "0048_KLOB"),
    ("Pumice",          "0049_KLOB"),
    ("Amethyst",        "0050_KLOB"),
    ("Ruby",            "0051_KLOB"),
    ("Sapphire",        "0052_KLOB"),
    ("Emerald",         "0053_KLOB"),
    ("Diamond",         "0054_KLOB"),
    ("Jade",            "0055_KLOB"),
    ("Crucible Tongs",  "0056_KLOB"),
    ("Ring Mold",       "0057_KLOB"),
    ("Ingot Mold",      "0058_KLOB"),
    ("Anvil",           "0059_KLOB"),
    ("Hammer",          "0060_KLOB"),
    ("Lathe Chuck",     "0061_KLOB"),
    ("Lathe",           "0062_KLOB"),
    ("Chisel",          "0063_KLOB"),
    ("Ring Blank",      "0064_KLOB"),
    ("Moldavite",       "0065_KLOB"),
    ("Desert Glass",    "0066_KLOB"),
    ("Pearl",           "0067_KLOB"),
    ("Black Pearl",     "0068_KLOB"),
    ("Pulp",            "0069_KLOB"),
    ("Paper",           "0070_KLOB"),
    ("Ink",             "0071_KLOB"),
    ("Pen",             "0072_KLOB"),
    ("Herb (Common)",       "0073_KLOB"),
    ("Herb (Restorative)",  "0074_KLOB"),
    ("Binding Wax",         "0075_KLOB"),
    ("Raw Desire Stone",    "0076_KLOB"),
    ("Asmodean Essence",    "0077_KLOB"),
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
    ("Joannah",             "0001_TOWN",  "Caravan Dispatcher, Cryptographer, Artist, Mother of 3 (32)"),
    ("Wells",               "0002_TOWN",  "Aqueduct Foreman, engineer, father of 6 (38)"),
    ("Lavelle",             "0003_TOWN",  "Laundry worker, explosive hobbyist, bookworm, mother of 2 (23)"),
    ("Sidhal",              "0004_TOWN",  "Farmer, Forester, Temple Custodian, Father of 2 (26)"),
    ("Kore",                "0005_WTCH",  "Life witch, Transfemme, Ko Devotee, Lesbian Lover of Tagame (30)"),
    ("Alfir",               "0006_WTCH",  "Cosmic Witch, Former priest, Daemonologist (50)"),
    ("Forest",              "0007_WTCH",  "Dryad obsessed Nature Wizard, Gay (27)"),
    ("Saffron",             "0008_PRST",  "Purple robe, red wings, Menace to Nature, Nexiott's Priest (72)"),
    ("Lucion",              "0009_PRST",  "Ceramics, cryptography, medicine, chemistry, Librarian (35), Jabiru Priest"),
    ("Rachelle",            "0010_PRST",  "Alfir's Replacement, Advisor to Chancellor Kelly, Shakzefan Priestess (35)"),
    ("Hue",                 "0011_ASSN",  "Student of Sophia, Haunted by Po'elfan, Kore's brother (24)"),
    ("Cyrus",               "0012_ASSN",  "Student of Lectura, disguise expert, blue hair (20)"),
    ("Asmoth",              "0013_ASSN",  "Child of the Fae, orphaned by Kielum's war (29)"),
    ("Chancellor Kelly",    "0014_ROYL",  "Oldest in Castle AZoth, talks to angels (38)"),
    ("King Bombastus",      "0015_ROYL",  "Father from FMAb, but lost as Van Hoenhiem. (58)"),
    ("Queen Hildegarde",    "0016_ROYL",  "Scholar Queen, stressed mother, linguistics lover (49)"),
    ("Lord Nexiott",        "0017_ROYL",  "Corona Caravans Boss, Propagandist (52)"),
    ("Duke Eomann",         "0018_ROYL",  "Devoted to Bombastus, Sworn to the Fae, (56)"),
    ("Princess Luminyx",    "0019_ROYL",  "Protagonist of Book 1 — spelling: Luminyx; Royal Heir (sole) Pivotal character, full of mischief and wonder (22)"),
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
    ("Vajil",               "1015_DRYA",  "Great Oak dryad, Titanium Bark, gay, CG"),
    ("Giann",               "1016_DJNN",  "Heart of Kael, Benefactor of All, CG"),
    ("Keshi",               "1017_DJNN",  "Gift Horse, Destroyer of Growth, CE"),
    ("Drovitth",            "1018_DJNN",  "Astrologer, Watcher of Life, LN"),
    ("Haldoro",             "2001_VDWR",  "Void Wraith - Knower of Minds"),
    ("Vios",                "2002_VDWR",  "Void Wraith - Knower of Souls"),
    ("Negaya",              "2003_VDWR",  "Void Wraith - Knower of Bodies"),
    ("Otheiru",             "2004_DMON",  "'Blood Ball', Made of Lost life, massive, voracious, master of blood puppets, Demon of Abandon"),
    ("Kielum",              "2005_DMON",  "'Conquest', Demon of finance, cults, war, abuse"),
    ("Ruzoa",               "2006_DMON",  "'Anhihilation', Demon of Depression and Despair"),
    ("Po'Elfan",            "2007_DMON",  "'Terrorizer', Demon of Anxiety and mindless panic"),
    ("Kaganue",             "2008_DMON",  "'Liar', Demon of Doublespeak and Ambiguity, Foil to Jabiru, Prophet of Ko"),
    ("Zukoru",              "2009_DMON",  "'Death Most Obscene', Demon of Betrayal — originating demon"),
    ("Shapier",             "2010_DEMI",  "Demigod of Culture, Spawned of Keshi and Jabiru"),
    ("Lanzu",               "2011_DEMI",  "Demigod of Transformation, Son of Lakota and Zukoru"),
    ("Tagame",              "2012_DEMI",  "Demigoddess of Life, Daughter of Negaya and Lakota"),
    ("Captain Lanvaki",     "2013_SOLD",  "Hero of Wisdom, Resilient and tenacious (33, Void-Gender)"),
    ("Sgt. Akande",         "2014_SOLD",  "Hero of Courage, Bold and willing (28, F)"),
    ("Pvt. Kilesha",        "2015_SOLD",  "Hero of Power, Foolish and Proud (25, M)"),
    ("Moshize",             "2016_GODS",  "Shygazun: Relaxed Relation There; Triple God/dess of Attainment and Harmony"),
    ("Shakzefan",           "2017_GODS",  "Shygazun: Fire of Growth; Goddess of Growth and Loss, connected with Loss, I Fear, Growing Pains, and Good Grief"),
    ("Lakota",              "2018_GODS",  "Shygazun: Tension of The Unconscious; God of Wisdom, Fires of Rebirth, and Necromancy"),
    ("Jabiru",              "2019_GODS",  "Shygazun: Front Ruling Bottom; Spirit of Language, God of Knowledge and stories"),
    ("Ohadame",             "2020_GODS",  "Shygazun: Mental Negation Present as Absolute Conjoined as Memory; Goddess of Past-life Memories and Lifetimes"),
    ("Ko",                  "2021_GODS",  "Shygazun: Experience/Intuition; Goddess of Creation and The Moon, Draconic."),
    ("Koga",                "2022_GODS",  "Shygazun: Experiential Void; Goddess of Mystery, Master Mage"),
    ("Mona",                "2023_GODS",  "Shygazun: Relaxed Void; Goddess of Tranquility, Master Warrior"),
    ("Zoha",                "2024_GODS",  "Shygazun: Absence Present as Absolute; Goddess of Art and Play, Master of Torment (not a Primordial)"),
    ("Ga",                  "2025_PRIM",  "The Void, Primordial of Darkness and Space"),
    ("Na",                  "2026_PRIM",  "The World, Primordial of Color and Relationship"),
    ("Ha",                  "2027_PRIM",  "The Abyss, Primordial of Light and Madness"),
    ("Ung",                 "2028_PRIM",  "The Path, Primordial of Energy"),
    ("Wu",                  "2029_PRIM",  "The Game, Primordial of Consciousness"),
    ("Kael",                "2030_PRIM",  "The Star, Primordial of Chaos and Life"),
    ("Lapidus",             "3001_ANMU",  "Anima Mundi — Spirit of the Overworld, Endurance, and Truth"),
    ("Mercurie",            "3002_ANMU",  "Anima Mundi — Spirit of the Spirit Realm, Nature, and Magic"),
    ("Sulphera",            "3003_ANMU",  "Anima Mundi — Spirit of the Underworld of Choices and Consequence"),
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
    ("Health Potion",            "0001_KLIT", False),
    ("Cherry",                   "0002_KLIT", False),
    ("Apple",                    "0003_KLIT", False),
    ("Pomegranate",              "0004_KLIT", False),
    ("Barley",                   "0005_KLIT", False),
    ("Pine Needle",              "0006_KLIT", False),
    ("Acorn",                    "0007_KLIT", False),
    ("Lotus Flower",             "0008_KLIT", False),
    ("Lotus Seed",               "0009_KLIT", False),
    ("Pine Nut",                 "0010_KLIT", False),
    ("Apple Seed",               "0011_KLIT", False),
    ("Cherry Pit",               "0012_KLIT", False),
    ("Necklace",                 "0013_KLIT", False),
    ("Ring",                     "0014_KLIT", True),
    ("Ingot",                    "0015_KLIT", True),
    ("Coin",                     "0016_KLIT", True),
    ("Dagger",                   "0017_KLIT", True),
    ("Sword",                    "0018_KLIT", True),
    ("Shield",                   "0019_KLIT", False),
    ("Bow",                      "0020_KLIT", False),
    ("Arrow",                    "0021_KLIT", True),
    ("Staff",                    "0022_KLIT", True),
    ("Desire Crystal",           "0023_KLIT", False),
    ("Angelic Spear",            "0024_KLIT", False),
    ("Angelic Gun",              "0025_KLIT", False),
    ("Demonic Irons",            "0026_KLIT", False),
    ("Basic Tincture",           "0034_KLIT", True),
    ("Restorative Tincture",     "0035_KLIT", True),
    ("Desire Crystal Fragment",  "0036_KLIT", True),
    ("Infernal Salve",           "0037_KLIT", True),
    ("Angelic Revival Salve",    "0038_KLIT", True),
    ("Map of Mercurie",          "0039_KLIT", False),
    ("Gold Rounds",              "0040_KLIT", False),
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
    ("Had Me in the First Half",  "0049_KLST", "Reveals Nexiott's affair"),
    ("Prophet of Ko",             "0050_KLST", "Kaganue's Quest"),
    ("Eclipse!",                  "0051_KLST", ""),
    ("The Abyss",                 "0052_KLST", ""),
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
    # ── Arc 1: Earth and the first wound (Games 1–4) ─────────────────────────
    BookEntry(1,  "Princess of Eclipses",          False, None),   # Luminyx mortal; timeline split 5237/1728; Great Obscenity origin
    BookEntry(2,  "Knights of the Veil",            False, None),   # Thool Society merger; Templar→Illuminati; narrative control begins
    BookEntry(3,  "Fullmetal Forest",               False, None),   # Cybernetic forest internet; chimera experiments; nuclear event
    BookEntry(4,  "Secrets of Neverland",           False, None),   # ~200yr post-nuclear; Sulphera leakage; Threshold Events introduced
    # ── Hub 1 — Truth Be Told (Game 5) ───────────────────────────────────────
    BookEntry(5,  "Truth Be Told",                  True,  "lower"),   # Hub: assembling what is true. Minerva Moon. Early space empire.
    # ── Arc 2: The Great Obscenity and the Labyrinth (Games 6–7) ────────────
    BookEntry(6,  "As Within So Without",           False, None),   # Late 33rd C; Great Obscenity trigger; Hypnotic Threshold Event
    # ── Hub 2 — An Alchemist's Labor of Love (Game 7) ────────────────────────
    BookEntry(7,  "An Alchemist's Labor of Love",   True,  "upper"),   # Hub: working with truth. Ko's Labyrinth (Aeralune). Saelith born.
    # ── Arc 3: After the Labyrinth (Games 8–11) ──────────────────────────────
    BookEntry(8,  "Reign of Nobody",                False, None),   # Reign of Saelith from the past
    BookEntry(9,  "Rise of Alzedros",               False, None),   
    BookEntry(10, "The Voice of Ko",                False, None),   # Ko-centered game
    BookEntry(11, "Icons of Time",                  False, None),
    # ── Arc 4: Sha's Arc (Games 12–13) ───────────────────────────────────────
    BookEntry(12, "Students of Sha",                False, None),   # Sha — Phoenix of intellect; Ko's counterpart; the intellectual journey
    BookEntry(13, "Ghosts of Azoth",                False, None),   # Azoth = complex number in BreathOfKo; alchemical throughline
    # ── Arc 5: Archon War and the Lost (Games 14–16) ─────────────────────────
    BookEntry(14, "Chimeras of The Archons",        False, None),   # Breaking the Gnostic mythology of evil over the back of cellular liberation
    BookEntry(15, "Lost Yokai",                     False, None),
    BookEntry(16, "Battered Stars",                 False, None),
    # ── Arc 6: Saelith's Arc (Game 17) ───────────────────────────────────────
    BookEntry(17, "Saelith's Mercy",                False, None),   # Saelith's own arc; FaeDjinn hybrid; born in Game 7; The Test homage
    # ── Convergence: Mystic Pines × KLGS (Game 18) ───────────────────────────
    BookEntry(18, "Mystic Blood",                   False, None),   # YuYu (0001_MYPN); the ONE sanctioned-kill game; St. Alaro erasure
    # ── Arc 7: The Cause and Hidden Knowledge (Games 19–21) ──────────────────
    BookEntry(19, "Tides of The Cause",             False, None),
    BookEntry(20, "Daath Most Have Seen",           False, None),   # Daath — Kabbalistic hidden knowledge
    BookEntry(21, "Callsigns of Thool",             False, None),   # Thool Society network legibility; learning to read their signals
    # ── Arc 8: Void and Requiem (Games 22–24) ────────────────────────────────
    BookEntry(22, "Horrors of The Void",            False, None),
    BookEntry(23, "Requiem of Po'Elfan",            False, None),   # Po'Elfan — Demon of Anxiety; trial: facing death; Thool/Po'Elfan link
    BookEntry(24, "Polar Shift",                    False, None),
    # ── Arc 9: Galactic and Fires (Games 25–26) ──────────────────────────────
    BookEntry(25, "Galactic Hallows",               False, None),
    BookEntry(26, "Fires of Sha",                   False, None),   # Sha's purifying end; bookends with Game 12; Ko←→Sha eternal cycle
    # ── Arc 10: Toward the Great Work (Games 27–31) ──────────────────────────
    BookEntry(27, "Gourds of Ash",                  False, None),
    BookEntry(28, "Legacy of Luminyx",              False, None),   # Luminyx honored near series end; spirit after 1782
    BookEntry(29, "Barkeep of Broken Dreams",       False, None),
    BookEntry(30, "Death of an Empress",            False, None),
    BookEntry(31, "The Great Work",                 False, None),   # Series conclusion — alchemical Magnum Opus
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
    "Alzedroswune",
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

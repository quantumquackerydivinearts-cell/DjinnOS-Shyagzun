/**
 * game7Registry.js
 *
 * Canonical data registry for Game 7 (7_KLGS) — Ko's Labyrnth, Aeralune.
 *
 * Entity ID conventions:
 *   Objects:    {####}_KLOB   (e.g. 8000_KLOB)
 *   Items:      {####}_KLIT   (e.g. 0035_KLIT)
 *   Quests:     {####}_KLST   (e.g. 0009_KLST, zero-padded to 4 digits)
 *   Characters: {####}_{TYPE} where TYPE is one of:
 *     test  — test/dev placeholders
 *     HIST  — Historical / Autobiographical avatar (Alexi = 0000_0451; ID references Hypatia of Alexandria ~415 CE)
 *     TOWN  — Townsperson
 *     WTCH  — Witch
 *     PRST  — Priest
 *     ASSN  — Assassin
 *     ROYL  — Royalty
 *     GNOM  — Gnome
 *     NYMP  — Nymph
 *     UNDI  — Undine
 *     SALA  — Salamander
 *     DRYA  — Dryad
 *     DJNN  — Djinn
 *     VDWR  — Void Wraith
 *     DMON  — Demon
 *     DEMI  — Demi-god
 *     SOLD  — Soldier
 *     GODS  — God
 *     PRIM  — Primordial
 *     ANMU  — Anima Mundi / World Soul (Sulphera, Lapidus, Mercurie, Pythia Solunikae)
 *
 *   dual_type: optional secondary type for beings that hold two natures simultaneously.
 *     Only Pythia Solunikae currently carries this — type: "ANMU", dual_type: "PRIM".
 *
 * Item prefix convention:
 *   ()ItemName — stackable item (can have quantity > 1)
 *
 * Object trait IDs (numeric):
 *   0=Usable, 1=Unusable, 2=Full, 3=Empty, 4=Alive, 5=Dead,
 *   6=Movable, 7=Immobilized, 8=Poisonous, 9=Flammable, 10=Inert,
 *   11=Explosive, 12=Token, 13=Collector, 14=Powdered, 15=Molten
 */

// ── Object Trait IDs ──────────────────────────────────────────────────────────
export const OBJECT_TRAITS = {
  0:  "Usable",
  1:  "Unusable",
  2:  "Full",
  3:  "Empty",
  4:  "Alive",
  5:  "Dead",
  6:  "Movable",
  7:  "Immobilized",
  8:  "Poisonous",
  9:  "Flammable",
  10: "Inert",
  11: "Explosive",
  12: "Token",
  13: "Collector",
  14: "Powdered",
  15: "Molten",
};

export const OBJECT_TRAIT_BY_NAME = Object.fromEntries(
  Object.entries(OBJECT_TRAITS).map(([id, name]) => [name, Number(id)])
);

// ── Objects (KLOB) ────────────────────────────────────────────────────────────
// ID groupings:
//   0001-0029  Lab equipment (tools, vessels, spoons)
//   0030       Heat equipment
//   1001-1099  Processing materials (bulk chemicals, organic)
//   2001-2099  Metals
//   3001-3099  Minerals
//   4001-4099  Gems and special stones
//   5001-5099  Writing materials
//   8000,2000  Grinding tools (Mortar, Pestle — existing IDs preserved)
//   9001-9099  Quest / realm-specific materials
export const OBJECTS = [
  // ── Grinding tools ──────────────────────────────────────────────────────────
  { id: "8000_KLOB", name: "Mortar",            category: "grinding",  default_trait: 0 },
  { id: "2000_KLOB", name: "Pestle",            category: "grinding",  default_trait: 1 },

  // ── Lab equipment ───────────────────────────────────────────────────────────
  { id: "0001_KLOB", name: "Rag",               category: "tool" },
  { id: "0002_KLOB", name: "Stand",             category: "tool" },
  { id: "0003_KLOB", name: "Retort",            category: "vessel" },
  { id: "0004_KLOB", name: "Volume Flask",      category: "vessel" },
  { id: "0005_KLOB", name: "Reagent Bottle",    category: "vessel" },
  { id: "0006_KLOB", name: "Bellows",           category: "tool" },
  { id: "0007_KLOB", name: "Crucible",          category: "vessel" },
  { id: "0008_KLOB", name: "Bottle",            category: "vessel" },
  { id: "0009_KLOB", name: "Jar",               category: "vessel" },
  { id: "0010_KLOB", name: "Crucible Tongs",    category: "tool" },
  { id: "0011_KLOB", name: "Ring Mold",         category: "tool" },
  { id: "0012_KLOB", name: "Ingot Mold",        category: "tool" },
  { id: "0013_KLOB", name: "Anvil",             category: "smithing" },
  { id: "0014_KLOB", name: "Hammer",            category: "smithing" },
  { id: "0015_KLOB", name: "Lathe Chuck",       category: "smithing" },
  { id: "0016_KLOB", name: "Lathe",             category: "smithing" },
  { id: "0017_KLOB", name: "Chisel",            category: "smithing" },
  { id: "0018_KLOB", name: "Ring Blank",        category: "smithing" },
  { id: "0019_KLOB", name: "Pen",               category: "writing" },

  // ── Spoons (stirring) ───────────────────────────────────────────────────────
  { id: "0020_KLOB", name: "Wooden Spoon",      category: "stirring" },
  { id: "0021_KLOB", name: "Copper Spoon",      category: "stirring" },
  { id: "0022_KLOB", name: "Iron Spoon",        category: "stirring" },
  { id: "0023_KLOB", name: "Steel Spoon",       category: "stirring" },
  { id: "0024_KLOB", name: "Granite Spoon",     category: "stirring" },

  // ── Heat equipment ──────────────────────────────────────────────────────────
  { id: "0030_KLOB", name: "Furnace",           category: "heat" },

  // ── Processing materials ────────────────────────────────────────────────────
  { id: "1001_KLOB", name: "Sand",              category: "material" },
  { id: "1002_KLOB", name: "Refined Sand",      category: "material" },
  { id: "1003_KLOB", name: "Diatom Earth",      category: "filtering" },
  { id: "1004_KLOB", name: "Glycerine",         category: "chemical" },
  { id: "1005_KLOB", name: "Petroleum Jelly",   category: "chemical" },
  { id: "1006_KLOB", name: "Saltpeter",         category: "chemical" },
  { id: "1007_KLOB", name: "Sulphur",           category: "chemical" },
  { id: "1008_KLOB", name: "Charcoal",          category: "chemical" },
  { id: "1009_KLOB", name: "Ashes",             category: "chemical" },
  { id: "1010_KLOB", name: "Caustic Lye",       category: "chemical" },
  { id: "1011_KLOB", name: "Potassium",         category: "chemical" },
  { id: "1012_KLOB", name: "Phosphorus",        category: "chemical" },
  { id: "1013_KLOB", name: "Arsenic",           category: "chemical" },
  { id: "1014_KLOB", name: "Cyanide",           category: "chemical" },
  { id: "1015_KLOB", name: "Water",             category: "material" },
  { id: "1016_KLOB", name: "Wood",              category: "material" },
  { id: "1017_KLOB", name: "Flint",             category: "mineral" },
  { id: "1018_KLOB", name: "Shark Tooth",       category: "mineral" },

  // ── Metals ──────────────────────────────────────────────────────────────────
  { id: "2001_KLOB", name: "Tin",               category: "metal" },
  { id: "2002_KLOB", name: "Iron",              category: "metal" },
  { id: "2003_KLOB", name: "Gold",              category: "metal" },
  { id: "2004_KLOB", name: "Copper",            category: "metal" },
  { id: "2005_KLOB", name: "Mercury",           category: "metal" },
  { id: "2006_KLOB", name: "Silver",            category: "metal" },
  { id: "2007_KLOB", name: "Lead",              category: "metal" },
  { id: "2008_KLOB", name: "Nickel",            category: "metal" },

  // ── Minerals ────────────────────────────────────────────────────────────────
  { id: "3001_KLOB", name: "Granite",           category: "mineral" },
  { id: "3002_KLOB", name: "Obsidian",          category: "mineral" },
  { id: "3003_KLOB", name: "Chalk",             category: "mineral" },
  { id: "3004_KLOB", name: "Gypsum",            category: "mineral" },
  { id: "3005_KLOB", name: "Quartz",            category: "mineral" },
  { id: "3006_KLOB", name: "Pumice",            category: "mineral" },

  // ── Gems and special stones ─────────────────────────────────────────────────
  { id: "4001_KLOB", name: "Amethyst",          category: "gem" },
  { id: "4002_KLOB", name: "Ruby",              category: "gem" },
  { id: "4003_KLOB", name: "Sapphire",          category: "gem" },
  { id: "4004_KLOB", name: "Emerald",           category: "gem" },
  { id: "4005_KLOB", name: "Diamond",           category: "gem" },
  { id: "4006_KLOB", name: "Jade",              category: "gem" },
  { id: "4007_KLOB", name: "Moldavite",         category: "gem" },
  { id: "4008_KLOB", name: "Desert Glass",      category: "gem" },
  { id: "4009_KLOB", name: "Pearl",             category: "gem" },
  { id: "4010_KLOB", name: "Black Pearl",       category: "gem" },

  // ── Writing materials ───────────────────────────────────────────────────────
  { id: "5001_KLOB", name: "Pulp",              category: "writing" },
  { id: "5002_KLOB", name: "Paper",             category: "writing" },
  { id: "5003_KLOB", name: "Ink",               category: "writing" },

  // ── Quest / realm-specific materials ────────────────────────────────────────
  { id: "9001_KLOB", name: "Demonic Iron",       category: "quest_material",
    note: "Iron from Sulphera — carries the infernal register. Used in 0041 poison and Colt .45." },
  { id: "9002_KLOB", name: "Angelic Spear",      category: "quest_material",
    note: "From the Pride Ring ash fields — continuous extermination campaign." },
  { id: "9003_KLOB", name: "Crystal Dust",       category: "quest_material",
    note: "Dissolved Asmodean Crystal from 0007 — reagent for Infernal Salve." },
  { id: "9004_KLOB", name: "Salt Water",         category: "quest_material",
    note: "Ocean water — used to rust purified demonic iron in 0041." },
  { id: "9005_KLOB", name: "Purified Demonic Iron", category: "quest_material",
    note: "Intermediate: demonic iron purified over sulphur in furnace." },
  { id: "9006_KLOB", name: "Rusted Iron Vial",   category: "quest_material",
    note: "Intermediate: rust from salt-water-corroded purified demonic iron, collected in vial." },
  { id: "9007_KLOB", name: "Angelic-Purified Iron", category: "quest_material",
    note: "Intermediate: demonic iron melted with angelic spears — basis for Colt .45." },
  { id: "9008_KLOB", name: "Infernal Salve",     category: "quest_output",
    note: "Enables descent into the Sulphera rings. Made from Crystal Dust." },
  { id: "9009_KLOB", name: "Nexiott Poison",     category: "quest_output",
    note: "Rusted iron vial mixed with mercury. Penetrates Kielum's protection." },
  { id: "9010_KLOB", name: "Colt .45",           category: "quest_output",
    note: "Hypatia's Angelic Gun. Fires gold bullets. Only thing that can kill Sophia." },
];

// ── Characters ────────────────────────────────────────────────────────────────
// stackable: false by default — set on items with () prefix in canonical data
export const CHARACTERS = [
  // Test
  { id: "0000_test",  name: "User1",               type: "test" },

  // Alexandria Sophia Hypatia — the author's avatar. ID references Hypatia of Alexandria (~415 CE).
  // Alexi (the developer) IS this character. The game is autobiographical at the deepest level.
  // Appears as NPC in the Royal Ring of Sulphera. Player character of the KLGS series.
  { id: "0000_0451",  name: "Alexandria Sophia Hypatia",  type: "HIST",
    full_name: "Alexandria Sophia Hypatia",
    note: "The developer Alexi's avatar. ID uses historical year reference (Hypatia of Alexandria). " +
          "Protagonist/player character across the series. NPC in Sulphera's Royal Ring." },

  // Townspeople
  { id: "0001_TOWN",  name: "Joannah",   type: "TOWN", note: "Warren resident. Husband: Kaelith (0009_TOWN)." },
  { id: "0002_TOWN",  name: "Wells",     type: "TOWN", note: "Aqueduct foreman, 38, father of 6. Wife: Janine (0007_TOWN). Serpent's Pass end of 0003_KLST." },
  { id: "0003_TOWN",  name: "Lavelle",   type: "TOWN", note: "Laundry/explosives/bookworm, 23, mother of 2. Husband: Hartwell (0008_TOWN). Serpent's Pass end of 0003_KLST." },
  { id: "0004_TOWN",  name: "Sidhal",    type: "TOWN", note: "Forester and temple custodian, 26, father of 2. Wife: Marcia (0010_TOWN). Guide through Hopefare Road warrens in 0003_KLST." },
  { id: "0005_TOWN",  name: "James",     type: "TOWN", note: "Aqueduct worker, 24. Lover: Tyrone (0006_TOWN). Works with Wells." },
  { id: "0006_TOWN",  name: "Tyrone",    type: "TOWN", note: "Aqueduct worker, 24. Lover: James (0005_TOWN). Works with Wells." },
  { id: "0007_TOWN",  name: "Janine",    type: "TOWN", note: "Wife of Wells (0002_TOWN)." },
  { id: "0008_TOWN",  name: "Hartwell",  type: "TOWN", note: "Husband of Lavelle (0003_TOWN)." },
  { id: "0009_TOWN",  name: "Kaelith",   type: "TOWN", note: "Husband of Joannah (0001_TOWN). Works the mines with the children, same age as Joannah." },
  { id: "0010_TOWN",  name: "Marcia",    type: "TOWN", note: "Wife of Sidhal (0004_TOWN), 28. Teacher at the temple." },
  { id: "0011_TOWN",  name: "Genovise",  type: "TOWN", note: "Single, 30. Runs an occult shop in an alley on the way to Serpent's Pass. Works with Savvi to run the black market." },

  // Witches — Alfir is the Game 7 mentor who teaches Infernal Meditation
  { id: "0005_WTCH",  name: "Kore",                type: "WTCH" },
  { id: "0006_WTCH",  name: "Alfir",               type: "WTCH",
    role: "mentor", teaches: "infernal_meditation",
    note: "Teaches Infernal Meditation early in Game 7. Gateway to Sulphera access." },
  { id: "0007_WTCH",  name: "Forest",              type: "WTCH" },

  // Priests
  { id: "0008_PRST",  name: "Saffron",             type: "PRST" },
  { id: "0009_PRST",  name: "Lucion",              type: "PRST" },
  { id: "0010_PRST",  name: "Rachelle",            type: "PRST" },

  // Assassins
  { id: "0011_ASSN",  name: "Hue",                 type: "ASSN" },
  { id: "0012_ASSN",  name: "Cyrus",               type: "ASSN" },
  { id: "0013_ASSN",  name: "Asmoth",              type: "ASSN" },

  // Royalty — Luminyx is a Princess in Game 7
  { id: "0014_ROYL",  name: "Chancellor Kelly",    type: "ROYL" },
  { id: "0015_ROYL",  name: "King Bombastus",      type: "ROYL" },
  { id: "0016_ROYL",  name: "Queen Hildegarde",    type: "ROYL" },
  { id: "0017_ROYL",  name: "Lord Nexiott",        type: "ROYL" },
  { id: "0018_ROYL",  name: "Duke Eomann",         type: "ROYL" },
  { id: "0019_ROYL",  name: "Princess Luminyx",    type: "ROYL",
    note: "Luminyx is a Princess in Game 7. She becomes the mortal in Game 1 (alive/mortal). " +
          "She does not become a spirit until 1782." },

  // Gnomes
  { id: "1001_GNOM",  name: "Clint",               type: "GNOM" },
  { id: "1002_GNOM",  name: "Gnolan",              type: "GNOM" },
  { id: "1003_GNOM",  name: "Winnona",             type: "GNOM" },

  // Nymphs
  { id: "1004_NYMP",  name: "Amelia",              type: "NYMP" },
  { id: "1005_NYMP",  name: "Echo",                type: "NYMP" },
  { id: "1006_NYMP",  name: "Karlia",              type: "NYMP" },

  // Undines
  { id: "1007_UNDI",  name: "Sophia",              type: "UNDI" },
  { id: "1008_UNDI",  name: "Lectura",             type: "UNDI" },
  { id: "1009_UNDI",  name: "Faygoru",             type: "UNDI" },

  // Salamanders (children of Lakota)
  { id: "1010_SALA",  name: "Chazak",              type: "SALA" },
  { id: "1011_SALA",  name: "Axiozul",             type: "SALA" },
  { id: "1012_SALA",  name: "Savvi",               type: "SALA" },

  // Dryads
  { id: "1013_DRYA",  name: "Eukala",              type: "DRYA" },
  { id: "1014_DRYA",  name: "Tymona",              type: "DRYA" },
  { id: "1015_DRYA",  name: "Vajil",               type: "DRYA" },

  // Djinn
  { id: "1016_DJNN",  name: "Giann",               type: "DJNN" },
  { id: "1017_DJNN",  name: "Keshi",               type: "DJNN" },
  { id: "1018_DJNN",  name: "Drovitth",            type: "DJNN",
    note: "Drovitth is the Djinn who built the Orrery alongside the 7 Sin Rulers and King Paimon." },

  // Void Wraiths
  { id: "2001_VDWR",  name: "Haldoro",             type: "VDWR",
    title: "Knower of Minds", observes: "silence" },
  { id: "2002_VDWR",  name: "Vios",                type: "VDWR",
    title: "Knower of Souls", observes: "omission" },
  { id: "2003_VDWR",  name: "Negaya",              type: "VDWR",
    title: "Knower of Bodies", observes: "kill" },

  // Demons
  { id: "2004_DMON",  name: "Otheiru",             type: "DMON" },
  { id: "2005_DMON",  name: "Kielum",              type: "DMON" },
  { id: "2006_DMON",  name: "Ruzoa",               type: "DMON" },
  { id: "2007_DMON",  name: "Po'Elfan",            type: "DMON" },
  { id: "2008_DMON",  name: "Kaganue",             type: "DMON" },
  { id: "2009_DMON",  name: "Zukoru",              type: "DMON" },
  { id: "2011_DMON",  name: "St. Alaro",           type: "DMON",
    alias: "Alastor",
    note: "The Radio Demon of Pride. Operating in Aeralune under the alias St. Alaro. " +
          "Encountered through the secret ending arc — not a traversal-path NPC. " +
          "Offers a Faustian pact: power and a game in exchange for a permanent mark on " +
          "the player's BreathOfKo (his signature written into the fractal save state). " +
          "The mark persists across all subsequent games and is erasable only in Game 18 " +
          "(Mystic Blood) through continuous righteous playthroughs. " +
          "He and Hypatia are peers — both navigating the deep structure of the 9th Ring." },

  // Demi-gods
  { id: "2012_DEMI",  name: "Shapieru",  type: "DEMI", domain: "Shaper of Cultures" },
  { id: "2013_DEMI",  name: "Lanzu",     type: "DEMI", note: "Son of Lakota × Zukoru — divine knowledge and demonic betrayal in one nature" },
  { id: "2014_DEMI",  name: "Tagame",   type: "DEMI", domain: "Life", note: "Daughter of Negaya × Lakota. Kore's lover." },

  // Soldiers
  { id: "2013_SOLD",  name: "Captain Lanvaki",     type: "SOLD" },
  { id: "2014_SOLD",  name: "Sgt. Akande",         type: "SOLD" },
  { id: "2015_SOLD",  name: "Pvt. Kilesha",        type: "SOLD" },

  // Gods (Gaian Lineage from Chaos, all at once, coeval with Primordials)
  { id: "2016_GODS",  name: "Moshize",             type: "GODS",
    domain: "Attainment and Harmony",
    note: "Simultaneously Goddess AND God — the only deity formally mirroring Shygazun dual-aspect." },
  { id: "2017_GODS",  name: "Shakzefan",           type: "GODS",
    domain: "Growth and Loss",
    note: "Canonical spelling: Shakzefan (NOT Shakzebar)" },
  { id: "2018_GODS",  name: "Lakota",              type: "GODS",
    domain: "River of Fire of Sulphera, Wisdom",
    note: "Father of the Salamanders. Fire = clarification-primary, not destruction-primary." },
  { id: "2019_GODS",  name: "Jabiru",              type: "GODS",
    domain: "Stories, Language, Knowledge",
    note: "Shygazun kernel is Jabiru's domain. The byte table is sacred text in his province." },
  { id: "2020_GODS",  name: "Ohadame",             type: "GODS",
    domain: "Past Life Memory",
    note: "Bridges Ko's fresh-dream with accumulated player history when invoked." },
  { id: "2021_GODS",  name: "Ko",                  type: "GODS",
    domain: "Dreams, The Unconscious, The Moon",
    note: "Black Ouroboros, 10 arms, 7 spirals. Assigns VITRIOL stats in dream sequences." },
  { id: "2022_GODS",  name: "Koga",                type: "GODS",
    domain: "Magic and Mystery" },
  { id: "2023_GODS",  name: "Mona",                type: "GODS",
    domain: "Play and Torment",
    note: "Governs Faekin temperament. For Faekin, play IS torment and torment IS play — unified." },
  { id: "2024_GODS",  name: "Zoha",                type: "GODS",
    domain: "Tranquility and Warriordom" },

  // Primordials (5 existential priors + Kael)
  { id: "2025_PRIM",  name: "Ga",                  type: "PRIM" },
  { id: "2026_PRIM",  name: "Na",                  type: "PRIM" },
  { id: "2027_PRIM",  name: "Ha",                  type: "PRIM" },
  { id: "2028_PRIM",  name: "Ung",                 type: "PRIM" },
  { id: "2029_PRIM",  name: "Wu",                  type: "PRIM" },
  { id: "2030_PRIM",  name: "Kael",                type: "PRIM",
    note: "Aether element that reflexively achieves Primordial status." },

  // ANMU — Anima Mundi (World Soul): the three Spirits of the Realms.
  // Each is both the animating spirit of their realm and the realm itself.
  { id: "3001_ANMU",  name: "Lapidus",             type: "ANMU",
    realm: "Overworld",
    note: "Spirit of the Overworld — the animating World Soul of the surface/material realm." },
  { id: "3002_ANMU",  name: "Mercurie",            type: "ANMU",
    realm: "Faewilds",
    note: "Spirit of the Faewilds — the animating World Soul of the orthogonal realm. " +
          "The Faewilds does not sit between Overworld and Underworld; it is perpendicular to that axis entirely." },
  { id: "3003_ANMU",  name: "Sulphera",            type: "ANMU",
    realm: "Underworld",
    note: "Spirit of the Underworld. Realm and spirit are the same entity. " +
          "When Sulphera reads/writes the Orrery it is the World Soul of the Underworld acting as substrate." },
  // Pythia Solunikae — not a pure realm-spirit but born of all three realms' affects,
  // a production of the Primordial drama. ANMU by association, PRIM by association.
  { id: "3004_ANMU",  name: "Pythia Solunikae",    type: "ANMU",
    dual_type: "PRIM",
    realm: null,
    note: "Has touched and been touched by all three realms (Overworld, Faewilds, Underworld). " +
          "Born of all their affects as a production of the Primordial drama. " +
          "Both ANMU and PRIM by association — the only being who holds both." },
];

// ── Items (KLIT) ──────────────────────────────────────────────────────────────
// () prefix = stackable (multiple quantity possible)
// ID groupings:
//   0001-0009  Botanicals / forageables
//   0010-0019  Equipment (weapons, jewelry, generic ingot/coin)
//   0020-0034  Quest items and consumables
//   0035       Health Potion (existing)
//   0036       Map of Mercurie (existing)
//   0040-0049  Typed metal ingots (one per metal — do not stack across types)
//   0050-0059  Typed coins
//   0060-0069  Ammunition and special projectiles
//   0070-0079  Processed materials (recipe outputs from KLOB → KLIT)
export const ITEMS = [
  // ── Botanicals / forageables ────────────────────────────────────────────────
  { id: "0001_KLIT", name: "Cherry",          stackable: true  },
  { id: "0002_KLIT", name: "Apple",           stackable: true  },
  { id: "0003_KLIT", name: "Pomegranate",     stackable: true  },
  { id: "0004_KLIT", name: "Barley",          stackable: true  },
  { id: "0005_KLIT", name: "Pine Needle",     stackable: true  },
  { id: "0006_KLIT", name: "Acorn",           stackable: true  },
  { id: "0007_KLIT", name: "Lotus Flower",    stackable: true  },
  { id: "0008_KLIT", name: "Lotus Seed",      stackable: true  },
  { id: "0009_KLIT", name: "Pine Nut",        stackable: true  },

  // ── Equipment ───────────────────────────────────────────────────────────────
  { id: "0010_KLIT", name: "Necklace",        stackable: false },
  { id: "0011_KLIT", name: "Ring",            stackable: true  },
  { id: "0012_KLIT", name: "Ingot",           stackable: true,
    note: "Generic ingot — use typed ingots (0040-0049) for smelting outputs." },
  { id: "0013_KLIT", name: "Coin",            stackable: true  },
  { id: "0014_KLIT", name: "Dagger",          stackable: true  },
  { id: "0015_KLIT", name: "Sword",           stackable: true  },
  { id: "0016_KLIT", name: "Shield",          stackable: false },
  { id: "0017_KLIT", name: "Bow",             stackable: false },
  { id: "0018_KLIT", name: "Arrow",           stackable: true  },
  { id: "0019_KLIT", name: "Staff",           stackable: true  },

  // ── Quest items and consumables ──────────────────────────────────────────────
  { id: "0021_KLIT", name: "Desire Crystal",  stackable: false,
    note: "Asmodean material. Structurally a time crystal — desire is forward-temporal. " +
          "Swallowing deposits the bearer in the timeline most consonant with their dominant desire. " +
          "In 0009_KLST: offered by the imp in trade for Hypatia's Dagger. Fades to dust after one use." },
  { id: "0022_KLIT", name: "Hypatia's Dagger", stackable: false,
    note: "Forged by Hypatia and left with the player at their first meeting. " +
          "Designed for processing raw reagents. The imp's desired trade item in 0009_KLST." },
  { id: "0023_KLIT", name: "Absinthe",        stackable: false,
    note: "The imp's fallback ask in 0009_KLST. Also craftable via distillation." },
  { id: "0024_KLIT", name: "Wormwood",        stackable: true  },
  { id: "0025_KLIT", name: "Anise",           stackable: true  },
  { id: "0026_KLIT", name: "Fennel",          stackable: true  },
  { id: "0027_KLIT", name: "White Wine",      stackable: false },
  { id: "0028_KLIT", name: "Aqua Vitae",      stackable: false,
    note: "Distilled white wine. Ingredient in Absinthe." },
  { id: "0029_KLIT", name: "Angelic Spear",   stackable: false },
  { id: "0030_KLIT", name: "Angelic Gun",     stackable: false },
  { id: "0031_KLIT", name: "Demonic Irons",   stackable: false },

  // ── Health and alchemy outputs ──────────────────────────────────────────────
  { id: "0035_KLIT", name: "Health Potion",   stackable: false },
  { id: "0036_KLIT", name: "Map of Mercurie", stackable: false,
    note: "Quest reward. Hand-drawn graphite map of Mercurie given by Forest (0007_WTCH)." },

  // ── Typed metal ingots (smelting outputs) ────────────────────────────────────
  { id: "0040_KLIT", name: "Iron Ingot",      stackable: true  },
  { id: "0041_KLIT", name: "Copper Ingot",    stackable: true  },
  { id: "0042_KLIT", name: "Gold Ingot",      stackable: true  },
  { id: "0043_KLIT", name: "Silver Ingot",    stackable: true  },
  { id: "0044_KLIT", name: "Lead Ingot",      stackable: true  },
  { id: "0045_KLIT", name: "Tin Ingot",       stackable: true  },
  { id: "0046_KLIT", name: "Nickel Ingot",    stackable: true  },

  // ── Typed coins ─────────────────────────────────────────────────────────────
  { id: "0050_KLIT", name: "Gold Coin",       stackable: true  },
  { id: "0051_KLIT", name: "Silver Coin",     stackable: true  },
  { id: "0052_KLIT", name: "Copper Coin",     stackable: true  },

  // ── Ammunition ──────────────────────────────────────────────────────────────
  { id: "0060_KLIT", name: "Gold Bullet",     stackable: true,
    note: "For the Colt .45 — the only thing that can kill Sophia." },
  { id: "0061_KLIT", name: "Iron Arrow",      stackable: true  },
  { id: "0062_KLIT", name: "Flint Arrow",     stackable: true  },

  // ── Processed material outputs ───────────────────────────────────────────────
  { id: "0070_KLIT", name: "Gunpowder",       stackable: true,
    note: "Saltpeter + Sulphur + Charcoal ground together. Traditional formula." },

  // ── Electronics (Hack-gated) ─────────────────────────────────────────────────
  { id: "0081_KLIT", name: "Receiver",        stackable: false,
    note: "Crystal radio receiver. Copper coil + Quartz crystal resonator + Wood housing. Hack 35." },
  { id: "0082_KLIT", name: "Transmitter",     stackable: false,
    note: "Signal transmitter. Copper + Iron core + Quartz + Wood. Hack 55." },
  { id: "0083_KLIT", name: "Radio",           stackable: false,
    note: "Full radio unit — Receiver + Transmitter assembled. Hack 80. " +
          "The physical counterpart to St. Alaro's broadcast deal. " +
          "Connects to the Lapidus airwaves infrastructure." },
];

// ── Quests (KLST) ─────────────────────────────────────────────────────────────
// Zero-padded to 4 digits. Format: {####}_KLST
export const QUESTS = [
  { id: "0001_KLST", name: "Fate Knocks" },
  { id: "0002_KLST", name: "Destiny Calls" },
  { id: "0003_KLST", name: "Yellow Brick Road" },
  { id: "0004_KLST", name: "The Golden Path" },
  { id: "0005_KLST", name: "Darker Secrets" },
  { id: "0006_KLST", name: "Twaddlespeak" },
  { id: "0007_KLST", name: "Dream of Glass" },
  { id: "0008_KLST", name: "Bunsen For Hire" },
  { id: "0009_KLST", name: "Demons and Diamonds",
    note: "Unlocked by completing prior quests and establishing sufficient Lapidus market presence " +
          "to have goods smuggled into Sulphera. An unnamed imp visits the player's home shop at " +
          "the witching hour and offers a trade: one Desire Crystal for Hypatia's Dagger. " +
          "Three outcomes: (1) steal the crystal from his corpse — it shatters; " +
          "(2) accept the trade — crystal fades to dust after one use, enough to enter Ring 1 " +
          "(Pride) without Infernal Meditation; " +
          "(3) reject the trade — the imp asks instead for a bottle of absinthe." },
  { id: "0010_KLST", name: "Perfect Circles" },
  { id: "0011_KLST", name: "The Siren Sounds" },
  { id: "0012_KLST", name: "The Mines" },
  { id: "0013_KLST", name: "War Never Changes" },
  { id: "0014_KLST", name: "Bombast" },
  { id: "0015_KLST", name: "Underworld" },
  { id: "0016_KLST", name: "Transcendental" },
  { id: "0017_KLST", name: "Loss, I Fear" },
  { id: "0018_KLST", name: "Growing Pains" },
  { id: "0019_KLST", name: "Wish Upon a Horse" },
  { id: "0020_KLST", name: "Wish Upon a Falling Star" },
  { id: "0021_KLST", name: "Starlight Shows" },
  { id: "0022_KLST", name: "Good Soldiers" },
  { id: "0023_KLST", name: "Mercenary Type" },
  { id: "0024_KLST", name: "Death Hallows" },
  { id: "0025_KLST", name: "Assassination" },
  { id: "0026_KLST", name: "Good Grief" },
  { id: "0027_KLST", name: "Echoes of the Past" },
  { id: "0028_KLST", name: "A Haunting Notion" },
  { id: "0029_KLST", name: "Doom and Gloom" },
  { id: "0030_KLST", name: "Plasma Freeze" },
  { id: "0031_KLST", name: "Master Koga" },
  { id: "0032_KLST", name: "Mona Lisa" },
  { id: "0033_KLST", name: "Zoha are" },
  { id: "0034_KLST", name: "Children? By Atom!" },
  { id: "0035_KLST", name: "Choices in Hell" },
  { id: "0036_KLST", name: "Consequence" },
  { id: "0037_KLST", name: "Witching Hour" },
  { id: "0038_KLST", name: "Wild Things" },
  { id: "0039_KLST", name: "Storybook" },
  { id: "0040_KLST", name: "Priceless" },
  { id: "0041_KLST", name: "Poisons and Lectures" },
  { id: "0042_KLST", name: "Meaning Less" },
  { id: "0043_KLST", name: "Less is More" },
  { id: "0044_KLST", name: "Voracity" },
  { id: "0045_KLST", name: "Good old .45" },
  { id: "0046_KLST", name: "Most Obscenities" },
  { id: "0047_KLST", name: "Shaped Charge" },
  { id: "0048_KLST", name: "De Lucion" },
  { id: "0049_KLST", name: "Had Me in the First Half" },
  { id: "0050_KLST", name: "Prophet of Ko" },
  { id: "0051_KLST", name: "Eclipse!" },
  { id: "0052_KLST", name: "The Abyss" },
  { id: "0053_KLST", name: "Chosen Dues" },
  { id: "0054_KLST", name: "Stolen Valor" },
  { id: "0055_KLST", name: "Ring-a-Ding-Ding" },
  { id: "0056_KLST", name: "Priestly Affair" },
  { id: "0057_KLST", name: "Fairly, a Priestess" },
  { id: "0058_KLST", name: "Rouse The Depths" },
  { id: "0059_KLST", name: "The Woods" },
  { id: "0060_KLST", name: "In Service To Starlight" },
  { id: "0061_KLST", name: "Ko's Great Tale" },
];

// ── Recipes ───────────────────────────────────────────────────────────────────
// Each recipe: { output, ingredients: [string, ...], note? }
// Ingredients are item names matching entries in ITEMS.
export const RECIPES = [
  {
    output:      "Absinthe",
    ingredients: ["Wormwood", "Anise", "Fennel", "Aqua Vitae"],
    note: "Required for the absinthe-path resolution of 0009_KLST (Demons and Diamonds) " +
          "if the Desire Crystal trade is rejected.",
  },
  {
    output:      "Aqua Vitae",
    ingredients: ["White Wine"],
    note: "Distilled white wine. Base spirit for Absinthe.",
  },
];

export const RECIPE_BY_OUTPUT = Object.fromEntries(RECIPES.map(r => [r.output, r]));

// ── Lookup helpers ────────────────────────────────────────────────────────────

export const CHARACTER_BY_ID   = Object.fromEntries(CHARACTERS.filter(c => c.id).map(c => [c.id, c]));
export const CHARACTER_BY_NAME = Object.fromEntries(CHARACTERS.map(c => [c.name, c]));
export const QUEST_BY_ID       = Object.fromEntries(QUESTS.map(q => [q.id, q]));
export const QUEST_BY_NAME     = Object.fromEntries(QUESTS.map(q => [q.name, q]));
export const ITEM_BY_NAME      = Object.fromEntries(ITEMS.map(i => [i.name, i]));
export const OBJECT_BY_NAME    = Object.fromEntries(OBJECTS.map(o => [o.name, o]));

/**
 * Return all characters of a given type code.
 * Includes characters whose dual_type matches when includeDual is true.
 * @param {string} type        — e.g. "WTCH", "ROYL", "VDWR", "HIST"
 * @param {boolean} includeDual — also match dual_type field (default true)
 */
export function charactersByType(type, includeDual = true) {
  return CHARACTERS.filter(c =>
    c.type === type || (includeDual && c.dual_type === type)
  );
}

/** All known TYPE codes — use to validate incoming character type strings. */
export const KNOWN_TYPES = new Set([
  "test", "HIST", "TOWN", "WTCH", "PRST", "ASSN", "ROYL",
  "GNOM", "NYMP", "UNDI", "SALA", "DRYA", "DJNN",
  "VDWR", "DMON", "DEMI", "SOLD", "GODS", "PRIM", "ANMU",
]);

/** The 3 Void Wraiths, keyed by their observes field. */
export const VOID_WRAITH_BY_OBSERVATION = Object.fromEntries(
  charactersByType("VDWR").map(c => [c.observes, c])
);

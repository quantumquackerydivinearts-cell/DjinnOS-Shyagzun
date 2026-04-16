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
export const OBJECTS = [
  { id: "8000_KLOB", name: "Mortar",           default_trait: 0 },
  { id: "2000_KLOB", name: "Pestle",           default_trait: 1 },
  { id: null,        name: "Rag",              default_trait: null },
  { id: null,        name: "Stand",            default_trait: null },
  { id: null,        name: "Retort",           default_trait: null },
  { id: null,        name: "Volume Flask",     default_trait: null },
  { id: null,        name: "Reagent Bottle",   default_trait: null },
  { id: null,        name: "Sand",             default_trait: null },
  { id: null,        name: "Refined Sand",     default_trait: null },
  { id: null,        name: "Furnace",          default_trait: null },
  { id: null,        name: "Wooden Spoon",     default_trait: null },
  { id: null,        name: "Copper Spoon",     default_trait: null },
  { id: null,        name: "Iron Spoon",       default_trait: null },
  { id: null,        name: "Steel Spoon",      default_trait: null },
  { id: null,        name: "Granite Spoon",    default_trait: null },
  { id: null,        name: "Bellows",          default_trait: null },
  { id: null,        name: "Crucible",         default_trait: null },
  { id: null,        name: "Bottle",           default_trait: null },
  { id: null,        name: "Jar",              default_trait: null },
  { id: null,        name: "Diatom Earth",     default_trait: null },
  { id: null,        name: "Glycerine",        default_trait: null },
  { id: null,        name: "Petrolium Jelly",  default_trait: null },
  { id: null,        name: "Saltpeter",        default_trait: null },
  { id: null,        name: "Sulphur",          default_trait: null },
  { id: null,        name: "Charcoal",         default_trait: null },
  { id: null,        name: "Tin",              default_trait: null },
  { id: null,        name: "Iron",             default_trait: null },
  { id: null,        name: "Gold",             default_trait: null },
  { id: null,        name: "Copper",           default_trait: null },
  { id: null,        name: "Mercury",          default_trait: null },
  { id: null,        name: "Silver",           default_trait: null },
  { id: null,        name: "Lead",             default_trait: null },
  { id: null,        name: "Nickel",           default_trait: null },
  { id: null,        name: "Cyanide",          default_trait: null },
  { id: null,        name: "Ashes",            default_trait: null },
  { id: null,        name: "Caustic Lye",      default_trait: null },
  { id: null,        name: "Potassium",        default_trait: null },
  { id: null,        name: "Phosphorus",       default_trait: null },
  { id: null,        name: "Arsenic",          default_trait: null },
  { id: null,        name: "Water",            default_trait: null },
  { id: null,        name: "Wood",             default_trait: null },
  { id: null,        name: "Flint",            default_trait: null },
  { id: null,        name: "Shark Tooth",      default_trait: null },
  { id: null,        name: "Granite",          default_trait: null },
  { id: null,        name: "Obsidian",         default_trait: null },
  { id: null,        name: "Chalk",            default_trait: null },
  { id: null,        name: "Gypsum",           default_trait: null },
  { id: null,        name: "Quartz",           default_trait: null },
  { id: null,        name: "Pumice",           default_trait: null },
  { id: null,        name: "Amythest",         default_trait: null },
  { id: null,        name: "Ruby",             default_trait: null },
  { id: null,        name: "Sapphire",         default_trait: null },
  { id: null,        name: "Emerald",          default_trait: null },
  { id: null,        name: "Diamond",          default_trait: null },
  { id: null,        name: "Jade",             default_trait: null },
  { id: null,        name: "Crucible Tongs",   default_trait: null },
  { id: null,        name: "Ring Mold",        default_trait: null },
  { id: null,        name: "Ingot Mold",       default_trait: null },
  { id: null,        name: "Anvil",            default_trait: null },
  { id: null,        name: "Hammer",           default_trait: null },
  { id: null,        name: "Lathe Chuck",      default_trait: null },
  { id: null,        name: "Lathe",            default_trait: null },
  { id: null,        name: "Chizel",           default_trait: null },
  { id: null,        name: "Ring Blank",       default_trait: null },
  { id: null,        name: "Moldavite",        default_trait: null },
  { id: null,        name: "Desert Glass",     default_trait: null },
  { id: null,        name: "Pearl",            default_trait: null },
  { id: null,        name: "Black Pearl",      default_trait: null },
  { id: null,        name: "Pulp",             default_trait: null },
  { id: null,        name: "Paper",            default_trait: null },
  { id: null,        name: "Ink",              default_trait: null },
  { id: null,        name: "Pen",              default_trait: null },
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
  { id: "0001_TOWN",  name: "Joannah",             type: "TOWN" },
  { id: "0002_TOWN",  name: "Wells",               type: "TOWN" },
  { id: "0003_TOWN",  name: "Lavelle",             type: "TOWN" },
  { id: "0004_TOWN",  name: "Sidhal",              type: "TOWN" },

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
  { id: "2010_DMON",  name: "St. Alaro",           type: "DMON",
    alias: "Alastor",
    note: "The Radio Demon of Pride. Operating in Aeralune under the alias St. Alaro. " +
          "Encountered through the secret ending arc — not a traversal-path NPC. " +
          "Offers a Faustian pact: power and a game in exchange for a permanent mark on " +
          "the player's BreathOfKo (his signature written into the fractal save state). " +
          "The mark persists across all subsequent games and is erasable only in Game 18 " +
          "(Mystic Blood) through continuous righteous playthroughs. " +
          "He and Hypatia are peers — both navigating the deep structure of the 9th Ring." },

  // Demi-gods
  { id: "2010_DEMI",  name: "Shapieru",            type: "DEMI" },
  { id: "2011_DEMI",  name: "Lanzu",               type: "DEMI" },
  { id: "2012_DEMI",  name: "Tagame",              type: "DEMI" },

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
export const ITEMS = [
  { id: "0035_KLIT", name: "Health Potion",  stackable: false },
  { id: null,        name: "Cherry",         stackable: false },
  { id: null,        name: "Apple",          stackable: false },
  { id: null,        name: "Pomegranate",    stackable: false },
  { id: null,        name: "Barley",         stackable: false },
  { id: null,        name: "Pine Needle",    stackable: false },
  { id: null,        name: "Acorn",          stackable: false },
  { id: null,        name: "Lotus Flower",   stackable: false },
  { id: null,        name: "Lotus Seed",     stackable: false },
  { id: null,        name: "Pine Nut",       stackable: false },
  { id: null,        name: "Necklace",       stackable: false },
  { id: null,        name: "Ring",           stackable: true  },   // ()Ring
  { id: null,        name: "Ingot",          stackable: true  },   // ()Ingot
  { id: null,        name: "Coin",           stackable: true  },   // ()Coin
  { id: null,        name: "Dagger",         stackable: true  },   // ()Dagger
  { id: null,        name: "Sword",          stackable: true  },   // ()Sword
  { id: null,        name: "Shield",         stackable: false },
  { id: null,        name: "Bow",            stackable: false },
  { id: null,        name: "Arrow",          stackable: true  },   // ()Arrow
  { id: null,        name: "Staff",          stackable: true  },   // ()Staff
  { id: null,        name: "Desire Crystal", stackable: false,
    note: "Asmodean material. Structurally a time crystal — desire is forward-temporal. " +
          "Swallowing deposits the bearer in the timeline most consonant with their dominant desire. " +
          "In 0009_KLST: offered by the imp in trade for Hypatia's Dagger. Fades to dust after one use " +
          "— sufficient for a single entry into Ring 1 (Pride) without Infernal Meditation. " +
          "If stolen instead of traded, it shatters on the imp's corpse." },
  { id: null,        name: "Hypatia's Dagger", stackable: false,
    note: "Forged by Hypatia and left with the player at their first meeting. " +
          "Designed for processing raw reagents. The imp's desired trade item in 0009_KLST." },
  { id: null,        name: "Absinthe",      stackable: false,
    note: "The imp's fallback ask in 0009_KLST if the Desire Crystal trade is rejected." },
  { id: null,        name: "Wormwood",      stackable: true },
  { id: null,        name: "Anise",         stackable: true },
  { id: null,        name: "Fennel",        stackable: true },
  { id: null,        name: "White Wine",    stackable: false },
  { id: null,        name: "Aqua Vitae",    stackable: false,
    note: "Distilled white wine. Brandy of white wine. Ingredient in Absinthe." },
  { id: null,        name: "Angelic Spear",  stackable: false },
  { id: null,        name: "Angelic Gun",    stackable: false },
  { id: null,        name: "Demonic Irons",  stackable: false },
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
 * @param {string} type  — e.g. "WTCH", "ROYL", "VDWR"
 */
export function charactersByType(type) {
  return CHARACTERS.filter(c => c.type === type);
}

/** The 3 Void Wraiths, keyed by their observes field. */
export const VOID_WRAITH_BY_OBSERVATION = Object.fromEntries(
  charactersByType("VDWR").map(c => [c.observes, c])
);

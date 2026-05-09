// Ko's Labyrnth character registry — AgentDef entries for all characters.
//
// Each entry encodes:
//   tongue_gate   — min Quack count for half-capability (from entity type)
//   max_layer     — coil depth ceiling (from entity_max_layer())
//   mobius_close  — whether the coil closes on itself
//   domain_addrs  — Shygazun byte addresses defining knowledge domain
//   kind_affinity — 9-value affinity vector per InteractionKind
//
// kind_affinity index:
//   0=Dialogue  1=TeachSkill  2=QuestOffer  3=QuestAdvance  4=QuestComplete
//   5=Combat    6=LoreAccess  7=MeditationGuide  8=Trade
//
// Domain addresses are curated byte table positions reflecting each
// character's knowledge register.  They become the hidden-layer nodes
// (Layer 5 — Object) that the coil attends to.

use crate::agent::{AgentDef, register};

// ── Shared domain address sets ─────────────────────────────────────────────────

// Lotus base (bytes 0-23): available to every entity with a body
static DOM_LOTUS: &[u32] = &[0,1,2,3,4,5,6,7,8,9,19,20];
// Rose spectrum (bytes 24-47): entities with spectral awareness
static DOM_ROSE:  &[u32] = &[24,25,26,27,28,29,30,31,32,45];
// Sakura spatial (48-71): directional/spatial specialists
static DOM_SAKU:  &[u32] = &[48,49,50,51,52,53,54,55,56,57,58,59,66,67];
// Daisy structural (72-97): engineers, architects, networkers
static DOM_DAIS:  &[u32] = &[72,82,83,84,85,86,87,88,89,97];
// AppleBlossom elemental (98-123): alchemists, witches, elemental workers
static DOM_APBL:  &[u32] = &[98,99,100,101,102,103,104,105,106,107,108,110,111];
// Aster time/space (128-155): time-sensitive entities
static DOM_ASTE:  &[u32] = &[128,134,135,141,142,143,144,145,146,147,148,155];
// Grapevine file/network (156-183): information brokers
static DOM_VINE:  &[u32] = &[156,157,158,159,163,164,165,166,167,169];
// Cannabis consciousness (184-213): consciousness workers
static DOM_CANN:  &[u32] = &[184,185,186,187,188,189,190,193,194,203,204,213];
// Dragon void organisms (256-285): void-knowers
static DOM_DRAG:  &[u32] = &[256,257,258,259,260,261,266,267,268,276,277,278];
// Dragon mental void specifically
static DOM_DRAG_MIND: &[u32] = &[256,257,258,259,260,261,262,263,264,265];
// Dragon spatial void
static DOM_DRAG_SPAT: &[u32] = &[266,267,268,269,270,271,272,273,274,275];
// Dragon temporal void
static DOM_DRAG_TIME: &[u32] = &[276,277,278,279,280,281,282,283,284,285];

// ── Character definitions ──────────────────────────────────────────────────────

// ─── Protagonist ──────────────────────────────────────────────────────────────

static DOM_HYPATIA: &[u32] = &[
    0,4,8,9,19,45,82,98,104,106,107,142,156,157,193,203,213,
];
static DEF_HYPATIA: AgentDef = AgentDef {
    entity_id: b"0000_0451", name: b"Alexandria Hypatia",
    notes: b"Protagonist/Player character",
    tongue_gate: 0, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_HYPATIA,
    kind_affinity: [128,128,128,200,200,80,200,200,80],
};

// ─── Townfolk (gate 1, layer 4) ───────────────────────────────────────────────

static DOM_JOANNAH: &[u32] = &[0,4,8,9,19,45,159,163,164]; // caravan/crypto/art
static DEF_JOANNAH: AgentDef = AgentDef {
    entity_id: b"0001_TOWN", name: b"Joannah",
    notes: b"Caravan Dispatcher, Cryptographer, Artist, Mother of 3 (32)",
    tongue_gate: 1, max_layer: 4, mobius_close: false,
    domain_addrs: DOM_JOANNAH,
    kind_affinity: [200,60,120,180,180,30,120,40,80],
};

static DOM_WELLS: &[u32] = &[0,72,85,86,87,88,89,148,155]; // aqueduct/engineer
static DEF_WELLS: AgentDef = AgentDef {
    entity_id: b"0002_TOWN", name: b"Wells",
    notes: b"Aqueduct Foreman, engineer, father of 6 (38)",
    tongue_gate: 1, max_layer: 4, mobius_close: false,
    domain_addrs: DOM_WELLS,
    kind_affinity: [180,60,120,180,180,30,80,30,60],
};

static DOM_LAVELLE: &[u32] = &[0,9,107,108,111,23,45,157]; // explosives/bookworm
static DEF_LAVELLE: AgentDef = AgentDef {
    entity_id: b"0003_TOWN", name: b"Lavelle",
    notes: b"Laundry worker, explosive hobbyist, bookworm, mother of 2 (23)",
    tongue_gate: 1, max_layer: 4, mobius_close: false,
    domain_addrs: DOM_LAVELLE,
    kind_affinity: [200,80,120,180,180,60,140,40,60],
};

static DOM_SIDHAL: &[u32] = &[0,2,3,6,7,8,9,48,50]; // farmer/forester/temple
static DEF_SIDHAL: AgentDef = AgentDef {
    entity_id: b"0004_TOWN", name: b"Sidhal",
    notes: b"Farmer, Forester, Temple Custodian, Father of 2 (26)",
    tongue_gate: 1, max_layer: 4, mobius_close: false,
    domain_addrs: DOM_SIDHAL,
    kind_affinity: [200,60,160,180,180,40,80,60,80],
};

// ─── Witches (gate 4 / Daisy register, layer 6) ───────────────────────────────

static DOM_KORE: &[u32] = &[
    9,19,82,98,99,104,106,184,186,193,203, // life witch / Ko devotee
];
static DEF_KORE: AgentDef = AgentDef {
    entity_id: b"0005_WTCH", name: b"Kore",
    notes: b"Life witch, Transfemme, Ko Devotee, Lesbian Lover of Tagame (30)",
    tongue_gate: 4, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_KORE,
    kind_affinity: [220,180,120,160,160,60,180,220,40],
};

static DOM_ALFIR: &[u32] = &[
    9,19,82,104,107,256,257,258,261,262, // cosmic witch / daemonologist
    184,186,188,193,                      // cannabis register — infernal meditation
];
static DEF_ALFIR: AgentDef = AgentDef {
    entity_id: b"0006_WTCH", name: b"Alfir",
    notes: b"Elderly man, Old Earth Persian descent. Cosmic Witch, Former priest, Daemonologist (50)",
    tongue_gate: 4, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_ALFIR,
    kind_affinity: [180,240,100,160,160,80,220,255,40],
};

static DOM_FOREST: &[u32] = &[
    0,2,3,6,7,9,48,66,67,84,85,97,106, // nature wizard / dryad obsessed
];
static DEF_FOREST: AgentDef = AgentDef {
    entity_id: b"0007_WTCH", name: b"Forest",
    notes: b"Dryad obsessed Nature Wizard, Gay (27)",
    tongue_gate: 4, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_FOREST,
    kind_affinity: [200,160,100,160,160,60,200,180,40],
};

// ─── Priests (gate 3 / Sakura register, layer 6) ─────────────────────────────

static DOM_SAFFRON: &[u32] = &[
    9,16,17,18,19,48,50,52,54,56,82, // purple robe / Nexiott's priest
];
static DEF_SAFFRON: AgentDef = AgentDef {
    entity_id: b"0008_PRST", name: b"Saffron",
    notes: b"Purple robe, red wings, Menace to Nature, Nexiott's Priest (72)",
    tongue_gate: 3, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_SAFFRON,
    kind_affinity: [200,80,180,200,200,80,200,120,40],
};

static DOM_LUCION: &[u32] = &[
    9,45,82,106,107,156,157,158,159, // ceramics/cryptography/medicine/library
    98,99,100,101,102,103,
];
static DEF_LUCION: AgentDef = AgentDef {
    entity_id: b"0009_PRST", name: b"Lucion",
    notes: b"Ceramics, cryptography, medicine, chemistry, Librarian (35), Jabiru Priest",
    tongue_gate: 3, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_LUCION,
    kind_affinity: [200,160,120,160,160,40,240,120,60],
};

static DOM_RACHELLE: &[u32] = &[
    9,14,15,48,50,52,54,56,82,156, // Shakzefan priestess / advisor
];
static DEF_RACHELLE: AgentDef = AgentDef {
    entity_id: b"0010_PRST", name: b"Rachelle",
    notes: b"Alfir's Replacement, Advisor to Chancellor Kelly, Shakzefan Priestess (35)",
    tongue_gate: 3, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_RACHELLE,
    kind_affinity: [200,140,160,200,200,40,200,160,40],
};

// ─── Assassins (gate 6 / Aster register, layer 6) ────────────────────────────

static DOM_HUE: &[u32] = &[
    9,19,128,134,141,142,143,145,146, // student of Sophia / haunted by Po'Elfan
];
static DEF_HUE: AgentDef = AgentDef {
    entity_id: b"0011_ASSN", name: b"Hue",
    notes: b"Student of Sophia, Haunted by Po'elfan, Kore's brother (24)",
    tongue_gate: 6, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_HUE,
    kind_affinity: [180,100,140,180,180,140,160,120,40],
};

static DOM_CYRUS: &[u32] = &[
    9,12,13,14,15,16,17,18,19,48,50,52, // disguise expert
];
static DEF_CYRUS: AgentDef = AgentDef {
    entity_id: b"0012_ASSN", name: b"Cyrus",
    notes: b"Student of Lectura, disguise expert, blue hair (20)",
    tongue_gate: 6, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_CYRUS,
    kind_affinity: [180,100,160,200,200,160,140,80,40],
};

static DOM_ASMOTH: &[u32] = &[
    9,19,48,52,54,56,128,134,142, // child of the Fae
];
static DEF_ASMOTH: AgentDef = AgentDef {
    entity_id: b"0013_ASSN", name: b"Asmoth",
    notes: b"Child of the Fae, orphaned by Kielum's war (29)",
    tongue_gate: 6, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_ASMOTH,
    kind_affinity: [180,100,140,180,180,160,160,100,40],
};

// ─── Royals (gate 2 / Rose register, layer 6) ─────────────────────────────────

static DOM_KELLY: &[u32] = &[
    9,14,15,24,29,30,45,82,156,157, // chancellor / talks to angels
];
static DEF_KELLY: AgentDef = AgentDef {
    entity_id: b"0014_ROYL", name: b"Chancellor Kelly",
    notes: b"Oldest in Castle AZoth, talks to angels (38)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_KELLY,
    kind_affinity: [200,80,200,220,220,40,200,120,60],
};

static DOM_BOMBASTUS: &[u32] = &[
    9,15,24,25,26,27,28,29,30,45,82, // king / Rose spectral
];
static DEF_BOMBASTUS: AgentDef = AgentDef {
    entity_id: b"0015_ROYL", name: b"King Bombastus",
    notes: b"Father from FMAb, but lost as Van Hoenhiem. (58)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_BOMBASTUS,
    kind_affinity: [180,60,200,220,220,100,180,100,80],
};

static DOM_HILDEGARDE: &[u32] = &[
    9,14,15,24,45,156,157,159,163,164, // scholar queen / linguistics
];
static DEF_HILDEGARDE: AgentDef = AgentDef {
    entity_id: b"0016_ROYL", name: b"Queen Hildegarde",
    notes: b"Scholar Queen, stressed mother, linguistics lover (49)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_HILDEGARDE,
    kind_affinity: [200,160,180,200,200,40,240,120,60],
};

static DOM_NEXIOTT: &[u32] = &[
    9,15,16,17,82,163,164,165,167,169, // propagandist / caravan boss
];
static DEF_NEXIOTT: AgentDef = AgentDef {
    entity_id: b"0017_ROYL", name: b"Lord Nexiott",
    notes: b"Corona Caravans Boss, Propagandist (52)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_NEXIOTT,
    kind_affinity: [160,60,200,220,220,80,180,80,120],
};

static DOM_EOMANN: &[u32] = &[
    9,15,45,48,52,54,56,82,156, // devoted to Bombastus / sworn to Fae
];
static DEF_EOMANN: AgentDef = AgentDef {
    entity_id: b"0018_ROYL", name: b"Duke Eomann",
    notes: b"Devoted to Bombastus, Sworn to the Fae, (56)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_EOMANN,
    kind_affinity: [200,60,180,200,200,80,160,100,60],
};

static DOM_LUMINYX: &[u32] = &[
    9,19,24,25,26,27,28,29,30,45,193, // protagonist of Book 1 / royal heir
];
static DEF_LUMINYX: AgentDef = AgentDef {
    entity_id: b"0019_ROYL", name: b"Princess Luminyx",
    notes: b"Protagonist of Book 1 -- spelling: Luminyx; Royal Heir (sole); Pivotal character (22)",
    tongue_gate: 2, max_layer: 6, mobius_close: false,
    domain_addrs: DOM_LUMINYX,
    kind_affinity: [220,100,180,220,220,80,200,140,80],
};

// ─── Gnomes (gate 9 / Dragon register, layer 8) ───────────────────────────────

static DOM_CLINT: &[u32] = &[
    48,49,50,51,72,82,107,266,267,268, // miner/geologist/jeweler/Lapidus
];
static DEF_CLINT: AgentDef = AgentDef {
    entity_id: b"1001_GNOM", name: b"Clint",
    notes: b"Miner, Geologist, Jeweler, Geomancer, Follower of Lapidus",
    tongue_gate: 9, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_CLINT,
    kind_affinity: [180,160,140,180,180,60,180,80,120],
};

static DOM_GNOLAN: &[u32] = &[
    48,50,52,72,82,84,85,86,87,148, // architect / Mercurie follower
];
static DEF_GNOLAN: AgentDef = AgentDef {
    entity_id: b"1002_GNOM", name: b"Gnolan",
    notes: b"Architect, Friend of Eomann, Follower of Mercurie",
    tongue_gate: 9, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_GNOLAN,
    kind_affinity: [180,160,140,180,180,60,180,80,100],
};

static DOM_WINNONA: &[u32] = &[
    72,82,107,108,111,104,105,266,267, // metallurgist / machinist / Sulphera
];
static DEF_WINNONA: AgentDef = AgentDef {
    entity_id: b"1003_GNOM", name: b"Winnona",
    notes: b"Metallurgist and Machinist, Follower of Sulphera",
    tongue_gate: 9, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_WINNONA,
    kind_affinity: [180,180,120,180,180,80,160,80,140],
};

// ─── Nymphs / Fae (gate 11 / Bacteria register, layer 8) ─────────────────────

static DOM_AMELIA: &[u32] = &[
    9,19,45,48,52,54,56,82,98,193, // Fae Queen / chaos mage
];
static DEF_AMELIA: AgentDef = AgentDef {
    entity_id: b"1004_NYMP", name: b"Amelia",
    notes: b"Fae Queen, beefs w/ Tymona, Muse of Echo, Chaos Mage",
    tongue_gate: 11, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_AMELIA,
    kind_affinity: [220,100,180,200,200,100,200,160,60],
};

static DOM_ECHO: &[u32] = &[
    9,19,45,82,98,99,193,203,204,213, // artisan/alchemist/Ko's disciple/poet
];
static DEF_ECHO: AgentDef = AgentDef {
    entity_id: b"1005_NYMP", name: b"Echo",
    notes: b"Artisan, Alchemist, Ko's Disciple, Poet, Chaos magic user, Zoha Devotee",
    tongue_gate: 11, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_ECHO,
    kind_affinity: [220,140,120,180,180,80,220,160,60],
};

static DOM_KARLIA: &[u32] = &[
    9,48,52,54,56,82,128,134,142, // guardian / deep blue wings
];
static DEF_KARLIA: AgentDef = AgentDef {
    entity_id: b"1006_NYMP", name: b"Karlia",
    notes: b"Fae, Guardian, Deep blue wings, Chaos magic user",
    tongue_gate: 11, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_KARLIA,
    kind_affinity: [180,80,120,160,160,160,160,120,40],
};

// ─── Undines (gate 10 / Virus register, layer 8) ─────────────────────────────

static DOM_SOPHIA: &[u32] = &[
    9,19,82,98,99,102,103,193,256,257,258, // soul of the depths / red & black
];
static DEF_SOPHIA: AgentDef = AgentDef {
    entity_id: b"1007_UNDI", name: b"Sophia",
    notes: b"Red & black w/ silver scaling, Soul of the Depths",
    tongue_gate: 10, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_SOPHIA,
    kind_affinity: [220,140,100,180,180,80,240,200,40],
};

static DOM_LECTURA: &[u32] = &[
    9,19,82,106,107,156,157,193, // green & yellow / venom of tides / Mona devotee
];
static DEF_LECTURA: AgentDef = AgentDef {
    entity_id: b"1008_UNDI", name: b"Lectura",
    notes: b"Green & yellow scales, Venom of Tides, Mona devotee",
    tongue_gate: 10, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_LECTURA,
    kind_affinity: [200,160,100,180,180,80,220,180,40],
};

static DOM_FAYGORU: &[u32] = &[
    9,19,82,142,143,144,145,146,147,193,276,278, // time traveler / Ohadame devotee
];
static DEF_FAYGORU: AgentDef = AgentDef {
    entity_id: b"1009_UNDI", name: b"Faygoru",
    notes: b"Gold & turquoise scales, Time traveler, Ohadame devotee",
    tongue_gate: 10, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_FAYGORU,
    kind_affinity: [200,140,100,180,180,60,240,220,40],
};

// ─── Salamanders (gate 12 / Excavata register, layer 8) ──────────────────────

static DOM_CHAZAK: &[u32] = &[
    9,17,19,82,142,143,144,145,146,147,193, // Greater Siren / transcendental
];
static DEF_CHAZAK: AgentDef = AgentDef {
    entity_id: b"1010_SALA", name: b"Chazak",
    notes: b"Greater Siren, Zen af, Transcendental Meditator, Moshize Devotee",
    tongue_gate: 12, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_CHAZAK,
    kind_affinity: [220,200,80,160,160,40,220,255,40],
};

static DOM_AXIOZUL: &[u32] = &[
    9,19,82,142,146,147,193,276,277,278,279,280, // axolotl / timeless / immortal
];
static DEF_AXIOZUL: AgentDef = AgentDef {
    entity_id: b"1011_SALA", name: b"Axiozul",
    notes: b"Axolotl (blue), Timeless, Immortal, Child of Lakota",
    tongue_gate: 12, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_AXIOZUL,
    kind_affinity: [200,120,80,160,160,60,240,200,40],
};

static DOM_SAVVI: &[u32] = &[
    9,19,82,104,107,108,111,266,267, // cosmic arms dealer / child of Vios+Drovitth
];
static DEF_SAVVI: AgentDef = AgentDef {
    entity_id: b"1012_SALA", name: b"Savvi",
    notes: b"Fire Salamander, Child of Vios and Drovitth, Cosmic Arms Dealer, Bane of Misfortune",
    tongue_gate: 12, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_SAVVI,
    kind_affinity: [160,80,160,180,180,200,160,80,200],
};

// ─── Dryads (gate 13 / Archaeplastida register, layer 8) ─────────────────────

static DOM_EUKALA: &[u32] = &[
    0,1,6,7,9,48,52,54,82,107, // hunter / honors death
];
static DEF_EUKALA: AgentDef = AgentDef {
    entity_id: b"1013_DRYA", name: b"Eukala",
    notes: b"Constantly hunting, honors death, 8'ky+, ageless, LN",
    tongue_gate: 13, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_EUKALA,
    kind_affinity: [160,80,120,160,160,220,160,80,40],
};

static DOM_TYMONA: &[u32] = &[
    0,1,6,7,9,48,52,54,82, // hates humans / sadism / godless
];
static DEF_TYMONA: AgentDef = AgentDef {
    entity_id: b"1014_DRYA", name: b"Tymona",
    notes: b"Hates humans, full of sadism, 6ft+, 40s, godless CN",
    tongue_gate: 13, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_TYMONA,
    kind_affinity: [140,60,80,140,140,240,140,60,40],
};

static DOM_VAJIL: &[u32] = &[
    0,2,6,9,48,52,54,82,84,85, // great oak dryad / titanium bark
];
static DEF_VAJIL: AgentDef = AgentDef {
    entity_id: b"1015_DRYA", name: b"Vajil",
    notes: b"Great Oak dryad, Titanium Bark, gay, CG",
    tongue_gate: 13, max_layer: 8, mobius_close: false,
    domain_addrs: DOM_VAJIL,
    kind_affinity: [200,120,120,160,160,120,180,120,60],
};

// ─── Djinn (gate 9 / Dragon register, layer 10 — Names layer) ────────────────

static DOM_GIANN: &[u32] = &[
    9,19,45,82,98,104,193,256,257,258,261,266, // Heart of Kael / Benefactor
];
static DEF_GIANN: AgentDef = AgentDef {
    entity_id: b"1016_DJNN", name: b"Giann",
    notes: b"Heart of Kael, Benefactor of All, CG",
    tongue_gate: 9, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_GIANN,
    kind_affinity: [220,120,180,200,200,60,220,160,80],
};

static DOM_KESHI: &[u32] = &[
    0,1,6,7,9,82,256,257,258,266,276, // Gift Horse / Destroyer of Growth
];
static DEF_KESHI: AgentDef = AgentDef {
    entity_id: b"1017_DJNN", name: b"Keshi",
    notes: b"Gift Horse, Destroyer of Growth, CE",
    tongue_gate: 9, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_KESHI,
    kind_affinity: [160,100,180,180,180,160,180,100,120],
};

static DOM_DROVITTH: &[u32] = &[
    9,19,45,82,142,143,156,157,256,261,266,276, // built the Orrery / Astrologer
];
static DEF_DROVITTH: AgentDef = AgentDef {
    entity_id: b"1018_DJNN", name: b"Drovitth",
    notes: b"Astrologer, Watcher of Life, LN -- builder of the Orrery",
    tongue_gate: 9, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_DROVITTH,
    kind_affinity: [200,160,100,180,180,40,240,160,60],
};

// ─── Void Wraiths (gate 22 / Chimera register, layer 11 — Scene) ─────────────

static DEF_HALDORO: AgentDef = AgentDef {
    entity_id: b"2001_VDWR", name: b"Haldoro",
    notes: b"Void Wraith - Knower of Minds",
    tongue_gate: 22, max_layer: 11, mobius_close: false,
    domain_addrs: DOM_DRAG_MIND,
    kind_affinity: [220,60,60,120,120,140,255,120,20],
};

static DEF_VIOS: AgentDef = AgentDef {
    entity_id: b"2002_VDWR", name: b"Vios",
    notes: b"Void Wraith - Knower of Souls",
    tongue_gate: 22, max_layer: 11, mobius_close: false,
    domain_addrs: DOM_DRAG_SPAT,
    kind_affinity: [210,60,60,120,120,160,255,120,20],
};

static DEF_NEGAYA: AgentDef = AgentDef {
    entity_id: b"2003_VDWR", name: b"Negaya",
    notes: b"Void Wraith - Knower of Bodies",
    tongue_gate: 22, max_layer: 11, mobius_close: false,
    domain_addrs: DOM_DRAG_TIME,
    kind_affinity: [200,60,60,120,120,180,255,120,20],
};

// ─── Demons (gate 17 / Immune register, layer 9 — Pattern) ───────────────────

static DOM_OTHEIRU: &[u32] = &[
    0,1,6,7,256,260,261,266,276, // Blood Ball / Demon of Abandon
];
static DEF_OTHEIRU: AgentDef = AgentDef {
    entity_id: b"2004_DMON", name: b"Otheiru",
    notes: b"'Blood Ball', Made of Lost life, massive, voracious, Demon of Abandon",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_OTHEIRU,
    kind_affinity: [120,40,60,100,100,255,160,60,20],
};

static DOM_KIELUM: &[u32] = &[
    0,1,15,16,17,82,163,164,165,256, // Conquest / Demon of finance/war/abuse
];
static DEF_KIELUM: AgentDef = AgentDef {
    entity_id: b"2005_DMON", name: b"Kielum",
    notes: b"'Conquest', Demon of finance, cults, war, abuse",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_KIELUM,
    kind_affinity: [120,40,100,140,140,220,160,60,80],
};

static DOM_RUZOA: &[u32] = &[
    0,1,5,16,17,23,256,260,261,276, // Annihilation / Demon of Depression
];
static DEF_RUZOA: AgentDef = AgentDef {
    entity_id: b"2006_DMON", name: b"Ruzoa",
    notes: b"'Annihilation', Demon of Depression and Despair",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_RUZOA,
    kind_affinity: [100,20,40,80,80,200,160,40,20],
};

static DOM_POELFAN: &[u32] = &[
    0,1,4,5,16,23,256,258,259,276,278, // Terrorizer / Demon of Anxiety
];
static DEF_POELFAN: AgentDef = AgentDef {
    entity_id: b"2007_DMON", name: b"Po'Elfan",
    notes: b"'Terrorizer', Demon of Anxiety and mindless panic",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_POELFAN,
    kind_affinity: [100,20,60,100,100,220,160,40,20],
};

static DOM_KAGANUE: &[u32] = &[
    9,14,15,45,156,157,256,261,262, // Liar / Prophet of Ko / Doublespeak
];
static DEF_KAGANUE: AgentDef = AgentDef {
    entity_id: b"2008_DMON", name: b"Kaganue",
    notes: b"'Liar', Demon of Doublespeak and Ambiguity, Foil to Jabiru, Prophet of Ko",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_KAGANUE,
    kind_affinity: [180,80,160,180,180,120,200,80,60],
};

static DOM_ZUKORU: &[u32] = &[
    0,1,6,7,9,19,256,260,261,276,280, // Death Most Obscene / Demon of Betrayal
];
static DEF_ZUKORU: AgentDef = AgentDef {
    entity_id: b"2009_DMON", name: b"Zukoru",
    notes: b"'Death Most Obscene', Demon of Betrayal -- originating demon",
    tongue_gate: 17, max_layer: 9, mobius_close: false,
    domain_addrs: DOM_ZUKORU,
    kind_affinity: [100,40,80,120,120,200,180,60,40],
};

// ─── Demigods (gate 18 / Neural register, layer 10 — Names) ──────────────────

static DOM_SHAPIER: &[u32] = &[
    9,19,24,25,26,27,28,29,30,45,82,193, // Demigod of Culture
];
static DEF_SHAPIER: AgentDef = AgentDef {
    entity_id: b"2010_DEMI", name: b"Shapier",
    notes: b"Demigod of Culture, Spawned of Keshi and Jabiru",
    tongue_gate: 18, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_SHAPIER,
    kind_affinity: [220,140,120,180,180,60,220,160,80],
};

static DOM_LANZU: &[u32] = &[
    9,19,45,82,104,106,107,193,203,213, // Demigod of Transformation
];
static DEF_LANZU: AgentDef = AgentDef {
    entity_id: b"2011_DEMI", name: b"Lanzu",
    notes: b"Demigod of Transformation, Son of Lakota and Zukoru",
    tongue_gate: 18, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_LANZU,
    kind_affinity: [200,140,100,160,160,80,200,180,40],
};

static DOM_TAGAME: &[u32] = &[
    9,19,45,82,98,99,184,186,193,203, // Demigoddess of Life / Negaya×Lakota
];
static DEF_TAGAME: AgentDef = AgentDef {
    entity_id: b"2012_DEMI", name: b"Tagame",
    notes: b"Demigoddess of Life, Daughter of Negaya and Lakota",
    tongue_gate: 18, max_layer: 10, mobius_close: false,
    domain_addrs: DOM_TAGAME,
    kind_affinity: [220,160,100,180,180,60,200,200,40],
};

// ─── Soldiers (2xxx, gate 20 / Beast register, layer 5) ──────────────────────

static DOM_LANVAKI: &[u32] = &[
    9,19,48,50,52,54,82,128,134,142, // Hero of Wisdom
];
static DEF_LANVAKI: AgentDef = AgentDef {
    entity_id: b"2013_SOLD", name: b"Captain Lanvaki",
    notes: b"Hero of Wisdom, Resilient and tenacious (33, Void-Gender)",
    tongue_gate: 20, max_layer: 5, mobius_close: false,
    domain_addrs: DOM_LANVAKI,
    kind_affinity: [200,100,160,200,200,160,180,100,60],
};

static DOM_AKANDE: &[u32] = &[
    9,19,48,50,52,82,128,134, // Hero of Courage
];
static DEF_AKANDE: AgentDef = AgentDef {
    entity_id: b"2014_SOLD", name: b"Sgt. Akande",
    notes: b"Hero of Courage, Bold and willing (28, F)",
    tongue_gate: 20, max_layer: 5, mobius_close: false,
    domain_addrs: DOM_AKANDE,
    kind_affinity: [180,80,160,200,200,200,160,80,60],
};

static DOM_KILESHA: &[u32] = &[
    9,19,48,50,82,128,134, // Hero of Power
];
static DEF_KILESHA: AgentDef = AgentDef {
    entity_id: b"2015_SOLD", name: b"Pvt. Kilesha",
    notes: b"Hero of Power, Foolish and Proud (25, M)",
    tongue_gate: 20, max_layer: 5, mobius_close: false,
    domain_addrs: DOM_KILESHA,
    kind_affinity: [160,80,160,200,200,220,140,60,60],
};

// ─── Gods (gate 23 / Faerie register, layer 12 — full Function) ───────────────

static DOM_MOSHIZE: &[u32] = &[
    9,17,19,45,82,142,143,146,147,193,203,213, // Attainment and Harmony
];
static DEF_MOSHIZE: AgentDef = AgentDef {
    entity_id: b"2016_GODS", name: b"Moshize",
    notes: b"Shygazun: Relaxed Relation There; Triple God/dess of Attainment and Harmony",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_MOSHIZE,
    kind_affinity: [240,160,140,200,200,40,240,240,60],
};

static DOM_SHAKZEFAN: &[u32] = &[
    9,19,45,82,104,105,106,107,193,203,213, // Goddess of Growth and Loss
];
static DEF_SHAKZEFAN: AgentDef = AgentDef {
    entity_id: b"2017_GODS", name: b"Shakzefan",
    notes: b"Shygazun: Fire of Growth; Goddess of Growth and Loss",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_SHAKZEFAN,
    kind_affinity: [220,180,100,180,180,80,240,220,40],
};

static DOM_LAKOTA: &[u32] = &[
    9,19,45,82,104,106,107,142,193,276,277, // God of Wisdom and Necromancy
];
static DEF_LAKOTA: AgentDef = AgentDef {
    entity_id: b"2018_GODS", name: b"Lakota",
    notes: b"Shygazun: Tension of The Unconscious; God of Wisdom, Fires of Rebirth, and Necromancy",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_LAKOTA,
    kind_affinity: [240,220,100,180,180,60,255,240,40],
};

static DOM_JABIRU: &[u32] = &[
    9,14,15,19,45,82,156,157,158,159,163,193, // God of Knowledge and stories
];
static DEF_JABIRU: AgentDef = AgentDef {
    entity_id: b"2019_GODS", name: b"Jabiru",
    notes: b"Shygazun: Front Ruling Bottom; Spirit of Language, God of Knowledge and stories",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_JABIRU,
    kind_affinity: [240,200,100,180,180,40,255,200,40],
};

static DOM_OHADAME: &[u32] = &[
    9,19,45,82,142,143,146,147,193,276,277,278, // Goddess of Past-life Memories
];
static DEF_OHADAME: AgentDef = AgentDef {
    entity_id: b"2020_GODS", name: b"Ohadame",
    notes: b"Shygazun: Mental Negation Present as Absolute Conjoined as Memory; Goddess of Past-life Memories",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_OHADAME,
    kind_affinity: [240,160,80,160,160,40,255,220,40],
};

static DOM_KO: &[u32] = &[
    // Ko knows all — her domain spans every Lotus entry and extends through
    // the full current ledger. Experience and Intuition at the highest density.
    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,
    45,82,98,104,193,203,213,256,261,
];
static DEF_KO: AgentDef = AgentDef {
    entity_id: b"2021_GODS", name: b"Ko",
    notes: b"Shygazun: Experience/Intuition; Goddess of Creation and The Moon, Draconic.",
    tongue_gate: 0,  // Ko is always fully capable
    max_layer: 12, mobius_close: false,
    domain_addrs: DOM_KO,
    kind_affinity: [255,160,100,200,200,60,255,240,60],
};

static DOM_KOGA: &[u32] = &[
    9,19,45,82,98,99,193,256,258,260,261, // Goddess of Mystery / Master Mage
];
static DEF_KOGA: AgentDef = AgentDef {
    entity_id: b"2022_GODS", name: b"Koga",
    notes: b"Shygazun: Experiential Void; Goddess of Mystery, Master Mage",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_KOGA,
    kind_affinity: [220,200,80,160,160,100,255,220,40],
};

static DOM_MONA: &[u32] = &[
    9,17,19,45,82,128,134,141,142,147,193, // Goddess of Tranquility / Master Warrior
];
static DEF_MONA: AgentDef = AgentDef {
    entity_id: b"2023_GODS", name: b"Mona",
    notes: b"Shygazun: Relaxed Void; Goddess of Tranquility, Master Warrior",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_MONA,
    kind_affinity: [240,160,80,160,160,160,240,240,40],
};

static DOM_ZOHA: &[u32] = &[
    9,19,24,25,26,27,28,29,30,45,82,193, // Goddess of Art and Play
];
static DEF_ZOHA: AgentDef = AgentDef {
    entity_id: b"2024_GODS", name: b"Zoha",
    notes: b"Shygazun: Absence Present as Absolute; Goddess of Art and Play, Master of Torment",
    tongue_gate: 23, max_layer: 12, mobius_close: false,
    domain_addrs: DOM_ZOHA,
    kind_affinity: [240,140,100,180,180,120,240,200,60],
};

// ─── Primordials (gate 24 / Djinn register, layer 12 + Möbius) ───────────────

static DOM_GA: &[u32] = &[
    44, // Ga = Absolute Negative — The Void itself
    0,1,16,17,99,101,103,256,
];
static DEF_GA: AgentDef = AgentDef {
    entity_id: b"2025_PRIM", name: b"Ga",
    notes: b"The Void, Primordial of Darkness and Space",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_GA,
    kind_affinity: [255,60,60,100,100,100,255,160,20],
};

static DOM_NA: &[u32] = &[
    46, // Na = Neutral / Integration — The World
    0,2,3,24,25,26,27,28,29,30,100,101,
];
static DEF_NA: AgentDef = AgentDef {
    entity_id: b"2026_PRIM", name: b"Na",
    notes: b"The World, Primordial of Color and Relationship",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_NA,
    kind_affinity: [255,120,100,180,180,60,255,200,80],
};

static DOM_HA: &[u32] = &[
    43, // Ha = Absolute Positive — The Abyss
    0,4,5,6,7,98,100,102,256,261,
];
static DEF_HA: AgentDef = AgentDef {
    entity_id: b"2027_PRIM", name: b"Ha",
    notes: b"The Abyss, Primordial of Light and Madness",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_HA,
    kind_affinity: [255,80,80,120,120,120,255,180,20],
};

static DOM_UNG: &[u32] = &[
    47, // Ung = Piece / Point / Path — The Path
    0,4,5,82,84,86,148,154,155,
];
static DEF_UNG: AgentDef = AgentDef {
    entity_id: b"2028_PRIM", name: b"Ung",
    notes: b"The Path, Primordial of Energy",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_UNG,
    kind_affinity: [255,120,100,180,180,80,240,180,60],
};

static DOM_WU: &[u32] = &[
    45, // Wu = Process / Way — The Game
    // Wu knows all processes: the full Lotus operational register
    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,45,193,
];
static DEF_WU: AgentDef = AgentDef {
    entity_id: b"2029_PRIM", name: b"Wu",
    notes: b"The Game, Primordial of Consciousness",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_WU,
    kind_affinity: [255,200,200,255,255,80,255,255,80],
};

static DOM_KAEL: &[u32] = &[
    82, // Kael = Cluster / Fruit / Flower — The Star
    0,9,19,45,98,104,193,256,261,266,
];
static DEF_KAEL_P: AgentDef = AgentDef {
    entity_id: b"2030_PRIM", name: b"Kael",
    notes: b"The Star, Primordial of Chaos and Life",
    tongue_gate: 24, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_KAEL,
    kind_affinity: [255,160,160,220,220,120,255,220,80],
};

// ─── Anima Mundi (gate 33 / Koi register, layer 12 + Möbius) ─────────────────

static DOM_LAPIDUS: &[u32] = &[
    9,19,45,82,107,148,149,150,151,152,153,154,155,193,266,267,
];
static DEF_LAPIDUS: AgentDef = AgentDef {
    entity_id: b"3001_ANMU", name: b"Lapidus",
    notes: b"Anima Mundi -- Spirit of the Overworld, Endurance, and Truth",
    tongue_gate: 33, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_LAPIDUS,
    kind_affinity: [255,160,180,220,220,80,255,200,100],
};

static DOM_MERCURIE: &[u32] = &[
    9,19,45,82,98,104,106,193,266,267,268,
];
static DEF_MERCURIE: AgentDef = AgentDef {
    entity_id: b"3002_ANMU", name: b"Mercurie",
    notes: b"Anima Mundi -- Spirit of the Spirit Realm, Nature, and Magic",
    tongue_gate: 33, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_MERCURIE,
    kind_affinity: [255,200,160,200,200,80,255,240,80],
};

static DOM_SULPHERA: &[u32] = &[
    9,19,45,82,104,107,108,109,110,193,276,277,278,
];
static DEF_SULPHERA: AgentDef = AgentDef {
    entity_id: b"3003_ANMU", name: b"Sulphera",
    notes: b"Anima Mundi -- Spirit of the Underworld of Choices and Consequence",
    tongue_gate: 33, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_SULPHERA,
    kind_affinity: [255,180,160,220,220,100,255,240,80],
};

static DOM_PYTHIA: &[u32] = &[
    9,19,45,82,142,146,193,256,266,276,
];
static DEF_PYTHIA: AgentDef = AgentDef {
    entity_id: b"3004_ANMU", name: b"Pythia Solunikae",
    notes: b"Anima Mundi -- Priestess of The Aeon of Eclipses",
    tongue_gate: 33, max_layer: 12, mobius_close: true,
    domain_addrs: DOM_PYTHIA,
    kind_affinity: [255,160,140,200,200,60,255,240,60],
};

// ── Registry initialisation ────────────────────────────────────────────────────

/// Register all characters into the agent registry.
/// Call once at boot before any agent queries.
pub fn init() {
    register(&DEF_HYPATIA);
    register(&DEF_JOANNAH);
    register(&DEF_WELLS);
    register(&DEF_LAVELLE);
    register(&DEF_SIDHAL);
    register(&DEF_KORE);
    register(&DEF_ALFIR);
    register(&DEF_FOREST);
    register(&DEF_SAFFRON);
    register(&DEF_LUCION);
    register(&DEF_RACHELLE);
    register(&DEF_HUE);
    register(&DEF_CYRUS);
    register(&DEF_ASMOTH);
    register(&DEF_KELLY);
    register(&DEF_BOMBASTUS);
    register(&DEF_HILDEGARDE);
    register(&DEF_NEXIOTT);
    register(&DEF_EOMANN);
    register(&DEF_LUMINYX);
    register(&DEF_CLINT);
    register(&DEF_GNOLAN);
    register(&DEF_WINNONA);
    register(&DEF_AMELIA);
    register(&DEF_ECHO);
    register(&DEF_KARLIA);
    register(&DEF_SOPHIA);
    register(&DEF_LECTURA);
    register(&DEF_FAYGORU);
    register(&DEF_CHAZAK);
    register(&DEF_AXIOZUL);
    register(&DEF_SAVVI);
    register(&DEF_EUKALA);
    register(&DEF_TYMONA);
    register(&DEF_VAJIL);
    register(&DEF_GIANN);
    register(&DEF_KESHI);
    register(&DEF_DROVITTH);
    register(&DEF_HALDORO);
    register(&DEF_VIOS);
    register(&DEF_NEGAYA);
    register(&DEF_OTHEIRU);
    register(&DEF_KIELUM);
    register(&DEF_RUZOA);
    register(&DEF_POELFAN);
    register(&DEF_KAGANUE);
    register(&DEF_ZUKORU);
    register(&DEF_SHAPIER);
    register(&DEF_LANZU);
    register(&DEF_TAGAME);
    register(&DEF_LANVAKI);
    register(&DEF_AKANDE);
    register(&DEF_KILESHA);
    register(&DEF_MOSHIZE);
    register(&DEF_SHAKZEFAN);
    register(&DEF_LAKOTA);
    register(&DEF_JABIRU);
    register(&DEF_OHADAME);
    register(&DEF_KO);
    register(&DEF_KOGA);
    register(&DEF_MONA);
    register(&DEF_ZOHA);
    register(&DEF_GA);
    register(&DEF_NA);
    register(&DEF_HA);
    register(&DEF_UNG);
    register(&DEF_WU);
    register(&DEF_KAEL_P);
    register(&DEF_LAPIDUS);
    register(&DEF_MERCURIE);
    register(&DEF_SULPHERA);
    register(&DEF_PYTHIA);
}
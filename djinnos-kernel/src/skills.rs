// skills.rs — Skills and perk runtime for Ko's Labyrinth (7_KLGS).
//
// Wraps player_state with game logic:
//   train()        — validate rank increase, apply VITRIOL boost
//   unlock_perk()  — check eligibility, apply sanity delta, set KoFlag
//   try_eval()     — kobra dispatch for `skill` and `perk` namespaces
//
// Skill indices and VITRIOL affinities match apps/atelier-desktop/src/skillRegistry.js.
//
// VITRIOL indices: 0=V(Vitality) 1=I(Introspection) 2=T(Tactility)
//                  3=R(Reflectivity) 4=I(Ingenuity) 5=O(Ostentation) 6=L(Levity)
//
// Sanity indices: 0=Alchemical 1=Narrative 2=Terrestrial 3=Cosmic

use crate::player_state::{
    SKILL_COUNT, SKILL_MEDITATION,
    PERK_BREATHWORK, PERK_ALCHEMICAL, PERK_HYPNOTIC, PERK_INFERNAL,
    PERK_DEPTH, PERK_TRANSCENDENTAL, PERK_ZEN,
};

// ── Skill name table ───────────────────────────────────────────────────────────

pub const SKILL_NAMES: [&[u8]; SKILL_COUNT] = [
    b"barter",        b"energy_weapons", b"explosives",  b"guns",
    b"lockpick",      b"medicine",       b"melee_weapons",b"repair",
    b"alchemy",       b"sneak",          b"hack",        b"speech",
    b"survival",      b"unarmed",        b"meditation",  b"magic",
    b"blacksmithing", b"silversmithing", b"goldsmithing",
];

pub const SKILL_DISPLAY: [&[u8]; SKILL_COUNT] = [
    b"Barter",        b"Energy Weapons", b"Explosives",  b"Guns",
    b"Lockpick",      b"Medicine",       b"Melee Weapons",b"Repair",
    b"Alchemy",       b"Sneak",          b"Hack",        b"Speech",
    b"Survival",      b"Unarmed",        b"Meditation",  b"Magic",
    b"Blacksmithing", b"Silversmithing", b"Goldsmithing",
];

// VITRIOL affinity per skill slot (index into vitriol[7]).
pub const SKILL_VITRIOL: [u8; SKILL_COUNT] = [
    5,  // barter         → O (Ostentation)
    4,  // energy_weapons → I (Ingenuity)
    2,  // explosives     → T (Tactility)
    2,  // guns           → T
    4,  // lockpick       → I
    3,  // medicine       → R (Reflectivity)
    0,  // melee_weapons  → V (Vitality)
    2,  // repair         → T
    3,  // alchemy        → R
    6,  // sneak          → L (Levity)
    4,  // hack           → I
    6,  // speech         → L
    6,  // survival       → L (Levity) primary, T secondary via SKILL_VITRIOL_2
    0,  // unarmed        → V
    1,  // meditation     → I_intro (Introspection)
    6,  // magic          → L
    2,  // blacksmithing  → T
    5,  // silversmithing → O
    5,  // goldsmithing   → O
];

// Named skill index constants for cross-module use.
pub const SKILL_ALCHEMY_IDX:      usize =  8;
pub const SKILL_MEDICINE_IDX:     usize =  5;
pub const SKILL_MELEE_IDX:        usize =  6;
pub const SKILL_GUNS_IDX:         usize =  3;
pub const SKILL_SNEAK_IDX:        usize =  9;
pub const SKILL_SPEECH_IDX:       usize = 11;
pub const SKILL_SURVIVAL_IDX:     usize = 12;
pub const SKILL_BARTER_IDX:       usize =  0;
pub const SKILL_LOCKPICK_IDX:     usize =  4;

// Some skills draw from two VITRIOL axes simultaneously.
// 0xFF = no secondary affinity.
// Survival draws from both Levity (L=6, environmental lightness) and
// Tactility (T=2, physical engagement with the material world).
pub const SKILL_VITRIOL_2: [u8; SKILL_COUNT] = [
    0xFF, // barter
    0xFF, // energy_weapons
    0xFF, // explosives
    0xFF, // guns
    0xFF, // lockpick
    0xFF, // medicine
    0xFF, // melee_weapons
    0xFF, // repair
    0xFF, // alchemy
    0xFF, // sneak
    0xFF, // hack
    0xFF, // speech
       2, // survival → T (Tactility) secondary
    0xFF, // unarmed
    0xFF, // meditation
    0xFF, // magic
    0xFF, // blacksmithing
    0xFF, // silversmithing
    0xFF, // goldsmithing
];

// Sanity dimension each skill presses (index into sanity[4]).
pub const SKILL_SANITY: [u8; SKILL_COUNT] = [
    1,  // barter         → Narrative
    3,  // energy_weapons → Cosmic
    2,  // explosives     → Terrestrial
    2,  // guns           → Terrestrial
    1,  // lockpick       → Narrative
    2,  // medicine       → Terrestrial
    2,  // melee_weapons  → Terrestrial
    0,  // repair         → Alchemical
    0,  // alchemy        → Alchemical
    1,  // sneak          → Narrative
    0,  // hack           → Alchemical
    1,  // speech         → Narrative
    2,  // survival       → Terrestrial
    2,  // unarmed        → Terrestrial
    3,  // meditation     → Cosmic
    3,  // magic          → Cosmic
    0,  // blacksmithing  → Alchemical
    0,  // silversmithing → Alchemical
    0,  // goldsmithing   → Alchemical
];

// ── Perk system (Fallout-style) ───────────────────────────────────────────────
//
// Each skill earns one perk SLOT per 20 ranks (max 5 per skill, 95 total).
// At each slot you choose one eligible perk from that skill's pool.
// Eligibility: primary skill rank >= min_rank AND gate requirements met.
// Perks with skill_idx=0xFF are VITRIOL-only or genocide-only (not slot-bound).
//
// Perk IDs 0-6: Meditation (legacy compatibility preserved).
// Full range: 0-127 (128 possible perks within PERK_WORDS=4 u32s).

// Gate types.
#[derive(Copy, Clone)]
pub enum PerkGate {
    None,                         // skill trained (rank >= 1) is enough
    Quest(&'static [u8]),         // quest slug must be COMPLETE
    VITRIOLMin(u8, u8),          // (axis_idx, min_value 1-10)
    VITRIOLDual(u8, u8, u8, u8), // (ax1, min1, ax2, min2) -- both required
    CrossSkill(usize, u8),        // (skill_idx_2, min_rank_2) -- both skills required
    DestrPath,                    // only if F_GENOCIDE_PATH ko_flag is set
    QuestAndVIT(&'static [u8], u8, u8), // quest + VITRIOL threshold
}

pub struct PerkDef {
    pub perk_id:     u8,
    pub skill_idx:   u8,           // 0xFF = VITRIOL-only or genocide-only
    pub name:        &'static [u8],
    pub flavor:      &'static [u8],// one in-world line, no mechanic description
    pub effect:      &'static [u8],// brief mechanic note
    pub min_rank:    u8,           // primary skill min rank (0 = just trained)
    pub gate:        PerkGate,
    pub excludes:    &'static [u8],// perk IDs closed by taking this one
    pub sanity_delta:[u8; 4],      // [alc, nar, ter, cos]
}

// Skill index constants for use in perk definitions.
const S_BARTER:   u8 =  0; const S_ENWEAP:   u8 =  1; const S_EXPLOS:   u8 =  2;
const S_GUNS:     u8 =  3; const S_LOCKPICK: u8 =  4; const S_MEDICINE: u8 =  5;
const S_MELEE:    u8 =  6; const S_REPAIR:   u8 =  7; const S_ALCHEMY:  u8 =  8;
const S_SNEAK:    u8 =  9; const S_HACK:     u8 = 10; const S_SPEECH:   u8 = 11;
const S_SURVIVAL: u8 = 12; const S_UNARMED:  u8 = 13; const S_MEDITAT:  u8 = 14;
const S_MAGIC:    u8 = 15; const S_BSMITH:   u8 = 16; const S_SILVER:   u8 = 17;
const S_GOLD:     u8 = 18; const S_SPECIAL:  u8 = 0xFF;

// VITRIOL axis indices used in gates.
const AX_V: u8 = 0; const AX_I: u8 = 1; const AX_T: u8 = 2; const AX_R: u8 = 3;
const AX_G: u8 = 4; const AX_O: u8 = 5; const AX_L: u8 = 6; // G = Ingenuity

pub const ALL_PERKS: &[PerkDef] = &[

    // ── Meditation (IDs 0-6) -- full tree, quest-gated ─────────────────────────
    PerkDef { perk_id:0, skill_idx:S_MEDITAT, name:b"Breathwork",
        flavor:b"The body is the first instrument.",
        effect:b"Reduces sanity dissonance during high-pressure encounters.",
        min_rank:1, gate:PerkGate::None, excludes:b"",
        sanity_delta:[8,0,10,0] },
    PerkDef { perk_id:1, skill_idx:S_MEDITAT, name:b"Alchemical",
        flavor:b"The inner coil mirrors the outer work.",
        effect:b"Boosts alchemical sanity. Synergizes with Alchemy skill.",
        min_rank:1, gate:PerkGate::Quest(b"0008_KLST"), excludes:b"",
        sanity_delta:[15,0,0,0] },
    PerkDef { perk_id:2, skill_idx:S_MEDITAT, name:b"Hypnotic",
        flavor:b"Soften the threshold. Some things only speak to minds that will.",
        effect:b"Unlocks deeper dialogue with Undine and Fae entities.",
        min_rank:1, gate:PerkGate::Quest(b"0007_KLST"), excludes:b"",
        sanity_delta:[0,10,0,5] },
    PerkDef { perk_id:3, skill_idx:S_MEDITAT, name:b"Infernal",
        flavor:b"To hold consciousness in the underworld without dissolution.",
        effect:b"Gates Sulphera access. Opens Visitor's Ring (Ring 8).",
        min_rank:1, gate:PerkGate::Quest(b"0010_KLST"), excludes:b"",
        sanity_delta:[0,0,0,20] },
    PerkDef { perk_id:4, skill_idx:S_MEDITAT, name:b"Depth",
        flavor:b"Below identity. The coil becomes visible.",
        effect:b"24-layer dream calibration reads deeper. Void Wraiths notice.",
        min_rank:1, gate:PerkGate::Quest(b"0011_KLST"), excludes:b"",
        sanity_delta:[8,8,8,8] },
    PerkDef { perk_id:5, skill_idx:S_MEDITAT, name:b"Transcendental",
        flavor:b"You sit more comfortably inside the Orrery's scale.",
        effect:b"Ko is more legible in dream sequences.",
        min_rank:1, gate:PerkGate::Quest(b"0016_KLST"), excludes:b"",
        sanity_delta:[0,0,0,13] },
    PerkDef { perk_id:6, skill_idx:S_MEDITAT, name:b"Zen",
        flavor:b"Grief is its prerequisite in the world.",
        effect:b"Reduces encounter-induced narrative dissonance.",
        min_rank:1, gate:PerkGate::Quest(b"0026_KLST"), excludes:b"",
        sanity_delta:[0,13,0,0] },

    // ── Alchemy (IDs 7-11) ─────────────────────────────────────────────────────
    PerkDef { perk_id:7, skill_idx:S_ALCHEMY, name:b"Calcination",
        flavor:b"You know the smell of the moment before change.",
        effect:b"Furnace operations yield one additional object per run.",
        min_rank:20, gate:PerkGate::Quest(b"0008_KLST"), excludes:b"",
        sanity_delta:[5,0,0,0] },
    PerkDef { perk_id:8, skill_idx:S_ALCHEMY, name:b"Dissolution",
        flavor:b"What the rings are made of, you have learned to unmake.",
        effect:b"Unlocks Desire Crystal craft chain. Sulphera material workbench.",
        min_rank:40, gate:PerkGate::Quest(b"0035_KLST"), excludes:b"",
        sanity_delta:[8,0,0,5] },
    PerkDef { perk_id:9, skill_idx:S_ALCHEMY, name:b"Philosopher's Approach",
        flavor:b"Principle, not procedure.",
        effect:b"One ingredient in any recipe substitutable with alchemical equivalent.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_R, 8), excludes:b"",
        sanity_delta:[10,0,0,0] },
    PerkDef { perk_id:10, skill_idx:S_ALCHEMY, name:b"Spagyric",
        flavor:b"The plant, the salt, the spirit: returned to the plant.",
        effect:b"Can craft healing items directly in dungeons without workbench.",
        min_rank:40, gate:PerkGate::CrossSkill(S_MEDICINE as usize, 40), excludes:b"",
        sanity_delta:[5,0,5,0] },
    PerkDef { perk_id:11, skill_idx:S_ALCHEMY, name:b"Sublimation",
        flavor:b"Solid to vapor without passing through liquid. You understand why.",
        effect:b"Retort operations bypass the grinding step if materials are pure.",
        min_rank:80, gate:PerkGate::VITRIOLMin(AX_R, 7), excludes:b"",
        sanity_delta:[12,0,0,0] },

    // ── Magic (IDs 12-16) ──────────────────────────────────────────────────────
    PerkDef { perk_id:12, skill_idx:S_MAGIC, name:b"Chaos Touch",
        flavor:b"Koga did not teach you. She confirmed you already had it.",
        effect:b"Chaos magic combat action available. Unpredictable Fae-register effect.",
        min_rank:40, gate:PerkGate::Quest(b"0031_KLST"), excludes:b"",
        sanity_delta:[0,5,0,10] },
    PerkDef { perk_id:13, skill_idx:S_MAGIC, name:b"Mona's Stillness",
        flavor:b"The deepest rest is not sleep.",
        effect:b"Defence doubled when player has not moved this combat turn.",
        min_rank:40, gate:PerkGate::Quest(b"0032_KLST"), excludes:b"",
        sanity_delta:[0,0,8,0] },
    PerkDef { perk_id:14, skill_idx:S_MAGIC, name:b"Zoha's Instrument",
        flavor:b"A bone flute. You understood what it was made from.",
        effect:b"Bone flute recharges -- usable once per Sulphera ring, not just once.",
        min_rank:40, gate:PerkGate::Quest(b"0033_KLST"), excludes:b"",
        sanity_delta:[0,8,0,5] },
    PerkDef { perk_id:15, skill_idx:S_MAGIC, name:b"Chaos Anchor",
        flavor:b"Still and wild at once. The Fae called it impossible.",
        effect:b"Can sustain Chaos magic spells during meditation state.",
        min_rank:40, gate:PerkGate::CrossSkill(S_MEDITAT as usize, 40), excludes:b"",
        sanity_delta:[0,0,0,15] },
    PerkDef { perk_id:16, skill_idx:S_MAGIC, name:b"Fae-Sight",
        flavor:b"The fold in the world is now legible.",
        effect:b"Hidden Fae presences become visible in zone exploration.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_L, 7), excludes:b"",
        sanity_delta:[0,5,0,8] },

    // ── Survival (IDs 17-20) ───────────────────────────────────────────────────
    PerkDef { perk_id:17, skill_idx:S_SURVIVAL, name:b"Light Touch",
        flavor:b"You take what you need. The rest stays.",
        effect:b"Foraging Fae costs halved. Zone depletion effects reduced.",
        min_rank:40, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,8,0] },
    PerkDef { perk_id:18, skill_idx:S_SURVIVAL, name:b"Land Reader",
        flavor:b"You saw what extraction without reading looks like.",
        effect:b"Zone depletion warning shown before strip threshold is hit.",
        min_rank:20, gate:PerkGate::Quest(b"0012_KLST"), excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:19, skill_idx:S_SURVIVAL, name:b"Offering Sense",
        flavor:b"You know what they want before they tell you.",
        effect:b"Intuitive knowledge of which offerings each Fae type values most.",
        min_rank:40, gate:PerkGate::VITRIOLMin(AX_L, 7), excludes:b"",
        sanity_delta:[0,5,5,0] },
    PerkDef { perk_id:20, skill_idx:S_SURVIVAL, name:b"Ghost Walk",
        flavor:b"The Assassins didn't teach you this. Survival did.",
        effect:b"Foraging in Mercurie triggers no Fae reaction.",
        min_rank:60, gate:PerkGate::CrossSkill(S_SNEAK as usize, 60), excludes:b"",
        sanity_delta:[0,0,5,5] },

    // ── Sneak (IDs 21-24) ──────────────────────────────────────────────────────
    PerkDef { perk_id:21, skill_idx:S_SNEAK, name:b"Shadow Fold",
        flavor:b"The Assassins didn't teach you to disappear. They confirmed you already had.",
        effect:b"Can enter certain dungeon area types without triggering enemy spawns.",
        min_rank:20, gate:PerkGate::Quest(b"0023_KLST"), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:22, skill_idx:S_SNEAK, name:b"Precision Strike",
        flavor:b"You move like you're not moving at all.",
        effect:b"Sneak combat action guarantees a critical hit.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_L, 6), excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:23, skill_idx:S_SNEAK, name:b"Dead Drop",
        flavor:b"A location is just a coordinate until you know what silence means.",
        effect:b"Can cache items in world locations; retrieval on later visit.",
        min_rank:40, gate:PerkGate::Quest(b"0024_KLST"), excludes:b"",
        sanity_delta:[0,3,0,0] },
    PerkDef { perk_id:24, skill_idx:S_SNEAK, name:b"Silent Kill",
        flavor:b"Neither art called it violence.",
        effect:b"Unarmed backstab in sneak mode -- no combat round triggered.",
        min_rank:50, gate:PerkGate::CrossSkill(S_UNARMED as usize, 50), excludes:b"",
        sanity_delta:[0,0,5,0] },

    // ── Speech (IDs 25-28) ─────────────────────────────────────────────────────
    PerkDef { perk_id:25, skill_idx:S_SPEECH, name:b"Civic Tongue",
        flavor:b"You walked through what they forgot, and they recognized it.",
        effect:b"Additional dialogue branch with all Lapidus townsfolk.",
        min_rank:20, gate:PerkGate::Quest(b"0038_KLST"), excludes:b"",
        sanity_delta:[0,10,0,0] },
    PerkDef { perk_id:26, skill_idx:S_SPEECH, name:b"Doublespeak Reading",
        flavor:b"The liar taught you to hear the gap.",
        effect:b"Hidden NPC information states become legible in dialogue.",
        min_rank:40, gate:PerkGate::Quest(b"0050_KLST"), excludes:b"",
        sanity_delta:[0,8,0,5] },
    PerkDef { perk_id:27, skill_idx:S_SPEECH, name:b"Honeyed Words",
        flavor:b"Neither flattery nor threat. Something between.",
        effect:b"Opens additional persuasion options when both O and L are high.",
        min_rank:40, gate:PerkGate::VITRIOLDual(AX_O,6, AX_L,6), excludes:b"",
        sanity_delta:[0,8,0,0] },
    PerkDef { perk_id:28, skill_idx:S_SPEECH, name:b"Negotiator",
        flavor:b"You know what it cost him. That knowledge is leverage.",
        effect:b"Unlocks negotiation dialogue in faction conflict resolution quests.",
        min_rank:60, gate:PerkGate::Quest(b"0049_KLST"), excludes:b"",
        sanity_delta:[0,10,0,0] },

    // ── Medicine (IDs 29-32) ───────────────────────────────────────────────────
    PerkDef { perk_id:29, skill_idx:S_MEDICINE, name:b"Field Medic",
        flavor:b"The wound doesn't wait for a workbench.",
        effect:b"Combat Use Item action heals full HP maximum instead of a flat value.",
        min_rank:30, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,8,0] },
    PerkDef { perk_id:30, skill_idx:S_MEDICINE, name:b"Necromantic Root",
        flavor:b"Negaya's void-nature inverted at the root.",
        effect:b"Can interact with the dead. Resolves Negaya's genocide torment.",
        min_rank:30, gate:PerkGate::CrossSkill(S_ALCHEMY as usize, 30), excludes:b"",
        sanity_delta:[5,5,5,5] },
    PerkDef { perk_id:31, skill_idx:S_MEDICINE, name:b"Stabilize",
        flavor:b"The system is tipping. You have a few seconds to find the fulcrum.",
        effect:b"Can prevent NPCs from dying in combat if you act within one turn.",
        min_rank:50, gate:PerkGate::VITRIOLMin(AX_R, 6), excludes:b"",
        sanity_delta:[0,0,10,0] },
    PerkDef { perk_id:32, skill_idx:S_MEDICINE, name:b"Antidote Sense",
        flavor:b"You know what you're tasting before it reaches you.",
        effect:b"Poison effects reduced by 50%. Warning before poisonous foraging.",
        min_rank:20, gate:PerkGate::VITRIOLMin(AX_R, 5), excludes:b"",
        sanity_delta:[0,0,5,0] },

    // ── Hack / Radio (IDs 33-38) ───────────────────────────────────────────────
    // The radio perks are the deepest Hack tree. Alaro's signal bleeds 3000+
    // years backward through Sulphera -- a skilled enough hacker doesn't just
    // tap Nexiott's caravan dispatch, they eventually receive temporal broadcasts.
    PerkDef { perk_id:33, skill_idx:S_HACK, name:b"Scanner",
        flavor:b"Nexiott's caravan routes are just coordinates. You can read them.",
        effect:b"Intercepts Nexiott Caravan Dispatch. Dungeon patrol routes visible.",
        min_rank:20, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,3,0,0] },
    PerkDef { perk_id:34, skill_idx:S_HACK, name:b"Frequency Finder",
        flavor:b"The Priesthood's broadcast runs on a frequency they think is clean.",
        effect:b"Unlocks Priesthood broadcast. Reveals Saffron's actual agenda.",
        min_rank:40, gate:PerkGate::VITRIOLMin(AX_G, 5), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:35, skill_idx:S_HACK, name:b"Alaro's Static",
        flavor:b"The signal is older than the tower. It was always there.",
        effect:b"Receive St. Alaro's temporal signal. Meditation sessions include future broadcasts. Dream sequences altered.",
        min_rank:40, gate:PerkGate::Quest(b"0047_KLST"), excludes:b"",
        sanity_delta:[0,0,0,12] },
    PerkDef { perk_id:36, skill_idx:S_HACK, name:b"Phantom Signal",
        flavor:b"Nexiott broadcasts on your frequency now.",
        effect:b"Can broadcast disinformation on Nexiott's entertainment channel. Opens propaganda subversion dialogue.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_G, 7), excludes:&[38],
        sanity_delta:[0,8,0,0] },
    PerkDef { perk_id:37, skill_idx:S_HACK, name:b"Royal Override",
        flavor:b"The Stelladevas speak to each other as if no one is listening.",
        effect:b"Access to Royal Channel. Castle private communications become legible.",
        min_rank:80, gate:PerkGate::Quest(b"0061_KLST"), excludes:b"",
        sanity_delta:[0,10,0,8] },
    PerkDef { perk_id:38, skill_idx:S_HACK, name:b"Dead Air",
        flavor:b"The city goes quiet. You made it quiet.",
        effect:b"Cut all radio networks. No broadcasts reach Lapidus. Genocide path only.",
        min_rank:40, gate:PerkGate::DestrPath, excludes:&[35,36,37],
        sanity_delta:[0,0,0,0] },

    // ── Barter (IDs 39-41) ─────────────────────────────────────────────────────
    PerkDef { perk_id:39, skill_idx:S_BARTER, name:b"Market Sense",
        flavor:b"The true price is not on the label.",
        effect:b"Can see true value of items -- what NPC shops would actually pay.",
        min_rank:20, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,3,0,0] },
    PerkDef { perk_id:40, skill_idx:S_BARTER, name:b"Monopoly",
        flavor:b"One thing in the world resists the logic of exchange.",
        effect:b"One item in player shop becomes price-locked. NPC customers cannot negotiate it down.",
        min_rank:40, gate:PerkGate::Quest(b"0040_KLST"), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:41, skill_idx:S_BARTER, name:b"Grey Market",
        flavor:b"Some economies don't use marks.",
        effect:b"Can trade within the Sulphera economy. Imp merchants become accessible.",
        min_rank:40, gate:PerkGate::VITRIOLMin(AX_O, 6), excludes:b"",
        sanity_delta:[0,0,0,5] },

    // ── Lockpick (IDs 42-44) ───────────────────────────────────────────────────
    PerkDef { perk_id:42, skill_idx:S_LOCKPICK, name:b"Bypass",
        flavor:b"The passage was always there. You just couldn't open it.",
        effect:b"Certain dungeon encounters avoidable entirely by picking preceding lock.",
        min_rank:40, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,3,0,0] },
    PerkDef { perk_id:43, skill_idx:S_LOCKPICK, name:b"Master Key",
        flavor:b"The revelation about Nexiott opened something in you.",
        effect:b"Unlocks hidden quest paths. Certain previously-closed doors become accessible.",
        min_rank:40, gate:PerkGate::Quest(b"0049_KLST"), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:44, skill_idx:S_LOCKPICK, name:b"Vault Sense",
        flavor:b"The mechanism is speaking. You just have to listen.",
        effect:b"Can detect lockpickable surfaces in dungeon rooms without searching.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_G, 6), excludes:b"",
        sanity_delta:[0,3,0,0] },

    // ── Melee Weapons (IDs 45-48) ──────────────────────────────────────────────
    PerkDef { perk_id:45, skill_idx:S_MELEE, name:b"Iron Fist",
        flavor:b"The weight of it stopped being a problem.",
        effect:b"Melee attacks bypass 3 points of enemy defence.",
        min_rank:20, gate:PerkGate::VITRIOLMin(AX_V, 6), excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:46, skill_idx:S_MELEE, name:b"Cleave",
        flavor:b"One motion, two problems.",
        effect:b"Successful melee attack deals half damage to an adjacent enemy.",
        min_rank:40, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:47, skill_idx:S_MELEE, name:b"War Veteran",
        flavor:b"You've been on both sides of this. The muscle learned.",
        effect:b"Combat turns begin with enemy telegraphing their next move (visible).",
        min_rank:40, gate:PerkGate::Quest(b"0022_KLST"), excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:48, skill_idx:S_MELEE, name:b"Berserker",
        flavor:b"The less you have left, the less you have to lose.",
        effect:b"Melee damage scales with missing HP. Below 25% HP: +50% damage.",
        min_rank:60, gate:PerkGate::VITRIOLMin(AX_V, 8), excludes:b"",
        sanity_delta:[0,0,5,0] },

    // ── Unarmed (IDs 49-51) ────────────────────────────────────────────────────
    PerkDef { perk_id:49, skill_idx:S_UNARMED, name:b"Iron Body",
        flavor:b"The armour is inside now.",
        effect:b"Defence scales with V VITRIOL when unarmed instead of T.",
        min_rank:50, gate:PerkGate::VITRIOLMin(AX_V, 7), excludes:b"",
        sanity_delta:[0,0,8,0] },
    PerkDef { perk_id:50, skill_idx:S_UNARMED, name:b"Monk's Calm",
        flavor:b"Two practices, one instrument.",
        effect:b"Meditation perks reduce unarmed combat damage taken.",
        min_rank:30, gate:PerkGate::CrossSkill(S_MEDITAT as usize, 30), excludes:b"",
        sanity_delta:[0,0,5,5] },
    PerkDef { perk_id:51, skill_idx:S_UNARMED, name:b"Pressure Point",
        flavor:b"The structure of the body is information.",
        effect:b"Unarmed attacks can apply status effects (stagger, slow).",
        min_rank:40, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,5,0] },

    // ── Guns (IDs 52-54) ───────────────────────────────────────────────────────
    PerkDef { perk_id:52, skill_idx:S_GUNS, name:b"Eagle Eye",
        flavor:b"The distance stopped being a variable.",
        effect:b"Ranged accuracy unaffected by dungeon visibility penalties.",
        min_rank:20, gate:PerkGate::VITRIOLMin(AX_T, 6), excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:53, skill_idx:S_GUNS, name:b"Gunslinger",
        flavor:b"The pause between draw and fire is not nothing. It is everything.",
        effect:b"Guns action fires twice in the same turn at 60% damage each.",
        min_rank:40, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:54, skill_idx:S_GUNS, name:b"Good Old .45",
        flavor:b"Hypatia left it somewhere you would find it.",
        effect:b"Angelic Gun equipped. The Colt path of the secret ending becomes available.",
        min_rank:40, gate:PerkGate::Quest(b"0045_KLST"), excludes:b"",
        sanity_delta:[0,0,0,8] },

    // ── Energy Weapons (IDs 55-56) ─────────────────────────────────────────────
    PerkDef { perk_id:55, skill_idx:S_ENWEAP, name:b"Overcharge",
        flavor:b"The cap exists for a reason. You removed it.",
        effect:b"Energy weapon damage +30% once per encounter. Weapon unusable next turn.",
        min_rank:40, gate:PerkGate::VITRIOLMin(AX_G, 6), excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:56, skill_idx:S_ENWEAP, name:b"Plasma Conduit",
        flavor:b"You carried the weapon they built to end the Fae. You know how it works.",
        effect:b"Energy weapon attacks bypass Fae resistances. Dangerous to reputation.",
        min_rank:40, gate:PerkGate::Quest(b"0030_KLST"), excludes:&[16,14],
        sanity_delta:[0,0,0,0] },

    // ── Explosives (IDs 57-60) -- Lavelle's domain ─────────────────────────────
    PerkDef { perk_id:57, skill_idx:S_EXPLOS, name:b"Shaped Charge",
        flavor:b"Lavelle showed you the difference between destruction and precision.",
        effect:b"Explosives deal full damage to target, reduced to adjacent enemies.",
        min_rank:20, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:58, skill_idx:S_EXPLOS, name:b"Demolitions Expert",
        flavor:b"The structure has a weakness. You can see it.",
        effect:b"Can collapse dungeon walls and corridors. Creates shortcuts.",
        min_rank:40, gate:PerkGate::VITRIOLMin(AX_T, 6), excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:59, skill_idx:S_EXPLOS, name:b"Fuse Reader",
        flavor:b"Time is legible when you know what it's counting toward.",
        effect:b"Can disarm any explosive trap in dungeons without a skill check.",
        min_rank:60, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:60, skill_idx:S_EXPLOS, name:b"Lavelle's Art",
        flavor:b"She called explosives a form of punctuation.",
        effect:b"Explosives can be crafted from foraged materials without the workbench.",
        min_rank:40, gate:PerkGate::Quest(b"0047_KLST"), excludes:b"",
        sanity_delta:[0,5,0,0] },

    // ── Repair (IDs 61-62) ─────────────────────────────────────────────────────
    PerkDef { perk_id:61, skill_idx:S_REPAIR, name:b"Field Strip",
        flavor:b"You maintain what you carry. It maintains you.",
        effect:b"Weapons can be maintained in the field without the workbench.",
        min_rank:30, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,3,0] },
    PerkDef { perk_id:62, skill_idx:S_REPAIR, name:b"Jury Rig",
        flavor:b"It shouldn't work. It will work once.",
        effect:b"Can combine two broken items into one functional item.",
        min_rank:50, gate:PerkGate::VITRIOLMin(AX_G, 5), excludes:b"",
        sanity_delta:[0,0,3,0] },

    // ── Blacksmithing (IDs 63-64) ──────────────────────────────────────────────
    PerkDef { perk_id:63, skill_idx:S_BSMITH, name:b"Temper",
        flavor:b"Heat it right and it holds. Hold it right and it heals.",
        effect:b"Crafted weapons have +15% durability.",
        min_rank:30, gate:PerkGate::VITRIOLMin(AX_T, 5), excludes:b"",
        sanity_delta:[0,0,5,0] },
    PerkDef { perk_id:64, skill_idx:S_BSMITH, name:b"Masterwork",
        flavor:b"The mark of something made to outlast you.",
        effect:b"Crafted weapons qualify as trade goods for the Sulphera economy.",
        min_rank:70, gate:PerkGate::VITRIOLMin(AX_T, 8), excludes:b"",
        sanity_delta:[0,0,8,0] },

    // ── Silversmithing (IDs 65-66) ─────────────────────────────────────────────
    PerkDef { perk_id:65, skill_idx:S_SILVER, name:b"Silver Tongue",
        flavor:b"Ostentation opens doors that eloquence cannot.",
        effect:b"Silversmithing-crafted jewelry grants O VITRIOL bonus when worn.",
        min_rank:30, gate:PerkGate::VITRIOLMin(AX_O, 5), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:66, skill_idx:S_SILVER, name:b"Sacred Metal",
        flavor:b"Silver remembers. It was there before the war.",
        effect:b"Silver items have Fae-protective properties. Fae disposition penalty halved.",
        min_rank:60, gate:PerkGate::None, excludes:b"",
        sanity_delta:[0,0,0,5] },

    // ── Goldsmithing (IDs 67-68) ───────────────────────────────────────────────
    PerkDef { perk_id:67, skill_idx:S_GOLD, name:b"Goldsmith's Eye",
        flavor:b"Value is legible now. Everything has a face.",
        effect:b"Can identify gem and metal quality at a glance. Reveals hidden item value.",
        min_rank:20, gate:PerkGate::VITRIOLMin(AX_O, 4), excludes:b"",
        sanity_delta:[0,3,0,0] },
    PerkDef { perk_id:68, skill_idx:S_GOLD, name:b"Desire Craft",
        flavor:b"Gold holds longing. You learned how to pour it.",
        effect:b"Can work with Asmodean materials. Desire Crystal Fragment craftable.",
        min_rank:50, gate:PerkGate::CrossSkill(S_ALCHEMY as usize, 50), excludes:b"",
        sanity_delta:[5,0,0,5] },

    // ── VITRIOL-only perks (IDs 69-75, skill_idx=S_SPECIAL) ───────────────────
    // No slots required. Auto-available when VITRIOL threshold is reached.
    PerkDef { perk_id:69, skill_idx:S_SPECIAL, name:b"Iron Will",
        flavor:b"The body holds what the mind lets go.",
        effect:b"HP maximum increased by V * 5.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_V, 8), excludes:b"",
        sanity_delta:[0,0,10,0] },
    PerkDef { perk_id:70, skill_idx:S_SPECIAL, name:b"Dream Clarity",
        flavor:b"The depth is where you live now.",
        effect:b"Meditation sessions begin at depth 3 automatically.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_I, 8), excludes:b"",
        sanity_delta:[0,0,0,10] },
    PerkDef { perk_id:71, skill_idx:S_SPECIAL, name:b"Sure Footing",
        flavor:b"The ground and you arrived at an agreement.",
        effect:b"Dungeon movement never triggers trap checks. Foraging yield always maximum.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_T, 8), excludes:b"",
        sanity_delta:[0,0,10,0] },
    PerkDef { perk_id:72, skill_idx:S_SPECIAL, name:b"Alchemical Intuition",
        flavor:b"The understanding became tactile.",
        effect:b"Occasional recipe hints in the workbench. Principle visible before procedure.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_R, 8), excludes:b"",
        sanity_delta:[10,0,0,0] },
    PerkDef { perk_id:73, skill_idx:S_SPECIAL, name:b"Quick Study",
        flavor:b"The connection between things is faster than the things themselves.",
        effect:b"Skill training costs 10% fewer actions to achieve rank milestones.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_G, 8), excludes:b"",
        sanity_delta:[5,0,0,0] },
    PerkDef { perk_id:74, skill_idx:S_SPECIAL, name:b"Market Dominance",
        flavor:b"The shop's reputation precedes you now.",
        effect:b"Player shop open-hours extended. Higher-wealth NPC customers appear.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_O, 8), excludes:b"",
        sanity_delta:[0,5,0,0] },
    PerkDef { perk_id:75, skill_idx:S_SPECIAL, name:b"Crowd Reading",
        flavor:b"Their regard for you is legible now. Not as number. As register.",
        effect:b"Faction standing with any NPC becomes legible as dialogue tone.",
        min_rank:0, gate:PerkGate::VITRIOLMin(AX_L, 8), excludes:b"",
        sanity_delta:[0,8,0,0] },

    // ── Genocide-only perks (IDs 76-79, skill_idx=S_SPECIAL) ──────────────────
    // Only accessible when F_GENOCIDE_PATH ko_flag is set.
    // Powerful, narrowing, and mutually exclusive with canonical perks.
    PerkDef { perk_id:76, skill_idx:S_SPECIAL, name:b"Keshi's Debt",
        flavor:b"You looked the gift horse in the mouth. It gave you something anyway.",
        effect:b"One VITRIOL stat doubled; corresponding axis drops to 1. Cannot be undone.",
        min_rank:0, gate:PerkGate::DestrPath,
        excludes:&[14,15,16,19,20],  // closes all Fae perks
        sanity_delta:[0,0,0,0] },
    PerkDef { perk_id:77, skill_idx:S_SPECIAL, name:b"Zukoru's Brand",
        flavor:b"The originating betrayal marked you. Everything is harder now. Everything yields more.",
        effect:b"All enemies scale harder. All loot doubled.",
        min_rank:0, gate:PerkGate::DestrPath, excludes:b"",
        sanity_delta:[0,0,0,0] },
    PerkDef { perk_id:78, skill_idx:S_SPECIAL, name:b"Othieru's Appetite",
        flavor:b"You consumed the pattern instead of defeating it.",
        effect:b"Attack damage scales with items destroyed from inventory.",
        min_rank:0, gate:PerkGate::DestrPath, excludes:b"",
        sanity_delta:[0,0,0,0] },
    PerkDef { perk_id:79, skill_idx:S_SPECIAL, name:b"Nothing",
        flavor:b"",
        effect:b"",
        min_rank:0, gate:PerkGate::DestrPath,
        excludes:b"",   // closes nothing -- is itself the absence
        sanity_delta:[0,0,0,0] },
];

// Total defined perks: 80 (IDs 0-79). Remaining bits (80-159) reserved.

// ── Perk access functions ─────────────────────────────────────────────────────

/// Find a perk by its numeric ID.
pub fn perk_by_id(id: u8) -> Option<&'static PerkDef> {
    ALL_PERKS.iter().find(|p| p.perk_id == id)
}

/// All perks belonging to a skill's pool (skill_idx matches).
/// Returns a slice iterator over the global ALL_PERKS array.
pub fn perks_for_skill(skill_idx: usize) -> impl Iterator<Item = &'static PerkDef> {
    ALL_PERKS.iter().filter(move |p| p.skill_idx as usize == skill_idx)
}

/// Check whether the player meets all requirements to unlock perk `id`.
/// Returns (can_unlock, reason).
pub fn perk_eligible_by_id(id: u8) -> (bool, &'static str) {
    let def = match perk_by_id(id) {
        Some(d) => d, None => return (false, "unknown perk"),
    };
    if crate::player_state::has_perk(id) { return (false, "already unlocked"); }

    // Primary skill rank check.
    if def.skill_idx != 0xFF && def.min_rank > 0 {
        let rank = crate::player_state::skill_rank(def.skill_idx as usize);
        if rank < def.min_rank { return (false, "skill rank too low"); }
    }

    // Gate check.
    match def.gate {
        PerkGate::None => {}
        PerkGate::Quest(slug) => {
            let state = crate::player_state::quest_state(slug);
            if state != Some(crate::player_state::QUEST_COMPLETE) {
                return (false, "required quest not complete");
            }
        }
        PerkGate::VITRIOLMin(axis, min) => {
            let v = crate::player_state::get().vitriol[axis as usize];
            if v < min { return (false, "VITRIOL too low"); }
        }
        PerkGate::VITRIOLDual(ax1, min1, ax2, min2) => {
            let ps = crate::player_state::get();
            if ps.vitriol[ax1 as usize] < min1 || ps.vitriol[ax2 as usize] < min2 {
                return (false, "VITRIOL requirements not met");
            }
        }
        PerkGate::CrossSkill(idx2, rank2) => {
            if crate::player_state::skill_rank(idx2) < rank2 {
                return (false, "secondary skill rank too low");
            }
        }
        PerkGate::DestrPath => {
            if !crate::ko_flags::ko_test(crate::ko_flags::F_GENOCIDE_PATH) {
                return (false, "not available on this path");
            }
        }
        PerkGate::QuestAndVIT(slug, axis, min) => {
            let state = crate::player_state::quest_state(slug);
            if state != Some(crate::player_state::QUEST_COMPLETE) {
                return (false, "required quest not complete");
            }
            let v = crate::player_state::get().vitriol[axis as usize];
            if v < min { return (false, "VITRIOL too low"); }
        }
    }

    // Exclusion check: is this perk excluded by something already taken?
    for p in ALL_PERKS.iter() {
        if crate::player_state::has_perk(p.perk_id) {
            if p.excludes.contains(&id) { return (false, "closed by another perk"); }
        }
    }

    (true, "eligible")
}

/// Unlock perk `id`. Applies sanity delta, fires eigenstate advance, spends slot.
/// Returns Err with reason if ineligible.
pub fn unlock_perk_by_id(id: u8) -> Result<(), &'static str> {
    let (ok, reason) = perk_eligible_by_id(id);
    if !ok { return Err(reason); }

    let def = perk_by_id(id).ok_or("unknown perk")?;
    crate::player_state::grant_perk(id);

    // Apply sanity deltas.
    let ps = crate::player_state::get_mut();
    for i in 0..4 { ps.sanity[i] = ps.sanity[i].saturating_add(def.sanity_delta[i]); }

    // Sulphera gate.
    if id == crate::player_state::PERK_INFERNAL {
        crate::ko_flags::ko_set(crate::ko_flags::F_SULPHERA_UNLOCKED);
    }

    // Spend a slot from the skill pool (if skill-bound perk).
    if def.skill_idx != 0xFF {
        crate::player_state::spend_perk_slot(def.skill_idx as usize);
    }

    // Exclusions are enforced via perk_eligible_by_id checks going forward.
    // No need to clear perks retroactively -- eligibility checks handle it.

    crate::eigenstate::advance(crate::eigenstate::T_CANNABIS);
    Ok(())
}

// Keep old unlock_perk for backward compatibility (meditation-only code path).
pub fn unlock_perk(perk_idx: usize) -> Result<(), &'static str> {
    if perk_idx >= 7 { return Err("use unlock_perk_by_id"); }
    unlock_perk_by_id(perk_idx as u8)
}

// Keep old perk_eligible for backward compatibility.
pub fn perk_eligible(perk_idx: usize) -> (bool, &'static str) {
    perk_eligible_by_id(perk_idx as u8)
}

// ── VITRIOL modifier functions ────────────────────────────────────────────────
//
// VITRIOL runs 1–10, neutral at 5 (the starting value in player_state).
//
// vitriol_scale(idx) → proportional multiplier (60–150, where 100 = neutral).
//   Use as:  result = base * vitriol_scale(idx) / 100
//   VITRIOL  1 → 60   (−40%)
//   VITRIOL  5 → 100  (no change)
//   VITRIOL 10 → 150  (+50%)
//   Formula: 100 + (v − 5) × 10
//
// vitriol_mod(idx) → additive offset (−4 to +5, where 0 = neutral).
//   Use as:  result = base + vitriol_mod(idx)
//   Formula: v − 5
//
// Skills with a secondary VITRIOL axis (see SKILL_VITRIOL_2) have their
// scale averaged across both axes.

fn axis_scale(v: u8) -> u32 {
    let v = v.max(1).min(10) as i32;
    (100 + (v - 5) * 10) as u32   // 1→60, 5→100, 10→150
}

pub fn vitriol_scale(skill_idx: usize) -> u32 {
    if skill_idx >= SKILL_COUNT { return 100; }
    let ps  = crate::player_state::get();
    let vi1 = SKILL_VITRIOL[skill_idx] as usize;
    let s1  = axis_scale(ps.vitriol[vi1]);
    let vi2 = SKILL_VITRIOL_2[skill_idx];
    if vi2 == 0xFF {
        s1
    } else {
        (s1 + axis_scale(ps.vitriol[vi2 as usize])) / 2
    }
}

pub fn vitriol_mod(skill_idx: usize) -> i8 {
    if skill_idx >= SKILL_COUNT { return 0; }
    let ps  = crate::player_state::get();
    let vi1 = SKILL_VITRIOL[skill_idx] as usize;
    let m1  = ps.vitriol[vi1] as i8 - 5;   // −4 to +5
    let vi2 = SKILL_VITRIOL_2[skill_idx];
    if vi2 == 0xFF {
        m1
    } else {
        let m2 = ps.vitriol[vi2 as usize] as i8 - 5;
        (m1 + m2) / 2
    }
}

// ── Train ─────────────────────────────────────────────────────────────────────

/// Train a skill to `new_rank` (1–100).  Returns Err if invalid or downgrade.
/// Applies a VITRIOL boost proportional to the rank increase.
pub fn train(idx: usize, new_rank: u8) -> Result<(), &'static str> {
    if idx >= SKILL_COUNT { return Err("unknown skill index"); }
    let new_rank = new_rank.min(100);
    let old_rank = crate::player_state::skill_rank(idx);
    if new_rank < old_rank { return Err("cannot decrease skill rank"); }
    if new_rank == old_rank { return Ok(()); }

    crate::player_state::skill_train(idx, new_rank);

    // VITRIOL boost: +1 per 50-rank milestone crossed (max +2 per skill, cap 10).
    // Reaching rank 50 gives +1; reaching rank 100 gives another +1.
    // Small, meaningful increments -- maxing all skills in one domain reaches 10.
    let old_milestones = old_rank / 50;
    let new_milestones = new_rank / 50;
    let boost = new_milestones.saturating_sub(old_milestones).min(2);
    let vi  = SKILL_VITRIOL[idx] as usize;
    let vi2 = SKILL_VITRIOL_2[idx];
    let ps  = crate::player_state::get_mut();
    if boost > 0 {
        ps.vitriol[vi] = ps.vitriol[vi].saturating_add(boost).min(10);
        if vi2 != 0xFF {
            ps.vitriol[vi2 as usize] =
                ps.vitriol[vi2 as usize].saturating_add(boost / 2).min(10);
        }
    }

    // Sanity nudge: +1 per 20 ranks gained on the skill's sanity dimension.
    let gain = (new_rank - old_rank) as u16;
    let san_boost = (gain / 20) as u8;
    if san_boost > 0 {
        let si = SKILL_SANITY[idx] as usize;
        ps.sanity[si] = ps.sanity[si].saturating_add(san_boost);
    }

    // Mirror flag: if this is meditation, set F_MEDITATION_TRAINED.
    if idx == SKILL_MEDITATION {
        crate::ko_flags::ko_set(crate::ko_flags::F_MEDITATION_TRAINED);
    }

    eigenstate_advance_skill(idx);
    Ok(())
}


// ── Kobra dispatch — `skill` and `perk` namespaces ───────────────────────────
//
// Called by kobra::eval_expr before normal Kobra AST parse.
// `out.push_text()` is used to write lines without needing the Output trait.

pub fn skill_dispatch(args: &[u8], out: &mut crate::kobra::EvalResult) {
    let (verb, rest) = split_verb(args);
    match verb {
        b"list" | b"status" if rest.is_empty() => {
            // List all 19 skills with current rank.
            let ps = crate::player_state::get();
            for i in 0..SKILL_COUNT {
                let rank = ps.skills[i];
                let mut buf = [b' '; 40];
                let n = SKILL_DISPLAY[i].len().min(20);
                buf[..n].copy_from_slice(&SKILL_DISPLAY[i][..n]);
                buf[22] = b'r'; buf[23] = b'k'; buf[24] = b' ';
                let rn = write_u8(&mut buf[25..], rank);
                out.push_text(&buf[..25 + rn]);
                out.push_line();
            }
        }
        b"status" => {
            // `skill status <name_or_idx>`
            if let Some(idx) = skill_idx_from(rest) {
                let rank = crate::player_state::skill_rank(idx);
                let mut buf = [b' '; 40];
                let n = SKILL_DISPLAY[idx].len().min(20);
                buf[..n].copy_from_slice(&SKILL_DISPLAY[idx][..n]);
                buf[22] = b'r'; buf[23] = b'k'; buf[24] = b' ';
                let rn = write_u8(&mut buf[25..], rank);
                out.push_text(&buf[..25 + rn]);
                out.push_line();
            } else {
                out.push_text(b"skill: unknown skill");
                out.push_line();
            }
        }
        b"set" | b"train" => {
            // `skill set <name_or_idx> <rank>`
            let (a, b_rest) = split_verb(rest);
            if let (Some(idx), Some(rank)) = (skill_idx_from(a), parse_u8(b_rest)) {
                match train(idx, rank) {
                    Ok(()) => {
                        out.push_text(b"trained: ");
                        out.push_text(SKILL_DISPLAY[idx]);
                        out.push_text(b" -> rk ");
                        let mut rb = [0u8; 4];
                        let rn = write_u8(&mut rb, crate::player_state::skill_rank(idx));
                        out.push_text(&rb[..rn]);
                        out.push_line();
                    }
                    Err(e) => { out.push_text(e.as_bytes()); out.push_line(); }
                }
            } else {
                out.push_text(b"skill set <name> <rank>");
                out.push_line();
            }
        }
        b"vitriol" => {
            let ps = crate::player_state::get();
            let labels = [b"V" as &[u8], b"I", b"T", b"R", b"I", b"O", b"L"];
            for i in 0..7 {
                let mut buf = [b' '; 16];
                buf[0] = labels[i][0];
                buf[2] = b'=';
                let vn = write_u8(&mut buf[4..], ps.vitriol[i]);
                out.push_text(&buf[..4 + vn]);
                out.push_text(b"  ");
            }
            out.push_line();
        }
        _ => {
            out.push_text(b"skill: list | status [name] | set <name> <rank> | vitriol");
            out.push_line();
        }
    }
}

pub fn perk_dispatch(args: &[u8], out: &mut crate::kobra::EvalResult) {
    let (verb, rest) = split_verb(args);
    match verb {
        b"list" | b"" => {
            for p in ALL_PERKS.iter() {
                if p.skill_idx == S_SPECIAL && p.perk_id < 76 {
                    // VITRIOL-only: skip in perk list, shown separately
                }
                let has   = crate::player_state::has_perk(p.perk_id);
                let (elig, _) = perk_eligible_by_id(p.perk_id);
                let tag: &[u8] = if has { b"[X]" } else if elig { b"[ ]" } else { b"[-]" };
                out.push_text(tag);
                out.push_text(b" ");
                out.push_text(p.name);
                out.push_line();
            }
            out.push_text(b"[X]=unlocked [ ]=eligible [-]=locked");
            out.push_line();
        }
        b"status" => {
            // perk status <numeric_id>
            if let Some(id) = parse_u8(rest) {
                if let Some(def) = perk_by_id(id) {
                    let has = crate::player_state::has_perk(id);
                    let (elig, reason) = perk_eligible_by_id(id);
                    out.push_text(def.name);
                    if has          { out.push_text(b": unlocked"); }
                    else if elig    { out.push_text(b": eligible"); }
                    else            { out.push_text(b": "); out.push_text(reason.as_bytes()); }
                    out.push_line();
                } else {
                    out.push_text(b"perk: unknown id"); out.push_line();
                }
            }
        }
        b"unlock" => {
            if let Some(id) = parse_u8(rest) {
                match unlock_perk_by_id(id) {
                    Ok(()) => {
                        let name = perk_by_id(id).map(|d| d.name).unwrap_or(b"?");
                        out.push_text(b"unlocked: "); out.push_text(name); out.push_line();
                    }
                    Err(e) => { out.push_text(e.as_bytes()); out.push_line(); }
                }
            } else {
                out.push_text(b"perk unlock <numeric_id>"); out.push_line();
            }
        }
        b"force" => {
            if let Some(id) = parse_u8(rest) {
                if let Some(def) = perk_by_id(id) {
                    crate::player_state::grant_perk(id);
                    let ps = crate::player_state::get_mut();
                    for i in 0..4 { ps.sanity[i] = ps.sanity[i].saturating_add(def.sanity_delta[i]); }
                    if id == crate::player_state::PERK_INFERNAL {
                        crate::ko_flags::ko_set(crate::ko_flags::F_SULPHERA_UNLOCKED);
                    }
                    out.push_text(b"force-granted: "); out.push_text(def.name); out.push_line();
                } else {
                    out.push_text(b"perk: unknown id"); out.push_line();
                }
            }
        }
        _ => {
            out.push_text(b"perk: list | status <id> | unlock <id> | force <id>");
            out.push_line();
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn split_verb(s: &[u8]) -> (&[u8], &[u8]) {
    let s = trim(s);
    match s.iter().position(|&b| b == b' ') {
        Some(i) => (&s[..i], trim(&s[i+1..])),
        None    => (s, b""),
    }
}

fn trim(s: &[u8]) -> &[u8] {
    let s = match s.iter().position(|&b| b != b' ' && b != b'\t') {
        Some(i) => &s[i..], None => return b"",
    };
    match s.iter().rposition(|&b| b != b' ' && b != b'\t') {
        Some(i) => &s[..=i], None => s,
    }
}

fn skill_idx_from(s: &[u8]) -> Option<usize> {
    // Try numeric index first.
    if let Some(n) = parse_u8(s) { if (n as usize) < SKILL_COUNT { return Some(n as usize); } }
    // Try name match.
    SKILL_NAMES.iter().position(|&nm| nm == s)
        .or_else(|| SKILL_DISPLAY.iter().position(|&nm| {
            // Case-insensitive ASCII compare.
            nm.len() == s.len() && nm.iter().zip(s).all(|(&a,&b)| a.to_ascii_lowercase() == b.to_ascii_lowercase())
        }))
}

fn parse_u8(s: &[u8]) -> Option<u8> {
    let s = trim(s);
    if s.is_empty() { return None; }
    let mut n = 0u16;
    for &b in s {
        if b < b'0' || b > b'9' { return None; }
        n = n * 10 + (b - b'0') as u16;
        if n > 255 { return None; }
    }
    Some(n as u8)
}

fn write_u8(buf: &mut [u8], v: u8) -> usize {
    if buf.is_empty() { return 0; }
    if v == 0 { buf[0] = b'0'; return 1; }
    let mut tmp = [0u8; 3]; let mut n = 0;
    let mut x = v;
    while x > 0 { tmp[n] = b'0' + x % 10; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n - 1 - i]; }
    n
}

fn eigenstate_advance_skill(idx: usize) {
    // Map skill to a Shygazun tongue for eigenstate advance.
    // Crafting/alchemy → Grapevine(7), Combat → Lotus(1), Social → Cannabis(8), etc.
    let tongue = match SKILL_VITRIOL[idx] {
        3 => crate::eigenstate::T_GRAPEVINE, // Reflectivity → data/craft
        1 => crate::eigenstate::T_CANNABIS,  // Introspection → consciousness
        _ => crate::eigenstate::T_LOTUS,     // all others → elemental/presence
    };
    crate::eigenstate::advance(tongue);
}

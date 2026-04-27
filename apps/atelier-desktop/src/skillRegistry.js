/**
 * skillRegistry.js
 *
 * Canonical skill and perk definitions for the KLGS series.
 *
 * Schema:
 *
 *   Skill {
 *     id:               string       — matches skill_table in services.py
 *     name:             string       — display name
 *     max_rank:         50           — all skills train to rank 50
 *     vitriol_affinity: string       — primary VITRIOL stat (V/I/R/T/I/O/L)
 *     sanity_dimension: string       — which sanity axis this skill presses
 *     perks:            PerkDef[]    — perks unlocked via this skill
 *   }
 *
 *   PerkDef {
 *     id:               string       — perk_id used in PerkUnlockInput
 *     name:             string       — display name
 *     required_skill:   string       — parent skill id (must be trained to access)
 *     required_quest:   string|null  — quest id that must be completed to unlock (KLST format)
 *     required_perks:   string[]     — prerequisite perk ids (empty = none)
 *     effect:           string       — what the perk does
 *     sanity_delta:     object       — live sanity boost applied on unlock
 *     stack_event:      string|null  — fires to Orrery when unlocked
 *     gates:            object|null  — special access flags this perk opens
 *   }
 *
 * Meditation perks are quest-gated, NOT rank-gated.
 * Each meditation perk unlocks when the player completes the associated quest.
 * No meditation perk requires another meditation perk as a prerequisite.
 *
 * VITRIOL key: V=Vitality I=Introspection R=Reflectivity T=Tactility I=Ingenuity O=Ostentation L=Levity
 * (Ingenuity is the second I — context distinguishes)
 */

// ── Meditation Perks — quest-gated, independent of each other ────────────────
//
//   Breathwork          — no quest required (available when meditation skill is trained)
//   Alchemical          — unlocks on: Bunsen For Hire       (0008_KLST)
//   Hypnotic            — unlocks on: Dream of Glass        (0007_KLST, narrative pos. ~0008-0009)
//   Infernal            — unlocks on: Demons and Diamonds   (0009_KLST) ← gates Sulphera
//   Depth               — unlocks on: The Siren Sounds      (0011_KLST)
//   Transcendental      — unlocks on: Transcendental        (0016_KLST)
//   Zen                 — unlocks on: Good Grief            (0026_KLST)

const MEDITATION_PERKS = [
  {
    id: "breathwork_meditation",
    name: "Breathwork Meditation",
    required_skill: "meditation",
    required_quest: null,           // No quest required — available as soon as meditation is trained
    required_perks: [],
    effect:
      "Conscious breath control as meditative anchor. Stabilizes sanity during high-pressure " +
      "encounters — reduces dissonance drift on the Terrestrial and Alchemical axes. " +
      "The body is the first instrument.",
    sanity_delta: { terrestrial: 0.04, alchemical: 0.03 },
    stack_event: "skill.perk.breathwork_meditation.unlocked",
    gates: null,
  },
  {
    id: "alchemical_meditation",
    name: "Alchemical Meditation",
    required_skill: "meditation",
    required_quest: "0008_KLST",    // Bunsen For Hire
    required_perks: [],
    effect:
      "Meditation as transmutation process — the inner coil mirrors the outer work. " +
      "Boosts Alchemical sanity. When both meditation and alchemy skills are trained, " +
      "each reinforces the other. Hypatia's native method.",
    sanity_delta: { alchemical: 0.06 },
    stack_event: "skill.perk.alchemical_meditation.unlocked",
    gates: null,
  },
  {
    id: "hypnotic_meditation",
    name: "Hypnotic Meditation",
    required_skill: "meditation",
    required_quest: "0007_KLST",    // Dream of Glass (narrative position between 0008 and 0009)
    required_perks: [],
    effect:
      "Directed trance states. Unlocks dialogue options with entities that only speak " +
      "to minds that have voluntarily softened their threshold. " +
      "Enables deeper Undine and Faerie encounter outcomes. " +
      "Presses Narrative sanity upward — trance coherence generates story clarity.",
    sanity_delta: { narrative: 0.04, cosmic: 0.02 },
    stack_event: "skill.perk.hypnotic_meditation.unlocked",
    gates: null,
  },
  {
    id: "infernal_meditation",
    name: "Infernal Meditation",
    required_skill: "meditation",
    required_quest: "0009_KLST",    // Demons and Diamonds
    required_perks: [],
    effect:
      "The ability to hold consciousness in the Underworld's register without dissolution. " +
      "This perk gates Sulphera access — opens the Visitor's Ring (Ring 8). " +
      "In Game 7, Alfir (0006_WTCH) delivers the teaching embedded in quest 0009_KLST. " +
      "Boosts Cosmic sanity substantially — sustaining infernal presence is a cosmic act.",
    sanity_delta: { cosmic: 0.08 },
    stack_event: "skill.perk.infernal_meditation.unlocked",
    gates: { sulphera_access: true },
  },
  {
    id: "depth_meditation",
    name: "Depth Meditation",
    required_skill: "meditation",
    required_quest: "0011_KLST",    // The Siren Sounds
    required_perks: [],
    effect:
      "Access to the sub-threshold layers — the place below identity where the coil " +
      "becomes visible. The 24-layer dream calibration reads deeper with this perk active. " +
      "All four sanity dimensions are boosted moderately. " +
      "The Void Wraiths take notice of players who reach this depth.",
    sanity_delta: { alchemical: 0.03, narrative: 0.03, terrestrial: 0.03, cosmic: 0.03 },
    stack_event: "skill.perk.depth_meditation.unlocked",
    gates: null,
  },
  {
    id: "transcendental_meditation",
    name: "Transcendental Meditation",
    required_skill: "meditation",
    required_quest: "0016_KLST",    // Transcendental
    required_perks: [],
    effect:
      "Mantra-based access to deep rest states. Boosts Cosmic sanity — the player " +
      "sits more comfortably inside the Orrery's scale. Ko is more legible in dream sequences.",
    sanity_delta: { cosmic: 0.05 },
    stack_event: "skill.perk.transcendental_meditation.unlocked",
    gates: null,
  },
  {
    id: "zen_meditation",
    name: "Zen Meditation",
    required_skill: "meditation",
    required_quest: "0026_KLST",    // Good Grief
    required_perks: [],
    effect:
      "Presence without object. Reduces encounter-induced Narrative dissonance — " +
      "the player accepts contradiction without fragmenting their story sense. " +
      "The latest-unlocking meditation perk; grief is its prerequisite in the world.",
    sanity_delta: { narrative: 0.05 },
    stack_event: "skill.perk.zen_meditation.unlocked",
    gates: null,
  },
];

// ── Full Skill Registry ───────────────────────────────────────────────────────

export const SKILLS = [
  {
    id: "barter",
    name: "Barter",
    max_rank: 50,
    vitriol_affinity: "O",        // Ostentation — exchange as display
    sanity_dimension: "narrative",
    perks: [],
  },
  {
    id: "energy_weapons",
    name: "Energy Weapons",
    max_rank: 50,
    vitriol_affinity: "I",        // Ingenuity
    sanity_dimension: "cosmic",
    perks: [],
  },
  {
    id: "explosives",
    name: "Explosives",
    max_rank: 50,
    vitriol_affinity: "T",        // Tactility
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "guns",
    name: "Guns",
    max_rank: 50,
    vitriol_affinity: "T",        // Tactility
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "lockpick",
    name: "Lockpick",
    max_rank: 50,
    vitriol_affinity: "I",        // Ingenuity
    sanity_dimension: "narrative",
    perks: [],
  },
  {
    id: "medicine",
    name: "Medicine",
    max_rank: 50,
    vitriol_affinity: "R",        // Reflectivity
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "melee_weapons",
    name: "Melee Weapons",
    max_rank: 50,
    vitriol_affinity: "V",        // Vitality
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "repair",
    name: "Repair",
    max_rank: 50,
    vitriol_affinity: "T",        // Tactility
    sanity_dimension: "alchemical",
    perks: [],
  },
  {
    id: "alchemy",
    name: "Alchemy",
    max_rank: 50,
    vitriol_affinity: "R",        // Reflectivity — transformation through understanding
    sanity_dimension: "alchemical",
    perks: [],
    note: "Hypatia's primary skill. Synergizes with alchemical_meditation perk.",
  },
  {
    id: "sneak",
    name: "Sneak",
    max_rank: 50,
    vitriol_affinity: "L",        // Levity — lightness of presence
    sanity_dimension: "narrative",
    perks: [],
  },
  {
    id: "hack",
    name: "Hack",
    max_rank: 50,
    vitriol_affinity: "I",        // Ingenuity
    sanity_dimension: "alchemical",
    perks: [],
  },
  {
    id: "speech",
    name: "Speech",
    max_rank: 50,
    vitriol_affinity: "L",        // Levity — expression and wit
    sanity_dimension: "narrative",
    perks: [],
  },
  {
    id: "survival",
    name: "Survival",
    max_rank: 50,
    vitriol_affinity: "V",        // Vitality
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "unarmed",
    name: "Unarmed",
    max_rank: 50,
    vitriol_affinity: "V",        // Vitality
    sanity_dimension: "terrestrial",
    perks: [],
  },
  {
    id: "meditation",
    name: "Meditation",
    max_rank: 50,
    vitriol_affinity: "I",        // Introspection — first I in VITRIOL
    sanity_dimension: "cosmic",
    perks: MEDITATION_PERKS,
    note: "The only skill with a full perk tree defined. Infernal Meditation (rank 5) gates Sulphera.",
  },
  {
    id: "magic",
    name: "Magic",
    max_rank: 50,
    vitriol_affinity: "L",        // Levity — magic as fluid, surprising, ungovernable
    sanity_dimension: "cosmic",
    perks: [],
  },
  {
    id: "blacksmithing",
    name: "Blacksmithing",
    max_rank: 50,
    vitriol_affinity: "T",        // Tactility — iron demands contact
    sanity_dimension: "alchemical",
    perks: [],
  },
  {
    id: "silversmithing",
    name: "Silversmithing",
    max_rank: 50,
    vitriol_affinity: "O",        // Ostentation — silver is prestige metal
    sanity_dimension: "alchemical",
    perks: [],
  },
  {
    id: "goldsmithing",
    name: "Goldsmithing",
    max_rank: 50,
    vitriol_affinity: "O",        // Ostentation — gold is the apex of material display
    sanity_dimension: "alchemical",
    perks: [],
    note: "The Desire Crystal (Asmodean material) is goldsmithing-adjacent in craft terms.",
  },
];

// ── Lookup helpers ────────────────────────────────────────────────────────────

export const SKILL_BY_ID = Object.fromEntries(SKILLS.map(s => [s.id, s]));

/** All perks across all skills as a flat array */
export const ALL_PERKS = SKILLS.flatMap(s => s.perks);

export const PERK_BY_ID = Object.fromEntries(ALL_PERKS.map(p => [p.id, p]));

/**
 * Check whether a perk can be unlocked given the player's current state.
 *
 * @param {string}   perkId
 * @param {object}   playerState
 * @param {boolean}  playerState.hasSkill        — whether the parent skill is trained at all
 * @param {string[]} playerState.completedQuests  — quest ids the player has completed
 * @param {string[]} playerState.unlockedPerks    — perk ids already unlocked
 * @returns {{ can_unlock: boolean, reason: string }}
 */
export function canUnlockPerk(perkId, { hasSkill = false, completedQuests = [], unlockedPerks = [] } = {}) {
  const perk = PERK_BY_ID[perkId];
  if (!perk) return { can_unlock: false, reason: "Unknown perk." };

  if (unlockedPerks.includes(perkId)) {
    return { can_unlock: false, reason: "Already unlocked." };
  }

  if (!hasSkill) {
    return { can_unlock: false, reason: `Requires the ${perk.required_skill} skill to be trained.` };
  }

  if (perk.required_quest && !completedQuests.includes(perk.required_quest)) {
    return {
      can_unlock: false,
      reason: `Requires quest ${perk.required_quest} to be completed first.`,
    };
  }

  const missingPrereqs = perk.required_perks.filter(p => !unlockedPerks.includes(p));
  if (missingPrereqs.length > 0) {
    return {
      can_unlock: false,
      reason: `Missing prerequisite perks: ${missingPrereqs.join(", ")}.`,
    };
  }

  return { can_unlock: true, reason: "Requirements met." };
}

/**
 * Check whether the player has Sulphera access.
 * Requires: infernal_meditation perk (which itself requires quest 0009_KLST).
 *
 * @param {string[]} unlockedPerks
 * @returns {boolean}
 */
export function hasSulpheraAccess(unlockedPerks) {
  return unlockedPerks.includes("infernal_meditation");
}

/**
 * Return all perks available to unlock given current player state.
 * Filters out already-unlocked perks.
 *
 * @param {Object}   skillRanks       — { skill_id: rank } (rank > 0 means trained)
 * @param {string[]} completedQuests
 * @param {string[]} unlockedPerks
 * @returns {PerkDef[]}
 */
export function availablePerks(skillRanks, completedQuests = [], unlockedPerks = []) {
  return ALL_PERKS.filter(perk => {
    const hasSkill = (skillRanks[perk.required_skill] ?? 0) > 0;
    return canUnlockPerk(perk.id, { hasSkill, completedQuests, unlockedPerks }).can_unlock;
  });
}

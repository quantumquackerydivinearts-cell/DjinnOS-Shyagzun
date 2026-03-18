/**
 * dungeonRegistry.js
 *
 * Canonical definitions for all dungeon types in the KLGS series.
 *
 * ── SULPHERA RINGS (9 total) ────────────────────────────────────────────────
 *
 *   Sulphera has 9 rings. Access is progressive — each ring requires the previous
 *   cleared and proven with a generated token.
 *
 *   Traversal order: 8 (entry) → 1→2→3→4→5→6→7 (sin rings) → 9 (Royal Ring)
 *
 *   Ring 8  — Visitor's Ring: presence of the Infernal Gods.
 *             Entry requires: Infernal Meditation skill + inciting token (quest 0008_KLST).
 *   Rings 1–7 — The 7 Sin Rings (Pride → Lust).
 *             Each cleared ring produces a token from the ruling Sin Lord.
 *             That token is required to enter the next ring.
 *   Ring 9  — The Royal Ring: gated by all 8 preceding rings.
 *
 *   Game 7 (7_KLGS) mentor for Infernal Meditation: Alfir.
 *   Quest that delivers the inciting token: 0008_KLST ("Demons and Diamonds").
 *
 * ── FAE DUNGEONS (5 total) ──────────────────────────────────────────────────
 *
 *   The 5 Fae peoples (Dryads, Undines, Salamanders, Gnomes, Faeries) are governed
 *   by Mona (Play and Torment, unified). They are NOT elemental proxies — each people
 *   has its own distinct nature. Elemental reduction does not apply.
 *
 * ── MINES OF MT. HIERONYMUS ─────────────────────────────────────────────────
 *
 *   Game 7 / Aeralune geography: Mt. Hieronymus pins Azonithia against Castle Azoth.
 *   A physical excavation, not a Sulphera construct.
 *
 * All dungeons randomize on entry. Layouts are ephemeral — only run outcomes persist.
 */

// ── Token system helpers ──────────────────────────────────────────────────────

/**
 * Stack event kind emitted when a Sin Ring is cleared and a token is granted.
 * Format: ring.{sin_slug}.token.granted
 */
export function ringTokenEventKind(sinSlug) {
  return `ring.${sinSlug}.token.granted`;
}

/**
 * Check whether a player workspace holds the token required to enter a given ring.
 * Token presence is determined by querying the stack for the granting event.
 * This is a client-side helper — actual gate enforcement happens in the stack.
 *
 * @param {string} requiredTokenKind  — e.g. "ring.pride.token.granted"
 * @param {string[]} grantedTokenKinds — array of token event kinds the workspace holds
 * @returns {boolean}
 */
export function hasToken(requiredTokenKind, grantedTokenKinds = []) {
  return grantedTokenKinds.includes(requiredTokenKind);
}

// ── Sulphera Rings ────────────────────────────────────────────────────────────

/**
 * Ring 8 — Visitor's Ring (entry point to Sulphera).
 * Accessible via: Infernal Meditation skill + inciting token from quest 0008_KLST.
 * This ring is the lobby — you stand in the presence of the Infernal Gods.
 * No Sin Ruler governs it; it is the antechamber of all seven.
 */
export const RING_VISITOR = {
  id: "ring_visitor",
  ring_number: 8,
  name: "Visitor's Ring",
  ruler: null,
  sin: null,
  vitriol_affinity: null,
  behavioral_contract:
    "The Visitor's Ring is Sulphera's antechamber. The Infernal Gods are present — " +
    "not as enemies but as presences. The player witnesses the Orrery from its edge. " +
    "Access requires the Infernal Meditation skill (taught by game-specific mentors, " +
    "e.g. Alfir in Game 7) and the inciting token delivered in quest 0008_KLST " +
    "(Demons and Diamonds). No combat — this ring is observational and ceremonial. " +
    "Clearing it opens the Ring of Pride.",
  tile_palette: "sulphera_antechamber",
  music_register: "infernal_presence",
  stack_event_prefix: "ring.visitor",
  // Access gate (not a ring token — a skill + quest gate)
  // Access: player must have the infernal_meditation perk.
  // That perk is itself quest-gated on 0009_KLST (Demons and Diamonds).
  // Check hasSulpheraAccess(unlockedPerks) from skillRegistry.js.
  requires_perk: "infernal_meditation",
  grants_token: null,           // Visitor's Ring grants no sin token; it IS the gate
  locked_by_token: null,        // Gated by skill + quest, not a prior ring's token
};

/**
 * Rings 1–7 — The 7 Sin Rings.
 * Traversal order: Pride (1) → Greed (2) → Envy (3) → Gluttony (4) → Sloth (5) → Wrath (6) → Lust (7)
 * Each ring, when cleared, generates a token from the ruling Sin Lord.
 * That token is consumed to enter the next ring.
 */
export const SINNERS_RINGS = [
  {
    id: "ring_pride",
    ring_number: 1,
    name: "Ring of Pride",
    ruler: "Lucifer",
    sin: "Pride",
    secondary: "Levity",
    sin_slug: "pride",
    ring_order: 1,
    vitriol_affinity: "L",           // Levity
    vitriol_pressure: "O",           // Ostentation — what pride performs
    behavioral_contract:
      "The Ring of Pride rewards those who act with conviction and punishes hesitation. " +
      "Lucifer's secondary nature is Levity — encounters tilt toward absurd grandeur. " +
      "Enemy encounters escalate if the player retreats without engaging. " +
      "The dungeon remembers whether the player bowed.",
    tile_palette: "obsidian_gold",
    music_register: "ceremonial",
    stack_event_prefix: "ring.pride",
    locked_by_token: null,                   // First sin ring — gated by Ring 8 (Visitor's Ring) access
    locked_by_ring: "ring_visitor",
    grants_token: ringTokenEventKind("pride"),
  },
  {
    id: "ring_greed",
    ring_number: 2,
    name: "Ring of Greed",
    ruler: "Mammon",
    sin: "Greed",
    secondary: "Ostentation",
    sin_slug: "greed",
    ring_order: 2,
    vitriol_affinity: "O",
    vitriol_pressure: "T",
    behavioral_contract:
      "The Ring of Greed is materially abundant and deliberately exhausting. " +
      "Mammon's secondary nature is Ostentation — everything is presented as precious. " +
      "The dungeon tracks items the player does not pick up. Negaya observes what is left to die. " +
      "Haldoro observes what the player does not claim when given the chance.",
    tile_palette: "brass_amber",
    music_register: "mercantile",
    stack_event_prefix: "ring.greed",
    locked_by_ring: "ring_pride",
    locked_by_token: ringTokenEventKind("pride"),
    grants_token: ringTokenEventKind("greed"),
  },
  {
    id: "ring_envy",
    ring_number: 3,
    name: "Ring of Envy",
    ruler: "Leviathan",
    sin: "Envy",
    secondary: "Ingenuity",
    sin_slug: "envy",
    ring_order: 3,
    vitriol_affinity: "I",           // Ingenuity (second I in VITRIOL)
    vitriol_pressure: "R",
    behavioral_contract:
      "The Ring of Envy is architecturally mirrored — everything encountered here has a copy. " +
      "Leviathan's secondary nature is Ingenuity — enemies adapt to what the player has already done. " +
      "The dungeon reads the player's prior run outcomes and spawns echoes of their own victories. " +
      "Vios observes choices the player skips when presented with apparent alternatives.",
    tile_palette: "deep_teal_silver",
    music_register: "contrapuntal",
    stack_event_prefix: "ring.envy",
    locked_by_ring: "ring_greed",
    locked_by_token: ringTokenEventKind("greed"),
    grants_token: ringTokenEventKind("envy"),
  },
  {
    id: "ring_gluttony",
    ring_number: 4,
    name: "Ring of Gluttony",
    ruler: "Beelzebub",
    sin: "Gluttony",
    secondary: "Tactility",
    sin_slug: "gluttony",
    ring_order: 4,
    vitriol_affinity: "T",
    vitriol_pressure: "V",
    behavioral_contract:
      "The Ring of Gluttony is sensory — tiles have texture, encounters have weight, " +
      "resources are plentiful but diminishing. Beelzebub's secondary nature is Tactility. " +
      "The dungeon rewards the player for engaging physically (movement, blocking, positioning). " +
      "Negaya observes everything consumed and not consumed in equal measure.",
    tile_palette: "rot_amber_flesh",
    music_register: "visceral",
    stack_event_prefix: "ring.gluttony",
    locked_by_ring: "ring_envy",
    locked_by_token: ringTokenEventKind("envy"),
    grants_token: ringTokenEventKind("gluttony"),
  },
  {
    id: "ring_sloth",
    ring_number: 5,
    name: "Ring of Sloth",
    ruler: "Belphegor",
    sin: "Sloth",
    secondary: "Reflectivity",
    sin_slug: "sloth",
    ring_order: 5,
    vitriol_affinity: "R",
    vitriol_pressure: "I",           // Introspection
    behavioral_contract:
      "The Ring of Sloth is the dungeon that does not pressure the player — and records how they " +
      "fill that absence. Belphegor's secondary nature is Reflectivity. " +
      "Time passes here. Waiting is mechanically valid. The dungeon watches what you do with stillness. " +
      "Vios is most active here — omission is the native language of Sloth.",
    tile_palette: "moss_grey_dust",
    music_register: "ambient_drone",
    stack_event_prefix: "ring.sloth",
    locked_by_ring: "ring_gluttony",
    locked_by_token: ringTokenEventKind("gluttony"),
    grants_token: ringTokenEventKind("sloth"),
  },
  {
    id: "ring_wrath",
    ring_number: 6,
    name: "Ring of Wrath",
    ruler: "Satan",
    sin: "Wrath",
    secondary: "Introspection",
    sin_slug: "wrath",
    ring_order: 6,
    vitriol_affinity: "I",           // Introspection (first I in VITRIOL)
    vitriol_pressure: "L",
    behavioral_contract:
      "The Ring of Wrath is the most dangerous ring. Satan's secondary nature is Introspection — " +
      "the dungeon turns aggression back on the player as self-examination. " +
      "Every kill here is tracked by Negaya without exception. " +
      "High-wrath play unlocks deeper Orrery readings but stresses the zero-kill gate for Luminyx's path.",
    tile_palette: "volcanic_crimson",
    music_register: "martial",
    stack_event_prefix: "ring.wrath",
    locked_by_ring: "ring_sloth",
    locked_by_token: ringTokenEventKind("sloth"),
    grants_token: ringTokenEventKind("wrath"),
  },
  {
    id: "ring_lust",
    ring_number: 7,
    name: "Ring of Lust",
    ruler: "Asmodeus",
    sin: "Lust",
    secondary: "Vitality",
    sin_slug: "lust",
    ring_order: 7,
    vitriol_affinity: "V",
    vitriol_pressure: "I",           // Ingenuity — desire invents
    behavioral_contract:
      "The Ring of Lust is the foundation of the Orrery's architecture — Asmodeus built the Orrery. " +
      "His secondary nature is Vitality. The dungeon is alive: tiles breathe, walls shift, " +
      "desire-crystals (structurally time crystals) appear as environmental hazards and rewards. " +
      "Clearing this ring unlocks the Asmodean Crystal path — the route through which Luminyx " +
      "falls from 5238AD to 1728AD. The dungeon is the most lore-dense in the series.",
    tile_palette: "rose_obsidian_crystal",
    music_register: "pulse",
    stack_event_prefix: "ring.lust",
    locked_by_ring: "ring_wrath",
    locked_by_token: ringTokenEventKind("wrath"),
    grants_token: ringTokenEventKind("lust"),
  },
];

/**
 * Ring 9 — The Royal Ring (final destination).
 * Gated by all 8 preceding rings (Visitor's Ring + all 7 Sin tokens).
 */
export const RING_ROYAL = {
  id: "ring_royal",
  ring_number: 9,
  name: "Royal Ring",
  ruler: null,
  sin: null,
  vitriol_affinity: null,
  behavioral_contract:
    "The Royal Ring is Sulphera's sovereign core. No dungeon mechanic — this is the Orrery's home. " +
    "The player has proven all 7 sin rings. The stack here reads the full arc of their choices. " +
    "The Void Wraiths present their complete record. " +
    "This is where the Orrery shows the player who they are through everything they did and didn't do.",
  tile_palette: "royal_sulphera",
  music_register: "sovereign",
  stack_event_prefix: "ring.royal",
  // Requires all 7 sin tokens + Visitor's Ring cleared
  locked_by_tokens: SINNERS_RINGS.map(r => r.grants_token),
  locked_by_ring: "ring_lust",
  grants_token: null,
};

// ── All Sulphera rings in structural order ────────────────────────────────────
// (Entry → Sin Rings → Royal Ring)
export const ALL_SULPHERA_RINGS = [RING_VISITOR, ...SINNERS_RINGS, RING_ROYAL];

// ── Fae Dungeons ──────────────────────────────────────────────────────────────
// The 5 Fae peoples are governed by Mona (Play and Torment, unified).
// They are NOT elemental proxies — each people has its own distinct nature.

export const FAE_DUNGEONS = [
  {
    id: "fae_dryad",
    fae_people: "Dryads",
    vitriol_affinity: "R",
    behavioral_contract:
      "Dryad dungeons are living — layouts grow between visits. " +
      "Dryads observe the player over time; this dungeon has continuity where others do not. " +
      "Mona's governance here is play as patient torment: the dungeon does not fight you, it watches, " +
      "and the longer you take the more it has learned. " +
      "Under Mona's domain, play and torment are not at odds — the Dryads enjoy your difficulty.",
    tile_palette: "bark_moss_canopy",
    music_register: "arboreal",
    stack_event_prefix: "fae.dryad",
    locked_by: null,
  },
  {
    id: "fae_undine",
    fae_people: "Undines",
    vitriol_affinity: "I",           // Introspection — depth, pressure, what lies beneath
    behavioral_contract:
      "Undine dungeons are fluid — passage and terrain shift with currents the player cannot see. " +
      "Undines communicate in indirect language; their encounters are negotiations, not battles. " +
      "Under Mona's domain, the torment is that play here requires surrender of control. " +
      "Haldoro is especially attentive in Undine spaces — silence means something different here.",
    tile_palette: "deep_water_bioluminescent",
    music_register: "tidal",
    stack_event_prefix: "fae.undine",
    locked_by: null,
  },
  {
    id: "fae_salamander",
    fae_people: "Salamanders",
    governor: "Lakota",              // Children of Lakota, God of the River of Fire of Sulphera
    vitriol_affinity: "V",
    behavioral_contract:
      "Salamander dungeons burn with clarifying fire — Lakota's fire is clarification-primary, not destruction-primary. " +
      "The dungeon is a forge: items are changed by passing through, the player may be changed too. " +
      "Under Mona's domain, the play is transformative pressure; the torment is that clarity reveals. " +
      "What the player brings in will not be what they bring out.",
    tile_palette: "ember_stone_magma",
    music_register: "forge",
    stack_event_prefix: "fae.salamander",
    locked_by: null,
  },
  {
    id: "fae_gnome",
    fae_people: "Gnomes",
    vitriol_affinity: "T",
    behavioral_contract:
      "Gnome dungeons are architecturally complex — crafted, layered, full of mechanisms. " +
      "Gnomes are makers; their dungeon is a demonstration. " +
      "Under Mona's domain, play is puzzle-as-torment: the dungeon is delightful and maddening simultaneously. " +
      "Vios tracks what mechanisms the player ignores when they could engage.",
    tile_palette: "stone_gear_earth",
    music_register: "clockwork",
    stack_event_prefix: "fae.gnome",
    locked_by: null,
  },
  {
    id: "fae_faerie",
    fae_people: "Faeries",
    vitriol_affinity: "L",           // Levity — Faeries are the most Mona-aligned
    behavioral_contract:
      "Faerie dungeons are the most overtly Mona-governed. Play IS torment, torment IS play — " +
      "not as paradox but as simple Faerie fact. The dungeon is absurd, joyful, punishing, and funny. " +
      "Spatial logic here is Mona's logic: things are where they should be for the game, not for reason. " +
      "All three Wraiths are active. The dungeon notices everything.",
    tile_palette: "luminous_impossible",
    music_register: "whimsical_dissonant",
    stack_event_prefix: "fae.faerie",
    locked_by: null,
  },
];

// ── Mines of Mt. Hieronymus ───────────────────────────────────────────────────

export const MINES_DUNGEONS = [
  {
    id: "mines_hieronymus",
    game_id: "7_KLGS",
    location: "Mt. Hieronymus, Aeralune",
    vitriol_affinity: "O",
    behavioral_contract:
      "The Mines are a physical excavation beneath Mt. Hieronymus between Azonithia and Castle Azoth. " +
      "Unlike the Sinner's Rings and Fae dungeons, the Mines are not governed by a supernatural patron. " +
      "They are a working mine: hazards are structural, encounters are with what lives in the deep. " +
      "Relevant to Hypatia's research — her notes reference veins of Asmodean crystal in the lower levels. " +
      "The player (Hypatia's apprentice) may find relevant materials here.",
    tile_palette: "raw_stone_mineshaft",
    music_register: "industrial_deep",
    stack_event_prefix: "mines.hieronymus",
    locked_by: null,
  },
];

// ── Flat index + helpers ──────────────────────────────────────────────────────

export const ALL_DUNGEONS = [...ALL_SULPHERA_RINGS, ...FAE_DUNGEONS, ...MINES_DUNGEONS];
export const DUNGEON_BY_ID = Object.fromEntries(ALL_DUNGEONS.map(d => [d.id, d]));

/**
 * Returns the 7 Sin Rings in traversal order (1–7).
 */
export function getSinnersRingsOrdered() {
  return [...SINNERS_RINGS].sort((a, b) => a.ring_order - b.ring_order);
}

/**
 * Check whether a dungeon is accessible given:
 *   - hasSulpheraAccess: player has Infernal Meditation + inciting token
 *   - grantedTokens: Set of token event kinds the workspace holds
 *
 * For Fae dungeons and Mines the only gate is whatever the game sets (default open).
 */
export function isDungeonAccessible(dungeonId, { hasSulpheraAccess = false, grantedTokens = new Set() } = {}) {
  const def = DUNGEON_BY_ID[dungeonId];
  if (!def) return false;

  // Visitor's Ring: requires Infernal Meditation + inciting token
  if (dungeonId === "ring_visitor") return hasSulpheraAccess;

  // Royal Ring: requires all 7 sin tokens
  if (dungeonId === "ring_royal") {
    return hasSulpheraAccess &&
      (RING_ROYAL.locked_by_tokens ?? []).every(t => grantedTokens.has(t));
  }

  // Sin Rings: requires Sulphera access + prior ring's token
  if (def.locked_by_token) {
    return hasSulpheraAccess && grantedTokens.has(def.locked_by_token);
  }
  // Pride: just needs Sulphera access (Visitor's Ring clears it)
  if (dungeonId === "ring_pride") return hasSulpheraAccess;

  // Fae / Mines: no Sulphera gate
  return true;
}

// Ko's Labyrnth â€” native Orrery registry.
//
// Spelling is canonical: Labyrnth, not Labyrinth.
// The missing 'i' encodes the Nth-dimensional nature of the structure:
// each game is an Nth-dimensional manifold of the same philosophical space
// where N is the current Quack count (number of attested tongues).
//
// The anthology is a 31-game philosophical dissertation in playable form.
// Its macro-topology is a figure-eight: two hub games (G5, G7) create two
// loops sharing a crossing point â€” MÃ¶bius-adjacent in structure.
//
// The exoteric sequence is release order.
// The esoteric sequence is different for every player.
//
// â”€â”€ Interchange weight semantics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//
// Each GameNode carries a sparse list of outgoing WeightEdges to other games.
// Each edge has:
//   target:  the game being influenced (1-based game_id)
//   weight:  base influence strength (0-255; 255 = maximum)
//   tongue:  which Quack gate this edge â€” the tongue whose attestation
//            activates this dimension of influence
//
// Effective weight = base_weight     if quack_count >= tongue
//                  = base_weight / 4  otherwise (dormant: dimension exists
//                                     but has not yet been named into legibility)
//
// Any (from, to) pair not listed in outgoing has background weight BACKGROUND.
// Nothing is zero â€” the anthology is a coherent whole.
//
// Adding new games: add a GameNode + its edge list. No existing data changes.
// Adding new tongues: new edges reference the new tongue number. Dormant until
// that Quack is named, at which point the dimension activates across all games
// that reference it.

// â”€â”€ Weight constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/// Default background connectivity â€” every game in the anthology influences
/// every other game at minimum (it is a single philosophical work).
pub const BACKGROUND: u8 = 8;

// Named weight tiers
pub const W_SEQ:    u8 = 200; // direct sequential within an arc (Gâ†’G+1)
pub const W_HUB_FW: u8 = 200; // hub outgoing to its primary forward arc
pub const W_HUB_BK: u8 = 160; // hub outgoing to its summarised backward arc
pub const W_HUB_HUB:u8 = 200; // hub-to-hub (the figure-eight crossing weight)
pub const W_ARC_HUB:u8 = 160; // arc game arriving at its hub
pub const W_MIRROR: u8 = 140; // strong thematic mirror (shared character/event)
pub const W_THEME:  u8 = 120; // medium thematic connection
pub const W_TONGUE: u8 = 100; // tongue-register adjacency within a group
pub const W_CROSS:  u8 =  80; // cross-arc tongue resonance
pub const W_REV:    u8 =  60; // reverse influence (laterâ†’earlier, acknowledging origin)
pub const W_WEAK:   u8 =  40; // weak cross-arc mention
pub const W_TRACE:  u8 =  20; // minimal connection (present but not central)

// â”€â”€ Data structures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/// A directed influence edge from one game to another.
#[derive(Copy, Clone)]
pub struct WeightEdge {
    /// Target game (1-based game_id).  Can exceed 31 as the anthology grows.
    pub target:  u8,
    /// Base influence weight (0â€“255).
    pub weight:  u8,
    /// Tongue number that gates this dimension.  If quack_count < tongue,
    /// the effective weight is weight/4 (dormant).  0 = always active.
    pub tongue:  u8,
}

/// A Shygazun state exit condition for a game.
/// When a player reaches this state in this game, the flag propagates
/// to other games via their interchange weights.
#[derive(Copy, Clone)]
pub struct ExitFlag {
    /// Shygazun byte table address of the state (e.g. 193 = Soa = Conscious persistence).
    pub addr: u32,
    /// Human-readable label for the Orrery layer_node.
    pub name: &'static [u8],
}

/// One game in the Ko's Labyrnth anthology.
pub struct GameNode {
    /// 1-based game_id.  The anthology currently spans 1â€“31.
    pub game_id:         u8,
    /// Title in the release language.
    pub title:           &'static [u8],
    /// The game's name expressed in Shygazun coordinate space.
    /// Filled in as the language develops; b"" until then.
    pub shygazun_name:   &'static [u8],
    /// True for the two hub games (G5 Truth Be Told, G7 Alchemist's Labor).
    pub is_hub:          bool,
    /// b"lower", b"upper", or b"" (non-hub).
    pub hub_arc:         &'static [u8],
    /// Shygazun tongue registers this game's philosophical space spans.
    /// A game exists at the intersection of all listed tongues simultaneously.
    /// Each tongue N = the Nth Quack; its attestation unlocks that register's
    /// dimensionality in this game's state space.
    /// Multiple entries reflect the fractal nature: the same game is a
    /// different argument depending on which tongues the player has attested.
    pub tongue_affinities: &'static [u8],
    /// Sparse outgoing influence edges to other games.
    /// All (from, to) pairs not listed here use BACKGROUND weight.
    pub outgoing:        &'static [WeightEdge],
    /// Shygazun state addresses this game can produce as exit conditions.
    /// These propagate through the Orrery when the game concludes.
    pub exit_flags:      &'static [ExitFlag],
}

// â”€â”€ Outgoing edge lists (one static per game) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//
// Tongue column: the tongue whose attestation activates this dimension.
// 0 = always active (topology-invariant connection, not tongue-gated).
//
// The figure-eight crossing: G5â†’G7 and G7â†’G5 carry W_HUB_HUB.

static E01: &[WeightEdge] = &[
    WeightEdge { target:  2, weight: W_SEQ,    tongue:  1 }, // arc sequential
    WeightEdge { target:  5, weight: W_ARC_HUB,tongue:  1 }, // toward Hub 1
    WeightEdge { target:  7, weight: W_THEME,  tongue:  8 }, // Great Obscenity â†’ Labyrinth
    WeightEdge { target: 28, weight: W_MIRROR, tongue:  1 }, // Luminyx echo at G28
    WeightEdge { target: 31, weight: W_TONGUE, tongue: 37 }, // origin â†’ Great Work (Circle)
];

static E02: &[WeightEdge] = &[
    WeightEdge { target:  3, weight: W_SEQ,    tongue:  2 },
    WeightEdge { target:  5, weight: W_ARC_HUB,tongue:  2 },
    WeightEdge { target: 21, weight: W_WEAK,   tongue: 27 }, // Thool seeds: G2 begins
];

static E03: &[WeightEdge] = &[
    WeightEdge { target:  4, weight: W_SEQ,    tongue:  4 },
    WeightEdge { target:  5, weight: W_ARC_HUB,tongue:  4 },
    WeightEdge { target: 14, weight: W_MIRROR, tongue: 13 }, // chimeras born here
];

static E04: &[WeightEdge] = &[
    WeightEdge { target:  5, weight: W_HUB_FW, tongue:  8 }, // Arc 1 â†’ Hub 1
    WeightEdge { target: 15, weight: W_WEAK,   tongue: 14 }, // Sulphera leakage â†’ G15 yokai
];

// Hub 1 â€” Truth Be Told
static E05: &[WeightEdge] = &[
    WeightEdge { target:  1, weight: W_HUB_BK, tongue:  1 }, // backward: Arc 1 summary
    WeightEdge { target:  2, weight: W_HUB_BK, tongue:  2 },
    WeightEdge { target:  3, weight: W_HUB_BK, tongue:  4 },
    WeightEdge { target:  4, weight: W_HUB_BK, tongue:  8 },
    WeightEdge { target:  6, weight: W_HUB_FW, tongue:  7 }, // forward: into Arc 2
    WeightEdge { target:  7, weight: W_HUB_HUB,tongue:  0 }, // hub crossing (topology-invariant)
    WeightEdge { target: 20, weight: W_THEME,  tongue: 26 }, // Truth assembles â†’ Daath
];

static E06: &[WeightEdge] = &[
    WeightEdge { target:  7, weight: W_HUB_FW, tongue:  7 }, // arc â†’ Hub 2
    WeightEdge { target: 13, weight: W_MIRROR, tongue:  8 }, // Azoth born in Obscenity trigger
];

// Hub 2 â€” An Alchemist's Labor of Love  (Ko's Labyrnth, game 7)
static E07: &[WeightEdge] = &[
    WeightEdge { target:  1, weight: W_CROSS,  tongue:  1 }, // Labyrinth echoes origin
    WeightEdge { target:  5, weight: W_HUB_HUB,tongue:  0 }, // hub crossing
    WeightEdge { target:  6, weight: W_HUB_BK, tongue:  7 }, // backward into Arc 2
    WeightEdge { target:  8, weight: W_HUB_FW, tongue:  9 }, // forward: Arc 3
    WeightEdge { target:  9, weight: W_HUB_FW, tongue: 10 },
    WeightEdge { target: 10, weight: W_HUB_FW, tongue: 11 },
    WeightEdge { target: 11, weight: W_HUB_FW, tongue: 12 },
    WeightEdge { target: 13, weight: W_THEME,  tongue:  8 }, // Azoth throughline
    WeightEdge { target: 17, weight: W_MIRROR, tongue: 23 }, // Saelith born here
    WeightEdge { target: 31, weight: W_THEME,  tongue: 37 }, // hub feeds Great Work
];

static E08: &[WeightEdge] = &[
    WeightEdge { target:  9, weight: W_SEQ,    tongue:  9 },
    WeightEdge { target: 17, weight: W_MIRROR, tongue: 23 }, // Saelith's past
];

static E09: &[WeightEdge] = &[
    WeightEdge { target: 10, weight: W_SEQ,    tongue: 10 },
    WeightEdge { target: 59, weight: W_TRACE,  tongue:  0 }, // Alzedros: future ALZD suffix
];

static E10: &[WeightEdge] = &[
    WeightEdge { target: 11, weight: W_SEQ,    tongue: 11 },
    WeightEdge { target: 31, weight: W_THEME,  tongue: 37 }, // Ko-centered â†’ Great Work
];

static E11: &[WeightEdge] = &[
    WeightEdge { target: 12, weight: W_SEQ,    tongue: 12 },
];

static E12: &[WeightEdge] = &[
    WeightEdge { target: 13, weight: W_SEQ,    tongue:  3 }, // Sha arc
    WeightEdge { target: 26, weight: W_MIRROR, tongue: 32 }, // Sha arc bookend
];

static E13: &[WeightEdge] = &[
    WeightEdge { target: 14, weight: W_SEQ,    tongue: 13 },
    WeightEdge { target:  7, weight: W_REV,    tongue:  8 }, // Azoth back to source
    WeightEdge { target: 31, weight: W_WEAK,   tongue: 37 }, // alchemical throughline â†’ end
];

static E14: &[WeightEdge] = &[
    WeightEdge { target: 15, weight: W_SEQ,    tongue: 14 },
    WeightEdge { target:  3, weight: W_MIRROR, tongue:  4 }, // chimera origin
];

static E15: &[WeightEdge] = &[
    WeightEdge { target: 16, weight: W_SEQ,    tongue: 15 },
];

static E16: &[WeightEdge] = &[
    WeightEdge { target: 17, weight: W_SEQ,    tongue: 23 },
];

static E17: &[WeightEdge] = &[
    WeightEdge { target: 18, weight: W_SEQ,    tongue: 32 }, // Saelith â†’ Convergence
    WeightEdge { target:  7, weight: W_MIRROR, tongue: 23 }, // born in G7
];

static E18: &[WeightEdge] = &[
    WeightEdge { target: 19, weight: W_SEQ,    tongue: 32 }, // Convergence â†’ Arc 7
    WeightEdge { target:  1, weight: W_TRACE,  tongue:  0 }, // Mystic Pines Ã— KLGS crossing
];

static E19: &[WeightEdge] = &[
    WeightEdge { target: 20, weight: W_SEQ,    tongue: 25 },
    WeightEdge { target:  2, weight: W_THEME,  tongue: 27 }, // Thool seeds planted at G2
];

static E20: &[WeightEdge] = &[
    WeightEdge { target: 21, weight: W_SEQ,    tongue: 26 },
];

static E21: &[WeightEdge] = &[
    WeightEdge { target: 22, weight: W_SEQ,    tongue: 31 },
    WeightEdge { target:  2, weight: W_MIRROR, tongue: 27 }, // Thool fully legible
];

static E22: &[WeightEdge] = &[
    WeightEdge { target: 23, weight: W_SEQ,    tongue: 30 },
];

static E23: &[WeightEdge] = &[
    WeightEdge { target: 24, weight: W_SEQ,    tongue: 29 },
    WeightEdge { target: 23, weight: W_TRACE,  tongue:  0 }, // Po'Elfan echoes forward
];

static E24: &[WeightEdge] = &[
    WeightEdge { target: 25, weight: W_SEQ,    tongue: 29 },
];

static E25: &[WeightEdge] = &[
    WeightEdge { target: 26, weight: W_SEQ,    tongue: 28 },
];

static E26: &[WeightEdge] = &[
    WeightEdge { target: 27, weight: W_SEQ,    tongue: 32 }, // Sha's end â†’ Arc 10
    WeightEdge { target: 12, weight: W_MIRROR, tongue: 32 }, // Sha cycle closes
];

static E27: &[WeightEdge] = &[
    WeightEdge { target: 28, weight: W_SEQ,    tongue: 33 },
];

static E28: &[WeightEdge] = &[
    WeightEdge { target: 29, weight: W_SEQ,    tongue: 34 },
    WeightEdge { target:  1, weight: W_MIRROR, tongue:  1 }, // Luminyx honored: back to origin
    WeightEdge { target: 31, weight: W_THEME,  tongue: 37 }, // legacy feeds Great Work
];

static E29: &[WeightEdge] = &[
    WeightEdge { target: 30, weight: W_SEQ,    tongue: 35 },
];

static E30: &[WeightEdge] = &[
    WeightEdge { target: 31, weight: W_SEQ,    tongue: 36 }, // Death â†’ Great Work
];

static E31: &[WeightEdge] = &[
    WeightEdge { target:  1, weight: W_REV,    tongue:  1 }, // Great Work acknowledges origin
    WeightEdge { target:  5, weight: W_REV,    tongue:  0 }, // closes the lower loop
    WeightEdge { target:  7, weight: W_REV,    tongue:  0 }, // closes the upper loop
];

// â”€â”€ Exit flags â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//
// These are the Shygazun state addresses that each game can produce.
// Filled in per game; empty slices are placeholders pending lore finalisation.
//
// Key addresses used as exit flags:
//   9  = Ta (Active being / presence)
//   19 = Ko (Experience / intuition)
//   82 = Kael (Cluster / completion event)
//   156 = Sa (Root volume mounted â€” world fully accessed)
//   193 = Soa (Conscious persistence â€” player state persisted)

static F01: &[ExitFlag] = &[
    ExitFlag { addr: 193, name: b"Soa-G01" },  // Luminyx mortal chapter complete
];
static F05: &[ExitFlag] = &[
    ExitFlag { addr: 193, name: b"Soa-G05" },
    ExitFlag { addr:  82, name: b"Kael-Hub1" }, // lower hub cluster complete
];
static F07: &[ExitFlag] = &[
    ExitFlag { addr: 193, name: b"Soa-G07" },
    ExitFlag { addr:  82, name: b"Kael-Hub2" }, // upper hub cluster complete
    ExitFlag { addr:  19, name: b"Ko-Labyrnth" }, // Ko's Labyrnth cleared
];
static F31: &[ExitFlag] = &[
    ExitFlag { addr:  82, name: b"Kael-GreatWork" },
    ExitFlag { addr:  19, name: b"Ko-Final" },
    ExitFlag { addr: 156, name: b"Sa-Complete" }, // all realms accessed
];

// Placeholder for games without defined exit flags yet
static F_EMPTY: &[ExitFlag] = &[];

// â”€â”€ Game node table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

pub static GAMES: &[GameNode] = &[
    // â”€â”€ Arc 1: Earth and the first wound â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 1, title: b"Princess of Eclipses",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[1],  // Lotus â€” initiation, the first wound
        outgoing: E01, exit_flags: F01,
    },
    GameNode {
        game_id: 2, title: b"Knights of the Veil",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[2],  // Rose â€” spectrum of deception, narrative colors
        outgoing: E02, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 3, title: b"Fullmetal Forest",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[4],  // Daisy â€” network / structural (cybernetic forest)
        outgoing: E03, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 4, title: b"Secrets of Neverland",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[8],  // Cannabis â€” consciousness emerging post-nuclear
        outgoing: E04, exit_flags: F_EMPTY,
    },
    // â”€â”€ Hub 1 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 5, title: b"Truth Be Told",
        shygazun_name: b"", is_hub: true, hub_arc: b"lower",
        tongue_affinities: &[6],  // Aster â€” time topology (assembling truth across time)
        outgoing: E05, exit_flags: F05,
    },
    // â”€â”€ Arc 2: The Great Obscenity and the Labyrnth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 6, title: b"As Within So Without",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[7],  // Grapevine â€” route/path to the Labyrnth
        outgoing: E06, exit_flags: F_EMPTY,
    },
    // â”€â”€ Hub 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 7, title: b"An Alchemist's Labor of Love",
        shygazun_name: b"", is_hub: true, hub_arc: b"upper",
        tongue_affinities: &[5],  // AppleBlossom â€” elemental alchemy
        outgoing: E07, exit_flags: F07,
    },
    // â”€â”€ Arc 3: After the Labyrnth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 8, title: b"Reign of Nobody",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[9],  // Dragon â€” void organism (Saelith from the past)
        outgoing: E08, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 9, title: b"Rise of Alzedros",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[10], // Virus â€” relational modes
        outgoing: E09, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 10, title: b"The Voice of Ko",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[11], // Bacteria â€” electrodynamic (direct divine connection)
        outgoing: E10, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 11, title: b"Icons of Time",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[12], // Excavata â€” helical-MÃ¶bius (temporal recursion)
        outgoing: E11, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 4: Sha's Arc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 12, title: b"Students of Sha",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[3],  // Sakura â€” spatial/directional (the intellectual path)
        outgoing: E12, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 13, title: b"Ghosts of Azoth",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[8],  // Cannabis â€” alchemical consciousness (Azoth = BreathOfKo)
        outgoing: E13, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 5: Archon War and the Lost â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 14, title: b"Chimeras of The Archons",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[13], // Archaeplastida â€” cellular liberation
        outgoing: E14, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 15, title: b"Lost Yokai",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[14], // Myxozoa â€” parasitic complexity
        outgoing: E15, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 16, title: b"Battered Stars",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[15], // Archea â€” archaic resilience
        outgoing: E16, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 6: Saelith's Arc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 17, title: b"Saelith's Mercy",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[23], // Faerie â€” Saelith = FaeDjinn hybrid, born G7
        outgoing: E17, exit_flags: F_EMPTY,
    },
    // â”€â”€ Convergence: Mystic Pines x KLGS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 18, title: b"Mystic Blood",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[32], // Moon â€” convergence between series
        outgoing: E18, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 7: The Cause and Hidden Knowledge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 19, title: b"Tides of The Cause",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[25], // Fold â€” topology fold (tides of movement)
        outgoing: E19, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 20, title: b"Daath Most Have Seen",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[26], // Topology â€” hidden knowledge (Daath)
        outgoing: E20, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 21, title: b"Callsigns of Thool",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[27], // Phase â€” phase transition, reading signals
        outgoing: E21, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 8: Void and Requiem â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 22, title: b"Horrors of The Void",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[31], // Blood â€” void blood
        outgoing: E22, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 23, title: b"Requiem of Po'Elfan",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[30], // Prion â€” recursive error (anxiety as prion)
        outgoing: E23, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 24, title: b"Polar Shift",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[29], // Curvature â€” spacetime shift
        outgoing: E24, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 9: Galactic and Fires â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 25, title: b"Galactic Hallows",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[28], // Gradient â€” galactic gradient
        outgoing: E25, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 26, title: b"Fires of Sha",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[32], // Moon â€” Sha's purifying end (Koâ†â†’Sha cycle close)
        outgoing: E26, exit_flags: F_EMPTY,
    },
    // â”€â”€ Arc 10: Toward the Great Work â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    GameNode {
        game_id: 27, title: b"Gourds of Ash",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[36, 33], // Fang + Koi
        outgoing: E27, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 28, title: b"Legacy of Luminyx",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[33, 34], // Koi + Rope
        outgoing: E28, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 29, title: b"Barkeep of Broken Dreams",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[35], // Hook â€” predation by mechanism
        outgoing: E29, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 30, title: b"Death of an Empress",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[34], // Rope â€” bound to Luminyx's legacy
        outgoing: E30, exit_flags: F_EMPTY,
    },
    GameNode {
        game_id: 31, title: b"The Great Work",
        shygazun_name: b"", is_hub: false, hub_arc: b"",
        tongue_affinities: &[37], // Circle â€” unity by ritual (series culmination)
        outgoing: E31, exit_flags: F31,
    },
];

// â”€â”€ Orrery query API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/// Look up a GameNode by its 1-based game_id.
/// Returns None if the game_id is not in the current registry.
pub fn game_by_id(id: u8) -> Option<&'static GameNode> {
    GAMES.iter().find(|g| g.game_id == id)
}

/// Compute the effective interchange weight from game `from_id` to `to_id`
/// given the current Quack count (number of tongues attested so far).
///
/// A quack_count of 0 means no tongues have been named â€” all tongue-gated
/// dimensions are dormant (weight/4).  At quack_count >= 38 (current ledger
/// maximum), all current dimensions are active.  As the ledger grows beyond
/// 38, new edges with higher tongue numbers become available.
pub fn effective_weight(from_id: u8, to_id: u8, quack_count: u8) -> u8 {
    let node = match game_by_id(from_id) { Some(n) => n, None => return 0 };
    for edge in node.outgoing {
        if edge.target == to_id {
            return if edge.tongue == 0 || quack_count >= edge.tongue {
                edge.weight
            } else {
                edge.weight / 4
            };
        }
    }
    BACKGROUND
}

/// Return all games that are hubs.
pub fn hubs() -> impl Iterator<Item = &'static GameNode> {
    GAMES.iter().filter(|g| g.is_hub)
}

/// Return all games with the given tongue affinity.
pub fn games_by_tongue(tongue: u8) -> impl Iterator<Item = &'static GameNode> {
    GAMES.iter().filter(move |g| g.tongue_affinities.contains(&tongue))
}

/// Propagate an exit flag from `from_id` to all other games,
/// returning an iterator of (target_game_id, effective_weight) pairs
/// above the BACKGROUND threshold.
///
/// The Orrery calls this when a game concludes to record which
/// layer_nodes should be activated in downstream games.
pub fn propagate(from_id: u8, quack_count: u8)
    -> impl Iterator<Item = (u8, u8)>
{
    let weights: &'static [WeightEdge] = match game_by_id(from_id) {
        Some(n) => n.outgoing,
        None    => &[],
    };
    weights.iter().filter_map(move |e| {
        let w = if e.tongue == 0 || quack_count >= e.tongue {
            e.weight
        } else {
            e.weight / 4
        };
        if w > BACKGROUND { Some((e.target, w)) } else { None }
    })
}

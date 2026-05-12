// zone_registry.rs -- World zone definitions for Ko's Labyrinth (7_KLGS).
//
// Three realms: Lapidus (overworld), Mercurie (Faewilds), Sulphera (underworld).
//
// ZoneKind determines what the game loop does when the player enters:
//
//   Town        -- inhabited, NPCs present, shops, zero enemy spawns, saveable
//   Market      -- trade-focused safe zone; shopkeepers, stalls
//   Temple      -- sacred/narrative; quests trigger; atmosphere-rendered
//   Wilderness  -- foraging, exploration; light random encounters possible
//   Dungeon     -- BSP-generated combat area; nonce/re-entry rules apply
//   Rest        -- guaranteed safe; player can sleep/save; minor NPC presence
//   Threshold   -- liminal atmospheric space; narrative text only, no spawns
//   Chamber     -- specific authored room; narrative/puzzle; no BSP
//   BossArena   -- single combat encounter; not randomised; major enemy
//
// Combat zones: Dungeon, BossArena (and Wilderness when encounter rolls).
// All others are non-adversarial by definition.
//
// Exits are stored as a static slice of zone ID byte strings -- the navigation
// graph. Directional labels are omitted at this level; the game loop presents
// them as a list the player chooses from.

use crate::ko_flags;

// ── Zone kinds ────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum ZoneKind {
    Town,
    Market,
    Temple,
    Wilderness,
    Dungeon,
    Rest,
    Threshold,
    Chamber,
    BossArena,
}

impl ZoneKind {
    pub fn is_combat(self) -> bool {
        matches!(self, ZoneKind::Dungeon | ZoneKind::BossArena)
    }
    pub fn is_safe(self) -> bool {
        matches!(self, ZoneKind::Town | ZoneKind::Market | ZoneKind::Temple
                     | ZoneKind::Rest | ZoneKind::Chamber)
    }
    pub fn can_forage(self) -> bool {
        matches!(self, ZoneKind::Wilderness | ZoneKind::Threshold)
    }
}

// ── Realm ─────────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum Realm { Lapidus, Mercurie, Sulphera }

// ── Zone definition ───────────────────────────────────────────────────────────

pub struct ZoneDef {
    pub id:       &'static [u8],
    pub name:     &'static [u8],
    pub realm:    Realm,
    pub kind:     ZoneKind,
    pub desc:     &'static [u8],
    /// ko_flag that must be set for the player to enter; 0xFF = always open.
    pub requires: u8,
    pub exits:    &'static [&'static [u8]],
}

impl ZoneDef {
    pub fn open(&self) -> bool {
        self.requires == 0xFF || ko_flags::ko_test(self.requires)
    }
}

// ── Helper -- look up zone by ID ──────────────────────────────────────────────

pub fn zone_by_id(id: &[u8]) -> Option<&'static ZoneDef> {
    ALL_ZONES.iter().find(|z| z.id == id)
}

// ── Zone table ────────────────────────────────────────────────────────────────
//
// Each entry: (id, name, realm, kind, desc, requires, exits).
// requires = 0xFF means always accessible.
// Exits are listed in the order they should appear in the navigation menu.

pub static ALL_ZONES: &[ZoneDef] = &[

    // =========================================================================
    // LAPIDUS -- THE OVERWORLD
    // =========================================================================

    // -- Wiltoll Lane ----------------------------------------------------------
    ZoneDef {
        id:       b"wiltoll_lane",
        name:     b"Wiltoll Lane",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Town,
        desc:     b"The lane is quiet at this hour. Lush hedgerows press close. \
                     Somewhere above, Mt. Elaene holds the cold. \
                     Elsa is three doors down. Hypatia's light is on at the far end.",
        requires: 0xFF,
        exits:    &[b"mt_elaene_path", b"hopefare", b"azonithia_west",
                    b"lapidus_elsa_house", b"lapidus_hypatia_house"],
    },

    // -- Elsa's house ----------------------------------------------------------
    ZoneDef {
        id:       b"lapidus_elsa_house",
        name:     b"Elsa's House",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Town,
        desc:     b"Warm, well-kept, thirty years inhabited. \
                     A chair by the window. Clean kitchen corner. \
                     The house of someone who has seen things without making a scene of it.",
        requires: 0xFF,
        exits:    &[b"wiltoll_lane"],
    },

    // -- Hypatia's house -------------------------------------------------------
    ZoneDef {
        id:       b"lapidus_hypatia_house",
        name:     b"Hypatia's House",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Chamber,
        desc:     b"The house with the light on at strange hours. \
                     The workshop is organized in the way that only makes sense \
                     to the person who organized it.",
        requires: 0xFF,
        exits:    &[b"wiltoll_lane"],
    },

    // -- Mt. Elaene path -------------------------------------------------------
    ZoneDef {
        id:       b"mt_elaene_path",
        name:     b"Mt. Elaene Path",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Wilderness,
        desc:     b"The slope is gentle here. Snowmelt runs through the stones. \
                     Mosses that glow faintly at night edge the trail.",
        requires: 0xFF,
        exits:    &[b"wiltoll_lane"],
    },

    // -- Azonithia Ave (west) -- Heartvein Heights / Youthspring ---------------
    ZoneDef {
        id:       b"azonithia_west",
        name:     b"Heartvein Heights",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Town,
        desc:     b"Cobblestones older than the castle. Apothecary lanterns burn gold. \
                     Children circle the well; their laughter carries far.",
        requires: 0xFF,
        exits:    &[b"wiltoll_lane", b"temple_quarter", b"hopefare"],
    },

    // -- Temple Quarter / Goldshoot --------------------------------------------
    ZoneDef {
        id:       b"temple_quarter",
        name:     b"Temple Quarter",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Temple,
        desc:     b"Goldshoot alley runs behind the great temple. Smoke of incense \
                     and burnt gold. Sidhal tends the outer court each morning.",
        requires: 0xFF,
        exits:    &[b"azonithia_west", b"june_street", b"castle_azoth_gates"],
    },

    // -- June Street Markets ---------------------------------------------------
    ZoneDef {
        id:       b"june_street",
        name:     b"June Street",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Market,
        desc:     b"Three stalls shoulder to shoulder: provisions, arms, and herbs. \
                     The herbalist keeps her prices fair; the arms dealer does not.",
        requires: 0xFF,
        exits:    &[b"temple_quarter", b"hopefare", b"castle_azoth_gates"],
    },

    // -- Hopefare (upper slums) ------------------------------------------------
    ZoneDef {
        id:       b"hopefare",
        name:     b"Hopefare",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Town,
        desc:     b"The buildings lean on each other here, as though for warmth. \
                     Laundry lines the alleys. Someone is always cooking.",
        requires: 0xFF,
        exits:    &[b"wiltoll_lane", b"azonithia_west", b"june_street",
                    b"orebustle", b"serpents_pass"],
    },

    // -- Orebustle (lower slums) -----------------------------------------------
    ZoneDef {
        id:       b"orebustle",
        name:     b"Orebustle",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Town,
        desc:     b"Deeper in the warrens. The smell of iron and old stone. \
                     Forge-smoke drifts from half-shuttered windows.",
        requires: 0xFF,
        exits:    &[b"hopefare", b"serpents_pass", b"mt_hieronymus_foothills"],
    },

    // -- Serpent's Pass --------------------------------------------------------
    ZoneDef {
        id:       b"serpents_pass",
        name:     b"Serpent's Pass",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Wilderness,
        desc:     b"A narrow defile between old walls. Wells and Lavelle have their \
                     camp at the far end, where the aqueduct stone is laid.",
        requires: 0xFF,
        exits:    &[b"hopefare", b"orebustle", b"mt_hieronymus_foothills",
                    b"ocean_shore"],
    },

    // -- Mt. Hieronymus foothills ----------------------------------------------
    ZoneDef {
        id:       b"mt_hieronymus_foothills",
        name:     b"Mt. Hieronymus Foothills",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Wilderness,
        desc:     b"Sparse pine and grey scree. The mine entrance is an old cut \
                     in the rock face, propped with dark timber.",
        requires: 0xFF,
        exits:    &[b"orebustle", b"serpents_pass", b"lapidus_mines"],
    },

    // -- Lapidus Mines ---------------------------------------------------------
    ZoneDef {
        id:       b"lapidus_mines",
        name:     b"Lapidus Mines",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Dungeon,
        desc:     b"The mine is quiet except for dripping water. The old shafts \
                     smell of sulphur and cold copper. \
                     The deepest level opens somewhere that is not the mine.",
        requires: 0xFF,
        exits:    &[b"mt_hieronymus_foothills", b"mercurie_threshold"],
    },

    // -- Castle Azoth gates ----------------------------------------------------
    ZoneDef {
        id:       b"castle_azoth_gates",
        name:     b"Castle Azoth Gates",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Threshold,
        desc:     b"The gates are open in daylight. Guards stand at ease. \
                     The lottery drum sits on its plinth, visible through the arch.",
        requires: 0xFF,
        exits:    &[b"june_street", b"temple_quarter", b"castle_azoth_halls"],
    },

    // -- Castle Azoth interior halls -------------------------------------------
    ZoneDef {
        id:       b"castle_azoth_halls",
        name:     b"Castle Azoth",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Chamber,
        desc:     b"The Stelladeva family's seat. Tapestries of the founding. \
                     The scent of beeswax and old ambition.",
        requires: ko_flags::F_CASTLE_AZOTH_SEEN,
        exits:    &[b"castle_azoth_gates"],
    },

    // -- Ocean shore -----------------------------------------------------------
    ZoneDef {
        id:       b"ocean_shore",
        name:     b"Ocean Shore",
        realm:    Realm::Lapidus,
        kind:     ZoneKind::Wilderness,
        desc:     b"The water is dark and honest. Salt wind. The horizon holds \
                     nothing you can name -- only distance and light. \
                     On certain tides, the boundary between worlds grows thin here.",
        requires: 0xFF,
        exits:    &[b"serpents_pass", b"mercurie_threshold"],
    },

    // =========================================================================
    // MERCURIE -- THE FAEWILDS
    // =========================================================================

    // -- Mercurie threshold ----------------------------------------------------
    ZoneDef {
        id:       b"mercurie_threshold",
        name:     b"Mercurie Threshold",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Threshold,
        desc:     b"The light bends here. The path behind is Lapidus -- \
                     the sea, or the dark of the mine. Ahead, something older \
                     holds its breath and watches you arrive.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"ocean_shore", b"lapidus_mines", b"tideglass", b"rootbloom"],
    },

    // -- Tideglass -------------------------------------------------------------
    ZoneDef {
        id:       b"tideglass",
        name:     b"Tideglass",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Wilderness,
        desc:     b"Water moves through the air as well as the ground. The Fae here \
                     have made themselves into light refracted through still pools.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"mercurie_threshold", b"cindergrove", b"rootbloom"],
    },

    // -- Cindergrove -----------------------------------------------------------
    ZoneDef {
        id:       b"cindergrove",
        name:     b"Cindergrove",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Wilderness,
        desc:     b"Ash trees whose bark is warm to the touch. Embers drift upward \
                     on no wind. The Fae of fire live carefully here.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"tideglass", b"rootbloom", b"thornveil"],
    },

    // -- Rootbloom -- most approachable Fae settlement -------------------------
    ZoneDef {
        id:       b"rootbloom",
        name:     b"Rootbloom",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Town,
        desc:     b"A Fae settlement woven between the roots of the great trees. \
                     Lanterns of living bioluminescence. Children -- Fae children -- \
                     regard you with curiosity rather than alarm.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"mercurie_threshold", b"tideglass", b"cindergrove",
                    b"thornveil", b"dewspire"],
    },

    // -- Thornveil -------------------------------------------------------------
    ZoneDef {
        id:       b"thornveil",
        name:     b"Thornveil",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Wilderness,
        desc:     b"The bramble grows in deliberate patterns here. The Fae have \
                     woven it as a warning and a wall. They watch from inside it.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"cindergrove", b"rootbloom", b"dewspire"],
    },

    // -- Dewspire -- Fae Queen Amelia's domain ---------------------------------
    ZoneDef {
        id:       b"dewspire",
        name:     b"Dewspire",
        realm:    Realm::Mercurie,
        kind:     ZoneKind::Temple,
        desc:     b"At the crown of the oldest tree, a spire of dewdrops held in \
                     permanent suspension. The Fae Queen does not live here; \
                     she IS here, in the way a cathedral is its architecture.",
        requires: ko_flags::F_MERCURIE_OPEN,
        exits:    &[b"rootbloom", b"thornveil"],
    },

    // =========================================================================
    // SULPHERA -- THE UNDERWORLD
    // =========================================================================

    // The Infernal perk gates all of Sulphera. From visitor_ring outward,
    // each ring requires either the ring above to be cleared or a sin-specific
    // gate (tracked via quest flags in the game loop).

    // -- Visitor Ring -- hub, market, waypoints --------------------------------
    ZoneDef {
        id:       b"visitor_ring",
        name:     b"The Visitor Ring",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Rest,
        desc:     b"The entry ring of Sulphera. Demons keep stalls here -- selling \
                     what cannot be sold elsewhere -- and the waypoint stones are \
                     warm to the touch. You are not yet in danger.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"pride_outer", b"greed_outer", b"envy_outer",
                    b"gluttony_outer", b"sloth_outer", b"wrath_outer",
                    b"lust_outer"],
    },

    // ── PRIDE ─────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"pride_outer",
        name:     b"Pride Ring -- Promenade",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Threshold,
        desc:     b"A wide boulevard lit by every variety of self-reflection. \
                     Mirrors do not show your face -- they show what you wish it were. \
                     The demons here are eloquent and very, very tired of themselves.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"pentagram_city_sewers",
                    b"lucifers_castle_depths", b"dantes_pit"],
    },
    ZoneDef {
        id:       b"pentagram_city_sewers",
        name:     b"Pentagram City Sewers",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Below the great city's streets. Pride's excess drains here. \
                     The infrastructure of vanity, unbeautiful in cross-section.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"pride_outer"],
    },
    ZoneDef {
        id:       b"lucifers_castle_depths",
        name:     b"Lucifer's Castle Depths",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Deeper than the public rooms. The architecture becomes personal \
                     here -- as though the castle were growing around a wound.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"pride_outer"],
    },
    ZoneDef {
        id:       b"dantes_pit",
        name:     b"Dante's Pit",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"The pit goes down. Whatever was written about it \
                     was understated.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"pride_outer"],
    },

    // ── GREED ────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"greed_outer",
        name:     b"Greed Ring -- Counting House Foyer",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Rest,
        desc:     b"The foyer smells of coin polish and nervous sweat. Ledgers \
                     are stacked to the ceiling. A clerk offers you tea \
                     and asks what you are worth.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"counting_house", b"the_vault",
                    b"liquidation_floor", b"inheritance_of_ash"],
    },
    ZoneDef {
        id:       b"counting_house",
        name:     b"The Counting House",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"The arithmetic of greed. Every corridor is a ledger. \
                     Every guard is an audit.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"greed_outer"],
    },
    ZoneDef {
        id:       b"the_vault",
        name:     b"The Vault",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Where the accumulated excess of Greed is stored. \
                     It is heavier than it should be.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"greed_outer"],
    },
    ZoneDef {
        id:       b"liquidation_floor",
        name:     b"The Liquidation Floor",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Everything is converted here. The rate of exchange \
                     is not in your favour.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"greed_outer"],
    },
    ZoneDef {
        id:       b"inheritance_of_ash",
        name:     b"Inheritance of Ash",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"The final room of the Greed ring. What was hoarded \
                     has become charcoal. A demon reads the will aloud \
                     to no one.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"greed_outer"],
    },

    // ── ENVY ─────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"envy_outer",
        name:     b"Envy Ring -- Approach",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Threshold,
        desc:     b"Every surface here is polished to show reflection. \
                     You can see what others have. You can see what you don't. \
                     The distance between the two is the ring.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"the_glass_corridor", b"the_other_life",
                    b"portrait_hall", b"the_neighbors_grave"],
    },
    ZoneDef {
        id:       b"the_glass_corridor",
        name:     b"The Glass Corridor",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Both sides of the corridor show someone else's life. \
                     You cannot stop watching.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"envy_outer"],
    },
    ZoneDef {
        id:       b"the_other_life",
        name:     b"The Other Life",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"A precise model of the life you did not choose. \
                     It is running. It looks content.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"envy_outer"],
    },
    ZoneDef {
        id:       b"portrait_hall",
        name:     b"Portrait Hall",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Paintings of every face you have envied. \
                     They are all watching the door.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"envy_outer"],
    },
    ZoneDef {
        id:       b"the_neighbors_grave",
        name:     b"The Neighbour's Grave",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"The thing you envied has been buried here. The marker \
                     reads a name. It is not yours. \
                     The date of death is today.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"envy_outer"],
    },

    // ── GLUTTONY ──────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"gluttony_outer",
        name:     b"Gluttony Ring -- Banquet Approach",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Rest,
        desc:     b"The smell reaches you before the ring does. \
                     A long table extends to the horizon. No one at it \
                     is eating; they are remembering how eating felt.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"the_banquet_eternal", b"the_larder",
                    b"abandonment_halls", b"the_drain", b"othierus_maw"],
    },
    ZoneDef {
        id:       b"the_banquet_eternal",
        name:     b"The Banquet Eternal",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Every dish here is a consequence. The courses do not end.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"gluttony_outer"],
    },
    ZoneDef {
        id:       b"the_larder",
        name:     b"The Larder",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Where the excess is stored before the excess of the excess \
                     is consumed. The logistics of insatiability.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"gluttony_outer"],
    },
    ZoneDef {
        id:       b"abandonment_halls",
        name:     b"Abandonment Halls",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"What was left behind when appetite moved elsewhere. \
                     The rooms are still set for occupants who are not coming.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"gluttony_outer"],
    },
    ZoneDef {
        id:       b"the_drain",
        name:     b"The Drain",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"The ring's runoff. Gluttony does not metabolise; \
                     it accumulates and then drains. This is where.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"gluttony_outer"],
    },
    ZoneDef {
        id:       b"othierus_maw",
        name:     b"Othieru's Maw",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::BossArena,
        desc:     b"The Demon of Abandon waits at the bottom. \
                     Othieru does not fight; Othieru receives. \
                     The arena is a throat.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"gluttony_outer"],
    },

    // ── SLOTH ─────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"sloth_outer",
        name:     b"The Sitting Place",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Rest,
        desc:     b"This is the genuine rest area of the Sloth ring. \
                     A soft chair. A low fire. Nothing requires you here. \
                     You may sit as long as you need. The demons pass quietly.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"the_unfinished_rooms", b"the_long_sleep",
                    b"the_hall_of_almost", b"the_letters_never_sent"],
    },
    ZoneDef {
        id:       b"the_unfinished_rooms",
        name:     b"The Unfinished Rooms",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Every room was almost completed. The half-painted walls, \
                     the floor with one corner left unfinished, \
                     the door with no handle. The rooms resist you.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"sloth_outer"],
    },
    ZoneDef {
        id:       b"the_long_sleep",
        name:     b"The Long Sleep",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Time is different here. You are not sure how long you \
                     have been walking. Neither are the enemies.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"sloth_outer"],
    },
    ZoneDef {
        id:       b"the_hall_of_almost",
        name:     b"The Hall of Almost",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Everything here was nearly done. Efforts that stopped \
                     one step from the end. The hall loops.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"sloth_outer"],
    },
    ZoneDef {
        id:       b"the_letters_never_sent",
        name:     b"The Letters Never Sent",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"A room full of letters. Every one is addressed. \
                     Every one was written and then kept. \
                     You may read them. They are not yours; \
                     they are everyone's.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"sloth_outer"],
    },

    // ── WRATH ─────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"wrath_outer",
        name:     b"Wrath Ring -- Threshold",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Threshold,
        desc:     b"The air here vibrates. Wrath's ring does not begin quietly. \
                     The sound before violence -- that particular held breath -- \
                     is constant and unresolvable.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"the_killing_floor", b"tribunal",
                    b"the_war_that_never_ended", b"negayas_corridor",
                    b"the_field_of_righteous_violence", b"the_last_grievance"],
    },
    ZoneDef {
        id:       b"the_killing_floor",
        name:     b"The Killing Floor",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Wrath made architecture. The floor has been used for its name. \
                     The geometry is unambiguous.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },
    ZoneDef {
        id:       b"tribunal",
        name:     b"The Tribunal",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"You are judged here. Not for guilt -- for potential. \
                     Wrath's tribunal asks only: what would you become \
                     if you let yourself.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },
    ZoneDef {
        id:       b"the_war_that_never_ended",
        name:     b"The War That Never Ended",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Still fighting. The soldiers here have no memory of what \
                     started it. They fight because they always have.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },
    ZoneDef {
        id:       b"negayas_corridor",
        name:     b"Negaya's Corridor",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"The Void Wraith has made a corridor of this. \
                     She moves through it selectively. If she is present \
                     when you arrive, you are in her space, not yours.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },
    ZoneDef {
        id:       b"the_field_of_righteous_violence",
        name:     b"The Field of Righteous Violence",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Every enemy here believes they are correct. \
                     The most dangerous dungeon in the Wrath ring. \
                     Justified anger is harder to argue with than injustice.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },
    ZoneDef {
        id:       b"the_last_grievance",
        name:     b"The Last Grievance",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::BossArena,
        desc:     b"One wrong that was never resolved. It has been growing \
                     in the dark. It is enormous now.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"wrath_outer"],
    },

    // ── LUST ──────────────────────────────────────────────────────────────────

    ZoneDef {
        id:       b"lust_outer",
        name:     b"Lust Ring -- Outer Approach",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Threshold,
        desc:     b"The largest ring. The approach is deliberate -- \
                     sensory, spatial, slow. You are meant to arrive \
                     already wanting something before the ring begins.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"visitor_ring", b"the_perfumed_corridors",
                    b"the_gallery_of_longing", b"desire_made_architecture",
                    b"the_asmodean_market", b"the_chamber_of_second_thoughts",
                    b"where_wanting_lives", b"asmodeus_antechamber"],
    },
    ZoneDef {
        id:       b"the_perfumed_corridors",
        name:     b"The Perfumed Corridors",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Navigable sensory space before any combat begins. \
                     The corridors are genuinely pleasant until they are not.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"the_gallery_of_longing",
        name:     b"The Gallery of Longing",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"Art made of wanting. Every piece here was made by someone \
                     who could not have what they were making it for. \
                     There are no enemies here. There is nothing to fight.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"desire_made_architecture",
        name:     b"Desire Made Architecture",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"Lust made the structure. The rooms are shaped by what \
                     was wanted, not what was built. The geometry is personal.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"the_asmodean_market",
        name:     b"The Asmodean Market",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Market,
        desc:     b"Asmodeus runs commerce here. The goods are unusual. \
                     The prices are negotiable, the currency is personal, \
                     and no transaction is without consequence.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"the_chamber_of_second_thoughts",
        name:     b"The Chamber of Second Thoughts",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"A decision chamber. Whatever you chose in the ring, \
                     this room asks you if you meant it. \
                     You may change your answer here. Once.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"where_wanting_lives",
        name:     b"Where Wanting Lives",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Dungeon,
        desc:     b"The deepest dungeon of the Lust ring. \
                     Desire that was never examined lives here \
                     and has grown feral in the dark.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer"],
    },
    ZoneDef {
        id:       b"asmodeus_antechamber",
        name:     b"Asmodeus's Antechamber",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Threshold,
        desc:     b"The space before Asmodeus. The air is warm and exact. \
                     Everything is arranged. You understand, arriving here, \
                     that you are expected.",
        requires: ko_flags::F_SULPHERA_UNLOCKED,
        exits:    &[b"lust_outer", b"royal_ring"],
    },

    // ── ROYAL RING -- requires Asmodeus's blessing ────────────────────────────

    ZoneDef {
        id:       b"royal_ring",
        name:     b"The Royal Ring",
        realm:    Realm::Sulphera,
        kind:     ZoneKind::Chamber,
        desc:     b"Accessible only after Asmodeus's blessing. \
                     The most particular space in Sulphera. \
                     Hypatia stands here with Drovitth, near the Orrery. \
                     She is in her demon form -- a polymorph, both-gendered, \
                     watching a child's future take shape.",
        requires: ko_flags::F_SULPHERA_BLESSED,
        exits:    &[b"asmodeus_antechamber"],
    },
];

// ── Convenience queries ───────────────────────────────────────────────────────

pub fn zones_in_realm(realm: Realm) -> impl Iterator<Item = &'static ZoneDef> {
    ALL_ZONES.iter().filter(move |z| z.realm == realm)
}

pub fn dungeon_zones() -> impl Iterator<Item = &'static ZoneDef> {
    ALL_ZONES.iter().filter(|z| z.kind.is_combat())
}

pub fn safe_zones() -> impl Iterator<Item = &'static ZoneDef> {
    ALL_ZONES.iter().filter(|z| z.kind.is_safe())
}

pub fn accessible_exits(zone_id: &[u8]) -> &'static [&'static [u8]] {
    zone_by_id(zone_id).map(|z| z.exits).unwrap_or(&[])
}

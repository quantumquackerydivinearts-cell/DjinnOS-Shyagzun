// npc_placements.rs -- Static NPC placement table for 7_KLGS.
//
// Maps entity IDs to zone IDs.  game7 queries this to add
// "Talk to [Name]" menu items when the player is in a matching zone.
//
// IDs follow the {####}_{TYPE} format used throughout the game registry.
// NPC types: TOWN WTCH PRST ASSN ROYL GNOM NYMP UNDI SALA DRYA DJNN VDWR DMON

pub struct NpcPlacement {
    pub entity_id: &'static [u8],
    pub name:      &'static [u8],
    pub zone_id:   &'static [u8],
    pub bio:       &'static [u8],   // one-line shown in zone menu tip
}

pub static ALL_NPC_PLACEMENTS: &[NpcPlacement] = &[

    // ── Lapidus: Wiltoll Lane ─────────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"0024_TOWN",
        name:      b"Elsa",
        zone_id:   b"wiltoll_lane",
        bio:       b"Neighbour, three doors down. Has lived on the lane thirty years.",
    },
    // Hypatia works at Castle Azoth — was in the lab before anyone else arrived.
    // Her house on Wiltoll Lane is easternmost on the street; she is not home during the day.
    // game7 filters her from the castle Talk menu once F_Q0002_C is set (she descends).
    NpcPlacement {
        entity_id: b"0000_0451",
        name:      b"Hypatia",
        zone_id:   b"castle_azoth_halls",
        bio:       b"Alchemist. Was in the lab all night; beats everyone out of bed.",
    },

    // ── Lapidus: Temple Quarter ────────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"0020_TOWN",
        name:      b"Sidhal",
        zone_id:   b"temple_quarter",
        bio:       b"Temple custodian, 26. Knows the warrens.",
    },

    // ── Lapidus: Serpent's Pass ────────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"0021_TOWN",
        name:      b"Wells",
        zone_id:   b"serpents_pass",
        bio:       b"Aqueduct foreman, 38. Six children. Reliable.",
    },
    NpcPlacement {
        entity_id: b"0022_TOWN",
        name:      b"Lavelle",
        zone_id:   b"serpents_pass",
        bio:       b"Laundry, explosives, books. 23. Asks for nothing easy.",
    },

    // ── Lapidus: Hopefare ─────────────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"0017_ROYL",
        name:      b"Nexiott",
        zone_id:   b"azonithia_west",
        bio:       b"Caravan boss. Owns the eastern routes. Runs the radio.",
    },

    // ── Lapidus: Mt. Elaene Path ──────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"0007_WTCH",
        name:      b"The Forest Witch",
        zone_id:   b"mt_elaene_path",
        bio:       b"Witch, 60-something. Has a map that folds strangely.",
    },

    // ── Lapidus: Castle Azoth halls ───────────────────────────────────────────
    // Alfir is accessible after entering Castle Azoth (he teaches in a private
    // chamber reached through the halls).
    NpcPlacement {
        entity_id: b"0006_WTCH",
        name:      b"Alfir",
        zone_id:   b"castle_azoth_halls",
        bio:       b"Witch, former priest. Teaches Infernal Meditation.",
    },

    // ── Sulphera: Royal Ring ──────────────────────────────────────────────────
    NpcPlacement {
        entity_id: b"1018_DJNN",
        name:      b"Drovitth",
        zone_id:   b"royal_ring",
        bio:       b"Djinn. Built the Orrery. Has been watching a long time.",
    },
];

pub fn npcs_in_zone(zone_id: &[u8]) -> impl Iterator<Item = &'static NpcPlacement> + '_ {
    ALL_NPC_PLACEMENTS.iter().filter(move |n| n.zone_id == zone_id)
}

pub fn npc_by_id(entity_id: &[u8]) -> Option<&'static NpcPlacement> {
    ALL_NPC_PLACEMENTS.iter().find(|n| n.entity_id == entity_id)
}

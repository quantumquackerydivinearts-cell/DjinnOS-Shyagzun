// ko_flags.rs — Narrative gate flag registry for Ko's Labyrinth (7_KLGS).
//
// KoFlags are a 256-bit bitset in PlayerState used to track world/quest events.
// Named constants here map semantic gates to stable flag indices.
//
// Allocation policy:
//   0–31   World state (zones visited, NPC first encounters, game events)
//   32–85  Quest accept/complete pairs (A=accept, C=complete), quests 0001–0027
//   86–127 Reserved for quests 0028–0049
//   128–255 Free — expansion, secret endings, genocide tracking, etc.

pub use crate::player_state::{ko_set, ko_clear, ko_test};

// ── World state (0–31) ────────────────────────────────────────────────────────

pub const F_WILTOLL_ENTERED:    u8 =  0;
pub const F_AZONITHIA_ENTERED:  u8 =  1;
pub const F_LABYRINTH_ENTERED:  u8 =  2;  // player has seen the situation screen
pub const F_SIDHAL_MET:         u8 =  3;  // 0003_KLST guide NPC encountered
pub const F_WELLS_MET:          u8 =  4;  // Serpent's Pass foreman met
pub const F_LAVELLE_MET:        u8 =  5;  // Laundry/explosives NPC met
pub const F_ALFIR_MET:          u8 =  6;  // 0006_WTCH — Infernal Meditation teacher
pub const F_HYPATIA_SOUGHT:     u8 =  7;  // player has begun seeking Hypatia
pub const F_LOTTERY_DRAWN:      u8 =  8;  // Royal Lottery drew the player's name
pub const F_SULPHERA_UNLOCKED:  u8 =  9;  // PERK_INFERNAL granted → Sulphera open
pub const F_NEXIOTT_ALIVE:      u8 = 10;  // Nexiott NPC not killed
pub const F_HYPATIA_FOUND:      u8 = 11;  // player has located Hypatia
pub const F_ALFIR_WINDOW_OPEN:  u8 = 12;  // Alfir's teaching window still available
pub const F_CASTLE_AZOTH_SEEN:  u8 = 13;
pub const F_MEDITATION_TRAINED: u8 = 14;  // player has trained meditation skill ≥ 1
pub const F_MERCURIE_OPEN:      u8 = 15;  // Fae relations sufficient to enter Mercurie
pub const F_SULPHERA_BLESSED:   u8 = 16;  // Asmodeus's blessing granted; Royal Ring open

// Genocide tracking (128+)
pub const F_GENOCIDE_PATH:      u8 = 128; // player killed at least one non-hostile NPC
pub const F_NEXIOTT_DEAD:       u8 = 129;
pub const F_NEGAYA_HAUNTING:    u8 = 130; // Negaya's torment active

// Secret ending flags (160+)
pub const F_RADIO_FOUND:        u8 = 160; // Hypatia's Secret Ending gate
pub const F_ST_ALARO_CONTACT:   u8 = 161; // Radio Demon of Pride contacted
pub const F_STELLADEVA_KNOWN:   u8 = 162;

// Dagger tracking
pub const F_DAGGER_AT_REUNION:  u8 = 163; // Set when player enters Royal Ring still holding the dagger.
                                            // Unlocks unique Hypatia reunion dialogue (0002 never completed).

// ── Quest flag helpers ────────────────────────────────────────────────────────
//
// Quests 0001–0027 get two flags each (A=accepted, C=complete) at indices 32–85.
// Quest N: accept flag = 32 + (N-1)*2, complete flag = 32 + (N-1)*2 + 1.

pub fn quest_flag_accept(n: u8) -> u8 {
    32u8.saturating_add(n.saturating_sub(1).saturating_mul(2))
}

pub fn quest_flag_complete(n: u8) -> u8 {
    quest_flag_accept(n).saturating_add(1)
}

/// Parse a quest slug like b"0003_KLST" into its numeric index (3).
pub fn quest_num(slug: &[u8]) -> Option<u8> {
    if slug.len() < 4 { return None; }
    let mut n = 0u16;
    for &b in &slug[..4] {
        if b < b'0' || b > b'9' { return None; }
        n = n * 10 + (b - b'0') as u16;
    }
    if n == 0 || n > 49 { return None; }
    Some(n as u8)
}

pub const F_Q0001_A: u8 = 32;  pub const F_Q0001_C: u8 = 33;
pub const F_Q0002_A: u8 = 34;  pub const F_Q0002_C: u8 = 35;
pub const F_Q0003_A: u8 = 36;  pub const F_Q0003_C: u8 = 37;
pub const F_Q0004_A: u8 = 38;  pub const F_Q0004_C: u8 = 39;
pub const F_Q0005_A: u8 = 40;  pub const F_Q0005_C: u8 = 41;
pub const F_Q0006_A: u8 = 42;  pub const F_Q0006_C: u8 = 43;
pub const F_Q0007_A: u8 = 44;  pub const F_Q0007_C: u8 = 45;
pub const F_Q0008_A: u8 = 46;  pub const F_Q0008_C: u8 = 47;
pub const F_Q0009_A: u8 = 48;  pub const F_Q0009_C: u8 = 49;
pub const F_Q0010_A: u8 = 50;  pub const F_Q0010_C: u8 = 51;
pub const F_Q0011_A: u8 = 52;  pub const F_Q0011_C: u8 = 53;
pub const F_Q0012_A: u8 = 54;  pub const F_Q0012_C: u8 = 55;
pub const F_Q0013_A: u8 = 56;  pub const F_Q0013_C: u8 = 57;
pub const F_Q0014_A: u8 = 58;  pub const F_Q0014_C: u8 = 59;
pub const F_Q0015_A: u8 = 60;  pub const F_Q0015_C: u8 = 61;
pub const F_Q0016_A: u8 = 62;  pub const F_Q0016_C: u8 = 63;
pub const F_Q0017_A: u8 = 64;  pub const F_Q0017_C: u8 = 65;
pub const F_Q0018_A: u8 = 66;  pub const F_Q0018_C: u8 = 67;
pub const F_Q0019_A: u8 = 68;  pub const F_Q0019_C: u8 = 69;
pub const F_Q0020_A: u8 = 70;  pub const F_Q0020_C: u8 = 71;
pub const F_Q0021_A: u8 = 72;  pub const F_Q0021_C: u8 = 73;
pub const F_Q0022_A: u8 = 74;  pub const F_Q0022_C: u8 = 75;
pub const F_Q0023_A: u8 = 76;  pub const F_Q0023_C: u8 = 77;
pub const F_Q0024_A: u8 = 78;  pub const F_Q0024_C: u8 = 79;
pub const F_Q0025_A: u8 = 80;  pub const F_Q0025_C: u8 = 81;
pub const F_Q0026_A: u8 = 82;  pub const F_Q0026_C: u8 = 83;
pub const F_Q0027_A: u8 = 84;  pub const F_Q0027_C: u8 = 85;

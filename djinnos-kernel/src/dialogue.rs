// Dialogue selector — scripted, voiced, responsive.
//
// Authors write DialogueLine entries in the Atelier.  The Twelvefold Coil
// reads player state and selects which line to surface.  HDA plays it.
// No generation — only selection.
//
// ── Selection pipeline ────────────────────────────────────────────────────────
//
//   1. CoilState.best_kind() names the InteractionKind the coil wants.
//   2. Filter: quack_min ≤ quack_count ≤ quack_max
//   3. Filter: coil_layer ≤ def.max_layer (entity can deliver this depth)
//   4. Filter: all condition addresses active in player eigenstate
//   5. Score:  tonal adjacency — how close are the line's condition colors
//              to the current coil Layer 7 color (the geometric fingerprint)?
//   6. Pick:   highest-scoring eligible line.  Tie-break: lower quack_min
//              (prefer more universally accessible lines on ties).
//   7. Fallback: if no match for wanted kind, retry with Dialogue.
//
// ── Quack gating ──────────────────────────────────────────────────────────────
//
// quack_min encodes which tongue must be attested before this line is eligible.
// A line about Infernal Meditation (byte 193, Cannabis T8) sets quack_min ≥ 8.
// A line about void organisms (Dragon T9) sets quack_min ≥ 9.
// As the ledger grows, higher-register lines become available across all chars.
//
// ── Tonal scoring ─────────────────────────────────────────────────────────────
//
// Each line's condition addresses have ring colors (palette::aki_color).
// The player's current coil Layer 7 RGB is the geometric fingerprint of their
// state.  Score = sum of (255 - L1_distance) for each condition address color.
// Lines whose semantic register is closest to the player's current coil color
// score highest — the selector gravitates toward tonal coherence.
//
// ── Audio reference ───────────────────────────────────────────────────────────
//
// audio_ref = Sa volume address of the voiced PCM data.
// 0 = subtitle-only (no audio).  The HDA player reads from Sa volume once
// writeable storage is available.  For now, all lines are subtitle-only.

use crate::agent::{AgentDef, CoilState, InteractionKind};
use crate::palette;

// ── DialogueLine ──────────────────────────────────────────────────────────────

pub struct DialogueLine {
    /// Unique line ID.  Recorded in attestation log so Orrery can track
    /// which specific lines have been delivered (continuity verification).
    pub line_id:     u32,
    /// Entity that delivers this line.  Matches AgentDef.entity_id.
    pub entity_id:   &'static [u8],
    /// Minimum Quack count for this line to be eligible.
    pub quack_min:   u8,
    /// Maximum Quack count (255 = no ceiling).
    pub quack_max:   u8,
    /// Which InteractionKind this line serves.
    pub interaction: InteractionKind,
    /// Minimum entity coil depth (def.max_layer) required to deliver this line.
    /// Prevents Townfolk from delivering God-register content.
    pub coil_layer:  u8,
    /// Byte table addresses that must be active in player eigenstate.
    /// Empty = always eligible (no precondition).
    pub conditions:  &'static [u32],
    /// The scripted text (displayed as subtitle; also used for text-mode).
    pub text:        &'static [u8],
    /// Sa volume file address for voiced PCM audio.  0 = subtitle only.
    pub audio_ref:   u32,
}

// ── Selector ──────────────────────────────────────────────────────────────────

/// Select the best dialogue line from `pool` for the given agent state.
///
/// Returns None if no line is eligible (agent is silent / not available).
/// The returned line's line_id should be recorded in the attestation log.
pub fn select(
    pool:        &'static [DialogueLine],
    state:       &CoilState,
    def:         &AgentDef,
    quack_count: u8,
    eigenstate:  &[u32; 24],
) -> Option<&'static DialogueLine> {
    // Primary: use what the coil wants
    let primary_kind = state.best_kind();
    // Fallback: plain dialogue if primary has no match
    let fallback_kind = Some(InteractionKind::Dialogue);

    for &wanted in &[primary_kind, fallback_kind] {
        let wanted = wanted?;
        if let Some(line) = select_for_kind(pool, state, def, quack_count, eigenstate, wanted) {
            return Some(line);
        }
    }
    None
}

fn select_for_kind(
    pool:        &'static [DialogueLine],
    state:       &CoilState,
    def:         &AgentDef,
    quack_count: u8,
    eigenstate:  &[u32; 24],
    wanted:      InteractionKind,
) -> Option<&'static DialogueLine> {
    let mut best_score: u32 = 0;
    let mut best_line:  Option<&'static DialogueLine> = None;
    let mut best_qmin:  u8  = 255;

    for line in pool {
        // Entity gate: this line must belong to the current agent
        if line.entity_id != def.entity_id { continue; }

        // Kind gate
        if line.interaction != wanted { continue; }

        // Quack range gate
        if quack_count < line.quack_min { continue; }
        if quack_count > line.quack_max { continue; }

        // Coil depth gate: entity must be deep enough to deliver this line
        if line.coil_layer > def.max_layer { continue; }

        // Eigenstate condition gate: all required addresses must be active
        if !all_conditions_met(line.conditions, eigenstate, quack_count) { continue; }

        // Tonal score: proximity of line's condition register to coil color
        let score = tonal_score(line, state);

        // Higher score wins; on tie, prefer lower quack_min (more universal)
        if score > best_score || (score == best_score && line.quack_min < best_qmin) {
            best_score = score;
            best_line  = Some(line);
            best_qmin  = line.quack_min;
        }
    }

    best_line
}

// ── Condition evaluation ──────────────────────────────────────────────────────

/// All condition byte addresses must be active in the player's eigenstate.
fn all_conditions_met(
    conditions:  &[u32],
    eigenstate:  &[u32; 24],
    quack_count: u8,
) -> bool {
    for &addr in conditions {
        if !eigenstate_active(addr, eigenstate, quack_count) { return false; }
    }
    true
}

/// A byte address is "active" when:
///   - Its tongue has been attested (quack_count ≥ tongue number)
///   - For tongues 1–24: the eigenstate slot for that tongue is non-zero
///   - For tongues 25–38: simply being attested is sufficient
fn eigenstate_active(addr: u32, eigenstate: &[u32; 24], quack_count: u8) -> bool {
    let tongue = addr_tongue(addr) as u8;
    if tongue == 0 { return true; }    // unknown address = no gate
    if quack_count < tongue { return false; }  // tongue not yet attested
    if tongue <= 24 {
        eigenstate[(tongue - 1) as usize] > 0
    } else {
        true  // tongues 25-38: attestation alone is sufficient
    }
}

/// Map a byte address to its tongue number (1–38) using the cluster boundaries.
fn addr_tongue(addr: u32) -> u32 {
    match addr {
        0..=23    => 1,
        24..=47   => 2,
        48..=71   => 3,
        72..=97   => 4,
        98..=127  => 5,
        128..=155 => 6,
        156..=183 => 7,
        184..=255 => 8,
        256..=285 => 9,
        286..=315 => 10,
        316..=345 => 11,
        346..=377 => 12,
        378..=409 => 13,
        410..=443 => 14,
        444..=477 => 15,
        478..=511 => 16,
        512..=545 => 17,
        546..=581 => 18,
        582..=617 => 19,
        618..=655 => 20,
        656..=693 => 21,
        694..=731 => 22,
        732..=769 => 23,
        770..=809 => 24,
        810..=849 => 25,
        850..=889 => 26,
        890..=929 => 27,
        930..=969 => 28,
        970..=1009 => 29,
        1010..=1051 => 30,
        1052..=1093 => 31,
        1094..=1137 => 32,
        1138..=1181 => 33,
        1182..=1225 => 34,
        1226..=1269 => 35,
        1270..=1313 => 36,
        1314..=1357 => 37,
        _          => 38,
    }
}

// ── Tonal scoring ─────────────────────────────────────────────────────────────

/// Score a line by how tonally adjacent its condition register is to the
/// current coil Layer 7 color (the geometric fingerprint of player state).
///
/// Empty conditions → neutral score 128 (always eligible, never preferred
/// over a precisely matched line).
fn tonal_score(line: &DialogueLine, state: &CoilState) -> u32 {
    let coil_col = (state.l07[0], state.l07[1], state.l07[2]);

    if line.conditions.is_empty() {
        return 128;
    }

    let mut total = 0u32;
    for &addr in line.conditions {
        let line_col = palette::aki_color(addr);
        let dist = rgb_l1(coil_col, line_col);
        total += 255u32.saturating_sub(dist);
    }
    total / line.conditions.len() as u32
}

fn rgb_l1(a: (u8,u8,u8), b: (u8,u8,u8)) -> u32 {
    (a.0 as i32 - b.0 as i32).unsigned_abs()
  + (a.1 as i32 - b.1 as i32).unsigned_abs()
  + (a.2 as i32 - b.2 as i32).unsigned_abs()
}

// ── Line delivery ─────────────────────────────────────────────────────────────

/// Deliver a dialogue line: push text to the shell and queue audio.
/// Records the line_id in the attestation log for Orrery continuity.
///
/// shell: mutable reference to the Ko shell for text display
/// (passed as a raw callback to avoid circular module dependencies)
pub fn deliver(
    line:       &'static DialogueLine,
    push_text:  &mut dyn FnMut(&[u8]),
    quack_count: u8,
    game_id:    u8,
    quest_id:   u32,
) {
    // Push the scripted text to the display layer
    push_text(line.text);

    // Record delivery in the attestation log
    crate::agent::record_attestation(crate::agent::Attestation {
        entity_id_hash: fnv1a(line.entity_id),
        quack_count,
        color_hash:     (0, 0, 0), // color is set by verify_coil; delivery uses 0
        tick:           read_tick(),
        game_id,
        quest_id,
    });

    // Queue audio if voiced (Sa volume address non-zero)
    if line.audio_ref != 0 {
        queue_audio(line.audio_ref);
    }
}

fn fnv1a(data: &[u8]) -> u32 {
    let mut h: u32 = 2166136261;
    for &b in data { h = h.wrapping_mul(16777619) ^ b as u32; }
    h
}

fn read_tick() -> u64 {
    #[cfg(target_arch = "x86_64")]
    { crate::arch::read_mtime() }
    #[cfg(not(target_arch = "x86_64"))]
    { crate::arch::read_mtime() }
}

/// Queue a voiced line for HDA playback from Sa volume.
/// Currently a stub — wired when Sa volume reads are available.
fn queue_audio(_sa_addr: u32) {
    // TODO: load PCM from Sa volume at sa_addr, push to HDA ring buffer
}

// ── Sample pool — Alfir lines at various Quack thresholds ─────────────────────
//
// These demonstrate the selector's range: from basic greeting (quack_min=4)
// through Cannabis-register teaching (quack_min=8) to Dragon-register
// daemonology (quack_min=9).  All subtitle-only (audio_ref=0).
//
// Full dialogue authoring happens in the Atelier once Sa volume is available.

pub static ALFIR_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00060001,
        entity_id: b"0006_WTCH",
        quack_min: 4, quack_max: 255,
        interaction: InteractionKind::Dialogue,
        coil_layer: 4, conditions: &[],
        text: b"Ah. You found me. Sit -- the fire doesn't bite.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060002,
        entity_id: b"0006_WTCH",
        quack_min: 4, quack_max: 7,
        interaction: InteractionKind::Dialogue,
        coil_layer: 4, conditions: &[9], // Ta = Active being
        text: b"You carry something -- not yet named. It will be.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060003,
        entity_id: b"0006_WTCH",
        quack_min: 8, quack_max: 255,
        interaction: InteractionKind::TeachSkill,
        coil_layer: 6,
        conditions: &[193], // Soa — Conscious persistence (Cannabis T8)
        text: b"Good. You've learned to persist consciously. \
                Now let me show you what lives below that threshold.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060004,
        entity_id: b"0006_WTCH",
        quack_min: 9, quack_max: 255,
        interaction: InteractionKind::MeditationGuide,
        coil_layer: 6,
        conditions: &[193, 256], // Soa + Dragon T9
        text: b"Infernal Meditation. It doesn't summon. \
                It listens. The difference is everything.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060005,
        entity_id: b"0006_WTCH",
        quack_min: 9, quack_max: 255,
        interaction: InteractionKind::LoreAccess,
        coil_layer: 6,
        conditions: &[261], // Rhasha-vok — Homo sapiens (Dragon T9, mental void 6)
        text: b"Homo sapiens. Entry six. The void organism that suppresses \
                its own correction. You understand why I study it.",
        audio_ref: 0,
    },
];

pub static KO_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x20210001,
        entity_id: b"2021_GODS",
        quack_min: 0, quack_max: 255,
        interaction: InteractionKind::Dialogue,
        coil_layer: 1, conditions: &[],
        text: b"I've been watching you since before you knew there was something to watch.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210002,
        entity_id: b"2021_GODS",
        quack_min: 0, quack_max: 7,
        interaction: InteractionKind::Dialogue,
        coil_layer: 1, conditions: &[19], // Ko byte = active
        text: b"The labyrinth doesn't have a center. It has a question.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210003,
        entity_id: b"2021_GODS",
        quack_min: 8, quack_max: 255,
        interaction: InteractionKind::Dialogue,
        coil_layer: 6,
        conditions: &[193], // Soa
        text: b"You made something persist. Most don't. Most let it fade \
                and call that wisdom. It isn't.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210004,
        entity_id: b"2021_GODS",
        quack_min: 24, quack_max: 255,
        interaction: InteractionKind::LoreAccess,
        coil_layer: 12,
        conditions: &[45, 193], // Wu + Soa
        text: b"The twenty-fourth tongue. You begin to hear what was always \
                underneath. It was always there. You just had no word for it.",
        audio_ref: 0,
    },
];

pub static NEGAYA_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x20030001,
        entity_id: b"2003_VDWR",
        quack_min: 22, quack_max: 255,
        interaction: InteractionKind::Dialogue,
        coil_layer: 11, conditions: &[],
        text: b"You killed them. I know their bodies. I know what you did \
                to each one. I remember everything you would prefer I forget.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20030002,
        entity_id: b"2003_VDWR",
        quack_min: 22, quack_max: 255,
        interaction: InteractionKind::Dialogue,
        coil_layer: 11,
        conditions: &[276], // temporal void 1 — Dragon T9
        text: b"Time passes through you, not for you. I have watched \
                enough of your kind to know you believe the opposite.",
        audio_ref: 0,
    },
];
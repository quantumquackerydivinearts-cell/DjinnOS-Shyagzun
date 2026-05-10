// Dialogue selector -- scripted, voiced, coil-routed.
//
// What gates availability:  quest state and narrative flags.
// What governs selection:   the Twelvefold Coil (tone, register, kind).
//
// Quack count governs the language system, the Orrery, and the tiler.
// It does not gate individual dialogue lines.
//
// ── Selection pipeline ────────────────────────────────────────────────────────
//
//   1. Filter:  quest_req and quest_state must match current quest tracker.
//   2. Filter:  all flag_req flags must be set in the game flag store.
//   3. Filter:  coil_layer <= def.max_layer (entity deep enough to deliver).
//   4. CoilState.best_kind() names the wanted InteractionKind.
//   5. Score:   tonal adjacency -- how close are the line's condition colors
//               to the coil Layer 7 geometric fingerprint?
//   6. Pick:    highest-scoring eligible line.
//   7. Fallback: if no match for wanted kind, retry with Dialogue.
//
// ── Narrative gates ───────────────────────────────────────────────────────────
//
// quest_req = 0        : no quest required (always available within the scene)
// quest_req > 0        : specific quest ID must be in the given state
// quest_state: 0=any   1=offered  2=in_progress  3=complete
// flag_req             : game flags that must ALL be set
//
// Examples:
//   Alfir's teaching line: quest_req=0x0009, quest_state=2 (Demons & Diamonds
//     must be in progress) -- he teaches when you're actively on his quest.
//   Negaya's genocide line: flag_req=[GENOCIDE_FLAG] -- only after mass killing.
//   Ko's greeting: quest_req=0, flag_req=[] -- always available.
//
// ── Coil conditions ───────────────────────────────────────────────────────────
//
// conditions: byte table addresses used for tonal scoring only.
// They are NOT gates -- a line is not excluded because a condition address
// is inactive.  They tune WHICH eligible line matches the current coil color.
// A line about Dragon-register content scores high when Layer 7 is in the
// blue-green region (Dragon tongue midpoint on the RGB ring).

use crate::agent::{AgentDef, CoilState, InteractionKind};
use crate::palette;

// ── Quest state constants ──────────────────────────────────────────────────────

pub const QS_ANY:         u8 = 0;
pub const QS_OFFERED:     u8 = 1;
pub const QS_IN_PROGRESS: u8 = 2;
pub const QS_COMPLETE:    u8 = 3;

// ── DialogueLine ──────────────────────────────────────────────────────────────

pub struct DialogueLine {
    /// Unique line ID.  Recorded in attestation log for Orrery continuity.
    pub line_id:     u32,
    /// Entity that delivers this line.
    pub entity_id:   &'static [u8],

    // ── Narrative gates ───────────────────────────────────────────────────────
    /// Quest ID that must be in the given state.  0 = no quest required.
    pub quest_req:   u32,
    /// Required quest state (QS_ANY / QS_OFFERED / QS_IN_PROGRESS / QS_COMPLETE).
    pub quest_state: u8,
    /// Game flags that must ALL be set.  Empty = no flag requirement.
    pub flag_req:    &'static [u32],

    // ── Coil routing ──────────────────────────────────────────────────────────
    /// Which InteractionKind this line serves.
    pub interaction: InteractionKind,
    /// Minimum entity coil depth (def.max_layer) to deliver this line.
    pub coil_layer:  u8,
    /// Byte table addresses used for tonal scoring against coil Layer 7.
    /// Not gates -- only tune the score.
    pub conditions:  &'static [u32],

    // ── Content ───────────────────────────────────────────────────────────────
    /// Scripted text (subtitle + text-mode display).
    pub text:        &'static [u8],
    /// Sa volume address of voiced PCM.  0 = subtitle only.
    pub audio_ref:   u32,
}

// ── Selector ──────────────────────────────────────────────────────────────────

/// Select the best dialogue line from `pool` for the current narrative state.
///
/// `active_quests`: slice of (quest_id, quest_state) pairs currently tracked.
/// `flags`: slice of currently set game flag IDs.
pub fn select(
    pool:          &'static [DialogueLine],
    state:         &CoilState,
    def:           &AgentDef,
    active_quests: &[(u32, u8)],
    flags:         &[u32],
) -> Option<&'static DialogueLine> {
    let primary  = state.best_kind();
    let fallback = Some(InteractionKind::Dialogue);

    for &wanted in &[primary, fallback] {
        let wanted = wanted?;
        if let Some(line) = select_for_kind(pool, state, def, active_quests, flags, wanted) {
            return Some(line);
        }
    }
    None
}

fn select_for_kind(
    pool:          &'static [DialogueLine],
    state:         &CoilState,
    def:           &AgentDef,
    active_quests: &[(u32, u8)],
    flags:         &[u32],
    wanted:        InteractionKind,
) -> Option<&'static DialogueLine> {
    let mut best_score: u32 = 0;
    let mut best_line:  Option<&'static DialogueLine> = None;

    for line in pool {
        if line.entity_id != def.entity_id { continue; }
        if line.interaction != wanted       { continue; }
        if line.coil_layer > def.max_layer  { continue; }

        // Quest gate
        if line.quest_req != 0 {
            let quest_ok = active_quests.iter().any(|&(id, st)| {
                id == line.quest_req
                && (line.quest_state == QS_ANY || st == line.quest_state)
            });
            if !quest_ok { continue; }
        }

        // Flag gate
        if !all_flags_set(line.flag_req, flags) { continue; }

        let score = tonal_score(line, state);
        if score > best_score {
            best_score = score;
            best_line  = Some(line);
        }
    }

    best_line
}

// ── Flag evaluation ───────────────────────────────────────────────────────────

fn all_flags_set(required: &[u32], active: &[u32]) -> bool {
    for &req in required {
        if !active.contains(&req) { return false; }
    }
    true
}

// ── Tonal scoring ─────────────────────────────────────────────────────────────

fn tonal_score(line: &DialogueLine, state: &CoilState) -> u32 {
    let coil_col = (state.l07[0], state.l07[1], state.l07[2]);
    if line.conditions.is_empty() { return 128; }
    let mut total = 0u32;
    for &addr in line.conditions {
        let line_col = palette::aki_color(addr);
        total += 255u32.saturating_sub(rgb_l1(coil_col, line_col));
    }
    total / line.conditions.len() as u32
}

fn rgb_l1(a: (u8,u8,u8), b: (u8,u8,u8)) -> u32 {
    (a.0 as i32 - b.0 as i32).unsigned_abs()
  + (a.1 as i32 - b.1 as i32).unsigned_abs()
  + (a.2 as i32 - b.2 as i32).unsigned_abs()
}

pub fn line_count() -> usize {
    ALFIR_LINES.len() + KO_LINES.len() + NEGAYA_LINES.len()
}

// ── Line delivery ─────────────────────────────────────────────────────────────

pub fn deliver(
    line:      &'static DialogueLine,
    push_text: &mut dyn FnMut(&[u8]),
    game_id:   u8,
    quest_id:  u32,
) {
    push_text(line.text);
    crate::agent::record_attestation(crate::agent::Attestation {
        entity_id_hash: fnv1a(line.entity_id),
        quack_count:    0,
        color_hash:     (0, 0, 0),
        tick:           read_tick(),
        game_id,
        quest_id,
    });
    if line.audio_ref != 0 { queue_audio(line.audio_ref); }
}

fn fnv1a(data: &[u8]) -> u32 {
    let mut h: u32 = 2166136261;
    for &b in data { h = h.wrapping_mul(16777619) ^ b as u32; }
    h
}

fn read_tick() -> u64 { crate::arch::read_mtime() }

fn queue_audio(_sa_addr: u32) {
    // Stub -- wired when Sa volume reads are available.
}

// ── Sample pools ──────────────────────────────────────────────────────────────
//
// Narrative conditions:
//   0x0009 = quest 0009_KLST "Demons and Diamonds" (Alfir's quest)
//   0x0011 = quest 0011_KLST "The Siren Sounds"
//   Flag 0x0001 = genocide path flag (for Negaya's judgment lines)
//
// Coil conditions are tonal only -- they tune selection, they do not gate.

// ── Sample pools — gates left as placeholders ─────────────────────────────────
//
// quest_req, quest_state, and flag_req values are placeholders (0 / empty).
// The actual narrative exposure chain for each character is authored in the
// Atelier by the game team.  These samples demonstrate the selector machinery
// and establish the scripted text; conditions are filled in during authoring.
//
// Tonal conditions (byte addresses in the conditions field) reflect the
// character's register and are stable -- they do not change with narrative design.

pub static ALFIR_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00060001, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD in Atelier
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[9, 15], // Ta + Sha
        text: b"Come in. I do not turn visitors away -- \
                only those who arrive without a question.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060002, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[14, 15], // Shi + Sha
        text: b"I spent thirty years as a priest before I understood \
                that the gods do not listen for worship. \
                They listen for precision.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060003, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::TeachSkill, coil_layer: 6,
        conditions: &[193, 256], // Soa + Dragon T9
        text: b"You have learned Soa. The act of making something \
                persist consciously. The old men of my grandfather's line \
                practiced this without a name for it -- only the act, \
                repeated, until the act did not need them anymore. \
                Now I will show you what it remembers on your behalf.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060004, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::MeditationGuide, coil_layer: 6,
        conditions: &[193, 256, 261], // Soa + Rhivesh + Rhasha-vok
        text: b"Infernal Meditation is not summoning. The old texts \
                confused the two because the scholars were afraid. \
                It is listening. Sit with me. I will show you \
                the difference between a door and a throat.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x00060005, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::LoreAccess, coil_layer: 6,
        conditions: &[261], // Rhasha-vok
        text: b"Entry six. The creature whose cognition is constituted \
                by suppressing its own correction. \
                I have studied it for forty years. \
                I include myself in the study.",
        audio_ref: 0,
    },
];

pub static KO_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x20210001, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 1,
        conditions: &[],
        text: b"I have been watching you since before you knew \
                there was something to watch.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210002, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 1,
        conditions: &[19],
        text: b"The labyrinth does not have a center. It has a question.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210003, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 6,
        conditions: &[193],
        text: b"You made something persist. Most do not. Most let it fade \
                and call that wisdom. It is not wisdom.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20210004, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::LoreAccess, coil_layer: 12,
        conditions: &[45, 193],
        text: b"You spoke with the one who built the Orrery. \
                Good. He knew what he was making. \
                Most architects do not.",
        audio_ref: 0,
    },
];

pub static NEGAYA_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x20030001, entity_id: b"2003_VDWR",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD (genocide path)
        interaction: InteractionKind::Dialogue, coil_layer: 11,
        conditions: &[],
        text: b"You killed them. I know their bodies. I know what you did \
                to each one. I remember everything \
                you would prefer I forget.",
        audio_ref: 0,
    },
    DialogueLine {
        line_id: 0x20030002, entity_id: b"2003_VDWR",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD (genocide + meditation)
        interaction: InteractionKind::MeditationGuide, coil_layer: 11,
        conditions: &[276, 277, 278],
        text: b"You want absolution through stillness. \
                I am the wrong void wraith to ask. \
                Haldoro judges minds. Vios judges souls. \
                I know what your body has done. \
                Sit with that first.",
        audio_ref: 0,
    },
];
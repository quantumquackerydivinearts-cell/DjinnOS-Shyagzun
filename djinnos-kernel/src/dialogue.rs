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

    // ── Side-effects on delivery ──────────────────────────────────────────────
    /// Quest slug this line acts on when delivered.
    ///   QuestOffer  → offer this quest
    ///   QuestAdvance → accept this quest (Offered→InProgress)
    ///   QuestComplete → mark this quest complete
    ///   Other → no quest action (leave empty)
    pub quest_action: &'static [u8],
    /// Perk ID to auto-unlock when this line is delivered.  0 = none.
    pub teaches_perk: u8,
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
    ALFIR_LINES.len() + ALFIR_LINES_EXT.len()
    + KO_LINES.len() + NEGAYA_LINES.len()
    + SIDHAL_LINES.len() + WELLS_LINES.len() + LAVELLE_LINES.len()
    + FOREST_WITCH_LINES.len() + NEXIOTT_LINES.len() + DROVITTH_LINES.len()
    + ELSA_LINES.len() + HYPATIA_EARLY_LINES.len()
    + HYPATIA_REUNION_DAGGER_LINES.len()
}

// ── Per-entity pool dispatcher ─────────────────────────────────────────────────

// Alfir's full pool (base + extended).  Checked linearly by select_npc_line.
// In no_std we can't easily concat slices, so the selector checks both.
pub fn alfir_all() -> (&'static [DialogueLine], &'static [DialogueLine]) {
    (ALFIR_LINES, ALFIR_LINES_EXT)
}

pub fn pool_for(entity_id: &[u8]) -> &'static [DialogueLine] {
    match entity_id {
        b"0006_WTCH" => ALFIR_LINES, // extended pool via alfir_all()
        b"2021_GODS" => KO_LINES,
        b"2003_VDWR" => NEGAYA_LINES,
        b"0020_TOWN" => SIDHAL_LINES,
        b"0021_TOWN" => WELLS_LINES,
        b"0022_TOWN" => LAVELLE_LINES,
        b"0007_WTCH" => FOREST_WITCH_LINES,
        b"0017_ROYL" => NEXIOTT_LINES,
        b"1018_DJNN" => DROVITTH_LINES,
        b"0024_TOWN" => ELSA_LINES,
        // Hypatia: early-game lines base; reunion dagger variant via hypatia_all()
        b"0000_0451" => HYPATIA_EARLY_LINES,
        _            => &[],
    }
}

/// Hypatia has two pools: early-game presence and dagger-kept reunion variant.
/// select_npc_line checks both when entity_id == b"0000_0451".
pub fn hypatia_all() -> (&'static [DialogueLine], &'static [DialogueLine]) {
    (HYPATIA_EARLY_LINES, HYPATIA_REUNION_DAGGER_LINES)
}

// ── Selector for NPC screen (bypasses CoilState -- topic chosen explicitly) ────

fn check_line(
    line:          &'static DialogueLine,
    kind:          InteractionKind,
    active_quests: &[(u32, u8)],
    flags:         &[u32],
    coil:          &CoilState,
    best_score:    &mut u32,
    best:          &mut Option<&'static DialogueLine>,
) {
    if line.interaction != kind { return; }
    if line.quest_req != 0 {
        let ok = active_quests.iter().any(|&(id, st)| {
            id == line.quest_req
            && (line.quest_state == QS_ANY || st == line.quest_state)
        });
        if !ok { return; }
    }
    if !all_flags_set(line.flag_req, flags) { return; }
    let score = tonal_score(line, coil);
    if score > *best_score { *best_score = score; *best = Some(line); }
}

pub fn select_npc_line(
    entity_id:     &[u8],
    kind:          InteractionKind,
    active_quests: &[(u32, u8)],
    flags:         &[u32],
) -> Option<&'static DialogueLine> {
    let coil = CoilState::zero();
    let mut best_score = 0u32;
    let mut best: Option<&'static DialogueLine> = None;

    let pool = pool_for(entity_id);
    for line in pool {
        check_line(line, kind, active_quests, flags, &coil, &mut best_score, &mut best);
    }
    // Alfir gets a second pass over the extended pool.
    if entity_id == b"0006_WTCH" {
        let (_, ext) = alfir_all();
        for line in ext {
            check_line(line, kind, active_quests, flags, &coil, &mut best_score, &mut best);
        }
    }
    // Hypatia gets a second pass over the reunion/dagger-kept pool.
    if entity_id == b"0000_0451" {
        let (_, reunion) = hypatia_all();
        for line in reunion {
            check_line(line, kind, active_quests, flags, &coil, &mut best_score, &mut best);
        }
    }
    best
}

/// Returns a bitmask of available InteractionKind values (bit N = kind N available).
pub fn available_kinds(
    entity_id:     &[u8],
    active_quests: &[(u32, u8)],
    flags:         &[u32],
) -> u16 {
    let mut mask = 0u16;
    for line in pool_for(entity_id) {
        if line.quest_req != 0 {
            let ok = active_quests.iter().any(|&(id, st)| {
                id == line.quest_req
                && (line.quest_state == QS_ANY || st == line.quest_state)
            });
            if !ok { continue; }
        }
        if !all_flags_set(line.flag_req, flags) { continue; }
        mask |= 1 << (line.interaction as u8);
    }
    let scan_extra = |mask: &mut u16, pool: &[DialogueLine]| {
        for line in pool {
            if line.quest_req != 0 {
                let ok = active_quests.iter().any(|&(id, st)| {
                    id == line.quest_req
                    && (line.quest_state == QS_ANY || st == line.quest_state)
                });
                if !ok { continue; }
            }
            if !all_flags_set(line.flag_req, flags) { continue; }
            *mask |= 1 << (line.interaction as u8);
        }
    };
    if entity_id == b"0006_WTCH" {
        let (_, ext) = alfir_all();
        scan_extra(&mut mask, ext);
    }
    if entity_id == b"0000_0451" {
        let (_, reunion) = hypatia_all();
        scan_extra(&mut mask, reunion);
    }
    mask
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00060002, entity_id: b"0006_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[14, 15], // Shi + Sha
        text: b"I spent thirty years as a priest before I understood \
                that the gods do not listen for worship. \
                They listen for precision.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x20210002, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 1,
        conditions: &[19],
        text: b"The labyrinth does not have a center. It has a question.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x20210003, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::Dialogue, coil_layer: 6,
        conditions: &[193],
        text: b"You made something persist. Most do not. Most let it fade \
                and call that wisdom. It is not wisdom.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x20210004, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[], // gate: TBD
        interaction: InteractionKind::LoreAccess, coil_layer: 12,
        conditions: &[45, 193],
        text: b"You spoke with the one who built the Orrery. \
                Good. He knew what he was making. \
                Most architects do not.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x20210005, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 14,
        conditions: &[19, 45],
        text: b"The species arrived on this world three thousand years \
                before you were born. They brought everything with them. \
                The gods who were already here watched them choose, again, \
                what they had chosen before. \
                That is what I have been watching.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x20210006, entity_id: b"2021_GODS",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 10,
        conditions: &[19],
        text: b"You are not the first of your kind to find this labyrinth. \
                You are the first in a very long time to find it \
                without already knowing what you lost to get here.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
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
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── SIDHAL (0020_TOWN) -- Temple custodian, 26, father of 2, guide to the warrens ──

pub static SIDHAL_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00200001, entity_id: b"0020_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[3, 8],
        text: b"You look like someone who came here knowing what they wanted \
                and found something different instead. \
                The city does that. Sit down, if you have a minute.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00200002, entity_id: b"0020_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::QuestOffer, coil_layer: 3,
        conditions: &[3, 4],
        text: b"The Hopefare Road route through the warrens is not on any map \
                the city keeps. I know it because my father taught it to me \
                and his father before him. If you need to reach the other side \
                of Azonithia without going through the lottery checkpoints, \
                I can walk you to it. There are people at the end of the road \
                worth meeting.",
        audio_ref: 0, quest_action: b"0003_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00200003, entity_id: b"0020_TOWN",
        quest_req: 3, quest_state: QS_IN_PROGRESS, flag_req: &[],
        interaction: InteractionKind::QuestAdvance, coil_layer: 3,
        conditions: &[4],
        text: b"The second turning is the one people miss. \
                There is a wall painted with a sun from some old religion -- \
                not the temple's religion; older than that. \
                Turn there, not at the archway. \
                The archway takes you into the overflow drain. \
                I have lost three apprentices that way. \
                Not to death -- to embarrassment.",
        audio_ref: 0, quest_action: b"0003_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00200004, entity_id: b"0020_TOWN",
        quest_req: 3, quest_state: QS_COMPLETE, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[3, 8],
        text: b"Good. Wells and Lavelle are exactly what they look like: \
                reliable, competent, and quietly furious about being both \
                in a city that doesn't deserve it. They'll help you. \
                They help everyone. It's a character flaw they've both accepted.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00200005, entity_id: b"0020_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 3,
        conditions: &[9, 19],
        text: b"The temple used to serve seven gods. Now it serves the lottery. \
                The priests kept their jobs by agreeing not to distinguish \
                between the two. I keep mine by mopping the floor \
                and pretending not to have opinions. \
                I have very specific opinions.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00200006, entity_id: b"0020_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[128],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[],
        text: b"I heard what happened in the quarter. \
                I want you to know that I will remember their names \
                long after you have forgotten what you did here.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── WELLS (0021_TOWN) -- Aqueduct foreman, 38, father of 6 ────────────────────

pub static WELLS_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00210001, entity_id: b"0021_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[4, 8],
        text: b"Sidhal sent you. I can tell -- \
                you've still got the look of someone who trusts \
                that the city works the way it says it does.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00210002, entity_id: b"0021_TOWN",
        quest_req: 3, quest_state: QS_IN_PROGRESS, flag_req: &[],
        interaction: InteractionKind::QuestAdvance, coil_layer: 3,
        conditions: &[4, 8],
        text: b"The aqueduct at this section is patched with three different \
                kinds of stone because three different administrations repaired it \
                three different ways and none of them talked to each other. \
                We have held it together for eleven years. \
                That is not competence. That is stubbornness. \
                I hope you have some.",
        audio_ref: 0, quest_action: b"0003_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00210003, entity_id: b"0021_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 3,
        conditions: &[19],
        text: b"The Lottery isn't random. I've worked these streets long enough \
                to know which families have never been drawn. \
                You want to know who actually runs this city, \
                ask yourself who has never won the prize nobody wants.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00210004, entity_id: b"0021_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[3],
        text: b"Six kids. The oldest works with me. The second one is smarter \
                than both of us and has decided to do something about it. \
                I don't ask for details. Some things a father \
                doesn't need to know in advance.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── LAVELLE (0022_TOWN) -- Laundry/explosives/bookworm, 23, mother of 2 ────────

pub static LAVELLE_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00220001, entity_id: b"0022_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[5, 3],
        text: b"If you're here about the laundry, the turnaround is three days, \
                more if there's blood in it. \
                If you're here about anything else, sit down \
                and tell me something I don't already know.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00220002, entity_id: b"0022_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 4,
        conditions: &[5],
        text: b"I learned demolitions from a manual written for the royal engineers. \
                It was in the temple library, misfiled under Moral Philosophy. \
                Which tells you everything you need to know \
                about whoever catalogued that collection.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00220003, entity_id: b"0022_TOWN",
        quest_req: 3, quest_state: QS_IN_PROGRESS, flag_req: &[],
        interaction: InteractionKind::QuestAdvance, coil_layer: 3,
        conditions: &[5, 4],
        text: b"There's a checkpoint at the sewer outlet. \
                They rotate guards on an irregular schedule \
                specifically so nobody can predict it. \
                I have a gap mapped. I will share it \
                when I know you won't do anything \
                that gets Wells's section shut down.",
        audio_ref: 0, quest_action: b"0003_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00220004, entity_id: b"0022_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[128],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[],
        text: b"I know what you have been doing. I have two children. \
                I need you to understand that I am noting your face \
                for reasons that I will act on at a time of my choosing. \
                Pick up your laundry on the way out.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── FOREST WITCH (0007_WTCH) -- Gay male witch, Mercurie map, Mt. Elaene ────────

pub static FOREST_WITCH_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00070001, entity_id: b"0007_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 5,
        conditions: &[3, 6],
        text: b"I don't get many visitors who aren't lost. \
                Are you lost, or are you looking? \
                The difference matters more than people expect. \
                Lost people want directions. Looking people want maps.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00070002, entity_id: b"0007_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::QuestOffer, coil_layer: 5,
        conditions: &[6, 193],
        text: b"There is a particular kind of dream that comes when the boundary \
                between what is real and what is possible becomes negotiable. \
                You have been having it, haven't you. \
                I can teach you to stay awake inside it. \
                That is what the Glass is -- the membrane you press against \
                from the wrong side. I will show you the right side. \
                Save whatever dust remains in the morning. I mean that literally.",
        audio_ref: 0, quest_action: b"0007_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00070003, entity_id: b"0007_WTCH",
        quest_req: 7, quest_state: QS_IN_PROGRESS, flag_req: &[],
        interaction: InteractionKind::MeditationGuide, coil_layer: 5,
        conditions: &[6, 193],
        text: b"You are doing fine. The temptation is to try to control it. Don't. \
                The glass does not shatter if you stop pushing -- it dissolves. \
                The dissolving is the point. Let it dissolve. \
                What is on the other side has been waiting. \
                It has patience in quantities that make patience look like rushing.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00070004, entity_id: b"0007_WTCH",
        quest_req: 7, quest_state: QS_COMPLETE, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 6,
        conditions: &[6, 193],
        text: b"You have been through it. Good. The Faewilds are accessible \
                through two thresholds near this region: \
                the ocean shore at low tide, and the mine's deepest level \
                past the third vein, where the stone changes color. \
                The Fae will know you before you know them. \
                That is not a problem unless you make it one. \
                I have a map. Keep it in your journal.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00070005, entity_id: b"0007_WTCH",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 5,
        conditions: &[3, 6],
        text: b"I have been here forty years. The forest has its own intelligence \
                and it is patient in ways that make patience look like rushing. \
                I am still a student. \
                I expect to remain one for whatever time I have left, \
                which I have not asked and do not intend to.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── ALFIR extended lines (0006_WTCH) -- quest 0009/0010 gated ─────────────────
// Use ALFIR_ALL_LINES in npc_screen to combine both pools.

pub static ALFIR_LINES_EXT: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00060006, entity_id: b"0006_WTCH",
        quest_req: 9, quest_state: QS_COMPLETE,
        flag_req: &[14], // F_MEDITATION_TRAINED
        interaction: InteractionKind::QuestOffer, coil_layer: 6,
        conditions: &[193, 256],
        text: b"You completed the first transaction with Sulphera. \
                That means you negotiated across the boundary without dissolving. \
                There is a ring of practice called Infernal Meditation. \
                The name comes from old ecclesiastical taxonomies -- \
                infernal simply meant below. Below the surface. \
                Below the ordinary subconscious. \
                I can teach you the descent. The requirement is that \
                your meditation skill is trained and that you are willing \
                to sit with what you find there. \
                It will not be pleasant. It will be true.",
        audio_ref: 0, quest_action: b"0010_KLST", teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00060007, entity_id: b"0006_WTCH",
        quest_req: 10, quest_state: QS_IN_PROGRESS,
        flag_req: &[14],
        interaction: InteractionKind::MeditationGuide, coil_layer: 6,
        conditions: &[193, 256, 261],
        text: b"Sit. Close your eyes. Do not try to see Sulphera -- \
                do not try to see anything. \
                The Rings do not respond to intention. \
                They respond to receptivity. \
                What you are learning is how to be present in a space \
                that most consciousness refuses to acknowledge. \
                The reason it refuses is not protection. It is comfort. \
                You are trading comfort for something with more uses.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00060008, entity_id: b"0006_WTCH",
        quest_req: 10, quest_state: QS_IN_PROGRESS,
        flag_req: &[14],
        interaction: InteractionKind::QuestAdvance, coil_layer: 6,
        conditions: &[193],
        text: b"That is the threshold. You found it without me pointing. \
                That is the completion of what I have to teach about descent. \
                The rest you learn from the rings themselves. \
                Sulphera receives you now. \
                What it asks of you is not courage. \
                Courage runs out. It asks for honesty. \
                Honesty is structural.",
        audio_ref: 0, quest_action: b"0010_KLST", teaches_perk: 3,
    },
];

// ── NEXIOTT (0017_ROYL) -- Caravan boss, plutocrat, radio infrastructure owner. Heartvein Heights ──
//
// He is not an information broker. He is the caravan boss.
// Trade routes in and out of Azonithia run on his schedule.
// The radio network is infrastructure he owns. The market prices he broadcasts
// are his market prices. The lottery letters travel with his caravans.
// Decades of old money. Failure has never cost him anything. He knows this.
// Voice: flat declarative. Not threatening. Not performing. Just stating facts
// about his property. He may find you interesting for a moment; that is instrumental.

pub static NEXIOTT_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00170001, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[19, 193],
        text: b"I know who you are. \
                The lottery letter came through my caravan. \
                I read the manifest.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170002, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[3, 193],
        text: b"I own the eastern routes and two of the northern ones. \
                Everything that enters or leaves Azonithia by land \
                moves through my checkpoints.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170003, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 4,
        conditions: &[193],
        text: b"The castle needs the caravans. \
                I own the caravans. \
                You can follow the chain from there.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170004, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 5,
        conditions: &[100, 193],
        text: b"The radio is mine. Twelve receivers, four transmitters. \
                Market prices, weather, aqueduct schedules go out. \
                What gets filed is a different category.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170005, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 5,
        conditions: &[19],
        text: b"My grandfather lost everything twice. \
                My father once. \
                I did not inherit money. \
                I inherited what survives when the money is gone.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170006, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[3],
        text: b"The route consolidations last season put three merchant families \
                out of operation. \
                The eastern approach needed to be unified. \
                They are part of the network now.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00170007, entity_id: b"0017_ROYL",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[128],
        interaction: InteractionKind::Dialogue, coil_layer: 5,
        conditions: &[],
        text: b"Everything you have done is on the radio record. \
                Not a judgment. A notation. \
                I want you to know it exists \
                before you make any further decisions \
                about what is worth doing here.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── DROVITTH (1018_DJNN) -- Djinn who built the Orrery, Royal Ring ───────────────

pub static DROVITTH_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x10180001, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11], // F_HYPATIA_FOUND
        interaction: InteractionKind::Dialogue, coil_layer: 8,
        conditions: &[19, 45, 193],
        text: b"You found her. Good. She has been here for two years. \
                Every one of them was structurally necessary. \
                I have been watching the Orrery confirm this, one year at a time. \
                It is a particular kind of patience -- \
                not the kind that accepts delay, \
                but the kind that recognizes the delay as the mechanism.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x10180002, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11],
        interaction: InteractionKind::LoreAccess, coil_layer: 8,
        conditions: &[45, 193],
        text: b"I built the Orrery to track the completion of one specific \
                causal chain. The chain requires a child to be born in this ring, \
                to two parents whose conjunction is arithmetically improbable \
                but not impossible. The child requires that a loop begun \
                two hundred years before closes here. \
                I have been waiting for the loop to close. \
                You are part of why it will.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x10180003, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11],
        interaction: InteractionKind::LoreAccess, coil_layer: 9,
        conditions: &[45],
        text: b"The child's name will be Saelith. \
                You do not know that name yet. You will. \
                When you do, remember that Saelith's existence is \
                retrospective proof that the entire chain was necessary -- \
                every choice, every suffering, every apparent accident. \
                That is what a Djinn born of three natures means: \
                all of it was load-bearing.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x10180004, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11],
        interaction: InteractionKind::Dialogue, coil_layer: 8,
        conditions: &[193],
        text: b"She became a demoness because the ring requires it and \
                because she chose to. She is stubborn and she is exact, \
                and love made her more so rather than less. \
                I find that admirable in a structural sense. \
                I am a Djinn. Structural admiration is the kind \
                I am best equipped to give.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x10180005, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11],
        interaction: InteractionKind::LoreAccess, coil_layer: 10,
        conditions: &[45, 19],
        text: b"The Orrery predates this city. \
                I built it before the first foundations were laid, \
                because I knew what the species carried across when they came \
                -- and I knew one particular thread in what they carried \
                would need to be watched very carefully \
                or it would close wrong.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x10180006, entity_id: b"1018_DJNN",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[11],
        interaction: InteractionKind::Dialogue, coil_layer: 11,
        conditions: &[19, 193],
        text: b"I watched the Foldings from a distance that does not translate \
                into any unit of measurement you were taught. \
                I watched this species nearly end itself four times \
                and cross the remainder of space to start again. \
                I have a great deal of patience. \
                I did not always.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── ELSA (0024_TOWN) -- Neighbour, Wiltoll Lane, 50s, 30 years on the lane ──
// Scene 0001 "Fate Knocks" -- first NPC encounter after receiving the lottery letter.
// She notices the seal. She has seen three of these in thirty years.
// She knows Hypatia by observation and proximity, not friendship.

pub static ELSA_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x00240001, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 2,
        conditions: &[3, 4],  // Puf + Zot — down-to-earth, grounded
        text: b"I saw the seal on that. Castle Azoth. You all right?",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00240002, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 2,
        conditions: &[3],
        text: b"Quiet. Works. Keeps the lane. \
                I don't think she means anyone harm.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00240003, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[6, 3],  // Kael + Puf -- life and change
        text: b"You won't be the same person coming back that you are going. \
                That's not a warning. That's just true.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00240004, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 3,
        conditions: &[19],  // Ko -- the pattern beneath
        text: b"Three. In thirty years. None of them came back changed \
                for the worse, for what it's worth. Changed, yes. Not worse.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00240005, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 2,
        conditions: &[],
        text: b"No. That's the discretion part. You're told, you go, you serve. \
                The reasons are at the castle end.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x00240006, entity_id: b"0024_TOWN",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 3,
        conditions: &[6],  // Kael -- the generative, the unexpected middle
        text: b"Not the first, not the last. Someone in the middle of a list. \
                Make of that what you will.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    // After 0002 is complete and Hypatia is gone:
    DialogueLine {
        line_id: 0x00240007, entity_id: b"0024_TOWN",
        quest_req: 2, quest_state: QS_COMPLETE, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 2,
        conditions: &[],
        text: b"I noticed the light's been off at the end of the lane. \
                You know what happened to her?",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── HYPATIA early-game (0000_0451) -- Wiltoll Lane, before she leaves ─────────
// Born Alzedroswune, adopted, 38 years in Azonithia.
// Scene 0002 "Destiny Calls" -- first real dialogue, happens in her house.
// She already knows the player is coming. She made enough tea.
// Note: the dagger item (0001_KLIT) is given via game7 inventory dispatch,
// not via teaches_perk — it's triggered when the QuestAdvance line is delivered.

pub static HYPATIA_EARLY_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x04510001, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[193, 3],  // Soa + Puf -- conscious presence, living precision
        text: b"Come in. I made enough tea.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510002, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 4,
        conditions: &[193],
        text: b"I was notified the same day you were, from a different letter. \
                The draw goes to both parties in parallel. \
                I've been waiting to see who they'd send.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510003, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::TeachSkill, coil_layer: 4,
        conditions: &[193, 4],  // Soa + Zot -- persistence + material knowledge
        text: b"Alchemy, first. How materials transform. How to read a process \
                instead of following a recipe. \
                Later, depending on what you turn out to be good at, other things.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510004, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY, flag_req: &[],
        interaction: InteractionKind::Dialogue, coil_layer: 5,
        conditions: &[193],
        text: b"I work in the mornings. I don't explain things twice, \
                but I do explain them once very carefully. \
                I'll tell you when you've made a mistake and I won't say it again after.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    // Quest 0002 advance -- the dagger handoff.
    // After this line the dagger (0001_KLIT) is added to player inventory
    // and quest 0002 moves to COMPLETE.
    DialogueLine {
        line_id: 0x04510005, entity_id: b"0000_0451",
        quest_req: 2, quest_state: QS_IN_PROGRESS, flag_req: &[],
        interaction: InteractionKind::QuestAdvance, coil_layer: 5,
        conditions: &[193, 9],  // Soa + Ta -- conscious persistence + time
        text: b"This belonged to my teacher. I want you to hold onto it for me. \
                Someone will come asking for it. \
                When they do -- don't agree immediately. \
                Think about what they're offering and why.",
        audio_ref: 0, quest_action: b"0002_KLST", teaches_perk: 0,
    },
    // Post-departure -- she is absent; this line plays when player enters
    // her house after 0002 is complete. No NPC, just ambient flavor via
    // journal entry or scene note. Encoded here for the record.
    DialogueLine {
        line_id: 0x04510006, entity_id: b"0000_0451",
        quest_req: 2, quest_state: QS_COMPLETE, flag_req: &[],
        interaction: InteractionKind::LoreAccess, coil_layer: 5,
        conditions: &[193],
        text: b"Elsewhere. The kind that's difficult to explain. \
                I'll be in contact when I can.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];

// ── HYPATIA Royal Ring -- dagger kept variant (0000_0451) ─────────────────────
// Gate: F_DAGGER_AT_REUNION (163) -- player enters Royal Ring with dagger in inventory,
// quest 0009_KLST never completed. They found another way here.
// These lines replace the standard Drovitth-introduces-Hypatia flow.

pub static HYPATIA_REUNION_DAGGER_LINES: &[DialogueLine] = &[
    DialogueLine {
        line_id: 0x04510010, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[163],  // F_DAGGER_AT_REUNION
        interaction: InteractionKind::Dialogue, coil_layer: 8,
        conditions: &[193, 45],
        text: b"You kept it.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510011, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[163],
        interaction: InteractionKind::Dialogue, coil_layer: 8,
        conditions: &[193],
        text: b"I thought there was a reasonable chance you'd trade it. \
                The offer was good, wasn't it.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510012, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[163],
        interaction: InteractionKind::Dialogue, coil_layer: 9,
        conditions: &[193, 19],  // Soa + Ko -- persistence + the full arc
        text: b"I know. That's the only way you could be standing here \
                with that still on you.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510013, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[163],
        interaction: InteractionKind::LoreAccess, coil_layer: 9,
        conditions: &[193, 45],
        text: b"You held it through everything that came between this room \
                and Wiltoll Lane. That means you understand what I meant \
                by 'hold onto it for me.' Not safekeeping. Proof.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
    DialogueLine {
        line_id: 0x04510014, entity_id: b"0000_0451",
        quest_req: 0, quest_state: QS_ANY,
        flag_req: &[163],
        interaction: InteractionKind::Dialogue, coil_layer: 10,
        conditions: &[193],
        text: b"You're someone I'd trust with the rest of it.",
        audio_ref: 0, quest_action: &[], teaches_perk: 0,
    },
];
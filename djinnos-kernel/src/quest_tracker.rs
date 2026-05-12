// quest_tracker.rs — Quest state machine for Ko's Labyrinth (7_KLGS).
//
// Quest lifecycle: Offered → InProgress → Complete (terminal states).
// on_complete() fires the perk auto-unlock hook for meditation perks.
//
// ko: dispatch:
//   quest status <slug>   — "offered"|"in_progress"|"complete"|"unknown"
//   quest offer  <slug>   — mark quest as offered (dev/world event)
//   quest accept <slug>   — player accepts (Offered → InProgress)
//   quest complete <slug> — mark complete, fire hooks
//   quest list            — all active quests with state

use crate::player_state::{QUEST_OFFERED, QUEST_IN_PROGRESS, QUEST_COMPLETE};

// ── Quest lifecycle ───────────────────────────────────────────────────────────

pub fn offer(slug: &[u8]) {
    if crate::player_state::quest_state(slug).is_none() {
        crate::player_state::quest_set(slug, QUEST_OFFERED);
        if let Some(n) = crate::ko_flags::quest_num(slug) {
            // Don't set accept flag — just track that it was offered.
            let _ = n;
        }
    }
}

pub fn accept(slug: &[u8]) -> bool {
    match crate::player_state::quest_state(slug) {
        Some(QUEST_OFFERED) | None => {
            crate::player_state::quest_set(slug, QUEST_IN_PROGRESS);
            if let Some(n) = crate::ko_flags::quest_num(slug) {
                crate::ko_flags::ko_set(crate::ko_flags::quest_flag_accept(n));
            }
            crate::eigenstate::advance(crate::eigenstate::T_GRAPEVINE);
            true
        }
        _ => false,
    }
}

pub fn complete(slug: &[u8]) {
    crate::player_state::quest_set(slug, QUEST_COMPLETE);
    if let Some(n) = crate::ko_flags::quest_num(slug) {
        crate::ko_flags::ko_set(crate::ko_flags::quest_flag_complete(n));
    }
    on_complete(slug);
    // Persist state after meaningful quest event.
    crate::player_state::save();
}

pub fn is_complete(slug: &[u8]) -> bool {
    crate::player_state::quest_state(slug) == Some(QUEST_COMPLETE)
}

pub fn status_str(slug: &[u8]) -> &'static str {
    match crate::player_state::quest_state(slug) {
        Some(QUEST_OFFERED)     => "offered",
        Some(QUEST_IN_PROGRESS) => "in_progress",
        Some(QUEST_COMPLETE)    => "complete",
        _                       => "unknown",
    }
}

// ── on_complete hook ──────────────────────────────────────────────────────────
//
// Fired after every quest completion.  Checks whether this quest gates a
// meditation perk; if the player has meditation trained, auto-unlocks it.
//
// Perk–quest link table (mirrors skillRegistry.js):
//   0007_KLST → hypnotic_meditation  (also sets F_MERCURIE_OPEN)
//   0008_KLST → alchemical_meditation
//   0010_KLST → infernal_meditation  (also opens Sulphera; 0009 gates this quest)
//   0011_KLST → depth_meditation
//   0016_KLST → transcendental_meditation
//   0026_KLST → zen_meditation

fn on_complete(slug: &[u8]) {
    // Find any perk gated by this quest slug and auto-unlock if eligible.
    for p in crate::skills::ALL_PERKS.iter() {
        if let crate::skills::PerkGate::Quest(q) = p.gate {
            if q == slug {
                // Meditation perks require meditation trained; others just need eligibility.
                let _ = crate::skills::unlock_perk_by_id(p.perk_id);
            }
        }
    }

    // Quest-specific world flags.
    match slug {
        b"0001_KLST" => crate::ko_flags::ko_set(crate::ko_flags::F_LABYRINTH_ENTERED),
        b"0003_KLST" => crate::ko_flags::ko_set(crate::ko_flags::F_SIDHAL_MET),
        // Dream of Glass: player has experienced the Asmodean crystal dream.
        // Grants partial Mercurie awareness; full access via quest 0016.
        b"0007_KLST" => crate::ko_flags::ko_set(crate::ko_flags::F_MERCURIE_OPEN),
        // Perfect Circles: Alfir teaches Infernal Meditation → Sulphera open.
        b"0010_KLST" => crate::ko_flags::ko_set(crate::ko_flags::F_SULPHERA_UNLOCKED),
        _ => {}
    }
}

// ── Kobra dispatch — `quest` namespace ───────────────────────────────────────

pub fn quest_dispatch(args: &[u8], out: &mut crate::kobra::EvalResult) {
    let (verb, rest) = split_verb(args);
    match verb {
        b"status" => {
            out.push_text(status_str(rest).as_bytes());
            out.push_line();
        }
        b"offer" => {
            offer(rest);
            out.push_text(b"offered: ");
            out.push_text(rest);
            out.push_line();
        }
        b"accept" => {
            if accept(rest) {
                out.push_text(b"accepted: ");
                out.push_text(rest);
            } else {
                out.push_text(b"quest already in progress or complete");
            }
            out.push_line();
        }
        b"complete" => {
            complete(rest);
            out.push_text(b"complete: ");
            out.push_text(rest);
            out.push_line();
        }
        b"list" | b"" => {
            let ps = crate::player_state::get();
            if ps.quest_count == 0 {
                out.push_text(b"no active quests");
                out.push_line();
            } else {
                for i in 0..ps.quest_count as usize {
                    let q = &ps.quests[i];
                    if q.is_empty() { continue; }
                    let state_tag = match q.state {
                        QUEST_OFFERED     => b"offered " as &[u8],
                        QUEST_IN_PROGRESS => b"active  ",
                        QUEST_COMPLETE    => b"done    ",
                        _                 => b"?       ",
                    };
                    out.push_text(state_tag);
                    out.push_text(&q.slug[..q.slug.iter().position(|&b| b == 0).unwrap_or(9)]);
                    out.push_line();
                }
            }
        }
        _ => {
            out.push_text(b"quest: status <slug> | offer <slug> | accept <slug> | complete <slug> | list");
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

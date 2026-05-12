// perk_screen.rs -- Fallout-style perk selection screen for DjinnOS.
//
// Layout:
//   Top bar:    VITRIOL stats (V:N I:N T:N R:N I:N O:N L:N)
//   Left panel: skill list with available slot count
//   Centre:     perk pool for selected skill (eligible / locked / taken)
//   Right:      selected perk details (flavor, effect, requirements)
//   Bottom:     controls
//
// Navigation:
//   Up/Down    = move selection within active panel
//   Left/Right = switch focus between skill list and perk list
//   Enter      = take selected eligible perk (if slot available)
//   Esc        = exit

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;
use crate::skills::{ALL_PERKS, SKILL_DISPLAY, perk_eligible_by_id, unlock_perk_by_id};
use crate::player_state::{perk_slots_available, SKILL_COUNT};

// -- Screen state -------------------------------------------------------------

#[derive(Copy, Clone, PartialEq)]
enum Focus { Skills, Perks }

pub struct PerkScreen {
    pub exited:      bool,
    focus:           Focus,
    skill_cursor:    usize,    // which skill is selected in left panel
    perk_cursor:     usize,    // which perk is selected in centre panel
    // Cache of perk IDs for the currently selected skill (rebuilt on skill change).
    pool:            [u8; 16],
    pool_n:          usize,
    rule_y:          u32,
    msg:             [u8; 64],
    msg_n:           usize,
}

static mut PS: PerkScreen = PerkScreen {
    exited:       false,
    focus:        Focus::Skills,
    skill_cursor: 0,
    perk_cursor:  0,
    pool:         [0u8; 16],
    pool_n:       0,
    rule_y:       0,
    msg:          [0u8; 64],
    msg_n:        0,
};

pub fn screen() -> &'static mut PerkScreen { unsafe { &mut PS } }

static mut PERK_REQ: bool = false;
pub fn request()         { unsafe { PERK_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = PERK_REQ; PERK_REQ = false; r } }

impl PerkScreen {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y       = rule_y;
        self.exited       = false;
        self.focus        = Focus::Skills;
        self.skill_cursor = 0;
        self.perk_cursor  = 0;
        self.msg_n        = 0;
        self.rebuild_pool();
    }

    pub fn exited(&self) -> bool { self.exited }

    fn rebuild_pool(&mut self) {
        self.pool_n = 0;
        let idx = self.skill_cursor;
        // Collect perks belonging to this skill.
        for p in ALL_PERKS.iter() {
            if p.skill_idx as usize == idx && self.pool_n < 16 {
                self.pool[self.pool_n] = p.perk_id;
                self.pool_n += 1;
            }
        }
        // VITRIOL-only perks shown when Special is selected (idx >= SKILL_COUNT).
        if idx == SKILL_COUNT {
            for p in ALL_PERKS.iter() {
                if p.skill_idx == 0xFF && p.perk_id < 76 && self.pool_n < 16 {
                    self.pool[self.pool_n] = p.perk_id;
                    self.pool_n += 1;
                }
            }
        }
        if idx == SKILL_COUNT + 1 {
            // Genocide perks visible if F_GENOCIDE_PATH set.
            if crate::ko_flags::ko_test(crate::ko_flags::F_GENOCIDE_PATH) {
                for p in ALL_PERKS.iter() {
                    if p.skill_idx == 0xFF && p.perk_id >= 76 && self.pool_n < 16 {
                        self.pool[self.pool_n] = p.perk_id;
                        self.pool_n += 1;
                    }
                }
            }
        }
        self.perk_cursor = 0;
    }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.exited = true; }
            Key::Left   => { self.focus = Focus::Skills; }
            Key::Right  => { if self.pool_n > 0 { self.focus = Focus::Perks; } }
            Key::Up     => match self.focus {
                Focus::Skills => {
                    if self.skill_cursor > 0 { self.skill_cursor -= 1; self.rebuild_pool(); }
                }
                Focus::Perks => {
                    if self.perk_cursor > 0 { self.perk_cursor -= 1; }
                }
            }
            Key::Down   => match self.focus {
                Focus::Skills => {
                    // +2 for VITRIOL-only and genocide groups beyond skill list.
                    if self.skill_cursor < SKILL_COUNT + 1 {
                        self.skill_cursor += 1;
                        self.rebuild_pool();
                    }
                }
                Focus::Perks => {
                    if self.perk_cursor + 1 < self.pool_n { self.perk_cursor += 1; }
                }
            }
            Key::Enter => {
                if self.focus == Focus::Perks && self.perk_cursor < self.pool_n {
                    let pid = self.pool[self.perk_cursor];
                    // Check a slot is available (for skill-bound perks).
                    let def = ALL_PERKS.iter().find(|p| p.perk_id == pid);
                    let slot_ok = def.map_or(true, |d| {
                        d.skill_idx == 0xFF || perk_slots_available(d.skill_idx as usize) > 0
                    });
                    if !slot_ok {
                        self.set_msg(b"No slots available -- train the skill further.");
                    } else {
                        match unlock_perk_by_id(pid) {
                            Ok(()) => {
                                let name = def.map(|d| d.name).unwrap_or(b"perk");
                                let mut m = [0u8; 64]; let n = name.len().min(60);
                                m[..n].copy_from_slice(&name[..n]);
                                m[n..n+11].copy_from_slice(b" unlocked. ");
                                self.set_msg(&m[..n+11]);
                                self.rebuild_pool();
                            }
                            Err(e) => { self.set_msg(e.as_bytes()); }
                        }
                    }
                }
            }
            _ => {}
        }
    }

    fn set_msg(&mut self, m: &[u8]) {
        let n = m.len().min(64);
        self.msg[..n].copy_from_slice(&m[..n]);
        self.msg_n = n;
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let w   = gpu.width();
        let h   = gpu.height();
        let top = self.rule_y + 4;
        it.fill(0, top, w, h.saturating_sub(top), t.bg);

        // ── VITRIOL bar ───────────────────────────────────────────────────────
        let ps   = crate::player_state::get();
        let vlbl = [b"V" as &[u8], b"I", b"T", b"R", b"I", b"O", b"L"];
        let vcol = [
            (200u8, 100u8, 100u8), // V red
            (100, 180, 220),        // I blue
            (180, 130, 80),         // T amber
            (80, 200, 130),         // R teal
            (180, 100, 220),        // I purple
            (220, 180, 60),         // O gold
            (120, 220, 120),        // L green
        ];
        let mut vx = 20u32;
        for i in 0..7 {
            it.text(vx, top + 4, core::str::from_utf8(vlbl[i]).unwrap_or("?"),
                    1, vcol[i]);
            vx += 8;
            let mut nb = [0u8; 4];
            nb[0] = b'0' + ps.vitriol[i]; nb[1] = 0;
            it.text(vx, top + 4, core::str::from_utf8(&nb[..1]).unwrap_or("?"),
                    1, vcol[i]);
            vx += 14;
        }
        it.fill(0, top + 16, w, 1, t.rule);

        // ── Skill list (left panel) ───────────────────────────────────────────
        let content_top = top + 20;
        let left_w = 140u32;
        it.fill(0, content_top, left_w, h.saturating_sub(content_top + 20), t.surface);

        const VISIBLE_SKILLS: usize = 22;
        let skill_names_ext: [&[u8]; SKILL_COUNT + 2] = [
            b"Barter", b"Energy Weapons", b"Explosives", b"Guns", b"Lockpick",
            b"Medicine", b"Melee Weapons", b"Repair", b"Alchemy", b"Sneak",
            b"Hack", b"Speech", b"Survival", b"Unarmed", b"Meditation",
            b"Magic", b"Blacksmithing", b"Silversmithing", b"Goldsmithing",
            b"VITRIOL Perks", b"Genocide Perks",
        ];
        let scroll_start = if self.skill_cursor >= VISIBLE_SKILLS {
            self.skill_cursor + 1 - VISIBLE_SKILLS } else { 0 };

        for (vi, si) in (scroll_start..(scroll_start + VISIBLE_SKILLS).min(SKILL_COUNT+2)).enumerate() {
            let y   = content_top + vi as u32 * 12;
            let sel = si == self.skill_cursor && self.focus == Focus::Skills;
            let col = if sel { t.accent } else { t.text };
            // Slot count for skill-bound entries.
            let slots = if si < SKILL_COUNT { perk_slots_available(si) } else { 0 };
            let s = core::str::from_utf8(skill_names_ext[si]).unwrap_or("?");
            it.text(6, y, s, 1, col);
            if si < SKILL_COUNT && slots > 0 {
                let mut sb = [0u8; 4]; sb[0] = b'0' + slots; sb[1] = 0;
                it.text(left_w - 12, y,
                    core::str::from_utf8(&sb[..1]).unwrap_or("?"), 1, t.accent);
            }
        }

        // ── Perk pool (centre panel) ──────────────────────────────────────────
        let centre_x = left_w + 8;
        let centre_w = (w.saturating_sub(left_w + 8 + 200)).min(240);

        if self.pool_n == 0 {
            it.text(centre_x, content_top, "(no perks for this skill)", 1, t.text_dim);
        } else {
            for i in 0..self.pool_n {
                let pid  = self.pool[i];
                let has  = crate::player_state::has_perk(pid);
                let (elig, _) = perk_eligible_by_id(pid);
                let tag: &[u8] = if has { b"[X]" } else if elig { b"[ ]" } else { b"[-]" };
                let col = if has  { t.text_dim }
                          else if elig { if i == self.perk_cursor && self.focus == Focus::Perks
                                         { t.accent } else { t.text } }
                          else { (60, 60, 70) };
                let y = content_top + i as u32 * 14;
                it.text(centre_x, y, core::str::from_utf8(tag).unwrap_or("?"), 1, col);
                if let Some(def) = ALL_PERKS.iter().find(|p| p.perk_id == pid) {
                    it.text(centre_x + 22, y,
                        core::str::from_utf8(def.name).unwrap_or("?"), 1, col);
                }
            }
        }

        // ── Perk detail (right panel) ─────────────────────────────────────────
        let detail_x = centre_x + centre_w + 8;
        if self.perk_cursor < self.pool_n {
            let pid = self.pool[self.perk_cursor];
            if let Some(def) = ALL_PERKS.iter().find(|p| p.perk_id == pid) {
                it.text(detail_x, content_top,
                    core::str::from_utf8(def.name).unwrap_or("?"), 2, t.header);
                // Flavor
                if def.flavor.len() > 0 {
                    it.text(detail_x, content_top + 20,
                        core::str::from_utf8(def.flavor).unwrap_or(""), 1, t.text_dim);
                }
                // Effect
                it.text(detail_x, content_top + 36,
                    core::str::from_utf8(def.effect).unwrap_or(""), 1, t.text);
                // Requirements
                let req_y = content_top + 56;
                it.text(detail_x, req_y, "Requires:", 1, t.text_dim);
                if def.min_rank > 0 {
                    let sname = if def.skill_idx < SKILL_COUNT as u8 {
                        core::str::from_utf8(SKILL_DISPLAY[def.skill_idx as usize]).unwrap_or("?")
                    } else { "special" };
                    let mut rb = [0u8; 40]; let mut rn = 0;
                    let sn = sname.len().min(20);
                    rb[..sn].copy_from_slice(sname.as_bytes()); rn += sn;
                    rb[rn] = b' '; rn += 1;
                    rb[rn] = b'0' + def.min_rank / 10; rn += 1;
                    rb[rn] = b'0' + def.min_rank % 10; rn += 1;
                    it.text(detail_x, req_y + 12,
                        core::str::from_utf8(&rb[..rn]).unwrap_or("?"), 1, t.text_dim);
                }
                // Sanity delta
                let sd = def.sanity_delta;
                if sd.iter().any(|&x| x > 0) {
                    it.text(detail_x, req_y + 26, "Sanity:", 1, t.text_dim);
                    let labels = [b"Alc" as &[u8], b"Nar", b"Ter", b"Cos"];
                    let mut sx = detail_x;
                    for i in 0..4 {
                        if sd[i] > 0 {
                            it.text(sx, req_y + 38,
                                core::str::from_utf8(labels[i]).unwrap_or("?"), 1, t.accent);
                            let mut nb = [0u8; 4]; nb[0] = b'+'; nb[1] = b'0' + sd[i] / 10;
                            nb[2] = b'0' + sd[i] % 10; nb[3] = 0;
                            it.text(sx + 18, req_y + 38,
                                core::str::from_utf8(&nb[..3]).unwrap_or("?"), 1, t.accent);
                            sx += 50;
                        }
                    }
                }
            }
        }

        // ── Message bar ───────────────────────────────────────────────────────
        if self.msg_n > 0 {
            let ms = core::str::from_utf8(&self.msg[..self.msg_n]).unwrap_or("");
            it.text(20, h.saturating_sub(24), ms, 1, t.accent);
        }

        // ── Controls ──────────────────────────────────────────────────────────
        it.fill(0, h.saturating_sub(14), w, 14, t.surface);
        it.text(8, h.saturating_sub(12),
            "arrows=navigate  Enter=take perk  Esc=back", 1, t.text_dim);
    }
}

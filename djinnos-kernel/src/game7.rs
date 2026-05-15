// game7.rs -- Ko's Labyrinth (7_KLGS) game loop.
//
// Sub-modes:
//   ZoneView    -- zone description, exits, and contextual actions
//   DungeonWalk -- ASCII-map navigation within a dungeon zone
//
// Zone navigation follows the graph in zone_registry::ALL_ZONES.
// Entering a Dungeon/BossArena zone generates a BSP layout via dungeon::dungeon().
// Combat triggers are delegated to AppMode::Combat (via combat::request_encounter()).
// On combat exit the main loop restores AppMode::Game7 if GAME7_FROM_COMBAT is set.

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;
use crate::zone_registry::{zone_by_id, ZoneKind, Realm};
use crate::ko_flags;
use crate::dungeon::{self, DUN_W, DUN_H};

// ── Sub-mode ──────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
enum G7Sub { ZoneView, DungeonWalk, Pause, KoDream }

// ── Menu item ─────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
enum MenuAction {
    GoZone(usize),
    EnterDungeon,
    Shop,
    Forage,
    Meditate,
    Rest,
    Journal,
    Perks,
    Examine,
    Talk([u8; 16], usize),   // entity_id bytes + length
}

#[derive(Copy, Clone)]
struct MenuItem {
    label:   [u8; 48],
    label_n: usize,
    action:  MenuAction,
}

impl MenuItem {
    const EMPTY: Self = Self {
        label: [0u8; 48], label_n: 0, action: MenuAction::Examine,
    };
    fn from(text: &[u8], action: MenuAction) -> Self {
        let mut m = Self::EMPTY;
        let n = text.len().min(47);
        m.label[..n].copy_from_slice(&text[..n]);
        m.label_n = n;
        m.action  = action;
        m
    }
}

// ── Game7 state ───────────────────────────────────────────────────────────────

pub struct Game7 {
    pub exited:    bool,
    rule_y:        u32,
    zone:          [u8; 40],
    zone_n:        usize,
    cursor:        usize,
    sub:           G7Sub,
    items:         [MenuItem; 16],
    item_n:        usize,
    walk_x:        usize,
    walk_y:        usize,
    walk_map:      [[u8; DUN_W]; DUN_H],
    msg:           [u8; 64],
    msg_n:         usize,
    pause_cursor:  usize,
    dream_text:    [u8; 256],
    dream_text_n:  usize,
}

static mut G7: Game7 = Game7 {
    exited:       false,
    rule_y:       0,
    zone:         [0u8; 40],
    zone_n:       0,
    cursor:       0,
    sub:          G7Sub::ZoneView,
    items:        [MenuItem::EMPTY; 16],
    item_n:       0,
    walk_x:       1,
    walk_y:       1,
    walk_map:     [[b'#'; DUN_W]; DUN_H],
    msg:          [0u8; 64],
    msg_n:        0,
    pause_cursor: 0,
    dream_text:   [0u8; 256],
    dream_text_n: 0,
};

// Counts Rest/Meditate actions — every DREAM_EVERY triggers a Ko dream.
static mut DREAM_TICK: u32 = 0;
const    DREAM_EVERY: u32  = 4;

pub fn game7() -> &'static mut Game7 { unsafe { &mut G7 } }

// Lets main.rs return to Game7 after AppMode::Combat exits.
pub static mut GAME7_FROM_COMBAT: bool = false;
pub fn set_from_combat()          { unsafe { GAME7_FROM_COMBAT = true; } }
pub fn consume_from_combat() -> bool {
    unsafe { let r = GAME7_FROM_COMBAT; GAME7_FROM_COMBAT = false; r }
}

static mut G7_REQ: bool = false;
pub fn request()         { unsafe { G7_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = G7_REQ; G7_REQ = false; r } }

// ── Implementation ────────────────────────────────────────────────────────────

impl Game7 {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y = rule_y;
        self.exited = false;
        self.sub    = G7Sub::ZoneView;
        self.msg_n  = 0;
        if self.zone_n == 0 {
            let s = b"wiltoll_lane";
            self.zone[..s.len()].copy_from_slice(s);
            self.zone_n = s.len();
        }
        // Auto-offer the opening quest on first play.
        if !ko_flags::ko_test(ko_flags::F_LABYRINTH_ENTERED) {
            crate::quest_tracker::offer(b"0001_KLST");
            crate::quest_tracker::accept(b"0001_KLST");
        }
        self.enter_zone();
    }

    fn zone_id(&self) -> &[u8] { &self.zone[..self.zone_n] }
    /// Public accessor for Kobra/Faerie zone queries (read-only).
    pub fn zone_id_pub(&self) -> &[u8] { &self.zone[..self.zone_n] }

    fn set_zone(&mut self, id: &[u8]) {
        let n = id.len().min(40);
        self.zone[..n].copy_from_slice(&id[..n]);
        self.zone_n = n;
    }

    fn enter_zone(&mut self) {
        self.cursor = 0;
        self.msg_n  = 0;
        let id = &self.zone[..self.zone_n];

        // Set world-state flags on first entry.
        match id {
            b"wiltoll_lane"          => ko_flags::ko_set(ko_flags::F_WILTOLL_ENTERED),
            b"azonithia_west"
            | b"june_street"
            | b"temple_quarter"
            | b"hopefare"
            | b"orebustle"           => ko_flags::ko_set(ko_flags::F_AZONITHIA_ENTERED),
            b"castle_azoth_gates"
            | b"castle_azoth_halls"  => ko_flags::ko_set(ko_flags::F_CASTLE_AZOTH_SEEN),
            _ => {}
        }

        // Gate check: Sulphera requires the Infernal perk.
        if let Some(z) = zone_by_id(id) {
            if z.realm == Realm::Sulphera
               && !ko_flags::ko_test(ko_flags::F_SULPHERA_UNLOCKED)
            {
                self.set_msg(b"The Infernal Meditation perk gates Sulphera.");
                self.set_zone(b"wiltoll_lane");
            }
        }

        self.build_menu();
    }

    fn build_menu(&mut self) {
        self.item_n = 0;
        // Copy zone_id to a local array so self is not borrowed through id.
        let mut zid_buf = [0u8; 40];
        let zid_n = self.zone_n.min(40);
        zid_buf[..zid_n].copy_from_slice(&self.zone[..zid_n]);
        let id   = &zid_buf[..zid_n];
        let zdef = zone_by_id(id);

        // Exits.
        if let Some(z) = zdef {
            for (i, &exit_id) in z.exits.iter().enumerate() {
                if let Some(dest) = zone_by_id(exit_id) {
                    if dest.open() && self.item_n < 14 {
                        let mut lbl = [0u8; 48];
                        lbl[0] = b'-'; lbl[1] = b'>'; lbl[2] = b' ';
                        let nn = dest.name.len().min(44);
                        lbl[3..3+nn].copy_from_slice(&dest.name[..nn]);
                        self.items[self.item_n] = MenuItem {
                            label: lbl, label_n: 3 + nn,
                            action: MenuAction::GoZone(i),
                        };
                        self.item_n += 1;
                    }
                }
            }
        }

        // Context actions.
        if let Some(z) = zdef {
            match z.kind {
                ZoneKind::Dungeon | ZoneKind::BossArena => {
                    self.push(b"Enter dungeon", MenuAction::EnterDungeon);
                }
                ZoneKind::Market => {
                    self.push(b"Open shop", MenuAction::Shop);
                }
                ZoneKind::Town => {
                    self.push(b"Rest here",  MenuAction::Rest);
                    self.push(b"Open shop",  MenuAction::Shop);
                }
                ZoneKind::Rest => {
                    self.push(b"Rest here",  MenuAction::Rest);
                    self.push(b"Meditate",   MenuAction::Meditate);
                }
                ZoneKind::Temple => {
                    self.push(b"Meditate",   MenuAction::Meditate);
                }
                ZoneKind::Wilderness => {
                    self.push(b"Forage",     MenuAction::Forage);
                    self.push(b"Meditate",   MenuAction::Meditate);
                }
                ZoneKind::Chamber | ZoneKind::Threshold => {
                    self.push(b"Examine",    MenuAction::Examine);
                }
            }
        }

        // NPCs present in this zone.
        for npc in crate::npc_placements::npcs_in_zone(id) {
            if self.item_n >= 14 { break; }
            let mut eid = [0u8; 16];
            let en = npc.entity_id.len().min(16);
            eid[..en].copy_from_slice(&npc.entity_id[..en]);
            // Label: "Talk to [Name]"
            let mut lbl = [0u8; 48];
            lbl[0..8].copy_from_slice(b"Talk to ");
            let nn = npc.name.len().min(39);
            lbl[8..8+nn].copy_from_slice(&npc.name[..nn]);
            self.items[self.item_n] = MenuItem {
                label: lbl, label_n: 8 + nn,
                action: MenuAction::Talk(eid, en),
            };
            self.item_n += 1;
        }

        self.push(b"Journal", MenuAction::Journal);
        self.push(b"Perks",   MenuAction::Perks);

        if self.cursor >= self.item_n { self.cursor = 0; }
    }

    fn push(&mut self, text: &[u8], action: MenuAction) {
        if self.item_n < 16 {
            self.items[self.item_n] = MenuItem::from(text, action);
            self.item_n += 1;
        }
    }

    fn set_msg(&mut self, m: &[u8]) {
        let n = m.len().min(64);
        self.msg[..n].copy_from_slice(&m[..n]);
        self.msg_n = n;
    }

    // ── Key handling ──────────────────────────────────────────────────────────

    pub fn handle_key(&mut self, key: Key) {
        match self.sub {
            G7Sub::ZoneView    => self.zone_key(key),
            G7Sub::DungeonWalk => self.walk_key(key),
            G7Sub::Pause       => self.pause_key(key),
            G7Sub::KoDream     => self.dream_key(key),
        }
    }

    fn zone_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.sub = G7Sub::Pause; self.pause_cursor = 0; }
            Key::Up     => {
                if self.cursor > 0 { self.cursor -= 1; }
                else { self.cursor = self.item_n.saturating_sub(1); }
            }
            Key::Down   => {
                if self.item_n > 0 {
                    self.cursor = (self.cursor + 1).min(self.item_n - 1);
                }
            }
            Key::Enter  => { self.activate(); }
            _ => {}
        }
    }

    fn activate(&mut self) {
        let idx = self.cursor;
        if idx >= self.item_n { return; }
        self.msg_n = 0;
        let action = self.items[idx].action;
        match action {
            MenuAction::GoZone(exit_i) => {
                let id = self.zone_id();
                if let Some(z) = zone_by_id(id) {
                    if let Some(&dest_id) = z.exits.get(exit_i) {
                        self.set_zone(dest_id);
                        self.enter_zone();
                    }
                }
            }
            MenuAction::EnterDungeon => {
                let zone_copy = self.zone;
                let zone_n    = self.zone_n;
                dungeon::dungeon().generate(&zone_copy[..zone_n]);
                let src = dungeon::ascii_map();
                self.walk_map.copy_from_slice(src);
                let (sx, sy)  = dungeon::dungeon().start;
                self.walk_x = sx;
                self.walk_y = sy;
                self.sub = G7Sub::DungeonWalk;
                self.set_msg(b"Entered dungeon. Arrows=move  Esc=flee");
            }
            MenuAction::Shop => {
                use crate::shop::{self, NpcShopId};
                let zone_copy = self.zone;
                let zone_n    = self.zone_n;
                let id        = &zone_copy[..zone_n];
                let ry        = self.rule_y;
                match id {
                    b"june_street"    => shop::shop().open_npc_shop(ry, NpcShopId::JuneProvisions),
                    b"temple_quarter" => shop::shop().open_npc_shop(ry, NpcShopId::TempleApothecary),
                    b"hopefare"
                    | b"wiltoll_lane" => shop::shop().open_npc_shop(ry, NpcShopId::HopefarePawnbroker),
                    b"orebustle"
                    | b"mt_hieronymus_foothills"
                                      => shop::shop().open_npc_shop(ry, NpcShopId::AlchemistWorkshop),
                    b"the_asmodean_market"
                    | b"lust_outer"   => shop::shop().open_npc_shop(ry, NpcShopId::JuneArmsAndTools),
                    _                 => shop::shop().open_player_shop(ry),
                }
                shop::request_open();
            }
            MenuAction::Forage => {
                let zone_copy = self.zone;
                let zone_n    = self.zone_n;
                let msg = crate::foraging::forage_zone(&zone_copy[..zone_n]);
                self.set_msg(msg);
            }
            MenuAction::Meditate => {
                self.maybe_trigger_dream();
                crate::meditation::meditation().open(self.rule_y);
                crate::meditation::request();
            }
            MenuAction::Rest => {
                let ps = crate::player_state::get_mut();
                for s in &mut ps.sanity { *s = (*s).saturating_add(5); }
                crate::player_state::save();
                self.maybe_trigger_dream();
                if self.sub != G7Sub::KoDream {
                    self.set_msg(b"Rested. Sanity partially restored. Game saved.");
                }
            }
            MenuAction::Journal => {
                crate::journal::journal().open(self.rule_y);
                crate::journal::request();
            }
            MenuAction::Perks => {
                crate::perk_screen::screen().open(self.rule_y);
                crate::perk_screen::request();
            }
            MenuAction::Examine => {
                if let Some(z) = zone_by_id(self.zone_id()) {
                    self.set_msg(z.desc);
                }
            }
            MenuAction::Talk(eid, en) => {
                crate::npc_screen::screen().open(self.rule_y, &eid[..en]);
                crate::npc_screen::request();
            }
        }
    }

    fn walk_key(&mut self, key: Key) {
        match key {
            Key::Escape => {
                dungeon::dungeon().record_exit(dungeon::LastExit::Fled);
                self.sub = G7Sub::ZoneView;
                self.build_menu();
                self.set_msg(b"You fled the dungeon.");
            }
            Key::Up    | Key::Char(b'w') | Key::Char(b'W') => {
                let (nx, ny) = (self.walk_x, self.walk_y.wrapping_sub(1));
                self.try_walk(nx, ny);
            }
            Key::Down  | Key::Char(b's') | Key::Char(b'S') => {
                let (nx, ny) = (self.walk_x, self.walk_y.wrapping_add(1));
                self.try_walk(nx, ny);
            }
            Key::Left  | Key::Char(b'a') | Key::Char(b'A') => {
                let (nx, ny) = (self.walk_x.wrapping_sub(1), self.walk_y);
                self.try_walk(nx, ny);
            }
            Key::Right | Key::Char(b'd') | Key::Char(b'D') => {
                let (nx, ny) = (self.walk_x.wrapping_add(1), self.walk_y);
                self.try_walk(nx, ny);
            }
            _ => {}
        }
    }

    fn pause_key(&mut self, key: Key) {
        // Pause menu: 0 = Continue, 1 = Return to Atelier
        match key {
            Key::Escape => { self.sub = G7Sub::ZoneView; }
            Key::Up => {
                if self.pause_cursor > 0 { self.pause_cursor -= 1; }
            }
            Key::Down => {
                if self.pause_cursor < 1 { self.pause_cursor += 1; }
            }
            Key::Enter => {
                match self.pause_cursor {
                    0 => { self.sub = G7Sub::ZoneView; }
                    _ => { self.exited = true; }
                }
            }
            _ => {}
        }
    }

    fn dream_key(&mut self, key: Key) {
        match key {
            Key::Enter | Key::Escape | Key::Char(b' ') => {
                self.sub = G7Sub::ZoneView;
            }
            _ => {}
        }
    }

    fn maybe_trigger_dream(&mut self) {
        unsafe {
            DREAM_TICK += 1;
            if DREAM_TICK % DREAM_EVERY == 0 {
                self.enter_ko_dream();
            }
        }
    }

    fn enter_ko_dream(&mut self) {
        let lines = crate::dialogue::KO_LINES;
        if lines.is_empty() { return; }
        let idx = unsafe { ((DREAM_TICK / DREAM_EVERY).wrapping_sub(1)) as usize % lines.len() };
        let text = lines[idx].text;
        let n = text.len().min(255);
        self.dream_text[..n].copy_from_slice(&text[..n]);
        self.dream_text_n = n;
        self.sub = G7Sub::KoDream;
    }

    fn try_walk(&mut self, nx: usize, ny: usize) {
        if nx >= DUN_W || ny >= DUN_H { return; }
        match self.walk_map[ny][nx] {
            b'#' => {}
            b'+' => { self.walk_map[self.walk_y][self.walk_x] = b'.'; self.walk_x = nx; self.walk_y = ny; }
            b'@' => {
                self.walk_map[ny][nx] = b'.';
                crate::game7::set_from_combat();
                crate::combat::request_encounter(crate::combat::ENEMY_SHADE, self.rule_y);
                self.set_msg(b"Enemy encountered!");
            }
            b'E' => {
                dungeon::dungeon().record_exit(dungeon::LastExit::Completed);
                self.sub = G7Sub::ZoneView;
                self.build_menu();
                self.set_msg(b"Dungeon cleared.");
            }
            _ => { self.walk_map[self.walk_y][self.walk_x] = b'.'; self.walk_x = nx; self.walk_y = ny; }
        }
    }

    /// Called by main loop when returning from AppMode::Combat that was triggered here.
    pub fn on_combat_return(&mut self) {
        if crate::combat::combat().result == crate::combat::CombatResult::PlayerDied {
            dungeon::dungeon().record_exit(dungeon::LastExit::Died);
            self.sub = G7Sub::ZoneView;
            self.build_menu();
            self.set_msg(b"You died. The dungeon reshuffled.");
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    pub fn render(&self, gpu: &dyn GpuSurface) {
        match self.sub {
            G7Sub::ZoneView    => self.render_zone(gpu),
            G7Sub::DungeonWalk => self.render_walk(gpu),
            G7Sub::Pause       => { self.render_zone(gpu); self.render_pause(gpu); }
            G7Sub::KoDream     => self.render_dream(gpu),
        }
    }

    fn render_zone(&self, gpu: &dyn GpuSurface) {
        let it = It::new(gpu);
        let t  = style::get();
        let w  = gpu.width();
        let h  = gpu.height();
        let y0 = self.rule_y + 4;
        it.fill(0, y0, w, h.saturating_sub(y0), t.bg);

        let id   = &self.zone[..self.zone_n];
        let zdef = zone_by_id(id);

        let name: &[u8] = zdef.map(|z| z.name).unwrap_or(b"Unknown Zone");
        it.tt(20, y0 as i32 + 6,
            core::str::from_utf8(name).unwrap_or("?"), 17.0, t.header);

        let rtag: &[u8] = zdef.map(|z| -> &[u8] { match z.realm {
            Realm::Lapidus  => b"Lapidus",
            Realm::Mercurie => b"Mercurie",
            Realm::Sulphera => b"Sulphera",
        }}).unwrap_or(b"");
        it.tt_right(w as i32 - 16, y0 as i32 + 8,
            core::str::from_utf8(rtag).unwrap_or(""), 11.0, t.text_dim);

        let ktag: &[u8] = zdef.map(|z| -> &[u8] { match z.kind {
            ZoneKind::Town       => b"Town",
            ZoneKind::Market     => b"Market",
            ZoneKind::Temple     => b"Temple",
            ZoneKind::Wilderness => b"Wilderness",
            ZoneKind::Dungeon    => b"Dungeon",
            ZoneKind::Rest       => b"Safe Rest",
            ZoneKind::Threshold  => b"Threshold",
            ZoneKind::Chamber    => b"Chamber",
            ZoneKind::BossArena  => b"Boss Arena",
        }}).unwrap_or(b"");
        it.tt_right(w as i32 - 16, y0 as i32 + 22,
            core::str::from_utf8(ktag).unwrap_or(""), 11.0, t.text_dim);

        it.fill(0, y0 + 24, w, 1, t.rule);

        let desc: &[u8] = zdef.map(|z| z.desc).unwrap_or(b"");
        let mut dy = y0 + 28;
        word_wrap(gpu, &it, desc, 20, &mut dy, w.saturating_sub(40), t.text_dim, 3);

        it.fill(0, dy + 6, w, 1, t.rule);
        let menu_y = dy + 10;

        let vis = ((h.saturating_sub(menu_y + 30)) / 14) as usize;
        let scroll = if self.cursor >= vis.max(1) { self.cursor + 1 - vis.max(1) } else { 0 };
        for vi in 0..vis.min(self.item_n.saturating_sub(scroll)) {
            let si  = scroll + vi;
            let vy  = menu_y + vi as u32 * 16;
            let sel = si == self.cursor;
            let col = if sel { t.accent } else { t.text };
            if sel {
                it.fill_rounded(6, vy.saturating_sub(1), w - 12, 17, 3, t.selection);
                it.tt(10, vy as i32, ">", 13.0, t.accent);
            }
            let lbl = &self.items[si].label[..self.items[si].label_n];
            it.tt(24, vy as i32, core::str::from_utf8(lbl).unwrap_or("?"), 13.0, col);
        }

        if self.msg_n > 0 {
            let ms = core::str::from_utf8(&self.msg[..self.msg_n]).unwrap_or("");
            it.tt(20, h as i32 - 26, ms, 11.0, t.accent);
        }
        it.fill(0, h.saturating_sub(16), w, 16, t.surface);
        it.tt(8, h as i32 - 13, "Up/Down=select  Enter=act  Esc=menu", 11.0, t.text_dim);
    }

    fn render_pause(&self, gpu: &dyn GpuSurface) {
        let it = It::new(gpu);
        let t  = style::get();
        let w  = gpu.width();
        let h  = gpu.height();

        // Dim overlay — a centered panel.
        let pw: u32 = 260;
        let ph: u32 = 80;
        let px = (w.saturating_sub(pw)) / 2;
        let py = (h.saturating_sub(ph)) / 2;
        it.fill(px, py, pw, ph, t.surface);
        it.fill(px, py, pw, 1, t.rule);
        it.fill(px, py + ph.saturating_sub(1), pw, 1, t.rule);

        it.text(px + 12, py + 10, "PAUSED", 1, t.header);

        let opts: &[&str] = &["Continue", "Return to Atelier"];
        for (i, &label) in opts.iter().enumerate() {
            let oy  = py + 28 + i as u32 * 16;
            let col = if i == self.pause_cursor { t.accent } else { t.text };
            if i == self.pause_cursor { it.text(px + 8, oy, ">", 1, t.accent); }
            it.text(px + 20, oy, label, 1, col);
        }
        it.text(px + 12, py + ph.saturating_sub(14), "Enter=select  Esc=cancel", 1, t.text_dim);
    }

    fn render_dream(&self, gpu: &dyn GpuSurface) {
        let it = It::new(gpu);
        let t  = style::get();
        let w  = gpu.width();
        let h  = gpu.height();

        it.fill(0, 0, w, h, (4, 2, 8));

        // Ko marker, centered upper quarter.
        let kx = w.saturating_sub(24) / 2;
        it.text(kx, h / 5, "Ko", 2, t.accent);

        // Ko's words, word-wrapped in the center band.
        let mut dy = h / 3;
        let margin = w / 5;
        word_wrap(
            gpu, &it,
            &self.dream_text[..self.dream_text_n],
            margin, &mut dy,
            w.saturating_sub(margin * 2),
            t.text_dim, 8,
        );

        it.fill(0, h.saturating_sub(14), w, 14, (8, 4, 16));
        it.text(8, h.saturating_sub(12), "Enter=wake", 1, t.text_dim);
    }

    fn render_walk(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let sw  = gpu.width();
        let sh  = gpu.height();
        let y0  = self.rule_y + 4;
        it.fill(0, y0, sw, sh.saturating_sub(y0), t.bg);

        let cell: u32 = 8;
        let mw   = DUN_W as u32 * cell;
        let mh   = DUN_H as u32 * cell;
        let ox   = (sw.saturating_sub(mw)) / 2;
        let oy   = y0 + 4;

        for row in 0..DUN_H {
            for cx in 0..DUN_W {
                let ch = self.walk_map[row][cx];
                let px = ox + cx as u32 * cell;
                let py = oy + row as u32 * cell;
                let is_player = cx == self.walk_x && row == self.walk_y;
                let color: (u8, u8, u8) = if is_player { t.accent }
                            else { cell_color(ch, &t) };
                let glyph = if is_player { "@" } else { cell_glyph(ch) };
                if !glyph.is_empty() {
                    it.text(px, py, glyph, 1, color);
                }
            }
        }

        if self.msg_n > 0 {
            let ms = core::str::from_utf8(&self.msg[..self.msg_n]).unwrap_or("");
            it.text(20, sh.saturating_sub(24), ms, 1, t.accent);
        }
        it.fill(0, sh.saturating_sub(14), sw, 14, t.surface);
        it.text(8, sh.saturating_sub(12), "Arrows/WASD=move  Esc=flee", 1, t.text_dim);
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn cell_glyph(ch: u8) -> &'static str {
    match ch {
        b'#' => "#", b'.' => ".", b'+' => "+",
        b'S' => "S", b'E' => "E", b'@' => "@", _ => "",
    }
}

fn cell_color(ch: u8, t: &style::Theme) -> (u8, u8, u8) {
    match ch {
        b'#' => (60u8, 60u8, 80u8),
        b'.' => (30u8, 30u8, 40u8),
        b'+' => t.text_dim,
        b'S' => t.accent,
        b'E' => t.header,
        b'@' => (220u8, 60u8, 60u8),
        _    => (0u8, 0u8, 0u8),
    }
}

// Simple word-wrap: splits `text` on spaces, renders up to `max_ln` lines of
// `px_w / 8` characters, advancing `*y` by 12 per line.
fn word_wrap(
    _gpu: &dyn GpuSurface,
    it:   &It,
    text: &[u8],
    x:    u32,
    y:    &mut u32,
    px_w: u32,
    col:  (u8, u8, u8),
    max_ln: usize,
) {
    let cpl = ((px_w / 8) as usize).max(10);
    let mut buf  = [0u8; 128];
    let mut bn   = 0usize;
    let mut drawn = 0usize;
    let mut i    = 0usize;

    while drawn < max_ln {
        // Scan to next word boundary.
        if i >= text.len() {
            if bn > 0 {
                it.text(x, *y, core::str::from_utf8(&buf[..bn]).unwrap_or(""), 1, col);
                drawn += 1;
            }
            break;
        }
        let ws = i;
        while i < text.len() && text[i] != b' ' && text[i] != b'\n' { i += 1; }
        let wlen = i - ws;
        while i < text.len() && (text[i] == b' ' || text[i] == b'\n') { i += 1; }

        let need = if bn == 0 { wlen } else { 1 + wlen };
        if bn + need > cpl && bn > 0 {
            it.text(x, *y, core::str::from_utf8(&buf[..bn]).unwrap_or(""), 1, col);
            *y += 12;
            drawn += 1;
            bn = 0;
        }
        if bn > 0 && bn < 127 { buf[bn] = b' '; bn += 1; }
        let copy = wlen.min(127 - bn);
        if copy > 0 {
            buf[bn..bn+copy].copy_from_slice(&text[ws..ws+copy]);
            bn += copy;
        }
    }
}

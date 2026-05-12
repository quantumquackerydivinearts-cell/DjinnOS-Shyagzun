// combat.rs — Turn-based combat system for Ko's Labyrinth (7_KLGS).
//
// VITRIOL stats modify attack/defence rolls.
// Skills (melee_weapons, guns, sneak, etc.) determine action availability.
// Sanity axes shift under combat conditions — Terrestrial most directly.
//
// Each encounter: one player vs one enemy (expandable to groups later).
// Action sequence: player picks action → enemy acts → resolve → loop.

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;

// ── Enemy definition ──────────────────────────────────────────────────────────

#[derive(Copy, Clone)]
pub struct EnemyDef {
    pub id:       u16,
    pub name:     &'static [u8],
    pub hp:       u8,
    pub attack:   u8,   // base damage
    pub defence:  u8,   // damage reduction
    pub vitriol:  u8,   // primary VITRIOL contribution on defeat
    pub reward_item:  u16,
    pub reward_count: u16,
    pub reward_coin:  u16,
}

pub const ENEMY_NONE:    u16 = 0;
pub const ENEMY_BANDIT:  u16 = 1;
pub const ENEMY_GUARD:   u16 = 2;
pub const ENEMY_SHADE:   u16 = 3;  // Sulphera entity
pub const ENEMY_ALFIRIN: u16 = 4;  // tutorial foe gated by Alfir quest

pub const ENEMY_DEFS: &[EnemyDef] = &[
    EnemyDef { id: ENEMY_BANDIT,  name: b"Bandit",       hp: 30, attack: 6, defence: 2,
               vitriol: 0 /*V*/, reward_item: 0, reward_count: 0, reward_coin: 12 },
    EnemyDef { id: ENEMY_GUARD,   name: b"Castle Guard",  hp: 50, attack: 9, defence: 5,
               vitriol: 2 /*T*/, reward_item: 0, reward_count: 0, reward_coin: 0 },
    EnemyDef { id: ENEMY_SHADE,   name: b"Shade",         hp: 40, attack: 12, defence: 1,
               vitriol: 3 /*R*/, reward_item: crate::alchemy::ITEM_INFERNAL_SALVE, reward_count: 1, reward_coin: 0 },
    EnemyDef { id: ENEMY_ALFIRIN, name: b"Alfirin",       hp: 20, attack: 4, defence: 1,
               vitriol: 1 /*I*/, reward_item: 0, reward_count: 0, reward_coin: 5 },
];

fn get_def(id: u16) -> Option<&'static EnemyDef> {
    ENEMY_DEFS.iter().find(|d| d.id == id)
}

// ── Action ────────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum Action {
    Attack,   // melee_weapons or unarmed skill
    Shoot,    // guns skill (requires ammo)
    Sneak,    // sneak skill — escape or backstab bonus
    UseItem,  // use top healing item from inventory
    Flee,     // flee attempt (survival skill)
}

// ── Combat state ──────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum CombatResult { Ongoing, PlayerWon, PlayerFled, PlayerDied }

pub struct Combat {
    pub enemy_id:      u16,
    pub enemy_hp:      u8,
    pub enemy_hp_max:  u8,
    pub player_hp:     u8,
    pub player_hp_max: u8,
    pub turn:          u32,
    pub result:        CombatResult,
    pub log:           [[u8; 60]; 6],
    pub log_n:         [u8; 6],
    pub log_count:     usize,
    pub cursor:        usize,  // selected action
    pub exited:        bool,
    rule_y:            u32,
    rng_state:         u32,
}

const ACTIONS: &[(&[u8], Action)] = &[
    (b"Attack",   Action::Attack),
    (b"Shoot",    Action::Shoot),
    (b"Sneak",    Action::Sneak),
    (b"Use Item", Action::UseItem),
    (b"Flee",     Action::Flee),
];

static mut COMBAT: Combat = Combat {
    enemy_id:      0,
    enemy_hp:      0,
    enemy_hp_max:  0,
    player_hp:     30,
    player_hp_max: 30,
    turn:          0,
    result:        CombatResult::Ongoing,
    log:           [[0u8; 60]; 6],
    log_n:         [0u8; 6],
    log_count:     0,
    cursor:        0,
    exited:        false,
    rule_y:        0,
    rng_state:     0xDEAD_BEEF,
};

pub fn combat() -> &'static mut Combat { unsafe { &mut COMBAT } }

static mut COMBAT_REQ: bool = false;
pub fn request_encounter(enemy_id: u16, rule_y: u32) {
    let c = unsafe { &mut COMBAT };
    c.enemy_id = enemy_id;
    c.rule_y   = rule_y;
    if let Some(def) = get_def(enemy_id) {
        c.enemy_hp      = def.hp;
        c.enemy_hp_max  = def.hp;
    }
    let ps = crate::player_state::get();
    // Player HP = 20 base + V(Vitality) * 3 + melee/unarmed skill rank / 10.
    // VITRIOL 1-10: vitality 1→+3, 5→+15, 10→+30.
    let vitality = ps.vitriol[0] as u16;
    let melee    = ps.skills[crate::skills::SKILL_MELEE_IDX] as u16;
    let unarmed  = ps.skills[13] as u16;
    c.player_hp_max = (20 + vitality * 3 + (melee + unarmed) / 10).min(255) as u8;
    c.player_hp  = c.player_hp_max;
    c.turn       = 0;
    c.result     = CombatResult::Ongoing;
    c.log_count  = 0;
    c.cursor     = 0;
    c.exited     = false;
    unsafe { COMBAT_REQ = true; }
}
pub fn consume_request() -> bool { unsafe { let r = COMBAT_REQ; COMBAT_REQ = false; r } }

// ── Combat impl ───────────────────────────────────────────────────────────────

impl Combat {
    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
        if self.result != CombatResult::Ongoing {
            match key { Key::Enter | Key::Escape => { self.exited = true; } _ => {} }
            return;
        }
        match key {
            Key::Up    => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Down  => { if self.cursor + 1 < ACTIONS.len() { self.cursor += 1; } }
            Key::Enter | Key::Char(b' ') => {
                let action = ACTIONS[self.cursor].1;
                self.resolve_turn(action);
            }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
    }

    fn resolve_turn(&mut self, action: Action) {
        self.turn += 1;
        let ps = crate::player_state::get_mut();

        // ── Player action ─────────────────────────────────────────────────────
        match action {
            Action::Attack => {
                let melee  = ps.skills[crate::skills::SKILL_MELEE_IDX] as u32;
                let unarmed= ps.skills[13] as u32;
                // Damage scaled by V (Vitality) vitriol_scale.
                // VITRIOL 5 = no change; VITRIOL 10 = +50% damage.
                let v_scale = crate::skills::vitriol_scale(crate::skills::SKILL_MELEE_IDX);
                let roll = self.rand8() as u32 % 8 + 1;
                let base = roll + melee / 20 + unarmed / 20;
                let dmg  = (base * v_scale / 100).min(255) as u8;
                let def  = get_def(self.enemy_id).map_or(2, |d| d.defence);
                let taken = dmg.saturating_sub(def);
                self.enemy_hp = self.enemy_hp.saturating_sub(taken);
                let mut buf = [0u8; 60];
                let n = fmt_msg(&mut buf, b"You hit for ", taken, b" damage");
                self.push_log(&buf[..n]);
            }
            Action::Shoot => {
                let guns = ps.skills[crate::skills::SKILL_GUNS_IDX] as u32;
                // Guns scaled by T (Tactility) -- physical precision.
                let t_scale = crate::skills::vitriol_scale(crate::skills::SKILL_GUNS_IDX);
                let roll = self.rand8() as u32 % 10 + 1;
                let dmg  = ((roll + guns / 15) * t_scale / 100).min(255) as u8;
                let def  = get_def(self.enemy_id).map_or(2, |d| d.defence);
                let taken = dmg.saturating_sub(def / 2); // guns bypass some armour
                self.enemy_hp = self.enemy_hp.saturating_sub(taken);
                let mut buf = [0u8; 60];
                let n = fmt_msg(&mut buf, b"Shot for ", taken, b" damage");
                self.push_log(&buf[..n]);
            }
            Action::Sneak => {
                let sneak = ps.skills[crate::skills::SKILL_SNEAK_IDX] as u32;
                let roll  = self.rand8() as u32;
                if roll < sneak / 2 + 20 {
                    // Backstab: 1.5x damage
                    let dmg = (self.rand8() as u32 % 12 + 1 + sneak / 10).min(255) as u8;
                    self.enemy_hp = self.enemy_hp.saturating_sub(dmg);
                    let mut buf = [0u8; 60];
                    let n = fmt_msg(&mut buf, b"Backstab! ", dmg, b" damage");
                    self.push_log(&buf[..n]);
                } else {
                    self.push_log(b"Sneak failed -- enemy noticed you");
                }
            }
            Action::UseItem => {
                // Use first healing item in inventory.
                if crate::player_state::inv_remove(crate::alchemy::ITEM_HEALTH_POTION, 1) {
                    let heal = 20u8;
                    self.player_hp = self.player_hp.saturating_add(heal).min(self.player_hp_max);
                    let mut buf = [0u8; 60];
                    let n = fmt_msg(&mut buf, b"Drank health potion: +", heal, b" HP");
                    self.push_log(&buf[..n]);
                } else {
                    self.push_log(b"No healing items");
                    return; // no enemy turn
                }
            }
            Action::Flee => {
                let surv = ps.skills[crate::skills::SKILL_SURVIVAL_IDX] as u32;
                // Flee chance boosted by Survival's dual VITRIOL (L+T average).
                let ls_mod = crate::skills::vitriol_mod(crate::skills::SKILL_SURVIVAL_IDX) as u32;
                let roll = self.rand8() as u32;
                if roll < surv / 2 + 30 + ls_mod * 2 {
                    self.result = CombatResult::PlayerFled;
                    self.push_log(b"You escaped!");
                    crate::dungeon::dungeon().record_exit(crate::dungeon::LastExit::Fled);
                    return;
                } else {
                    self.push_log(b"Couldn't escape!");
                }
            }
        }

        // Check win.
        if self.enemy_hp == 0 {
            self.result = CombatResult::PlayerWon;
            self.on_victory();
            return;
        }

        // ── Enemy action ──────────────────────────────────────────────────────
        let def    = get_def(self.enemy_id);
        let e_atk  = def.map_or(5, |d| d.attack);
        let p_def  = ps.vitriol[2] as u32 / 2; // T = Tactility → defence (1→0, 5→2, 10→5)
        let e_roll = self.rand8() as u32 % e_atk as u32 + 1;
        let e_dmg  = (e_roll).saturating_sub(p_def) as u8;
        self.player_hp = self.player_hp.saturating_sub(e_dmg);

        let mut buf = [0u8; 60];
        let n = fmt_msg(&mut buf, b"Enemy hits you for ", e_dmg, b" damage");
        self.push_log(&buf[..n]);

        // Terrestrial sanity shifts under combat.
        ps.sanity[2] = ps.sanity[2].saturating_sub(1);

        if self.player_hp == 0 {
            self.result = CombatResult::PlayerDied;
            self.push_log(b"You have been defeated.");
            crate::dungeon::dungeon().record_exit(crate::dungeon::LastExit::Died);
        }
    }

    fn on_victory(&mut self) {
        if let Some(def) = get_def(self.enemy_id) {
            let mut buf = [0u8; 60];
            let n = fmt_msg(&mut buf, b"Defeated! Coin +", def.reward_coin as u8, b"");
            self.push_log(&buf[..n]);
            // Reward coin.
            let shop = crate::shop::shop();
            shop.coin = shop.coin.saturating_add(def.reward_coin as u32);
            // Reward item.
            if def.reward_item != 0 {
                crate::player_state::inv_add(def.reward_item, def.reward_count);
            }
            // VITRIOL boost.
            let ps = crate::player_state::get_mut();
            ps.vitriol[def.vitriol as usize] =
                ps.vitriol[def.vitriol as usize].saturating_add(2).min(100);
            // Add journal entry.
            let ps_coin = shop.coin;
            let _ = ps_coin;
            crate::journal::add_combat(def.name, self.turn);
        }
        crate::eigenstate::advance(crate::eigenstate::T_LOTUS);
    }

    fn push_log(&mut self, msg: &[u8]) {
        let idx = self.log_count % 6;
        let n   = msg.len().min(60);
        self.log[idx][..n].copy_from_slice(&msg[..n]);
        self.log_n[idx] = n as u8;
        self.log_count += 1;
    }

    fn rand8(&mut self) -> u8 {
        // xorshift32
        self.rng_state ^= self.rng_state << 13;
        self.rng_state ^= self.rng_state >> 17;
        self.rng_state ^= self.rng_state << 5;
        (self.rng_state & 0xFF) as u8
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let top = self.rule_y + 8;
        it.fill(0, top, gpu.width(), gpu.height().saturating_sub(top), t.bg);

        let def = get_def(self.enemy_id);
        let ename = def.map(|d| core::str::from_utf8(d.name).unwrap_or("?")).unwrap_or("?");
        it.text(40, top + 4, ename, 2, (220, 80, 80));

        // Enemy HP bar
        let ehp_w = if self.enemy_hp_max > 0 {
            (self.enemy_hp as u32 * 200) / self.enemy_hp_max as u32
        } else { 0 };
        it.fill(40, top + 32, 200, 10, (60, 20, 20));
        it.fill(40, top + 32, ehp_w, 10, (200, 50, 50));

        // Player HP bar
        it.text(40, top + 50, "You", 2, t.text);
        let php_w = if self.player_hp_max > 0 {
            (self.player_hp as u32 * 200) / self.player_hp_max as u32
        } else { 0 };
        it.fill(40, top + 72, 200, 10, (20, 60, 20));
        it.fill(40, top + 72, php_w, 10, (50, 200, 50));

        // Combat log
        let log_start = if self.log_count >= 6 { self.log_count - 6 } else { 0 };
        for i in 0..self.log_count.min(6) {
            let idx = (log_start + i) % 6;
            let n   = self.log_n[idx] as usize;
            let s   = core::str::from_utf8(&self.log[idx][..n]).unwrap_or("");
            it.text(40, top + 92 + i as u32 * 13, s, 1, t.text_dim);
        }

        // Actions
        if self.result == CombatResult::Ongoing {
            for (i, (label, _)) in ACTIONS.iter().enumerate() {
                let col = if i == self.cursor { t.accent } else { t.text };
                let s = core::str::from_utf8(label).unwrap_or("?");
                it.text(40, top + 172 + i as u32 * 16, s, 1, col);
            }
        } else {
            let msg = match self.result {
                CombatResult::PlayerWon  => "Victory!",
                CombatResult::PlayerFled => "Escaped.",
                CombatResult::PlayerDied => "Defeated.",
                CombatResult::Ongoing    => "",
            };
            it.text(40, top + 172, msg, 2, t.accent);
            it.text(40, top + 196, "[Enter] to continue", 1, t.text_dim);
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn fmt_msg(buf: &mut [u8; 60], prefix: &[u8], val: u8, suffix: &[u8]) -> usize {
    let mut n = 0usize;
    let pn = prefix.len().min(60); buf[..pn].copy_from_slice(&prefix[..pn]); n += pn;
    let mut vb = [0u8; 4]; let vn = write_u8(&mut vb, val);
    buf[n..n+vn].copy_from_slice(&vb[..vn]); n += vn;
    let sn = suffix.len().min(60 - n); buf[n..n+sn].copy_from_slice(&suffix[..sn]); n += sn;
    n
}

fn write_u8(buf: &mut [u8], v: u8) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8;3]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + x % 10; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}

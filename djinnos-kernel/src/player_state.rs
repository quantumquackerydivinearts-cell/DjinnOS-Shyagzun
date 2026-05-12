// player_state.rs — Ko's Labyrinth game player state.
//
// Persisted to Sa volume as "player.dat" (binary, format tag "PS01").
// Single global player state; loaded at boot, saved on significant events.
//
// ── Skill index (matches apps/atelier-desktop/src/skillRegistry.js) ──────────
//   Ranks 1–100.  Currently 19 named skills; slots 19–99 reserved for expansion.
//   0  barter          7  repair         14  meditation
//   1  energy_weapons  8  alchemy        15  magic
//   2  explosives      9  sneak          16  blacksmithing
//   3  guns           10  hack           17  silversmithing
//   4  lockpick       11  speech         18  goldsmithing
//   5  medicine       12  survival
//   6  melee_weapons  13  unarmed
//
// ── Meditation perk bitmask ───────────────────────────────────────────────────
//   bit 0  breathwork          (no quest gate)
//   bit 1  alchemical          (0008_KLST)
//   bit 2  hypnotic            (0007_KLST)
//   bit 3  infernal            (0009_KLST) ← gates Sulphera
//   bit 4  depth               (0011_KLST)
//   bit 5  transcendental      (0016_KLST)
//   bit 6  zen                 (0026_KLST)
//
// ── VITRIOL indices ───────────────────────────────────────────────────────────
//   0=V (Vitality)  1=I (Introspection)  2=T (Tactility)  3=R (Reflectivity)
//   4=I (Ingenuity)  5=O (Ostentation)  6=L (Levity)
//
// ── Sanity indices ────────────────────────────────────────────────────────────
//   0=Alchemical  1=Narrative  2=Terrestrial  3=Cosmic

pub const SKILL_COUNT:  usize = 19;
pub const VITRIOL_LEN:  usize =  7;
pub const SANITY_LEN:   usize =  4;
pub const MAX_QUESTS:   usize = 32;
pub const MAX_INV:      usize = 64;
pub const QUEST_SLUG_N: usize =  9;  // "0001_KLST"
pub const INV_ID_N:     usize = 12;

// -- Perk bitset (160 bits = 5 x u32) -----------------------------------------
// Perks are addressed by numeric ID (0-159).
// Each skill earns one perk slot per 20 ranks (max 5 per skill, 95 total).
// Perk IDs 0-6: Meditation tree (preserved from prior system).
// Full ID map lives in skills::ALL_PERKS.
pub const PERK_WORDS: usize = 5;  // 5 x 32 = 160 bits

// Meditation perk IDs (perk IDs, not bitmasks).
pub const PERK_BREATHWORK:     u8 =  0;
pub const PERK_ALCHEMICAL:     u8 =  1;
pub const PERK_HYPNOTIC:       u8 =  2;
pub const PERK_INFERNAL:       u8 =  3;  // gates Sulphera
pub const PERK_DEPTH:          u8 =  4;
pub const PERK_TRANSCENDENTAL: u8 =  5;
pub const PERK_ZEN:            u8 =  6;

// Quest state.
pub const QUEST_OFFERED:     u8 = 0;
pub const QUEST_IN_PROGRESS: u8 = 1;
pub const QUEST_COMPLETE:    u8 = 2;

// KoFlag count (bitset of 256 named narrative gates).
const KOFLAG_WORDS: usize = 8;  // 8 × u32 = 256 flags

#[derive(Copy, Clone)]
pub struct QuestEntry {
    pub slug:  [u8; QUEST_SLUG_N],
    pub state: u8,
}

impl QuestEntry {
    const EMPTY: Self = Self { slug: [0u8; QUEST_SLUG_N], state: 0 };
    pub fn is_empty(&self) -> bool { self.slug[0] == 0 }
}

#[derive(Copy, Clone)]
pub struct InvSlot {
    pub item_id: u16,    // numeric item ID (desktop maps to named entry)
    pub count:   u16,
}

impl InvSlot {
    const EMPTY: Self = Self { item_id: 0, count: 0 };
    pub fn is_empty(&self) -> bool { self.item_id == 0 }
}

pub struct PlayerState {
    /// Skill ranks (0 = untrained, 1-100).
    pub skills:          [u8; SKILL_COUNT],
    /// Perk bitset: 160 bits (5 x u32). Bit N = perk ID N is taken.
    pub perks:           [u32; PERK_WORDS],
    /// Perk slots used per skill (max 5 each = rank/20 earned).
    pub perk_slots_used: [u8; SKILL_COUNT],
    /// VITRIOL stats (1-10 each, neutral = 5).
    pub vitriol:         [u8; VITRIOL_LEN],
    /// Sanity levels (0-255 = 0.0-1.0 mapped, 128 = neutral).
    pub sanity:       [u8; SANITY_LEN],
    /// Narrative gate flags (256 bits).
    pub ko_flags:     [u32; KOFLAG_WORDS],
    /// Quack count (incremented on canon QQVA interactions).
    pub quack_count:  u32,
    /// Current zone identifier (e.g. b"wiltoll\0\0\0\0\0\0\0\0\0").
    pub zone_id:      [u8; 16],
    /// World position within current zone (voxel cell units).
    pub pos_wx:       i16,
    pub pos_wz:       i16,
    /// Active quest log.
    pub quests:       [QuestEntry; MAX_QUESTS],
    pub quest_count:  u8,
    /// Inventory.
    pub inventory:    [InvSlot; MAX_INV],
    pub inv_count:    u8,
}

impl PlayerState {
    const fn new() -> Self {
        Self {
            skills:          [0u8; SKILL_COUNT],
            perks:           [0u32; PERK_WORDS],
            perk_slots_used: [0u8; SKILL_COUNT],
            vitriol:         [5u8; VITRIOL_LEN],
            sanity:      [128u8; SANITY_LEN],    // start neutral
            ko_flags:    [0u32; KOFLAG_WORDS],
            quack_count: 0,
            zone_id:     *b"wiltoll\0\0\0\0\0\0\0\0\0",
            pos_wx:      4,
            pos_wz:      4,
            quests:      [QuestEntry::EMPTY; MAX_QUESTS],
            quest_count: 0,
            inventory:   [InvSlot::EMPTY; MAX_INV],
            inv_count:   0,
        }
    }
}

static mut STATE: PlayerState = PlayerState::new();

pub fn get() -> &'static PlayerState        { unsafe { &STATE } }
pub fn get_mut() -> &'static mut PlayerState { unsafe { &mut STATE } }

// ── KoFlag helpers ────────────────────────────────────────────────────────────

pub fn ko_set(flag: u8) {
    let ps = get_mut();
    ps.ko_flags[(flag >> 5) as usize] |= 1 << (flag & 31);
}

pub fn ko_clear(flag: u8) {
    let ps = get_mut();
    ps.ko_flags[(flag >> 5) as usize] &= !(1 << (flag & 31));
}

pub fn ko_test(flag: u8) -> bool {
    let ps = get();
    (ps.ko_flags[(flag >> 5) as usize] >> (flag & 31)) & 1 == 1
}

// ── Perk bitset helpers ───────────────────────────────────────────────────────

/// Test whether perk `id` (0-159) is taken.
pub fn has_perk(id: u8) -> bool {
    let w = (id / 32) as usize;
    if w >= PERK_WORDS { return false; }
    (get().perks[w] >> (id & 31)) & 1 == 1
}

/// Set perk `id` in the bitset.
pub fn grant_perk(id: u8) {
    let w = (id / 32) as usize;
    if w < PERK_WORDS { get_mut().perks[w] |= 1 << (id & 31); }
}

/// Clear perk `id` (used only by the Nothing perk slot erasure).
pub fn clear_perk(id: u8) {
    let w = (id / 32) as usize;
    if w < PERK_WORDS { get_mut().perks[w] &= !(1 << (id & 31)); }
}

pub fn has_sulphera_access() -> bool { has_perk(PERK_INFERNAL) }

/// Slots available for a skill: earned (rank/20) minus already used.
pub fn perk_slots_available(skill_idx: usize) -> u8 {
    if skill_idx >= SKILL_COUNT { return 0; }
    let ps      = get();
    let earned  = ps.skills[skill_idx] / 20;
    let used    = ps.perk_slots_used[skill_idx];
    earned.saturating_sub(used)
}

/// Spend one perk slot for a skill.
pub fn spend_perk_slot(skill_idx: usize) {
    if skill_idx < SKILL_COUNT {
        get_mut().perk_slots_used[skill_idx] =
            get().perk_slots_used[skill_idx].saturating_add(1).min(5);
    }
}

// ── Quest helpers ─────────────────────────────────────────────────────────────

pub fn quest_state(slug: &[u8]) -> Option<u8> {
    let ps = get();
    for i in 0..ps.quest_count as usize {
        if ps.quests[i].slug.starts_with(slug) { return Some(ps.quests[i].state); }
    }
    None
}

pub fn quest_set(slug: &[u8], state: u8) {
    let ps = get_mut();
    // Update existing entry.
    for i in 0..ps.quest_count as usize {
        if ps.quests[i].slug.starts_with(slug) {
            ps.quests[i].state = state;
            return;
        }
    }
    // Insert new entry.
    if ps.quest_count as usize >= MAX_QUESTS { return; }
    let idx = ps.quest_count as usize;
    let n   = slug.len().min(QUEST_SLUG_N);
    ps.quests[idx].slug[..n].copy_from_slice(&slug[..n]);
    ps.quests[idx].state = state;
    ps.quest_count += 1;
}

// ── Skill helpers ─────────────────────────────────────────────────────────────

pub fn skill_rank(idx: usize) -> u8 {
    if idx < SKILL_COUNT { get().skills[idx] } else { 0 }
}

pub fn skill_train(idx: usize, rank: u8) {
    if idx < SKILL_COUNT { get_mut().skills[idx] = rank.min(100); }
}

/// Clamp a raw VITRIOL value to the canonical 1–10 range.
pub fn vitriol_clamp(v: u8) -> u8 { v.max(1).min(10) }

// Meditation is skill index 14.
pub const SKILL_MEDITATION: usize = 14;

pub fn meditation_trained() -> bool { skill_rank(SKILL_MEDITATION) > 0 }

// ── Inventory helpers ─────────────────────────────────────────────────────────

pub fn inv_add(item_id: u16, count: u16) -> bool {
    let ps = get_mut();
    // Stack into existing slot.
    for i in 0..ps.inv_count as usize {
        if ps.inventory[i].item_id == item_id {
            ps.inventory[i].count =
                ps.inventory[i].count.saturating_add(count);
            return true;
        }
    }
    // New slot.
    if ps.inv_count as usize >= MAX_INV { return false; }
    let idx = ps.inv_count as usize;
    ps.inventory[idx] = InvSlot { item_id, count };
    ps.inv_count += 1;
    true
}

pub fn inv_remove(item_id: u16, count: u16) -> bool {
    let ps = get_mut();
    for i in 0..ps.inv_count as usize {
        if ps.inventory[i].item_id == item_id {
            if ps.inventory[i].count < count { return false; }
            ps.inventory[i].count -= count;
            if ps.inventory[i].count == 0 {
                // Pack array: shift remaining entries left.
                let total = ps.inv_count as usize;
                for j in i..total - 1 { ps.inventory[j] = ps.inventory[j + 1]; }
                ps.inventory[total - 1] = InvSlot::EMPTY;
                ps.inv_count -= 1;
            }
            return true;
        }
    }
    false
}

// ── Persist / Load ────────────────────────────────────────────────────────────
//
// Binary format "PS02" (version 2 -- perks expanded to 160-bit bitset):
//   [0..4]   magic "PS02"
//   [4]      version = 2
//   [5..24]  skills[19]
//   [24..44] perks[5 x u32 LE] = 20 bytes
//   [44..63] perk_slots_used[19]
//   [63..70] vitriol[7]
//   [70..74] sanity[4]
//   [74..106] ko_flags[8 x u32 LE]
//   [106..110] quack_count u32 LE
//   [110..126] zone_id[16]
//   [126..128] pos_wx i16 LE
//   [128..130] pos_wz i16 LE
//   [130]    quest_count
//   quests padded to MAX_QUESTS x 10
//   inv_count + inventory x 4

const MAGIC: &[u8; 4] = b"PS02";
const MAX_BYTES: usize = 4 + 1 + 19 + 20 + 19 + 7 + 4 + 32 + 4 + 16 + 4
                       + 1 + MAX_QUESTS * 10
                       + 1 + MAX_INV * 4;

static mut SAVE_BUF: [u8; MAX_BYTES] = [0u8; MAX_BYTES];

pub fn save() {
    let ps  = get();
    let buf = unsafe { &mut SAVE_BUF };
    let mut off = 0usize;

    macro_rules! wb   { ($b:expr) => { buf[off] = $b; off += 1; } }
    macro_rules! wu16 { ($v:expr) => {
        let v = $v as u16;
        buf[off] = (v & 0xff) as u8; buf[off+1] = (v >> 8) as u8; off += 2;
    } }
    macro_rules! wu32 { ($v:expr) => {
        let v = $v as u32;
        buf[off]   = (v        & 0xff) as u8; buf[off+1] = ((v >>  8) & 0xff) as u8;
        buf[off+2] = ((v >> 16) & 0xff) as u8; buf[off+3] = ((v >> 24) & 0xff) as u8;
        off += 4;
    } }

    buf[0]=MAGIC[0]; buf[1]=MAGIC[1]; buf[2]=MAGIC[2]; buf[3]=MAGIC[3]; off=4;
    wb!(2u8);   // version 2
    for s in &ps.skills           { wb!(*s); }
    for w in &ps.perks            { wu32!(*w); }
    for s in &ps.perk_slots_used  { wb!(*s); }
    for v in &ps.vitriol          { wb!(*v); }
    for s in &ps.sanity           { wb!(*s); }
    for f in &ps.ko_flags         { wu32!(*f); }
    wu32!(ps.quack_count);
    for b in &ps.zone_id          { wb!(*b); }
    wu16!(ps.pos_wx as u16);
    wu16!(ps.pos_wz as u16);
    wb!(ps.quest_count);
    for i in 0..ps.quest_count as usize {
        for b in &ps.quests[i].slug { wb!(*b); }
        wb!(ps.quests[i].state);
    }
    for _ in ps.quest_count as usize..MAX_QUESTS {
        for _ in 0..QUEST_SLUG_N { wb!(0); }
        wb!(0);
    }
    wb!(ps.inv_count);
    for i in 0..ps.inv_count as usize {
        wu16!(ps.inventory[i].item_id);
        wu16!(ps.inventory[i].count);
    }
    crate::sa::write_file(b"player.dat", &buf[..off]);
}

pub fn load() {
    let mut buf = [0u8; MAX_BYTES];
    let n = crate::sa::read_file(b"player.dat", &mut buf);
    if n < 5 { return; }
    if &buf[0..4] != MAGIC { return; }
    if buf[4] != 2 { return; }   // only version 2

    let ps  = get_mut();
    let mut off = 5usize;

    macro_rules! rb   { () => {{ let b = buf[off]; off += 1; b }} }
    macro_rules! ru16 { () => {{
        let lo = buf[off] as u16; let hi = buf[off+1] as u16; off += 2; lo | (hi<<8)
    }} }
    macro_rules! ru32 { () => {{
        let a=buf[off] as u32; let b=buf[off+1] as u32;
        let c=buf[off+2] as u32; let d=buf[off+3] as u32;
        off += 4; a|(b<<8)|(c<<16)|(d<<24)
    }} }

    for s in &mut ps.skills           { *s = rb!(); }
    for w in &mut ps.perks            { *w = ru32!(); }
    for s in &mut ps.perk_slots_used  { *s = rb!(); }
    for v in &mut ps.vitriol          { *v = rb!(); }
    for s in &mut ps.sanity           { *s = rb!(); }
    for f in &mut ps.ko_flags         { *f = ru32!(); }
    ps.quack_count = ru32!();
    for b in &mut ps.zone_id          { *b = rb!(); }
    ps.pos_wx = ru16!() as i16;
    ps.pos_wz = ru16!() as i16;
    ps.quest_count = rb!();
    for i in 0..MAX_QUESTS {
        for b in &mut ps.quests[i].slug { *b = rb!(); }
        ps.quests[i].state = rb!();
    }
    ps.inv_count = rb!();
    for i in 0..ps.inv_count as usize {
        ps.inventory[i].item_id = ru16!();
        ps.inventory[i].count   = ru16!();
    }
}

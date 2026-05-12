// alchemy.rs -- Apparatus-driven alchemy for Ko's Labyrinth (7_KLGS).
//
// Source of truth: kos_labyrnth.py SS11.2 Object Registry and SS11.3 Object Traits.
// Object IDs map to _OBJECT_TABLE (0001_KLOB through 0077_KLOB).
// Item IDs map to _ITEM_TABLE (0001_KLIT through 0040_KLIT).
//
// Alchemy is SPATIAL, not grid-based:
//   The player assembles apparatus on the workbench (world objects).
//   Loading an ingredient into an apparatus and operating it produces a result.
//   Proximity to apparatus is required -- this is embodied work.
//
// Object traits (bitmask -- OBJECT_TRAITS in kos_labyrnth.py):
//   0=Usable  1=Unusable  2=Full     3=Empty    4=Alive     5=Dead
//   6=Movable 7=Immobilized 8=Poisonous 9=Flammable 10=Inert
//   11=Explosive 12=Token 13=Collector 14=Powdered 15=Molten

// -- Object ID constants (numeric part of _KLOB entity IDs) -------------------

pub const OBJ_MORTAR:         u16 = 0x0001;  // 0001_KLOB -- grinder apparatus
pub const OBJ_PESTLE:         u16 = 0x0002;  // 0002_KLOB -- mortar companion
pub const OBJ_RETORT:         u16 = 0x0005;  // 0005_KLOB -- distillation vessel
pub const OBJ_VOLUME_FLASK:   u16 = 0x0006;  // 0006_KLOB -- measuring vessel
pub const OBJ_REAGENT_BOTTLE: u16 = 0x0007;  // 0007_KLOB -- storage
pub const OBJ_FURNACE:        u16 = 0x000A;  // 0010_KLOB -- heat source (Immobilized)
pub const OBJ_CRUCIBLE:       u16 = 0x0011;  // 0017_KLOB -- holds molten material
pub const OBJ_BOTTLE:         u16 = 0x0012;  // 0018_KLOB
pub const OBJ_JAR:            u16 = 0x0013;  // 0019_KLOB
pub const OBJ_SALTPETER:      u16 = 0x0017;  // 0023_KLOB
pub const OBJ_SULPHUR:        u16 = 0x0018;  // 0024_KLOB
pub const OBJ_CHARCOAL:       u16 = 0x0019;  // 0025_KLOB
pub const OBJ_IRON:           u16 = 0x001B;  // 0027_KLOB
pub const OBJ_GOLD:           u16 = 0x001C;  // 0028_KLOB
pub const OBJ_COPPER:         u16 = 0x001D;  // 0029_KLOB
pub const OBJ_MERCURY_OBJ:    u16 = 0x001E;  // 0030_KLOB -- Mercury (the element)
pub const OBJ_SILVER:         u16 = 0x001F;  // 0031_KLOB
pub const OBJ_LEAD:           u16 = 0x0020;  // 0032_KLOB
pub const OBJ_WATER:          u16 = 0x0028;  // 0040_KLOB
pub const OBJ_HERB_COMMON:    u16 = 0x0049;  // 0073_KLOB
pub const OBJ_HERB_RESTORE:   u16 = 0x004A;  // 0074_KLOB
pub const OBJ_RAW_DESIRE:     u16 = 0x004C;  // 0076_KLOB
pub const OBJ_ASMODEAN:       u16 = 0x004D;  // 0077_KLOB
pub const OBJ_RING_MOLD:      u16 = 0x0039;  // 0057_KLOB
pub const OBJ_INGOT_MOLD:     u16 = 0x003A;  // 0058_KLOB
pub const OBJ_CRUCIBLE_TONGS: u16 = 0x0038;  // 0056_KLOB
pub const OBJ_GLYCERINE:      u16 = 0x0015;  // 0021_KLOB
pub const OBJ_DESERT_GLASS:   u16 = 0x0042;  // 0066_KLOB

// -- Item ID constants (numeric part of _KLIT entity IDs) ---------------------

pub const ITEM_BASIC_TINCTURE:    u16 = 0x0022;  // 0034_KLIT
pub const ITEM_RESTORATIVE_TINCT: u16 = 0x0023;  // 0035_KLIT
pub const ITEM_DESIRE_FRAGMENT:   u16 = 0x0024;  // 0036_KLIT
pub const ITEM_INFERNAL_SALVE:    u16 = 0x0025;  // 0037_KLIT
pub const ITEM_ANGELIC_SALVE:     u16 = 0x0026;  // 0038_KLIT
pub const ITEM_RING:              u16 = 0x000E;  // 0014_KLIT (craftable)
pub const ITEM_INGOT:             u16 = 0x000F;  // 0015_KLIT (craftable)
pub const ITEM_COIN_ITEM:         u16 = 0x0010;  // 0016_KLIT (craftable)
pub const ITEM_DAGGER:            u16 = 0x0011;  // 0017_KLIT
pub const ITEM_SWORD:             u16 = 0x0012;  // 0018_KLIT
pub const ITEM_HEALTH_POTION:     u16 = 0x0001;  // 0001_KLIT

// -- Object trait bitmask ------------------------------------------------------

pub const TRAIT_USABLE:      u16 = 1 << 0;
pub const TRAIT_UNUSABLE:    u16 = 1 << 1;
pub const TRAIT_FULL:        u16 = 1 << 2;
pub const TRAIT_EMPTY:       u16 = 1 << 3;
pub const TRAIT_ALIVE:       u16 = 1 << 4;
pub const TRAIT_DEAD:        u16 = 1 << 5;
pub const TRAIT_MOVABLE:     u16 = 1 << 6;
pub const TRAIT_IMMOBILIZED: u16 = 1 << 7;  // furnace, anvil
pub const TRAIT_POISONOUS:   u16 = 1 << 8;
pub const TRAIT_FLAMMABLE:   u16 = 1 << 9;
pub const TRAIT_INERT:       u16 = 1 << 10;
pub const TRAIT_EXPLOSIVE:   u16 = 1 << 11;
pub const TRAIT_TOKEN:       u16 = 1 << 12;
pub const TRAIT_COLLECTOR:   u16 = 1 << 13;  // vessels that hold contents
pub const TRAIT_POWDERED:    u16 = 1 << 14;  // after mortar grinding
pub const TRAIT_MOLTEN:      u16 = 1 << 15;  // after furnace heating

// -- Apparatus type ------------------------------------------------------------

#[derive(Copy, Clone, PartialEq)]
pub enum Apparatus {
    Mortar,    // grinds solids -> Powdered
    Retort,    // distills liquids -> refined output
    Furnace,   // heats metals -> Molten; fires combustible mixtures
    Crucible,  // holds Molten material; used with molds for casting
}

impl Apparatus {
    pub fn name(&self) -> &'static str {
        match self {
            Self::Mortar   => "Mortar",
            Self::Retort   => "Retort",
            Self::Furnace  => "Furnace",
            Self::Crucible => "Crucible",
        }
    }
    pub fn object_id(&self) -> u16 {
        match self {
            Self::Mortar   => OBJ_MORTAR,
            Self::Retort   => OBJ_RETORT,
            Self::Furnace  => OBJ_FURNACE,
            Self::Crucible => OBJ_CRUCIBLE,
        }
    }
}

// -- Workbench slot ------------------------------------------------------------
// An apparatus loaded with up to 3 ingredient objects.

const MAX_LOADED: usize = 3;

#[derive(Copy, Clone)]
pub struct WorkbenchSlot {
    pub apparatus: Apparatus,
    pub loaded:    [u16; MAX_LOADED],   // object IDs loaded into this apparatus
    pub loaded_n:  usize,
    pub traits:    [u16; MAX_LOADED],   // current trait bitmask per ingredient
}

impl WorkbenchSlot {
    const fn empty(apparatus: Apparatus) -> Self {
        Self { apparatus, loaded: [0u16; MAX_LOADED], loaded_n: 0, traits: [0u16; MAX_LOADED] }
    }

    pub fn load(&mut self, obj_id: u16, base_traits: u16) -> bool {
        if self.loaded_n >= MAX_LOADED { return false; }
        self.loaded[self.loaded_n] = obj_id;
        self.traits[self.loaded_n] = base_traits;
        self.loaded_n += 1;
        true
    }

    pub fn clear(&mut self) { self.loaded_n = 0; }
}

// -- Operation resolution -----------------------------------------------------
//
// Result of operating an apparatus with its current ingredient set.

#[derive(Copy, Clone)]
pub struct OpResult {
    pub item_id:    u16,   // output item (KLIT ID), or 0 if no item produced
    pub item_count: u16,
    pub obj_id:     u16,   // output object transformation (KLOB ID), or 0
    pub obj_trait:  u16,   // trait bitmask to apply to obj_id result
    pub msg:        &'static [u8],
}

impl OpResult {
    const NONE: Self = Self {
        item_id: 0, item_count: 0, obj_id: 0, obj_trait: 0, msg: b"no reaction",
    };
}

/// Resolve what an apparatus produces from its current loaded ingredients.
/// `alchemy_rank` is the raw skill rank; R (Reflectivity) VITRIOL scales the
/// effective rank -- high R lets you access advanced recipes at lower raw rank.
/// effective_rank = raw_rank * vitriol_scale(SKILL_ALCHEMY_IDX) / 100
pub fn resolve(slot: &WorkbenchSlot, alchemy_rank: u8) -> OpResult {
    // Apply R (Reflectivity) modifier to effective rank.
    let r_scale   = crate::skills::vitriol_scale(crate::skills::SKILL_ALCHEMY_IDX);
    let alchemy_rank = ((alchemy_rank as u32 * r_scale / 100).min(100)) as u8;
    let objs = &slot.loaded[..slot.loaded_n];
    match slot.apparatus {
        // -- Mortar: grinds solids ---------------------------------------------
        Apparatus::Mortar => {
            // Three classic components -> Black Powder (requires rank 15)
            if contains3(objs, OBJ_SULPHUR, OBJ_SALTPETER, OBJ_CHARCOAL) {
                if alchemy_rank < 15 {
                    return OpResult { msg: b"rank 15 required for black powder", ..OpResult::NONE };
                }
                return OpResult {
                    item_id: ITEM_INFERNAL_SALVE, item_count: 1,
                    obj_id: 0, obj_trait: 0,
                    msg: b"Black Powder: Sulphur+Saltpeter+Charcoal",
                };
            }
            // Common herb -> ground herb (Powdered state, use in Retort)
            if contains1(objs, OBJ_HERB_COMMON) {
                return OpResult {
                    item_id: 0, obj_id: OBJ_HERB_COMMON, obj_trait: TRAIT_POWDERED,
                    item_count: 0, msg: b"Herb (Common) ground to powder",
                };
            }
            // Restorative herb -> ground restorative (use in Retort)
            if contains1(objs, OBJ_HERB_RESTORE) {
                return OpResult {
                    item_id: 0, obj_id: OBJ_HERB_RESTORE, obj_trait: TRAIT_POWDERED,
                    item_count: 0, msg: b"Herb (Restorative) ground to powder",
                };
            }
            // Any metal -> powdered metal (for reactions)
            for &obj in objs {
                if is_metal(obj) {
                    return OpResult {
                        item_id: 0, obj_id: obj, obj_trait: TRAIT_POWDERED,
                        item_count: 0, msg: b"Metal ground to powder",
                    };
                }
            }
            OpResult::NONE
        }

        // -- Retort: distillation ----------------------------------------------
        Apparatus::Retort => {
            if alchemy_rank < 5 {
                return OpResult { msg: b"rank 5 required for retort", ..OpResult::NONE };
            }
            // Ground herb (Common) + Water -> Basic Tincture
            if contains_powdered(objs, OBJ_HERB_COMMON) && contains1(objs, OBJ_WATER) {
                return OpResult {
                    item_id: ITEM_BASIC_TINCTURE, item_count: 1,
                    obj_id: 0, obj_trait: 0,
                    msg: b"Basic Tincture: ground herb distilled in water",
                };
            }
            // Ground herb (Restorative) + Water -> Restorative Tincture
            if contains_powdered(objs, OBJ_HERB_RESTORE) && contains1(objs, OBJ_WATER) {
                if alchemy_rank < 15 {
                    return OpResult { msg: b"rank 15 required for restorative tincture", ..OpResult::NONE };
                }
                return OpResult {
                    item_id: ITEM_RESTORATIVE_TINCT, item_count: 1,
                    obj_id: 0, obj_trait: 0,
                    msg: b"Restorative Tincture: refined herb concentrate",
                };
            }
            // Desert Glass + Glycerine -> Desire Crystal Fragment (Asmodean craft)
            if contains1(objs, OBJ_DESERT_GLASS) && contains1(objs, OBJ_GLYCERINE) {
                if alchemy_rank < 40 {
                    return OpResult { msg: b"rank 40 required for desire synthesis", ..OpResult::NONE };
                }
                return OpResult {
                    item_id: ITEM_DESIRE_FRAGMENT, item_count: 1,
                    obj_id: 0, obj_trait: 0,
                    msg: b"Desire Crystal Fragment: glass memory of longing, refined",
                };
            }
            // Mercury + Herb (any) -> Infernal Salve (requires Infernal perk)
            let has_herb = contains1(objs, OBJ_HERB_COMMON) || contains1(objs, OBJ_HERB_RESTORE);
            if contains1(objs, OBJ_MERCURY_OBJ) && has_herb {
                if !crate::player_state::has_perk(crate::player_state::PERK_INFERNAL) {
                    return OpResult { msg: b"Infernal Meditation perk required", ..OpResult::NONE };
                }
                return OpResult {
                    item_id: ITEM_INFERNAL_SALVE, item_count: 1,
                    obj_id: 0, obj_trait: 0,
                    msg: b"Infernal Salve: mercury-herb reduction, Sulphera-aligned",
                };
            }
            OpResult::NONE
        }

        // -- Furnace: heat source ----------------------------------------------
        Apparatus::Furnace => {
            if alchemy_rank < 10 {
                return OpResult { msg: b"rank 10 required for furnace", ..OpResult::NONE };
            }
            for &obj in objs {
                if is_metal(obj) {
                    return OpResult {
                        item_id: 0, obj_id: obj, obj_trait: TRAIT_MOLTEN, item_count: 0,
                        msg: b"Metal heated to molten state; load into Crucible to cast",
                    };
                }
            }
            OpResult::NONE
        }

        // -- Crucible: casting -------------------------------------------------
        Apparatus::Crucible => {
            if alchemy_rank < 10 {
                return OpResult { msg: b"rank 10 required for casting", ..OpResult::NONE };
            }
            let has_ring_mold  = contains1(objs, OBJ_RING_MOLD);
            let has_ingot_mold = contains1(objs, OBJ_INGOT_MOLD);
            if let Some(&metal) = objs.iter().find(|&&o| is_metal(o)) {
                if has_ring_mold {
                    return OpResult {
                        item_id: metal_ring_type(metal).unwrap_or(ITEM_RING), item_count: 1,
                        obj_id: 0, obj_trait: 0,
                        msg: b"Ring cast from molten metal",
                    };
                }
                if has_ingot_mold {
                    return OpResult {
                        item_id: ITEM_INGOT, item_count: 1,
                        obj_id: 0, obj_trait: 0,
                        msg: b"Ingot cast from molten metal",
                    };
                }
                return OpResult { msg: b"Crucible loaded; add ring or ingot mold to cast", ..OpResult::NONE };
            }
            OpResult::NONE
        }
    }
}

// -- Workbench state ----------------------------------------------------------

const N_APPARATUS: usize = 4;

pub struct Workbench {
    pub slots:      [WorkbenchSlot; N_APPARATUS],
    pub selected:   usize,
    pub last_msg:   [u8; 80],
    pub last_msg_n: usize,
    pub last_item:  u16,
    pub last_item_n: u16,
    pub exited:     bool,
    rule_y: u32,
}

static mut WB: Workbench = Workbench {
    slots: [
        WorkbenchSlot::empty(Apparatus::Mortar),
        WorkbenchSlot::empty(Apparatus::Retort),
        WorkbenchSlot::empty(Apparatus::Furnace),
        WorkbenchSlot::empty(Apparatus::Crucible),
    ],
    selected:   0,
    last_msg:   [0u8; 80],
    last_msg_n: 0,
    last_item:  0,
    last_item_n: 0,
    exited:     false,
    rule_y:     0,
};

pub fn workbench() -> &'static mut Workbench { unsafe { &mut WB } }

static mut WB_REQ: bool = false;
pub fn request()         { unsafe { WB_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = WB_REQ; WB_REQ = false; r } }

impl Workbench {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y = rule_y;
        self.exited = false;
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn operate(&mut self) {
        let rank = crate::player_state::skill_rank(crate::skills::SKILL_ALCHEMY_IDX);
        let result = resolve(&self.slots[self.selected], rank);
        let mn = result.msg.len().min(80);
        self.last_msg[..mn].copy_from_slice(&result.msg[..mn]);
        self.last_msg_n = mn;
        if result.item_id != 0 {
            crate::player_state::inv_add(result.item_id, result.item_count);
            self.last_item   = result.item_id;
            self.last_item_n = result.item_count;
            self.slots[self.selected].clear();
            crate::eigenstate::advance(crate::eigenstate::T_GRAPEVINE);
            let ps = crate::player_state::get_mut();
            ps.sanity[0] = ps.sanity[0].saturating_add(4);
        }
    }

    pub fn load_from_inv(&mut self, obj_id: u16, base_traits: u16) -> bool {
        self.slots[self.selected].load(obj_id, base_traits)
    }

    pub fn clear_selected(&mut self) { self.slots[self.selected].clear(); }

    pub fn handle_key(&mut self, key: crate::input::Key) {
        use crate::input::Key;
        match key {
            Key::Left  => { if self.selected > 0 { self.selected -= 1; } }
            Key::Right => { if self.selected + 1 < N_APPARATUS { self.selected += 1; } }
            Key::Enter | Key::Char(b'o') | Key::Char(b'O') => self.operate(),
            Key::Char(b'c') | Key::Char(b'C') => self.clear_selected(),
            Key::Char(b's') => { self.slots[self.selected].load(OBJ_SULPHUR, TRAIT_FLAMMABLE); }
            Key::Char(b'n') => { self.slots[self.selected].load(OBJ_SALTPETER, TRAIT_FLAMMABLE); }
            Key::Char(b'k') => { self.slots[self.selected].load(OBJ_CHARCOAL, TRAIT_FLAMMABLE); }
            Key::Char(b'w') => { self.slots[self.selected].load(OBJ_WATER, TRAIT_USABLE | TRAIT_FULL); }
            Key::Char(b'h') => { self.slots[self.selected].load(OBJ_HERB_COMMON, TRAIT_USABLE | TRAIT_ALIVE); }
            Key::Char(b'H') => { self.slots[self.selected].load(OBJ_HERB_RESTORE, TRAIT_USABLE | TRAIT_ALIVE); }
            Key::Char(b'i') => { self.slots[self.selected].load(OBJ_IRON, TRAIT_INERT | TRAIT_MOVABLE); }
            Key::Char(b'g') => { self.slots[self.selected].load(OBJ_GOLD, TRAIT_INERT | TRAIT_MOVABLE); }
            Key::Char(b'm') => { self.slots[self.selected].load(OBJ_MERCURY_OBJ, TRAIT_POISONOUS | TRAIT_MOVABLE); }
            Key::Char(b'r') => { self.slots[self.selected].load(OBJ_RING_MOLD, TRAIT_USABLE | TRAIT_MOVABLE); }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn crate::gpu::GpuSurface) {
        use crate::render2d::It;
        use crate::style;
        let it  = It::new(gpu);
        let t   = style::get();
        let w   = gpu.width();
        let top = self.rule_y + 8;
        it.fill(0, top, w, gpu.height().saturating_sub(top), t.bg);
        it.text(40, top + 4, "Workbench", 2, t.header);
        it.text(40, top + 26, "Hypatia's Alchemical Laboratory", 1, t.text_dim);

        let slot_w = (w.saturating_sub(80)) / N_APPARATUS as u32;
        for i in 0..N_APPARATUS {
            let sx  = 40 + i as u32 * (slot_w + 4);
            let sy  = top + 48;
            let sel = i == self.selected;
            let border = if sel { t.accent } else { t.rule };
            let bg     = if sel { style::mix(t.bg, t.surface, 40) } else { t.surface };
            it.fill(sx, sy, slot_w, 80, bg);
            it.fill(sx, sy, slot_w, 1, border);
            it.fill(sx, sy + 79, slot_w, 1, border);
            it.fill(sx, sy, 1, 80, border);
            it.fill(sx + slot_w - 1, sy, 1, 80, border);
            let ap = &self.slots[i];
            it.text(sx + 4, sy + 4, ap.apparatus.name(), 1, if sel { t.accent } else { t.text });
            for j in 0..ap.loaded_n {
                let oname = obj_name_short(ap.loaded[j]);
                let ttag  = trait_tag_short(ap.traits[j]);
                it.text(sx + 4, sy + 18 + j as u32 * 12, oname, 1, t.text_dim);
                if !ttag.is_empty() {
                    it.text(sx + 4 + 7 * 6, sy + 18 + j as u32 * 12, ttag, 1, t.accent);
                }
            }
            if ap.loaded_n == 0 {
                it.text(sx + 4, sy + 18, "(empty)", 1, (60, 60, 60));
            }
        }
        if self.last_msg_n > 0 {
            let ms = core::str::from_utf8(&self.last_msg[..self.last_msg_n]).unwrap_or("");
            it.text(40, top + 144, ms, 1, t.accent);
        }
        it.text(40, top + 164,
            "Load: [s]=sulphur [n]=saltpeter [k]=charcoal [w]=water [h]=herb [H]=restore [i]=iron [g]=gold [m]=mercury [r]=ring mold",
            1, t.text_dim);
        it.text(40, top + 176,
            "arrows=select  [O/Enter]=operate  [C]=clear  Esc=back",
            1, t.text_dim);
    }
}

// -- Helpers ------------------------------------------------------------------

fn contains1(objs: &[u16], id: u16) -> bool { objs.iter().any(|&o| o == id) }

fn contains3(objs: &[u16], a: u16, b: u16, c: u16) -> bool {
    contains1(objs, a) && contains1(objs, b) && contains1(objs, c)
}

fn contains_powdered(objs: &[u16], id: u16) -> bool { contains1(objs, id) }

fn is_metal(obj: u16) -> bool {
    matches!(obj, OBJ_IRON | OBJ_GOLD | OBJ_COPPER | OBJ_MERCURY_OBJ | OBJ_SILVER | OBJ_LEAD)
}

fn metal_ring_type(metal: u16) -> Option<u16> {
    match metal {
        OBJ_GOLD | OBJ_SILVER | OBJ_COPPER => Some(ITEM_RING),
        _ => None,
    }
}

fn obj_name_short(id: u16) -> &'static str {
    match id {
        OBJ_MORTAR         => "Mortar",
        OBJ_PESTLE         => "Pestle",
        OBJ_RETORT         => "Retort",
        OBJ_VOLUME_FLASK   => "Vol.Flask",
        OBJ_REAGENT_BOTTLE => "Reagent",
        OBJ_FURNACE        => "Furnace",
        OBJ_CRUCIBLE       => "Crucible",
        OBJ_SALTPETER      => "Saltpeter",
        OBJ_SULPHUR        => "Sulphur",
        OBJ_CHARCOAL       => "Charcoal",
        OBJ_IRON           => "Iron",
        OBJ_GOLD           => "Gold",
        OBJ_COPPER         => "Copper",
        OBJ_MERCURY_OBJ    => "Mercury",
        OBJ_SILVER         => "Silver",
        OBJ_LEAD           => "Lead",
        OBJ_WATER          => "Water",
        OBJ_HERB_COMMON    => "Herb",
        OBJ_HERB_RESTORE   => "Herb+",
        OBJ_RAW_DESIRE     => "RawDesire",
        OBJ_ASMODEAN       => "Asmodean",
        OBJ_RING_MOLD      => "Ring Mold",
        OBJ_INGOT_MOLD     => "IngotMold",
        OBJ_GLYCERINE      => "Glycerine",
        OBJ_DESERT_GLASS   => "D.Glass",
        _                  => "???",
    }
}

fn trait_tag_short(traits: u16) -> &'static str {
    if traits & TRAIT_MOLTEN    != 0 { return "[MOL]"; }
    if traits & TRAIT_POWDERED  != 0 { return "[PWD]"; }
    if traits & TRAIT_EXPLOSIVE != 0 { return "[EXP]"; }
    if traits & TRAIT_POISONOUS != 0 { return "[PSN]"; }
    if traits & TRAIT_FLAMMABLE != 0 { return "[FLM]"; }
    ""
}

/// Alchemy skill slot index (mirrors skills::SKILL_ALCHEMY_IDX).
pub const SKILL_ALCHEMY_IDX: usize = crate::skills::SKILL_ALCHEMY_IDX;

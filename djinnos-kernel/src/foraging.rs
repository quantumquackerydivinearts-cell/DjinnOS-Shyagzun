// foraging.rs -- World resource foraging and Fae relation tracking.
//
// Resources are organised by the five Lotus elemental axes:
//   Zot  (Earth) -- minerals, metals, stone
//   Mel  (Water) -- water, aquatic, moisture
//   Puf  (Air)   -- herbs, plants, spores
//   Shak (Fire)  -- sulphur, charcoal, volcanic minerals
//   Kael (Life)  -- living organisms, seeds; affects ALL Fae equally
//
// Elemental cross-contamination is built into each resource definition.
// Taking charcoal means burning wood -- the Shak act has a Zot (Dryad)
// secondary impact.  Draining a mountain stream affects both Undines (Mel)
// and Nymphs (Puf -- the moisture that feeds the plants above).
//
// The Fae relation state is INVISIBLE to the player.
// Consequences surface as: NPC dialogue tone, quest gate availability,
// Fae entity behaviour (welcoming/wary/hostile), and rare material gifting.
// For the author/designer, the full state is readable via Atelier/shell.
//
// Harvest thresholds (per zone per session):
//   1-2  items -- Light.    Negligible effect.  Natural.
//   3-5  items -- Moderate. Small elemental draw.
//   6-10 items -- Heavy.    Noticeable draw; zone recovery timer set.
//   11+  items -- Strip.    Significant negative; zone depleted.
//   Destroy src -- Permanent negative; ko_flag written.
//
// Source: Lotus tongue (bytes 1-8); KLOB IDs from kos_labyrnth.py ss11.2.

// -- Lotus element enum --------------------------------------------------------

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Elem { Zot, Mel, Puf, Shak, Kael }

// -- Fae type enum -------------------------------------------------------------

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum FaeType { Dryad, Undine, Nymph, Salamander }

// -- Disposition ---------------------------------------------------------------
// How a Fae type currently regards the player.  Never shown directly to the
// player; accessed by dialogue/quest systems.

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Disposition { Welcoming, Neutral, Wary, Hostile }

// -- Resource definition -------------------------------------------------------

pub struct ResourceDef {
    pub obj_id:      u16,         // KLOB numeric ID
    pub name:        &'static [u8],
    pub zone:        ZoneId,
    pub elem:        Elem,
    pub base_yield:  u8,          // objects per harvest action
    pub abundance:   u8,          // 0-5; 0 = depleted
    // Each unit harvested costs this much on the primary element balance.
    pub primary_cost: i8,
    // Optional secondary element affected (cross-contamination).
    pub secondary_elem: Option<Elem>,
    pub secondary_cost: i8,
    // Cost if the SOURCE is destroyed entirely.
    pub destroy_cost: i8,
}

// -- Zone IDs ------------------------------------------------------------------

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ZoneId {
    Wiltoll,      // Mt. Elaene foothills -- Zot/Puf, Dryad/Nymph
    Azonithia,    // City proper -- limited foraging
    Hieronymus,   // Mines and plateau -- Shak/Zot, Salamander/Dryad boundary
    Ocean,        // Plateau coast -- Mel, Undine territory
    Mercurie,     // Faewilds (when accessible) -- Kael/Puf, all Fae
    Sulphera,     // Underworld zones -- extreme Shak
}

// -- Resource table ------------------------------------------------------------
// All KLOB IDs match kos_labyrnth.py _OBJECT_TABLE exactly.

pub const RESOURCES: &[ResourceDef] = &[
    // ── Wiltoll / Mt. Elaene foothills ────────────────────────────────────────
    ResourceDef {
        obj_id: 0x0049, name: b"Herb (Common)",
        zone: ZoneId::Wiltoll, elem: Elem::Puf,
        base_yield: 2, abundance: 5,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -5,
    },
    ResourceDef {
        obj_id: 0x004A, name: b"Herb (Restorative)",
        zone: ZoneId::Wiltoll, elem: Elem::Puf,
        base_yield: 1, abundance: 3,
        primary_cost: -2, secondary_elem: None, secondary_cost: 0, destroy_cost: -8,
    },
    ResourceDef {
        obj_id: 0x0028, name: b"Water",
        zone: ZoneId::Wiltoll, elem: Elem::Mel,
        base_yield: 3, abundance: 5,
        primary_cost: -1, secondary_elem: Some(Elem::Puf), secondary_cost: -1,
        destroy_cost: -10,
    },
    ResourceDef {
        obj_id: 0x002A, name: b"Flint",    // 0042_KLOB
        zone: ZoneId::Wiltoll, elem: Elem::Zot,
        base_yield: 2, abundance: 4,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -4,
    },
    ResourceDef {
        obj_id: 0x002F, name: b"Chalk",    // 0046_KLOB
        zone: ZoneId::Wiltoll, elem: Elem::Zot,
        base_yield: 2, abundance: 4,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -3,
    },

    // ── Hieronymus Mines / Plateau ─────────────────────────────────────────────
    ResourceDef {
        obj_id: 0x0018, name: b"Sulphur",   // 0024_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Shak,
        base_yield: 2, abundance: 4,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -6,
    },
    ResourceDef {
        obj_id: 0x0017, name: b"Saltpeter", // 0023_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Shak,
        base_yield: 1, abundance: 3,
        primary_cost: -2, secondary_elem: None, secondary_cost: 0, destroy_cost: -7,
    },
    ResourceDef {
        // Charcoal: burning wood -- Shak act with Zot (Dryad) secondary damage.
        obj_id: 0x0019, name: b"Charcoal",  // 0025_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Shak,
        base_yield: 3, abundance: 3,
        primary_cost: -1, secondary_elem: Some(Elem::Zot), secondary_cost: -2,
        destroy_cost: -9,
    },
    ResourceDef {
        obj_id: 0x001B, name: b"Iron",      // 0027_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Zot,
        base_yield: 1, abundance: 4,
        primary_cost: -2, secondary_elem: None, secondary_cost: 0, destroy_cost: -8,
    },
    ResourceDef {
        obj_id: 0x001D, name: b"Copper",    // 0029_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Zot,
        base_yield: 1, abundance: 3,
        primary_cost: -2, secondary_elem: None, secondary_cost: 0, destroy_cost: -7,
    },
    ResourceDef {
        obj_id: 0x001E, name: b"Mercury",   // 0030_KLOB -- poisonous; Undine secondary
        zone: ZoneId::Hieronymus, elem: Elem::Zot,
        base_yield: 1, abundance: 2,
        primary_cost: -3, secondary_elem: Some(Elem::Mel), secondary_cost: -3,
        destroy_cost: -12,
    },
    ResourceDef {
        obj_id: 0x0030, name: b"Quartz",    // 0048_KLOB
        zone: ZoneId::Hieronymus, elem: Elem::Zot,
        base_yield: 2, abundance: 4,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -4,
    },

    // ── Ocean / Hieronymus Plateau coast ──────────────────────────────────────
    ResourceDef {
        obj_id: 0x0028, name: b"Water (ocean)",  // same obj_id, different zone
        zone: ZoneId::Ocean, elem: Elem::Mel,
        base_yield: 4, abundance: 5,
        primary_cost: -1, secondary_elem: None, secondary_cost: 0, destroy_cost: -12,
    },
    ResourceDef {
        obj_id: 0x0031, name: b"Pumice",    // 0049_KLOB
        zone: ZoneId::Ocean, elem: Elem::Zot,
        base_yield: 2, abundance: 3,
        primary_cost: -1, secondary_elem: Some(Elem::Mel), secondary_cost: -1,
        destroy_cost: -4,
    },
    ResourceDef {
        // Pearl: Kael (life) -- affects all Fae.  Rare, precious.
        obj_id: 0x0043, name: b"Pearl",     // 0067_KLOB
        zone: ZoneId::Ocean, elem: Elem::Kael,
        base_yield: 1, abundance: 2,
        primary_cost: -4, secondary_elem: None, secondary_cost: 0, destroy_cost: -15,
    },
    ResourceDef {
        obj_id: 0x0015, name: b"Glycerine", // 0021_KLOB -- aquatic plant oils
        zone: ZoneId::Ocean, elem: Elem::Mel,
        base_yield: 1, abundance: 3,
        primary_cost: -2, secondary_elem: Some(Elem::Puf), secondary_cost: -1,
        destroy_cost: -8,
    },

    // ── Mercurie (Faewilds) -- only accessible after Transcendental / ship ────
    ResourceDef {
        // Kael Spore: highest consequence.  Taking it from Faewilds is maximally felt.
        obj_id: 0x004D, name: b"Kael Spore", // 0077_KLOB (Asmodean Essence equiv)
        zone: ZoneId::Mercurie, elem: Elem::Kael,
        base_yield: 1, abundance: 2,
        primary_cost: -6, secondary_elem: None, secondary_cost: 0, destroy_cost: -20,
    },
    ResourceDef {
        obj_id: 0x0042, name: b"Desert Glass", // 0066_KLOB -- lightning/sky formation
        zone: ZoneId::Mercurie, elem: Elem::Puf,
        base_yield: 1, abundance: 1,
        primary_cost: -3, secondary_elem: None, secondary_cost: 0, destroy_cost: -10,
    },
    ResourceDef {
        obj_id: 0x0041, name: b"Moldavite",  // 0065_KLOB -- sky-born, Kael-adjacent
        zone: ZoneId::Mercurie, elem: Elem::Kael,
        base_yield: 1, abundance: 1,
        primary_cost: -5, secondary_elem: Some(Elem::Puf), secondary_cost: -2,
        destroy_cost: -18,
    },

    // ── Sulphera (underworld zones) ───────────────────────────────────────────
    ResourceDef {
        // Raw Desire Stone: Asmodean, Kael-aligned, from the Lust Ring environs.
        obj_id: 0x004C, name: b"Raw Desire Stone", // 0076_KLOB
        zone: ZoneId::Sulphera, elem: Elem::Kael,
        base_yield: 1, abundance: 2,
        primary_cost: -5, secondary_elem: Some(Elem::Shak), secondary_cost: -2,
        destroy_cost: -20,
    },
];

// -- Zone depletion state ------------------------------------------------------
// Tracks per-zone session harvest count and recovery.
// Recovery happens over game days (3 in-game years = ~1155 days).

const N_ZONES: usize = 6;

fn zone_idx(z: ZoneId) -> usize {
    match z {
        ZoneId::Wiltoll    => 0,
        ZoneId::Azonithia  => 1,
        ZoneId::Hieronymus => 2,
        ZoneId::Ocean      => 3,
        ZoneId::Mercurie   => 4,
        ZoneId::Sulphera   => 5,
    }
}

#[derive(Copy, Clone)]
struct ZoneState {
    // Items harvested this session (resets after recovery_days have passed).
    session_count: u8,
    // Days since last heavy harvest.  When this reaches recovery_threshold, zone recovers.
    recovery_days: u16,
    // Permanent depletion (destroy_source called).
    destroyed:     bool,
}

impl ZoneState {
    const fn new() -> Self { Self { session_count: 0, recovery_days: 0, destroyed: false } }
}

static mut ZONE_STATES: [ZoneState; N_ZONES] = [ZoneState::new(); N_ZONES];

// -- Fae relation state --------------------------------------------------------

#[derive(Copy, Clone)]
pub struct FaeRelation {
    // Elemental balance per axis.  Starts at 0; negative = extractive.
    // Floor at -100 (complete hostility); no positive ceiling (goodwill accrues).
    pub zot:  i16,
    pub mel:  i16,
    pub puf:  i16,
    pub shak: i16,
    pub kael: i16,
    // Behavioural counters.
    pub zones_stripped:    u8,
    pub sources_destroyed: u8,
    pub offerings_left:    u8,
}

impl FaeRelation {
    const fn new() -> Self {
        Self { zot: 0, mel: 0, puf: 0, shak: 0, kael: 0,
               zones_stripped: 0, sources_destroyed: 0, offerings_left: 0 }
    }

    fn apply_elem(&mut self, elem: Elem, delta: i8) {
        let v = match elem {
            Elem::Zot  => &mut self.zot,
            Elem::Mel  => &mut self.mel,
            Elem::Puf  => &mut self.puf,
            Elem::Shak => &mut self.shak,
            Elem::Kael => &mut self.kael,
        };
        *v = (*v + delta as i16).max(-100).min(50);
    }

    // Returns the disposition of a specific Fae type toward the player.
    // Dryads read Zot + Kael/2.  Undines read Mel + Kael/2.
    // Nymphs read Puf + Kael/2.  Salamanders read Shak + Kael/2.
    pub fn disposition(&self, fae: FaeType) -> Disposition {
        let base = match fae {
            FaeType::Dryad     => self.zot,
            FaeType::Undine    => self.mel,
            FaeType::Nymph     => self.puf,
            FaeType::Salamander=> self.shak,
        };
        let kael_weight = self.kael / 2;
        let score = base + kael_weight
            - self.zones_stripped   as i16 * 3
            - self.sources_destroyed as i16 * 8
            + self.offerings_left    as i16 * 2;

        match score {
            s if s >= 5  => Disposition::Welcoming,
            s if s >= -10 => Disposition::Neutral,
            s if s >= -30 => Disposition::Wary,
            _             => Disposition::Hostile,
        }
    }

    // Whether the player can access the Fae quest line at all.
    // Requires no Fae type to be Hostile AND at least two Neutral or better.
    pub fn can_access_fae_line(&self) -> bool {
        let types = [FaeType::Dryad, FaeType::Undine, FaeType::Nymph, FaeType::Salamander];
        let mut hostile = 0u8;
        let mut neutral_or_better = 0u8;
        for t in &types {
            match self.disposition(*t) {
                Disposition::Hostile   => hostile += 1,
                Disposition::Wary      => {}
                _                      => neutral_or_better += 1,
            }
        }
        hostile == 0 && neutral_or_better >= 2
    }

    // Whether Zoha will offer the bone flute (Zoha Are, quest 0033).
    // Requires Nymph at least Neutral AND Kael balance >= -10.
    pub fn can_receive_bone_flute(&self) -> bool {
        self.disposition(FaeType::Nymph) <= Disposition::Neutral
            && self.kael >= -10
    }

    // Whether Amelia will trust the player enough for the Fae protection path.
    // Requires all four types Neutral or better.
    pub fn amelia_trusts_player(&self) -> bool {
        let types = [FaeType::Dryad, FaeType::Undine, FaeType::Nymph, FaeType::Salamander];
        types.iter().all(|t| self.disposition(*t) <= Disposition::Neutral)
    }

    pub fn save(&self) {
        static mut BUF: [u8; 16] = [0u8; 16];
        let buf = unsafe { &mut BUF };
        macro_rules! wi16 { ($v:expr, $i:expr) => {
            let x = $v as i16;
            buf[$i]   = (x & 0xFF) as u8;
            buf[$i+1] = ((x >> 8) & 0xFF) as u8;
        } }
        wi16!(self.zot,  0); wi16!(self.mel,  2);
        wi16!(self.puf,  4); wi16!(self.shak, 6); wi16!(self.kael, 8);
        buf[10] = self.zones_stripped;
        buf[11] = self.sources_destroyed;
        buf[12] = self.offerings_left;
        crate::sa::write_file(b"fae.dat", &buf[..13]);
    }

    pub fn load(&mut self) {
        let mut buf = [0u8; 16];
        if crate::sa::read_file(b"fae.dat", &mut buf) < 13 { return; }
        macro_rules! ri16 { ($i:expr) => {
            (buf[$i] as i16) | ((buf[$i+1] as i16) << 8)
        } }
        self.zot  = ri16!(0); self.mel  = ri16!(2);
        self.puf  = ri16!(4); self.shak = ri16!(6); self.kael = ri16!(8);
        self.zones_stripped   = buf[10];
        self.sources_destroyed = buf[11];
        self.offerings_left   = buf[12];
    }
}

static mut FAE_REL: FaeRelation = FaeRelation::new();

pub fn fae() -> &'static mut FaeRelation { unsafe { &mut FAE_REL } }

// -- Harvest function ----------------------------------------------------------

pub struct HarvestResult {
    pub obj_id: u16,
    pub count:  u8,
    pub zone_depleted: bool,
}

/// Attempt to harvest `resource_idx` from RESOURCES.
///
/// Survival skill modulation:
///   rank  1-19:  base yield, full Fae cost, base strip threshold
///   rank 20-39:  +1 yield on rich nodes, 20% reduced Fae cost
///   rank 40-59:  +1 yield always, 40% reduced Fae cost, wider strip threshold
///   rank 60-79:  +2 yield on rich nodes, 50% reduced cost, zone recovery +50%
///   rank 80-100: expert -- minimal Fae impact, maximum yield, reads signs
///               before harvesting (warns if zone near depletion)
///
/// The Survival skill represents reading the land correctly --
/// knowing what to take, how much, and how to leave it viable.
/// High Survival makes the player a sustainable forager rather than
/// an extractive one.  Low Survival strips zones accidentally.
pub fn harvest(resource_idx: usize) -> Option<HarvestResult> {
    if resource_idx >= RESOURCES.len() { return None; }
    let r   = &RESOURCES[resource_idx];
    let zi  = zone_idx(r.zone);
    let zs  = unsafe { &mut ZONE_STATES[zi] };

    if zs.destroyed { return None; }

    let survival = crate::player_state::skill_rank(crate::skills::SKILL_SURVIVAL_IDX);

    // Effective strip threshold scales with Survival.
    let eff_threshold = effective_threshold(r.zone, survival);
    if zs.session_count >= eff_threshold { return None; }

    // Yield bonus from Survival.
    let bonus: u8 = match survival {
        80..=100 => 2,
        40..=79  => 1,
        20..=39  if r.abundance >= 4 => 1,
        _        => 0,
    };
    let count = r.base_yield + bonus;
    zs.session_count += count;

    // Fae cost reduction: high Survival means knowing how to take
    // without damaging the source.
    let cost_factor: i8 = match survival {
        80..=100 => 20,   // 20% of normal cost
        60..=79  => 50,
        40..=59  => 60,
        20..=39  => 80,
        _        => 100,  // full cost
    };
    let primary_cost = (r.primary_cost as i16 * cost_factor as i16 / 100) as i8;
    let secondary_cost = (r.secondary_cost as i16 * cost_factor as i16 / 100) as i8;

    // Apply relation deltas.
    let rel = fae();
    rel.apply_elem(r.elem, primary_cost * count as i8);
    if let (Some(se), sc) = (r.secondary_elem, secondary_cost) {
        if sc != 0 { rel.apply_elem(se, sc * count as i8); }
    }
    // Kael echo: at high Survival, taking is accompanied by awareness
    // that almost eliminates the Kael draw.
    if survival < 60 {
        rel.apply_elem(Elem::Kael, -(count as i8 / 3).max(0).min(1));
    }

    // Check strip threshold.
    let depleted = zs.session_count >= eff_threshold;
    if depleted {
        zs.recovery_days = 0;
        // Low Survival players strip zones accidentally.
        // High Survival players shouldn't reach this point (threshold higher).
        if survival < 40 {
            rel.zones_stripped = rel.zones_stripped.saturating_add(1);
        }
    }

    // Add to player inventory.
    crate::player_state::inv_add(r.obj_id, count as u16);

    Some(HarvestResult { obj_id: r.obj_id, count, zone_depleted: depleted })
}

/// Permanently destroy a resource source (burning a forest, draining a spring).
/// Sets ko_flag, applies maximum negative relation, marks zone destroyed.
pub fn destroy_source(resource_idx: usize) {
    if resource_idx >= RESOURCES.len() { return; }
    let r  = &RESOURCES[resource_idx];
    let zi = zone_idx(r.zone);
    unsafe { ZONE_STATES[zi].destroyed = true; }

    let rel = fae();
    rel.apply_elem(r.elem, r.destroy_cost);
    if let (Some(se), sc) = (r.secondary_elem, r.secondary_cost) {
        rel.apply_elem(se, sc * 3); // amplified secondary on destruction
    }
    rel.apply_elem(Elem::Kael, -5); // all Fae feel destruction of life
    rel.sources_destroyed = rel.sources_destroyed.saturating_add(1);

    // Set genocide-path flag.
    crate::ko_flags::ko_set(crate::ko_flags::F_GENOCIDE_PATH);
}

/// Leave an offering at a zone (an act of reciprocity).
/// Used by players who want to restore Fae goodwill.
/// Requires an item from inventory to offer.
pub fn leave_offering(zone: ZoneId, item_id: u16) -> bool {
    if !crate::player_state::inv_remove(item_id, 1) { return false; }
    let elem = offering_element(item_id);
    let rel  = fae();
    rel.apply_elem(elem, 3);    // direct restoration
    rel.apply_elem(Elem::Kael, 1); // Kael appreciates any giving-back
    rel.offerings_left = rel.offerings_left.saturating_add(1);
    // Log in journal.
    crate::journal::add_note(b"Left an offering.");
    true
}

// -- Advance game day (call from main loop periodically) ----------------------

/// Advance zone recovery by one game day.
/// Survival skill accelerates zone recovery -- skilled foragers disturb
/// less and leave zones that heal faster behind them.
pub fn advance_day() {
    let survival = crate::player_state::skill_rank(crate::skills::SKILL_SURVIVAL_IDX);
    // Recovery threshold: how many days before a zone starts healing.
    // Lower threshold = faster recovery.  Survival compresses this window.
    let recovery_threshold: u16 = match survival {
        80..=100 => 10,   // expert -- zones recover quickly
        60..=79  => 15,
        40..=59  => 20,
        20..=39  => 25,
        _        => 30,   // untrained -- slow recovery
    };
    // Recovery rate: how much session_count decreases per recovery tick.
    let recovery_rate: u8 = match survival {
        80..=100 => 4,
        60..=79  => 3,
        40..=59  => 2,
        _        => 1,
    };

    let zones = unsafe { &mut ZONE_STATES };
    for zs in zones.iter_mut() {
        if !zs.destroyed && zs.session_count > 0 {
            zs.recovery_days += 1;
            if zs.recovery_days >= recovery_threshold {
                zs.session_count = zs.session_count.saturating_sub(recovery_rate);
                if zs.session_count == 0 { zs.recovery_days = 0; }
            }
        }
    }
    // Small Kael drift toward neutral over time -- the world tries to heal.
    // High Survival players heal Kael faster through their relationship with the land.
    let rel = fae();
    if rel.kael < 0 {
        let kael_heal = if survival >= 60 { 1 } else if survival >= 30 { 1 } else { 0 };
        // Only heal Kael every few days for low Survival.
        rel.kael = (rel.kael + kael_heal as i16).min(0);
    }
}

// -- Quick forage for game7 UI ------------------------------------------------
// Maps a zone_registry zone slug to a foraging ZoneId and attempts a harvest.
pub fn forage_zone(zone_id: &[u8]) -> &'static [u8] {
    let fzone = match zone_id {
        b"wiltoll_lane"
        | b"mt_elaene_path"    => Some(ZoneId::Wiltoll),
        b"azonithia_west"
        | b"hopefare"
        | b"orebustle"
        | b"june_street"
        | b"temple_quarter"    => Some(ZoneId::Azonithia),
        b"mt_hieronymus_foothills"
        | b"lapidus_mines"     => Some(ZoneId::Hieronymus),
        b"ocean_shore"
        | b"serpents_pass"     => Some(ZoneId::Ocean),
        b"tideglass" | b"cindergrove" | b"rootbloom"
        | b"thornveil"| b"dewspire"
        | b"mercurie_threshold"=> Some(ZoneId::Mercurie),
        b"visitor_ring" | b"lust_outer" | b"the_asmodean_market"
        | b"pride_outer" | b"sloth_outer" | b"wrath_outer"
        | b"gluttony_outer" | b"envy_outer" | b"greed_outer" => Some(ZoneId::Sulphera),
        _                      => None,
    };
    let zid = match fzone { Some(z) => z, None => return b"Nothing to forage here." };
    for (i, r) in RESOURCES.iter().enumerate() {
        if r.zone == zid {
            if let Some(hr) = harvest(i) {
                return if hr.zone_depleted {
                    b"Gathered supplies -- but this area is growing thin."
                } else {
                    b"You forage and find something useful."
                };
            }
        }
    }
    b"Nothing to forage here right now."
}

// -- Kobra / shell dispatch ---------------------------------------------------

pub fn forage_dispatch(args: &[u8], out: &mut crate::kobra::EvalResult) {
    let (verb, rest) = split_verb(args);
    match verb {
        b"list" | b"" => {
            // List all resources in the given zone, or all zones.
            let zone_filter = parse_zone(rest);
            for (i, r) in RESOURCES.iter().enumerate() {
                if zone_filter.map_or(false, |z| z != r.zone) { continue; }
                let zi  = zone_idx(r.zone);
                let zs  = unsafe { &ZONE_STATES[zi] };
                let avail = !zs.destroyed && zs.session_count < strip_threshold(r.zone);
                let tag: &[u8] = if zs.destroyed      { b"[gone]" }
                                 else if !avail       { b"[depleted]" }
                                 else                 { b"[available]" };
                out.push_text(&[b'0' + (i / 10) as u8, b'0' + (i % 10) as u8, b' ']);
                out.push_text(r.name);
                out.push_text(b"  ");
                out.push_text(zone_name(r.zone));
                out.push_text(b"  ");
                out.push_text(tag);
                out.push_line();
            }
        }
        b"take" => {
            if let Some(idx) = parse_u8(rest) {
                match harvest(idx as usize) {
                    Some(hr) => {
                        out.push_text(b"harvested: ");
                        out.push_text(RESOURCES[idx as usize].name);
                        out.push_text(b" x");
                        let mut nb = [0u8; 4]; let nn = write_u8(&mut nb, hr.count);
                        out.push_text(&nb[..nn]);
                        if hr.zone_depleted { out.push_text(b"  [zone depleted]"); }
                        out.push_line();
                    }
                    None => { out.push_text(b"nothing to harvest here"); out.push_line(); }
                }
            } else {
                out.push_text(b"forage take <idx>"); out.push_line();
            }
        }
        b"offer" => {
            // forage offer <zone> <item_id_hex>
            let (zone_s, item_s) = split_verb(rest);
            if let (Some(zone), Some(item_id)) = (parse_zone(zone_s), parse_hex_u16(item_s)) {
                if leave_offering(zone, item_id) {
                    out.push_text(b"offering left"); out.push_line();
                } else {
                    out.push_text(b"item not in inventory"); out.push_line();
                }
            } else {
                out.push_text(b"forage offer <zone> <item_id_hex>"); out.push_line();
            }
        }
        b"fae" => {
            // Show Fae relation state (designer/author tool).
            let rel = fae();
            let labels = [b"Zot  (Dryad)    " as &[u8], b"Mel  (Undine)   ",
                          b"Puf  (Nymph)    ", b"Shak (Salamander)",
                          b"Kael (All)      "];
            let vals = [rel.zot, rel.mel, rel.puf, rel.shak, rel.kael];
            for i in 0..5 {
                out.push_text(labels[i]);
                let v = vals[i];
                if v >= 0 { out.push_text(b"+"); }
                let mut nb = [0u8; 8]; let nn = write_i16(&mut nb, v);
                out.push_text(&nb[..nn]);
                let disp = if i < 4 {
                    let ft = [FaeType::Dryad, FaeType::Undine, FaeType::Nymph, FaeType::Salamander][i];
                    match rel.disposition(ft) {
                        Disposition::Welcoming => b"  Welcoming" as &[u8],
                        Disposition::Neutral   => b"  Neutral",
                        Disposition::Wary      => b"  Wary",
                        Disposition::Hostile   => b"  HOSTILE",
                    }
                } else { b"" };
                out.push_text(disp);
                out.push_line();
            }
            out.push_text(b"Fae line: ");
            out.push_text(if rel.can_access_fae_line() { b"open" } else { b"CLOSED" });
            out.push_text(b"  Amelia trust: ");
            out.push_text(if rel.amelia_trusts_player() { b"yes" } else { b"no" });
            out.push_line();
        }
        _ => {
            out.push_text(b"forage: list [zone] | take <idx> | offer <zone> <item> | fae");
            out.push_line();
        }
    }
}

// -- Helpers ------------------------------------------------------------------

fn strip_threshold(z: ZoneId) -> u8 {
    match z {
        ZoneId::Mercurie | ZoneId::Sulphera => 3,   // fragile Fae zones
        ZoneId::Ocean                        => 8,
        _                                    => 12,
    }
}

/// Effective strip threshold for a zone given the player's Survival rank
/// and their Survival VITRIOL scale (L + T average).
/// Higher Survival + high L/T = zone tolerates more before flagging depletion.
fn effective_threshold(z: ZoneId, survival: u8) -> u8 {
    let base = strip_threshold(z);
    let rank_bonus: u8 = match survival {
        80..=100 => base / 2,
        60..=79  => base / 4,
        40..=59  => base / 6,
        _        => 0,
    };
    // L (Levity) + T (Tactility) VITRIOL scale adds up to base/4 more headroom.
    // vitriol_scale 100 = no bonus; 150 = +base/4 extra.
    let v_scale  = crate::skills::vitriol_scale(crate::skills::SKILL_SURVIVAL_IDX);
    let vit_bonus = (base as u32 * v_scale.saturating_sub(100) / 400) as u8;
    base + rank_bonus + vit_bonus
}

fn zone_name(z: ZoneId) -> &'static [u8] {
    match z {
        ZoneId::Wiltoll    => b"Wiltoll",
        ZoneId::Azonithia  => b"Azonithia",
        ZoneId::Hieronymus => b"Hieronymus",
        ZoneId::Ocean      => b"Ocean",
        ZoneId::Mercurie   => b"Mercurie",
        ZoneId::Sulphera   => b"Sulphera",
    }
}

fn parse_zone(s: &[u8]) -> Option<ZoneId> {
    match s {
        b"wiltoll"    | b"Wiltoll"    => Some(ZoneId::Wiltoll),
        b"azonithia"  | b"Azonithia"  => Some(ZoneId::Azonithia),
        b"hieronymus" | b"Hieronymus" => Some(ZoneId::Hieronymus),
        b"ocean"      | b"Ocean"      => Some(ZoneId::Ocean),
        b"mercurie"   | b"Mercurie"   => Some(ZoneId::Mercurie),
        b"sulphera"   | b"Sulphera"   => Some(ZoneId::Sulphera),
        _                             => None,
    }
}

fn offering_element(item_id: u16) -> Elem {
    // Map KLIT item IDs to the element they restore.
    match item_id {
        0x0003 | 0x0004 | 0x0005 => Elem::Puf,  // Apple, Pomegranate, Barley
        0x0002                   => Elem::Kael,  // Cherry (life-gift)
        0x0022 | 0x0023          => Elem::Puf,  // Tinctures (herb-derived)
        0x0025                   => Elem::Shak, // Infernal Salve (fire element)
        _                        => Elem::Kael, // default: Kael restoration
    }
}

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

fn parse_u8(s: &[u8]) -> Option<u8> {
    let s = trim(s); if s.is_empty() { return None; }
    let mut n = 0u16;
    for &b in s {
        if b < b'0' || b > b'9' { return None; }
        n = n * 10 + (b - b'0') as u16;
        if n > 255 { return None; }
    }
    Some(n as u8)
}

fn parse_hex_u16(s: &[u8]) -> Option<u16> {
    let s = trim(s); if s.is_empty() { return None; }
    let s = if s.starts_with(b"0x") { &s[2..] } else { s };
    let mut n = 0u32;
    for &b in s {
        let digit = match b {
            b'0'..=b'9' => b - b'0',
            b'a'..=b'f' => b - b'a' + 10,
            b'A'..=b'F' => b - b'A' + 10,
            _ => return None,
        };
        n = n * 16 + digit as u32;
        if n > 0xFFFF { return None; }
    }
    Some(n as u16)
}

fn write_u8(buf: &mut [u8], v: u8) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 3]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + x % 10; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}

fn write_i16(buf: &mut [u8], v: i16) -> usize {
    if v < 0 {
        if !buf.is_empty() { buf[0] = b'-'; }
        let n = write_u8(&mut buf[1..], v.unsigned_abs() as u8);
        n + 1
    } else {
        write_u8(buf, v as u8)
    }
}

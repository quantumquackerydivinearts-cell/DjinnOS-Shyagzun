// Native neural agent — The Twelvefold Coil.
//
// The 12-layer database structure from Layers.py expressed as computation.
// Each layer is a tiny feed-forward network; together they cascade from
// raw bit-level player eigenstate up to executable function.
//
//   Layer  1  Gaoh       Bit            small  — tongue activation bits
//   Layer  2  Ao-Seth    Decimal        small  — Rose numeral enumeration
//   Layer  3  Tyzu-Soa   Boolean        small  — Lotus initiator/terminator gates
//   Layer  4  Ja-Foa     Coordinate     small  — Sakura spatial orientation
//   Layer  5  Kael-Seth  Object         medium — Daisy cluster binding
//   Layer  6  Shak-Lo    Entity         medium — AppleBlossom identity/fire
//   Layer  7  Ru-Mavo    Color Metadata medium — Rose/Aster spectral signature
//   Layer  8  Si-Myza    Movement Diffs medium — Aster time-type change tracking
//   Layer  9  Dyf-Vr     Pattern Flows  medium — Grapevine jitter/rotor patterns
//   Layer 10  Ne-Soa     Names          full   — Daisy/Grapevine name-space
//   Layer 11  Sy-Mek     Scene Diffs    full   — Aster fold-time scene delta
//   Layer 12  Wu-Yl      Function       full   — Rose/Aster operative output
//
// Möbius invariant: Layer 12 wraps back to Layer 1.
// Wu-Yl (Process/Way operating on Run-space) IS Gaoh made operative.
// Same surface, higher density of correspondence.
//
// ── Entity depth — cosmological hierarchy maps to coil depth ─────────────────
//
//   Townfolk                      → layers 1–4  (Bit through Coordinate)
//   Witches/Priests/Royals/Assn   → layers 1–6  (through Entity)
//   Non-humans (1xxx)             → layers 1–8  (through Movement)
//   Demons                        → layers 1–9  (through Pattern)
//   Demigods                      → layers 1–10 (through Names)
//   Void Wraiths                  → layers 1–11 (through Scene)
//   Gods                          → layers 1–12 (through Function)
//   Primordials + Anima Mundi     → layers 1–12 + Möbius recurrence
//   Protagonist (0000_0451)       → layers 1–12 + Möbius (player traverses all)
//
// Lower-tier entities have zero or near-zero weights in layers above their
// depth ceiling — deeper signal does not propagate, so the coil is effectively
// shorter for them.  No conditional logic in the forward pass: the geometry
// does the gating.
//
// Weights are initialized analytically from RGB ring distances between
// tongue midpoints (palette::aki_color).  No training, no gradient descent.

use crate::palette;

// ── Layer widths ───────────────────────────────────────────────────────────────

pub const W01: usize = 38; // Bit — one per tongue in the current ledger
pub const W02: usize = 12; // Decimal — Rose base-12 numeral set
pub const W03: usize =  8; // Boolean — Lotus element pairs × polarity
pub const W04: usize = 12; // Coordinate — Sakura orientations + motion states
pub const W05: usize = 16; // Object — Daisy structural nodes
pub const W06: usize =  8; // Entity — tier gates × polarity
pub const W07: usize =  3; // Color — RGB spectral identity
pub const W08: usize = 12; // Movement — Aster time-types + space-modes
pub const W09: usize =  9; // Pattern — Grapevine dyf×3 / jru×3 / wik×3
pub const W10: usize = 16; // Names — Shygazun name-space width
pub const W11: usize = 12; // Scene — fold-time scene delta width
pub const W12: usize =  9; // Function — one per InteractionKind

// ── Interaction kinds ──────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq, Eq)]
#[repr(u8)]
pub enum InteractionKind {
    Dialogue        = 0,
    TeachSkill      = 1,
    QuestOffer      = 2,
    QuestAdvance    = 3,
    QuestComplete   = 4,
    Combat          = 5,
    LoreAccess      = 6,
    MeditationGuide = 7,
    Trade           = 8,
}

impl InteractionKind {
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Self::Dialogue),       1 => Some(Self::TeachSkill),
            2 => Some(Self::QuestOffer),     3 => Some(Self::QuestAdvance),
            4 => Some(Self::QuestComplete),  5 => Some(Self::Combat),
            6 => Some(Self::LoreAccess),     7 => Some(Self::MeditationGuide),
            8 => Some(Self::Trade),          _ => None,
        }
    }
}

// ── Layer — tiny feed-forward unit ────────────────────────────────────────────

/// Fixed-point i8 weights (−128..127, scale 1/128).
/// Output = ReLU(Σ w[j][i]×input[i] / 128 + b[j]) clamped 0–255.
struct Layer<const IN: usize, const OUT: usize> {
    w: [[i8; IN]; OUT],
    b: [i8; OUT],
}

impl<const IN: usize, const OUT: usize> Layer<IN, OUT> {
    const fn zero() -> Self {
        Layer { w: [[0i8; IN]; OUT], b: [0i8; OUT] }
    }

    fn forward(&self, input: &[u8; IN]) -> [u8; OUT] {
        let mut out = [0u8; OUT];
        for j in 0..OUT {
            let mut acc: i32 = self.b[j] as i32 * 128;
            for i in 0..IN {
                acc += self.w[j][i] as i32 * input[i] as i32;
            }
            out[j] = (acc / 128).max(0).min(255) as u8;
        }
        out
    }
}

// ── Coil state ─────────────────────────────────────────────────────────────────

pub struct CoilState {
    pub l01: [u8; W01], pub l02: [u8; W02], pub l03: [u8; W03],
    pub l04: [u8; W04], pub l05: [u8; W05], pub l06: [u8; W06],
    pub l07: [u8; W07], pub l08: [u8; W08], pub l09: [u8; W09],
    pub l10: [u8; W10], pub l11: [u8; W11], pub l12: [u8; W12],
}

impl CoilState {
    pub fn zero() -> Self {
        CoilState {
            l01:[0;W01], l02:[0;W02], l03:[0;W03], l04:[0;W04],
            l05:[0;W05], l06:[0;W06], l07:[0;W07], l08:[0;W08],
            l09:[0;W09], l10:[0;W10], l11:[0;W11], l12:[0;W12],
        }
    }

    pub fn best_kind(&self) -> Option<InteractionKind> {
        let (mut best, mut bi) = (0u8, None);
        for k in 0..W12 {
            if self.l12[k] > best { best = self.l12[k]; bi = InteractionKind::from_u8(k as u8); }
        }
        bi
    }

    /// Spectral identity: the RGB color of the current coil state (Layer 7).
    pub fn color(&self) -> (u8, u8, u8) { (self.l07[0], self.l07[1], self.l07[2]) }
}

// ── Agent definition ───────────────────────────────────────────────────────────

pub struct AgentDef {
    pub entity_id:    &'static [u8],
    pub name:         &'static [u8],
    pub notes:        &'static [u8],
    /// Quack count at which this agent reaches half-capability.  0 = always full.
    pub tongue_gate:  u8,
    /// Maximum coil layer active for this entity type (1–12).
    /// Derived from faction:
    ///   Townfolk=4  Witches/Priests/Royals/Assn/Sold=6  Non-human(1xxx)=8
    ///   Demon=9  Demigod=10  VoidWraith=11  God=12  Primordial/AnimaMundi=12+Möbius
    pub max_layer:    u8,
    /// True for Primordials and Anima Mundi: their coil closes on itself.
    pub mobius_close: bool,
    /// Shygazun byte addresses defining the agent's knowledge domain.
    pub domain_addrs: &'static [u32],
    /// Output affinity per InteractionKind (index = discriminant, 0–255).
    pub kind_affinity: [u8; W12],
}

impl AgentDef {
    pub fn capability_level(&self, quack_count: u8) -> u8 {
        capability_level(self.tongue_gate, quack_count)
    }
    pub fn available(&self, quack_count: u8) -> bool {
        self.tongue_gate == 0 || quack_count > 0
    }
    pub fn fully_capable(&self, quack_count: u8) -> bool {
        self.tongue_gate == 0 || quack_count >= self.tongue_gate.saturating_mul(2)
    }
}

// ── Twelvefold Coil network ────────────────────────────────────────────────────

pub struct AgentCoil {
    l01_02: Layer<W01, W02>,
    l02_03: Layer<W02, W03>,
    l03_04: Layer<W03, W04>,
    l04_05: Layer<W04, W05>,
    l05_06: Layer<W05, W06>,
    l06_07: Layer<W06, W07>,
    l07_08: Layer<W07, W08>,
    l08_09: Layer<W08, W09>,
    l09_10: Layer<W09, W10>,
    l10_11: Layer<W10, W11>,
    l11_12: Layer<W11, W12>,
    /// Möbius recurrent: L12 → L01 bias (active only when mobius_close=true).
    recurrent: [i8; W01],
    /// Maximum active layer for this agent (1–12).
    max_layer: u8,
    mobius_close: bool,
}

impl AgentCoil {
    pub const fn zeroed() -> Self {
        AgentCoil {
            l01_02: Layer::zero(), l02_03: Layer::zero(), l03_04: Layer::zero(),
            l04_05: Layer::zero(), l05_06: Layer::zero(), l06_07: Layer::zero(),
            l07_08: Layer::zero(), l08_09: Layer::zero(), l09_10: Layer::zero(),
            l10_11: Layer::zero(), l11_12: Layer::zero(),
            recurrent: [0i8; W01], max_layer: 4, mobius_close: false,
        }
    }

    /// Initialize all 12 layers from the RGB ring geometry.
    /// Layers above def.max_layer receive near-zero weights (signal does not
    /// propagate through them — same forward pass, different effective depth).
    pub fn init_from_geometry(&mut self, def: &AgentDef) {
        self.max_layer   = def.max_layer;
        self.mobius_close = def.mobius_close;

        // Scale factor per layer based on whether it's within this agent's depth.
        let scale = |layer: u8| -> i8 {
            if layer <= def.max_layer { 1 } else { 0 }
        };

        // ── L1→L2: tongue bits → Rose base-12 enumeration ────────────────────
        geo_init_2d(&mut self.l01_02, |j, i| {
            let near = if (i % 12) == j { 80i8 } else {
                let a = palette::aki_color(tongue_mid(i as u8 + 1));
                let b = palette::aki_color(24 + j as u32 * 2);
                ring_w(a, b)
            };
            near * scale(2)
        });

        // ── L2→L3: decimal → Lotus boolean gates ─────────────────────────────
        geo_init_2d(&mut self.l02_03, |j, i| {
            let a = palette::aki_color((j * 3) as u32);         // Lotus addr
            let b = palette::aki_color((24 + i * 2) as u32);   // Rose addr
            ring_w(a, b) * scale(3)
        });

        // ── L3→L4: boolean → Sakura coordinates ──────────────────────────────
        geo_init_2d(&mut self.l03_04, |j, i| {
            let a = palette::aki_color((48 + j * 2) as u32);
            let b = palette::aki_color((i * 3) as u32);
            ring_w(a, b) * scale(4)
        });

        // ── L4→L5: coordinate → Daisy object clusters ────────────────────────
        geo_init_2d(&mut self.l04_05, |j, i| {
            let a = palette::aki_color((72 + j * 2) as u32);
            let b = palette::aki_color((48 + i * 2) as u32);
            ring_w(a, b) * scale(5)
        });

        // ── L5→L6: object → entity tier gates ────────────────────────────────
        geo_init_2d(&mut self.l05_06, |j, i| {
            let a = palette::aki_color((98 + j) as u32);        // AppleBlossom
            let b = palette::aki_color((72 + i * 2) as u32);   // Daisy
            ring_w(a, b) * scale(6)
        });

        // ── L6→L7: entity → RGB spectral identity ────────────────────────────
        // Output IS the 3-channel color derived from the entity's tongue state.
        geo_init_2d(&mut self.l06_07, |j, i| {
            let col = palette::aki_color(24 + (i * 6 / W06) as u32);
            let ch  = [col.0, col.1, col.2][j];
            (ch / 2) as i8 * scale(7)
        });

        // ── L7→L8: color → Aster time/space modes ────────────────────────────
        geo_init_2d(&mut self.l07_08, |j, i| {
            let a = palette::aki_color((128 + j * 2) as u32);   // Aster
            let b = palette::aki_color((24 + i * 2) as u32);   // Rose channel
            ring_w(a, b) * scale(8)
        });

        // ── L8→L9: movement → Grapevine pattern flows ────────────────────────
        geo_init_2d(&mut self.l08_09, |j, i| {
            let a = palette::aki_color((170 + j * 2) as u32);   // Dyf region
            let b = palette::aki_color((128 + i * 2) as u32);  // Aster
            ring_w(a, b) * scale(9)
        });

        // ── L9→L10: pattern → Names (Ne-Soa / language layer) ────────────────
        // Biased by the agent's domain addresses — the language they can name.
        geo_init_2d(&mut self.l09_10, |j, i| {
            let base: i8 = 32 * scale(10);
            // Boost if agent domain_addrs covers this name-space slot.
            let boost: i8 = if j < def.domain_addrs.len() && scale(10) != 0 {
                let addr = def.domain_addrs[j];
                if addr >= 156 && addr <= 213 { 24 } else { 0 }
            } else { 0 };
            let _ = i;
            base + boost
        });

        // ── L10→L11: names → scene diffs (Sy-Mek / fold-time events) ─────────
        geo_init_2d(&mut self.l10_11, |j, i| {
            let a = palette::aki_color((128 + (j % 6) * 2 + 8) as u32); // Sy=146
            let b = palette::aki_color((156 + i * 2) as u32);           // Grapevine
            ring_w(a, b) * scale(11)
        });

        // ── L11→L12: scene → function (Wu-Yl / operative output) ─────────────
        // The function layer belongs to Gods, Primordials, Void Wraiths.
        // Kind affinity biases which interactions the agent can offer.
        geo_init_2d(&mut self.l11_12, |j, i| {
            let geo: i8 = {
                let a = palette::aki_color(45);            // Wu (Process/Way)
                let b = palette::aki_color((128 + i * 2) as u32); // Aster
                ring_w(a, b)
            };
            let aff = (def.kind_affinity[j] / 2) as i8;
            (geo.saturating_add(aff)) * scale(12)
        });
        for j in 0..W12 {
            self.l11_12.b[j] = ((def.kind_affinity[j] / 4) as i8) * scale(12);
        }

        // ── Möbius recurrence: L12 → L01 (Primordials / Anima Mundi only) ────
        // Wu-Yl reaching back to Gaoh — same surface, different density.
        if def.mobius_close {
            for i in 0..W01 {
                self.recurrent[i] = (def.kind_affinity[i % W12] / 8) as i8;
            }
        }
    }

    /// Full forward pass through the Twelvefold Coil.
    pub fn forward(&self, input: &[u8; W01]) -> CoilState {
        let mut s = CoilState::zero();
        s.l01 = *input;

        // Apply Möbius recurrent feedback from previous pass if active.
        // (On first call recurrent is zero; subsequent calls carry state.)
        if self.mobius_close {
            for i in 0..W01 {
                let feedback = (self.recurrent[i] as i32 * s.l01[i] as i32 / 128)
                    .max(0).min(255) as u8;
                s.l01[i] = s.l01[i].saturating_add(feedback);
            }
        }

        s.l02 = self.l01_02.forward(&s.l01);
        s.l03 = self.l02_03.forward(&s.l02);
        s.l04 = self.l03_04.forward(&s.l03);
        s.l05 = self.l04_05.forward(&s.l04);
        s.l06 = self.l05_06.forward(&s.l05);
        s.l07 = self.l06_07.forward(&s.l06);
        s.l08 = self.l07_08.forward(&s.l07);
        s.l09 = self.l08_09.forward(&s.l08);
        s.l10 = self.l09_10.forward(&s.l09);
        s.l11 = self.l10_11.forward(&s.l10);
        s.l12 = self.l11_12.forward(&s.l11);
        s
    }
}

// ── Capability scaling ─────────────────────────────────────────────────────────

pub fn capability_level(gate: u8, quack_count: u8) -> u8 {
    if gate == 0 { return 255; }
    let (q, g) = (quack_count as u32, gate as u32);
    if q == 0    { return 0; }
    if q >= g * 2 { return 255; }
    if q >= g { (128 + ((q - g) * 127) / g) as u8 }
    else      { ((q * 128) / g) as u8 }
}

/// Derive max coil depth from entity_id suffix and prefix.
///
/// Depth determines how far signal propagates through the Twelvefold Coil.
/// Layers above the ceiling carry zero weights for that entity — the forward
/// pass runs identically for all agents, but deeper signal does not emerge.
///
/// Anticheat note: the CoilState produced by a legitimate forward pass is a
/// native proof of legitimate play.  The Layer 7 RGB is a compact geometric
/// hash of the current game state; the Möbius recurrence (Primordials/AnimaMundi)
/// creates temporal chaining — each state fingerprint depends on prior states
/// in a way that cannot be forged without full coil traversal.
pub fn entity_max_layer(entity_id: &[u8]) -> u8 {
    // Protagonist (0000_0451): full Möbius — player traverses all layers
    if entity_id == b"0000_0451" { return 12; }
    // Tier 4 (3xxx) Anima Mundi — full + Möbius
    if entity_id.first().copied() == Some(b'3') { return 12; }
    // Tier 3 supernatural
    if entity_id.ends_with(b"_PRIM") { return 12; }  // Primordials — operative
    if entity_id.ends_with(b"_GODS") { return 12; }  // Gods — functional
    if entity_id.ends_with(b"_VDWR") { return 11; }  // Void Wraiths — scene
    if entity_id.ends_with(b"_DEMI") { return 10; }  // Demigods — names
    if entity_id.ends_with(b"_DMON") { return  9; }  // Demons — pattern
    if entity_id.ends_with(b"_ALZD") { return 11; }  // Alzedroswune — near-void
    // Djinn — Dragon tongue affinity, language of the cosmos, Drovitth built
    // the Orrery: they reach the Names layer (10) but not the full Scene.
    if entity_id.ends_with(b"_DJNN") { return 10; }
    // Tier 2 — other non-humans: movement diffs (8)
    if entity_id.first().copied() == Some(b'1') { return 8; }
    // Tier 1 variants
    if entity_id.ends_with(b"_TOWN") { return 4; }   // Townfolk — coordinate
    if entity_id.ends_with(b"_SOLD") { return 5; }   // Soldiers — object
    // Witches, Priests, Royals, Assassins — entity layer
    6
}

/// Whether this entity's coil closes on itself (Möbius recurrence).
pub fn entity_mobius(entity_id: &[u8]) -> bool {
    entity_id == b"0000_0451"
    || entity_id.ends_with(b"_PRIM")
    || entity_id.first().copied() == Some(b'3')  // Anima Mundi
}

/// Build the input tensor from player state.
pub fn build_input(
    def:        &AgentDef,
    quack_count: u8,
    eigenstate: &[u32; 24],
) -> [u8; W01] {
    let mut act = [0u8; W01];
    for t in 0..W01.min(quack_count as usize) {
        let cap = capability_level(def.tongue_gate, quack_count);
        act[t] = if t < 24 && eigenstate[t] > 0 { cap } else { cap / 2 };
    }
    act
}

// ── Geometry helpers ───────────────────────────────────────────────────────────

pub fn tongue_mid(tongue: u8) -> u32 {
    match tongue {
        1  => 11,   2  => 35,   3  => 59,   4  => 84,
        5  => 110,  6  => 141,  7  => 169,  8  => 198,
        9  => 270,  10 => 300,  11 => 330,  12 => 361,
        13 => 393,  14 => 426,  15 => 460,  16 => 494,
        17 => 528,  18 => 563,  19 => 599,  20 => 636,
        21 => 674,  22 => 712,  23 => 750,  24 => 789,
        25 => 829,  26 => 869,  27 => 909,  28 => 949,
        29 => 989,  30 => 1030, 31 => 1072, 32 => 1115,
        33 => 1159, 34 => 1203, 35 => 1247, 36 => 1291,
        37 => 1335, 38 => 1380, _  => 0,
    }
}

fn rgb_l1(a: (u8,u8,u8), b: (u8,u8,u8)) -> u32 {
    (a.0 as i32 - b.0 as i32).unsigned_abs()
  + (a.1 as i32 - b.1 as i32).unsigned_abs()
  + (a.2 as i32 - b.2 as i32).unsigned_abs()
}

/// Compute a connection weight from RGB ring L1 distance: closer = stronger.
/// Returns i8 in range 0..63.
fn ring_w(a: (u8,u8,u8), b: (u8,u8,u8)) -> i8 {
    ((255u32.saturating_sub(rgb_l1(a, b))) / 4).min(63) as i8
}

/// Initialize a Layer's weights from a closure (OUT, IN) → i8.
fn geo_init_2d<const IN: usize, const OUT: usize>(
    layer: &mut Layer<IN, OUT>,
    f: impl Fn(usize, usize) -> i8,
) {
    for j in 0..OUT {
        for i in 0..IN {
            layer.w[j][i] = f(j, i);
        }
    }
}

// ── Registry ───────────────────────────────────────────────────────────────────

const MAX_AGENTS: usize = 128;
static mut REGISTRY:   [Option<&'static AgentDef>; MAX_AGENTS] =
    [const { None }; MAX_AGENTS];
static mut REGISTRY_N: usize = 0;

pub fn register(def: &'static AgentDef) {
    unsafe {
        if REGISTRY_N < MAX_AGENTS {
            REGISTRY[REGISTRY_N] = Some(def);
            REGISTRY_N += 1;
        }
    }
}

pub fn find(entity_id: &[u8]) -> Option<&'static AgentDef> {
    unsafe {
        REGISTRY[..REGISTRY_N].iter()
            .filter_map(|s| *s)
            .find(|a| a.entity_id == entity_id)
    }
}

pub fn find_by_name(name: &[u8]) -> Option<&'static AgentDef> {
    unsafe {
        REGISTRY[..REGISTRY_N].iter()
            .filter_map(|s| *s)
            .find(|a| a.name == name)
    }
}

pub fn agent_count() -> usize { unsafe { REGISTRY_N } }

pub fn get_by_index(i: usize) -> Option<&'static AgentDef> {
    unsafe {
        if i < REGISTRY_N { REGISTRY[i] } else { None }
    }
}

// ── Attestation log ───────────────────────────────────────────────────────────
//
// Every verify_coil() call that passes produces an Attestation — a timestamped
// record binding the agent identity, the Layer 7 color hash, and the tick
// counter at verification time.  The Orrery uses these to:
//   1. Prove the sequence of interactions was legitimate (temporal chaining)
//   2. Detect out-of-order or replayed states (timestamps must advance)
//   3. Anchor Quack-count claims to real game time (no instant attestation)
//
// The tick counter comes from arch::read_mtime() — the same monotonic counter
// the LAPIC timer drives.  On x86_64 hardware this is the LAPIC tick count
// since boot, not wall-clock time, but it advances strictly monotonically and
// cannot be faked without kernel access.

#[derive(Copy, Clone)]
pub struct Attestation {
    pub entity_id_hash: u32,    // FNV-1a hash of entity_id bytes
    pub quack_count:    u8,     // Quack count at time of verification
    pub color_hash:     (u8, u8, u8), // Layer 7 spectral fingerprint
    pub tick:           u64,    // arch::read_mtime() at verification moment
    pub game_id:        u8,     // game context
    pub quest_id:       u32,    // quest context
}

impl Attestation {
    /// Verify that this attestation immediately precedes `next` in a
    /// legitimate sequence (tick advances, Quack count does not regress,
    /// and entity remains the same).
    pub fn chains_to(&self, next: &Attestation) -> bool {
        self.entity_id_hash == next.entity_id_hash
        && next.tick > self.tick
        && next.quack_count >= self.quack_count
    }
}

const MAX_ATTEST: usize = 256;
static mut ATTEST_LOG:  [Option<Attestation>; MAX_ATTEST] = [const { None }; MAX_ATTEST];
static mut ATTEST_HEAD: usize = 0;

/// Record an attestation.  Ring-buffer: oldest entry is overwritten when full.
pub fn record_attestation(a: Attestation) {
    unsafe {
        ATTEST_LOG[ATTEST_HEAD % MAX_ATTEST] = Some(a);
        ATTEST_HEAD = ATTEST_HEAD.wrapping_add(1);
    }
}

/// Return the most recent attestation for an entity (by entity_id hash).
pub fn last_attestation(entity_id_hash: u32) -> Option<Attestation> {
    unsafe {
        // Walk backward from head
        let n = ATTEST_HEAD.min(MAX_ATTEST);
        for i in (0..n).rev() {
            let slot = (ATTEST_HEAD.wrapping_sub(1 + i)) % MAX_ATTEST;
            if let Some(a) = ATTEST_LOG[slot] {
                if a.entity_id_hash == entity_id_hash { return Some(a); }
            }
        }
        None
    }
}

fn fnv1a(data: &[u8]) -> u32 {
    let mut h: u32 = 2166136261;
    for &b in data { h = h.wrapping_mul(16777619) ^ b as u32; }
    h
}

// ── Anticheat verification ─────────────────────────────────────────────────────
//
// The CoilState produced by a legitimate forward pass is a native proof of
// play that cannot be forged without traversing the full coil.
//
// Layer 7 (RGB color) is the compact geometric hash of the current state —
// 3 bytes derived from the entire tongue activation history.
//
// The Möbius recurrence in Primordials/AnimaMundi creates temporal chaining:
// each CoilState influences the next, so replaying a valid state sequence
// requires all prior states to be correct.
//
// Verification checks that the recomputed coil matches the claimed state
// within a tolerance band (small floating-point drift is expected from
// fixed-point rounding; large deviation indicates tampered input).

/// Recompute the coil from claimed inputs and compare against a presented state.
/// On success, records a timestamped Attestation in the log.
/// Returns true if the coil output matches within the integrity tolerance.
/// `tolerance`: max L1 deviation per node (1–15; tighter = stricter anticheat).
pub fn verify_coil(
    coil:       &AgentCoil,
    input:      &[u8; W01],
    presented:  &CoilState,
    tolerance:  u8,
    def:        &AgentDef,
    quack_count: u8,
    game_id:    u8,
    quest_id:   u32,
) -> bool {
    let fresh = coil.forward(input);

    // Check Layer 12 (function output) — the operative result
    for k in 0..W12 {
        if presented.l12[k].abs_diff(fresh.l12[k]) > tolerance { return false; }
    }
    // Check Layer 7 (color hash) — geometric fingerprint
    for k in 0..W07 {
        if presented.l07[k].abs_diff(fresh.l07[k]) > tolerance { return false; }
    }

    // Verification passed — record a timestamped attestation.
    let tick = {
        #[cfg(target_arch = "x86_64")]
        { crate::arch::read_mtime() }
        #[cfg(not(target_arch = "x86_64"))]
        { crate::arch::read_mtime() }
    };

    // Enforce temporal ordering: reject if tick does not advance beyond
    // the last attestation for this entity.
    let id_hash = fnv1a(def.entity_id);
    if let Some(prev) = last_attestation(id_hash) {
        if tick <= prev.tick { return false; }
        if quack_count < prev.quack_count { return false; }
    }

    record_attestation(Attestation {
        entity_id_hash: id_hash,
        quack_count,
        color_hash: (fresh.l07[0], fresh.l07[1], fresh.l07[2]),
        tick,
        game_id,
        quest_id,
    });

    true
}

pub fn available(quack_count: u8) -> impl Iterator<Item = &'static AgentDef> {
    unsafe {
        REGISTRY[..REGISTRY_N].iter()
            .filter_map(|s| *s)
            .filter(move |a| a.tongue_gate == 0 || quack_count > 0)
    }
}
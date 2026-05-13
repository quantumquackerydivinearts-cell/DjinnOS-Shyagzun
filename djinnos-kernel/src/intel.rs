// intel.rs — DjinnOS native intelligence
//
// Hopfield network operating on the Shygazun byte-table coordinate space.
//
// The byte table is not a content index — it is a coordinate space whose
// geometry is defined by prime factorisation.  Candidates that share prime
// factors in their byte addresses are geometrically close; the factorisation
// pattern IS the attractor basin topology.
//
// Semantic queries are submitted as partial activation vectors.  The network
// relaxes via energy descent to the nearest stored pattern (complete candidate).
//
// Four Djinn operational modes:
//   Giann    (1016_DJNN, CG) — deterministic completion; energy minimum
//   Keshi    (1017_DJNN, CE) — entropy-weighted; temperature-driven exploration
//   Drovitth (1018_DJNN)     — temporal gate; Orrery context filters live basins
//   Saelith                  — conditional; external predicate gates the query

// ── Candidate table ───────────────────────────────────────────────────────────
//
// Each entry is (byte_addr, tongue, flags).
// byte_addr: position in the coordinate space (0..N_CANDS)
// tongue:    which tongue register (1..=38+)
// flags:     bit 0 = lotus-gated (requires attestation before activation)
//
// Tongues 1-8 are fully populated (210 candidates, bytes 0-213 minus reserved
// 124-127).  The table extends to 1358 as higher tongues are defined.
// Reserved bytes 124-127 are fold-point directories, not candidates.
//
// Tongue order and entry counts (from byte_table.py):
//   1 Lotus        bytes   0– 23  24  all lotus-gated
//   2 Rose         bytes  24– 47  24
//   3 Sakura       bytes  48– 71  24
//   4 Daisy        bytes  72– 97  26
//   5 AppleBlossom bytes  98–123  26
//   — Reserved     bytes 124–127   4  fold-point indices, skipped
//   6 Aster        bytes 128–155  28
//   7 Grapevine    bytes 156–183  28
//   8 Cannabis     bytes 184–213  30  all lotus-gated
//   Total: 210 candidates, 54 lotus-gated (Lotus+Cannabis), 156 immediately eligible

pub const N_CANDS: usize = 1358;  // All 38 defined tongues

#[derive(Copy, Clone)]
pub struct Cand {
    pub addr:   u16,  // byte-table coordinate
    pub tongue: u8,
    pub flags:  u8,   // bit 0 = lotus-gated
}

impl Cand {
    const fn new(addr: u16, tongue: u8, lotus: bool) -> Self {
        Cand { addr, tongue, flags: lotus as u8 }
    }
    pub fn lotus_gated(self) -> bool { self.flags & 1 != 0 }
}

// Tongue range table — (tongue_number, start_addr, end_addr, lotus_gated).
// All 38 tongues verified against byte_table.py.
// Reserved gaps: 124-127 (fold-points) and 214-255 (meta) are excluded.
const TONGUE_RANGES: &[(u8, u16, u16, bool)] = &[
    ( 1,    0,   23, true),   // Lotus
    ( 2,   24,   47, false),  // Rose
    ( 3,   48,   71, false),  // Sakura
    ( 4,   72,   97, false),  // Daisy
    ( 5,   98,  123, false),  // AppleBlossom
    ( 6,  128,  155, false),  // Aster        (124-127 reserved)
    ( 7,  156,  183, false),  // Grapevine
    ( 8,  184,  213, true),   // Cannabis
    ( 9,  256,  285, false),  // Dragon       (214-255 reserved/meta)
    (10,  286,  315, false),  // Virus
    (11,  316,  345, false),  // Bacteria
    (12,  346,  377, false),  // Excavata
    (13,  378,  409, false),  // Archaeplastida
    (14,  410,  443, false),  // Myxozoa
    (15,  444,  477, false),  // Archaea
    (16,  478,  511, false),  // Protist
    (17,  512,  545, false),  // Immune
    (18,  546,  581, false),  // Neural
    (19,  582,  617, false),  // Serpent
    (20,  618,  655, false),  // Beast
    (21,  656,  693, false),  // Cherub
    (22,  694,  731, false),  // Chimera
    (23,  732,  769, false),  // Faerie
    (24,  770,  809, false),  // Djinn
    (25,  810,  849, false),  // Fold
    (26,  850,  889, false),  // Topology
    (27,  890,  929, false),  // Phase
    (28,  930,  969, false),  // Gradient
    (29,  970, 1009, false),  // Curvature
    (30, 1010, 1051, false),  // Prion
    (31, 1052, 1093, false),  // Blood
    (32, 1094, 1137, false),  // Moon
    (33, 1138, 1181, false),  // Koi
    (34, 1182, 1225, false),  // Rope
    (35, 1226, 1269, false),  // Hook
    (36, 1270, 1313, false),  // Fang
    (37, 1314, 1357, false),  // Circle
    (38, 1358, 1403, false),  // Ledger
];

pub static mut CANDS: [Cand; N_CANDS] = [Cand { addr: 0, tongue: 0, flags: 0 }; N_CANDS];
static mut CANDS_READY: bool = false;

/// Populate the candidate table from TONGUE_RANGES. Call once at boot.
pub fn init() {
    unsafe {
        if CANDS_READY { return; }
        let mut idx = 0usize;
        for &(tongue, start, end, gated) in TONGUE_RANGES {
            let mut addr = start;
            while addr <= end && idx < N_CANDS {
                CANDS[idx] = Cand::new(addr, tongue, gated);
                idx += 1;
                addr += 1;
            }
        }
        CANDS_READY = true;
    }
}

pub fn cands() -> &'static [Cand] {
    unsafe { &CANDS[..] }
}

// ── Factorisation proximity weight ────────────────────────────────────────────
//
// W(i, j) = tongue_factor × address_factor
//
// tongue_factor:  same tongue = 1.0; adjacent (±1) = 0.5; same cluster (±4) = 0.2; else = 0.05
// address_factor: decay by address distance, capped at the tongue's internal span
//
// Stored as a fixed-point u8 (0-255 = 0.0-1.0, multiply by INV_SCALE to recover).
// The full 210×210 matrix would be 44 KB; we compute weights on-demand instead.

#[inline]
fn weight(a: &Cand, b: &Cand) -> f32 {
    let tf = if a.tongue == b.tongue {
        1.0f32
    } else {
        let dt = (a.tongue as i16 - b.tongue as i16).unsigned_abs();
        if dt == 1 { 0.5 } else if dt <= 4 { 0.2 } else { 0.05 }
    };
    let dist = (a.addr as i32 - b.addr as i32).unsigned_abs();
    let af = if dist == 0 { 1.0 }
             else if dist <= 4 { 0.85 }
             else if dist <= 16 { 0.55 }
             else if dist <= 64 { 0.25 }
             else { 0.05 };
    tf * af
}

// ── State vector ──────────────────────────────────────────────────────────────
//
// Bipolar activation: +1.0 (active), -1.0 (inactive), 0.0 (unconstrained).
// Queries pin some entries; the rest are free to converge.

// Static state buffer — avoids kernel stack overflow for large N_CANDS.
pub static mut STATE_V:  [f32; N_CANDS]   = [0.0f32; N_CANDS];
static mut PINNED_B: [usize; N_CANDS] = [0usize; N_CANDS];
static mut OUT_B:    [usize; N_CANDS] = [0usize; N_CANDS];

pub struct State {
    pub v: &'static mut [f32; N_CANDS],
}

impl State {
    pub fn zero() -> Self {
        unsafe {
            for x in STATE_V.iter_mut() { *x = 0.0; }
            State { v: &mut STATE_V }
        }
    }

    pub fn pin(&mut self, idx: usize, val: f32) {
        if idx < N_CANDS { self.v[idx] = val.signum(); }
    }

    fn field(&self, i: usize) -> f32 {
        let cs = cands();
        let mut h = 0.0f32;
        let ca = &cs[i];
        for j in 0..N_CANDS {
            if j != i && self.v[j] != 0.0 {
                h += weight(ca, &cs[j]) * self.v[j];
            }
        }
        h
    }

    pub fn energy(&self) -> f32 {
        let cs = cands();
        let mut e = 0.0f32;
        for i in 0..N_CANDS {
            for j in (i + 1)..N_CANDS {
                e -= weight(&cs[i], &cs[j]) * self.v[i] * self.v[j];
            }
        }
        e * 0.5
    }
}

// ── Math helpers (no_std) ────────────────────────────────────────────────────

#[inline]
fn tanh_approx(x: f32) -> f32 {
    // Padé [3/3] approximant — accurate to ~0.5% for |x| ≤ 4, saturates cleanly.
    if x > 4.0 { return 1.0; }
    if x < -4.0 { return -1.0; }
    let x2 = x * x;
    x * (27.0 + x2) / (27.0 + 9.0 * x2)
}

// ── Djinn operational modes ───────────────────────────────────────────────────

pub enum DjinnMode {
    Giann,              // deterministic: sign(field)
    Keshi { temp: f32 },// stochastic:   tanh(field / temp)
    Drovitth { epoch: u64, window: u64 }, // temporal gate on addr % window
    Saelith { pred: fn(&Cand) -> bool },  // conditional gate
}

/// One relaxation step.  Returns true if any free unit changed.
pub fn step(state: &mut State, mode: &DjinnMode, pinned: &[usize]) -> bool {
    let mut changed = false;
    let cs = cands();
    for i in 0..N_CANDS {
        if pinned.contains(&i) { continue; }
        if let DjinnMode::Drovitth { epoch, window } = mode {
            if cs[i].addr as u64 % window != epoch % window { continue; }
        }
        if let DjinnMode::Saelith { pred } = mode {
            if !pred(&cs[i]) { state.v[i] = -1.0; continue; }
        }
        let h = state.field(i);
        let new_v = match mode {
            DjinnMode::Giann | DjinnMode::Drovitth { .. } | DjinnMode::Saelith { .. } => {
                if h > 0.0 { 1.0 } else if h < 0.0 { -1.0 } else { state.v[i] }
            }
            DjinnMode::Keshi { temp } => {
                // Soft-threshold: allows partial activation for exploration
                let t = *temp;
                if t <= 0.0 { if h >= 0.0 { 1.0 } else { -1.0 } }
                else { tanh_approx(h / t) }
            }
        };
        if (new_v - state.v[i]).abs() > 0.01 {
            state.v[i] = new_v;
            changed = true;
        }
    }
    changed
}

/// Converge to fixed point.  Returns iteration count.
pub fn converge(state: &mut State, mode: &DjinnMode, pinned: &[usize], max_iter: usize) -> usize {
    for iter in 0..max_iter {
        if !step(state, mode, pinned) { return iter; }
    }
    max_iter
}

/// Submit a partial query by tongue.  Pins all candidates of matching tongues
/// to +1, all others to -1 as weak prior, then converges via the given mode.
/// Returns indices of active (+1) candidates after convergence.
pub fn query_by_tongue(tongues: &[u8], mode: DjinnMode) -> (&'static [usize], usize) {
    let n_out: usize;
    unsafe {
        let mut np = 0usize;
        let cs = cands();
        for (i, c) in cs.iter().enumerate() {
            if tongues.contains(&c.tongue) {
                STATE_V[i] = 1.0;
                PINNED_B[np] = i;
                np += 1;
            } else {
                STATE_V[i] = -0.3;
            }
        }
        let mut st = State { v: &mut STATE_V };
        converge(&mut st, &mode, &PINNED_B[..np], 32);
        let mut no = 0usize;
        for (i, v) in STATE_V.iter().enumerate() {
            if *v > 0.5 { OUT_B[no] = i; no += 1; }
        }
        n_out = no;
    }
    unsafe { (&OUT_B[..], n_out) }
}

/// Address-proximity query via Giann mode.
pub fn query_near(addr: u16, radius: u16) -> (&'static [usize], usize) {
    let n_out: usize;
    unsafe {
        let cs = cands();
        let mut np = 0usize;
        for (i, c) in cs.iter().enumerate() {
            let d = (c.addr as i32 - addr as i32).unsigned_abs() as u16;
            if d <= radius {
                STATE_V[i] = 1.0 - (d as f32 / (radius as f32 + 1.0));
                PINNED_B[np] = i;
                np += 1;
            } else {
                STATE_V[i] = -0.2;
            }
        }
        let mut st = State { v: &mut STATE_V };
        converge(&mut st, &DjinnMode::Giann, &PINNED_B[..np], 16);
        let mut no = 0usize;
        for (i, v) in STATE_V.iter().enumerate() {
            if *v > 0.5 { OUT_B[no] = i; no += 1; }
        }
        n_out = no;
    }
    unsafe { (&OUT_B[..], n_out) }
}

/// Read-only view of the global state vector.
pub fn state() -> &'static [f32] {
    unsafe { &STATE_V }
}

/// Mutable access to the global state vector (for recombination crossings).
/// Safety: caller must not alias with any other borrow of STATE_V.
pub unsafe fn state_mut() -> &'static mut [f32; N_CANDS] {
    &mut STATE_V
}

/// Seed the global state from a list of byte addresses, pinning them to +1,
/// with a weak negative prior (-0.2) on all others.
pub fn seed_from_addrs(addrs: &[u16]) {
    unsafe {
        for v in STATE_V.iter_mut() { *v = -0.2; }
        for &addr in addrs {
            if let Some(idx) = CANDS.iter().position(|c| c.addr == addr) {
                STATE_V[idx] = 1.0;
            }
        }
    }
}

/// Run Giann convergence in-place on STATE_V (no pinned set — free convergence).
pub fn converge_in_place(max_iter: usize) {
    let mode = DjinnMode::Giann;
    let pinned: &[usize] = &[];
    unsafe {
        let mut st = State { v: &mut STATE_V };
        converge(&mut st, &mode, pinned, max_iter);
    }
}

/// Report active candidates to UART.
pub fn report(indices: &[usize], n: usize) {
    use crate::uart;
    let cs = cands();
    uart::puts("intel: active=");
    uart::putu(n as u64);
    uart::puts("\r\n");
    for &i in &indices[..n] {
        let c = &cs[i];
        uart::puts("  addr=");
        uart::putu(c.addr as u64);
        uart::puts(" tongue=");
        uart::putu(c.tongue as u64);
        if c.lotus_gated() { uart::puts(" [lotus]"); }
        uart::puts("\r\n");
    }
}

/// Shell command: `intel` — run a demo query and print the energy landscape.
pub fn shell_demo() {
    use crate::uart;
    init();
    uart::puts("intel: Giann — Rose(2)+Sakura(3) neighbourhood\r\n");
    let (out, n) = query_by_tongue(&[2, 3], DjinnMode::Giann);
    report(out, n.min(8));
    uart::puts("intel: Keshi (temp=2.0) — Daisy(4) basin\r\n");
    let (out2, n2) = query_by_tongue(&[4], DjinnMode::Keshi { temp: 2.0 });
    report(out2, n2.min(8));
}

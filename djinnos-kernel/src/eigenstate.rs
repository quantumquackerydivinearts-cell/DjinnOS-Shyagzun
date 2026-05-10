// Eigenstate tracker — per-tongue invocation counters.
//
// Each Shygazun tongue has a 64-bit counter that advances every time the
// kernel dispatches an ecall whose byte address belongs to that tongue.
// The byte table is therefore a living register: its state encodes the
// cumulative invocation history of the running system.
//
// Tongue indices map directly to the Tongue discriminant (0 unused; 1=Lotus
// through 37=Circle). Array slots 38–127 reserved for future tongues.
//
// Usage:
//   eigenstate::advance(tongue_number)   — called from trap dispatcher
//   eigenstate::read(tongue_number)      — readable from shell / user ecall
//   eigenstate::snapshot()               — copy of all 128 counters

use core::sync::atomic::{AtomicU64, Ordering};

const SLOTS: usize = 128;

static COUNTS: [AtomicU64; SLOTS] = {
    // FIXME: const-init once Rust stabilises const AtomicU64::new in arrays
    // For now, initialise via an explicit const-init macro workaround.
    macro_rules! z { () => { AtomicU64::new(0) }; }
    [
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //   0–  7
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //   8– 15
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  16– 23
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  24– 31
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  32– 39
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  40– 47
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  48– 55
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  56– 63
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  64– 71
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  72– 79
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  80– 87
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  88– 95
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  //  96–103
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  // 104–111
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  // 112–119
        z!(), z!(), z!(), z!(), z!(), z!(), z!(), z!(),  // 120–127
    ]
};

/// Advance the counter for `tongue` by 1 (called on every matching ecall).
#[inline]
pub fn advance(tongue: u8) {
    if (tongue as usize) < SLOTS {
        COUNTS[tongue as usize].fetch_add(1, Ordering::Relaxed);
    }
}

/// Read the current counter for `tongue`.
#[inline]
pub fn read(tongue: u8) -> u64 {
    if (tongue as usize) < SLOTS {
        COUNTS[tongue as usize].load(Ordering::Relaxed)
    } else {
        0
    }
}

/// Return the total invocations across all tongues.
pub fn total() -> u64 {
    COUNTS.iter().fold(0u64, |acc, c| acc.wrapping_add(c.load(Ordering::Relaxed)))
}

/// Copy the first `out.len()` counters into `out`.
pub fn snapshot(out: &mut [u64]) {
    for (i, slot) in out.iter_mut().enumerate() {
        *slot = if i < SLOTS { COUNTS[i].load(Ordering::Relaxed) } else { 0 };
    }
}

/// Return the tongue number (1-based) with the highest count.
/// Returns 1 (Lotus) if all counts are zero.
pub fn dominant() -> u8 {
    let mut best_t = 1u8;
    let mut best_v = 0u64;
    for i in 1..SLOTS {
        let v = COUNTS[i].load(Ordering::Relaxed);
        if v > best_v { best_v = v; best_t = i as u8; }
    }
    best_t
}

/// Normalised weight for tongue `t` (1-based) in range 0..=255.
/// 128 = average activity; higher = more active than average.
pub fn weight(t: u8) -> u8 {
    let tot = total();
    if tot == 0 { return 128; }
    let count = read(t);
    // Normalise: expected share = tot / num_active_tongues
    // weight = clamp(count * 255 / expected, 0, 255)
    let active = COUNTS[1..].iter().filter(|c| c.load(Ordering::Relaxed) > 0).count().max(1);
    let expected = (tot / active as u64).max(1);
    ((count * 255 / expected).min(255)) as u8
}

/// Tongue numbers for the system's first-cluster activities.
/// Used by main.rs to advance the correct tongue on each action.
pub const T_LOTUS:      u8 =  1;  // input / presence
pub const T_ROSE:       u8 =  2;  // numbers / addressing
pub const T_SAKURA:     u8 =  3;  // spatial / render / cursor
pub const T_DAISY:      u8 =  4;  // structural / system
pub const T_ABLOSSOM:   u8 =  5;  // elemental / mode transition
pub const T_ASTER:      u8 =  6;  // temporal / scheduling
pub const T_GRAPEVINE:  u8 =  7;  // data / network / files
pub const T_CANNABIS:   u8 =  8;  // consciousness / perception / REPL

/// Advance the tongue that corresponds to the active AppMode.
pub fn advance_mode(mode_name: &str) {
    let t = match mode_name {
        "Ko"      => T_LOTUS,      // shell: presence
        "Soa"     => T_CANNABIS,   // REPL: conscious expression
        "Saoshin" => T_GRAPEVINE,  // file editor: Sao = cup/file
        "Samos"   => T_CANNABIS,   // byte ledger: chromatic perception
        "Faerie"  => T_GRAPEVINE,  // browser: network/data
        "To"      => T_SAKURA,     // voxel lab: spatial construction
        "Vrsei"   => T_SAKURA,     // model sculptor: spatial form
        "Av"      => T_CANNABIS,   // agent workshop: relational awareness
        "Mekha"   => T_GRAPEVINE,  // dialogue forge: herald/emit
        "DjinnOS" => T_LOTUS,      // login: presence
        _         => T_LOTUS,
    };
    advance(t);
}

/// Persist eigenstate counters to the Sa volume.
/// Called periodically so linguistic history survives reboots.
pub fn persist() {
    // Format: 8 bytes per slot (u64 LE) × 38 tongues = 304 bytes
    static mut BUF: [u8; 38 * 8] = [0u8; 38 * 8];
    unsafe {
        for i in 1..=38usize {
            let v = COUNTS[i].load(Ordering::Relaxed);
            BUF[(i-1)*8..(i-1)*8+8].copy_from_slice(&v.to_le_bytes());
        }
        crate::sa::write_file(b"eigenstate.esn", &BUF);
    }
}

/// Load eigenstate counters from the Sa volume (call at boot).
pub fn load() {
    static mut BUF: [u8; 38 * 8] = [0u8; 38 * 8];
    let n = crate::sa::read_file(b"eigenstate.esn", unsafe { &mut BUF });
    if n < 38 * 8 { return; }
    for i in 1..=38usize {
        let v = u64::from_le_bytes(unsafe { BUF[(i-1)*8..(i-1)*8+8].try_into().unwrap_or([0;8]) });
        COUNTS[i].store(v, Ordering::Relaxed);
    }
}

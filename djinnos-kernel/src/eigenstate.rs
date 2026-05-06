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

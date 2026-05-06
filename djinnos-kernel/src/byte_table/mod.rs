mod types;
mod table;

pub use types::{Address, ByteEntry, EntryKind, Tongue};
pub use table::BYTE_TABLE;

/// Look up an entry by byte address. O(log n) binary search over rodata.
pub fn lookup(addr: u32) -> Option<&'static ByteEntry> {
    let target = Address(addr);
    BYTE_TABLE
        .binary_search_by_key(&target, |e| e.address)
        .ok()
        .map(|i| &BYTE_TABLE[i])
}

/// Return the Tongue discriminant (1–37) for a byte address, or 0 if unknown.
/// Used by the eigenstate tracker to advance the right counter on ecall.
pub fn tongue_for_addr(addr: u32) -> u8 {
    lookup(addr).and_then(|e| e.tongue).map(|t| t as u8).unwrap_or(0)
}

/// Glyph string for a byte address, or empty string if unknown.
pub fn glyph_for_addr(addr: u32) -> &'static str {
    lookup(addr).and_then(|e| e.glyph).unwrap_or("")
}

/// Number of symbol-bearing entries (candidates).
pub fn symbol_count() -> usize {
    BYTE_TABLE.iter().filter(|e| e.kind == EntryKind::Symbol).count()
}

/// Number of entries for a given tongue.
pub fn tongue_count(tongue: Tongue) -> usize {
    BYTE_TABLE
        .iter()
        .filter(|e| e.tongue == Some(tongue))
        .count()
}

// ── Shygazun syscall ABI — canonical byte addresses ──────────────────────────
//
// The ecall register a7 holds a Shygazun byte address.
// The operation IS the meaning of that address in the byte table.
// Eigenstates advance automatically on every dispatch.

/// Lotus — Earth Initiator: spawn / initiate a new process.
/// a0 = ELF code pointer (VA), a1 = length → a0 = PID or u64::MAX on failure.
pub const SYS_TY:    u32 =   0;

/// Lotus — Earth Terminator: exit / empirical closure.
/// a0 = exit code → does not return.
pub const SYS_ZU:    u32 =   1;

/// Lotus — Water Initiator: read / feel / receive input.
/// a0 = fd, a1 = buf VA, a2 = max bytes → a0 = bytes read.
pub const SYS_LY:    u32 =   2;

/// Lotus — Air Initiator: think toward / cooperative yield.
/// No args → void.
pub const SYS_FY:    u32 =   4;

/// Lotus — Here / near presence: get current PID.
/// No args → a0 = PID.
pub const SYS_TI:    u32 =   8;

/// Lotus — Active being / presence: clone / fork.
/// a0 = flags → a0 = child PID (0 in child).
pub const SYS_TA:    u32 =   9;

/// Lotus — Absence / passive non-being: sleep for ticks.
/// a0 = tick count → void.
pub const SYS_ZO:    u32 =  16;

/// Lotus — Experience / intuition: wait for event (blocking).
/// a0 = event mask → a0 = event that fired.
pub const SYS_KO:    u32 =  19;

/// Daisy — Cluster / Fruit / Flower: heap alloc.
/// a0 = byte count → a0 = VA of new cluster, or 0 on failure.
pub const SYS_KAEL:  u32 =  82;

/// Daisy — Ion-channel / Gate / Receptor: open IPC gate.
/// a0 = channel ID → a0 = handle.
pub const SYS_RO:    u32 =  83;

/// Daisy — Switch / Circuit Actuator: send on IPC channel.
/// a0 = handle, a1 = data word → void.
pub const SYS_NZ:    u32 =  89;

/// Aster — Linear time: read monotonic tick counter.
/// No args → a0 = ticks since boot.
pub const SYS_SI:    u32 = 142;

/// Aster — Assign space: map virtual memory region.
/// a0 = VA hint, a1 = len, a2 = flags → a0 = mapped VA.
pub const SYS_EP:    u32 = 148;

/// Aster — Delete space: unmap virtual memory region.
/// a0 = VA, a1 = len → void.
pub const SYS_ENNO:  u32 = 153;

/// Grapevine — Feast table / root volume: query mounted volume.
/// No args → a0 = volume block count.
pub const SYS_SA:    u32 = 156;

/// Grapevine — Cup / file / persistent object: open a file.
/// a0 = name VA, a1 = name len → a0 = fd, or u64::MAX on failure.
pub const SYS_SAO:   u32 = 157;

/// Grapevine — Wine / volatile buffer: create anonymous temp fd.
/// No args → a0 = fd.
pub const SYS_SYR:   u32 = 158;

/// Grapevine — Platter / directory / bundle: read directory listing.
/// a0 = name VA (0 = root), a1 = name len, a2 = out buf VA, a3 = buf len
/// → a0 = bytes written.
pub const SYS_SETH:  u32 = 159;

/// Grapevine — Messenger / packet: send a message packet.
/// a0 = dst PID, a1 = buf VA, a2 = len → a0 = ok (1) / fail (0).
pub const SYS_MYK:   u32 = 163;

/// Grapevine — Call / emit event: fire a kernel event.
/// a0 = event ID, a1 = data → void.
pub const SYS_MEK:   u32 = 166;

/// Cannabis — Conscious persistence: write output (the act of mind making something durable).
/// a0 = fd, a1 = buf VA, a2 = len → a0 = bytes written.
pub const SYS_SOA:   u32 = 193;

/// Cannabis — Conscious spatial action: extend heap (sbrk).
/// a0 = increment bytes → a0 = new break VA.
pub const SYS_SEI:   u32 = 203;

/// Cannabis — Conscious temporal action: sleep for ticks.
/// a0 = tick count → void.
pub const SYS_SUY:   u32 = 213;

/// Relational — Koi (Mav): create balanced-exchange channel.
/// No args → a0 = channel ID.
pub const SYS_KOI:   u32 = 1138;

/// Relational — Rope (Mab): bind ownership of a resource.
/// a0 = resource token → a0 = ownership handle.
pub const SYS_ROPE:  u32 = 1182;

/// Relational — Hook (Mag): register IRQ / mechanism handler.
/// a0 = IRQ number, a1 = handler VA → a0 = ok.
pub const SYS_HOOK:  u32 = 1226;

/// Relational — Fang (Madj): declare constitutive resource contract.
/// a0 = resource class, a1 = rate → void.
pub const SYS_FANG:  u32 = 1270;

/// Relational — Circle (Man): broadcast event to all waiters.
/// a0 = event ID, a1 = data → void.
pub const SYS_CIRCLE: u32 = 1314;
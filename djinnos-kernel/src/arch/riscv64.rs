// RISC-V RV64 architecture primitives.
//
// Sv39 virtual memory:
//   39-bit VA space, 3-level page table, 4 KiB pages.
//   Gigapages (1 GiB, L2 leaf) used for the initial kernel identity map.
//   Root page table physical address → satp[43:0] (PPN), satp[63:60] = 8 (Sv39 mode).
//
// x86_64 equivalent:
//   enable_paging(root_pa)  ↔  mov cr3, root_pa
//   flush_tlb()             ↔  invlpg / mov cr3,cr3
//   paging_active()         ↔  (cr0 & CR0_PG) != 0
//   set_trap_vector(addr)   ↔  lidt + set IDT entries
//   wfi()                   ↔  hlt

use core::arch::asm;

// ── Sv39 paging ───────────────────────────────────────────────────────────────

const SATP_SV39: u64 = 8u64 << 60;

/// Enable Sv39 paging.  `root_pa` must be 4 KiB-aligned.
/// After this call physical and virtual addresses are identical (identity map).
pub fn enable_paging(root_pa: u64) {
    let satp = SATP_SV39 | (root_pa >> 12);
    unsafe {
        asm!(
            "csrw satp, {s}",
            "sfence.vma zero, zero",
            s = in(reg) satp,
            options(nostack),
        );
    }
}

/// Flush the entire TLB (all ASIDs, all addresses).
pub fn flush_tlb() {
    unsafe { asm!("sfence.vma zero, zero", options(nostack, nomem)); }
}

/// True if Sv39 (or any) paging mode is active.
pub fn paging_active() -> bool {
    let satp: u64;
    unsafe { asm!("csrr {}, satp", out(reg) satp, options(nostack, nomem)); }
    satp >> 60 != 0
}

// ── Trap vector ───────────────────────────────────────────────────────────────

/// Point stvec at a 4-byte-aligned direct-mode trap handler.
pub fn set_trap_vector(addr: u64) {
    unsafe {
        asm!(
            "csrw stvec, {v}",
            v = in(reg) addr,
            options(nostack),
        );
    }
}

// ── Miscellaneous ─────────────────────────────────────────────────────────────

/// Wait for interrupt — used by parked harts and the idle loop.
pub fn wfi() {
    unsafe { asm!("wfi", options(nostack, nomem)); }
}

// ── CLINT timer ───────────────────────────────────────────────────────────────
//
// The CLINT mtime counter ticks at 10 MHz on the QEMU virt machine.
// M-mode owns the timer hardware; S-mode arms it via the SBI_SET_TIMER ecall
// (a7=0, a0=deadline) which causes M-mode to clear STIP and write mtimecmp.

const MTIME: *const u64 = 0x200_BFF8 as *const u64;

/// Ticks per scheduler interval (10 ms at 10 MHz CLINT).
pub const TICK_INTERVAL: u64 = 100_000;

/// Read the current value of the mtime counter.
pub fn read_mtime() -> u64 {
    unsafe { MTIME.read_volatile() }
}

/// SBI_SET_TIMER — ecall to M-mode: write `deadline` to mtimecmp and clear STIP.
/// Call this to arm or re-arm the supervisor timer interrupt.
pub fn sbi_set_timer(deadline: u64) {
    unsafe {
        asm!(
            "ecall",
            in("a7") 0usize,
            in("a0") deadline,
            options(nostack),
        );
    }
}

/// Enable supervisor timer interrupts (sie.STIE) and global S-mode interrupts
/// (sstatus.SIE).  Call once after process::init(), before the main event loop.
pub fn enable_timer() {
    unsafe {
        asm!(
            "csrs sie, {stie}",
            "csrs sstatus, {sie}",
            stie = in(reg) 1u64 << 5,
            sie  = in(reg) 1u64 << 1,
            options(nostack),
        );
    }
}
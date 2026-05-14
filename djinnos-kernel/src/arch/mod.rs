// Architecture abstraction layer.
//
// Every machine-specific primitive — paging, trap vectors, timer, I/O ports —
// lives behind this module.  The kernel above src/arch/ is architecture-neutral.
//
// To port DjinnOS to a new target:
//   1. Add src/arch/<target>.rs
//   2. Implement the primitives below
//   3. Add a cfg gate here
//   4. Update boot.s / linker.ld for the new target
//
#![allow(unused_imports)]
// Currently supported: riscv64gc-unknown-none-elf, x86_64-unknown-none

#[cfg(target_arch = "riscv64")]
mod riscv64;

#[cfg(target_arch = "riscv64")]
pub use riscv64::{
    enable_paging,
    flush_tlb,
    paging_active,
    set_trap_vector,
    wfi,
    read_mtime,
    sbi_set_timer,
    enable_timer,
    TICK_INTERVAL,
};

#[cfg(target_arch = "x86_64")]
mod x86_64;

#[cfg(target_arch = "x86_64")]
pub use x86_64::{
    enable_paging,
    flush_tlb,
    paging_active,
    set_trap_vector,
    wfi,
    read_mtime,
    sbi_set_timer,
    enable_timer,
    start_timer,
    probe_timer,
    TICK_INTERVAL,
    uart_init,
    uart_putc,
    uart_getc,
    inb,
    outb,
    inl,
    outl,
    probe_apic,
    // Ring-3 userspace
    setup_userspace,
    make_all_user_accessible,
    enter_user,
    enter_user_x86,
    exit_user,
    user_sbrk,
    USER_HEAP_BREAK,
    USER_HEAP,
};

// RISC-V stubs so trap.rs and process/mod.rs compile on both targets.
#[cfg(target_arch = "riscv64")]
pub fn user_sbrk(_incr: usize) -> u64 { u64::MAX }
#[cfg(target_arch = "riscv64")]
pub fn setup_userspace() {}
#[cfg(target_arch = "riscv64")]
pub fn make_all_user_accessible() {}
#[cfg(target_arch = "riscv64")]
pub fn enter_user(_entry: u64, _stack: u64) {}
#[cfg(target_arch = "riscv64")]
pub fn exit_user() -> ! { loop {} }
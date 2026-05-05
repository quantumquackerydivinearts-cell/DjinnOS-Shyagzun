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
    TICK_INTERVAL,
    uart_init,
    uart_putc,
    uart_getc,
};
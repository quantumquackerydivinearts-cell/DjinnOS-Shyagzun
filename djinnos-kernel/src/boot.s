# DjinnOS boot entry — RISC-V RV64
# Runs before any Rust code.  Sets up the stack, clears BSS, jumps to kernel_main.
# On QEMU virt with -bios none, execution begins at 0x80000000 (hartid in a0, dtb in a1).

.section .text.boot
.global _start

_start:
    # Only hart 0 continues; all others park
    csrr  t0, mhartid
    bnez  t0, .park

    # Set stack pointer
    la    sp, _stack_top

    # Clear BSS
    la    t0, _bss_start
    la    t1, _bss_end
.clear_bss:
    bgeu  t0, t1, .done_bss
    sd    zero, 0(t0)
    addi  t0, t0, 8
    j     .clear_bss
.done_bss:

    # Hand off to Rust — never returns
    call  kernel_main

.park:
    wfi
    j .park
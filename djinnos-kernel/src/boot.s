# DjinnOS boot entry — RISC-V RV64
#
# Execution begins in M-mode (machine mode) at 0x80000000.
# We set up minimal M-mode state then drop to S-mode (supervisor mode)
# where the Sv39 virtual memory subsystem lives.
#
# M-mode responsibilities (done here, never revisited):
#   1. PMP — grant S/U-mode full physical memory access
#   2. Trap delegation — all exceptions/interrupts → S-mode handlers
#   3. mstatus.MPP = S-mode
#   4. mret → kernel_main runs in S-mode
#
# x86_64 equivalent of this file:
#   real-mode → protected-mode → long-mode bootstrap
#   GDT, IDT, CR3 setup, then jump to 64-bit C entry
#
# After this file, the kernel never returns to M-mode.

.section .text.boot
.global _start

_start:
    # Only hart 0 continues; all others park immediately.
    csrr  t0, mhartid
    bnez  t0, .park

    # Set up the boot stack (grows downward).
    la    sp, _stack_top

    # ── Clear BSS ────────────────────────────────────────────────
    la    t0, _bss_start
    la    t1, _bss_end
.clr:
    bgeu  t0, t1, .done_clr
    sd    zero, 0(t0)
    addi  t0, t0, 8
    j     .clr
.done_clr:

    # ── PMP: grant S and U-mode full physical memory access ──────
    # Without this, any S-mode memory access raises a fault.
    # pmpaddr0 = all-ones → entire 64-bit physical address space (NAPOT)
    li    t0, -1
    csrw  pmpaddr0, t0
    # pmpcfg0[7:0]: A=NAPOT(3<<3), X, W, R  →  0b00011111 = 0x1f
    li    t0, 0x1f
    csrw  pmpcfg0, t0

    # ── M-mode timer: install handler, arm mtimecmp, enable MTIE ────────────
    # mscratch = M-mode stack top; _m_trap swaps sp↔mscratch to avoid
    # using a possibly-virtual U-mode sp when M-mode fires.
    la    t0, _stack_top
    csrw  mscratch, t0

    # Push mtimecmp to max so MTIP doesn't fire until main.rs arms it.
    li    t0, -1
    li    t1, 0x2004000
    sd    t0, 0(t1)

    # Enable MTIE so MTIP can fire once main.rs writes a real deadline.
    li    t0, (1 << 7)
    csrs  mie, t0

    # Install M-mode trap vector.
    la    t0, _m_trap
    csrw  mtvec, t0

    # ── Delegate traps to S-mode ─────────────────────────────────────────────
    # Interrupt delegation: all except MTIP (bit 7, read-only 0 in mideleg).
    li    t0, 0xffff
    csrw  mideleg, t0
    # Exception delegation: all EXCEPT S-mode ecall (bit 9) — kept in M-mode
    # so S-mode can call SBI_SET_TIMER via ecall without going back to S-mode.
    li    t0, 0xfdff
    csrw  medeleg, t0

    # ── Set mstatus: MPP=S-mode, FS=Initial ─────────────────────
    # FS [14:13] must be non-zero before any FP instruction runs in S-mode.
    # Setting FS=01 (Initial) here means sstatus.FS is already live when
    # kernel_main executes its first f32 operation.
    li    t0, (3 << 11) | (3 << 13)   # clear MPP and FS fields
    csrc  mstatus, t0
    li    t0, (1 << 11) | (1 << 13)   # MPP=S (01), FS=Initial (01)
    csrs  mstatus, t0

    # ── Jump to S-mode ───────────────────────────────────────────
    # mepc = kernel_main; mret drops privilege to MPP=S and jumps there.
    la    t0, kernel_main
    csrw  mepc, t0
    mret                   # → kernel_main now runs in S-mode

.park:
    wfi
    j .park

# ── Supervisor trap entry ─────────────────────────────────────────────────────
# stvec direct-mode target (must be 4-byte aligned).
#
# Distinguishes kernel traps (sstatus.SPP=1) from user traps (SPP=0).
#
# Kernel path: minimal save of ra+a0-a2, call _trap_handler, sret.
# User path:   full 31-register + CSR save to TrapFrame via sscratch,
#              switch to kernel stack, call _trap_handler_user, then sret.
#
# sscratch contract:
#   While a user process runs: sscratch = &TrapFrame (kernel PA = kernel VA).
#   While kernel runs:         sscratch = 0 (kernel traps never use it).

.section .text
.global _trap_entry
.align 4
_trap_entry:
    # Check sstatus.SPP (bit 8): 1 = trapped from S-mode, 0 = from U-mode.
    csrr  t0, sstatus
    andi  t0, t0, 0x100
    beqz  t0, .user_trap

    # ── Kernel trap path ─────────────────────────────────────────────────────
    addi sp, sp, -48
    sd   ra,  0(sp)
    sd   a0,  8(sp)
    sd   a1, 16(sp)
    sd   a2, 24(sp)
    csrr a0, scause
    csrr a1, sepc
    csrr a2, stval
    call _trap_handler
    ld   ra,  0(sp)
    ld   a0,  8(sp)
    ld   a1, 16(sp)
    ld   a2, 24(sp)
    addi sp, sp, 48
    sret

    # ── User trap path ───────────────────────────────────────────────────────
    # sscratch = &TrapFrame; swap a0 ↔ sscratch so a0 = TrapFrame ptr.
.user_trap:
    csrrw a0, sscratch, a0      # a0 = TrapFrame*, sscratch = user a0

    sd ra,    0(a0)
    sd sp,    8(a0)
    sd gp,   16(a0)
    sd tp,   24(a0)
    sd t0,   32(a0)
    sd t1,   40(a0)
    sd t2,   48(a0)
    sd s0,   56(a0)
    sd s1,   64(a0)
    # a0 is in sscratch — recover and save it
    csrr t0, sscratch
    sd t0,   72(a0)
    # restore sscratch = TrapFrame ptr (handler reads it; user_sret uses it)
    csrw sscratch, a0
    sd a1,   80(a0)
    sd a2,   88(a0)
    sd a3,   96(a0)
    sd a4,  104(a0)
    sd a5,  112(a0)
    sd a6,  120(a0)
    sd a7,  128(a0)
    sd s2,  136(a0)
    sd s3,  144(a0)
    sd s4,  152(a0)
    sd s5,  160(a0)
    sd s6,  168(a0)
    sd s7,  176(a0)
    sd s8,  184(a0)
    sd s9,  192(a0)
    sd s10, 200(a0)
    sd s11, 208(a0)
    sd t3,  216(a0)
    sd t4,  224(a0)
    sd t5,  232(a0)
    sd t6,  240(a0)
    csrr t0, sepc;    sd t0, 248(a0)
    csrr t0, sstatus; sd t0, 256(a0)
    # Switch to kernel stack (TrapFrame.ksp at offset 272)
    ld sp, 272(a0)
    # Call user trap handler(tf*, cause, sepc, stval)
    csrr a1, scause
    csrr a2, sepc
    csrr a3, stval
    call _trap_handler_user
    # Reload TrapFrame ptr (sscratch preserved across handler) and sret.
    csrr a0, sscratch
    j    .user_sret

# ── Resume user mode ──────────────────────────────────────────────────────────
# Called by switch_context on first scheduling (and after cooperative yield).
#   s0 = &TrapFrame   (set in Context.s0 by spawn_elf)
#   sp = kernel stack top for this process
.global user_resume
user_resume:
    mv a0, s0       # a0 = TrapFrame ptr

# ── Shared restore-and-sret path ──────────────────────────────────────────────
# Input: a0 = &TrapFrame, sp = kernel stack pointer for this process.
.user_sret:
    sd sp,  272(a0)             # update TrapFrame.ksp = current kernel sp
    csrw sscratch, a0           # set sscratch = TrapFrame for next user trap
    ld t0, 248(a0); csrw sepc,    t0
    ld t0, 256(a0); csrw sstatus, t0
    ld t0, 264(a0); csrw satp,    t0   # switch to user page table
    sfence.vma zero, zero
    # Restore all registers.  s0 and a0 restored last (used as base pointer).
    ld ra,    0(a0)
    ld sp,    8(a0)
    ld gp,   16(a0)
    ld tp,   24(a0)
    ld t0,   32(a0)
    ld t1,   40(a0)
    ld t2,   48(a0)
    ld s1,   64(a0)
    ld a1,   80(a0)
    ld a2,   88(a0)
    ld a3,   96(a0)
    ld a4,  104(a0)
    ld a5,  112(a0)
    ld a6,  120(a0)
    ld a7,  128(a0)
    ld s2,  136(a0)
    ld s3,  144(a0)
    ld s4,  152(a0)
    ld s5,  160(a0)
    ld s6,  168(a0)
    ld s7,  176(a0)
    ld s8,  184(a0)
    ld s9,  192(a0)
    ld s10, 200(a0)
    ld s11, 208(a0)
    ld t3,  216(a0)
    ld t4,  224(a0)
    ld t5,  232(a0)
    ld t6,  240(a0)
    ld s0,   56(a0)             # restore s0 (uses old a0 as base — safe in RISC-V)
    ld a0,   72(a0)             # restore a0 (very last load)
    sret

# ── M-mode trap handler (timer + SBI) ────────────────────────────────────────
#
# Handles two cases:
#   MTIP (interrupt 7) — sets STIP in mip, pushes mtimecmp to far future.
#   S-mode ecall, a7=0 (SBI_SET_TIMER) — clears STIP, writes a0 to mtimecmp.
#
# Register save: swaps sp↔mscratch to get a valid physical stack address
# regardless of whether M-mode was entered from S-mode or U-mode.
# (U-mode sp is a virtual address; M-mode uses physical addresses only.)

.global _m_trap
.align 2
_m_trap:
    csrrw sp, mscratch, sp      # sp = M-mode stack (physical); mscratch = caller's sp
    addi  sp, sp, -24
    sd    t0,  0(sp)
    sd    t1,  8(sp)
    sd    t2, 16(sp)

    csrr  t0, mcause
    srli  t1, t0, 63            # interrupt bit
    beqz  t1, .m_exc

    # ── MTIP (interrupt code 7) ───────────────────────────────────────────────
    andi  t0, t0, 0x7f
    li    t1, 7
    bne   t0, t1, .m_ret        # not MTIP — ignore

    li    t0, (1 << 5)
    csrs  mip, t0               # set STIP so S-mode sees the timer interrupt

    li    t0, -1                # 0xFFFF...FFFF — far future
    li    t1, 0x2004000
    sd    t0, 0(t1)             # push mtimecmp past heat death of the universe
    j     .m_ret

    # ── S-mode ecall (exception code 9) with a7=0: SBI_SET_TIMER ─────────────
.m_exc:
    andi  t0, t0, 0x7f
    li    t1, 9
    bne   t0, t1, .m_ret        # not S-mode ecall — ignore

    bnez  a7, .m_ret            # only handle SBI function 0

    li    t0, (1 << 5)
    csrc  mip, t0               # clear STIP (prevents double-tick after re-arm)

    li    t1, 0x2004000
    sd    a0, 0(t1)             # mtimecmp = a0 (deadline passed by S-mode)

    csrr  t0, mepc
    addi  t0, t0, 4
    csrw  mepc, t0              # advance past the ecall instruction

.m_ret:
    ld    t0,  0(sp)
    ld    t1,  8(sp)
    ld    t2, 16(sp)
    addi  sp, sp, 24
    csrrw sp, mscratch, sp      # restore caller's sp; mscratch = M-mode stack top
    mret
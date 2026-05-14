/* DjinnOS — x86_64 boot  (Intel syntax, default for Rust global_asm! on x86)
 *
 * Dual-header design:
 *   – Multiboot2 (0xE85250D6): GRUB uses this to load the 64-bit ELF directly
 *     and pass a framebuffer tag.  Entry at _start in 32-bit protected mode
 *     with EAX=0x36d76289, EBX=mb2_info_physical_address.
 *   – Multiboot1 a.out kludge (0x1BADB002 | bit16): QEMU's -kernel + flat-
 *     binary path uses this for development testing.  EAX=0x2BADB002.
 *
 * Page tables cover 0–4 GiB using 2 MiB huge pages (4 PDs × 512 entries).
 * This ensures the GOP framebuffer (typically 0xC0000000–0xFF000000) is
 * accessible immediately without runtime page-table additions.
 *
 * The multiboot2 info address in EBX is saved to _mb2_info before anything
 * clobbers EBX, then passed to kernel_main as its first argument (RDI).
 */

.code32

/* ── Multiboot2 header ────────────────────────────────────────────────────── */
/* Must be within the first 32 768 bytes of a PT_LOAD segment, 8-byte aligned. */

.section .text.boot, "ax"
.global _start

.align 8
mb2_start:
    .long  0xE85250D6                          /* magic */
    .long  0                                   /* i386 protected mode */
    .long  mb2_end - mb2_start                 /* header_length */
    .long  -(0xE85250D6 + 0 + (mb2_end - mb2_start))  /* checksum */
    /* Framebuffer request tag (type 5) */
    .word  5, 0                                /* type, flags */
    .long  20                                  /* size */
    .long  0, 0, 32                            /* width=any, height=any, depth=32bpp */
    /* End tag (type 0) */
    .word  0, 0
    .long  8
mb2_end:

/* ── Multiboot1 a.out kludge ─────────────────────────────────────────────── */
/* Fallback for QEMU's -kernel with flat binary during development. */

.align 4
mb1_header:
    .long  0x1BADB002
    .long  0x00010000                          /* a.out kludge flag */
    .long  -(0x1BADB002 + 0x00010000)
    .long  mb1_header                          /* header_addr */
    .long  0x100000                            /* load_addr */
    .long  0
    .long  0
    .long  _start                              /* entry_addr */

/* ── 32-bit entry ─────────────────────────────────────────────────────────── */

_start:
    cld
    mov   esp, 0x90000

    /* Save the multiboot info pointer IMMEDIATELY before any register use.
     * EBX is not clobbered by the page table setup code below. */
    mov   DWORD PTR [_mb2_info], ebx

    /* Accept both multiboot1 and multiboot2 magic values. */
    cmp   eax, 0x36d76289                      /* multiboot2 */
    je    .mbok
    cmp   eax, 0x2BADB002                      /* multiboot1 */
    jne   .halt32
.mbok:

    /* ── Page table setup: identity map 0–4 GiB with 2 MiB huge pages ─────
     * Layout: PML4[1 page] + PDPT[1 page] + PD0..PD3[4 pages] = 6 × 4 KiB
     * PDPT[0..3] each point to a PD covering 1 GiB.
     * Each PD has 512 entries × 2 MiB = 1 GiB. */

    /* Clear all 6 tables (6 × 4 KiB = 6144 dwords). */
    mov   edi, OFFSET _boot_pml4
    xor   eax, eax
    mov   ecx, 6144
    rep   stosd

    /* PML4[0] = &PDPT | 3 */
    mov   eax, OFFSET _boot_pdpt
    or    eax, 3
    mov   DWORD PTR [OFFSET _boot_pml4],   eax
    mov   DWORD PTR [OFFSET _boot_pml4+4], 0

    /* PDPT[0..3] = &PD0..&PD3 | 3  (each covers 1 GiB) */
    mov   eax, OFFSET _boot_pd0
    or    eax, 3
    mov   DWORD PTR [OFFSET _boot_pdpt+0],  eax
    mov   DWORD PTR [OFFSET _boot_pdpt+4],  0
    mov   eax, OFFSET _boot_pd1
    or    eax, 3
    mov   DWORD PTR [OFFSET _boot_pdpt+8],  eax
    mov   DWORD PTR [OFFSET _boot_pdpt+12], 0
    mov   eax, OFFSET _boot_pd2
    or    eax, 3
    mov   DWORD PTR [OFFSET _boot_pdpt+16], eax
    mov   DWORD PTR [OFFSET _boot_pdpt+20], 0
    mov   eax, OFFSET _boot_pd3
    or    eax, 3
    mov   DWORD PTR [OFFSET _boot_pdpt+24], eax
    mov   DWORD PTR [OFFSET _boot_pdpt+28], 0

    /* Fill all 4 PDs: 2048 entries covering 0–4 GiB.
     * Entry n covers physical [n×2MiB, (n+1)×2MiB).
     * High 32 bits of each PTE are 0 (all addresses fit in 32 bits). */
    mov   edi, OFFSET _boot_pd0
    xor   eax, eax
    or    eax, 0x83                            /* P=1 R/W=1 PS=1 (2 MiB page) */
    mov   ecx, 2048
.fill_pds:
    mov   DWORD PTR [edi],   eax
    mov   DWORD PTR [edi+4], 0
    add   edi, 8
    add   eax, 0x200000                        /* advance 2 MiB */
    loop  .fill_pds

    /* Load CR3 = PML4 physical address. */
    mov   eax, OFFSET _boot_pml4
    mov   cr3, eax

    /* CR4.PAE = 1. */
    mov   eax, cr4
    or    eax, 0x20
    mov   cr4, eax

    /* EFER.LME = 1 (IA32_EFER MSR 0xC0000080 bit 8). */
    mov   ecx, 0xC0000080
    rdmsr
    or    eax, 0x100
    wrmsr

    /* CR0.PG = 1 — activates compatibility mode (long mode). */
    mov   eax, cr0
    or    eax, 0x80000000
    mov   cr0, eax

    lgdt  [OFFSET _gdt_ptr]

    /* Far jump to 64-bit code segment (raw encoding). */
    .byte 0xEA
    .long _start64
    .word 0x08

.halt32:
    hlt
    jmp .halt32

/* ── 64-bit entry ─────────────────────────────────────────────────────────── */

.code64
_start64:
    mov   ax, 0x10
    mov   ds, ax
    mov   es, ax
    mov   fs, ax
    mov   gs, ax
    mov   ss, ax

    mov   rsp, OFFSET _stack_top

    /* Zero BSS.  .boot_pt comes before .bss in linker_x86.ld, so the
     * live page tables are never touched by this memset. */
    mov   rdi, OFFSET _bss_start
    mov   rcx, OFFSET _bss_end
    sub   rcx, rdi
    xor   eax, eax
    shr   rcx, 3
    rep   stosq

    /* Pass the saved mb2 info physical address as the first argument (RDI).
     * Zero-extend the 32-bit saved value — all physical addresses < 4 GiB. */
    mov   edi, DWORD PTR [_mb2_info]           /* zero-extends to RDI */

    call  kernel_main

.halt64:
    hlt
    jmp .halt64

/* ── GDT ──────────────────────────────────────────────────────────────────── */

.section .data
.align 16
_gdt:
    .quad 0
    .quad 0x00af9a000000ffff      /* 0x08 code64 (L=1 P=1 DPL=0) */
    .quad 0x00af92000000ffff      /* 0x10 data64 */
_gdt_end:

_gdt_ptr:
    .word _gdt_end - _gdt - 1
    .long _gdt

/* Saved multiboot2 info physical address (written before page setup). */
_mb2_info:
    .long 0

/* ── ISR stubs ────────────────────────────────────────────────────────────── */

.section .text
.global _isr_timer
_isr_timer:
    push  rax
    push  rcx
    push  rdx
    push  rdi
    push  rsi
    push  r8
    push  r9
    push  r10
    push  r11
    call  _timer_tick
    pop   r11; pop r10; pop r9; pop r8
    pop   rsi; pop rdi; pop rdx; pop rcx; pop rax
    iretq

.global _isr_fault
_isr_fault:
    hlt
    jmp _isr_fault

/* Generic hardware IRQ handler for vectors 0x20–0xFE.
 * Sends LAPIC EOI (xAPIC MMIO at 0xFEE000B0) and returns.
 * Silences unexpected IOAPIC-delivered interrupts (keyboard, USB, etc.)
 * that would otherwise halt the CPU in _isr_fault. */
.global _isr_generic
_isr_generic:
    push  rax
    push  rdx
    xor   edx, edx
    mov   rax, 0xFEE000B0
    mov   dword ptr [rax], edx   /* LAPIC EOI = 0 */
    pop   rdx
    pop   rax
    iretq

/* LAPIC spurious interrupt — must NOT send EOI; just return.
 * The LAPIC does not set the ISR bit for spurious vectors, so an EOI
 * here would acknowledge the wrong (next-highest-priority) interrupt. */
.global _isr_spurious
_isr_spurious:
    iretq

/* ── Userspace RSP save slots ─────────────────────────────────────────────── */
/* Used by _syscall_entry to swap between user and kernel stacks without
 * touching the user stack (which is in ring-3 and may not be trusted). */

.section .data
.align 8
.global _user_rsp_save
.global _kernel_rsp_save
_user_rsp_save:   .quad 0
_kernel_rsp_save: .quad 0

/* ── SYSCALL entry stub ────────────────────────────────────────────────────── */
/* LSTAR MSR points here.  The SYSCALL instruction saves user RIP → RCX,
 * user RFLAGS → R11, then jumps here in ring 0 with interrupts disabled.
 * RSP is still the user RSP — we switch to the kernel syscall stack first.
 *
 * SyscallFrame layout (RSP after all pushes, low address first):
 *   RSP+0   padding (8 B for 16-byte alignment)
 *   RSP+8   r11     (user RFLAGS saved by SYSCALL)
 *   RSP+16  rcx     (user RIP saved by SYSCALL)
 *   RSP+24  r15
 *   RSP+32  r14
 *   RSP+40  r13
 *   RSP+48  r12
 *   RSP+56  rbp
 *   RSP+64  rbx
 *   RSP+72  r9      (arg5)
 *   RSP+80  r8      (arg4)
 *   RSP+88  r10     (arg3)
 *   RSP+96  rdx     (arg2)
 *   RSP+104 rsi     (arg1)
 *   RSP+112 rdi     (arg0)
 *   RSP+120 rax     (syscall number; return value in rax after dispatch)
 *
 * Total: 16 × 8 = 128 bytes pushed.  Kernel stack top must be 16-byte aligned
 * so that RSP = top - 128 is also 16-byte aligned when call fires.
 */

.section .text
.global _syscall_entry
.align 16
_syscall_entry:
    mov   [rip + _user_rsp_save],   rsp
    mov   rsp, [rip + _kernel_rsp_save]

    push  rax          /* syscall number (return value slot) */
    push  rdi          /* arg0 */
    push  rsi          /* arg1 */
    push  rdx          /* arg2 */
    push  r10          /* arg3 */
    push  r8           /* arg4 */
    push  r9           /* arg5 */
    push  rbx
    push  rbp
    push  r12
    push  r13
    push  r14
    push  r15
    push  rcx          /* user RIP */
    push  r11          /* user RFLAGS */
    sub   rsp, 8       /* alignment pad → 128 bytes total, aligned ✓ */

    mov   rdi, rsp
    call  _dispatch_syscall_x86_rs   /* returns value in rax */

    add   rsp, 8       /* skip padding */
    pop   r11          /* user RFLAGS → for SYSRETQ */
    pop   rcx          /* user RIP   → for SYSRETQ */
    pop   r15
    pop   r14
    pop   r13
    pop   r12
    pop   rbp
    pop   rbx
    pop   r9
    pop   r8
    pop   r10
    pop   rdx
    pop   rsi
    pop   rdi
    add   rsp, 8       /* skip saved rax — return value is already in rax */

    mov   rsp, [rip + _user_rsp_save]
    sysretq

/* ── Kernel syscall stack + enter/exit user frame ─────────────────────────── */

.section .bss
.align 16
.global _kern_syscall_stack
_kern_syscall_stack:  .space 16384
.global _kern_syscall_stack_top
_kern_syscall_stack_top:

/* Callee-saved context saved by _enter_user_x86, restored by _exit_user_x86. */
.align 8
.global _uef_r15; _uef_r15: .space 8
.global _uef_r14; _uef_r14: .space 8
.global _uef_r13; _uef_r13: .space 8
.global _uef_r12; _uef_r12: .space 8
.global _uef_rbx; _uef_rbx: .space 8
.global _uef_rbp; _uef_rbp: .space 8
.global _uef_rsp; _uef_rsp: .space 8

/* ── Enter ring 3 via IRETQ ───────────────────────────────────────────────── */
// _enter_user_x86(entry: rdi, user_stack: rsi)
// Saves callee-saved regs, arms the kernel syscall stack, then IRETQ.
// Returns normally when the user process calls SYS_ZU (see _exit_user_x86).
.section .text
.global _enter_user_x86
_enter_user_x86:
    mov   [rip + _uef_r15], r15
    mov   [rip + _uef_r14], r14
    mov   [rip + _uef_r13], r13
    mov   [rip + _uef_r12], r12
    mov   [rip + _uef_rbx], rbx
    mov   [rip + _uef_rbp], rbp
    mov   [rip + _uef_rsp], rsp   /* caller RSP — return address is on top */

    lea   rax, [rip + _kern_syscall_stack_top]
    mov   [rip + _kernel_rsp_save], rax

    /* Build IRETQ frame: push SS, RSP_user, RFLAGS, CS_user, RIP */
    mov   r10, 0x1b               /* user SS: selector 0x18 | RPL=3 */
    push  r10
    push  rsi                     /* user RSP */
    mov   r10, 0x202              /* RFLAGS: IF=1, bit1=1 */
    push  r10
    mov   r10, 0x23               /* user CS: selector 0x20 | RPL=3 */
    push  r10
    push  rdi                     /* user RIP */

    xor   eax,  eax;  xor ebx,  ebx;  xor ecx,  ecx;  xor edx,  edx
    xor   esi,  esi;  xor edi,  edi;  xor ebp,  ebp
    xor   r8d,  r8d;  xor r9d,  r9d;  xor r10d, r10d; xor r11d, r11d
    xor   r12d, r12d; xor r13d, r13d; xor r14d, r14d; xor r15d, r15d
    iretq

/* ── Restore kernel context on user process exit ─────────────────────────── */
/* Called from _dispatch_syscall_x86_rs when sys=SYS_ZU.                     */
/* Restores callee-saved regs + RSP, then rets to the caller of              */
/* _enter_user_x86, making it appear to return normally.                      */
.global _exit_user_x86
_exit_user_x86:
    mov   r15, [rip + _uef_r15]
    mov   r14, [rip + _uef_r14]
    mov   r13, [rip + _uef_r13]
    mov   r12, [rip + _uef_r12]
    mov   rbx, [rip + _uef_rbx]
    mov   rbp, [rip + _uef_rbp]
    mov   rsp, [rip + _uef_rsp]
    xor   eax, eax
    ret

/* ── Boot page tables (before .bss so the BSS clear never touches them) ───── */

.section .boot_pt, "aw"
.align 4096
.global _boot_pml4; _boot_pml4: .space 4096
.global _boot_pdpt; _boot_pdpt: .space 4096
.global _boot_pd0;  _boot_pd0:  .space 4096
.global _boot_pd1;  _boot_pd1:  .space 4096
.global _boot_pd2;  _boot_pd2:  .space 4096
.global _boot_pd3;  _boot_pd3:  .space 4096

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

/* ── Boot page tables (before .bss so the BSS clear never touches them) ───── */

.section .boot_pt, "aw"
.align 4096
.global _boot_pml4; _boot_pml4: .space 4096
.global _boot_pdpt; _boot_pdpt: .space 4096
.global _boot_pd0;  _boot_pd0:  .space 4096
.global _boot_pd1;  _boot_pd1:  .space 4096
.global _boot_pd2;  _boot_pd2:  .space 4096
.global _boot_pd3;  _boot_pd3:  .space 4096

/* DjinnOS — x86_64 boot  (Intel syntax, default for Rust global_asm! on x86)
 *
 * Uses multiboot1 (magic 0x1BADB002) because QEMU's -kernel only supports
 * multiboot1 (not multiboot2) for direct x86 kernel loading.
 *
 * QEMU delivers us in 32-bit protected mode with paging disabled.
 * We set up 2 MiB identity-mapped huge pages for 0–1 GiB, enter long mode,
 * zero BSS, then call kernel_main.
 */

.code32

/* ── PVH ELF note (required by QEMU 9+ for loading 64-bit ELF with -kernel) ─
 *
 * QEMU's x86 direct-kernel loader tries PVH before multiboot1.
 * PVH entry: 32-bit protected mode, EBX = hvm_start_info ptr (can ignore),
 * flat segments, paging off.  Same environment as multiboot1. */

.section .note.Xen, "a"
.align 4
.long 4              /* name length including NUL: "Xen\0" */
.long 4              /* desc length: one 32-bit physical address */
.long 18             /* type XEN_ELFNOTE_PHYS32_ENTRY */
.byte 0x58,0x65,0x6e,0x00  /* "Xen\0" */
.long _start         /* 32-bit PVH entry point */

/* ── Multiboot1 header (fallback) ────────────────────────────────────────── */

.section .text.boot, "ax"
.global _start

/* Multiboot1 header with a.out kludge (bit 16).
 * QEMU's multiboot loader scans the first 8192 bytes for magic 0x1BADB002.
 * When bit 16 is set, it reads load/header/entry addresses from this header
 * instead of parsing ELF — bypasses the ELFCLASS64 rejection.
 *
 * File-offset calculation QEMU uses:
 *   file_off = header_file_pos - (header_addr - load_addr)
 *            = header_file_pos - (header_addr - 0x100000)
 * In a flat binary: header_file_pos = header_addr - 0x100000
 *            => file_off = 0  (reads from start of file)
 */
.align 4
mb1_header:
    .long  0x1BADB002               /* magic */
    .long  0x00010000               /* flags: bit 16 = a.out kludge */
    .long  -(0x1BADB002 + 0x00010000) /* checksum */
    .long  mb1_header               /* header_addr: VA of this header */
    .long  0x100000                 /* load_addr:   load kernel here */
    .long  0                        /* load_end:    0 = whole file */
    .long  0                        /* bss_end:     0 = skip */
    .long  _start                   /* entry_addr */

/* ── 32-bit entry — entered from both PVH and multiboot1 ─────────────────── */

_start:
    cld
    mov   esp, 0x90000

    /* Clear PML4 + PDPT + PD (3 × 4096 = 12288 bytes = 3072 dwords) */
    mov   edi, OFFSET _boot_pml4
    xor   eax, eax
    mov   ecx, 3072
    rep   stosd

    /* PML4[0] = &PDPT | 3  (P=1 R/W=1) */
    mov   eax, OFFSET _boot_pdpt
    or    eax, 3
    mov   [OFFSET _boot_pml4], eax

    /* PDPT[0] = &PD | 3 */
    mov   eax, OFFSET _boot_pd
    or    eax, 3
    mov   [OFFSET _boot_pdpt], eax

    /* PD[0..511]: 2 MiB huge-page entries (P=1 R/W=1 PS=1) covering 0–1 GiB */
    mov   edi, OFFSET _boot_pd
    mov   eax, 0x83                 /* base=0, PS=1, R/W=1, P=1 */
    mov   ecx, 512
.fill_pd:
    mov   [edi],   eax
    mov   DWORD PTR [edi+4], 0
    add   edi, 8
    add   eax, 0x200000             /* next 2 MiB */
    loop  .fill_pd

    /* Load CR3 = PML4 physical address */
    mov   eax, OFFSET _boot_pml4
    mov   cr3, eax

    /* CR4.PAE = 1 */
    mov   eax, cr4
    or    eax, 0x20
    mov   cr4, eax

    /* EFER.LME = 1  (IA32_EFER MSR 0xC0000080, bit 8) */
    mov   ecx, 0xC0000080
    rdmsr
    or    eax, 0x100
    wrmsr

    /* CR0.PG = 1 — activates compatibility (long) mode */
    mov   eax, cr0
    or    eax, 0x80000000
    mov   cr0, eax

    /* Load 64-bit GDT */
    lgdt  [OFFSET _gdt_ptr]

    /* Far jump into 64-bit code segment.
     * Raw encoding: opcode 0xEA + 32-bit offset + 16-bit selector. */
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

    /* Switch to the kernel stack defined by linker_x86.ld */
    mov   rsp, OFFSET _stack_top

    /* Zero BSS.  .boot_pt comes before .bss in the linker script, so
     * [_bss_start, _bss_end) does not include the live page tables. */
    mov   rdi, OFFSET _bss_start
    mov   rcx, OFFSET _bss_end
    sub   rcx, rdi
    xor   eax, eax
    shr   rcx, 3
    rep   stosq

    call  kernel_main

.halt64:
    hlt
    jmp .halt64

/* ── GDT ──────────────────────────────────────────────────────────────────── */

.section .data
.align 16
_gdt:
    .quad 0                       /* 0x00 null */
    .quad 0x00af9a000000ffff      /* 0x08 code64 (L=1 P=1 DPL=0) */
    .quad 0x00af92000000ffff      /* 0x10 data64 (P=1 DPL=0 R/W) */
_gdt_end:

/* GDTR: 16-bit limit + 32-bit base (kernel loads < 4 GiB) */
_gdt_ptr:
    .word _gdt_end - _gdt - 1
    .long _gdt

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
    call  _timer_tick           /* increments TICKS + sends master PIC EOI */
    pop   r11
    pop   r10
    pop   r9
    pop   r8
    pop   rsi
    pop   rdi
    pop   rdx
    pop   rcx
    pop   rax
    iretq

.global _isr_fault
_isr_fault:
    hlt
    jmp _isr_fault

/* ── Boot page tables (placed before .bss by linker_x86.ld) ──────────────── */

.section .boot_pt, "aw"
.align 4096
.global _boot_pml4
_boot_pml4: .space 4096
.global _boot_pdpt
_boot_pdpt: .space 4096
.global _boot_pd
_boot_pd:   .space 4096
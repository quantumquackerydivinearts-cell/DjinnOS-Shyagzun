/* DjinnOS kernel — x86_64 (multiboot2 ELF64 + multiboot1 flat binary fallback)
 * Load address: 1 MiB (0x100000).
 *
 * Section order matters:
 *   .note.Xen     PVH ELF note (QEMU 9+ direct load experiment — harmless)
 *   .text         multiboot2 + multiboot1 headers, then _start + 64-bit code
 *   .rodata
 *   .data         GDT, saved MB2 ptr
 *   .boot_pt      Six 4 KiB page tables — BEFORE .bss so BSS clear is safe
 *   .bss          Zero-initialised data (cleared by _start64)
 *   .stack        256 KiB boot stack
 */

ENTRY(_start)

MEMORY {
    RAM : ORIGIN = 0x1000000, LENGTH = 64M
}

SECTIONS {
    . = 0x1000000;

    .note.Xen : {
        KEEP(*(.note.Xen))
    } > RAM

    .text : {
        KEEP(*(.text.boot))
        *(.text .text.*)
    } > RAM

    .rodata : {
        *(.rodata .rodata.*)
    } > RAM

    /* UEFI entry pointer — 8 bytes read by djinnos-loader at section ".uefi_hdr". */
    .uefi_hdr : {
        KEEP(*(.uefi_hdr))
    } > RAM

    .data : {
        *(.data .data.*)
    } > RAM

    /* Boot page tables — six 4 KiB pages (PML4 + PDPT + PD0–PD3 = 24 KiB).
     * Placed before .bss so that zeroing [_bss_start, _bss_end) never
     * touches live page table data. */
    .boot_pt (NOLOAD) : {
        . = ALIGN(4096);
        *(.boot_pt)
    } > RAM

    .bss (NOLOAD) : {
        _bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        _bss_end = .;
    } > RAM

    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . += 256 * 1024;
        _stack_top = .;
    } > RAM
}

/* DjinnOS kernel — x86_64 (multiboot2, loaded at 1 MiB) */

ENTRY(_start)

MEMORY {
    RAM : ORIGIN = 0x100000, LENGTH = 64M
}

SECTIONS {
    . = 0x100000;

    .note.Xen : {
        KEEP(*(.note.Xen))
    } > RAM

    .text : {
        KEEP(*(.text.boot))    /* multiboot1 header + _start */
        *(.text .text.*)
    } > RAM

    .rodata : {
        *(.rodata .rodata.*)
    } > RAM

    .data : {
        *(.data .data.*)
    } > RAM

    /* Boot page tables: before .bss so zeroing [_bss_start, _bss_end)
       never touches live PML4/PDPT/PD during early init. */
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
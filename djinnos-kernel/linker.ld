/* DjinnOS kernel — RISC-V virt machine memory layout
   QEMU virt places RAM at 0x80000000.
   The byte table lives in .rodata (coordinate space, never mutated). */

MEMORY {
    RAM : ORIGIN = 0x80000000, LENGTH = 128M
}

SECTIONS {
    . = 0x80000000;

    .text : {
        KEEP(*(.text.boot))   /* boot entry must come first */
        *(.text .text.*)
    } > RAM

    .rodata : {
        *(.rodata .rodata.*)
    } > RAM

    .data : {
        *(.data .data.*)
    } > RAM

    .bss (NOLOAD) : {
        _bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        _bss_end = .;
    } > RAM

    /* Boot stack: placed explicitly after all BSS so it never collides with
       the 8 MiB static heap or the per-process stack array.
       256 KiB is ample for the deepest kernel call chains. */
    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . += 256 * 1024;
        _stack_top = .;
    } > RAM
}
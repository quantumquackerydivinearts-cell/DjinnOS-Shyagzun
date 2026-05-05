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

    /* Stack grows downward from 8 MiB mark */
    _stack_top = 0x80000000 + 8 * 1024 * 1024;
}
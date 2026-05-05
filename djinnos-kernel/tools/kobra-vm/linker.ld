/* Kobra VM — links at 0x40020000 (above hello-user at 0x40010000) */
MEMORY {
    RAM : ORIGIN = 0x40020000, LENGTH = 2M
}
SECTIONS {
    . = 0x40020000;
    .text   : { *(.text.start) *(.text .text.*) } > RAM
    .rodata : { *(.rodata .rodata.*)             } > RAM
    .data   : { *(.data   .data.*)               } > RAM
    .bss    : { *(.bss    .bss.*)  *(COMMON)     } > RAM
}
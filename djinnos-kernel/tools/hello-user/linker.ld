/* hello-user linker script
   User VAs live in VPN2=1 space (0x40000000–0x7FFFFFFF).
   Neither kernel gigapage covers this range, so map_page() can build L1/L0
   entries under VPN2=1 freely. */

MEMORY {
    RAM : ORIGIN = 0x40010000, LENGTH = 256K
}

SECTIONS {
    . = 0x40010000;

    .text   : { *(.text.start) *(.text .text.*) } > RAM
    .rodata : { *(.rodata .rodata.*)             } > RAM
    .data   : { *(.data   .data.*)               } > RAM
    .bss    : { *(.bss    .bss.*)  *(COMMON)     } > RAM
}
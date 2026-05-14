/*
 * hopfield_demo.c — Phase 2 example.
 *
 * Demonstrates calling the Hopfield semantic substrate from C.
 * This file is NOT compiled into the kernel binary; it exists to document
 * correct usage of the djinnos.h API.
 *
 * Equivalent to the Rust shell_demo() in intel.rs, but written in C.
 *
 * To compile standalone (on a host with djinnos_c linked):
 *   clang --target=x86_64-unknown-none-elf -ffreestanding -nostdlib \
 *         -I../include -o demo.o -c hopfield_demo.c
 */

#include <djinnos.h>

/* Called from a kernel context — no printf, no malloc, no hosted runtime. */
void hopfield_demo(void)
{
    /* ── Giann query: Rose(2) + Sakura(3) ─────────────────────────────── */
    static uint16_t rose_sakura_out[64];
    size_t n_rose_sakura = 0;

    uint8_t tongues_rs[2] = { 2, 3 };  /* Rose=2, Sakura=3 */

    djinnos_query_by_tongue(
        tongues_rs, 2,
        DJINN_GIANN, 0.0f,
        rose_sakura_out, &n_rose_sakura,
        64
    );

    /* ── Keshi query: Daisy(4) with temperature 2.0 ────────────────────── */
    static uint16_t daisy_out[64];
    size_t n_daisy = 0;

    uint8_t tongue_d[1] = { 4 };   /* Daisy=4 */

    djinnos_query_by_tongue(
        tongue_d, 1,
        DJINN_KESHI, 2.0f,
        daisy_out, &n_daisy,
        64
    );

    /* ── Proximity query around byte address 87 (Ne / Network) ──────────── */
    static uint16_t near_out[16];
    size_t n_near = 0;

    djinnos_query_near(87, 8, near_out, &n_near, 16);

    /* ── Byte table introspection ──────────────────────────────────────── */
    size_t total = djinnos_cand_count();   /* 1358 */

    /* addr, tongue, lotus_gated for the first candidate */
    uint16_t addr0   = djinnos_cand_addr(0);
    uint8_t  tongue0 = djinnos_cand_tongue(0);
    int      lotus0  = djinnos_cand_lotus_gated(0);

    /* Suppress unused-variable warnings in freestanding build. */
    (void)n_rose_sakura; (void)n_daisy; (void)n_near;
    (void)total; (void)addr0; (void)tongue0; (void)lotus0;
}

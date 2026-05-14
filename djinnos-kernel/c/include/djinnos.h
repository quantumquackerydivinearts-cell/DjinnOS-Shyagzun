/*
 * djinnos.h — DjinnOS public C API.
 *
 * Freestanding; safe to include in any kernel C module.
 * Populated incrementally:
 *   Phase 1  — FFI probe (c_add)
 *   Phase 2  — Hopfield / semantic substrate
 *   Phase 3  — Memory allocator, panic
 *   Phase 4  — Streaming platform
 */
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Phase 1: FFI probe ──────────────────────────────────────────────────── */

/** Trivial add — confirms the C↔Rust FFI pipeline end-to-end. */
int c_add(int a, int b);

/* ── Phase 2: Hopfield / semantic substrate ──────────────────────────────── */

/**
 * Djinn operational modes.
 *   DJINN_GIANN    — deterministic energy minimum
 *   DJINN_KESHI    — temperature-driven exploration (use temp field)
 *   DJINN_DROVITTH — temporal gate (use epoch / window fields)
 */
#define DJINN_GIANN    0
#define DJINN_KESHI    1
#define DJINN_DROVITTH 2

/** Query the Hopfield network by tongue numbers.
 *
 *  tongues     : array of tongue numbers to pin (1 = Lotus … 38 = Ledger)
 *  n_tongues   : length of tongues[]
 *  mode        : DJINN_GIANN | DJINN_KESHI | DJINN_DROVITTH
 *  temp        : temperature for DJINN_KESHI (ignored otherwise)
 *  out_addrs   : caller-supplied buffer; receives active byte-table addresses
 *  out_n       : set to number of active candidates written
 *  capacity    : size of out_addrs[]
 *  returns 0 on success, negative on error
 */
int djinnos_query_by_tongue(
    const uint8_t  *tongues,
    size_t          n_tongues,
    uint8_t         mode,
    float           temp,
    uint16_t       *out_addrs,
    size_t         *out_n,
    size_t          capacity
);

/** Query by proximity to a byte-table address. */
int djinnos_query_near(
    uint16_t  addr,
    uint16_t  radius,
    uint16_t *out_addrs,
    size_t   *out_n,
    size_t    capacity
);

/** Total number of candidates in the byte table. */
size_t djinnos_cand_count(void);

/** Address of the i-th candidate (0-based). */
uint16_t djinnos_cand_addr(size_t i);

/** Tongue number of the i-th candidate. */
uint8_t  djinnos_cand_tongue(size_t i);

/** Returns 1 if the i-th candidate is Lotus-gated, 0 otherwise. */
int djinnos_cand_lotus_gated(size_t i);

/* ── Phase 3: Allocator + panic ──────────────────────────────────────────── */

/** Allocate `size` bytes from the kernel heap. Returns NULL on failure. */
void *djinnos_alloc(size_t size);

/** Free a pointer previously returned by djinnos_alloc. */
void  djinnos_free(void *ptr);

/** Abort with a message written to UART. Does not return. */
void  djinnos_abort(const char *msg) __attribute__((noreturn));

/* ── Phase 4: Streaming platform ─────────────────────────────────────────── */

#define STREAM_MAX_COORDS  16   /* max byte-table coordinates per stream */
#define STREAM_ID_LEN      32   /* null-terminated stream ID string */
#define STREAM_LABEL_LEN   64   /* human-readable label */

typedef struct {
    char     id[STREAM_ID_LEN];
    char     label[STREAM_LABEL_LEN];
    uint16_t coords[STREAM_MAX_COORDS];
    uint8_t  n_coords;
    uint8_t  active;
} DjinnStream;

/** Register a stream.  Returns 0 on success, -1 if registry is full. */
int djinnos_stream_register(const DjinnStream *s);

/** Remove a stream by ID.  Returns 0 if found and removed, -1 if not found. */
int djinnos_stream_unregister(const char *id);

/**
 * QCR discovery: given a set of query tongues, run Hopfield convergence and
 * return streams whose coordinates overlap the attractor.
 *
 * tongues     : array of tongue numbers to query
 * n_tongues   : length of tongues[]
 * out         : caller buffer for matching DjinnStream pointers
 * out_n       : set to number of matches
 * capacity    : size of out[]
 * returns 0 on success
 */
int djinnos_stream_discover(
    const uint8_t     *tongues,
    size_t             n_tongues,
    const DjinnStream **out,
    size_t            *out_n,
    size_t             capacity
);

/** HTTP request handler for /api/stream/* routes.
 *  Called by the kernel HTTP server.  Writes response into resp_buf.
 *  Returns the number of bytes written, or 0 on error.
 */
size_t djinnos_stream_handle_http(
    const char *method,
    const char *path,
    const char *body,
    size_t      body_len,
    char       *resp_buf,
    size_t      resp_cap
);

#ifdef __cplusplus
}
#endif

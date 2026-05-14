// stream_platform.rs — Rust glue for the C streaming platform module.
//
// Exports:
//   djinnos_entropy_tick   — C calls this to contribute session entropy to QQEES
//   djinnos_read_ticks     — C reads the LAPIC tick counter for entropy values
//
// The C module (c/streaming/stream_platform.c) owns the stream registry and
// HTTP handler; this file wires it into the kernel's entropy and timing systems.

// ── Entropy tick (QQEES integration) ─────────────────────────────────────────

/// Called from C streaming module when a session contributes entropy.
/// `source_id` is the stream ID (null-terminated); `value` is an entropy sample.
#[no_mangle]
pub extern "C" fn djinnos_entropy_tick(source_id: *const u8, value: u64) {
    if source_id.is_null() { return; }
    // Advance the Sakura eigenstate (orientation / timing) on each session tick.
    crate::eigenstate::advance(crate::eigenstate::T_SAKURA);
    // Log to UART at trace level.
    crate::uart::puts("stream: entropy tick ");
    crate::uart::putx(value);
    crate::uart::puts("\r\n");
}

/// Read the current kernel tick counter — used by C code for entropy seeding.
#[no_mangle]
pub extern "C" fn djinnos_read_ticks() -> u64 {
    crate::arch::read_mtime()
}

// ── HTTP route dispatch ────────────────────────────────────────────────────────

/// Returns true if `path` begins with `/api/stream/`.
pub fn is_stream_route(path: &str) -> bool {
    path.starts_with("/api/stream/") || path == "/api/stream/list"
}

/// Dispatch a streaming HTTP request.
/// When the C module is compiled in, delegates to the C handler.
/// Otherwise returns a 503 stub response.
pub fn handle_stream_request(method: &str, path: &str, body: &[u8]) -> alloc::vec::Vec<u8> {
    #[cfg(c_toolchain_available)]
    {
        extern "C" {
            fn djinnos_stream_handle_http(
                method:   *const u8, path:     *const u8,
                body:     *const u8, body_len: usize,
                resp_buf: *mut u8,   resp_cap: usize,
            ) -> usize;
        }

        let mut m = alloc::vec![0u8; method.len() + 1];
        m[..method.len()].copy_from_slice(method.as_bytes());

        let mut p = alloc::vec![0u8; path.len() + 1];
        p[..path.len()].copy_from_slice(path.as_bytes());

        let mut b = alloc::vec![0u8; body.len() + 1];
        b[..body.len()].copy_from_slice(body);

        let mut resp = alloc::vec![0u8; 8192];
        let n = unsafe {
            djinnos_stream_handle_http(
                m.as_ptr(), p.as_ptr(), b.as_ptr(), body.len(),
                resp.as_mut_ptr(), resp.len(),
            )
        };
        resp.truncate(n);
        return resp;
    }

    #[cfg(not(c_toolchain_available))]
    b"HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\n\r\n\
      {\"error\":\"streaming C module not compiled -- install a C cross-compiler\"}"
        .to_vec()
}

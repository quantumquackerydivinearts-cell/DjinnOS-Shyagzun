// c_api.rs — DjinnOS C API exports (Phases 5–8).
//
// Phase 5: Userspace / process management
// Phase 6: Framebuffer (kernel C modules draw directly)
// Phase 7: Network (tcp socket wrappers for C)
// Phase 8: UART / console output
//
// All functions use extern "C" / #[no_mangle] so they resolve from
// the C toolchain's compiled .a archive and from ring-3 C programs
// that call through the syscall dispatch table.
//
// The framebuffer state is initialised once by djinnos_fb_init() called
// from main.rs after FbDriver is constructed.  Until then fb calls are no-ops.

// ── Framebuffer global ────────────────────────────────────────────────────────

struct CfbState {
    addr:     u64,     // physical linear address of pixel data
    width:    u32,
    height:   u32,
    pitch_px: u32,     // row stride in 32-bit pixels
    r_pos:    u8,
    g_pos:    u8,
    b_pos:    u8,
    ready:    bool,
}

static mut CFB: CfbState = CfbState {
    addr: 0, width: 0, height: 0, pitch_px: 0,
    r_pos: 16, g_pos: 8, b_pos: 0, ready: false,
};

/// Called once from main.rs after FbDriver is initialised.
pub fn djinnos_fb_init(
    addr:     u64,
    width:    u32,
    height:   u32,
    pitch_px: u32,
    r_pos:    u8,
    g_pos:    u8,
    b_pos:    u8,
) {
    unsafe {
        CFB = CfbState { addr, width, height, pitch_px, r_pos, g_pos, b_pos, ready: true };
    }
}

// ── Phase 5: Userspace / Process ──────────────────────────────────────────────

/// Spawn a C function as a new kernel-mode cooperative process.
///
/// `fn_ptr`   : address of `void fn(uint64_t arg)` — must be a valid kernel fn.
/// `coord`    : byte-table address used as process identity (e.g. 19 = Ko).
/// `arg`      : passed to fn_ptr as first argument.
/// Returns 0 on success, -1 if the process table is full.
#[no_mangle]
pub extern "C" fn djinnos_spawn_fn(fn_ptr: u64, coord: u32, arg: u64) -> i32 {
    // Transmute the raw fn pointer into the type process::spawn expects.
    // Safety: caller guarantees fn_ptr points to a valid kernel function.
    let entry: fn(u64) -> ! = unsafe { core::mem::transmute(fn_ptr) };
    match crate::process::spawn(coord, entry, arg) {
        Some(_) => 0,
        None    => -1,
    }
}

/// Load a static ELF binary and run it in ring-3 (x86-64) or user-mode (riscv64).
///
/// Blocks until the user process exits via `djinnos_exit()`.
/// Returns 0 on success, -1 if ELF parsing or memory allocation fails.
#[no_mangle]
pub extern "C" fn djinnos_spawn_elf(data: *const u8, len: usize) -> i32 {
    if data.is_null() || len == 0 { return -1; }
    let slice = unsafe { core::slice::from_raw_parts(data, len) };
    #[cfg(target_arch = "x86_64")]
    { match crate::process::spawn_elf_x86(slice) { Some(_) => 0, None => -1 } }
    #[cfg(not(target_arch = "x86_64"))]
    { match crate::process::spawn_elf(0, slice) { Some(_) => 0, None => -1 } }
}

/// Cooperatively yield the CPU to the next ready process.
#[no_mangle]
pub extern "C" fn djinnos_yield() {
    crate::process::yield_now();
}

/// Return the byte-table coordinate of the currently running process.
#[no_mangle]
pub extern "C" fn djinnos_current_coord() -> u32 {
    crate::process::current_id().0
}

/// Expand the flat user heap by `incr` bytes.
/// Returns the previous break (base of the newly allocated region).
/// Returns UINT64_MAX on OOM.
#[no_mangle]
pub extern "C" fn djinnos_sbrk(incr: usize) -> u64 {
    crate::arch::user_sbrk(incr)
}

// ── Phase 6: Framebuffer ──────────────────────────────────────────────────────

#[no_mangle]
pub extern "C" fn djinnos_fb_width() -> u32 {
    unsafe { if CFB.ready { CFB.width } else { 0 } }
}

#[no_mangle]
pub extern "C" fn djinnos_fb_height() -> u32 {
    unsafe { if CFB.ready { CFB.height } else { 0 } }
}

/// Write one RGB pixel at (x, y).  Out-of-bounds writes are silently dropped.
#[no_mangle]
pub extern "C" fn djinnos_fb_put_pixel(x: u32, y: u32, r: u8, g: u8, b: u8) {
    unsafe {
        let fb = &CFB;
        if !fb.ready || x >= fb.width || y >= fb.height { return; }
        let pixel = (r as u32) << fb.r_pos
                  | (g as u32) << fb.g_pos
                  | (b as u32) << fb.b_pos;
        let ptr = fb.addr as *mut u32;
        core::ptr::write_volatile(ptr.add((y * fb.pitch_px + x) as usize), pixel);
    }
}

/// Fill a rectangle with a solid RGB colour.  Clips to framebuffer bounds.
#[no_mangle]
pub extern "C" fn djinnos_fb_fill_rect(x: u32, y: u32, w: u32, h: u32, r: u8, g: u8, b: u8) {
    unsafe {
        let fb = &CFB;
        if !fb.ready { return; }
        let pixel = (r as u32) << fb.r_pos
                  | (g as u32) << fb.g_pos
                  | (b as u32) << fb.b_pos;
        let ptr = fb.addr as *mut u32;
        let x1 = (x + w).min(fb.width);
        let y1 = (y + h).min(fb.height);
        for row in y..y1 {
            for col in x..x1 {
                core::ptr::write_volatile(ptr.add((row * fb.pitch_px + col) as usize), pixel);
            }
        }
    }
}

/// Draw a null-terminated ASCII string at (x, y) using the kernel's 8×8 font.
/// Returns the x coordinate just past the last character drawn.
#[no_mangle]
pub extern "C" fn djinnos_fb_text(x: u32, y: u32, text: *const u8, r: u8, g: u8, b: u8) -> u32 {
    if text.is_null() { return x; }
    let s = unsafe { cstr_bytes(text) };
    unsafe {
        let fb = &CFB;
        if !fb.ready { return x; }
    }
    // Route through render2d so we share the kernel font.
    // Build a temporary GpuSurface adaptor over the raw CFB state.
    let adaptor = CfbAdaptor;
    let it = crate::render2d::It::new(&adaptor);
    if let Ok(txt) = core::str::from_utf8(s) {
        it.text(x, y, txt, 1, (r, g, b));
    }
    x + s.len() as u32 * 8
}

// Minimal GpuSurface adaptor over the static CFB so render2d can drive it.
struct CfbAdaptor;
impl crate::gpu::GpuSurface for CfbAdaptor {
    fn width(&self)  -> u32 { unsafe { CFB.width } }
    fn height(&self) -> u32 { unsafe { CFB.height } }
    fn set_pixel(&self, x: u32, y: u32, b: u8, g: u8, r: u8) {
        djinnos_fb_put_pixel(x, y, r, g, b);
    }
    fn fill(&self, b: u8, g: u8, r: u8) {
        unsafe {
            djinnos_fb_fill_rect(0, 0, CFB.width, CFB.height, r, g, b);
        }
    }
    fn flush(&mut self) {}
}

// ── Phase 7: Network ──────────────────────────────────────────────────────────
// TCP uses crate::net which resolves to x86net on x86_64 and virtio-net on riscv64.

/// Open a TCP socket and begin connecting to ip0.ip1.ip2.ip3:port.
/// Returns a file descriptor, or u64::MAX on failure.
#[no_mangle]
pub extern "C" fn djinnos_tcp_connect(
    ip0: u8, ip1: u8, ip2: u8, ip3: u8,
    port: u16,
) -> u64 {
    let fd = crate::net::tcp_socket(0);
    if fd == u64::MAX { return u64::MAX; }
    crate::net::tcp_connect(fd, [ip0, ip1, ip2, ip3], port);
    fd
}

/// Returns 1 if the connection is established and ready for I/O, 0 otherwise.
#[no_mangle]
pub extern "C" fn djinnos_tcp_ready(fd: u64) -> i32 {
    if crate::net::tcp_ready(fd) { 1 } else { 0 }
}

/// Send `len` bytes from `data`.  Returns bytes actually sent.
#[no_mangle]
pub extern "C" fn djinnos_tcp_send(fd: u64, data: *const u8, len: usize) -> usize {
    if data.is_null() || len == 0 { return 0; }
    let slice = unsafe { core::slice::from_raw_parts(data, len) };
    crate::net::tcp_send(fd, slice)
}

/// Receive up to `cap` bytes into `buf`.  Returns bytes received (0 = none ready).
#[no_mangle]
pub extern "C" fn djinnos_tcp_recv(fd: u64, buf: *mut u8, cap: usize) -> usize {
    if buf.is_null() || cap == 0 { return 0; }
    let slice = unsafe { core::slice::from_raw_parts_mut(buf, cap) };
    crate::net::tcp_recv(fd, slice)
}

/// Close a TCP socket.
#[no_mangle]
pub extern "C" fn djinnos_tcp_close(fd: u64) {
    crate::net::tcp_close(fd);
}

// ── Phase 9: JavaScript (QuickJS via Faerie) ─────────────────────────────────

/// Evaluate a JavaScript expression and write the result as a string into `out`.
/// Returns 0 on success, -1 on error (error message in `out`).
/// Gate: only available when QuickJS was compiled in (quickjs_available cfg).
#[cfg(all(quickjs_available, target_arch = "x86_64"))]
#[no_mangle]
pub extern "C" fn djinnos_js_eval_rs(
    src: *const u8, src_len: usize,
    out: *mut u8,   out_cap:  usize,
) -> i32 {
    if src.is_null() || out.is_null() || out_cap == 0 { return -1; }
    unsafe {
        djinnos_js_eval(src as *const i8, src_len, out as *mut i8, out_cap)
    }
}

/// Evaluate JS with a minimal DOM (document.write accumulates HTML).
/// The accumulated HTML is written into `html_out`.
#[cfg(all(quickjs_available, target_arch = "x86_64"))]
#[no_mangle]
pub extern "C" fn djinnos_js_eval_dom_rs(
    src:      *const u8, src_len:  usize,
    html_out: *mut u8,   html_cap: usize,
) -> i32 {
    if src.is_null() || html_out.is_null() || html_cap == 0 { return -1; }
    unsafe {
        djinnos_js_eval_dom(src as *const i8, src_len,
                            html_out as *mut i8, html_cap)
    }
}

#[cfg(all(quickjs_available, target_arch = "x86_64"))]
unsafe extern "C" {
    fn djinnos_js_eval(src: *const i8, len: usize,
                       out: *mut i8, cap: usize) -> i32;
    fn djinnos_js_eval_dom(src: *const i8, len: usize,
                           out: *mut i8, cap: usize) -> i32;
}

// ── Phase 8: UART / console ───────────────────────────────────────────────────

/// Write a null-terminated string to the UART console.
#[no_mangle]
pub extern "C" fn djinnos_puts(msg: *const u8) {
    if msg.is_null() { return; }
    let s = unsafe { cstr_bytes(msg) };
    crate::uart::puts_bytes(s);
}

/// Write exactly `len` bytes to UART (no null terminator required).
#[no_mangle]
pub extern "C" fn djinnos_write_uart(data: *const u8, len: usize) {
    if data.is_null() || len == 0 { return; }
    let slice = unsafe { core::slice::from_raw_parts(data, len) };
    crate::uart::puts_bytes(slice);
}

// ── Internal helpers ──────────────────────────────────────────────────────────

/// Read a null-terminated C string into a byte slice without allocating.
unsafe fn cstr_bytes(ptr: *const u8) -> &'static [u8] {
    let mut len = 0usize;
    while *ptr.add(len) != 0 { len += 1; }
    core::slice::from_raw_parts(ptr, len)
}

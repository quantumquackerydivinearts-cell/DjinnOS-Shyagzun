// stream.rs — DjinnOS native stream broadcaster.
//
// Maintains a persistent outbound TCP connection to a stream relay service.
// Pushes downsampled framebuffer captures and semantic events.  The relay
// handles internet delivery, transcoding, and viewer auth (QCR guild model).
//
// Wire protocol — all multi-byte values little-endian:
//
//   [4]  magic  : b"DJNX"
//   [1]  type   : PKT_FRAME | PKT_SEMANTIC | PKT_KEEPALIVE | PKT_META
//   [4]  length : payload bytes (u32 LE)
//   [N]  payload
//
// PKT_FRAME payload:
//   [2]  width  (u16 LE)
//   [2]  height (u16 LE)
//   [N]  RGB bytes, R-G-B per pixel, row-major
//
// PKT_SEMANTIC payload: UTF-8 JSON — {"ev":"<type>",...}
// PKT_META     payload: UTF-8 JSON — stream metadata sent on connect
// PKT_KEEPALIVE: empty (length = 0)
//
// Caller integration (main.rs):
//   stream::configure([relay_ip], relay_port);  // once
//   stream::start();                             // begin connecting
//   // inside main loop:
//   stream::poll(Some(&fbdrv as &dyn gpu::GpuSurface));
//
// Other modules emit semantic events with:
//   stream::push_semantic(b"quest_state", b"\"id\":\"0009_KLST\",\"status\":\"in_progress\"");
//   stream::push_semantic(b"shygazun_word", b"\"symbol\":\"Ko\",\"tongue\":\"Lotus\"");

use crate::gpu::GpuSurface;

// ── Wire constants ────────────────────────────────────────────────────────────

const MAGIC:         &[u8; 4] = b"DJNX";
const PKT_FRAME:     u8       = 0x01;
const PKT_SEMANTIC:  u8       = 0x02;
const PKT_KEEPALIVE: u8       = 0x04;
const PKT_META:      u8       = 0x05;

// ── Stream parameters ─────────────────────────────────────────────────────────

// Capture resolution — 16:9, 1/6th native on each axis ≈ 170 KB/frame uncompressed.
const STREAM_W:    u32   = 320;
const STREAM_H:    u32   = 180;
const FRAME_BYTES: usize = (STREAM_W * STREAM_H * 3) as usize;

// Max bytes per chunk pushed to the NIC in one call — stays within Ethernet MSS.
const CHUNK:       usize = 1400;

// Emit one frame every N poll() calls.  At a ~500Hz main loop this ≈ 10fps.
const FRAME_EVERY: u32   = 50;

// Send a keepalive every N poll() calls if no other data is sent.
const KA_EVERY:    u32   = 300;

// Give up connecting and retry after this many poll() calls.
const CONNECT_TIMEOUT: u32 = 1500;

// ── Event queue ───────────────────────────────────────────────────────────────

const QUEUE_SLOTS: usize = 16;
const EVENT_MAX:   usize = 480;  // max payload bytes per semantic event

#[derive(Copy, Clone)]
struct EvSlot {
    ty:   u8,
    len:  u16,
    data: [u8; EVENT_MAX],
}

impl EvSlot {
    const fn new() -> Self {
        EvSlot { ty: 0, len: 0, data: [0u8; EVENT_MAX] }
    }
}

const INIT_EV: EvSlot = EvSlot::new();

// ── Stream metadata ───────────────────────────────────────────────────────────

const TITLE_MAX:   usize = 64;
const TONGUES_MAX: usize = 16;

static mut STREAM_TITLE:    [u8;  TITLE_MAX]   = [0u8;  TITLE_MAX];
static mut STREAM_TITLE_LEN: usize             = 0;
static mut STREAM_TONGUES:  [u16; TONGUES_MAX] = [0u16; TONGUES_MAX];
static mut STREAM_TONGUE_N: usize              = 0;

/// Set the stream title (shown to witnesses, included in META packet).
pub fn set_title(title: &[u8]) {
    unsafe {
        let n = title.len().min(TITLE_MAX);
        STREAM_TITLE[..n].copy_from_slice(&title[..n]);
        STREAM_TITLE_LEN = n;
    }
}

/// Set the tongue numbers that describe this stream's semantic register.
/// Used by QCR discovery on the relay.
pub fn set_tongues(tongues: &[u16]) {
    unsafe {
        let n = tongues.len().min(TONGUES_MAX);
        STREAM_TONGUES[..n].copy_from_slice(&tongues[..n]);
        STREAM_TONGUE_N = n;
    }
}

/// Current stream title as a byte slice.
pub fn title() -> &'static [u8] {
    unsafe { &STREAM_TITLE[..STREAM_TITLE_LEN] }
}

/// Current relay IP.
pub fn relay_ip() -> [u8; 4] { unsafe { RELAY_IP } }

/// Current relay port.
pub fn relay_port() -> u16 { unsafe { RELAY_PORT } }

/// Entropy ticks emitted this session (frame count proxy).
pub fn frame_tick() -> u32 { unsafe { FRAME_TICK } }

// ── Static state ──────────────────────────────────────────────────────────────

static mut RELAY_IP:    [u8; 4]          = [127, 0, 0, 1];
static mut RELAY_PORT:  u16              = 7700;
static mut ACTIVE:      bool             = false;
static mut STREAM_FD:   u64             = u64::MAX;
static mut ESTABLISHED: bool             = false;
static mut CONN_TICKS:  u32             = 0;
static mut FRAME_TICK:  u32             = 0;
static mut KA_TICK:     u32             = 0;
static mut FRAME_BUF:   [u8; FRAME_BYTES] = [0u8; FRAME_BYTES];
static mut EV_QUEUE:    [EvSlot; QUEUE_SLOTS] = [INIT_EV; QUEUE_SLOTS];
static mut EV_HEAD:     usize           = 0;
static mut EV_TAIL:     usize           = 0;

// ── Public API ────────────────────────────────────────────────────────────────

/// Set relay address before calling start().
pub fn configure(ip: [u8; 4], port: u16) {
    unsafe { RELAY_IP = ip; RELAY_PORT = port; }
}

/// Begin connecting to the relay.  Safe to call multiple times.
pub fn start() {
    unsafe { ACTIVE = true; }
    crate::uart::puts("stream: active — will connect to relay\r\n");
}

/// Stop streaming and close the connection.
pub fn stop() {
    unsafe {
        ACTIVE = false;
        drop_connection();
    }
    crate::uart::puts("stream: stopped\r\n");
}

/// True when the relay connection is established and data is flowing.
pub fn is_live() -> bool {
    unsafe { ACTIVE && ESTABLISHED }
}

/// Queue a semantic event.  Non-blocking; drops silently if the ring is full.
///
/// ev_type : short ASCII label, e.g. b"quest_state"
/// fields  : JSON field pairs WITHOUT surrounding braces,
///           e.g. b"\"id\":\"0009_KLST\",\"status\":\"in_progress\""
pub fn push_semantic(ev_type: &[u8], fields: &[u8]) {
    unsafe {
        let next = (EV_HEAD + 1) % QUEUE_SLOTS;
        if next == EV_TAIL { return; }  // ring full — drop

        let slot = &mut EV_QUEUE[EV_HEAD];
        slot.ty  = PKT_SEMANTIC;
        let mut pos = 0usize;

        wb(&mut slot.data, &mut pos, b"{\"ev\":\"");
        wb(&mut slot.data, &mut pos, ev_type);
        if fields.is_empty() {
            wb(&mut slot.data, &mut pos, b"\"}");
        } else {
            wb(&mut slot.data, &mut pos, b"\",");
            wb(&mut slot.data, &mut pos, fields);
            wb(&mut slot.data, &mut pos, b"}");
        }
        slot.len = pos as u16;
        EV_HEAD  = next;
    }
}

/// Drive the stream connection, flush queued events, and emit a frame.
/// Call once per main-loop iteration.  Pass None for gpu to suppress frame capture.
pub fn poll(gpu: Option<&dyn GpuSurface>) {
    if !unsafe { ACTIVE } { return; }

    let fd = ensure_fd();
    if fd == u64::MAX { return; }               // FD just allocated — wait for handshake

    if !crate::x86net::tcp_ready(fd) {
        unsafe {
            if ESTABLISHED {
                // Connection was up — peer closed or RST.
                drop_connection();
            } else {
                CONN_TICKS += 1;
                if CONN_TICKS > CONNECT_TIMEOUT {
                    crate::uart::puts("stream: connect timeout — retrying\r\n");
                    drop_connection();
                }
            }
        }
        return;
    }

    // Newly established?
    if !unsafe { ESTABLISHED } {
        unsafe { ESTABLISHED = true; CONN_TICKS = 0; KA_TICK = 0; }
        crate::uart::puts("stream: relay connected\r\n");
        send_meta(fd);
    }

    flush_events(fd);

    if let Some(g) = gpu {
        unsafe {
            FRAME_TICK += 1;
            if FRAME_TICK >= FRAME_EVERY {
                FRAME_TICK = 0;
                capture_frame(g, &mut FRAME_BUF);
                send_frame(fd, &FRAME_BUF);
            }
            KA_TICK += 1;
            if KA_TICK >= KA_EVERY {
                KA_TICK = 0;
                send_packet(fd, PKT_KEEPALIVE, &[]);
            }
        }
    }
}

// ── Connection management ─────────────────────────────────────────────────────

/// Ensure a TCP fd exists.  Returns MAX if the fd was just created (not ready).
fn ensure_fd() -> u64 {
    unsafe {
        if STREAM_FD != u64::MAX { return STREAM_FD; }

        let fd = crate::x86net::tcp_socket(0);
        if fd == u64::MAX {
            crate::uart::puts("stream: no socket slot\r\n");
            return u64::MAX;
        }

        let ip   = RELAY_IP;
        let port = RELAY_PORT;
        crate::x86net::tcp_connect(fd, ip, port);
        STREAM_FD  = fd;
        CONN_TICKS = 0;
        u64::MAX    // not established yet
    }
}

unsafe fn drop_connection() {
    if STREAM_FD != u64::MAX {
        crate::x86net::tcp_close(STREAM_FD);
        STREAM_FD = u64::MAX;
    }
    ESTABLISHED = false;
    CONN_TICKS  = 0;
    FRAME_TICK  = 0;
    KA_TICK     = 0;
}

// ── Packet construction ───────────────────────────────────────────────────────

fn send_packet(fd: u64, pkt_type: u8, payload: &[u8]) {
    let mut hdr = [0u8; 9];
    hdr[0..4].copy_from_slice(MAGIC);
    hdr[4] = pkt_type;
    hdr[5..9].copy_from_slice(&(payload.len() as u32).to_le_bytes());
    send_all(fd, &hdr);
    if !payload.is_empty() {
        send_all(fd, payload);
    }
}

fn send_all(fd: u64, data: &[u8]) {
    let mut off = 0;
    while off < data.len() {
        let end  = (off + CHUNK).min(data.len());
        let sent = crate::x86net::tcp_send(fd, &data[off..end]);
        if sent == 0 { break; }
        off += sent;
    }
}

fn send_meta(fd: u64) {
    let mut buf = [0u8; 256];
    let mut pos = 0usize;
    let ip = crate::net_stack::our_ip();

    wb(&mut buf, &mut pos, b"{\"type\":\"djinnos_stream\",\"game\":\"7_KLGS\",\"version\":1");

    // Stream title
    unsafe {
        if STREAM_TITLE_LEN > 0 {
            wb(&mut buf, &mut pos, b",\"title\":\"");
            wb(&mut buf, &mut pos, &STREAM_TITLE[..STREAM_TITLE_LEN]);
            wb(&mut buf, &mut pos, b"\"");
        }
    }

    // Tongue coordinates for QCR discovery
    unsafe {
        if STREAM_TONGUE_N > 0 {
            wb(&mut buf, &mut pos, b",\"tongues\":[");
            for i in 0..STREAM_TONGUE_N {
                if i > 0 { wb(&mut buf, &mut pos, b","); }
                wu32(&mut buf, &mut pos, STREAM_TONGUES[i] as u32);
            }
            wb(&mut buf, &mut pos, b"]");
        }
    }

    wb(&mut buf, &mut pos, b",\"w\":");
    wu32(&mut buf, &mut pos, STREAM_W);
    wb(&mut buf, &mut pos, b",\"h\":");
    wu32(&mut buf, &mut pos, STREAM_H);
    wb(&mut buf, &mut pos, b",\"fps\":10,\"src\":\"");
    wip(&mut buf, &mut pos, ip);
    wb(&mut buf, &mut pos, b"\"}");

    send_packet(fd, PKT_META, &buf[..pos]);
}

fn send_frame(fd: u64, rgb: &[u8]) {
    // Header + dimension prefix in one allocation to avoid two small sends.
    let mut hdr = [0u8; 13];  // 9 wire hdr + 4 dim
    hdr[0..4].copy_from_slice(MAGIC);
    hdr[4] = PKT_FRAME;
    let total = 4 + rgb.len();
    hdr[5..9].copy_from_slice(&(total as u32).to_le_bytes());
    hdr[9..11].copy_from_slice(&(STREAM_W as u16).to_le_bytes());
    hdr[11..13].copy_from_slice(&(STREAM_H as u16).to_le_bytes());
    send_all(fd, &hdr);
    send_all(fd, rgb);
}

fn flush_events(fd: u64) {
    unsafe {
        while EV_TAIL != EV_HEAD {
            let slot = &EV_QUEUE[EV_TAIL];
            send_packet(fd, slot.ty, &slot.data[..slot.len as usize]);
            EV_TAIL = (EV_TAIL + 1) % QUEUE_SLOTS;
        }
    }
}

// ── Frame capture ─────────────────────────────────────────────────────────────

fn capture_frame(gpu: &dyn GpuSurface, buf: &mut [u8]) {
    let src_w  = gpu.width();
    let src_h  = gpu.height();
    // Integer step — sample evenly across the source resolution.
    let step_x = (src_w / STREAM_W).max(1);
    let step_y = (src_h / STREAM_H).max(1);
    let mut out = 0usize;
    for dy in 0..STREAM_H {
        let sy = (dy * step_y).min(src_h - 1);
        for dx in 0..STREAM_W {
            let sx = (dx * step_x).min(src_w - 1);
            let (b, g, r) = gpu.get_pixel(sx, sy);  // FbDriver returns (b,g,r) BGR order
            if out + 2 < buf.len() {
                buf[out]     = r;
                buf[out + 1] = g;
                buf[out + 2] = b;
            }
            out += 3;
        }
    }
}

// ── Write helpers (no alloc, no format!) ─────────────────────────────────────

/// Append bytes to a fixed buffer at *pos, silently truncating at capacity.
#[inline]
fn wb(buf: &mut [u8], pos: &mut usize, s: &[u8]) {
    for &b in s {
        if *pos < buf.len() { buf[*pos] = b; *pos += 1; }
    }
}

fn wu32(buf: &mut [u8], pos: &mut usize, mut n: u32) {
    if n == 0 { wb(buf, pos, b"0"); return; }
    let mut tmp = [0u8; 10];
    let mut len = 0usize;
    while n > 0 { tmp[len] = b'0' + (n % 10) as u8; n /= 10; len += 1; }
    for i in (0..len).rev() {
        if *pos < buf.len() { buf[*pos] = tmp[i]; *pos += 1; }
    }
}

fn wip(buf: &mut [u8], pos: &mut usize, ip: [u8; 4]) {
    for (i, &octet) in ip.iter().enumerate() {
        wu32(buf, pos, octet as u32);
        if i < 3 { wb(buf, pos, b"."); }
    }
}

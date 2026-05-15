// UART abstraction.
//
// RISC-V: 16550A mapped at 0x10000000 (QEMU virt MMIO).
// x86_64:  COM1 at I/O port 0x3F8 (16550A, programmed by arch::uart_init).

#[cfg(target_arch = "riscv64")]
const UART_MMIO: *mut u8 = 0x10000000 as *mut u8;

// ── Ring buffer — captures last 8 KiB of UART output ─────────────────────────
// Shell `log` command reads this to display diagnostic output on screen.

const RING_SZ: usize = 8 * 1024;
static mut RING: [u8; RING_SZ] = [0u8; RING_SZ];
static mut RING_W: usize = 0;
static mut RING_FULL: bool = false;

fn ring_push(b: u8) {
    unsafe {
        RING[RING_W] = b;
        RING_W += 1;
        if RING_W >= RING_SZ { RING_W = 0; RING_FULL = true; }
    }
}

/// Copy up to `out.len()` bytes of recent log into `out`.
/// Returns the number of bytes written and whether the buffer wrapped.
pub fn recent_log(out: &mut [u8]) -> (usize, bool) {
    unsafe {
        if !RING_FULL {
            let n = RING_W.min(out.len());
            out[..n].copy_from_slice(&RING[..n]);
            (n, false)
        } else {
            // Wrapped: data runs from RING_W..RING_SZ then 0..RING_W.
            let tail = RING_SZ - RING_W;
            let head = RING_W;
            let total = tail + head;
            let skip = if total > out.len() { total - out.len() } else { 0 };
            let mut wi = 0usize;
            // Copy tail portion (older data), skipping if needed.
            let tail_skip = skip.min(tail);
            for i in (RING_W + tail_skip)..RING_SZ {
                if wi < out.len() { out[wi] = RING[i]; wi += 1; }
            }
            // Copy head portion.
            let head_skip = skip.saturating_sub(tail);
            for i in head_skip..RING_W {
                if wi < out.len() { out[wi] = RING[i]; wi += 1; }
            }
            (wi, true)
        }
    }
}

pub fn putc(byte: u8) {
    ring_push(byte);

    #[cfg(target_arch = "riscv64")]
    unsafe { UART_MMIO.write_volatile(byte) }

    #[cfg(target_arch = "x86_64")]
    crate::arch::uart_putc(byte);
}

/// Non-blocking read — returns None if no byte waiting.
#[allow(dead_code)]
pub fn getc() -> Option<u8> {
    #[cfg(target_arch = "riscv64")]
    { None }  // RISC-V uses VirtIO keyboard, not UART input

    #[cfg(target_arch = "x86_64")]
    crate::arch::uart_getc()
}

pub fn puts(s: &str) {
    for b in s.bytes() { putc(b); }
}

pub fn puts_bytes(s: &[u8]) {
    for &b in s { putc(b); }
}

pub fn putc_char(c: u8) { putc(c); }

pub fn putu(mut n: u64) {
    if n == 0 { putc(b'0'); return; }
    let mut buf = [0u8; 20];
    let mut i = 20usize;
    while n > 0 {
        i -= 1;
        buf[i] = b'0' + (n % 10) as u8;
        n /= 10;
    }
    for &b in &buf[i..] { putc(b); }
}

pub fn putx(mut n: u64) {
    let digits = b"0123456789abcdef";
    let mut buf = [0u8; 16];
    let mut i = 16usize;
    if n == 0 { putc(b'0'); return; }
    while n > 0 {
        i -= 1;
        buf[i] = digits[(n & 0xf) as usize];
        n >>= 4;
    }
    for &b in &buf[i..] { putc(b); }
}
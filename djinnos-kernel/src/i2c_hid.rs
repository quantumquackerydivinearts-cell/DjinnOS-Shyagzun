// i2c_hid.rs — I2C HID trackpad driver for HP Envy
//
// Hardware path:
//   Intel LPSS DesignWare I2C controller (PCI, BAR0 = 4 KiB MMIO)
//   → I2C HID Protocol Specification 1.0
//   → ELAN / Synaptics trackpad
//
// PCI scan order: Kaby/Whiskey Lake → Ice Lake → Comet Lake → Tiger Lake.
// Trackpad probe order: ELAN 0x15 → Synaptics 0x2C → ELAN alt 0x38/0x70.
// HID descriptor register: 0x0001 (ELAN), 0x0020 (Synaptics).
//
// I2C HID combined transaction:
//   Write 2-byte register addr → repeated START → read N bytes
//
// Main loop calls i2c_hid::init() once after ps2::init().
// Then calls i2c_hid::poll() each iteration + drains poll_mouse().

use crate::input::MouseEvent;
use crate::uart;

// ── DW I2C register offsets ───────────────────────────────────────────────────

const IC_CON:           u32 = 0x000;
const IC_TAR:           u32 = 0x004;
const IC_DATA_CMD:      u32 = 0x010;
const IC_FS_SCL_HCNT:   u32 = 0x01C;
const IC_FS_SCL_LCNT:   u32 = 0x020;
const IC_CLR_INTR:      u32 = 0x040;
const IC_ENABLE:        u32 = 0x06C;
const IC_STATUS:        u32 = 0x070;
const IC_TXFLR:         u32 = 0x074;
const IC_RXFLR:         u32 = 0x078;
const IC_TX_ABRT_SRC:   u32 = 0x080;

// IC_CON configuration: master, fast-mode, restart enable, slave disabled
const CON_MASTER:     u32 = 1 << 0;
const CON_SPEED_FAST: u32 = 2 << 1;   // bits [2:1] = 10
const CON_RESTART_EN: u32 = 1 << 5;
const CON_SLAVE_DIS:  u32 = 1 << 6;
const IC_CON_INIT: u32 = CON_MASTER | CON_SPEED_FAST | CON_RESTART_EN | CON_SLAVE_DIS;

// IC_STATUS bits
const STATUS_TFNF: u32 = 1 << 1;   // TX FIFO not full
const STATUS_TFE:  u32 = 1 << 2;   // TX FIFO empty
const STATUS_RFNE: u32 = 1 << 3;   // RX FIFO not empty

// IC_DATA_CMD flags
const CMD_READ:    u32 = 1 << 8;
const CMD_STOP:    u32 = 1 << 9;
const CMD_RESTART: u32 = 1 << 10;

// ── LPSS I2C PCI IDs ──────────────────────────────────────────────────────────

const LPSS_IDS: &[(u16, u16, &str)] = &[
    (0x8086, 0x9D61, "KBL/WHL I2C1"),
    (0x8086, 0x9D60, "KBL/WHL I2C0"),
    (0x8086, 0x9D62, "KBL/WHL I2C2"),
    (0x8086, 0x9D63, "KBL/WHL I2C3"),
    (0x8086, 0x34E9, "ICL I2C1"),
    (0x8086, 0x34E8, "ICL I2C0"),
    (0x8086, 0x02E9, "CML I2C1"),
    (0x8086, 0x02E8, "CML I2C0"),
    (0x8086, 0xA0C6, "TGL I2C1"),
    (0x8086, 0xA0C5, "TGL I2C0"),
    (0x8086, 0x51E9, "ADL I2C1"),
    (0x8086, 0x51E8, "ADL I2C0"),
];

// ── Trackpad probe table ──────────────────────────────────────────────────────

const TP_PROBES: &[(u8, u16, &str)] = &[
    (0x15, 0x0001, "ELAN"),
    (0x2C, 0x0020, "Synaptics"),
    (0x38, 0x0001, "ELAN-38"),
    (0x70, 0x0001, "ELAN-70"),
];

// ── Global state ──────────────────────────────────────────────────────────────

static mut BASE:       u64  = 0;
static mut TP_ADDR:    u8   = 0;
static mut INPUT_REG:  u16  = 0;
static mut RLEN:       u16  = 0;
static mut READY:      bool = false;

// Previous absolute position for delta conversion.
// 0xFFFF = sentinel "finger not down" — reset on lift, set on first contact.
static mut PREV_X: u16 = 0xFFFF;
static mut PREV_Y: u16 = 0xFFFF;

// Consecutive xfer failure counter — triggers controller recovery after MAX_FAILS.
static mut FAIL_COUNT: u8 = 0;
const MAX_FAILS: u8 = 5;

// Sensitivity scale for absolute→relative delta conversion.
// Multiply raw delta by SENS_NUM / SENS_DEN.
// ELAN coords are typically ~3000 wide for a 130 mm trackpad; screen is 1920 px.
// A scale of 3/2 gives 1.5× acceleration for comfortable daily use.
const SENS_NUM: i32 = 3;
const SENS_DEN: i32 = 2;

// Mouse event ring (mirrors ps2.rs layout)
const MRING: usize = 8;
static mut M_RING:  [MouseEvent; MRING] = [MouseEvent { dx: 0, dy: 0, dz: 0, buttons: 0 }; MRING];
static mut M_WHEAD: usize = 0;
static mut M_RTAIL: usize = 0;

fn mouse_push(e: MouseEvent) {
    unsafe {
        let next = (M_WHEAD + 1) % MRING;
        if next != M_RTAIL { M_RING[M_WHEAD] = e; M_WHEAD = next; }
    }
}

pub fn poll_mouse() -> Option<MouseEvent> {
    unsafe {
        if M_RTAIL == M_WHEAD { return None; }
        let e = M_RING[M_RTAIL];
        M_RTAIL = (M_RTAIL + 1) % MRING;
        Some(e)
    }
}

// ── MMIO register helpers ─────────────────────────────────────────────────────

#[inline(always)]
fn rr(off: u32) -> u32 {
    unsafe { ((BASE + off as u64) as *const u32).read_volatile() }
}

#[inline(always)]
fn rw(off: u32, v: u32) {
    unsafe { ((BASE + off as u64) as *mut u32).write_volatile(v) }
}

fn spin(n: u32, ok: impl Fn() -> bool) -> bool {
    for _ in 0..n {
        if ok() { return true; }
        for _ in 0..200 { unsafe { core::arch::asm!("pause", options(nostack, nomem)); } }
    }
    false
}

// ── DW I2C core ───────────────────────────────────────────────────────────────

fn i2c_disable() {
    rw(IC_ENABLE, 0);
    spin(500, || rr(IC_ENABLE) & 1 == 0);
}

fn i2c_enable() {
    rw(IC_ENABLE, 1);
    // Wait until IC_ENABLE bit 0 reads back as 1 (enable took effect).
    spin(500, || rr(IC_ENABLE) & 1 != 0);
}

fn i2c_setup(addr: u8) {
    i2c_disable();
    let _ = rr(IC_TX_ABRT_SRC);
    let _ = rr(IC_CLR_INTR);

    rw(IC_CON, IC_CON_INIT);

    // 400 kHz timing for 19.2 MHz LPSS source clock.
    // t_high ≥ 0.6 µs → ceil(0.6 × 19.2) + 3 = 12 + 3 = 15 cycles
    // t_low  ≥ 1.3 µs → ceil(1.3 × 19.2) + 1 = 25 + 1 = 26 cycles
    rw(IC_FS_SCL_HCNT, 15);
    rw(IC_FS_SCL_LCNT, 26);

    rw(IC_TAR, addr as u32);
    i2c_enable();
}

/// Write bytes then read `rlen` bytes in one combined transaction.
/// Returns None on abort or timeout.
fn xfer(wbuf: &[u8], rlen: u16) -> Option<[u8; 64]> {
    // Drain stale RX
    while rr(IC_RXFLR) > 0 { let _ = rr(IC_DATA_CMD); }
    let _ = rr(IC_TX_ABRT_SRC);

    // Write phase (no STOP — combined transaction)
    for &b in wbuf {
        if !spin(2000, || rr(IC_STATUS) & STATUS_TFNF != 0) { return None; }
        rw(IC_DATA_CMD, b as u32);
    }

    // Read phase: RESTART on first byte, STOP on last
    for i in 0..rlen {
        if !spin(2000, || rr(IC_STATUS) & STATUS_TFNF != 0) { return None; }
        let mut cmd = CMD_READ;
        if i == 0           { cmd |= CMD_RESTART; }
        if i == rlen - 1    { cmd |= CMD_STOP; }
        rw(IC_DATA_CMD, cmd);
    }

    // Collect bytes
    let mut buf = [0u8; 64];
    for i in 0..rlen as usize {
        if !spin(50_000, || rr(IC_RXFLR) > 0) { return None; }
        buf[i] = (rr(IC_DATA_CMD) & 0xFF) as u8;
    }

    if rr(IC_TX_ABRT_SRC) != 0 { return None; }
    Some(buf)
}

// ── I2C HID descriptor ────────────────────────────────────────────────────────
//
// I2C HID 1.0 §5.2: host writes 2-byte descriptor register address, then
// reads 30 bytes.  Byte 0–1 = wHIDDescLength (must equal 0x001E).

fn read_hid_desc(addr: u8, desc_reg: u16) -> Option<(u16, u16)> {
    i2c_setup(addr);
    let reg = [(desc_reg & 0xFF) as u8, (desc_reg >> 8) as u8];
    let buf = xfer(&reg, 30)?;

    let hlen       = u16::from_le_bytes([buf[0],  buf[1]]);
    let input_reg  = u16::from_le_bytes([buf[8],  buf[9]]);
    let max_input  = u16::from_le_bytes([buf[10], buf[11]]);
    let vendor     = u16::from_le_bytes([buf[20], buf[21]]);
    let product    = u16::from_le_bytes([buf[22], buf[23]]);

    if hlen != 0x001E { return None; } // not a valid I2C HID descriptor

    uart::puts("i2c_hid: VID=0x");
    uart::putx(vendor as u64);
    uart::puts(" PID=0x");
    uart::putx(product as u64);
    uart::puts(" input_reg=0x");
    uart::putx(input_reg as u64);
    uart::puts("\r\n");

    Some((input_reg, max_input.max(6).min(64)))
}

// ── Public API ────────────────────────────────────────────────────────────────

pub fn init() -> bool {
    // Find first available LPSS I2C controller
    let dev = 'found: {
        for &(vid, did, name) in LPSS_IDS {
            if let Some(d) = crate::pci::find_id(vid, did) {
                uart::puts("i2c_hid: ");
                uart::puts(name);
                uart::puts("\r\n");
                break 'found d;
            }
        }
        uart::puts("i2c_hid: no LPSS I2C controller\r\n");
        return false;
    };

    // Enable bus master + memory space
    unsafe {
        let cmd = crate::pci::read16(dev.bus, dev.dev, dev.func, 0x04);
        crate::pci::write32(dev.bus, dev.dev, dev.func, 0x04, (cmd | 0x06) as u32);
    }

    // Map BAR0 (64-bit preferred, 32-bit fallback)
    let bar = dev.bar_mem64(0)
        .or_else(|| dev.bar_mem32(0))
        .unwrap_or(0);
    if bar == 0 {
        uart::puts("i2c_hid: BAR0 unmapped\r\n");
        return false;
    }
    unsafe { BASE = bar; }
    uart::puts("i2c_hid: BAR0=0x");
    uart::putx(bar);
    uart::puts("\r\n");

    // Probe known trackpad addresses
    for &(addr, desc_reg, name) in TP_PROBES {
        uart::puts("i2c_hid: probe ");
        uart::puts(name);
        uart::puts(" @0x");
        uart::putx(addr as u64);
        uart::puts("\r\n");

        if let Some((input_reg, rlen)) = read_hid_desc(addr, desc_reg) {
            unsafe {
                TP_ADDR   = addr;
                INPUT_REG = input_reg;
                RLEN      = rlen;
                READY     = true;
            }
            uart::puts("i2c_hid: ");
            uart::puts(name);
            uart::puts(" ready\r\n");
            return true;
        }
    }

    uart::puts("i2c_hid: no trackpad responded\r\n");
    false
}

/// Called each main-loop iteration. Reads one report if available and pushes
/// to the ring. Caller drains via poll_mouse().
///
/// i2c_setup() is NOT called here — the controller is configured once during
/// init() and the target address never changes. Calling i2c_setup() on every
/// poll would disable/re-enable the controller each frame, thrashing the bus.
/// Recovery from persistent failures (TX_ABRT bus hang) re-runs i2c_setup().
pub fn poll() {
    if !unsafe { READY } { return; }

    let (addr, input_reg, rlen) = unsafe { (TP_ADDR, INPUT_REG, RLEN) };
    let reg = [(input_reg & 0xFF) as u8, (input_reg >> 8) as u8];
    let buf = match xfer(&reg, rlen) {
        Some(b) => {
            unsafe { FAIL_COUNT = 0; }
            b
        }
        None => {
            unsafe {
                FAIL_COUNT += 1;
                if FAIL_COUNT >= MAX_FAILS {
                    FAIL_COUNT = 0;
                    // Bus may be hung — reconfigure the controller to recover.
                    i2c_setup(addr);
                }
            }
            return;
        }
    };

    // I2C HID §6.1.1: buf[0..2] = wLength (LE), buf[2] = report ID, buf[3..] = data
    let pkt_len = u16::from_le_bytes([buf[0], buf[1]]) as usize;
    if pkt_len < 4 || pkt_len > rlen as usize { return; }

    let report_id = buf[2];
    let data = &buf[3..pkt_len.min(rlen as usize)];
    if data.is_empty() { return; }

    if let Some(ev) = parse(report_id, data) {
        if ev.dx != 0 || ev.dy != 0 || ev.buttons != 0 {
            mouse_push(ev);
        }
    }
}

// ── HID report parser ─────────────────────────────────────────────────────────
//
// Handles:
//   0x01 / 0x03  relative mouse (boot protocol or ELAN single-touch)
//   0x04-0x07    ELAN absolute multitouch → converted to relative via delta

fn parse(id: u8, data: &[u8]) -> Option<MouseEvent> {
    match id {
        // Relative mouse: boot protocol or ELAN single-touch relative report
        0x01 | 0x03 if data.len() >= 3 => {
            Some(MouseEvent {
                buttons: data[0] & 0x07,
                dx:      data[1] as i8,
                dy:     -(data[2] as i8),
                dz:      0,
            })
        }

        // Absolute multitouch: ELAN report IDs 0x04–0x07
        // data[0] = contact count (0 = all fingers lifted)
        // data[1..2] = X LE, data[3..4] = Y LE (first contact)
        0x04..=0x07 if data.len() >= 5 => {
            let contact_count = data[0];

            // Finger lifted — reset delta anchor so the next touch starts clean.
            if contact_count == 0 {
                unsafe { PREV_X = 0xFFFF; PREV_Y = 0xFFFF; }
                return None;
            }

            let x = u16::from_le_bytes([data[1], data[2]]);
            let y = u16::from_le_bytes([data[3], data[4]]);

            // Reject all-zero reports — spurious data with no real contact.
            if x == 0 && y == 0 {
                unsafe { PREV_X = 0xFFFF; PREV_Y = 0xFFFF; }
                return None;
            }

            unsafe {
                // First sample after a new touch: anchor without moving cursor.
                if PREV_X == 0xFFFF {
                    PREV_X = x; PREV_Y = y;
                    return None;
                }

                // Scale raw deltas by SENS_NUM / SENS_DEN for comfortable speed.
                let raw_dx = (x as i32 - PREV_X as i32) * SENS_NUM / SENS_DEN;
                let raw_dy = (y as i32 - PREV_Y as i32) * SENS_NUM / SENS_DEN;
                PREV_X = x; PREV_Y = y;

                let dx = raw_dx.clamp(-127, 127) as i8;
                let dy = (-raw_dy).clamp(-127, 127) as i8;  // invert Y: trackpad down = screen down
                Some(MouseEvent { buttons: 0, dx, dy, dz: 0 })
            }
        }

        _ => None,
    }
}

// PS/2 keyboard driver — polled, scancode set 1.
//
// PS/2 controller ports:
//   0x60  data register   (read scancode / write command data)
//   0x64  status register (bit 0 = output buffer full — byte waiting)
//
// Scancode set 1 (default AT-compatible):
//   0x01–0x58  key press  (make code)
//   0x81–0xD8  key release (make | 0x80) — we use this to track shift
//   0xE0 prefix marks extended keys (ignored for now)

use crate::input::{Key, MouseEvent};
use crate::arch::{inb, outb};

const PS2_DATA:   u16 = 0x60;
const PS2_STATUS: u16 = 0x64;
const PS2_CMD:    u16 = 0x64;
const OBF:        u8  = 0x01;  // output buffer full
const IBF:        u8  = 0x02;  // input buffer full (must be clear before write)
const AUX_DATA:   u8  = 0x20;  // status bit 5: byte is from aux (mouse) port

static mut SHIFT:   bool = false;
static mut CTRL:    bool = false;
static mut SKIP_E0: bool = false;

// Mouse packet accumulation
static mut M_BUF: [u8; 3] = [0u8; 3];
static mut M_IDX: usize    = 0;

// Small ring of pending mouse events (mouse bytes arrive between keyboard polls)
const MRING: usize = 8;
static mut M_RING:  [MouseEvent; MRING] = [MouseEvent { dx: 0, dy: 0, buttons: 0 }; MRING];
static mut M_WHEAD: usize = 0;
static mut M_RTAIL: usize = 0;

fn mouse_push(e: MouseEvent) {
    unsafe {
        let next = (M_WHEAD + 1) % MRING;
        if next != M_RTAIL {   // drop if full
            M_RING[M_WHEAD] = e;
            M_WHEAD = next;
        }
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

fn aux_send(byte: u8) {
    unsafe {
        wait_ibuf_clear();
        outb(PS2_CMD, 0xD4);   // route next byte to aux port
        wait_ibuf_clear();
        outb(PS2_DATA, byte);
        // Drain ACK (0xFA) — don't block, just flush if present
        let mut n = 0u32;
        while n < 10_000 {
            if inb(PS2_STATUS) & OBF != 0 { let _ = inb(PS2_DATA); break; }
            n += 1;
        }
    }
}

/// Initialise the PS/2 controller — keyboard on port 1, mouse on port 2.
pub fn init() {
    unsafe {
        // Flush any stale byte.
        if inb(PS2_STATUS) & OBF != 0 { let _ = inb(PS2_DATA); }

        // Enable port 1 (keyboard).
        wait_ibuf_clear();
        outb(PS2_CMD, 0xAE);
        wait_ibuf_clear();
        outb(PS2_DATA, 0xF4);  // enable keyboard scanning

        // Enable port 2 (aux / mouse).
        wait_ibuf_clear();
        outb(PS2_CMD, 0xA8);   // enable aux port

        aux_send(0xF6);  // set defaults
        aux_send(0xF4);  // enable data reporting
    }
}

/// Poll for the next key event.  Returns None if no byte is waiting.
/// Mouse bytes are drained here and pushed to the mouse ring — call
/// poll_mouse() separately to consume them.
pub fn poll() -> Option<Key> {
    unsafe {
        if inb(PS2_STATUS) & OBF == 0 { return None; }
        let status = inb(PS2_STATUS);
        let sc     = inb(PS2_DATA);

        // Byte from aux (mouse) port — accumulate into 3-byte packet.
        if status & AUX_DATA != 0 {
            // Re-sync: first byte must have bit 3 set.
            if M_IDX == 0 && sc & 0x08 == 0 { return None; }
            M_BUF[M_IDX] = sc;
            M_IDX += 1;
            if M_IDX == 3 {
                M_IDX = 0;
                let b0 = M_BUF[0];
                let raw_dx = M_BUF[1] as i16
                    | if b0 & 0x10 != 0 { -256i16 } else { 0 };
                let raw_dy = M_BUF[2] as i16
                    | if b0 & 0x20 != 0 { -256i16 } else { 0 };
                // PS/2 Y is inverted relative to screen Y
                let dx = raw_dx.clamp(-127, 127) as i8;
                let dy = (-(raw_dy)).clamp(-127, 127) as i8;
                let buttons = b0 & 0x07;
                mouse_push(MouseEvent { dx, dy, buttons });
            }
            return None;
        }

        // Extended key prefix — next byte is an extended make/break code.
        if sc == 0xE0 {
            SKIP_E0 = true;
            return None;
        }
        if SKIP_E0 {
            SKIP_E0 = false;
            // Only act on make codes; ignore releases (sc & 0x80 != 0).
            if sc & 0x80 == 0 {
                return match sc {
                    0x48 => Some(Key::Up),
                    0x50 => Some(Key::Down),
                    0x4B => Some(Key::Left),
                    0x4D => Some(Key::Right),
                    _    => None,
                };
            }
            return None;
        }

        // Key release: clear modifier state.
        if sc & 0x80 != 0 {
            let make = sc & 0x7F;
            if make == 0x2A || make == 0x36 { SHIFT = false; }
            if make == 0x1D { CTRL  = false; }
            return None;
        }

        // Key press.
        match sc {
            0x01        => Some(Key::Escape),
            0x1C        => Some(Key::Enter),
            0x0E        => Some(Key::Backspace),
            0x1D        => { CTRL  = true; None }           // left Ctrl
            0x2A | 0x36 => { SHIFT = true; None }           // left/right Shift
            _           => {
                let table = if SHIFT { &SCAN_SHIFTED } else { &SCAN_NORMAL };
                let idx = sc as usize;
                if idx < table.len() && table[idx] != 0 {
                    let ch = table[idx];
                    // Ctrl+letter → control code (e.g. Ctrl+S = 0x13)
                    if CTRL && ch.is_ascii_alphabetic() {
                        Some(Key::Char(ch & 0x1F))
                    } else {
                        Some(Key::Char(ch))
                    }
                } else {
                    None
                }
            }
        }
    }
}

fn wait_ibuf_clear() {
    unsafe {
        let mut n = 0u32;
        while inb(PS2_STATUS) & IBF != 0 && n < 100_000 { n += 1; }
    }
}

// ── Scancode set 1 translation tables ────────────────────────────────────────

#[rustfmt::skip]
static SCAN_NORMAL: [u8; 58] = [
    0,    0x1B, b'1', b'2', b'3', b'4', b'5', b'6',  // 0x00–0x07
    b'7', b'8', b'9', b'0', b'-', b'=', 0,   b'\t',  // 0x08–0x0F
    b'q', b'w', b'e', b'r', b't', b'y', b'u', b'i',  // 0x10–0x17
    b'o', b'p', b'[', b']', 0,    0,    b'a', b's',  // 0x18–0x1F
    b'd', b'f', b'g', b'h', b'j', b'k', b'l', b';',  // 0x20–0x27
    b'\'',b'`', 0,    b'\\',b'z', b'x', b'c', b'v',  // 0x28–0x2F
    b'b', b'n', b'm', b',', b'.', b'/', 0,    b'*',  // 0x30–0x37
    0,    b' ',                                        // 0x38–0x39
];

#[rustfmt::skip]
static SCAN_SHIFTED: [u8; 58] = [
    0,    0x1B, b'!', b'@', b'#', b'$', b'%', b'^',  // 0x00–0x07
    b'&', b'*', b'(', b')', b'_', b'+', 0,   b'\t',  // 0x08–0x0F
    b'Q', b'W', b'E', b'R', b'T', b'Y', b'U', b'I',  // 0x10–0x17
    b'O', b'P', b'{', b'}', 0,    0,    b'A', b'S',  // 0x18–0x1F
    b'D', b'F', b'G', b'H', b'J', b'K', b'L', b':',  // 0x20–0x27
    b'"', b'~', 0,    b'|', b'Z', b'X', b'C', b'V',  // 0x28–0x2F
    b'B', b'N', b'M', b'<', b'>', b'?', 0,    b'*',  // 0x30–0x37
    0,    b' ',                                        // 0x38–0x39
];

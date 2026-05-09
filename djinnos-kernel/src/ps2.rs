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

use crate::input::Key;
use crate::arch::{inb, outb};

const PS2_DATA:   u16 = 0x60;
const PS2_STATUS: u16 = 0x64;
const PS2_CMD:    u16 = 0x64;
const OBF:        u8  = 0x01;  // output buffer full
const IBF:        u8  = 0x02;  // input buffer full (must be clear before write)

static mut SHIFT:   bool = false;
static mut CTRL:    bool = false;
static mut SKIP_E0: bool = false;  // pending E0-prefixed extended key

/// Initialise the PS/2 controller.
/// Sends a "set defaults + enable scanning" sequence so keyboards that
/// power on in disabled state start generating scancodes.
pub fn init() {
    unsafe {
        // Flush any stale byte in the output buffer.
        if inb(PS2_STATUS) & OBF != 0 { let _ = inb(PS2_DATA); }

        // Enable port 1 (keyboard).
        wait_ibuf_clear();
        outb(PS2_CMD, 0xAE);

        // Enable keyboard scanning (0xF4).
        wait_ibuf_clear();
        outb(PS2_DATA, 0xF4);
    }
}

/// Poll for the next key event.  Returns None if no byte is waiting.
/// Should be called frequently from the main event loop.
pub fn poll() -> Option<Key> {
    unsafe {
        if inb(PS2_STATUS) & OBF == 0 { return None; }
        let sc = inb(PS2_DATA);

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

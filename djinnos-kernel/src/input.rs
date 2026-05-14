// Shared key event type — used by both the VirtIO keyboard (RISC-V)
// and the PS/2 keyboard (x86_64).  Translated from hardware-specific
// scancodes / evdev codes by the respective driver before reaching
// the shell.

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Char(u8),
    Enter,
    Backspace,
    Up,
    Down,
    Left,
    Right,
    PageUp,
    PageDown,
    Escape,
}

/// Mouse movement and button event from PS/2 or USB HID.
/// dy is already screen-oriented (positive = down), matching screen coords.
/// dz is scroll wheel delta: positive = scroll down (toward user).
#[derive(Clone, Copy)]
pub struct MouseEvent {
    pub dx:      i8,
    pub dy:      i8,
    pub dz:      i8,  // scroll wheel; 0 if not supported by source
    pub buttons: u8,  // bit 0 = left, bit 1 = right, bit 2 = middle
}

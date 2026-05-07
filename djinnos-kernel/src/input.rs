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
    Escape,
}

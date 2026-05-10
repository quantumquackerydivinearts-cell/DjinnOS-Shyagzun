// cursor.rs -- software mouse cursor for DjinnOS.
//
// Tracks screen position, renders a 12x16 arrow cursor as the final
// layer before every framebuffer flush.

use crate::gpu::GpuSurface;
use crate::input::MouseEvent;

static mut CUR_X:       u32 = 0;
static mut CUR_Y:       u32 = 0;
static mut CUR_BTN:     u8  = 0;
static mut CUR_PREV:    u8  = 0;
static mut SCREEN_W:    u32 = 1920;
static mut SCREEN_H:    u32 = 1080;

pub fn init(sw: u32, sh: u32) {
    unsafe {
        SCREEN_W = sw;
        SCREEN_H = sh;
        CUR_X    = sw / 2;
        CUR_Y    = sh / 2;
    }
}

pub fn update(ev: MouseEvent, sw: u32, sh: u32) {
    unsafe {
        SCREEN_W = sw;
        SCREEN_H = sh;
        CUR_PREV = CUR_BTN;
        CUR_BTN  = ev.buttons;
        let nx = CUR_X as i32 + ev.dx as i32;
        let ny = CUR_Y as i32 + ev.dy as i32;
        CUR_X = nx.clamp(0, sw as i32 - 1) as u32;
        CUR_Y = ny.clamp(0, sh as i32 - 1) as u32;
    }
}

pub fn pos() -> (u32, u32) { unsafe { (CUR_X, CUR_Y) } }
pub fn buttons() -> u8     { unsafe { CUR_BTN } }

/// True the frame the left button transitions 0 -> 1.
pub fn left_clicked() -> bool {
    unsafe { CUR_BTN & 0x01 != 0 && CUR_PREV & 0x01 == 0 }
}

/// True while left button is held.
pub fn left_held() -> bool { unsafe { CUR_BTN & 0x01 != 0 } }

// ── Arrow cursor bitmap ───────────────────────────────────────────────────────
//
// 12 columns wide, 16 rows tall.
// 'X' = bright outline (white), 'i' = dark interior, '.' = transparent.
//
//  X . . . . . . . . . . .
//  X X . . . . . . . . . .
//  X i X . . . . . . . . .
//  X i i X . . . . . . . .
//  X i i i X . . . . . . .
//  X i i i i X . . . . . .
//  X i i i i i X . . . . .
//  X i i i i i i X . . . .
//  X i i i i X X X . . . .
//  X i i X X . . . . . . .
//  X i X . X . . . . . . .
//  X X . . . X . . . . . .
//  X . . . . . . . . . . .
//  . . . . . . . . . . . .
//  . . . . . . . . . . . .
//  . . . . . . . . . . . .

const ARROW: &[&[u8]] = &[
    b"X...........",
    b"XX..........",
    b"XiX.........",
    b"XiiX........",
    b"XiiiX.......",
    b"XiiiiX......",
    b"XiiiiiX.....",
    b"XiiiiiiX....",
    b"XiiiiXXX....",
    b"XiiiXX......",
    b"XiX.X.......",
    b"XX..X.......",
    b"X...........",
    b"............",
    b"............",
    b"............",
];

const OUT_R: u8 = 0xFF; const OUT_G: u8 = 0xFF; const OUT_B: u8 = 0xFF;
const INT_R: u8 = 0x30; const INT_G: u8 = 0x30; const INT_B: u8 = 0x30;
const HOT_R: u8 = 0x00; const HOT_G: u8 = 0xD0; const HOT_B: u8 = 0x60;

pub fn render(gpu: &dyn GpuSurface) {
    let (cx, cy) = pos();
    let sw = gpu.width();
    let sh = gpu.height();

    for (row, &line) in ARROW.iter().enumerate() {
        let py = cy + row as u32;
        if py >= sh { break; }
        for (col, &ch) in line.iter().enumerate() {
            let px = cx + col as u32;
            if px >= sw { break; }
            match ch {
                b'X' => {
                    if row == 0 && col == 0 {
                        gpu.set_pixel(px, py, HOT_B, HOT_G, HOT_R);
                    } else {
                        gpu.set_pixel(px, py, OUT_B, OUT_G, OUT_R);
                    }
                }
                b'i' => { gpu.set_pixel(px, py, INT_B, INT_G, INT_R); }
                _    => {}
            }
        }
    }
}
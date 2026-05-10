// login.rs -- Boot-time login screen for DjinnOS.
//
// Displayed before the Ko shell. Profile selection then optional
// password entry. No-password profiles log in immediately on Enter.

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;

const SCALE: u32 = 2;
const CHAR_W: u32 = font::GLYPH_W * SCALE;
const CHAR_H: u32 = font::GLYPH_H * SCALE;
const MX: u32 = 12;

const BG_R: u8 = 0x06; const BG_G: u8 = 0x08; const BG_B: u8 = 0x10;
const HD_R: u8 = 0xc8; const HD_G: u8 = 0x96; const HD_B: u8 = 0x4b;
const TX_R: u8 = 0xc0; const TX_G: u8 = 0xc0; const TX_B: u8 = 0xc0;
const AC_R: u8 = 0x60; const AC_G: u8 = 0xd0; const AC_B: u8 = 0x88;
const DM_R: u8 = 0x58; const DM_G: u8 = 0x60; const DM_B: u8 = 0x58;
const ER_R: u8 = 0xe0; const ER_G: u8 = 0x40; const ER_B: u8 = 0x40;
const HI_R: u8 = 0x10; const HI_G: u8 = 0x28; const HI_B: u8 = 0x18;

pub struct LoginScreen {
    sel:     usize,
    pw_mode: bool,
    pw_buf:  [u8; 64],
    pw_n:    usize,
    msg:     [u8; 48],
    msg_n:   usize,
    rule_y:  u32,
    pub done: bool,
}

impl LoginScreen {
    pub fn new(rule_y: u32) -> Self {
        LoginScreen {
            sel: 0, pw_mode: false,
            pw_buf: [0u8; 64], pw_n: 0,
            msg: [0u8; 48], msg_n: 0,
            rule_y, done: false,
        }
    }

    fn set_msg(&mut self, s: &[u8]) {
        let n = s.len().min(47);
        self.msg[..n].copy_from_slice(&s[..n]);
        self.msg_n = n;
    }

    pub fn handle_key(&mut self, key: Key) {
        let count = crate::profile::count();
        if count == 0 { return; }

        if self.pw_mode {
            match key {
                Key::Escape => {
                    self.pw_mode = false;
                    self.pw_n    = 0;
                    self.msg_n   = 0;
                }
                Key::Backspace => { if self.pw_n > 0 { self.pw_n -= 1; } }
                Key::Char(c) if c >= 0x20 => {
                    if self.pw_n < 63 { self.pw_buf[self.pw_n] = c; self.pw_n += 1; }
                }
                Key::Enter => {
                    if let Some(p) = crate::profile::get(self.sel) {
                        if let Some(p) = crate::profile::authenticate(
                            p.name_str(), &self.pw_buf[..self.pw_n])
                        {
                            crate::profile::set_active(p);
                            self.done = true;
                        } else {
                            self.set_msg(b"Access denied.");
                            self.pw_n = 0;
                        }
                    }
                }
                _ => {}
            }
        } else {
            match key {
                Key::Up   => { if self.sel > 0 { self.sel -= 1; self.msg_n = 0; } }
                Key::Down => { if self.sel + 1 < count { self.sel += 1; self.msg_n = 0; } }
                Key::Enter => {
                    if let Some(p) = crate::profile::get(self.sel) {
                        if p.hash == 0 {
                            // No password — log in immediately.
                            crate::profile::set_active(p);
                            self.done = true;
                        } else {
                            self.pw_mode = true;
                            self.pw_n    = 0;
                            self.msg_n   = 0;
                        }
                    }
                }
                _ => {}
            }
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, 0, w, h, BG_B, BG_G, BG_R);

        // Header
        font::draw_str(gpu, MX, MX, "DJINNOS", SCALE, HD_R, HD_G, HD_B);
        font::draw_str(gpu, MX + CHAR_W * 10, MX,
                       "Ko's Labyrinth", SCALE, DM_R, DM_G, DM_B);

        let rule_y = self.rule_y;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        let cx = w / 2;
        let base_y = h / 2 - CHAR_H * 4;

        if !self.pw_mode {
            // Profile selection
            let title = "Select profile:";
            let tx = cx.saturating_sub((title.len() as u32 * CHAR_W) / 2);
            font::draw_str(gpu, tx, base_y, title, SCALE, TX_R, TX_G, TX_B);

            let count = crate::profile::count();
            for i in 0..count {
                let Some(p) = crate::profile::get(i) else { continue };
                let y = base_y + CHAR_H * 2 + i as u32 * (CHAR_H + 4);

                let sel = i == self.sel;
                if sel {
                    gpu.fill_rect(cx.saturating_sub(CHAR_W * 14), y.saturating_sub(2),
                                  CHAR_W * 28, CHAR_H + 4, HI_B, HI_G, HI_R);
                }

                // Arrow
                let ax = cx.saturating_sub(CHAR_W * 12);
                if sel {
                    font::draw_str(gpu, ax, y, ">", SCALE, AC_R, AC_G, AC_B);
                }

                // Name
                let name_x = ax + CHAR_W * 2;
                if let Ok(s) = core::str::from_utf8(p.name_str()) {
                    let (r, g, b) = if sel { (AC_R, AC_G, AC_B) } else { (TX_R, TX_G, TX_B) };
                    font::draw_str(gpu, name_x, y, s, SCALE, r, g, b);
                }

                // Role tag
                let role = if p.is_admin() { "(admin)" } else if p.can_atelier() { "(user)" } else { "(guest)" };
                let rx = name_x + CHAR_W * 10;
                font::draw_str(gpu, rx, y, role, SCALE, DM_R, DM_G, DM_B);
            }

            // Hints
            let hy = base_y + CHAR_H * 2 + count as u32 * (CHAR_H + 4) + CHAR_H;
            font::draw_str(gpu, cx.saturating_sub(CHAR_W * 16), hy,
                           "Up/Dn navigate   Enter select", SCALE, DM_R, DM_G, DM_B);

        } else {
            // Password entry
            let Some(p) = crate::profile::get(self.sel) else { return };

            let lbl = "Profile:";
            let lx = cx.saturating_sub(CHAR_W * 10);
            font::draw_str(gpu, lx, base_y, lbl, SCALE, TX_R, TX_G, TX_B);
            if let Ok(s) = core::str::from_utf8(p.name_str()) {
                font::draw_str(gpu, lx + CHAR_W * 9, base_y, s, SCALE, AC_R, AC_G, AC_B);
            }

            let py = base_y + CHAR_H + 8;
            font::draw_str(gpu, lx, py, "Password:", SCALE, TX_R, TX_G, TX_B);
            // Echo as stars
            for i in 0..self.pw_n.min(32) {
                let sx = lx + CHAR_W * 10 + i as u32 * CHAR_W;
                font::draw_str(gpu, sx, py, "*", SCALE, AC_R, AC_G, AC_B);
            }
            // Cursor
            let cx2 = lx + CHAR_W * 10 + self.pw_n as u32 * CHAR_W;
            gpu.fill_rect(cx2, py, CHAR_W, CHAR_H, AC_B, AC_G, AC_R);

            let hy = py + CHAR_H + 8;
            font::draw_str(gpu, lx, hy, "Enter confirm   Esc back",
                           SCALE, DM_R, DM_G, DM_B);
        }

        // Error / status message
        if self.msg_n > 0 {
            let my = h.saturating_sub(CHAR_H * 2 + 8);
            if let Ok(s) = core::str::from_utf8(&self.msg[..self.msg_n]) {
                let mx2 = w / 2 - (self.msg_n as u32 * CHAR_W) / 2;
                font::draw_str(gpu, mx2, my, s, SCALE, ER_R, ER_G, ER_B);
            }
        }
    }
}
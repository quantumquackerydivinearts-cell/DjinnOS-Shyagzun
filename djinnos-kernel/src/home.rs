// home.rs -- DjinnOS home screen.
//
// Appears after login in place of landing directly in the Ko shell.
// A warm ambient dashboard: profile welcome, app tile grid, eigenstate strip.
//
// Layout (1920×1080 reference):
//   Ne Bar (top, 48px) — handled by compositor
//   Welcome area (80px) — "Welcome, {name}" + profile role
//   App grid (2 rows × 3 cols of 130px tiles, 32px gaps)
//   Bottom ambient strip (4px) — eigenstate dominant tongue color
//   Status bar (28px)
//
// Navigation: arrow keys, Enter launches. Esc drops to Ko shell.

use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::render2d::{It, ATL_BRAND_H};
use crate::style;

// ── App tile definitions ──────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum TileLaunch {
    Atelier,
    Play,
    Journal,
    Shell,
    Meditation,
    Codex,
}

struct Tile {
    label:    &'static str,
    sub:      &'static str,
    shortcut: &'static str,
    launch:   TileLaunch,
}

const TILES: &[Tile] = &[
    Tile { label: "Atelier",    sub: "Kaelshunshikeaninsuy",     shortcut: "A", launch: TileLaunch::Atelier    },
    Tile { label: "Play",       sub: "Ko's Labyrinth  7_KLGS",   shortcut: "P", launch: TileLaunch::Play       },
    Tile { label: "Journal",    sub: "Write and remember",        shortcut: "J", launch: TileLaunch::Journal    },
    Tile { label: "Ko Shell",   sub: "Terminal",                  shortcut: "K", launch: TileLaunch::Shell      },
    Tile { label: "Meditation", sub: "BreathOfKo",                shortcut: "M", launch: TileLaunch::Meditation },
    Tile { label: "Codex",      sub: "Book authoring",            shortcut: "C", launch: TileLaunch::Codex      },
];

const COLS: usize = 3;
const ROWS: usize = 2;

// ── Home ──────────────────────────────────────────────────────────────────────

pub struct Home {
    pub exited:  bool,
    pub launch:  Option<TileLaunch>,
    rule_y:      u32,
    selected:    usize,
}

static mut HOME: Home = Home {
    exited:   false,
    launch:   None,
    rule_y:   0,
    selected: 0,
};

pub fn home() -> &'static mut Home { unsafe { &mut HOME } }

static mut HOME_REQ: bool = false;
pub fn request()         { unsafe { HOME_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = HOME_REQ; HOME_REQ = false; r } }

impl Home {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y  = rule_y;
        self.exited  = false;
        self.launch  = None;
        self.selected = 0;
    }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.exited = true; }
            Key::Left   => {
                if self.selected % COLS > 0 { self.selected -= 1; }
            }
            Key::Right  => {
                if self.selected % COLS < COLS - 1 && self.selected + 1 < TILES.len() {
                    self.selected += 1;
                }
            }
            Key::Up     => {
                if self.selected >= COLS { self.selected -= COLS; }
            }
            Key::Down   => {
                if self.selected + COLS < TILES.len() { self.selected += COLS; }
            }
            Key::Enter  => {
                self.launch = Some(TILES[self.selected].launch);
            }
            Key::Char(c) => {
                // Single-letter shortcuts.
                let uc = c.to_ascii_uppercase();
                for (i, tile) in TILES.iter().enumerate() {
                    if tile.shortcut.as_bytes().first() == Some(&uc) {
                        self.selected = i;
                        self.launch   = Some(tile.launch);
                        break;
                    }
                }
            }
            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let prev = style::get();
        style::set(style::warm_theme());

        let it  = It::new(gpu);
        let t   = style::get();
        let w   = gpu.width();
        let h   = gpu.height();
        let y0  = self.rule_y + 4;

        // Full warm background.
        it.fill(0, y0, w, h.saturating_sub(y0), t.bg);

        // ── Welcome header ────────────────────────────────────────────────────
        let ps   = crate::player_state::get();
        let name = crate::profile::active()
            .map(|p| core::str::from_utf8(p.name_str()).unwrap_or(""))
            .unwrap_or("");

        let welcome_y = y0 + 48;

        if !name.is_empty() {
            // "Welcome," label
            let lw = it.tt_width("Welcome,", 20.0);
            let tx = (w as i32 - lw - it.tt_width(name, 34.0) - 14) / 2;
            let ex = it.tt(tx, welcome_y as i32, "Welcome,", 20.0, t.text_dim);
            it.tt(ex + 10, welcome_y as i32 - 6, name, 34.0, t.text);
        } else {
            it.tt_center(0, welcome_y as i32, w as i32, "DjinnOS", 34.0, t.text);
        }

        // Sanity / profile status line below name
        let status_y = welcome_y + 44;
        let sanity_total: u16 = ps.sanity.iter().map(|&s| s as u16).sum();
        let mut sb = [0u8; 32];
        let sn = write_u8_arr(&mut sb, &ps.sanity);
        let sanity_str = core::str::from_utf8(&sb[..sn]).unwrap_or("");
        let status_line = if sanity_total > 0 { sanity_str } else { "Ko's Labyrinth" };
        it.tt_center(0, status_y as i32, w as i32, status_line, 12.0, t.text_dim);

        // Thin rule under welcome.
        let rule_y = status_y + 20;
        let rule_x = (w.saturating_sub(400)) / 2;
        it.fill(rule_x, rule_y, 400, 1, t.rule);

        // ── App tile grid ─────────────────────────────────────────────────────
        let tile_w: u32 = 300;
        let tile_h: u32 = 130;
        let gap:    u32 = 28;
        let grid_w  = COLS as u32 * tile_w + (COLS as u32 - 1) * gap;
        let grid_x  = (w.saturating_sub(grid_w)) / 2;
        let grid_y  = rule_y + 32;

        for (i, tile) in TILES.iter().enumerate() {
            let col = (i % COLS) as u32;
            let row = (i / COLS) as u32;
            let tx  = grid_x + col * (tile_w + gap);
            let ty  = grid_y + row * (tile_h + gap);
            let sel = i == self.selected;

            // Tile background: selected gets accent-soft, others plain surface.
            if sel {
                it.fill_rounded(tx, ty, tile_w, tile_h, 12, t.selection);
                it.stroke_rounded(tx, ty, tile_w, tile_h, 12, 2, t.accent);
            } else {
                it.atl_panel(tx, ty, tile_w, tile_h);
            }

            // App name.
            let nc = if sel { t.accent } else { t.text };
            it.tt_center(tx as i32, ty as i32 + 28, tile_w as i32,
                         tile.label, 17.0, nc);

            // Description.
            it.tt_center(tx as i32, ty as i32 + 56, tile_w as i32,
                         tile.sub, 12.0, t.text_dim);

            // Keyboard shortcut badge.
            let badge_x = tx + tile_w - 36;
            let badge_y = ty + tile_h - 30;
            it.atl_badge(badge_x, badge_y, tile.shortcut,
                         if sel { t.accent } else { t.text_dim });
        }

        // ── Eigenstate ambient strip ──────────────────────────────────────────
        // A 4px horizontal band at the bottom of the content area whose color
        // reflects the most-active Shygazun tongue in the current session.
        let dominant = crate::eigenstate::dominant();
        // Map tongue number to a byte table address.  Tongues 1-8 start at
        // byte 1 (Lotus), each tongue cluster ~8-30 entries; approximate.
        let byte_addr = dominant as u32 * 8 + 1;
        let ambient_col = crate::palette::aki_color(byte_addr);
        let strip_y = h.saturating_sub(32);
        it.fill(0, strip_y, w, 4, ambient_col);

        // ── Status bar ────────────────────────────────────────────────────────
        let sb_y = h.saturating_sub(28);
        it.fill(0, sb_y, w, 28, t.surface);
        it.fill(0, sb_y, w, 1, t.rule);
        let ty2 = sb_y as i32 + 7;
        it.tt(20, ty2,
            "arrows = navigate   Enter / letter = launch   Esc = Ko shell",
            12.0, t.text_dim);

        // System time right-aligned in status bar (x86 RTC only).
        #[cfg(target_arch = "x86_64")]
        {
            let rtc = crate::rtc::read();
            let mut tb = [0u8; 10];
            let tn = fmt_time(&mut tb, rtc.hour, rtc.minute);
            let ts = core::str::from_utf8(&tb[..tn]).unwrap_or("");
            it.tt_right(w as i32 - 20, ty2, ts, 12.0, t.text_dim);
        }

        style::set(prev);
    }
}

// ── Format helpers ────────────────────────────────────────────────────────────

fn fmt_time(buf: &mut [u8], h: u8, m: u8) -> usize {
    buf[0] = b'0' + h / 10; buf[1] = b'0' + h % 10;
    buf[2] = b':';
    buf[3] = b'0' + m / 10; buf[4] = b'0' + m % 10;
    5
}

fn write_u8_arr(buf: &mut [u8], vals: &[u8]) -> usize {
    let labels = [b'A', b'N', b'T', b'C'];
    let mut n = 0;
    for (i, &v) in vals.iter().enumerate() {
        if i < labels.len() && n + 4 < buf.len() {
            buf[n] = labels[i]; n += 1;
            buf[n] = b':'; n += 1;
            buf[n] = b'0' + v / 100; n += 1;
            buf[n] = b' '; n += 1;
        }
    }
    n
}

// meditation.rs — Meditation system for Ko's Labyrinth (7_KLGS).
//
// Entering meditation restores Cosmic sanity and applies breath regulation.
// The BreathOfKo visualization renders a Mandelbrot set using integer
// fixed-point arithmetic (Q8.24) — no floating point required.
//
// Perks accessible through meditation (see skills.rs PERKS) become
// visually available as depth layers: each unlocked perk reveals one
// deeper ring of the Mandelbrot rendering.
//
// The 24-layer dream calibration ties to the 24 Cannabis tongue symbols —
// one layer per byte-table entry in the consciousness register.

use crate::input::Key;
use crate::gpu::GpuSurface;

// ── Fixed-point Mandelbrot ────────────────────────────────────────────────────
// Q8.24: 1 real unit = 1 << 24 ticks.

const FP: i64 = 1 << 24;
const MAX_ITER: u32 = 64;

fn mandelbrot(cx: i64, cy: i64) -> u32 {
    let mut zx: i64 = 0;
    let mut zy: i64 = 0;
    for i in 0..MAX_ITER {
        // |z|² = zx² + zy²; if > 4 (in FP: 4 << 24) → escaped
        let zx2 = (zx * zx) >> 24;
        let zy2 = (zy * zy) >> 24;
        if zx2 + zy2 > 4 * FP { return i; }
        let new_zx = zx2 - zy2 + cx;
        zy = 2 * ((zx * zy) >> 24) + cy;
        zx = new_zx;
    }
    MAX_ITER
}

// ── Meditation palette ────────────────────────────────────────────────────────
// Maps iteration count → (B, G, R) colour.
// Deep = blue-purple (Cannabis register); mid = teal; near = amber.

fn iter_color(i: u32, max: u32) -> (u8, u8, u8) {
    if i >= max { return (5, 5, 10); } // interior (in set) → near-black
    let t = (i * 255 / max.max(1)) as u8;
    match t {
        0..=63  => (t.saturating_mul(2), t / 2, t.saturating_mul(3)),     // deep violet
        64..=127 => (t, t * 3 / 4, t / 4),                                // teal
        128..=191 => (t / 2, t, t / 3),                                    // green
        _        => (t / 3, t / 2, t),                                     // amber-gold
    }
}

// ── Breath counter ────────────────────────────────────────────────────────────
// Each meditation session counts breaths (Enter key = one full breath cycle).
// BreathOfKo position: pan the Mandelbrot view along the breath count.

const BREATH_VIEW_W: u32 = 320;
const BREATH_VIEW_H: u32 = 240;

pub struct Meditation {
    pub breath_count:  u32,
    pub session_depth: u8,   // 0–24 (increases with perks)
    pub exited:        bool,
    rule_y:            u32,
    // View parameters: centre and zoom in Q8.24
    view_cx:  i64,
    view_cy:  i64,
    view_zoom: i64,  // pixels per FP unit
    anim_frame: u32,
}

static mut MED: Meditation = Meditation {
    breath_count:  0,
    session_depth: 0,
    exited:        false,
    rule_y:        0,
    view_cx:  -1 * (1i64 << 24) / 2,   // centre at (-0.5, 0)
    view_cy:  0,
    view_zoom: (1i64 << 24) / 200,       // 200 pixels per unit
    anim_frame: 0,
};

pub fn meditation() -> &'static mut Meditation { unsafe { &mut MED } }

static mut MED_REQ: bool = false;
pub fn request()         { unsafe { MED_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = MED_REQ; MED_REQ = false; r } }

impl Meditation {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y = rule_y;
        self.exited = false;
        // Depth = 1 base + 1 per unlocked perk.
        // Depth = 1 base + 1 per taken perk (any perk deepens the practice).
        self.session_depth = 1;
        let ps = crate::player_state::get();
        for w in &ps.perks {
            self.session_depth = self.session_depth
                .saturating_add(w.count_ones() as u8).min(24);
        }
        self.session_depth = self.session_depth.min(24);
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Enter | Key::Char(b' ') => {
                // One breath: restore Cosmic sanity, advance BreathOfKo
                self.breath_count += 1;
                let ps = crate::player_state::get_mut();
                let restore = 3u8 + self.session_depth / 4;
                ps.sanity[3] = ps.sanity[3].saturating_add(restore);   // Cosmic
                ps.sanity[2] = ps.sanity[2].saturating_add(1);          // Terrestrial (minor)
                // Breathwork perk amplifies Alchemical restore.
                if crate::player_state::has_perk(crate::player_state::PERK_BREATHWORK) {
                    ps.sanity[0] = ps.sanity[0].saturating_add(2);      // Alchemical
                }
                // Pan the view slightly with each breath (BreathOfKo spiral).
                self.view_cx = self.view_cx.wrapping_add(FP / 400);
                self.view_cy = self.view_cy.wrapping_add(FP / 600);
                crate::eigenstate::advance(crate::eigenstate::T_CANNABIS);
            }
            Key::Up    => { self.view_zoom = (self.view_zoom * 5 / 4).max(FP / 500); }
            Key::Down  => { self.view_zoom = (self.view_zoom * 4 / 5).max(FP / 2000); }
            Key::Left  => { self.view_cx -= FP / 20; }
            Key::Right => { self.view_cx += FP / 20; }
            Key::Escape => {
                self.exited = true;
                self.apply_session_close();
            }
            _ => {}
        }
    }

    fn apply_session_close(&self) {
        crate::player_state::save();
    }

    pub fn render(&mut self, gpu: &dyn GpuSurface) {
        let sw = gpu.width();
        let sh = gpu.height();
        let top = self.rule_y + 4;
        let avail_h = sh.saturating_sub(top + 32);

        // Mandelbrot view centred on screen.
        let vw = BREATH_VIEW_W.min(sw);
        let vh = BREATH_VIEW_H.min(avail_h);
        let ox = (sw.saturating_sub(vw)) / 2;
        let oy = top + 16;

        // Background fill
        gpu.fill_rect(0, top, sw, sh.saturating_sub(top), 2, 2, 5);

        // Animate: every 4 frames shift view slightly for "breathing" feel.
        self.anim_frame = self.anim_frame.wrapping_add(1);
        let phase_cx = (self.anim_frame as i64 * FP / 1200) % FP;
        let phase_cy = (self.anim_frame as i64 * FP / 1800) % FP;

        // Render Mandelbrot into framebuffer (pixel by pixel, slow but correct).
        let max_iter = 16 + (self.session_depth as u32) * 3;
        for py in 0..vh {
            for px in 0..vw {
                let cx = self.view_cx + phase_cx / 20
                    + ((px as i64 - (vw/2) as i64) * self.view_zoom);
                let cy = self.view_cy + phase_cy / 20
                    + ((py as i64 - (vh/2) as i64) * self.view_zoom);
                let iter = mandelbrot(cx, cy);
                let (b, g, r) = iter_color(iter.min(max_iter), max_iter);
                let sx = ox + px;
                let sy = oy + py;
                if sx < sw && sy < sh {
                    gpu.fill_span(sx, sx + 1, sy, b, g, r);
                }
            }
        }

        // HUD: breath count and depth.
        use crate::render2d::It;
        use crate::style;
        let it = It::new(gpu);
        let t  = style::get();
        let mut bb = [0u8; 10]; let bn = write_u32(&mut bb, self.breath_count);
        it.text(ox, oy + vh + 4, "Breaths: ", 1, t.text_dim);
        it.text(ox + 72, oy + vh + 4, core::str::from_utf8(&bb[..bn]).unwrap_or("?"), 1, t.accent);
        it.text(ox + 120, oy + vh + 4, "  Depth: ", 1, t.text_dim);
        let mut db = [0u8; 4]; db[0] = b'0' + self.session_depth; let dn = 1;
        it.text(ox + 192, oy + vh + 4, core::str::from_utf8(&db[..dn]).unwrap_or("?"), 1, t.accent);
        it.text(ox, oy + vh + 16, "[Space/Enter]=breathe  arrows=navigate  Esc=exit", 1, t.text_dim);
    }
}

fn write_u32(buf: &mut [u8], v: u32) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8;10]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}

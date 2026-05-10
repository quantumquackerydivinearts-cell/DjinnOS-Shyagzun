// render2d.rs -- It: grounded locality renderer for DjinnOS.
//
// It (byte 212, Cannabis): grounded locality / the spatial fact of material
// presence (Lotus through Space -- where something is in the most concrete
// sense, its place in the earth).
//
// Zero-cost wrapper around &dyn GpuSurface providing:
//   gradients, alpha compositing, rounded rectangles, bezier curves,
//   shadows, sprites, semantic UI primitives.
//
// All operations respect the active Style theme (style::get()).

use crate::font;
use crate::gpu::GpuSurface;
use crate::style::{self, Theme, SCALE, RADIUS, RULE_W};

pub struct It<'a> {
    pub gpu: &'a dyn GpuSurface,
    theme:   Theme,
    // clipping region
    cx: u32, cy: u32, cw: u32, ch: u32,
}

impl<'a> It<'a> {
    pub fn new(gpu: &'a dyn GpuSurface) -> Self {
        let w = gpu.width();
        let h = gpu.height();
        It { gpu, theme: style::get(), cx: 0, cy: 0, cw: w, ch: h }
    }

    pub fn with_theme(gpu: &'a dyn GpuSurface, theme: Theme) -> Self {
        let w = gpu.width();
        let h = gpu.height();
        It { gpu, theme, cx: 0, cy: 0, cw: w, ch: h }
    }

    /// Return a sub-renderer clipped to a rect.
    pub fn clip(&self, x: u32, y: u32, w: u32, h: u32) -> It<'a> {
        It { gpu: self.gpu, theme: self.theme,
             cx: self.cx + x, cy: self.cy + y,
             cw: w.min(self.cw.saturating_sub(x)),
             ch: h.min(self.ch.saturating_sub(y)) }
    }

    fn px(&self, x: u32) -> u32 { self.cx + x }
    fn py(&self, y: u32) -> u32 { self.cy + y }
    fn clamp_x(&self, x: u32) -> bool { x < self.cw }
    fn clamp_y(&self, y: u32) -> bool { y < self.ch }

    // ── Primitive fills ───────────────────────────────────────────────────────

    pub fn clear(&self) {
        let (b,g,r) = self.theme.bg;
        self.gpu.fill_rect(self.cx, self.cy, self.cw, self.ch, b, g, r);
    }

    pub fn fill(&self, x: u32, y: u32, w: u32, h: u32, col: (u8,u8,u8)) {
        self.gpu.fill_rect(self.px(x), self.py(y), w.min(self.cw.saturating_sub(x)),
                           h.min(self.ch.saturating_sub(y)), col.0, col.1, col.2);
    }

    pub fn fill_alpha(&self, x: u32, y: u32, w: u32, h: u32, col: (u8,u8,u8), alpha: u8) {
        self.gpu.fill_rect_alpha(self.px(x), self.py(y),
                                 w.min(self.cw.saturating_sub(x)),
                                 h.min(self.ch.saturating_sub(y)),
                                 col.0, col.1, col.2, alpha);
    }

    pub fn grad_v(&self, x: u32, y: u32, w: u32, h: u32,
                  top: (u8,u8,u8), bot: (u8,u8,u8)) {
        self.gpu.fill_grad_v(self.px(x), self.py(y),
                             w.min(self.cw.saturating_sub(x)),
                             h.min(self.ch.saturating_sub(y)),
                             top.0, top.1, top.2, bot.0, bot.1, bot.2);
    }

    pub fn grad_h(&self, x: u32, y: u32, w: u32, h: u32,
                  left: (u8,u8,u8), right: (u8,u8,u8)) {
        self.gpu.fill_grad_h(self.px(x), self.py(y),
                             w.min(self.cw.saturating_sub(x)),
                             h.min(self.ch.saturating_sub(y)),
                             left.0, left.1, left.2, right.0, right.1, right.2);
    }

    // ── Rounded rectangle ─────────────────────────────────────────────────────

    pub fn fill_rounded(&self, x: u32, y: u32, w: u32, h: u32,
                        r: u32, col: (u8,u8,u8)) {
        if w == 0 || h == 0 { return; }
        let r = r.min(w / 2).min(h / 2);
        let (b,g,rc) = col;
        // Central cross (no corners)
        self.gpu.fill_rect(self.px(x), self.py(y + r), w, h.saturating_sub(r * 2), b, g, rc);
        self.gpu.fill_rect(self.px(x + r), self.py(y), w.saturating_sub(r * 2), r, b, g, rc);
        self.gpu.fill_rect(self.px(x + r), self.py(y + h.saturating_sub(r)), w.saturating_sub(r * 2), r, b, g, rc);
        // Rasterise four quarter-circles using Bresenham
        self.fill_quarter(x + r,         y + r,         r, 2, col);
        self.fill_quarter(x + w - r - 1, y + r,         r, 1, col);
        self.fill_quarter(x + r,         y + h - r - 1, r, 3, col);
        self.fill_quarter(x + w - r - 1, y + h - r - 1, r, 0, col);
    }

    /// Fill one quadrant of a circle. quad: 0=BotRight,1=BotLeft,2=TopRight,3=TopLeft
    fn fill_quarter(&self, cx: u32, cy: u32, r: u32, quad: u8, col: (u8,u8,u8)) {
        if r == 0 { return; }
        let ri = r as i32;
        let (b,g,rc) = col;
        for dy in 0..=ri {
            // integer sqrt approximation: find dx where dx^2 + dy^2 <= r^2
            let dx = isqrt((ri * ri - dy * dy).max(0));
            let (x0, x1, py) = match quad {
                0 => (cx as i32,      cx as i32 + dx, cy as i32 + dy),
                1 => (cx as i32 - dx, cx as i32,      cy as i32 + dy),
                2 => (cx as i32,      cx as i32 + dx, cy as i32 - dy),
                _ => (cx as i32 - dx, cx as i32,      cy as i32 - dy),
            };
            if py < 0 || py >= self.gpu.height() as i32 { continue; }
            let x0 = (self.cx as i32 + x0).max(0) as u32;
            let x1 = (self.cx as i32 + x1 + 1).min(self.gpu.width() as i32) as u32;
            if x0 < x1 {
                self.gpu.fill_span(x0, x1, py as u32, b, g, rc);
            }
        }
    }

    pub fn stroke_rounded(&self, x: u32, y: u32, w: u32, h: u32,
                          r: u32, t: u32, col: (u8,u8,u8)) {
        let t = t.max(1);
        // Outer - inner rounded rect (approximation: fill outer, fill inner with bg)
        self.fill_rounded(x, y, w, h, r, col);
        if w > t * 2 && h > t * 2 {
            let ir = r.saturating_sub(t);
            self.fill_rounded(x + t, y + t, w - t * 2, h - t * 2, ir, self.theme.bg);
        }
    }

    // ── Lines ─────────────────────────────────────────────────────────────────

    pub fn hline(&self, x: u32, y: u32, w: u32, col: (u8,u8,u8)) {
        if !self.clamp_y(y) { return; }
        self.gpu.fill_span(self.px(x), self.px(x) + w.min(self.cw.saturating_sub(x)),
                           self.py(y), col.0, col.1, col.2);
    }

    pub fn vline(&self, x: u32, y: u32, h: u32, col: (u8,u8,u8)) {
        if !self.clamp_x(x) { return; }
        self.gpu.fill_rect(self.px(x), self.py(y), 1, h.min(self.ch.saturating_sub(y)),
                           col.0, col.1, col.2);
    }

    pub fn line(&self, x0: i32, y0: i32, x1: i32, y1: i32, col: (u8,u8,u8)) {
        self.gpu.draw_line(self.cx as i32 + x0, self.cy as i32 + y0,
                           self.cx as i32 + x1, self.cy as i32 + y1,
                           col.0, col.1, col.2);
    }

    // ── Bezier curves ─────────────────────────────────────────────────────────

    /// Quadratic bezier from p0 through control p1 to p2.
    pub fn bezier_quad(&self, p0: (i32,i32), p1: (i32,i32), p2: (i32,i32),
                       col: (u8,u8,u8)) {
        let (b,g,r) = col;
        let steps = 32u32;
        let mut prev = p0;
        for i in 1..=steps {
            let t  = i * 256 / steps;
            let it = 256 - t;
            let qx = (it*it*(p0.0 as u32)/256 + 2*it*t*(p1.0 as u32)/256 + t*t*(p2.0 as u32)/256) as i32 / 256;
            let qy = (it*it*(p0.1 as u32)/256 + 2*it*t*(p1.1 as u32)/256 + t*t*(p2.1 as u32)/256) as i32 / 256;
            self.gpu.draw_line(self.cx as i32 + prev.0, self.cy as i32 + prev.1,
                               self.cx as i32 + qx,     self.cy as i32 + qy, b, g, r);
            prev = (qx, qy);
        }
    }

    /// Cubic bezier through p0, p1, p2, p3.
    pub fn bezier_cubic(&self, p0: (i32,i32), p1: (i32,i32),
                        p2: (i32,i32), p3: (i32,i32), col: (u8,u8,u8)) {
        let (b,g,r) = col;
        let steps = 48u32;
        let mut prev = p0;
        for i in 1..=steps {
            let t  = i * 256 / steps;
            let it = 256 - t;
            // de Casteljau in fixed-point
            let cx0 = ((it as i32 * p0.0 + t as i32 * p1.0) / 256) as i32;
            let cy0 = ((it as i32 * p0.1 + t as i32 * p1.1) / 256) as i32;
            let cx1 = ((it as i32 * p1.0 + t as i32 * p2.0) / 256) as i32;
            let cy1 = ((it as i32 * p1.1 + t as i32 * p2.1) / 256) as i32;
            let cx2 = ((it as i32 * p2.0 + t as i32 * p3.0) / 256) as i32;
            let cy2 = ((it as i32 * p2.1 + t as i32 * p3.1) / 256) as i32;
            let dx0 = ((it as i32 * cx0 + t as i32 * cx1) / 256) as i32;
            let dy0 = ((it as i32 * cy0 + t as i32 * cy1) / 256) as i32;
            let dx1 = ((it as i32 * cx1 + t as i32 * cx2) / 256) as i32;
            let dy1 = ((it as i32 * cy1 + t as i32 * cy2) / 256) as i32;
            let qx  = ((it as i32 * dx0 + t as i32 * dx1) / 256) as i32;
            let qy  = ((it as i32 * dy0 + t as i32 * dy1) / 256) as i32;
            self.gpu.draw_line(self.cx as i32 + prev.0, self.cy as i32 + prev.1,
                               self.cx as i32 + qx,     self.cy as i32 + qy, b, g, r);
            prev = (qx, qy);
        }
    }

    // ── Shadow ────────────────────────────────────────────────────────────────

    pub fn shadow(&self, x: u32, y: u32, w: u32, h: u32, blur: u32) {
        let (b,g,r) = self.theme.shadow;
        for i in 1..=blur {
            let alpha = (180 / blur * (blur - i + 1)) as u8;
            let off = i;
            self.gpu.fill_rect_alpha(self.px(x + off), self.py(y + off), w, h, b, g, r, alpha);
        }
    }

    // ── Text ──────────────────────────────────────────────────────────────────

    pub fn text(&self, x: u32, y: u32, s: &str, scale: u32, col: (u8,u8,u8)) {
        font::draw_str(self.gpu, self.px(x), self.py(y), s, scale, col.2, col.1, col.0);
    }

    pub fn text_dim(&self, x: u32, y: u32, s: &str) {
        let c = self.theme.text_dim;
        font::draw_str(self.gpu, self.px(x), self.py(y), s, SCALE, c.2, c.1, c.0);
    }

    pub fn text_accent(&self, x: u32, y: u32, s: &str) {
        let c = self.theme.accent;
        font::draw_str(self.gpu, self.px(x), self.py(y), s, SCALE, c.2, c.1, c.0);
    }

    pub fn text_header(&self, x: u32, y: u32, s: &str) {
        let c = self.theme.header;
        font::draw_str(self.gpu, self.px(x), self.py(y), s, SCALE, c.2, c.1, c.0);
    }

    pub fn text_centered(&self, y: u32, s: &str, scale: u32, col: (u8,u8,u8)) {
        let cw = font::GLYPH_W * scale;
        let total_w = s.len() as u32 * cw;
        let x = self.cw.saturating_sub(total_w) / 2;
        self.text(x, y, s, scale, col);
    }

    // ── Sprite blit ───────────────────────────────────────────────────────────

    pub fn blit(&self, x: u32, y: u32, data: &[(u8,u8,u8)], sw: u32, _sh: u32) {
        let rows = data.len() as u32 / sw.max(1);
        for row in 0..rows {
            if !self.clamp_y(y + row) { break; }
            let slice = &data[(row * sw) as usize..((row + 1) * sw) as usize];
            self.gpu.blit_row(slice, self.px(x), self.py(y + row));
        }
    }

    /// Blit with colorkey transparency (key color is skipped).
    pub fn blit_key(&self, x: u32, y: u32, data: &[(u8,u8,u8)],
                    sw: u32, _sh: u32, key: (u8,u8,u8)) {
        let rows = data.len() as u32 / sw.max(1);
        let gw = self.gpu.width();
        for row in 0..rows {
            let py = self.py(y + row);
            if py >= self.gpu.height() { break; }
            for col in 0..sw {
                let px = self.px(x + col);
                if px >= gw { break; }
                let (b,g,r) = data[(row * sw + col) as usize];
                if (b,g,r) != key { self.gpu.set_pixel(px, py, b, g, r); }
            }
        }
    }

    // ── Semantic UI components ────────────────────────────────────────────────

    /// Background panel with shadow.
    pub fn panel(&self, x: u32, y: u32, w: u32, h: u32) {
        self.shadow(x, y, w, h, 3);
        self.fill_rounded(x, y, w, h, RADIUS, self.theme.surface);
    }

    /// Elevated card (modal, popup).
    pub fn card(&self, x: u32, y: u32, w: u32, h: u32) {
        self.shadow(x, y, w, h, 5);
        self.fill_rounded(x, y, w, h, RADIUS, self.theme.elevated);
    }

    /// Horizontal divider rule.
    pub fn divider(&self, x: u32, y: u32, w: u32) {
        self.fill(x, y, w, RULE_W, self.theme.rule);
    }

    /// Labelled button with focus/press states.
    pub fn button(&self, x: u32, y: u32, w: u32, h: u32,
                  label: &str, pressed: bool, focused: bool) {
        let bg = if pressed   { self.theme.accent }
                 else if focused { style::mix(self.theme.surface, self.theme.accent, 80) }
                 else            { self.theme.surface };
        self.fill_rounded(x, y, w, h, RADIUS, bg);
        if focused {
            self.stroke_rounded(x, y, w, h, RADIUS, 1, self.theme.accent);
        }
        let text_col = if pressed { self.theme.text_inv } else { self.theme.text };
        let cw = font::GLYPH_W * SCALE;
        let tx = x + w.saturating_sub(label.len() as u32 * cw) / 2;
        let ty = y + h.saturating_sub(font::GLYPH_H * SCALE) / 2;
        self.text(tx, ty, label, SCALE, text_col);
    }

    /// Single-line text input field.
    pub fn input_field(&self, x: u32, y: u32, w: u32, h: u32,
                       value: &str, cursor_pos: usize, focused: bool) {
        let bg = if focused { style::mix(self.theme.surface, self.theme.elevated, 128) }
                 else        { self.theme.surface };
        self.fill_rounded(x, y, w, h, RADIUS / 2, bg);
        self.stroke_rounded(x, y, w, h, RADIUS / 2, 1,
                            if focused { self.theme.accent } else { self.theme.rule });
        let pad = 6u32;
        let cw = font::GLYPH_W * SCALE;
        let ty = y + h.saturating_sub(font::GLYPH_H * SCALE) / 2;
        self.text(x + pad, ty, value, SCALE, self.theme.text);
        if focused {
            let cur_x = x + pad + cursor_pos as u32 * cw;
            self.fill(cur_x, ty, 2, font::GLYPH_H * SCALE, self.theme.accent);
        }
    }

    /// Header bar at top of a tool window.
    pub fn header_bar(&self, y: u32, h: u32, title: &str) {
        self.grad_v(0, y, self.cw, h,
                    style::mix(self.theme.surface, self.theme.elevated, 80),
                    self.theme.surface);
        self.text(style::M4, y + h.saturating_sub(font::GLYPH_H * SCALE) / 2,
                  title, SCALE, self.theme.header);
        self.divider(0, y + h.saturating_sub(1), self.cw);
    }

    /// Status / hint bar at bottom of a tool window.
    pub fn status_bar(&self, h: u32, left: &str, right: &str) {
        let y = self.ch.saturating_sub(h);
        self.fill(0, y, self.cw, h, self.theme.bg);
        self.divider(0, y, self.cw);
        let ty = y + h.saturating_sub(font::GLYPH_H * SCALE) / 2;
        self.text(style::M4, ty, left,  SCALE, self.theme.text_dim);
        let cw = font::GLYPH_W * SCALE;
        let rx = self.cw.saturating_sub(style::M4 + right.len() as u32 * cw);
        self.text(rx, ty, right, SCALE, self.theme.text_dim);
    }

    /// Scrollable list row — fills and optionally labels one row.
    pub fn list_row(&self, x: u32, y: u32, w: u32, h: u32,
                    label: &str, selected: bool) {
        if selected {
            self.fill_rounded(x, y.saturating_sub(2), w, h + 4, RADIUS / 2, self.theme.selection);
            let tx = x + style::M3 * 2;
            self.text(x + style::M3, y, ">", SCALE, self.theme.accent);
            self.text(tx, y, label, SCALE, self.theme.accent);
        } else {
            self.text(x + style::M3 * 2, y, label, SCALE, self.theme.text);
        }
    }
}

// ── Integer sqrt ─────────────────────────────────────────────────────────────

fn isqrt(n: i32) -> i32 {
    if n <= 0 { return 0; }
    let mut x = n;
    loop {
        let next = (x + n / x) / 2;
        if next >= x { return x; }
        x = next;
    }
}
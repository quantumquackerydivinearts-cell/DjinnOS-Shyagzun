// compositor.rs -- Ne: network / system of visual layers for DjinnOS.
//
// Ne (byte 87, Daisy): Network / System -- the compositor IS the network
// that holds all visual layers in coordinated relation.
//
// Four layers, composited in order before each scanout:
//
//   Layer 0: Background  -- wallpaper / scene gradient (rarely dirty)
//   Layer 1: Content     -- active AppMode render (dirty on input / state)
//   Layer 2: Overlay     -- modal dialogs, notifications, tooltips
//   Layer 3: Cursor      -- hardware cursor if available, software fallback
//
// Hardware cursor path: layer 3 is a DCN MMIO write (zero framebuffer cost).
// Software cursor path: layer 3 is drawn by cursor::render() at flush time.
//
// Dirty tracking: only re-render layers that have changed.
// Background layer rarely changes after boot; content layer changes on input.

#[derive(Clone, Copy, PartialEq)]
pub enum LayerKind {
    Background,
    Content,
    Overlay,
    Cursor,
}

#[derive(Clone, Copy)]
pub struct Layer {
    pub kind:    LayerKind,
    pub dirty:   bool,
    pub visible: bool,
}

impl Layer {
    const fn new(kind: LayerKind) -> Self {
        Layer { kind, dirty: true, visible: true }
    }
}

// Notification queue for the overlay layer.
const MAX_NOTIF: usize = 4;
const NOTIF_TTL: u32   = 120; // frames

struct Notification {
    msg:   [u8; 48],
    msg_n: usize,
    ttl:   u32,
}

pub struct Compositor {
    layers: [Layer; 4],
    notifs: [Notification; MAX_NOTIF],
    notif_n: usize,
    pub hw_cursor: bool,
}

impl Compositor {
    pub const fn new() -> Self {
        Compositor {
            layers: [
                Layer::new(LayerKind::Background),
                Layer::new(LayerKind::Content),
                Layer::new(LayerKind::Overlay),
                Layer::new(LayerKind::Cursor),
            ],
            notifs: [
                Notification { msg: [0u8; 48], msg_n: 0, ttl: 0 },
                Notification { msg: [0u8; 48], msg_n: 0, ttl: 0 },
                Notification { msg: [0u8; 48], msg_n: 0, ttl: 0 },
                Notification { msg: [0u8; 48], msg_n: 0, ttl: 0 },
            ],
            notif_n: 0,
            hw_cursor: false,
        }
    }

    // ── Dirty tracking ────────────────────────────────────────────────────────

    pub fn mark_dirty(&mut self, kind: LayerKind) {
        for l in &mut self.layers {
            if l.kind == kind { l.dirty = true; }
        }
    }

    pub fn mark_all_dirty(&mut self) {
        for l in &mut self.layers { l.dirty = true; }
    }

    pub fn is_dirty(&self) -> bool {
        self.layers.iter().any(|l| l.dirty && l.visible)
    }

    pub fn clear_dirty(&mut self, kind: LayerKind) {
        for l in &mut self.layers {
            if l.kind == kind { l.dirty = false; }
        }
    }

    // ── Cursor management ─────────────────────────────────────────────────────

    pub fn init_hw_cursor(&mut self) {
        #[cfg(target_arch = "x86_64")]
        if crate::amdgpu::hw_cursor_available() {
            self.hw_cursor = true;
            self.layers[3].dirty = false;
        }
    }

    pub fn on_cursor_move(&mut self, x: u32, y: u32) {
        #[cfg(target_arch = "x86_64")]
        if self.hw_cursor {
            crate::amdgpu::update_cursor(x, y);
            return;
        }
        let _ = (x, y);
        self.mark_dirty(LayerKind::Cursor);
        self.mark_dirty(LayerKind::Content);
    }

    // ── Notifications ─────────────────────────────────────────────────────────

    pub fn notify(&mut self, msg: &[u8]) {
        let n = msg.len().min(47);
        let slot = self.notif_n % MAX_NOTIF;
        self.notifs[slot].msg[..n].copy_from_slice(&msg[..n]);
        self.notifs[slot].msg_n = n;
        self.notifs[slot].ttl   = NOTIF_TTL;
        self.notif_n += 1;
        self.mark_dirty(LayerKind::Overlay);
    }

    /// Tick notification TTLs.  Returns true if overlay needs redraw.
    pub fn tick_notifs(&mut self) -> bool {
        let mut changed = false;
        for n in &mut self.notifs {
            if n.ttl > 0 { n.ttl -= 1; if n.ttl == 0 { changed = true; } }
        }
        if changed { self.mark_dirty(LayerKind::Overlay); }
        changed
    }

    // ── Render pass ───────────────────────────────────────────────────────────

    /// Render all dirty visible layers in order, then flush.
    /// `render_content` is called for layer 1 (AppMode render).
    pub fn render(
        &mut self,
        gpu:            &dyn crate::gpu::GpuSurface,
        render_content: impl FnOnce(&dyn crate::gpu::GpuSurface),
    ) {
        use crate::render2d::It;
        use crate::style;

        // Layer 0: Background (only when dirty)
        if self.layers[0].dirty && self.layers[0].visible {
            let it = It::new(gpu);
            let w  = gpu.width();
            let h  = gpu.height();
            let t  = style::get();
            it.grad_v(0, 0, w, h, t.bg, style::mix(t.bg, t.surface, 80));
            self.layers[0].dirty = false;
        }

        // Layer 1: Content
        if self.layers[1].dirty && self.layers[1].visible {
            render_content(gpu);
            self.layers[1].dirty = false;
        }

        // Layer 2: Overlay (notifications)
        if self.layers[2].dirty && self.layers[2].visible {
            self.render_overlay(gpu);
            self.layers[2].dirty = false;
        }

        // Layer 3: Cursor (software fallback only -- hardware path skips this)
        if !self.hw_cursor && self.layers[3].dirty && self.layers[3].visible {
            #[cfg(target_arch = "x86_64")]
            crate::cursor::render(gpu);
            self.layers[3].dirty = false;
        }
    }

    fn render_overlay(&self, gpu: &dyn crate::gpu::GpuSurface) {
        use crate::render2d::It;
        use crate::style;
        let it = It::new(gpu);
        let w  = gpu.width();
        let h  = gpu.height();
        let ch = (crate::font::GLYPH_H * style::SCALE) + style::M3 * 2;
        let mut active = 0u32;
        for n in &self.notifs {
            if n.ttl > 0 { active += 1; }
        }
        if active == 0 { return; }
        let panel_h = active * (ch + style::M2);
        let panel_w = w * 2 / 5;
        let px = w.saturating_sub(panel_w + style::M4);
        let py = h.saturating_sub(panel_h + style::M4);
        let mut row = 0u32;
        for n in &self.notifs {
            if n.ttl == 0 { continue; }
            let alpha = if n.ttl < 30 { (n.ttl * 255 / 30) as u8 } else { 220 };
            let ry = py + row * (ch + style::M2);
            it.fill_alpha(px, ry, panel_w, ch, style::get().elevated, alpha);
            if let Ok(s) = core::str::from_utf8(&n.msg[..n.msg_n]) {
                it.text(px + style::M3, ry + style::M3, s, style::SCALE, style::get().text);
            }
            row += 1;
        }
    }
}

// ── Static compositor instance ────────────────────────────────────────────────

static mut COMPOSITOR: Compositor = Compositor::new();

pub fn get() -> &'static mut Compositor { unsafe { &mut COMPOSITOR } }

pub fn init() {
    unsafe {
        COMPOSITOR.mark_all_dirty();
        COMPOSITOR.init_hw_cursor();
    }
}

pub fn notify(msg: &[u8]) { unsafe { COMPOSITOR.notify(msg); } }
// ne_bar.rs -- Ne: auxiliary hotbar for DjinnOS.
//
// Ne (byte 87, Daisy): Network / System -- the connective structure.
// A thin persistent strip anchored to the bottom of the screen.
// Rendered last by the compositor (above content, below cursor).
//
// Layout:
//   [  ◈ DjinnOS  |  active tool name  |  profile  time  status  ]
//    ^launcher       ^center                ^right cluster

use crate::font;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;

pub const NE_BAR_H: u32 = 48;

// ── Time display (frame-derived until RTC is wired) ───────────────────────────

fn frame_clock(frame: u64) -> [u8; 5] {
    // Approximate: assumes ~60fps. Replace with RTC when available.
    let total_s  = frame / 60;
    let minutes  = (total_s / 60) % 60;
    let hours    = (total_s / 3600) % 24;
    let mut out = [0u8; 5];
    out[0] = b'0' + (hours / 10) as u8;
    out[1] = b'0' + (hours % 10) as u8;
    out[2] = b':';
    out[3] = b'0' + (minutes / 10) as u8;
    out[4] = b'0' + (minutes % 10) as u8;
    out
}

// ── Network indicator ─────────────────────────────────────────────────────────

fn net_status() -> &'static str {
    #[cfg(target_arch = "x86_64")]
    if crate::x86net::info().is_some() { return "Net"; }
    "---"
}

// ── Render ────────────────────────────────────────────────────────────────────

/// Render the Ne Bar at the bottom of the screen.
/// `mode_name`: Shygazun name of the active AppMode.
/// `profile_name`: name of the logged-in profile.
/// `frame`: frame counter for clock approximation.
pub fn render(
    gpu:          &dyn GpuSurface,
    mode_name:    &str,
    profile_name: &str,
    frame:        u64,
) {
    let it  = It::new(gpu);
    let t   = style::get();
    let w   = gpu.width();
    let h   = gpu.height();
    let by  = h.saturating_sub(NE_BAR_H);

    let cw  = font::GLYPH_W  * style::SCALE;
    let ch  = font::GLYPH_H  * style::SCALE;
    let ty  = by + (NE_BAR_H.saturating_sub(ch)) / 2; // vertically centred text

    // ── Background ────────────────────────────────────────────────────────────

    // Slightly translucent elevated surface
    it.fill_alpha(0, by, w, NE_BAR_H, t.elevated, 230);
    // Top border line
    it.hline(0, by, w, t.rule);

    // ── Left: launcher mark ──────────────────────────────────────────────────

    let lx = style::M4;
    // Diamond glyph as launcher mark (ASCII-safe: use "Ko" wordmark)
    it.text(lx, ty, "Ko", style::SCALE, t.accent);
    let sep_x = lx + cw * 4;
    it.vline(sep_x, by + style::M2, NE_BAR_H.saturating_sub(style::M2 * 2), t.rule);

    // ── Centre: active mode pill ─────────────────────────────────────────────

    let pill_w  = (mode_name.len() as u32 * cw + style::M3 * 2).max(cw * 4);
    let pill_x  = (w / 2).saturating_sub(pill_w / 2);
    let pill_y  = by + style::M2;
    let pill_h  = NE_BAR_H.saturating_sub(style::M2 * 2);

    it.fill_rounded(pill_x, pill_y, pill_w, pill_h, style::RADIUS / 2, t.selection);
    let text_x = pill_x + (pill_w.saturating_sub(mode_name.len() as u32 * cw)) / 2;
    it.text(text_x, ty, mode_name, style::SCALE, t.accent);

    // ── Right: profile / status / clock ──────────────────────────────────────

    let mut rx = w.saturating_sub(style::M4);

    // Clock
    let clock = frame_clock(frame);
    if let Ok(s) = core::str::from_utf8(&clock) {
        let clock_w = 5 * cw;
        rx = rx.saturating_sub(clock_w);
        it.text(rx, ty, s, style::SCALE, t.text_dim);
        rx = rx.saturating_sub(style::M3);
    }

    // Network
    let net = net_status();
    let net_w = net.len() as u32 * cw;
    rx = rx.saturating_sub(net_w + style::M2);
    let net_col = if net == "---" { t.text_dim } else { t.success };
    it.text(rx, ty, net, style::SCALE, net_col);
    rx = rx.saturating_sub(style::M3);

    // Separator
    it.vline(rx.saturating_sub(style::M2), by + style::M2,
             NE_BAR_H.saturating_sub(style::M2 * 2), t.rule);
    rx = rx.saturating_sub(style::M2 * 2 + style::M2);

    // Profile name
    let pn_w = profile_name.len() as u32 * cw;
    rx = rx.saturating_sub(pn_w);
    it.text(rx, ty, profile_name, style::SCALE, t.header);
}

// ── Content area height (screen minus Ne Bar) ─────────────────────────────────

pub fn content_h(gpu: &dyn GpuSurface) -> u32 {
    gpu.height().saturating_sub(NE_BAR_H)
}

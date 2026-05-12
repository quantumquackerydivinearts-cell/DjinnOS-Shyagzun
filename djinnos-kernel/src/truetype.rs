// truetype.rs -- Anti-aliased text rendering for DjinnOS.
//
// Glyph bitmaps are pre-rasterized at build time (build.rs) using fontdue
// on the host, then embedded as static arrays.  No runtime TrueType parsing
// required — all rendering is simple alpha-blended bitmap lookup.
//
// Two fonts:
//   Inter Regular          -- body text, headings, UI labels (FontId::Inter)
//   JetBrains Mono Regular -- code, REPL, Kobra output    (FontId::JbMono)
//
// Available sizes: 11, 12, 13, 14, 17 px (covers all Atelier UI sizes).

use crate::gpu::GpuSurface;

// Pull in the generated glyph tables from build.rs output.
include!(concat!(env!("OUT_DIR"), "/bitmaps_gen.rs"));

// ── Font ID ───────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum FontId { Inter, JbMono }

// ── Size ID (maps f32 size to the nearest pre-rasterized table) ───────────────

fn size_id(size_px: f32) -> u32 {
    let s = size_px as u32;
    // Snap to nearest available: 11, 12, 13, 14, 17
    match s {
        ..=11 => 110,
        12    => 120,
        13    => 130,
        14    => 140,
        _     => 170,
    }
}

// ── Glyph lookup ──────────────────────────────────────────────────────────────

fn lookup(font: FontId, ch: char, size_px: f32) -> Option<&'static GlyphEntry> {
    let sid = size_id(size_px);
    let cp  = ch as u32;
    let table: &[GlyphEntry] = match (font, sid) {
        (FontId::Inter,  110) => INTER_S110,
        (FontId::Inter,  120) => INTER_S120,
        (FontId::Inter,  130) => INTER_S130,
        (FontId::Inter,  140) => INTER_S140,
        (FontId::Inter,  _  ) => INTER_S170,
        (FontId::JbMono, 110) => JBMONO_S110,
        (FontId::JbMono, 120) => JBMONO_S120,
        (FontId::JbMono, 130) => JBMONO_S130,
        (FontId::JbMono, 140) => JBMONO_S140,
        (FontId::JbMono, _  ) => JBMONO_S170,
    };
    table.iter().find(|e| e.codepoint == cp)
}

// ── Core renderer ─────────────────────────────────────────────────────────────
//
// Renders `text` starting at (x, y) where y is the TOP of the em-box.
// Each glyph's alpha coverage byte is blended against the background.
// Returns the x position after the last glyph.
//
// Color convention: (b, g, r) matching GpuSurface.

pub fn text(
    gpu:     &dyn GpuSurface,
    x:       i32,
    y:       i32,
    s:       &str,
    size_px: f32,
    font_id: FontId,
    color:   (u8, u8, u8),   // (b, g, r)
) -> i32 {
    let (b, g, r) = color;
    let mut cx = x;
    let sw = gpu.width()  as i32;
    let sh = gpu.height() as i32;
    let baseline = y + (size_px * 0.78) as i32;

    for ch in s.chars() {
        let entry = match lookup(font_id, ch, size_px) {
            Some(e) => e,
            None    => { cx += (size_px * 0.5) as i32; continue; }
        };

        let gx = cx + entry.xmin;
        let gy = baseline - entry.height as i32 - entry.ymin;

        for row in 0..entry.height {
            let py = gy + row as i32;
            if py < 0 || py >= sh { continue; }
            for col in 0..entry.width {
                let px = gx + col as i32;
                if px < 0 || px >= sw { continue; }
                let alpha = entry.bitmap[row * entry.width + col];
                if alpha == 0 { continue; }
                if alpha == 255 {
                    gpu.set_pixel(px as u32, py as u32, b, g, r);
                } else {
                    let (db, dg, dr) = gpu.get_pixel(px as u32, py as u32);
                    let a  = alpha as u32;
                    let ia = 255 - a;
                    let nb = ((b as u32 * a + db as u32 * ia) / 255) as u8;
                    let ng = ((g as u32 * a + dg as u32 * ia) / 255) as u8;
                    let nr = ((r as u32 * a + dr as u32 * ia) / 255) as u8;
                    gpu.set_pixel(px as u32, py as u32, nb, ng, nr);
                }
            }
        }
        cx += entry.advance / 64;
    }
    cx
}

// ── Convenience wrappers ──────────────────────────────────────────────────────

pub fn inter(gpu: &dyn GpuSurface, x: i32, y: i32, s: &str,
             size_px: f32, color: (u8, u8, u8)) -> i32 {
    text(gpu, x, y, s, size_px, FontId::Inter, color)
}

pub fn mono(gpu: &dyn GpuSurface, x: i32, y: i32, s: &str,
            size_px: f32, color: (u8, u8, u8)) -> i32 {
    text(gpu, x, y, s, size_px, FontId::JbMono, color)
}

pub fn inter_width(s: &str, size_px: f32) -> i32 {
    s.chars().map(|c| {
        lookup(FontId::Inter, c, size_px)
            .map(|e| e.advance / 64)
            .unwrap_or((size_px * 0.5) as i32)
    }).sum()
}

pub fn mono_width(s: &str, size_px: f32) -> i32 {
    s.chars().map(|c| {
        lookup(FontId::JbMono, c, size_px)
            .map(|e| e.advance / 64)
            .unwrap_or((size_px * 0.5) as i32)
    }).sum()
}

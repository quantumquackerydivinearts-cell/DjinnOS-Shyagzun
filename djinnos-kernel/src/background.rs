// background.rs -- Living Shygazun byte-table desktop background.
//
// The desktop surface IS the language made visible.
// Eight tongue bands correspond to the first cluster (bytes 0-213):
//   Lotus(0-23) Rose(24-47) Sakura(48-97) Daisy(82-97)
//   AppleBlossom(98-127) Aster(128-155) Grapevine(156-181) Cannabis(182-213)
//
// Each band renders at very low luminance (85% darkened) so panels
// are fully legible over it.  A radial vignette brightens the center
// slightly.  Every ANIM_PERIOD frames the highlight byte advances one
// position around the palette ring, creating a slow living pulse.

use crate::gpu::GpuSurface;
use crate::palette;
use crate::style;
use crate::render2d::It;

// ── Tongue band definitions ───────────────────────────────────────────────────

struct TongueBand {
    mid_byte: u32,   // representative byte for palette color
    label:    &'static str,
}

const BANDS: &[TongueBand] = &[
    TongueBand { mid_byte: 11,  label: "Lotus"       },  // bytes 0-23
    TongueBand { mid_byte: 35,  label: "Rose"        },  // bytes 24-47
    TongueBand { mid_byte: 64,  label: "Sakura"      },  // bytes 48-97
    TongueBand { mid_byte: 89,  label: "Daisy"       },  // bytes 82-97
    TongueBand { mid_byte: 112, label: "AppleBlossom"},  // bytes 98-127
    TongueBand { mid_byte: 141, label: "Aster"       },  // bytes 128-155
    TongueBand { mid_byte: 169, label: "Grapevine"   },  // bytes 156-181
    TongueBand { mid_byte: 198, label: "Cannabis"    },  // bytes 182-213
];

// How dark the bands render (0=black, 100=full color).
const BAND_LUMINANCE: u32 = 8;
// How often the pulse byte advances (frames).
const ANIM_PERIOD: u64 = 90;
// Width of a tongue label in the background (drawn very dim).
const LABEL_SCALE: u32 = 1;

// ── Main render ───────────────────────────────────────────────────────────────

pub fn render(gpu: &dyn GpuSurface, frame: u64, content_h: u32) {
    let it = It::new(gpu);
    let t  = style::get();
    let w  = gpu.width();
    let h  = content_h;

    // Base fill: bg color
    it.fill(0, 0, w, h, t.bg);

    // Tongue bands as horizontal strips — luminance weighted by eigenstate.
    // Active tongues glow slightly brighter; idle tongues stay near bg.
    let band_h = h / BANDS.len() as u32;
    for (i, band) in BANDS.iter().enumerate() {
        let tongue_num = (i + 1) as u8; // T1=Lotus through T8=Cannabis
        let w8 = crate::eigenstate::weight(tongue_num); // 0-255, 128=average
        // Map weight to luminance: idle=4%, average=8%, hot=16%
        let lum = if w8 < 128 {
            BAND_LUMINANCE.saturating_sub(4)
        } else {
            let extra = ((w8 as u32 - 128) * 8 / 127).min(8);
            BAND_LUMINANCE + extra
        };
        let by = i as u32 * band_h;
        let bh = if i + 1 == BANDS.len() { h - by } else { band_h };
        let col = style::darken(palette::aki_color(band.mid_byte), 100 - lum);
        it.fill(0, by, w, bh, col);
    }

    // Radial vignette: center is slightly lighter than edges.
    // Approximate with vertical + horizontal gradient overlays at low alpha.
    let cx = w / 2;
    let cy = h / 2;
    let vr = style::darken(t.bg, 60);     // vignette dark edge
    let vc = style::mix(t.bg, t.surface, 40); // vignette brighter center
    // Horizontal: dark left + dark right edges
    it.grad_h(0, 0, cx, h, vr, vc);
    it.grad_h(cx, 0, cx, h, vc, vr);
    // Vertical: dark top + dark bottom edges (composited with alpha over hgrad)
    // Use fill_alpha to blend rather than overwrite
    it.fill_alpha(0, 0, w, cy / 2, t.bg, 80);
    it.fill_alpha(0, h.saturating_sub(cy / 2), w, cy / 2, t.bg, 80);

    // Animated pulse: one byte position glows slightly brighter.
    let pulse_byte = (frame / ANIM_PERIOD) % 214;
    let pulse_col  = style::darken(palette::aki_color(pulse_byte as u32), 50);
    let pulse_band = (pulse_byte * BANDS.len() as u64 / 214) as usize;
    let by = pulse_band as u32 * band_h;
    let bh = if pulse_band + 1 == BANDS.len() { h - by } else { band_h };
    // Thin bright stripe at the top of the pulsing band
    it.fill_alpha(0, by, w, 2, pulse_col, 120);

    // Tongue labels: very dim, right-aligned, one per band
    for (i, band) in BANDS.iter().enumerate() {
        let ty = i as u32 * band_h + band_h.saturating_sub(crate::font::GLYPH_H * LABEL_SCALE + 4);
        let tw = band.label.len() as u32 * crate::font::GLYPH_W * LABEL_SCALE;
        let tx = w.saturating_sub(tw + style::M4);
        let col = style::darken(palette::aki_color(BANDS[i].mid_byte), 60);
        it.text(tx, ty, band.label, LABEL_SCALE, col);
    }
}

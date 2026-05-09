// Shygazun semantic colour palette.
//
// Terminology:
//   aki     — individual phonetic carrier (sub-symbol primitive)
//   akinen  — discrete composition of aki; the atomic unit of the byte table
//   akinenwun — nonwhitespaced concatenation of 2+ akinen (a compound word)
//
// The "alphabetical ring through a triangular prism of RGB" —
// the canonical address sequence of the byte table (0 → 2048 capacity)
// is mapped around the RGB triangle with three primary vertices derived
// from the Rose tongue's spectrum (T2, bytes 24–30):
//
//   Ru  (byte  24) = Red     — first Rose spectrum akinen
//   Ki  (byte  27) = Green   — fourth Rose spectrum akinen
//   AE  (byte  30) = Violet  — seventh Rose spectrum akinen (closes to Red)
//
// At 2048 ring capacity each vertex falls at:
//   Red   vertex: byte    0  (and every 2048 thereafter)
//   Green vertex: byte  683  (2048 / 3)
//   Blue  vertex: byte 1365  (2048 × 2/3)
//
// The ring is 2048 (cluster 1+2 boundary, power-of-2) so new tongues
// added to the ledger fill remaining colour space without shifting existing
// addresses.
//
// Colour derivation:
//   Single akinen entry (has a byte address):
//     → aki_color(addr)  — the ring colour at that address
//   Akinenwun (glyph composed of multiple akinen):
//     → segment the glyph into its constituent akinen via sublayer::segment()
//     → average the ring colours of all recognised akinen
//     → this makes compound glyphs inherit the blended colour of their
//        phonemic composition
//   Entries without a glyph (Reserved / Meta structural primitives):
//     → aki_color(entry.address) — ring position at the entry's own address
//
// This module is the single source of truth for colour in the system.
// Tiler, HUD overlays, Orrery, and Ambroflow all share this derivation.

use crate::byte_table::ByteEntry;
use kobra_core::sublayer::segment;

// ── Ring constants ────────────────────────────────────────────────────────────

/// Total ring capacity (first two clusters, power-of-2 boundary).
const RING: u32 = 2048;

/// Named Rose-spectrum colours for direct reference.
/// All (B, G, R) to match BGRX framebuffer layout.
pub const RU: (u8,u8,u8) = (0x00, 0x00, 0xcc);  // Red    addr 24
pub const OT: (u8,u8,u8) = (0x00, 0x80, 0xcc);  // Orange addr 25
pub const EL: (u8,u8,u8) = (0x00, 0xcc, 0xcc);  // Yellow addr 26
pub const KI: (u8,u8,u8) = (0x00, 0xcc, 0x00);  // Green  addr 27
pub const FU: (u8,u8,u8) = (0xcc, 0x00, 0x00);  // Blue   addr 28
pub const KA: (u8,u8,u8) = (0xcc, 0x00, 0x88);  // Indigo addr 29
pub const AE: (u8,u8,u8) = (0xb0, 0x00, 0xcc);  // Violet addr 30

/// AppleBlossom elemental colours — for direct elemental references.
pub const FIRE:  (u8,u8,u8) = (0x00, 0x40, 0xcc);
pub const AIR:   (u8,u8,u8) = (0x00, 0xcc, 0xcc);
pub const WATER: (u8,u8,u8) = (0xcc, 0x50, 0x10);
pub const EARTH: (u8,u8,u8) = (0x10, 0x88, 0x30);

/// AppleBlossom dimensional colours — for direct register references.
pub const MIND_P:  (u8,u8,u8) = (0xe0, 0xd0, 0xff);
pub const MIND_M:  (u8,u8,u8) = (0x30, 0x20, 0x50);
pub const SPACE_P: (u8,u8,u8) = (0x40, 0xc0, 0xff);
pub const SPACE_M: (u8,u8,u8) = (0x80, 0x30, 0x20);
pub const TIME_P:  (u8,u8,u8) = (0x20, 0xd0, 0x80);
pub const TIME_M:  (u8,u8,u8) = (0x60, 0x20, 0x80);

pub const VOID_COL: (u8,u8,u8) = (0x12, 0x12, 0x1a);

// ── Ring → RGB mapping ────────────────────────────────────────────────────────

/// Map a byte-table address to its position on the RGB triangular prism ring.
/// Vertices:
///   addr   0 → Red
///   addr 683 → Green
///   addr 1365 → Blue (→ Violet toward Red)
/// The ring is continuous; addresses above 2047 wrap via addr % RING.
pub fn aki_color(addr: u32) -> (u8, u8, u8) {
    let pos = addr % RING;
    // Scale to 0-767 (three segments of 256 each).
    let t = (pos * 768) / RING;  // 0..767

    if t < 256 {
        // Segment 1: Red → Green
        let s = t;
        (0, s as u8, (255 - s) as u8)          // BGR
    } else if t < 512 {
        // Segment 2: Green → Blue
        let s = t - 256;
        (s as u8, (255 - s) as u8, 0)           // BGR
    } else {
        // Segment 3: Blue → Red (through Violet)
        let s = t - 512;
        ((255 - s) as u8, 0, s as u8)           // BGR
    }
}

// ── Glyph decomposition colour ────────────────────────────────────────────────

/// Decompose `glyph` into its constituent akinen via the longest-prefix
/// symbol matcher, then average the ring colours of all recognised akinen.
/// Unrecognised byte sequences (aki with no byte table entry) are skipped.
/// Returns the ring colour of `fallback_addr` if no akinen are recognised.
pub fn glyph_color(glyph: &[u8], fallback_addr: u32) -> (u8, u8, u8) {
    let (akinen, count) = segment(glyph);
    let mut b_sum = 0u32;
    let mut g_sum = 0u32;
    let mut r_sum = 0u32;
    let mut n     = 0u32;

    for i in 0..count {
        let ak = akinen[i];
        if ak.addr != u16::MAX {
            let col = aki_color(ak.addr as u32);
            b_sum += col.0 as u32;
            g_sum += col.1 as u32;
            r_sum += col.2 as u32;
            n     += 1;
        }
    }

    if n == 0 {
        aki_color(fallback_addr)
    } else {
        ((b_sum / n) as u8, (g_sum / n) as u8, (r_sum / n) as u8)
    }
}

// ── Entry colour — the public API ─────────────────────────────────────────────

/// Derive the semantic tile colour for any byte table entry.
///
/// For entries with a glyph: segment into akinen, blend their ring colours.
/// For entries without a glyph (Reserved / Meta structural primitives):
///   use the entry's own byte address on the ring — this gives Physics,
///   Chemistry, and MetaTopology entries distinct colours based on their
///   position at the threshold of cluster 1 (bytes 228–255) rather than
///   a flat uniform hue.
pub fn entry_color(e: &ByteEntry) -> (u8, u8, u8) {
    match e.glyph {
        Some(g) => glyph_color(g.as_bytes(), e.address.0),
        None    => aki_color(e.address.0),
    }
}

// ── Colour operations ─────────────────────────────────────────────────────────

pub const fn blend_ct(a: (u8,u8,u8), b: (u8,u8,u8)) -> (u8,u8,u8) {
    (a.0/2 + b.0/2, a.1/2 + b.1/2, a.2/2 + b.2/2)
}

pub fn blend(a: (u8,u8,u8), b: (u8,u8,u8)) -> (u8,u8,u8) {
    (a.0/2 + b.0/2, a.1/2 + b.1/2, a.2/2 + b.2/2)
}

pub fn bright(c: (u8,u8,u8)) -> (u8,u8,u8) {
    (c.0.saturating_add(0x40),
     c.1.saturating_add(0x40),
     c.2.saturating_add(0x40))
}

pub fn dim(c: (u8,u8,u8)) -> (u8,u8,u8) {
    (c.0 / 2, c.1 / 2, c.2 / 2)
}
// style.rs -- Ar: chromatic perception layer for DjinnOS.
//
// Ar (byte 185, Cannabis): chromatic perception / awareness of energetic
// quality (Rose through Mind -- the direct experience of frequency, color
// as felt rather than measured).
//
// All semantic color tokens derive from palette::aki_color() at specific
// byte table addresses. The visual language IS the language -- one source
// of truth. No magic hex values; every color traces back to a Shygazun word.
//
// Layout constants follow the base-12 Rose numeral geometry.
// Scale factors follow the font scale convention (SCALE=2 default).

use crate::palette;

// ── Semantic color tokens ─────────────────────────────────────────────────────

/// A complete visual theme -- all semantic color roles in one struct.
#[derive(Clone, Copy)]
pub struct Theme {
    // Backgrounds
    pub bg:         (u8,u8,u8),  // primary background
    pub surface:    (u8,u8,u8),  // panel / card surface (slightly elevated)
    pub elevated:   (u8,u8,u8),  // modal / tooltip (most elevated)
    pub selection:  (u8,u8,u8),  // selected item background

    // Text
    pub text:       (u8,u8,u8),  // primary text
    pub text_dim:   (u8,u8,u8),  // secondary / muted text
    pub text_inv:   (u8,u8,u8),  // inverted text (on accent bg)

    // Semantic roles
    pub accent:     (u8,u8,u8),  // interactive / focused
    pub header:     (u8,u8,u8),  // section headers / titles
    pub modified:   (u8,u8,u8),  // unsaved / changed state
    pub error:      (u8,u8,u8),  // errors and warnings
    pub success:    (u8,u8,u8),  // confirmation / success

    // Structure
    pub rule:       (u8,u8,u8),  // dividers and rules
    pub shadow:     (u8,u8,u8),  // drop shadows / depth
}

// ── Layout constants (Rose numeral geometry, base-12) ─────────────────────────

pub const M1:     u32 = 2;    // micro gap
pub const M2:     u32 = 4;    // small gap (Gaoh-level)
pub const M3:     u32 = 8;    // standard margin / MX-half
pub const M4:     u32 = 12;   // outer margin (MX -- Ao×12 = Shu)
pub const M6:     u32 = 24;   // section gap (2×M4)
pub const M12:    u32 = 48;   // large gap (4×M4)
pub const RADIUS: u32 = 6;    // default corner radius
pub const RULE_W: u32 = 1;    // divider / rule line thickness
pub const SCALE:  u32 = 2;    // default font scale

// ── Default themes ────────────────────────────────────────────────────────────

/// Ko theme -- the default DjinnOS visual language.
/// Midnight blue-green, gold headers, accent green.
/// Byte addresses chosen from the byte table for semantic resonance.
pub fn ko_theme() -> Theme {
    // Backgrounds: derived from low Cannabis addresses (grounded awareness)
    let bg       = darken(palette::aki_color(184), 80);   // At -- near presence, darkened
    let surface  = darken(palette::aki_color(184), 60);
    let elevated = darken(palette::aki_color(186), 50);   // Av -- relational consciousness
    let selection = darken(palette::aki_color(186), 30);

    // Text: high-luminance neutral, dim from mid Cannabis
    let text     = (0xC0, 0xC0, 0xC0);
    let text_dim = darken(palette::aki_color(199), 40);   // In -- chiral orientation
    let text_inv = (0x08, 0x08, 0x08);

    // Semantic: from named Shygazun words
    let accent   = palette::aki_color(193);               // Soa -- conscious persistence
    let header   = (0x4B, 0x96, 0xC8);                   // gold (B,G,R)
    let modified = palette::aki_color(166);               // Mek -- call/emit (orange-red region)
    let error    = palette::aki_color(170);               // Dyne -- broadcast/flood (red)
    let success  = palette::aki_color(193);               // Soa again, brighter

    // Structure
    let rule     = darken(text_dim, 60);
    let shadow   = darken(bg, 90);

    Theme { bg, surface, elevated, selection,
            text, text_dim, text_inv,
            accent, header, modified, error, success,
            rule, shadow }
}

/// Faerie theme -- absinthe green x sugarfloss pink.
/// For the Faerie browser; matches Kyompufwun.
pub fn faerie_theme() -> Theme {
    let bg      = (0x08, 0x0e, 0x08);
    let surface = (0x0c, 0x14, 0x0c);
    Theme {
        bg, surface,
        elevated:  (0x10, 0x1c, 0x10),
        selection: (0x18, 0x28, 0x18),
        text:      (0x32, 0xa0, 0x14),   // absinthe text (B,G,R)
        text_dim:  (0x20, 0x60, 0x0c),
        text_inv:  (0x04, 0x06, 0x04),
        accent:    (0xe8, 0x9b, 0xc3),   // sugarfloss accent (B,G,R)
        header:    (0x50, 0xd2, 0x28),
        modified:  (0xff, 0xaa, 0xdc),
        error:     (0x40, 0x40, 0xe0),
        success:   (0x32, 0xa0, 0x14),
        rule:      (0x18, 0x30, 0x18),
        shadow:    (0x04, 0x06, 0x04),
    }
}

/// Voxel theme -- warm earth tones for scene editing.
pub fn voxel_theme() -> Theme {
    let bg = (0x10, 0x08, 0x06);
    Theme {
        bg, surface: (0x18, 0x10, 0x0c),
        elevated:  (0x22, 0x16, 0x10),
        selection: (0x18, 0x28, 0x10),
        text:      (0xC0, 0xC0, 0xC0),
        text_dim:  (0x60, 0x58, 0x50),
        text_inv:  (0x08, 0x06, 0x04),
        accent:    palette::aki_color(193),
        header:    (0x30, 0x80, 0xC0),
        modified:  (0x60, 0x60, 0xD0),
        error:     (0x40, 0x40, 0xE0),
        success:   palette::bright(palette::aki_color(193)),
        rule:      (0x30, 0x28, 0x20),
        shadow:    (0x04, 0x02, 0x02),
    }
}

// ── Active theme ──────────────────────────────────────────────────────────────

static mut ACTIVE: Theme = Theme {
    bg: (0x10, 0x08, 0x06), surface: (0x10, 0x08, 0x06),
    elevated: (0x10, 0x08, 0x06), selection: (0x18, 0x28, 0x10),
    text: (0xC0, 0xC0, 0xC0), text_dim: (0x60, 0x58, 0x50),
    text_inv: (0x08, 0x08, 0x08),
    accent: (0x88, 0xD0, 0x60), header: (0x4B, 0x96, 0xC8),
    modified: (0x60, 0x60, 0xD0), error: (0x40, 0x40, 0xE0),
    success: (0x88, 0xD0, 0x60),
    rule: (0x30, 0x28, 0x20), shadow: (0x04, 0x02, 0x02),
};

pub fn init() { unsafe { ACTIVE = ko_theme(); } }
pub fn set(t: Theme) { unsafe { ACTIVE = t; } }
pub fn get() -> Theme { unsafe { ACTIVE } }

// Fast token accessors
pub fn bg()        -> (u8,u8,u8) { unsafe { ACTIVE.bg } }
pub fn surface()   -> (u8,u8,u8) { unsafe { ACTIVE.surface } }
pub fn elevated()  -> (u8,u8,u8) { unsafe { ACTIVE.elevated } }
pub fn selection() -> (u8,u8,u8) { unsafe { ACTIVE.selection } }
pub fn text()      -> (u8,u8,u8) { unsafe { ACTIVE.text } }
pub fn text_dim()  -> (u8,u8,u8) { unsafe { ACTIVE.text_dim } }
pub fn text_inv()  -> (u8,u8,u8) { unsafe { ACTIVE.text_inv } }
pub fn accent()    -> (u8,u8,u8) { unsafe { ACTIVE.accent } }
pub fn header()    -> (u8,u8,u8) { unsafe { ACTIVE.header } }
pub fn modified()  -> (u8,u8,u8) { unsafe { ACTIVE.modified } }
pub fn error()     -> (u8,u8,u8) { unsafe { ACTIVE.error } }
pub fn success()   -> (u8,u8,u8) { unsafe { ACTIVE.success } }
pub fn rule()      -> (u8,u8,u8) { unsafe { ACTIVE.rule } }
pub fn shadow()    -> (u8,u8,u8) { unsafe { ACTIVE.shadow } }

/// Warm Atelier theme -- botanical warmth matching the web Atelier exactly.
/// CSS variables translated to (b, g, r) tuples for the framebuffer.
///
///   --bg          #f4f0e8   warm cream background
///   --ink         #1c1a16   near-black text
///   --accent      #2f6d62   sage green interactive
///   --accent-soft #d7ebe6   pale sage highlight / selection
///   --panel       #fffaf1   off-white panel surface
///   --line        #d8cbb8   warm taupe border / rule
pub fn warm_theme() -> Theme {
    // hex #rrggbb → (b, g, r)
    let bg         = (0xe8u8, 0xf0u8, 0xf4u8); // #f4f0e8
    let surface    = (0xf1u8, 0xfau8, 0xffu8); // #fffaf1
    let elevated   = (0xefu8, 0xf7u8, 0xffu8); // #fff7ef — modal
    let selection  = (0xe6u8, 0xebu8, 0xd7u8); // #d7ebe6 accent-soft
    let text       = (0x16u8, 0x1au8, 0x1cu8); // #1c1a16 ink
    let text_dim   = (0x80u8, 0x85u8, 0x8au8); // muted warm grey
    let text_inv   = (0xf0u8, 0xf4u8, 0xf8u8); // near-white on accent bg
    let accent     = (0x62u8, 0x6du8, 0x2fu8); // #2f6d62 sage green
    let header     = (0x34u8, 0x3au8, 0x17u8); // #173a34 dark sage
    let modified   = (0x14u8, 0x5du8, 0x7bu8); // #7b5d14 warning amber
    let error      = (0x23u8, 0x23u8, 0x7au8); // #7a2323 warm red
    let success    = (0x3au8, 0x58u8, 0x23u8); // #23583a forest green
    let rule       = (0xb8u8, 0xcbu8, 0xd8u8); // #d8cbb8 warm taupe
    let shadow     = (0xd4u8, 0xdbu8, 0xe0u8); // slightly darker bg
    Theme { bg, surface, elevated, selection,
            text, text_dim, text_inv,
            accent, header, modified, error, success,
            rule, shadow }
}

/// Sidebar gradient endpoints for the warm Atelier.
/// Top of sidebar = #fef6e8, bottom = #f4ecdc (both (b, g, r)).
pub const WARM_SIDEBAR_TOP: (u8,u8,u8) = (0xe8u8, 0xf6u8, 0xfeu8);
pub const WARM_SIDEBAR_BOT: (u8,u8,u8) = (0xdcu8, 0xecu8, 0xf4u8);

// ── Color utilities ───────────────────────────────────────────────────────────

/// Scale all channels toward black by `pct` percent (0=unchanged, 100=black).
pub fn darken(c: (u8,u8,u8), pct: u32) -> (u8,u8,u8) {
    let scale = (100 - pct.min(100)) as u32;
    ((c.0 as u32 * scale / 100) as u8,
     (c.1 as u32 * scale / 100) as u8,
     (c.2 as u32 * scale / 100) as u8)
}

/// Scale all channels toward white by `pct` percent.
pub fn lighten(c: (u8,u8,u8), pct: u32) -> (u8,u8,u8) {
    let p = pct.min(100) as u32;
    (((c.0 as u32 * (100 - p) + 255 * p) / 100) as u8,
     ((c.1 as u32 * (100 - p) + 255 * p) / 100) as u8,
     ((c.2 as u32 * (100 - p) + 255 * p) / 100) as u8)
}

/// Blend two colours at a given ratio (0=all a, 255=all b).
pub fn mix(a: (u8,u8,u8), b: (u8,u8,u8), t: u8) -> (u8,u8,u8) {
    let t  = t as u32;
    let it = 255 - t;
    (((a.0 as u32 * it + b.0 as u32 * t) / 255) as u8,
     ((a.1 as u32 * it + b.1 as u32 * t) / 255) as u8,
     ((a.2 as u32 * it + b.2 as u32 * t) / 255) as u8)
}
// renderer_bridge — Ko's Labyrinth rendering contract.
//
// Source of truth: DjinnOS_Shyagzun/shygazun/sanctum/renderer_bridge.ko
//
// The .ko file is compiled in at build time so the kernel always carries
// the authoritative spec alongside it.  Stage 2 (Kobra VM) will decode
// the Shygazun colour tokens at runtime; for Stage 1 the colour tables
// are the pre-decoded form of the same contract, marked with their LoKiel
// origin entry for when the VM makes the live decode possible.
//
// What this module currently provides from renderer_bridge.ko:
//
//   LoYeshu (Cannabis mode map)
//     → tile pixel sizes for modes A / I / Y
//     → z-scale values for each mode
//
//   LoYe (time topology map)
//     → walkability per topology token (Va = passable, Vo = impassable)
//     → used to cross-check the ASCII passability table
//
//   LoKiel (tongue colour map)  ← Stage 2: decoded via Kobra VM
//     Currently: pre-decoded BGRx triples mirroring gl_world_play.py
//     constants.  Each entry is annotated with its LoKiel compound token.
//
//   LoShu (axis map)            ← Stage 2
//   LoAo  (chirality map)       ← Stage 2
//   LoLao (cluster / LOD map)   ← Stage 2

// The .ko source is embedded per call-site via include_bytes! so it never
// becomes a module-level &[u8] constant (which would require a GOT entry
// under the pic relocation model, but we use relocation-model=static).

// ── Cannabis mode tile sizes (LoYeshu) ────────────────────────────────────────
//
// Parsed from:
//   [A  MavoTile Ao Shu    MavoZScale Ao Gaoh]   → tile = Ao×12+Shu  = 16, z=12
//   [I  MavoTile Ao Shushy MavoZScale Shushy  ]   → tile = Ao×12+Shushy = 20, z=8
//   [Y  MavoTile Ao Ye     MavoZScale Yeshu   ]   → tile = Ao×12+Ye  = 14, z=6
//
// Rose numerals (base-12): Gaoh=0 Ao=1 Ye=2 Ui=3 Shu=4 Kiel=5 Yeshu=6
//                           Lao=7 Shushy=8 Uinshu=9 Kokiel=10 Aonkiel=11

pub const TILE_A: u32 = 16;   // Cannabis mode A  — primary world view
pub const TILE_I: u32 = 20;   // Cannabis mode I  — detail view
pub const TILE_Y: u32 = 14;   // Cannabis mode Y  — overview

pub const ZSCALE_A: u32 = 12;
pub const ZSCALE_I: u32 =  8;
pub const ZSCALE_Y: u32 =  6;

// ── Entity colours (LoKiel pre-decode, matching gl_world_play.py) ─────────────
//
// All values are (B, G, R) to match the BGRX framebuffer layout.
// They mirror the Python constants in gl_world_play.py exactly.
//
// LoKiel decode target (Stage 2):
//   MavoAorutakael  BG=ZoFuMel   EDGE=FuMel   — Lapidus base tile palette
//
// Player and NPC colours match _PLAYER_FILL / _NPC_FILL / _PLAYER_SHADOW /
// _NPC_OUTLINE from gl_world_play.py so the two renderers produce identical
// entity tokens.

pub const PLAYER_FILL:   (u8, u8, u8) = (100, 190, 220);  // BGR of (220,190,100)
pub const PLAYER_SHADOW: (u8, u8, u8) = ( 20,  60,  80);  // BGR of ( 80, 60, 20)
pub const NPC_FILL:      (u8, u8, u8) = (180, 160, 160);  // BGR of (160,160,180)
pub const NPC_OUTLINE:   (u8, u8, u8) = (120, 100, 100);  // BGR of (100,100,120)
pub const HUD_TEXT:      (u8, u8, u8) = (130, 180, 200);  // BGR of (200,180,130)
pub const HUD_ACCENT:    (u8, u8, u8) = ( 50, 155, 200);  // BGR of (200,155, 50)

// ── Lapidus tile colours (LoKiel pre-decode) ──────────────────────────────────
//
// Mirrors _LAP_FILL and _LAP_EDGE from gl_world_play.py (RGB→BGR).
// LoKiel entry tokens are listed as comments for Stage 2 wiring.
//
//   MavoAorutakael    ZoFuMel   — background palette for Lapidus
//   MavoAokitakael    KaAE      — edge/accent palette
//   (full decode: see renderer_bridge.ko LoKiel)

/// Resolve the fill (B,G,R) and edge (B,G,R) colours for an ASCII tile character.
/// Colour values are the pre-decoded form of renderer_bridge.ko LoKiel entries.
/// Returns VOID (black) for unknown characters.
/// Implemented as a match to avoid any slice-reference GOT dependency.
pub fn tile_colors(ch: u8) -> ((u8, u8, u8), (u8, u8, u8)) {
    let ch = match ch { b'@' | b'N' => b'.', c => c };
    match ch {
        b'#' => (( 54,  70,  82), ( 36,  50,  60)), // WALL
        b'W' => (( 72,  98, 118), ( 55,  78,  95)), // WALL_FACE
        b'.' => (( 48,  60,  68), ( 36,  46,  52)), // FLOOR
        b'+' => (( 42,  78, 112), ( 55, 100, 140)), // DOOR
        b',' => (( 38,  88,  50), ( 28,  70,  38)), // GRASS
        b'=' => (( 70,  96, 112), ( 54,  78,  92)), // ROAD
        b'D' => (( 48,  74,  95), ( 35,  55,  70)), // DIRT
        b'S' => (( 72,  82,  88), ( 55,  62,  68)), // STONE
        b'~' => (( 98,  56,  28), ( 78,  42,  18)), // WATER
        b'/' => (( 50,  80, 100), ( 38,  62,  78)), // BRIDGE
        b'^' => (( 65,  85,  95), ( 48,  65,  72)), // STAIRS_UP
        b'v' => (( 40,  52,  60), ( 28,  38,  45)), // STAIRS_DOWN
        b'T' => (( 18,  55,  18), ( 10,  40,  10)), // TREE
        b'M' => ((200, 215, 220), (162, 175, 180)), // MARBLE
        b'Y' => (( 55, 145, 185), ( 38, 118, 155)), // YELLOW_BRICK
        b'C' => ((155, 128,  88), (130, 105,  68)), // CERAMIC
        b'L' => (( 88,  78,  72), ( 70,  60,  54)), // SLATE
        b'X' => ((165, 185, 195), (138, 155, 165)), // SILICA
        _    => ((  0,   0,   0), (  0,   0,   0)), // VOID
    }
}

/// Return true when an ASCII tile character is passable by the player.
/// Derived from LoYe (time topology) of renderer_bridge.ko.
///   Va (walkable) tokens: Si Su Se As → passable surface types
///   Vo (void/solid) tokens: Os Sy → impassable surface types
/// Applied to ASCII tile chars via the zone tile codec.
pub fn passable(ch: u8) -> bool {
    matches!(ch,
        b'.' | b'+' | b',' | b'=' | b'D' | b'S' | b'/'
        | b'^' | b'v' | b'P' | b'E' | b'M' | b'Y' | b'C'
        | b'L' | b'X' | b'@' | b'N'
    )
}

// ── Cannabis mode selector ────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum CannabisMode { A, I, Y }

impl CannabisMode {
    pub fn tile_px(self) -> u32 {
        match self { Self::A => TILE_A, Self::I => TILE_I, Self::Y => TILE_Y }
    }
    pub fn zscale(self) -> u32 {
        match self { Self::A => ZSCALE_A, Self::I => ZSCALE_I, Self::Y => ZSCALE_Y }
    }
}

// ── Runtime verification (zero-allocation) ────────────────────────────────────
//
// Reads the embedded _KO_DATA at init time and verifies that the compile-time
// constants above match what the .ko file actually declares.
// Uses only stack memory — no heap allocations — so it is safe to call
// before the heap is fully warmed up.
//
// Stage 2: this function will also decode LoKiel colour tokens once the Kobra
// VM is available, replacing the pre-decoded tables above.

pub fn verify_and_log() {
    let ko: &[u8] = include_bytes!(
        "../../DjinnOS_Shyagzun/shygazun/sanctum/rndrbdge.ko"
    );
    match parse_cannabis_modes_noalloc(ko) {
        Some((a, i, y)) => {
            let ok = a == TILE_A && i == TILE_I && y == TILE_Y;
            if ok {
                crate::uart::puts("renderer_bridge: cannabis modes verified (A=");
            } else {
                crate::uart::puts("renderer_bridge: WARNING mismatch (A=");
            }
            crate::uart::putu(a as u64); crate::uart::puts(" I=");
            crate::uart::putu(i as u64); crate::uart::puts(" Y=");
            crate::uart::putu(y as u64); crate::uart::puts(")\r\n");
        }
        None => {
            crate::uart::puts("renderer_bridge: could not parse cannabis modes\r\n");
        }
    }
}

// ── Zero-allocation .ko parser ────────────────────────────────────────────────
//
// Parses Cannabis mode tile sizes from LoYeshu without touching the heap.
// Uses a small fixed-size token array on the stack.
// Sufficient for the known structure of renderer_bridge.ko.

const ROSE: &[(&[u8], u32)] = &[
    (b"Gaoh", 0), (b"Ao", 1), (b"Ye", 2), (b"Ui", 3), (b"Shu", 4), (b"Kiel", 5),
    (b"Yeshu", 6), (b"Lao", 7), (b"Shushy", 8), (b"Uinshu", 9),
    (b"Kokiel", 10), (b"Aonkiel", 11),
];

fn rose_val(tok: &[u8]) -> Option<u32> {
    for (name, v) in ROSE { if *name == tok { return Some(*v); } }
    None
}

/// Read one base-12 Rose numeral (1 or 2 tokens). Returns (value, consumed).
fn rose_read<'a>(toks: &[&'a [u8]], i: usize) -> (u32, usize) {
    if i >= toks.len() { return (0, 0); }
    if let Some(v0) = rose_val(toks[i]) {
        if i + 1 < toks.len() {
            if let Some(v1) = rose_val(toks[i + 1]) {
                return (v0 * 12 + v1, 2);
            }
        }
        return (v0, 1);
    }
    (0, 0)
}

/// Skip whitespace in a byte slice; returns new position.
fn skip_ws(data: &[u8], mut i: usize) -> usize {
    while i < data.len()
        && (data[i] == b' ' || data[i] == b'\t'
         || data[i] == b'\n' || data[i] == b'\r')
    { i += 1; }
    // Skip # comments
    if i < data.len() && data[i] == b'#' {
        while i < data.len() && data[i] != b'\n' { i += 1; }
        return skip_ws(data, i);
    }
    i
}

/// Read one token (non-whitespace, non-bracket run). Returns (slice, new_pos).
fn read_tok(data: &[u8], i: usize) -> Option<(&[u8], usize)> {
    let i = skip_ws(data, i);
    if i >= data.len() { return None; }
    let c = data[i];
    if c == b'[' || c == b']' || c == b'{' || c == b'}' || c == b':' {
        return Some((&data[i..i + 1], i + 1));
    }
    let start = i;
    let mut j = i;
    while j < data.len() {
        let b = data[j];
        if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r'
            || b == b'[' || b == b']' || b == b'{' || b == b'}'
            || b == b':' || b == b'(' || b == b')' { break; }
        j += 1;
    }
    if j > start { Some((&data[start..j], j)) } else { None }
}

/// Locate the first `[...]` block containing `needle` after `start`.
/// Returns position just past the closing `]`, and the inner content slice.
fn find_spec_with<'a>(data: &'a [u8], start: usize, needle: &[u8])
    -> Option<(&'a [u8], usize)>
{
    let mut i = start;
    while i < data.len() {
        if data[i] == b'[' {
            let open = i + 1;
            let mut depth = 1u32;
            let mut j = open;
            while j < data.len() && depth > 0 {
                if data[j] == b'[' { depth += 1; }
                else if data[j] == b']' { depth -= 1; }
                j += 1;
            }
            let inner = &data[open..j.saturating_sub(1)];
            if inner.windows(needle.len()).any(|w| w == needle) {
                return Some((inner, j));
            }
            i = j;
        } else {
            i += 1;
        }
    }
    None
}

/// Locate the body of a LoXxx section.
fn find_section_body(data: &[u8], lo_name: &[u8]) -> Option<(usize, usize)> {
    let mut i = 0;
    while i + lo_name.len() < data.len() {
        if data[i..].starts_with(lo_name) {
            let mut j = i + lo_name.len();
            while j < data.len() && data[j] != b'{' { j += 1; }
            if j >= data.len() { return None; }
            j += 1;
            let start = j;
            let mut depth = 1u32;
            while j < data.len() && depth > 0 {
                if data[j] == b'{' { depth += 1; }
                else if data[j] == b'}' { depth -= 1; }
                j += 1;
            }
            return Some((start, j.saturating_sub(1)));
        }
        i += 1;
    }
    None
}

/// Parse Cannabis mode tile sizes from LoYeshu — zero heap allocations.
fn parse_cannabis_modes_noalloc(data: &[u8]) -> Option<(u32, u32, u32)> {
    let (sec_start, sec_end) = find_section_body(data, b"LoYeshu")?;
    let section = &data[sec_start..sec_end];

    // Fixed-size token buffer — enough for one spec line
    const MAX_TOKS: usize = 16;
    let mut tile_a: Option<u32> = None;
    let mut tile_i: Option<u32> = None;
    let mut tile_y: Option<u32> = None;

    // Walk specs in LoYeshu, looking for MavoTile entries
    let mut pos = 0usize;
    loop {
        let (inner, next) = match find_spec_with(section, pos, b"MavoTile") {
            Some(v) => v,
            None    => break,
        };
        pos = next;

        // Tokenise inner into fixed array (no alloc)
        let mut toks: [&[u8]; MAX_TOKS] = [b""; MAX_TOKS];
        let mut n = 0usize;
        let mut ip = 0usize;
        while n < MAX_TOKS {
            match read_tok(inner, ip) {
                Some((tok, np)) => { toks[n] = tok; n += 1; ip = np; }
                None => break,
            }
        }
        if n == 0 { continue; }

        // TaShyMa = closure marker — skip
        if toks[..n].iter().any(|t| *t == b"TaShyMa") { continue; }

        // First token is the Cannabis mode (A / I / Y)
        let mode = toks[0];

        // Find MavoTile position and read the Rose pair after it
        let tp = toks[..n].iter().position(|t| *t == b"MavoTile");
        if let Some(tp) = tp {
            let (tile_sz, _) = rose_read(&toks[..n], tp + 1);
            match mode {
                b"A" => tile_a = Some(tile_sz),
                b"I" => tile_i = Some(tile_sz),
                b"Y" => tile_y = Some(tile_sz),
                _ => {}
            }
        }
    }

    Some((tile_a?, tile_i?, tile_y?))
}
// Shygazun byte table tiler — live structural map of the ledger.
//
// Groups are derived from BYTE_TABLE at render time; no hardcoded address
// ranges.  Tile colour comes from palette::entry_color, which maps each
// entry's address (and glyph akinen composition) onto the RGB ring.
//
// Invoked with `tiler` from the Ko shell.  Arrow keys navigate; Esc exits.

use crate::byte_table::{self, ByteEntry, EntryKind, Tongue, BYTE_TABLE};
use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::palette;

const SCALE:   u32 = 2;
const CHAR_W:  u32 = font::GLYPH_W * SCALE;
const CHAR_H:  u32 = font::GLYPH_H * SCALE;
const TILE:    u32 = 12;
const GAP:     u32 = 2;
const STEP:    u32 = TILE + GAP;
const MAX_GRP: usize = 64;

const BG_R: u8 = 0x06; const BG_G: u8 = 0x06; const BG_B: u8 = 0x0a;

// ── Phonetic tree ─────────────────────────────────────────────────────────────

const MAX_ROOTS:    usize = 80;
const MAX_PER_ROOT: usize = 160;

#[derive(Clone, Copy)]
struct PhonemeRoot {
    key:    [u8; 4],   // initial phoneme cluster, e.g. b"Sh\0\0"
    key_n:  usize,
    addrs:  [u32; MAX_PER_ROOT],
    count:  usize,
}

impl PhonemeRoot {
    const EMPTY: Self = PhonemeRoot {
        key: [0u8; 4], key_n: 0,
        addrs: [0u32; MAX_PER_ROOT], count: 0,
    };
    fn key_str(&self) -> &[u8] { &self.key[..self.key_n] }
}

// ── Shygazun syllabism ────────────────────────────────────────────────────────
//
// Syllable structure: (C)(C)V(C*)
//   onset  = initial consonant(s), max 2 for known digraphs
//   nucleus = one or more vowels
//   coda    = trailing consonants only if followed by another consonant or EOS
//             (if the next character after a consonant is a vowel, that
//             consonant is the onset of the NEXT syllable, not this coda)
//
// Vowels: a e i o u.  Y is consonant-initial (Time+ akinen).
//
// Known digraph onsets: Rh Sh Zh Dv Kw Gw Ny Ng Ra'- (prime after root)

fn is_vowel(c: u8) -> bool {
    matches!(c.to_ascii_lowercase(), b'a' | b'e' | b'i' | b'o' | b'u')
}

fn is_cons(c: u8) -> bool {
    c.is_ascii_alphabetic() && !is_vowel(c)
}

fn is_digraph(c0: u8, c1: u8) -> bool {
    matches!(
        (c0.to_ascii_uppercase(), c1.to_ascii_lowercase()),
        (b'R',b'h') | (b'S',b'h') | (b'Z',b'h') |
        (b'D',b'v') | (b'K',b'w') | (b'G',b'w') |
        (b'N',b'y') | (b'N',b'g') | (b'R',b'a')
    )
}

/// Extract the first complete syllable from `sym` starting at byte offset `from`.
/// Returns (syllable_bytes, syllable_len, chars_consumed_from_sym[from..]).
fn first_syllable_at(b: &[u8], from: usize) -> ([u8; 8], usize, usize) {
    let b = &b[from..];
    let len = b.len();
    if len == 0 { return ([0u8; 8], 0, 0); }

    let mut out = [0u8; 8];
    let mut oi  = 0usize;
    let mut ci  = 0usize; // index into b

    // Phase 1: consonant onset (1 or 2 chars for digraph)
    if ci < len && is_cons(b[ci]) {
        let take2 = ci + 1 < len && is_digraph(b[ci], b[ci + 1]);
        out[oi] = b[ci].to_ascii_uppercase(); oi += 1; ci += 1;
        if take2 && oi < 8 { out[oi] = b[ci].to_ascii_lowercase(); oi += 1; ci += 1; }
    }

    let had_onset = ci > 0;

    // Phase 2: vowel nucleus
    let nucleus_start = oi;
    while ci < len && is_vowel(b[ci]) && oi < 8 {
        out[oi] = b[ci].to_ascii_lowercase(); oi += 1; ci += 1;
    }

    // If no vowel and had onset: return just the consonant onset
    if oi == nucleus_start && !had_onset {
        // vowel-initial with no onset: consume the vowel
        if ci < len && is_vowel(b[ci]) && oi < 8 {
            out[oi] = b[ci].to_ascii_lowercase(); oi += 1; ci += 1;
        }
    }

    // Phase 3: coda — consonants that are NOT the onset of the next syllable
    // A consonant is coda if the character AFTER it is another consonant or EOS.
    while ci < len && is_cons(b[ci]) && oi < 8 {
        let next = if ci + 1 < len { b[ci + 1] } else { 0 };
        if next == 0 || is_cons(next) {
            // coda: absorb
            out[oi] = b[ci].to_ascii_lowercase(); oi += 1; ci += 1;
        } else {
            break; // onset of next syllable
        }
    }

    // Skip non-alpha (hyphens, apostrophes)
    while ci < len && !b[ci].is_ascii_alphabetic() { ci += 1; }

    if oi == 0 { (out, 0, ci.max(1)) } else { (out, oi, ci) }
}

/// Extract ALL syllables of a symbol (up to 6).
fn all_syllables(sym: &str) -> ([[u8; 8]; 6], [usize; 6], usize) {
    let b = sym.as_bytes();
    let mut syls   = [[0u8; 8]; 6];
    let mut slens  = [0usize; 6];
    let mut count  = 0usize;
    let mut pos    = 0usize;
    while pos < b.len() && count < 6 {
        let (syl, slen, consumed) = first_syllable_at(b, pos);
        if consumed == 0 || slen == 0 { break; }
        syls[count]  = syl;
        slens[count] = slen;
        count += 1;
        pos += consumed;
    }
    (syls, slens, count)
}

/// Check whether a syllable matches a known standalone glyph in the byte table.
/// Used for cross-referencing: if "ko" appears as a morpheme in "Yefko",
/// and "Ko" is in the table, "Yefko" is indexed under the Ko group too.
fn is_known_glyph(syl: &[u8], slen: usize) -> bool {
    if slen == 0 { return false; }
    BYTE_TABLE.iter().any(|e| {
        if let Some(g) = e.glyph {
            let gb = g.as_bytes();
            gb.len() == slen && gb.iter().zip(&syl[..slen]).all(|(a,b)|
                a.to_ascii_lowercase() == b.to_ascii_lowercase())
        } else { false }
    })
}

/// Add an entry address to a root group, creating the group if needed.
fn roots_add(roots: &mut [PhonemeRoot; MAX_ROOTS], n: &mut usize,
             key: [u8; 8], kn: usize, addr: u32, cross_ref: bool)
{
    if kn == 0 { return; }
    // Pack key into the 4-byte field (only first 4 chars used for grouping)
    let mut k4 = [0u8; 4];
    k4[..kn.min(4)].copy_from_slice(&key[..kn.min(4)]);
    let kn4 = kn.min(4);

    let ri = roots[..*n].iter().position(|r| r.key[..r.key_n] == k4[..kn4]);
    let ri = match ri {
        Some(i) => i,
        None => {
            if *n >= MAX_ROOTS { return; }
            roots[*n].key   = k4;
            roots[*n].key_n = kn4;
            let i = *n; *n += 1; i
        }
    };
    // Avoid duplicate addresses
    let already = roots[ri].addrs[..roots[ri].count].contains(&addr);
    if !already && roots[ri].count < MAX_PER_ROOT {
        roots[ri].addrs[roots[ri].count] = addr;
        roots[ri].count += 1;
    }
    let _ = cross_ref;
}

/// Build phoneme root groups from the full BYTE_TABLE.
/// Each entry is indexed under its PRIMARY syllable.
/// Compound entries (multi-syllable) are ALSO cross-referenced under any
/// secondary syllables that match a known standalone glyph (e.g. "Yefko"
/// appears under "Yef" AND under "Ko" because Ko is a known root).
fn build_phoneme_roots() -> ([PhonemeRoot; MAX_ROOTS], usize) {
    let mut roots = [PhonemeRoot::EMPTY; MAX_ROOTS];
    let mut n = 0usize;

    for e in BYTE_TABLE {
        let sym = match e.glyph { Some(g) => g, None => continue };
        let (syls, slens, scount) = all_syllables(sym);

        if scount == 0 { continue; }

        // Primary: first syllable
        roots_add(&mut roots, &mut n, syls[0], slens[0], e.address.0, false);

        // Cross-reference: secondary syllables that are known standalone glyphs
        for si in 1..scount {
            if slens[si] > 0 && is_known_glyph(&syls[si], slens[si]) {
                roots_add(&mut roots, &mut n, syls[si], slens[si], e.address.0, true);
            }
        }
    }

    // Sort entries within each root by tongue number then address
    for ri in 0..n {
        let cnt = roots[ri].count;
        for i in 1..cnt {
            let mut j = i;
            while j > 0 {
                let ta = tongue_num_of_addr(roots[ri].addrs[j-1]);
                let tb = tongue_num_of_addr(roots[ri].addrs[j]);
                if ta > tb || (ta == tb && roots[ri].addrs[j-1] > roots[ri].addrs[j]) {
                    let tmp = roots[ri].addrs[j-1];
                    roots[ri].addrs[j-1] = roots[ri].addrs[j];
                    roots[ri].addrs[j]   = tmp;
                    j -= 1;
                } else { break; }
            }
        }
    }

    // Sort roots alphabetically by key
    for i in 1..n {
        let mut j = i;
        while j > 0 && roots[j].key[..roots[j].key_n] < roots[j-1].key[..roots[j-1].key_n] {
            roots.swap(j, j-1); j -= 1;
        }
    }

    (roots, n)
}

fn tongue_num_of_addr(addr: u32) -> u32 {
    match byte_table::lookup(addr) {
        None    => 999,
        Some(e) => match e.tongue {
            None    => 999,
            Some(t) => tongue_to_num(t),
        }
    }
}

fn tongue_to_num(t: Tongue) -> u32 {
    match t {
        Tongue::Lotus => 1, Tongue::Rose => 2, Tongue::Sakura => 3,
        Tongue::Daisy => 4, Tongue::AppleBlossom => 5, Tongue::Aster => 6,
        Tongue::Grapevine => 7, Tongue::Cannabis => 8,
        Tongue::Dragon => 9, Tongue::Virus => 10, Tongue::Bacteria => 11,
        Tongue::Excavata => 12, Tongue::Archaeplastida => 13, Tongue::Myxozoa => 14,
        Tongue::Archea => 15, Tongue::Protist => 16,
        Tongue::Immune => 17, Tongue::Neural => 18, Tongue::Serpent => 19,
        Tongue::Beast => 20, Tongue::Cherub => 21, Tongue::Chimera => 22,
        Tongue::Faerie => 23, Tongue::Djinn => 24,
        Tongue::Fold => 25, Tongue::Topology => 26, Tongue::Phase => 27,
        Tongue::Gradient => 28, Tongue::Curvature => 29, Tongue::Prion => 30,
        Tongue::Blood => 31, Tongue::Moon => 32,
        Tongue::Koi => 33, Tongue::Rope => 34, Tongue::Hook => 35,
        Tongue::Fang => 36, Tongue::Circle => 37, Tongue::Ledger => 38,
    }
}

/// Tab selector
#[derive(Clone, Copy, PartialEq)]
enum TilerTab { Strips, PhoneticTree }

/// Linearised position in the phonetic tree.
/// Allows Up/Down navigation across roots and entries without collapse.
fn tree_line_count(roots: &[PhonemeRoot; MAX_ROOTS], rn: usize) -> usize {
    roots[..rn].iter().map(|r| 1 + r.count).sum()
}

/// Resolve linear index into (root_idx, entry_idx_within_root_or_None_for_root_header).
fn tree_resolve(roots: &[PhonemeRoot; MAX_ROOTS], rn: usize, line: usize)
    -> (usize, Option<usize>)
{
    let mut pos = 0usize;
    for ri in 0..rn {
        if pos == line { return (ri, None); }
        pos += 1;
        if line < pos + roots[ri].count { return (ri, Some(line - pos)); }
        pos += roots[ri].count;
    }
    (rn.saturating_sub(1), None)
}

// ── Request mechanism ─────────────────────────────────────────────────────────

static mut REQUESTED: bool = false;
pub fn request() { unsafe { REQUESTED = true; } }
pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

// ── Group descriptor (derived from BYTE_TABLE at render time) ─────────────────

#[derive(Copy, Clone)]
struct Group {
    first_addr: u32,
    last_addr:  u32,
    tongue:     Option<Tongue>,
    kind:       EntryKind,
}

fn build_groups() -> ([Group; MAX_GRP], usize) {
    let mut gs = [Group { first_addr: 0, last_addr: 0,
                          tongue: None, kind: EntryKind::Symbol }; MAX_GRP];
    let mut n   = 0usize;
    let mut cur = None::<Group>;

    for e in BYTE_TABLE {
        let same = cur.as_ref().map_or(false, |c| {
            c.tongue == e.tongue &&
            core::mem::discriminant(&c.kind) == core::mem::discriminant(&e.kind)
        });
        if same {
            if let Some(ref mut c) = cur { c.last_addr = e.address.0; }
        } else {
            if let Some(c) = cur { if n < MAX_GRP { gs[n] = c; n += 1; } }
            cur = Some(Group {
                first_addr: e.address.0, last_addr: e.address.0,
                tongue: e.tongue, kind: e.kind,
            });
        }
    }
    if let Some(c) = cur { if n < MAX_GRP { gs[n] = c; n += 1; } }
    (gs, n)
}

// ── Tiler ─────────────────────────────────────────────────────────────────────

pub struct Tiler {
    cursor:    u32,
    top_group: usize,
    rule_y:    u32,
    exited:    bool,
    tab:       TilerTab,
    tree_line: usize,   // cursor row in phonetic tree
    tree_top:  usize,   // scroll offset in phonetic tree
}

impl Tiler {
    pub fn new(rule_y: u32) -> Self {
        Tiler { cursor: 0, top_group: 0, rule_y, exited: false,
                tab: TilerTab::Strips, tree_line: 0, tree_top: 0 }
    }

    pub fn reset(&mut self) {
        self.cursor    = 0;
        self.top_group = 0;
        self.exited    = false;
        self.tab       = TilerTab::Strips;
        self.tree_line = 0;
        self.tree_top  = 0;
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
        // Tab key switches between views
        if key == Key::Char(b'\t') {
            self.tab = match self.tab {
                TilerTab::Strips      => TilerTab::PhoneticTree,
                TilerTab::PhoneticTree => TilerTab::Strips,
            };
            return;
        }

        match self.tab {
            TilerTab::Strips      => self.strips_key(key),
            TilerTab::PhoneticTree => self.tree_key(key),
        }
    }

    fn strips_key(&mut self, key: Key) {
        let (gs, gn) = build_groups();
        let gi = group_index(&gs, gn, self.cursor).unwrap_or(0);
        match key {
            Key::Escape => { self.exited = true; }
            Key::Right  => {
                if let Some(a) = next_entry_in(&gs[gi], self.cursor) { self.cursor = a; }
            }
            Key::Left   => {
                if let Some(a) = prev_entry_in(&gs[gi], self.cursor) { self.cursor = a; }
            }
            Key::Down   => {
                if gi + 1 < gn {
                    let col = entry_col_in(&gs[gi], self.cursor);
                    self.cursor = entry_at_col(&gs[gi + 1], col);
                    self.scroll_to(gi + 1);
                }
            }
            Key::Up     => {
                if gi > 0 {
                    let col = entry_col_in(&gs[gi], self.cursor);
                    self.cursor = entry_at_col(&gs[gi - 1], col);
                    self.scroll_to(gi - 1);
                }
            }
            _ => {}
        }
    }

    fn tree_key(&mut self, key: Key) {
        let (roots, rn) = build_phoneme_roots();
        let total = tree_line_count(&roots, rn);
        match key {
            Key::Escape => { self.exited = true; }
            Key::Down   => {
                if self.tree_line + 1 < total { self.tree_line += 1; }
                if self.tree_line >= self.tree_top + 20 {
                    self.tree_top = self.tree_line.saturating_sub(19);
                }
            }
            Key::Up     => {
                if self.tree_line > 0 { self.tree_line -= 1; }
                if self.tree_line < self.tree_top { self.tree_top = self.tree_line; }
            }
            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        // Tab bar
        let tab1_col = if self.tab == TilerTab::Strips      { (0xc8u8, 0x96u8, 0x4bu8) } else { (0x40u8, 0x40u8, 0x50u8) };
        let tab2_col = if self.tab == TilerTab::PhoneticTree { (0xc8u8, 0x96u8, 0x4bu8) } else { (0x40u8, 0x40u8, 0x50u8) };
        font::draw_str(gpu, 20, floor + 2, "Samos", SCALE, tab1_col.0, tab1_col.1, tab1_col.2);
        font::draw_str(gpu, 20 + CHAR_W * 8, floor + 2, "Phonetic Tree", SCALE, tab2_col.0, tab2_col.1, tab2_col.2);
        font::draw_str(gpu, w.saturating_sub(20 + CHAR_W * 14), floor + 2,
                       "Tab:switch  Esc:exit", SCALE, 0x38, 0x38, 0x48);

        // Underline for active tab
        let ul_x = if self.tab == TilerTab::Strips { 20 } else { 20 + CHAR_W * 8 };
        let ul_w = if self.tab == TilerTab::Strips { CHAR_W * 5 } else { CHAR_W * 13 };
        gpu.fill_rect(ul_x, floor + 2 + CHAR_H + 1, ul_w, 1, 0x4b, 0x96, 0xc8);

        match self.tab {
            TilerTab::Strips      => self.render_strips(gpu, floor, w, h),
            TilerTab::PhoneticTree => self.render_phonetic_tree(gpu, floor, w, h),
        }
    }

    fn render_strips(&self, gpu: &dyn GpuSurface, floor: u32, w: u32, h: u32) {

        let gx = 20u32;
        let mut gy = floor + 2 + CHAR_H + 6;
        let (gs, gn) = build_groups();
        let cur_gi   = group_index(&gs, gn, self.cursor).unwrap_or(0);

        let row_h    = CHAR_H + TILE + GAP + 6;
        let max_rows = (h.saturating_sub(gy + CHAR_H + 4)) / row_h;
        let vis_end  = (self.top_group + max_rows as usize).min(gn);

        for gi in self.top_group..vis_end {
            let g = &gs[gi];

            // Group label with address range — dimmed ring colour of group midpoint
            let mid_addr = (g.first_addr + g.last_addr) / 2;
            let mid_col  = palette::aki_color(mid_addr);
            let dim_col  = palette::dim(mid_col);
            {
                let lbl = group_label(g);
                let ll  = lbl.len().min(22);
                let mut lb = [b' '; 56]; let mut ln = ll;
                lb[..ll].copy_from_slice(&lbl[..ll]);
                lb[ln] = b' '; lb[ln+1] = b' '; ln += 2;
                lb[ln] = b'['; ln += 1;
                ln += write_u32(&mut lb[ln..], g.first_addr);
                lb[ln] = b'-'; ln += 1;
                ln += write_u32(&mut lb[ln..], g.last_addr);
                lb[ln] = b']'; ln += 1;
                if let Ok(s) = core::str::from_utf8(&lb[..ln]) {
                    font::draw_str(gpu, gx, gy, s, SCALE, dim_col.0, dim_col.1, dim_col.2);
                }
            }
            gy += CHAR_H + 2;

            // Tile strip — each tile coloured via palette::entry_color
            let mut tx = gx;
            for addr in g.first_addr..=g.last_addr {
                if tx + TILE > w { break; }
                let col = match byte_table::lookup(addr) {
                    None    => palette::VOID_COL,
                    Some(e) => palette::entry_color(e),
                };
                gpu.fill_rect(tx, gy, TILE, TILE, col.0, col.1, col.2);

                if addr == self.cursor {
                    let (x0,y0) = (tx as i32, gy as i32);
                    let (x1,y1) = ((tx+TILE-1) as i32, (gy+TILE-1) as i32);
                    gpu.draw_line(x0,y0, x1,y0, 0xff,0xff,0xff);
                    gpu.draw_line(x0,y1, x1,y1, 0xff,0xff,0xff);
                    gpu.draw_line(x0,y0, x0,y1, 0xff,0xff,0xff);
                    gpu.draw_line(x1,y0, x1,y1, 0xff,0xff,0xff);
                }
                tx += STEP;
            }

            // Active-group side bar in the group's ring colour
            if gi == cur_gi {
                let bx = gx.saturating_sub(6);
                let by = gy - (CHAR_H + 2);
                gpu.fill_rect(bx, by, 3, CHAR_H + TILE + 4, mid_col.0, mid_col.1, mid_col.2);
            }

            gy += TILE + GAP + 6;
        }

        // Scroll indicators
        let dt = (0x40u8, 0x40u8, 0x50u8);
        if self.top_group > 0 {
            if let Ok(s) = core::str::from_utf8(b"^ more") {
                font::draw_str(gpu, gx, floor + 2, s, SCALE, dt.0, dt.1, dt.2);
            }
        }
        if vis_end < gn {
            if let Ok(s) = core::str::from_utf8(b"v more") {
                font::draw_str(gpu, gx, h.saturating_sub(CHAR_H + 2), s, SCALE, dt.0, dt.1, dt.2);
            }
        }

        // Info panel
        let ix = (w * 2 / 3).max(500).min(w.saturating_sub(40));
        self.draw_info(gpu, &gs, gn, ix, floor + 2 + CHAR_H + 6);
    }

    fn draw_info(&self, gpu: &dyn GpuSurface, gs: &[Group; MAX_GRP], gn: usize,
                 x: u32, y: u32) {
        let addr  = self.cursor;
        let entry = byte_table::lookup(addr);

        // Address
        {
            let mut buf = [0u8; 20]; let mut n = 0;
            n += write_u32(&mut buf[n..], addr);
            let h = b"  0x"; buf[n..n+h.len()].copy_from_slice(h); n += h.len();
            buf[n] = hex_hi((addr>>8) as u8); n+=1;
            buf[n] = hex_lo((addr>>8) as u8); n+=1;
            buf[n] = hex_hi(addr as u8);      n+=1;
            buf[n] = hex_lo(addr as u8);      n+=1;
            if let Ok(s) = core::str::from_utf8(&buf[..n]) {
                font::draw_str(gpu, x, y, s, SCALE, 0x58, 0x58, 0x68);
            }
        }

        let mut cy = y + CHAR_H + 6;

        match entry {
            None => {
                if let Ok(s) = core::str::from_utf8(b"[void]") {
                    font::draw_str(gpu, x, cy, s, SCALE, 0x28, 0x28, 0x32);
                }
                cy += CHAR_H + 4;
                if let Ok(s) = core::str::from_utf8(b"factorisation gap") {
                    font::draw_str(gpu, x, cy, s, SCALE, 0x20, 0x20, 0x28);
                }
            }
            Some(e) => {
                let col = palette::entry_color(e);
                if let Some(glyph) = e.glyph {
                    font::draw_str(gpu, x, cy, glyph, SCALE, col.0, col.1, col.2);
                    cy += CHAR_H + 4;
                }
                for chunk in e.meaning.as_bytes().chunks(34).take(3) {
                    if let Ok(s) = core::str::from_utf8(chunk) {
                        font::draw_str(gpu, x, cy, s, SCALE, 0x88, 0xb0, 0x88);
                        cy += CHAR_H + 2;
                    }
                }
                cy += 4;
                let gi = group_index(gs, gn, addr).unwrap_or(0);
                if gn > 0 {
                    let lbl = group_label(&gs[gi]);
                    let gc  = palette::dim(palette::aki_color((gs[gi].first_addr + gs[gi].last_addr) / 2));
                    if let Ok(s) = core::str::from_utf8(lbl) {
                        font::draw_str(gpu, x, cy, s, SCALE, gc.0, gc.1, gc.2);
                    }
                }
            }
        }
    }

    fn scroll_to(&mut self, gi: usize) {
        if gi < self.top_group { self.top_group = gi; }
        if gi >= self.top_group + 14 { self.top_group = gi.saturating_sub(13); }
    }

    // ── Phonetic tree renderer ────────────────────────────────────────────────

    fn render_phonetic_tree(&self, gpu: &dyn GpuSurface, floor: u32, w: u32, h: u32) {
        let (roots, rn) = build_phoneme_roots();
        let total = tree_line_count(&roots, rn);

        let content_y = floor + 2 + CHAR_H + 8; // below tab bar
        let line_h    = CHAR_H + 3;
        let vis_lines = (h.saturating_sub(content_y + CHAR_H)) / line_h;

        // Right panel breakpoint
        let panel_x = (w * 3 / 5).max(300).min(w.saturating_sub(20));

        let mut line_idx = 0usize;
        let mut screen_row = 0u32;

        'outer: for ri in 0..rn {
            let root = &roots[ri];

            // Root header line
            if line_idx >= self.tree_top {
                if screen_row >= vis_lines as u32 { break; }
                let gy = content_y + screen_row * line_h;
                let is_cursor = line_idx == self.tree_line;

                // Background highlight for selected root
                if is_cursor {
                    gpu.fill_rect(0, gy, panel_x, line_h, 0x18, 0x18, 0x28);
                }

                // Root color = midpoint of first entry's palette color
                let root_col = if root.count > 0 {
                    palette::aki_color(root.addrs[0])
                } else {
                    (0x60, 0x60, 0x70)
                };

                // Key: "Yef-  (3 entries)" in root color
                let mut buf = [b' '; 32];
                let kn = root.key_n.min(4);
                buf[..kn].copy_from_slice(&root.key[..kn]);
                buf[kn]   = b'-';
                buf[kn+1] = b' '; buf[kn+2] = b'(';
                let cn = write_u32(&mut buf[kn+3..], root.count as u32);
                buf[kn+3+cn] = b')';
                let total_n = kn + 4 + cn;
                if let Ok(s) = core::str::from_utf8(&buf[..total_n]) {
                    font::draw_str(gpu, 20, gy + 1, s, SCALE,
                                   root_col.0, root_col.1, root_col.2);
                }

                // Right panel: entry addresses preview (up to 8)
                if is_cursor && root.count > 0 {
                    let mut px = panel_x + 8;
                    let preview = root.count.min(8);
                    for k in 0..preview {
                        let a = root.addrs[k];
                        if let Some(e) = byte_table::lookup(a) {
                            if let Some(glyph) = e.glyph {
                                let col = palette::entry_color(e);
                                if px + glyph.len() as u32 * CHAR_W < w {
                                    font::draw_str(gpu, px, gy + 1, glyph, SCALE,
                                                   col.0, col.1, col.2);
                                    px += (glyph.len() as u32 + 1) * CHAR_W;
                                }
                            }
                        }
                    }
                    if root.count > 8 {
                        let mut nb = [0u8; 8]; nb[0] = b'+';
                        let nl = 1 + write_u32(&mut nb[1..], (root.count - 8) as u32);
                        if let Ok(s) = core::str::from_utf8(&nb[..nl]) {
                            font::draw_str(gpu, px, gy + 1, s, SCALE, 0x40, 0x40, 0x58);
                        }
                    }
                }

                screen_row += 1;
            }
            line_idx += 1;

            // Entry lines — grouped by tongue with sub-headers on change
            let mut prev_tongue_num = u32::MAX;
            for ei in 0..root.count {
                let addr = root.addrs[ei];
                let cur_tongue_num = tongue_num_of_addr(addr);

                // Insert tongue sub-header on tongue change
                if cur_tongue_num != prev_tongue_num {
                    prev_tongue_num = cur_tongue_num;
                    if line_idx >= self.tree_top {
                        if screen_row >= vis_lines as u32 { break 'outer; }
                        let gy = content_y + screen_row * line_h;
                        // Tongue header: "  T12 Excavata" dimmed
                        let lbl = if let Some(e) = byte_table::lookup(addr) {
                            e.tongue.map(tongue_short).unwrap_or(b"---")
                        } else { b"---" };
                        let header_col = (0x38u8, 0x40u8, 0x60u8);
                        font::draw_str(gpu, 20 + CHAR_W * 2, gy + 1,
                                       "T", SCALE, header_col.0, header_col.1, header_col.2);
                        if let Ok(s) = core::str::from_utf8(lbl) {
                            font::draw_str(gpu, 20 + CHAR_W * 4, gy + 1, s,
                                           SCALE, header_col.0, header_col.1, header_col.2);
                        }
                        screen_row += 1;
                    }
                    // tongue sub-header is NOT a cursor-navigable line
                    // (doesn't increment line_idx)
                }

                if line_idx >= self.tree_top {
                    if screen_row >= vis_lines as u32 { break 'outer; }
                    let gy = content_y + screen_row * line_h;
                    let is_cursor = line_idx == self.tree_line;

                    if is_cursor {
                        gpu.fill_rect(0, gy, w, line_h, 0x10, 0x10, 0x1c);
                    }

                    if let Some(e) = byte_table::lookup(addr) {
                        let col = palette::entry_color(e);
                        let dim = palette::dim(col);
                        let glyph = e.glyph.unwrap_or("?");
                        let gx = 20 + CHAR_W * 5; // further indent under tongue header

                        font::draw_str(gpu, gx, gy + 1, glyph, SCALE, col.0, col.1, col.2);

                        let glyph_w = (glyph.len() as u32 + 2) * CHAR_W;
                        let mut ab = [b' '; 12]; let mut an = 0;
                        ab[an] = b'['; an += 1;
                        an += write_u32(&mut ab[an..], addr);
                        ab[an] = b']'; an += 1;
                        if let Ok(s) = core::str::from_utf8(&ab[..an]) {
                            font::draw_str(gpu, gx + glyph_w, gy + 1, s, SCALE,
                                           0x40, 0x40, 0x58);
                        }

                        // Meaning (truncated)
                        let meaning_x = gx + glyph_w + CHAR_W * 8;
                        let max_ch = ((w.saturating_sub(meaning_x)) / CHAR_W) as usize;
                        if max_ch > 2 {
                            let meaning = &e.meaning[..e.meaning.len().min(max_ch - 1)];
                            if let Ok(s) = core::str::from_utf8(meaning.as_bytes()) {
                                font::draw_str(gpu, meaning_x, gy + 1, s, SCALE,
                                               0x70, 0x90, 0x78);
                            }
                        }
                    }
                    screen_row += 1;
                }
                line_idx += 1;
            }
        }

        // Scroll indicators
        if self.tree_top > 0 {
            font::draw_str(gpu, 20, content_y, "^ more", SCALE, 0x38, 0x38, 0x50);
        }
        if line_idx > self.tree_top + vis_lines as usize {
            font::draw_str(gpu, 20, h.saturating_sub(CHAR_H + 2), "v more",
                           SCALE, 0x38, 0x38, 0x50);
        }

        // Stats line at bottom
        let mut sb = [0u8; 32];
        let lbl = b"roots: ";
        sb[..lbl.len()].copy_from_slice(lbl);
        let n = lbl.len() + write_u32(&mut sb[lbl.len()..], rn as u32);
        let lbl2 = b"  entries: ";
        sb[n..n+lbl2.len()].copy_from_slice(lbl2);
        let n2 = n + lbl2.len() + write_u32(&mut sb[n+lbl2.len()..], total as u32);
        if let Ok(s) = core::str::from_utf8(&sb[..n2]) {
            font::draw_str(gpu, w.saturating_sub(n2 as u32 * CHAR_W + 20),
                           h.saturating_sub(CHAR_H + 2), s, SCALE, 0x38, 0x38, 0x50);
        }
    }
}

// ── Group label ───────────────────────────────────────────────────────────────

fn group_label(g: &Group) -> &'static [u8] {
    match g.tongue {
        Some(t) => tongue_label(t),
        None    => match g.kind {
            EntryKind::Reserved     => b"Reserved",
            EntryKind::MetaTopology => b"MetaTopology",
            EntryKind::MetaPhysics  => b"MetaPhysics",
            EntryKind::Physics      => b"Physics",
            EntryKind::Chemistry    => b"Chemistry",
            EntryKind::Symbol       => b"Symbol",
        },
    }
}

fn tongue_label(t: Tongue) -> &'static [u8] {
    match t {
        Tongue::Lotus          => b"T01 Lotus",
        Tongue::Rose           => b"T02 Rose",
        Tongue::Sakura         => b"T03 Sakura",
        Tongue::Daisy          => b"T04 Daisy",
        Tongue::AppleBlossom   => b"T05 AppleBlossom",
        Tongue::Aster          => b"T06 Aster",
        Tongue::Grapevine      => b"T07 Grapevine",
        Tongue::Cannabis       => b"T08 Cannabis",
        Tongue::Dragon         => b"T09 Dragon",
        Tongue::Virus          => b"T10 Virus",
        Tongue::Bacteria       => b"T11 Bacteria",
        Tongue::Excavata       => b"T12 Excavata",
        Tongue::Archaeplastida => b"T13 Archaeplastida",
        Tongue::Myxozoa        => b"T14 Myxozoa",
        Tongue::Archea         => b"T15 Archea",
        Tongue::Protist        => b"T16 Protist",
        Tongue::Immune         => b"T17 Immune",
        Tongue::Neural         => b"T18 Neural",
        Tongue::Serpent        => b"T19 Serpent",
        Tongue::Beast          => b"T20 Beast",
        Tongue::Cherub         => b"T21 Cherub",
        Tongue::Chimera        => b"T22 Chimera",
        Tongue::Faerie         => b"T23 Faerie",
        Tongue::Djinn          => b"T24 Djinn",
        Tongue::Fold           => b"T25 Fold",
        Tongue::Topology       => b"T26 Topology",
        Tongue::Phase          => b"T27 Phase",
        Tongue::Gradient       => b"T28 Gradient",
        Tongue::Curvature      => b"T29 Curvature",
        Tongue::Prion          => b"T30 Prion",
        Tongue::Blood          => b"T31 Blood",
        Tongue::Moon           => b"T32 Moon",
        Tongue::Koi            => b"T33 Koi",
        Tongue::Rope           => b"T34 Rope",
        Tongue::Hook           => b"T35 Hook",
        Tongue::Fang           => b"T36 Fang",
        Tongue::Circle         => b"T37 Circle",
        Tongue::Ledger         => b"T38 Ledger",
    }
}

// ── Group navigation ──────────────────────────────────────────────────────────

fn group_index(gs: &[Group; MAX_GRP], gn: usize, addr: u32) -> Option<usize> {
    gs[..gn].iter().position(|g| addr >= g.first_addr && addr <= g.last_addr)
}

fn entry_col_in(g: &Group, addr: u32) -> u32 {
    BYTE_TABLE.iter()
        .filter(|e| e.address.0 >= g.first_addr && e.address.0 <= g.last_addr)
        .position(|e| e.address.0 == addr)
        .unwrap_or(0) as u32
}

fn entry_at_col(g: &Group, col: u32) -> u32 {
    BYTE_TABLE.iter()
        .filter(|e| e.address.0 >= g.first_addr && e.address.0 <= g.last_addr)
        .nth(col as usize)
        .map(|e| e.address.0)
        .unwrap_or(g.first_addr)
}

fn next_entry_in(g: &Group, addr: u32) -> Option<u32> {
    BYTE_TABLE.iter()
        .filter(|e| e.address.0 >= g.first_addr && e.address.0 <= g.last_addr
                 && e.address.0 > addr)
        .map(|e| e.address.0).next()
}

fn prev_entry_in(g: &Group, addr: u32) -> Option<u32> {
    BYTE_TABLE.iter()
        .filter(|e| e.address.0 >= g.first_addr && e.address.0 <= g.last_addr
                 && e.address.0 < addr)
        .map(|e| e.address.0).last()
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + (n % 10) as u8; n /= 10; l += 1; }
    for i in 0..l.min(buf.len()) { buf[i] = tmp[l-1-i]; }
    l
}

fn hex_hi(v: u8) -> u8 { let n=v>>4;  if n<10 { b'0'+n } else { b'a'+n-10 } }
fn hex_lo(v: u8) -> u8 { let n=v&0xf; if n<10 { b'0'+n } else { b'a'+n-10 } }

fn tongue_short(t: Tongue) -> &'static [u8] {
    match t {
        Tongue::Lotus          => b"T01",
        Tongue::Rose           => b"T02",
        Tongue::Sakura         => b"T03",
        Tongue::Daisy          => b"T04",
        Tongue::AppleBlossom   => b"T05",
        Tongue::Aster          => b"T06",
        Tongue::Grapevine      => b"T07",
        Tongue::Cannabis       => b"T08",
        Tongue::Dragon         => b"T09",
        Tongue::Virus          => b"T10",
        Tongue::Bacteria       => b"T11",
        Tongue::Excavata       => b"T12",
        Tongue::Archaeplastida => b"T13",
        Tongue::Myxozoa        => b"T14",
        Tongue::Archea         => b"T15",
        Tongue::Protist        => b"T16",
        Tongue::Immune         => b"T17",
        Tongue::Neural         => b"T18",
        Tongue::Serpent        => b"T19",
        Tongue::Beast          => b"T20",
        Tongue::Cherub         => b"T21",
        Tongue::Chimera        => b"T22",
        Tongue::Faerie         => b"T23",
        Tongue::Djinn          => b"T24",
        Tongue::Fold           => b"T25",
        Tongue::Topology       => b"T26",
        Tongue::Phase          => b"T27",
        Tongue::Gradient       => b"T28",
        Tongue::Curvature      => b"T29",
        Tongue::Prion          => b"T30",
        Tongue::Blood          => b"T31",
        Tongue::Moon           => b"T32",
        Tongue::Koi            => b"T33",
        Tongue::Rope           => b"T34",
        Tongue::Hook           => b"T35",
        Tongue::Fang           => b"T36",
        Tongue::Circle         => b"T37",
        Tongue::Ledger         => b"T38",
    }
}
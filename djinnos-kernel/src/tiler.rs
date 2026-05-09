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
}

impl Tiler {
    pub fn new(rule_y: u32) -> Self {
        Tiler { cursor: 0, top_group: 0, rule_y, exited: false }
    }

    pub fn reset(&mut self) {
        self.cursor    = 0;
        self.top_group = 0;
        self.exited    = false;
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
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

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let hdr = b"Shygazun ledger  [Arrows: navigate  Esc: exit]";
        if let Ok(s) = core::str::from_utf8(hdr) {
            font::draw_str(gpu, 20, floor + 2, s, SCALE, 0x4b, 0x96, 0xc8);
        }

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
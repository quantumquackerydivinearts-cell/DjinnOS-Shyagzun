// book.rs -- Book authoring, typesetting, and binding specification.
//
// A real book production tool for Quantum Quackery Divine Arts.
// Not a game mechanic -- produces actual books bound in wood and cloth.
//
// Pipeline:
//   Write (prose editor) -> Typeset (page layout engine) -> Bind (cut list)
//
// Physical output:
//   .bkm  raw manuscript (Sa-persisted, editable)
//   .bkl  typeset page layout (one page per form-feed, printable)
//   .bks  binding specification (exact dimensions for boards, spine, cloth)
//
// Manuscript markup (minimal, in-band):
//   # Title     -- chapter heading: page break before, centred, space after
//   ## Title    -- section heading: space before/after
//   ---         -- scene break: three centred bullets (*  *  *)
//   [pg]        -- forced page break
//   blank line  -- paragraph break (indent continuation)
//
// Objects: Pulp (0069_KLOB), Paper (0070_KLOB), Ink (0071_KLOB),
//          Pen (0072_KLOB), Binding Wax (0075_KLOB) -- from kos_labyrnth.py.

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;

// -- Constants ----------------------------------------------------------------

pub const MANUSCRIPT_MAX: usize = 65536;  // 64 KB raw prose
const MAX_CHAPTERS:  usize = 48;
const TITLE_N:       usize = 80;
const AUTHOR_N:      usize = 64;
const PAGE_COLS_MAX: usize = 80;
const PAGE_LINES_MAX: usize = 50;
const SPEC_OUT_MAX:  usize = 4096;  // binding spec text output

// -- Page size presets --------------------------------------------------------
// All dimensions in tenths of a millimetre (0.1 mm = 1 unit).
// Standard typographic leading: body text at 12pt/14pt
//   1pt = 3.527px at 90dpi; for print estimation: 14pt leading = ~5mm per line

struct PagePreset {
    name:    &'static [u8],
    w:       u16,   // page width  (0.1 mm)
    h:       u16,   // page height (0.1 mm)
    gutter:  u16,   // inside margin (spine side)
    fore:    u16,   // outside margin
    head:    u16,   // top margin
    tail:    u16,   // bottom margin
    // Derived at runtime: cols = text_w / char_w_mm; lines = text_h / leading_mm
    // char_w at 12pt monospace approx 2.1 mm; leading at 14pt approx 4.9 mm
}

const PRESETS: &[PagePreset] = &[
    PagePreset { name: b"A5 (148x210)",    w: 1480, h: 2100, gutter: 200, fore: 180, head: 175, tail: 200 },
    PagePreset { name: b"Trade (152x229)", w: 1520, h: 2290, gutter: 220, fore: 190, head: 190, tail: 215 },
    PagePreset { name: b"Royal (156x234)", w: 1560, h: 2340, gutter: 225, fore: 200, head: 195, tail: 220 },
    PagePreset { name: b"Demy (138x216)",  w: 1380, h: 2160, gutter: 190, fore: 170, head: 175, tail: 195 },
    PagePreset { name: b"Digest (140x216)",w: 1400, h: 2160, gutter: 190, fore: 170, head: 175, tail: 195 },
    PagePreset { name: b"A6 pocket",       w: 1050, h: 1480, gutter: 140, fore: 125, head: 130, tail: 145 },
];

const CHAR_W_DMMT: u16 = 21;   // character width in 0.1mm (approx 12pt monospace = ~2.1mm)
const LEADING_DMMT: u16 = 49;  // line leading in 0.1mm (14pt = ~4.9mm)

// -- Binding type -------------------------------------------------------------

#[derive(Copy, Clone, PartialEq)]
pub enum BindingType {
    CaseBound,    // wood boards + cloth case (sewn signatures)
    CopticStitch, // exposed spine, sewn through boards
    LongStitch,   // visible long-stitch through spine
    PerfectBound, // glued square spine (no sewing)
}

impl BindingType {
    pub fn name(&self) -> &'static str {
        match self {
            Self::CaseBound    => "Case Bound (wood boards, cloth case)",
            Self::CopticStitch => "Coptic Stitch (exposed spine)",
            Self::LongStitch   => "Long Stitch (visible spine sewing)",
            Self::PerfectBound => "Perfect Bound (glued spine)",
        }
    }
}

// -- Wood and cloth presets ---------------------------------------------------

#[derive(Copy, Clone)]
pub struct WoodSpec { pub name: &'static str, pub thickness_dmm: u8 }  // board thickness

const WOOD_PRESETS: &[WoodSpec] = &[
    WoodSpec { name: "3mm plywood",     thickness_dmm: 30 },
    WoodSpec { name: "4mm birch ply",   thickness_dmm: 40 },
    WoodSpec { name: "3mm MDF",         thickness_dmm: 30 },
    WoodSpec { name: "5mm oak board",   thickness_dmm: 50 },
    WoodSpec { name: "2mm pasteboard",  thickness_dmm: 20 },
];

const CLOTH_PRESETS: &[&str] = &[
    "Natural linen",
    "Buckram (starch-filled cotton)",
    "Book cloth (acrylic-coated cotton)",
    "Leather-grain book cloth",
    "Japanese silk",
    "Hemp canvas",
];

// -- Typesetting configuration ------------------------------------------------

#[derive(Copy, Clone)]
pub struct TypesetConfig {
    pub cols:       u8,   // characters per line
    pub body_lines: u8,   // body text lines per page (excl. header/footer)
    pub indent:     u8,   // paragraph indent (spaces)
    pub show_header: bool,
    pub show_folio:  bool,
}

impl TypesetConfig {
    pub fn from_preset(idx: usize) -> Self {
        let p = &PRESETS[idx.min(PRESETS.len() - 1)];
        let text_w = p.w.saturating_sub(p.gutter + p.fore);
        let text_h = p.h.saturating_sub(p.head + p.tail);
        let cols = (text_w / CHAR_W_DMMT).min(80) as u8;
        let lines = (text_h / LEADING_DMMT).saturating_sub(3) as u8; // -3 for header+footer+gap
        TypesetConfig { cols, body_lines: lines, indent: 3, show_header: true, show_folio: true }
    }
}

// -- Typeset page (in-memory rendered page) -----------------------------------

const LINE_W: usize = PAGE_COLS_MAX;

pub struct TypesetPage {
    pub lines:   [[u8; LINE_W]; PAGE_LINES_MAX],
    pub line_n:  [u8; PAGE_LINES_MAX],  // used bytes in each line
    pub n:       usize,                 // filled line count
    pub page_num: u32,
}

impl TypesetPage {
    const fn empty() -> Self {
        Self {
            lines:    [[b' '; LINE_W]; PAGE_LINES_MAX],
            line_n:   [0u8; PAGE_LINES_MAX],
            n:        0,
            page_num: 0,
        }
    }

    fn push_line(&mut self, src: &[u8]) -> bool {
        if self.n >= PAGE_LINES_MAX { return false; }
        let n = src.len().min(LINE_W);
        self.lines[self.n][..n].copy_from_slice(&src[..n]);
        self.line_n[self.n] = n as u8;
        self.n += 1;
        true
    }

    fn push_blank(&mut self) -> bool { self.push_line(b"") }

    fn is_full(&self, cfg: &TypesetConfig) -> bool {
        self.n >= cfg.body_lines as usize + 2  // +2 for header row and folio row
    }
}

// -- Typesetting engine -------------------------------------------------------
//
// Streams through the raw manuscript byte-by-byte, building pages.
// Call next_page() repeatedly to get typeset pages.

pub struct Typesetter<'a> {
    text: &'a [u8],
    pos:  usize,
    cfg:  TypesetConfig,
    page_num: u32,
    // Current line buffer being built.
    line_buf: [u8; LINE_W],
    line_pos: usize,
    at_para_start: bool,  // next word starts a new paragraph
    pending_blank: bool,  // a blank line is owed after current line
    // Chapter title seen on this page (for running header).
    chapter_buf: [u8; 64],
    chapter_n:   usize,
}

impl<'a> Typesetter<'a> {
    pub fn new(text: &'a [u8], cfg: TypesetConfig) -> Self {
        let mut t = Self {
            text, pos: 0, cfg, page_num: 1,
            line_buf: [b' '; LINE_W], line_pos: 0,
            at_para_start: true, pending_blank: false,
            chapter_buf: [0u8; 64], chapter_n: 0,
        };
        t
    }

    pub fn done(&self) -> bool { self.pos >= self.text.len() }

    /// Render the next page into `out`. Returns false if no more text.
    pub fn next_page(&mut self, out: &mut TypesetPage) -> bool {
        if self.done() { return false; }
        *out = TypesetPage::empty();
        out.page_num = self.page_num;
        self.page_num += 1;
        let cols = self.cfg.cols as usize;
        let max_body = self.cfg.body_lines as usize;

        // Running header (chapter title + page number).
        if self.cfg.show_header && self.chapter_n > 0 {
            let mut hdr = [b' '; LINE_W];
            let cn = self.chapter_n.min(cols.saturating_sub(8));
            hdr[..cn].copy_from_slice(&self.chapter_buf[..cn]);
            out.push_line(&hdr[..cols]);
            out.push_blank();
        } else if self.cfg.show_header {
            out.push_blank();
            out.push_blank();
        }

        let header_lines = out.n;

        // Fill body lines.
        loop {
            if out.n - header_lines >= max_body { break; }
            if self.done() { break; }

            // Peek at the line start for markup.
            let line_start = self.pos;
            if self.text[self.pos] == b'#' {
                // Chapter or section heading.
                let level = if self.pos + 1 < self.text.len() && self.text[self.pos + 1] == b'#' {
                    self.pos += 1; 2
                } else { 1 };
                while self.pos < self.text.len() && self.text[self.pos] == b'#' { self.pos += 1; }
                while self.pos < self.text.len() && self.text[self.pos] == b' ' { self.pos += 1; }
                let ts = self.pos;
                while self.pos < self.text.len() && self.text[self.pos] != b'\n' { self.pos += 1; }
                let title = &self.text[ts..self.pos];
                if self.pos < self.text.len() { self.pos += 1; }

                if level == 1 {
                    // Chapter heading: add to header, break page if not at top.
                    let body_so_far = out.n - header_lines;
                    if body_so_far > 1 {
                        // Already have content -- flush this page, restart for chapter.
                        // Don't advance pos past this markup -- rewind.
                        self.pos = line_start;
                        self.page_num -= 1; // will be re-incremented on next call
                        break;
                    }
                    // At page top: emit chapter heading.
                    let tn = title.len().min(64);
                    self.chapter_buf[..tn].copy_from_slice(&title[..tn]);
                    self.chapter_n = tn;
                    out.push_blank();
                    let centered = centre_text(title, cols);
                    out.push_line(&centered);
                    out.push_line(&underline(title.len().min(cols)));
                    out.push_blank();
                } else {
                    // Section heading.
                    out.push_blank();
                    let mut sh = [b' '; LINE_W];
                    let n = title.len().min(cols);
                    sh[..n].copy_from_slice(&title[..n]);
                    out.push_line(&sh[..cols]);
                    out.push_blank();
                }
                self.at_para_start = true;
                continue;
            }

            // Scene break marker.
            if self.text[self.pos..].starts_with(b"---") {
                while self.pos < self.text.len() && self.text[self.pos] != b'\n' { self.pos += 1; }
                if self.pos < self.text.len() { self.pos += 1; }
                let sc = scene_break(cols);
                out.push_blank();
                out.push_line(&sc);
                out.push_blank();
                continue;
            }

            // Forced page break.
            if self.text[self.pos..].starts_with(b"[pg]") {
                self.pos += 4;
                while self.pos < self.text.len() && self.text[self.pos] == b'\n' { self.pos += 1; }
                break;
            }

            // Empty line = paragraph break.
            if self.text[self.pos] == b'\n' {
                self.pos += 1;
                // Double newline = paragraph break.
                if self.pos < self.text.len() && self.text[self.pos] == b'\n' {
                    self.pos += 1;
                    // Flush current line buffer.
                    self.flush_line(out, cols);
                    out.push_blank();
                    self.at_para_start = true;
                }
                continue;
            }

            // Read a word.
            let word_start = self.pos;
            while self.pos < self.text.len()
                && self.text[self.pos] != b' '
                && self.text[self.pos] != b'\n' {
                self.pos += 1;
            }
            let word = &self.text[word_start..self.pos];
            // Skip trailing space.
            if self.pos < self.text.len() && self.text[self.pos] == b' ' { self.pos += 1; }

            // If at paragraph start, add indent.
            if self.at_para_start && self.line_pos == 0 {
                for _ in 0..self.cfg.indent as usize { self.append_char(b' '); }
                self.at_para_start = false;
            }

            // Will the word fit on the current line?
            let word_len = word.len();
            let space_needed = if self.line_pos > 0 { word_len + 1 } else { word_len };
            if self.line_pos + space_needed > cols {
                // Flush current line.
                self.flush_line(out, cols);
                if out.n - header_lines >= max_body { break; }
            }
            if self.line_pos > 0 { self.append_char(b' '); }
            for &b in word { self.append_char(b); }
        }

        // Flush any remaining partial line.
        self.flush_line(out, cols);

        // Page folio (page number, bottom).
        if self.cfg.show_folio {
            let body_used = out.n - header_lines;
            while out.n - header_lines < max_body { out.push_blank(); }
            out.push_blank();
            let folio = page_num_line(out.page_num, cols);
            out.push_line(&folio);
        }

        true
    }

    fn append_char(&mut self, c: u8) {
        if self.line_pos < LINE_W { self.line_buf[self.line_pos] = c; self.line_pos += 1; }
    }

    fn flush_line(&mut self, out: &mut TypesetPage, cols: usize) {
        if self.line_pos > 0 {
            out.push_line(&self.line_buf[..self.line_pos.min(cols)]);
            self.line_buf.fill(b' ');
            self.line_pos = 0;
        }
    }
}

// -- Binding specification calculator ----------------------------------------
// All dimensions in 0.1 mm.

pub struct BindingSpec {
    // Board dimensions
    pub board_w:     u16,
    pub board_h:     u16,
    pub board_thick: u8,   // board thickness (0.1 mm)
    // Spine
    pub spine_w:     u16,
    // Case cloth panel
    pub cloth_w:     u16,
    pub cloth_h:     u16,
    // Signatures
    pub n_sigs:      u8,
    pub sheets_per_sig: u8,
    pub last_sig_sheets: u8,
    pub total_sheets:    u16,
    // Turn-in allowance (cloth wrapped onto inside of boards)
    pub turn_in:     u8,   // 0.1 mm
}

const PAPER_THICK_DMMT: u16 = 1;  // 80gsm uncoated = ~0.1mm per sheet
const SWELL_DMMT:       u16 = 3;  // sewing swell: ~0.3mm

pub fn compute_binding(
    preset_idx: usize,
    wood_idx:   usize,
    n_pages:    u32,
    binding:    BindingType,
) -> BindingSpec
{
    let p = &PRESETS[preset_idx.min(PRESETS.len() - 1)];
    let w_thick = WOOD_PRESETS[wood_idx.min(WOOD_PRESETS.len() - 1)].thickness_dmm;
    let total_sheets = ((n_pages + 1) / 2) as u16;  // 2 pages per sheet

    // Standard signature size: 4 or 8 sheets per signature.
    let sig_size = if total_sheets <= 24 { 4u8 } else { 8u8 };
    let n_sigs_full = total_sheets / sig_size as u16;
    let remainder   = (total_sheets % sig_size as u16) as u8;
    let n_sigs = if remainder > 0 { n_sigs_full as u8 + 1 } else { n_sigs_full as u8 };
    let last_sig = if remainder > 0 { remainder } else { sig_size };

    // Paper stack thickness.
    let stack_dmmt = total_sheets * PAPER_THICK_DMMT + SWELL_DMMT;
    let spine_w = stack_dmmt.max(15);  // minimum 1.5mm spine

    // Board size: page + 3mm overhang on fore-edge, top, tail; flush at spine.
    let overhang: u16 = 30;  // 3mm in 0.1mm units
    let board_w = p.w + overhang;
    let board_h = p.h + overhang * 2;

    // Turn-in: 20mm for wood boards (extra to grip the board edge).
    let turn_in: u8 = 200;  // 20mm in 0.1mm

    // Case cloth:
    // width  = turn_in + board_w + gap + spine_w + gap + board_w + turn_in
    // For case binding, 2mm gap between board edge and spine.
    let gap: u16 = 20;
    let cloth_w = turn_in as u16 * 2 + board_w * 2 + spine_w + gap * 2;
    let cloth_h = turn_in as u16 * 2 + board_h;

    BindingSpec {
        board_w, board_h, board_thick: w_thick,
        spine_w, cloth_w, cloth_h,
        n_sigs, sheets_per_sig: sig_size,
        last_sig_sheets: last_sig, total_sheets,
        turn_in,
    }
}

/// Render the binding spec as human-readable text into `out`.
/// Returns the number of bytes written.
pub fn render_binding_spec(
    spec:       &BindingSpec,
    title:      &[u8],
    author:     &[u8],
    n_pages:    u32,
    preset_idx: usize,
    wood_idx:   usize,
    cloth_idx:  usize,
    binding:    BindingType,
    out:        &mut [u8; SPEC_OUT_MAX],
) -> usize
{
    let mut n = 0usize;
    macro_rules! w { ($s:expr) => { for &b in $s { if n < SPEC_OUT_MAX - 1 { out[n] = b; n += 1; } } } }
    macro_rules! wn { () => { w!(b"\n") } }
    macro_rules! wd { ($v:expr) => {{
        let mut tb = [0u8; 8]; let tn = write_dmm(&mut tb, $v as u16);
        w!(&tb[..tn]);
    }} }
    macro_rules! wu { ($v:expr) => {{
        let mut tb = [0u8; 8]; let tn = write_u32(&mut tb, $v as u32); w!(&tb[..tn]);
    }} }

    w!(b"BINDING SPECIFICATION"); wn!();
    w!(b"===================="); wn!(); wn!();
    w!(b"Title:  "); w!(&title[..title.iter().position(|&b|b==0).unwrap_or(title.len())]); wn!();
    w!(b"Author: "); w!(&author[..author.iter().position(|&b|b==0).unwrap_or(author.len())]); wn!();
    w!(b"Pages:  "); wu!(n_pages); wn!();
    w!(b"Binding: "); w!(binding.name().as_bytes()); wn!();
    w!(b"Page size: "); w!(PRESETS[preset_idx].name); wn!(); wn!();

    w!(b"PAPER"); wn!();
    w!(b"-----"); wn!();
    w!(b"Total sheets:    "); wu!(spec.total_sheets); w!(b" sheets ("); wu!(n_pages); w!(b" pages, 2 up)"); wn!();
    w!(b"Grain direction: Long grain (grain parallel to spine)"); wn!();
    w!(b"Weight:          80gsm uncoated text or 90gsm smooth"); wn!();
    wn!();

    w!(b"SIGNATURES"); wn!();
    w!(b"----------"); wn!();
    w!(b"Count:  "); wu!(spec.n_sigs); w!(b" signatures"); wn!();
    if spec.last_sig_sheets == spec.sheets_per_sig {
        w!(b"Layout: "); wu!(spec.n_sigs); w!(b" x "); wu!(spec.sheets_per_sig); w!(b" sheets each"); wn!();
    } else {
        w!(b"Layout: "); wu!(spec.n_sigs.saturating_sub(1)); w!(b" x "); wu!(spec.sheets_per_sig);
        w!(b" sheets + 1 x "); wu!(spec.last_sig_sheets); w!(b" sheets"); wn!();
    }
    w!(b"Pages per sig:  "); wu!(spec.sheets_per_sig as u32 * 4); w!(b" pp"); wn!();
    wn!();

    w!(b"BOARDS ("); w!(WOOD_PRESETS[wood_idx].name.as_bytes()); w!(b")"); wn!();
    w!(b"------"); wn!();
    w!(b"Front board: "); wd!(spec.board_w); w!(b" x "); wd!(spec.board_h); w!(b" mm"); wn!();
    w!(b"Back board:  "); wd!(spec.board_w); w!(b" x "); wd!(spec.board_h); w!(b" mm"); wn!();
    w!(b"Thickness:   "); wu!(spec.board_thick as u32 / 10); w!(b"."); wu!((spec.board_thick as u32 % 10)); w!(b" mm"); wn!();
    w!(b"Overhang:    3 mm on fore-edge, head, and tail; flush at spine"); wn!();
    w!(b"Cut 2 identical boards. Grain direction: parallel to spine."); wn!();
    wn!();

    w!(b"SPINE"); wn!();
    w!(b"-----"); wn!();
    w!(b"Width:   "); wd!(spec.spine_w); w!(b" mm  (stack + sewing swell)"); wn!();
    w!(b"Height:  "); wd!(spec.board_h); w!(b" mm  (same as board height)"); wn!();
    wn!();

    w!(b"CASE CLOTH ("); w!(CLOTH_PRESETS[cloth_idx.min(CLOTH_PRESETS.len()-1)].as_bytes()); w!(b")"); wn!();
    w!(b"----------"); wn!();
    w!(b"Panel width:  "); wd!(spec.cloth_w); w!(b" mm"); wn!();
    w!(b"Panel height: "); wd!(spec.cloth_h); w!(b" mm"); wn!();
    w!(b"Turn-in:      20 mm on all edges"); wn!();
    w!(b"Layout (width, left to right):"); wn!();
    w!(b"  20mm turn-in | "); wd!(spec.board_w); w!(b"mm board | 2mm gap |"); wn!();
    w!(b"  "); wd!(spec.spine_w); w!(b"mm spine | 2mm gap | "); wd!(spec.board_w); w!(b"mm board | 20mm turn-in"); wn!();
    wn!();

    w!(b"SEWING THREAD"); wn!();
    w!(b"-------------"); wn!();
    w!(b"Type:   Waxed linen, 18/3 or 18/2"); wn!();
    w!(b"Pattern: ");
    if spec.n_sigs <= 3 { w!(b"2-hole pamphlet or Japanese stab"); }
    else                { w!(b"Kettle stitch, 3-hole per signature"); }
    wn!();
    w!(b"Needle: Curved bookbinding needle"); wn!();
    wn!();

    w!(b"ADHESIVE"); wn!();
    w!(b"--------"); wn!();
    w!(b"Spine:  PVA bookbinding adhesive (diluted 3:1 with water for first coat)"); wn!();
    w!(b"Boards: PVA full-strength for cloth application"); wn!();
    w!(b"Boards are adhered after case is dry; use bone folder for corners."); wn!();
    wn!();

    if binding == BindingType::CaseBound {
        w!(b"CASE CONSTRUCTION ORDER"); wn!();
        w!(b"-----------------------"); wn!();
        w!(b"1. Sew all signatures with waxed thread."); wn!();
        w!(b"2. Apply PVA to spine; let cure. Trim spine square."); wn!();
        w!(b"3. Cut cloth panel to dimensions above."); wn!();
        w!(b"4. Mark board positions on cloth (pencil, inside face)."); wn!();
        w!(b"5. Apply PVA to cloth; press boards into position."); wn!();
        w!(b"6. Turn-in cloth at corners (library corners or mitered)."); wn!();
        w!(b"7. Let case dry under weight (24h)."); wn!();
        w!(b"8. Attach text block to case via endpapers (PVA)."); wn!();
        w!(b"9. Press 24h between boards under weight."); wn!();
        wn!();
    }

    w!(b"MATERIALS LIST"); wn!();
    w!(b"--------------"); wn!();
    w!(b"  Paper: "); wu!(spec.total_sheets); w!(b" sheets 80gsm, "); wd!(PRESETS[preset_idx].w + 10); w!(b" x "); wd!(PRESETS[preset_idx].h + 10); w!(b" mm uncut"); wn!();
    w!(b"  Wood:  2 pcs "); wd!(spec.board_w); w!(b" x "); wd!(spec.board_h); w!(b" mm x "); wu!(spec.board_thick as u32 / 10); w!(b"mm"); wn!();
    w!(b"  Cloth: 1 pc  "); wd!(spec.cloth_w); w!(b" x "); wd!(spec.cloth_h); w!(b" mm + 10mm overlap allowance"); wn!();
    w!(b"  PVA adhesive, waxed linen thread, bone folder, pressing boards"); wn!();
    wn!();

    out[n] = 0; // null-terminate
    n
}

// -- Book project state -------------------------------------------------------

/// Char(0x09) = Tab key; cycles between tabs.
/// Char(b'1'-b'4') selects tabs directly when in non-Write mode.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum BookTab { Write, Layout, Spec, Bind }

pub struct BookProject {
    pub title:       [u8; TITLE_N],
    pub title_n:     usize,
    pub author:      [u8; AUTHOR_N],
    pub author_n:    usize,
    pub manuscript:  [u8; MANUSCRIPT_MAX],
    pub ms_len:      usize,
    pub preset_idx:  usize,
    pub wood_idx:    usize,
    pub cloth_idx:   usize,
    pub binding:     BindingType,
    // Computed
    pub page_count:  u32,
    // Editor state
    pub tab:         BookTab,
    pub cursor:      usize,   // byte position in manuscript (Write tab)
    pub scroll_line: usize,   // topmost visible line (Write tab)
    pub view_page:   u32,     // page being viewed (Layout tab)
    pub spec_scroll: usize,   // Spec/Bind tab scroll
    // Working page (Layout tab, re-typeset on demand)
    pub cur_page:    TypesetPage,
    // Binding spec output
    pub spec_out:    [u8; SPEC_OUT_MAX],
    pub spec_out_n:  usize,
    pub exited:      bool,
    // Title bar editing
    pub editing_title:  bool,
    pub editing_author: bool,
    rule_y: u32,
}

static mut BOOK: BookProject = BookProject {
    title:       [0u8; TITLE_N],
    title_n:     0,
    author:      [0u8; AUTHOR_N],
    author_n:    0,
    manuscript:  [0u8; MANUSCRIPT_MAX],
    ms_len:      0,
    preset_idx:  0,   // A5 by default
    wood_idx:    0,   // 3mm plywood
    cloth_idx:   0,   // Natural linen
    binding:     BindingType::CaseBound,
    page_count:  0,
    tab:         BookTab::Write,
    cursor:      0,
    scroll_line: 0,
    view_page:   1,
    spec_scroll: 0,
    cur_page:    TypesetPage::empty(),
    spec_out:    [0u8; SPEC_OUT_MAX],
    spec_out_n:  0,
    exited:      false,
    editing_title:  false,
    editing_author: false,
    rule_y: 0,
};

pub fn book() -> &'static mut BookProject { unsafe { &mut BOOK } }

static mut BOOK_REQ: bool = false;
pub fn request()         { unsafe { BOOK_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = BOOK_REQ; BOOK_REQ = false; r } }

impl BookProject {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y = rule_y;
        self.exited = false;
        self.tab    = BookTab::Write;
    }

    pub fn exited(&self) -> bool { self.exited }

    // -- Page count -----------------------------------------------------------

    pub fn recount_pages(&mut self) {
        let cfg = TypesetConfig::from_preset(self.preset_idx);
        let mut ts = Typesetter::new(&self.manuscript[..self.ms_len], cfg);
        let mut pg = TypesetPage::empty();
        let mut count = 0u32;
        while ts.next_page(&mut pg) { count += 1; if count > 2000 { break; } }
        self.page_count = count;
    }

    // -- Typeset a specific page ----------------------------------------------

    pub fn typeset_page(&mut self, target: u32) {
        let cfg = TypesetConfig::from_preset(self.preset_idx);
        let mut ts = Typesetter::new(&self.manuscript[..self.ms_len], cfg);
        let mut pg = TypesetPage::empty();
        for _ in 0..target {
            if !ts.next_page(&mut pg) { break; }
        }
        self.cur_page = pg;
    }

    // -- Rebuild binding spec -------------------------------------------------

    pub fn rebuild_spec(&mut self) {
        self.recount_pages();
        let spec = compute_binding(self.preset_idx, self.wood_idx, self.page_count, self.binding);
        self.spec_out_n = render_binding_spec(
            &spec,
            &self.title, &self.author, self.page_count,
            self.preset_idx, self.wood_idx, self.cloth_idx,
            self.binding, &mut self.spec_out,
        );
    }

    // -- Save / Load ----------------------------------------------------------

    pub fn save(&self, name: &[u8]) {
        const SZ: usize = 4 + 1 + TITLE_N + AUTHOR_N + 4 + 4 + MANUSCRIPT_MAX;
        static mut BUF: [u8; SZ] = [0u8; SZ];
        let buf = unsafe { &mut BUF };
        buf[0] = b'B'; buf[1] = b'K'; buf[2] = b'0'; buf[3] = b'1';
        buf[4] = 1; // version
        buf[5..5 + TITLE_N].copy_from_slice(&self.title);
        buf[5 + TITLE_N..5 + TITLE_N + AUTHOR_N].copy_from_slice(&self.author);
        let off = 5 + TITLE_N + AUTHOR_N;
        buf[off]   = (self.ms_len & 0xff) as u8;
        buf[off+1] = ((self.ms_len >> 8)  & 0xff) as u8;
        buf[off+2] = ((self.ms_len >> 16) & 0xff) as u8;
        buf[off+3] = 0;
        buf[off+4] = self.preset_idx as u8;
        buf[off+5] = self.wood_idx   as u8;
        buf[off+6] = self.cloth_idx  as u8;
        buf[off+7] = match self.binding {
            BindingType::CaseBound    => 0,
            BindingType::CopticStitch => 1,
            BindingType::LongStitch   => 2,
            BindingType::PerfectBound => 3,
        };
        let moff = off + 8;
        buf[moff..moff + self.ms_len].copy_from_slice(&self.manuscript[..self.ms_len]);
        crate::sa::write_file(name, &buf[..moff + self.ms_len]);
    }

    pub fn load(&mut self, name: &[u8]) -> bool {
        const SZ: usize = 4 + 1 + TITLE_N + AUTHOR_N + 8 + MANUSCRIPT_MAX;
        let mut buf = [0u8; 5 + TITLE_N + AUTHOR_N + 8];
        let n = crate::sa::read_file(name, &mut buf);
        if n < 5 + TITLE_N + AUTHOR_N + 8 { return false; }
        if &buf[0..4] != b"BK01" { return false; }
        self.title.copy_from_slice(&buf[5..5 + TITLE_N]);
        self.title_n = self.title.iter().position(|&b| b == 0).unwrap_or(TITLE_N);
        self.author.copy_from_slice(&buf[5 + TITLE_N..5 + TITLE_N + AUTHOR_N]);
        self.author_n = self.author.iter().position(|&b| b == 0).unwrap_or(AUTHOR_N);
        let off = 5 + TITLE_N + AUTHOR_N;
        let ms_len = buf[off] as usize | ((buf[off+1] as usize) << 8) | ((buf[off+2] as usize) << 16);
        self.preset_idx = buf[off+4] as usize;
        self.wood_idx   = buf[off+5] as usize;
        self.cloth_idx  = buf[off+6] as usize;
        self.binding = match buf[off+7] {
            1 => BindingType::CopticStitch,
            2 => BindingType::LongStitch,
            3 => BindingType::PerfectBound,
            _ => BindingType::CaseBound,
        };
        // Load manuscript separately (it can be up to 64KB).
        let ms_read = crate::sa::read_file(name, &mut self.manuscript);
        // Skip header to reach manuscript bytes.
        let moff = off + 8;
        if ms_read > moff {
            let actual = (ms_read - moff).min(ms_len).min(MANUSCRIPT_MAX);
            // Slide manuscript bytes to start (they come after header in full read).
            // Since read_file fills from byte 0, we need to shift.
            for i in 0..actual { self.manuscript[i] = self.manuscript[moff + i]; }
            self.ms_len = actual;
        }
        true
    }

    // -- Export typeset layout to Sa ------------------------------------------

    pub fn export_layout(&mut self, name: &[u8]) {
        let cfg = TypesetConfig::from_preset(self.preset_idx);
        let mut ts  = Typesetter::new(&self.manuscript[..self.ms_len], cfg);
        let mut pg  = TypesetPage::empty();
        static mut PAGE_BUF: [u8; 8192] = [0u8; 8192];
        let buf = unsafe { &mut PAGE_BUF };
        let mut boff = 0usize;

        while ts.next_page(&mut pg) {
            if boff + 4096 > 8192 { break; } // flush when approaching limit
            for li in 0..pg.n {
                let ln = pg.line_n[li] as usize;
                let src = &pg.lines[li][..ln];
                let need = ln + 1;
                if boff + need < 8192 {
                    buf[boff..boff + ln].copy_from_slice(src);
                    buf[boff + ln] = b'\n';
                    boff += need;
                }
            }
            if boff + 1 < 8192 { buf[boff] = 0x0C; boff += 1; } // form-feed = page separator
        }
        crate::sa::write_file(name, &buf[..boff]);
    }

    // -- Key handling ---------------------------------------------------------

    pub fn handle_key(&mut self, key: Key) {
        // Char(0x09) = Tab key: cycle through tabs.
        // Outside Write mode, Char(b'1'-b'4') jump directly to a tab.
        if key == Key::Char(0x09) {
            self.tab = match self.tab {
                BookTab::Write  => { self.typeset_page(self.view_page); BookTab::Layout }
                BookTab::Layout => BookTab::Spec,
                BookTab::Spec   => { self.rebuild_spec(); BookTab::Bind }
                BookTab::Bind   => BookTab::Write,
            };
            return;
        }
        if self.tab != BookTab::Write {
            match key {
                Key::Char(b'1') => { self.tab = BookTab::Write; return; }
                Key::Char(b'2') => { self.typeset_page(self.view_page); self.tab = BookTab::Layout; return; }
                Key::Char(b'3') => { self.tab = BookTab::Spec; return; }
                Key::Char(b'4') => { self.rebuild_spec(); self.tab = BookTab::Bind; return; }
                _ => {}
            }
        }
        match key {
            Key::Escape => { self.exited = true; }
            _ => match self.tab {
                BookTab::Write  => self.key_write(key),
                BookTab::Layout => self.key_layout(key),
                BookTab::Spec   => self.key_spec(key),
                BookTab::Bind   => self.key_bind(key),
            }
        }
    }

    fn key_write(&mut self, key: Key) {
        match key {
            Key::Char(c) if c >= 0x20 && c < 0x7F => {
                if self.ms_len < MANUSCRIPT_MAX - 1 {
                    // Insert at cursor.
                    for i in (self.cursor..self.ms_len).rev() {
                        if i + 1 < MANUSCRIPT_MAX { self.manuscript[i + 1] = self.manuscript[i]; }
                    }
                    self.manuscript[self.cursor] = c;
                    self.ms_len += 1;
                    self.cursor += 1;
                }
            }
            Key::Enter => {
                if self.ms_len < MANUSCRIPT_MAX - 1 {
                    for i in (self.cursor..self.ms_len).rev() {
                        if i + 1 < MANUSCRIPT_MAX { self.manuscript[i + 1] = self.manuscript[i]; }
                    }
                    self.manuscript[self.cursor] = b'\n';
                    self.ms_len += 1;
                    self.cursor += 1;
                }
            }
            Key::Backspace => {
                if self.cursor > 0 {
                    self.cursor -= 1;
                    for i in self.cursor..self.ms_len.saturating_sub(1) {
                        self.manuscript[i] = self.manuscript[i + 1];
                    }
                    if self.ms_len > 0 { self.ms_len -= 1; }
                }
            }
            Key::Left  => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Right => { if self.cursor < self.ms_len { self.cursor += 1; } }
            Key::Up    => {
                // Move cursor to start of previous line.
                if self.cursor > 0 { self.cursor -= 1; }
                while self.cursor > 0 && self.manuscript[self.cursor - 1] != b'\n' {
                    self.cursor -= 1;
                }
            }
            Key::Down  => {
                // Move cursor to start of next line.
                while self.cursor < self.ms_len && self.manuscript[self.cursor] != b'\n' {
                    self.cursor += 1;
                }
                if self.cursor < self.ms_len { self.cursor += 1; }
            }
            _ => {}
        }
    }

    fn key_layout(&mut self, key: Key) {
        match key {
            Key::Left | Key::Up => {
                if self.view_page > 1 {
                    self.view_page -= 1;
                    self.typeset_page(self.view_page);
                }
            }
            Key::Right | Key::Down => {
                if self.page_count == 0 { self.recount_pages(); }
                if self.view_page < self.page_count {
                    self.view_page += 1;
                    self.typeset_page(self.view_page);
                }
            }
            _ => {}
        }
    }

    fn key_spec(&mut self, key: Key) {
        match key {
            Key::Up   => { if self.preset_idx > 0 { self.preset_idx -= 1; } }
            Key::Down => { if self.preset_idx + 1 < PRESETS.len() { self.preset_idx += 1; } }
            Key::Left => { if self.wood_idx > 0 { self.wood_idx -= 1; } }
            Key::Right=> { if self.wood_idx + 1 < WOOD_PRESETS.len() { self.wood_idx += 1; } }
            Key::Char(b'c') | Key::Char(b'C') => {
                self.cloth_idx = (self.cloth_idx + 1) % CLOTH_PRESETS.len();
            }
            Key::Char(b'b') | Key::Char(b'B') => {
                self.binding = match self.binding {
                    BindingType::CaseBound    => BindingType::CopticStitch,
                    BindingType::CopticStitch => BindingType::LongStitch,
                    BindingType::LongStitch   => BindingType::PerfectBound,
                    BindingType::PerfectBound => BindingType::CaseBound,
                };
            }
            _ => {}
        }
    }

    fn key_bind(&mut self, key: Key) {
        match key {
            Key::Up   => { if self.spec_scroll > 0 { self.spec_scroll -= 1; } }
            Key::Down => { self.spec_scroll = self.spec_scroll.saturating_add(1); }
            Key::Char(b's') | Key::Char(b'S') => { self.save_spec(); }
            Key::Char(b'e') | Key::Char(b'E') => {
                // Export typeset layout as layout.bkl to Sa.
                self.export_layout(b"layout.bkl");
            }
            Key::Char(b'p') | Key::Char(b'P') => {
                // Export then print immediately if printer is ready.
                self.export_layout(b"layout.bkl");
                #[cfg(target_arch = "x86_64")]
                { let _ = crate::printer::print_sa_file(b"layout.bkl"); }
            }
            _ => {}
        }
    }

    fn save_spec(&self) {
        let mut name = [0u8; 24];
        let base = if self.title_n > 0 {
            let n = self.title_n.min(12);
            name[..n].copy_from_slice(&self.title[..n]);
            n
        } else {
            name[..4].copy_from_slice(b"book");
            4
        };
        name[base..base+4].copy_from_slice(b".bks");
        crate::sa::write_file(&name[..base+4], &self.spec_out[..self.spec_out_n]);
    }

    // -- Render ---------------------------------------------------------------

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let w   = gpu.width();
        let h   = gpu.height();
        let top = self.rule_y + 4;
        it.fill(0, top, w, h.saturating_sub(top), t.bg);

        // Tab bar
        let tabs = [("Write", BookTab::Write), ("Layout", BookTab::Layout),
                    ("Spec",  BookTab::Spec),  ("Bind",   BookTab::Bind)];
        let mut tx = 20u32;
        for (label, tab) in &tabs {
            let sel = self.tab == *tab;
            let col = if sel { t.accent } else { t.text_dim };
            it.text(tx, top + 4, label, 1, col);
            if sel {
                it.fill(tx, top + 13, label.len() as u32 * 6, 1, t.accent);
            }
            tx += label.len() as u32 * 6 + 12;
        }
        it.fill(0, top + 16, w, 1, t.rule);

        let content_top = top + 22;

        match self.tab {
            BookTab::Write  => self.render_write(&it, &t, w, content_top),
            BookTab::Layout => self.render_layout(&it, &t, w, content_top),
            BookTab::Spec   => self.render_spec(&it, &t, w, content_top),
            BookTab::Bind   => self.render_bind(&it, &t, w, h, content_top),
        }

        // Status bar at bottom
        it.fill(0, h.saturating_sub(14), w, 14, t.surface);
        let mut sb = [0u8; 80]; let mut sn = 0;
        let pfx = b"Tab=switch  "; sb[..pfx.len()].copy_from_slice(pfx); sn = pfx.len();
        let rest: &[u8] = match self.tab {
            BookTab::Write  => b"type prose  Enter=newline  BS=delete",
            BookTab::Layout => b"arrows=page",
            BookTab::Spec   => b"up/down=page size  left/right=wood  [C]=cloth  [B]=binding",
            BookTab::Bind   => b"up/down=scroll  [S]=save .bks  [E]=export .bkl  [P]=export+print",
        };
        let rn = rest.len().min(80 - sn);
        sb[sn..sn+rn].copy_from_slice(&rest[..rn]); sn += rn;
        it.text(8, h.saturating_sub(12), core::str::from_utf8(&sb[..sn]).unwrap_or(""), 1, t.text_dim);
    }

    fn render_write(&self, it: &It, t: &style::Theme, w: u32, top: u32) {
        // Title and author header
        let title_s = core::str::from_utf8(&self.title[..self.title_n]).unwrap_or("");
        let auth_s  = core::str::from_utf8(&self.author[..self.author_n]).unwrap_or("");
        it.text(20, top, title_s, 2, t.header);
        it.text(20, top + 20, auth_s, 1, t.text_dim);

        // Manuscript text with cursor, soft-wrapped at display width.
        let cols = ((w.saturating_sub(60)) / 6).min(80) as usize;
        let mut y = top + 36;
        let mut px = 0usize;   // position in manuscript we're rendering
        let mut line_start = 0usize;
        let mut cur_rendered = false;
        const VISIBLE_LINES: usize = 30;

        // Find the display start: scroll to keep cursor visible.
        // (Simplified: render from byte 0 up to visible area.)
        let mut col = 0usize;
        let mut line_idx = 0usize;

        while px <= self.ms_len && y < top + 36 + VISIBLE_LINES as u32 * 12 {
            let at_cursor = px == self.cursor;
            if col == cols || (px < self.ms_len && self.manuscript[px] == b'\n') {
                // Advance display line.
                line_idx += 1;
                y += 12;
                col = 0;
                if px < self.ms_len && self.manuscript[px] == b'\n' { px += 1; continue; }
                continue;
            }
            if px >= self.ms_len {
                // End of text -- show cursor here.
                if at_cursor {
                    let cx = 20 + col as u32 * 6;
                    it.fill(cx, y, 5, 10, t.accent);
                }
                break;
            }
            let c = self.manuscript[px];
            if c >= 0x20 && c < 0x7F {
                let cx = 20 + col as u32 * 6;
                if y >= top + 36 {
                    if at_cursor {
                        it.fill(cx, y, 5, 10, t.accent);
                    }
                    let cs = core::str::from_utf8(&self.manuscript[px..px+1]).unwrap_or(" ");
                    it.text(cx, y, cs, 1, t.text);
                }
                col += 1;
            }
            px += 1;
        }

        // Word count
        let words = word_count(&self.manuscript[..self.ms_len]);
        let mut wcb = [0u8; 32]; let wn = write_u32(&mut wcb, words as u32);
        it.text(20, top + 36 + VISIBLE_LINES as u32 * 12 + 4,
            core::str::from_utf8(&wcb[..wn]).unwrap_or("?"), 1, t.text_dim);
        it.text(20 + wn as u32 * 6 + 4, top + 36 + VISIBLE_LINES as u32 * 12 + 4,
            "words", 1, t.text_dim);
    }

    fn render_layout(&self, it: &It, t: &style::Theme, w: u32, top: u32) {
        if self.page_count == 0 {
            it.text(20, top, "No content yet. Write first.", 1, t.text_dim);
            return;
        }
        // Show page number and total.
        let mut pb = [0u8; 16]; let pn = write_u32(&mut pb, self.view_page);
        let mut tb = [0u8; 16]; let tn = write_u32(&mut tb, self.page_count);
        it.text(20, top, "Page", 1, t.text_dim);
        it.text(50, top, core::str::from_utf8(&pb[..pn]).unwrap_or("?"), 1, t.accent);
        it.text(50 + pn as u32 * 6 + 4, top, "of", 1, t.text_dim);
        it.text(50 + pn as u32 * 6 + 20, top, core::str::from_utf8(&tb[..tn]).unwrap_or("?"), 1, t.text_dim);

        // Page preview box
        let bx = 40u32;
        let by = top + 16;
        let bw = (w.saturating_sub(80)).min(500);
        let bh = (bw * 14 / 10).min(350);  // 2:sqrt(2) aspect ratio
        it.fill(bx, by, bw, bh, (240, 240, 240));
        it.fill(bx, by, bw, 1, t.rule);
        it.fill(bx, by + bh - 1, bw, 1, t.rule);
        it.fill(bx, by, 1, bh, t.rule);
        it.fill(bx + bw - 1, by, 1, bh, t.rule);

        // Render typeset lines into the page box
        let margin_x = 16u32;
        let margin_y = 12u32;
        let max_vis = ((bh.saturating_sub(margin_y * 2)) / 9).min(60) as usize;
        for li in 0..self.cur_page.n.min(max_vis) {
            let n  = self.cur_page.line_n[li] as usize;
            let s  = core::str::from_utf8(&self.cur_page.lines[li][..n]).unwrap_or("");
            let ly = by + margin_y + li as u32 * 9;
            it.text(bx + margin_x, ly, s, 1, (20, 20, 20));
        }
    }

    fn render_spec(&self, it: &It, t: &style::Theme, _w: u32, top: u32) {
        let cfg = TypesetConfig::from_preset(self.preset_idx);
        it.text(20, top, "Page Size", 1, t.text_dim);
        for i in 0..PRESETS.len() {
            let col = if i == self.preset_idx { t.accent } else { t.text };
            let pn = core::str::from_utf8(PRESETS[i].name).unwrap_or("?");
            it.text(30, top + 14 + i as u32 * 13, pn, 1, col);
        }
        let ty = top + 14 + PRESETS.len() as u32 * 13 + 8;

        it.text(20, ty, "Wood Board", 1, t.text_dim);
        for i in 0..WOOD_PRESETS.len() {
            let col = if i == self.wood_idx { t.accent } else { t.text };
            it.text(30, ty + 14 + i as u32 * 13, WOOD_PRESETS[i].name, 1, col);
        }
        let ty2 = ty + 14 + WOOD_PRESETS.len() as u32 * 13 + 8;

        it.text(20, ty2, "Cloth", 1, t.text_dim);
        let cn = CLOTH_PRESETS[self.cloth_idx.min(CLOTH_PRESETS.len()-1)];
        it.text(30, ty2 + 14, cn, 1, t.accent);

        it.text(20, ty2 + 32, "Binding", 1, t.text_dim);
        it.text(30, ty2 + 46, self.binding.name(), 1, t.accent);

        it.text(20, ty2 + 64, "Text area:", 1, t.text_dim);
        let mut cb = [0u8; 8]; let cn2 = write_u32(&mut cb, cfg.cols as u32);
        it.text(100, ty2 + 64, core::str::from_utf8(&cb[..cn2]).unwrap_or("?"), 1, t.text);
        it.text(100 + cn2 as u32 * 6 + 4, ty2 + 64, "cols x", 1, t.text_dim);
        let mut lb = [0u8; 8]; let ln2 = write_u32(&mut lb, cfg.body_lines as u32);
        it.text(100 + cn2 as u32 * 6 + 44, ty2 + 64,
            core::str::from_utf8(&lb[..ln2]).unwrap_or("?"), 1, t.text);
        it.text(100 + cn2 as u32 * 6 + 44 + ln2 as u32 * 6 + 4, ty2 + 64, "lines", 1, t.text_dim);
    }

    fn render_bind(&self, it: &It, t: &style::Theme, w: u32, h: u32, top: u32) {
        if self.spec_out_n == 0 {
            it.text(20, top, "Calculating...", 1, t.text_dim);
            return;
        }
        let cols = ((w.saturating_sub(40)) / 6).min(80) as usize;
        let avail = (h.saturating_sub(top + 16)) / 11;
        let mut y = top;
        let mut line = 0usize;
        let mut pos  = 0usize;
        let spec = &self.spec_out[..self.spec_out_n];
        let mut lstart = 0usize;
        let mut lcount = 0usize;

        // Count lines to implement scroll.
        while pos <= spec.len() {
            if pos == spec.len() || spec[pos] == b'\n' {
                if lcount >= self.spec_scroll {
                    if line < avail as usize {
                        let s = core::str::from_utf8(&spec[lstart..pos]).unwrap_or("");
                        let col = if s.contains('=') || s.ends_with('-') { t.header }
                                  else if s.starts_with("  ") { t.text_dim }
                                  else { t.text };
                        it.text(20, y + line as u32 * 11, s, 1, col);
                        line += 1;
                    }
                }
                lcount += 1;
                if pos < spec.len() { lstart = pos + 1; }
            }
            if pos >= spec.len() { break; }
            pos += 1;
        }
    }
}

// -- Text helpers -------------------------------------------------------------

fn centre_text(text: &[u8], cols: usize) -> [u8; LINE_W] {
    let mut out = [b' '; LINE_W];
    let n = text.len().min(cols);
    let pad = (cols.saturating_sub(n)) / 2;
    out[pad..pad + n].copy_from_slice(&text[..n]);
    out
}

fn underline(len: usize) -> [u8; LINE_W] {
    let mut out = [b' '; LINE_W];
    for i in 0..len.min(LINE_W) { out[i] = b'-'; }
    out
}

fn scene_break(cols: usize) -> [u8; LINE_W] {
    let mut out = [b' '; LINE_W];
    if cols >= 7 {
        let mid = cols / 2;
        out[mid.saturating_sub(3)] = b'*';
        out[mid]                   = b'*';
        out[mid + 3]               = b'*';
    }
    out
}

fn page_num_line(n: u32, cols: usize) -> [u8; LINE_W] {
    let mut out = [b' '; LINE_W];
    let mut nb = [0u8; 8]; let nn = write_u32(&mut nb, n);
    let pos = (cols.saturating_sub(nn)) / 2;
    out[pos..pos + nn].copy_from_slice(&nb[..nn]);
    out
}

fn word_count(text: &[u8]) -> usize {
    let mut in_word = false;
    let mut count   = 0usize;
    for &b in text {
        match b {
            b' ' | b'\n' | b'\t' => { in_word = false; }
            _ => { if !in_word { count += 1; in_word = true; } }
        }
    }
    count
}

fn write_dmm(buf: &mut [u8], v_dmm: u16) -> usize {
    // Write as mm with one decimal: e.g. 1480 -> "148.0"
    let mm    = v_dmm / 10;
    let tenth = v_dmm % 10;
    let mut n = write_u32(buf, mm as u32);
    if n < buf.len() { buf[n] = b'.'; n += 1; }
    if n < buf.len() { buf[n] = b'0' + tenth as u8; n += 1; }
    n
}

fn write_u32(buf: &mut [u8], v: u32) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n - 1 - i]; }
    n
}


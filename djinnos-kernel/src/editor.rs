// Ko editor — in-kernel text editor for .ko and plain-text files.
//
// Invoked with `edit <filename>` from the Ko shell.
// Operates on a static 8 KiB mutable buffer.  On exit (Escape) the buffer
// is written to the ramdisk volatile slot so `Sao` sees the updated version.
//
// Keys:
//   Arrow keys     navigate
//   Printable      insert at cursor
//   Enter          insert newline
//   Backspace      delete before cursor
//   Ctrl+S (0x13)  save without exiting
//   Escape         save and exit

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;

const SCALE:   u32 = 2;
const CHAR_W:  u32 = font::GLYPH_W * SCALE;
const CHAR_H:  u32 = font::GLYPH_H * SCALE;
const MX:      u32 = 8;
const MY:      u32 = 4;
const BUF_CAP: usize = 8192;
const MAX_LS:  usize = 512;

const BG_R:  u8 = 0x08; const BG_G:  u8 = 0x0c; const BG_B:  u8 = 0x08;
const R_HDR: u8 = 0xc8; const G_HDR: u8 = 0x96; const B_HDR: u8 = 0x4b;
const R_LN:  u8 = 0x50; const G_LN:  u8 = 0x50; const B_LN:  u8 = 0x50;
const R_TXT: u8 = 0xc0; const G_TXT: u8 = 0xc0; const B_TXT: u8 = 0xc0;
const R_CUR: u8 = 0x10; const G_CUR: u8 = 0x10; const B_CUR: u8 = 0x10;
const R_HIL: u8 = 0xc8; const G_HIL: u8 = 0xd0; const B_HIL: u8 = 0x80;
const R_STA: u8 = 0x70; const G_STA: u8 = 0x70; const B_STA: u8 = 0x70;
const R_MOD: u8 = 0xd0; const G_MOD: u8 = 0x60; const B_MOD: u8 = 0x60;

// ── Request mechanism ─────────────────────────────────────────────────────────

static mut REQUESTED:  bool    = false;
static mut REQ_NAME:   [u8; 32] = [0u8; 32];
static mut REQ_NAME_N: usize   = 0;

pub fn request(name: &[u8]) {
    unsafe {
        let n = name.len().min(31);
        REQ_NAME[..n].copy_from_slice(&name[..n]);
        REQ_NAME_N = n;
        REQUESTED = true;
    }
}

pub fn consume_request() -> Option<&'static [u8]> {
    unsafe {
        if REQUESTED {
            REQUESTED = false;
            Some(&REQ_NAME[..REQ_NAME_N])
        } else {
            None
        }
    }
}

// ── Static edit buffer ────────────────────────────────────────────────────────

static mut ED_BUF: [u8; BUF_CAP] = [0u8; BUF_CAP];
static mut ED_LEN: usize          = 0;

// ── Editor ────────────────────────────────────────────────────────────────────

pub struct Editor {
    cursor:   usize,
    top_line: usize,
    name:     [u8; 32],
    name_n:   usize,
    modified: bool,
    exited:   bool,
    rule_y:   u32,
}

impl Editor {
    pub fn new(rule_y: u32) -> Self {
        Editor {
            cursor: 0, top_line: 0,
            name: [0; 32], name_n: 0,
            modified: false, exited: false,
            rule_y,
        }
    }

    pub fn load(&mut self, name: &[u8]) {
        self.name_n = name.len().min(31);
        self.name[..self.name_n].copy_from_slice(&name[..self.name_n]);
        self.cursor   = 0;
        self.top_line = 0;
        self.modified = false;
        self.exited   = false;
        unsafe {
            match crate::ramdisk::find(name) {
                Some(data) => {
                    let n = data.len().min(BUF_CAP);
                    ED_BUF[..n].copy_from_slice(&data[..n]);
                    ED_LEN = n;
                }
                None => { ED_LEN = 0; }
            }
        }
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.save(); self.exited = true; }
            Key::Char(0x13) => { self.save(); }         // Ctrl+S
            Key::Char(c) if c >= 0x20 => { self.insert(c); }
            Key::Enter     => { self.insert(b'\n'); }
            Key::Backspace => { self.backspace(); }
            Key::Left  => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Right => {
                let len = unsafe { ED_LEN };
                if self.cursor < len { self.cursor += 1; }
            }
            Key::Up    => { self.move_vert(-1); }
            Key::Down  => { self.move_vert(1); }
            _ => {}
        }
        self.scroll_to_cursor();
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MY;
        let (cur_row, cur_col) = buf_cursor_pos(self.cursor);

        // Header
        self.draw_header(gpu, y0, w, cur_row, cur_col);
        let content_y = y0 + CHAR_H + 4;

        // Line-number column: "NNN|" = 4 chars
        let lncol_w = 4 * CHAR_W;
        let text_x  = MX + lncol_w + CHAR_W;

        let content_h = h.saturating_sub(content_y + CHAR_H + 6);
        let vis_rows  = (content_h / CHAR_H) as usize;

        let ls  = buf_line_starts();
        let len = unsafe { ED_LEN };

        let mut y = content_y;
        for i in 0..vis_rows {
            let li = self.top_line + i;
            if li >= ls.count { break; }

            let lstart = ls.starts[li];
            let lend   = if li + 1 < ls.count { ls.starts[li + 1].saturating_sub(1) }
                         else { len };

            // Highlight current row
            if li == cur_row {
                gpu.fill_rect(0, y, w, CHAR_H, BG_B + 3, BG_G + 6, BG_R + 3);
            }

            // Line number
            {
                let mut nb = [b' '; 4];
                write_u32_right(&mut nb[..3], (li + 1) as u32);
                nb[3] = b'|';
                if let Ok(s) = core::str::from_utf8(&nb) {
                    font::draw_str(gpu, MX, y, s, SCALE, R_LN, G_LN, B_LN);
                }
            }

            // Text
            let max_ch = ((w.saturating_sub(text_x)) / CHAR_W) as usize;
            let data   = unsafe { &ED_BUF[lstart..lend.min(lstart + max_ch)] };
            if let Ok(s) = core::str::from_utf8(data) {
                font::draw_str(gpu, text_x, y, s, SCALE, R_TXT, G_TXT, B_TXT);
            }

            // Cursor block
            if li == cur_row {
                let cx = text_x + cur_col as u32 * CHAR_W;
                if cx + CHAR_W <= w {
                    // Draw highlight behind cursor char
                    gpu.fill_rect(cx, y, CHAR_W, CHAR_H, B_HIL, G_HIL, R_HIL);
                    // Re-draw the character in dark so it stays legible
                    let off = lstart + cur_col;
                    if off < lend {
                        let cb = unsafe { ED_BUF[off] };
                        if cb >= 0x20 {
                            let tmp = [cb];
                            if let Ok(s) = core::str::from_utf8(&tmp) {
                                font::draw_str(gpu, cx, y, s, SCALE, R_CUR, G_CUR, B_CUR);
                            }
                        }
                    }
                }
            }

            y += CHAR_H;
        }

        // Status bar
        let sy = h.saturating_sub(CHAR_H + 2);
        let hint = b"Esc: save+exit   Ctrl+S: save   Arrows: move";
        if let Ok(s) = core::str::from_utf8(hint) {
            font::draw_str(gpu, MX, sy, s, SCALE, R_STA, G_STA, B_STA);
        }
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn move_vert(&mut self, delta: i32) {
        let (row, col)  = buf_cursor_pos(self.cursor);
        let ls          = buf_line_starts();
        let new_row     = if delta < 0 {
            row.saturating_sub((-delta) as usize)
        } else {
            (row + delta as usize).min(ls.count.saturating_sub(1))
        };
        if new_row == row { return; }
        let ns  = ls.starts[new_row];
        let ne  = if new_row + 1 < ls.count {
            ls.starts[new_row + 1].saturating_sub(1)
        } else {
            unsafe { ED_LEN }
        };
        self.cursor = ns + col.min(ne.saturating_sub(ns));
    }

    fn scroll_to_cursor(&mut self) {
        let (row, _) = buf_cursor_pos(self.cursor);
        if row < self.top_line {
            self.top_line = row;
        } else if row >= self.top_line + 20 {
            self.top_line = row.saturating_sub(19);
        }
    }

    fn insert(&mut self, c: u8) {
        unsafe {
            if ED_LEN >= BUF_CAP { return; }
            let mut i = ED_LEN;
            while i > self.cursor { ED_BUF[i] = ED_BUF[i - 1]; i -= 1; }
            ED_BUF[self.cursor] = c;
            ED_LEN  += 1;
            self.cursor  += 1;
            self.modified = true;
        }
    }

    fn backspace(&mut self) {
        unsafe {
            if self.cursor == 0 || ED_LEN == 0 { return; }
            self.cursor -= 1;
            let mut i = self.cursor;
            while i + 1 < ED_LEN { ED_BUF[i] = ED_BUF[i + 1]; i += 1; }
            ED_LEN -= 1;
            self.modified = true;
        }
    }

    fn save(&mut self) {
        if !self.modified { return; }
        let name = &self.name[..self.name_n];
        let data = unsafe { &ED_BUF[..ED_LEN] };
        // Write to Sa volume (session-persistent) and volatile ramdisk slot.
        crate::sa::write_file(name, data);
        crate::ramdisk::write_edit(name, data);
        self.modified = false;
    }

    fn draw_header(&self, gpu: &dyn GpuSurface, y: u32, w: u32,
                   row: usize, col: usize) {
        // Left: filename [modified]
        let mut buf = [b' '; 80];
        let mut n = self.name_n.min(24);
        buf[..n].copy_from_slice(&self.name[..n]);
        if self.modified {
            let m = b"  [*]";
            if n + m.len() < 80 {
                buf[n..n + m.len()].copy_from_slice(m);
                n += m.len();
            }
        }
        // Right: Ln/Col
        let mut rc = [b' '; 20];
        let mut ri = 0;
        let l = b"Ln:";
        rc[ri..ri + l.len()].copy_from_slice(l); ri += l.len();
        ri += write_u32(&mut rc[ri..], (row + 1) as u32);
        let c = b"  Col:";
        rc[ri..ri + c.len()].copy_from_slice(c); ri += c.len();
        ri += write_u32(&mut rc[ri..], (col + 1) as u32);
        let max_cols = (w.saturating_sub(MX * 2)) / CHAR_W;
        let rstart = (max_cols as usize).saturating_sub(ri).min(79);
        for (k, &b) in rc[..ri].iter().enumerate() {
            if rstart + k < 80 { buf[rstart + k] = b; }
        }
        n = n.max(rstart + ri);
        if let Ok(s) = core::str::from_utf8(&buf[..n]) {
            let color = if self.modified { [R_MOD, G_MOD, B_MOD] } else { [R_HDR, G_HDR, B_HDR] };
            font::draw_str(gpu, MX, y, s, SCALE, color[0], color[1], color[2]);
        }
    }
}

// ── Buffer helpers ────────────────────────────────────────────────────────────

struct LineStarts {
    starts: [usize; MAX_LS],
    count:  usize,
}

fn buf_line_starts() -> LineStarts {
    let len = unsafe { ED_LEN };
    let mut ls = LineStarts { starts: [0; MAX_LS], count: 1 };
    unsafe {
        for i in 0..len {
            if ED_BUF[i] == b'\n' && ls.count < MAX_LS {
                ls.starts[ls.count] = i + 1;
                ls.count += 1;
            }
        }
    }
    ls
}

fn buf_cursor_pos(cursor: usize) -> (usize, usize) {
    let len = unsafe { ED_LEN };
    let (mut row, mut col) = (0usize, 0usize);
    unsafe {
        for i in 0..cursor.min(len) {
            if ED_BUF[i] == b'\n' { row += 1; col = 0; } else { col += 1; }
        }
    }
    (row, col)
}

// ── Numeric formatting ────────────────────────────────────────────────────────

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + (n % 10) as u8; n /= 10; l += 1; }
    for i in 0..l.min(buf.len()) { buf[i] = tmp[l - 1 - i]; }
    l
}

fn write_u32_right(buf: &mut [u8], n: u32) {
    let mut tmp = [b' '; 10];
    let l = write_u32(&mut tmp, n);
    let w = buf.len();
    if l <= w {
        let off = w - l;
        for i in 0..off { buf[i] = b' '; }
        buf[off..].copy_from_slice(&tmp[..l]);
    }
}
// Kobra REPL — interactive Shygazun expression evaluator.
//
// Invoked from the Ko shell with `Kobra` (no arguments).
// Escape returns to the Ko shell.
// Arrow Up/Down browse input history.
// `Ze` clears the output history.

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use kobra_core::ast::Pool;
use kobra_core::eval::{eval, Output};
use kobra_core::parser::{parse, ParseResult};

const SCALE:    u32 = 2;
const CHAR_W:   u32 = font::GLYPH_W * SCALE;
const CHAR_H:   u32 = font::GLYPH_H * SCALE;
const MARGIN_X: u32 = 16;
const MARGIN_Y: u32 = 8;
const LINE_W:   usize = 76;
const MAX_HIST: usize = 40;
const MAX_IHIST: usize = 16;

const R_HDR: u8 = 0xc8; const G_HDR: u8 = 0x96; const B_HDR: u8 = 0x4b;
const R_IN:  u8 = 0x80; const G_IN:  u8 = 0xd0; const B_IN:  u8 = 0x80;
const R_OUT: u8 = 0xa0; const G_OUT: u8 = 0x78; const B_OUT: u8 = 0x38;
const R_ERR: u8 = 0xd0; const G_ERR: u8 = 0x50; const B_ERR: u8 = 0x50;
const BG_R:  u8 = 0x08; const BG_G:  u8 = 0x08; const BG_B:  u8 = 0x10;

// ── Request flag (shell → main loop) ─────────────────────────────────────────

static mut REQUESTED: bool = false;

pub fn request() { unsafe { REQUESTED = true; } }

pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

// ── REPL state ────────────────────────────────────────────────────────────────

pub struct KobraRepl {
    hist:     [[u8; LINE_W]; MAX_HIST],
    hist_len: [u8; MAX_HIST],
    hist_col: [[u8; 3]; MAX_HIST],
    hist_n:   usize,

    ihist:    [[u8; 80]; MAX_IHIST],
    ihist_n:  [u8; MAX_IHIST],
    ihist_sz: usize,
    ihist_pos: usize,  // MAX_IHIST = not browsing

    input:    [u8; 80],
    input_n:  usize,

    rule_y:   u32,
    exited:   bool,
}

impl KobraRepl {
    pub fn new(rule_y: u32) -> Self {
        KobraRepl {
            hist:     [[0; LINE_W]; MAX_HIST],
            hist_len: [0; MAX_HIST],
            hist_col: [[R_OUT, G_OUT, B_OUT]; MAX_HIST],
            hist_n:   0,
            ihist:    [[0; 80]; MAX_IHIST],
            ihist_n:  [0; MAX_IHIST],
            ihist_sz: 0,
            ihist_pos: MAX_IHIST,
            input:    [0; 80],
            input_n:  0,
            rule_y,
            exited: false,
        }
    }

    pub fn reset(&mut self) {
        self.hist_n  = 0;
        self.input_n = 0;
        self.exited  = false;
        self.ihist_pos = MAX_IHIST;
        self.push_line(b"Kobra REPL  [Esc: shell  Ze: clear  Up/Down: history]",
                       [R_HDR, G_HDR, B_HDR]);
        self.push_line(b"", [R_OUT, G_OUT, B_OUT]);
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.exited = true; }

            Key::Enter => { self.submit(); }

            Key::Backspace => {
                if self.input_n > 0 { self.input_n -= 1; }
            }

            Key::Up => {
                if self.ihist_sz == 0 { return; }
                if self.ihist_pos == MAX_IHIST {
                    self.ihist_pos = self.ihist_sz - 1;
                } else if self.ihist_pos > 0 {
                    self.ihist_pos -= 1;
                }
                let p = self.ihist_pos;
                let l = self.ihist_n[p] as usize;
                self.input[..l].copy_from_slice(&self.ihist[p][..l]);
                self.input_n = l;
            }

            Key::Down => {
                if self.ihist_pos >= self.ihist_sz.saturating_sub(1) {
                    self.ihist_pos = MAX_IHIST;
                    self.input_n = 0;
                } else {
                    self.ihist_pos += 1;
                    let p = self.ihist_pos;
                    let l = self.ihist_n[p] as usize;
                    self.input[..l].copy_from_slice(&self.ihist[p][..l]);
                    self.input_n = l;
                }
            }

            Key::Char(c) => {
                if self.input_n < 79 {
                    self.input[self.input_n] = c;
                    self.input_n += 1;
                }
            }

            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let floor_top = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor_top, w, h.saturating_sub(floor_top), BG_B, BG_G, BG_R);

        // How many history lines fit above the input row.
        let avail_h = h.saturating_sub(floor_top + MARGIN_Y + CHAR_H + 4);
        let max_rows = (avail_h / CHAR_H) as usize;
        let visible  = self.hist_n.min(max_rows);
        let start    = self.hist_n.saturating_sub(visible);

        let mut y = floor_top + MARGIN_Y;
        for i in start..self.hist_n {
            let l = self.hist_len[i] as usize;
            let [r, g, b] = self.hist_col[i];
            if let Ok(s) = core::str::from_utf8(&self.hist[i][..l]) {
                font::draw_str(gpu, MARGIN_X, y, s, SCALE, r, g, b);
            }
            y += CHAR_H;
        }

        // Input prompt + current line.
        let px = font::draw_str(gpu, MARGIN_X, y, "[Ko] > ", SCALE, R_IN, G_IN, B_IN);
        if let Ok(s) = core::str::from_utf8(&self.input[..self.input_n]) {
            let cx = font::draw_str(gpu, px, y, s, SCALE, R_HDR, G_HDR, B_HDR);
            gpu.fill_rect(cx, y, CHAR_W, CHAR_H, B_HDR, G_HDR, R_HDR);
        }
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn submit(&mut self) {
        let n = self.input_n;
        if n == 0 { return; }

        // Echo
        let mut echo = [0u8; LINE_W];
        let pfx = b"[Ko] > ";
        let pl = pfx.len().min(LINE_W);
        echo[..pl].copy_from_slice(&pfx[..pl]);
        let cl = n.min(LINE_W - pl);
        echo[pl..pl + cl].copy_from_slice(&self.input[..cl]);
        self.push_line(&echo[..pl + cl], [R_IN, G_IN, B_IN]);

        // Save to input history
        let mut saved = [0u8; 80];
        saved[..n].copy_from_slice(&self.input[..n]);
        let saved_n = n;

        let cmd = trim(&self.input[..n]);

        // Special: Ze / clear
        if cmd == b"Ze" || cmd == b"clear" {
            self.hist_n = 0;
            self.push_line(b"Kobra REPL  [Esc: shell  Ze: clear  Up/Down: history]",
                           [R_HDR, G_HDR, B_HDR]);
            self.push_line(b"", [R_OUT, G_OUT, B_OUT]);
            self.input_n = 0;
            return;
        }

        // Eval
        let mut pool = Pool::empty();
        let mut out  = ReplOut::new();
        match parse(cmd, &mut pool) {
            ParseResult::Ok(root) => {
                eval(&pool, root, &mut out);
                out.flush_cur();
                if out.count == 0 {
                    self.push_line(b"(no output)", [R_OUT, G_OUT, B_OUT]);
                } else {
                    for i in 0..out.count {
                        let l = out.lens[i] as usize;
                        self.push_line(&out.lines[i][..l], [R_OUT, G_OUT, B_OUT]);
                    }
                }
            }
            ParseResult::Empty => {
                self.push_line(b"(empty)", [R_OUT, G_OUT, B_OUT]);
            }
            ParseResult::Err => {
                self.push_line(b"parse error", [R_ERR, G_ERR, B_ERR]);
            }
        }
        self.push_line(b"", [R_OUT, G_OUT, B_OUT]);

        // Append to input history (shift if full)
        if self.ihist_sz >= MAX_IHIST {
            for i in 0..MAX_IHIST - 1 {
                self.ihist[i] = self.ihist[i + 1];
                self.ihist_n[i] = self.ihist_n[i + 1];
            }
            self.ihist_sz = MAX_IHIST - 1;
        }
        let s = self.ihist_sz;
        self.ihist[s][..saved_n].copy_from_slice(&saved[..saved_n]);
        self.ihist_n[s] = saved_n as u8;
        self.ihist_sz += 1;
        self.ihist_pos = MAX_IHIST;
        self.input_n = 0;
    }

    fn push_line(&mut self, text: &[u8], color: [u8; 3]) {
        if self.hist_n >= MAX_HIST {
            for i in 0..MAX_HIST - 1 {
                self.hist[i]     = self.hist[i + 1];
                self.hist_len[i] = self.hist_len[i + 1];
                self.hist_col[i] = self.hist_col[i + 1];
            }
            self.hist_n = MAX_HIST - 1;
        }
        let i = self.hist_n;
        let l = text.len().min(LINE_W);
        self.hist[i][..l].copy_from_slice(&text[..l]);
        self.hist_len[i] = l as u8;
        self.hist_col[i] = color;
        self.hist_n += 1;
    }
}

// ── Local Output buffer ───────────────────────────────────────────────────────

struct ReplOut {
    lines: [[u8; LINE_W]; 20],
    lens:  [u8; 20],
    count: usize,
    cur:   [u8; LINE_W],
    cur_n: usize,
}

impl ReplOut {
    fn new() -> Self {
        ReplOut {
            lines: [[0; LINE_W]; 20], lens: [0; 20], count: 0,
            cur: [0; LINE_W], cur_n: 0,
        }
    }

    fn flush_cur(&mut self) {
        if self.cur_n > 0 && self.count < 20 {
            let n = self.cur_n;
            self.lines[self.count][..n].copy_from_slice(&self.cur[..n]);
            self.lens[self.count] = n as u8;
            self.count += 1;
            self.cur_n = 0;
        }
    }
}

impl Output for ReplOut {
    fn write(&mut self, s: &[u8]) {
        for &b in s {
            if b == b'\n' || b == b'\r' { self.flush_cur(); }
            else if self.cur_n < LINE_W { self.cur[self.cur_n] = b; self.cur_n += 1; }
        }
    }
}

fn trim(s: &[u8]) -> &[u8] {
    let s = match s.iter().position(|&b| b != b' ' && b != b'\t') {
        Some(i) => &s[i..],
        None    => return b"",
    };
    match s.iter().rposition(|&b| b != b' ' && b != b'\t') {
        Some(i) => &s[..=i],
        None    => s,
    }
}
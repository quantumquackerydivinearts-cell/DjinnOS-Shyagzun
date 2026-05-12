// kobra — Shygazun Kobra interpreter wired into the DjinnOS kernel.
//
// All output from the parser/evaluator is captured into an EvalResult
// (a fixed-size line buffer on the stack) so the shell can push lines
// to the framebuffer and/or UART after the call returns.
//
// Entry points
// ------------
//   eval_expr(src)  — parse and evaluate a raw Kobra expression byte slice.
//   eval_file(data) — same, but for the full bytes of a .ko ramdisk file.
//                     Iterates newline-delimited expressions and evals each.

use kobra_core::ast::Pool;
use kobra_core::eval::{eval, Output};
use kobra_core::parser::{parse, ParseResult};

// ── Result type ───────────────────────────────────────────────────────────────

const MAX_LINES: usize = 12;
const LINE_CAP:  usize = 78;

pub struct EvalResult {
    lines: [[u8; LINE_CAP]; MAX_LINES],
    lens:  [u8; MAX_LINES],
    count: usize,
    // Current partial line being assembled
    cur:   [u8; LINE_CAP],
    cur_n: usize,
}

impl EvalResult {
    fn new() -> Self {
        EvalResult {
            lines: [[0u8; LINE_CAP]; MAX_LINES],
            lens:  [0u8; MAX_LINES],
            count: 0,
            cur:   [0u8; LINE_CAP],
            cur_n: 0,
        }
    }

    fn flush_cur(&mut self) {
        if self.cur_n > 0 && self.count < MAX_LINES {
            let n = self.cur_n;
            self.lines[self.count][..n].copy_from_slice(&self.cur[..n]);
            self.lens[self.count] = n as u8;
            self.count += 1;
            self.cur_n = 0;
        }
    }

    pub fn line_count(&self) -> usize { self.count }

    pub fn line(&self, i: usize) -> &[u8] {
        &self.lines[i][..self.lens[i] as usize]
    }

    /// Append bytes to the current partial line (no newline).
    pub fn push_text(&mut self, s: &[u8]) { self.write(s); }

    /// Flush the current partial line as a complete line (equivalent to writing '\n').
    pub fn push_line(&mut self) { self.flush_cur(); }
}

impl Output for EvalResult {
    fn write(&mut self, s: &[u8]) {
        for &b in s {
            if b == b'\n' {
                self.flush_cur();
            } else if b == b'\r' {
                // ignore bare CR; \r\n flushed on \n
            } else if self.cur_n < LINE_CAP {
                self.cur[self.cur_n] = b;
                self.cur_n += 1;
            }
        }
    }
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Parse and evaluate a single Kobra expression (raw bytes, no newline needed).
/// Game-system namespaces (quest/skill/perk) are dispatched before Kobra AST.
/// Returns a line buffer the caller can display.
pub fn eval_expr(src: &[u8]) -> EvalResult {
    let mut out = EvalResult::new();

    // Game dispatch layer — intercept before Kobra AST.
    if src.starts_with(b"quest ") {
        crate::quest_tracker::quest_dispatch(&src[6..], &mut out);
        return out;
    }
    if src.starts_with(b"quest") && src.len() == 5 {
        crate::quest_tracker::quest_dispatch(b"", &mut out);
        return out;
    }
    if src.starts_with(b"skill ") {
        crate::skills::skill_dispatch(&src[6..], &mut out);
        return out;
    }
    if src.starts_with(b"perk ") {
        crate::skills::perk_dispatch(&src[5..], &mut out);
        return out;
    }
    if src.starts_with(b"perk") && src.len() == 4 {
        crate::skills::perk_dispatch(b"", &mut out);
        return out;
    }
    if src.starts_with(b"forage ") {
        crate::foraging::forage_dispatch(&src[7..], &mut out);
        return out;
    }
    if src.starts_with(b"forage") && src.len() == 6 {
        crate::foraging::forage_dispatch(b"", &mut out);
        return out;
    }

    let mut pool = Pool::empty();

    match parse(src, &mut pool) {
        ParseResult::Ok(root) => {
            eval(&pool, root, &mut out);
            out.flush_cur();
        }
        ParseResult::Empty => {}
        ParseResult::Err   => {
            // Operative-ambiguity model: echo as live object
            out.write(b"echo: ");
            out.write(src);
            out.flush_cur();
        }
    }

    out
}

/// Evaluate every newline-delimited expression in a .ko file.
/// Blank lines and lines starting with '#' are skipped.
/// Returns a combined line buffer (up to MAX_LINES total).
pub fn eval_file(data: &[u8]) -> EvalResult {
    let mut combined = EvalResult::new();
    let mut pool     = Pool::empty();

    let mut start = 0usize;
    while start <= data.len() {
        let end = data[start..]
            .iter()
            .position(|&b| b == b'\n')
            .map(|i| start + i)
            .unwrap_or(data.len());

        let raw  = &data[start..end];
        let line = trim_bytes(raw);

        if !line.is_empty() && line[0] != b'#' {
            pool.reset();
            match parse(line, &mut pool) {
                ParseResult::Ok(root) => {
                    if combined.count < MAX_LINES {
                        eval(&pool, root, &mut combined);
                        combined.flush_cur();
                    }
                }
                ParseResult::Err => {
                    if combined.count < MAX_LINES {
                        combined.write(b"echo: ");
                        combined.write(line);
                        combined.flush_cur();
                    }
                }
                ParseResult::Empty => {}
            }
        }

        if end >= data.len() { break; }
        start = end + 1;
    }

    combined
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn trim_bytes(s: &[u8]) -> &[u8] {
    let s = match s.iter().position(|&b| b != b' ' && b != b'\t' && b != b'\r') {
        Some(i) => &s[i..],
        None    => return b"",
    };
    match s.iter().rposition(|&b| b != b' ' && b != b'\t' && b != b'\r') {
        Some(i) => &s[..=i],
        None    => s,
    }
}
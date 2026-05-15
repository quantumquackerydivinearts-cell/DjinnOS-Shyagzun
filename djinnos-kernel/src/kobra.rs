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
    cur:   [u8; LINE_CAP],
    cur_n: usize,
    /// Set by dispatchers that emit Faerie-safe HTML.
    /// When true, eval_ko passes the output to parse_html instead of push_line.
    pub html: bool,
}

impl EvalResult {
    fn new() -> Self {
        EvalResult {
            lines: [[0u8; LINE_CAP]; MAX_LINES],
            lens:  [0u8; MAX_LINES],
            count: 0,
            cur:   [0u8; LINE_CAP],
            cur_n: 0,
            html:  false,
        }
    }

    /// Write all completed lines into `buf` with '\n' separators.
    /// Returns bytes written.  Used by eval_ko to feed parse_html.
    pub fn write_to(&self, buf: &mut [u8]) -> usize {
        let mut pos = 0usize;
        for i in 0..self.count {
            let n = self.lens[i] as usize;
            let copy = n.min(buf.len().saturating_sub(pos));
            buf[pos..pos + copy].copy_from_slice(&self.lines[i][..copy]);
            pos += copy;
            if pos < buf.len() { buf[pos] = b'\n'; pos += 1; }
        }
        pos
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

    // ── Faerie/browser dispatch — emit HTML for ko: links ────────────────────
    if src.starts_with(b"page ") {
        page_dispatch(trim_bytes(&src[5..]), &mut out);
        return out;
    }
    if src.starts_with(b"zone") {
        let arg = trim_bytes(if src.len() > 4 { &src[4..] } else { b"" });
        zone_dispatch(arg, &mut out);
        return out;
    }
    if src == b"player" {
        player_dispatch(&mut out);
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

// ── Faerie dispatch handlers ──────────────────────────────────────────────────

/// `ko:page <name>` — outputs a local:// URL, causing Faerie to navigate.
fn page_dispatch(name: &[u8], out: &mut EvalResult) {
    if name.is_empty() {
        out.write(b"local://home.html");
    } else {
        out.write(b"local://");
        out.write(name);
        if !name.ends_with(b".html") { out.write(b".html"); }
    }
    out.flush_cur();
}

/// `ko:zone [zone_id]` — renders zone lore as Faerie HTML.
/// With no arg, shows the current game zone.  With an arg, shows that zone.
fn zone_dispatch(arg: &[u8], out: &mut EvalResult) {
    use crate::zone_registry::{zone_by_id, ZoneKind, Realm};
    out.html = true;

    let id: &[u8] = if arg.is_empty() {
        crate::game7::game7().zone_id_pub()
    } else {
        arg
    };

    let Some(z) = zone_by_id(id) else {
        out.write(b"<p>Unknown zone: ");
        out.write(id);
        out.write(b"</p>");
        out.flush_cur();
        return;
    };

    // Realm tag
    let realm: &[u8] = match z.realm {
        Realm::Lapidus  => b"Lapidus",
        Realm::Mercurie => b"Mercurie",
        Realm::Sulphera => b"Sulphera",
    };
    let kind: &[u8] = match z.kind {
        ZoneKind::Town       => b"Town",
        ZoneKind::Market     => b"Market",
        ZoneKind::Temple     => b"Temple",
        ZoneKind::Wilderness => b"Wilderness",
        ZoneKind::Dungeon    => b"Dungeon",
        ZoneKind::BossArena  => b"Boss Arena",
        ZoneKind::Rest       => b"Safe Rest",
        ZoneKind::Threshold  => b"Threshold",
        ZoneKind::Chamber    => b"Chamber",
    };

    out.write(b"<h1>"); out.write(z.name); out.write(b"</h1>");
    out.write(b"<p>"); out.write(realm); out.write(b" -- "); out.write(kind); out.write(b"</p>");
    out.write(b"<p>"); out.write(z.desc); out.write(b"</p>");
    out.flush_cur();

    // Exits as browsable links (lore only — does not move the player).
    let mut has_exit = false;
    for &exit_id in z.exits {
        if let Some(dest) = zone_by_id(exit_id) {
            if !has_exit {
                out.write(b"<hr><h2>Exits</h2><ul>");
                has_exit = true;
            }
            out.write(b"<li><a href=\"ko:zone ");
            out.write(exit_id);
            out.write(b"\">");
            out.write(dest.name);
            out.write(b"</a></li>");
            out.flush_cur();
        }
    }
    if has_exit {
        out.write(b"</ul>");
        out.flush_cur();
    }

    out.write(b"<hr><p><a href=\"local://labyrinth.html\">Back to Labyrinth</a></p>");
    out.flush_cur();
}

/// `ko:player` — renders player sanity and active quests as Faerie HTML.
fn player_dispatch(out: &mut EvalResult) {
    out.html = true;
    let ps = crate::player_state::get();

    out.write(b"<h1>Player State</h1><h2>Sanity</h2><ul>");
    out.flush_cur();

    let labels: [&[u8]; 4] = [b"Alchemical", b"Narrative", b"Terrestrial", b"Cosmic"];
    for (i, &label) in labels.iter().enumerate() {
        if i < ps.sanity.len() {
            out.write(b"<li>"); out.write(label);
            out.write(b": "); wu8(out, ps.sanity[i]);
            out.write(b"/100</li>");
            out.flush_cur();
        }
    }
    out.write(b"</ul>");
    out.flush_cur();

    out.write(b"<hr><p><a href=\"ko:quest\">Active Quests</a></p>");
    out.write(b"<p><a href=\"ko:zone\">Current Zone</a></p>");
    out.write(b"<p><a href=\"local://home.html\">Home</a></p>");
    out.flush_cur();
}

fn wu8(out: &mut EvalResult, mut n: u8) {
    if n == 0 { out.write(b"0"); return; }
    let mut buf = [0u8; 3]; let mut i = 3usize;
    while n > 0 { i -= 1; buf[i] = b'0' + n % 10; n /= 10; }
    out.write(&buf[i..]);
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
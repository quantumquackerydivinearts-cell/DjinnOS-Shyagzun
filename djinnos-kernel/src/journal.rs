// journal.rs — Player journal for Ko's Labyrinth (7_KLGS).
//
// Three entry kinds:
//   Quest   — auto-created when quest state changes
//   Combat  — auto-created on combat result
//   Note    — player-authored free text
//
// Persisted to Sa as "journal.dat" (binary, tag "JN01").
// UI: scrollable entry list with expand-on-select.

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;

// ── Entry ─────────────────────────────────────────────────────────────────────

const MAX_ENTRIES:  usize = 64;
const ENTRY_TEXT_N: usize = 80;
const ENTRY_SLUG_N: usize = 10;

#[derive(Copy, Clone)]
pub enum EntryKind { Quest, Combat, Note }

impl EntryKind {
    fn tag(&self) -> &'static str {
        match self { Self::Quest => "Quest", Self::Combat => "Combat", Self::Note => "Note" }
    }
}

#[derive(Copy, Clone)]
pub struct JournalEntry {
    pub kind:  EntryKind,
    pub slug:  [u8; ENTRY_SLUG_N],  // quest slug or short combat name
    pub slug_n: u8,
    pub text:  [u8; ENTRY_TEXT_N],
    pub text_n: u8,
    pub turn:  u32,  // game turn when entry was recorded
}

impl JournalEntry {
    const EMPTY: Self = Self {
        kind: EntryKind::Note,
        slug: [0u8; ENTRY_SLUG_N],
        slug_n: 0,
        text: [0u8; ENTRY_TEXT_N],
        text_n: 0,
        turn: 0,
    };
}

// ── Journal state ─────────────────────────────────────────────────────────────

pub struct Journal {
    pub entries:   [JournalEntry; MAX_ENTRIES],
    pub count:     usize,
    pub cursor:    usize,
    pub expanded:  bool,
    pub exited:    bool,
    // Note authoring
    pub authoring: bool,
    pub note_buf:  [u8; ENTRY_TEXT_N],
    pub note_n:    usize,
    rule_y: u32,
    game_turn: u32,
}

static mut JOURNAL: Journal = Journal {
    entries:  [JournalEntry::EMPTY; MAX_ENTRIES],
    count:    0,
    cursor:   0,
    expanded: false,
    exited:   false,
    authoring: false,
    note_buf: [0u8; ENTRY_TEXT_N],
    note_n:   0,
    rule_y:   0,
    game_turn: 0,
};

pub fn journal() -> &'static mut Journal { unsafe { &mut JOURNAL } }

static mut JREQ: bool = false;
pub fn request()         { unsafe { JREQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = JREQ; JREQ = false; r } }

// ── Public add functions ──────────────────────────────────────────────────────

pub fn add_quest_event(slug: &[u8], event: &[u8]) {
    let j = journal();
    if j.count >= MAX_ENTRIES { j.shift(); }
    let idx = j.count;
    j.entries[idx].kind = EntryKind::Quest;
    let sn = slug.len().min(ENTRY_SLUG_N);
    j.entries[idx].slug[..sn].copy_from_slice(&slug[..sn]);
    j.entries[idx].slug_n = sn as u8;
    let tn = event.len().min(ENTRY_TEXT_N);
    j.entries[idx].text[..tn].copy_from_slice(&event[..tn]);
    j.entries[idx].text_n = tn as u8;
    j.entries[idx].turn = j.game_turn;
    j.count += 1;
}

pub fn add_combat(enemy_name: &[u8], turns: u32) {
    let j = journal();
    if j.count >= MAX_ENTRIES { j.shift(); }
    let idx = j.count;
    j.entries[idx].kind = EntryKind::Combat;
    let sn = enemy_name.len().min(ENTRY_SLUG_N);
    j.entries[idx].slug[..sn].copy_from_slice(&enemy_name[..sn]);
    j.entries[idx].slug_n = sn as u8;
    // Text: "Defeated in N turns"
    let mut txt = [0u8; ENTRY_TEXT_N];
    let pfx = b"Defeated in ";
    txt[..pfx.len()].copy_from_slice(pfx);
    let mut n = pfx.len();
    let mut tmp = [0u8; 10]; let tn = write_u32(&mut tmp, turns);
    txt[n..n+tn].copy_from_slice(&tmp[..tn]); n += tn;
    let sfx = b" turns";
    txt[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
    j.entries[idx].text[..n].copy_from_slice(&txt[..n]);
    j.entries[idx].text_n = n as u8;
    j.entries[idx].turn = j.game_turn;
    j.count += 1;
}

pub fn add_note(text: &[u8]) {
    let j = journal();
    if j.count >= MAX_ENTRIES { j.shift(); }
    let idx = j.count;
    j.entries[idx].kind = EntryKind::Note;
    j.entries[idx].slug_n = 0;
    let tn = text.len().min(ENTRY_TEXT_N);
    j.entries[idx].text[..tn].copy_from_slice(&text[..tn]);
    j.entries[idx].text_n = tn as u8;
    j.entries[idx].turn = j.game_turn;
    j.count += 1;
}

pub fn advance_turn() {
    journal().game_turn = journal().game_turn.wrapping_add(1);
}

// ── Journal impl ──────────────────────────────────────────────────────────────

impl Journal {
    pub fn open(&mut self, rule_y: u32) {
        self.rule_y   = rule_y;
        self.exited   = false;
        self.expanded = false;
        self.authoring = false;
        if self.count > 0 { self.cursor = self.count - 1; } // most recent first
    }

    pub fn exited(&self) -> bool { self.exited }

    fn shift(&mut self) {
        // Drop oldest entry when full.
        for i in 0..MAX_ENTRIES - 1 { self.entries[i] = self.entries[i + 1]; }
        self.count = MAX_ENTRIES - 1;
    }

    pub fn handle_key(&mut self, key: Key) {
        if self.authoring {
            match key {
                Key::Char(c) if c >= 0x20 && c < 0x7F && self.note_n < ENTRY_TEXT_N - 1 => {
                    self.note_buf[self.note_n] = c; self.note_n += 1;
                }
                Key::Backspace => { if self.note_n > 0 { self.note_n -= 1; } }
                Key::Enter => {
                    add_note(&self.note_buf[..self.note_n]);
                    self.note_n   = 0;
                    self.authoring = false;
                    if self.count > 0 { self.cursor = self.count - 1; }
                }
                Key::Escape => { self.authoring = false; self.note_n = 0; }
                _ => {}
            }
            return;
        }
        match key {
            Key::Up   => { if self.cursor > 0 { self.cursor -= 1; self.expanded = false; } }
            Key::Down => {
                if self.count > 0 && self.cursor + 1 < self.count {
                    self.cursor += 1; self.expanded = false;
                }
            }
            Key::Enter | Key::Char(b' ') => { self.expanded = !self.expanded; }
            Key::Char(b'n') | Key::Char(b'N') => {
                self.authoring = true; self.note_n = 0;
            }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let w   = gpu.width();
        let top = self.rule_y + 8;
        it.fill(0, top, w, gpu.height().saturating_sub(top), t.bg);

        it.text(40, top + 4, "Journal", 2, t.header);

        if self.authoring {
            it.text(40, top + 32, "New note:", 1, t.accent);
            let s = core::str::from_utf8(&self.note_buf[..self.note_n]).unwrap_or("");
            it.text(40, top + 48, s, 1, t.text);
            it.text(40, top + 64, "[Enter]=save  Esc=cancel", 1, t.text_dim);
            return;
        }

        if self.count == 0 {
            it.text(40, top + 32, "(no entries yet)", 1, t.text_dim);
        } else {
            const VISIBLE: usize = 12;
            let start = if self.cursor >= VISIBLE { self.cursor + 1 - VISIBLE } else { 0 };
            let end   = (start + VISIBLE).min(self.count);
            for i in start..end {
                let e   = &self.entries[i];
                let sel = i == self.cursor;
                let col = if sel { t.accent } else { t.text };
                let y   = top + 32 + (i - start) as u32 * 14;
                let tag = e.kind.tag();
                it.text(40, y, tag, 1, if sel { t.accent } else { t.text_dim });
                if e.slug_n > 0 {
                    let s = core::str::from_utf8(&e.slug[..e.slug_n as usize]).unwrap_or("?");
                    it.text(92, y, s, 1, col);
                }
                if sel && self.expanded {
                    let txt = core::str::from_utf8(&e.text[..e.text_n as usize]).unwrap_or("");
                    it.text(52, y + 14, txt, 1, t.text_dim);
                }
            }
        }
        let cy = top + 32 + ENTRY_TEXT_N as u32 + 8;
        it.text(40, cy, "[N]=new note  Enter=expand  Esc=back", 1, t.text_dim);
    }

    // ── Persist / Load ────────────────────────────────────────────────────────
    // Format: "JN01" + u8 count + entries (slug_n + slug + text_n + text + u32 turn + u8 kind)

    pub fn save(&self) {
        const SZ: usize = 4 + 1 + MAX_ENTRIES * (1 + ENTRY_SLUG_N + 1 + ENTRY_TEXT_N + 4 + 1);
        static mut BUF: [u8; SZ] = [0u8; SZ];
        let buf = unsafe { &mut BUF };
        buf[0] = b'J'; buf[1] = b'N'; buf[2] = b'0'; buf[3] = b'1';
        buf[4] = self.count as u8;
        let mut off = 5usize;
        for i in 0..self.count {
            let e = &self.entries[i];
            buf[off] = e.slug_n; off += 1;
            buf[off..off + ENTRY_SLUG_N].copy_from_slice(&e.slug); off += ENTRY_SLUG_N;
            buf[off] = e.text_n; off += 1;
            buf[off..off + ENTRY_TEXT_N].copy_from_slice(&e.text); off += ENTRY_TEXT_N;
            let t = e.turn;
            buf[off] = (t & 0xFF) as u8; buf[off+1] = ((t>>8)&0xFF) as u8;
            buf[off+2] = ((t>>16)&0xFF) as u8; buf[off+3] = ((t>>24)&0xFF) as u8; off += 4;
            buf[off] = match e.kind { EntryKind::Quest=>0, EntryKind::Combat=>1, EntryKind::Note=>2 };
            off += 1;
        }
        crate::sa::write_file(b"journal.dat", &buf[..off]);
    }

    pub fn load(&mut self) {
        const SZ: usize = 4 + 1 + MAX_ENTRIES * (1 + ENTRY_SLUG_N + 1 + ENTRY_TEXT_N + 4 + 1);
        let mut buf = [0u8; SZ];
        let n = crate::sa::read_file(b"journal.dat", &mut buf);
        if n < 5 || &buf[0..4] != b"JN01" { return; }
        let count = buf[4] as usize;
        let mut off = 5usize;
        self.count = 0;
        for i in 0..count.min(MAX_ENTRIES) {
            if off + 1 + ENTRY_SLUG_N + 1 + ENTRY_TEXT_N + 5 > n { break; }
            let slug_n = buf[off] as usize; off += 1;
            self.entries[i].slug[..ENTRY_SLUG_N].copy_from_slice(&buf[off..off+ENTRY_SLUG_N]);
            self.entries[i].slug_n = slug_n as u8; off += ENTRY_SLUG_N;
            let text_n = buf[off] as usize; off += 1;
            self.entries[i].text[..ENTRY_TEXT_N].copy_from_slice(&buf[off..off+ENTRY_TEXT_N]);
            self.entries[i].text_n = text_n as u8; off += ENTRY_TEXT_N;
            let t0=buf[off] as u32; let t1=buf[off+1] as u32;
            let t2=buf[off+2] as u32; let t3=buf[off+3] as u32;
            self.entries[i].turn = t0|(t1<<8)|(t2<<16)|(t3<<24); off += 4;
            self.entries[i].kind = match buf[off] { 0=>EntryKind::Quest, 1=>EntryKind::Combat, _=>EntryKind::Note };
            off += 1;
            self.count += 1;
        }
    }
}

fn write_u32(buf: &mut [u8], v: u32) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8;10]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}

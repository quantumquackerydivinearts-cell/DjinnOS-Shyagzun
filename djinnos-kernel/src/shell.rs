// Ko shell — interactive terminal running on the desktop floor.
//
// Coordinate 19: Ko — Experience / intuition.
// Renders below the rule line using the 8×8 bitmap font at 2× scale (16×16 px).

use crate::font;
use crate::fs::SaVolume;
use crate::mm;
use crate::virtio::{BlockDriver, GpuDriver};
use crate::byte_table;

// ── Layout constants ──────────────────────────────────────────────────────────

const SCALE:       u32 = 2;
const CHAR_W:      u32 = font::GLYPH_W * SCALE;   // 16
const CHAR_H:      u32 = font::GLYPH_H * SCALE;   // 16
const MARGIN_X:    u32 = 40;
const MARGIN_Y:    u32 = 16;   // below the rule
const COLS:        u32 = 76;
const ROWS:        u32 = 20;

// Text colour — dim Ko-gold for shell output, brighter for input
const R_DIM: u8 = 0xa0; const G_DIM: u8 = 0x78; const B_DIM: u8 = 0x38;
const R_IN:  u8 = 0xc8; const G_IN:  u8 = 0x96; const B_IN:  u8 = 0x4b;
const R_PR:  u8 = 0x80; const G_PR:  u8 = 0xd0; const B_PR:  u8 = 0x80;  // green prompt

// Floor background colour (Ta-dark)
const BG_R:  u8 = 0x10; const BG_G: u8 = 0x0c; const BG_B: u8 = 0x10;

// ── Shell state ───────────────────────────────────────────────────────────────

pub struct Shell {
    // Scrollback line buffer — simple ring
    lines:      [[u8; 80]; 22],
    line_color: [[u8; 3]; 22],   // per-line RGB
    line_len:   [u8; 22],
    next_line:  usize,

    // Current input line
    input:     [u8; 80],
    input_len: usize,

    rule_y:    u32,
    dirty:     bool,
    _frame:    u64,
}

const PROMPT: &[u8] = b"Ko > ";

impl Shell {
    pub fn new(rule_y: u32) -> Self {
        Shell {
            lines:      [[0u8; 80]; 22],
            line_color: [[R_DIM, G_DIM, B_DIM]; 22],
            line_len:   [0u8; 22],
            next_line:  0,
            input:      [0u8; 80],
            input_len:  0,
            rule_y,
            dirty:      true,
            _frame:     0,
        }
    }

    /// Print the intro banner on first draw.
    pub fn boot_banner(&mut self) {
        self.push_line(b"Ko [byte 19 \x97 Experience / intuition]", [R_IN, G_IN, B_IN]);
        let mut buf = [0u8; 80];
        let s = byte_table::symbol_count() as u32;
        let t = byte_table::BYTE_TABLE.len() as u32;
        let n = write_banner(&mut buf, t, s);
        self.push_line(&buf[..n], [R_DIM, G_DIM, B_DIM]);
        self.push_line(b"type 'help' for commands", [R_DIM, G_DIM, B_DIM]);
        self.push_line(b"", [R_DIM, G_DIM, B_DIM]);
    }

    /// Handle a decoded key event from the keyboard driver.
    pub fn handle_key(
        &mut self,
        key: crate::virtio::input::Key,
        blk: Option<&mut BlockDriver>,
        vol: Option<&SaVolume>,
    ) {
        use crate::virtio::input::Key;
        match key {
            Key::Char(c) => {
                if self.input_len < 79 {
                    self.input[self.input_len] = c;
                    self.input_len += 1;
                    self.dirty = true;
                }
            }
            Key::Backspace => {
                if self.input_len > 0 {
                    self.input_len -= 1;
                    self.dirty = true;
                }
            }
            Key::Enter => {
                // Copy input to local buffer to avoid borrow conflict
                let mut cmd_buf = [0u8; 80];
                let cmd_len = self.input_len;
                cmd_buf[..cmd_len].copy_from_slice(&self.input[..cmd_len]);

                // Echo the input line
                let mut echo = [0u8; 80];
                let plen = PROMPT.len().min(80);
                echo[..plen].copy_from_slice(&PROMPT[..plen]);
                let clen = cmd_len.min(80 - plen);
                echo[plen..plen + clen].copy_from_slice(&cmd_buf[..clen]);
                self.push_line(&echo[..plen + clen], [R_IN, G_IN, B_IN]);
                self.execute(&cmd_buf[..cmd_len], blk, vol);
                self.input_len = 0;
                self.dirty = true;
            }
        }
    }

    pub fn needs_flush(&self) -> bool { self.dirty }

    pub fn set_frame(&mut self, f: u64) {
        let _ = f;  // will render in render() below
        self._frame = f;
        self.dirty = true;
    }

    /// Render everything to the GPU framebuffer (does NOT call gpu.flush()).
    pub fn render(&mut self, gpu: &GpuDriver) {
        if !self.dirty { return; }
        self.dirty = false;

        let floor_top = self.rule_y + 4;
        let w = gpu.width;
        let h = gpu.height;

        // Clear desktop floor
        for py in floor_top..h {
            for px in 0..w {
                gpu.set_pixel(px, py, BG_B, BG_G, BG_R);
            }
        }

        // Draw scrollback lines
        let mut y = floor_top + MARGIN_Y;
        for i in 0..(self.next_line.min(ROWS as usize)) {
            let len = self.line_len[i] as usize;
            let [r, g, b] = self.line_color[i];
            font::draw_str(
                gpu, MARGIN_X, y,
                core::str::from_utf8(&self.lines[i][..len]).unwrap_or(""),
                SCALE, r, g, b,
            );
            y += CHAR_H;
        }

        // Draw prompt + current input
        let prompt_x = font::draw_str(gpu, MARGIN_X, y, "Ko > ", SCALE,
                                       R_PR, G_PR, B_PR);
        let input_str = core::str::from_utf8(&self.input[..self.input_len])
            .unwrap_or("");
        let cx = font::draw_str(gpu, prompt_x, y, input_str, SCALE,
                                 R_IN, G_IN, B_IN);

        // Cursor block
        for dy in 0..CHAR_H {
            for dx in 0..CHAR_W {
                gpu.set_pixel(cx + dx, y + dy, B_IN, G_IN, R_IN);
            }
        }

        // Frame counter — top-right of desktop floor (proves loop is alive)
        let mut fc_buf = [0u8; 12];
        let fc_len = write_u32(&mut fc_buf, (self._frame & 0xFFFFFFFF) as u32);
        let fc_str = core::str::from_utf8(&fc_buf[..fc_len]).unwrap_or("?");
        let fc_w   = fc_len as u32 * CHAR_W;
        font::draw_str(gpu,
            gpu.width - fc_w - 4,
            floor_top + 4,
            fc_str, SCALE,
            0x40, 0x40, 0x40,
        );
    }

    // ── Public output for user process stdout ─────────────────────────────────

    pub fn push_user_line(&mut self, text: &[u8]) {
        // Cyan-ish colour to distinguish user process output from shell output.
        self.push_line(text, [0x60, 0xb0, 0xe0]);
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn push_line(&mut self, text: &[u8], color: [u8; 3]) {
        if self.next_line < self.lines.len() {
            let len = text.len().min(80);
            self.lines[self.next_line][..len].copy_from_slice(&text[..len]);
            self.line_len[self.next_line]   = len as u8;
            self.line_color[self.next_line] = color;
            self.next_line += 1;
            self.dirty = true;
        }
    }

    fn execute(&mut self, cmd: &[u8], blk: Option<&mut BlockDriver>, vol: Option<&SaVolume>) {
        let cmd = trim(cmd);
        match cmd {
            b"help" => {
                self.push_line(b"commands:", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  help          show this list", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  info          system info", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  clear         clear terminal", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  ls            list files (Sa volume)", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  cat <file>    print text file contents", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ty <file>     spawn ELF as user process  (run)", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Zu            terminate user process       (kill)", [R_DIM, G_DIM, B_DIM]);
            }
            b"info" => {
                let mut buf = [0u8; 80];
                let n = write_banner(&mut buf,
                    byte_table::BYTE_TABLE.len() as u32,
                    byte_table::symbol_count() as u32);
                self.push_line(&buf[..n], [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"process: Ko (coord 19)  kernel (coord 9)",
                    [R_DIM, G_DIM, B_DIM]);
                // Heap stats
                let (free, blocks) = mm::ALLOCATOR.stats();
                let mut hbuf = [0u8; 80];
                let pfx = b"heap: ";
                let plen = pfx.len();
                hbuf[..plen].copy_from_slice(pfx);
                let mut n = plen;
                n += write_u32(&mut hbuf[n..], (free / 1024) as u32);
                let sfx = b" KiB free  blocks: ";
                hbuf[n..n + sfx.len()].copy_from_slice(sfx); n += sfx.len();
                n += write_u32(&mut hbuf[n..], blocks as u32);
                self.push_line(&hbuf[..n], [R_DIM, G_DIM, B_DIM]);

                match vol {
                    Some(v) => {
                        let mut vbuf = [0u8; 80];
                        let pfx = b"volume: Sa  files: ";
                        let plen = pfx.len();
                        vbuf[..plen].copy_from_slice(pfx);
                        let n = write_u32(&mut vbuf[plen..], v.count);
                        self.push_line(&vbuf[..plen + n], [R_DIM, G_DIM, B_DIM]);
                    }
                    None => self.push_line(b"volume: no disk", [R_DIM, G_DIM, B_DIM]),
                }
            }
            b"clear" => {
                for i in 0..self.lines.len() { self.line_len[i] = 0; }
                self.next_line = 0;
            }
            b"ls" => {
                match vol {
                    None => self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]),
                    Some(v) => {
                        if v.list().is_empty() {
                            self.push_line(b"(empty)", [R_DIM, G_DIM, B_DIM]);
                        }
                        for entry in v.list() {
                            let mut line = [0u8; 80];
                            let name = entry.name_str();
                            let nlen = name.len().min(40);
                            line[..nlen].copy_from_slice(&name[..nlen]);
                            // right-align size
                            let mut sz_buf = [0u8; 12];
                            let sz_len = write_u32(&mut sz_buf, entry.len);
                            let sz_off = 48usize.saturating_sub(sz_len);
                            if sz_off >= nlen {
                                line[sz_off..sz_off + sz_len]
                                    .copy_from_slice(&sz_buf[..sz_len]);
                                let b_sfx = b" B";
                                let boff = sz_off + sz_len;
                                line[boff..boff + 2].copy_from_slice(b_sfx);
                                self.push_line(&line[..boff + 2], [R_IN, G_IN, B_IN]);
                            } else {
                                self.push_line(&line[..nlen], [R_IN, G_IN, B_IN]);
                            }
                        }
                    }
                }
            }
            _ if cmd.starts_with(b"cat ") || cmd == b"cat" => {
                let arg = trim(if cmd.len() > 4 { &cmd[4..] } else { b"" });
                if arg.is_empty() {
                    self.push_line(b"usage: cat <filename>", [0xa0, 0x40, 0x40]);
                } else {
                    match (vol, blk) {
                        (Some(v), Some(b)) => {
                            match v.find(arg) {
                                None => {
                                    let mut msg = [0u8; 80];
                                    let pfx = b"not found: ";
                                    let plen = pfx.len();
                                    msg[..plen].copy_from_slice(pfx);
                                    let alen = arg.len().min(80 - plen);
                                    msg[plen..plen + alen].copy_from_slice(&arg[..alen]);
                                    self.push_line(&msg[..plen + alen], [0xa0, 0x40, 0x40]);
                                }
                                Some(entry) => {
                                    // Peek at the first 8 bytes to detect binary files.
                                    static mut FILE_BUF: [u8; 8192] = [0u8; 8192];
                                    let n = unsafe {
                                        v.read_file(b, entry, &mut FILE_BUF)
                                    };
                                    let data = unsafe { &FILE_BUF[..n] };
                                    // ELF magic: \x7fELF
                                    if n >= 4 && &data[..4] == b"\x7fELF" {
                                        let mut msg = [0u8; 80];
                                        let pfx = b"binary ELF  (use 'run ";
                                        msg[..pfx.len()].copy_from_slice(pfx);
                                        let alen = arg.len().min(80 - pfx.len() - 2);
                                        msg[pfx.len()..pfx.len()+alen].copy_from_slice(&arg[..alen]);
                                        let off = pfx.len() + alen;
                                        msg[off] = b')';
                                        self.push_line(&msg[..off+1], [R_DIM, G_DIM, B_DIM]);
                                    } else {
                                        // Split on newlines and push each line
                                        let mut start = 0;
                                        for (i, &byte) in data.iter().enumerate() {
                                            if byte == b'\n' || i == n - 1 {
                                                let end = if byte == b'\n' { i } else { i + 1 };
                                                let slice = &data[start..end.min(n)];
                                                let mut off = 0;
                                                while off < slice.len() {
                                                    let chunk = &slice[off..(off + 78).min(slice.len())];
                                                    self.push_line(chunk, [R_DIM, G_DIM, B_DIM]);
                                                    off += 78;
                                                }
                                                start = i + 1;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        _ => self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]),
                    }
                }
            }
            b"Zu" | b"kill" => {
                crate::process::kill_user_processes();
                self.push_line(b"Zu: user process terminated", [R_DIM, G_DIM, B_DIM]);
            }
            _ if cmd.starts_with(b"Ty ") || cmd.starts_with(b"run ") || cmd == b"Ty" || cmd == b"run" => {
                let prefix_len = if cmd.starts_with(b"Ty ") { 3 } else { 4 };
                let arg = trim(if cmd.len() > prefix_len { &cmd[prefix_len..] } else { b"" });
                if arg.is_empty() {
                    self.push_line(b"usage: run <filename>", [0xa0, 0x40, 0x40]);
                } else {
                    match (vol, blk) {
                        (Some(v), Some(b)) => {
                            match v.find(arg) {
                                None => self.push_line(b"file not found", [0xa0, 0x40, 0x40]),
                                Some(entry) => {
                                    use alloc::vec;
                                    let mut buf = vec![0u8; entry.len as usize];
                                    let n = v.read_file(b, entry, &mut buf);
                                    if n < entry.len as usize {
                                        self.push_line(b"read error", [0xa0, 0x40, 0x40]);
                                    } else if n < 4 || &buf[..4] != b"\x7fELF" {
                                        self.push_line(b"not an ELF binary", [0xa0, 0x40, 0x40]);
                                    } else {
                                        // Kill any running user process before spawning.
                                        crate::process::kill_user_processes();
                                        match crate::process::spawn_elf(19, &buf) {
                                            Some(_) => {
                                                let mut msg = [0u8; 80];
                                                let pfx = b"running: ";
                                                msg[..pfx.len()].copy_from_slice(pfx);
                                                let alen = arg.len().min(80 - pfx.len());
                                                msg[pfx.len()..pfx.len()+alen].copy_from_slice(&arg[..alen]);
                                                self.push_line(&msg[..pfx.len()+alen], [R_IN, G_IN, B_IN]);
                                            }
                                            None => self.push_line(b"spawn failed", [0xa0, 0x40, 0x40]),
                                        }
                                    }
                                }
                            }
                        }
                        _ => self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]),
                    }
                }
            }
            b"" => {}
            _ => {
                let mut msg = [0u8; 80];
                let pfx = b"unknown: ";
                let plen = pfx.len();
                msg[..plen].copy_from_slice(pfx);
                let clen = cmd.len().min(80 - plen);
                msg[plen..plen + clen].copy_from_slice(&cmd[..clen]);
                self.push_line(&msg[..plen + clen], [0xa0, 0x40, 0x40]);
            }
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn trim(s: &[u8]) -> &[u8] {
    let s = match s.iter().position(|&b| b != b' ') {
        Some(i) => &s[i..],
        None    => return b"",
    };
    match s.iter().rposition(|&b| b != b' ') {
        Some(i) => &s[..=i],
        None    => s,
    }
}

fn write_banner(buf: &mut [u8; 80], total: u32, candidates: u32) -> usize {
    // "byte table: NNN entries  NNN candidates"
    let mut i = 0;
    let pfx = b"byte table: ";
    buf[i..i + pfx.len()].copy_from_slice(pfx); i += pfx.len();
    i += write_u32(&mut buf[i..], total);
    let mid = b" entries  ";
    buf[i..i + mid.len()].copy_from_slice(mid); i += mid.len();
    i += write_u32(&mut buf[i..], candidates);
    let sfx = b" candidates";
    buf[i..i + sfx.len()].copy_from_slice(sfx); i += sfx.len();
    i
}

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { buf[0] = b'0'; return 1; }
    let mut tmp = [0u8; 10];
    let mut len = 0;
    while n > 0 { tmp[len] = b'0' + (n % 10) as u8; n /= 10; len += 1; }
    for i in 0..len { buf[i] = tmp[len - 1 - i]; }
    len
}
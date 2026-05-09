// Ko shell — interactive terminal, runs on any GpuSurface.
//
// Coordinate 19: Ko — Experience / intuition.
// Renders below the rule line using the 8×8 bitmap font at 2× scale (16×16 px).
// Works on both VirtIO GPU (RISC-V) and linear framebuffer (x86_64).

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::mm;
use crate::byte_table;


// ── Layout constants ──────────────────────────────────────────────────────────

const SCALE:    u32 = 2;
const CHAR_W:   u32 = font::GLYPH_W * SCALE;
const CHAR_H:   u32 = font::GLYPH_H * SCALE;
const MARGIN_X: u32 = 40;
const MARGIN_Y: u32 = 16;
const ROWS:     u32 = 20;

const R_DIM: u8 = 0xa0; const G_DIM: u8 = 0x78; const B_DIM: u8 = 0x38;
const R_IN:  u8 = 0xc8; const G_IN:  u8 = 0x96; const B_IN:  u8 = 0x4b;
const R_PR:  u8 = 0x80; const G_PR:  u8 = 0xd0; const B_PR:  u8 = 0x80;
const BG_R:  u8 = 0x10; const BG_G:  u8 = 0x0c; const BG_B:  u8 = 0x10;

const PROMPT: &[u8] = b"Ko > ";

// ── Shell state ───────────────────────────────────────────────────────────────

const BUF_LINES: usize = 256;

pub struct Shell {
    lines:       [[u8; 80]; BUF_LINES],
    line_color:  [[u8; 3]; BUF_LINES],
    line_len:    [u8; BUF_LINES],
    next_line:   usize,
    view_offset: usize,   // lines scrolled up from bottom; 0 = follow tail
    input:       [u8; 80],
    input_len:   usize,
    rule_y:      u32,
    dirty:       bool,
    _frame:      u64,
}

impl Shell {
    pub fn new(rule_y: u32) -> Self {
        Shell {
            lines:       [[0u8; 80]; BUF_LINES],
            line_color:  [[R_DIM, G_DIM, B_DIM]; BUF_LINES],
            line_len:    [0u8; BUF_LINES],
            next_line:   0,
            view_offset: 0,
            input:       [0u8; 80],
            input_len:   0,
            rule_y,
            dirty:       true,
            _frame:      0,
        }
    }

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

    // ── Key dispatch — RISC-V variant ────────────────────────────────────────
    //
    // blk/vol are now in static VFS storage; the shell accesses them via
    // crate::vfs directly rather than through borrowed references.

    #[cfg(target_arch = "riscv64")]
    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Char(c) => {
                if self.input_len < 79 {
                    self.input[self.input_len] = c;
                    self.input_len += 1;
                    self.dirty = true;
                }
            }
            Key::Backspace => {
                if self.input_len > 0 { self.input_len -= 1; self.dirty = true; }
            }
            Key::Enter => self.commit_and_execute_rv(),
            _          => {}   // Up/Down/Left/Right/Escape handled by main loop
        }
    }

    // ── Key dispatch — x86_64 variant (no filesystem yet) ────────────────────

    #[cfg(not(target_arch = "riscv64"))]
    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Char(c) => {
                if self.input_len < 79 {
                    self.input[self.input_len] = c;
                    self.input_len += 1;
                    self.dirty = true;
                }
            }
            Key::Backspace => {
                if self.input_len > 0 { self.input_len -= 1; self.dirty = true; }
            }
            Key::Enter => self.commit_and_execute_x86(),
            Key::Up    => {
                self.view_offset = (self.view_offset + 1).min(self.next_line.saturating_sub(1));
                self.dirty = true;
            }
            Key::Down  => {
                self.view_offset = self.view_offset.saturating_sub(1);
                self.dirty = true;
            }
            _          => {}
        }
    }

    pub fn needs_flush(&self) -> bool { self.dirty }

    pub fn set_frame(&mut self, f: u64) {
        self._frame = f;
        self.dirty = true;
    }

    /// Render to any GpuSurface.  Does NOT call gpu.flush().
    pub fn render(&self, gpu: &dyn GpuSurface) {
        if !self.dirty { return; }

        let floor_top = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();

        gpu.fill_rect(0, floor_top, w, h.saturating_sub(floor_top), BG_B, BG_G, BG_R);

        // Compute the visible window into the line buffer.
        // view_offset=0 → show the most recent ROWS lines.
        let rows    = ROWS as usize;
        let end     = self.next_line.saturating_sub(self.view_offset);
        let start   = end.saturating_sub(rows);

        // Scroll indicator: dim "^" when there is history above.
        if start > 0 {
            font::draw_str(gpu, MARGIN_X, floor_top + 2, "^", SCALE,
                           0x40, 0x40, 0x50);
        }

        let mut y = floor_top + MARGIN_Y;
        for i in start..end {
            let len = self.line_len[i] as usize;
            let [r, g, b] = self.line_color[i];
            font::draw_str(
                gpu, MARGIN_X, y,
                core::str::from_utf8(&self.lines[i][..len]).unwrap_or(""),
                SCALE, r, g, b,
            );
            y += CHAR_H;
        }

        let prompt_x = font::draw_str(gpu, MARGIN_X, y, "Ko > ", SCALE, R_PR, G_PR, B_PR);
        let input_str = core::str::from_utf8(&self.input[..self.input_len]).unwrap_or("");
        let cx = font::draw_str(gpu, prompt_x, y, input_str, SCALE, R_IN, G_IN, B_IN);

        gpu.fill_rect(cx, y, CHAR_W, CHAR_H, B_IN, G_IN, R_IN);

        let mut fc_buf = [0u8; 12];
        let fc_len = write_u32(&mut fc_buf, (self._frame & 0xFFFFFFFF) as u32);
        let fc_str = core::str::from_utf8(&fc_buf[..fc_len]).unwrap_or("?");
        let fc_w   = fc_len as u32 * CHAR_W;
        font::draw_str(gpu, w - fc_w - 4, floor_top + 4, fc_str, SCALE, 0x40, 0x40, 0x40);
    }

    pub fn push_user_line(&mut self, text: &[u8]) {
        self.push_line(text, [0x60, 0xb0, 0xe0]);
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn push_line(&mut self, text: &[u8], color: [u8; 3]) {
        if self.next_line >= BUF_LINES {
            // Shift buffer up by one, dropping the oldest line.
            for i in 0..BUF_LINES - 1 {
                self.lines[i]      = self.lines[i + 1];
                self.line_len[i]   = self.line_len[i + 1];
                self.line_color[i] = self.line_color[i + 1];
            }
            self.next_line = BUF_LINES - 1;
        }
        let len = text.len().min(80);
        self.lines[self.next_line][..len].copy_from_slice(&text[..len]);
        self.line_len[self.next_line]   = len as u8;
        self.line_color[self.next_line] = color;
        self.next_line += 1;
        // New content arrives → jump to tail unless the user pinned scroll.
        if self.view_offset > 0 { self.view_offset = self.view_offset.saturating_sub(1); }
        self.dirty = true;
    }

    #[cfg(target_arch = "riscv64")]
    fn commit_and_execute_rv(&mut self) {
        let mut cmd_buf = [0u8; 80];
        let cmd_len = self.input_len;
        cmd_buf[..cmd_len].copy_from_slice(&self.input[..cmd_len]);
        self.echo_input();
        self.execute_rv(&cmd_buf[..cmd_len]);
        self.input_len = 0;
        self.dirty = true;
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn commit_and_execute_x86(&mut self) {
        let mut cmd_buf = [0u8; 80];
        let cmd_len = self.input_len;
        cmd_buf[..cmd_len].copy_from_slice(&self.input[..cmd_len]);
        self.echo_input();
        self.execute_x86(&cmd_buf[..cmd_len]);
        self.input_len = 0;
        self.dirty = true;
    }

    fn echo_input(&mut self) {
        let cmd_len = self.input_len;
        let mut echo = [0u8; 80];
        let plen = PROMPT.len().min(80);
        echo[..plen].copy_from_slice(&PROMPT[..plen]);
        let clen = cmd_len.min(80 - plen);
        echo[plen..plen + clen].copy_from_slice(&self.input[..clen]);
        self.push_line(&echo[..plen + clen], [R_IN, G_IN, B_IN]);
    }

    // ── Command executor — RISC-V (full feature set) ──────────────────────────
    //
    // Primary commands use Shygazun glyphs that match the byte table exactly.
    // English aliases are kept for ergonomics during the transition.

    #[cfg(target_arch = "riscv64")]
    fn execute_rv(&mut self, cmd: &[u8]) {
        let cmd = trim(cmd);
        let (verb, rest) = split_verb(cmd);

        match verb {
            // ── Meta ──────────────────────────────────────────────────────────
            b"help" | b"Sha" => {
                // Sha = byte 15 — Intellect of spirit
                self.push_line(b"Ko shell  [glyphs / English alias]", [R_IN, G_IN, B_IN]);
                self.push_line(b"  Sha / help         this list", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  info               system + eigenstate", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ze                 clear terminal", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Seth / ls          directory listing", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Sao <file>  / cat  read file (.ko files are evaluated)", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Kobra <expr>       evaluate a Kobra expression", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ty <file>          spawn ELF process", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Zu                 terminate process", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Kael               heap stats", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Myr / net          network status", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Myrun <path>       GET 10.0.2.2:9000/<path>", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Myrun :<port>/<p>  GET 10.0.2.2:<port>/<p>", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ko                 eigenstate summary", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  klgs [zone_id]     launch Ko's Labyrinth world view", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  www <url>          open Faerie Browser", [R_DIM, G_DIM, B_DIM]);
            }

            b"info" => self.cmd_info(),

            // ── Ze = byte 20 — There / far: reach toward void → clear ─────────
            b"Ze" | b"clear" => {
                for i in 0..self.lines.len() { self.line_len[i] = 0; }
                self.next_line   = 0;
                self.view_offset = 0;
            }

            // ── Seth = byte 159 — Platter / directory / bundle ───────────────
            b"Seth" | b"ls" => self.cmd_ls(),

            // ── Sao = byte 157 — Cup / file / persistent object ──────────────
            b"Sao" | b"cat" => {
                if rest.is_empty() {
                    self.push_line(b"Sao: need filename", [0xa0, 0x40, 0x40]);
                } else {
                    self.cmd_cat_arg(rest);
                }
            }

            // ── Zu = byte 1 — Earth Terminator: kill ──────────────────────────
            b"Zu" | b"kill" => {
                crate::process::kill_user_processes();
                self.push_line(b"Zu \x97 empirical closure / process terminated", [R_DIM, G_DIM, B_DIM]);
            }

            // ── Ty = byte 0 — Earth Initiator: spawn ─────────────────────────
            b"Ty" | b"run" => self.cmd_run_arg(rest),

            // ── Kael = byte 82 — Cluster / Fruit / Flower: heap stats ─────────
            b"Kael" => self.cmd_heap(),

            // ── Myr = byte 164 — Procession path / route: network status ────────
            b"Myr" | b"net" => self.cmd_net_rv(),

            // ── Myrun = byte 169 — Sacred march / stream: HTTP client ────────────
            // Myrun /path                → GET 10.0.2.2:9000/path  (Atelier API)
            // Myrun :8000/path           → GET 10.0.2.2:8000/path  (kernel HTTP)
            // Myrun <ip>:<port>/<path>   → explicit
            b"Myrun" | b"fetch" => self.cmd_myrun(rest),

            // ── Ko = byte 19 — Experience / intuition: eigenstate display ──────
            b"Ko" | b"eigenstate" => self.cmd_eigenstate_rv(),

            // ── klgs — launch Ko's Labyrinth world view ───────────────────────
            b"klgs" => {
                let zone = if rest.is_empty() {
                    crate::world::default_zone()
                } else {
                    rest
                };
                self.push_line(b"Launching Ko's Labyrinth...", [R_IN, G_IN, B_IN]);
                let mut zn = [0u8; 48];
                let n = zone.len().min(47);
                zn[..n].copy_from_slice(&zone[..n]);
                {
                    let mut b2 = [0u8; 80];
                    let pre = b"zone: ";
                    b2[..pre.len()].copy_from_slice(pre);
                    b2[pre.len()..pre.len() + n].copy_from_slice(&zn[..n]);
                    self.push_line(&b2[..pre.len() + n], [R_DIM, G_DIM, B_DIM]);
                }
                crate::world::request_launch(&zn[..n]);
                if crate::world::world().playing {
                    self.push_line(b"Zone loaded. Entering world...", [R_PR, G_PR, B_PR]);
                } else {
                    self.push_line(b"klgs: failed (is Atelier API running on :9000?)", [0xa0, 0x40, 0x40]);
                }
            }

            // ── www — Faerie Browser ─────────────────────────────────────────
            b"www" => {
                if rest.is_empty() {
                    self.push_line(b"www: usage: www http://example.com/", [0xa0, 0x40, 0x40]);
                } else {
                    self.push_line(b"Launching Faerie Browser...", [R_IN, G_IN, B_IN]);
                    crate::browser::request_launch(rest);
                }
            }

            // ── Kobra — inline Shygazun expression evaluator ─────────────────
            b"Kobra" => {
                if rest.is_empty() {
                    self.push_line(b"Kobra: usage: Kobra <expr>  e.g. Kobra [Ko Sha]", [0xa0, 0x40, 0x40]);
                } else {
                    let result = crate::kobra::eval_expr(rest);
                    if result.line_count() == 0 {
                        self.push_line(b"Kobra: (empty)", [R_DIM, G_DIM, B_DIM]);
                    } else {
                        for i in 0..result.line_count() {
                            self.push_line(result.line(i), [R_DIM, G_DIM, B_DIM]);
                        }
                    }
                }
            }

            b"" => {}
            _ => self.unknown_cmd(cmd),
        }
    }

    // ── Command executor — x86_64 ─────────────────────────────────────────────
    //
    // Glyph-native names are primary; English names alias to the same handler.

    #[cfg(not(target_arch = "riscv64"))]
    fn execute_x86(&mut self, cmd: &[u8]) {
        let cmd = trim(cmd);
        let (verb, rest) = split_verb(cmd);

        match verb {
            // ── Meta ──────────────────────────────────────────────────────────
            b"help" | b"Sha" => {
                self.push_line(b"Ko shell  [glyphs / English alias]", [R_IN, G_IN, B_IN]);
                self.push_line(b"  Sha / help               this list",     [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  info                     system + eigenstate", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ze / clear               clear terminal",[R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ro / pci                 PCI devices",   [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Zot / acpi               ACPI tables",   [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Si / date                date/time",     [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Shak / audio             HDA codec",     [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Shak <hz> / beep <hz>   play tone",     [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Zo / mute                stop audio",    [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Mel / battery            battery status",[R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Kael                     heap stats",    [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Ko / eigenstate          eigenstate",    [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Seth / ls                list files",    [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Sao <file> / cat <file>  read file (.ko evaluated)", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  tiler                    byte table structural map", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  edit <file> / Yew        open file editor", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Kobra                    open Kobra REPL", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  Kobra <expr>             evaluate Kobra expression", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  ec [NN]                  EC register",   [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  dsdt                     DSDT bytes",    [R_DIM, G_DIM, B_DIM]);
            }

            b"info" => self.cmd_info_bare(),

            // ── Ze = byte 20 — There / far → clear ──────────────────────────
            b"Ze" | b"clear" => {
                for i in 0..self.lines.len() { self.line_len[i] = 0; }
                self.next_line   = 0;
                self.view_offset = 0;
            }

            // ── Ro = byte 83 — Ion-channel / Gate / Receptor → PCI ───────────
            b"Ro" | b"pci" => self.cmd_pci(),

            // ── Zot = byte 107 — Earth → ACPI hardware structure ─────────────
            b"Zot" | b"acpi" => self.cmd_acpi(),

            // ── Si = byte 142 — Linear time → date/time ──────────────────────
            b"Si" | b"date" => self.cmd_date(),

            // ── Shak = byte 104 — Fire → audio / tone ────────────────────────
            b"Shak" | b"audio" if rest.is_empty() => self.cmd_audio(),
            b"Shak" | b"beep" => {
                let freq_arg: u32 = parse_u32(rest).unwrap_or(440);
                self.cmd_beep_freq(freq_arg);
            }

            // ── Zo = byte 16 — Absence → mute / stop ─────────────────────────
            b"Zo" | b"mute" => self.cmd_mute(),

            // ── Mel = byte 106 — Water → battery / flowing charge ────────────
            b"Mel" | b"battery" => self.cmd_battery(),

            // ── Kael = byte 82 — Cluster → heap stats ────────────────────────
            b"Kael" => self.cmd_heap(),

            // ── Ko = byte 19 — Experience → eigenstate display ───────────────
            b"Ko" | b"eigenstate" => self.cmd_eigenstate_x86(),

            // ── Seth = byte 159 — Platter / directory → ramdisk listing ──────
            b"Seth" | b"ls" => {
                let n = crate::ramdisk::file_count();
                if n == 0 {
                    self.push_line(b"ramdisk: empty (put files in USB root)", [R_DIM, G_DIM, B_DIM]);
                } else {
                    for i in 0..n {
                        if let Some(f) = crate::ramdisk::get(i) {
                            let nm = f.name;
                            let mut buf = [b' '; 60];
                            let nl = nm.len().min(40);
                            buf[..nl].copy_from_slice(&nm[..nl]);
                            let mut sz_buf = [0u8; 12];
                            let sz_len = write_u32(&mut sz_buf, f.data.len() as u32);
                            let sz_str = &sz_buf[..sz_len];
                            let offset = 42;
                            let sl = sz_len.min(60 - offset);
                            buf[offset..offset+sl].copy_from_slice(&sz_str[..sl]);
                            self.push_line(&buf[..offset+sl], [R_DIM, G_DIM, B_DIM]);
                        }
                    }
                }
            }

            // ── Sao = byte 157 — Cup / persistent object → read ramdisk file ─
            b"Sao" | b"cat" => {
                if rest.is_empty() {
                    self.push_line(b"Sao: need filename", [0xa0, 0x40, 0x40]);
                } else {
                    match crate::ramdisk::find(rest) {
                        None => {
                            let mut b = [0u8; 80];
                            let pfx = b"Sao: not found: ";
                            b[..pfx.len()].copy_from_slice(pfx);
                            let n = rest.len().min(80 - pfx.len());
                            b[pfx.len()..pfx.len()+n].copy_from_slice(&rest[..n]);
                            self.push_line(&b[..pfx.len()+n], [0xa0, 0x40, 0x40]);
                        }
                        Some(data) => {
                            // .ko files are Kobra source — evaluate rather than print.
                            if rest.ends_with(b".ko") {
                                let result = crate::kobra::eval_file(data);
                                if result.line_count() == 0 {
                                    self.push_line(b"(no output)", [R_DIM, G_DIM, B_DIM]);
                                } else {
                                    for i in 0..result.line_count() {
                                        self.push_line(result.line(i), [R_DIM, G_DIM, B_DIM]);
                                    }
                                }
                            } else {
                                let mut start = 0;
                                while start < data.len() {
                                    let end = data[start..].iter()
                                        .position(|&b| b == b'\n')
                                        .map(|p| start + p)
                                        .unwrap_or(data.len());
                                    self.push_line(&data[start..end.min(start+79)], [R_IN, G_IN, B_IN]);
                                    start = if end < data.len() { end + 1 } else { data.len() };
                                }
                            }
                        }
                    }
                }
            }

            // ── Kobra — REPL (no args) or inline eval ────────────────────────
            b"Kobra" => {
                if rest.is_empty() {
                    crate::kobra_repl::request();
                    self.push_line(b"Entering Kobra REPL...", [R_IN, G_IN, B_IN]);
                } else {
                    let result = crate::kobra::eval_expr(rest);
                    if result.line_count() == 0 {
                        self.push_line(b"Kobra: (empty)", [R_DIM, G_DIM, B_DIM]);
                    } else {
                        for i in 0..result.line_count() {
                            self.push_line(result.line(i), [R_DIM, G_DIM, B_DIM]);
                        }
                    }
                }
            }

            // ── tiler — byte table structural map ────────────────────────────
            b"tiler" => {
                crate::tiler::request();
                self.push_line(b"Opening Shygazun ledger tiler...", [R_IN, G_IN, B_IN]);
            }

            // ── edit — file editor ────────────────────────────────────────────
            b"edit" | b"Yew" => {
                if rest.is_empty() {
                    self.push_line(b"edit: usage: edit <filename>", [0xa0, 0x40, 0x40]);
                } else {
                    crate::editor::request(rest);
                    let mut msg = [0u8; 80];
                    let pfx = b"Opening ";
                    msg[..pfx.len()].copy_from_slice(pfx);
                    let n = rest.len().min(80 - pfx.len());
                    msg[pfx.len()..pfx.len() + n].copy_from_slice(&rest[..n]);
                    self.push_line(&msg[..pfx.len() + n], [R_IN, G_IN, B_IN]);
                }
            }

            // ── Legacy diagnostic commands (kept unglyph'd) ───────────────────
            _ if verb == b"ec" => self.cmd_ec(cmd),
            b"dsdt" => self.cmd_dsdt(),

            b"" => {}
            _ => self.unknown_cmd(cmd),
        }
    }

    // ── Network status — RISC-V ───────────────────────────────────────────────

    #[cfg(target_arch = "riscv64")]
    fn cmd_net_rv(&mut self) {
        match crate::net::info() {
            None => self.push_line(b"Myr: no network (add -device virtio-net-device)", [0xa0, 0x40, 0x40]),
            Some(i) => {
                // MAC line
                let mut b = [0u8; 80]; let mut n = 0;
                let lbl = b"MAC: "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                for (k, &byte) in i.mac.iter().enumerate() {
                    if k > 0 { b[n] = b':'; n += 1; }
                    b[n]   = hex_hi(byte); b[n+1] = hex_lo(byte); n += 2;
                }
                self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
                // IP line
                let mut b = [0u8; 80]; let mut n = 0;
                let lbl = b"IP:  "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                for (k, &oct) in i.ip.iter().enumerate() {
                    if k > 0 { b[n] = b'.'; n += 1; }
                    n += write_u32(&mut b[n..], oct as u32);
                }
                let sfx = b"/24  gw 10.0.2.2";
                b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
                // HTTP line
                let mut b = [0u8; 80]; let mut n = 0;
                let lbl = b"HTTP: port "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                n += write_u32(&mut b[n..], i.http_port as u32);
                let sfx = b"  (host: curl http://localhost:8080/)";
                b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
            }
        }
    }

    // ── Myrun — HTTP client (byte 169: Sacred march / stream) ────────────────

    #[cfg(target_arch = "riscv64")]
    fn cmd_myrun(&mut self, arg: &[u8]) {
        if arg.is_empty() {
            self.push_line(b"Myrun: usage: Myrun /path  or  Myrun :port/path", [0xa0, 0x40, 0x40]);
            return;
        }

        // Parse target: extract (ip, port, path_slice).
        let (ip, port, path) = myrun_parse_target(arg);

        // ── 1. Allocate socket ────────────────────────────────────────────────
        let fd = crate::net::tcp_socket(0);
        if fd == u64::MAX {
            self.push_line(b"Myrun: no network stack (add virtio-net-device)", [0xa0, 0x40, 0x40]);
            return;
        }

        // ── 2. Initiate TCP connect ───────────────────────────────────────────
        if crate::net::tcp_connect(fd, ip, port) == 0 {
            self.push_line(b"Myrun: connect failed (is the server running?)", [0xa0, 0x40, 0x40]);
            crate::net::tcp_close(fd);
            return;
        }

        // Show what we're connecting to.
        {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b">> GET "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            for (k, &o) in ip.iter().enumerate() {
                if k > 0 { b[n] = b'.'; n += 1; }
                n += write_u32(&mut b[n..], o as u32);
            }
            b[n] = b':'; n += 1;
            n += write_u32(&mut b[n..], port as u32);
            let plen = path.len().min(80 - n);
            b[n..n + plen].copy_from_slice(&path[..plen]); n += plen;
            self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
        }

        // ── 3. Poll until ESTABLISHED (≤ 2000 iterations ≈ instant on SLIRP) ─
        let mut ok = false;
        for _ in 0..2000 {
            crate::net::poll();
            if crate::net::tcp_ready(fd) { ok = true; break; }
        }
        if !ok {
            self.push_line(b"Myrun: connection timeout", [0xa0, 0x40, 0x40]);
            crate::net::tcp_close(fd);
            return;
        }

        // ── 4. Send HTTP/1.0 GET ──────────────────────────────────────────────
        let mut req = [0u8; 512];
        let req_len = myrun_build_get(&mut req, path, ip, port);
        crate::net::tcp_send(fd, &req[..req_len]);
        crate::net::poll();

        // ── 5. Read response (retry until data stops flowing) ────────────────
        static mut RBUF: [u8; 16384] = [0u8; 16384];
        let mut total = 0usize;
        let mut idle  = 0usize;
        loop {
            crate::net::poll();
            let n = crate::net::tcp_recv(fd, unsafe { &mut RBUF[total..] });
            total += n;
            if n == 0 { idle += 1; } else { idle = 0; }
            if total >= unsafe { RBUF.len() } || idle > 300 { break; }
        }
        crate::net::tcp_close(fd);

        if total == 0 {
            self.push_line(b"Myrun: empty response", [0xa0, 0x40, 0x40]);
            return;
        }

        // ── 6. Display: status line + body ────────────────────────────────────
        let resp = unsafe { &RBUF[..total] };
        self.myrun_display(resp, total);
    }

    #[cfg(target_arch = "riscv64")]
    fn myrun_display(&mut self, resp: &[u8], total: usize) {
        // Locate the header/body separator: \r\n\r\n
        let body_start = resp.windows(4)
            .position(|w| w == b"\r\n\r\n")
            .map(|i| i + 4)
            .unwrap_or(0);

        // Show HTTP status line (first line of response).
        if let Some(end) = resp.iter().position(|&b| b == b'\r') {
            let status_line = &resp[..end.min(78)];
            let color = if resp.get(9..12) == Some(b"200") {
                [0x50u8, 0xd0u8, 0x50u8]   // green for 200
            } else {
                [0xa0u8, 0x50u8, 0x50u8]   // red for 4xx/5xx
            };
            self.push_line(status_line, color);
        }

        // Show "N bytes" summary.
        {
            let mut b = [0u8; 80]; let mut n = 0;
            let pfx = b"   "; b[..pfx.len()].copy_from_slice(pfx); n = pfx.len();
            n += write_u32(&mut b[n..], total as u32);
            let sfx = b" B received  body:";
            b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }

        // Display up to 14 lines of body (78 chars each).
        let body = &resp[body_start..];
        let mut pos   = 0usize;
        let mut lines = 0usize;
        while pos < body.len() && lines < 14 {
            // Advance past whitespace-only lines to find something useful.
            let start = pos;
            let end = body[pos..].iter()
                .position(|&b| b == b'\n')
                .map(|i| pos + i)
                .unwrap_or(body.len());
            let raw = &body[start..end];
            // Strip trailing \r
            let line = raw.strip_suffix(b"\r").unwrap_or(raw);
            pos = (end + 1).min(body.len());
            if line.is_empty() { continue; }

            // Chunk long lines at 78 chars.
            let mut off = 0;
            while off < line.len() && lines < 14 {
                let chunk = &line[off..(off + 78).min(line.len())];
                self.push_line(chunk, [R_DIM, G_DIM, B_DIM]);
                off += 78;
                lines += 1;
            }
        }

        // Show truncation notice if we hit the limit.
        if pos < body.len() {
            let mut b = [0u8; 80]; let mut n = 0;
            let pfx = b"   ... (";
            b[..pfx.len()].copy_from_slice(pfx); n = pfx.len();
            n += write_u32(&mut b[n..], (body.len() - pos) as u32);
            let sfx = b" B more)";
            b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
    }

    // ── Eigenstate display — RISC-V ───────────────────────────────────────────

    #[cfg(target_arch = "riscv64")]
    fn cmd_eigenstate_rv(&mut self) {
        use crate::eigenstate;
        self.push_line(b"eigenstate [tongue : invocations]", [R_IN, G_IN, B_IN]);
        let names: &[(&[u8], u8)] = &[
            (b"Lotus(1)", 1), (b"Rose(2)", 2), (b"Sakura(3)", 3),
            (b"Daisy(4)", 4), (b"AppleBlossom(5)", 5), (b"Aster(6)", 6),
            (b"Grapevine(7)", 7), (b"Cannabis(8)", 8),
        ];
        for (name, t) in names {
            let count = eigenstate::read(*t);
            if count == 0 { continue; }
            let mut b = [b' '; 80]; let mut n = 0;
            b[n] = b' '; n += 1;
            let nl = name.len(); b[n..n+nl].copy_from_slice(name); n += nl;
            b[n] = b':'; b[n+1] = b' '; n += 2;
            n += write_u32(&mut b[n..], count as u32);
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
        let total = eigenstate::total();
        let mut b = [b' '; 80]; let mut n = 0;
        let lbl = b"total: "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
        n += write_u32(&mut b[n..], total as u32);
        self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
    }

    // ── Eigenstate display — x86_64 ───────────────────────────────────────────

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_eigenstate_x86(&mut self) {
        use crate::eigenstate;
        self.push_line(b"eigenstate  [no ecalls on x86 yet]", [R_IN, G_IN, B_IN]);
        let total = eigenstate::total();
        let mut b = [b' '; 80]; let mut n = 0;
        let lbl = b"total: "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
        n += write_u32(&mut b[n..], total as u32);
        self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
    }

    // ── Heap stats (both arches) ──────────────────────────────────────────────

    fn cmd_heap(&mut self) {
        let (free, blocks) = mm::ALLOCATOR.stats();
        let mut b = [b' '; 80]; let mut n = 0;
        let lbl = b"Kael cluster: "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
        n += write_u32(&mut b[n..], (free / 1024) as u32);
        let mid = b" KiB free  blocks: "; b[n..n+mid.len()].copy_from_slice(mid); n += mid.len();
        n += write_u32(&mut b[n..], blocks as u32);
        self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
    }


    // ── Shak beep with parsed frequency ──────────────────────────────────────

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_beep_freq(&mut self, freq: u32) {
        match crate::hda::get() {
            None => { self.push_line(b"HDA: no controller", [0xa0, 0x40, 0x40]); }
            Some(d) => {
                d.play_tone(freq);
                let mut b = [b' '; 80]; let mut n = 0;
                let lbl = b"Shak: "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                n += write_u32(&mut b[n..], freq);
                let sfx = b" Hz"; b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
            }
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_pci(&mut self) {
        use crate::pci;
        let n = pci::count();
        if n == 0 {
            self.push_line(b"no PCI devices found", [0xa0, 0x40, 0x40]);
            return;
        }
        for slot in pci::devices() {
            if let Some(ref d) = slot {
                // Format: "BB:DD.F  VVVV:DDDD  CC  description"
                let mut line = [b' '; 80];
                let mut i = 0;
                // bus:dev.func
                line[i] = hex_hi(d.bus);  i += 1;
                line[i] = hex_lo(d.bus);  i += 1;
                line[i] = b':';           i += 1;
                line[i] = hex_hi(d.dev);  i += 1;
                line[i] = hex_lo(d.dev);  i += 1;
                line[i] = b'.';           i += 1;
                line[i] = b'0' + d.func;  i += 1;
                line[i] = b' '; line[i+1] = b' '; i += 2;
                // vendor:device
                i = put_hex16(&mut line, i, d.vendor);
                line[i] = b':'; i += 1;
                i = put_hex16(&mut line, i, d.device);
                line[i] = b' '; line[i+1] = b' '; i += 2;
                // class.sub
                i = put_hex8(&mut line, i, d.class);
                line[i] = b':'; i += 1;
                i = put_hex8(&mut line, i, d.sub);
                line[i] = b' '; line[i+1] = b' '; i += 2;
                // description
                let desc = pci::class_name(d.class, d.sub).as_bytes();
                let dlen = desc.len().min(80 - i);
                line[i..i+dlen].copy_from_slice(&desc[..dlen]);
                i += dlen;
                self.push_line(&line[..i], [R_IN, G_IN, B_IN]);
            }
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_acpi(&mut self) {
        use crate::acpi;
        let i = acpi::get();
        if i.rsdp_addr == 0 {
            self.push_line(b"ACPI: not found", [0xa0, 0x40, 0x40]);
            return;
        }

        // RSDP line
        {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"RSDP @ 0x"; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, i.rsdp_addr);
            self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
        }
        // XSDT / RSDT
        {
            let mut b = [b' '; 80]; let mut n = 0;
            let (lbl, addr) = if i.xsdt_addr != 0 {
                (&b"XSDT @ 0x"[..], i.xsdt_addr)
            } else {
                (&b"RSDT @ 0x"[..], i.rsdt_addr)
            };
            b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, addr);
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
        // FADT / DSDT
        if i.fadt_addr != 0 {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"FADT @ 0x"; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, i.fadt_addr);
            if i.dsdt_addr != 0 {
                let d = b"  DSDT @ 0x"; b[n..n+d.len()].copy_from_slice(d); n += d.len();
                n = put_hex64(&mut b, n, i.dsdt_addr);
            }
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
        // MCFG / ECAM
        if i.ecam_base != 0 {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"ECAM @ 0x"; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, i.ecam_base);
            let sfx = b"  bus "; b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
            b[n] = b'0' + i.ecam_start_bus / 10; b[n+1] = b'0' + i.ecam_start_bus % 10;
            b[n+2] = b'-';
            b[n+3] = b'0' + i.ecam_end_bus / 10; b[n+4] = b'0' + i.ecam_end_bus % 10;
            n += 5;
            self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
        } else {
            self.push_line(b"ECAM: not found (CAM only)", [R_DIM, G_DIM, B_DIM]);
        }
        // LAPIC / IOAPIC
        if i.lapic_addr != 0 {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"LAPIC @ 0x"; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, i.lapic_addr);
            if i.ioapic_addr != 0 {
                let d = b"  IOAPIC @ 0x"; b[n..n+d.len()].copy_from_slice(d); n += d.len();
                n = put_hex64(&mut b, n, i.ioapic_addr);
            }
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
        // IRQ overrides
        for k in 0..i.n_overrides as usize {
            let o = &i.overrides[k];
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"  IRQ "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex8(&mut b, n, o.irq);
            let a = b" -> GSI "; b[n..n+a.len()].copy_from_slice(a); n += a.len();
            n += write_u32(&mut b[n..], o.gsi);
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_date(&mut self) {
        let dt = crate::rtc::read();
        let mut buf = [0u8; 80];
        let n = crate::rtc::format(&dt, &mut buf);
        self.push_line(&buf[..n], [R_IN, G_IN, B_IN]);
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_audio(&mut self) {
        match crate::hda::get() {
            None => { self.push_line(b"HDA: no controller", [0xa0, 0x40, 0x40]); }
            Some(d) => {
                let vendor = d.vendor;
                let mut b = [b' '; 80]; let mut n = 0;
                let lbl = b"codec  "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                n = put_hex16(&mut b, n, (vendor >> 16) as u16);
                b[n] = b':'; n += 1;
                n = put_hex16(&mut b, n, vendor as u16);
                self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
                let mut b = [b' '; 80]; let mut n = 0;
                let lbl = b"DAC NID "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                n += write_u32(&mut b[n..], d.dac_nid as u32);
                let mid = b"  pin NID "; b[n..n+mid.len()].copy_from_slice(mid); n += mid.len();
                n += write_u32(&mut b[n..], d.pin_nid as u32);
                let st = if d.stream_running { b"  [playing]" } else { b"  [stopped]" };
                b[n..n+st.len()].copy_from_slice(st); n += st.len();
                self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
            }
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_beep(&mut self, cmd: &[u8]) {
        // Parse optional frequency argument: "beep 880"
        let freq: u32 = if cmd.len() > 5 {
            parse_u32(trim(if cmd.len() > 5 { &cmd[5..] } else { b"" }))
                .unwrap_or(440)
        } else { 440 };

        match crate::hda::get() {
            None => { self.push_line(b"HDA: no controller", [0xa0, 0x40, 0x40]); }
            Some(d) => {
                d.play_tone(freq);
                let mut b = [b' '; 80]; let mut n = 0;
                let lbl = b"playing "; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                n += write_u32(&mut b[n..], freq);
                let sfx = b" Hz"; b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
            }
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_mute(&mut self) {
        match crate::hda::get() {
            None => { self.push_line(b"HDA: no controller", [0xa0, 0x40, 0x40]); }
            Some(d) => {
                d.stop();
                self.push_line(b"audio stopped", [R_DIM, G_DIM, B_DIM]);
            }
        }
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_battery(&mut self) {
        use crate::battery;
        if !crate::ec::present() {
            self.push_line(b"battery: EC not responding", [0xa0, 0x40, 0x40]);
            return;
        }
        match battery::detect() {
            None => {
                self.push_line(b"battery: EC found, DSDT pattern not recognised", [R_DIM, G_DIM, B_DIM]);
                self.push_line(b"  run 'ec 00' through 'ec 3f' to probe registers", [R_DIM, G_DIM, B_DIM]);
            }
            Some(layout) => {
                match battery::read(&layout) {
                    None => self.push_line(b"battery: not present or read failed", [R_DIM, G_DIM, B_DIM]),
                    Some(st) => {
                        // Line 1: state + percent
                        let state: &[u8] = if st.charging { b"charging" }
                                    else if st.discharging { b"discharging" }
                                    else { b"idle" };
                        let pct = st.percent();
                        let mut b = [b' '; 80]; let mut n = 0;
                        b[..state.len()].copy_from_slice(state); n = state.len();
                        b[n] = b' '; n += 1;
                        n += write_u32(&mut b[n..], pct);
                        let sfx = b"%"; b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                        if st.critical { let c=b"  [CRITICAL]"; b[n..n+c.len()].copy_from_slice(c); n+=c.len(); }
                        self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
                        // Line 2: capacity
                        let mut b = [b' '; 80]; let mut n = 0;
                        n += write_u32(&mut b[n..], st.remaining_mah);
                        let mid = b" / "; b[n..n+mid.len()].copy_from_slice(mid); n += mid.len();
                        n += write_u32(&mut b[n..], st.full_mah);
                        let sfx = b" mAh"; b[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
                        self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
                        // Line 3: voltage + rate
                        let mut b = [b' '; 80]; let mut n = 0;
                        n += write_u32(&mut b[n..], st.voltage_mv / 1000);
                        b[n] = b'.'; n += 1;
                        n += write_u32(&mut b[n..], (st.voltage_mv % 1000) / 10);
                        let v = b" V"; b[n..n+v.len()].copy_from_slice(v); n += v.len();
                        if st.rate_ma != 0 {
                            let a = b"  "; b[n..n+a.len()].copy_from_slice(a); n += a.len();
                            let (sign, ma) = if st.rate_ma < 0 { (b'-', (-st.rate_ma) as u32) }
                                             else { (b'+', st.rate_ma as u32) };
                            b[n] = sign; n += 1;
                            n += write_u32(&mut b[n..], ma);
                            let a = b" mA"; b[n..n+a.len()].copy_from_slice(a); n += a.len();
                        }
                        self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
                    }
                }
            }
        }
    }

    /// `ec [NN]` — read EC register at hex address NN, or dump 0x00–0x0F if omitted.
    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_ec(&mut self, cmd: &[u8]) {
        use crate::ec;
        if !ec::present() {
            self.push_line(b"EC not responding", [0xa0, 0x40, 0x40]);
            return;
        }
        let arg = trim(if cmd.len() > 3 { &cmd[3..] } else { b"" });

        if arg.is_empty() {
            // Dump first 16 EC registers.
            for row in 0..2u8 {
                let mut b = [b' '; 80]; let mut n = 0;
                let base = row * 8;
                n = put_hex8(&mut b, n, base);
                b[n] = b':'; b[n+1] = b' '; n += 2;
                for j in 0..8u8 {
                    let v = ec::read(base + j).unwrap_or(0xFF);
                    n = put_hex8(&mut b, n, v);
                    b[n] = b' '; n += 1;
                }
                self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
            }
        } else {
            // Parse hex address.
            let addr = parse_hex_u8(arg).unwrap_or(0);
            match ec::read(addr) {
                None => self.push_line(b"EC read timeout", [0xa0, 0x40, 0x40]),
                Some(v) => {
                    let mut b = [b' '; 80]; let mut n = 0;
                    let lbl = b"EC["; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
                    n = put_hex8(&mut b, n, addr);
                    b[n] = b']'; b[n+1] = b' '; b[n+2] = b'='; b[n+3] = b' '; n += 4;
                    n = put_hex8(&mut b, n, v);
                    b[n] = b' '; b[n+1] = b'('; n += 2;
                    n += write_u32(&mut b[n..], v as u32);
                    b[n] = b')'; n += 1;
                    self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
                }
            }
        }
    }

    /// Dump first 64 bytes of DSDT as hex — diagnostic for battery register hunting.
    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_dsdt(&mut self) {
        let addr = crate::acpi::dsdt_addr();
        if addr == 0 {
            self.push_line(b"DSDT: not found", [0xa0, 0x40, 0x40]);
            return;
        }
        {
            let mut b = [b' '; 80]; let mut n = 0;
            let lbl = b"DSDT @ 0x"; b[..lbl.len()].copy_from_slice(lbl); n = lbl.len();
            n = put_hex64(&mut b, n, addr);
            self.push_line(&b[..n], [R_IN, G_IN, B_IN]);
        }
        // Show 64 bytes in 4 rows of 16.
        let p = addr as *const u8;
        for row in 0..4usize {
            let mut b = [b' '; 80]; let mut n = 0;
            let off = row * 16;
            n = put_hex8(&mut b, n, off as u8);
            b[n] = b':'; b[n+1] = b' '; n += 2;
            for j in 0..16usize {
                let v = unsafe { p.add(off + j).read_volatile() };
                n = put_hex8(&mut b, n, v);
                b[n] = b' '; n += 1;
            }
            self.push_line(&b[..n], [R_DIM, G_DIM, B_DIM]);
        }
    }

    // ── Shared command implementations ────────────────────────────────────────

    fn unknown_cmd(&mut self, cmd: &[u8]) {
        let mut msg = [0u8; 80];
        let pfx = b"unknown: ";
        let plen = pfx.len();
        msg[..plen].copy_from_slice(pfx);
        let clen = cmd.len().min(80 - plen);
        msg[plen..plen + clen].copy_from_slice(&cmd[..clen]);
        self.push_line(&msg[..plen + clen], [0xa0, 0x40, 0x40]);
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn cmd_info_bare(&mut self) {
        let mut buf = [0u8; 80];
        let n = write_banner(&mut buf, byte_table::BYTE_TABLE.len() as u32,
                             byte_table::symbol_count() as u32);
        self.push_line(&buf[..n], [R_DIM, G_DIM, B_DIM]);
        let (free, blocks) = mm::ALLOCATOR.stats();
        let mut hbuf = [0u8; 80]; let pfx = b"heap: "; let plen = pfx.len();
        hbuf[..plen].copy_from_slice(pfx);
        let mut n = plen;
        n += write_u32(&mut hbuf[n..], (free / 1024) as u32);
        let sfx = b" KiB  blocks: "; hbuf[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
        n += write_u32(&mut hbuf[n..], blocks as u32);
        self.push_line(&hbuf[..n], [R_DIM, G_DIM, B_DIM]);
        self.push_line(b"disk: none (sprint 3)", [R_DIM, G_DIM, B_DIM]);
    }

    #[cfg(target_arch = "riscv64")]
    fn cmd_info(&mut self) {
        let mut buf = [0u8; 80];
        let n = write_banner(&mut buf, byte_table::BYTE_TABLE.len() as u32,
                             byte_table::symbol_count() as u32);
        self.push_line(&buf[..n], [R_DIM, G_DIM, B_DIM]);
        self.push_line(b"process: Ko (coord 19)  kernel (coord 9)", [R_DIM, G_DIM, B_DIM]);
        let (free, blocks) = mm::ALLOCATOR.stats();
        let mut hbuf = [0u8; 80]; let pfx = b"heap: "; let plen = pfx.len();
        hbuf[..plen].copy_from_slice(pfx);
        let mut n = plen;
        n += write_u32(&mut hbuf[n..], (free / 1024) as u32);
        let sfx = b" KiB free  blocks: "; hbuf[n..n+sfx.len()].copy_from_slice(sfx); n += sfx.len();
        n += write_u32(&mut hbuf[n..], blocks as u32);
        self.push_line(&hbuf[..n], [R_DIM, G_DIM, B_DIM]);
        if crate::vfs::is_mounted() {
            let mut cnt = 0u32;
            crate::vfs::for_each_entry(|_, _| cnt += 1);
            let mut vbuf = [0u8; 80];
            let pfx = b"Sa volume: "; let plen = pfx.len();
            vbuf[..plen].copy_from_slice(pfx);
            let n = write_u32(&mut vbuf[plen..], cnt);
            let sfx = b" files  ecall ready";
            vbuf[plen+n..plen+n+sfx.len()].copy_from_slice(sfx);
            self.push_line(&vbuf[..plen+n+sfx.len()], [R_DIM, G_DIM, B_DIM]);
        } else {
            self.push_line(b"volume: no disk", [R_DIM, G_DIM, B_DIM]);
        }
    }

    #[cfg(target_arch = "riscv64")]
    fn cmd_ls(&mut self) {
        if !crate::vfs::is_mounted() {
            self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]);
            return;
        }
        let mut any = false;
        crate::vfs::for_each_entry(|name, len| {
            any = true;
            let mut line = [0u8; 80];
            let nlen = name.len().min(40);
            line[..nlen].copy_from_slice(&name[..nlen]);
            let mut sz_buf = [0u8; 12];
            let sz_len = write_u32(&mut sz_buf, len);
            let sz_off = 48usize.saturating_sub(sz_len);
            if sz_off >= nlen {
                line[sz_off..sz_off + sz_len].copy_from_slice(&sz_buf[..sz_len]);
                let boff = sz_off + sz_len;
                line[boff] = b' '; line[boff + 1] = b'B';
                self.push_line(&line[..boff + 2], [R_IN, G_IN, B_IN]);
            } else {
                self.push_line(&line[..nlen], [R_IN, G_IN, B_IN]);
            }
        });
        if !any { self.push_line(b"(empty)", [R_DIM, G_DIM, B_DIM]); }
    }

    #[cfg(target_arch = "riscv64")]
    fn cmd_cat_arg(&mut self, name: &[u8]) {
        if !crate::vfs::is_mounted() {
            self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]);
            return;
        }
        if crate::vfs::find_entry(name).is_none() {
            let mut msg = [0u8; 80]; let pfx = b"not found: "; let plen = pfx.len();
            msg[..plen].copy_from_slice(pfx);
            let alen = name.len().min(80 - plen);
            msg[plen..plen + alen].copy_from_slice(&name[..alen]);
            self.push_line(&msg[..plen + alen], [0xa0, 0x40, 0x40]);
            return;
        }
        static mut FILE_BUF: [u8; 8192] = [0u8; 8192];
        let data = unsafe {
            let n = crate::vfs::read_named(name, &mut FILE_BUF);
            &FILE_BUF[..n]
        };
        if data.len() >= 4 && &data[..4] == b"\x7fELF" {
            let mut msg = [0u8; 80]; let pfx = b"binary ELF  (use Ty ";
            msg[..pfx.len()].copy_from_slice(pfx);
            let alen = name.len().min(80 - pfx.len() - 1);
            msg[pfx.len()..pfx.len() + alen].copy_from_slice(&name[..alen]);
            let off = pfx.len() + alen; msg[off] = b')';
            self.push_line(&msg[..off + 1], [R_DIM, G_DIM, B_DIM]);
            return;
        }
        // .ko files are Kobra source — evaluate rather than print raw text.
        if name.ends_with(b".ko") {
            let result = crate::kobra::eval_file(data);
            if result.line_count() == 0 {
                self.push_line(b"(no output)", [R_DIM, G_DIM, B_DIM]);
            } else {
                for i in 0..result.line_count() {
                    self.push_line(result.line(i), [R_DIM, G_DIM, B_DIM]);
                }
            }
            return;
        }
        let n = data.len();
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

    #[cfg(target_arch = "riscv64")]
    fn cmd_run_arg(&mut self, name: &[u8]) {
        if name.is_empty() {
            self.push_line(b"Ty: need filename", [0xa0, 0x40, 0x40]);
            return;
        }
        if !crate::vfs::is_mounted() {
            self.push_line(b"no volume mounted", [0xa0, 0x40, 0x40]);
            return;
        }
        let (start, len) = match crate::vfs::find_entry(name) {
            None    => { self.push_line(b"file not found", [0xa0, 0x40, 0x40]); return; }
            Some(v) => v,
        };
        use alloc::vec;
        let mut buf = vec![0u8; len as usize];
        let n = crate::vfs::read_named(name, &mut buf);
        if n < len as usize {
            self.push_line(b"read error", [0xa0, 0x40, 0x40]);
        } else if n < 4 || &buf[..4] != b"\x7fELF" {
            self.push_line(b"not an ELF binary", [0xa0, 0x40, 0x40]);
        } else {
            let _ = start;
            crate::process::kill_user_processes();
            match crate::process::spawn_elf(19, &buf) {
                Some(_) => {
                    let mut msg = [0u8; 80]; let pfx = b"Ty: running ";
                    msg[..pfx.len()].copy_from_slice(pfx);
                    let alen = name.len().min(80 - pfx.len());
                    msg[pfx.len()..pfx.len() + alen].copy_from_slice(&name[..alen]);
                    self.push_line(&msg[..pfx.len() + alen], [R_IN, G_IN, B_IN]);
                }
                None => self.push_line(b"spawn failed", [0xa0, 0x40, 0x40]),
            }
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Parse a Myrun argument into (ip, port, path).
///
///   /path            → ([10,0,2,2], 9000, arg)
///   :port/path       → ([10,0,2,2], port, path_part)
///   :port            → ([10,0,2,2], port, b"/")
///   a.b.c.d:port/p   → (parsed ip, port, path_part)
///   (anything else)  → ([10,0,2,2], 9000, b"/")
fn myrun_parse_target(arg: &[u8]) -> ([u8; 4], u16, &[u8]) {
    let default_ip   = [10u8, 0, 2, 2];
    let default_port = 9000u16;

    // /path — bare path, use default host:port
    if arg.first() == Some(&b'/') {
        return (default_ip, default_port, arg);
    }

    // :port[/path] — alternate port on default host
    if arg.first() == Some(&b':') {
        let rest = &arg[1..];
        let slash = rest.iter().position(|&b| b == b'/').unwrap_or(rest.len());
        let port  = parse_u32(&rest[..slash]).unwrap_or(default_port as u32) as u16;
        let path  = if slash < rest.len() { &rest[slash..] } else { b"/" };
        return (default_ip, port, path);
    }

    // Try to parse a.b.c.d:port/path
    // Find the colon
    if let Some(colon) = arg.iter().position(|&b| b == b':') {
        let host_part = &arg[..colon];
        let after     = &arg[colon + 1..];
        let slash     = after.iter().position(|&b| b == b'/').unwrap_or(after.len());
        let port      = parse_u32(&after[..slash]).unwrap_or(default_port as u32) as u16;
        let path      = if slash < after.len() { &after[slash..] } else { b"/" };
        // Parse dotted-decimal IP
        let mut ip   = default_ip;
        let mut octet = 0u32;
        let mut idx  = 0usize;
        let mut valid = true;
        for &b in host_part {
            if b == b'.' {
                if idx < 4 { ip[idx] = octet as u8; idx += 1; octet = 0; }
                else { valid = false; break; }
            } else if b >= b'0' && b <= b'9' {
                octet = octet * 10 + (b - b'0') as u32;
            } else {
                valid = false; break;
            }
        }
        if valid && idx == 3 { ip[3] = octet as u8; }
        return (ip, port, path);
    }

    (default_ip, default_port, b"/")
}

/// Build an HTTP/1.0 GET request into `buf`. Returns bytes written.
fn myrun_build_get(buf: &mut [u8], path: &[u8], ip: [u8; 4], port: u16) -> usize {
    let mut n = 0usize;
    macro_rules! w {
        ($s:expr) => {{ let s: &[u8] = $s; let l = s.len().min(buf.len() - n); buf[n..n+l].copy_from_slice(&s[..l]); n += l; }};
    }
    w!(b"GET ");
    w!(path);
    w!(b" HTTP/1.0\r\nHost: ");
    // ip:port
    for (k, &o) in ip.iter().enumerate() {
        if k > 0 { w!(b"."); }
        let mut tmp = [0u8; 4];
        let l = write_u32(&mut tmp, o as u32);
        w!(&tmp[..l]);
    }
    w!(b":");
    let mut tmp = [0u8; 6];
    let l = write_u32(&mut tmp, port as u32);
    w!(&tmp[..l]);
    w!(b"\r\nAccept: */*\r\nConnection: close\r\n\r\n");
    n
}

/// Split `"verb arg"` into `(verb, arg)` at the first space.
/// If no space, returns `(cmd, b"")`.
fn split_verb(cmd: &[u8]) -> (&[u8], &[u8]) {
    match cmd.iter().position(|&b| b == b' ') {
        None    => (cmd, b""),
        Some(i) => (trim(&cmd[..i]), trim(&cmd[i+1..])),
    }
}

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

fn hex_digit(v: u8) -> u8 {
    if v < 10 { b'0' + v } else { b'a' + v - 10 }
}
fn hex_hi(v: u8) -> u8 { hex_digit(v >> 4) }
fn hex_lo(v: u8) -> u8 { hex_digit(v & 0xF) }

fn put_hex8(buf: &mut [u8], off: usize, v: u8) -> usize {
    buf[off]   = hex_hi(v);
    buf[off+1] = hex_lo(v);
    off + 2
}

fn put_hex16(buf: &mut [u8], off: usize, v: u16) -> usize {
    let off = put_hex8(buf, off, (v >> 8) as u8);
    put_hex8(buf, off, v as u8)
}

fn parse_hex_u8(s: &[u8]) -> Option<u8> {
    if s.is_empty() { return None; }
    let mut v: u8 = 0;
    for &b in s.iter().take(2) {
        let nib = match b {
            b'0'..=b'9' => b - b'0',
            b'a'..=b'f' => b - b'a' + 10,
            b'A'..=b'F' => b - b'A' + 10,
            _ => return None,
        };
        v = v.wrapping_shl(4) | nib;
    }
    Some(v)
}

fn parse_u32(s: &[u8]) -> Option<u32> {
    if s.is_empty() { return None; }
    let mut v: u32 = 0;
    for &b in s {
        if b < b'0' || b > b'9' { return None; }
        v = v.wrapping_mul(10).wrapping_add((b - b'0') as u32);
    }
    Some(v)
}

fn put_hex64(buf: &mut [u8], off: usize, v: u64) -> usize {
    let mut o = off;
    for shift in [56u32, 48, 40, 32, 24, 16, 8, 0] {
        o = put_hex8(buf, o, (v >> shift) as u8);
    }
    o
}

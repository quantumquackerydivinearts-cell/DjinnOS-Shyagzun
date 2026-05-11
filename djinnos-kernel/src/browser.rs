// Faerie Browser — no-JS HTML reader for DjinnOS.
//
// Fetches pages through browser_proxy.py on port 8080 at 10.0.2.2.
// The proxy accepts HTTP-proxy-style requests and returns the remote page.
// No JS, no cookies, no CSS — plain word-wrapped text with link navigation.
//
// Key bindings (browse mode):
//   Arrow Up/Down       scroll
//   PgUp / PgDn         fast scroll
//   Tab                 cycle to next link
//   Enter               follow focused link
//   G or g              enter URL bar
//   Backspace           go back
//   Escape              exit to Ko shell

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;

// ── Layout ────────────────────────────────────────────────────────────────────

const SCALE:  u32 = 2;
const CHAR_W: u32 = font::GLYPH_W * SCALE;
const CHAR_H: u32 = font::GLYPH_H * SCALE;
const MAR:    u32 = 32;

// Faerie Browser palette — absinthe green × sugarfloss pink.
// All values are BGR (Blue, Green, Red) to match the BGRX framebuffer layout.
//
// Absinthe green: the chartreuse-emerald of the spirit, slightly yellow-warm.
// Sugarfloss pink: soft spun-sugar pink, not hot, not pastel — mid-saturated.
const BG_B: u8 = 0x08; const BG_G: u8 = 0x0e; const BG_R: u8 = 0x08; // near-black green
const UB_B: u8 = 0x0c; const UB_G: u8 = 0x16; const UB_R: u8 = 0x0c; // bar background
const TX_B: u8 = 0x20; const TX_G: u8 = 0xd0; const TX_R: u8 = 0x48; // absinthe body text (bright)
const HD_B: u8 = 0x40; const HD_G: u8 = 0xff; const HD_R: u8 = 0x70; // bright absinthe headings
const LK_B: u8 = 0xd8; const LK_G: u8 = 0xb0; const LK_R: u8 = 0xff; // sugarfloss links
const LF_B: u8 = 0xff; const LF_G: u8 = 0xcc; const LF_R: u8 = 0xff; // focused sugarfloss
const SB_B: u8 = 0x30; const SB_G: u8 = 0x60; const SB_R: u8 = 0x30; // muted absinthe status
const HR_B: u8 = 0x19; const HR_G: u8 = 0x3c; const HR_R: u8 = 0x1e; // dark absinthe rule

// Line kind constants
const KIND_NORMAL:  u8 = 0;
const KIND_HEADING: u8 = 1;
const KIND_LINK:    u8 = 2;
const KIND_HR:      u8 = 3;

// Kyom (byte 182, Grapevine T7) — Replica / proxy / masked follower.
// The browser reaches the internet through a Kyom: a machine running
// browser_proxy.py that speaks HTTPS to the internet and returns plain
// HTTP to the kernel (which has no TLS stack).
//
// Default: 10.0.2.2:8888 (QEMU SLIRP gateway).
// On real hardware: the IP of the machine running browser_proxy.py,
// set with `Kyom <ip>:<port>` at the Ko shell.
static mut KYOM_IP:   [u8; 4] = [10, 0, 2, 2];
static mut KYOM_PORT: u16     = 8888;

pub fn set_kyom(ip: [u8; 4], port: u16) {
    unsafe { KYOM_IP = ip; KYOM_PORT = port; }
}

pub fn proxy_ip()   -> [u8; 4] { unsafe { KYOM_IP } }
pub fn proxy_port() -> u16     { unsafe { KYOM_PORT } }

// Sizes
const LINE_W:  usize = 104;  // chars per rendered line (2× scale @ 1920px)
const MAX_L:   usize = 512;  // max rendered lines per page
const MAX_LNK: usize = 64;   // max links per page
const LNK_W:   usize = 200;  // max link URL length
const URL_W:   usize = 256;  // max URL bar length
const TTL_W:   usize = 64;   // max page title length
const HIST:    usize = 8;    // back-history depth

// ── Static state ──────────────────────────────────────────────────────────────

static mut BROWSER: BrowserClient = BrowserClient::const_new();
static mut LAUNCH_URL: [u8; URL_W] = [0u8; URL_W];
static mut LAUNCH_LEN: usize = 0;
static mut LAUNCH_PENDING: bool = false;

// Large response buffer lives in BSS, not on the stack.
static mut RBUF: [u8; 32768] = [0u8; 32768];
static mut REQBUF: [u8; 512] = [0u8; 512];

// ── Public interface ──────────────────────────────────────────────────────────

pub fn browser() -> &'static mut BrowserClient {
    unsafe { &mut BROWSER }
}

pub fn request_launch(url: &[u8]) {
    let n = url.len().min(URL_W - 1);
    unsafe {
        LAUNCH_URL[..n].copy_from_slice(&url[..n]);
        LAUNCH_LEN    = n;
        LAUNCH_PENDING = true;
    }
}

pub fn consume_launch() -> bool {
    if unsafe { LAUNCH_PENDING } {
        unsafe {
            LAUNCH_PENDING = false;
            let n = LAUNCH_LEN;
            let mut tmp = [0u8; URL_W];
            tmp[..n].copy_from_slice(&LAUNCH_URL[..n]);
            BROWSER.playing = true;
            BROWSER.navigate(&tmp[..n]);
        }
        true
    } else {
        false
    }
}

// ── BrowserClient ─────────────────────────────────────────────────────────────

pub struct BrowserClient {
    // Page content
    lines:     [[u8; LINE_W]; MAX_L],
    line_len:  [u16; MAX_L],
    line_kind: [u8; MAX_L],
    line_link: [u8; MAX_L],   // 0xFF = no link
    n_lines:   usize,

    // Discovered links
    lnk_url:   [[u8; LNK_W]; MAX_LNK],
    lnk_len:   [u8; MAX_LNK],
    n_lnk:     usize,

    // Current URL and page title
    url:       [u8; URL_W],
    url_len:   usize,
    title:     [u8; TTL_W],
    title_len: usize,

    // URL-bar input
    input:     [u8; URL_W],
    input_len: usize,
    mode:      u8,   // 0=browse  1=url-input

    // Navigation history
    hist:      [[u8; URL_W]; HIST],
    hist_lens: [usize; HIST],
    hist_d:    usize,

    // View state
    scroll:    usize,
    focused:   u8,   // 0xFF = none

    // Status bar
    status:    [u8; 80],
    status_n:  usize,

    pub playing: bool,
    dirty:       bool,
}

impl BrowserClient {
    pub const fn const_new() -> Self {
        BrowserClient {
            lines:     [[0u8; LINE_W]; MAX_L],
            line_len:  [0u16; MAX_L],
            line_kind: [0u8; MAX_L],
            line_link: [0xFFu8; MAX_L],
            n_lines:   0,
            lnk_url:   [[0u8; LNK_W]; MAX_LNK],
            lnk_len:   [0u8; MAX_LNK],
            n_lnk:     0,
            url:       [0u8; URL_W],
            url_len:   0,
            title:     [0u8; TTL_W],
            title_len: 0,
            input:     [0u8; URL_W],
            input_len: 0,
            mode:      0,
            hist:      [[0u8; URL_W]; HIST],
            hist_lens: [0usize; HIST],
            hist_d:    0,
            scroll:    0,
            focused:   0xFF,
            status:    [0u8; 80],
            status_n:  0,
            playing:   false,
            dirty:     true,
        }
    }

    pub fn exit(&mut self) {
        self.playing = false;
        self.dirty   = true;
    }

    // ── Input ─────────────────────────────────────────────────────────────────

    // ── Click handling ────────────────────────────────────────────────────────
    //
    // Faerie-safe click model:
    //   - Click in content area → hit-test rendered lines
    //   - Line with a link index → navigate(lnk_url[link_idx])
    //   - URL beginning "local://"  → read from Sa volume
    //   - URL beginning "ko:"       → evaluate Kobra expression, render result
    //   - Regular http(s)://        → Kyom proxy fetch

    // Content area starts at: title bar + gap + URL bar + gap
    // tb_h = CHAR_H + 10, ub_h = CHAR_H + 8 → content_y = 2*CHAR_H + 21
    const CONTENT_Y: u32 = CHAR_H * 2 + 21;

    pub fn handle_click(&mut self, click_x: u32, click_y: u32) {
        let _ = click_x; // horizontal position unused (full-width lines)
        if self.mode == 1 { return; } // in URL input — ignore click
        if click_y < Self::CONTENT_Y { return; }

        let row    = ((click_y - Self::CONTENT_Y) / CHAR_H) as usize;
        let li     = self.scroll + row;
        if li >= self.n_lines { return; }

        let lnk = self.line_link[li];
        if lnk == 0xFF { return; } // not a link

        let url_n = self.lnk_len[lnk as usize] as usize;
        let mut tmp = [0u8; LNK_W];
        tmp[..url_n].copy_from_slice(&self.lnk_url[lnk as usize][..url_n]);
        self.navigate(&tmp[..url_n]);
        self.dirty = true;
    }

    pub fn handle_key(&mut self, key: Key) {
        if self.mode == 1 {
            self.key_url(key);
        } else {
            self.key_browse(key);
        }
    }

    fn key_url(&mut self, key: Key) {
        match key {
            Key::Escape => { self.mode = 0; self.dirty = true; }
            Key::Enter  => {
                let n = self.input_len;
                let mut tmp = [0u8; URL_W];
                tmp[..n].copy_from_slice(&self.input[..n]);
                self.mode = 0;
                self.navigate(&tmp[..n]);
            }
            Key::Backspace => {
                if self.input_len > 0 { self.input_len -= 1; }
                self.dirty = true;
            }
            Key::Char(c) => {
                if self.input_len + 1 < URL_W {
                    self.input[self.input_len] = c;
                    self.input_len += 1;
                }
                self.dirty = true;
            }
            _ => {}
        }
    }

    fn key_browse(&mut self, key: Key) {
        match key {
            Key::Up => {
                if self.scroll > 0 { self.scroll -= 1; self.dirty = true; }
            }
            Key::Down => {
                if self.scroll + 1 < self.n_lines { self.scroll += 1; self.dirty = true; }
            }
            Key::Char(b'\t') => { self.cycle_link(); self.dirty = true; }
            Key::Enter => { self.follow_link(); }
            Key::Char(b'g') | Key::Char(b'G') => {
                let n = self.url_len;
                self.input[..n].copy_from_slice(&self.url[..n]);
                self.input_len = n;
                self.mode = 1;
                self.dirty = true;
            }
            Key::Backspace => { self.go_back(); }
            _ => {}
        }
    }

    fn cycle_link(&mut self) {
        if self.n_lnk == 0 { return; }
        self.focused = if self.focused == 0xFF || self.focused as usize + 1 >= self.n_lnk {
            0
        } else {
            self.focused + 1
        };
        self.scroll_to_link();
        self.status_from_link();
    }

    fn scroll_to_link(&mut self) {
        let idx = self.focused as usize;
        for i in 0..self.n_lines {
            if self.line_link[i] == idx as u8 {
                if i < self.scroll || i >= self.scroll + 14 {
                    self.scroll = i.saturating_sub(4);
                }
                break;
            }
        }
    }

    fn status_from_link(&mut self) {
        let idx = self.focused as usize;
        if idx >= self.n_lnk { return; }
        let n = self.lnk_len[idx] as usize;
        self.status_n = n.min(80);
        self.status[..self.status_n].copy_from_slice(&self.lnk_url[idx][..self.status_n]);
    }

    fn follow_link(&mut self) {
        if self.focused == 0xFF || self.focused as usize >= self.n_lnk { return; }
        let idx = self.focused as usize;
        let n   = self.lnk_len[idx] as usize;
        let mut tmp = [0u8; URL_W];
        tmp[..n].copy_from_slice(&self.lnk_url[idx][..n]);
        self.navigate(&tmp[..n]);
    }

    fn go_back(&mut self) {
        if self.hist_d == 0 { return; }
        self.hist_d -= 1;
        let n = self.hist_lens[self.hist_d];
        let mut tmp = [0u8; URL_W];
        tmp[..n].copy_from_slice(&self.hist[self.hist_d][..n]);
        self.nav_inner(&tmp[..n]);
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    pub fn navigate(&mut self, url: &[u8]) {
        if self.url_len > 0 && self.hist_d < HIST {
            let d = self.hist_d;
            let n = self.url_len.min(URL_W);
            self.hist[d][..n].copy_from_slice(&self.url[..n]);
            self.hist_lens[d] = n;
            self.hist_d += 1;
        }
        self.nav_inner(url);
    }

    fn nav_inner(&mut self, url: &[u8]) {
        let n = url.len().min(URL_W);
        self.url[..n].copy_from_slice(&url[..n]);
        self.url_len = n;
        self.n_lines  = 0;
        self.n_lnk    = 0;
        self.scroll    = 0;
        self.focused   = 0xFF;
        self.title_len = 0;
        self.dirty     = true;

        if url.starts_with(b"local://") {
            set_status_inner(&mut self.status, &mut self.status_n, b"Loading local...");
            self.fetch_local(&url[8..]);
        } else if url.starts_with(b"ko:") {
            self.eval_ko(&url[3..]);
        } else {
            set_status_inner(&mut self.status, &mut self.status_n, b"Loading...");
            self.fetch_and_parse(url);
        }
    }

    // ── local:// — read HTML from Sa volume ──────────────────────────────────

    fn fetch_local(&mut self, filename: &[u8]) {
        let n = crate::sa::read_file(filename, unsafe { &mut RBUF });
        if n == 0 {
            self.push_line(b"local: file not found", KIND_NORMAL, 0xFF);
            let mut msg = [0u8; 48];
            let pfx = b"Not found: ";
            msg[..pfx.len()].copy_from_slice(pfx);
            let fn_n = filename.len().min(48 - pfx.len());
            msg[pfx.len()..pfx.len() + fn_n].copy_from_slice(&filename[..fn_n]);
            self.setstatus(&msg[..pfx.len() + fn_n]);
            return;
        }
        let body = unsafe { &RBUF[..n] };
        self.parse_html(body);
        if self.n_lines == 0 {
            self.push_line(b"[ empty local page ]", KIND_NORMAL, 0xFF);
        }
        let mut sb = [0u8; 32];
        let pfx = b"local  lines: ";
        sb[..pfx.len()].copy_from_slice(pfx);
        let sn = pfx.len() + write_u32(&mut sb[pfx.len()..], self.n_lines as u32);
        self.setstatus(&sb[..sn]);
    }

    // ── ko: — evaluate Kobra expression, render result ───────────────────────

    fn eval_ko(&mut self, script: &[u8]) {
        if let Ok(s) = core::str::from_utf8(script) {
            let result = crate::kobra::eval_expr(s.as_bytes());
            if result.line_count() == 0 {
                self.push_line(b"(no output)", KIND_NORMAL, 0xFF);
            } else {
                for i in 0..result.line_count() {
                    let line = result.line(i);
                    // If result looks like a URL, navigate there
                    if line.starts_with(b"local://") || line.starts_with(b"http") {
                        let mut tmp = [0u8; URL_W];
                        let ln = line.len().min(URL_W);
                        tmp[..ln].copy_from_slice(&line[..ln]);
                        self.nav_inner(&tmp[..ln]);
                        return;
                    }
                    self.push_line(line, KIND_NORMAL, 0xFF);
                }
            }
        } else {
            self.push_line(b"ko: invalid UTF-8", KIND_NORMAL, 0xFF);
        }
        self.setstatus(b"ko: evaluated");
    }

    // ── Render ────────────────────────────────────────────────────────────────

    pub fn render(&self, gpu: &dyn GpuSurface) {
        if !self.dirty { return; }
        let w = gpu.width();
        let h = gpu.height();

        // ── Full-frame background ─────────────────────────────────────────────
        gpu.fill_rect(0, 0, w, h, BG_B, BG_G, BG_R);

        // ── Title bar ─────────────────────────────────────────────────────────
        //  "◈ Faerie"   [proxy address right-aligned]
        let tb_h = CHAR_H + 10;
        gpu.fill_rect(0, 0, w, tb_h, UB_B, UB_G, UB_R);
        // Left: wordmark
        let tx = font::draw_str(gpu, 10, 5, "Faerie", SCALE, HD_B, HD_G, HD_R);
        // Loading indicator dot when in motion
        if self.status_n > 0 && &self.status[..7.min(self.status_n)] == b"Loading" {
            font::draw_str(gpu, tx + 6, 5, "...", SCALE, LK_B, LK_G, LK_R);
        }
        // Right: Kyom address (byte 182 — Replica / proxy / masked follower)
        {
            let pip = proxy_ip();
            let ppt = proxy_port();
            let mut pb = [0u8; 40]; let mut pn = 0;
            let lbl = b"Kyom: ";
            pb[..lbl.len()].copy_from_slice(lbl); pn += lbl.len();
            for (k, &o) in pip.iter().enumerate() {
                if k > 0 { pb[pn] = b'.'; pn += 1; }
                pn += write_u32(&mut pb[pn..], o as u32);
            }
            pb[pn] = b':'; pn += 1;
            pn += write_u32(&mut pb[pn..], ppt as u32);
            if let Ok(ps) = core::str::from_utf8(&pb[..pn]) {
                let pw = pn as u32 * CHAR_W;
                font::draw_str(gpu, w.saturating_sub(pw + 10), 5, ps, SCALE, SB_B, SB_G, SB_R);
            }
        }
        // Separator line under title bar
        gpu.draw_line(0, tb_h as i32, w as i32, tb_h as i32, HR_B, HR_G, HR_R);

        // ── URL bar ───────────────────────────────────────────────────────────
        let ub_y = tb_h + 1;
        let ub_h = CHAR_H + 8;
        gpu.fill_rect(0, ub_y, w, ub_h, UB_B, UB_G, UB_R);
        let ty = ub_y + 4;
        let label = if self.mode == 1 { " Go: " } else { "    " };
        let lx = font::draw_str(gpu, 6, ty, label, SCALE, SB_B, SB_G, SB_R);
        let (disp, dlen) = if self.mode == 1 {
            (&self.input, self.input_len)
        } else {
            (&self.url, self.url_len)
        };
        let url_col = if self.mode == 1 { (LF_B, LF_G, LF_R) } else { (TX_B, TX_G, TX_R) };
        let dstr = core::str::from_utf8(&disp[..dlen]).unwrap_or("?");
        // Truncate URL display to fit available width
        let max_url_chars = ((w.saturating_sub(lx + 60)) / CHAR_W) as usize;
        let dstr_show = if dstr.len() > max_url_chars && max_url_chars > 3 {
            &dstr[dstr.len() - max_url_chars..]
        } else { dstr };
        let cx = font::draw_str(gpu, lx, ty, dstr_show, SCALE, url_col.0, url_col.1, url_col.2);
        if self.mode == 1 {
            gpu.fill_rect(cx, ty, CHAR_W, CHAR_H, LF_B, LF_G, LF_R);
        }
        // Page title right-aligned in URL bar (browse mode)
        if self.mode == 0 && self.title_len > 0 {
            let ts = core::str::from_utf8(&self.title[..self.title_len]).unwrap_or("");
            let tw = ts.len() as u32 * CHAR_W;
            let tx2 = w.saturating_sub(tw + 12);
            if tx2 > cx + CHAR_W * 4 {
                font::draw_str(gpu, tx2, ty, ts, SCALE, SB_B, SB_G, SB_R);
            }
        }
        gpu.draw_line(0, (ub_y + ub_h) as i32, w as i32, (ub_y + ub_h) as i32, HR_B, HR_G, HR_R);

        // ── Content area ──────────────────────────────────────────────────────
        let cy    = ub_y + ub_h + 2;
        let sb_h  = CHAR_H + 6;   // status bar height
        let scr_w = 8u32;         // scrollbar width
        let bot   = h.saturating_sub(sb_h);
        let avail = bot.saturating_sub(cy);
        let vrows = (avail / CHAR_H) as usize;
        let cw    = w.saturating_sub(MAR + scr_w + 4); // content width excl. scrollbar

        let mut y = cy;
        for vi in 0..vrows {
            let li = self.scroll + vi;
            if li >= self.n_lines { break; }
            let len  = self.line_len[li] as usize;
            let kind = self.line_kind[li];
            let lnk  = self.line_link[li];

            if kind == KIND_HR {
                let mid = y + CHAR_H / 2;
                gpu.draw_line(MAR as i32, mid as i32, (w - scr_w - 4) as i32, mid as i32, HR_B, HR_G, HR_R);
                y += CHAR_H;
                continue;
            }

            let (b, g, r) = match kind {
                KIND_HEADING => (HD_B, HD_G, HD_R),
                KIND_LINK if lnk != 0xFF && lnk == self.focused => (LF_B, LF_G, LF_R),
                KIND_LINK    => (LK_B, LK_G, LK_R),
                _            => (TX_B, TX_G, TX_R),
            };

            let text = core::str::from_utf8(&self.lines[li][..len]).unwrap_or("");
            font::draw_str(gpu, MAR, y, text, SCALE, b, g, r);

            if kind == KIND_HEADING && len > 0 {
                let lw = (len as u32 * CHAR_W).min(cw.saturating_sub(MAR));
                gpu.draw_line(MAR as i32, (y + CHAR_H + 1) as i32,
                              (MAR + lw) as i32, (y + CHAR_H + 1) as i32,
                              HD_B, HD_G, HD_R);
            }
            if kind == KIND_LINK && lnk != 0xFF && lnk == self.focused {
                gpu.draw_line((MAR - 6) as i32, y as i32,
                              (MAR - 6) as i32, (y + CHAR_H - 1) as i32,
                              LF_B, LF_G, LF_R);
            }
            y += CHAR_H;
        }

        // ── Scrollbar ─────────────────────────────────────────────────────────
        let track_h = avail;
        let track_x = w - scr_w - 2;
        gpu.fill_rect(track_x, cy, scr_w, track_h, UB_B, UB_G, UB_R);
        if self.n_lines > vrows {
            let thumb_h = ((vrows as u32 * track_h) / self.n_lines as u32).max(4);
            let thumb_y = cy + (self.scroll as u32 * track_h) / self.n_lines as u32;
            gpu.fill_rect(track_x + 1, thumb_y, scr_w - 2, thumb_h, SB_B, SB_G, SB_R);
        }

        // ── Status bar ────────────────────────────────────────────────────────
        gpu.fill_rect(0, bot, w, sb_h, UB_B, UB_G, UB_R);
        gpu.draw_line(0, bot as i32, w as i32, bot as i32, HR_B, HR_G, HR_R);
        let ss = core::str::from_utf8(&self.status[..self.status_n]).unwrap_or("");
        font::draw_str(gpu, 8, bot + 4, ss, SCALE, SB_B, SB_G, SB_R);
        // Hint text right-aligned
        let hint = "↑↓ scroll   Tab link   Enter follow   G url   Bksp back   Esc exit";
        let hw = hint.len() as u32 * CHAR_W;
        if hw + 16 < w {
            font::draw_str(gpu, w - hw - 8, bot + 4, hint, SCALE,
                           UB_B.saturating_add(0x20), UB_G.saturating_add(0x20), UB_R.saturating_add(0x20));
        }
    }

    // ── Fetch and parse ───────────────────────────────────────────────────────
    // crate::net resolves to virtio-net on RISC-V and x86net (e1000/xHCI)
    // on x86_64.  No cfg gate needed.

    fn fetch_and_parse(&mut self, url: &[u8]) {
        let fd = crate::net::tcp_socket(0);
        if fd == u64::MAX {
            self.setstatus(b"no network");
            return;
        }
        if crate::net::tcp_connect(fd, proxy_ip(), proxy_port()) == 0 {
            self.setstatus(b"Kyom unreachable (browser_proxy.py not running?)");
            crate::net::tcp_close(fd);
            return;
        }
        let mut ok = false;
        for _ in 0..3000 {
            crate::net::poll();
            if crate::net::tcp_ready(fd) { ok = true; break; }
        }
        if !ok {
            self.setstatus(b"proxy connect timeout");
            crate::net::tcp_close(fd);
            return;
        }

        let req_n = unsafe { build_proxy_get(&mut REQBUF, url) };
        crate::net::tcp_send(fd, unsafe { &REQBUF[..req_n] });
        crate::net::poll();

        let total = recv_all(fd);
        crate::net::tcp_close(fd);

        if total == 0 {
            self.setstatus(b"empty response");
            return;
        }

        let resp = unsafe { &RBUF[..total] };
        self.parse_response(resp);
    }

    // ── HTTP response parser ──────────────────────────────────────────────────

    fn parse_response(&mut self, resp: &[u8]) {
        // Check status code (bytes 9-11 of "HTTP/1.x NNN ...")
        if resp.len() > 12 {
            let code = &resp[9..12];
            if code != b"200" {
                self.setstatus(b"HTTP error (non-200 response)");
                self.push_line(code, KIND_HEADING, 0xFF);
            }
        }

        // Find header/body separator: \r\n\r\n
        let body_start = resp.windows(4)
            .position(|w| w == b"\r\n\r\n")
            .map(|i| i + 4)
            .unwrap_or(0);

        let body = &resp[body_start..];
        if body.is_empty() {
            self.setstatus(b"empty body");
            return;
        }

        self.parse_html(body);

        // If very little content: this is a JS-rendered site.
        if self.n_lines < 4 {
            self.push_line(b"", KIND_NORMAL, 0xFF);
            self.push_line(b"[ Page requires JavaScript -- Faerie is a no-JS reader ]", KIND_NORMAL, 0xFF);
            self.push_line(b"", KIND_NORMAL, 0xFF);
            self.push_line(b"Try a local page:", KIND_HEADING, 0xFF);
            let lnk = self.n_lnk as u8;
            if (lnk as usize) < MAX_LNK {
                let home = b"local://home.html";
                let hn = home.len().min(LNK_W);
                self.lnk_url[lnk as usize][..hn].copy_from_slice(&home[..hn]);
                self.lnk_len[lnk as usize] = hn as u8;
                self.n_lnk += 1;
                self.push_line(b"  QQVA home (local://home.html)", KIND_LINK, lnk);
            }
            let lnk2 = self.n_lnk as u8;
            if (lnk2 as usize) < MAX_LNK {
                let lab = b"local://labyrinth.html";
                let ln2 = lab.len().min(LNK_W);
                self.lnk_url[lnk2 as usize][..ln2].copy_from_slice(&lab[..ln2]);
                self.lnk_len[lnk2 as usize] = ln2 as u8;
                self.n_lnk += 1;
                self.push_line(b"  Ko's Labyrinth (local://labyrinth.html)", KIND_LINK, lnk2);
            }
        }

        let n = self.n_lines;
        let mut sb = [0u8; 80];
        let pfx = b"done  lines: ";
        sb[..pfx.len()].copy_from_slice(pfx);
        let mut sn = pfx.len();
        sn += write_u32(&mut sb[sn..], n as u32);
        self.setstatus(&sb[..sn]);
    }

    fn setstatus(&mut self, msg: &[u8]) {
        set_status_inner(&mut self.status, &mut self.status_n, msg);
    }

    // ── HTML parser ───────────────────────────────────────────────────────────
    //
    // State machine: Text → Tag → Attr → HrefVal → EntityAmp
    // Block elements flush the current line.  Inline elements (a, strong, em)
    // set kind or link index without flushing.

    fn parse_html(&mut self, html: &[u8]) {
        // Parser scratch (on stack — only ~400 bytes)
        let mut tag:    [u8; 32] = [0u8; 32];
        let mut tag_n:  usize = 0;
        let mut href:   [u8; LNK_W] = [0u8; LNK_W];
        let mut href_n: usize = 0;
        let mut ent:    [u8; 8]  = [0u8; 8];
        let mut ent_n:  usize = 0;

        // Word / line accumulator (also on stack)
        let mut word:    [u8; 80] = [0u8; 80];
        let mut word_n:  usize = 0;
        let mut line:    [u8; LINE_W] = [0u8; LINE_W];
        let mut line_n:  usize = 0;

        // Per-word kind and link (applies to whole pending word)
        let mut kind:    u8 = KIND_NORMAL;
        let mut lnk_idx: u8 = 0xFF;

        // Parser state flags
        let mut in_script: bool = false;
        let mut in_style:  bool = false;
        let mut in_title:  bool = false;
        let mut in_pre:    bool = false;
        let mut _in_href:  bool = false;
        let mut in_link:   bool = false;
        let mut in_ent:    bool = false;
        let mut in_tag:    bool = false;

        // Title buffer (written to self.title when </title> seen)
        let mut title_buf: [u8; TTL_W] = [0u8; TTL_W];
        let mut title_n:   usize = 0;

        // Macro: push accumulated word to line (or flush line if full)
        macro_rules! flush_word {
            () => {
                if word_n > 0 {
                    // Would adding this word exceed line width?
                    let needed = if line_n == 0 { word_n } else { 1 + word_n };
                    if line_n + needed > LINE_W {
                        // Emit current line
                        let n = line_n;
                        self.push_line(&line[..n], kind, lnk_idx);
                        line_n = 0;
                    }
                    if line_n > 0 { line[line_n] = b' '; line_n += 1; }
                    let wl = word_n.min(LINE_W - line_n);
                    line[line_n..line_n + wl].copy_from_slice(&word[..wl]);
                    line_n += wl;
                    word_n = 0;
                }
            };
        }

        macro_rules! flush_line {
            () => {
                flush_word!();
                if line_n > 0 {
                    let n = line_n;
                    self.push_line(&line[..n], kind, lnk_idx);
                    line_n = 0;
                }
            };
        }

        macro_rules! blank_line {
            () => {
                flush_line!();
                if self.n_lines > 0 && self.line_len[self.n_lines - 1] != 0 {
                    self.push_line(b"", KIND_NORMAL, 0xFF);
                }
            };
        }

        let mut i = 0;
        while i < html.len() {
            let b = html[i];
            i += 1;

            if in_ent {
                // Accumulate HTML entity name: &NAME;
                if b == b';' || ent_n >= 7 {
                    in_ent = false;
                    let ch = decode_entity(&ent[..ent_n]);
                    ent_n = 0;
                    if ch != 0 {
                        // Emit entity char as text
                        if word_n < 79 { word[word_n] = ch; word_n += 1; }
                    }
                } else {
                    ent[ent_n] = b; ent_n += 1;
                }
                continue;
            }

            if in_script || in_style {
                // Skip everything inside script/style until the closing tag.
                // Check for </script> or </style>
                if b == b'<' {
                    // Peek ahead
                    let rem = &html[i..];
                    if rem.starts_with(b"/script>") || rem.starts_with(b"/SCRIPT>") {
                        in_script = false; i += 8;
                    } else if rem.starts_with(b"/style>") || rem.starts_with(b"/STYLE>") {
                        in_style = false; i += 7;
                    }
                }
                continue;
            }

            if in_tag {
                // Inside <tag ...> — accumulate tag name until space, > or /
                if b == b'>' || b == b'/' {
                    in_tag = false;
                    let close = b == b'/';
                    // Skip whitespace / rest of tag until >
                    if b == b'/' {
                        while i < html.len() && html[i] != b'>' { i += 1; }
                        if i < html.len() { i += 1; }
                    }
                    self.dispatch_tag(&tag[..tag_n], close, &href[..href_n],
                                      &mut kind, &mut lnk_idx, &mut in_link,
                                      &mut in_script, &mut in_style,
                                      &mut in_pre, &mut in_title,
                                      &mut line, &mut line_n,
                                      &mut title_buf, &mut title_n,
                                      &mut word, &mut word_n);
                    tag_n = 0; href_n = 0; _in_href = false;
                } else if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' {
                    // Start scanning attributes (for href)
                    self.scan_attrs(html, &mut i, &mut href, &mut href_n, &tag[..tag_n]);
                    // After scan_attrs, we should be at '>' or '/>'
                    // dispatch_tag will be called when we re-enter with '>'
                    let close = i < html.len() && html[i] == b'/';
                    if close { i += 1; }
                    if i < html.len() && html[i] == b'>' { i += 1; }
                    in_tag = false;
                    self.dispatch_tag(&tag[..tag_n], close, &href[..href_n],
                                      &mut kind, &mut lnk_idx, &mut in_link,
                                      &mut in_script, &mut in_style,
                                      &mut in_pre, &mut in_title,
                                      &mut line, &mut line_n,
                                      &mut title_buf, &mut title_n,
                                      &mut word, &mut word_n);
                    tag_n = 0; href_n = 0; _in_href = false;
                } else if tag_n < 31 {
                    // Accumulate tag name (lowercase)
                    tag[tag_n] = to_lower(b); tag_n += 1;
                }
                continue;
            }

            // Text mode
            match b {
                b'<' => {
                    // Check for comment <!-- ... -->
                    if html[i..].starts_with(b"!--") {
                        i += 3;
                        while i + 2 < html.len() {
                            if html[i] == b'-' && html[i+1] == b'-' && html[i+2] == b'>' {
                                i += 3; break;
                            }
                            i += 1;
                        }
                        continue;
                    }
                    // Check for closing tag </
                    in_tag = true;
                    tag_n  = 0;
                    href_n = 0;
                    if i < html.len() && html[i] == b'/' {
                        // Closing tag: read it
                        i += 1;
                        let start = i;
                        while i < html.len() && html[i] != b'>' && html[i] != b' ' { i += 1; }
                        let tname = &html[start..i];
                        if i < html.len() && html[i] == b'>' { i += 1; }
                        in_tag = false;
                        self.dispatch_closing_tag(tname, &mut kind, &mut lnk_idx,
                                                  &mut in_link, &mut in_pre, &mut in_title,
                                                  &mut line, &mut line_n,
                                                  &title_buf[..title_n],
                                                  &mut word, &mut word_n);
                        continue;
                    }
                }
                b'&' => {
                    in_ent = true;
                    ent_n  = 0;
                }
                b'\r' | b'\n' => {
                    if in_pre {
                        flush_line!();
                    } else {
                        // Collapse whitespace
                        if word_n > 0 { flush_word!(); }
                        // Consume additional whitespace
                        while i < html.len() && (html[i] == b'\r' || html[i] == b'\n' || html[i] == b' ' || html[i] == b'\t') {
                            i += 1;
                        }
                        if word_n == 0 && line_n > 0 {
                            // Add a space to separate inline content
                            line[line_n] = b' '; line_n += 1;
                        }
                    }
                }
                b' ' | b'\t' => {
                    if in_pre {
                        if line_n < LINE_W { line[line_n] = b' '; line_n += 1; }
                    } else {
                        flush_word!();
                    }
                }
                _ => {
                    if in_title {
                        if title_n < TTL_W { title_buf[title_n] = b; title_n += 1; }
                    } else if word_n < 79 {
                        word[word_n] = b; word_n += 1;
                    }
                }
            }
        }

        // Flush any remaining content
        flush_line!();
    }

    // Scan attributes looking for href="..." on <a> tags.
    fn scan_attrs(&mut self, html: &[u8], i: &mut usize, href: &mut [u8; LNK_W], href_n: &mut usize, tag: &[u8]) {
        if tag != b"a" { self.skip_to_tag_end(html, i); return; }
        // Scan: key=value pairs until >
        loop {
            if *i >= html.len() { break; }
            let b = html[*i];
            if b == b'>' || b == b'/' { break; }
            *i += 1;
            if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' { continue; }
            // Read attribute name
            let mut attr: [u8; 16] = [0u8; 16];
            let mut an = 0;
            attr[an] = to_lower(b); an += 1;
            while *i < html.len() && html[*i] != b'=' && html[*i] != b'>' && html[*i] != b' ' {
                if an < 15 { attr[an] = to_lower(html[*i]); an += 1; }
                *i += 1;
            }
            if *i < html.len() && html[*i] == b'=' { *i += 1; } else { continue; }
            // Skip optional quotes
            let quote = if *i < html.len() && (html[*i] == b'"' || html[*i] == b'\'') {
                let q = html[*i]; *i += 1; q
            } else { b' ' };
            let val_start = *i;
            // Read value
            while *i < html.len() {
                if html[*i] == quote || (quote == b' ' && (html[*i] == b'>' || html[*i] == b' ')) { break; }
                *i += 1;
            }
            let val = &html[val_start..*i];
            if *i < html.len() && html[*i] == quote { *i += 1; }
            // Is this the href?
            if &attr[..an] == b"href" {
                let n = val.len().min(LNK_W);
                href[..n].copy_from_slice(&val[..n]);
                *href_n = n;
            }
        }
    }

    fn skip_to_tag_end(&mut self, html: &[u8], i: &mut usize) {
        while *i < html.len() && html[*i] != b'>' { *i += 1; }
    }

    fn dispatch_tag(
        &mut self,
        tag: &[u8], close: bool, href: &[u8],
        kind: &mut u8, lnk_idx: &mut u8, in_link: &mut bool,
        in_script: &mut bool, in_style: &mut bool,
        in_pre: &mut bool, in_title: &mut bool,
        line: &mut [u8; LINE_W], line_n: &mut usize,
        _title_buf: &mut [u8; TTL_W], title_n: &mut usize,
        word: &mut [u8; 80], word_n: &mut usize,
    ) {
        macro_rules! fl {
            () => {
                if *word_n > 0 {
                    let needed = if *line_n == 0 { *word_n } else { 1 + *word_n };
                    if *line_n + needed > LINE_W {
                        self.push_line(&line[..*line_n], *kind, *lnk_idx);
                        *line_n = 0;
                    }
                    if *line_n > 0 { line[*line_n] = b' '; *line_n += 1; }
                    let wl = (*word_n).min(LINE_W - *line_n);
                    line[*line_n..*line_n+wl].copy_from_slice(&word[..wl]);
                    *line_n += wl;
                    *word_n = 0;
                }
                if *line_n > 0 {
                    self.push_line(&line[..*line_n], *kind, *lnk_idx);
                    *line_n = 0;
                }
            };
        }
        if close { return; }
        match tag {
            b"script" => { *in_script = true; }
            b"style"  => { *in_style  = true; }
            b"pre" | b"code" => { *in_pre = true; }
            b"title" => { *in_title = true; *title_n = 0; }
            b"h1" | b"h2" | b"h3" | b"h4" | b"h5" | b"h6" => {
                fl!();
                if self.n_lines > 0 { self.push_line(b"", KIND_NORMAL, 0xFF); }
                *kind = KIND_HEADING;
            }
            b"p" => {
                fl!();
                if self.n_lines > 0 && self.line_len[self.n_lines - 1] != 0 {
                    self.push_line(b"", KIND_NORMAL, 0xFF);
                }
            }
            // Structural containers: just flush accumulated text, no blank line.
            b"div" | b"article" | b"section" | b"header" | b"main" | b"footer"
            | b"nav" | b"aside" | b"ul" | b"ol" | b"table" | b"tbody"
            | b"thead" | b"tr" | b"td" | b"th" => {
                fl!();
            }
            b"br" => {
                fl!();
            }
            b"li" => {
                fl!();
                // Prepend bullet as the first word
                word[0] = 0xc2; // UTF-8 would be ideal; use ASCII bullet instead
                word[0] = b'*'; word[1] = b' '; *word_n = 2;
            }
            b"hr" => {
                fl!();
                self.push_line(b"", KIND_HR, 0xFF);
            }
            b"a" => {
                if !href.is_empty() {
                    if self.n_lnk < MAX_LNK {
                        let idx = self.n_lnk;
                        let n = href.len().min(LNK_W);
                        self.lnk_url[idx][..n].copy_from_slice(&href[..n]);
                        self.lnk_len[idx] = n as u8;
                        *lnk_idx = idx as u8;
                        self.n_lnk += 1;
                    }
                    *kind    = KIND_LINK;
                    *in_link = true;
                }
            }
            _ => {}
        }
    }

    fn dispatch_closing_tag(
        &mut self,
        tag: &[u8],
        kind: &mut u8, lnk_idx: &mut u8, in_link: &mut bool,
        in_pre: &mut bool, in_title: &mut bool,
        line: &mut [u8; LINE_W], line_n: &mut usize,
        title_bytes: &[u8],
        word: &mut [u8; 80], word_n: &mut usize,
    ) {
        macro_rules! fl {
            () => {
                if *word_n > 0 {
                    let needed = if *line_n == 0 { *word_n } else { 1 + *word_n };
                    if *line_n + needed > LINE_W {
                        self.push_line(&line[..*line_n], *kind, *lnk_idx);
                        *line_n = 0;
                    }
                    if *line_n > 0 { line[*line_n] = b' '; *line_n += 1; }
                    let wl = (*word_n).min(LINE_W - *line_n);
                    line[*line_n..*line_n+wl].copy_from_slice(&word[..wl]);
                    *line_n += wl;
                    *word_n = 0;
                }
                if *line_n > 0 {
                    self.push_line(&line[..*line_n], *kind, *lnk_idx);
                    *line_n = 0;
                }
            };
        }
        match tag {
            b"pre" | b"code" => { *in_pre = false; fl!(); }
            b"title" => {
                *in_title = false;
                let n = title_bytes.len().min(TTL_W);
                self.title[..n].copy_from_slice(&title_bytes[..n]);
                self.title_len = n;
            }
            b"h1" | b"h2" | b"h3" | b"h4" | b"h5" | b"h6" => {
                fl!();
                *kind = KIND_NORMAL;
                self.push_line(b"", KIND_NORMAL, 0xFF);
            }
            b"p" => {
                fl!();
                if self.n_lines > 0 && self.line_len[self.n_lines - 1] != 0 {
                    self.push_line(b"", KIND_NORMAL, 0xFF);
                }
            }
            // Structural containers: just flush, no blank line.
            b"div" | b"article" | b"section" | b"header" | b"main" | b"footer"
            | b"nav" | b"aside" | b"ul" | b"ol" | b"table" | b"tbody"
            | b"thead" | b"tr" | b"li" => {
                fl!();
            }
            b"a" => {
                if *in_link {
                    fl!();
                    *in_link  = false;
                    *kind     = KIND_NORMAL;
                    *lnk_idx  = 0xFF;
                }
            }
            _ => {}
        }
    }

    fn push_line(&mut self, text: &[u8], kind: u8, lnk: u8) {
        if self.n_lines >= MAX_L { return; }
        let i = self.n_lines;
        let n = text.len().min(LINE_W);
        self.lines[i][..n].copy_from_slice(&text[..n]);
        self.line_len[i]  = n as u16;
        self.line_kind[i] = kind;
        self.line_link[i] = lnk;
        self.n_lines += 1;
        self.dirty = true;
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn set_status_inner(status: &mut [u8; 80], status_n: &mut usize, msg: &[u8]) {
    let n = msg.len().min(80);
    status[..n].copy_from_slice(&msg[..n]);
    *status_n = n;
}

fn to_lower(b: u8) -> u8 {
    if b >= b'A' && b <= b'Z' { b + 32 } else { b }
}

fn decode_entity(name: &[u8]) -> u8 {
    match name {
        b"amp"   => b'&',
        b"lt"    => b'<',
        b"gt"    => b'>',
        b"quot"  => b'"',
        b"apos"  => b'\'',
        b"nbsp"  => b' ',
        b"mdash" | b"ndash" => b'-',
        b"laquo" | b"raquo" => b'"',
        b"copy"  => b'c',
        b"reg"   => b'r',
        b"trade" => b't',
        b"hellip" => b'.',
        _ => 0,
    }
}

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut len = 0;
    while n > 0 { tmp[len] = b'0' + (n % 10) as u8; n /= 10; len += 1; }
    for i in 0..len { if i < buf.len() { buf[i] = tmp[len - 1 - i]; } }
    len
}

fn build_proxy_get(buf: &mut [u8; 512], url: &[u8]) -> usize {
    let mut n = 0;
    macro_rules! w { ($s:expr) => {{
        let s: &[u8] = $s;
        let l = s.len().min(buf.len() - n);
        buf[n..n+l].copy_from_slice(&s[..l]); n += l;
    }}; }
    w!(b"GET ");
    w!(url);
    w!(b" HTTP/1.0\r\nHost: faerie\r\nUser-Agent: DjinnOS/Faerie\r\nAccept: text/html\r\nConnection: close\r\n\r\n");
    n
}

fn recv_all(fd: u64) -> usize {
    let mut total = 0usize;
    let mut idle  = 0usize;
    // The proxy fetches from the internet before it sends back any data.
    // That round-trip can take hundreds of milliseconds.  Each poll() call
    // triggers at most one SLIRP event in QEMU, so we need a large idle
    // budget to cover the proxy's outbound latency before the first byte
    // arrives.  Once data starts flowing, idle resets to 0.
    const IDLE_MAX: usize = 80_000;
    loop {
        crate::net::poll();
        let n = crate::net::tcp_recv(fd, unsafe { &mut RBUF[total..] });
        total += n;
        if n == 0 { idle += 1; } else { idle = 0; }
        if total + 64 >= unsafe { RBUF.len() } || idle > IDLE_MAX { break; }
    }
    total
}
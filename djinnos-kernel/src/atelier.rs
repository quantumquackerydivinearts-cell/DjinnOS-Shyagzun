// Atelier — DjinnOS in-kernel production hub.
//
// The authoring environment for Ko's Labyrinth and the KLGS series,
// running bare-metal inside DjinnOS.
//
// Keys (hub):
//   Up/Down    navigate
//   Enter      open selected tool
//   Escape     return to Ko shell
//
// Keys (filename / URL prompt):
//   Printable  type
//   Backspace  delete
//   Enter      confirm and launch
//   Escape     cancel back to hub
//
// Keys (Character Workshop / Dialogue Forge):
//   Up/Down    scroll
//   Escape     back to hub

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;

const SCALE: u32 = 2;
const CHAR_W: u32 = font::GLYPH_W * SCALE;
const CHAR_H: u32 = font::GLYPH_H * SCALE;
const MX: u32 = 12;
const MY: u32 = 8;

const BG_R: u8 = 0x06; const BG_G: u8 = 0x08; const BG_B: u8 = 0x10;
const HD_R: u8 = 0xc8; const HD_G: u8 = 0x96; const HD_B: u8 = 0x4b;
const TX_R: u8 = 0xc0; const TX_G: u8 = 0xc0; const TX_B: u8 = 0xc0;
const AC_R: u8 = 0x60; const AC_G: u8 = 0xd0; const AC_B: u8 = 0x88;
const HI_R: u8 = 0x10; const HI_G: u8 = 0x28; const HI_B: u8 = 0x18;
const DM_R: u8 = 0x58; const DM_G: u8 = 0x60; const DM_B: u8 = 0x58;
const PR_R: u8 = 0xff; const PR_G: u8 = 0xe0; const PR_B: u8 = 0x40;
const SH_R: u8 = 0x80; const SH_G: u8 = 0x80; const SH_B: u8 = 0x80;

// ── Request ───────────────────────────────────────────────────────────────────

static mut REQUESTED: bool = false;

pub fn request() { unsafe { REQUESTED = true; } }

pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

// ── Input buffer (filename / URL typed by user) ───────────────────────────────

static mut ATL_INPUT:   [u8; 128] = [0u8; 128];
static mut ATL_INPUT_N: usize     = 0;

pub fn launch_input() -> &'static [u8] {
    unsafe { &ATL_INPUT[..ATL_INPUT_N] }
}

// ── Menu ──────────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
enum MenuKey {
    KoStudio,
    Yew,
    Ledger,
    Faerie,
    VoxelLab,
    CharWorkshop,
    DialogueForge,
    Shell,
}

struct MenuItem {
    label: &'static str,
    desc:  &'static str,
    key:   MenuKey,
}

const MENU: &[MenuItem] = &[
    MenuItem { label: "Soa",     desc: "Conscious persistence — Kobra REPL",        key: MenuKey::KoStudio },
    MenuItem { label: "Sao",     desc: "Cup / file / persistent object — editor",   key: MenuKey::Yew },
    MenuItem { label: "Samos",   desc: "Banquet hall — byte table structural map",  key: MenuKey::Ledger },
    MenuItem { label: "Faerie",  desc: "Kyompufwun — HTTP reader via Kyom",         key: MenuKey::Faerie },
    MenuItem { label: "To",      desc: "Scaffold / framework — voxel scene editor", key: MenuKey::VoxelLab },
    MenuItem { label: "Av",      desc: "Relational consciousness — agent registry", key: MenuKey::CharWorkshop },
    MenuItem { label: "Mekha",   desc: "Herald / gateway — scripted dialogue",      key: MenuKey::DialogueForge },
    MenuItem { label: "Ko",      desc: "",                                           key: MenuKey::Shell },
];

const LABEL_COL: u32 = 22; // chars wide for label column

// ── Launch signal ─────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
pub enum AtelierLaunch {
    KoStudio,
    Yew,       // filename in launch_input()
    Ledger,
    Faerie,    // URL in launch_input()
    VoxelLab,
    Shell,
}

// ── Sub-mode ──────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
enum SubMode {
    Hub,
    PromptFilename,
    PromptUrl,
    CharWorkshop,
    DialogueForge,
}

// ── Atelier ───────────────────────────────────────────────────────────────────

pub struct Atelier {
    selected: usize,
    sub_mode: SubMode,
    rule_y:   u32,
    launch:   Option<AtelierLaunch>,
    cw_top:   usize,
    cw_sel:   usize,
    df_top:   usize,
}

impl Atelier {
    pub fn new(rule_y: u32) -> Self {
        Atelier {
            selected: 0,
            sub_mode: SubMode::Hub,
            rule_y,
            launch: None,
            cw_top: 0, cw_sel: 0,
            df_top: 0,
        }
    }

    pub fn reset(&mut self) {
        self.selected = 0;
        self.sub_mode = SubMode::Hub;
        self.launch   = None;
    }

    pub fn consume_launch(&mut self) -> Option<AtelierLaunch> {
        self.launch.take()
    }

    pub fn handle_key(&mut self, key: Key) {
        match self.sub_mode {
            SubMode::Hub            => self.hub_key(key),
            SubMode::PromptFilename => self.prompt_key(key, false),
            SubMode::PromptUrl      => self.prompt_key(key, true),
            SubMode::CharWorkshop   => self.cw_key(key),
            SubMode::DialogueForge  => self.df_key(key),
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        match self.sub_mode {
            SubMode::Hub            => self.render_hub(gpu),
            SubMode::PromptFilename => self.render_prompt(gpu, "Sao  >  Filename:", false),
            SubMode::PromptUrl      => self.render_prompt(gpu, "Faerie  >  URL:", true),
            SubMode::CharWorkshop   => self.render_cw(gpu),
            SubMode::DialogueForge  => self.render_df(gpu),
        }
    }

    // ── Hub ───────────────────────────────────────────────────────────────────

    fn hub_key(&mut self, key: Key) {
        match key {
            Key::Up   => { if self.selected > 0 { self.selected -= 1; } }
            Key::Down => { if self.selected + 1 < MENU.len() { self.selected += 1; } }
            Key::Enter => match MENU[self.selected].key {
                MenuKey::KoStudio     => { self.launch = Some(AtelierLaunch::KoStudio); }
                MenuKey::Yew          => { unsafe { ATL_INPUT_N = 0; } self.sub_mode = SubMode::PromptFilename; }
                MenuKey::Ledger       => { self.launch = Some(AtelierLaunch::Ledger); }
                MenuKey::Faerie       => { unsafe { ATL_INPUT_N = 0; } self.sub_mode = SubMode::PromptUrl; }
                MenuKey::VoxelLab     => { self.launch = Some(AtelierLaunch::VoxelLab); }
                MenuKey::CharWorkshop => { self.cw_top = 0; self.cw_sel = 0; self.sub_mode = SubMode::CharWorkshop; }
                MenuKey::DialogueForge => { self.df_top = 0; self.sub_mode = SubMode::DialogueForge; }
                MenuKey::Shell        => { self.launch = Some(AtelierLaunch::Shell); }
            },
            Key::Escape => { self.launch = Some(AtelierLaunch::Shell); }
            _ => {}
        }
    }

    fn render_hub(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MY;

        // Header
        font::draw_str(gpu, MX, y0, "Kaelshunshikeaninsuy", SCALE, HD_R, HD_G, HD_B);
        let sub = "Ko's Labyrinth  7_KLGS";
        let sub_x = w.saturating_sub(MX + (sub.len() as u32) * CHAR_W);
        font::draw_str(gpu, sub_x, y0, sub, SCALE, DM_R, DM_G, DM_B);

        // Rule
        let rule_y = y0 + CHAR_H + 4;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        let label_x = MX + CHAR_W * 2;
        let desc_x  = label_x + CHAR_W * LABEL_COL;
        let item_y0 = rule_y + MY;
        let max_y   = h.saturating_sub(CHAR_H + 8);

        for (i, item) in MENU.iter().enumerate() {
            let y = item_y0 + i as u32 * (CHAR_H + 4);
            if y + CHAR_H > max_y { break; }

            // Separator before Ko Shell
            if item.key == MenuKey::Shell {
                gpu.fill_rect(label_x, y.saturating_sub(4), w.saturating_sub(label_x + MX), 1,
                              DM_B / 2, DM_G / 2, DM_R / 2);
                font::draw_str(gpu, label_x, y, item.label, SCALE, DM_R, DM_G, DM_B);
                if i == self.selected {
                    gpu.fill_rect(0, y.saturating_sub(2), w, CHAR_H + 4, HI_B, HI_G, HI_R);
                    font::draw_str(gpu, MX, y, ">", SCALE, SH_R, SH_G, SH_B);
                    font::draw_str(gpu, label_x, y, item.label, SCALE, SH_R, SH_G, SH_B);
                }
                continue;
            }

            if i == self.selected {
                gpu.fill_rect(0, y.saturating_sub(2), w, CHAR_H + 4, HI_B, HI_G, HI_R);
                font::draw_str(gpu, MX, y, ">", SCALE, AC_R, AC_G, AC_B);
                font::draw_str(gpu, label_x, y, item.label, SCALE, AC_R, AC_G, AC_B);
            } else {
                font::draw_str(gpu, label_x, y, item.label, SCALE, TX_R, TX_G, TX_B);
            }

            if !item.desc.is_empty() {
                font::draw_str(gpu, desc_x, y, item.desc, SCALE, DM_R, DM_G, DM_B);
            }
        }

        // Status bar
        let sy = h.saturating_sub(CHAR_H + 2);
        font::draw_str(gpu, MX, sy, "Up/Dn navigate   Enter select   Esc to shell",
                       SCALE, DM_R, DM_G, DM_B);
    }

    // ── Prompt ────────────────────────────────────────────────────────────────

    fn prompt_key(&mut self, key: Key, is_url: bool) {
        match key {
            Key::Escape    => { self.sub_mode = SubMode::Hub; }
            Key::Enter     => {
                if unsafe { ATL_INPUT_N } > 0 {
                    self.launch = Some(if is_url { AtelierLaunch::Faerie } else { AtelierLaunch::Yew });
                }
            }
            Key::Backspace => { unsafe { if ATL_INPUT_N > 0 { ATL_INPUT_N -= 1; } } }
            Key::Char(c) if c >= 0x20 => {
                unsafe {
                    if ATL_INPUT_N < 127 {
                        ATL_INPUT[ATL_INPUT_N] = c;
                        ATL_INPUT_N += 1;
                    }
                }
            }
            _ => {}
        }
    }

    fn render_prompt(&self, gpu: &dyn GpuSurface, label: &str, _is_url: bool) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MY;
        font::draw_str(gpu, MX, y0, "Kaelshunshikeaninsuy", SCALE, HD_R, HD_G, HD_B);

        let rule_y = y0 + CHAR_H + 4;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        let py = rule_y + MY * 5;

        // Label
        font::draw_str(gpu, MX, py, label, SCALE, PR_R, PR_G, PR_B);

        // Input text
        let input_x = MX + (label.len() as u32 + 2) * CHAR_W;
        let inp_n = unsafe { ATL_INPUT_N };
        let inp   = unsafe { &ATL_INPUT[..inp_n] };
        if let Ok(s) = core::str::from_utf8(inp) {
            font::draw_str(gpu, input_x, py, s, SCALE, TX_R, TX_G, TX_B);
        }

        // Cursor
        let cx = input_x + inp_n as u32 * CHAR_W;
        if cx + CHAR_W <= w {
            gpu.fill_rect(cx, py, CHAR_W, CHAR_H, AC_B, AC_G, AC_R);
        }

        let sy = h.saturating_sub(CHAR_H + 2);
        font::draw_str(gpu, MX, sy, "Enter open   Esc cancel", SCALE, DM_R, DM_G, DM_B);
    }

    // ── Character Workshop ────────────────────────────────────────────────────

    fn cw_key(&mut self, key: Key) {
        let count = crate::agent::agent_count();
        match key {
            Key::Escape => { self.sub_mode = SubMode::Hub; }
            Key::Up     => { if self.cw_sel > 0 { self.cw_sel -= 1; } }
            Key::Down   => { if count > 0 && self.cw_sel + 1 < count { self.cw_sel += 1; } }
            _ => {}
        }
        if self.cw_sel < self.cw_top { self.cw_top = self.cw_sel; }
        else if self.cw_sel >= self.cw_top + 14 { self.cw_top = self.cw_sel.saturating_sub(13); }
    }

    fn render_cw(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MY;
        font::draw_str(gpu, MX, y0, "Kaelshunshikeaninsuy  >  Av", SCALE, HD_R, HD_G, HD_B);

        let rule_y = y0 + CHAR_H + 4;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        // Column headers
        let col_id   = MX + CHAR_W * 2;
        let col_name = col_id + CHAR_W * 12;
        let col_gate = col_name + CHAR_W * 22;
        let col_lay  = col_gate + CHAR_W * 6;
        let col_mob  = col_lay  + CHAR_W * 5;

        let hdr_y = rule_y + 4;
        font::draw_str(gpu, col_id,   hdr_y, "ID",      SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, col_name, hdr_y, "Name",    SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, col_gate, hdr_y, "Gate",    SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, col_lay,  hdr_y, "Lay",     SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, col_mob,  hdr_y, "Mob",     SCALE, DM_R, DM_G, DM_B);

        let list_y = hdr_y + CHAR_H + 4;
        let vis = ((h.saturating_sub(list_y + CHAR_H + 8)) / (CHAR_H + 2)) as usize;
        let count = crate::agent::agent_count();

        for i in 0..vis {
            let ai = self.cw_top + i;
            if ai >= count { break; }
            let Some(a) = crate::agent::get_by_index(ai) else { break };
            let y = list_y + i as u32 * (CHAR_H + 2);

            if ai == self.cw_sel {
                gpu.fill_rect(0, y.saturating_sub(2), w, CHAR_H + 4, HI_B, HI_G, HI_R);
                font::draw_str(gpu, MX, y, ">", SCALE, AC_R, AC_G, AC_B);
            }

            let (tr, tg, tb) = if ai == self.cw_sel { (AC_R, AC_G, AC_B) } else { (TX_R, TX_G, TX_B) };

            // entity_id
            let id_n = a.entity_id.len().min(10);
            if let Ok(s) = core::str::from_utf8(&a.entity_id[..id_n]) {
                font::draw_str(gpu, col_id, y, s, SCALE, tr, tg, tb);
            }

            // name (first 20 chars)
            let nm_n = a.name.len().min(20);
            if let Ok(s) = core::str::from_utf8(&a.name[..nm_n]) {
                font::draw_str(gpu, col_name, y, s, SCALE, tr, tg, tb);
            }

            // tongue_gate
            let mut tg_buf = [b' '; 4];
            write_u8_dec(&mut tg_buf, a.tongue_gate);
            if let Ok(s) = core::str::from_utf8(trim(&tg_buf)) {
                font::draw_str(gpu, col_gate, y, s, SCALE, DM_R, DM_G, DM_B);
            }

            // max_layer
            let mut lay_buf = [b' '; 4];
            write_u8_dec(&mut lay_buf, a.max_layer);
            if let Ok(s) = core::str::from_utf8(trim(&lay_buf)) {
                font::draw_str(gpu, col_lay, y, s, SCALE, DM_R, DM_G, DM_B);
            }

            // mobius
            if a.mobius_close {
                font::draw_str(gpu, col_mob, y, "M", SCALE, AC_R, AC_G, AC_B);
            }
        }

        // Count line
        let cnt_y = h.saturating_sub(CHAR_H * 2 + 6);
        let mut cbuf = [b' '; 24];
        let lbl = b"Registered: ";
        cbuf[..lbl.len()].copy_from_slice(lbl);
        let n = lbl.len() + write_u32_buf(&mut cbuf[lbl.len()..], count as u32);
        if let Ok(s) = core::str::from_utf8(&cbuf[..n]) {
            font::draw_str(gpu, MX, cnt_y, s, SCALE, DM_R, DM_G, DM_B);
        }

        let sy = h.saturating_sub(CHAR_H + 2);
        font::draw_str(gpu, MX, sy, "Up/Dn navigate   Esc back", SCALE, DM_R, DM_G, DM_B);
    }

    // ── Dialogue Forge ────────────────────────────────────────────────────────

    fn df_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.sub_mode = SubMode::Hub; }
            Key::Up     => { if self.df_top > 0 { self.df_top -= 1; } }
            Key::Down   => { self.df_top = self.df_top.saturating_add(1); }
            _ => {}
        }
    }

    fn render_df(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MY;
        font::draw_str(gpu, MX, y0, "Kaelshunshikeaninsuy  >  Mekha", SCALE, HD_R, HD_G, HD_B);

        let rule_y = y0 + CHAR_H + 4;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        // Info block
        let iy = rule_y + MY;
        font::draw_str(gpu, MX, iy,
            "Dialogue is authored in the Atelier API and synced via Myrun.",
            SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, MX, iy + CHAR_H + 4,
            "Use Sao to edit .ko scripts.  quest_req / flag_req are set in the Atelier.",
            SCALE, DM_R, DM_G, DM_B);

        // Line count
        let total = crate::dialogue::line_count();
        let mut buf = [b' '; 32];
        let lbl = b"Loaded lines: ";
        buf[..lbl.len()].copy_from_slice(lbl);
        let n = lbl.len() + write_u32_buf(&mut buf[lbl.len()..], total as u32);
        if let Ok(s) = core::str::from_utf8(&buf[..n]) {
            font::draw_str(gpu, MX, iy + (CHAR_H + 4) * 3, s, SCALE, TX_R, TX_G, TX_B);
        }

        // Pool breakdown
        let pools: &[(&[u8], usize)] = &[
            (b"Alfir (0006_WTCH)", crate::dialogue::ALFIR_LINES.len()),
            (b"Ko (2021_GODS)",    crate::dialogue::KO_LINES.len()),
            (b"Negaya (1101_VDWR)", crate::dialogue::NEGAYA_LINES.len()),
        ];
        let mut py = iy + (CHAR_H + 4) * 4 + 8;
        for (name, count) in pools {
            if py + CHAR_H > h.saturating_sub(CHAR_H + 8) { break; }
            let mut row = [b' '; 40];
            let nn = name.len().min(22);
            row[..nn].copy_from_slice(&name[..nn]);
            row[24] = b':';
            let cn = write_u32_buf(&mut row[26..], *count as u32);
            if let Ok(s) = core::str::from_utf8(&row[..26 + cn]) {
                font::draw_str(gpu, MX + CHAR_W * 2, py, s, SCALE, TX_R, TX_G, TX_B);
            }
            py += CHAR_H + 2;
        }

        let sy = h.saturating_sub(CHAR_H + 2);
        font::draw_str(gpu, MX, sy, "Esc back", SCALE, DM_R, DM_G, DM_B);
    }
}

// ── Formatting helpers ────────────────────────────────────────────────────────

fn write_u8_dec(buf: &mut [u8], mut n: u8) {
    if buf.is_empty() { return; }
    if n == 0 { buf[0] = b'0'; return; }
    let mut tmp = [0u8; 3]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + n % 10; n /= 10; l += 1; }
    let w = buf.len();
    for i in 0..l.min(w) { buf[i] = tmp[l - 1 - i]; }
}

fn write_u32_buf(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + (n % 10) as u8; n /= 10; l += 1; }
    for i in 0..l.min(buf.len()) { buf[i] = tmp[l - 1 - i]; }
    l
}

fn trim(buf: &[u8]) -> &[u8] {
    let end = buf.iter().position(|&b| b == b' ').unwrap_or(buf.len());
    if end == 0 { &buf[..1] } else { &buf[..end] }
}
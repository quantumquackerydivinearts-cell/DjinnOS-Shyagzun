// atelier.rs -- Kaelshunshikeaninsuy: DjinnOS production hub.
//
// Visual design mirrors the web Atelier (apps/atelier-desktop/):
//   Warm cream palette, 280px sidebar, Inter typography, flat panels.
//   Sidebar: gradient, brand header, nav items with active state.
//   Content: tool-specific view with header bar + status bar.
//
// Navigation:
//   Up/Down / mouse    sidebar item selection
//   Enter              open selected tool
//   Escape             back to Ko shell

use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::render2d::{It, ATL_SIDEBAR_W, ATL_NAV_H, ATL_BRAND_H};
use crate::style;

// ── Request / launch ──────────────────────────────────────────────────────────

static mut REQUESTED: bool = false;
pub fn request()         { unsafe { REQUESTED = true; } }
pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

static mut ATL_INPUT:   [u8; 128] = [0u8; 128];
static mut ATL_INPUT_N: usize     = 0;

pub fn launch_input() -> &'static [u8] {
    unsafe { &ATL_INPUT[..ATL_INPUT_N] }
}

// ── Menu items ────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
pub enum AtelierLaunch {
    KoStudio, Yew, Ledger, Faerie, VoxelLab, Vrsei, Shell,
}

struct NavItem {
    label: &'static str,
    desc:  &'static str,
}

const NAV: &[NavItem] = &[
    NavItem { label: "Soa",      desc: "Mind holding both poles — REPL"           },
    NavItem { label: "Saoshin",  desc: "Cup related seed — file editor"            },
    NavItem { label: "Samos",    desc: "Feast of held ease — byte table"           },
    NavItem { label: "Faerie",   desc: "Kyompufwun — HTTP reader"                  },
    NavItem { label: "To",       desc: "Scaffold before building — voxel lab"      },
    NavItem { label: "Vrsei",    desc: "Rotor shaping space — sculptor"            },
    NavItem { label: "Av",       desc: "Mind holding space — agent registry"       },
    NavItem { label: "Mekha",    desc: "Call held absolute — dialogue forge"       },
    NavItem { label: "Ko",       desc: "Return to shell"                           },
];

// Section break before Ko (index 8) — thin rule separates it.
const SECTION_BREAK: usize = 8;

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
    pub selected: usize,
    sub_mode:     SubMode,
    rule_y:       u32,
    launch:       Option<AtelierLaunch>,
    cw_top:       usize,
    cw_sel:       usize,
    df_top:       usize,
}

impl Atelier {
    pub fn new(rule_y: u32) -> Self {
        Atelier {
            selected: 0, sub_mode: SubMode::Hub,
            rule_y, launch: None,
            cw_top: 0, cw_sel: 0, df_top: 0,
        }
    }

    pub fn reset(&mut self) {
        self.selected = 0;
        self.sub_mode = SubMode::Hub;
        self.launch   = None;
    }

    pub fn consume_launch(&mut self) -> Option<AtelierLaunch> { self.launch.take() }

    // ── Key handling ──────────────────────────────────────────────────────────

    pub fn handle_key(&mut self, key: Key) {
        match self.sub_mode {
            SubMode::Hub            => self.hub_key(key),
            SubMode::PromptFilename => self.prompt_key(key, false),
            SubMode::PromptUrl      => self.prompt_key(key, true),
            SubMode::CharWorkshop   => self.cw_key(key),
            SubMode::DialogueForge  => self.df_key(key),
        }
    }

    fn hub_key(&mut self, key: Key) {
        match key {
            Key::Up     => { if self.selected > 0 { self.selected -= 1; } }
            Key::Down   => { if self.selected + 1 < NAV.len() { self.selected += 1; } }
            Key::Enter  => { self.activate(); }
            Key::Escape => { self.launch = Some(AtelierLaunch::Shell); }
            _ => {}
        }
    }

    fn activate(&mut self) {
        match self.selected {
            0 => { self.launch = Some(AtelierLaunch::KoStudio); }
            1 => { unsafe { ATL_INPUT_N = 0; } self.sub_mode = SubMode::PromptFilename; }
            2 => { self.launch = Some(AtelierLaunch::Ledger); }
            3 => { unsafe { ATL_INPUT_N = 0; } self.sub_mode = SubMode::PromptUrl; }
            4 => { self.launch = Some(AtelierLaunch::VoxelLab); }
            5 => { self.launch = Some(AtelierLaunch::Vrsei); }
            6 => { self.cw_sel = 0; self.cw_top = 0; self.sub_mode = SubMode::CharWorkshop; }
            7 => { self.df_top = 0; self.sub_mode = SubMode::DialogueForge; }
            _ => { self.launch = Some(AtelierLaunch::Shell); }
        }
    }

    fn prompt_key(&mut self, key: Key, is_url: bool) {
        match key {
            Key::Escape    => { self.sub_mode = SubMode::Hub; }
            Key::Enter     => {
                if unsafe { ATL_INPUT_N } > 0 {
                    self.launch = Some(if is_url {
                        AtelierLaunch::Faerie
                    } else {
                        AtelierLaunch::Yew
                    });
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

    fn df_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.sub_mode = SubMode::Hub; }
            Key::Up     => { if self.df_top > 0 { self.df_top -= 1; } }
            Key::Down   => { self.df_top += 1; }
            _ => {}
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    pub fn render(&self, gpu: &dyn GpuSurface) {
        // Switch to warm Atelier theme for this render call.
        let prev_theme = style::get();
        style::set(style::warm_theme());

        let it  = It::new(gpu);
        let y0  = self.rule_y + 4;

        // Full background
        it.fill(0, y0, gpu.width(), gpu.height().saturating_sub(y0), style::get().bg);

        // ── Sidebar ───────────────────────────────────────────────────────────
        it.atl_sidebar(y0);
        it.atl_brand(y0, "Kaelshunshikeaninsuy");

        let nav_y0 = y0 + ATL_BRAND_H + 1;
        for (i, item) in NAV.iter().enumerate() {
            if i == SECTION_BREAK {
                // Thin rule before the last item (Ko shell).
                let sy = nav_y0 + i as u32 * ATL_NAV_H - 6;
                it.fill(16, sy, ATL_SIDEBAR_W - 32, 1, style::get().rule);
            }
            let iy = nav_y0 + i as u32 * ATL_NAV_H;
            it.atl_nav_item(iy, item.label, item.desc, i == self.selected);
        }

        // ── Content area ──────────────────────────────────────────────────────
        it.atl_content_bg(y0);

        match self.sub_mode {
            SubMode::Hub            => self.render_hub_content(&it, y0),
            SubMode::PromptFilename => self.render_prompt(&it, y0, "Open file:", false),
            SubMode::PromptUrl      => self.render_prompt(&it, y0, "Open URL:", true),
            SubMode::CharWorkshop   => self.render_cw(&it, y0),
            SubMode::DialogueForge  => self.render_df(&it, y0),
        }

        // Status bar
        it.atl_status_bar(
            "arrows = navigate   Enter = open   Esc = shell",
            "Kaelshunshikeaninsuy",
        );

        // Restore previous theme
        style::set(prev_theme);
    }

    // ── Hub content (welcome + selected item detail) ──────────────────────────

    fn render_hub_content(&self, it: &It, y0: u32) {
        let t    = style::get();
        let item = &NAV[self.selected];
        let cx   = ATL_SIDEBAR_W + 1;
        let cw   = it.gpu.width().saturating_sub(cx);

        it.atl_header_bar(y0, item.label, item.desc);

        let py = y0 + ATL_BRAND_H + 40;

        // Welcome card
        it.atl_panel(cx + 28, py, cw.saturating_sub(56), 160);

        let card_x = (cx + 44) as i32;
        let card_y = (py + 24) as i32;

        it.tt(card_x, card_y,      "Kaelshunshikeaninsuy", 22.0, t.text);
        it.tt(card_x, card_y + 36, "The authoring environment for Ko's Labyrinth", 14.0, t.text_dim);
        it.tt(card_x, card_y + 58, "and the KLGS series, running bare-metal inside DjinnOS.", 13.0, t.text_dim);

        // Quick action buttons
        it.atl_button(cx + 28, py + 116, 140, 32, "Open Tool", true, false);
        it.atl_button(cx + 180, py + 116, 120, 32, "Ko Shell", false, false);

        // Keyboard hint panel
        let hint_y = py + 196;
        it.tt(cx as i32 + 28, hint_y as i32, "Keyboard", 12.0, t.text_dim);
        it.fill(cx + 28, hint_y + 16, cw.saturating_sub(56), 1, t.rule);

        let hints = [
            ("Up / Down",   "Navigate sidebar"),
            ("Enter",       "Open selected tool"),
            ("Escape",      "Return to Ko shell"),
        ];
        for (i, (key, desc)) in hints.iter().enumerate() {
            let hy = hint_y + 24 + i as u32 * 22;
            it.tt(cx as i32 + 28,  hy as i32, key,  12.0, t.accent);
            it.tt(cx as i32 + 140, hy as i32, desc, 12.0, t.text_dim);
        }
    }

    // ── Prompt (filename / URL input) ─────────────────────────────────────────

    fn render_prompt(&self, it: &It, y0: u32, label: &str, _is_url: bool) {
        let t    = style::get();
        let cx   = ATL_SIDEBAR_W + 1;
        let cw   = it.gpu.width().saturating_sub(cx);
        let tool = if _is_url { "Faerie" } else { "Saoshin" };

        it.atl_header_bar(y0, tool, label);

        let inp_x = cx + 28;
        let inp_y = y0 + ATL_BRAND_H + 60;
        let inp_w = cw.saturating_sub(56).min(560);

        // Label
        it.tt(inp_x as i32, inp_y as i32 - 22, label, 13.0, t.text_dim);

        // Input field
        let inp_n = unsafe { ATL_INPUT_N };
        let inp   = unsafe { &ATL_INPUT[..inp_n] };
        let val   = core::str::from_utf8(inp).unwrap_or("");
        it.atl_input(inp_x, inp_y, inp_w, "Type here...", val, true);

        // Action buttons
        it.atl_button(inp_x, inp_y + 52, 120, 32, "Open", true, false);
        it.atl_button(inp_x + 136, inp_y + 52, 100, 32, "Cancel", false, false);
    }

    // ── Character Workshop ────────────────────────────────────────────────────

    fn render_cw(&self, it: &It, y0: u32) {
        let t  = style::get();
        let cx = ATL_SIDEBAR_W + 1;
        let cw = it.gpu.width().saturating_sub(cx);

        it.atl_header_bar(y0, "Av", "Agent registry — character workshop");

        let count   = crate::agent::agent_count();
        let tab_y   = y0 + ATL_BRAND_H;
        it.atl_tab_bar(&["Agents", "Coil", "Attestations"], 0, tab_y);

        let list_y  = tab_y + 36 + 16;
        let row_h   = 40u32;
        let vis     = ((it.gpu.height().saturating_sub(list_y + 40)) / row_h) as usize;

        // Column headers
        let col_id   = cx + 28;
        let col_name = cx + 140;
        let col_gate = cx + 340;
        let col_lay  = cx + 500;

        it.tt(col_id   as i32, list_y as i32, "ID",       11.0, t.text_dim);
        it.tt(col_name as i32, list_y as i32, "Name",     11.0, t.text_dim);
        it.tt(col_gate as i32, list_y as i32, "Gate",     11.0, t.text_dim);
        it.tt(col_lay  as i32, list_y as i32, "Layer",    11.0, t.text_dim);
        it.fill(cx, list_y + 16, cw.saturating_sub(28), 1, t.rule);

        for vi in 0..vis {
            let si = self.cw_top + vi;
            if si >= count { break; }
            let row_y = list_y + 20 + vi as u32 * row_h;
            let sel   = si == self.cw_sel;

            if sel {
                it.fill(cx, row_y - 4, cw.saturating_sub(28), row_h, t.selection);
            }
            let tc = if sel { t.accent } else { t.text };

            if let Some(ag) = crate::agent::get_by_index(si) {
                it.tt_mono(col_id   as i32, row_y as i32,
                    core::str::from_utf8(ag.entity_id).unwrap_or("?"), 12.0, tc);
                it.tt(col_name as i32, row_y as i32,
                    core::str::from_utf8(ag.name).unwrap_or("?"), 13.0, tc);
                it.tt(col_gate as i32, row_y as i32,
                    if ag.tongue_gate > 0 { "gated" } else { "open" }, 12.0, t.text_dim);
                let mut lb = [0u8; 4]; lb[0] = b'0' + ag.max_layer / 10; lb[1] = b'0' + ag.max_layer % 10;
                it.tt_mono(col_lay as i32, row_y as i32,
                    core::str::from_utf8(&lb[..2]).unwrap_or("?"), 12.0, t.text_dim);
            }
        }

        if count == 0 {
            let ey = list_y + 48;
            it.tt(cx as i32 + 28, ey as i32, "No agents registered.", 14.0, t.text_dim);
        }
    }

    // ── Dialogue Forge ────────────────────────────────────────────────────────

    fn render_df(&self, it: &It, y0: u32) {
        let t  = style::get();
        let cx = ATL_SIDEBAR_W + 1;
        let cw = it.gpu.width().saturating_sub(cx);

        it.atl_header_bar(y0, "Mekha", "Dialogue forge — scripted line pools");

        let tab_y = y0 + ATL_BRAND_H;
        it.atl_tab_bar(&["Lines", "Coil", "Attestations"], 0, tab_y);

        let pool_count = crate::dialogue::line_count();
        let list_y     = tab_y + 36 + 16;
        let row_h      = 36u32;
        let vis        = ((it.gpu.height().saturating_sub(list_y + 40)) / row_h) as usize;

        // Header row
        let col_id   = cx + 28;
        let col_ent  = cx + 130;
        let col_kind = cx + 280;
        let col_gate = cx + 420;

        it.tt(col_id   as i32, list_y as i32, "Line ID",    11.0, t.text_dim);
        it.tt(col_ent  as i32, list_y as i32, "Entity",     11.0, t.text_dim);
        it.tt(col_kind as i32, list_y as i32, "Kind",       11.0, t.text_dim);
        it.tt(col_gate as i32, list_y as i32, "Quest gate", 11.0, t.text_dim);
        it.fill(cx, list_y + 16, cw.saturating_sub(28), 1, t.rule);

        // Pool summary (per-entity counts from all pools)
        let pools: &[(&[u8], &[crate::dialogue::DialogueLine])] = &[
            (b"0006_WTCH", crate::dialogue::ALFIR_LINES),
            (b"2021_GODS", crate::dialogue::KO_LINES),
            (b"2003_VDWR", crate::dialogue::NEGAYA_LINES),
            (b"0020_TOWN", crate::dialogue::SIDHAL_LINES),
            (b"0021_TOWN", crate::dialogue::WELLS_LINES),
            (b"0022_TOWN", crate::dialogue::LAVELLE_LINES),
            (b"0007_WTCH", crate::dialogue::FOREST_WITCH_LINES),
            (b"0017_ROYL", crate::dialogue::NEXIOTT_LINES),
            (b"1018_DJNN", crate::dialogue::DROVITTH_LINES),
            (b"0024_TOWN", crate::dialogue::ELSA_LINES),
            (b"0000_0451", crate::dialogue::HYPATIA_EARLY_LINES),
        ];

        for (vi, &(eid, pool)) in pools.iter().skip(self.df_top).take(vis).enumerate() {
            let row_y = list_y + 20 + vi as u32 * row_h;
            let name  = core::str::from_utf8(eid).unwrap_or("?");
            it.tt_mono(col_ent as i32, row_y as i32, name, 12.0, t.text);
            let mut nb = [0u8; 4]; let n = pool.len();
            nb[0] = b'0' + (n / 10) as u8; nb[1] = b'0' + (n % 10) as u8;
            it.tt(col_id as i32, row_y as i32,
                core::str::from_utf8(&nb[..2]).unwrap_or("?"), 12.0, t.text_dim);
            it.tt(col_kind as i32, row_y as i32, "mixed", 12.0, t.text_dim);
        }

        // Total badge
        let mut tb = [0u8; 6]; let tp = pool_count;
        let mut idx = 0; let mut v = tp;
        while v > 0 && idx < 6 { tb[idx] = b'0' + (v % 10) as u8; idx += 1; v /= 10; }
        tb[..idx].reverse();
        let ts = core::str::from_utf8(&tb[..idx.max(1)]).unwrap_or("0");
        it.atl_badge(cx + cw.saturating_sub(120), list_y - 4, ts, t.accent);
    }
}

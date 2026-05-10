// Vrsei - voxel model sculptor.
//
// Vr(94, Daisy, Rotor/Tensor) + Sei(203, Cannabis, Conscious spatial action).
// The rotor that consciously shapes space.
//
// 4-panel layout (editor state):
//   Top-left:  Isometric preview
//   Top-right: Top-down  (XZ) orthographic grid
//   Bot-left:  Front     (XY) orthographic grid
//   Bot-right: Side      (ZY) orthographic grid
//
// Browser state: scrollable list of .vxm files from Sa volume.
//
// Keys (browser):
//   Up/Down    navigate
//   Enter      open selected model
//   N          new model (name prompt)
//   D          delete selected model
//   Esc        exit to Atelier
//
// Keys (editor):
//   Tab        cycle active panel (Iso -> Top -> Front -> Side)
//   Arrows     move cursor in active panel's 2D axes
//   [ / ]      Y layer (all panels)
//   Enter      place voxel
//   Backspace  erase voxel
//   M          cycle material
//   T          cycle structural type
//   X          toggle X-axis symmetry
//   Ctrl+S     save .vxm to Sa volume
//   Esc        return to browser

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::palette;
use crate::renderer_bridge::CannabisMode;
use crate::voxel::{
    VoxelNode, VA, VO, VI, VY,
    FACE_JY, FACE_JI, FACE_JE,
    JY, JI, JE,
    iso_x, iso_y,
    draw_face_jy, draw_face_ji, draw_face_je,
};

const SCALE:     u32   = 2;
const CHAR_W:    u32   = font::GLYPH_W * SCALE;
const CHAR_H:    u32   = font::GLYPH_H * SCALE;
const MX:        u32   = 8;
const MOD:       usize = 16;
const MAX_MODELS:usize = 64;

const BG_R: u8 = 0x06; const BG_G: u8 = 0x08; const BG_B: u8 = 0x0e;
const HD_R: u8 = 0xc8; const HD_G: u8 = 0x96; const HD_B: u8 = 0x4b;
const TX_R: u8 = 0xc0; const TX_G: u8 = 0xc0; const TX_B: u8 = 0xc0;
const AC_R: u8 = 0x60; const AC_G: u8 = 0xd0; const AC_B: u8 = 0x88;
const DM_R: u8 = 0x58; const DM_G: u8 = 0x60; const DM_B: u8 = 0x58;
const HI_R: u8 = 0x10; const HI_G: u8 = 0x28; const HI_B: u8 = 0x18;
const MO_R: u8 = 0xd0; const MO_G: u8 = 0x60; const MO_B: u8 = 0x60;
const PL_R: u8 = 0x10; const PL_G: u8 = 0x18; const PL_B: u8 = 0x28;
const SL_R: u8 = 0x20; const SL_G: u8 = 0x30; const SL_B: u8 = 0x20;

// ── Request ───────────────────────────────────────────────────────────────────

static mut REQUESTED: bool = false;
pub fn request() { unsafe { REQUESTED = true; } }
pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

// ── Model storage (16KB in BSS) ───────────────────────────────────────────────

static mut VR_NODES: [[[VoxelNode; MOD]; MOD]; MOD] =
    [[[VoxelNode::AIR; MOD]; MOD]; MOD];

fn vr_get(x: usize, y: usize, z: usize) -> VoxelNode {
    if x < MOD && y < MOD && z < MOD { unsafe { VR_NODES[x][y][z] } }
    else { VoxelNode::AIR }
}
fn vr_set(x: usize, y: usize, z: usize, n: VoxelNode) {
    if x < MOD && y < MOD && z < MOD { unsafe { VR_NODES[x][y][z] = n; } }
}
fn vr_is_air(x: usize, y: usize, z: usize) -> bool { vr_get(x, y, z).is_air() }

// Public accessors for mesh.rs
pub const MOD_PUB: usize = MOD;
pub fn vr_is_air_pub(x: usize, y: usize, z: usize) -> bool { vr_is_air(x, y, z) }
pub fn vr_mat_pub(x: usize, y: usize, z: usize) -> u8 {
    if vr_is_air(x, y, z) { b' ' } else { vr_get(x, y, z).material }
}

fn vr_cull(x: usize, y: usize, z: usize) {
    if vr_is_air(x, y, z) { return; }
    let jy = y + 1 >= MOD || vr_is_air(x, y + 1, z);
    let ji = x + 1 >= MOD || vr_is_air(x + 1, y, z);
    let je = x == 0       || vr_is_air(x - 1, y, z);
    let mut f = 0u8;
    if jy { f |= FACE_JY; }
    if ji { f |= FACE_JI; }
    if je { f |= FACE_JE; }
    unsafe { VR_NODES[x][y][z].faces = f; }
}

fn vr_cull_neighborhood(x: usize, y: usize, z: usize) {
    vr_cull(x, y, z);
    if x > 0       { vr_cull(x - 1, y, z); }
    if x + 1 < MOD { vr_cull(x + 1, y, z); }
    if y > 0       { vr_cull(x, y - 1, z); }
    if y + 1 < MOD { vr_cull(x, y + 1, z); }
    if z > 0       { vr_cull(x, y, z - 1); }
    if z + 1 < MOD { vr_cull(x, y, z + 1); }
}

fn vr_clear() {
    unsafe { VR_NODES = [[[VoxelNode::AIR; MOD]; MOD]; MOD]; }
}

// ── File format (.vxm) ────────────────────────────────────────────────────────
// [0..4]   magic "VM01"
// [4..36]  name  (32 bytes, null-padded)
// [36..39] w, h, d (each u8, currently always 16)
// [39..43] node count (u32 LE)
// [43..]   per node: x y z sak_type material (5 bytes each)

const VXM_MAGIC: &[u8; 4] = b"VM01";
const VXM_HDR:  usize     = 43;
const VXM_NODE: usize     = 5;
const VXM_MAX:  usize     = VXM_HDR + MOD * MOD * MOD * VXM_NODE;

static mut VXM_SCRATCH: [u8; VXM_MAX] = [0u8; VXM_MAX];

fn vxm_save(name: &[u8]) -> bool {
    let mut count = 0u32;
    for x in 0..MOD { for y in 0..MOD { for z in 0..MOD {
        if !vr_is_air(x, y, z) { count += 1; }
    }}}
    let total = VXM_HDR + count as usize * VXM_NODE;
    let buf = unsafe { &mut VXM_SCRATCH };
    buf[0..4].copy_from_slice(VXM_MAGIC);
    let nn = name.len().min(32);
    buf[4..4 + nn].copy_from_slice(&name[..nn]);
    buf[4 + nn..36].fill(0);
    buf[36] = MOD as u8; buf[37] = MOD as u8; buf[38] = MOD as u8;
    buf[39..43].copy_from_slice(&count.to_le_bytes());
    let mut off = VXM_HDR;
    for x in 0..MOD { for y in 0..MOD { for z in 0..MOD {
        let n = vr_get(x, y, z);
        if n.is_air() { continue; }
        buf[off]     = x as u8;
        buf[off + 1] = y as u8;
        buf[off + 2] = z as u8;
        buf[off + 3] = n.sak_type;
        buf[off + 4] = n.material;
        off += VXM_NODE;
    }}}
    crate::sa::write_file(name, &buf[..total])
}

fn vxm_load(name: &[u8]) -> bool {
    let buf = unsafe { &mut VXM_SCRATCH };
    let n = crate::sa::read_file(name, buf);
    if n < VXM_HDR { return false; }
    if &buf[0..4] != VXM_MAGIC { return false; }
    let count = u32::from_le_bytes([buf[39], buf[40], buf[41], buf[42]]) as usize;
    if n < VXM_HDR + count * VXM_NODE { return false; }
    vr_clear();
    let mut off = VXM_HDR;
    for _ in 0..count {
        let x = buf[off] as usize;
        let y = buf[off + 1] as usize;
        let z = buf[off + 2] as usize;
        let s = buf[off + 3];
        let m = buf[off + 4];
        off += VXM_NODE;
        if x < MOD && y < MOD && z < MOD {
            vr_set(x, y, z, VoxelNode {
                sak_type: s, faces: FACE_JY | FACE_JI | FACE_JE,
                material: m, adjacency: crate::voxel::DO,
            });
        }
    }
    for x in 0..MOD { for y in 0..MOD { for z in 0..MOD { vr_cull(x, y, z); }}}
    true
}

// ── Material palette ──────────────────────────────────────────────────────────

struct MatDef { ch: u8, name: &'static str, stype: u8 }
const MATS: &[MatDef] = &[
    MatDef { ch: b'.', name: "floor",   stype: VA },
    MatDef { ch: b'#', name: "wall",    stype: VA },
    MatDef { ch: b',', name: "grass",   stype: VO },
    MatDef { ch: b'D', name: "dirt",    stype: VO },
    MatDef { ch: b'S', name: "stone",   stype: VA },
    MatDef { ch: b'~', name: "water",   stype: VO },
    MatDef { ch: b'T', name: "tree",    stype: VY },
    MatDef { ch: b'M', name: "marble",  stype: VA },
    MatDef { ch: b'Y', name: "brick",   stype: VA },
    MatDef { ch: b'C', name: "ceramic", stype: VA },
    MatDef { ch: b'L', name: "slate",   stype: VA },
    MatDef { ch: b'X', name: "silica",  stype: VA },
];

const STYPES: &[(u8, &str)] = &[
    (VA, "Va"), (VO, "Vo"), (VI, "Vi"), (VY, "Vy"),
];

// ── Panel enum ────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
enum Panel { Iso, Top, Front, Side }

impl Panel {
    fn next(self) -> Self {
        match self { Panel::Iso => Panel::Top, Panel::Top => Panel::Front,
                     Panel::Front => Panel::Side, Panel::Side => Panel::Iso }
    }
    fn label(self) -> &'static str {
        match self { Panel::Iso => "Iso", Panel::Top => "Top (XZ)",
                     Panel::Front => "Front (XY)", Panel::Side => "Side (ZY)" }
    }
}

// ── State enum ────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
enum VrseiState { Browser, NewPrompt, Editor }

// ── Vrsei ─────────────────────────────────────────────────────────────────────

pub struct Vrsei {
    state:     VrseiState,
    exporting: bool,   // true = export format prompt visible
    // -- browser
    br_list:  [[u8; 32]; MAX_MODELS],
    br_n:     usize,
    br_sel:   usize,
    br_top:   usize,
    br_input: [u8; 32],
    br_inp_n: usize,
    // -- editor
    panel:    Panel,
    cx: usize, cy: usize, cz: usize,
    mat_idx:  usize,
    type_idx: usize,
    sym_x:    bool,
    name:     [u8; 32],
    name_n:   usize,
    modified: bool,
    rule_y:   u32,
    exited:   bool,
}

impl Vrsei {
    pub fn new(rule_y: u32) -> Self {
        Vrsei {
            state: VrseiState::Browser,
            exporting: false,
            br_list: [[0u8; 32]; MAX_MODELS],
            br_n: 0, br_sel: 0, br_top: 0,
            br_input: [0u8; 32], br_inp_n: 0,
            panel: Panel::Iso,
            cx: MOD / 2, cy: 1, cz: MOD / 2,
            mat_idx: 0, type_idx: 0,
            sym_x: false,
            name: [0u8; 32], name_n: 0,
            modified: false,
            rule_y,
            exited: false,
        }
    }

    pub fn exited(&self) -> bool { self.exited }

    pub fn open(&mut self) {
        self.exited = false;
        self.state  = VrseiState::Browser;
        self.populate_browser();
    }

    fn populate_browser(&mut self) {
        let list = &mut self.br_list;
        let n    = &mut self.br_n;
        *n = 0;
        crate::sa::for_each(|name, _| {
            if name.ends_with(b".vxm") && *n < MAX_MODELS {
                let len = name.len().min(32);
                list[*n][..len].copy_from_slice(&name[..len]);
                list[*n][len..].fill(0);
                *n += 1;
            }
        });
        if self.br_sel >= self.br_n && self.br_n > 0 {
            self.br_sel = self.br_n - 1;
        }
    }

    pub fn handle_key(&mut self, key: Key) {
        match self.state {
            VrseiState::Browser   => self.browser_key(key),
            VrseiState::NewPrompt => self.new_prompt_key(key),
            VrseiState::Editor    => self.editor_key(key),
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        match self.state {
            VrseiState::Browser | VrseiState::NewPrompt => self.render_browser(gpu),
            VrseiState::Editor                          => self.render_editor(gpu),
        }
    }

    // ── Browser keys ─────────────────────────────────────────────────────────

    fn browser_key(&mut self, key: Key) {
        match key {
            Key::Up   => { if self.br_sel > 0 { self.br_sel -= 1; } }
            Key::Down => { if self.br_sel + 1 < self.br_n { self.br_sel += 1; } }
            Key::Enter => {
                if self.br_n > 0 {
                    let name = &self.br_list[self.br_sel];
                    let nn = name.iter().position(|&b| b == 0).unwrap_or(32);
                    vxm_load(&name[..nn]);
                    self.name[..nn].copy_from_slice(&name[..nn]);
                    self.name_n = nn;
                    self.modified = false;
                    self.cx = MOD / 2; self.cy = 1; self.cz = MOD / 2;
                    self.state = VrseiState::Editor;
                }
            }
            Key::Char(b'n') | Key::Char(b'N') => {
                self.br_input = [0u8; 32];
                self.br_inp_n = 0;
                self.state = VrseiState::NewPrompt;
            }
            Key::Char(b'd') | Key::Char(b'D') => {
                if self.br_n > 0 {
                    let name = &self.br_list[self.br_sel];
                    let nn = name.iter().position(|&b| b == 0).unwrap_or(32);
                    crate::sa::delete_file(&name[..nn]);
                    self.populate_browser();
                }
            }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
        // scroll
        if self.br_sel < self.br_top { self.br_top = self.br_sel; }
        else if self.br_sel >= self.br_top + 16 { self.br_top = self.br_sel.saturating_sub(15); }
    }

    fn new_prompt_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.state = VrseiState::Browser; }
            Key::Enter  => {
                if self.br_inp_n > 0 {
                    // Auto-append .vxm if missing
                    let has_ext = self.br_inp_n >= 4
                        && &self.br_input[self.br_inp_n - 4..self.br_inp_n] == b".vxm";
                    let mut fname = [0u8; 32];
                    let base_n = self.br_inp_n.min(28);
                    fname[..base_n].copy_from_slice(&self.br_input[..base_n]);
                    let full_n = if has_ext { base_n } else {
                        let ext = b".vxm";
                        if base_n + 4 <= 32 {
                            fname[base_n..base_n + 4].copy_from_slice(ext);
                            base_n + 4
                        } else { base_n }
                    };
                    vr_clear();
                    self.name[..full_n].copy_from_slice(&fname[..full_n]);
                    self.name_n = full_n;
                    self.modified = true;
                    self.cx = MOD / 2; self.cy = 1; self.cz = MOD / 2;
                    self.state = VrseiState::Editor;
                }
            }
            Key::Backspace => { if self.br_inp_n > 0 { self.br_inp_n -= 1; } }
            Key::Char(c) if c >= 0x20 => {
                if self.br_inp_n < 28 {
                    self.br_input[self.br_inp_n] = c;
                    self.br_inp_n += 1;
                }
            }
            _ => {}
        }
    }

    // ── Editor keys ───────────────────────────────────────────────────────────

    fn editor_key(&mut self, key: Key) {
        // Export prompt intercepts all keys
        if self.exporting {
            match key {
                Key::Char(b's') | Key::Char(b'S') => {
                    crate::mesh::export_stl(&self.name[..self.name_n]);
                    self.exporting = false;
                }
                Key::Char(b'o') | Key::Char(b'O') => {
                    crate::mesh::export_obj(&self.name[..self.name_n]);
                    self.exporting = false;
                }
                Key::Escape => { self.exporting = false; }
                _ => {}
            }
            return;
        }
        match key {
            Key::Escape    => { self.state = VrseiState::Browser; self.populate_browser(); }
            Key::Char(0x13)=> { if self.modified { vxm_save(&self.name[..self.name_n]); self.modified = false; } }
            Key::Char(0x05)=> { self.exporting = true; } // Ctrl+E
            Key::Char(b'\t')=> { self.panel = self.panel.next(); }

            // Y axis (all panels)
            Key::Char(b'[') => { if self.cy > 0         { self.cy -= 1; } }
            Key::Char(b']') => { if self.cy + 1 < MOD   { self.cy += 1; } }

            // Cursor movement per panel
            Key::Right => match self.panel {
                Panel::Iso | Panel::Top | Panel::Front => { if self.cx + 1 < MOD { self.cx += 1; } }
                Panel::Side => { if self.cz + 1 < MOD  { self.cz += 1; } }
            },
            Key::Left => match self.panel {
                Panel::Iso | Panel::Top | Panel::Front => { if self.cx > 0 { self.cx -= 1; } }
                Panel::Side => { if self.cz > 0         { self.cz -= 1; } }
            },
            Key::Down => match self.panel {
                Panel::Iso | Panel::Top => { if self.cz + 1 < MOD { self.cz += 1; } }
                Panel::Front | Panel::Side => { if self.cy > 0     { self.cy -= 1; } }
            },
            Key::Up => match self.panel {
                Panel::Iso | Panel::Top => { if self.cz > 0         { self.cz -= 1; } }
                Panel::Front | Panel::Side => { if self.cy + 1 < MOD { self.cy += 1; } }
            },

            // Place / erase
            Key::Enter => { self.place(); }
            Key::Backspace => { self.erase(); }

            // Material / type / symmetry
            Key::Char(b'm') | Key::Char(b'M') => { self.mat_idx = (self.mat_idx + 1) % MATS.len(); }
            Key::Char(b't') | Key::Char(b'T') => { self.type_idx = (self.type_idx + 1) % STYPES.len(); }
            Key::Char(b'x') | Key::Char(b'X') => { self.sym_x = !self.sym_x; }

            _ => {}
        }
    }

    fn place(&mut self) {
        let mat = MATS[self.mat_idx].ch;
        let stype = STYPES[self.type_idx].0;
        let node = VoxelNode {
            sak_type: stype, faces: FACE_JY | FACE_JI | FACE_JE,
            material: mat, adjacency: crate::voxel::DO,
        };
        vr_set(self.cx, self.cy, self.cz, node);
        vr_cull_neighborhood(self.cx, self.cy, self.cz);
        if self.sym_x {
            let mx = MOD - 1 - self.cx;
            vr_set(mx, self.cy, self.cz, node);
            vr_cull_neighborhood(mx, self.cy, self.cz);
        }
        self.modified = true;
    }

    fn erase(&mut self) {
        vr_set(self.cx, self.cy, self.cz, VoxelNode::AIR);
        vr_cull_neighborhood(self.cx, self.cy, self.cz);
        if self.sym_x {
            let mx = MOD - 1 - self.cx;
            vr_set(mx, self.cy, self.cz, VoxelNode::AIR);
            vr_cull_neighborhood(mx, self.cy, self.cz);
        }
        self.modified = true;
    }

    // ── Browser render ────────────────────────────────────────────────────────

    fn render_browser(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();
        gpu.fill_rect(0, floor, w, h.saturating_sub(floor), BG_B, BG_G, BG_R);

        let y0 = floor + MX;
        font::draw_str(gpu, MX, y0, "Vrsei", SCALE, HD_R, HD_G, HD_B);
        let sub = "Model Browser";
        font::draw_str(gpu, MX + CHAR_W * 8, y0, sub, SCALE, DM_R, DM_G, DM_B);

        let rule_y = y0 + CHAR_H + 4;
        gpu.fill_rect(MX, rule_y, w.saturating_sub(MX * 2), 1, DM_B, DM_G, DM_R);

        let list_y = rule_y + MX;
        let vis = ((h.saturating_sub(list_y + CHAR_H * 3 + 8)) / (CHAR_H + 2)) as usize;

        if self.br_n == 0 {
            font::draw_str(gpu, MX, list_y, "No .vxm models in Sa volume.",
                           SCALE, DM_R, DM_G, DM_B);
            font::draw_str(gpu, MX, list_y + CHAR_H + 4,
                           "Press N to create the first model.",
                           SCALE, DM_R, DM_G, DM_B);
        } else {
            for i in 0..vis {
                let idx = self.br_top + i;
                if idx >= self.br_n { break; }
                let y = list_y + i as u32 * (CHAR_H + 2);
                let sel = idx == self.br_sel;
                if sel {
                    gpu.fill_rect(0, y.saturating_sub(2), w, CHAR_H + 4, HI_B, HI_G, HI_R);
                    font::draw_str(gpu, MX, y, ">", SCALE, AC_R, AC_G, AC_B);
                }
                let name = &self.br_list[idx];
                let nn = name.iter().position(|&b| b == 0).unwrap_or(32);
                if let Ok(s) = core::str::from_utf8(&name[..nn]) {
                    let (r, g, b) = if sel { (AC_R, AC_G, AC_B) } else { (TX_R, TX_G, TX_B) };
                    font::draw_str(gpu, MX + CHAR_W * 2, y, s, SCALE, r, g, b);
                }
            }
        }

        // New prompt overlay
        if self.state == VrseiState::NewPrompt {
            let py = h.saturating_sub(CHAR_H * 3 + 12);
            gpu.fill_rect(0, py.saturating_sub(4), w, CHAR_H * 2 + 16, PL_B, PL_G, PL_R);
            font::draw_str(gpu, MX, py, "New model name:", SCALE, HD_R, HD_G, HD_B);
            let inp_y = py + CHAR_H + 4;
            if let Ok(s) = core::str::from_utf8(&self.br_input[..self.br_inp_n]) {
                font::draw_str(gpu, MX, inp_y, s, SCALE, TX_R, TX_G, TX_B);
            }
            let cx = MX + self.br_inp_n as u32 * CHAR_W;
            gpu.fill_rect(cx, inp_y, CHAR_W, CHAR_H, AC_B, AC_G, AC_R);
        }

        let sy = h.saturating_sub(CHAR_H + 2);
        let hint = if self.state == VrseiState::NewPrompt {
            "Enter confirm   Esc cancel"
        } else {
            "Enter open   N new   D delete   Esc exit"
        };
        font::draw_str(gpu, MX, sy, hint, SCALE, DM_R, DM_G, DM_B);
    }

    // ── Editor render ─────────────────────────────────────────────────────────

    fn render_editor(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let w = gpu.width();
        let h = gpu.height();

        // Header
        gpu.fill_rect(0, floor, w, CHAR_H + 6, 0x0e, 0x08, 0x06);
        font::draw_str(gpu, MX, floor + 2, "Vrsei", SCALE, HD_R, HD_G, HD_B);
        if self.name_n > 0 {
            if let Ok(s) = core::str::from_utf8(&self.name[..self.name_n]) {
                font::draw_str(gpu, MX + CHAR_W * 8, floor + 2, s, SCALE, TX_R, TX_G, TX_B);
            }
        }
        if self.modified {
            let mx = MX + (self.name_n as u32 + 9) * CHAR_W;
            font::draw_str(gpu, mx, floor + 2, "[*]", SCALE, MO_R, MO_G, MO_B);
        }
        // Panel label + sym indicator (top right)
        let lbl = self.panel.label();
        let sym = if self.sym_x { "  X-sym ON" } else { "" };
        let lx = w.saturating_sub(MX + (lbl.len() as u32 + sym.len() as u32 + 1) * CHAR_W);
        font::draw_str(gpu, lx, floor + 2, lbl, SCALE, AC_R, AC_G, AC_B);
        if self.sym_x {
            font::draw_str(gpu, lx + (lbl.len() as u32 + 1) * CHAR_W, floor + 2,
                           sym, SCALE, HD_R, HD_G, HD_B);
        }

        let hdr_h   = CHAR_H + 6;
        let stat_h  = CHAR_H + 4;
        let content_y = floor + hdr_h;
        let content_h = h.saturating_sub(content_y + stat_h);
        let half_w  = w / 2;
        let half_h  = content_h / 2;

        // Dividers
        gpu.fill_rect(half_w, content_y, 1, content_h, DM_B, DM_G, DM_R);
        gpu.fill_rect(0, content_y + half_h, w, 1, DM_B, DM_G, DM_R);

        // Four panels
        let panels = [
            (Panel::Iso,   0u32,   content_y),
            (Panel::Top,   half_w, content_y),
            (Panel::Front, 0u32,   content_y + half_h + 1),
            (Panel::Side,  half_w, content_y + half_h + 1),
        ];
        for (p, px, py) in panels {
            let pw = half_w.saturating_sub(1);
            let ph = half_h.saturating_sub(1);
            let active = p == self.panel;
            if active {
                gpu.fill_rect(px, py, pw, ph, SL_B, SL_G, SL_R);
            } else {
                gpu.fill_rect(px, py, pw, ph, BG_B, BG_G, BG_R);
            }
            match p {
                Panel::Iso   => self.draw_iso(gpu, px, py, pw, ph),
                Panel::Top   => self.draw_ortho_top(gpu, px, py, pw, ph, active),
                Panel::Front => self.draw_ortho_front(gpu, px, py, pw, ph, active),
                Panel::Side  => self.draw_ortho_side(gpu, px, py, pw, ph, active),
            }
        }

        // Export prompt overlay
        if self.exporting {
            let ey = h / 2 - CHAR_H * 2;
            gpu.fill_rect(w / 4, ey.saturating_sub(8), w / 2, CHAR_H * 3 + 16, 0x20, 0x10, 0x06);
            font::draw_str(gpu, w / 4 + MX, ey, "Export mesh:", SCALE, HD_R, HD_G, HD_B);
            font::draw_str(gpu, w / 4 + MX, ey + CHAR_H + 4,
                           "S = binary STL   O = OBJ   Esc = cancel",
                           SCALE, TX_R, TX_G, TX_B);
        }

        // Status bar
        let sy = h.saturating_sub(stat_h);
        self.draw_status(gpu, sy, w);
    }

    // ── Iso mini-renderer ─────────────────────────────────────────────────────

    fn draw_iso(&self, gpu: &dyn GpuSurface, vx: u32, vy: u32, vw: u32, vh: u32) {
        let tw = CannabisMode::I.tile_px();
        let th = tw / 2;
        let zs = CannabisMode::I.zscale();
        let cam_wx = MOD as i32 / 2;
        let cam_wz = MOD as i32 / 2;
        let sx = vx + vw / 2;
        let sy = vy + vh / 2 + (MOD as u32 / 2) * zs;
        let sw = vx + vw;
        let sh = vy + vh;
        let clip_l = vx as i32;
        let clip_r = sw as i32;
        let clip_t = vy as i32;
        let clip_b = sh as i32;
        let tw_i = tw as i32;
        let th_i = th as i32;
        let zs_i = zs as i32;

        // Collect + sort draw commands
        const MAX_C: usize = MOD * MOD * MOD;
        let mut cmds = [(0usize, 0u8, 0u8, 0u8); MAX_C];
        let mut nc = 0usize;
        for x in 0..MOD { for y in 0..MOD { for z in 0..MOD {
            let n = vr_get(x, y, z);
            if n.is_air() || n.faces == 0 { continue; }
            let depth = x + z + (MOD - 1 - y);
            cmds[nc] = (depth, x as u8, y as u8, z as u8);
            nc += 1;
        }}}
        for i in 1..nc {
            let mut j = i;
            while j > 0 && cmds[j].0 > cmds[j-1].0 { cmds.swap(j, j-1); j -= 1; }
        }

        for ci in 0..nc {
            let (_, wx, wy, wz) = cmds[ci];
            let rx = wx as i32 - cam_wx;
            let rz = wz as i32 - cam_wz;
            let ox = sx as i32 + iso_x(rx, rz, tw);
            let oy = sy as i32 + iso_y(rx, wy as i32, rz, th, zs);
            if ox + tw_i < clip_l || ox > clip_r { continue; }
            if oy + th_i + zs_i < clip_t || oy > clip_b { continue; }
            let node = vr_get(wx as usize, wy as usize, wz as usize);
            let (bc, gc, rc) = node.base_color();
            let (br, gr, rr) = palette::bright((bc, gc, rc));
            let (bd, gd, rd) = palette::dim((bc, gc, rc));
            if node.faces & FACE_JY != 0 { draw_face_jy(gpu, ox, oy, tw, th, (br, gr, rr), sw, sh); }
            if node.faces & FACE_JI != 0 { draw_face_ji(gpu, ox, oy, tw, th, zs, (bc, gc, rc), sw, sh); }
            if node.faces & FACE_JE != 0 { draw_face_je(gpu, ox, oy, tw, th, zs, (bd, gd, rd), sw, sh); }
        }

        // Cursor highlight
        let rx = self.cx as i32 - cam_wx;
        let rz = self.cz as i32 - cam_wz;
        let ox = sx as i32 + iso_x(rx, rz, tw);
        let oy = sy as i32 + iso_y(rx, self.cy as i32, rz, th, zs);
        let tc = (80u8, 220u8, 200u8);
        let rc_col = (40u8, 200u8, 100u8);
        let lc = (25u8, 140u8, 60u8);
        draw_face_jy(gpu, ox, oy, tw, th, tc, sw, sh);
        draw_face_ji(gpu, ox, oy, tw, th, zs, rc_col, sw, sh);
        draw_face_je(gpu, ox, oy, tw, th, zs, lc, sw, sh);

        // Label
        font::draw_str(gpu, vx + 4, vy + 4, "Iso", SCALE, DM_R, DM_G, DM_B);
    }

    // ── Orthographic views ────────────────────────────────────────────────────

    fn draw_ortho_top(&self, gpu: &dyn GpuSurface,
                       vx: u32, vy: u32, vw: u32, vh: u32, active: bool) {
        let cell = self.cell_px(vw, vh);
        let ox = vx + (vw.saturating_sub(cell * MOD as u32)) / 2;
        let oy = vy + (vh.saturating_sub(cell * MOD as u32)) / 2;

        for xi in 0..MOD { for zi in 0..MOD {
            let px = ox + xi as u32 * cell;
            let py = oy + zi as u32 * cell;
            // Find highest non-air Y
            let color = (0..MOD).rev()
                .find(|&y| !vr_is_air(xi, y, zi))
                .map(|y| { let n = vr_get(xi, y, zi); mat_color(n.material) });
            if let Some((b, g, r)) = color {
                gpu.fill_rect(px, py, cell.saturating_sub(1), cell.saturating_sub(1), b, g, r);
            }
            // Cursor highlight
            if xi == self.cx && zi == self.cz {
                self.draw_cursor_cell(gpu, px, py, cell, active);
            }
        }}

        self.draw_view_label(gpu, vx, vy, "Top (XZ)", active);
        // Y-layer indicator
        let mut yb = [b' '; 6]; yb[0] = b'Y'; yb[1] = b':';
        write_dec(&mut yb[2..], self.cy as u32);
        if let Ok(s) = core::str::from_utf8(&yb[..4]) {
            font::draw_str(gpu, vx + vw.saturating_sub(CHAR_W * 6), vy + 4, s, SCALE, DM_R, DM_G, DM_B);
        }
    }

    fn draw_ortho_front(&self, gpu: &dyn GpuSurface,
                         vx: u32, vy: u32, vw: u32, vh: u32, active: bool) {
        let cell = self.cell_px(vw, vh);
        let ox = vx + (vw.saturating_sub(cell * MOD as u32)) / 2;
        let oy = vy + (vh.saturating_sub(cell * MOD as u32)) / 2;

        for xi in 0..MOD { for yi in 0..MOD {
            let px = ox + xi as u32 * cell;
            let py = oy + (MOD - 1 - yi) as u32 * cell; // y=0 at bottom
            let color = (0..MOD)
                .find(|&z| !vr_is_air(xi, yi, z))
                .map(|z| { let n = vr_get(xi, yi, z); mat_color(n.material) });
            if let Some((b, g, r)) = color {
                gpu.fill_rect(px, py, cell.saturating_sub(1), cell.saturating_sub(1), b, g, r);
            }
            if xi == self.cx && yi == self.cy {
                self.draw_cursor_cell(gpu, px, py, cell, active);
            }
        }}
        self.draw_view_label(gpu, vx, vy, "Front (XY)", active);
    }

    fn draw_ortho_side(&self, gpu: &dyn GpuSurface,
                        vx: u32, vy: u32, vw: u32, vh: u32, active: bool) {
        let cell = self.cell_px(vw, vh);
        let ox = vx + (vw.saturating_sub(cell * MOD as u32)) / 2;
        let oy = vy + (vh.saturating_sub(cell * MOD as u32)) / 2;

        for zi in 0..MOD { for yi in 0..MOD {
            let px = ox + zi as u32 * cell;
            let py = oy + (MOD - 1 - yi) as u32 * cell;
            let color = (0..MOD)
                .find(|&x| !vr_is_air(x, yi, zi))
                .map(|x| { let n = vr_get(x, yi, zi); mat_color(n.material) });
            if let Some((b, g, r)) = color {
                gpu.fill_rect(px, py, cell.saturating_sub(1), cell.saturating_sub(1), b, g, r);
            }
            if zi == self.cz && yi == self.cy {
                self.draw_cursor_cell(gpu, px, py, cell, active);
            }
        }}
        self.draw_view_label(gpu, vx, vy, "Side (ZY)", active);
    }

    fn cell_px(&self, vw: u32, vh: u32) -> u32 {
        let cx = (vw.saturating_sub(8)) / MOD as u32;
        let cy = (vh.saturating_sub(8)) / MOD as u32;
        cx.min(cy).max(2)
    }

    fn draw_cursor_cell(&self, gpu: &dyn GpuSurface, px: u32, py: u32, cell: u32, active: bool) {
        let (r, g, b) = if active { (0x60u8, 0xd0u8, 0x88u8) } else { (0x40u8, 0x80u8, 0x50u8) };
        // Draw border: top, bottom, left, right edges
        gpu.fill_rect(px, py, cell.saturating_sub(1), 1, b, g, r);
        gpu.fill_rect(px, py + cell.saturating_sub(2), cell.saturating_sub(1), 1, b, g, r);
        gpu.fill_rect(px, py, 1, cell.saturating_sub(1), b, g, r);
        gpu.fill_rect(px + cell.saturating_sub(2), py, 1, cell.saturating_sub(1), b, g, r);
    }

    fn draw_view_label(&self, gpu: &dyn GpuSurface, vx: u32, vy: u32, label: &str, active: bool) {
        let (r, g, b) = if active { (AC_R, AC_G, AC_B) } else { (DM_R, DM_G, DM_B) };
        font::draw_str(gpu, vx + 4, vy + 4, label, SCALE, r, g, b);
    }

    // ── Status bar ────────────────────────────────────────────────────────────

    fn draw_status(&self, gpu: &dyn GpuSurface, sy: u32, w: u32) {
        let mat = &MATS[self.mat_idx];
        let stype = STYPES[self.type_idx].1;

        // Position
        let mut pos = [b' '; 16];
        pos[0] = b'X'; pos[1] = b':';
        let mut p = 2 + write_dec(&mut pos[2..], self.cx as u32);
        pos[p] = b' '; pos[p+1] = b'Y'; pos[p+2] = b':'; p += 3;
        p += write_dec(&mut pos[p..], self.cy as u32);
        pos[p] = b' '; pos[p+1] = b'Z'; pos[p+2] = b':'; p += 3;
        p += write_dec(&mut pos[p..], self.cz as u32);
        if let Ok(s) = core::str::from_utf8(&pos[..p]) {
            font::draw_str(gpu, MX, sy, s, SCALE, TX_R, TX_G, TX_B);
        }

        // Material
        let mat_x = MX + CHAR_W * 14;
        let ch = [mat.ch];
        if let Ok(s) = core::str::from_utf8(&ch) {
            let (fill, _) = crate::renderer_bridge::tile_colors(mat.ch);
            font::draw_str(gpu, mat_x, sy, s, SCALE, fill.2, fill.1, fill.0);
        }
        font::draw_str(gpu, mat_x + CHAR_W * 2, sy, mat.name, SCALE, TX_R, TX_G, TX_B);
        font::draw_str(gpu, mat_x + CHAR_W * 10, sy, stype, SCALE, DM_R, DM_G, DM_B);

        // Hints (right side)
        let hint = "Tab:panel  Ent:place  Bsp:erase  M:mat  T:type  X:sym  []:Y  ^S:save  ^E:export  Esc:browser";
        let hx = w.saturating_sub(MX + hint.len() as u32 * CHAR_W);
        font::draw_str(gpu, hx, sy, hint, SCALE, DM_R, DM_G, DM_B);
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn mat_color(ch: u8) -> (u8, u8, u8) {
    let (fill, _) = crate::renderer_bridge::tile_colors(ch);
    fill
}

fn write_dec(buf: &mut [u8], mut n: u32) -> usize {
    if buf.is_empty() { return 0; }
    if n == 0 { buf[0] = b'0'; return 1; }
    let mut tmp = [0u8; 5]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + (n % 10) as u8; n /= 10; l += 1; }
    for i in 0..l.min(buf.len()) { buf[i] = tmp[l - 1 - i]; }
    l
}
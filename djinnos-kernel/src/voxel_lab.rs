// Voxel Lab — in-kernel voxel scene authoring tool.
//
// Full-screen isometric editor for building zone scenes.
// Scenes serialise as sparse .vx files in the Sa volume.
//
// Keys:
//   Arrow keys       move cursor X/Z (isometric-aligned)
//   [ / ]            move cursor Y (down / up)
//   Enter            place voxel at cursor
//   Backspace        erase voxel at cursor
//   Tab              cycle material forward
//   q                cycle material backward
//   t                cycle structural type (Va/Vo/Vi/Vy)
//   c                cycle Cannabis rendering mode (A / I / Y)
//   Ctrl+S (0x13)    save scene to Sa volume
//   Escape           exit to Atelier

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::renderer_bridge::CannabisMode;
use crate::voxel::{
    self, VoxelNode, VoxelScene, Camera,
    VA, VO, VI, VY, MAP_X, MAP_Y, MAP_Z,
};

const SCALE: u32 = 2;
const CHAR_W: u32 = font::GLYPH_W * SCALE;
const CHAR_H: u32 = font::GLYPH_H * SCALE;
const MX:    u32 = 8;

const HD_R: u8 = 0xc8; const HD_G: u8 = 0x96; const HD_B: u8 = 0x4b;
const TX_R: u8 = 0xc0; const TX_G: u8 = 0xc0; const TX_B: u8 = 0xc0;
const AC_R: u8 = 0x60; const AC_G: u8 = 0xd0; const AC_B: u8 = 0x88;
const DM_R: u8 = 0x58; const DM_G: u8 = 0x60; const DM_B: u8 = 0x58;
const MO_R: u8 = 0xd0; const MO_G: u8 = 0x60; const MO_B: u8 = 0x60;
const HI_R: u8 = 0x18; const HI_G: u8 = 0x30; const HI_B: u8 = 0x18;

// ── Request ───────────────────────────────────────────────────────────────────

static mut REQUESTED: bool = false;

pub fn request() { unsafe { REQUESTED = true; } }

pub fn consume_request() -> bool {
    unsafe { if REQUESTED { REQUESTED = false; true } else { false } }
}

// ── Static scene (256 KB in BSS) ─────────────────────────────────────────────

static mut LAB_SCENE: VoxelScene = VoxelScene::empty();

// ── Material palette ─────────────────────────────────────────────────────────

struct MatDef {
    ch:    u8,
    name:  &'static str,
    stype: u8,
}

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
    MatDef { ch: b'+', name: "door",    stype: VA },
    MatDef { ch: b'=', name: "road",    stype: VO },
    MatDef { ch: b'/', name: "bridge",  stype: VA },
    MatDef { ch: b'^', name: "stairs+", stype: VA },
    MatDef { ch: b'v', name: "stairs-", stype: VA },
];

// Structural types user can cycle through.
const STYPES: &[(u8, &str)] = &[
    (VA, "Va/solid"),
    (VO, "Vo/terrain"),
    (VI, "Vi/entity"),
    (VY, "Vy/living"),
];

// ── Serialisation ─────────────────────────────────────────────────────────────
//
// .vx sparse format:
//   [0..4]  magic  "VX01"
//   [4..8]  node count (u32 LE)
//   [8..]   per node: x(u8) y(u8) z(u8) sak_type(u8) material(u8) = 5 bytes

const MAGIC: &[u8; 4] = b"VX01";

fn scene_to_bytes(scene: &VoxelScene, buf: &mut [u8]) -> usize {
    // Count non-air nodes.
    let mut count = 0u32;
    for x in 0..MAP_X { for y in 0..MAP_Y { for z in 0..MAP_Z {
        if !scene.nodes[x][y][z].is_air() { count += 1; }
    }}}
    let needed = 8 + count as usize * 5;
    if buf.len() < needed { return 0; }

    buf[0..4].copy_from_slice(MAGIC);
    buf[4] = (count & 0xFF) as u8;
    buf[5] = ((count >> 8)  & 0xFF) as u8;
    buf[6] = ((count >> 16) & 0xFF) as u8;
    buf[7] = ((count >> 24) & 0xFF) as u8;

    let mut off = 8usize;
    for x in 0..MAP_X { for y in 0..MAP_Y { for z in 0..MAP_Z {
        let n = &scene.nodes[x][y][z];
        if n.is_air() { continue; }
        buf[off]     = x as u8;
        buf[off + 1] = y as u8;
        buf[off + 2] = z as u8;
        buf[off + 3] = n.sak_type;
        buf[off + 4] = n.material;
        off += 5;
    }}}
    off
}

fn bytes_to_scene(scene: &mut VoxelScene, buf: &[u8]) -> bool {
    if buf.len() < 8 { return false; }
    if &buf[0..4] != MAGIC { return false; }
    let count = u32::from_le_bytes([buf[4], buf[5], buf[6], buf[7]]) as usize;
    if buf.len() < 8 + count * 5 { return false; }

    // Clear to air first.
    for x in 0..MAP_X { for y in 0..MAP_Y { for z in 0..MAP_Z {
        scene.nodes[x][y][z] = VoxelNode::AIR;
    }}}

    let mut off = 8usize;
    for _ in 0..count {
        let x = buf[off]     as usize;
        let y = buf[off + 1] as usize;
        let z = buf[off + 2] as usize;
        let sak = buf[off + 3];
        let mat = buf[off + 4];
        off += 5;
        if x < MAP_X && y < MAP_Y && z < MAP_Z {
            scene.nodes[x][y][z] = VoxelNode {
                sak_type: sak, faces: voxel::ISO_FACES,
                material: mat, adjacency: voxel::DO,
            };
        }
    }
    scene.cull_all();
    true
}

// Sa serialise buffer — 320 KB covers a fully packed 64×16×64 scene.
const SER_BUF: usize = 8 + MAP_X * MAP_Y * MAP_Z * 5;
static mut SER_SCRATCH: [u8; SER_BUF] = [0u8; SER_BUF];

// ── VoxelLab ──────────────────────────────────────────────────────────────────

pub struct VoxelLab {
    camera:   Camera,
    cx: usize, cy: usize, cz: usize,  // cursor world position
    mat_idx:  usize,
    type_idx: usize,
    cannabis: CannabisMode,
    modified: bool,
    name:     [u8; 32],
    name_n:   usize,
    rule_y:   u32,
    exited:   bool,
}

impl VoxelLab {
    pub fn new(rule_y: u32) -> Self {
        VoxelLab {
            camera:   Camera::new(0, 0, 0, 0, 0),
            cx: MAP_X / 2, cy: 1, cz: MAP_Z / 2,
            mat_idx:  0,
            type_idx: 0,
            cannabis: CannabisMode::A,
            modified: false,
            name:     [0u8; 32],
            name_n:   0,
            rule_y,
            exited:   false,
        }
    }

    pub fn exited(&self) -> bool { self.exited }

    /// Load a scene from the Sa volume.  If name is empty, start fresh.
    pub fn open(&mut self, name: &[u8]) {
        self.exited   = false;
        self.modified = false;
        let n = name.len().min(31);
        self.name[..n].copy_from_slice(&name[..n]);
        self.name_n = n;

        if n == 0 {
            // New empty scene: flat ground of grass.
            unsafe {
                for x in 0..MAP_X { for z in 0..MAP_Z {
                    LAB_SCENE.nodes[x][0][z] = VoxelNode::terrain(b',');
                }}
                for x in 0..MAP_X { for y in 1..MAP_Y { for z in 0..MAP_Z {
                    LAB_SCENE.nodes[x][y][z] = VoxelNode::AIR;
                }}}
                LAB_SCENE.cull_all();
            }
            let def = b"scene.vx";
            self.name[..def.len()].copy_from_slice(def);
            self.name_n = def.len();
        } else {
            unsafe {
                let read_n = crate::sa::read_file(name, &mut SER_SCRATCH);
                if read_n > 0 {
                    bytes_to_scene(&mut LAB_SCENE, &SER_SCRATCH[..read_n]);
                } else {
                    // File not found — start fresh.
                    for x in 0..MAP_X { for z in 0..MAP_Z {
                        LAB_SCENE.nodes[x][0][z] = VoxelNode::terrain(b',');
                    }}
                    for x in 0..MAP_X { for y in 1..MAP_Y { for z in 0..MAP_Z {
                        LAB_SCENE.nodes[x][y][z] = VoxelNode::AIR;
                    }}}
                    LAB_SCENE.cull_all();
                }
            }
        }

        self.cx = MAP_X / 2;
        self.cy = 1;
        self.cz = MAP_Z / 2;
    }

    pub fn handle_key(&mut self, key: Key) {
        match key {
            Key::Escape      => { self.exited = true; }
            Key::Char(0x13)  => { self.save(); }

            // Cursor movement — iso-aligned XZ, direct Y.
            Key::Right => { if self.cx + 1 < MAP_X { self.cx += 1; } }
            Key::Left  => { if self.cx > 0          { self.cx -= 1; } }
            Key::Down  => { if self.cz + 1 < MAP_Z  { self.cz += 1; } }
            Key::Up    => { if self.cz > 0           { self.cz -= 1; } }
            Key::Char(b'[') => { if self.cy > 0          { self.cy -= 1; } }
            Key::Char(b']') => { if self.cy + 1 < MAP_Y  { self.cy += 1; } }

            // Place voxel.
            Key::Enter => {
                let m = &MATS[self.mat_idx];
                let s = STYPES[self.type_idx].0;
                let node = VoxelNode {
                    sak_type: s, faces: voxel::ISO_FACES,
                    material: m.ch, adjacency: voxel::DO,
                };
                unsafe {
                    LAB_SCENE.set(self.cx, self.cy, self.cz, node);
                    // Re-cull this cell and its neighbours.
                    self.cull_neighborhood(self.cx, self.cy, self.cz);
                }
                self.modified = true;
            }

            // Erase voxel.
            Key::Backspace => {
                unsafe {
                    LAB_SCENE.set(self.cx, self.cy, self.cz, VoxelNode::AIR);
                    self.cull_neighborhood(self.cx, self.cy, self.cz);
                }
                self.modified = true;
            }

            // Cycle material.
            Key::Char(b'\t') => { self.mat_idx = (self.mat_idx + 1) % MATS.len(); }
            Key::Char(b'q')  => {
                self.mat_idx = if self.mat_idx == 0 { MATS.len() - 1 } else { self.mat_idx - 1 };
            }

            // Cycle structural type.
            Key::Char(b't') => { self.type_idx = (self.type_idx + 1) % STYPES.len(); }

            // Cycle Cannabis rendering mode.
            Key::Char(b'c') => {
                self.cannabis = match self.cannabis {
                    CannabisMode::A => CannabisMode::I,
                    CannabisMode::I => CannabisMode::Y,
                    CannabisMode::Y => CannabisMode::A,
                };
            }

            _ => {}
        }
    }

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let floor = self.rule_y + 4;
        let sw = gpu.width();
        let sh = gpu.height();

        // Camera: center on cursor.
        let tw = self.cannabis.tile_px();
        let th = tw / 2;
        let zs = self.cannabis.zscale();
        let viewport_h = sh.saturating_sub(floor + CHAR_H + 4 + CHAR_H + 4);
        let center_y   = floor + CHAR_H + 4 + viewport_h / 2;
        let camera = Camera {
            wx: self.cx as i32 * 256,
            wy: 0,
            wz: self.cz as i32 * 256,
            sx: sw / 2,
            sy: center_y + self.cy as u32 * zs,
            mode: self.cannabis,
        };

        // Render scene into viewport area.
        let scene_ref = unsafe { &LAB_SCENE };
        voxel::render(scene_ref, &camera, gpu);

        // Cursor highlight (drawn last, on top).
        voxel::render_cursor(scene_ref, &camera, gpu, self.cx, self.cy, self.cz);

        // Header bar.
        gpu.fill_rect(0, floor, sw, CHAR_H + 4, 0x0e, 0x08, 0x06);
        font::draw_str(gpu, MX, floor + 2, "VOXEL LAB", SCALE, HD_R, HD_G, HD_B);

        // Scene name + modified.
        let name_x = MX + CHAR_W * 12;
        if self.name_n > 0 {
            if let Ok(s) = core::str::from_utf8(&self.name[..self.name_n]) {
                font::draw_str(gpu, name_x, floor + 2, s, SCALE, TX_R, TX_G, TX_B);
            }
        }
        if self.modified {
            let mod_x = name_x + (self.name_n as u32 + 1) * CHAR_W;
            font::draw_str(gpu, mod_x, floor + 2, "[*]", SCALE, MO_R, MO_G, MO_B);
        }

        // Cannabis mode label (top-right).
        let cm_str = match self.cannabis { CannabisMode::A => "A", CannabisMode::I => "I", CannabisMode::Y => "Y" };
        let cm_label = "Cannabis:";
        let cm_x = sw.saturating_sub(MX + (cm_label.len() as u32 + 3) * CHAR_W);
        font::draw_str(gpu, cm_x, floor + 2, cm_label, SCALE, DM_R, DM_G, DM_B);
        font::draw_str(gpu, cm_x + (cm_label.len() as u32 + 1) * CHAR_W, floor + 2,
                       cm_str, SCALE, AC_R, AC_G, AC_B);

        // Material panel (right strip, below header).
        self.render_mat_panel(gpu, floor + CHAR_H + 8, viewport_h, sw, sh);

        // Status bar.
        let sy = sh.saturating_sub(CHAR_H + 2);
        self.render_status(gpu, sy, sw);
    }

    // ── Material panel ────────────────────────────────────────────────────────

    fn render_mat_panel(&self, gpu: &dyn GpuSurface, top: u32, _height: u32, sw: u32, sh: u32) {
        let panel_w = CHAR_W * 10;
        let px = sw.saturating_sub(panel_w + 4);
        let row_h = CHAR_H + 2;
        let max_y = sh.saturating_sub(CHAR_H + 4);

        for (i, mat) in MATS.iter().enumerate() {
            let y = top + i as u32 * row_h;
            if y + row_h > max_y { break; }

            let selected = i == self.mat_idx;
            if selected {
                gpu.fill_rect(px.saturating_sub(2), y, panel_w + 4, row_h,
                              HI_B, HI_G, HI_R);
            }

            // Material tile char.
            let tile_ch = [mat.ch];
            if let Ok(s) = core::str::from_utf8(&tile_ch) {
                let (fill, _) = crate::renderer_bridge::tile_colors(mat.ch);
                font::draw_str(gpu, px, y, s, SCALE, fill.2, fill.1, fill.0);
            }

            // Name.
            let (tr, tg, tb) = if selected { (AC_R, AC_G, AC_B) } else { (DM_R, DM_G, DM_B) };
            font::draw_str(gpu, px + CHAR_W * 2, y, mat.name, SCALE, tr, tg, tb);
        }

        // Selected structural type.
        let stype_y = top + MATS.len() as u32 * row_h + 4;
        if stype_y + CHAR_H < sh.saturating_sub(CHAR_H + 4) {
            font::draw_str(gpu, px, stype_y, STYPES[self.type_idx].1,
                           SCALE, AC_R, AC_G, AC_B);
        }
    }

    // ── Status bar ────────────────────────────────────────────────────────────

    fn render_status(&self, gpu: &dyn GpuSurface, sy: u32, sw: u32) {
        // Coordinates.
        let mut coord = [b' '; 24];
        let lbl = b"X:";
        coord[..2].copy_from_slice(lbl);
        let mut off = 2 + write_u8_3(&mut coord[2..], self.cx as u8);
        coord[off] = b' '; off += 1;
        coord[off] = b'Y'; coord[off+1] = b':'; off += 2;
        off += write_u8_3(&mut coord[off..], self.cy as u8);
        coord[off] = b' '; off += 1;
        coord[off] = b'Z'; coord[off+1] = b':'; off += 2;
        off += write_u8_3(&mut coord[off..], self.cz as u8);
        if let Ok(s) = core::str::from_utf8(&coord[..off]) {
            font::draw_str(gpu, MX, sy, s, SCALE, TX_R, TX_G, TX_B);
        }

        // Hints (right side).
        let hint = "Arrows:XZ  []:Y  Ent:place  Bsp:erase  Tab:mat  t:type  c:mode  ^S:save  Esc:exit";
        let hint_x = sw.saturating_sub(MX + (hint.len() as u32) * CHAR_W);
        font::draw_str(gpu, hint_x, sy, hint, SCALE, DM_R, DM_G, DM_B);
    }

    // ── Internals ─────────────────────────────────────────────────────────────

    fn save(&mut self) {
        if !self.modified { return; }
        unsafe {
            let n = scene_to_bytes(&LAB_SCENE, &mut SER_SCRATCH);
            if n > 0 {
                crate::sa::write_file(&self.name[..self.name_n], &SER_SCRATCH[..n]);
                self.modified = false;
            }
        }
    }

    fn cull_neighborhood(&self, x: usize, y: usize, z: usize) {
        unsafe {
            LAB_SCENE.cull_faces(x, y, z);
            // Neighbours in all 6 axis directions.
            if x > 0         { LAB_SCENE.cull_faces(x-1, y, z); }
            if x+1 < MAP_X   { LAB_SCENE.cull_faces(x+1, y, z); }
            if y > 0         { LAB_SCENE.cull_faces(x, y-1, z); }
            if y+1 < MAP_Y   { LAB_SCENE.cull_faces(x, y+1, z); }
            if z > 0         { LAB_SCENE.cull_faces(x, y, z-1); }
            if z+1 < MAP_Z   { LAB_SCENE.cull_faces(x, y, z+1); }
        }
    }
}

// ── Formatting ────────────────────────────────────────────────────────────────

fn write_u8_3(buf: &mut [u8], mut n: u8) -> usize {
    if buf.is_empty() { return 0; }
    if n == 0 { buf[0] = b'0'; return 1; }
    let mut tmp = [0u8; 3]; let mut l = 0;
    while n > 0 { tmp[l] = b'0' + n % 10; n /= 10; l += 1; }
    for i in 0..l.min(buf.len()) { buf[i] = tmp[l-1-i]; }
    l
}
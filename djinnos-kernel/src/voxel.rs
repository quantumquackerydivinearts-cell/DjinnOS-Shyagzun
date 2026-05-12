// Voxel GL engine — segmented raycaster, Octopath Traveler aesthetic.
//
// Vocabulary is Sakura (Tongue 3, bytes 48–71) — the spatial/directional
// tongue whose entries are literally the six faces of a voxel cube and the
// structural state types.
//
// ── Sakura face vocabulary ────────────────────────────────────────────────────
//
//   Jy (48) = Top         — the +Y face, always brightest
//   Ji (49) = Starboard   — right face (+X), medium shade
//   Ja (50) = Front       — front face (+Z), used for front-view scenes
//   Jo (51) = Back        — back face (-Z), occluded in standard iso view
//   Je (52) = Port        — left face (-X), darkest shade
//   Ju (53) = Bottom      — bottom face (-Y), never visible in standard iso
//
// ── Sakura structural types ───────────────────────────────────────────────────
//
//   Va (66) = Order / Structure / Life    — solid structural voxel
//   Vo (67) = Chaos / Boundary-breakage   — terrain / procedural voxel
//   Ve (68) = Pieces / Where              — sparse / partial voxel
//   Vu (69) = Death-moment / Now          — momentary / temporary voxel
//   Vi (70) = Body / Wherever             — entity body voxel
//   Vy (71) = Lifespan / Whenever         — persistent / living voxel
//
// ── Sakura motion states (adjacency) ─────────────────────────────────────────
//
//   Di (55) = Traveling / Distancing      — voxel is exposed / no neighbour
//   Da (56) = Meeting / Conjoined         — face is adjacent to another voxel
//   Do (57) = Parting / Divorced          — face borders a gap / air
//   De (58) = Domesticating / Staying     — face is interior / occluded
//   Bo (63) = Hidden / Occulted           — face is fully culled
//   Ba (62) = Plain / Explicit            — face is surface-visible
//
// ── Rendering model ───────────────────────────────────────────────────────────
//
// Isometric projection, painter's algorithm (back-to-front by x+y+z depth).
// Each voxel exposes at most three faces in standard iso view: Jy, Ji, Je.
// Each face is rasterized as horizontal fill_span segments — the segmented
// raycaster.  No per-pixel depth buffer; depth order is resolved by sort.
//
// Shading derived from the palette RGB ring color of the material:
//   Jy (Top)       → palette::bright(material_color)
//   Ji (Starboard) → material_color
//   Je (Port)      → palette::dim(material_color)
//
// Octopath aesthetic: high-contrast face shading, background gradient,
// characters rendered as blit_row sprites on top of the voxel layer.

use crate::gpu::GpuSurface;
use crate::palette;
use crate::renderer_bridge::{CannabisMode, tile_colors};

// ── Sakura byte addresses — voxel vocabulary ──────────────────────────────────

pub const JY: u32 = 48; // Top
pub const JI: u32 = 49; // Starboard / Right
pub const JA: u32 = 50; // Front
pub const JO: u32 = 51; // Back
pub const JE: u32 = 52; // Port / Left
pub const JU: u32 = 53; // Bottom

pub const VA: u8 = 66; // solid structural
pub const VO: u8 = 67; // chaotic / terrain
pub const VE: u8 = 68; // sparse / partial
pub const VU: u8 = 69; // momentary
pub const VI: u8 = 70; // entity body
pub const VY: u8 = 71; // persistent / living

pub const DA: u8 = 56; // adjacent face (occluded by neighbour)
pub const DO: u8 = 57; // gap face (visible, borders air)
pub const BO: u8 = 63; // culled face

// Face bitmask — which Sakura faces are visible on this node.
pub const FACE_JY: u8 = 1 << 0; // Top        (Jy)
pub const FACE_JI: u8 = 1 << 1; // Starboard  (Ji)
pub const FACE_JA: u8 = 1 << 2; // Front      (Ja)
pub const FACE_JO: u8 = 1 << 3; // Back       (Jo)
pub const FACE_JE: u8 = 1 << 4; // Port       (Je)
pub const FACE_JU: u8 = 1 << 5; // Bottom     (Ju)

// Standard isometric view: only Jy + Ji + Je are ever drawn.
pub const ISO_FACES: u8 = FACE_JY | FACE_JI | FACE_JE;

// ── VoxelNode ─────────────────────────────────────────────────────────────────

/// One voxel in the scene.
/// The type field uses Sakura structural vocabulary (Va/Vo/Vi/Vy/Ve/Vu).
/// The faces field is a bitmask of which Sakura faces are currently visible.
/// The material field is an ASCII tile character for renderer_bridge::tile_colors.
#[derive(Copy, Clone)]
pub struct VoxelNode {
    /// Sakura structural type: VA / VO / VE / VU / VI / VY, or 0 = air.
    pub sak_type:  u8,
    /// Visible face bitmask (FACE_JY | FACE_JI | FACE_JE for standard iso).
    pub faces:     u8,
    /// ASCII material code for tile_colors() lookup.
    pub material:  u8,
    /// Adjacency state per face pair (Da = occluded, Do = exposed).
    pub adjacency: u8,
}

impl VoxelNode {
    pub const AIR: Self = Self { sak_type: 0, faces: 0, material: b' ', adjacency: 0 };

    pub const fn solid(material: u8) -> Self {
        Self { sak_type: VA, faces: ISO_FACES, material, adjacency: DO }
    }

    pub const fn terrain(material: u8) -> Self {
        Self { sak_type: VO, faces: ISO_FACES, material, adjacency: DO }
    }

    pub const fn entity(material: u8) -> Self {
        Self { sak_type: VI, faces: ISO_FACES, material, adjacency: DO }
    }

    pub fn is_air(&self) -> bool { self.sak_type == 0 }

    /// Palette ring color for this voxel's material.
    pub fn base_color(&self) -> (u8, u8, u8) {
        // tile_colors uses the material character to get (fill, edge) BGR pairs.
        // We use the fill color as the base.
        let (fill, _) = tile_colors(self.material);
        fill
    }

    /// Shaded color for a given Sakura face address.
    pub fn face_color(&self, face_addr: u32) -> (u8, u8, u8) {
        let base = self.base_color();
        match face_addr {
            JY => palette::bright(base), // Top: brightest
            JI => base,                  // Starboard: base color
            JE => palette::dim(base),    // Port: darkest
            _  => base,
        }
    }
}

// ── VoxelScene ────────────────────────────────────────────────────────────────

pub const MAP_X: usize = 64;
pub const MAP_Y: usize = 16; // height layers
pub const MAP_Z: usize = 64;

/// The voxel scene: a 64×16×64 grid.
/// Indexed [x][y][z] where y=0 is ground level, y increases upward.
/// Air = VoxelNode::AIR (sak_type=0).
pub struct VoxelScene {
    pub nodes: [[[VoxelNode; MAP_Z]; MAP_Y]; MAP_X],
}

impl VoxelScene {
    pub const fn empty() -> Self {
        Self { nodes: [[[VoxelNode::AIR; MAP_Z]; MAP_Y]; MAP_X] }
    }

    pub fn get(&self, x: i32, y: i32, z: i32) -> &VoxelNode {
        if x < 0 || y < 0 || z < 0
        || x >= MAP_X as i32 || y >= MAP_Y as i32 || z >= MAP_Z as i32 {
            return &VoxelNode::AIR;
        }
        &self.nodes[x as usize][y as usize][z as usize]
    }

    pub fn set(&mut self, x: usize, y: usize, z: usize, node: VoxelNode) {
        if x < MAP_X && y < MAP_Y && z < MAP_Z {
            self.nodes[x][y][z] = node;
        }
    }

    /// Recompute face visibility for a node based on its neighbours.
    /// Jy is visible if y+1 is air; Ji if x+1 is air; Je if x-1 is air.
    pub fn cull_faces(&mut self, x: usize, y: usize, z: usize) {
        if x >= MAP_X || y >= MAP_Y || z >= MAP_Z { return; }
        if self.nodes[x][y][z].is_air() { return; }

        let jy = y + 1 >= MAP_Y || self.nodes[x][y+1][z].is_air();
        let ji = x + 1 >= MAP_X || self.nodes[x+1][y][z].is_air();
        let je = x == 0         || self.nodes[x-1][y][z].is_air();

        let mut faces = 0u8;
        if jy { faces |= FACE_JY; }
        if ji { faces |= FACE_JI; }
        if je { faces |= FACE_JE; }
        self.nodes[x][y][z].faces = faces;
    }

    /// Run cull_faces for every non-air node.
    pub fn cull_all(&mut self) {
        for x in 0..MAP_X {
            for y in 0..MAP_Y {
                for z in 0..MAP_Z {
                    self.cull_faces(x, y, z);
                }
            }
        }
    }
}

// ── Camera ────────────────────────────────────────────────────────────────────

pub struct Camera {
    /// World position (fixed-point, units = voxel cells × 256).
    pub wx: i32, pub wy: i32, pub wz: i32,
    /// Screen offset (top-left corner where the scene is rendered).
    pub sx: u32, pub sy: u32,
    /// Cannabis rendering mode (A/I/Y determines tile pixel sizes).
    pub mode: CannabisMode,
}

impl Camera {
    pub fn new(wx: i32, wy: i32, wz: i32, sx: u32, sy: u32) -> Self {
        Camera { wx, wy, wz, sx, sy, mode: CannabisMode::A }
    }
}

// ── Isometric projection ──────────────────────────────────────────────────────
//
// Standard 2:1 isometric:
//   screen_x = (wx - wz) * tile_w / 2
//   screen_y = (wx + wz) * tile_h / 2 - wy * zscale
//
// tile_w and tile_h come from CannabisMode (renderer_bridge).
// The result is relative to camera.sx/sy.

#[inline]
pub(crate) fn iso_x(wx: i32, wz: i32, tile_w: u32) -> i32 {
    (wx - wz) * (tile_w as i32) / 2
}

#[inline]
pub(crate) fn iso_y(wx: i32, wy: i32, wz: i32, tile_h: u32, zscale: u32) -> i32 {
    (wx + wz) * (tile_h as i32) / 2 - wy * zscale as i32
}

// ── Face rasteriser — segmented fill_span ─────────────────────────────────────
//
// Each of the three visible iso faces is a parallelogram.
// We rasterise it as horizontal fill_span segments — one per scan line.
//
// Face geometry (tile_w = TW, tile_h = TH, zscale = ZS):
//
//   Jy (Top):    a diamond of height TH centred at the cell's iso top point.
//                Scan lines vary in width from 1 to TW, then back to 1.
//
//   Ji (Right):  a parallelogram leaning right, height ZS.
//                Top-right of Jy → bottom-right, then step right each line.
//
//   Je (Left):   a parallelogram leaning left, height ZS.
//                Top-left of Jy → bottom-left, then step left each line.

pub(crate) fn draw_face_jy(
    gpu: &dyn GpuSurface,
    ox: i32, oy: i32,   // iso origin of this voxel's top-left corner on screen
    tw: u32, th: u32,   // tile width, tile height
    col: (u8,u8,u8),
    sw: u32, sh: u32,   // screen width/height for clipping
) {
    // The Jy (top) face is a diamond centred at (ox + tw/2, oy).
    // First half: from 1 pixel wide at top, expanding to tw at mid.
    // Second half: from tw at mid, contracting back to 1 at bottom.
    let half_h = (th / 2).max(1) as i32;
    let cx = ox + tw as i32 / 2;

    for dy in -half_h..=half_h {
        let width = (tw as i32 * (half_h - dy.abs())) / half_h;
        if width <= 0 { continue; }
        let sx0 = cx - width / 2;
        let sy  = oy + dy;
        if sy < 0 || sy >= sh as i32 { continue; }
        let x0 = sx0.max(0) as u32;
        let x1 = (sx0 + width).min(sw as i32) as u32;
        if x0 < x1 {
            gpu.fill_span(x0, x1, sy as u32, col.0, col.1, col.2);
        }
    }
}

pub(crate) fn draw_face_ji(
    gpu: &dyn GpuSurface,
    ox: i32, oy: i32,
    tw: u32, th: u32, zs: u32,
    col: (u8,u8,u8),
    sw: u32, sh: u32,
) {
    // Ji (right) face: parallelogram.
    // Starts at top-right of the Jy diamond, descends by zs rows.
    // Left edge steps right by 1 per 2 rows; right edge is tw/2 further.
    let half_h = (th / 2).max(1) as i32;
    let right_top_x = ox + tw as i32;     // right corner of top face
    let right_top_y = oy;                  // at voxel top

    for dy in 0..zs as i32 {
        // Left edge descends and steps inward along the iso diagonal.
        let lx = right_top_x - dy / 2;
        let rx = lx + tw as i32 / 2;
        let sy = right_top_y + half_h + dy;
        if sy < 0 || sy >= sh as i32 { continue; }
        let x0 = lx.max(0) as u32;
        let x1 = rx.min(sw as i32).max(0) as u32;
        if x0 < x1 {
            gpu.fill_span(x0, x1, sy as u32, col.0, col.1, col.2);
        }
    }
}

pub(crate) fn draw_face_je(
    gpu: &dyn GpuSurface,
    ox: i32, oy: i32,
    tw: u32, th: u32, zs: u32,
    col: (u8,u8,u8),
    sw: u32, sh: u32,
) {
    // Je (left) face: parallelogram mirroring Ji.
    let half_h = (th / 2).max(1) as i32;
    let left_top_x = ox;
    let left_top_y = oy;

    for dy in 0..zs as i32 {
        let rx = left_top_x + dy / 2;
        let lx = rx - tw as i32 / 2;
        let sy = left_top_y + half_h + dy;
        if sy < 0 || sy >= sh as i32 { continue; }
        let x0 = lx.max(0) as u32;
        let x1 = rx.min(sw as i32).max(0) as u32;
        if x0 < x1 {
            gpu.fill_span(x0, x1, sy as u32, col.0, col.1, col.2);
        }
    }
}

// ── Render pass ───────────────────────────────────────────────────────────────

/// Depth key for painter's algorithm: higher = further back, draw first.
/// Standard isometric depth = sum of coordinates in the draw direction.
#[inline]
fn depth_key(x: usize, y: usize, z: usize) -> usize {
    // In standard iso (camera looking from +x+z, slightly above):
    // further = higher x + z, lower y.
    x + z + (MAP_Y - 1 - y)
}

// Fixed-size sort buffer for visible nodes.
const MAX_VISIBLE: usize = 1024;

// World-space viewport radius. Only cells within this many voxels of the
// camera are collected; avoids iterating the full 64×64 grid every frame.
// At TILE_A=32 on 1920-wide screen: ~30 iso-cells across → radius 28 gives margin.
const VIEWPORT_R: i32 = 28;

#[derive(Copy, Clone)]
struct DrawCmd {
    depth: usize,
    x: u8, y: u8, z: u8,
}

/// Render the scene to the GPU surface using the segmented raycaster.
pub fn render(
    scene:  &VoxelScene,
    camera: &Camera,
    gpu:    &dyn GpuSurface,
) {
    let sw = gpu.width();
    let sh = gpu.height();
    let tw = camera.mode.tile_px();
    let th = tw / 2;  // 2:1 isometric tile height
    let zs = camera.mode.zscale();

    // Background: gradient from top to bottom in the Cannabis blue-green register.
    // Octopath style: deep sky at top, lighter horizon at mid.
    let sky_b = (0x40u8, 0x28u8, 0x18u8); // BGR: dark sky
    let hor_b = (0x60u8, 0x48u8, 0x30u8); // BGR: horizon
    let mid_y = sh * 2 / 5;
    for y in 0..sh {
        let (b, g, r) = if y < mid_y {
            let t = y * 255 / mid_y.max(1);
            blend_col(sky_b, hor_b, t as u8)
        } else {
            let t = (y - mid_y) * 255 / (sh - mid_y).max(1);
            blend_col(hor_b, (0x50u8, 0x40u8, 0x28u8), t as u8)
        };
        gpu.fill_span(0, sw, y, b, g, r);
    }

    // Camera world position (integer cells).
    let cam_wx = camera.wx / 256;
    let cam_wz = camera.wz / 256;

    // Viewport window: only iterate cells within VIEWPORT_R of the camera.
    let x_lo = (cam_wx - VIEWPORT_R).max(0) as usize;
    let x_hi = (cam_wx + VIEWPORT_R + 1).min(MAP_X as i32) as usize;
    let z_lo = (cam_wz - VIEWPORT_R).max(0) as usize;
    let z_hi = (cam_wz + VIEWPORT_R + 1).min(MAP_Z as i32) as usize;

    // Collect visible nodes into the draw buffer, sorted back-to-front.
    let mut cmds  = [DrawCmd { depth: 0, x: 0, y: 0, z: 0 }; MAX_VISIBLE];
    let mut ncmds = 0usize;

    'outer: for x in x_lo..x_hi {
        for y in 0..MAP_Y {
            for z in z_lo..z_hi {
                let node = &scene.nodes[x][y][z];
                if node.is_air() || node.faces == 0 { continue; }
                if ncmds >= MAX_VISIBLE { break 'outer; }
                cmds[ncmds] = DrawCmd {
                    depth: depth_key(x, y, z),
                    x: x as u8, y: y as u8, z: z as u8,
                };
                ncmds += 1;
            }
        }
    }

    // Counting sort on bounded depth key (max depth = MAP_X + MAP_Z + MAP_Y - 1 = 143).
    // O(n) sort, no heap required, depth buckets on stack.
    const DEPTH_MAX: usize = MAP_X + MAP_Z + MAP_Y;
    let mut buckets = [0u16; DEPTH_MAX];
    for ci in 0..ncmds { buckets[cmds[ci].depth] += 1; }
    // Prefix sums — we want descending order (furthest first), so scan from high end.
    let mut sorted = [DrawCmd { depth: 0, x: 0, y: 0, z: 0 }; MAX_VISIBLE];
    let mut prefix = [0u16; DEPTH_MAX];
    let mut acc = 0u16;
    for d in (0..DEPTH_MAX).rev() {
        prefix[d] = acc;
        acc += buckets[d];
    }
    for ci in 0..ncmds {
        let d = cmds[ci].depth;
        sorted[prefix[d] as usize] = cmds[ci];
        prefix[d] += 1;
    }

    // Draw each node back-to-front.

    for ci in 0..ncmds {
        let c    = &sorted[ci];
        let wx   = c.x as i32;
        let wy   = c.y as i32;
        let wz   = c.z as i32;
        let node = &scene.nodes[c.x as usize][c.y as usize][c.z as usize];

        // Iso screen position relative to camera.
        let rx = wx - cam_wx;
        let rz = wz - cam_wz;
        let ox = camera.sx as i32 + iso_x(rx, rz, tw);
        let oy = camera.sy as i32 + iso_y(rx, wy, rz, th, zs);

        // Cull if entirely off-screen.
        let tw_i = tw as i32;
        let zs_i = zs as i32;
        if ox + tw_i < 0 || ox > sw as i32 { continue; }
        if oy + th as i32 + zs_i < 0 || oy > sh as i32 { continue; }

        if node.faces & FACE_JY != 0 {
            let col = node.face_color(JY);
            draw_face_jy(gpu, ox, oy, tw, th, col, sw, sh);
        }
        if node.faces & FACE_JI != 0 {
            let col = node.face_color(JI);
            draw_face_ji(gpu, ox, oy, tw, th, zs, col, sw, sh);
        }
        if node.faces & FACE_JE != 0 {
            let col = node.face_color(JE);
            draw_face_je(gpu, ox, oy, tw, th, zs, col, sw, sh);
        }
    }
}

// ── Colour helpers ────────────────────────────────────────────────────────────

fn blend_col(a: (u8,u8,u8), b: (u8,u8,u8), t: u8) -> (u8,u8,u8) {
    let ti = t as u32;
    let ai = 255 - ti;
    (
        ((a.0 as u32 * ai + b.0 as u32 * ti) / 255) as u8,
        ((a.1 as u32 * ai + b.1 as u32 * ti) / 255) as u8,
        ((a.2 as u32 * ai + b.2 as u32 * ti) / 255) as u8,
    )
}

/// Draw a single highlighted cursor cell at world position (wx, wy, wz).
/// Called after render() to guarantee it appears on top.
pub fn render_cursor(
    scene:  &VoxelScene,
    camera: &Camera,
    gpu:    &dyn GpuSurface,
    wx: usize, wy: usize, wz: usize,
) {
    let sw = gpu.width();
    let sh = gpu.height();
    let tw = camera.mode.tile_px();
    let th = tw / 2;
    let zs = camera.mode.zscale();

    let cam_wx = camera.wx / 256;
    let cam_wz = camera.wz / 256;
    let rx = wx as i32 - cam_wx;
    let rz = wz as i32 - cam_wz;
    let ox = camera.sx as i32 + iso_x(rx, rz, tw);
    let oy = camera.sy as i32 + iso_y(rx, wy as i32, rz, th, zs);

    let node = scene.get(wx as i32, wy as i32, wz as i32);
    let top_col   = (200u8, 220u8, 80u8);   // bright yellow-green  (B,G,R)
    let right_col = (100u8, 200u8, 60u8);
    let left_col  = ( 60u8, 140u8, 40u8);

    // If the cell is air, draw outline using dim ghost colors; otherwise highlight.
    let (tc, rc, lc) = if node.is_air() {
        ((60u8, 80u8, 30u8), (40u8, 70u8, 25u8), (25u8, 50u8, 15u8))
    } else {
        (top_col, right_col, left_col)
    };

    draw_face_jy(gpu, ox, oy, tw, th, tc, sw, sh);
    draw_face_ji(gpu, ox, oy, tw, th, zs, rc, sw, sh);
    draw_face_je(gpu, ox, oy, tw, th, zs, lc, sw, sh);
}

// ── Scene building helpers ────────────────────────────────────────────────────

/// Fill a flat ground plane at y=0 with a given material.
pub fn fill_ground(scene: &mut VoxelScene, material: u8) {
    for x in 0..MAP_X {
        for z in 0..MAP_Z {
            scene.set(x, 0, z, VoxelNode::terrain(material));
        }
    }
}

/// Place a solid box of Va voxels.
pub fn fill_box(
    scene: &mut VoxelScene,
    x0: usize, y0: usize, z0: usize,
    x1: usize, y1: usize, z1: usize,
    material: u8,
) {
    for x in x0..x1.min(MAP_X) {
        for y in y0..y1.min(MAP_Y) {
            for z in z0..z1.min(MAP_Z) {
                scene.set(x, y, z, VoxelNode::solid(material));
            }
        }
    }
}
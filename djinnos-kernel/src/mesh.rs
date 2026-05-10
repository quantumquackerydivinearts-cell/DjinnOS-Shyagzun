// mesh.rs -- Voxel-to-triangle mesh conversion.
//
// Generates binary STL and OBJ from a 16x16x16 voxel grid.
// All 6 faces are checked for exposure (not just the 3 iso-visible ones),
// producing a watertight mesh suitable for 3D printing and game use.
//
// Coordinate system: x=right, y=up, z=forward (same as voxel grid).
// Winding: right-hand, outward normals.
//
// Binary STL:
//   80-byte header | u32 triangle count | (12+12+12+12+2) per triangle
//
// OBJ:
//   v x y z      -- vertices (deduplicated per node face, not globally)
//   vn nx ny nz  -- per-face normals (6 axis-aligned)
//   g mat_name   -- group per material type
//   f i//n ...   -- triangles

use crate::voxel_modeler::{vr_is_air_pub, vr_mat_pub, MOD_PUB};

const SCRATCH: usize = 384 * 1024;
static mut MESH_BUF: [u8; SCRATCH] = [0u8; SCRATCH];

// ── Face geometry ─────────────────────────────────────────────────────────────

#[derive(Clone, Copy)]
struct V3 { x: f32, y: f32, z: f32 }

impl V3 {
    const fn new(x: f32, y: f32, z: f32) -> Self { V3 { x, y, z } }
    fn to_le_bytes(self) -> [u8; 12] {
        let mut b = [0u8; 12];
        b[0..4].copy_from_slice(&self.x.to_le_bytes());
        b[4..8].copy_from_slice(&self.y.to_le_bytes());
        b[8..12].copy_from_slice(&self.z.to_le_bytes());
        b
    }
}

// Each face is a quad split into 2 triangles.
// Offsets are relative to voxel origin (x, y, z).
struct FaceDef {
    normal: V3,
    // Quad corners (ccw from outside)
    q: [(f32,f32,f32); 4],
}

fn face_jy(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let n = V3::new(0.0, 1.0, 0.0);
    let v = [V3::new(x,y+1.0,z), V3::new(x+1.0,y+1.0,z),
             V3::new(x+1.0,y+1.0,z+1.0), V3::new(x,y+1.0,z+1.0)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}
fn face_ju(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let v = [V3::new(x,y,z+1.0), V3::new(x+1.0,y,z+1.0),
             V3::new(x+1.0,y,z), V3::new(x,y,z)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}
fn face_ji(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let v = [V3::new(x+1.0,y,z), V3::new(x+1.0,y+1.0,z),
             V3::new(x+1.0,y+1.0,z+1.0), V3::new(x+1.0,y,z+1.0)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}
fn face_je(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let v = [V3::new(x,y,z+1.0), V3::new(x,y+1.0,z+1.0),
             V3::new(x,y+1.0,z), V3::new(x,y,z)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}
fn face_ja(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let v = [V3::new(x+1.0,y,z+1.0), V3::new(x+1.0,y+1.0,z+1.0),
             V3::new(x,y+1.0,z+1.0), V3::new(x,y,z+1.0)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}
fn face_jo(x: f32, y: f32, z: f32) -> ([V3;3],[V3;3]) {
    let v = [V3::new(x,y,z), V3::new(x,y+1.0,z),
             V3::new(x+1.0,y+1.0,z), V3::new(x+1.0,y,z)];
    ([v[0],v[1],v[2]], [v[0],v[2],v[3]])
}

// ── Exposure check ────────────────────────────────────────────────────────────

fn exposed_jy(x: usize, y: usize, z: usize) -> bool { y+1 >= MOD_PUB || vr_is_air_pub(x, y+1, z) }
fn exposed_ju(x: usize, y: usize, z: usize) -> bool { y == 0          || vr_is_air_pub(x, y-1, z) }
fn exposed_ji(x: usize, y: usize, z: usize) -> bool { x+1 >= MOD_PUB || vr_is_air_pub(x+1, y, z) }
fn exposed_je(x: usize, y: usize, z: usize) -> bool { x == 0          || vr_is_air_pub(x-1, y, z) }
fn exposed_ja(x: usize, y: usize, z: usize) -> bool { z+1 >= MOD_PUB || vr_is_air_pub(x, y, z+1) }
fn exposed_jo(x: usize, y: usize, z: usize) -> bool { z == 0          || vr_is_air_pub(x, y, z-1) }

// ── Triangle count (for STL header) ──────────────────────────────────────────

pub fn tri_count() -> u32 {
    let mut n = 0u32;
    for x in 0..MOD_PUB { for y in 0..MOD_PUB { for z in 0..MOD_PUB {
        if vr_is_air_pub(x, y, z) { continue; }
        if exposed_jy(x,y,z) { n += 2; }
        if exposed_ju(x,y,z) { n += 2; }
        if exposed_ji(x,y,z) { n += 2; }
        if exposed_je(x,y,z) { n += 2; }
        if exposed_ja(x,y,z) { n += 2; }
        if exposed_jo(x,y,z) { n += 2; }
    }}}
    n
}

// ── Binary STL ────────────────────────────────────────────────────────────────

fn write_stl_tri(buf: &mut [u8], off: &mut usize, n: V3, t0: [V3;3], t1: [V3;3]) {
    for (norm, tri) in [(n, t0), (n, t1)] {
        if *off + 50 > buf.len() { return; }
        buf[*off..*off+12].copy_from_slice(&norm.to_le_bytes());
        buf[*off+12..*off+24].copy_from_slice(&tri[0].to_le_bytes());
        buf[*off+24..*off+36].copy_from_slice(&tri[1].to_le_bytes());
        buf[*off+36..*off+48].copy_from_slice(&tri[2].to_le_bytes());
        buf[*off+48] = 0; buf[*off+49] = 0;
        *off += 50;
    }
}

/// Write binary STL to Sa volume as `name.stl`.
/// Returns true on success.
pub fn export_stl(base_name: &[u8]) -> bool {
    let buf = unsafe { &mut MESH_BUF };
    // Header: 80 bytes of ASCII text
    let hdr = b"Vrsei DjinnOS voxel model";
    buf[..hdr.len()].copy_from_slice(hdr);
    buf[hdr.len()..80].fill(0);
    // Triangle count placeholder; fill after
    let tc = tri_count();
    buf[80..84].copy_from_slice(&tc.to_le_bytes());
    let mut off = 84usize;

    for xi in 0..MOD_PUB { for yi in 0..MOD_PUB { for zi in 0..MOD_PUB {
        if vr_is_air_pub(xi, yi, zi) { continue; }
        let (x,y,z) = (xi as f32, yi as f32, zi as f32);
        if exposed_jy(xi,yi,zi) { let (a,b) = face_jy(x,y,z); write_stl_tri(buf, &mut off, V3::new(0.0,1.0,0.0), a, b); }
        if exposed_ju(xi,yi,zi) { let (a,b) = face_ju(x,y,z); write_stl_tri(buf, &mut off, V3::new(0.0,-1.0,0.0), a, b); }
        if exposed_ji(xi,yi,zi) { let (a,b) = face_ji(x,y,z); write_stl_tri(buf, &mut off, V3::new(1.0,0.0,0.0), a, b); }
        if exposed_je(xi,yi,zi) { let (a,b) = face_je(x,y,z); write_stl_tri(buf, &mut off, V3::new(-1.0,0.0,0.0), a, b); }
        if exposed_ja(xi,yi,zi) { let (a,b) = face_ja(x,y,z); write_stl_tri(buf, &mut off, V3::new(0.0,0.0,1.0), a, b); }
        if exposed_jo(xi,yi,zi) { let (a,b) = face_jo(x,y,z); write_stl_tri(buf, &mut off, V3::new(0.0,0.0,-1.0), a, b); }
    }}}

    // Write Sa file named `base.stl`
    let mut fname = [0u8; 36];
    let bn = base_name.len().min(32);
    fname[..bn].copy_from_slice(&base_name[..bn]);
    let ext = b".stl";
    if bn + 4 <= 36 { fname[bn..bn+4].copy_from_slice(ext); }
    let fn_n = (bn + 4).min(36);
    crate::sa::write_file(&fname[..fn_n], &buf[..off])
}

// ── OBJ export ────────────────────────────────────────────────────────────────

fn write_bytes(buf: &mut [u8], off: &mut usize, data: &[u8]) {
    let avail = buf.len().saturating_sub(*off);
    let n = data.len().min(avail);
    buf[*off..*off+n].copy_from_slice(&data[..n]);
    *off += n;
}

fn write_str(buf: &mut [u8], off: &mut usize, s: &str) {
    write_bytes(buf, off, s.as_bytes());
}

fn write_f32(buf: &mut [u8], off: &mut usize, v: f32) {
    // Write as integer (voxel coords are always whole numbers)
    let i = v as i32;
    write_int(buf, off, i);
    write_str(buf, off, ".0");
}

fn write_int(buf: &mut [u8], off: &mut usize, mut n: i32) {
    if n < 0 { write_str(buf, off, "-"); n = -n; }
    let mut tmp = [0u8; 12]; let mut l = 0;
    if n == 0 { write_bytes(buf, off, b"0"); return; }
    let mut u = n as u32;
    while u > 0 { tmp[l] = b'0' + (u % 10) as u8; u /= 10; l += 1; }
    let mut rev = [0u8; 12];
    for i in 0..l { rev[i] = tmp[l-1-i]; }
    write_bytes(buf, off, &rev[..l]);
}

fn write_v3_obj(buf: &mut [u8], off: &mut usize, prefix: &str, v: V3) {
    write_str(buf, off, prefix);
    write_str(buf, off, " ");
    write_f32(buf, off, v.x);
    write_str(buf, off, " ");
    write_f32(buf, off, v.y);
    write_str(buf, off, " ");
    write_f32(buf, off, v.z);
    write_str(buf, off, "\n");
}

/// Write OBJ to Sa volume as `name.obj`.
/// Vertices are per-face (not globally deduplicated — simpler, larger file).
pub fn export_obj(base_name: &[u8]) -> bool {
    let buf = unsafe { &mut MESH_BUF };
    let mut off = 0usize;

    write_str(buf, &mut off, "# Vrsei DjinnOS voxel model\n");
    write_str(buf, &mut off, "# Coordinate system: x=right y=up z=forward\n");
    write_str(buf, &mut off, "o model\n");

    // 6 named normals
    let normals = [
        V3::new(0.0,1.0,0.0), V3::new(0.0,-1.0,0.0),
        V3::new(1.0,0.0,0.0), V3::new(-1.0,0.0,0.0),
        V3::new(0.0,0.0,1.0), V3::new(0.0,0.0,-1.0),
    ];
    for n in &normals { write_v3_obj(buf, &mut off, "vn", *n); }

    // Vertices and faces — emit per-face vertices
    // Track vertex index (OBJ is 1-based)
    let mut vi = 1u32;

    // Group per material (collect unique materials first)
    let mut mats = [0u8; 12]; // up to 12 unique material chars
    let mut mat_n = 0usize;
    for x in 0..MOD_PUB { for y in 0..MOD_PUB { for z in 0..MOD_PUB {
        let m = vr_mat_pub(x, y, z);
        if m != b' ' && !mats[..mat_n].contains(&m) && mat_n < 12 {
            mats[mat_n] = m; mat_n += 1;
        }
    }}}

    // Emit vertices and faces grouped by material
    for mi in 0..mat_n {
        let mat = mats[mi];
        write_str(buf, &mut off, "g ");
        let mname = mat_name(mat);
        write_str(buf, &mut off, mname);
        write_str(buf, &mut off, "\n");

        for xi in 0..MOD_PUB { for yi in 0..MOD_PUB { for zi in 0..MOD_PUB {
            if vr_mat_pub(xi, yi, zi) != mat { continue; }
            let (x,y,z) = (xi as f32, yi as f32, zi as f32);

            // For each exposed face: emit 4 vertices + face lines
            let faces: [(bool, fn(f32,f32,f32)->([V3;3],[V3;3]), usize); 6] = [
                (exposed_jy(xi,yi,zi), face_jy, 1),
                (exposed_ju(xi,yi,zi), face_ju, 2),
                (exposed_ji(xi,yi,zi), face_ji, 3),
                (exposed_je(xi,yi,zi), face_je, 4),
                (exposed_ja(xi,yi,zi), face_ja, 5),
                (exposed_jo(xi,yi,zi), face_jo, 6),
            ];
            for (exposed, face_fn, ni) in faces {
                if !exposed { continue; }
                let (t0, t1) = face_fn(x, y, z);
                // Emit 3 vertices for t0, 3 for t1 (6 total, potentially shared but we keep it simple)
                for v in t0.iter().chain(t1.iter()) {
                    write_v3_obj(buf, &mut off, "v", *v);
                }
                // Face 1: vi, vi+1, vi+2 with normal ni
                write_str(buf, &mut off, "f ");
                write_int(buf, &mut off, vi as i32); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, " ");
                write_int(buf, &mut off, vi as i32 + 1); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, " ");
                write_int(buf, &mut off, vi as i32 + 2); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, "\n");
                // Face 2: vi+3, vi+4, vi+5
                write_str(buf, &mut off, "f ");
                write_int(buf, &mut off, vi as i32 + 3); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, " ");
                write_int(buf, &mut off, vi as i32 + 4); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, " ");
                write_int(buf, &mut off, vi as i32 + 5); write_str(buf, &mut off, "//");
                write_int(buf, &mut off, ni as i32); write_str(buf, &mut off, "\n");
                vi += 6;
            }
        }}}
    }

    // Write Sa file named `base.obj`
    let mut fname = [0u8; 36];
    let bn = base_name.len().min(32);
    fname[..bn].copy_from_slice(&base_name[..bn]);
    fname[bn..bn+4].copy_from_slice(b".obj");
    crate::sa::write_file(&fname[..bn+4], &buf[..off])
}

fn mat_name(ch: u8) -> &'static str {
    match ch {
        b'.' => "floor",  b'#' => "wall",   b',' => "grass",
        b'D' => "dirt",   b'S' => "stone",  b'~' => "water",
        b'T' => "tree",   b'M' => "marble", b'Y' => "brick",
        b'C' => "ceramic",b'L' => "slate",  b'X' => "silica",
        b'+' => "door",   b'=' => "road",   b'/' => "bridge",
        b'^' => "stairs", b'v' => "stairs_dn",
        _    => "voxel",
    }
}
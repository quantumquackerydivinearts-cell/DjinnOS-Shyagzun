// Ko's Labyrinth — DjinnOS tile renderer  (Stage 1: thin client)
//
// Fetches zone tile data from the Atelier API over HTTP/1.0 and renders
// it to any GpuSurface.  Game logic remains on the host; the kernel is
// the display + input layer.
//
// HTTP endpoint:
//   GET /v1/game7/zone/{zone_id}/tiles  (port 9000 on 10.0.2.2)
//
// Response format (plain text):
//   "W{width} H{height} @{spawn_x},{spawn_y}\n"
//   "{row_0}\n"
//   "{row_1}\n"
//   ...
//
// ASCII tile key (same as lapidus.py + AmbroflowEngine):
//   #  WALL        .  FLOOR       +  DOOR        ,  GRASS
//   =  ROAD        D  DIRT        S  STONE        T  TREE
//   W  WALL_FACE   ^  STAIRS_UP   v  STAIRS_DOWN  ~  WATER
//   M  MARBLE      Y  YELLOW_BRICK C  CERAMIC     L  SLATE
//   X  SILICA      @  player spawn  N  NPC spawn
//
// Controls (while in game mode):
//   Arrow keys / WASD   — move player
//   Escape              — return to Ko shell

use crate::font;
use crate::gpu::GpuSurface;
use crate::input::Key;
use crate::renderer_bridge as rb;

// ── Constants ─────────────────────────────────────────────────────────────────

// Tile size from renderer_bridge.ko Cannabis mode A.
pub use rb::TILE_A as TILE;

const MAX_W:        usize   = 64;
const MAX_H:        usize   = 48;

const ATELIER_IP:   [u8; 4] = [10, 0, 2, 2];
const ATELIER_PORT: u16     = 9000;
const DEFAULT_ZONE: &[u8]   = b"lapidus_wiltoll_home";

// Raycaster z-buffer — one entry per screen column, stores wall perp-dist.
const MAX_COLS: usize = 1280;
static mut ZBUF: [f32; MAX_COLS] = [0.0f32; MAX_COLS];

// Isometric tile dimensions (2:1 ratio, 64 wide × 32 tall).
const ISO_TW: i32 = 64;
const ISO_TH: i32 = 32;

// ── Entity list ───────────────────────────────────────────────────────────────

const MAX_ENTITIES: usize = 32;
const INTERACT_RANGE_SQ: f32 = 2.25; // 1.5 tiles²

#[derive(Clone, Copy)]
struct Entity {
    kind: u8,   // ASCII: N=NPC  F=Furniture  ?=trigger
    tx:   u8,
    ty:   u8,
}

impl Entity {
    const fn zero() -> Self { Entity { kind: 0, tx: 0, ty: 0 } }
}

// ── WorldClient ───────────────────────────────────────────────────────────────

// Rotation step constants (precomputed so we need no trig at runtime).
// ROT_SPEED = 0.06 radians ≈ 3.4° per keypress.
const ROT_SIN: f32 = 0.059964;   // sin(0.06)
const ROT_COS: f32 = 0.998202;   // cos(0.06)
const MOVE_SPEED: f32 = 0.08;    // tiles per keypress
const PLAYER_R:   f32 = 0.25;    // collision radius in tiles

pub struct WorldClient {
    pub playing:       bool,
    rows:              [[u8; MAX_W]; MAX_H],
    pub zone_width:    usize,
    pub zone_height:   usize,
    pub player_x:      i32,
    pub player_y:      i32,
    zone_name:         [u8; 48],
    zone_name_len:     usize,
    dirty:             bool,
    // Raycaster state — floating-point position, direction, camera plane
    pos_x: f32,
    pos_y: f32,
    dir_x: f32,
    dir_y: f32,
    cam_x: f32,
    cam_y: f32,
    // Entity list — populated from zone tiles on load
    entities:      [Entity; MAX_ENTITIES],
    entity_count:  usize,
    // Dialogue overlay
    dialogue:      [u8; 256],
    dialogue_len:  usize,
    dialogue_vis:  bool,
    // Pending interact command stripped from CMD: prefix lines
    pending_cmd:     [u8; 48],
    pending_cmd_len: usize,
    // Render mode: b'R' = raycaster (interiors), b'I' = isometric (exteriors)
    render_mode: u8,
}

impl WorldClient {
    pub const fn new() -> Self {
        WorldClient {
            playing:       false,
            rows:          [[0u8; MAX_W]; MAX_H],
            zone_width:    0,
            zone_height:   0,
            player_x:      0,
            player_y:      0,
            zone_name:     [0u8; 48],
            zone_name_len: 0,
            dirty:         false,
            pos_x: 0.5, pos_y: 0.5,
            dir_x: 1.0, dir_y: 0.0,
            cam_x: 0.0, cam_y: 0.66,
            entities:     [Entity::zero(); MAX_ENTITIES],
            entity_count: 0,
            dialogue:     [0u8; 256],
            dialogue_len: 0,
            dialogue_vis: false,
            pending_cmd:     [0u8; 48],
            pending_cmd_len: 0,
            render_mode: b'R',
        }
    }

    fn passable_f(&self, x: f32, y: f32) -> bool {
        let r = PLAYER_R;
        for &(fx, fy) in &[(x-r,y-r),(x+r,y-r),(x-r,y+r),(x+r,y+r)] {
            if fx < 0.0 || fy < 0.0 { return false; }
            let ix = fx as usize;
            let iy = fy as usize;
            if ix >= self.zone_width || iy >= self.zone_height { return false; }
            if !rb::passable(self.rows[iy][ix]) { return false; }
        }
        true
    }

    // ── Zone loading (blocking — same TCP pattern as Myrun) ───────────────────

    pub fn load_zone(&mut self, zone_id: &[u8]) -> bool {
        // Build path: /v1/game7/zone/{zone_id}/tiles
        let mut path = [0u8; 80];
        let prefix = b"/v1/game7/zone/";
        let id_n   = zone_id.len().min(32);
        let suffix = b"/tiles";
        let mut n  = 0usize;
        path[n..n + prefix.len()].copy_from_slice(prefix); n += prefix.len();
        path[n..n + id_n].copy_from_slice(&zone_id[..id_n]);           n += id_n;
        path[n..n + suffix.len()].copy_from_slice(suffix);             n += suffix.len();
        let path_len = n;

        // TCP connect
        let fd = crate::net::tcp_socket(0);
        if fd == u64::MAX { return false; }
        if crate::net::tcp_connect(fd, ATELIER_IP, ATELIER_PORT) == 0 {
            crate::net::tcp_close(fd);
            return false;
        }
        // Wait for ESTABLISHED
        let mut ready = false;
        for _ in 0..100_000 {
            crate::net::poll();
            if crate::net::tcp_ready(fd) { ready = true; break; }
        }
        if !ready { crate::net::tcp_close(fd); return false; }

        // Send HTTP/1.0 GET
        let mut req = [0u8; 256];
        let req_len = http_get(&mut req, &path[..path_len], ATELIER_IP, ATELIER_PORT);
        crate::net::tcp_send(fd, &req[..req_len]);
        crate::net::poll();

        // Read response
        static mut RBUF: [u8; 16384] = [0u8; 16384];
        let mut total = 0usize;
        let mut idle  = 0usize;
        loop {
            crate::net::poll();
            let chunk = unsafe { &mut RBUF[total..] };
            let got = crate::net::tcp_recv(fd, chunk);
            total += got;
            if got == 0 { idle += 1; } else { idle = 0; }
            if total + 1 >= unsafe { RBUF.len() } || idle > 4000 { break; }
        }
        crate::net::tcp_close(fd);
        if total == 0 { return false; }

        // Locate HTTP body
        let resp = unsafe { &RBUF[..total] };
        let body_start = resp.windows(4)
            .position(|w| w == b"\r\n\r\n")
            .map(|i| i + 4)
            .unwrap_or(0);

        self.parse_body(&resp[body_start..], zone_id)
    }

    fn parse_body(&mut self, body: &[u8], zone_id: &[u8]) -> bool {
        // Line 0: "W{w} H{h} @{sx},{sy}"
        let lf0 = body.iter().position(|&b| b == b'\n').unwrap_or(body.len());
        let header = strip_cr(&body[..lf0]);
        let (w, h, sx, sy, mode) = match parse_header(header) {
            Some(v) => v,
            None    => return false,
        };
        if w == 0 || h == 0 || w > MAX_W || h > MAX_H { return false; }

        self.zone_width  = w;
        self.zone_height = h;
        self.player_x    = sx as i32;
        self.player_y    = sy as i32;

        let n_name = zone_id.len().min(47);
        self.zone_name[..n_name].copy_from_slice(&zone_id[..n_name]);
        self.zone_name_len = n_name;

        // Remaining lines: tile rows
        let mut pos = lf0 + 1;
        for row in 0..h {
            if pos >= body.len() { break; }
            let end = body[pos..].iter().position(|&b| b == b'\n')
                .map(|i| pos + i).unwrap_or(body.len());
            let line = strip_cr(&body[pos..end]);
            for col in 0..w {
                self.rows[row][col] = line.get(col).copied().unwrap_or(b' ');
            }
            for col in line.len().min(w)..MAX_W {
                self.rows[row][col] = b' ';
            }
            pos = (end + 1).min(body.len());
        }

        // Extract entity markers — replace with floor so the raycaster ignores them.
        self.entity_count = 0;
        for row in 0..h {
            for col in 0..w {
                let ch = self.rows[row][col];
                if matches!(ch, b'N' | b'F' | b'?') {
                    if self.entity_count < MAX_ENTITIES {
                        self.entities[self.entity_count] = Entity {
                            kind: ch, tx: col as u8, ty: row as u8,
                        };
                        self.entity_count += 1;
                    }
                    self.rows[row][col] = b'.';
                }
            }
        }

        self.dialogue_vis    = false;
        self.dialogue_len    = 0;
        self.pending_cmd_len = 0;
        self.render_mode     = mode;
        self.pos_x = sx as f32 + 0.5;
        self.pos_y = sy as f32 + 0.5;
        self.dir_x = 1.0; self.dir_y = 0.0;
        self.cam_x = 0.0; self.cam_y = 0.66;
        self.playing = true;
        self.dirty   = true;
        true
    }

    // ── Input ─────────────────────────────────────────────────────────────────

    pub fn handle_key(&mut self, key: Key) {
        if !self.playing { return; }
        match key {
            Key::Up | Key::Char(b'w') => {
                if self.render_mode == b'I' {
                    let ny = self.pos_y - MOVE_SPEED;
                    if self.passable_f(self.pos_x, ny) { self.pos_y = ny; }
                } else {
                    let nx = self.pos_x + self.dir_x * MOVE_SPEED;
                    let ny = self.pos_y + self.dir_y * MOVE_SPEED;
                    if self.passable_f(nx, self.pos_y) { self.pos_x = nx; }
                    if self.passable_f(self.pos_x, ny) { self.pos_y = ny; }
                }
            }
            Key::Down | Key::Char(b's') => {
                if self.render_mode == b'I' {
                    let ny = self.pos_y + MOVE_SPEED;
                    if self.passable_f(self.pos_x, ny) { self.pos_y = ny; }
                } else {
                    let nx = self.pos_x - self.dir_x * MOVE_SPEED;
                    let ny = self.pos_y - self.dir_y * MOVE_SPEED;
                    if self.passable_f(nx, self.pos_y) { self.pos_x = nx; }
                    if self.passable_f(self.pos_x, ny) { self.pos_y = ny; }
                }
            }
            Key::Left | Key::Char(b'a') => {
                if self.render_mode == b'I' {
                    let nx = self.pos_x - MOVE_SPEED;
                    if self.passable_f(nx, self.pos_y) { self.pos_x = nx; }
                } else {
                    let (odx, ocx) = (self.dir_x, self.cam_x);
                    self.dir_x =  odx * ROT_COS + self.dir_y * ROT_SIN;
                    self.dir_y = -odx * ROT_SIN + self.dir_y * ROT_COS;
                    self.cam_x =  ocx * ROT_COS + self.cam_y * ROT_SIN;
                    self.cam_y = -ocx * ROT_SIN + self.cam_y * ROT_COS;
                }
            }
            Key::Right | Key::Char(b'd') => {
                if self.render_mode == b'I' {
                    let nx = self.pos_x + MOVE_SPEED;
                    if self.passable_f(nx, self.pos_y) { self.pos_x = nx; }
                } else {
                    let (odx, ocx) = (self.dir_x, self.cam_x);
                    self.dir_x = odx * ROT_COS - self.dir_y * ROT_SIN;
                    self.dir_y = odx * ROT_SIN + self.dir_y * ROT_COS;
                    self.cam_x = ocx * ROT_COS - self.cam_y * ROT_SIN;
                    self.cam_y = ocx * ROT_SIN + self.cam_y * ROT_COS;
                }
            }
            Key::Char(b'e') | Key::Char(b'E') => {
                if self.dialogue_vis {
                    self.dialogue_vis = false;
                    self.dirty = true;
                    return;
                }
                // Find nearest entity within interact range.
                let mut best = usize::MAX;
                let mut best_d = INTERACT_RANGE_SQ;
                for i in 0..self.entity_count {
                    let ex = self.entities[i].tx as f32 + 0.5;
                    let ey = self.entities[i].ty as f32 + 0.5;
                    let d = (ex - self.pos_x) * (ex - self.pos_x)
                          + (ey - self.pos_y) * (ey - self.pos_y);
                    if d < best_d { best_d = d; best = i; }
                }
                if best != usize::MAX {
                    let e = self.entities[best];
                    self.send_interact(e.kind, e.tx, e.ty);
                }
                return;
            }
            _ => return,
        }
        self.player_x = self.pos_x as i32;
        self.player_y = self.pos_y as i32;
        self.dirty = true;
    }

    // ── Raycaster render ──────────────────────────────────────────────────────
    //
    // Classic DDA (Lode's algorithm). One ray per screen column; perpendicular
    // distance prevents fisheye. Y-side walls are half-brightness for cheap
    // directional shading. Minimap overlaid top-right for navigation.

    pub fn render(&mut self, gpu: &dyn GpuSurface) {
        if !self.playing || !self.dirty { return; }
        self.dirty = false;

        if self.render_mode == b'I' {
            self.render_iso(gpu);
            return;
        }

        let sw   = gpu.width()  as u32;
        let sh   = gpu.height() as u32;
        let hud  = 20u32;
        let view = sh - hud;

        // Ceiling and floor fills
        gpu.fill_rect(0, 0,    sw, view / 2,        0x18, 0x14, 0x24);
        gpu.fill_rect(0, view/2, sw, view - view/2, 0x30, 0x24, 0x14);

        let px = self.pos_x;
        let py = self.pos_y;

        for col in 0..sw {
            let cam = 2.0 * col as f32 / sw as f32 - 1.0;
            let rdx = self.dir_x + self.cam_x * cam;
            let rdy = self.dir_y + self.cam_y * cam;

            let mut mx = px as i32;
            let mut my = py as i32;

            let ddx = if rdx.abs() < 1e-10 { f32::MAX } else { (1.0 / rdx).abs() };
            let ddy = if rdy.abs() < 1e-10 { f32::MAX } else { (1.0 / rdy).abs() };

            let (step_x, mut sdx) = if rdx < 0.0 {
                (-1i32, (px - mx as f32) * ddx)
            } else {
                (1i32, (mx as f32 + 1.0 - px) * ddx)
            };
            let (step_y, mut sdy) = if rdy < 0.0 {
                (-1i32, (py - my as f32) * ddy)
            } else {
                (1i32, (my as f32 + 1.0 - py) * ddy)
            };

            let mut side   = 0i32;
            let mut wall_ch = b'#';
            let mut hit    = false;

            for _ in 0..64 {
                if sdx < sdy { sdx += ddx; mx += step_x; side = 0; }
                else         { sdy += ddy; my += step_y; side = 1; }
                if mx < 0 || my < 0
                    || mx as usize >= self.zone_width
                    || my as usize >= self.zone_height { break; }
                let ch = self.rows[my as usize][mx as usize];
                if !rb::passable(ch) { wall_ch = ch; hit = true; break; }
            }

            if !hit { continue; }

            let perp = if side == 0 {
                (mx as f32 - px + (1.0 - step_x as f32) * 0.5) / rdx
            } else {
                (my as f32 - py + (1.0 - step_y as f32) * 0.5) / rdy
            };
            if perp <= 0.0 { continue; }

            let wall_h = ((view as f32 / perp) as u32).min(view);
            let top    = (view - wall_h) / 2;

            let (fill, _) = rb::tile_colors(wall_ch);
            let (b, g, r) = if side == 1 {
                (fill.0 >> 1, fill.1 >> 1, fill.2 >> 1)
            } else {
                fill
            };

            gpu.fill_rect(col, top, 1, wall_h, b, g, r);
            unsafe { ZBUF[col as usize] = perp; }
        }

        // ── Billboard pass (entities) ─────────────────────────────────────────
        self.draw_billboards(gpu, sw, view, hud);

        // ── HUD bar ───────────────────────────────────────────────────────────
        gpu.fill_rect(0, sh - hud, sw, hud, 0x08, 0x06, 0x10);
        font::draw_str(gpu, 4, sh - hud + 6,
            core::str::from_utf8(&self.zone_name[..self.zone_name_len]).unwrap_or(""),
            1, 0x60, 0x90, 0xC0);
        if self.pending_cmd_len > 0 {
            font::draw_str(gpu, sw - 160, sh - hud + 6,
                core::str::from_utf8(&self.pending_cmd[..self.pending_cmd_len]).unwrap_or(""),
                1, 0xA0, 0xFF, 0xA0);
        }

        // ── Minimap (top-right, 1 px per tile) ───────────────────────────────
        let mm_x = sw.saturating_sub(self.zone_width as u32 + 2);
        let mm_y = 2u32;
        for ty in 0..self.zone_height {
            for tx in 0..self.zone_width {
                let ch = self.rows[ty][tx];
                let (fill, _) = rb::tile_colors(ch);
                gpu.fill_rect(mm_x + tx as u32, mm_y + ty as u32, 1, 1,
                    fill.0, fill.1, fill.2);
            }
        }
        // Player dot on minimap
        let pdx = mm_x + self.pos_x as u32;
        let pdy = mm_y + self.pos_y as u32;
        if pdx < sw && pdy < sh {
            gpu.fill_rect(pdx, pdy, 2, 2, 0xFF, 0xFF, 0xFF);
        }

        // ── Dialogue overlay ──────────────────────────────────────────────────
        if self.dialogue_vis && self.dialogue_len > 0 {
            let dh  = 52u32;
            let dy  = sh - hud - dh - 2;
            gpu.fill_rect(2, dy, sw - 4, dh, 0x0C, 0x08, 0x18);
            gpu.fill_rect(2, dy, sw - 4, 1,  0x40, 0x30, 0x60);
            gpu.fill_rect(2, dy + dh - 1, sw - 4, 1, 0x40, 0x30, 0x60);
            let text = core::str::from_utf8(&self.dialogue[..self.dialogue_len])
                .unwrap_or("...");
            font::draw_str(gpu, 8, dy + 8,  text, 1, 0xE0, 0xD0, 0xFF);
            font::draw_str(gpu, 8, dy + dh - 12, "[E] dismiss", 1, 0x50, 0x40, 0x70);
        }
    }

    // ── Billboard pass — entities as depth-tested color sprites ──────────────
    fn draw_billboards(&self, gpu: &dyn GpuSurface, sw: u32, view: u32, _hud: u32) {
        let px = self.pos_x;
        let py = self.pos_y;
        let sw_i = sw as i32;
        let view_i = view as i32;

        // Sort indices farthest-first (simple insertion sort — ≤32 entities).
        let mut order = [0usize; MAX_ENTITIES];
        let n = self.entity_count;
        for i in 0..n { order[i] = i; }
        for i in 1..n {
            let mut j = i;
            while j > 0 {
                let da = self.entity_dist_sq(order[j-1]);
                let db = self.entity_dist_sq(order[j]);
                if da >= db { break; }
                order.swap(j-1, j);
                j -= 1;
            }
        }

        for &idx in &order[..n] {
            let ex = self.entities[idx].tx as f32 + 0.5;
            let ey = self.entities[idx].ty as f32 + 0.5;
            let dx = ex - px;
            let dy = ey - py;

            // Camera-space transform (inverse of [[dir_x,cam_x],[dir_y,cam_y]]).
            let inv = 1.0 / (self.cam_x * self.dir_y - self.dir_x * self.cam_y);
            let t_depth = inv * ( self.dir_y * dx - self.dir_x * dy);
            let t_x     = inv * (-self.cam_y * dx + self.cam_x * dy);
            if t_depth <= 0.0 { continue; }

            let spr_sx  = ((sw_i / 2) as f32 * (1.0 + t_x / t_depth)) as i32;
            let spr_h   = ((view_i as f32 / t_depth).abs() as i32).min(view_i);
            let spr_w   = spr_h;

            let x0 = (spr_sx - spr_w / 2).max(0);
            let x1 = (spr_sx + spr_w / 2).min(sw_i - 1);
            let y0 = (view_i / 2 - spr_h / 2).max(0) as u32;
            let y1 = (view_i / 2 + spr_h / 2).min(view_i - 1) as u32;
            if x0 > x1 || y1 <= y0 { continue; }

            let (cb, cg, cr) = entity_color(self.entities[idx].kind);
            for col in x0..=x1 {
                if col >= sw_i { break; }
                if t_depth < unsafe { ZBUF[col as usize] } {
                    gpu.fill_rect(col as u32, y0, 1, y1 - y0, cb, cg, cr);
                }
            }
        }
    }

    fn entity_dist_sq(&self, i: usize) -> f32 {
        let dx = self.entities[i].tx as f32 + 0.5 - self.pos_x;
        let dy = self.entities[i].ty as f32 + 0.5 - self.pos_y;
        dx * dx + dy * dy
    }

    // ── Isometric renderer — exterior/overworld zones ────────────────────────
    fn render_iso(&mut self, gpu: &dyn GpuSurface) {
        let sw   = gpu.width()  as u32;
        let sh   = gpu.height() as u32;
        let hud  = 20u32;
        let view = sh - hud;
        let sw_i = sw as i32;
        let view_i = view as i32;

        // Sky strip and ground base.
        gpu.fill_rect(0, 0,      sw, view / 3,      0x24, 0x30, 0x48);
        gpu.fill_rect(0, view/3, sw, view - view/3,  0x18, 0x14, 0x10);

        let cx   = sw_i / 2;
        let cy   = view_i / 2;
        let px   = self.pos_x;
        let py   = self.pos_y;

        // Draw tiles back-to-front (ascending tx+ty).
        for ty_t in 0..self.zone_height {
            for tx_t in 0..self.zone_width {
                let ch = self.rows[ty_t][tx_t];
                let dx = tx_t as f32 + 0.5 - px;
                let dy = ty_t as f32 + 0.5 - py;

                // Isometric screen position (top vertex of diamond).
                let sx = cx + ((dx - dy) * (ISO_TW as f32 * 0.5)) as i32;
                let sy = cy + ((dx + dy) * (ISO_TH as f32 * 0.5)) as i32 - ISO_TH / 2;

                // Cull tiles fully outside the view.
                if sx + ISO_TW < 0 || sx - ISO_TW > sw_i { continue; }
                if sy + ISO_TH < 0 || sy > view_i        { continue; }

                let (fill, _) = rb::tile_colors(ch);

                // Draw diamond scanlines.
                for row in 0..ISO_TH {
                    let half_w = ((row + 1).min(ISO_TH - row)) * (ISO_TW / ISO_TH);
                    let rx = sx - half_w;
                    let ry = sy + row;
                    if ry < 0 || ry >= view_i { continue; }
                    let x0 = rx.max(0) as u32;
                    let x1 = (rx + half_w * 2).min(sw_i) as u32;
                    if x1 > x0 {
                        // Darken east-facing half for cheap shading.
                        let (b, g, r) = if row > ISO_TH / 2 {
                            (fill.0 >> 1, fill.1 >> 1, fill.2 >> 1)
                        } else { fill };
                        gpu.fill_rect(x0, ry as u32, x1 - x0, 1, b, g, r);
                    }
                }
            }
        }

        // Entity markers in isometric space (small colored diamonds).
        for i in 0..self.entity_count {
            let ex  = self.entities[i].tx as f32 + 0.5;
            let ey  = self.entities[i].ty as f32 + 0.5;
            let dx  = ex - px;
            let dy  = ey - py;
            let sx  = cx + ((dx - dy) * (ISO_TW as f32 * 0.5)) as i32;
            let sy  = cy + ((dx + dy) * (ISO_TH as f32 * 0.5)) as i32 - ISO_TH / 2;
            let (cb, cg, cr) = entity_color(self.entities[i].kind);
            // 8×4 mini-diamond centered on tile.
            for row in 0..4i32 {
                let hw = (row + 1).min(4 - row);
                let ry = sy + ISO_TH / 2 - 2 + row;
                if ry < 0 || ry >= view_i { continue; }
                let x0 = (sx - hw).max(0) as u32;
                let x1 = (sx + hw).min(sw_i) as u32;
                if x1 > x0 { gpu.fill_rect(x0, ry as u32, x1 - x0, 1, cb, cg, cr); }
            }
        }

        // HUD.
        gpu.fill_rect(0, sh - hud, sw, hud, 0x08, 0x06, 0x10);
        font::draw_str(gpu, 4, sh - hud + 6,
            core::str::from_utf8(&self.zone_name[..self.zone_name_len]).unwrap_or(""),
            1, 0x60, 0x90, 0xC0);
        if self.pending_cmd_len > 0 {
            font::draw_str(gpu, sw - 160, sh - hud + 6,
                core::str::from_utf8(&self.pending_cmd[..self.pending_cmd_len]).unwrap_or(""),
                1, 0xA0, 0xFF, 0xA0);
        }

        // Minimap.
        let mm_x = sw.saturating_sub(self.zone_width as u32 + 2);
        for ty_t in 0..self.zone_height {
            for tx_t in 0..self.zone_width {
                let ch = self.rows[ty_t][tx_t];
                let (fill, _) = rb::tile_colors(ch);
                gpu.fill_rect(mm_x + tx_t as u32, 2 + ty_t as u32, 1, 1,
                              fill.0, fill.1, fill.2);
            }
        }
        let pdx = mm_x + self.pos_x as u32;
        if pdx < sw { gpu.fill_rect(pdx, 2 + self.pos_y as u32, 2, 2, 0xFF, 0xFF, 0xFF); }

        // Dialogue overlay.
        if self.dialogue_vis && self.dialogue_len > 0 {
            let dh = 52u32;
            let dy = sh - hud - dh - 2;
            gpu.fill_rect(2, dy, sw - 4, dh, 0x0C, 0x08, 0x18);
            gpu.fill_rect(2, dy, sw - 4, 1,  0x40, 0x30, 0x60);
            gpu.fill_rect(2, dy + dh - 1, sw - 4, 1, 0x40, 0x30, 0x60);
            let text = core::str::from_utf8(&self.dialogue[..self.dialogue_len])
                .unwrap_or("...");
            font::draw_str(gpu, 8, dy + 8,  text, 1, 0xE0, 0xD0, 0xFF);
            font::draw_str(gpu, 8, dy + dh - 12, "[E] dismiss", 1, 0x50, 0x40, 0x70);
        }
    }

    pub fn exit(&mut self) {
        self.playing = false;
        self.dirty   = false;
    }

    // ── Interact — POST /v1/klgs/interact, show plain-text response ───────────

    fn send_interact(&mut self, kind: u8, tx: u8, ty: u8) {
        // Build JSON body.
        let mut body = [0u8; 160];
        let mut bn = 0usize;
        let bpush = |buf: &mut [u8], n: &mut usize, s: &[u8]| {
            let len = s.len().min(buf.len() - *n);
            buf[*n..*n + len].copy_from_slice(&s[..len]);
            *n += len;
        };
        bpush(&mut body, &mut bn, b"{\"zone\":\"");
        bpush(&mut body, &mut bn, &self.zone_name[..self.zone_name_len]);
        bpush(&mut body, &mut bn, b"\",\"kind\":\"");
        if bn < body.len() { body[bn] = kind; bn += 1; }
        bpush(&mut body, &mut bn, b"\",\"x\":");
        bn += fmt_u32(&mut body[bn..], tx as u32);
        bpush(&mut body, &mut bn, b",\"y\":");
        bn += fmt_u32(&mut body[bn..], ty as u32);
        bpush(&mut body, &mut bn, b"}");

        let fd = crate::net::tcp_socket(0);
        if fd == u64::MAX { return; }
        if crate::net::tcp_connect(fd, ATELIER_IP, ATELIER_PORT) == 0 {
            crate::net::tcp_close(fd); return;
        }
        let mut ready = false;
        for _ in 0..100_000 {
            crate::net::poll();
            if crate::net::tcp_ready(fd) { ready = true; break; }
        }
        if !ready { crate::net::tcp_close(fd); return; }

        let mut req = [0u8; 512];
        let req_len = http_post(&mut req, b"/v1/klgs/interact",
                                ATELIER_IP, ATELIER_PORT, &body[..bn]);
        crate::net::tcp_send(fd, &req[..req_len]);
        crate::net::poll();

        static mut IBUF: [u8; 4096] = [0u8; 4096];
        let mut total = 0usize;
        let mut idle  = 0usize;
        loop {
            crate::net::poll();
            let chunk = unsafe { &mut IBUF[total..] };
            let got = crate::net::tcp_recv(fd, chunk);
            total += got;
            if got == 0 { idle += 1; } else { idle = 0; }
            if total + 1 >= unsafe { IBUF.len() } || idle > 4000 { break; }
        }
        crate::net::tcp_close(fd);
        if total == 0 { return; }

        let resp = unsafe { &IBUF[..total] };
        let body_start = resp.windows(4)
            .position(|w| w == b"\r\n\r\n")
            .map(|i| i + 4)
            .unwrap_or(0);
        let text = &resp[body_start..total];

        // Strip leading CMD:{command}\n lines — store command, show clean text.
        let (display, cmd) = if text.starts_with(b"CMD:") {
            let nl = text.iter().position(|&b| b == b'\n').unwrap_or(text.len());
            let c  = &text[4..nl];
            let d  = if nl + 1 < text.len() { &text[nl + 1..] } else { b"" };
            (d, c)
        } else {
            (text, b"" as &[u8])
        };

        let dlen = display.len().min(255);
        self.dialogue[..dlen].copy_from_slice(&display[..dlen]);
        self.dialogue_len = dlen;

        let clen = cmd.len().min(47);
        self.pending_cmd[..clen].copy_from_slice(&cmd[..clen]);
        self.pending_cmd_len = clen;

        self.dialogue_vis = true;
        self.dirty = true;
    }
}

// ── Entity color palette ──────────────────────────────────────────────────────
// Placeholder colors until Mercury Department delivers sprites.
fn entity_color(kind: u8) -> (u8, u8, u8) {
    match kind {
        b'N' => (0x50, 0xC0, 0x60),   // NPC: green
        b'F' => (0xC0, 0x88, 0x40),   // furniture: warm wood
        b'?' => (0xFF, 0xFF, 0x40),   // trigger: yellow
        _    => (0x80, 0x80, 0x80),
    }
}

// ── Static singleton ─────────────────────────────────────────────────────────

static mut WORLD:            WorldClient = WorldClient::new();
static mut LAUNCH_REQUESTED: bool        = false;

pub fn world() -> &'static mut WorldClient {
    unsafe { &mut WORLD }
}

pub fn request_launch(zone_id: &[u8]) {
    // Pre-load the zone synchronously so main loop just needs to flip game_mode.
    let w = unsafe { &mut WORLD };
    w.load_zone(zone_id);
    if w.playing {
        unsafe { LAUNCH_REQUESTED = true; }
    }
}

pub fn consume_launch() -> bool {
    unsafe {
        let v = LAUNCH_REQUESTED;
        LAUNCH_REQUESTED = false;
        v
    }
}

pub fn default_zone() -> &'static [u8] { DEFAULT_ZONE }


// ── Parsing helpers ───────────────────────────────────────────────────────────

fn strip_cr(s: &[u8]) -> &[u8] {
    s.strip_suffix(b"\r").unwrap_or(s)
}

fn parse_u32(s: &[u8]) -> Option<u32> {
    let mut v: u32 = 0;
    let mut any = false;
    for &b in s.iter().take(8) {
        if b < b'0' || b > b'9' { break; }
        v = v * 10 + (b - b'0') as u32;
        any = true;
    }
    if any { Some(v) } else { None }
}

fn parse_prefixed(line: &[u8], prefix: u8) -> Option<u32> {
    let pos = line.iter().position(|&b| b == prefix)?;
    parse_u32(&line[pos + 1..])
}

fn parse_header(line: &[u8]) -> Option<(usize, usize, usize, usize, u8)> {
    let w  = parse_prefixed(line, b'W')? as usize;
    let h  = parse_prefixed(line, b'H')? as usize;
    let at = line.iter().position(|&b| b == b'@')?;
    let after = &line[at + 1..];
    let comma = after.iter().position(|&b| b == b',')?;
    let sx = parse_u32(&after[..comma])? as usize;
    let sy = parse_u32(&after[comma + 1..])? as usize;
    // Optional M{mode}: R=raycaster I=isometric; defaults to R.
    let mode = line.iter().position(|&b| b == b'M')
        .and_then(|p| line.get(p + 1).copied())
        .unwrap_or(b'R');
    Some((w, h, sx, sy, mode))
}

fn fmt_u32(buf: &mut [u8], mut v: u32) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10];
    let mut n = 0usize;
    while v > 0 && n < 10 {
        tmp[n] = b'0' + (v % 10) as u8;
        v /= 10;
        n += 1;
    }
    for i in 0..n.min(buf.len()) {
        buf[i] = tmp[n - 1 - i];
    }
    n.min(buf.len())
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

fn http_get(buf: &mut [u8], path: &[u8], ip: [u8; 4], port: u16) -> usize {
    let mut n = 0usize;

    let push = |buf: &mut [u8], n: &mut usize, s: &[u8]| {
        let len = s.len().min(buf.len() - *n);
        buf[*n..*n + len].copy_from_slice(&s[..len]);
        *n += len;
    };

    push(buf, &mut n, b"GET ");
    push(buf, &mut n, path);
    push(buf, &mut n, b" HTTP/1.0\r\nHost: ");
    // Write IP
    let mut tmp = [0u8; 16];
    let mut tn = 0usize;
    for (k, &o) in ip.iter().enumerate() {
        if k > 0 { tmp[tn] = b'.'; tn += 1; }
        tn += fmt_u32(&mut tmp[tn..], o as u32);
    }
    push(buf, &mut n, &tmp[..tn]);
    push(buf, &mut n, b":");
    let mut pn = [0u8; 6];
    let plen = fmt_u32(&mut pn, port as u32);
    push(buf, &mut n, &pn[..plen]);
    push(buf, &mut n, b"\r\nConnection: close\r\n\r\n");
    n
}

fn http_post(buf: &mut [u8], path: &[u8], ip: [u8; 4], port: u16, body: &[u8]) -> usize {
    let mut n = 0usize;
    let push = |buf: &mut [u8], n: &mut usize, s: &[u8]| {
        let len = s.len().min(buf.len() - *n);
        buf[*n..*n + len].copy_from_slice(&s[..len]);
        *n += len;
    };
    push(buf, &mut n, b"POST ");
    push(buf, &mut n, path);
    push(buf, &mut n, b" HTTP/1.0\r\nHost: ");
    let mut tmp = [0u8; 16];
    let mut tn = 0usize;
    for (k, &o) in ip.iter().enumerate() {
        if k > 0 { tmp[tn] = b'.'; tn += 1; }
        tn += fmt_u32(&mut tmp[tn..], o as u32);
    }
    push(buf, &mut n, &tmp[..tn]);
    push(buf, &mut n, b":");
    let mut pn = [0u8; 6];
    let plen = fmt_u32(&mut pn, port as u32);
    push(buf, &mut n, &pn[..plen]);
    push(buf, &mut n, b"\r\nContent-Type: application/json\r\nContent-Length: ");
    let mut cl = [0u8; 10];
    let clen = fmt_u32(&mut cl, body.len() as u32);
    push(buf, &mut n, &cl[..clen]);
    push(buf, &mut n, b"\r\nConnection: close\r\n\r\n");
    push(buf, &mut n, body);
    n
}
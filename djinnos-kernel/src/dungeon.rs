// dungeon.rs — Procedural dungeon generator for Ko's Labyrinth (7_KLGS).
//
// Generates room-corridor layouts seeded by zone ID.
// Output: a VoxelScene with walls, floors, doors, and entity placement markers.
//
// Room-based BSP (binary space partition) approach:
//   1. Divide the map into two halves.
//   2. Recurse on each half until minimum room size.
//   3. Place a room in each leaf.
//   4. Connect siblings with L-shaped corridors.
//
// ── Seed policy ───────────────────────────────────────────────────────────────
//
//   ROOT ENTRY (first visit, or normal revisit after saving inside):
//     seed = zone_seed(zone_id)
//     The dungeon layout is the same every time the player first enters.
//     This ensures a stable, authored-feeling layout for a given zone.
//
//   RE-ENTRY AFTER DEATH (died in dungeon, before saving):
//     seed = zone_seed(zone_id) ^ entry_nonce
//     entry_nonce increments each time death-or-flee triggers a re-entry.
//     The player faces a fresh, unknown layout — punishment for dying.
//
//   RE-ENTRY AFTER FLEE (fled the dungeon mid-run):
//     Same nonce increment as death.  The zone rearranges on the player.
//     Enemies they passed to reach the escape point may be elsewhere.
//
//   NORMAL REVISIT (completed dungeon, saved, returned):
//     Nonce resets to 0 when the dungeon is completed cleanly.
//     Player revisits the known canonical layout.
//
// The nonce is stored per-zone in a small static table (not in player_state —
// it's session-volatile by design; dying resets it only in the current session).

use crate::voxel::{VoxelScene, VoxelNode, MAP_X, MAP_Y, MAP_Z};

// ── Map dimensions ────────────────────────────────────────────────────────────

pub const DUN_W: usize = 48;   // cells (fits within MAP_X=64)
pub const DUN_H: usize = 48;   // cells (fits within MAP_Z=64)
const DUN_FLOOR_Y: usize = 0; // y=0 is ground level

// ── ASCII map ─────────────────────────────────────────────────────────────────
// '#' = wall, '.' = floor, '+' = door, 'S' = start, 'E' = exit, '@' = enemy

static mut ASCII_MAP: [[u8; DUN_W]; DUN_H] = [[b'#'; DUN_W]; DUN_H];

pub fn ascii_map() -> &'static [[u8; DUN_W]; DUN_H] { unsafe { &ASCII_MAP } }

// ── Dungeon state ─────────────────────────────────────────────────────────────

/// How the player left the dungeon last time — drives nonce policy.
#[derive(Copy, Clone, PartialEq)]
pub enum LastExit { None, Completed, Died, Fled }

/// Per-zone re-entry nonce record.  Max 8 tracked zones in session.
#[derive(Copy, Clone)]
struct ZoneNonce {
    zone_id: [u8; 16],
    nonce:   u32,
    last_exit: LastExit,
}

impl ZoneNonce {
    const EMPTY: Self = Self { zone_id: [0u8; 16], nonce: 0, last_exit: LastExit::None };
}

const MAX_ZONE_NONCES: usize = 8;

pub struct DungeonState {
    pub generated:  bool,
    pub seed:       u32,
    pub room_count: usize,
    pub rooms:      [Rect; 16],
    pub start:      (usize, usize),
    pub exit:       (usize, usize),
    pub enemy_pos:  [(usize, usize); 8],
    pub enemy_id:   [u16; 8],
    pub enemy_n:    usize,
    // Current zone tracking
    pub current_zone: [u8; 16],
    pub current_zone_n: usize,
    // Nonce table
    zone_nonces: [ZoneNonce; MAX_ZONE_NONCES],
}

#[derive(Copy, Clone, Default)]
pub struct Rect {
    pub x: usize, pub y: usize, pub w: usize, pub h: usize,
}

static mut DUNGEON: DungeonState = DungeonState {
    generated:      false,
    seed:           0,
    room_count:     0,
    rooms:          [Rect { x: 0, y: 0, w: 0, h: 0 }; 16],
    start:          (0, 0),
    exit:           (0, 0),
    enemy_pos:      [(0,0); 8],
    enemy_id:       [0u16; 8],
    enemy_n:        0,
    current_zone:   [0u8; 16],
    current_zone_n: 0,
    zone_nonces:    [ZoneNonce::EMPTY; MAX_ZONE_NONCES],
};

pub fn dungeon() -> &'static mut DungeonState { unsafe { &mut DUNGEON } }

// ── Generation ────────────────────────────────────────────────────────────────

impl DungeonState {
    /// Signal that the player has left the current dungeon in a particular way.
    /// Call before the next generate() so the nonce is updated correctly.
    pub fn record_exit(&mut self, exit: LastExit) {
        let zn = self.current_zone_n;
        if zn == 0 { return; }
        for rec in &mut self.zone_nonces {
            if rec.zone_id[..zn] == self.current_zone[..zn] {
                rec.last_exit = exit;
                // Increment nonce on death or flee — next entry shuffles the dungeon.
                if exit == LastExit::Died || exit == LastExit::Fled {
                    rec.nonce = rec.nonce.wrapping_add(1);
                } else if exit == LastExit::Completed {
                    // Clean completion resets the nonce — canonical layout restored.
                    rec.nonce = 0;
                }
                return;
            }
        }
    }

    /// Generate a dungeon from the zone ID.
    /// First visit: deterministic canonical seed.
    /// Re-entry after death/flee: seed XORed with incremented nonce → fresh layout.
    pub fn generate(&mut self, zone_id: &[u8]) {
        // Store current zone.
        let zn = zone_id.len().min(16);
        self.current_zone[..zn].copy_from_slice(&zone_id[..zn]);
        if zn < 16 { self.current_zone[zn..].fill(0); }
        self.current_zone_n = zn;

        // Look up or create nonce record for this zone.
        let base_seed = zone_seed(zone_id);
        let nonce = self.get_or_create_nonce(zone_id);
        let seed = base_seed ^ nonce;
        self.generated = false;
        self.room_count = 0;
        self.enemy_n = 0;

        // Clear map to walls.
        let map = unsafe { &mut ASCII_MAP };
        for row in map.iter_mut() { row.fill(b'#'); }

        let mut rng = Rng { state: seed };

        // BSP partition → rooms
        let root = Rect { x: 1, y: 1, w: DUN_W - 2, h: DUN_H - 2 };
        self.bsp_split(map, root, 5, &mut rng);

        // Start = first room centre, Exit = last room centre.
        if self.room_count >= 2 {
            let r0 = self.rooms[0];
            self.start = (r0.x + r0.w / 2, r0.y + r0.h / 2);
            map[self.start.1][self.start.0] = b'S';
            let rn = self.rooms[self.room_count - 1];
            self.exit = (rn.x + rn.w / 2, rn.y + rn.h / 2);
            map[self.exit.1][self.exit.0] = b'E';
        }

        // Scatter enemies in middle rooms.
        for i in 1..self.room_count.saturating_sub(1) {
            if self.enemy_n >= 8 { break; }
            let r   = self.rooms[i];
            let ex  = r.x + 1 + (rng.next() as usize % r.w.max(2));
            let ey  = r.y + 1 + (rng.next() as usize % r.h.max(2));
            let eid = match rng.next() % 4 {
                0 => crate::combat::ENEMY_BANDIT,
                1 => crate::combat::ENEMY_GUARD,
                2 => crate::combat::ENEMY_SHADE,
                _ => crate::combat::ENEMY_ALFIRIN,
            };
            let idx = self.enemy_n;
            self.enemy_pos[idx] = (ex.min(DUN_W-1), ey.min(DUN_H-1));
            self.enemy_id[idx]  = eid;
            self.enemy_n += 1;
            if ex < DUN_W && ey < DUN_H { map[ey][ex] = b'@'; }
        }

        self.generated = true;
    }

    fn get_or_create_nonce(&mut self, zone_id: &[u8]) -> u32 {
        let zn = zone_id.len().min(16);
        // Search existing records.
        for rec in &self.zone_nonces {
            if !rec.zone_id.iter().any(|&b| b != 0)
                && zone_id.iter().all(|&b| b == 0) { continue; }
            if rec.zone_id[..zn] == zone_id[..zn] {
                return rec.nonce;
            }
        }
        // Insert into first empty slot.
        for rec in &mut self.zone_nonces {
            if rec.zone_id.iter().all(|&b| b == 0) {
                rec.zone_id[..zn].copy_from_slice(&zone_id[..zn]);
                rec.nonce    = 0;
                rec.last_exit = LastExit::None;
                return 0;
            }
        }
        // Table full — return 0 (deterministic fallback).
        0
    }

    fn bsp_split(&mut self, map: &mut [[u8; DUN_W]; DUN_H],
                 area: Rect, depth: u8, rng: &mut Rng)
    {
        if depth == 0 || area.w < 6 || area.h < 6 {
            // Leaf: carve a room.
            self.carve_room(map, area, rng);
            return;
        }
        // Split horizontally or vertically.
        let horiz = if area.w > area.h { false } else if area.h > area.w { true }
                    else { rng.next() % 2 == 0 };
        if horiz && area.h >= 8 {
            let split = area.y + 3 + (rng.next() as usize % (area.h - 6).max(1));
            let a = Rect { x: area.x, y: area.y, w: area.w, h: split - area.y };
            let b = Rect { x: area.x, y: split,   w: area.w, h: area.y + area.h - split };
            self.bsp_split(map, a, depth - 1, rng);
            self.bsp_split(map, b, depth - 1, rng);
            // Connect rooms through the split with a vertical corridor.
            self.connect_v(map, area.x + area.w / 2, a.y + a.h / 2, b.y + b.h / 2);
        } else if !horiz && area.w >= 8 {
            let split = area.x + 3 + (rng.next() as usize % (area.w - 6).max(1));
            let a = Rect { x: area.x, y: area.y, w: split - area.x,       h: area.h };
            let b = Rect { x: split,   y: area.y, w: area.x + area.w - split, h: area.h };
            self.bsp_split(map, a, depth - 1, rng);
            self.bsp_split(map, b, depth - 1, rng);
            self.connect_h(map, area.y + area.h / 2, a.x + a.w / 2, b.x + b.w / 2);
        } else {
            self.carve_room(map, area, rng);
        }
    }

    fn carve_room(&mut self, map: &mut [[u8; DUN_W]; DUN_H], area: Rect, rng: &mut Rng) {
        if self.room_count >= 16 { return; }
        let rw = 3 + (rng.next() as usize % (area.w.saturating_sub(3)).max(1));
        let rh = 3 + (rng.next() as usize % (area.h.saturating_sub(3)).max(1));
        let rx = area.x + (rng.next() as usize % (area.w.saturating_sub(rw) + 1).max(1));
        let ry = area.y + (rng.next() as usize % (area.h.saturating_sub(rh) + 1).max(1));
        let x0 = rx.min(DUN_W - 1);
        let y0 = ry.min(DUN_H - 1);
        let x1 = (rx + rw).min(DUN_W - 1);
        let y1 = (ry + rh).min(DUN_H - 1);
        for y in y0..=y1 {
            for x in x0..=x1 {
                map[y][x] = b'.';
            }
        }
        // Place door in one wall.
        if x0 > 0 { map[y0 + rh/2][x0] = b'+'; }
        self.rooms[self.room_count] = Rect { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
        self.room_count += 1;
    }

    fn connect_h(&self, map: &mut [[u8; DUN_W]; DUN_H], row: usize, x0: usize, x1: usize) {
        let lo = x0.min(x1); let hi = x0.max(x1);
        for x in lo..=hi.min(DUN_W - 1) {
            if row < DUN_H && map[row][x] == b'#' { map[row][x] = b'.'; }
        }
    }

    fn connect_v(&self, map: &mut [[u8; DUN_W]; DUN_H], col: usize, y0: usize, y1: usize) {
        let lo = y0.min(y1); let hi = y0.max(y1);
        for y in lo..=hi.min(DUN_H - 1) {
            if col < DUN_W && map[y][col] == b'#' { map[y][col] = b'.'; }
        }
    }

    // ── Voxel scene from ASCII map ─────────────────────────────────────────────

    pub fn build_voxel_scene(&self, scene: &mut VoxelScene) {
        use crate::renderer_bridge::tile_colors;
        let map = unsafe { &ASCII_MAP };
        for z in 0..DUN_H {
            for x in 0..DUN_W {
                let ch = map[z][x];
                match ch {
                    b'.' | b'S' | b'E' | b'@' => {
                        // Floor
                        scene.set(x, DUN_FLOOR_Y, z, VoxelNode::terrain(b'D'));
                    }
                    b'+' => {
                        scene.set(x, DUN_FLOOR_Y, z, VoxelNode::solid(b'+'));
                        scene.set(x, DUN_FLOOR_Y + 1, z, VoxelNode::solid(b'+'));
                    }
                    b'#' => {
                        // Wall — 2 cells high
                        scene.set(x, DUN_FLOOR_Y, z, VoxelNode::solid(b'#'));
                        if DUN_FLOOR_Y + 1 < MAP_Y {
                            scene.set(x, DUN_FLOOR_Y + 1, z, VoxelNode::solid(b'W'));
                        }
                    }
                    _ => {}
                }
                let _ = tile_colors;
            }
        }
        scene.cull_all();
    }
}

// ── RNG ───────────────────────────────────────────────────────────────────────

struct Rng { state: u32 }

impl Rng {
    fn next(&mut self) -> u32 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 17;
        self.state ^= self.state << 5;
        self.state
    }
}

fn zone_seed(zone_id: &[u8]) -> u32 {
    let mut h: u32 = 0x811C_9DC5;
    for &b in zone_id.iter().take(16) {
        h ^= b as u32;
        h = h.wrapping_mul(0x0100_0193);
    }
    if h == 0 { 1 } else { h }
}

/**
 * dungeonGenerator.js
 *
 * Seeded procedural dungeon generation for KLGS roguelike dungeons.
 * Produces a voxel array compatible with the existing renderer and collision map pipeline.
 *
 * Algorithm: BSP (Binary Space Partitioning) room placement with corridor connectors.
 * Each dungeon randomizes on entry — the seed is ephemeral (not persisted).
 * Only run outcomes persist in the stack, never the layout itself.
 *
 * Output voxels are typed for collision map inference:
 *   "floor"   → passable
 *   "wall"    → impassable (solid)
 *   "door"    → passable (entry/exit markers)
 *   "chest"   → passable (interactable)
 *   "pillar"  → impassable
 *   "stair"   → passable (floor transition)
 *
 * Usage:
 *   const gen = createDungeonGenerator(dungeonDef, options);
 *   const { voxels, rooms, encounters, metadata } = gen.generate();
 */

// ── Seeded PRNG (mulberry32) ──────────────────────────────────────────────────
function mulberry32(seed) {
  let s = seed >>> 0;
  return function () {
    s += 0x6d2b79f5;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeRng(seed) {
  if (seed == null) seed = (Date.now() ^ (Math.random() * 0xffffffff)) >>> 0;
  const rand = mulberry32(seed);
  return {
    seed,
    float: () => rand(),
    int: (lo, hi) => Math.floor(rand() * (hi - lo + 1)) + lo,   // inclusive
    pick: (arr) => arr[Math.floor(rand() * arr.length)],
    bool: (prob = 0.5) => rand() < prob,
  };
}

// ── BSP node ──────────────────────────────────────────────────────────────────
function bspSplit(node, rng, minSize = 6) {
  const { x, y, w, h } = node;
  if (w < minSize * 2 && h < minSize * 2) return;   // too small to split

  const splitH = w >= h ? false : h >= w ? true : rng.bool();

  if (splitH) {
    if (h < minSize * 2) return;
    const split = rng.int(minSize, h - minSize);
    node.left  = { x, y,          w, h: split,     left: null, right: null };
    node.right = { x, y: y + split, w, h: h - split, left: null, right: null };
  } else {
    if (w < minSize * 2) return;
    const split = rng.int(minSize, w - minSize);
    node.left  = { x,          y, w: split,     h, left: null, right: null };
    node.right = { x: x + split, y, w: w - split, h, left: null, right: null };
  }

  bspSplit(node.left,  rng, minSize);
  bspSplit(node.right, rng, minSize);
}

function collectLeaves(node, leaves = []) {
  if (!node.left && !node.right) { leaves.push(node); return leaves; }
  if (node.left)  collectLeaves(node.left,  leaves);
  if (node.right) collectLeaves(node.right, leaves);
  return leaves;
}

// ── Room carving ──────────────────────────────────────────────────────────────
function carveRoom(leaf, rng, margin = 1) {
  const maxW = leaf.w - margin * 2;
  const maxH = leaf.h - margin * 2;
  const rw = rng.int(Math.max(3, Math.floor(maxW * 0.5)), maxW);
  const rh = rng.int(Math.max(3, Math.floor(maxH * 0.5)), maxH);
  const rx = leaf.x + margin + rng.int(0, maxW - rw);
  const ry = leaf.y + margin + rng.int(0, maxH - rh);
  return { x: rx, y: ry, w: rw, h: rh };
}

function roomCenter(room) {
  return { x: Math.floor(room.x + room.w / 2), y: Math.floor(room.y + room.h / 2) };
}

// ── Corridor carving ──────────────────────────────────────────────────────────
function carveCorridor(grid, a, b) {
  const ca = roomCenter(a);
  const cb = roomCenter(b);
  // L-shaped corridor — horizontal then vertical
  const { x: x1, y: y1 } = ca;
  const { x: x2, y: y2 } = cb;
  // Horizontal segment
  const xMin = Math.min(x1, x2), xMax = Math.max(x1, x2);
  for (let x = xMin; x <= xMax; x++) {
    grid[y1] = grid[y1] || {};
    grid[y1][x] = "floor";
  }
  // Vertical segment
  const yMin = Math.min(y1, y2), yMax = Math.max(y1, y2);
  for (let y = yMin; y <= yMax; y++) {
    grid[y] = grid[y] || {};
    grid[y][x2] = "floor";
  }
}

// ── Grid → voxel array ────────────────────────────────────────────────────────
function gridToVoxels(grid, gridW, gridH, tilePalette, z = 0) {
  const voxels = [];
  // First pass: floor/content cells
  for (let y = 0; y < gridH; y++) {
    for (let x = 0; x < gridW; x++) {
      const cell = grid[y]?.[x];
      if (!cell) continue;
      voxels.push({ x, y, z, type: cell, meta: {}, palette: tilePalette });
    }
  }
  // Second pass: walls around floor cells
  const wallSet = new Set();
  for (let y = 0; y < gridH; y++) {
    for (let x = 0; x < gridW; x++) {
      if (!grid[y]?.[x]) continue;
      for (const [dx, dy] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= gridW || ny >= gridH) continue;
        if (!grid[ny]?.[nx]) {
          const wk = `${nx},${ny}`;
          if (!wallSet.has(wk)) {
            wallSet.add(wk);
            voxels.push({ x: nx, y: ny, z, type: "wall", meta: { solid: true }, palette: tilePalette });
          }
        }
      }
    }
  }
  return voxels;
}

// ── Encounter spawning ────────────────────────────────────────────────────────
const ENCOUNTER_KINDS = ["combat", "negotiation", "observation", "trap", "lore"];

function spawnEncounters(rooms, rng, dungeonDef) {
  const encounters = [];
  for (let i = 1; i < rooms.length; i++) {        // skip spawn room (index 0)
    if (i === rooms.length - 1) continue;          // skip exit room (last)
    if (!rng.bool(0.65)) continue;                 // ~65% of rooms get encounters

    const center = roomCenter(rooms[i]);
    const kind = rng.pick(ENCOUNTER_KINDS);
    encounters.push({
      room_index: i,
      x: center.x,
      y: center.y,
      kind,
      vitriol_affinity: dungeonDef.vitriol_affinity,
      stack_event: `${dungeonDef.stack_event_prefix}.encounter.${kind}`,
    });
  }
  return encounters;
}

// ── Special tile placement ────────────────────────────────────────────────────
function placeSpecialTiles(grid, rooms, rng, dungeonDef) {
  const specials = [];

  // Entry stair in first room
  const entry = roomCenter(rooms[0]);
  grid[entry.y][entry.x] = "stair";
  specials.push({ type: "entry", x: entry.x, y: entry.y });

  // Exit stair in last room
  const exit = roomCenter(rooms[rooms.length - 1]);
  grid[exit.y][exit.x] = "stair";
  specials.push({ type: "exit", x: exit.x, y: exit.y });

  // Chests in 1-3 rooms
  const chestRooms = rooms.slice(1, -1).filter(() => rng.bool(0.3));
  for (const room of chestRooms.slice(0, 3)) {
    const cx = rng.int(room.x + 1, room.x + room.w - 2);
    const cy = rng.int(room.y + 1, room.y + room.h - 2);
    grid[cy] = grid[cy] || {};
    grid[cy][cx] = "chest";
    specials.push({ type: "chest", x: cx, y: cy });
  }

  // Dungeon-specific special: lust ring gets a desire-crystal node
  if (dungeonDef.id === "ring_lust" && rooms.length > 2) {
    const midRoom = rooms[Math.floor(rooms.length / 2)];
    const mc = roomCenter(midRoom);
    grid[mc.y][mc.x] = "crystal";
    specials.push({ type: "desire_crystal", x: mc.x, y: mc.y });
  }

  // Salamander dungeons get forge tiles
  if (dungeonDef.id === "fae_salamander" && rooms.length > 1) {
    const forgeRoom = rooms[rng.int(1, rooms.length - 1)];
    const fc = roomCenter(forgeRoom);
    grid[fc.y][fc.x] = "forge";
    specials.push({ type: "forge", x: fc.x, y: fc.y });
  }

  return specials;
}

// ── Public: createDungeonGenerator ───────────────────────────────────────────
/**
 * @param {object} dungeonDef   — one entry from dungeonRegistry.js (DUNGEON_BY_ID[id])
 * @param {object} [options]
 * @param {number} [options.seed]       — explicit seed (random if omitted)
 * @param {number} [options.gridW=40]   — grid columns
 * @param {number} [options.gridH=40]   — grid rows
 * @param {number} [options.minRoomSize=5]
 * @param {number} [options.depth=0]    — Z-level offset (multi-floor support)
 */
export function createDungeonGenerator(dungeonDef, options = {}) {
  const {
    seed      = null,
    gridW     = 40,
    gridH     = 40,
    minRoomSize = 5,
    depth     = 0,
  } = options;

  return {
    /**
     * Generate a dungeon layout.
     * @returns {{ voxels, rooms, encounters, specials, metadata }}
     */
    generate() {
      const rng = makeRng(seed);

      // BSP partition
      const root = { x: 0, y: 0, w: gridW, h: gridH, left: null, right: null };
      bspSplit(root, rng, minRoomSize);
      const leaves = collectLeaves(root);

      // Carve rooms
      const rooms = leaves.map(leaf => carveRoom(leaf, rng));

      // Build floor grid
      const grid = {};
      for (const room of rooms) {
        for (let y = room.y; y < room.y + room.h; y++) {
          grid[y] = grid[y] || {};
          for (let x = room.x; x < room.x + room.w; x++) {
            grid[y][x] = "floor";
          }
        }
      }

      // Connect consecutive rooms with corridors
      for (let i = 0; i < rooms.length - 1; i++) {
        carveCorridor(grid, rooms[i], rooms[i + 1]);
      }

      // Special tiles (entry/exit/chests/dungeon-specific)
      const specials = placeSpecialTiles(grid, rooms, rng, dungeonDef);

      // Convert grid to voxel array
      const voxels = gridToVoxels(grid, gridW, gridH, dungeonDef.tile_palette, depth);

      // Encounter spawning
      const encounters = spawnEncounters(rooms, rng, dungeonDef);

      return {
        voxels,
        rooms,
        encounters,
        specials,
        metadata: {
          dungeon_id: dungeonDef.id,
          seed: rng.seed,
          grid_w: gridW,
          grid_h: gridH,
          depth,
          room_count: rooms.length,
          encounter_count: encounters.length,
          tile_palette: dungeonDef.tile_palette,
          music_register: dungeonDef.music_register,
          generated_at: new Date().toISOString(),
          // Layout is ephemeral — do not persist. Only outcomes go to the stack.
          ephemeral: true,
        },
      };
    },
  };
}

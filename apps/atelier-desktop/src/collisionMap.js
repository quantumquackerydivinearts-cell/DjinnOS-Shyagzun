/**
 * collisionMap.js
 *
 * Builds a spatial collision grid from a voxel array, draws an isometric overlay,
 * and exports the grid as a portable JSON artifact for Ko's Labyrinth / QQVA.
 *
 * Pipeline:
 *   buildCollisionMap(voxels)          → CollisionMap
 *   drawCollisionOverlay(canvas, map, settings) → void  (paints over renderer canvas)
 *   exportCollisionMap(map, packId)    → plain object  (JSON-serialisable)
 */

// ── Solid type inference ──────────────────────────────────────────────────────
// Used only when meta.walkable / meta.solid are absent from the voxel.
const INFERRED_SOLID_TYPES = new Set([
  "wall", "stone", "water", "lava", "mountain", "cliff",
  "boulder", "pillar", "fence", "barrier", "column",
  "structure_wall", "bedrock", "ice_wall", "cactus",
]);

const INFERRED_PASSABLE_TYPES = new Set([
  "floor", "cobble", "grass", "dirt", "sand", "path", "road",
  "plaza", "bridge", "terrain", "structure_floor", "carpet",
  "tile", "plank", "gravel", "mud", "snow",
]);

/**
 * Determine whether a voxel is passable.
 * Priority: meta.walkable → !meta.solid → type inference → default passable.
 */
function isVoxelPassable(voxel) {
  const meta = voxel.meta || {};

  // Explicit walkable flag wins
  if (typeof meta.walkable === "boolean") return meta.walkable;

  // Explicit solid flag
  if (typeof meta.solid === "boolean") return !meta.solid;

  // Type-based inference
  const t = String(voxel.type || "").toLowerCase();
  if (INFERRED_SOLID_TYPES.has(t)) return false;
  if (INFERRED_PASSABLE_TYPES.has(t)) return true;

  // Prefix heuristics
  if (t.startsWith("wall") || t.startsWith("barrier") || t.startsWith("fence")) return false;
  if (t.startsWith("floor") || t.startsWith("ground") || t.startsWith("terrain")) return true;

  // Default: passable (open world assumption)
  return true;
}

// ── Key helpers ───────────────────────────────────────────────────────────────
function voxelKey(x, y, z) {
  return `${x},${y},${z}`;
}

function parseKey(k) {
  const [x, y, z] = k.split(",").map(Number);
  return { x, y, z };
}

// ── buildCollisionMap ─────────────────────────────────────────────────────────
/**
 * @param {Array} voxels  — rendererMotionVoxels (or any voxel array)
 * @returns {CollisionMap}
 *
 * CollisionMap shape:
 * {
 *   grid: Map<"x,y,z", { passable, inferred, type, meta }>,
 *   passable: Set<"x,y,z">,
 *   impassable: Set<"x,y,z">,
 *   bounds: { minX, maxX, minY, maxY, minZ, maxZ },
 *   stats: { total, passable_count, impassable_count, inferred_count },
 * }
 */
export function buildCollisionMap(voxels) {
  if (!Array.isArray(voxels) || voxels.length === 0) {
    return {
      grid: new Map(),
      passable: new Set(),
      impassable: new Set(),
      bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0, minZ: 0, maxZ: 0 },
      stats: { total: 0, passable_count: 0, impassable_count: 0, inferred_count: 0 },
    };
  }

  const grid = new Map();
  const passable = new Set();
  const impassable = new Set();

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let minZ = Infinity, maxZ = -Infinity;
  let inferred_count = 0;

  for (const voxel of voxels) {
    const x = Number(voxel.x ?? 0);
    const y = Number(voxel.y ?? 0);
    const z = Number(voxel.z ?? 0);

    // Track bounds
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;

    const meta = voxel.meta || {};
    const hasExplicit = typeof meta.walkable === "boolean" || typeof meta.solid === "boolean";
    if (!hasExplicit) inferred_count++;

    const pass = isVoxelPassable(voxel);
    const key = voxelKey(x, y, z);

    grid.set(key, { passable: pass, inferred: !hasExplicit, type: voxel.type || "", meta });
    if (pass) passable.add(key); else impassable.add(key);
  }

  return {
    grid,
    passable,
    impassable,
    bounds: { minX, maxX, minY, maxY, minZ, maxZ },
    stats: {
      total: voxels.length,
      passable_count: passable.size,
      impassable_count: impassable.size,
      inferred_count,
    },
  };
}

// ── Isometric projection ──────────────────────────────────────────────────────
// Mirrors the renderer's own projection so overlay cells align with tiles.
function toIso(x, y, z, tile, zScale, offsetX, offsetY) {
  const isoX = (x - y) * tile + offsetX;
  const isoY = (x + y) * (tile * 0.5) - z * zScale + offsetY;
  return { isoX, isoY };
}

function isoTilePolygon(x, y, z, tile, zScale, offsetX, offsetY) {
  // Diamond corners of the top face of the tile
  const hw = tile;        // half-width  = tile (full diamond width)
  const hh = tile * 0.5;  // half-height
  const { isoX, isoY } = toIso(x, y, z, tile, zScale, offsetX, offsetY);

  return [
    [isoX,      isoY - hh],  // top
    [isoX + hw, isoY      ], // right
    [isoX,      isoY + hh],  // bottom
    [isoX - hw, isoY      ], // left
  ];
}

// ── drawCollisionOverlay ──────────────────────────────────────────────────────
/**
 * Paints a semi-transparent pass/fail overlay on top of the renderer canvas.
 * Call this *after* drawVoxelScene so the overlay sits on top.
 *
 * @param {HTMLCanvasElement} canvas
 * @param {CollisionMap} collisionMap   — result of buildCollisionMap
 * @param {object} settings             — voxelSettings (for tile, zScale)
 */
export function drawCollisionOverlay(canvas, collisionMap, settings = {}) {
  if (!canvas || !collisionMap || collisionMap.grid.size === 0) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const tile   = Number(settings.tile   ?? 16);
  const zScale = Number(settings.zScale ?? 8);
  const cw = canvas.width;
  const ch = canvas.height;

  // Centre origin matches renderer convention
  const offsetX = cw / 2;
  const offsetY = ch / 2;

  const PASSABLE_FILL     = "rgba(46,204,113,0.28)";
  const IMPASSABLE_FILL   = "rgba(231,76,60,0.32)";
  const INFERRED_STROKE   = "rgba(243,156,18,0.55)";
  const PASSABLE_STROKE   = "rgba(46,204,113,0.55)";
  const IMPASSABLE_STROKE = "rgba(231,76,60,0.55)";

  ctx.save();

  for (const [key, cell] of collisionMap.grid) {
    const { x, y, z } = parseKey(key);
    const poly = isoTilePolygon(x, y, z, tile, zScale, offsetX, offsetY);

    ctx.beginPath();
    ctx.moveTo(poly[0][0], poly[0][1]);
    for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0], poly[i][1]);
    ctx.closePath();

    ctx.fillStyle = cell.passable ? PASSABLE_FILL : IMPASSABLE_FILL;
    ctx.fill();

    ctx.strokeStyle = cell.inferred
      ? INFERRED_STROKE
      : cell.passable ? PASSABLE_STROKE : IMPASSABLE_STROKE;
    ctx.lineWidth = cell.inferred ? 1.2 : 0.8;
    ctx.stroke();
  }

  ctx.restore();
}

// ── exportCollisionMap ────────────────────────────────────────────────────────
/**
 * Serialise a collision map to a portable JSON object.
 *
 * @param {CollisionMap} collisionMap
 * @param {string}       packId        — render pack id or scene id
 * @returns {object}  JSON-serialisable
 */
export function exportCollisionMap(collisionMap, packId = "unknown") {
  const { grid, bounds, stats } = collisionMap;

  const gridArray = [];
  for (const [key, cell] of grid) {
    const { x, y, z } = parseKey(key);
    gridArray.push({
      x, y, z,
      passable: cell.passable,
      inferred: cell.inferred,
      type: cell.type,
    });
  }

  return {
    schema: "qqva.collision_map.v1",
    pack_id: packId,
    generated_at: new Date().toISOString(),
    bounds,
    stats,
    passable: [...collisionMap.passable].map(parseKey),
    impassable: [...collisionMap.impassable].map(parseKey),
    grid: gridArray,
  };
}
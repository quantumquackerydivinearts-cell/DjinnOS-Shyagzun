/**
 * gltfBridge.js
 *
 * GLTF 2.0 ↔ voxel scene bridge — no external dependencies.
 *
 *   voxelsToGlb(voxels, options)  → ArrayBuffer  (.glb — opens in Blender)
 *   parseGltfFile(file, options)  → Promise<voxel[]>  (.glb or .gltf → renderer voxels)
 *
 * Coordinate mapping (GLTF is Y-up, right-handed):
 *   GLTF X  =  vox.x * tile
 *   GLTF Y  =  vox.z * zScale
 *   GLTF Z  = -vox.y * tile
 */

// ── Material colour table ─────────────────────────────────────────────────────
const TYPE_COLORS = {
  floor:           [0.65, 0.60, 0.55, 1.0],
  cobble:          [0.55, 0.55, 0.52, 1.0],
  wall:            [0.40, 0.35, 0.30, 1.0],
  structure_wall:  [0.45, 0.40, 0.38, 1.0],
  structure_floor: [0.60, 0.58, 0.55, 1.0],
  grass:           [0.25, 0.65, 0.20, 1.0],
  dirt:            [0.55, 0.40, 0.25, 1.0],
  sand:            [0.85, 0.78, 0.55, 1.0],
  gravel:          [0.60, 0.57, 0.52, 1.0],
  stone:           [0.50, 0.50, 0.50, 1.0],
  bedrock:         [0.25, 0.25, 0.25, 1.0],
  terrain:         [0.35, 0.55, 0.25, 1.0],
  water:           [0.10, 0.45, 0.85, 0.75],
  lava:            [0.90, 0.30, 0.05, 1.0],
  snow:            [0.92, 0.95, 0.98, 1.0],
  plinth:          [0.70, 0.68, 0.65, 1.0],
  pillar:          [0.72, 0.70, 0.65, 1.0],
  bench:           [0.60, 0.45, 0.28, 1.0],
  spire:           [0.55, 0.50, 0.60, 1.0],
};

function typeColor(type) {
  return TYPE_COLORS[String(type || "").toLowerCase()] || [0.5, 0.5, 0.5, 1.0];
}

// ── Box geometry (24 vertices — 4 per face, flat normals) ─────────────────────
// Local space: centred at origin, size 1 × 1 × 1.
// Scale by (tile, zScale, tile) and translate to (cx, cy, cz) in GLTF space.
const LOCAL_POS = new Float32Array([
  // Top    (+Y)
  -0.5, +0.5, -0.5,  +0.5, +0.5, -0.5,  +0.5, +0.5, +0.5,  -0.5, +0.5, +0.5,
  // Bottom (-Y)
  -0.5, -0.5, +0.5,  +0.5, -0.5, +0.5,  +0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,
  // Front  (+Z)
  -0.5, -0.5, +0.5,  +0.5, -0.5, +0.5,  +0.5, +0.5, +0.5,  -0.5, +0.5, +0.5,
  // Back   (-Z)
  +0.5, -0.5, -0.5,  -0.5, -0.5, -0.5,  -0.5, +0.5, -0.5,  +0.5, +0.5, -0.5,
  // Right  (+X)
  +0.5, -0.5, +0.5,  +0.5, -0.5, -0.5,  +0.5, +0.5, -0.5,  +0.5, +0.5, +0.5,
  // Left   (-X)
  -0.5, -0.5, -0.5,  -0.5, -0.5, +0.5,  -0.5, +0.5, +0.5,  -0.5, +0.5, -0.5,
]);

const LOCAL_NRM = new Float32Array([
   0, 1, 0,  0, 1, 0,  0, 1, 0,  0, 1, 0,   // Top
   0,-1, 0,  0,-1, 0,  0,-1, 0,  0,-1, 0,   // Bottom
   0, 0, 1,  0, 0, 1,  0, 0, 1,  0, 0, 1,   // Front
   0, 0,-1,  0, 0,-1,  0, 0,-1,  0, 0,-1,   // Back
   1, 0, 0,  1, 0, 0,  1, 0, 0,  1, 0, 0,   // Right
  -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0,  // Left
]);

// 36 indices per box (CCW winding)
const LOCAL_IDX = [
   0, 1, 2,   0, 2, 3,   // Top
   4, 5, 6,   4, 6, 7,   // Bottom
   8, 9,10,   8,10,11,   // Front
  12,13,14,  12,14,15,   // Back
  16,17,18,  16,18,19,   // Right
  20,21,22,  20,22,23,   // Left
];

// ── Mesh builder ──────────────────────────────────────────────────────────────
function buildMeshBuffers(voxels, tile, zScale) {
  const n = voxels.length;
  const positions = new Float32Array(n * 24 * 3);
  const normals   = new Float32Array(n * 24 * 3);
  const indices   = new Uint32Array(n * 36);

  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

  const sx = tile, sy = zScale, sz = tile;

  for (let i = 0; i < n; i++) {
    const v = voxels[i];
    const cx =  Number(v.x ?? 0) * tile;
    const cy =  Number(v.z ?? 0) * zScale;
    const cz = -Number(v.y ?? 0) * tile;

    const pb = i * 72;  // 24 vertices × 3 floats
    const ib = i * 36;

    for (let j = 0; j < 24; j++) {
      const lj = j * 3;
      const wx = LOCAL_POS[lj    ] * sx + cx;
      const wy = LOCAL_POS[lj + 1] * sy + cy;
      const wz = LOCAL_POS[lj + 2] * sz + cz;
      positions[pb + lj    ] = wx;
      positions[pb + lj + 1] = wy;
      positions[pb + lj + 2] = wz;
      normals[pb + lj    ] = LOCAL_NRM[lj    ];
      normals[pb + lj + 1] = LOCAL_NRM[lj + 1];
      normals[pb + lj + 2] = LOCAL_NRM[lj + 2];

      if (wx < minX) minX = wx; if (wx > maxX) maxX = wx;
      if (wy < minY) minY = wy; if (wy > maxY) maxY = wy;
      if (wz < minZ) minZ = wz; if (wz > maxZ) maxZ = wz;
    }

    for (let k = 0; k < 36; k++) {
      indices[ib + k] = LOCAL_IDX[k] + i * 24;
    }
  }

  return {
    positions, normals, indices,
    min: [minX, minY, minZ],
    max: [maxX, maxY, maxZ],
  };
}

// ── GLB packer ────────────────────────────────────────────────────────────────
function pad4(n) { return Math.ceil(n / 4) * 4; }

function packGlb(gltfJson, binBuffer) {
  const jsonBytes = new TextEncoder().encode(JSON.stringify(gltfJson));
  const jsonPadded = pad4(jsonBytes.byteLength);
  const binPadded  = pad4(binBuffer.byteLength);

  const total = 12 + 8 + jsonPadded + (binBuffer.byteLength > 0 ? 8 + binPadded : 0);
  const out = new ArrayBuffer(total);
  const view = new DataView(out);
  let off = 0;

  // Header
  view.setUint32(off, 0x46546C67, true); off += 4; // magic "glTF"
  view.setUint32(off, 2,          true); off += 4; // version
  view.setUint32(off, total,      true); off += 4; // length

  // JSON chunk
  view.setUint32(off, jsonPadded,   true); off += 4;
  view.setUint32(off, 0x4E4F534A,   true); off += 4; // "JSON"
  new Uint8Array(out, off, jsonBytes.byteLength).set(jsonBytes);
  // pad with spaces
  for (let i = jsonBytes.byteLength; i < jsonPadded; i++) {
    new Uint8Array(out)[off + i] = 0x20;
  }
  off += jsonPadded;

  // BIN chunk
  if (binBuffer.byteLength > 0) {
    view.setUint32(off, binPadded,    true); off += 4;
    view.setUint32(off, 0x004E4942,   true); off += 4; // "BIN\0"
    new Uint8Array(out, off, binBuffer.byteLength).set(new Uint8Array(binBuffer));
    off += binPadded;
  }

  return out;
}

// ── voxelsToGlb ───────────────────────────────────────────────────────────────
/**
 * Convert a voxel array to a GLB binary (opens in Blender, three.js, Godot, etc.)
 *
 * @param {Array}  voxels   — rendererMotionVoxels or any voxel array
 * @param {object} options  — { tile=16, zScale=8 }
 * @returns {ArrayBuffer}
 */
export function voxelsToGlb(voxels, options = {}) {
  const tile   = Number(options.tile   ?? 16);
  const zScale = Number(options.zScale ?? 8);

  if (!Array.isArray(voxels) || voxels.length === 0) {
    // Return minimal valid empty GLB
    const gltf = { asset: { version: "2.0", generator: "QQVA" }, scene: 0,
      scenes: [{ name: "Scene", nodes: [] }], nodes: [], meshes: [], materials: [],
      accessors: [], bufferViews: [], buffers: [] };
    return packGlb(gltf, new ArrayBuffer(0));
  }

  // Group by type
  const groups = new Map();
  for (const v of voxels) {
    const t = String(v.type || "unknown").toLowerCase();
    if (!groups.has(t)) groups.set(t, []);
    groups.get(t).push(v);
  }

  const gltfMaterials = [];
  const gltfMeshes    = [];
  const gltfNodes     = [];
  const gltfAccessors = [];
  const gltfBufferViews = [];

  // Single binary buffer — accumulate ArrayBuffers then merge
  const binaryChunks = [];
  let byteOffset = 0;

  let meshIdx = 0;
  for (const [typeName, typeVoxels] of groups) {
    const { positions, normals, indices, min, max } = buildMeshBuffers(typeVoxels, tile, zScale);

    const posByteLen = positions.buffer.byteLength;
    const nrmByteLen = normals.buffer.byteLength;
    const idxByteLen = indices.buffer.byteLength;

    // BufferViews
    const bvPos = gltfBufferViews.length;
    gltfBufferViews.push({ buffer: 0, byteOffset, byteLength: posByteLen, target: 34962 });
    byteOffset += pad4(posByteLen);

    const bvNrm = gltfBufferViews.length;
    gltfBufferViews.push({ buffer: 0, byteOffset, byteLength: nrmByteLen, target: 34962 });
    byteOffset += pad4(nrmByteLen);

    const bvIdx = gltfBufferViews.length;
    gltfBufferViews.push({ buffer: 0, byteOffset, byteLength: idxByteLen, target: 34963 });
    byteOffset += pad4(idxByteLen);

    binaryChunks.push(positions.buffer, normals.buffer, indices.buffer);

    // Accessors
    const accPos = gltfAccessors.length;
    gltfAccessors.push({
      bufferView: bvPos, byteOffset: 0,
      componentType: 5126 /* FLOAT */, type: "VEC3",
      count: typeVoxels.length * 24,
      min, max,
    });

    const accNrm = gltfAccessors.length;
    gltfAccessors.push({
      bufferView: bvNrm, byteOffset: 0,
      componentType: 5126, type: "VEC3",
      count: typeVoxels.length * 24,
    });

    const accIdx = gltfAccessors.length;
    gltfAccessors.push({
      bufferView: bvIdx, byteOffset: 0,
      componentType: 5125 /* UNSIGNED_INT */, type: "SCALAR",
      count: typeVoxels.length * 36,
    });

    // Material
    const matIdx = gltfMaterials.length;
    const color = typeColor(typeName);
    gltfMaterials.push({
      name: typeName,
      pbrMetallicRoughness: {
        baseColorFactor: color,
        metallicFactor: 0.0,
        roughnessFactor: 0.85,
      },
      alphaMode: color[3] < 1 ? "BLEND" : "OPAQUE",
    });

    // Mesh
    gltfMeshes.push({
      name: typeName,
      primitives: [{
        attributes: { POSITION: accPos, NORMAL: accNrm },
        indices: accIdx,
        material: matIdx,
        mode: 4 /* TRIANGLES */,
      }],
    });

    gltfNodes.push({ name: typeName, mesh: meshIdx });
    meshIdx++;
  }

  // Merge binary chunks (padded)
  const totalBin = byteOffset;
  const binBuffer = new ArrayBuffer(totalBin);
  const binView = new Uint8Array(binBuffer);
  let binOff = 0;
  for (const chunk of binaryChunks) {
    binView.set(new Uint8Array(chunk), binOff);
    binOff += pad4(chunk.byteLength);
  }

  const gltf = {
    asset: { version: "2.0", generator: "QQVA voxel renderer" },
    scene: 0,
    scenes: [{ name: "Scene", nodes: gltfNodes.map((_, i) => i) }],
    nodes: gltfNodes,
    meshes: gltfMeshes,
    materials: gltfMaterials,
    accessors: gltfAccessors,
    bufferViews: gltfBufferViews,
    buffers: [{ byteLength: totalBin }],
  };

  return packGlb(gltf, binBuffer);
}

// ── GLTF/GLB parser ───────────────────────────────────────────────────────────
function readGlbChunks(buffer) {
  const view = new DataView(buffer);
  const magic = view.getUint32(0, true);
  if (magic !== 0x46546C67) throw new Error("Not a GLB file (bad magic)");

  let off = 12;
  let jsonChunk = null;
  let binChunk  = null;

  while (off < buffer.byteLength) {
    const chunkLen  = view.getUint32(off,     true);
    const chunkType = view.getUint32(off + 4, true);
    off += 8;
    if (chunkType === 0x4E4F534A) { // JSON
      jsonChunk = new TextDecoder().decode(new Uint8Array(buffer, off, chunkLen));
    } else if (chunkType === 0x004E4942) { // BIN
      binChunk = buffer.slice(off, off + chunkLen);
    }
    off += pad4(chunkLen);
  }

  if (!jsonChunk) throw new Error("GLB has no JSON chunk");
  return { gltf: JSON.parse(jsonChunk), bin: binChunk };
}

function resolveBuffer(gltf, bufferIdx, externalBin) {
  const bufDef = gltf.buffers?.[bufferIdx];
  if (!bufDef) return null;
  if (externalBin && bufferIdx === 0 && !bufDef.uri) return externalBin;
  if (bufDef.uri?.startsWith("data:")) {
    const base64 = bufDef.uri.split(",")[1];
    const raw = atob(base64);
    const ab = new ArrayBuffer(raw.length);
    const u8 = new Uint8Array(ab);
    for (let i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
    return ab;
  }
  return null;
}

function readAccessorData(gltf, accessorIdx, externalBin) {
  const acc = gltf.accessors?.[accessorIdx];
  if (!acc) return null;

  const bv  = gltf.bufferViews?.[acc.bufferView];
  if (!bv) return null;

  const buf = resolveBuffer(gltf, bv.buffer ?? 0, externalBin);
  if (!buf) return null;

  const byteOff = (bv.byteOffset ?? 0) + (acc.byteOffset ?? 0);
  const compType = acc.componentType;
  const count = acc.count;

  const typeComponentCount = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
  const numComponents = typeComponentCount[acc.type] ?? 1;
  const total = count * numComponents;

  if (compType === 5126) return new Float32Array(buf, byteOff, total);   // FLOAT
  if (compType === 5125) return new Uint32Array(buf, byteOff, total);    // UNSIGNED_INT
  if (compType === 5123) return new Uint16Array(buf, byteOff, total);    // UNSIGNED_SHORT
  return null;
}

/**
 * Convert GLTF mesh vertices → voxel grid.
 * Strategy: snap each vertex to the nearest grid cell, deduplicate, tag with
 * the mesh node name as the voxel type.
 */
function gltfToVoxels(gltf, externalBin, options) {
  const tile   = Number(options.tile   ?? 16);
  const zScale = Number(options.zScale ?? 8);

  const voxelMap = new Map(); // "x,y,z" → { x, y, z, type }

  function processNode(nodeIdx, parentName) {
    const node = gltf.nodes?.[nodeIdx];
    if (!node) return;

    const meshIdx = node.mesh;
    const name = node.name || parentName || `mesh_${meshIdx ?? nodeIdx}`;

    if (meshIdx != null) {
      const mesh = gltf.meshes?.[meshIdx];
      if (mesh) {
        for (const prim of mesh.primitives ?? []) {
          const posAcc = prim.attributes?.POSITION;
          if (posAcc == null) continue;
          const positions = readAccessorData(gltf, posAcc, externalBin);
          if (!positions) continue;

          for (let i = 0; i < positions.length; i += 3) {
            const gx = positions[i];
            const gy = positions[i + 1];
            const gz = positions[i + 2];

            // GLTF → voxel coords
            const vx = Math.round(gx / tile);
            const vy = Math.round(-gz / tile);
            const vz = Math.round(gy / zScale);

            const key = `${vx},${vy},${vz}`;
            if (!voxelMap.has(key)) {
              voxelMap.set(key, { x: vx, y: vy, z: vz, type: name });
            }
          }
        }
      }
    }

    for (const childIdx of node.children ?? []) {
      processNode(childIdx, name);
    }
  }

  // Walk every scene node
  for (const scene of gltf.scenes ?? []) {
    for (const nodeIdx of scene.nodes ?? []) {
      processNode(nodeIdx, null);
    }
  }

  // Fallback: if no scenes, walk all nodes
  if ((gltf.scenes?.length ?? 0) === 0) {
    for (let i = 0; i < (gltf.nodes?.length ?? 0); i++) {
      processNode(i, null);
    }
  }

  return [...voxelMap.values()];
}

// ── parseGltfFile ─────────────────────────────────────────────────────────────
/**
 * Parse a .glb or .gltf File object into a voxel array.
 *
 * @param {File}   file     — from <input type="file">
 * @param {object} options  — { tile=16, zScale=8 }
 * @returns {Promise<voxel[]>}
 */
export function parseGltfFile(file, options = {}) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onerror = () => reject(new Error("Failed to read file"));

    if (file.name.toLowerCase().endsWith(".glb")) {
      reader.onload = (e) => {
        try {
          const { gltf, bin } = readGlbChunks(e.target.result);
          resolve(gltfToVoxels(gltf, bin, options));
        } catch (err) {
          reject(err);
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      // .gltf — JSON only (embedded base64 buffers handled by resolveBuffer)
      reader.onload = (e) => {
        try {
          const gltf = JSON.parse(e.target.result);
          resolve(gltfToVoxels(gltf, null, options));
        } catch (err) {
          reject(err);
        }
      };
      reader.readAsText(file);
    }
  });
}

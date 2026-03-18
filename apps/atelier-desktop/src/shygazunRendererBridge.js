/**
 * shygazunRendererBridge.js
 *
 * Translates a Shygazun kernel projection output into a voxelSettings patch.
 *
 * This is the semantic bridge: the kernel describes the nature of space and
 * time in symbolic terms; the renderer expresses that description visually.
 * A projection is not just metadata — it IS the spatial-temporal-semantic
 * description of a scene. The renderer should obey it.
 *
 *   chirality      → camera handedness, rose saturation
 *   time_topology  → visual style, edge glow
 *   space_operator → render mode, projection type
 *   axis           → camera angles
 *   tongue_projection → background palette, glow color, rose
 *   cannabis_mode  → tile size, vertical scale (depth expression)
 *   cluster_role   → LOD level
 *   trust_grade    → lighting posture
 *   authority_level → label mode
 *
 * Usage:
 *   const { patch, trace, coverage } =
 *     deriveRendererSettingsFromProjection(projectOutput, currentVoxelSettings);
 *   setVoxelSettings(prev => ({ ...prev, ...patch }));
 */

// ── Chirality tables ──────────────────────────────────────────────────────────
const LEFT_CHIRAL = new Set(["ra","tho","lu","ge","fo","kw","dr"]);
const RIGHT_CHIRAL = new Set(["ry","oth","le","gi","fe","ky","alz"]);

function classifyChirality(values) {
  let left = 0; let right = 0;
  for (const v of values) {
    const lc = String(v).toLowerCase();
    if (LEFT_CHIRAL.has(lc)) left++;
    else if (RIGHT_CHIRAL.has(lc)) right++;
  }
  if (left > right) return "left";
  if (right > left) return "right";
  return "neutral";
}

// ── Normalization helpers ─────────────────────────────────────────────────────
function toArray(v) {
  if (!v) return [];
  if (Array.isArray(v)) return v.map(String).filter(Boolean);
  return [String(v)].filter(Boolean);
}

function first(arr, fallback = null) {
  return arr.length > 0 ? arr[0].toLowerCase() : fallback;
}

// ── Tongue palette table ──────────────────────────────────────────────────────
const TONGUE_PALETTES = {
  rose:         { background: "#1a0b26", edgeGlowColor: "#ff8fd3", roseStrength: 0.65 },
  lotus:        { background: "#0b1a1a", edgeGlowColor: "#8fd3ff", roseStrength: 0.45 },
  sakura:       { background: "#1a0b15", edgeGlowColor: "#ffb3d1", roseStrength: 0.50 },
  daisy:        { background: "#1a1a0b", edgeGlowColor: "#ffd38f", roseStrength: 0.40 },
  appleblossom: { background: "#1a0f0b", edgeGlowColor: "#ffcc8f", roseStrength: 0.45 },
  aster:        { background: "#0b0b1a", edgeGlowColor: "#8f8fff", roseStrength: 0.55 },
  grapevine:    { background: "#0f0b0b", edgeGlowColor: "#c88f8f", roseStrength: 0.35 },
  cannabis:     { background: "#0b1a0b", edgeGlowColor: "#8fffa0", roseStrength: 0.50 },
};

// ── Axis → camera3d angles ────────────────────────────────────────────────────
const AXIS_CAMERA = {
  x:            { yaw:    0, pitch: 30 },
  y:            { yaw:  -90, pitch: 20 },
  z:            { yaw:  -35, pitch: 70 },
  longitudinal: { yaw:  -45, pitch: 25 },
  transverse:   { yaw: -135, pitch: 25 },
  vertical:     { yaw:  -35, pitch: 75 },
};

// ── Main bridge function ──────────────────────────────────────────────────────
/**
 * @param {object} projectOutput  Full kernel projection output
 * @param {object} currentSettings  Current voxelSettings (for safe nested merges)
 * @returns {{ patch: object, trace: object, coverage: object }}
 */
export function deriveRendererSettingsFromProjection(projectOutput, currentSettings = {}) {
  if (!projectOutput || typeof projectOutput !== "object") {
    return { patch: {}, trace: {}, coverage: { fields_mapped: 0, fields_total: 9, unmapped: [] } };
  }

  const composed = projectOutput.composed_features || {};
  const trustGrade = String(projectOutput.trust_contract?.grade || "unknown").toLowerCase();
  const authorityLevel = String(projectOutput.authoritative_projection?.authority_level || "").toLowerCase();

  const chirality     = toArray(composed.chirality);
  const timeTopo      = toArray(composed.time_topology);
  const spaceOp       = toArray(composed.space_operator);
  const axisVals      = toArray(composed.axis);
  const tongueProj    = toArray(composed.tongue_projection).map(t => t.toLowerCase());
  const cannabisMode  = toArray(composed.cannabis_mode);
  const clusterRole   = toArray(composed.cluster_role);

  const patch = {};
  const trace = {};
  let mapped = 0;

  // ── 1. chirality → camera yaw bias + rose saturation ───────────────────────
  if (chirality.length > 0) {
    const hand = classifyChirality(chirality);
    const cam3d = { ...(currentSettings.camera3d || {}), zoom: currentSettings.camera3d?.zoom ?? 1 };
    const roseBase = currentSettings.rose || {};

    if (hand === "left") {
      cam3d.yaw = currentSettings.camera3d?.yaw ?? -35; // preserve user yaw; bias handled by axis below
      patch.rose = { ...roseBase, enabled: true, strength: 0.55 };
    } else if (hand === "right") {
      // Mirror: flip yaw sign
      const baseYaw = currentSettings.camera3d?.yaw ?? -35;
      cam3d.yaw = -baseYaw;
      patch.rose = { ...roseBase, enabled: true, strength: 0.25 };
    } else {
      patch.rose = { ...roseBase, enabled: true, strength: 0.35 };
    }
    patch.camera3d = cam3d;
    trace.chirality = { input: chirality, handedness: hand, applied: { "camera3d.yaw": cam3d.yaw, "rose.strength": patch.rose.strength } };
    mapped++;
  }

  // ── 2. time_topology → visualStyle + edgeGlow ──────────────────────────────
  if (timeTopo.length > 0) {
    const topo = first(timeTopo);
    const styleMap = {
      linear:      { visualStyle: "default",           edgeGlow: false },
      loop:        { visualStyle: "pokemon_ds",         edgeGlow: false },
      exponential: { visualStyle: "pixel_voxel_hybrid", edgeGlow: false },
      logarithmic: { visualStyle: "pokemon_g45",        edgeGlow: false },
      fold:        { visualStyle: "pixel_voxel_hybrid", edgeGlow: true  },
      frozen:      { visualStyle: "classic_fallout",    edgeGlow: false },
    };
    const mapping = styleMap[topo] || { visualStyle: "default", edgeGlow: false };
    patch.visualStyle = mapping.visualStyle;
    patch.edgeGlow = mapping.edgeGlow;
    trace.time_topology = { input: timeTopo, dominant: topo, applied: { visualStyle: mapping.visualStyle, edgeGlow: mapping.edgeGlow } };
    mapped++;
  }

  // ── 3. space_operator → renderMode + projection ────────────────────────────
  if (spaceOp.length > 0) {
    const op = first(spaceOp);
    const modeMap = {
      assign:  { renderMode: "3d",   projection: "isometric" },
      save:    { renderMode: "2.5d", projection: "isometric" },
      parse:   { renderMode: "2d",   projection: "cardinal"  },
      loop:    { renderMode: "2.5d", projection: "isometric" },
      push:    { renderMode: "3d",   projection: "cardinal"  },
      delete:  { renderMode: "2d",   projection: "cardinal"  },
      run:     { renderMode: "3d",   projection: "isometric" },
      unbind:  { renderMode: "2.5d", projection: "cardinal"  },
    };
    const mapping = modeMap[op] || { renderMode: "2.5d", projection: "isometric" };
    patch.renderMode = mapping.renderMode;
    patch.projection = mapping.projection;
    trace.space_operator = { input: spaceOp, dominant: op, applied: mapping };
    mapped++;
  }

  // ── 4. axis → camera3d pitch + yaw (overrides chirality yaw if present) ────
  if (axisVals.length > 0) {
    const ax = first(axisVals);
    const angles = AXIS_CAMERA[ax];
    if (angles) {
      const existing = patch.camera3d || { ...(currentSettings.camera3d || {}) };
      // chirality may have set yaw — axis takes precedence for primary orientation
      patch.camera3d = { ...existing, yaw: angles.yaw, pitch: angles.pitch };
      trace.axis = { input: axisVals, dominant: ax, applied: { yaw: angles.yaw, pitch: angles.pitch } };
      mapped++;
    } else {
      trace.axis = { input: axisVals, dominant: ax, applied: null, note: "unrecognized axis value" };
    }
  }

  // ── 5. tongue_projection → background palette + glow color + rose ──────────
  if (tongueProj.length > 0) {
    // First recognized tongue wins; blend roseStrength if multiple
    let palette = null;
    let strengthSum = 0; let strengthCount = 0;
    const tonguesApplied = [];
    for (const t of tongueProj) {
      const key = t.replace(/[^a-z]/g, "");
      if (TONGUE_PALETTES[key]) {
        if (!palette) palette = TONGUE_PALETTES[key];
        strengthSum += TONGUE_PALETTES[key].roseStrength;
        strengthCount++;
        tonguesApplied.push(key);
      }
    }
    if (palette) {
      const blendedStrength = strengthCount > 1
        ? Math.round((strengthSum / strengthCount) * 100) / 100
        : palette.roseStrength;
      patch.background = palette.background;
      patch.edgeGlowColor = palette.edgeGlowColor;
      patch.rose = { ...(patch.rose || currentSettings.rose || {}), enabled: true, strength: blendedStrength };
      trace.tongue_projection = { input: tongueProj, applied: tonguesApplied, palette: { background: palette.background, edgeGlowColor: palette.edgeGlowColor, roseStrength: blendedStrength } };
      mapped++;
    } else {
      trace.tongue_projection = { input: tongueProj, applied: [], note: "no recognized tongue" };
    }
  }

  // ── 6. cannabis_mode → tile size + zScale (depth/introspection) ────────────
  if (cannabisMode.length > 0) {
    const mode = first(cannabisMode);
    const modeMap = {
      mind:  { tile: 16, zScale: 12 },  // tall, introspective, fine detail
      space: { tile: 20, zScale: 8  },  // wide, expansive, spatial breadth
      time:  { tile: 14, zScale: 6  },  // compressed, historical, layered depth
    };
    const mapping = modeMap[mode] || null;
    if (mapping) {
      patch.tile = mapping.tile;
      patch.zScale = mapping.zScale;
      trace.cannabis_mode = { input: cannabisMode, dominant: mode, applied: mapping };
      mapped++;
    } else {
      trace.cannabis_mode = { input: cannabisMode, dominant: mode, applied: null, note: "unrecognized mode" };
    }
  }

  // ── 7. cluster_role → LOD level ────────────────────────────────────────────
  if (clusterRole.length > 0) {
    const role = first(clusterRole);
    const lodMap = {
      leader:   1,  // full detail — authoritative node sees everything
      follower: 2,  // standard — participant view
      replica:  3,  // reduced — copy keeps broad strokes
      arbiter:  2,  // balanced — mediator sees enough
    };
    const level = lodMap[role];
    if (level !== undefined) {
      const currentLod = currentSettings.lod || {};
      patch.lod = { ...currentLod, level };
      trace.cluster_role = { input: clusterRole, dominant: role, applied: { "lod.level": level } };
      mapped++;
    } else {
      trace.cluster_role = { input: clusterRole, dominant: role, applied: null, note: "unrecognized role" };
    }
  }

  // ── 8. trust_grade → lighting ──────────────────────────────────────────────
  {
    const currentLighting = currentSettings.lighting || {};
    const lightingMap = {
      high:    { enabled: true,  ambient: 0.45, intensity: 0.95 },
      medium:  { enabled: true,  ambient: 0.35, intensity: 0.85 },
      low:     { enabled: false, ambient: 0.25, intensity: 0.70 },
      unknown: { enabled: false, ambient: 0.35, intensity: 0.85 },
    };
    const lm = lightingMap[trustGrade] || lightingMap.unknown;
    patch.lighting = { ...currentLighting, ...lm };
    trace.trust_grade = { input: trustGrade, applied: lm };
    mapped++;
  }

  // ── 9. authority_level → label mode ────────────────────────────────────────
  if (authorityLevel) {
    const labelMap = {
      lesson_exact_match: "role",
      rule_based:         "type",
    };
    const labelMode = labelMap[authorityLevel] || "none";
    patch.labelMode = labelMode;
    trace.authority_level = { input: authorityLevel, applied: { labelMode } };
    mapped++;
  }

  // ── Coverage report ─────────────────────────────────────────────────────────
  const FIELDS = ["chirality","time_topology","space_operator","axis","tongue_projection","cannabis_mode","cluster_role","trust_grade","authority_level"];
  const unmapped = FIELDS.filter((f) => !(f in trace) || trace[f]?.applied === null);

  return {
    patch,
    trace,
    coverage: {
      fields_mapped: mapped,
      fields_total: FIELDS.length,
      unmapped,
    },
  };
}

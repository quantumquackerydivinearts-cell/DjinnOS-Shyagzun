function parseJsonObject(text, fallback) {
  try {
    const parsed = JSON.parse(String(text || ""));
    if (parsed && typeof parsed === "object") {
      return parsed;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function sanitizeRendererSettings(settings) {
  const src = settings && typeof settings === "object" ? settings : {};
  return {
    renderMode: String(src.renderMode || "2.5d").toLowerCase() === "3d" ? "3d" : "2.5d",
    tile: Number.isFinite(Number(src.tile)) ? Number(src.tile) : 18,
    zScale: Number.isFinite(Number(src.zScale)) ? Number(src.zScale) : 8,
    renderScale: Number.isFinite(Number(src.renderScale)) ? Number(src.renderScale) : 1,
    visualStyle: typeof src.visualStyle === "string" ? src.visualStyle : "default",
    pixelate: Boolean(src.pixelate),
    background: typeof src.background === "string" ? src.background : "#0b1426",
    outline: Boolean(src.outline),
    outlineColor: typeof src.outlineColor === "string" ? src.outlineColor : "#0f203c",
    edgeGlow: Boolean(src.edgeGlow),
    edgeGlowColor: typeof src.edgeGlowColor === "string" ? src.edgeGlowColor : "#8fd3ff",
    edgeGlowStrength: Number.isFinite(Number(src.edgeGlowStrength)) ? Number(src.edgeGlowStrength) : 8,
    labelMode: typeof src.labelMode === "string" ? src.labelMode : "none",
    labelColor: typeof src.labelColor === "string" ? src.labelColor : "#d9e6ff",
    camera3d: src.camera3d && typeof src.camera3d === "object" ? cloneJson(src.camera3d) : { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
    lighting: src.lighting && typeof src.lighting === "object" ? cloneJson(src.lighting) : { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
    rose: src.rose && typeof src.rose === "object" ? cloneJson(src.rose) : { enabled: true, strength: 0.35 },
  };
}

export function extractVoxelsFromRendererJson(rendererJsonText) {
  const parsed = parseJsonObject(rendererJsonText, {});
  if (Array.isArray(parsed)) {
    return parsed;
  }
  if (Array.isArray(parsed.voxels)) {
    return parsed.voxels;
  }
  if (Array.isArray(parsed.scene?.voxels)) {
    return parsed.scene.voxels;
  }
  return [];
}

export function createRenderPack({
  name,
  notes,
  workspaceId,
  source = "studio_hub_sandbox",
  rendererJsonText,
  voxelSettings,
}) {
  const voxels = extractVoxelsFromRendererJson(rendererJsonText);
  const now = new Date().toISOString();
  const packId = `rpack_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
  return {
    schema: "atelier.renderer.pack.v1",
    pack_id: packId,
    name: String(name || packId),
    notes: String(notes || ""),
    source: String(source),
    workspace_id: String(workspaceId || "main"),
    created_at: now,
    render_settings: sanitizeRendererSettings(voxelSettings),
    scene_payload: {
      voxels: cloneJson(voxels),
    },
    stats: {
      voxel_count: Array.isArray(voxels) ? voxels.length : 0,
    },
  };
}

export function validateRenderPack(pack) {
  const errors = [];
  const warnings = [];
  if (!pack || typeof pack !== "object") {
    errors.push("pack must be an object");
    return { ok: false, errors, warnings };
  }
  if (pack.schema !== "atelier.renderer.pack.v1") {
    errors.push("schema must be atelier.renderer.pack.v1");
  }
  if (!pack.pack_id || typeof pack.pack_id !== "string") {
    errors.push("pack_id required");
  }
  if (!pack.name || typeof pack.name !== "string") {
    errors.push("name required");
  }
  const voxels = Array.isArray(pack.scene_payload?.voxels) ? pack.scene_payload.voxels : null;
  if (!voxels) {
    errors.push("scene_payload.voxels must be an array");
  } else if (voxels.length === 0) {
    warnings.push("scene_payload.voxels is empty");
  }
  return { ok: errors.length === 0, errors, warnings };
}

export function applyRenderPack(pack, fallbackSettings) {
  const settings = sanitizeRendererSettings(pack && pack.render_settings ? pack.render_settings : fallbackSettings || {});
  const voxels = Array.isArray(pack?.scene_payload?.voxels) ? pack.scene_payload.voxels : [];
  return {
    rendererJsonText: JSON.stringify({ voxels }, null, 2),
    voxelSettings: settings,
  };
}


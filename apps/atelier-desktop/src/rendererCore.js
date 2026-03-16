function normalizeRenderMode(raw) {
  const s = String(raw || "").toLowerCase();
  if (s === "3d") return "3d";
  if (s === "2d") return "2d";
  return "2.5d";
}

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

function toInt(value, fallback = 0) {
  const n = Number(value);
  if (Number.isFinite(n)) return Math.trunc(n);
  return fallback;
}

function chunkKeyForPoint(x, y, sizeX, sizeY) {
  const sx = Math.max(1, toInt(sizeX, 64));
  const sy = Math.max(1, toInt(sizeY, 64));
  const cx = Math.floor(toInt(x, 0) / sx);
  const cy = Math.floor(toInt(y, 0) / sy);
  return `cx${cx}_cy${cy}`;
}

export function sanitizeRendererSettings(settings) {
  const src = settings && typeof settings === "object" ? settings : {};
  return {
    renderMode: normalizeRenderMode(src.renderMode),
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
    classicFalloutShowLabels: Boolean(src.classicFalloutShowLabels),
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
  const schema = typeof pack.schema === "string" ? pack.schema : "";
  if (schema !== "atelier.renderer.pack.v1" && schema !== "atelier.renderer.pack.v2") {
    errors.push("schema must be atelier.renderer.pack.v1 or atelier.renderer.pack.v2");
  }
  if (!pack.pack_id || typeof pack.pack_id !== "string") {
    errors.push("pack_id required");
  }
  if (!pack.name || typeof pack.name !== "string") {
    errors.push("name required");
  }
  const voxels = schema === "atelier.renderer.pack.v2"
    ? (Array.isArray(pack.compiled_scene?.voxels) ? pack.compiled_scene.voxels : null)
    : (Array.isArray(pack.scene_payload?.voxels) ? pack.scene_payload.voxels : null);
  if (!voxels) {
    if (schema === "atelier.renderer.pack.v2") {
      errors.push("compiled_scene.voxels must be an array");
    } else {
      errors.push("scene_payload.voxels must be an array");
    }
  } else if (voxels.length === 0) {
    warnings.push("pack voxels are empty");
  }
  if (schema === "atelier.renderer.pack.v2") {
    if (!pack.compile || typeof pack.compile !== "object") {
      errors.push("compile block required for pack.v2");
    }
    if (!pack.hashes || typeof pack.hashes !== "object") {
      errors.push("hashes block required for pack.v2");
    }
  }
  return { ok: errors.length === 0, errors, warnings };
}

export function applyRenderPack(pack, fallbackSettings) {
  const settings = sanitizeRendererSettings(pack && pack.render_settings ? pack.render_settings : fallbackSettings || {});
  const schema = typeof pack?.schema === "string" ? pack.schema : "";
  let voxels = schema === "atelier.renderer.pack.v2"
    ? (Array.isArray(pack?.compiled_scene?.voxels) ? pack.compiled_scene.voxels : [])
    : (Array.isArray(pack?.scene_payload?.voxels) ? pack.scene_payload.voxels : []);

  const runtimeStream = resolveRuntimeStreamPayload(pack);
  if (runtimeStream && runtimeStream.ok) {
    const selected = selectStreamWindow(runtimeStream.manifest, runtimeStream.prefetch, runtimeStream.context);
    voxels = materializeVoxelsFromChunkIds(runtimeStream.chunkMap, selected.windowChunkIds, voxels);
  }
  return {
    rendererJsonText: JSON.stringify({ voxels }, null, 2),
    voxelSettings: settings,
  };
}

export function resolveRuntimeStreamPayload(pack) {
  if (!pack || typeof pack !== "object") return null;
  const stream = pack.runtime_stream && typeof pack.runtime_stream === "object" ? pack.runtime_stream : null;
  if (!stream) return null;
  const manifest = stream.manifest && typeof stream.manifest === "object" ? stream.manifest : null;
  if (!manifest || manifest.schema !== "atelier.renderer.stream_manifest.v1") return null;
  const prefetch = stream.prefetch && typeof stream.prefetch === "object" ? stream.prefetch : null;
  const chunks = stream.chunks && typeof stream.chunks === "object" ? stream.chunks : {};
  const chunkMap = {};
  Object.keys(chunks).forEach((chunkId) => {
    const payload = chunks[chunkId];
    if (!payload || typeof payload !== "object") return;
    if (!Array.isArray(payload.voxels)) return;
    chunkMap[chunkId] = payload.voxels;
  });
  const context = stream.context && typeof stream.context === "object" ? stream.context : {};
  return { ok: true, manifest, prefetch, chunkMap, context };
}

export function selectStreamWindow(manifest, prefetchManifest, context) {
  const grid = manifest && typeof manifest.grid === "object" ? manifest.grid : {};
  const chunkSizeX = toInt(grid.chunk_size_x, 64);
  const chunkSizeY = toInt(grid.chunk_size_y, 64);
  const x = toInt(context && context.player_x, 0);
  const y = toInt(context && context.player_y, 0);
  const currentChunkId = chunkKeyForPoint(x, y, chunkSizeX, chunkSizeY);

  const selected = new Set([currentChunkId]);
  if (prefetchManifest && prefetchManifest.schema === "atelier.renderer.stream_prefetch_manifest.v1" && Array.isArray(prefetchManifest.chunks)) {
    const row = prefetchManifest.chunks.find((entry) => entry && entry.chunk_id === currentChunkId);
    if (row && row.priority && typeof row.priority === "object") {
      const immediate = Array.isArray(row.priority.immediate) ? row.priority.immediate : [];
      const warm = Array.isArray(row.priority.warm) ? row.priority.warm : [];
      immediate.forEach((id) => typeof id === "string" && selected.add(id));
      warm.forEach((id) => typeof id === "string" && selected.add(id));
    }
  } else if (Array.isArray(manifest?.chunks)) {
    // Fallback when prefetch manifest is not provided: include manhattan ring-1 neighbors.
    const coordById = {};
    manifest.chunks.forEach((entry) => {
      if (!entry || typeof entry !== "object" || typeof entry.chunk_id !== "string") return;
      const cx = toInt(entry?.coord?.cx, null);
      const cy = toInt(entry?.coord?.cy, null);
      if (cx === null || cy === null) return;
      coordById[entry.chunk_id] = { cx, cy };
    });
    const center = coordById[currentChunkId];
    if (center) {
      Object.keys(coordById).forEach((id) => {
        if (id === currentChunkId) return;
        const c = coordById[id];
        const dist = Math.abs(c.cx - center.cx) + Math.abs(c.cy - center.cy);
        if (dist === 1) selected.add(id);
      });
    }
  }

  return {
    currentChunkId,
    windowChunkIds: Array.from(selected.values()).sort((a, b) => String(a).localeCompare(String(b))),
  };
}

export function materializeVoxelsFromChunkIds(chunkMap, chunkIds, fallbackVoxels) {
  const out = [];
  if (!chunkMap || typeof chunkMap !== "object" || !Array.isArray(chunkIds)) {
    return Array.isArray(fallbackVoxels) ? fallbackVoxels : [];
  }
  chunkIds.forEach((chunkId) => {
    const rows = chunkMap[chunkId];
    if (!Array.isArray(rows)) return;
    rows.forEach((row) => {
      if (row && typeof row === "object") out.push(row);
    });
  });
  return out.length > 0 ? out : (Array.isArray(fallbackVoxels) ? fallbackVoxels : []);
}

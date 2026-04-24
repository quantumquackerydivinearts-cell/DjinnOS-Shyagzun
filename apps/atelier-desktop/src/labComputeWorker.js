function parseKobraShygazunScriptWorker(sourceText) {
  const lines = String(sourceText || "").split(/\r?\n/);
  const entities = [];
  const words = [];
  let current = null;
  lines.forEach((rawLine) => {
    const indent = rawLine.length - rawLine.trimStart().length;
    const lineText = rawLine.trim();
    if (!lineText || lineText.startsWith("#")) {
      return;
    }
    if (indent > 0 && current) {
      const colonAt = lineText.indexOf(":");
      let key = "";
      let value = "";
      if (colonAt > 0) {
        key = lineText.slice(0, colonAt).trim();
        value = lineText.slice(colonAt + 1).trim();
      } else {
        const spaceAt = lineText.indexOf(" ");
        if (spaceAt > 0) {
          key = lineText.slice(0, spaceAt).trim();
          value = lineText.slice(spaceAt + 1).trim();
        } else {
          key = lineText;
        }
      }
      if (!current.meta) {
        current.meta = {};
      }
      current.meta[key] = value;
      if (key === "lex" || key === "akinenwun" || key === "shygazun") {
        current.akinenwun = value;
        const split = value.match(/[A-Z]+[a-z]*/g);
        words.push({ word: value, symbols: split && split.length > 0 ? split : [value] });
      }
      return;
    }
    if (/^entity\s+/i.test(lineText)) {
      const parts = lineText.split(/\s+/);
      const zCandidate = parts[4];
      const parsedZ = Number(zCandidate);
      const hasZ = zCandidate !== undefined && zCandidate !== "" && Number.isFinite(parsedZ);
      current = {
        id: parts[1] || "anon",
        x: Number(parts[2] || 0),
        y: Number(parts[3] || 0),
        z: hasZ ? parsedZ : 0,
        tag: hasZ ? (parts[5] || "none") : (parts[4] || "none"),
        meta: {},
      };
      entities.push(current);
      return;
    }
    current = null;
    if (/^(lex|akinenwun|word)\s+/i.test(lineText)) {
      const spaceAt = lineText.indexOf(" ");
      const word = spaceAt > 0 ? lineText.slice(spaceAt + 1).trim() : "";
      if (word) {
        const split = word.match(/[A-Z]+[a-z]*/g);
        words.push({ word, symbols: split && split.length > 0 ? split : [word] });
      }
    }
  });
  return { entities, words };
}

function normalizeCamera2dWorker(camera) {
  const c = camera && typeof camera === "object" ? camera : {};
  return {
    panX: Number.isFinite(Number(c.panX)) ? Number(c.panX) : 0,
    panY: Number.isFinite(Number(c.panY)) ? Number(c.panY) : 0,
    zoom: Number.isFinite(Number(c.zoom)) ? Number(c.zoom) : 1,
  };
}

function resolveInputLodLevelWorker(settings) {
  const s = settings && typeof settings === "object" ? settings : {};
  const lod = s.lod && typeof s.lod === "object" ? s.lod : {};
  const mode = String(lod.mode || "auto_zoom").toLowerCase();
  if (mode === "fixed") {
    return Math.max(0, Math.min(3, Number(lod.level || 2)));
  }
  const cam = normalizeCamera2dWorker(s.camera2d);
  const zoom = Number(cam.zoom || 1);
  if (zoom >= 2) return 3;
  if (zoom >= 1.25) return 2;
  if (zoom >= 0.8) return 1;
  return 0;
}

function lodRuleMatchesWorker(rule, lodLevel, zoom) {
  const r = rule && typeof rule === "object" ? rule : {};
  if (Number.isFinite(Number(r.level)) && Number(r.level) !== lodLevel) return false;
  if (Number.isFinite(Number(r.min_level)) && lodLevel < Number(r.min_level)) return false;
  if (Number.isFinite(Number(r.max_level)) && lodLevel > Number(r.max_level)) return false;
  if (Number.isFinite(Number(r.min_zoom)) && zoom < Number(r.min_zoom)) return false;
  if (Number.isFinite(Number(r.max_zoom)) && zoom > Number(r.max_zoom)) return false;
  return true;
}

function normalizeVoxelFastWorker(item, index) {
  const entry = item && typeof item === "object" ? item : {};
  const meta = entry.meta && typeof entry.meta === "object" ? entry.meta : {};
  return {
    ...entry,
    id: String(entry.id || entry.entity_id || entry.entityId || `voxel_${index}`),
    x: Number.isFinite(Number(entry.x)) ? Number(entry.x) : 0,
    y: Number.isFinite(Number(entry.y)) ? Number(entry.y) : 0,
    z: Number.isFinite(Number(entry.z)) ? Number(entry.z) : 0,
    type: String(entry.type || entry.kind || entry.tag || entry.id || `voxel_${index}`),
    kind: String(entry.kind || entry.type || entry.tag || ""),
    meta,
  };
}

function extractAndApplyLodWorker(payload, settings) {
  if (!payload || typeof payload !== "object") {
    return [];
  }
  const graphNodes = payload.graph && Array.isArray(payload.graph.nodes) ? payload.graph.nodes : null;
  const directNodes = Array.isArray(payload.nodes) ? payload.nodes : null;
  const candidates = graphNodes
    ? graphNodes
    : directNodes && directNodes.length > 0
    ? directNodes
    : Array.isArray(payload.voxels)
    ? payload.voxels
    : Array.isArray(payload.entities)
    ? payload.entities
    : Array.isArray(payload.points)
    ? payload.points
    : Array.isArray(payload.data)
    ? payload.data
    : [];
  const normalized = candidates.map((item, index) => normalizeVoxelFastWorker(item, index));
  const camera2d = normalizeCamera2dWorker(settings && settings.camera2d);
  const zoom = Number(camera2d.zoom || 1);
  const lodLevel = resolveInputLodLevelWorker(settings || {});
  const out = [];
  normalized.forEach((baseVoxel) => {
    if (!baseVoxel || typeof baseVoxel !== "object") {
      return;
    }
    const rule = baseVoxel.lod && typeof baseVoxel.lod === "object" ? baseVoxel.lod : {};
    if (!lodRuleMatchesWorker(rule, lodLevel, zoom)) {
      return;
    }
    const variants = Array.isArray(baseVoxel.lodVariants) ? baseVoxel.lodVariants : [];
    let resolved = baseVoxel;
    variants.forEach((variantRaw) => {
      if (!variantRaw || typeof variantRaw !== "object") {
        return;
      }
      const when = variantRaw.when && typeof variantRaw.when === "object" ? variantRaw.when : {};
      if (!lodRuleMatchesWorker(when, lodLevel, zoom)) {
        return;
      }
      const variant = { ...variantRaw };
      delete variant.when;
      resolved = {
        ...resolved,
        ...variant,
        meta: {
          ...(resolved.meta && typeof resolved.meta === "object" ? resolved.meta : {}),
          ...(variant.meta && typeof variant.meta === "object" ? variant.meta : {}),
        },
      };
    });
    if (resolved.hidden === true || resolved.hide === true || (resolved.meta && resolved.meta.hidden === true)) {
      return;
    }
    out.push(resolved);
  });
  return out;
}

self.onmessage = (event) => {
  const data = event && event.data && typeof event.data === "object" ? event.data : {};
  try {
    if (data.type === "run_tile_proc") {
      const payload = data.payload && typeof data.payload === "object" ? data.payload : {};
      const seed = Number(payload.seed || 0);
      const cols = Number(payload.cols || 0);
      const rows = Number(payload.rows || 0);
      const layer = typeof payload.layer === "string" ? payload.layer : "base";
      const code = typeof payload.code === "string" ? payload.code : "";
      const fn = new Function("seed", "cols", "rows", "layer", "\"use strict\";\n" + code);
      const result = fn(seed, cols, rows, layer);
      self.postMessage({ type: "tile_proc_result", ok: true, result });
      return;
    }
    if (data.type === "run_payload_parse") {
      const payload = data.payload && typeof data.payload === "object" ? data.payload : {};
      const mode = typeof payload.mode === "string" ? payload.mode : "json";
      const sourceText = typeof payload.sourceText === "string" ? payload.sourceText : "";
      let result = {};
      if (mode === "kobra") {
        result = parseKobraShygazunScriptWorker(sourceText);
      } else if (mode === "json") {
        const parsed = JSON.parse(sourceText || "{}");
        result = parsed && typeof parsed === "object" ? parsed : {};
      } else {
        result = {};
      }
      self.postMessage({ type: "payload_parse_result", ok: true, result });
      return;
    }
    if (data.type === "run_voxel_extract_lod") {
      const payload = data.payload && typeof data.payload === "object" ? data.payload : {};
      const result = extractAndApplyLodWorker(payload.payload, payload.settings);
      self.postMessage({ type: "voxel_extract_lod_result", ok: true, result });
    }
  } catch (error) {
    self.postMessage({
      type:
        data.type === "run_payload_parse"
          ? "payload_parse_result"
          : data.type === "run_voxel_extract_lod"
          ? "voxel_extract_lod_result"
          : "tile_proc_result",
      ok: false,
      error: error instanceof Error ? error.message : "worker_compute_error",
    });
  }
};

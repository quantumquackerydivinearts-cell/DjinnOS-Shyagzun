/**
 * renderLabState.js
 * Pure JS module — no React imports.
 * Exports default state shapes, localStorage key constants, and factory functions
 * for the Render Lab. State is owned by App.jsx (or RenderLabContext) via useState;
 * this module is the single source of truth for what that state looks like.
 *
 * Extracted from apps/atelier-desktop/src/App.jsx renderer state initializers.
 */

// ---------------------------------------------------------------------------
// localStorage keys
// ---------------------------------------------------------------------------

export const RENDERER_STORAGE_KEYS = {
  REALM:             "atelier.renderer.realm",
  VISUAL_SOURCE:     "atelier.renderer.visual_source",
  VOXEL_SETTINGS:    "atelier.renderer.voxel_settings",
  ATLASES:           "atelier.renderer.atlases",
  MATERIALS:         "atelier.renderer.materials",
  LAYERS:            "atelier.renderer.layers",
  PIPELINE:          "atelier.renderer.pipeline",
  VALIDATE_BEFORE:   "atelier.renderer.validate_before_emit",
  STRICT_BILINGUAL:  "atelier.renderer.strict_bilingual",
  AKINENWUN:         "atelier.renderer_akinenwun_snapshots",
  BIZ_INPUT_MODE:    "atelier.business_renderer.input_mode",
  BIZ_INPUT_TEXT:    "atelier.business_renderer.input_text",
  BIZ_USE_DERIVED:   "atelier.business_renderer.use_derived",
  BIZL_INPUT_MODE:   "atelier.business_logic_renderer.input_mode",
  BIZL_INPUT_TEXT:   "atelier.business_logic_renderer.input_text",
  BIZL_USE_DERIVED:  "atelier.business_logic_renderer.use_derived",
};

// ---------------------------------------------------------------------------
// Default state factories
// ---------------------------------------------------------------------------

export function defaultVoxelSettings() {
  return {
    renderMode:              "2.5d",
    projection:              "isometric",
    camera3d:                { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
    camera2d:                { panX: 0, panY: 0, zoom: 1 },
    tile:                    18,
    zScale:                  8,
    renderScale:             1,
    visualStyle:             "default",
    pixelate:                false,
    background:              "#0b1426",
    outline:                 false,
    outlineColor:            "#0f203c",
    edgeGlow:                false,
    edgeGlowColor:           "#8fd3ff",
    edgeGlowStrength:        8,
    classicFalloutShowLabels: false,
    labelMode:               "none",
    labelColor:              "#d9e6ff",
    lighting:                { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
    lod:                     { mode: "auto_zoom", level: 2 },
    rose:                    { enabled: true, strength: 0.35 },
  };
}

export function defaultRendererPipeline() {
  return {
    mode:              "json",
    pythonFileId:      null,
    kobraFileId:       null,
    jsFileId:          null,
    jsonFileId:        null,
    engineFileId:      null,
    worldRegionRealmId: "lapidus",
    realmId:           "lapidus",
    projectId:         null,   // linked render_lab project ID
  };
}

export function defaultLabCoherence() {
  return {
    last_check_at:      "",
    runtime_consume_ok: null,
    module_catalog_ok:  null,
    world_stream_ok:    null,
    main_plan_ok:       null,
    guided_bootstrap_ok: null,
    gate_a_ok:          null,
    gate_d_ok:          null,
    // Render Lab additions:
    readiness_green:    null,
    federation_green:   null,
    project_id:         null,
  };
}

export function defaultVoxelMaterials() {
  return [
    { id: "stone",      color: "#9aa4b2", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "wood",       color: "#b07d4f", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "grass",      color: "#4e7a3d", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "water",      color: "#2a5fa8", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "thatch",     color: "#c8a85a", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "lantern",    color: "#f5c842", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "player",     color: "#5b8fd4", textureTop: "", textureLeft: "", textureRight: "" },
    { id: "background", color: "#1a2a44", textureTop: "", textureLeft: "", textureRight: "" },
  ];
}

export function defaultVoxelAtlasDraft() {
  return { id: "", src: "", tileSize: 16, cols: 8, rows: 8, padding: 0 };
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

export function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage quota or private browsing — silent
  }
}

// ---------------------------------------------------------------------------
// Pipeline readiness helpers
// ---------------------------------------------------------------------------

/**
 * Returns true if all Render Lab coherence checks that have been run pass.
 * null means "not yet checked" (does not count as failure).
 */
export function isReadinessGreen(labCoherence) {
  const checks = [
    labCoherence.runtime_consume_ok,
    labCoherence.module_catalog_ok,
    labCoherence.world_stream_ok,
    labCoherence.gate_a_ok,
  ];
  return checks.every((c) => c === null || c === true) &&
    checks.some((c) => c === true);
}

export function isFederationGreen(labCoherence) {
  return labCoherence.federation_green === true;
}

/**
 * Merge a readiness API response into labCoherence state.
 * Call this after GET /v1/render_lab/projects/{id}/readiness.
 */
export function applyReadinessResponse(labCoherence, apiResponse) {
  const checks = Array.isArray(apiResponse.checks) ? apiResponse.checks : [];
  const find = (name) => checks.find((c) => c.name === name);
  return {
    ...labCoherence,
    last_check_at:      new Date().toISOString(),
    runtime_consume_ok: find("api_ready")?.ok ?? labCoherence.runtime_consume_ok,
    module_catalog_ok:  find("kernel_health")?.ok ?? labCoherence.module_catalog_ok,
    world_stream_ok:    find("toolchain_go_no_go")?.ok ?? labCoherence.world_stream_ok,
    readiness_green:    apiResponse.readiness_green ?? false,
    federation_green:   apiResponse.federation_green ?? false,
    project_id:         apiResponse.project_id ?? labCoherence.project_id,
  };
}

/**
 * renderLabArchDiagram.js
 * Pure JS module — no React imports, no canvas dependency for parsing.
 *
 * Extracted from apps/atelier-desktop/src/App.jsx:
 *   laneRank, normalizeArchitectureSpec, deriveBusinessArchitectureSpec,
 *   architectureNodeColor, drawBusinessArchitecture, parseArchitectureInput,
 *   plus new export/SVG helpers.
 *
 * The draw functions DO require a canvas element passed at call time.
 * All parse/normalize functions are pure.
 */

// ---------------------------------------------------------------------------
// Lane ordering
// ---------------------------------------------------------------------------

export function laneRank(lane) {
  const normalized = String(lane || "").toLowerCase().trim();
  if (normalized === "business") return 0;
  if (normalized === "systems")  return 1;
  if (normalized === "runtime")  return 2;
  if (normalized === "data")     return 3;
  if (normalized === "delivery") return 4;
  return 99;
}

// ---------------------------------------------------------------------------
// Node color by kind
// ---------------------------------------------------------------------------

export function architectureNodeColor(kind) {
  const k = String(kind || "").toLowerCase();
  if (k === "domain")             return "#2f4f9d";
  if (k === "service")            return "#266d56";
  if (k === "engine" || k === "rules") return "#6f4b1f";
  if (k === "data")               return "#5e2b69";
  if (k === "renderer")           return "#25416b";
  if (k === "tool")               return "#4a4f57";
  return "#3f4754";
}

// ---------------------------------------------------------------------------
// Spec normalisation
// ---------------------------------------------------------------------------

/**
 * Normalise a raw arch diagram spec (from JSON, Cobra, English, or Shygazun parse)
 * into a canonical { lanes, nodes, flows } model used by draw functions.
 */
export function normalizeArchitectureSpec(rawSpec) {
  const spec = rawSpec && typeof rawSpec === "object" ? rawSpec : {};
  const mergedNodes = []
    .concat(Array.isArray(spec.domains) ? spec.domains : [])
    .concat(Array.isArray(spec.systems) ? spec.systems : [])
    .concat(Array.isArray(spec.tools)   ? spec.tools   : []);

  const nodesMap = {};
  mergedNodes.forEach((rawNode, index) => {
    if (!rawNode || typeof rawNode !== "object") return;
    const id = String(rawNode.id || `node_${index}`);
    nodesMap[id] = {
      id,
      name:        String(rawNode.name || rawNode.title || id),
      lane:        String(rawNode.lane || "Systems"),
      kind:        String(rawNode.kind || "component"),
      domain:      rawNode.domain      ? String(rawNode.domain)      : "",
      description: rawNode.description ? String(rawNode.description) : "",
    };
  });

  const lanes = Object.values(nodesMap)
    .map((n) => n.lane)
    .filter((lane, i, arr) => arr.indexOf(lane) === i)
    .sort((a, b) => {
      const diff = laneRank(a) - laneRank(b);
      return diff !== 0 ? diff : a.localeCompare(b);
    });

  // Apply layout_hints lane_order if provided
  const hintOrder = Array.isArray(spec.layout_hints?.lane_order) ? spec.layout_hints.lane_order : [];
  if (hintOrder.length > 0) {
    lanes.sort((a, b) => {
      const ia = hintOrder.indexOf(a);
      const ib = hintOrder.indexOf(b);
      if (ia === -1 && ib === -1) return laneRank(a) - laneRank(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
  }

  const flows = (Array.isArray(spec.flows) ? spec.flows : [])
    .map((flow, index) => {
      if (!flow || typeof flow !== "object") return null;
      return {
        id:    String(flow.id    || `flow_${index}`),
        from:  String(flow.from  || ""),
        to:    String(flow.to    || ""),
        label: String(flow.label || ""),
        style: String(flow.style || "solid"),
      };
    })
    .filter((flow) => flow && nodesMap[flow.from] && nodesMap[flow.to]);

  const highlightIds = new Set(
    Array.isArray(spec.layout_hints?.highlight_ids) ? spec.layout_hints.highlight_ids : []
  );

  return { lanes, nodes: Object.values(nodesMap), flows, highlightIds };
}

// ---------------------------------------------------------------------------
// Derived spec from live Atelier state
// ---------------------------------------------------------------------------

/**
 * Derive an arch diagram spec from live renderer tables, pipeline config, and studio files.
 * Mirrors the deriveBusinessArchitectureSpec function from App.jsx.
 */
export function deriveBusinessArchitectureSpec(rendererTables, rendererPipeline, studioFiles) {
  const tableKeys = rendererTables && typeof rendererTables === "object"
    ? Object.keys(rendererTables) : [];
  const domains = [
    { id: "crm",      name: "Business Domain", lane: "Business",  kind: "domain" },
    { id: "runtime",  name: "Runtime Domain",  lane: "Runtime",   kind: "domain" },
    { id: "delivery", name: "Delivery Domain", lane: "Delivery",  kind: "domain" },
  ];
  const systems = [
    { id: "atelier_api",  name: "Atelier API",        lane: "Systems",  kind: "service",  domain: "crm" },
    { id: "kernel",       name: "Shygazun Kernel",    lane: "Runtime",  kind: "engine",   domain: "runtime" },
    { id: "renderer",     name: "Unified Renderer",   lane: "Delivery", kind: "renderer", domain: "delivery" },
    { id: "table_store",  name: "State Tables",       lane: "Data",     kind: "data",
      description: tableKeys.join(", ") },
  ];
  const tools = [
    { id: "cobra",     name: "Cobra Compiler",  lane: "Systems", kind: "tool" },
    { id: "studio_fs", name: `Studio Files (${Array.isArray(studioFiles) ? studioFiles.length : 0})`,
      lane: "Data", kind: "tool" },
    { id: "pipeline",  name: "Renderer Pipeline", lane: "Systems", kind: "tool",
      description: rendererPipeline?.mode ? String(rendererPipeline.mode) : "" },
  ];
  const flows = [
    { from: "atelier_api",  to: "table_store", label: "business writes",  style: "solid" },
    { from: "kernel",       to: "table_store", label: "runtime writes",   style: "solid" },
    { from: "cobra",        to: "kernel",      label: "script compile",   style: "dashed" },
    { from: "table_store",  to: "renderer",    label: "render state",     style: "solid" },
    { from: "studio_fs",    to: "cobra",       label: "script source",    style: "dotted" },
    { from: "pipeline",     to: "renderer",    label: "material pass",    style: "dashed" },
  ];
  return { domains, systems, tools, flows };
}

// ---------------------------------------------------------------------------
// Input parsing
// ---------------------------------------------------------------------------

/**
 * Parse architecture input text in the specified mode.
 * Returns a raw spec object suitable for normalizeArchitectureSpec.
 */
export function parseArchitectureInput(mode, text) {
  const normalized = String(mode || "json").toLowerCase();
  if (normalized === "json")      return _parseJson(text);
  if (normalized === "english")   return _parseEnglish(text);
  if (normalized === "cobra")     return _parseCobra(text);
  if (normalized === "shygazun")  return _parseShygazun(text);
  return _parseJson(text);
}

function _parseJson(text) {
  try {
    const parsed = JSON.parse(String(text || "{}"));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function _parseEnglish(text) {
  // Heuristic English parser: extract nouns as systems, verbs as flows.
  // Lines starting with "DOMAIN:", "SYSTEM:", "TOOL:", "FLOW:" are parsed structurally.
  const lines = String(text || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const domains = [], systems = [], tools = [], flows = [];
  for (const line of lines) {
    if (/^domain:/i.test(line)) {
      const name = line.replace(/^domain:\s*/i, "").trim();
      if (name) domains.push({ id: _slugify(name), name, lane: "Business", kind: "domain" });
    } else if (/^system:/i.test(line)) {
      const name = line.replace(/^system:\s*/i, "").trim();
      if (name) systems.push({ id: _slugify(name), name, lane: "Systems", kind: "service" });
    } else if (/^tool:/i.test(line)) {
      const name = line.replace(/^tool:\s*/i, "").trim();
      if (name) tools.push({ id: _slugify(name), name, lane: "Systems", kind: "tool" });
    } else if (/^flow:/i.test(line)) {
      const rest = line.replace(/^flow:\s*/i, "").trim();
      // "A -> B: label" or "A -> B"
      const match = rest.match(/^(.+?)\s*->\s*(.+?)(?:\s*:\s*(.+))?$/);
      if (match) {
        flows.push({
          from:  _slugify(match[1].trim()),
          to:    _slugify(match[2].trim()),
          label: match[3] ? match[3].trim() : "",
        });
      }
    }
  }
  return { domains, systems, tools, flows };
}

function _parseCobra(text) {
  // Minimal Cobra architecture parser: entity declarations become nodes,
  // edge declarations become flows.
  // entity <id> <x> <y> <kind>  →  system node in lane derived from kind
  // edge <from> <to> <label?>   →  flow
  const lines = String(text || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const systems = [], flows = [];
  for (const line of lines) {
    if (line.startsWith("//") || line.startsWith("#")) continue;
    const entityMatch = line.match(/^entity\s+(\S+)\s+\S+\s+\S+\s+(\S+)/);
    if (entityMatch) {
      const [, id, kind] = entityMatch;
      const lane = _kindToLane(kind);
      systems.push({ id, name: id, lane, kind });
      continue;
    }
    const edgeMatch = line.match(/^edge\s+(\S+)\s+(\S+)(?:\s+(.+))?/);
    if (edgeMatch) {
      const [, from, to, label] = edgeMatch;
      flows.push({ from, to, label: label ? label.trim() : "" });
    }
  }
  return { systems, flows };
}

// ---------------------------------------------------------------------------
// Shygazun byte table — symbol-to-tongue index (canonical, from byte_table.py)
// Tongue index: 0=Lotus 1=Rose 2=Sakura 3=Daisy 4=AppleBlossom 5=Aster 6=Grapevine 7=Cannabis
// ---------------------------------------------------------------------------
const _SHY_SYMBOL_TONGUE = (() => {
  const t = {};
  // Lotus 0–23
  for (const s of ["ty","zu","ly","mu","fy","pu","shy","ku","ti","ta","li","la","fi","fa","shi","sha","zo","mo","po","ko","ze","me","pe","ke"]) t[s] = 0;
  // Rose 24–47
  for (const s of ["ru","ot","el","ki","fu","ka","ae","gaoh","ao","ye","ui","shu","kiel","yeshu","lao","shushy","uinshu","kokiel","aonkiel","ha","ga","wu","na","ung"]) t[s] = 1;
  // Sakura 48–71
  for (const s of ["jy","ji","ja","jo","je","ju","dy","di","da","do","de","du","by","bi","ba","bo","be","bu","va","vo","ve","vu","vi","vy"]) t[s] = 2;
  // Daisy 72–97
  for (const s of ["lo","yei","ol","x","yx","go","foa","oy","w","th","kael","ro","gl","to","ma","ne","ym","nz","sho","hi","mh","zhi","vr","st","fn","n"]) t[s] = 3;
  // AppleBlossom 98–123
  for (const s of ["a","o","i","e","y","u","shak","puf","mel","zot","zhuk","kypa","alky","kazho","puky","pyfu","mipa","zitef","shem","lefu","milo","myza","zashu","fozt","mazi","zaot"]) t[s] = 4;
  // Aster 128–155
  for (const s of ["ry","oth","le","gi","fe","ky","alz","ra","tho","lu","ge","fo","kw","dr","si","su","os","se","sy","as","ep","gwev","ifa","ier","san","enno","yl","hoz"]) t[s] = 5;
  // Grapevine 156–183
  for (const s of ["sa","sao","syr","seth","samos","sava","sael","myk","myr","mio","mek","mavo","mekha","myrun","dyf","dyo","dyth","dyska","dyne","dyran","dyso","kyf","kyl","kyra","kyvos","kysha","kyom","kysael"]) t[s] = 6;
  // Cannabis 184–213
  for (const s of ["at","ar","av","azr","af","an","od","ox","om","soa","it","ir","iv","izr","if","in","ed","ex","em","sei","yt","yr","yv","yzr","yf","yn","ud","ux","um","suy"]) t[s] = 7;
  return t;
})();

// Tongue index → arch diagram lane / kind / display name
const _SHY_TONGUE_LANE = ["Data","Business","Systems","Systems","Runtime","Runtime","Delivery","Business"];
const _SHY_TONGUE_KIND = ["data","domain","component","engine","engine","engine","service","domain"];

/** Resolve tongue index (0–7) from a Shygazun compound or decimal address string. */
function _shyTongue(compound) {
  const raw = String(compound || "").trim();
  // Decimal address: byte range determines tongue
  if (/^\d+$/.test(raw)) {
    const d = parseInt(raw, 10);
    if (d <= 23)  return 0;  // Lotus
    if (d <= 47)  return 1;  // Rose
    if (d <= 71)  return 2;  // Sakura
    if (d <= 97)  return 3;  // Daisy
    if (d <= 123) return 4;  // AppleBlossom
    if (d <= 127) return -1; // Reserved multiversal gateway
    if (d <= 155) return 5;  // Aster
    if (d <= 183) return 6;  // Grapevine
    if (d <= 213) return 7;  // Cannabis
    return -1;
  }
  // Symbol compound: split on hyphen, take first part, case-insensitive lookup
  const firstPart = raw.split("-")[0].toLowerCase();
  const idx = _SHY_SYMBOL_TONGUE[firstPart];
  return idx !== undefined ? idx : -1;
}

function _parseShygazun(text) {
  // Shygazun arch input: each non-comment line is a node or node→flow declaration.
  //
  // Node line:   <compound> <name> [kind:<kind>] [lane:<lane>]
  // Flow line:   <compound> <name> -> <target_compound> [<flow_label>]
  //
  // <compound> is a Shygazun hyphenated symbol sequence (e.g. Ne-Sao, Mek-Sao)
  // or a decimal byte address (e.g. 87, 157).
  // The tongue of the first symbol/byte determines the default lane and kind;
  // explicit kind:/lane: annotations override the defaults.
  //
  // Examples:
  //   Ne-Sao kernel_api -> Mek-Sao database write_path
  //   157 persistent_store kind:data
  //   Kyf cluster_node lane:Delivery
  //   Mek-Sao event_bus -> Dyne broadcaster flood_signal

  const lines = String(text || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const systems = [], flows = [];
  const seen = new Set();

  const addNode = (id, name, tongueIdx, overrideKind, overrideLane) => {
    if (seen.has(id)) return;
    seen.add(id);
    const defaultLane = tongueIdx >= 0 ? _SHY_TONGUE_LANE[tongueIdx] : "Systems";
    const defaultKind = tongueIdx >= 0 ? _SHY_TONGUE_KIND[tongueIdx] : "component";
    systems.push({
      id,
      name: name || id,
      lane: overrideLane || defaultLane,
      kind: overrideKind || defaultKind,
    });
  };

  for (const line of lines) {
    if (line.startsWith("//") || line.startsWith("#")) continue;

    // Extract inline kind:/lane: annotations before further parsing
    let rest = line;
    let overrideKind = "";
    let overrideLane = "";
    rest = rest.replace(/\bkind:(\S+)/gi, (_, v) => { overrideKind = v.toLowerCase(); return ""; });
    rest = rest.replace(/\blane:(\S+)/gi, (_, v) => { overrideLane = v; return ""; });
    rest = rest.replace(/\s+/g, " ").trim();

    // Flow syntax: <fromCompound> <fromName?> -> <toCompound> [<flowLabel>]
    // The name portion before -> may be absent (compound only) or present.
    const arrowIdx = rest.indexOf(" -> ");
    if (arrowIdx !== -1) {
      const lhs = rest.slice(0, arrowIdx).trim();
      const rhs = rest.slice(arrowIdx + 4).trim();

      const lhsParts = lhs.split(/\s+/);
      const fromId   = lhsParts[0];
      const fromName = lhsParts.slice(1).join(" ") || fromId;
      const fromTongue = _shyTongue(fromId);
      addNode(fromId, fromName, fromTongue, overrideKind, overrideLane);

      const rhsParts   = rhs.split(/\s+/);
      const toId       = rhsParts[0];
      const flowLabel  = rhsParts.slice(1).join(" ");
      const toTongue   = _shyTongue(toId);
      // Target node gets its own tongue-derived defaults (no annotation override)
      addNode(toId, toId, toTongue, "", "");

      flows.push({ from: fromId, to: toId, label: flowLabel });
    } else {
      // Node-only line: <compound> [<name>]
      const parts = rest.split(/\s+/);
      const id    = parts[0];
      const name  = parts.slice(1).join(" ") || id;
      const tongueIdx = _shyTongue(id);
      addNode(id, name, tongueIdx, overrideKind, overrideLane);
    }
  }

  return { systems, flows };
}

function _slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function _kindToLane(kind) {
  const k = String(kind || "").toLowerCase();
  if (k === "domain")                    return "Business";
  if (k === "service" || k === "api")    return "Systems";
  if (k === "engine" || k === "kernel")  return "Runtime";
  if (k === "data" || k === "store")     return "Data";
  if (k === "renderer" || k === "ui")    return "Delivery";
  return "Systems";
}

// ---------------------------------------------------------------------------
// Canvas drawing
// ---------------------------------------------------------------------------

/**
 * Draw the architecture diagram onto a canvas element.
 * @param {HTMLCanvasElement} canvas
 * @param {{ lanes: string[], nodes: object[], flows: object[], highlightIds?: Set }} model
 */
export function drawArchDiagram(canvas, model) {
  if (!canvas || !model) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const width  = Math.max(960, Math.floor(canvas.clientWidth  || 960));
  const height = Math.max(420, Math.floor(canvas.clientHeight || 420));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width  = width;
    canvas.height = height;
  }

  ctx.clearRect(0, 0, width, height);
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#0b0e12");
  gradient.addColorStop(1, "#101722");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const lanes = Array.isArray(model.lanes) && model.lanes.length ? model.lanes : ["Systems"];
  const highlightIds = model.highlightIds instanceof Set ? model.highlightIds : new Set();
  const laneW = width / lanes.length;
  const lanePadding = 14;

  // Lane backgrounds + headers
  lanes.forEach((lane, laneIndex) => {
    const x = Math.floor(laneIndex * laneW);
    ctx.fillStyle = laneIndex % 2 === 0 ? "rgba(255,255,255,0.025)" : "rgba(255,255,255,0.04)";
    ctx.fillRect(x, 0, Math.ceil(laneW), height);
    ctx.fillStyle = "#d6dce6";
    ctx.font = "600 12px ui-sans-serif, system-ui, sans-serif";
    ctx.fillText(lane, x + lanePadding, 20);
  });

  // Node placement
  const nodesByLane = {};
  lanes.forEach((lane) => {
    nodesByLane[lane] = (model.nodes || []).filter((n) => n.lane === lane);
  });

  const nodeW = Math.min(240, Math.max(160, laneW - 20));
  const nodeH = 68;
  const coords = {};

  lanes.forEach((lane, laneIndex) => {
    const nodes = nodesByLane[lane] || [];
    nodes.forEach((node, rowIndex) => {
      const x = Math.floor(laneIndex * laneW + (laneW - nodeW) / 2);
      const y = 36 + rowIndex * (nodeH + 14);
      coords[node.id] = { x, y, w: nodeW, h: nodeH };
    });
  });

  // Flows (drawn before nodes so nodes render on top)
  ctx.lineWidth = 1.25;
  (model.flows || []).forEach((flow) => {
    const from = coords[flow.from];
    const to   = coords[flow.to];
    if (!from || !to) return;

    const x1 = from.x + from.w, y1 = from.y + from.h / 2;
    const x2 = to.x,            y2 = to.y   + to.h   / 2;
    const cx  = (x1 + x2) / 2;

    ctx.strokeStyle = "rgba(176,196,222,0.45)";
    if (flow.style === "dashed")      ctx.setLineDash([6, 3]);
    else if (flow.style === "dotted") ctx.setLineDash([2, 3]);
    else                              ctx.setLineDash([]);

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(cx, y1, cx, y2, x2, y2);
    ctx.stroke();
    ctx.setLineDash([]);

    if (flow.label) {
      ctx.fillStyle = "rgba(210,220,235,0.92)";
      ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
      ctx.fillText(flow.label, cx + 6, (y1 + y2) / 2 - 4);
    }
  });

  // Nodes
  (model.nodes || []).forEach((node) => {
    const box = coords[node.id];
    if (!box) return;

    const isHighlighted = highlightIds.has(node.id);
    ctx.fillStyle = architectureNodeColor(node.kind);
    ctx.strokeStyle = isHighlighted ? "#f5c842" : "rgba(255,255,255,0.16)";
    ctx.lineWidth = isHighlighted ? 2 : 1;

    ctx.beginPath();
    ctx.roundRect(box.x, box.y, box.w, box.h, 10);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#f4f7fb";
    ctx.font = "600 12px ui-sans-serif, system-ui, sans-serif";
    ctx.fillText(node.name.slice(0, 34), box.x + 10, box.y + 22);

    ctx.fillStyle = "rgba(242,247,252,0.86)";
    ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    const kindLabel = `${node.kind}${node.domain ? ` · ${node.domain}` : ""}`;
    ctx.fillText(kindLabel, box.x + 10, box.y + 40);

    if (node.description) {
      const clipped = node.description.length > 44
        ? `${node.description.slice(0, 44)}…` : node.description;
      ctx.fillStyle = "rgba(220,230,240,0.8)";
      ctx.fillText(clipped, box.x + 10, box.y + 56);
    }
  });
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

/**
 * Export a canvas to a PNG data URL (client-side only).
 * @param {HTMLCanvasElement} canvas
 * @returns {Promise<string>} data URL
 */
export function exportArchDiagramToPNG(canvas) {
  return new Promise((resolve, reject) => {
    if (!canvas) { reject(new Error("no_canvas")); return; }
    canvas.toBlob((blob) => {
      if (!blob) { reject(new Error("canvas_to_blob_failed")); return; }
      const reader = new FileReader();
      reader.onload = () => resolve(/** @type {string} */ (reader.result));
      reader.onerror = () => reject(new Error("file_reader_error"));
      reader.readAsDataURL(blob);
    }, "image/png");
  });
}

/**
 * Export the diagram spec to an SVG string (no canvas required).
 * Matches the _spec_to_svg logic in render_lab.py for consistency.
 * @param {{ lanes: string[], nodes: object[], flows: object[] }} model
 * @param {{ width?: number, height?: number }} options
 * @returns {string} SVG markup
 */
export function exportArchDiagramToSVG(model, options = {}) {
  const lanes = Array.isArray(model.lanes) && model.lanes.length ? model.lanes : ["Systems"];
  const W = options.width || 960;
  const H = options.height || Math.max(
    420,
    80 + 90 * Math.max(...lanes.map((l) =>
      (model.nodes || []).filter((n) => n.lane === l).length), 1)
  );
  const laneW = W / lanes.length;
  const nodeW = Math.min(220, laneW - 20), nodeH = 60;

  const nodesByLane = {};
  lanes.forEach((l) => {
    nodesByLane[l] = (model.nodes || []).filter((n) => n.lane === l);
  });

  const coords = {};
  lanes.forEach((lane, li) => {
    (nodesByLane[lane] || []).forEach((node, ri) => {
      const nx = li * laneW + (laneW - nodeW) / 2;
      const ny = 30 + ri * (nodeH + 12);
      coords[node.id] = { cx: nx + nodeW / 2, cy: ny + nodeH / 2, x: nx, y: ny };
    });
  });

  const parts = [];

  // Backgrounds
  lanes.forEach((lane, li) => {
    const x = li * laneW;
    parts.push(`<rect x="${x}" y="0" width="${laneW}" height="${H}" fill="${li % 2 === 0 ? "#14191f" : "#10151a"}"/>`);
    parts.push(`<text x="${x + 10}" y="18" fill="#9baec8" font-size="11" font-weight="600" font-family="ui-sans-serif,sans-serif">${_escXml(lane)}</text>`);
  });

  // Flows
  (model.flows || []).forEach((flow) => {
    const fc = coords[flow.from], tc = coords[flow.to];
    if (!fc || !tc) return;
    const x1 = fc.cx, y1 = fc.cy, x2 = tc.cx, y2 = tc.cy, mx = (x1 + x2) / 2;
    const dash = flow.style === "dashed" ? ' stroke-dasharray="6,3"'
               : flow.style === "dotted" ? ' stroke-dasharray="2,3"' : "";
    parts.push(`<path d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" stroke="#7a9ec8" stroke-width="1.25" fill="none"${dash}/>`);
    if (flow.label) parts.push(`<text x="${mx}" y="${(y1 + y2) / 2 - 4}" fill="#aabdd4" font-size="10" text-anchor="middle" font-family="ui-sans-serif,sans-serif">${_escXml(flow.label)}</text>`);
  });

  // Nodes
  (model.nodes || []).forEach((node) => {
    const c = coords[node.id];
    if (!c) return;
    const color = architectureNodeColor(node.kind);
    parts.push(`<rect x="${c.x}" y="${c.y}" width="${nodeW}" height="${nodeH}" rx="8" fill="${color}" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>`);
    parts.push(`<text x="${c.x + 10}" y="${c.y + 20}" fill="#f4f7fb" font-size="11" font-weight="600" font-family="ui-sans-serif,sans-serif">${_escXml(node.name.slice(0, 36))}</text>`);
    parts.push(`<text x="${c.x + 10}" y="${c.y + 36}" fill="#c8d4e0" font-size="10" font-family="ui-sans-serif,sans-serif">${_escXml(node.kind)}</text>`);
    if (node.description) {
      const d = node.description.length > 44 ? `${node.description.slice(0, 44)}…` : node.description;
      parts.push(`<text x="${c.x + 10}" y="${c.y + 52}" fill="rgba(220,230,240,0.8)" font-size="10" font-family="ui-sans-serif,sans-serif">${_escXml(d)}</text>`);
    }
  });

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="background:#0b0e12">\n${parts.join("\n")}\n</svg>`;
}

function _escXml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

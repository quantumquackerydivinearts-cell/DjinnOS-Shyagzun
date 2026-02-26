import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:9000";

const NAV_ITEMS = [
  "Foyer",
  "Workshop",
  "Temple and Gardens",
  "Guild Hall",
  "Messages",
  "Studio Hub",
  "Lesson Creation",
  "Module Creation",
  "Learning Hall",
  "CRM",
  "Booking System",
  "Leads",
  "Clients",
  "Quotes",
  "Orders",
  "Commission Hall",
  "Suppliers",
  "Inventory",
  "Graph Maker",
  "Renderer Lab",
  "Privacy"
];

function capabilitiesForRole(role) {
  if (role === "steward") {
    return [
      "kernel.place",
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "kernel.attest",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "booking.write",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "order.write",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  if (role === "senior_artisan") {
    return [
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "kernel.attest",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "booking.write",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "order.write",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  if (role === "artisan") {
    return [
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  return [
    "kernel.observe",
    "kernel.timeline",
    "kernel.frontiers",
    "crm.contacts.read",
    "booking.read",
    "lesson.read",
    "module.read",
    "lead.read",
    "client.read",
    "quote.read",
    "order.read",
    "supplier.read",
    "inventory.read"
  ];
}

function buildHeaders(role, capsCsv, adminGateToken) {
  const headers = {
    "Content-Type": "application/json",
    "X-Atelier-Actor": "desktop-user",
    "X-Atelier-Capabilities": capsCsv,
    "X-Artisan-Id": "artisan-desktop",
    "X-Artisan-Role": role,
    "X-Workshop-Id": "workshop-primary",
    "X-Workshop-Scopes": "scene:*,workspace:*"
  };
  if (adminGateToken) {
    headers["X-Admin-Gate-Token"] = adminGateToken;
  }
  return headers;
}

function parseSafeJson(text) {
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function GraphBars({ title, items }) {
  const max = items.reduce((m, it) => (it.value > m ? it.value : m), 0);
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="graph">
        {items.map((item) => {
          const pct = max === 0 ? 0 : Math.round((item.value / max) * 100);
          return (
            <div className="graph-row" key={item.label}>
              <span>{item.label}</span>
              <div className="graph-track">
                <div className="graph-fill" style={{ width: `${pct}%` }} />
              </div>
              <strong>{item.value}</strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function buildFrontierGraph(frontier) {
  if (!frontier || typeof frontier !== "object" || !Array.isArray(frontier.paths)) {
    return { nodes: [], edges: [], stats: { paths: 0, nodes: 0, edges: 0, symbols: 0 } };
  }
  const nodes = [];
  const edges = [];
  const symbols = new Set();
  frontier.paths.forEach((path, pathIndex) => {
    if (!path || typeof path !== "object") {
      return;
    }
    const pathSymbols = Array.isArray(path.symbols) ? path.symbols : [];
    const pathDecimals = Array.isArray(path.decimals) ? path.decimals : [];
    pathSymbols.forEach((symbol, symbolIndex) => {
      const nodeId = `p${pathIndex}-s${symbolIndex}`;
      const label = `${String(symbol)}${pathDecimals[symbolIndex] !== undefined ? ` (${String(pathDecimals[symbolIndex])})` : ""}`;
      nodes.push({ id: nodeId, label, pathIndex, symbolIndex });
      symbols.add(String(symbol));
      if (symbolIndex > 0) {
        edges.push({ from: `p${pathIndex}-s${symbolIndex - 1}`, to: nodeId, pathIndex });
      }
    });
  });
  return {
    nodes,
    edges,
    stats: {
      paths: frontier.paths.length,
      nodes: nodes.length,
      edges: edges.length,
      symbols: symbols.size
    }
  };
}

function stableStringify(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  const entries = Object.entries(value).sort(([a], [b]) => a.localeCompare(b));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(",")}}`;
}

function localFrontierHash(frontierObj) {
  const canon = stableStringify(frontierObj);
  let hash = 0;
  for (let i = 0; i < canon.length; i += 1) {
    hash = (hash * 31 + canon.charCodeAt(i)) >>> 0;
  }
  return `h_local_${hash.toString(16).padStart(8, "0")}`;
}

function localStringHash(text) {
  let hash = 0;
  const input = String(text);
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return `h_local_${hash.toString(16).padStart(8, "0")}`;
}

function parseObjectJson(text, fallback = {}) {
  try {
    const parsed = JSON.parse(text || "{}");
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

function compileCobraFromEntities(entities) {
  if (!Array.isArray(entities)) {
    return "";
  }
  return entities
    .map((entity) => {
      const id = String(entity.id || "anon");
      const x = Number(entity.x || 0);
      const y = Number(entity.y || 0);
      const kind = String(entity.kind || "token");
      const lex =
        typeof entity.akinenwun === "string" && entity.akinenwun.trim()
          ? entity.akinenwun.trim()
          : typeof entity.lex === "string" && entity.lex.trim()
            ? entity.lex.trim()
            : "";
      if (!lex) {
        return `entity ${id} ${x} ${y} ${kind}`;
      }
      return [`entity ${id} ${x} ${y} ${kind}`, `  lex ${lex}`].join("\n");
    })
    .join("\n");
}

function parseCobraShygazunScript(sourceText) {
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
    if (lineText.startsWith("entity ")) {
      const parts = lineText.split(/\s+/);
      current = {
        id: parts[1] || "anon",
        x: Number(parts[2] || 0),
        y: Number(parts[3] || 0),
        tag: parts[4] || "none",
        meta: {}
      };
      entities.push(current);
      return;
    }
    current = null;
    if (lineText.startsWith("lex ") || lineText.startsWith("akinenwun ") || lineText.startsWith("word ")) {
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

function analyzeCobraShygazunScript(sourceText) {
  const lines = String(sourceText || "").split(/\r?\n/);
  const warnings = [];
  let hasEntity = false;
  lines.forEach((rawLine, index) => {
    const lineNo = index + 1;
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      return;
    }
    if (rawLine.includes("\t")) {
      warnings.push(`L${lineNo}: tabs detected; use spaces for indentation`);
    }
    const indent = rawLine.length - rawLine.trimStart().length;
    if (trimmed.startsWith("entity ")) {
      const parts = trimmed.split(/\s+/);
      if (parts.length < 5) {
        warnings.push(`L${lineNo}: entity requires 'entity <id> <x> <y> <tag>'`);
      }
      hasEntity = true;
      return;
    }
    if (indent > 0 && !hasEntity) {
      warnings.push(`L${lineNo}: indented attribute without a parent statement`);
      return;
    }
    if (trimmed.startsWith("lex ") || trimmed.startsWith("akinenwun ") || trimmed.startsWith("shygazun ")) {
      const value = trimmed.replace(/^(lex|akinenwun|shygazun)\s+/, "").trim();
      if (!value) {
        warnings.push(`L${lineNo}: empty Shygazun lexical payload`);
      }
    }
  });
  return warnings;
}

function compilePythonDrawFromEntities(sceneName, entities) {
  const title = sceneName ? String(sceneName) : "Game Scene";
  const count = Array.isArray(entities) ? entities.length : 0;
  return [`#draw title=${title}`, `#draw entities=${count}`].join("\n");
}

function tileKey(x, y, layer = "base") {
  return `${layer}|${x},${y}`;
}

function parseTileKey(key) {
  const parts = String(key).split("|");
  const layer = parts.length > 1 ? parts[0] : "base";
  const coord = parts.length > 1 ? parts[1] : parts[0];
  const coordParts = String(coord).split(",");
  const x = Number.parseInt(coordParts[0] || "0", 10);
  const y = Number.parseInt(coordParts[1] || "0", 10);
  return { layer, x, y };
}

function tileDistance(a, b) {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function relationTokenForDistance(distance, nearThreshold) {
  return distance <= nearThreshold ? "Ti" : "Ze";
}

function tokenColor(token) {
  const map = {
    Ru: "#c62828",
    Ot: "#ef6c00",
    El: "#f9a825",
    Ki: "#2e7d32",
    Fu: "#1565c0",
    Ka: "#283593",
    AE: "#6a1b9a",
    Ha: "#ffffff",
    Ga: "#111111",
    Na: "#9e9e9e",
    Ung: "#4e342e",
    Wu: "#cfd8dc",
  };
  return map[token] || "#607d8b";
}

function tokenOpacity(token) {
  const map = {
    Ha: 1,
    Ga: 1,
    Na: 0.62,
    Ung: 0.86,
    Wu: 0.16,
  };
  return map[token] ?? 0.7;
}

function clampInt(value, min, max, fallback) {
  const parsed = Number.parseInt(String(value), 10);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, parsed));
}

function buildTileSvgMarkup(model, showGrid, showLinks, renderScale = 1) {
  const scaledWidth = Math.max(1, Math.round(model.width * renderScale));
  const scaledHeight = Math.max(1, Math.round(model.height * renderScale));
  const gridLines = [];
  if (showGrid) {
    for (let x = 0; x <= model.cols; x += 1) {
      gridLines.push(`<line x1="${x * model.cell}" y1="0" x2="${x * model.cell}" y2="${model.height}" stroke="#d8cbb8" stroke-width="1" />`);
    }
    for (let y = 0; y <= model.rows; y += 1) {
      gridLines.push(`<line x1="0" y1="${y * model.cell}" x2="${model.width}" y2="${y * model.cell}" stroke="#d8cbb8" stroke-width="1" />`);
    }
  }
  const layerRects = model.layers
    .map((layer) =>
      layer.tiles
        .map((t) => {
          const fill = tokenColor(String(t.color_token || "Ru"));
          const opacity = tokenOpacity(String(t.opacity_token || "Na"));
          const x = Number(t.x || 0) * model.cell;
          const y = Number(t.y || 0) * model.cell;
          return `<rect x="${x}" y="${y}" width="${model.cell}" height="${model.cell}" fill="${fill}" fill-opacity="${opacity}" rx="4" />`;
        })
        .join("")
    )
    .join("");
  const links = showLinks
    ? model.links
        .map((link) => {
          const near = String(link.relation_token || "") === "Ti";
          return `<line x1="${link.x1}" y1="${link.y1}" x2="${link.x2}" y2="${link.y2}" stroke="${near ? "#2f6d62" : "#1565c0"}" stroke-width="2" stroke-dasharray="${near ? "" : "5 3"}" />`;
        })
        .join("")
    : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${model.width} ${model.height}" width="${scaledWidth}" height="${scaledHeight}"><rect x="0" y="0" width="${model.width}" height="${model.height}" fill="#fffaf1" />${gridLines.join("")}${layerRects}${links}</svg>`;
}

const TILE_PROC_FORM_LIBRARY = {
  ring_bloom: [
    "const cx = Math.floor(cols / 2);",
    "const cy = Math.floor(rows / 2);",
    "const radius = Math.max(4, Math.floor(Math.min(cols, rows) * 0.22));",
    "const tokens = [\"Ru\",\"Ot\",\"El\",\"Ki\",\"Fu\",\"Ka\",\"AE\"];",
    "const tiles = [];",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const dx = x - cx;",
    "    const dy = y - cy;",
    "    const d = Math.sqrt(dx * dx + dy * dy);",
    "    if (Math.abs(d - radius) <= 1.25) {",
    "      const idx = (x + y + seed) % tokens.length;",
    "      tiles.push({ x, y, layer: \"base\", color_token: tokens[idx], opacity_token: \"Na\", presence_token: \"Ta\" });",
    "    }",
    "  }",
    "}",
    "return { tiles, links: [], entities: [{ id: `ring-${seed}`, kind: \"pattern\", x: cx, y: cy }] };",
  ].join("\n"),
  maze_carve: [
    "const tiles = [];",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const wall = x % 2 === 0 || y % 2 === 0;",
    "    tiles.push({",
    "      x, y, layer: wall ? \"ground\" : \"base\",",
    "      color_token: wall ? \"Ga\" : \"Ki\",",
    "      opacity_token: wall ? \"Ung\" : \"Na\",",
    "      presence_token: \"Ta\"",
    "    });",
    "  }",
    "}",
    "for (let n = 0; n < Math.floor((cols * rows) * 0.12); n += 1) {",
    "  const x = (seed * 13 + n * 17) % cols;",
    "  const y = (seed * 7 + n * 19) % rows;",
    "  tiles.push({ x, y, layer: \"base\", color_token: \"Ki\", opacity_token: \"Na\", presence_token: \"Ta\" });",
    "}",
    "return { tiles, links: [] };",
  ].join("\n"),
  island_chain: [
    "const tiles = [];",
    "const centers = [",
    "  { x: Math.floor(cols * 0.2), y: Math.floor(rows * 0.35), r: Math.floor(Math.min(cols, rows) * 0.12) },",
    "  { x: Math.floor(cols * 0.5), y: Math.floor(rows * 0.52), r: Math.floor(Math.min(cols, rows) * 0.15) },",
    "  { x: Math.floor(cols * 0.78), y: Math.floor(rows * 0.42), r: Math.floor(Math.min(cols, rows) * 0.1) },",
    "];",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    let land = false;",
    "    for (const c of centers) {",
    "      const dx = x - c.x;",
    "      const dy = y - c.y;",
    "      const d = Math.sqrt(dx * dx + dy * dy);",
    "      if (d <= c.r) { land = true; break; }",
    "    }",
    "    tiles.push({",
    "      x, y, layer: \"base\",",
    "      color_token: land ? \"Ki\" : \"Fu\",",
    "      opacity_token: land ? \"Na\" : \"Wu\",",
    "      presence_token: \"Ta\"",
    "    });",
    "  }",
    "}",
    "return { tiles, links: [] };",
  ].join("\n"),
  corridor_grid: [
    "const tiles = [];",
    "const links = [];",
    "const step = 4;",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const corridor = x % step === 0 || y % step === 0;",
    "    tiles.push({",
    "      x, y, layer: \"base\",",
    "      color_token: corridor ? \"El\" : \"Ga\",",
    "      opacity_token: corridor ? \"Na\" : \"Ung\",",
    "      presence_token: \"Ta\"",
    "    });",
    "    if (corridor && x + step < cols && y % step === 0) {",
    "      links.push({ ax: x, ay: y, bx: x + step, by: y });",
    "    }",
    "    if (corridor && y + step < rows && x % step === 0) {",
    "      links.push({ ax: x, ay: y, bx: x, by: y + step });",
    "    }",
    "  }",
    "}",
    "return { tiles, links };",
  ].join("\n"),
  noise_caves: [
    "function noise(x, y, s) {",
    "  const n = Math.sin((x * 12.9898 + y * 78.233 + s) * 43758.5453);",
    "  return n - Math.floor(n);",
    "}",
    "const tiles = [];",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const n = noise(x, y, seed);",
    "    const solid = n > 0.48;",
    "    tiles.push({",
    "      x, y, layer: \"base\",",
    "      color_token: solid ? \"Ga\" : \"Fu\",",
    "      opacity_token: solid ? \"Ung\" : \"Wu\",",
    "      presence_token: \"Ta\"",
    "    });",
    "  }",
    "}",
    "return { tiles, links: [] };",
  ].join("\n"),
};

const ASSET_GEN_PROFILE_V1 = {
  profile: "asset-gen-v1",
  cols: "64",
  rows: "36",
  cellPx: "20",
  exportScale: "2",
  nearThreshold: "3",
  colorToken: "Ru",
  opacityToken: "Na",
  layer: "base",
  template: "ring_bloom",
};

function monthLabel(year, month) {
  return new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function buildCalendarDays(year, month) {
  const first = new Date(year, month, 1);
  const startWeekday = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < startWeekday; i += 1) {
    cells.push({ key: `pad-${i}`, day: null, iso: null });
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const iso = new Date(year, month, day).toISOString().slice(0, 10);
    cells.push({ key: iso, day, iso });
  }
  return cells;
}

function compareIso(a, b) {
  if (a < b) {
    return -1;
  }
  if (a > b) {
    return 1;
  }
  return 0;
}

function makeStudioFileId() {
  return `studio_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
}

function rangesOverlap(startA, endA, startB, endB) {
  return startA < endB && startB < endA;
}

function renderInlineMarkdown(text) {
  const parts = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let idx = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > last) {
      parts.push(<span key={`plain-${idx}`}>{text.slice(last, match.index)}</span>);
      idx += 1;
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(<strong key={`strong-${idx}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(<em key={`em-${idx}`}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(<code key={`code-${idx}`}>{token.slice(1, -1)}</code>);
    }
    idx += 1;
    last = pattern.lastIndex;
    match = pattern.exec(text);
  }
  if (last < text.length) {
    parts.push(<span key={`tail-${idx}`}>{text.slice(last)}</span>);
  }
  return parts;
}

function renderMarkdownBlocks(text) {
  const lines = text.split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      i += 1;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      blocks.push(<h3 key={`h3-${i}`}>{renderInlineMarkdown(trimmed.slice(4))}</h3>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      blocks.push(<h2 key={`h2-${i}`}>{renderInlineMarkdown(trimmed.slice(3))}</h2>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("# ")) {
      blocks.push(<h1 key={`h1-${i}`}>{renderInlineMarkdown(trimmed.slice(2))}</h1>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("> ")) {
      blocks.push(<blockquote key={`quote-${i}`}>{renderInlineMarkdown(trimmed.slice(2))}</blockquote>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("- ")) {
      const items = [];
      let j = i;
      while (j < lines.length && lines[j].trim().startsWith("- ")) {
        items.push(lines[j].trim().slice(2));
        j += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`}>
          {items.map((item, k) => (
            <li key={`uli-${i}-${k}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      i = j;
      continue;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      const items = [];
      let j = i;
      while (j < lines.length && /^\d+\.\s+/.test(lines[j].trim())) {
        items.push(lines[j].trim().replace(/^\d+\.\s+/, ""));
        j += 1;
      }
      blocks.push(
        <ol key={`ol-${i}`}>
          {items.map((item, k) => (
            <li key={`oli-${i}-${k}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>
      );
      i = j;
      continue;
    }
    const para = [];
    let j = i;
    while (j < lines.length && lines[j].trim() && !/^(#|>|- |\d+\.\s+)/.test(lines[j].trim())) {
      para.push(lines[j].trim());
      j += 1;
    }
    blocks.push(<p key={`p-${i}`}>{renderInlineMarkdown(para.join(" "))}</p>);
    i = j;
  }
  if (blocks.length === 0) {
    return <p>Lesson preview appears here as you type.</p>;
  }
  return blocks;
}

const LESSON_MARKDOWN_CHEATSHEET = [
  "# Title",
  "## Section",
  "### Subsection",
  "- Bullet item",
  "1. Numbered step",
  "> Callout block",
  "**bold** *italic* `code`"
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function buildRendererFrameHtml(kind, source, engineState) {
  const escapedSource = JSON.stringify(String(source));
  const escapedState = JSON.stringify(engineState);
  return `<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <style>
      body { margin: 0; font: 13px monospace; background: #0f1729; color: #cde0ff; }
      #root { padding: 10px; white-space: pre-wrap; }
      .entity { margin: 6px 0; padding: 6px; border: 1px solid #284063; border-radius: 6px; background: #111b2f; }
      .ok { color: #8be9a8; }
      .err { color: #ff8f8f; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script>
      const root = document.getElementById("root");
      const source = ${escapedSource};
      const engine = ${escapedState};
      function line(text, cls) {
        const div = document.createElement("div");
        if (cls) div.className = cls;
        div.textContent = text;
        root.appendChild(div);
      }
      function renderEntities(entities) {
        entities.forEach((entity, idx) => {
          const div = document.createElement("div");
          div.className = "entity";
          div.textContent = \`#\${idx + 1} \${JSON.stringify(entity)}\`;
          root.appendChild(div);
        });
      }
      function splitAkinenwun(word) {
        const raw = String(word || "").trim();
        if (!raw) return [];
        const parts = raw.match(/[A-Z]+[a-z]*/g);
        if (!parts || parts.length === 0) return [raw];
        return parts;
      }
      function parseCobraShygazun(sourceText) {
        const lines = String(sourceText || "").split(/\\r?\\n/);
        const entities = [];
        const words = [];
        let current = null;
        lines.forEach((rawLine) => {
          const indent = rawLine.length - rawLine.trimStart().length;
          const lineText = rawLine.trim();
          if (!lineText || lineText.startsWith("#")) return;
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
            if (!current.meta) current.meta = {};
            current.meta[key] = value;
            if (key === "lex" || key === "akinenwun" || key === "shygazun") {
              current.akinenwun = value;
              words.push({ word: value, symbols: splitAkinenwun(value) });
            }
            return;
          }
          if (lineText.startsWith("entity ")) {
            const parts = lineText.split(/\\s+/);
            current = {
              id: parts[1] || "anon",
              x: Number(parts[2] || 0),
              y: Number(parts[3] || 0),
              tag: parts[4] || "none",
              meta: {}
            };
            entities.push(current);
            return;
          }
          current = null;
          if (lineText.startsWith("lex ") || lineText.startsWith("akinenwun ") || lineText.startsWith("word ")) {
            const spaceAt = lineText.indexOf(" ");
            const word = spaceAt > 0 ? lineText.slice(spaceAt + 1).trim() : "";
            if (word) words.push({ word, symbols: splitAkinenwun(word) });
          }
        });
        return { entities, words };
      }
      try {
        line("engine.tick=" + String(engine.tick || 0), "ok");
        if ("${kind}" === "javascript") {
          const fn = new Function("engine", "root", source + "\\n; return (typeof render === 'function' ? render(engine, root) : null);");
          const result = fn(engine, root);
          if (result !== null && result !== undefined) line("return: " + JSON.stringify(result), "ok");
        } else if ("${kind}" === "json") {
          const parsed = JSON.parse(source || "{}");
          line("json parsed ok", "ok");
          renderEntities(Array.isArray(parsed.entities) ? parsed.entities : []);
          line(JSON.stringify(parsed, null, 2));
        } else if ("${kind}" === "cobra") {
          const parsed = parseCobraShygazun(source);
          line("cobra entities=" + parsed.entities.length, "ok");
          line("shygazun words=" + parsed.words.length, "ok");
          parsed.words.forEach((entry, idx) => {
            line("akinenwun[" + String(idx + 1) + "] " + entry.word + " => " + entry.symbols.join("|"), "ok");
          });
          renderEntities(parsed.entities);
        } else if ("${kind}" === "python") {
          const lines = source.split(/\\r?\\n/).map((v) => v.trim());
          const drawLines = lines.filter((ln) => ln.startsWith("#draw "));
          line("python directives=" + drawLines.length, "ok");
          drawLines.forEach((ln) => line(ln.slice(6)));
        }
      } catch (err) {
        line(String(err && err.message ? err.message : err), "err");
      }
    </script>
  </body>
</html>`;
}

export function App() {
  const [section, setSection] = useState(() => localStorage.getItem("atelier.section") || "Foyer");
  const [role, setRole] = useState(() => localStorage.getItem("atelier.role") || "senior_artisan");
  const [workspaceId, setWorkspaceId] = useState(() => localStorage.getItem("atelier.workspace") || "main");
  const [output, setOutput] = useState("{}");
  const [notice, setNotice] = useState("Ready");
  const [busyAction, setBusyAction] = useState(null);
  const [activityLog, setActivityLog] = useState([]);

  const [gateCode, setGateCode] = useState("");
  const [adminGateToken, setAdminGateToken] = useState(null);
  const [adminVerified, setAdminVerified] = useState(false);
  const [gateMessage, setGateMessage] = useState("Placement tooling is locked.");
  const [raw, setRaw] = useState("");
  const [timelineLast, setTimelineLast] = useState("25");
  const [spriteId, setSpriteId] = useState("sprite_001");
  const [spriteKind, setSpriteKind] = useState("token");
  const [spriteLayer, setSpriteLayer] = useState("foreground");
  const [spriteX, setSpriteX] = useState("0");
  const [spriteY, setSpriteY] = useState("0");
  const [spriteAutoPrefix, setSpriteAutoPrefix] = useState("sprite_auto");
  const [spriteAutoCount, setSpriteAutoCount] = useState("6");
  const [spriteAutoColumns, setSpriteAutoColumns] = useState("3");
  const [spriteAutoStartX, setSpriteAutoStartX] = useState("0");
  const [spriteAutoStartY, setSpriteAutoStartY] = useState("0");
  const [spriteAutoStepX, setSpriteAutoStepX] = useState("1");
  const [spriteAutoStepY, setSpriteAutoStepY] = useState("1");
  const [akinenwunWord, setAkinenwunWord] = useState("TyKoWuVu");
  const [akinenwunMode, setAkinenwunMode] = useState("prose");
  const [akinenwunIngest, setAkinenwunIngest] = useState(true);
  const [akinenwunFrontier, setAkinenwunFrontier] = useState(null);
  const [rendererAkinenwunMode, setRendererAkinenwunMode] = useState("prose");
  const [rendererAkinenwunWord, setRendererAkinenwunWord] = useState("TyKoWuVu");
  const [rendererAkinenwunFrontier, setRendererAkinenwunFrontier] = useState(null);
  const [graphMakerSource, setGraphMakerSource] = useState("workshop");
  const [graphMakerManualFrontierText, setGraphMakerManualFrontierText] = useState("{\"paths\":[]}");
  const [rendererAkinenwunSnapshots, setRendererAkinenwunSnapshots] = useState(() => {
    const rawSaved = localStorage.getItem("atelier.renderer_akinenwun_snapshots");
    if (!rawSaved) {
      return [];
    }
    try {
      const parsed = JSON.parse(rawSaved);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contacts, setContacts] = useState([]);
  const [contactFilter, setContactFilter] = useState("");

  const [bookingStart, setBookingStart] = useState("");
  const [bookingEnd, setBookingEnd] = useState("");
  const [bookings, setBookings] = useState([]);
  const [bookingFilter, setBookingFilter] = useState("");
  const [profileName, setProfileName] = useState(() => localStorage.getItem("atelier.profile_name") || "Artisan");
  const [profileEmail, setProfileEmail] = useState(() => localStorage.getItem("atelier.profile_email") || "");
  const [profileTimezone, setProfileTimezone] = useState(
    () => localStorage.getItem("atelier.profile_tz") || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [artisanAccessInput, setArtisanAccessInput] = useState("");
  const [artisanAccessVerified, setArtisanAccessVerified] = useState(false);
  const [artisanIssuedCode, setArtisanIssuedCode] = useState("");
  const today = new Date();
  const [calendarYear, setCalendarYear] = useState(today.getFullYear());
  const [calendarMonth, setCalendarMonth] = useState(today.getMonth());
  const [calendarDragStart, setCalendarDragStart] = useState(null);
  const [calendarDragEnd, setCalendarDragEnd] = useState(null);
  const [calendarDragging, setCalendarDragging] = useState(false);
  const [quickStartHour, setQuickStartHour] = useState("10:00");
  const [quickEndHour, setQuickEndHour] = useState("11:00");
  const [calendarModalOpen, setCalendarModalOpen] = useState(false);
  const [calendarModalDay, setCalendarModalDay] = useState(null);
  const [calendarModalStart, setCalendarModalStart] = useState("10:00");
  const [calendarModalEnd, setCalendarModalEnd] = useState("11:00");
  const [calendarModalStatus, setCalendarModalStatus] = useState("scheduled");
  const [calendarModalNotes, setCalendarModalNotes] = useState("");

  const [lessonTitle, setLessonTitle] = useState("");
  const [lessonBody, setLessonBody] = useState("");
  const [lessons, setLessons] = useState([]);
  const [lessonFilter, setLessonFilter] = useState("");
  const LESSON_SOFT_LIMIT = 12000;

  const [moduleTitle, setModuleTitle] = useState("");
  const [moduleDescription, setModuleDescription] = useState("");
  const [modules, setModules] = useState([]);
  const [moduleFilter, setModuleFilter] = useState("");

  const [leadName, setLeadName] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [leadDetails, setLeadDetails] = useState("");
  const [leads, setLeads] = useState([]);
  const [leadFilter, setLeadFilter] = useState("");

  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clients, setClients] = useState([]);
  const [clientFilter, setClientFilter] = useState("");

  const [quoteTitle, setQuoteTitle] = useState("");
  const [quoteAmount, setQuoteAmount] = useState("");
  const [quoteCurrency, setQuoteCurrency] = useState("USD");
  const [quotePublic, setQuotePublic] = useState(false);
  const [quotes, setQuotes] = useState([]);
  const [quoteFilter, setQuoteFilter] = useState("");

  const [orderTitle, setOrderTitle] = useState("");
  const [orderAmount, setOrderAmount] = useState("");
  const [orderCurrency, setOrderCurrency] = useState("USD");
  const [orders, setOrders] = useState([]);
  const [orderFilter, setOrderFilter] = useState("");

  const [supplierName, setSupplierName] = useState("");
  const [supplierContact, setSupplierContact] = useState("");
  const [supplierEmail, setSupplierEmail] = useState("");
  const [suppliers, setSuppliers] = useState([]);
  const [supplierFilter, setSupplierFilter] = useState("");

  const [inventorySku, setInventorySku] = useState("");
  const [inventoryName, setInventoryName] = useState("");
  const [inventoryQty, setInventoryQty] = useState("0");
  const [inventoryReorder, setInventoryReorder] = useState("0");
  const [inventoryCost, setInventoryCost] = useState("0");
  const [inventorySupplierId, setInventorySupplierId] = useState("");
  const [inventoryItems, setInventoryItems] = useState([]);
  const [inventoryFilter, setInventoryFilter] = useState("");

  const [rendererPython, setRendererPython] = useState("#draw title=Workshop Renderer");
  const [rendererCobra, setRendererCobra] = useState("entity cube 12 8 amber");
  const [rendererJs, setRendererJs] = useState("function render(engine, root) { root.append('js tick=' + engine.tick); return { ok: true, tick: engine.tick }; }");
  const [rendererJson, setRendererJson] = useState("{\"entities\":[{\"id\":\"light-1\",\"x\":3,\"y\":5,\"kind\":\"lamp\"}]}");
  const [rendererEngineStateText, setRendererEngineStateText] = useState("{\"tick\":0,\"camera\":{\"x\":0,\"y\":0}}");
  const [rendererGameSpecText, setRendererGameSpecText] = useState(
    "{\"scene\":{\"name\":\"prototype\"},\"systems\":{\"gravity\":0.0,\"camera\":{\"x\":0,\"y\":0}},\"entities\":[{\"id\":\"hero\",\"kind\":\"player\",\"x\":0,\"y\":0,\"hp\":100},{\"id\":\"orb-1\",\"kind\":\"pickup\",\"x\":4,\"y\":2,\"value\":10}]}"
  );
  const [rendererGameStatus, setRendererGameStatus] = useState("idle");
  const [rendererSimPlaying, setRendererSimPlaying] = useState(false);
  const [rendererSimMs, setRendererSimMs] = useState("300");
  const [rendererNewEntityId, setRendererNewEntityId] = useState("enemy-1");
  const [rendererNewEntityKind, setRendererNewEntityKind] = useState("enemy");
  const [rendererNewEntityX, setRendererNewEntityX] = useState("3");
  const [rendererNewEntityY, setRendererNewEntityY] = useState("1");
  const [tileCols, setTileCols] = useState("48");
  const [tileRows, setTileRows] = useState("27");
  const [tileCellPx, setTileCellPx] = useState("24");
  const [tileSvgExportScale, setTileSvgExportScale] = useState("2");
  const [tileActiveLayer, setTileActiveLayer] = useState("base");
  const [tilePresenceToken, setTilePresenceToken] = useState("Ta");
  const [tileColorToken, setTileColorToken] = useState("Ru");
  const [tileOpacityToken, setTileOpacityToken] = useState("Na");
  const [tileNearThreshold, setTileNearThreshold] = useState("2");
  const [tilePlacements, setTilePlacements] = useState({});
  const [tileConnections, setTileConnections] = useState([]);
  const [tileConnectMode, setTileConnectMode] = useState(false);
  const [tileConnectFrom, setTileConnectFrom] = useState(null);
  const [tileSvgShowGrid, setTileSvgShowGrid] = useState(true);
  const [tileSvgShowLinks, setTileSvgShowLinks] = useState(true);
  const [tileProcSeed, setTileProcSeed] = useState("42");
  const [tileProcTemplate, setTileProcTemplate] = useState("ring_bloom");
  const [tileProcCode, setTileProcCode] = useState(
    [
      "// Return { tiles, links, entities? }",
      "// tiles: [{ x, y, layer?, color_token, opacity_token, presence_token? }]",
      "const cx = Math.floor(cols / 2);",
      "const cy = Math.floor(rows / 2);",
      "const radius = Math.max(4, Math.floor(Math.min(cols, rows) * 0.22));",
      "const tokens = [\"Ru\",\"Ot\",\"El\",\"Ki\",\"Fu\",\"Ka\",\"AE\"];",
      "const tiles = [];",
      "for (let y = 0; y < rows; y += 1) {",
      "  for (let x = 0; x < cols; x += 1) {",
      "    const dx = x - cx;",
      "    const dy = y - cy;",
      "    const d = Math.sqrt(dx * dx + dy * dy);",
      "    if (Math.abs(d - radius) <= 1.25) {",
      "      const idx = (x + y + seed) % tokens.length;",
      "      tiles.push({ x, y, layer: \"base\", color_token: tokens[idx], opacity_token: \"Na\", presence_token: \"Ta\" });",
      "    }",
      "  }",
      "}",
      "return { tiles, links: [], entities: [{ id: `ring-${seed}`, kind: \"pattern\", x: cx, y: cy }] };",
    ].join("\n")
  );
  const [tileProcStatus, setTileProcStatus] = useState("idle");
  const [tilePresetName, setTilePresetName] = useState("asset_batch_01");
  const [tileSavedPresets, setTileSavedPresets] = useState(() => {
    const rawSaved = localStorage.getItem("atelier.tile_presets");
    if (!rawSaved) {
      return [];
    }
    try {
      const parsed = JSON.parse(rawSaved);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  const [publicName, setPublicName] = useState("");
  const [publicEmail, setPublicEmail] = useState("");
  const [publicDetails, setPublicDetails] = useState("");
  const [publicQuotes, setPublicQuotes] = useState([]);
  const [privacyManifest, setPrivacyManifest] = useState(null);

  const [messageDraft, setMessageDraft] = useState("");
  const [messageLog, setMessageLog] = useState([]);
  const [studioFolders, setStudioFolders] = useState(() => {
    const raw = localStorage.getItem("atelier.studio_folders");
    if (!raw) {
      return ["notes", "scripts", "templates"];
    }
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.every((item) => typeof item === "string")) {
        return parsed;
      }
      return ["notes", "scripts", "templates"];
    } catch {
      return ["notes", "scripts", "templates"];
    }
  });
  const [studioFiles, setStudioFiles] = useState(() => {
    const raw = localStorage.getItem("atelier.studio_files");
    if (!raw) {
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    }
    try {
      const parsed = JSON.parse(raw);
      if (
        Array.isArray(parsed) &&
        parsed.every(
          (item) =>
            item &&
            typeof item.id === "string" &&
            typeof item.name === "string" &&
            typeof item.folder === "string" &&
            typeof item.content === "string"
        )
      ) {
        return parsed;
      }
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    } catch {
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    }
  });
  const [studioSelectedFileId, setStudioSelectedFileId] = useState(() => localStorage.getItem("atelier.studio_selected") || "file_notes");
  const [studioNewFolder, setStudioNewFolder] = useState("");
  const [studioNewFileName, setStudioNewFileName] = useState("");
  const [studioTargetFolder, setStudioTargetFolder] = useState("notes");
  const [studioRenameFileName, setStudioRenameFileName] = useState("");
  const [studioRenameFolderFrom, setStudioRenameFolderFrom] = useState("notes");
  const [studioRenameFolderTo, setStudioRenameFolderTo] = useState("");
  const [studioMoveTargetFolder, setStudioMoveTargetFolder] = useState("notes");
  const [studioDraggedFileId, setStudioDraggedFileId] = useState(null);
  const [studioFsRoot, setStudioFsRoot] = useState(() => localStorage.getItem("atelier.studio_fs_root") || "");
  const [studioFsScripts, setStudioFsScripts] = useState([]);
  const [studioFsSelectedScript, setStudioFsSelectedScript] = useState("");

  const caps = useMemo(() => capabilitiesForRole(role).join(","), [role]);
  const datasetSummary = useMemo(
    () => [
      { label: "Contacts", value: contacts.length },
      { label: "Bookings", value: bookings.length },
      { label: "Lessons", value: lessons.length },
      { label: "Modules", value: modules.length },
      { label: "Leads", value: leads.length },
      { label: "Clients", value: clients.length },
      { label: "Quotes", value: quotes.length },
      { label: "Orders", value: orders.length },
      { label: "Suppliers", value: suppliers.length },
      { label: "Inventory", value: inventoryItems.length }
    ],
    [contacts, bookings, lessons, modules, leads, clients, quotes, orders, suppliers, inventoryItems]
  );
  const studioSelectedFile = useMemo(
    () => studioFiles.find((file) => file.id === studioSelectedFileId) || null,
    [studioFiles, studioSelectedFileId]
  );

  useEffect(() => localStorage.setItem("atelier.section", section), [section]);
  useEffect(() => localStorage.setItem("atelier.role", role), [role]);
  useEffect(() => localStorage.setItem("atelier.workspace", workspaceId), [workspaceId]);
  useEffect(() => localStorage.setItem("atelier.profile_name", profileName), [profileName]);
  useEffect(() => localStorage.setItem("atelier.profile_email", profileEmail), [profileEmail]);
  useEffect(() => localStorage.setItem("atelier.profile_tz", profileTimezone), [profileTimezone]);
  useEffect(() => localStorage.setItem("atelier.studio_folders", JSON.stringify(studioFolders)), [studioFolders]);
  useEffect(() => localStorage.setItem("atelier.studio_files", JSON.stringify(studioFiles)), [studioFiles]);
  useEffect(() => localStorage.setItem("atelier.studio_selected", studioSelectedFileId), [studioSelectedFileId]);
  useEffect(() => localStorage.setItem("atelier.studio_fs_root", studioFsRoot), [studioFsRoot]);
  useEffect(
    () => localStorage.setItem("atelier.renderer_akinenwun_snapshots", JSON.stringify(rendererAkinenwunSnapshots)),
    [rendererAkinenwunSnapshots]
  );
  useEffect(() => localStorage.setItem("atelier.tile_presets", JSON.stringify(tileSavedPresets)), [tileSavedPresets]);
  useEffect(() => {
    if (!rendererSimPlaying) {
      return undefined;
    }
    const intervalMs = Math.max(60, Number.parseInt(rendererSimMs || "300", 10) || 300);
    const timer = window.setInterval(() => {
      stepRendererEngine();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [rendererSimPlaying, rendererSimMs]);
  useEffect(() => {
    function stopDrag() {
      setCalendarDragging(false);
    }
    window.addEventListener("mouseup", stopDrag);
    return () => window.removeEventListener("mouseup", stopDrag);
  }, []);
  useEffect(() => {
    if (studioFiles.length === 0) {
      return;
    }
    if (!studioFiles.some((file) => file.id === studioSelectedFileId)) {
      setStudioSelectedFileId(studioFiles[0].id);
    }
  }, [studioFiles, studioSelectedFileId]);
  useEffect(() => {
    if (studioFolders.length === 0) {
      return;
    }
    if (!studioFolders.includes(studioTargetFolder)) {
      setStudioTargetFolder(studioFolders[0]);
    }
    if (!studioFolders.includes(studioRenameFolderFrom)) {
      setStudioRenameFolderFrom(studioFolders[0]);
    }
    if (!studioFolders.includes(studioMoveTargetFolder)) {
      setStudioMoveTargetFolder(studioFolders[0]);
    }
  }, [studioFolders, studioTargetFolder, studioRenameFolderFrom, studioMoveTargetFolder]);
  useEffect(() => {
    setArtisanAccessVerified(false);
    setArtisanAccessInput("");
    setArtisanIssuedCode("");
  }, [profileName, profileEmail, role, workspaceId]);
  useEffect(() => {
    void fetchArtisanAccessStatus();
  }, [profileName, profileEmail, role, workspaceId]);
  useEffect(() => {
    if (!studioSelectedFile) {
      setStudioRenameFileName("");
      return;
    }
    setStudioRenameFileName(studioSelectedFile.name);
  }, [studioSelectedFile]);

  function pushActivity(action, ok, detail) {
    setActivityLog((prev) =>
      [{ at: new Date().toISOString(), section, workspace_id: workspaceId, action, ok, detail }, ...prev].slice(0, 60)
    );
  }

  async function runAction(actionName, fn) {
    setBusyAction(actionName);
    try {
      const data = await fn();
      setNotice(`${actionName}: success`);
      pushActivity(actionName, true, "ok");
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setNotice(`${actionName}: failed`);
      pushActivity(actionName, false, msg);
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function apiCall(path, method, body, tokenOverride) {
    const token = tokenOverride === undefined ? adminGateToken : tokenOverride;
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: buildHeaders(role, caps, token),
      body: body === null ? undefined : JSON.stringify(body)
    });
    const data = parseSafeJson(await response.text());
    setOutput(JSON.stringify(data, null, 2));
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async function publicApiCall(path, method, body) {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === null ? undefined : JSON.stringify(body)
    });
    const data = parseSafeJson(await response.text());
    setOutput(JSON.stringify(data, null, 2));
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async function refreshGateStatus(tokenOverride) {
    await runAction("admin_gate_status", async () => {
      const data = await apiCall("/v1/atelier/admin/gate/status", "GET", null, tokenOverride);
      const verified = Boolean(data.verified_admin);
      setAdminVerified(verified);
      setGateMessage(verified ? "Placement tooling unlocked." : "Placement tooling is locked.");
      return data;
    });
  }

  useEffect(() => {
    setAdminGateToken(null);
    setAdminVerified(false);
    setGateCode("");
    setGateMessage("Placement tooling is locked.");
    void refreshGateStatus(null);
  }, [role, caps]);

  const makeList = (path, setter, action) => async () =>
    runAction(action, async () => {
      const data = await apiCall(path, "GET", null);
      setter(data);
      return data;
    });

  const listContacts = makeList(`/v1/crm/contacts?workspace_id=${encodeURIComponent(workspaceId)}`, setContacts, "contacts_list");
  const listBookings = makeList(`/v1/booking?workspace_id=${encodeURIComponent(workspaceId)}`, setBookings, "bookings_list");
  const listLessons = makeList(`/v1/lessons?workspace_id=${encodeURIComponent(workspaceId)}`, setLessons, "lessons_list");
  const listModules = makeList(`/v1/modules?workspace_id=${encodeURIComponent(workspaceId)}`, setModules, "modules_list");
  const listLeads = makeList(`/v1/leads?workspace_id=${encodeURIComponent(workspaceId)}`, setLeads, "leads_list");
  const listClients = makeList(`/v1/clients?workspace_id=${encodeURIComponent(workspaceId)}`, setClients, "clients_list");
  const listQuotes = makeList(`/v1/quotes?workspace_id=${encodeURIComponent(workspaceId)}`, setQuotes, "quotes_list");
  const listOrders = makeList(`/v1/orders?workspace_id=${encodeURIComponent(workspaceId)}`, setOrders, "orders_list");
  const listSuppliers = makeList(`/v1/suppliers?workspace_id=${encodeURIComponent(workspaceId)}`, setSuppliers, "suppliers_list");
  const listInventory = makeList(`/v1/inventory?workspace_id=${encodeURIComponent(workspaceId)}`, setInventoryItems, "inventory_list");
  const loadPublicQuotes = async () =>
    runAction("public_quotes_list", async () => {
      const data = await publicApiCall(`/public/commission-hall/quotes?workspace_id=${encodeURIComponent(workspaceId)}`, "GET", null);
      setPublicQuotes(data);
      return data;
    });
  const loadPrivacyManifest = async () =>
    runAction("privacy_manifest_load", async () => {
      const data = await publicApiCall("/public/privacy/manifest", "GET", null);
      setPrivacyManifest(data);
      return data;
    });

  async function loadOrganizationOverview() {
    await runAction("organization_overview", async () => {
      await Promise.all([
        listContacts(),
        listBookings(),
        listLessons(),
        listModules(),
        listLeads(),
        listClients(),
        listQuotes(),
        listOrders(),
        listSuppliers(),
        listInventory()
      ]);
      return {};
    });
  }

  async function verifyAdminGate() {
    await runAction("admin_gate_verify", async () => {
      const data = await apiCall("/v1/atelier/admin/gate/verify", "POST", { gate_code: gateCode }, null);
      const token = typeof data.admin_gate_token === "string" ? data.admin_gate_token : null;
      setAdminGateToken(token);
      setAdminVerified(Boolean(data.verified_admin) && token !== null);
      setGateMessage("Placement tooling unlocked.");
      return data;
    });
  }

  async function observe() {
    await runAction("observe", () => apiCall("/v1/ambroflow/semantic-value", "GET", null));
  }
  async function timeline() {
    await runAction("timeline", () => apiCall(`/v1/atelier/timeline?last=${encodeURIComponent(timelineLast)}`, "GET", null));
  }
  async function frontiers() {
    await runAction("frontiers", () => apiCall("/v1/atelier/frontiers", "GET", null));
  }
  async function place() {
    await runAction("place", () =>
      apiCall("/v1/ambroflow/place", "POST", {
        raw,
        scene_id: section.toLowerCase(),
        context: { workspace_id: workspaceId },
      })
    );
  }

  async function emitCobraPlacements() {
    await runAction("cobra_emit_placements", async () => {
      const parsed = parseCobraShygazunScript(rendererCobra);
      if (!parsed.entities.length) {
        throw new Error("cobra_emit: no entities found");
      }
      for (const entity of parsed.entities) {
        const entityRaw = `entity ${entity.id} ${Number(entity.x || 0)} ${Number(entity.y || 0)} ${String(entity.tag || "none")}`;
        await apiCall("/v1/ambroflow/place", "POST", {
          raw: entityRaw,
          scene_id: "renderer-lab",
          context: {
            workspace_id: workspaceId,
            cobra_entity: entity,
            akinenwun: typeof entity.akinenwun === "string" ? entity.akinenwun : null
          }
        });
      }
      return { placed: parsed.entities.length };
    });
  }

  function toInt(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
  }

  async function emitSpriteManual() {
    const x = toInt(spriteX, 0);
    const y = toInt(spriteY, 0);
    const line = `sprite.place id=${spriteId} kind=${spriteKind} x=${x} y=${y} layer=${spriteLayer}`;
    await runAction("sprite_manual_place", () =>
      apiCall("/v1/ambroflow/place", "POST", {
        raw: line,
        scene_id: section.toLowerCase(),
        tags: { feature: "sprite-generator", mode: "manual" },
        metadata: {
          sprite: {
            id: spriteId,
            kind: spriteKind,
            x,
            y,
            layer: spriteLayer,
          },
        },
        context: { workspace_id: workspaceId },
      })
    );
  }

  async function emitSpriteAuto() {
    const count = Math.max(1, toInt(spriteAutoCount, 1));
    const columns = Math.max(1, toInt(spriteAutoColumns, 1));
    const startX = toInt(spriteAutoStartX, 0);
    const startY = toInt(spriteAutoStartY, 0);
    const stepX = toInt(spriteAutoStepX, 1);
    const stepY = toInt(spriteAutoStepY, 1);
    await runAction("sprite_auto_place", async () => {
      for (let i = 0; i < count; i += 1) {
        const col = i % columns;
        const row = Math.floor(i / columns);
        const id = `${spriteAutoPrefix}_${String(i + 1).padStart(3, "0")}`;
        const x = startX + col * stepX;
        const y = startY + row * stepY;
        const line = `sprite.place id=${id} kind=${spriteKind} x=${x} y=${y} layer=${spriteLayer}`;
        await apiCall("/v1/ambroflow/place", "POST", {
          raw: line,
          scene_id: section.toLowerCase(),
          tags: { feature: "sprite-generator", mode: "automatic" },
          metadata: {
            sprite: {
              id,
              kind: spriteKind,
              x,
              y,
              layer: spriteLayer,
            },
            auto: {
              index: i,
              count,
              columns,
            },
          },
          context: { workspace_id: workspaceId },
        });
      }
      return { emitted: count };
    });
  }

  async function lookupAkinenwun(word, mode, ingest, setter, actionName) {
    await runAction(actionName, async () => {
      const data = await apiCall("/v1/ambroflow/akinenwun/lookup", "POST", {
        akinenwun: word,
        mode,
        ingest
      });
      setter(data);
      return data;
    });
  }

  function pinRendererFrontierSnapshot() {
    if (!rendererAkinenwunFrontier || typeof rendererAkinenwunFrontier !== "object") {
      setNotice("renderer_akinenwun_pin: no frontier loaded");
      return;
    }
    const snapshot = {
      hash: String(rendererAkinenwunFrontier.frontier_hash || ""),
      akinenwun: rendererAkinenwunWord,
      mode: rendererAkinenwunMode,
      at: new Date().toISOString(),
      frontier: rendererAkinenwunFrontier.frontier || {}
    };
    if (!snapshot.hash) {
      setNotice("renderer_akinenwun_pin: missing frontier hash");
      return;
    }
    setRendererAkinenwunSnapshots((prev) => {
      const deduped = prev.filter((item) => item.hash !== snapshot.hash);
      return [snapshot, ...deduped].slice(0, 40);
    });
  }

  function restoreRendererSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") {
      return;
    }
    setRendererAkinenwunWord(String(snapshot.akinenwun || ""));
    setRendererAkinenwunMode(String(snapshot.mode || "prose"));
    setRendererAkinenwunFrontier({
      akinenwun: String(snapshot.akinenwun || ""),
      mode: String(snapshot.mode || "prose"),
      frontier_hash: String(snapshot.hash || ""),
      frontier: snapshot.frontier || {}
    });
  }

  function promoteGraphMakerToRendererSnapshot() {
    const frontierObj = graphMakerFrontierResult.frontier;
    if (!frontierObj || typeof frontierObj !== "object") {
      setNotice("graph_maker_promote: no frontier to promote");
      return;
    }
    const sourcePayload =
      graphMakerSource === "workshop"
        ? akinenwunFrontier
        : graphMakerSource === "renderer"
        ? rendererAkinenwunFrontier
        : null;
    const hash =
      sourcePayload && typeof sourcePayload.frontier_hash === "string" && sourcePayload.frontier_hash
        ? sourcePayload.frontier_hash
        : localFrontierHash(frontierObj);
    const mode =
      sourcePayload && typeof sourcePayload.mode === "string"
        ? sourcePayload.mode
        : graphMakerSource === "manual"
        ? "manual"
        : "prose";
    const akinenwun =
      sourcePayload && typeof sourcePayload.akinenwun === "string"
        ? sourcePayload.akinenwun
        : graphMakerSource === "manual"
        ? "manual_frontier"
        : "frontier";

    const snapshot = {
      hash,
      akinenwun,
      mode,
      at: new Date().toISOString(),
      frontier: frontierObj
    };
    setRendererAkinenwunSnapshots((prev) => {
      const deduped = prev.filter((item) => item.hash !== snapshot.hash);
      return [snapshot, ...deduped].slice(0, 40);
    });
    restoreRendererSnapshot(snapshot);
    setSection("Renderer Lab");
  }

  function downloadTileSvg() {
    const scale = clampInt(tileSvgExportScale, 1, 8, 2);
    const svg = buildTileSvgMarkup(tileSvgModel, tileSvgShowGrid, tileSvgShowLinks, scale);
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tilemap-${workspaceId}-${tileSvgModel.width * scale}x${tileSvgModel.height * scale}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function applyResolutionPreset(preset) {
    if (preset === "SD") {
      setTileCols("32");
      setTileRows("18");
      setTileCellPx("20");
      setTileSvgExportScale("2");
      return;
    }
    if (preset === "HD") {
      setTileCols("64");
      setTileRows("36");
      setTileCellPx("20");
      setTileSvgExportScale("2");
      return;
    }
    if (preset === "2K") {
      setTileCols("128");
      setTileRows("72");
      setTileCellPx("16");
      setTileSvgExportScale("2");
    }
  }

  function applyAssetGenProfileV1() {
    setTileCols(ASSET_GEN_PROFILE_V1.cols);
    setTileRows(ASSET_GEN_PROFILE_V1.rows);
    setTileCellPx(ASSET_GEN_PROFILE_V1.cellPx);
    setTileSvgExportScale(ASSET_GEN_PROFILE_V1.exportScale);
    setTileNearThreshold(ASSET_GEN_PROFILE_V1.nearThreshold);
    setTileColorToken(ASSET_GEN_PROFILE_V1.colorToken);
    setTileOpacityToken(ASSET_GEN_PROFILE_V1.opacityToken);
    setTileActiveLayer(ASSET_GEN_PROFILE_V1.layer);
    setTileProcTemplate(ASSET_GEN_PROFILE_V1.template);
    setTileProcCode(TILE_PROC_FORM_LIBRARY[ASSET_GEN_PROFILE_V1.template]);
    setTileProcStatus("profile_loaded:asset-gen-v1");
  }

  function applyProceduralTiles() {
    const seed = clampInt(tileProcSeed, 0, 999999, 42);
    const cols = clampInt(tileCols, 1, 256, 48);
    const rows = clampInt(tileRows, 1, 256, 27);
    try {
      const fn = new Function(
        "seed",
        "cols",
        "rows",
        "layer",
        "\"use strict\";\n" + tileProcCode
      );
      const out = fn(seed, cols, rows, tileActiveLayer);
      if (!out || typeof out !== "object" || Array.isArray(out)) {
        throw new Error("generator must return object");
      }
      const tiles = Array.isArray(out.tiles) ? out.tiles : [];
      const links = Array.isArray(out.links) ? out.links : [];
      const entities = Array.isArray(out.entities) ? out.entities : [];

      const nextPlacements = {};
      for (const item of tiles) {
        if (!item || typeof item !== "object") {
          continue;
        }
        const x = clampInt(item.x, 0, cols - 1, 0);
        const y = clampInt(item.y, 0, rows - 1, 0);
        const layer = typeof item.layer === "string" && item.layer ? item.layer : tileActiveLayer;
        const presence = item.presence_token === "Zo" ? "Zo" : "Ta";
        if (presence === "Zo") {
          continue;
        }
        const color = typeof item.color_token === "string" ? item.color_token : tileColorToken;
        const opacity = typeof item.opacity_token === "string" ? item.opacity_token : tileOpacityToken;
        const key = tileKey(x, y, layer);
        nextPlacements[key] = {
          id: `tile_${layer}_${x}_${y}`,
          x,
          y,
          layer,
          presence_token: "Ta",
          color_token: color,
          opacity_token: opacity,
        };
      }
      setTilePlacements(nextPlacements);

      const nextLinks = links
        .map((link, index) => {
          if (!link || typeof link !== "object") {
            return null;
          }
          const ax = clampInt(link.ax, 0, cols - 1, 0);
          const ay = clampInt(link.ay, 0, rows - 1, 0);
          const bx = clampInt(link.bx, 0, cols - 1, 0);
          const by = clampInt(link.by, 0, rows - 1, 0);
          const al = typeof link.alayer === "string" && link.alayer ? link.alayer : tileActiveLayer;
          const bl = typeof link.blayer === "string" && link.blayer ? link.blayer : tileActiveLayer;
          const from = tileKey(ax, ay, al);
          const to = tileKey(bx, by, bl);
          const dist = tileDistance({ x: ax, y: ay }, { x: bx, y: by });
          const nearThreshold = Math.max(1, Number.parseInt(tileNearThreshold || "2", 10) || 2);
          const rel = relationTokenForDistance(dist, nearThreshold);
          return {
            id: `link_proc_${index}_${from.replace("|", "_").replace(",", "_")}_${to.replace("|", "_").replace(",", "_")}`,
            from,
            to,
            distance: dist,
            relation_token: rel,
          };
        })
        .filter(Boolean);
      setTileConnections(nextLinks);

      if (entities.length > 0) {
        const spec = parseObjectJson(rendererGameSpecText, {});
        const existing = Array.isArray(spec.entities) ? spec.entities : [];
        const merged = { ...spec, entities: [...existing, ...entities] };
        setRendererGameSpecText(JSON.stringify(merged, null, 2));
      }
      setTileProcStatus(`generated:${Object.keys(nextPlacements).length}_tiles`);
      setRendererGameStatus(`procedural:${Object.keys(nextPlacements).length}_tiles`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setTileProcStatus(`error:${msg}`);
      setNotice(`procedural_generate: ${msg}`);
    }
  }

  function loadProceduralTemplate(name) {
    const template = TILE_PROC_FORM_LIBRARY[name];
    if (!template) {
      setNotice(`template_not_found:${name}`);
      return;
    }
    setTileProcTemplate(name);
    setTileProcCode(template);
    setTileProcStatus(`template_loaded:${name}`);
  }

  function saveGenerationPreset() {
    const name = tilePresetName.trim();
    if (!name) {
      setNotice("preset_save: name required");
      return;
    }
    const preset = {
      name,
      at: new Date().toISOString(),
      params: {
        cols: tileCols,
        rows: tileRows,
        cellPx: tileCellPx,
        exportScale: tileSvgExportScale,
        nearThreshold: tileNearThreshold,
        activeLayer: tileActiveLayer,
        presenceToken: tilePresenceToken,
        colorToken: tileColorToken,
        opacityToken: tileOpacityToken,
        template: tileProcTemplate,
        seed: tileProcSeed,
      },
      code: tileProcCode,
    };
    setTileSavedPresets((prev) => [preset, ...prev.filter((item) => item.name !== name)].slice(0, 40));
    setTileProcStatus(`preset_saved:${name}`);
  }

  function loadGenerationPreset(name) {
    const preset = tileSavedPresets.find((item) => item.name === name);
    if (!preset || typeof preset !== "object") {
      setNotice(`preset_load: not found ${name}`);
      return;
    }
    const p = preset.params || {};
    setTileCols(String(p.cols ?? tileCols));
    setTileRows(String(p.rows ?? tileRows));
    setTileCellPx(String(p.cellPx ?? tileCellPx));
    setTileSvgExportScale(String(p.exportScale ?? tileSvgExportScale));
    setTileNearThreshold(String(p.nearThreshold ?? tileNearThreshold));
    setTileActiveLayer(String(p.activeLayer ?? tileActiveLayer));
    setTilePresenceToken(String(p.presenceToken ?? tilePresenceToken));
    setTileColorToken(String(p.colorToken ?? tileColorToken));
    setTileOpacityToken(String(p.opacityToken ?? tileOpacityToken));
    setTileProcTemplate(String(p.template ?? tileProcTemplate));
    setTileProcSeed(String(p.seed ?? tileProcSeed));
    setTileProcCode(typeof preset.code === "string" ? preset.code : tileProcCode);
    setTileProcStatus(`preset_loaded:${name}`);
  }

  function buildAssetGenerationManifest() {
    return {
      profile: "asset-gen-v1",
      generated_at: new Date().toISOString(),
      workspace_id: workspaceId,
      generation: {
        seed: tileProcSeed,
        template: tileProcTemplate,
        code_hash: localStringHash(tileProcCode),
      },
      grid: {
        cols: tileSvgModel.cols,
        rows: tileSvgModel.rows,
        cell_px: tileSvgModel.cell,
        export_scale: clampInt(tileSvgExportScale, 1, 8, 2),
        width_px: tileSvgModel.width,
        height_px: tileSvgModel.height,
      },
      token_defaults: {
        presence: tilePresenceToken,
        color: tileColorToken,
        opacity: tileOpacityToken,
      },
      layers: tileSvgModel.layers.map((layer) => ({ name: layer.name, tile_count: layer.tiles.length })),
      counts: {
        tiles: Object.keys(tilePlacements).length,
        links: tileConnections.length,
      },
      hashes: {
        svg_hash: localStringHash(tileSvgMarkup),
        placement_hash: localFrontierHash(tilePlacements),
        links_hash: localFrontierHash(tileConnections),
      },
      motion_logic: {
        near_threshold: Number.parseInt(tileNearThreshold || "2", 10) || 2,
        tokens: { near: "Ti", far: "Ze" },
      },
    };
  }

  function exportAssetManifest() {
    const manifest = buildAssetGenerationManifest();
    downloadJson(`asset-manifest-${workspaceId}.json`, manifest);
  }

  async function createEntity(action, path, payload, reset, refresh) {
    await runAction(action, async () => {
      await apiCall(path, "POST", payload);
      reset();
      await refresh();
      return {};
    });
  }

  async function quickCreateCalendarBooking() {
    if (!selectedCalendarRange) {
      setNotice("calendar_booking_create: select one or more calendar days first");
      return;
    }
    if (!quickStartHour || !quickEndHour) {
      setNotice("calendar_booking_create: start and end time required");
      return;
    }
    const startIso = `${selectedCalendarRange.start}T${quickStartHour}:00`;
    const endIso = `${selectedCalendarRange.end}T${quickEndHour}:00`;
    if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
      setNotice("calendar_booking_create: end must be after start");
      return;
    }
    await createEntity(
      "calendar_booking_create",
      "/v1/booking",
      {
        workspace_id: workspaceId,
        starts_at: startIso,
        ends_at: endIso,
        status: "scheduled",
        notes: `profile:${profileName || "Artisan"}`
      },
      () => {},
      listBookings
    );
  }

  function openCalendarModalForDay(dayIso) {
    setCalendarModalDay(dayIso);
    setCalendarModalStart("10:00");
    setCalendarModalEnd("11:00");
    setCalendarModalStatus("scheduled");
    setCalendarModalNotes(`profile:${profileName || "Artisan"}`);
    setCalendarModalOpen(true);
  }

  async function createCalendarModalBooking() {
    if (!calendarModalDay) {
      setNotice("calendar_modal_create: no day selected");
      return;
    }
    const startIso = `${calendarModalDay}T${calendarModalStart}:00`;
    const endIso = `${calendarModalDay}T${calendarModalEnd}:00`;
    if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
      setNotice("calendar_modal_create: end must be after start");
      return;
    }
    if (calendarModalConflicts.length > 0) {
      setNotice("calendar_modal_create: conflict detected, adjust time or proceed intentionally");
      return;
    }
    await createEntity(
      "calendar_modal_create",
      "/v1/booking",
      {
        workspace_id: workspaceId,
        starts_at: startIso,
        ends_at: endIso,
        status: calendarModalStatus,
        notes: calendarModalNotes
      },
      () => {
        setCalendarModalOpen(false);
        setCalendarModalDay(null);
      },
      listBookings
    );
  }

  function createStudioFolder() {
    const name = studioNewFolder.trim();
    if (!name) {
      setNotice("studio_folder_create: name required");
      return;
    }
    if (studioFolders.includes(name)) {
      setNotice("studio_folder_create: folder already exists");
      return;
    }
    setStudioFolders((prev) => [...prev, name]);
    setStudioTargetFolder(name);
    setStudioNewFolder("");
  }

  function createStudioFile() {
    const name = studioNewFileName.trim();
    if (!name) {
      setNotice("studio_file_create: name required");
      return;
    }
    if (!studioTargetFolder) {
      setNotice("studio_file_create: folder required");
      return;
    }
    const next = {
      id: makeStudioFileId(),
      name,
      folder: studioTargetFolder,
      content: ""
    };
    setStudioFiles((prev) => [...prev, next]);
    setStudioSelectedFileId(next.id);
    setStudioNewFileName("");
  }

  function updateStudioSelectedContent(value) {
    if (!studioSelectedFile) {
      return;
    }
    setStudioFiles((prev) =>
      prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, content: value } : file))
    );
  }

  function deleteStudioSelectedFile() {
    if (!studioSelectedFile) {
      return;
    }
    setStudioFiles((prev) => prev.filter((file) => file.id !== studioSelectedFile.id));
  }

  function renameStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_rename: no file selected");
      return;
    }
    const nextName = studioRenameFileName.trim();
    if (!nextName) {
      setNotice("studio_file_rename: name required");
      return;
    }
    setStudioFiles((prev) => prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, name: nextName } : file)));
  }

  function moveStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_move: no file selected");
      return;
    }
    if (!studioMoveTargetFolder) {
      setNotice("studio_file_move: target folder required");
      return;
    }
    setStudioFiles((prev) =>
      prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, folder: studioMoveTargetFolder } : file))
    );
  }

  function renameStudioFolder() {
    const from = studioRenameFolderFrom.trim();
    const to = studioRenameFolderTo.trim();
    if (!from || !to) {
      setNotice("studio_folder_rename: source and target required");
      return;
    }
    if (!studioFolders.includes(from)) {
      setNotice("studio_folder_rename: source not found");
      return;
    }
    if (studioFolders.includes(to)) {
      setNotice("studio_folder_rename: target already exists");
      return;
    }
    setStudioFolders((prev) => prev.map((folder) => (folder === from ? to : folder)));
    setStudioFiles((prev) => prev.map((file) => (file.folder === from ? { ...file, folder: to } : file)));
    setStudioTargetFolder(to);
    setStudioMoveTargetFolder(to);
    setStudioRenameFolderFrom(to);
    setStudioRenameFolderTo("");
  }

  async function fetchArtisanAccessStatus() {
    await runAction("artisan_access_status", async () => {
      const data = await apiCall("/v1/access/artisan-id/status", "GET", null);
      setArtisanAccessVerified(Boolean(data.artisan_access_verified));
      return data;
    });
  }

  async function issueArtisanAccessCode() {
    await runAction("artisan_access_issue", async () => {
      const data = await apiCall("/v1/access/artisan-id/issue", "POST", {
        profile_name: profileName,
        profile_email: profileEmail
      });
      const issued = typeof data.artisan_code === "string" ? data.artisan_code : "";
      setArtisanIssuedCode(issued);
      setArtisanAccessInput(issued);
      setArtisanAccessVerified(Boolean(data.status?.artisan_access_verified));
      return data;
    });
  }

  async function verifyArtisanAccess() {
    await runAction("artisan_access_verify", async () => {
      const data = await apiCall("/v1/access/artisan-id/verify", "POST", {
        profile_name: profileName,
        profile_email: profileEmail,
        artisan_code: artisanAccessInput
      });
      setArtisanAccessVerified(Boolean(data.artisan_access_verified));
      return data;
    });
  }

  function duplicateStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_duplicate: no file selected");
      return;
    }
    const copy = {
      ...studioSelectedFile,
      id: makeStudioFileId(),
      name: `${studioSelectedFile.name}.copy`
    };
    setStudioFiles((prev) => [...prev, copy]);
    setStudioSelectedFileId(copy.id);
  }

  function duplicateStudioFolder() {
    const from = studioRenameFolderFrom.trim();
    if (!from || !studioFolders.includes(from)) {
      setNotice("studio_folder_duplicate: source folder required");
      return;
    }
    const duplicated = `${from}_copy`;
    if (studioFolders.includes(duplicated)) {
      setNotice("studio_folder_duplicate: copy already exists");
      return;
    }
    const filesToCopy = studioFiles.filter((file) => file.folder === from);
    setStudioFolders((prev) => [...prev, duplicated]);
    setStudioFiles((prev) => [
      ...prev,
      ...filesToCopy.map((file) => ({
        ...file,
        id: makeStudioFileId(),
        folder: duplicated,
        name: `${file.name}.copy`
      }))
    ]);
  }

  function moveFileToFolder(fileId, folder) {
    if (!fileId || !folder) {
      return;
    }
    setStudioFiles((prev) => prev.map((file) => (file.id === fileId ? { ...file, folder } : file)));
  }

  function hasDesktopFs() {
    return Boolean(window.atelierDesktop && window.atelierDesktop.fs);
  }

  async function chooseStudioFsFolder() {
    await runAction("studio_fs_choose", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      const result = await window.atelierDesktop.fs.chooseDirectory();
      if (!result || !result.ok || typeof result.directory !== "string") {
        throw new Error("studio_fs_choose cancelled");
      }
      setStudioFsRoot(result.directory);
      return result;
    });
  }

  async function refreshStudioFsScripts() {
    await runAction("studio_fs_list", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const result = await window.atelierDesktop.fs.listCobraScripts(studioFsRoot);
      if (!result || !result.ok || !Array.isArray(result.files)) {
        throw new Error("studio_fs_list failed");
      }
      setStudioFsScripts(result.files);
      if (result.files.length > 0) {
        setStudioFsSelectedScript(String(result.files[0]));
      }
      return result;
    });
  }

  async function saveSelectedStudioFileToFs() {
    await runAction("studio_fs_save_selected", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioSelectedFile) {
        throw new Error("studio_fs no selected file");
      }
      const sourceName = String(studioSelectedFile.name || "untitled.cobra");
      const filename = sourceName.toLowerCase().endsWith(".cobra") ? sourceName : `${sourceName}.cobra`;
      const result = await window.atelierDesktop.fs.writeCobraScript(studioFsRoot, filename, String(studioSelectedFile.content || ""));
      await refreshStudioFsScripts();
      return result;
    });
  }

  async function importSelectedFsScriptToStudio() {
    await runAction("studio_fs_import", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioFsSelectedScript) {
        throw new Error("studio_fs no script selected");
      }
      const result = await window.atelierDesktop.fs.readCobraScript(studioFsRoot, studioFsSelectedScript);
      if (!result || !result.ok || typeof result.content !== "string") {
        throw new Error("studio_fs_read failed");
      }
      const nextFile = {
        id: makeStudioFileId(),
        name: typeof result.filename === "string" && result.filename ? result.filename : studioFsSelectedScript,
        folder: "scripts",
        content: result.content
      };
      setStudioFiles((prev) => [...prev, nextFile]);
      setStudioSelectedFileId(nextFile.id);
      setRendererCobra(result.content);
      return result;
    });
  }

  async function exportAllCobraScriptsToFs() {
    await runAction("studio_fs_export_all_cobra", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const cobraFiles = studioFiles.filter((file) => String(file.name || "").toLowerCase().endsWith(".cobra"));
      if (cobraFiles.length === 0) {
        throw new Error("studio_fs no .cobra files in studio");
      }
      for (const file of cobraFiles) {
        await window.atelierDesktop.fs.writeCobraScript(studioFsRoot, file.name, String(file.content || ""));
      }
      await refreshStudioFsScripts();
      return { exported: cobraFiles.length };
    });
  }

  function appendLessonBlock(block) {
    setLessonBody((prev) => `${prev}${prev ? "\n\n" : ""}${block}`);
  }

  function surroundSelection(textarea, open, close) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = lessonBody.slice(0, start);
    const selected = lessonBody.slice(start, end);
    const after = lessonBody.slice(end);
    const next = `${before}${open}${selected}${close}${after}`;
    setLessonBody(next);
    requestAnimationFrame(() => {
      const cursorStart = start + open.length;
      const cursorEnd = cursorStart + selected.length;
      textarea.setSelectionRange(cursorStart, cursorEnd);
      textarea.focus();
    });
  }

  function prefixSelectedLines(textarea, prefix) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = lessonBody.slice(0, start);
    const selected = lessonBody.slice(start, end);
    const after = lessonBody.slice(end);
    const lines = selected ? selected.split("\n") : [""];
    const prefixed = lines.map((line) => `${prefix}${line}`).join("\n");
    const next = `${before}${prefixed}${after}`;
    setLessonBody(next);
    requestAnimationFrame(() => {
      textarea.setSelectionRange(start, start + prefixed.length);
      textarea.focus();
    });
  }

  function handleLessonEditorKeyDown(event) {
    const textarea = event.currentTarget;
    const mod = event.ctrlKey || event.metaKey;
    if (event.key === "Tab") {
      event.preventDefault();
      const pos = textarea.selectionStart;
      const next = `${lessonBody.slice(0, pos)}  ${lessonBody.slice(textarea.selectionEnd)}`;
      setLessonBody(next);
      requestAnimationFrame(() => {
        textarea.setSelectionRange(pos + 2, pos + 2);
      });
      return;
    }
    if (!mod) {
      return;
    }
    if (event.key.toLowerCase() === "b") {
      event.preventDefault();
      surroundSelection(textarea, "**", "**");
      return;
    }
    if (event.key.toLowerCase() === "i") {
      event.preventDefault();
      surroundSelection(textarea, "*", "*");
      return;
    }
    if (event.key.toLowerCase() === "k") {
      event.preventDefault();
      surroundSelection(textarea, "`", "`");
      return;
    }
    if (event.shiftKey && event.key === "7") {
      event.preventDefault();
      prefixSelectedLines(textarea, "1. ");
      return;
    }
    if (event.shiftKey && event.key === "8") {
      event.preventDefault();
      prefixSelectedLines(textarea, "- ");
      return;
    }
    if (event.shiftKey && event.key.toLowerCase() === "c") {
      event.preventDefault();
      prefixSelectedLines(textarea, "> ");
    }
  }

  const filtered = (items, text, keys) =>
    items.filter((it) => (text ? keys.map((k) => String(it[k] || "")).join(" ").toLowerCase().includes(text.toLowerCase()) : true));

  const filteredContacts = filtered(contacts, contactFilter, ["full_name", "email"]);
  const filteredBookings = filtered(bookings, bookingFilter, ["status", "starts_at", "ends_at"]);
  const filteredLessons = filtered(lessons, lessonFilter, ["title", "status"]);
  const filteredModules = filtered(modules, moduleFilter, ["title", "status"]);
  const filteredLeads = filtered(leads, leadFilter, ["full_name", "email", "status"]);
  const filteredClients = filtered(clients, clientFilter, ["full_name", "email", "status"]);
  const filteredQuotes = filtered(quotes, quoteFilter, ["title", "status", "currency"]);
  const filteredOrders = filtered(orders, orderFilter, ["title", "status", "currency"]);
  const filteredSuppliers = filtered(suppliers, supplierFilter, ["supplier_name", "contact_name", "contact_email"]);
  const filteredInventory = filtered(inventoryItems, inventoryFilter, ["sku", "name", "currency"]);
  const rendererEngineState = useMemo(() => {
    try {
      const parsed = JSON.parse(rendererEngineStateText || "{}");
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed;
      }
      return { tick: 0 };
    } catch {
      return { tick: 0 };
    }
  }, [rendererEngineStateText]);
  const pythonFrameDoc = useMemo(() => buildRendererFrameHtml("python", rendererPython, rendererEngineState), [rendererPython, rendererEngineState]);
  const cobraFrameDoc = useMemo(() => buildRendererFrameHtml("cobra", rendererCobra, rendererEngineState), [rendererCobra, rendererEngineState]);
  const cobraLintWarnings = useMemo(() => analyzeCobraShygazunScript(rendererCobra), [rendererCobra]);
  const jsFrameDoc = useMemo(() => buildRendererFrameHtml("javascript", rendererJs, rendererEngineState), [rendererJs, rendererEngineState]);
  const jsonFrameDoc = useMemo(() => buildRendererFrameHtml("json", rendererJson, rendererEngineState), [rendererJson, rendererEngineState]);
  const workshopFrontierGraph = useMemo(
    () => buildFrontierGraph(akinenwunFrontier && akinenwunFrontier.frontier ? akinenwunFrontier.frontier : null),
    [akinenwunFrontier]
  );
  const rendererFrontierGraph = useMemo(
    () => buildFrontierGraph(
      rendererAkinenwunFrontier && rendererAkinenwunFrontier.frontier ? rendererAkinenwunFrontier.frontier : null
    ),
    [rendererAkinenwunFrontier]
  );
  const rendererGameSpec = useMemo(() => parseObjectJson(rendererGameSpecText, {}), [rendererGameSpecText]);
  const rendererGameEntities = useMemo(
    () => (Array.isArray(rendererGameSpec.entities) ? rendererGameSpec.entities : []),
    [rendererGameSpec]
  );
  const tileGridCells = useMemo(() => {
    const cols = clampInt(tileCols, 1, 128, 48);
    const rows = clampInt(tileRows, 1, 128, 27);
    const out = [];
    for (let y = 0; y < rows; y += 1) {
      for (let x = 0; x < cols; x += 1) {
        const key = tileKey(x, y);
        out.push({
          key,
          x,
          y,
          placement: tilePlacements[key] || null,
        });
      }
    }
    return out;
  }, [tileCols, tileRows, tilePlacements]);
  const tilePreviewCellPx = useMemo(() => clampInt(tileCellPx, 10, 40, 24), [tileCellPx]);
  const tileLayerList = useMemo(() => {
    const defaults = ["ground", "base", "detail", "fx", "ui"];
    const found = Object.values(tilePlacements)
      .map((item) => String(item.layer || "base"))
      .filter((item, index, arr) => arr.indexOf(item) === index);
    return [...defaults.filter((d) => !found.includes(d)), ...found].sort((a, b) => a.localeCompare(b));
  }, [tilePlacements]);
  const tileSvgModel = useMemo(() => {
    const cols = clampInt(tileCols, 1, 256, 48);
    const rows = clampInt(tileRows, 1, 256, 27);
    const cell = clampInt(tileCellPx, 8, 128, 24);
    const width = cols * cell;
    const height = rows * cell;
    const layers = tileLayerList.map((layer) => ({
      name: layer,
      tiles: Object.values(tilePlacements).filter((item) => String(item.layer || "base") === layer),
    }));
    const links = tileConnections.map((link) => {
      const a = parseTileKey(link.from);
      const b = parseTileKey(link.to);
      return {
        ...link,
        x1: a.x * cell + cell / 2,
        y1: a.y * cell + cell / 2,
        x2: b.x * cell + cell / 2,
        y2: b.y * cell + cell / 2,
      };
    });
    return { cols, rows, cell, width, height, layers, links };
  }, [tileCols, tileRows, tileCellPx, tileLayerList, tilePlacements, tileConnections]);
  const tileSvgMarkup = useMemo(() => {
    return buildTileSvgMarkup(tileSvgModel, tileSvgShowGrid, tileSvgShowLinks, 1);
  }, [tileSvgModel, tileSvgShowGrid, tileSvgShowLinks]);
  const graphMakerFrontierResult = useMemo(() => {
    if (graphMakerSource === "workshop") {
      return {
        frontier: akinenwunFrontier && akinenwunFrontier.frontier ? akinenwunFrontier.frontier : null,
        error: ""
      };
    }
    if (graphMakerSource === "renderer") {
      return {
        frontier: rendererAkinenwunFrontier && rendererAkinenwunFrontier.frontier ? rendererAkinenwunFrontier.frontier : null,
        error: ""
      };
    }
    try {
      const parsed = JSON.parse(graphMakerManualFrontierText || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return { frontier: null, error: "manual frontier must be an object" };
      }
      return { frontier: parsed, error: "" };
    } catch {
      return { frontier: null, error: "manual frontier is not valid JSON" };
    }
  }, [graphMakerSource, akinenwunFrontier, rendererAkinenwunFrontier, graphMakerManualFrontierText]);
  const graphMakerGraph = useMemo(() => buildFrontierGraph(graphMakerFrontierResult.frontier), [graphMakerFrontierResult]);
  const calendarCells = useMemo(() => buildCalendarDays(calendarYear, calendarMonth), [calendarYear, calendarMonth]);
  const selectedCalendarRange = useMemo(() => {
    if (!calendarDragStart || !calendarDragEnd) {
      return null;
    }
    const start = compareIso(calendarDragStart, calendarDragEnd) <= 0 ? calendarDragStart : calendarDragEnd;
    const end = compareIso(calendarDragStart, calendarDragEnd) <= 0 ? calendarDragEnd : calendarDragStart;
    return { start, end };
  }, [calendarDragStart, calendarDragEnd]);
  const bookingsByDay = useMemo(() => {
    const byDay = {};
    for (const booking of bookings) {
      const start = String(booking.starts_at || "").slice(0, 10);
      if (!start) {
        continue;
      }
      if (!byDay[start]) {
        byDay[start] = [];
      }
      byDay[start].push(booking);
    }
    return byDay;
  }, [bookings]);
  const calendarModalConflicts = useMemo(() => {
    if (!calendarModalDay) {
      return [];
    }
    const startIso = `${calendarModalDay}T${calendarModalStart}:00`;
    const endIso = `${calendarModalDay}T${calendarModalEnd}:00`;
    const start = new Date(startIso).getTime();
    const end = new Date(endIso).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      return [];
    }
    return bookings.filter((booking) => {
      const bStart = new Date(String(booking.starts_at || "")).getTime();
      const bEnd = new Date(String(booking.ends_at || "")).getTime();
      if (!Number.isFinite(bStart) || !Number.isFinite(bEnd)) {
        return false;
      }
      return rangesOverlap(start, end, bStart, bEnd);
    });
  }, [bookings, calendarModalDay, calendarModalStart, calendarModalEnd]);

  function isDaySelected(iso) {
    if (!iso || !selectedCalendarRange) {
      return false;
    }
    return compareIso(iso, selectedCalendarRange.start) >= 0 && compareIso(iso, selectedCalendarRange.end) <= 0;
  }

  function stepRendererEngine() {
    const next = {
      ...rendererEngineState,
      tick: Number(rendererEngineState.tick || 0) + 1
    };
    setRendererEngineStateText(JSON.stringify(next, null, 2));
  }

  function compileGameSpecToRenderer() {
    const spec = parseObjectJson(rendererGameSpecText, {});
    const scene = spec.scene && typeof spec.scene === "object" ? spec.scene : {};
    const systems = spec.systems && typeof spec.systems === "object" ? spec.systems : {};
    const entities = Array.isArray(spec.entities) ? spec.entities : [];
    const tileEntities = Object.values(tilePlacements);
    const linkEntities = tileConnections.map((link) => ({
      id: link.id,
      kind: "tile_link",
      from: link.from,
      to: link.to,
      from_layer: parseTileKey(link.from).layer,
      to_layer: parseTileKey(link.to).layer,
      relation_token: link.relation_token,
      distance: link.distance,
    }));
    const mergedEntities = [...entities, ...tileEntities, ...linkEntities];
    const tileMotion = tileConnections.map((link) => ({
      from: link.from,
      to: link.to,
      relation_token: link.relation_token,
      distance: link.distance,
    }));
    const systemsNext = {
      ...systems,
      tile_motion_logic: tileMotion,
    };
    const nextEngine = {
      ...rendererEngineState,
      camera: systems.camera && typeof systems.camera === "object" ? systems.camera : rendererEngineState.camera || { x: 0, y: 0 },
      gravity: Number(systems.gravity || 0),
      scene: scene.name || "prototype",
      entities: mergedEntities.length
    };
    setRendererPython(compilePythonDrawFromEntities(String(scene.name || "prototype"), mergedEntities));
    setRendererCobra(compileCobraFromEntities(mergedEntities));
    setRendererJson(JSON.stringify({ scene, systems: systemsNext, entities: mergedEntities }, null, 2));
    setRendererEngineStateText(JSON.stringify(nextEngine, null, 2));
    setRendererGameStatus(`compiled:${mergedEntities.length}_entities`);
  }

  function addEntityToGameSpec() {
    const spec = parseObjectJson(rendererGameSpecText, {});
    const existing = Array.isArray(spec.entities) ? spec.entities : [];
    const nextEntity = {
      id: rendererNewEntityId || `entity-${Date.now()}`,
      kind: rendererNewEntityKind || "token",
      x: Number(rendererNewEntityX || 0),
      y: Number(rendererNewEntityY || 0)
    };
    const merged = { ...spec, entities: [...existing, nextEntity] };
    setRendererGameSpecText(JSON.stringify(merged, null, 2));
    setRendererGameStatus(`entity_added:${nextEntity.id}`);
  }

  function paintTile(x, y) {
    const key = tileKey(x, y, tileActiveLayer);
    if (tilePresenceToken === "Zo") {
      setTilePlacements((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      setRendererGameStatus(`tile_removed:${key}`);
      return;
    }
    const placement = {
      id: `tile_${tileActiveLayer}_${x}_${y}`,
      x,
      y,
      layer: tileActiveLayer,
      presence_token: "Ta",
      color_token: tileColorToken,
      opacity_token: tileOpacityToken,
    };
    setTilePlacements((prev) => ({ ...prev, [key]: placement }));
    setRendererGameStatus(`tile_painted:${key}`);
  }

  function connectTile(aKey, bKey) {
    if (!aKey || !bKey || aKey === bKey) {
      return;
    }
    const a = parseTileKey(aKey);
    const b = parseTileKey(bKey);
    const distance = tileDistance(a, b);
    const nearThreshold = Math.max(1, Number.parseInt(tileNearThreshold || "2", 10) || 2);
    const relation = relationTokenForDistance(distance, nearThreshold);
    const connId = [aKey, bKey].sort().join("->");
    const nextConn = {
      id: `link_${connId.replace(",", "_").replace("->", "__")}`,
      from: aKey,
      to: bKey,
      distance,
      relation_token: relation,
    };
    setTileConnections((prev) => {
      const filtered = prev.filter((it) => it.id !== nextConn.id);
      return [...filtered, nextConn];
    });
    setRendererGameStatus(`tile_connected:${nextConn.id}`);
  }

  function handleTileClick(x, y) {
    const key = tileKey(x, y, tileActiveLayer);
    if (tileConnectMode) {
      if (!tileConnectFrom) {
        setTileConnectFrom(key);
        return;
      }
      connectTile(tileConnectFrom, key);
      setTileConnectFrom(null);
      return;
    }
    paintTile(x, y);
  }

  function renderSectionTools() {
    const restrictedSections = new Set(["Workshop", "Temple and Gardens", "Guild Hall"]);
    if (restrictedSections.has(section) && !artisanAccessVerified) {
      return (
        <section className="panel">
          <h2>Artisan Access Gate</h2>
          <p>This space requires a verified ArtisanID bound to your profile and station.</p>
          <div className="row">
            <input value={artisanAccessInput} onChange={(e) => setArtisanAccessInput(e.target.value)} placeholder="enter artisan ID code" />
            <button className="action" onClick={verifyArtisanAccess}>Verify Access</button>
          </div>
          <p>{`Profile: ${profileName || "Artisan"} | Station: ${role} | Workspace: ${workspaceId}`}</p>
          <div className="row">
            <button className="action" onClick={issueArtisanAccessCode}>Issue Server Code</button>
            <button className="action" onClick={fetchArtisanAccessStatus}>Refresh Status</button>
          </div>
          {artisanIssuedCode ? <p>{`Issued code: ${artisanIssuedCode}`}</p> : null}
        </section>
      );
    }

    if (section === "Foyer") {
      return (
        <>
          <section className="panel">
            <h2>Session Control</h2>
            <div className="row">
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="apprentice">Apprentice</option>
                <option value="artisan">Artisan</option>
                <option value="senior_artisan">Senior Artisan</option>
                <option value="steward">Steward</option>
              </select>
              <input value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} placeholder="workspace id" />
              <button className="action" onClick={loadOrganizationOverview}>Load Overview</button>
            </div>
            <div className="kpis">
              {datasetSummary.map((it) => (
                <div className="kpi" key={it.label}><span>{it.label}</span><strong>{it.value}</strong></div>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2>User Profile</h2>
            <div className="row">
              <input value={profileName} onChange={(e) => setProfileName(e.target.value)} placeholder="display name" />
              <input value={profileEmail} onChange={(e) => setProfileEmail(e.target.value)} placeholder="email" />
              <input value={profileTimezone} onChange={(e) => setProfileTimezone(e.target.value)} placeholder="timezone (IANA)" />
            </div>
            <p>{`Bookings and calendar views are scoped to workspace "${workspaceId}" and profile "${profileName || "Artisan"}".`}</p>
            <div className="row">
              <input value={artisanAccessInput} onChange={(e) => setArtisanAccessInput(e.target.value)} placeholder="artisan ID access code" />
              <button className="action" onClick={verifyArtisanAccess}>Verify Workshop/Temple/Guild Access</button>
              <button className="action" onClick={issueArtisanAccessCode}>Issue Server Code</button>
              <button className="action" onClick={fetchArtisanAccessStatus}>Refresh Status</button>
            </div>
            <p>{`Access status: ${artisanAccessVerified ? "verified" : "locked"}`}</p>
            {artisanIssuedCode ? <p>{`Issued code: ${artisanIssuedCode}`}</p> : null}
          </section>
          <section className="panel">
            <h2>Booking Calendar</h2>
            <div className="row">
              <button className="action" onClick={() => {
                if (calendarMonth === 0) {
                  setCalendarMonth(11);
                  setCalendarYear((y) => y - 1);
                } else {
                  setCalendarMonth((m) => m - 1);
                }
              }}>Prev Month</button>
              <strong className="calendar-label">{monthLabel(calendarYear, calendarMonth)}</strong>
              <button className="action" onClick={() => {
                if (calendarMonth === 11) {
                  setCalendarMonth(0);
                  setCalendarYear((y) => y + 1);
                } else {
                  setCalendarMonth((m) => m + 1);
                }
              }}>Next Month</button>
              <button className="action" onClick={listBookings}>Refresh Bookings</button>
            </div>
            <div className="row">
              <input value={quickStartHour} onChange={(e) => setQuickStartHour(e.target.value)} placeholder="start HH:MM" />
              <input value={quickEndHour} onChange={(e) => setQuickEndHour(e.target.value)} placeholder="end HH:MM" />
              <button className="action" onClick={quickCreateCalendarBooking}>Create Booking From Selection</button>
              <button className="action" onClick={() => { setCalendarDragStart(null); setCalendarDragEnd(null); }}>Clear Selection</button>
            </div>
            <p>
              {selectedCalendarRange
                ? `Selected range: ${selectedCalendarRange.start} to ${selectedCalendarRange.end}`
                : "Drag across days to select a booking range."}
            </p>
            <div className="calendar-grid">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((name) => (
                <div key={name} className="calendar-head">{name}</div>
              ))}
              {calendarCells.map((cell) => {
                const count = cell.iso ? (bookingsByDay[cell.iso] || []).length : 0;
                return (
                  <div
                    key={cell.key}
                    className={`calendar-cell ${cell.day ? "" : "calendar-cell-empty"} ${isDaySelected(cell.iso) ? "calendar-cell-selected" : ""}`}
                    onMouseDown={() => {
                      if (!cell.iso) {
                        return;
                      }
                      setCalendarDragStart(cell.iso);
                      setCalendarDragEnd(cell.iso);
                      setCalendarDragging(true);
                    }}
                    onMouseEnter={() => {
                      if (!cell.iso || !calendarDragging) {
                        return;
                      }
                      setCalendarDragEnd(cell.iso);
                    }}
                    onMouseUp={() => {
                      if (!cell.iso) {
                        setCalendarDragging(false);
                        return;
                      }
                      if (calendarDragging) {
                        setCalendarDragEnd(cell.iso);
                      }
                      setCalendarDragging(false);
                    }}
                  >
                    {cell.day ? (
                      <>
                        <div className="calendar-day-row">
                          <span>{cell.day}</span>
                          <button
                            className="calendar-add-btn"
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (cell.iso) {
                                openCalendarModalForDay(cell.iso);
                              }
                            }}
                          >
                            +
                          </button>
                        </div>
                        {count > 0 ? <em>{`${count} booking${count === 1 ? "" : "s"}`}</em> : null}
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {calendarModalOpen ? (
              <div className="modal-backdrop">
                <div className="modal-card">
                  <h3>{`Create Booking - ${calendarModalDay}`}</h3>
                  <div className="row">
                    <input value={calendarModalStart} onChange={(e) => setCalendarModalStart(e.target.value)} placeholder="start HH:MM" />
                    <input value={calendarModalEnd} onChange={(e) => setCalendarModalEnd(e.target.value)} placeholder="end HH:MM" />
                  </div>
                  <div className="row">
                    <input value={calendarModalStatus} onChange={(e) => setCalendarModalStatus(e.target.value)} placeholder="status" />
                    <input value={calendarModalNotes} onChange={(e) => setCalendarModalNotes(e.target.value)} placeholder="notes" />
                  </div>
                  {calendarModalConflicts.length > 0 ? (
                    <div className="conflict-box">
                      <strong>{`${calendarModalConflicts.length} conflict${calendarModalConflicts.length === 1 ? "" : "s"} detected`}</strong>
                      <ul>
                        {calendarModalConflicts.map((booking) => (
                          <li key={booking.id || `${booking.starts_at}-${booking.ends_at}`}>
                            {`${String(booking.starts_at)} -> ${String(booking.ends_at)} (${String(booking.status || "scheduled")})`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <div className="row">
                    <button className="action" onClick={createCalendarModalBooking}>Create</button>
                    <button
                      className="action"
                      onClick={() =>
                        createEntity(
                          "calendar_modal_force_create",
                          "/v1/booking",
                          {
                            workspace_id: workspaceId,
                            starts_at: `${calendarModalDay}T${calendarModalStart}:00`,
                            ends_at: `${calendarModalDay}T${calendarModalEnd}:00`,
                            status: calendarModalStatus,
                            notes: `${calendarModalNotes} [conflict_override]`
                          },
                          () => {
                            setCalendarModalOpen(false);
                            setCalendarModalDay(null);
                          },
                          listBookings
                        )
                      }
                      disabled={calendarModalConflicts.length === 0}
                    >
                      Force Create
                    </button>
                    <button className="action" onClick={() => setCalendarModalOpen(false)}>Cancel</button>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
          <GraphBars title="Organization Graph" items={datasetSummary} />
        </>
      );
    }
    if (section === "Workshop") {
      return (
        <>
          <section className="panel">
            <h2>Admin Gate</h2>
            <p>{gateMessage}</p>
            <div className="row">
              <input value={gateCode} onChange={(e) => setGateCode(e.target.value)} placeholder="steward gate code" disabled={role !== "steward"} />
              <button className="action" onClick={verifyAdminGate} disabled={role !== "steward"}>Verify Gate</button>
              <button className="action" onClick={() => void refreshGateStatus(undefined)}>Refresh</button>
            </div>
          </section>
          {adminVerified && role === "steward" ? (
            <>
              <section className="panel">
                <h2>Placement Emitter</h2>
                <div className="row">
                  <input value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="emit placement line" />
                  <button className="action" onClick={place}>Emit Placement</button>
                </div>
              </section>
              <section className="panel">
                <h2>Sprite Generator</h2>
                <p>Emit structural sprite placements (manual or automatic grid) through Ambroflow landing.</p>
                <div className="row">
                  <input value={spriteId} onChange={(e) => setSpriteId(e.target.value)} placeholder="sprite id" />
                  <input value={spriteKind} onChange={(e) => setSpriteKind(e.target.value)} placeholder="sprite kind" />
                  <input value={spriteLayer} onChange={(e) => setSpriteLayer(e.target.value)} placeholder="layer" />
                </div>
                <div className="row">
                  <input value={spriteX} onChange={(e) => setSpriteX(e.target.value)} placeholder="x" />
                  <input value={spriteY} onChange={(e) => setSpriteY(e.target.value)} placeholder="y" />
                  <button className="action" onClick={emitSpriteManual}>Emit Manual Sprite</button>
                </div>
                <div className="row">
                  <input value={spriteAutoPrefix} onChange={(e) => setSpriteAutoPrefix(e.target.value)} placeholder="auto prefix" />
                  <input value={spriteAutoCount} onChange={(e) => setSpriteAutoCount(e.target.value)} placeholder="count" />
                  <input value={spriteAutoColumns} onChange={(e) => setSpriteAutoColumns(e.target.value)} placeholder="columns" />
                </div>
                <div className="row">
                  <input value={spriteAutoStartX} onChange={(e) => setSpriteAutoStartX(e.target.value)} placeholder="start x" />
                  <input value={spriteAutoStartY} onChange={(e) => setSpriteAutoStartY(e.target.value)} placeholder="start y" />
                  <input value={spriteAutoStepX} onChange={(e) => setSpriteAutoStepX(e.target.value)} placeholder="step x" />
                  <input value={spriteAutoStepY} onChange={(e) => setSpriteAutoStepY(e.target.value)} placeholder="step y" />
                  <button className="action" onClick={emitSpriteAuto}>Emit Auto Sprites</button>
                </div>
              </section>
              <section className="panel">
                <h2>Akinenwun Composer</h2>
                <p>Compound symbols are contiguous (no spaces). Resolve meaning frontier through kernel lookup.</p>
                <div className="row">
                  <input value={akinenwunWord} onChange={(e) => setAkinenwunWord(e.target.value)} placeholder="Akinenwun e.g. TyKoWuVu" />
                  <select value={akinenwunMode} onChange={(e) => setAkinenwunMode(e.target.value)}>
                    <option value="prose">Prose mode</option>
                    <option value="engine">Engine mode</option>
                  </select>
                  <label>
                    <input type="checkbox" checked={akinenwunIngest} onChange={(e) => setAkinenwunIngest(e.target.checked)} /> Ingest dictionary
                  </label>
                  <button
                    className="action"
                    onClick={() => lookupAkinenwun(akinenwunWord, akinenwunMode, akinenwunIngest, setAkinenwunFrontier, "akinenwun_lookup_workshop")}
                  >
                    Resolve Frontier
                  </button>
                </div>
                <div className="row">
                  <span className="badge">{`Hash: ${akinenwunFrontier?.frontier_hash || "n/a"}`}</span>
                  <span className="badge">{`Stored: ${akinenwunFrontier?.stored ? "yes" : "no"}`}</span>
                  <span className="badge">{`Dictionary Size: ${akinenwunFrontier?.dictionary_size ?? 0}`}</span>
                </div>
                <pre>{JSON.stringify(akinenwunFrontier || {}, null, 2)}</pre>
              </section>
              <GraphBars
                title="Akinenwun Graph Maker"
                items={[
                  { label: "Paths", value: workshopFrontierGraph.stats.paths },
                  { label: "Nodes", value: workshopFrontierGraph.stats.nodes },
                  { label: "Edges", value: workshopFrontierGraph.stats.edges },
                  { label: "Symbols", value: workshopFrontierGraph.stats.symbols }
                ]}
              />
              <section className="panel">
                <h2>Graph Projection</h2>
                <p>Projected node/edge view from frontier paths for workshop tooling.</p>
                <pre>{JSON.stringify({ nodes: workshopFrontierGraph.nodes, edges: workshopFrontierGraph.edges }, null, 2)}</pre>
              </section>
            </>
          ) : null}
        </>
      );
    }
    if (section === "CRM") {
      return (
        <section className="panel">
          <h2>CRM</h2>
          <div className="row">
            <input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="contact name" />
            <input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="contact email" />
            <button className="action" onClick={() => createEntity("contacts_create", "/v1/crm/contacts", { workspace_id: workspaceId, full_name: contactName, email: contactEmail || null, notes: "" }, () => { setContactName(""); setContactEmail(""); }, listContacts)}>Create</button>
            <button className="action" onClick={listContacts}>Refresh</button>
          </div>
          <div className="row"><input value={contactFilter} onChange={(e) => setContactFilter(e.target.value)} placeholder="filter contacts" /><button className="action" onClick={() => downloadJson(`contacts-${workspaceId}.json`, filteredContacts)}>Export</button></div>
          <pre>{JSON.stringify(filteredContacts, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Booking System") {
      return (
        <section className="panel">
          <h2>Booking System</h2>
          <div className="row">
            <input value={bookingStart} onChange={(e) => setBookingStart(e.target.value)} placeholder="start ISO datetime" />
            <input value={bookingEnd} onChange={(e) => setBookingEnd(e.target.value)} placeholder="end ISO datetime" />
            <button className="action" onClick={() => createEntity("bookings_create", "/v1/booking", { workspace_id: workspaceId, starts_at: bookingStart, ends_at: bookingEnd, status: "scheduled", notes: "" }, () => {}, listBookings)}>Create</button>
            <button className="action" onClick={listBookings}>Refresh</button>
          </div>
          <div className="row"><input value={bookingFilter} onChange={(e) => setBookingFilter(e.target.value)} placeholder="filter bookings" /><button className="action" onClick={() => downloadJson(`bookings-${workspaceId}.json`, filteredBookings)}>Export</button></div>
          <pre>{JSON.stringify(filteredBookings, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Lesson Creation") {
      return (
        <section className="panel">
          <h2>Lesson Builder</h2>
          <div className="row">
            <input value={lessonTitle} onChange={(e) => setLessonTitle(e.target.value)} placeholder="lesson title" />
            <button className="action" onClick={() => createEntity("lessons_create", "/v1/lessons", { workspace_id: workspaceId, title: lessonTitle, body: lessonBody, status: "draft" }, () => { setLessonTitle(""); setLessonBody(""); }, listLessons)}>Create</button>
            <button className="action" onClick={listLessons}>Refresh</button>
          </div>
          <div className="row">
            <button className="action" onClick={() => appendLessonBlock("## Learning Objective\n- ")}>Add Objective Block</button>
            <button className="action" onClick={() => appendLessonBlock("### Exercise\n1. ")}>Add Exercise Block</button>
            <button className="action" onClick={() => appendLessonBlock("### Reflection\n- ")}>Add Reflection Block</button>
            <button className="action" onClick={() => appendLessonBlock("> Key Insight")}>Add Callout</button>
            <input value={lessonFilter} onChange={(e) => setLessonFilter(e.target.value)} placeholder="filter lessons" />
          </div>
          <div className="lesson-workbench">
            <div>
              <textarea
                className="editor lesson-editor"
                value={lessonBody}
                onChange={(e) => setLessonBody(e.target.value)}
                onKeyDown={handleLessonEditorKeyDown}
                placeholder="Write full lesson content with sections, spacing, bullets, and examples."
              />
              <div className="cheatsheet">
                <h4>Markdown Cheatsheet</h4>
                <ul>
                  {LESSON_MARKDOWN_CHEATSHEET.map((item) => (
                    <li key={item}><code>{item}</code></li>
                  ))}
                </ul>
                <p>Shortcuts: Ctrl/Cmd+B bold, Ctrl/Cmd+I italic, Ctrl/Cmd+K code, Ctrl/Cmd+Shift+8 bullet, Ctrl/Cmd+Shift+7 numbered, Ctrl/Cmd+Shift+C quote.</p>
              </div>
              <p className={`char-count ${lessonBody.length > LESSON_SOFT_LIMIT ? "char-count-warn" : ""}`}>
                {`Characters: ${lessonBody.length}${lessonBody.length > LESSON_SOFT_LIMIT ? ` (above soft limit ${LESSON_SOFT_LIMIT})` : ""}`}
              </p>
            </div>
            <div className="lesson-preview">
              <h3>Live Preview</h3>
              <div className="preview-body">{renderMarkdownBlocks(lessonBody)}</div>
            </div>
          </div>
          <pre>{JSON.stringify(filteredLessons, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Module Creation") {
      return (
        <section className="panel">
          <h2>Module Builder</h2>
          <div className="row">
            <input value={moduleTitle} onChange={(e) => setModuleTitle(e.target.value)} placeholder="module title" />
            <button className="action" onClick={() => createEntity("modules_create", "/v1/modules", { workspace_id: workspaceId, title: moduleTitle, description: moduleDescription, status: "draft" }, () => { setModuleTitle(""); setModuleDescription(""); }, listModules)}>Create</button>
            <button className="action" onClick={listModules}>Refresh</button>
          </div>
          <div className="row"><input value={moduleDescription} onChange={(e) => setModuleDescription(e.target.value)} placeholder="module description" /><input value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} placeholder="filter modules" /></div>
          <pre>{JSON.stringify(filteredModules, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Leads") {
      return (
        <section className="panel">
          <h2>Leads</h2>
          <div className="row">
            <input value={leadName} onChange={(e) => setLeadName(e.target.value)} placeholder="lead name" />
            <input value={leadEmail} onChange={(e) => setLeadEmail(e.target.value)} placeholder="lead email" />
            <button className="action" onClick={() => createEntity("leads_create", "/v1/leads", { workspace_id: workspaceId, full_name: leadName, email: leadEmail || null, details: leadDetails, status: "new", source: "internal" }, () => { setLeadName(""); setLeadEmail(""); setLeadDetails(""); }, listLeads)}>Create</button>
            <button className="action" onClick={listLeads}>Refresh</button>
          </div>
          <div className="row"><input value={leadDetails} onChange={(e) => setLeadDetails(e.target.value)} placeholder="lead details" /><input value={leadFilter} onChange={(e) => setLeadFilter(e.target.value)} placeholder="filter leads" /></div>
          <pre>{JSON.stringify(filteredLeads, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Clients") {
      return (
        <section className="panel">
          <h2>Clients</h2>
          <div className="row">
            <input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="client name" />
            <input value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} placeholder="client email" />
            <input value={clientPhone} onChange={(e) => setClientPhone(e.target.value)} placeholder="client phone" />
            <button className="action" onClick={() => createEntity("clients_create", "/v1/clients", { workspace_id: workspaceId, full_name: clientName, email: clientEmail || null, phone: clientPhone || null, status: "active" }, () => { setClientName(""); setClientEmail(""); setClientPhone(""); }, listClients)}>Create</button>
            <button className="action" onClick={listClients}>Refresh</button>
          </div>
          <div className="row"><input value={clientFilter} onChange={(e) => setClientFilter(e.target.value)} placeholder="filter clients" /></div>
          <pre>{JSON.stringify(filteredClients, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Quotes") {
      return (
        <>
          <section className="panel">
            <h2>Quotes</h2>
            <div className="row">
              <input value={quoteTitle} onChange={(e) => setQuoteTitle(e.target.value)} placeholder="quote title" />
              <input value={quoteAmount} onChange={(e) => setQuoteAmount(e.target.value)} placeholder="amount cents" />
              <input value={quoteCurrency} onChange={(e) => setQuoteCurrency(e.target.value)} placeholder="currency" />
              <label><input type="checkbox" checked={quotePublic} onChange={(e) => setQuotePublic(e.target.checked)} /> Public</label>
              <button className="action" onClick={() => createEntity("quotes_create", "/v1/quotes", { workspace_id: workspaceId, title: quoteTitle, amount_cents: Number.parseInt(quoteAmount || "0", 10), currency: quoteCurrency, status: quotePublic ? "published" : "draft", is_public: quotePublic, notes: "" }, () => { setQuoteTitle(""); setQuoteAmount(""); setQuotePublic(false); }, listQuotes)}>Create</button>
              <button className="action" onClick={listQuotes}>Refresh</button>
            </div>
            <div className="row"><input value={quoteFilter} onChange={(e) => setQuoteFilter(e.target.value)} placeholder="filter quotes" /></div>
            <pre>{JSON.stringify(filteredQuotes, null, 2)}</pre>
          </section>
          <GraphBars
            title="Quote Status Graph"
            items={[
              { label: "Draft", value: quotes.filter((q) => q.status === "draft").length },
              { label: "Published", value: quotes.filter((q) => q.status === "published").length },
              { label: "Public", value: quotes.filter((q) => q.is_public).length }
            ]}
          />
        </>
      );
    }
    if (section === "Orders") {
      return (
        <section className="panel">
          <h2>Orders</h2>
          <div className="row">
            <input value={orderTitle} onChange={(e) => setOrderTitle(e.target.value)} placeholder="order title" />
            <input value={orderAmount} onChange={(e) => setOrderAmount(e.target.value)} placeholder="amount cents" />
            <input value={orderCurrency} onChange={(e) => setOrderCurrency(e.target.value)} placeholder="currency" />
            <button className="action" onClick={() => createEntity("orders_create", "/v1/orders", { workspace_id: workspaceId, title: orderTitle, amount_cents: Number.parseInt(orderAmount || "0", 10), currency: orderCurrency, status: "open", notes: "" }, () => { setOrderTitle(""); setOrderAmount(""); }, listOrders)}>Create</button>
            <button className="action" onClick={listOrders}>Refresh</button>
          </div>
          <div className="row"><input value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)} placeholder="filter orders" /></div>
          <pre>{JSON.stringify(filteredOrders, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Suppliers") {
      return (
        <section className="panel">
          <h2>Suppliers</h2>
          <div className="row">
            <input value={supplierName} onChange={(e) => setSupplierName(e.target.value)} placeholder="supplier name" />
            <input value={supplierContact} onChange={(e) => setSupplierContact(e.target.value)} placeholder="contact name" />
            <input value={supplierEmail} onChange={(e) => setSupplierEmail(e.target.value)} placeholder="contact email" />
            <button
              className="action"
              onClick={() =>
                createEntity(
                  "suppliers_create",
                  "/v1/suppliers",
                  {
                    workspace_id: workspaceId,
                    supplier_name: supplierName,
                    contact_name: supplierContact,
                    contact_email: supplierEmail || null,
                    contact_phone: null,
                    notes: ""
                  },
                  () => {
                    setSupplierName("");
                    setSupplierContact("");
                    setSupplierEmail("");
                  },
                  listSuppliers
                )
              }
            >
              Create
            </button>
            <button className="action" onClick={listSuppliers}>Refresh</button>
          </div>
          <div className="row">
            <input value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} placeholder="filter suppliers" />
            <button className="action" onClick={() => downloadJson(`suppliers-${workspaceId}.json`, filteredSuppliers)}>Export</button>
          </div>
          <pre>{JSON.stringify(filteredSuppliers, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Inventory") {
      return (
        <section className="panel">
          <h2>Inventory</h2>
          <div className="row">
            <input value={inventorySku} onChange={(e) => setInventorySku(e.target.value)} placeholder="SKU" />
            <input value={inventoryName} onChange={(e) => setInventoryName(e.target.value)} placeholder="item name" />
            <input value={inventoryQty} onChange={(e) => setInventoryQty(e.target.value)} placeholder="qty on hand" />
            <input value={inventoryReorder} onChange={(e) => setInventoryReorder(e.target.value)} placeholder="reorder level" />
            <input value={inventoryCost} onChange={(e) => setInventoryCost(e.target.value)} placeholder="unit cost cents" />
          </div>
          <div className="row">
            <select value={inventorySupplierId} onChange={(e) => setInventorySupplierId(e.target.value)}>
              <option value="">no supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>{supplier.supplier_name}</option>
              ))}
            </select>
            <button
              className="action"
              onClick={() =>
                createEntity(
                  "inventory_create",
                  "/v1/inventory",
                  {
                    workspace_id: workspaceId,
                    sku: inventorySku,
                    name: inventoryName,
                    quantity_on_hand: Number.parseInt(inventoryQty || "0", 10),
                    reorder_level: Number.parseInt(inventoryReorder || "0", 10),
                    unit_cost_cents: Number.parseInt(inventoryCost || "0", 10),
                    currency: "USD",
                    supplier_id: inventorySupplierId || null,
                    notes: ""
                  },
                  () => {
                    setInventorySku("");
                    setInventoryName("");
                    setInventoryQty("0");
                    setInventoryReorder("0");
                    setInventoryCost("0");
                    setInventorySupplierId("");
                  },
                  listInventory
                )
              }
            >
              Create
            </button>
            <button className="action" onClick={listSuppliers}>Load Suppliers</button>
            <button className="action" onClick={listInventory}>Refresh Inventory</button>
          </div>
          <div className="row">
            <input value={inventoryFilter} onChange={(e) => setInventoryFilter(e.target.value)} placeholder="filter inventory" />
            <button className="action" onClick={() => downloadJson(`inventory-${workspaceId}.json`, filteredInventory)}>Export</button>
          </div>
          <pre>{JSON.stringify(filteredInventory, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Renderer Lab") {
      return (
        <>
          <section className="panel">
            <h2>Multi-Frame Renderer</h2>
            <p>Programmable structural renderer with independent Python, Cobra, JavaScript, and JSON frames.</p>
            <p>Cobra + Shygazun structure follows `COBRA_SHYGAZUN_SPEC.md` (entity statements + indented lexical attributes).</p>
            <div className="row">
              <button className="action" onClick={stepRendererEngine}>Step Engine Tick</button>
              <button className="action" onClick={emitCobraPlacements}>Emit Cobra Placements</button>
              <button className="action" onClick={() => setRendererEngineStateText(JSON.stringify({ tick: 0, camera: { x: 0, y: 0 } }, null, 2))}>Reset Engine</button>
            </div>
            <div className="renderer-grid">
              <div className="renderer-cell">
                <h3>Python Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererPython} onChange={(e) => setRendererPython(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={pythonFrameDoc} title="python-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>Cobra Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererCobra} onChange={(e) => setRendererCobra(e.target.value)} />
                <div className="row">
                  <span className="badge">{`Lint: ${cobraLintWarnings.length === 0 ? "clean" : `${cobraLintWarnings.length} warning(s)`}`}</span>
                </div>
                {cobraLintWarnings.length > 0 ? (
                  <pre>{JSON.stringify(cobraLintWarnings, null, 2)}</pre>
                ) : null}
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={cobraFrameDoc} title="cobra-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JavaScript Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJs} onChange={(e) => setRendererJs(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={jsFrameDoc} title="js-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JSON Scene Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJson} onChange={(e) => setRendererJson(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={jsonFrameDoc} title="json-renderer" />
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Engine State</h2>
            <div className="row">
              <button className="action" onClick={() => setRendererSimPlaying((prev) => !prev)}>
                {rendererSimPlaying ? "Pause Playtest" : "Start Playtest"}
              </button>
              <input value={rendererSimMs} onChange={(e) => setRendererSimMs(e.target.value)} placeholder="tick ms" />
              <span className="badge">{`Status: ${rendererGameStatus}`}</span>
            </div>
            <textarea className="editor editor-mono renderer-state" value={rendererEngineStateText} onChange={(e) => setRendererEngineStateText(e.target.value)} />
          </section>
          <section className="panel">
            <h2>Game Design Workbench</h2>
            <p>Define scene/systems/entities as Game Spec JSON and compile into renderer layers for playtesting.</p>
            <div className="row">
              <button className="action" onClick={compileGameSpecToRenderer}>Compile Game Spec</button>
              <button className="action" onClick={() => downloadJson("renderer-game-spec.json", rendererGameSpec)}>Export Spec</button>
              <span className="badge">{`Entities: ${rendererGameEntities.length}`}</span>
            </div>
            <div className="row">
              <input value={rendererNewEntityId} onChange={(e) => setRendererNewEntityId(e.target.value)} placeholder="entity id" />
              <input value={rendererNewEntityKind} onChange={(e) => setRendererNewEntityKind(e.target.value)} placeholder="entity kind" />
              <input value={rendererNewEntityX} onChange={(e) => setRendererNewEntityX(e.target.value)} placeholder="x" />
              <input value={rendererNewEntityY} onChange={(e) => setRendererNewEntityY(e.target.value)} placeholder="y" />
              <button className="action" onClick={addEntityToGameSpec}>Add Entity</button>
            </div>
            <textarea
              className="editor editor-mono renderer-game-spec"
              value={rendererGameSpecText}
              onChange={(e) => setRendererGameSpecText(e.target.value)}
              placeholder='{"scene":{"name":"prototype"},"systems":{"gravity":0.0},"entities":[...]}'
            />
          </section>
          <section className="panel">
            <h2>Tile Placement Network</h2>
            <p>
              Tile semantics: <code>Ta</code> present, <code>Zo</code> absent, color vectors <code>Ru..AE</code>, tone
              tokens <code>Ha/Ga/Na/Ung/Wu</code>, connection relation by distance with <code>Ti</code> (near) and
              <code>Ze</code> (far).
            </p>
            <div className="row">
              <input value={tileCols} onChange={(e) => setTileCols(e.target.value)} placeholder="cols" />
              <input value={tileRows} onChange={(e) => setTileRows(e.target.value)} placeholder="rows" />
              <input value={tileCellPx} onChange={(e) => setTileCellPx(e.target.value)} placeholder="cell px" />
              <input value={tileSvgExportScale} onChange={(e) => setTileSvgExportScale(e.target.value)} placeholder="export scale" />
              <button className="action" onClick={() => applyResolutionPreset("SD")}>Preset SD</button>
              <button className="action" onClick={() => applyResolutionPreset("HD")}>Preset HD</button>
              <button className="action" onClick={() => applyResolutionPreset("2K")}>Preset 2K</button>
              <button className="action" onClick={applyAssetGenProfileV1}>Load asset-gen-v1</button>
              <select value={tileActiveLayer} onChange={(e) => setTileActiveLayer(e.target.value)}>
                {tileLayerList.map((layer) => (
                  <option key={layer} value={layer}>{layer}</option>
                ))}
              </select>
              <select value={tilePresenceToken} onChange={(e) => setTilePresenceToken(e.target.value)}>
                <option value="Ta">Ta present</option>
                <option value="Zo">Zo absent</option>
              </select>
              <select value={tileColorToken} onChange={(e) => setTileColorToken(e.target.value)}>
                {["Ru", "Ot", "El", "Ki", "Fu", "Ka", "AE", "Ha", "Ga", "Na", "Ung", "Wu"].map((tok) => (
                  <option key={tok} value={tok}>{tok}</option>
                ))}
              </select>
              <select value={tileOpacityToken} onChange={(e) => setTileOpacityToken(e.target.value)}>
                {["Ha", "Ga", "Na", "Ung", "Wu"].map((tok) => (
                  <option key={tok} value={tok}>{tok}</option>
                ))}
              </select>
              <input value={tileNearThreshold} onChange={(e) => setTileNearThreshold(e.target.value)} placeholder="near threshold" />
              <button className="action" onClick={() => setTileConnectMode((prev) => !prev)}>
                {tileConnectMode ? "Paint Mode" : "Connect Mode"}
              </button>
              <label><input type="checkbox" checked={tileSvgShowGrid} onChange={(e) => setTileSvgShowGrid(e.target.checked)} /> SVG grid</label>
              <label><input type="checkbox" checked={tileSvgShowLinks} onChange={(e) => setTileSvgShowLinks(e.target.checked)} /> SVG links</label>
              <button className="action" onClick={downloadTileSvg}>Export SVG</button>
              <button className="action" onClick={exportAssetManifest}>Export Manifest</button>
              <button className="action" onClick={() => setTileConnections([])}>Clear Links</button>
              <button className="action" onClick={() => setTilePlacements({})}>Clear Tiles</button>
            </div>
            <div className="row">
              <span className="badge">{`Tiles: ${Object.keys(tilePlacements).length}`}</span>
              <span className="badge">{`Links: ${tileConnections.length}`}</span>
              <span className="badge">{`Mode: ${tileConnectMode ? "connect" : "paint"}`}</span>
              <span className="badge">{`Layer: ${tileActiveLayer}`}</span>
              <span className="badge">{`Resolution: ${tileSvgModel.width}x${tileSvgModel.height}`}</span>
              <span className="badge">{`Connect from: ${tileConnectFrom || "none"}`}</span>
              <span className="badge">{`Procedural: ${tileProcStatus}`}</span>
            </div>
            <div className="row">
              <input value={tileProcSeed} onChange={(e) => setTileProcSeed(e.target.value)} placeholder="proc seed" />
              <select value={tileProcTemplate} onChange={(e) => loadProceduralTemplate(e.target.value)}>
                <option value="ring_bloom">Ring Bloom</option>
                <option value="maze_carve">Maze Carve</option>
                <option value="island_chain">Island Chain</option>
                <option value="corridor_grid">Corridor Grid</option>
                <option value="noise_caves">Noise Caves</option>
              </select>
              <button className="action" onClick={() => loadProceduralTemplate(tileProcTemplate)}>Load Template</button>
              <button className="action" onClick={() => setTileProcCode(TILE_PROC_FORM_LIBRARY.ring_bloom)}>Reset Code</button>
              <button className="action" onClick={applyProceduralTiles}>Generate Procedural Form</button>
            </div>
            <div className="row">
              <input value={tilePresetName} onChange={(e) => setTilePresetName(e.target.value)} placeholder="preset name" />
              <button className="action" onClick={saveGenerationPreset}>Save Preset</button>
              <select onChange={(e) => loadGenerationPreset(e.target.value)} defaultValue="">
                <option value="" disabled>load saved preset</option>
                {tileSavedPresets.map((preset) => (
                  <option key={preset.name} value={preset.name}>{preset.name}</option>
                ))}
              </select>
            </div>
            <textarea
              className="editor editor-mono tile-proc-editor"
              value={tileProcCode}
              onChange={(e) => setTileProcCode(e.target.value)}
              placeholder="// return { tiles, links, entities? }"
            />
            <div
              className="tile-grid"
              style={{ gridTemplateColumns: `repeat(${clampInt(tileCols, 1, 128, 48)}, minmax(0, 1fr))` }}
            >
              {tileGridCells.map((cell) => {
                const token = cell.placement ? cell.placement.color_token : "";
                return (
                  <button
                    key={cell.key}
                    className={`tile-cell ${tileConnectFrom === cell.key ? "tile-cell-connect-from" : ""}`}
                    style={{
                      background: cell.placement ? tokenColor(token) : "#faf5eb",
                      color: token === "Ha" || token === "El" || token === "Wu" ? "#111" : "#fff",
                      width: `${tilePreviewCellPx}px`,
                      minHeight: `${tilePreviewCellPx}px`,
                    }}
                    onClick={() => handleTileClick(cell.x, cell.y)}
                    title={`${cell.key}${cell.placement ? ` ${cell.placement.presence_token}/${cell.placement.color_token}/${cell.placement.opacity_token}` : ""}`}
                  >
                    {cell.placement ? cell.placement.color_token : "·"}
                  </button>
                );
              })}
            </div>
            <div className="tile-svg-wrap" dangerouslySetInnerHTML={{ __html: tileSvgMarkup }} />
            <pre>{JSON.stringify({ tiles: tilePlacements, links: tileConnections }, null, 2)}</pre>
          </section>
          <GraphBars
            title="Game Design Metrics"
            items={[
              { label: "Entities", value: rendererGameEntities.length + Object.keys(tilePlacements).length + tileConnections.length },
              {
                label: "Systems",
                value:
                  rendererGameSpec.systems && typeof rendererGameSpec.systems === "object"
                    ? Object.keys(rendererGameSpec.systems).length
                    : 0
              },
              { label: "Tick", value: Number(rendererEngineState.tick || 0) },
              { label: "Snapshots", value: rendererAkinenwunSnapshots.length },
              { label: "Tile Links", value: tileConnections.length }
            ]}
          />
          <section className="panel">
            <h2>Akinenwun Renderer Bridge</h2>
            <p>Load a frontier, inspect graph shape, and pin hash-addressed snapshots for deterministic reuse.</p>
            <div className="row">
              <input value={rendererAkinenwunWord} onChange={(e) => setRendererAkinenwunWord(e.target.value)} placeholder="Akinenwun e.g. TyKoWuVu" />
              <select value={rendererAkinenwunMode} onChange={(e) => setRendererAkinenwunMode(e.target.value)}>
                <option value="prose">Prose mode</option>
                <option value="engine">Engine mode</option>
              </select>
              <button
                className="action"
                onClick={() =>
                  lookupAkinenwun(
                    rendererAkinenwunWord,
                    rendererAkinenwunMode,
                    false,
                    setRendererAkinenwunFrontier,
                    "akinenwun_lookup_renderer"
                  )
                }
              >
                Load Frontier
              </button>
              <button className="action" onClick={pinRendererFrontierSnapshot}>Pin Snapshot</button>
            </div>
            <div className="row">
              <span className="badge">{`Hash: ${rendererAkinenwunFrontier?.frontier_hash || "n/a"}`}</span>
              <span className="badge">{`Snapshots: ${rendererAkinenwunSnapshots.length}`}</span>
            </div>
            <pre>{JSON.stringify(rendererAkinenwunFrontier || {}, null, 2)}</pre>
          </section>
          <GraphBars
            title="Renderer Graph Maker"
            items={[
              { label: "Paths", value: rendererFrontierGraph.stats.paths },
              { label: "Nodes", value: rendererFrontierGraph.stats.nodes },
              { label: "Edges", value: rendererFrontierGraph.stats.edges },
              { label: "Symbols", value: rendererFrontierGraph.stats.symbols }
            ]}
          />
          <section className="panel">
            <h2>Hash-Pinned Snapshots</h2>
            {rendererAkinenwunSnapshots.length === 0 ? (
              <p>No pinned snapshots yet.</p>
            ) : (
              <div className="snapshot-list">
                {rendererAkinenwunSnapshots.map((snapshot) => (
                  <div className="snapshot-row" key={snapshot.hash}>
                    <code>{snapshot.hash}</code>
                    <span>{`${snapshot.akinenwun} [${snapshot.mode}]`}</span>
                    <button className="action" onClick={() => restoreRendererSnapshot(snapshot)}>Restore</button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      );
    }
    if (section === "Graph Maker") {
      return (
        <>
          <section className="panel">
            <h2>Unified Graph Workspace</h2>
            <p>Compose one graph surface from Workshop frontier, Renderer frontier, or a manual frontier payload.</p>
            <div className="row">
              <select value={graphMakerSource} onChange={(e) => setGraphMakerSource(e.target.value)}>
                <option value="workshop">Workshop frontier</option>
                <option value="renderer">Renderer frontier</option>
                <option value="manual">Manual JSON frontier</option>
              </select>
              <button className="action" onClick={promoteGraphMakerToRendererSnapshot}>Promote to Renderer Snapshot</button>
              <button className="action" onClick={() => downloadJson("graph-maker-nodes.json", graphMakerGraph.nodes)}>Export Nodes</button>
              <button className="action" onClick={() => downloadJson("graph-maker-edges.json", graphMakerGraph.edges)}>Export Edges</button>
              <button className="action" onClick={() => downloadJson("graph-maker-frontier.json", graphMakerFrontierResult.frontier || {})}>Export Frontier</button>
            </div>
            {graphMakerSource === "manual" ? (
              <textarea
                className="editor editor-mono graph-maker-editor"
                value={graphMakerManualFrontierText}
                onChange={(e) => setGraphMakerManualFrontierText(e.target.value)}
                placeholder='{"paths":[{"symbols":["Ty","Ko"],"decimals":[0,19],"assembly":{"mode":"prose"}}]}'
              />
            ) : null}
            {graphMakerFrontierResult.error ? <p className="graph-maker-error">{graphMakerFrontierResult.error}</p> : null}
          </section>
          <GraphBars
            title="Graph Maker Summary"
            items={[
              { label: "Paths", value: graphMakerGraph.stats.paths },
              { label: "Nodes", value: graphMakerGraph.stats.nodes },
              { label: "Edges", value: graphMakerGraph.stats.edges },
              { label: "Symbols", value: graphMakerGraph.stats.symbols }
            ]}
          />
          <section className="panel">
            <h2>Nodes</h2>
            <pre>{JSON.stringify(graphMakerGraph.nodes, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>Edges</h2>
            <pre>{JSON.stringify(graphMakerGraph.edges, null, 2)}</pre>
          </section>
        </>
      );
    }
    if (section === "Privacy") {
      return (
        <section className="panel">
          <h2>Privacy Policy Manifest</h2>
          <p>Machine-readable disclosure bundle for app/web/electron/android distribution.</p>
          <div className="row">
            <button className="action" onClick={loadPrivacyManifest}>Load from API</button>
            <button className="action" onClick={() => downloadJson("privacy-policy-manifest.json", privacyManifest || {})}>Export</button>
          </div>
          <pre>{JSON.stringify(privacyManifest || {}, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Commission Hall") {
      return (
        <section className="panel">
          <h2>Public Commission Hall</h2>
          <p>Public surface for published quote visibility and inquiry intake.</p>
          <div className="row"><button className="action" onClick={loadPublicQuotes}>Load Public Quotes</button><button className="action" onClick={() => downloadJson(`public-quotes-${workspaceId}.json`, publicQuotes)}>Export</button></div>
          <div className="row"><input value={publicName} onChange={(e) => setPublicName(e.target.value)} placeholder="your name" /><input value={publicEmail} onChange={(e) => setPublicEmail(e.target.value)} placeholder="your email" /><button className="action" onClick={() => runAction("public_inquiry_create", () => publicApiCall("/public/commission-hall/inquiries", "POST", { workspace_id: workspaceId, full_name: publicName, email: publicEmail || null, details: publicDetails }))}>Submit Inquiry</button></div>
          <div className="row"><input value={publicDetails} onChange={(e) => setPublicDetails(e.target.value)} placeholder="commission details" /></div>
          <pre>{JSON.stringify(publicQuotes, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Temple and Gardens") {
      return <section className="panel"><h2>Frontier Reflection</h2><div className="row"><button className="action" onClick={frontiers}>Load Frontiers</button><button className="action" onClick={observe}>Run Observe</button><button className="action" onClick={timeline}>Timeline</button></div></section>;
    }
    if (section === "Guild Hall") {
      return <section className="panel"><h2>Guild Activity</h2><div className="row"><button className="action" onClick={listLessons}>Refresh Lessons</button><button className="action" onClick={listModules}>Refresh Modules</button></div></section>;
    }
    if (section === "Messages") {
      return <section className="panel"><h2>Messages</h2><div className="row"><input value={messageDraft} onChange={(e) => setMessageDraft(e.target.value)} placeholder="message text" /><button className="action" onClick={() => setMessageLog((prev) => [{ section, text: messageDraft, at: new Date().toISOString() }, ...prev].slice(0, 40))}>Post</button></div><pre>{JSON.stringify(messageLog, null, 2)}</pre></section>;
    }
    if (section === "Studio Hub") {
      return (
        <>
          <section className="panel">
            <h2>Studio Workspace</h2>
            <div className="row">
              <input value={studioFsRoot} onChange={(e) => setStudioFsRoot(e.target.value)} placeholder="cobra scripts folder path" />
              <button className="action" onClick={chooseStudioFsFolder}>Choose Folder</button>
              <button className="action" onClick={refreshStudioFsScripts}>List .cobra</button>
              <button className="action" onClick={importSelectedFsScriptToStudio}>Import Selected</button>
              <button className="action" onClick={saveSelectedStudioFileToFs}>Save Selected</button>
              <button className="action" onClick={exportAllCobraScriptsToFs}>Export All .cobra</button>
            </div>
            <div className="row">
              <select value={studioFsSelectedScript} onChange={(e) => setStudioFsSelectedScript(e.target.value)}>
                <option value="">select .cobra from folder</option>
                {studioFsScripts.map((scriptName) => (
                  <option key={`studio-fs-${scriptName}`} value={scriptName}>{scriptName}</option>
                ))}
              </select>
              <span className="badge">{`Desktop FS: ${hasDesktopFs() ? "available" : "web-only"}`}</span>
              <span className="badge">{`.cobra files: ${studioFsScripts.length}`}</span>
            </div>
            <div className="row">
              <input value={studioNewFolder} onChange={(e) => setStudioNewFolder(e.target.value)} placeholder="new folder name" />
              <button className="action" onClick={createStudioFolder}>Add Folder</button>
            </div>
            <div className="row">
              <select value={studioRenameFolderFrom} onChange={(e) => setStudioRenameFolderFrom(e.target.value)}>
                {studioFolders.map((folder) => (
                  <option key={`rename-${folder}`} value={folder}>{folder}</option>
                ))}
              </select>
              <input value={studioRenameFolderTo} onChange={(e) => setStudioRenameFolderTo(e.target.value)} placeholder="rename folder to" />
              <button className="action" onClick={renameStudioFolder}>Rename Folder</button>
              <button className="action" onClick={duplicateStudioFolder}>Duplicate Folder</button>
            </div>
            <div className="row">
              <select value={studioTargetFolder} onChange={(e) => setStudioTargetFolder(e.target.value)}>
                {studioFolders.map((folder) => (
                  <option key={folder} value={folder}>{folder}</option>
                ))}
              </select>
              <input value={studioNewFileName} onChange={(e) => setStudioNewFileName(e.target.value)} placeholder="new file name" />
              <button className="action" onClick={createStudioFile}>Add File</button>
            </div>
            <div className="studio-grid">
              <aside className="studio-tree">
                {studioFolders.map((folder) => (
                  <div key={folder} className="studio-folder">
                    <strong>{folder}</strong>
                    <div
                      className={`studio-dropzone ${studioDraggedFileId ? "studio-dropzone-active" : ""}`}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        moveFileToFolder(studioDraggedFileId, folder);
                        setStudioDraggedFileId(null);
                      }}
                    >
                      Drop file here to move
                    </div>
                    {studioFiles
                      .filter((file) => file.folder === folder)
                      .map((file) => (
                        <button
                          key={file.id}
                          className={`studio-file ${studioSelectedFileId === file.id ? "studio-file-active" : ""}`}
                          onClick={() => setStudioSelectedFileId(file.id)}
                          draggable
                          onDragStart={() => setStudioDraggedFileId(file.id)}
                          onDragEnd={() => setStudioDraggedFileId(null)}
                        >
                          {file.name}
                        </button>
                      ))}
                  </div>
                ))}
              </aside>
              <div className="studio-editor-wrap">
                <div className="row">
                  <strong>{studioSelectedFile ? `${studioSelectedFile.folder}/${studioSelectedFile.name}` : "No file selected"}</strong>
                </div>
                <div className="row">
                  <input value={studioRenameFileName} onChange={(e) => setStudioRenameFileName(e.target.value)} placeholder="rename selected file" />
                  <button className="action" onClick={renameStudioSelectedFile}>Rename File</button>
                  <select value={studioMoveTargetFolder} onChange={(e) => setStudioMoveTargetFolder(e.target.value)}>
                    {studioFolders.map((folder) => (
                      <option key={`move-${folder}`} value={folder}>{folder}</option>
                    ))}
                  </select>
                  <button className="action" onClick={moveStudioSelectedFile}>Move File</button>
                  <button className="action" onClick={duplicateStudioSelectedFile}>Duplicate File</button>
                </div>
                <div className="row">
                  <button
                    className="action"
                    onClick={() =>
                      downloadJson(`studio-file-${workspaceId}.json`, {
                        file: studioSelectedFile || null
                      })
                    }
                  >
                    Export Current
                  </button>
                  <button className="action" onClick={() => downloadJson(`studio-files-${workspaceId}.json`, studioFiles)}>Export All</button>
                  <button className="action" onClick={deleteStudioSelectedFile}>Delete File</button>
                </div>
                <textarea
                  className={`editor ${studioSelectedFile && studioSelectedFile.name.endsWith(".py") ? "editor-mono" : ""}`}
                  value={studioSelectedFile ? studioSelectedFile.content : ""}
                  onChange={(e) => updateStudioSelectedContent(e.target.value)}
                  placeholder="Select or create a file to begin editing."
                />
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Studio Operations</h2>
            <div className="row">
              <button className="action" onClick={observe}>Sync Kernel State</button>
              <button className="action" onClick={() => downloadJson(`activity-${workspaceId}.json`, activityLog)}>Export Audit</button>
            </div>
            <pre>{JSON.stringify(activityLog, null, 2)}</pre>
          </section>
        </>
      );
    }
    if (section === "Learning Hall") {
      return (
        <section className="panel">
          <h2>Learning Hall</h2>
          <div className="row">
            <button className="action" onClick={listLessons}>Load Lessons</button>
            <button className="action" onClick={listModules}>Load Modules</button>
          </div>
          {filteredLessons.length > 0 ? (
            <div className="lesson-preview">
              <h3>{filteredLessons[0].title}</h3>
              <div className="preview-body">{renderMarkdownBlocks(filteredLessons[0].body || "")}</div>
            </div>
          ) : (
            <p>No lessons loaded yet.</p>
          )}
        </section>
      );
    }
    return <section className="panel"><h2>Tooling</h2><p>Select a section.</p></section>;
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Quantum Quackery Atelier<small>FOYER NAVIGATOR</small></div>
        <div className="nav">{NAV_ITEMS.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => setSection(item)}>{item}</button>)}</div>
      </aside>
      <main className="content">
        <div className="hero">
          <h1>{section}</h1>
          <p>Operational tooling first. Kernel placement remains workshop-gated for verified steward sessions.</p>
          <div className="statusbar">
            <span className="badge">Role: {role}</span>
            <span className="badge">Workspace: {workspaceId}</span>
            <span className="badge">Admin Gate: {adminVerified ? "verified" : "locked"}</span>
            <span className="badge">Artisan Access: {artisanAccessVerified ? "verified" : "locked"}</span>
            <span className="badge">{busyAction ? `Running: ${busyAction}` : notice}</span>
          </div>
        </div>
        <div className="tools-grid">{renderSectionTools()}</div>
        {section === "Workshop" ? (
          <section className="panel">
            <h2>API Output</h2>
            <pre>{output}</pre>
          </section>
        ) : null}
      </main>
    </div>
  );
}


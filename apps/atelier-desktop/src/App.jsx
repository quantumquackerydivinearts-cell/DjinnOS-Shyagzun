import React, { useEffect, useMemo, useRef, useState } from "react";
import sceneGraphDefaults from "../../../scene_graph_defaults.json";
import { consumeInboxBatch } from "./engineInbox";
import { applyRenderPack, createRenderPack, validateRenderPack } from "./rendererCore";
import { GuildHallPanel } from "./panels/GuildHallPanel";
import { MessagesPanel } from "./panels/MessagesPanel";
import { ClientConversationsPanel } from "./panels/ClientConversationsPanel";
import { GuildDMPanel } from "./panels/GuildDMPanel";
import { deriveRendererSettingsFromProjection } from "./shygazunRendererBridge";
import { buildCollisionMap, drawCollisionOverlay, exportCollisionMap } from "./collisionMap";
import { voxelsToGlb, parseGltfFile } from "./gltfBridge";
import { CalculatorPanel } from "./panels/CalculatorPanel";
import { RenderLabPanel } from "./panels/RenderLabPanel";
import { LotusPanel } from "./panels/LotusPanel";
import { AlchemySubjectPanel } from "./panels/AlchemySubjectPanel";
import { ShopManagerPanel } from "./panels/ShopManagerPanel";

function resolveRuntimeApiBase() {
  try {
    const query = new URLSearchParams(window.location.search);
    const queryValue = query.get("apiBase");
    if (queryValue) {
      return queryValue;
    }
  } catch {
  }
  if (import.meta.env.VITE_API_BASE) return import.meta.env.VITE_API_BASE;
  try {
    const proto = window.location.protocol;
    const h = window.location.hostname;
    // Capacitor bundle on Android/iOS: capacitor://localhost or http://localhost
    if (proto === "capacitor:" || (h === "localhost" && proto !== "http:" && proto !== "https:")) {
      return "https://djinnos-shyagzun-atelier-api.onrender.com";
    }
    if (h !== "localhost" && h !== "127.0.0.1" && h !== "") {
      return "https://djinnos-shyagzun-atelier-api.onrender.com";
    }
  } catch {
  }
  return "http://127.0.0.1:9000";
}

const API_BASE = resolveRuntimeApiBase();

function resolveRuntimeKernelBase() {
  try {
    const query = new URLSearchParams(window.location.search);
    const queryValue = query.get("kernelBase");
    if (queryValue) {
      return queryValue;
    }
  } catch {
  }
  if (import.meta.env.VITE_KERNEL_BASE) return import.meta.env.VITE_KERNEL_BASE;
  try {
    const h = window.location.hostname;
    if (h !== "localhost" && h !== "127.0.0.1" && h !== "") {
      return "https://djinnos-shyagzun-kernel.onrender.com";
    }
  } catch {
  }
  return "http://127.0.0.1:8000";
}

const KERNEL_BASE = resolveRuntimeKernelBase();
const WAND_DAMAGE_IMAGE_ACCEPT = ".heic,.heif,.jpg,.jpeg,.png,.webp";
const WAND_DAMAGE_ALLOWED_IMAGE_MIME_TYPES = [
  "image/heic",
  "image/heif",
  "image/jpeg",
  "image/png",
  "image/webp",
];

const PANEL_SLUG_MAP = {
  "consultations":    "Booking System",
  "licenses":         "Orders",
  "catalog":          "Inventory",
  "custom-orders":    "Quotes",
  "digital":          "Orders",
  "land-assessments": "Booking System",
};

function resolveInitialSection() {
  try {
    const q = new URLSearchParams(window.location.search);
    const panel = q.get("panel");
    if (panel) {
      const mapped = PANEL_SLUG_MAP[panel] || panel;
      if (NAV_ITEMS.includes(mapped)) return mapped;
    }
  } catch {}
  return localStorage.getItem("atelier.section") || "Foyer";
}

const NAV_ITEMS = [
  "Foyer",
  "Workshop",
  "Temple and Gardens",
  "Guild Hall",
  "Guild Profiles",
  "Messages",
  "Studio Hub",
  "Asset Library",
  "Kernel Fields",
  "Lesson Creation",
  "Module Creation",
  "Learning Hall",
  "CRM",
  "Booking System",
  "Leads",
  "Clients",
  "Quotes",
  "Orders",
  "Contracts",
  "Ledger",
  "Commission Hall",
  "Suppliers",
  "Inventory",
  "Graph Maker",
  "Business Logic",
  "Renderer Lab",
  "Privacy",
  "Calculator",
  "Lotus",
  "Alchemy Lab",
  "Shop Manager"
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
      "contract.read",
      "contract.write",
      "contract.admin",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write",
      "ledger.read",
      "ledger.write"
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
      "contract.read",
      "contract.write",
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
      "contract.read",
      "contract.write",
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
    "contract.read",
    "supplier.read",
    "inventory.read"
  ];
}

function buildHeaders(role, capsCsv, adminGateToken, artisanId, workshopId, authToken, workspaceId) {
  const headers = {
    "Content-Type": "application/json",
    "X-Atelier-Actor": artisanId || "desktop-user",
    "X-Atelier-Capabilities": capsCsv,
    "X-Artisan-Id": artisanId || "artisan-desktop",
    "X-Artisan-Role": role,
    "X-Workshop-Id": workshopId || "workshop-primary",
    "X-Workshop-Scopes": "scene:*,workspace:*"
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  // Tell the server which workspace to scope to (enables multi-workspace switching).
  if (workspaceId && workspaceId !== "main") {
    headers["X-Workspace-Id"] = workspaceId;
  }
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

function normalizeSummaryValues(value) {
  if (Array.isArray(value)) {
    return value.filter((item) => item !== null && item !== undefined && item !== "");
  }
  if (value === null || value === undefined || value === "") {
    return [];
  }
  return [value];
}

function normalizeProfileText(value, fallback = "") {
  const normalized = String(value || "").trim();
  return normalized || fallback;
}

function buildProfilePayload(profileName, profileEmail, profileTimezone) {
  return {
    profile_name: normalizeProfileText(profileName, "Artisan"),
    profile_email: normalizeProfileText(profileEmail),
    profile_timezone: normalizeProfileText(profileTimezone, "UTC"),
  };
}

function profileIsComplete(profileName, profileEmail) {
  return Boolean(normalizeProfileText(profileName) && normalizeProfileText(profileEmail));
}

function slugProfileIdentity(value, fallback = "artisan") {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ".")
    .replace(/^\.+|\.+$/g, "");
  return normalized || fallback;
}

function deriveProfileMemberId(profileName, profileEmail) {
  const email = normalizeProfileText(profileEmail);
  if (email) {
    const [localPart] = email.split("@");
    return slugProfileIdentity(localPart, "artisan");
  }
  return slugProfileIdentity(profileName, "artisan");
}

function buildShygazunSemanticSummary(projectOutput) {
  if (!projectOutput || typeof projectOutput !== "object") {
    return null;
  }
  const composedFeatures = projectOutput.composed_features;
  if (!composedFeatures || typeof composedFeatures !== "object") {
    return null;
  }
  return {
    chirality: normalizeSummaryValues(composedFeatures.chirality),
    timeTopology: normalizeSummaryValues(composedFeatures.time_topology),
    spaceOperator: normalizeSummaryValues(composedFeatures.space_operator),
    networkRole: normalizeSummaryValues(composedFeatures.network_role),
    clusterRole: normalizeSummaryValues(composedFeatures.cluster_role),
    axis: normalizeSummaryValues(composedFeatures.axis),
    tongueProjection: normalizeSummaryValues(composedFeatures.tongue_projection),
    cannabisMode: normalizeSummaryValues(composedFeatures.cannabis_mode),
    authorityLevel: projectOutput.authoritative_projection?.authority_level || "none",
    trustGrade: projectOutput.trust_contract?.grade || "unknown"
  };
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

function downloadText(filename, text, type = "text/plain") {
  const blob = new Blob([text], { type });
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

class PanelErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error instanceof Error ? error.message : "panel render failed" };
  }

  componentDidCatch(error) {
    // Keep panel failure isolated so the rest of the studio remains usable.
    console.error("panel_error_boundary", error);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.panelKey !== this.props.panelKey && this.state.hasError) {
      this.setState({ hasError: false, message: "" });
    }
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <section className="panel">
        <h2>Panel Recovered</h2>
        <p>{this.state.message || "A panel error was contained."}</p>
        <button className="action" onClick={() => this.setState({ hasError: false, message: "" })}>
          Retry Panel
        </button>
      </section>
    );
  }
}

const BUSINESS_ARCHITECTURE_TEMPLATE = JSON.stringify(
  {
    domains: [
      { id: "crm", name: "CRM", lane: "Business", kind: "domain" },
      { id: "world", name: "World Runtime", lane: "Systems", kind: "domain" },
      { id: "render", name: "Rendering", lane: "Delivery", kind: "domain" }
    ],
    systems: [
      { id: "contacts", name: "Contacts Service", lane: "Systems", kind: "service", domain: "crm" },
      { id: "quests", name: "Headless Quest Engine", lane: "Runtime", kind: "engine", domain: "world" },
      { id: "market", name: "Market Rules", lane: "Runtime", kind: "rules", domain: "world" },
      { id: "renderer", name: "Unified Renderer", lane: "Delivery", kind: "renderer", domain: "render" },
      { id: "db12", name: "12-Layer Store", lane: "Data", kind: "data" }
    ],
    tools: [
      { id: "cobra", name: "Cobra Compiler", lane: "Systems", kind: "tool" },
      { id: "studio", name: "Studio Hub FS", lane: "Data", kind: "tool" }
    ],
    flows: [
      { from: "contacts", to: "db12", label: "persist" },
      { from: "quests", to: "db12", label: "state writes" },
      { from: "market", to: "db12", label: "table updates" },
      { from: "cobra", to: "quests", label: "scripts" },
      { from: "db12", to: "renderer", label: "render state" }
    ]
  },
  null,
  2
);

const RENDERER_TEST_SPEC_FRAGMENTS = [
  {
    id: "room.town_square",
    label: "Room: Town Square",
    spec: {
      renderer_json: {
        scene: { id: "room_town_square", name: "Town Square" },
        voxels: [
          { id: "sq_0", type: "cobble", x: 0, y: 0, z: 0, color: "#7d7f86" },
          { id: "sq_1", type: "cobble", x: 1, y: 0, z: 0, color: "#7d7f86" },
          { id: "sq_2", type: "cobble", x: 0, y: 1, z: 0, color: "#7d7f86" },
          { id: "sq_3", type: "cobble", x: 1, y: 1, z: 0, color: "#7d7f86" },
          { id: "fountain_core", type: "fountain", x: 3, y: 2, z: 1, color: "#8fb8d9" },
        ],
      },
    },
  },
  {
    id: "room.alchemy_lab",
    label: "Room: Alchemy Lab",
    spec: {
      renderer_json: {
        scene: { id: "room_alchemy_lab", name: "Alchemy Lab" },
        voxels: [
          { id: "lab_floor_0", type: "stone", x: 0, y: 0, z: 0, color: "#5e646d" },
          { id: "lab_floor_1", type: "stone", x: 1, y: 0, z: 0, color: "#5e646d" },
          { id: "lab_floor_2", type: "stone", x: 2, y: 0, z: 0, color: "#5e646d" },
          { id: "lab_bench", type: "bench", x: 2, y: 1, z: 1, color: "#6a4b33" },
          { id: "lab_furnace", type: "furnace", x: 4, y: 2, z: 2, color: "#8d5f32" },
          { id: "lab_alembic", type: "alembic", x: 3, y: 1, z: 2, color: "#9ec9d4" },
        ],
      },
    },
  },
  {
    id: "scene.storm_morning",
    label: "Scene: Storm Morning Sky",
    spec: {
      renderer_json: {
        background: { kind: "sky_gradient", top: "#556b7f", bottom: "#1d2e40" },
        meta: { weather: "storm", period: "morning" },
      },
      settings: {
        background: "#1d2e40",
        lighting: { enabled: true, x: 0.28, y: -0.82, z: 0.74, ambient: 0.34, intensity: 0.84 },
      },
    },
  },
  {
    id: "spawn.player_center",
    label: "Spawn: Player Center",
    spec: {
      renderer_json: {
        voxels: [{ id: "player", type: "player", x: 2, y: 2, z: 1, color: "#f6c677", meta: { role: "player" } }],
      },
      controls: {
        player_id: "player",
        follow_player: true,
        keyboard_motion: true,
        click_move: true,
        path_step_ms: 70,
        player_step: 1,
      },
      signal: { player_position: { x: 0, y: 0, z: 0 } },
    },
  },
  {
    id: "set.market_stalls",
    label: "Set: Market Stalls",
    spec: {
      renderer_json: {
        voxels: [
          { id: "stall_a_base", type: "stall", x: 6, y: 1, z: 1, color: "#835f3d" },
          { id: "stall_a_awning", type: "awning", x: 6, y: 1, z: 2, color: "#a63f3f" },
          { id: "stall_b_base", type: "stall", x: 8, y: 2, z: 1, color: "#6f5a44" },
          { id: "stall_b_awning", type: "awning", x: 8, y: 2, z: 2, color: "#c08b3a" },
        ],
      },
    },
  },
  {
    id: "profile.cardinal_hd",
    label: "Profile: Cardinal HD",
    spec: {
      settings: {
        renderMode: "2.5d",
        projection: "cardinal",
        renderScale: 2,
        tile: 28,
        zScale: 10,
        pixelate: false,
        outline: true,
      },
    },
  },
];

const ROOM_KIT_TEMPLATES = [
  {
    room_id: "room.town_square",
    label: "Town Square",
    footprint: { width: 10, height: 8, depth: 3 },
    tags: ["civic", "open", "social"],
    renderer_json: {
      scene: { id: "room_town_square", name: "Town Square" },
      voxels: [
        { id: "sq_0", type: "cobble", x: 0, y: 0, z: 0, color: "#7d7f86" },
        { id: "sq_1", type: "cobble", x: 1, y: 0, z: 0, color: "#7d7f86" },
        { id: "sq_2", type: "cobble", x: 0, y: 1, z: 0, color: "#7d7f86" },
        { id: "sq_3", type: "cobble", x: 1, y: 1, z: 0, color: "#7d7f86" },
        { id: "fountain_core", type: "fountain", x: 3, y: 2, z: 1, color: "#8fb8d9" },
      ],
    },
  },
  {
    room_id: "room.alchemy_lab",
    label: "Alchemy Lab",
    footprint: { width: 8, height: 6, depth: 4 },
    tags: ["craft", "interior", "alchemy"],
    renderer_json: {
      scene: { id: "room_alchemy_lab", name: "Alchemy Lab" },
      voxels: [
        { id: "lab_floor_0", type: "stone", x: 0, y: 0, z: 0, color: "#5e646d" },
        { id: "lab_floor_1", type: "stone", x: 1, y: 0, z: 0, color: "#5e646d" },
        { id: "lab_floor_2", type: "stone", x: 2, y: 0, z: 0, color: "#5e646d" },
        { id: "lab_bench", type: "bench", x: 2, y: 1, z: 1, color: "#6a4b33" },
        { id: "lab_furnace", type: "furnace", x: 4, y: 2, z: 2, color: "#8d5f32" },
        { id: "lab_alembic", type: "alembic", x: 3, y: 1, z: 2, color: "#9ec9d4" },
      ],
    },
  },
];

const FEATURE_KIT_TEMPLATES = [
  {
    feature_id: "feature.scene.storm_morning",
    label: "Storm Morning Sky",
    kind: "scene_overlay",
    scene_patch: {
      background: { kind: "sky_gradient", top: "#556b7f", bottom: "#1d2e40" },
      meta: { weather: "storm", period: "morning" },
    },
    systems_patch: {
      background: "#1d2e40",
      lighting: { enabled: true, x: 0.28, y: -0.82, z: 0.74, ambient: 0.34, intensity: 0.84 },
    },
  },
  {
    feature_id: "feature.spawn.player_center",
    label: "Player Center Spawn",
    kind: "spawn",
    renderer_json: {
      voxels: [{ id: "player", type: "player", x: 2, y: 2, z: 1, color: "#f6c677", meta: { role: "player" } }],
    },
    systems_patch: {
      controls: {
        player_id: "player",
        follow_player: true,
        keyboard_motion: true,
        click_move: true,
        path_step_ms: 70,
        player_step: 1,
      },
    },
    signal_patch: { player_position: { x: 0, y: 0, z: 0 } },
  },
  {
    feature_id: "feature.market_stalls",
    label: "Market Stalls",
    kind: "set_dressing",
    renderer_json: {
      voxels: [
        { id: "stall_a_base", type: "stall", x: 6, y: 1, z: 1, color: "#835f3d" },
        { id: "stall_a_awning", type: "awning", x: 6, y: 1, z: 2, color: "#a63f3f" },
        { id: "stall_b_base", type: "stall", x: 8, y: 2, z: 1, color: "#6f5a44" },
        { id: "stall_b_awning", type: "awning", x: 8, y: 2, z: 2, color: "#c08b3a" },
      ],
    },
  },
  {
    feature_id: "feature.profile.cardinal_hd",
    label: "Cardinal HD Profile",
    kind: "render_profile",
    systems_patch: {
      render_profile: {
        renderMode: "2.5d",
        projection: "cardinal",
        renderScale: 2,
        tile: 28,
        zScale: 10,
        pixelate: false,
        outline: true,
      },
    },
  },
];

const CHUNK_KIT_TEMPLATES = [
  {
    chunk_id: "chunk.market_crossroads",
    label: "Market Crossroads",
    room_refs: [{ room_id: "room.town_square", offset: { x: 0, y: 0, z: 0 } }],
    feature_refs: ["feature.market_stalls"],
    tags: ["outdoor", "market", "hub"],
  },
  {
    chunk_id: "chunk.alchemy_wing",
    label: "Alchemy Wing",
    room_refs: [{ room_id: "room.alchemy_lab", offset: { x: 12, y: 0, z: 0 } }],
    feature_refs: [],
    tags: ["interior", "craft", "lab"],
  },
  {
    chunk_id: "chunk.crossroads_lab",
    label: "Crossroads and Lab",
    room_refs: [
      { room_id: "room.town_square", offset: { x: 0, y: 0, z: 0 } },
      { room_id: "room.alchemy_lab", offset: { x: 12, y: 1, z: 0 } },
    ],
    feature_refs: ["feature.market_stalls"],
    tags: ["mixed", "hub", "craft"],
  },
];

const SCENE_SHELL_TEMPLATES = [
  {
    scene_id: "scene.crossroads_day",
    label: "Crossroads Day",
    scene: { id: "crossroads_day", name: "Crossroads Day", biome: "town" },
    systems: { gravity: 0, camera: { x: 0, y: 0 } },
    tags: ["overworld", "day"],
  },
  {
    scene_id: "scene.alchemy_district",
    label: "Alchemy District",
    scene: { id: "alchemy_district", name: "Alchemy District", biome: "district" },
    systems: { gravity: 0, camera: { x: 4, y: 1 } },
    tags: ["district", "craft"],
  },
];

function parseKitIdSequence(text) {
  return String(text || "")
    .split(/[\s,|/;]+/)
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

function mergeSceneKitPatch(base, patch) {
  const left = base && typeof base === "object" ? base : {};
  const right = patch && typeof patch === "object" ? patch : {};
  const out = { ...left };
  Object.entries(right).forEach(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value) && left[key] && typeof left[key] === "object" && !Array.isArray(left[key])) {
      out[key] = mergeSceneKitPatch(left[key], value);
    } else {
      out[key] = value;
    }
  });
  return out;
}

function offsetSceneKitVoxel(voxel, offset, prefix, extraMeta) {
  const source = voxel && typeof voxel === "object" ? voxel : {};
  const shift = offset && typeof offset === "object" ? offset : {};
  return {
    ...source,
    id: `${prefix}${String(source.id || "voxel")}`,
    x: Number(source.x || 0) + Number(shift.x || 0),
    y: Number(source.y || 0) + Number(shift.y || 0),
    z: Number(source.z || 0) + Number(shift.z || 0),
    meta: mergeSceneKitPatch(source.meta, extraMeta),
  };
}

function composeSceneKitSpec(config) {
  const shellId = String(config.scene_shell_id || "scene.crossroads_day");
  const shell = SCENE_SHELL_TEMPLATES.find((item) => item.scene_id === shellId) || SCENE_SHELL_TEMPLATES[0];
  const roomIds = Array.isArray(config.room_ids) ? config.room_ids : [];
  const chunkIds = Array.isArray(config.chunk_ids) ? config.chunk_ids : [];
  const featureIds = Array.isArray(config.feature_ids) ? config.feature_ids : [];
  const roomById = Object.fromEntries(ROOM_KIT_TEMPLATES.map((item) => [item.room_id, item]));
  const chunkById = Object.fromEntries(CHUNK_KIT_TEMPLATES.map((item) => [item.chunk_id, item]));
  const featureById = Object.fromEntries(FEATURE_KIT_TEMPLATES.map((item) => [item.feature_id, item]));

  const scene = mergeSceneKitPatch(shell.scene, { module_scene_id: shell.scene_id });
  const systems = mergeSceneKitPatch(shell.systems, {});
  const entities = [];
  const rooms = [];
  const chunks = [];
  const features = [];
  const appliedFeatureIds = new Set();

  const attachFeature = (featureId, placementMeta = {}, offset = { x: 0, y: 0, z: 0 }) => {
    const feature = featureById[featureId];
    if (!feature) {
      return;
    }
    const placementKey =
      String(
        placementMeta.source ||
          placementMeta.chunk_id ||
          placementMeta.feature_slot ||
          features.length
      ).replace(/[^\w.-]+/g, "_");
    features.push({ feature_id: feature.feature_id, kind: feature.kind || "feature", ...placementMeta });
    appliedFeatureIds.add(feature.feature_id);
    if (feature.scene_patch) {
      Object.assign(scene, mergeSceneKitPatch(scene, feature.scene_patch));
    }
    if (feature.systems_patch) {
      Object.assign(systems, mergeSceneKitPatch(systems, feature.systems_patch));
    }
    if (feature.signal_patch) {
      systems.signal = mergeSceneKitPatch(systems.signal, feature.signal_patch);
    }
    const voxels = Array.isArray(feature?.renderer_json?.voxels) ? feature.renderer_json.voxels : [];
    voxels.forEach((voxel, index) => {
      entities.push(
        offsetSceneKitVoxel(voxel, offset, `${feature.feature_id.replace(/[^\w.-]+/g, "_")}_${placementKey}_${index}_`, {
          scene_feature: true,
          feature_id: feature.feature_id,
          ...placementMeta,
        })
      );
    });
  };

  const attachRoom = (roomId, offset = { x: 0, y: 0, z: 0 }, context = {}) => {
    const room = roomById[roomId];
    if (!room) {
      return;
    }
    const placementKey =
      String(
        context.source ||
          context.chunk_id ||
          context.chunk_room_index ||
          rooms.length
      ).replace(/[^\w.-]+/g, "_");
    rooms.push({
      room_id: room.room_id,
      offset,
      tags: room.tags || [],
      footprint: room.footprint || null,
      ...context,
    });
    const voxels = Array.isArray(room?.renderer_json?.voxels) ? room.renderer_json.voxels : [];
    voxels.forEach((voxel, index) => {
      entities.push(
        offsetSceneKitVoxel(voxel, offset, `${room.room_id.replace(/[^\w.-]+/g, "_")}_${placementKey}_${index}_`, {
          scene_room: true,
          room_id: room.room_id,
          ...context,
        })
      );
    });
  };

  roomIds.forEach((roomId, index) => {
    attachRoom(roomId, { x: index * 10, y: 0, z: 0 }, { source: "direct_room" });
  });

  chunkIds.forEach((chunkId) => {
    const chunk = chunkById[chunkId];
    if (!chunk) {
      return;
    }
    chunks.push({
      chunk_id: chunk.chunk_id,
      tags: chunk.tags || [],
      room_count: Array.isArray(chunk.room_refs) ? chunk.room_refs.length : 0,
    });
    (Array.isArray(chunk.room_refs) ? chunk.room_refs : []).forEach((roomRef, index) => {
      const offset = roomRef && typeof roomRef === "object" ? roomRef.offset || {} : {};
      attachRoom(String(roomRef.room_id || ""), offset, { chunk_id: chunk.chunk_id, chunk_room_index: index });
    });
    (Array.isArray(chunk.feature_refs) ? chunk.feature_refs : []).forEach((featureId) => {
      attachFeature(String(featureId || ""), { chunk_id: chunk.chunk_id });
    });
  });

  featureIds.forEach((featureId) => attachFeature(featureId, { source: "direct_feature" }));

  return {
    schema: "qqva.scene_kit.v1",
    scene,
    systems,
    entities,
    modules: {
      scene_shell_id: shell.scene_id,
      room_ids,
      chunk_ids,
      feature_ids: Array.from(new Set([...featureIds, ...Array.from(appliedFeatureIds)])),
      rooms,
      chunks,
      features,
    },
    stats: {
      entity_count: entities.length,
      room_count: rooms.length,
      chunk_count: chunks.length,
      feature_count: features.length,
    },
  };
}

function laneRank(lane) {
  const normalized = String(lane || "").trim().toLowerCase();
  if (normalized === "business") {
    return 0;
  }
  if (normalized === "systems") {
    return 1;
  }
  if (normalized === "runtime") {
    return 2;
  }
  if (normalized === "data") {
    return 3;
  }
  if (normalized === "delivery") {
    return 4;
  }
  return 99;
}

function normalizeArchitectureSpec(rawSpec) {
  const spec = rawSpec && typeof rawSpec === "object" ? rawSpec : {};
  const mergedNodes = []
    .concat(Array.isArray(spec.domains) ? spec.domains : [])
    .concat(Array.isArray(spec.systems) ? spec.systems : [])
    .concat(Array.isArray(spec.tools) ? spec.tools : []);
  const nodesMap = {};
  mergedNodes.forEach((rawNode, index) => {
    if (!rawNode || typeof rawNode !== "object") {
      return;
    }
    const id = String(rawNode.id || `node_${index}`);
    nodesMap[id] = {
      id,
      name: String(rawNode.name || rawNode.title || id),
      lane: String(rawNode.lane || "Systems"),
      kind: String(rawNode.kind || "component"),
      domain: rawNode.domain ? String(rawNode.domain) : "",
      description: rawNode.description ? String(rawNode.description) : ""
    };
  });
  const lanes = Object.values(nodesMap)
    .map((node) => node.lane)
    .filter((lane, index, arr) => arr.indexOf(lane) === index)
    .sort((a, b) => {
      const diff = laneRank(a) - laneRank(b);
      return diff !== 0 ? diff : a.localeCompare(b);
    });
  const flows = (Array.isArray(spec.flows) ? spec.flows : [])
    .map((flow, index) => {
      if (!flow || typeof flow !== "object") {
        return null;
      }
      return {
        id: String(flow.id || `flow_${index}`),
        from: String(flow.from || ""),
        to: String(flow.to || ""),
        label: String(flow.label || "")
      };
    })
    .filter((flow) => flow && nodesMap[flow.from] && nodesMap[flow.to]);
  return {
    lanes,
    nodes: Object.values(nodesMap),
    flows
  };
}

function deriveBusinessArchitectureSpec(rendererTables, rendererPipeline, studioFiles) {
  const tableKeys = rendererTables && typeof rendererTables === "object" ? Object.keys(rendererTables) : [];
  const domains = [
    { id: "crm", name: "Business Domain", lane: "Business", kind: "domain" },
    { id: "runtime", name: "Runtime Domain", lane: "Runtime", kind: "domain" },
    { id: "delivery", name: "Delivery Domain", lane: "Delivery", kind: "domain" }
  ];
  const systems = [
    { id: "atelier_api", name: "Atelier API", lane: "Systems", kind: "service", domain: "crm" },
    { id: "kernel", name: "Shygazun Kernel", lane: "Runtime", kind: "engine", domain: "runtime" },
    { id: "renderer", name: "Unified Renderer", lane: "Delivery", kind: "renderer", domain: "delivery" },
    { id: "table_store", name: "State Tables", lane: "Data", kind: "data", description: tableKeys.join(", ") }
  ];
  const tools = [
    { id: "cobra", name: "Cobra Compiler", lane: "Systems", kind: "tool" },
    { id: "studio_fs", name: `Studio Files (${Array.isArray(studioFiles) ? studioFiles.length : 0})`, lane: "Data", kind: "tool" },
    { id: "pipeline", name: "Renderer Pipeline", lane: "Systems", kind: "tool", description: rendererPipeline && rendererPipeline.mode ? String(rendererPipeline.mode) : "" }
  ];
  const flows = [
    { from: "atelier_api", to: "table_store", label: "business writes" },
    { from: "kernel", to: "table_store", label: "runtime writes" },
    { from: "cobra", to: "kernel", label: "script compile" },
    { from: "table_store", to: "renderer", label: "render state" },
    { from: "studio_fs", to: "cobra", label: "script source" },
    { from: "pipeline", to: "renderer", label: "material pass" }
  ];
  return { domains, systems, tools, flows };
}

function architectureNodeColor(kind) {
  const k = String(kind || "").toLowerCase();
  if (k === "domain") {
    return "#2f4f9d";
  }
  if (k === "service") {
    return "#266d56";
  }
  if (k === "engine" || k === "rules") {
    return "#6f4b1f";
  }
  if (k === "data") {
    return "#5e2b69";
  }
  if (k === "renderer") {
    return "#25416b";
  }
  if (k === "tool") {
    return "#4a4f57";
  }
  return "#3f4754";
}

function drawBusinessArchitecture(canvas, model) {
  if (!canvas || !model) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }
  const width = Math.max(960, Math.floor(canvas.clientWidth || 960));
  const height = Math.max(420, Math.floor(canvas.clientHeight || 420));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  ctx.clearRect(0, 0, width, height);
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#0b0e12");
  gradient.addColorStop(1, "#101722");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  const lanes = Array.isArray(model.lanes) && model.lanes.length ? model.lanes : ["Systems"];
  const laneW = width / lanes.length;
  const lanePadding = 14;
  lanes.forEach((lane, laneIndex) => {
    const x = Math.floor(laneIndex * laneW);
    ctx.fillStyle = laneIndex % 2 === 0 ? "rgba(255,255,255,0.025)" : "rgba(255,255,255,0.04)";
    ctx.fillRect(x, 0, Math.ceil(laneW), height);
    ctx.fillStyle = "#d6dce6";
    ctx.font = "600 12px ui-sans-serif";
    ctx.fillText(lane, x + lanePadding, 20);
  });
  const nodesByLane = {};
  lanes.forEach((lane) => {
    nodesByLane[lane] = model.nodes.filter((node) => node.lane === lane);
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
  ctx.strokeStyle = "rgba(176,196,222,0.45)";
  ctx.lineWidth = 1.25;
  model.flows.forEach((flow) => {
    const from = coords[flow.from];
    const to = coords[flow.to];
    if (!from || !to) {
      return;
    }
    const x1 = from.x + from.w;
    const y1 = from.y + from.h / 2;
    const x2 = to.x;
    const y2 = to.y + to.h / 2;
    const cx = (x1 + x2) / 2;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(cx, y1, cx, y2, x2, y2);
    ctx.stroke();
    if (flow.label) {
      ctx.fillStyle = "rgba(210,220,235,0.92)";
      ctx.font = "11px ui-sans-serif";
      ctx.fillText(flow.label, cx + 6, (y1 + y2) / 2 - 4);
    }
  });
  model.nodes.forEach((node) => {
    const box = coords[node.id];
    if (!box) {
      return;
    }
    ctx.fillStyle = architectureNodeColor(node.kind);
    ctx.strokeStyle = "rgba(255,255,255,0.16)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(box.x, box.y, box.w, box.h, 10);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#f4f7fb";
    ctx.font = "600 12px ui-sans-serif";
    ctx.fillText(node.name, box.x + 10, box.y + 22);
    ctx.fillStyle = "rgba(242,247,252,0.86)";
    ctx.font = "11px ui-sans-serif";
    ctx.fillText(`${node.kind}${node.domain ? ` · ${node.domain}` : ""}`, box.x + 10, box.y + 40);
    if (node.description) {
      const clipped = node.description.length > 44 ? `${node.description.slice(0, 44)}...` : node.description;
      ctx.fillStyle = "rgba(220,230,240,0.8)";
      ctx.fillText(clipped, box.x + 10, box.y + 56);
    }
  });
}

function architectureModelToVoxels(model) {
  const lanes = Array.isArray(model?.lanes) ? model.lanes : [];
  const nodes = Array.isArray(model?.nodes) ? model.nodes : [];
  const laneIndex = {};
  lanes.forEach((lane, index) => {
    laneIndex[lane] = index;
  });
  const rowByLane = {};
  return nodes.map((node, index) => {
    const lane = String(node.lane || "Systems");
    const x = Number.isFinite(Number(laneIndex[lane])) ? Number(laneIndex[lane]) * 4 + 2 : (index % 6) * 2;
    const row = Number.isFinite(Number(rowByLane[lane])) ? Number(rowByLane[lane]) : 0;
    rowByLane[lane] = row + 1;
    const y = row * 2 + 2;
    const kind = String(node.kind || "component");
    const z =
      kind === "domain"
        ? 3
        : kind === "data"
          ? 1
          : kind === "renderer"
            ? 2
            : 0;
    return {
      x,
      y,
      z,
      type: kind,
      meta: {
        id: String(node.id || `node_${index}`),
        label: String(node.name || node.id || `node_${index}`),
        lane
      }
    };
  });
}

function parseArchitectureEnglish(text) {
  const domains = [];
  const systems = [];
  const tools = [];
  const flows = [];
  String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .forEach((line, index) => {
      const flowMatch = line.match(/^flow\s+([A-Za-z0-9_.-]+)\s*->\s*([A-Za-z0-9_.-]+)(?:\s*:\s*(.+))?$/i);
      if (flowMatch) {
        flows.push({ from: flowMatch[1], to: flowMatch[2], label: String(flowMatch[3] || "") });
        return;
      }
      const domainMatch = line.match(/^domain\s+([A-Za-z0-9_.-]+)(?:\s*:\s*(.+))?$/i);
      if (domainMatch) {
        domains.push({ id: domainMatch[1], name: String(domainMatch[2] || domainMatch[1]), lane: "Business", kind: "domain" });
        return;
      }
      const toolMatch = line.match(/^tool\s+([A-Za-z0-9_.-]+)(?:\s*:\s*(.+))?$/i);
      if (toolMatch) {
        tools.push({ id: toolMatch[1], name: String(toolMatch[2] || toolMatch[1]), lane: "Systems", kind: "tool" });
        return;
      }
      const systemMatch = line.match(/^system\s+([A-Za-z0-9_.-]+)(?:\s+in\s+([A-Za-z0-9_.-]+))?(?:\s*:\s*(.+))?$/i);
      if (systemMatch) {
        systems.push({
          id: systemMatch[1],
          domain: String(systemMatch[2] || ""),
          name: String(systemMatch[3] || systemMatch[1]),
          lane: "Runtime",
          kind: "service"
        });
        return;
      }
      systems.push({
        id: `line_${index}`,
        name: line,
        lane: "Runtime",
        kind: "service"
      });
    });
  return { domains, systems, tools, flows };
}

function parseArchitectureCobra(text) {
  const domains = [];
  const systems = [];
  const tools = [];
  const flows = [];
  let lastEntityId = "";
  String(text || "")
    .split(/\r?\n/)
    .forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) {
        return;
      }
      const tokens = line.split(/\s+/);
      const head = String(tokens[0] || "").toLowerCase();
      if (head === "domain" && tokens[1]) {
        domains.push({ id: tokens[1], name: tokens.slice(2).join(" ") || tokens[1], lane: "Business", kind: "domain" });
        return;
      }
      if (head === "system" && tokens[1]) {
        systems.push({
          id: tokens[1],
          name: tokens.slice(2).join(" ") || tokens[1],
          lane: "Runtime",
          kind: "service"
        });
        return;
      }
      if (head === "tool" && tokens[1]) {
        tools.push({ id: tokens[1], name: tokens.slice(2).join(" ") || tokens[1], lane: "Systems", kind: "tool" });
        return;
      }
      if (head === "entity" && tokens[1]) {
        const entityId = String(tokens[1]);
        const entityKind = String(tokens[4] || "entity");
        systems.push({
          id: entityId,
          name: `${entityId} (${entityKind})`,
          lane: "Runtime",
          kind: "service",
          description: `entity ${tokens.slice(1).join(" ")}`
        });
        if (lastEntityId) {
          flows.push({ from: lastEntityId, to: entityId, label: "placement order" });
        }
        lastEntityId = entityId;
        return;
      }
      if (head === "flow" && tokens[1] && tokens[2]) {
        if (tokens[2] === "->" && tokens[3]) {
          flows.push({
            from: tokens[1],
            to: tokens[3],
            label: tokens.slice(4).join(" ").replace(/^:\s*/, "")
          });
          return;
        }
        flows.push({
          from: tokens[1],
          to: tokens[2],
          label: tokens.slice(3).join(" ")
        });
      }
    });
  return { domains, systems, tools, flows };
}

function parseArchitectureShygazun(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
  const domains = [];
  const systems = [];
  const tools = [];
  const flows = [];
  lines.forEach((line, index) => {
    const tokens = line.split(/\s+/);
    const lead = String(tokens[0] || "").toLowerCase();
    if (lead === "ty" || lead === "tykowuvu" || lead === "domain") {
      const id = String(tokens[1] || `domain_${index}`);
      domains.push({ id, name: tokens.slice(2).join(" ") || id, lane: "Business", kind: "domain" });
      return;
    }
    if (lead === "wu" || lead === "tashamowun" || lead === "system") {
      const id = String(tokens[1] || `system_${index}`);
      systems.push({ id, name: tokens.slice(2).join(" ") || id, lane: "Runtime", kind: "service" });
      return;
    }
    if (lead === "fi" || lead === "tool") {
      const id = String(tokens[1] || `tool_${index}`);
      tools.push({ id, name: tokens.slice(2).join(" ") || id, lane: "Systems", kind: "tool" });
      return;
    }
    if ((lead === "ru" || lead === "flow") && tokens[1] && tokens[2]) {
      flows.push({ from: tokens[1], to: tokens[2], label: tokens.slice(3).join(" ") });
      return;
    }
    systems.push({ id: `shy_${index}`, name: line, lane: "Runtime", kind: "service" });
  });
  return { domains, systems, tools, flows };
}

function parseArchitectureInput(mode, text) {
  const normalized = String(mode || "json").toLowerCase();
  if (normalized === "json") {
    return parseObjectJson(text, {});
  }
  if (normalized === "english") {
    return parseArchitectureEnglish(text);
  }
  if (normalized === "cobra") {
    return parseArchitectureCobra(text);
  }
  if (normalized === "shygazun") {
    return parseArchitectureShygazun(text);
  }
  return parseObjectJson(text, {});
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeRulePayload(payload, workspaceId, actorId) {
  if (!isPlainObject(payload) || Object.keys(payload).length === 0) {
    return null;
  }
  const normalized = { ...payload };
  if (!normalized.workspace_id) {
    normalized.workspace_id = workspaceId;
  }
  if (!normalized.actor_id) {
    normalized.actor_id = actorId;
  }
  return normalized;
}

function mergeRendererTables(localTables, apiTables, precedence) {
  const local = isPlainObject(localTables) ? localTables : {};
  const api = isPlainObject(apiTables) ? apiTables : {};
  const merged = precedence === "api_over_local" ? { ...local, ...api } : { ...api, ...local };
  ["vitriol", "market", "alchemy", "blacksmith", "perks", "skills", "levels"].forEach((key) => {
    const localLayer = isPlainObject(local[key]) ? local[key] : null;
    const apiLayer = isPlainObject(api[key]) ? api[key] : null;
    if (!localLayer && !apiLayer) {
      return;
    }
    merged[key] =
      precedence === "api_over_local"
        ? { ...(localLayer || {}), ...(apiLayer || {}) }
        : { ...(apiLayer || {}), ...(localLayer || {}) };
  });
  return merged;
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
        meta: {}
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
  const toHex = (rgb) => `#${byteToHex(rgb.r)}${byteToHex(rgb.g)}${byteToHex(rgb.b)}`;
  const shiftToward = (hex, target, factor) => {
    const rgb = parseHexColor(hex);
    if (!rgb) {
      return "#607d8b";
    }
    return toHex({
      r: Math.round(rgb.r + ((target.r - rgb.r) * factor)),
      g: Math.round(rgb.g + ((target.g - rgb.g) * factor)),
      b: Math.round(rgb.b + ((target.b - rgb.b) * factor)),
    });
  };
  const resolveSingle = (raw) => {
    const exact = String(raw || "").trim();
    if (ROSE_COLOR_MAP[exact]) {
      return ROSE_COLOR_MAP[exact];
    }
    if (ASTER_LEFT_CHIRAL_TOKENS[exact]) {
      return shiftToward(ROSE_COLOR_MAP[ASTER_LEFT_CHIRAL_TOKENS[exact]], { r: 0, g: 0, b: 0 }, 0.32);
    }
    if (ASTER_RIGHT_CHIRAL_TOKENS[exact]) {
      return shiftToward(ROSE_COLOR_MAP[ASTER_RIGHT_CHIRAL_TOKENS[exact]], { r: 255, g: 255, b: 255 }, 0.28);
    }
    return "";
  };
  const direct = resolveSingle(token);
  if (direct) {
    return direct;
  }
  const normalized = String(token || "").trim();
  if (!normalized) {
    return "#607d8b";
  }
  const source = normalized.replace(/[^A-Za-z]/g, "");
  const units = ["Ung", "Alz", "Oth", "Tho", "AE", "Ru", "Ot", "El", "Ki", "Fu", "Ka", "Ha", "Ga", "Na", "Wu", "Ry", "Ra", "Le", "Lu", "Gi", "Ge", "Fe", "Fo", "Ky", "Kw", "Dr"];
  const parts = [];
  let offset = 0;
  while (offset < source.length) {
    let matched = "";
    for (const unit of units) {
      if (source.startsWith(unit, offset)) {
        matched = unit;
        break;
      }
    }
    if (!matched) {
      return "#607d8b";
    }
    parts.push(matched);
    offset += matched.length;
  }
  if (parts.length <= 1) {
    return resolveSingle(parts[0]) || "#607d8b";
  }
  const rgbs = parts.map((part) => parseHexColor(resolveSingle(part))).filter(Boolean);
  if (rgbs.length === 0) {
    return "#607d8b";
  }
  const mixed = {
    r: Math.round(rgbs.reduce((sum, item) => sum + item.r, 0) / rgbs.length),
    g: Math.round(rgbs.reduce((sum, item) => sum + item.g, 0) / rgbs.length),
    b: Math.round(rgbs.reduce((sum, item) => sum + item.b, 0) / rgbs.length),
  };
  return `#${byteToHex(mixed.r)}${byteToHex(mixed.g)}${byteToHex(mixed.b)}`;
}

function parseHexColor(value) {
  const text = String(value || "").trim();
  const m = /^#?([0-9a-fA-F]{6})$/.exec(text);
  if (!m) {
    return null;
  }
  const raw = m[1];
  return {
    r: Number.parseInt(raw.slice(0, 2), 16),
    g: Number.parseInt(raw.slice(2, 4), 16),
    b: Number.parseInt(raw.slice(4, 6), 16),
  };
}

function byteToHex(value) {
  return Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, "0");
}

function stylizeVoxelColor(hex, style) {
  const mode = String(style || "default");
  if (mode === "pokemon_ds") {
    const rgb = parseHexColor(hex);
    if (!rgb) {
      return hex;
    }
    const q = 32;
    let r = Math.round(rgb.r / q) * q;
    let g = Math.round(rgb.g / q) * q;
    let b = Math.round(rgb.b / q) * q;
    const avg = (r + g + b) / 3;
    if (avg < 84) {
      r += 14;
      g += 14;
      b += 14;
    }
    if (avg > 212) {
      r -= 8;
      g -= 8;
      b -= 8;
    }
    return `#${byteToHex(r)}${byteToHex(g)}${byteToHex(b)}`;
  }
  if (mode === "classic_fallout") {
    const rgb = parseHexColor(hex);
    if (!rgb) {
      return hex;
    }
    const luma = 0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b;
    const olive = {
      r: Math.max(0, Math.min(255, luma * 0.78 + 28)),
      g: Math.max(0, Math.min(255, luma * 0.9 + 34)),
      b: Math.max(0, Math.min(255, luma * 0.62 + 12)),
    };
    const q = 24;
    const r = Math.round(olive.r / q) * q;
    const g = Math.round(olive.g / q) * q;
    const b = Math.round(olive.b / q) * q;
    return `#${byteToHex(r)}${byteToHex(g)}${byteToHex(b)}`;
  }
  if (mode === "pokemon_g45") {
    const rgb = parseHexColor(hex);
    if (!rgb) {
      return hex;
    }
    const q = 16;
    let r = Math.round(rgb.r / q) * q;
    let g = Math.round(rgb.g / q) * q;
    let b = Math.round(rgb.b / q) * q;
    const luma = 0.299 * r + 0.587 * g + 0.114 * b;
    if (luma < 74) {
      r += 18;
      g += 18;
      b += 18;
    } else if (luma > 212) {
      r -= 10;
      g -= 10;
      b -= 10;
    }
    return `#${byteToHex(r)}${byteToHex(g)}${byteToHex(b)}`;
  }
  if (mode === "pixel_voxel_hybrid") {
    const rgb = parseHexColor(hex);
    if (!rgb) {
      return hex;
    }
    const q = 20;
    let r = Math.round(rgb.r / q) * q;
    let g = Math.round(rgb.g / q) * q;
    let b = Math.round(rgb.b / q) * q;
    // Slightly bias toward readable midtones so pixel clusters stay legible.
    const luma = 0.299 * r + 0.587 * g + 0.114 * b;
    if (luma < 72) {
      r += 14;
      g += 14;
      b += 14;
    } else if (luma > 220) {
      r -= 10;
      g -= 10;
      b -= 10;
    }
    return `#${byteToHex(r)}${byteToHex(g)}${byteToHex(b)}`;
  }
  if (mode !== "default") {
    return hex;
  }
  return hex;
}

function isHighFidelityStyle(style) {
  return String(style || "").toLowerCase() === "pokemon_g45";
}

function isHybridPixelVoxelStyle(style) {
  return String(style || "").toLowerCase() === "pixel_voxel_hybrid";
}

function nearestTokenForColor(hex) {
  const rgb = parseHexColor(hex);
  if (!rgb) {
    return "Ru";
  }
  const tokens = ROSE_COLOR_TOKENS;
  let bestToken = tokens[0];
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const token of tokens) {
    const sample = parseHexColor(tokenColor(token));
    if (!sample) {
      continue;
    }
    const d =
      (rgb.r - sample.r) * (rgb.r - sample.r) +
      (rgb.g - sample.g) * (rgb.g - sample.g) +
      (rgb.b - sample.b) * (rgb.b - sample.b);
    if (d < bestDistance) {
      bestDistance = d;
      bestToken = token;
    }
  }
  return bestToken;
}

const ROSE_COLOR_TOKENS = ["Ru", "Ot", "El", "Ki", "Fu", "Ka", "AE", "Ha", "Ga", "Na", "Ung", "Wu"];

const ROSE_COLOR_MAP = {
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

const ASTER_LEFT_CHIRAL_TOKENS = {
  Ra: "Ru",
  Tho: "Ot",
  Lu: "El",
  Ge: "Ki",
  Fo: "Fu",
  Kw: "Ka",
  Dr: "AE",
};

const ASTER_RIGHT_CHIRAL_TOKENS = {
  Ry: "Ru",
  Oth: "Ot",
  Le: "El",
  Gi: "Ki",
  Fe: "Fu",
  Ky: "Ka",
  Alz: "AE",
};

const ASTER_RIGHT_TOKENS = Object.keys(ASTER_RIGHT_CHIRAL_TOKENS);
const ASTER_LEFT_TOKENS = Object.keys(ASTER_LEFT_CHIRAL_TOKENS);

const ROSE_COLOR_COMBINATION_PRESETS = [
  { label: "Light Brown", value: "RuOtKi" },
  { label: "Tan", value: "OtElKi" },
  { label: "Moss", value: "KiFuEl" },
  { label: "Rust", value: "RuOtGa" },
  { label: "Slate", value: "KaFuNa" },
  { label: "Ash", value: "GaNaWu" },
  { label: "Rosewood", value: "RuKaOt" },
  { label: "Bruised Plum", value: "KaAERu" },
];

function clampNumber(value, min, max, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, n));
}

const DAISY_TONGUE_ROWS = [
  { symbol: "Lo", meaning: "Segments / Identity" },
  { symbol: "Yei", meaning: "Component / Integrator" },
  { symbol: "Ol", meaning: "Deadzone / Relative Void" },
  { symbol: "X", meaning: "Joint / Interlock" },
  { symbol: "Yx", meaning: "Fulcrum / Crux" },
  { symbol: "Go", meaning: "Plug / Blocker" },
  { symbol: "Foa", meaning: "Degree / Space" },
  { symbol: "Oy", meaning: "Depths / Layers" },
  { symbol: "W", meaning: "Freefall / Socket Space" },
  { symbol: "Th", meaning: "Cuff / Indentation" },
  { symbol: "Kael", meaning: "Cluster / Fruit / Flower" },
  { symbol: "Ro", meaning: "Ion-channel / Gate / Receptor" },
  { symbol: "Gl", meaning: "Membrane / Muscle" },
  { symbol: "To", meaning: "Scaffold / Framework" },
  { symbol: "Ma", meaning: "Web / Interchange" },
  { symbol: "Ne", meaning: "Network / System" },
  { symbol: "Ym", meaning: "Radial Space" },
  { symbol: "Nz", meaning: "Switch / Circuit Actuator" },
  { symbol: "Sho", meaning: "Valve / Fluid Actuator" },
  { symbol: "Hi", meaning: "Lever / Radial Actuator" },
  { symbol: "Mh", meaning: "Bond" },
  { symbol: "Zhi", meaning: "Eye / Vortex" },
  { symbol: "Vr", meaning: "Rotor / Tensor" },
  { symbol: "St", meaning: "Surface" },
  { symbol: "Fn", meaning: "Passage / Pathway" },
  { symbol: "N", meaning: "Seed / Sheet / Fiber" },
];

const DAISY_TONGUE_SYMBOLS = DAISY_TONGUE_ROWS.map((row) => row.symbol);

const SAKURA_TONGUE_ROWS = [
  { symbol: "Jy", meaning: "Top" },
  { symbol: "Ji", meaning: "Starboard" },
  { symbol: "Ja", meaning: "Front" },
  { symbol: "Jo", meaning: "Back" },
  { symbol: "Je", meaning: "Port" },
  { symbol: "Ju", meaning: "Bottom" },
  { symbol: "Dy", meaning: "Hence / Heretofore" },
  { symbol: "Di", meaning: "Traveling / Distancing" },
  { symbol: "Da", meaning: "Meeting / Conjoined" },
  { symbol: "Do", meaning: "Parting / Divorced" },
  { symbol: "De", meaning: "Domesticating / Staying" },
  { symbol: "Du", meaning: "Whither / Status of" },
  { symbol: "By", meaning: "When-hence / Eventual" },
  { symbol: "Bi", meaning: "Crowned / Owning" },
  { symbol: "Ba", meaning: "Plain / Explicit" },
  { symbol: "Bo", meaning: "Hidden / Occulted" },
  { symbol: "Be", meaning: "Common / Outer / Wild" },
  { symbol: "Bu", meaning: "Since / Relational" },
  { symbol: "Va", meaning: "Order / Structure / Life" },
  { symbol: "Vo", meaning: "Chaos / Boundary-breakage / Mutation" },
  { symbol: "Ve", meaning: "Pieces / Not-wherever / Where" },
  { symbol: "Vu", meaning: "Death-moment / Never / Now" },
  { symbol: "Vi", meaning: "Body / Wherever / What" },
  { symbol: "Vy", meaning: "Lifespan / Whenever / How" },
];

const SAKURA_TONGUE_SYMBOLS = SAKURA_TONGUE_ROWS.map((row) => row.symbol);

const SAKURA_BELONGING_CHAIN_PRESETS = [
  { label: "Embodied Order", value: "Va > Vi" },
  { label: "Spiritual Lifespan", value: "Va > Vy" },
  { label: "Relational Belonging", value: "Bu > Bi > Vi" },
  { label: "Wild Pieces", value: "Be > Ve" },
  { label: "Occult Body", value: "Bo > Vi" },
  { label: "Eventual Dissolution", value: "By > Vu" },
];

function parseDaisySymbolSequence(text) {
  const raw = String(text || "");
  const parts = raw
    .split(/[\s,|/;]+/)
    .map((item) => item.trim())
    .filter((item) => item !== "");
  const seen = new Set();
  const out = [];
  for (const symbol of parts) {
    if (!DAISY_TONGUE_SYMBOLS.includes(symbol)) {
      continue;
    }
    if (seen.has(symbol)) {
      continue;
    }
    seen.add(symbol);
    out.push(symbol);
  }
  return out;
}

function parseSakuraBelongingChain(text) {
  const raw = String(text || "");
  if (!raw.trim()) {
    return [];
  }
  return raw
    .split(/[>\s,|/;]+/)
    .map((item) => item.trim())
    .filter((item) => item !== "" && SAKURA_TONGUE_SYMBOLS.includes(item));
}

function formatSakuraBelongingChain(chain) {
  return parseSakuraBelongingChain(Array.isArray(chain) ? chain.join(" > ") : String(chain || "")).join(" > ");
}

function buildDaisyRoleComposition(archetype, symmetry, allowedSymbols) {
  const allow = Array.isArray(allowedSymbols) && allowedSymbols.length > 0 ? allowedSymbols : DAISY_TONGUE_SYMBOLS;
  const has = new Set(allow);
  const pick = (candidates, fallback) => {
    for (const symbol of candidates) {
      if (has.has(symbol)) {
        return symbol;
      }
    }
    if (has.has(fallback)) {
      return fallback;
    }
    return allow[0];
  };
  const actuatorByArchetype =
    archetype === "serpentine"
      ? ["Sho", "Nz", "Hi"]
      : archetype === "avian"
      ? ["Hi", "Nz", "Sho"]
      : archetype === "beast"
      ? ["Nz", "Hi", "Sho"]
      : ["Nz", "Sho", "Hi"];
  const spatialBySymmetry = symmetry === "radial" ? ["Ym", "Foa", "Oy"] : ["Foa", "Oy", "Ym"];
  return {
    identity: pick(["Lo", "N"], "Lo"),
    integrator: pick(["Yei", "Ne"], "Yei"),
    framework: pick(["To", "Ma"], "To"),
    network: pick(["Ne", "Ma"], "Ne"),
    membrane: pick(["Gl", "St"], "Gl"),
    surface: pick(["St", "Gl"], "St"),
    passage: pick(["Fn", "Ro"], "Fn"),
    joint: pick(["X", "Yx"], "X"),
    fulcrum: pick(["Yx", "X"], "Yx"),
    bond: pick(["Mh", "Go"], "Mh"),
    gateway: pick(["Ro", "Fn"], "Ro"),
    cluster: pick(["Kael", "N"], "Kael"),
    depth: pick(["Oy", "Foa"], "Oy"),
    spatial: pick(spatialBySymmetry, "Foa"),
    actuator_primary: pick(actuatorByArchetype, "Nz"),
    seed: pick(["N", "Lo"], "N"),
  };
}

function sanitizeDaisyRoleOverrides(overrides, allowedSymbols, baseComposition) {
  const out = {};
  if (!overrides || typeof overrides !== "object") {
    return out;
  }
  const allowedSet = new Set(Array.isArray(allowedSymbols) ? allowedSymbols : []);
  const allowedKeys = new Set(Object.keys(baseComposition || {}));
  for (const [key, value] of Object.entries(overrides)) {
    if (!allowedKeys.has(String(key))) {
      continue;
    }
    const symbol = String(value || "").trim();
    if (symbol === "") {
      continue;
    }
    if (allowedSet.size > 0 && !allowedSet.has(symbol)) {
      continue;
    }
    out[String(key)] = symbol;
  }
  return out;
}

function buildDaisyBodyplanSpec(config) {
  const systemId = String(config.system_id || "daisy.system.alpha");
  const archetype = String(config.archetype || "humanoid");
  const symmetry = String(config.symmetry || "bilateral");
  const segmentCount = Math.round(clampNumber(config.segment_count, 1, 24, 7));
  const limbPairs = Math.round(clampNumber(config.limb_pairs, 0, 8, 2));
  const coreToken = String(config.core_token || "Ki");
  const accentToken = String(config.accent_token || "Fu");
  const coreBelongingChain = parseSakuraBelongingChain(config.core_belonging_chain);
  const accentBelongingChain = parseSakuraBelongingChain(config.accent_belonging_chain);
  const seed = Math.round(clampNumber(config.seed, 0, 999999, 42));
  const useWholeTongue = Boolean(config.use_whole_tongue ?? true);
  const customSymbols = Array.isArray(config.daisy_symbols) ? config.daisy_symbols.map((s) => String(s)) : [];
  const allowedSymbols =
    useWholeTongue || customSymbols.length === 0
      ? DAISY_TONGUE_SYMBOLS.slice()
      : customSymbols.filter((symbol) => DAISY_TONGUE_SYMBOLS.includes(symbol));
  const compositionBase = buildDaisyRoleComposition(archetype, symmetry, allowedSymbols);
  const roleOverridesRaw =
    config && config.role_overrides && typeof config.role_overrides === "object" ? config.role_overrides : {};
  const roleOverrides = sanitizeDaisyRoleOverrides(roleOverridesRaw, allowedSymbols, compositionBase);
  const composition = { ...compositionBase, ...roleOverrides };
  const usedSymbols = Array.from(new Set(Object.values(composition)));
  return {
    schema: "qqva.daisy.bodyplan.v1",
    system_id: systemId,
    archetype,
    symmetry,
    segment_count: segmentCount,
    limb_pairs: limbPairs,
    palette: {
      core_token: coreToken,
      accent_token: accentToken,
      core_rgb: tokenColor(coreToken),
      accent_rgb: tokenColor(accentToken),
    },
    sakura_belonging: {
      semantics: "role_belonging_chain",
      coordinate_independent: true,
      tongue_ref: "byte_table:Sakura",
      core_chain: formatSakuraBelongingChain(coreBelongingChain),
      core_steps: coreBelongingChain,
      accent_chain: formatSakuraBelongingChain(accentBelongingChain),
      accent_steps: accentBelongingChain,
    },
    seed,
    daisy_tongue: {
      use_whole_tongue: useWholeTongue,
      allowed_symbols: allowedSymbols,
      composition,
      role_overrides: roleOverrides,
      semantics: "role_composition",
      lexicon_ref: "byte_table:Daisy",
      coverage: {
        total: DAISY_TONGUE_SYMBOLS.length,
        allowed: allowedSymbols.length,
        used: usedSymbols.length,
      },
    },
    generated_at: new Date().toISOString(),
  };
}

function daisyBodyplanToVoxels(spec) {
  const segmentCount = Math.round(clampNumber(spec.segment_count, 1, 24, 7));
  const limbPairs = Math.round(clampNumber(spec.limb_pairs, 0, 8, 2));
  const symmetry = String(spec.symmetry || "bilateral");
  const coreToken = String(spec?.palette?.core_token || "Ki");
  const accentToken = String(spec?.palette?.accent_token || "Fu");
  const coreBelongingSteps = parseSakuraBelongingChain(spec?.sakura_belonging?.core_chain || spec?.sakura_belonging?.core_steps);
  const accentBelongingSteps = parseSakuraBelongingChain(
    spec?.sakura_belonging?.accent_chain || spec?.sakura_belonging?.accent_steps
  );
  const coreBelongingChain = formatSakuraBelongingChain(coreBelongingSteps);
  const accentBelongingChain = formatSakuraBelongingChain(accentBelongingSteps);
  const coreColor = tokenColor(coreToken);
  const accentColor = tokenColor(accentToken);
  const systemId = String(spec.system_id || "daisy.system.alpha");
  const archetype = String(spec.archetype || "humanoid");
  const composition =
    spec && spec.daisy_tongue && spec.daisy_tongue.composition && typeof spec.daisy_tongue.composition === "object"
      ? spec.daisy_tongue.composition
      : buildDaisyRoleComposition(archetype, symmetry, DAISY_TONGUE_SYMBOLS);
  const voxels = [];
  for (let i = 0; i < segmentCount; i += 1) {
    const isHead = i === segmentCount - 1;
    const daisySymbol = isHead ? String(composition.integrator || "Yei") : String(composition.identity || "Lo");
    voxels.push({
      id: `daisy_core_${i + 1}`,
      type: isHead ? "daisy_head" : "daisy_core",
      x: 0,
      y: i,
      z: Math.floor(i * 0.35),
      color: coreColor,
      meta: {
        daisy: true,
        role: isHead ? "head" : "core",
        system_id: systemId,
        archetype,
        core_token: coreToken,
        sakura_belonging_anchor: "core",
        sakura_belonging_chain: coreBelongingChain || undefined,
        sakura_belonging_steps: coreBelongingSteps,
        daisy_symbol: daisySymbol,
      },
    });
  }
  const limbStart = Math.max(1, Math.floor(segmentCount * 0.2));
  const limbEnd = Math.max(limbStart, Math.floor(segmentCount * 0.9));
  const span = Math.max(1, limbEnd - limbStart);
  for (let p = 0; p < limbPairs; p += 1) {
    const y = limbStart + Math.floor((p / Math.max(1, limbPairs - 1 || 1)) * span);
    const reach = 1 + (p % 3);
    const leftSymbol = String(composition.joint || "X");
    const rightSymbol = String(composition.bond || "Mh");
    voxels.push({
      id: `daisy_limb_l_${p + 1}`,
      type: "daisy_limb",
      x: -reach,
      y,
      z: Math.max(0, Math.floor(y * 0.2)),
      color: accentColor,
      meta: {
        daisy: true,
        role: "limb",
        side: "left",
        pair: p + 1,
        system_id: systemId,
        accent_token: accentToken,
        sakura_belonging_anchor: "accent",
        sakura_belonging_chain: accentBelongingChain || undefined,
        sakura_belonging_steps: accentBelongingSteps,
        daisy_symbol: leftSymbol,
      },
    });
    voxels.push({
      id: `daisy_limb_r_${p + 1}`,
      type: "daisy_limb",
      x: reach,
      y,
      z: Math.max(0, Math.floor(y * 0.2)),
      color: accentColor,
      meta: {
        daisy: true,
        role: "limb",
        side: "right",
        pair: p + 1,
        system_id: systemId,
        accent_token: accentToken,
        sakura_belonging_anchor: "accent",
        sakura_belonging_chain: accentBelongingChain || undefined,
        sakura_belonging_steps: accentBelongingSteps,
        daisy_symbol: rightSymbol,
      },
    });
    if (symmetry === "radial") {
      const forwardSymbol = String(composition.actuator_primary || "Nz");
      const backwardSymbol = String(composition.spatial || "Foa");
      voxels.push({
        id: `daisy_limb_f_${p + 1}`,
        type: "daisy_limb",
        x: 0,
        y: y + 1,
        z: reach,
        color: accentColor,
        meta: {
          daisy: true,
          role: "limb",
          side: "forward",
          pair: p + 1,
          system_id: systemId,
          accent_token: accentToken,
          sakura_belonging_anchor: "accent",
          sakura_belonging_chain: accentBelongingChain || undefined,
          sakura_belonging_steps: accentBelongingSteps,
          daisy_symbol: forwardSymbol,
        },
      });
      voxels.push({
        id: `daisy_limb_b_${p + 1}`,
        type: "daisy_limb",
        x: 0,
        y: y - 1,
        z: Math.max(0, -reach),
        color: accentColor,
        meta: {
          daisy: true,
          role: "limb",
          side: "backward",
          pair: p + 1,
          system_id: systemId,
          accent_token: accentToken,
          sakura_belonging_anchor: "accent",
          sakura_belonging_chain: accentBelongingChain || undefined,
          sakura_belonging_steps: accentBelongingSteps,
          daisy_symbol: backwardSymbol,
        },
      });
    }
  }
  voxels.push({
    id: "daisy_system_framework",
    type: "daisy_system_node",
    x: -2,
    y: -1,
    z: 0,
    color: accentColor,
    meta: {
      daisy: true,
      role: "framework",
      system_id: systemId,
      sakura_core_belonging_chain: coreBelongingChain || undefined,
      sakura_core_belonging_steps: coreBelongingSteps,
      sakura_accent_belonging_chain: accentBelongingChain || undefined,
      sakura_accent_belonging_steps: accentBelongingSteps,
      daisy_symbol: String(composition.framework || "To"),
    },
  });
  voxels.push({
    id: "daisy_system_network",
    type: "daisy_system_node",
    x: 2,
    y: -1,
    z: 0,
    color: accentColor,
    meta: {
      daisy: true,
      role: "network",
      system_id: systemId,
      sakura_core_belonging_chain: coreBelongingChain || undefined,
      sakura_core_belonging_steps: coreBelongingSteps,
      sakura_accent_belonging_chain: accentBelongingChain || undefined,
      sakura_accent_belonging_steps: accentBelongingSteps,
      daisy_symbol: String(composition.network || "Ne"),
    },
  });
  return voxels;
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

function audioMimeTypeForFilename(filename) {
  const lower = String(filename || "").toLowerCase();
  if (lower.endsWith(".mp3")) {
    return "audio/mpeg";
  }
  if (lower.endsWith(".wav")) {
    return "audio/wav";
  }
  if (lower.endsWith(".ogg")) {
    return "audio/ogg";
  }
  if (lower.endsWith(".flac")) {
    return "audio/flac";
  }
  if (lower.endsWith(".m4a")) {
    return "audio/mp4";
  }
  return "application/octet-stream";
}

function imageMimeTypeForFilename(filename) {
  const lower = String(filename || "").toLowerCase();
  if (lower.endsWith(".heic")) {
    return "image/heic";
  }
  if (lower.endsWith(".heif")) {
    return "image/heif";
  }
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  if (lower.endsWith(".png")) {
    return "image/png";
  }
  if (lower.endsWith(".webp")) {
    return "image/webp";
  }
  return "application/octet-stream";
}

async function sha256HexFromArrayBuffer(buffer) {
  if (!window.crypto || !window.crypto.subtle) {
    throw new Error("crypto_subtle_unavailable");
  }
  const digest = await window.crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function buildWandDamageMediaDescriptors(files) {
  const descriptors = [];
  for (const file of files) {
    const mimeType = String(file.type || imageMimeTypeForFilename(file.name)).toLowerCase();
    const arrayBuffer = await file.arrayBuffer();
    descriptors.push({
      filename: file.name,
      mime_type: mimeType,
      sha256: await sha256HexFromArrayBuffer(arrayBuffer),
      size_bytes: Number(file.size || 0),
      capture_timestamp: null,
      metadata_hash: null,
      feature_digest: null,
      width: null,
      height: null,
    });
  }
  return descriptors;
}

function normalizeCamera3d(camera) {
  const source = camera && typeof camera === "object" ? camera : {};
  const yaw = Number.isFinite(Number(source.yaw)) ? Number(source.yaw) : -35;
  const pitch = Number.isFinite(Number(source.pitch)) ? Number(source.pitch) : 28;
  const zoom = Number.isFinite(Number(source.zoom)) ? Number(source.zoom) : 1;
  const panX = Number.isFinite(Number(source.panX)) ? Number(source.panX) : 0;
  const panY = Number.isFinite(Number(source.panY)) ? Number(source.panY) : 0;
  return {
    yaw: Math.max(-180, Math.min(180, yaw)),
    pitch: Math.max(5, Math.min(80, pitch)),
    zoom: Math.max(0.25, Math.min(4, zoom)),
    panX: Math.max(-4000, Math.min(4000, panX)),
    panY: Math.max(-4000, Math.min(4000, panY)),
  };
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
  navigable_town: [
    "const tiles = [];",
    "const links = [];",
    "const entities = [];",
    "const walkableSet = new Set();",
    "const centerX = Math.floor(cols / 2);",
    "const centerY = Math.floor(rows / 2);",
    "const toKey = (x, y) => `${x},${y}`;",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const border = x === 0 || y === 0 || x === cols - 1 || y === rows - 1;",
    "    const crossRoad = Math.abs(x - centerX) <= 1 || Math.abs(y - centerY) <= 1;",
    "    const lane = x % 8 === 0 || y % 8 === 0;",
    "    const isWalk = !border && (crossRoad || lane);",
    "    tiles.push({",
    "      x, y, layer: \"base\",",
    "      color_token: border ? \"Ga\" : isWalk ? \"El\" : \"Ki\",",
    "      opacity_token: border ? \"Ung\" : \"Na\",",
    "      presence_token: \"Ta\",",
    "      meta: { walkable: isWalk }",
    "    });",
    "    if (isWalk) walkable.add(toKey(x, y));",
    "  }",
    "}",
    "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
    "for (const key of walkable) {",
    "  const [xRaw, yRaw] = key.split(\",\");",
    "  const x = Number(xRaw);",
    "  const y = Number(yRaw);",
    "  for (const [dx, dy] of dirs) {",
    "    const nx = x + dx;",
    "    const ny = y + dy;",
    "    const nKey = toKey(nx, ny);",
    "    if (!walkable.has(nKey)) continue;",
    "    if (nx < x || ny < y) continue;",
    "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
    "  }",
    "}",
    "entities.push({ id: \"player\", kind: \"player\", x: centerX, y: centerY, z: 1 });",
    "for (let i = 0; i < 8; i += 1) {",
    "  const ox = ((seed + i * 11) % (cols - 4)) + 2;",
    "  const oy = ((seed * 3 + i * 7) % (rows - 4)) + 2;",
    "  if (walkable.has(toKey(ox, oy))) {",
    "    entities.push({ id: `npc_${i + 1}`, kind: \"npc\", x: ox, y: oy, z: 1 });",
    "  }",
    "}",
    "return { tiles, links, entities };",
  ].join("\n"),
  navigable_wilds: [
    "function noise(x, y, s) {",
    "  const n = Math.sin((x * 12.9898 + y * 78.233 + s) * 43758.5453);",
    "  return n - Math.floor(n);",
    "}",
    "const tiles = [];",
    "const links = [];",
    "const entities = [];",
    "const walkable = new Set();",
    "const toKey = (x, y) => `${x},${y}`;",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const n = noise(x, y, seed);",
    "    const river = Math.abs(y - Math.floor(rows * 0.55 + Math.sin(x * 0.17) * 3)) <= 1;",
    "    const isRock = n > 0.76;",
    "    const isWalk = !river && !isRock;",
    "    tiles.push({",
    "      x, y, layer: \"base\",",
    "      color_token: river ? \"Fu\" : isRock ? \"Ga\" : \"Ki\",",
    "      opacity_token: river ? \"Wu\" : isRock ? \"Ung\" : \"Na\",",
    "      presence_token: \"Ta\",",
    "      meta: { walkable: isWalk }",
    "    });",
    "    if (isWalk) walkable.add(toKey(x, y));",
    "  }",
    "}",
    "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
    "for (const key of walkable) {",
    "  const [xRaw, yRaw] = key.split(\",\");",
    "  const x = Number(xRaw);",
    "  const y = Number(yRaw);",
    "  for (const [dx, dy] of dirs) {",
    "    const nx = x + dx;",
    "    const ny = y + dy;",
    "    const nKey = toKey(nx, ny);",
    "    if (!walkable.has(nKey)) continue;",
    "    if (nx < x || ny < y) continue;",
    "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
    "  }",
    "}",
    "const centerX = Math.floor(cols / 2);",
    "const centerY = Math.floor(rows / 2);",
    "entities.push({ id: \"player\", kind: \"player\", x: centerX, y: centerY, z: 1 });",
    "for (let i = 0; i < 10; i += 1) {",
    "  const ox = ((seed * 5 + i * 13) % (cols - 2)) + 1;",
    "  const oy = ((seed * 7 + i * 17) % (rows - 2)) + 1;",
    "  if (walkable.has(toKey(ox, oy))) entities.push({ id: `npc_wild_${i + 1}`, kind: \"npc\", x: ox, y: oy, z: 1 });",
    "}",
    "return { tiles, links, entities };",
  ].join("\n"),
  humanoid_curve: [
    "const tiles = [];",
    "const links = [];",
    "const entities = [];",
    "const walkable = new Set();",
    "const toKey = (x, y) => `${x},${y}`;",
    "const cx = Math.floor(cols * 0.5);",
    "const cy = Math.floor(rows * 0.52);",
    "const clamp01 = (v) => Math.max(0, Math.min(1, v));",
    "const dist = (x1, y1, x2, y2) => Math.hypot(x1 - x2, y1 - y2);",
    "const sdfCircle = (x, y, ox, oy, r) => dist(x, y, ox, oy) - r;",
    "const sdfCapsule = (x, y, ax, ay, bx, by, r) => {",
    "  const pax = x - ax;",
    "  const pay = y - ay;",
    "  const bax = bx - ax;",
    "  const bay = by - ay;",
    "  const h = clamp01((pax * bax + pay * bay) / Math.max(1e-6, bax * bax + bay * bay));",
    "  const qx = pax - bax * h;",
    "  const qy = pay - bay * h;",
    "  return Math.hypot(qx, qy) - r;",
    "};",
    "",
    "// Curved humanoid primitives",
    "const torsoTopX = cx;",
    "const torsoTopY = cy - 8;",
    "const torsoBotX = cx;",
    "const torsoBotY = cy + 4;",
    "const leftArmAX = cx - 1;",
    "const leftArmAY = cy - 6;",
    "const leftArmBX = cx - 8;",
    "const leftArmBY = cy - 1;",
    "const rightArmAX = cx + 1;",
    "const rightArmAY = cy - 6;",
    "const rightArmBX = cx + 8;",
    "const rightArmBY = cy - 1;",
    "const leftLegAX = cx - 1;",
    "const leftLegAY = cy + 4;",
    "const leftLegBX = cx - 4;",
    "const leftLegBY = cy + 13;",
    "const rightLegAX = cx + 1;",
    "const rightLegAY = cy + 4;",
    "const rightLegBX = cx + 4;",
    "const rightLegBY = cy + 13;",
    "const headX = cx;",
    "const headY = cy - 12;",
    "",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const dHead = sdfCircle(x, y, headX, headY, 3.2);",
    "    const dTorso = sdfCapsule(x, y, torsoTopX, torsoTopY, torsoBotX, torsoBotY, 2.6);",
    "    const dArmL = sdfCapsule(x, y, leftArmAX, leftArmAY, leftArmBX, leftArmBY, 1.35);",
    "    const dArmR = sdfCapsule(x, y, rightArmAX, rightArmAY, rightArmBX, rightArmBY, 1.35);",
    "    const dLegL = sdfCapsule(x, y, leftLegAX, leftLegAY, leftLegBX, leftLegBY, 1.55);",
    "    const dLegR = sdfCapsule(x, y, rightLegAX, rightLegAY, rightLegBX, rightLegBY, 1.55);",
    "    const d = Math.min(dHead, dTorso, dArmL, dArmR, dLegL, dLegR);",
    "    const inside = d <= 0;",
    "    const edgeBand = Math.max(0, Math.min(3, Math.floor((d + 1.8) * 1.35)));",
    "    const lod = inside ? 3 : Math.max(0, 2 - edgeBand);",
    "    const shade = inside ? \"El\" : d < 1.6 ? \"Ot\" : \"Ga\";",
    "    const walkableCell = inside;",
    "    if (inside || d < 1.2) {",
    "      tiles.push({",
    "        x, y, layer: \"base\",",
    "        color_token: shade,",
    "        opacity_token: inside ? \"Na\" : \"Wu\",",
    "        presence_token: \"Ta\",",
    "        meta: { lod, walkable: walkableCell, curve: true, sdf: Number(d.toFixed(3)) }",
    "      });",
    "      if (walkableCell) walkableSet.add(toKey(x, y));",
    "    }",
    "  }",
    "}",
    "",
    "// 4-neighbor walk graph over body interior",
    "const dirs = [[1,0],[-1,0],[0,1],[0,-1]];",
    "for (const key of walkableSet) {",
    "  const [xRaw, yRaw] = key.split(\",\");",
    "  const x = Number(xRaw);",
    "  const y = Number(yRaw);",
    "  for (const [dx, dy] of dirs) {",
    "    const nx = x + dx;",
    "    const ny = y + dy;",
    "    const nKey = toKey(nx, ny);",
    "    if (!walkableSet.has(nKey)) continue;",
    "    if (nx < x || ny < y) continue;",
    "    links.push({ ax: x, ay: y, bx: nx, by: ny });",
    "  }",
    "}",
    "",
    "entities.push({ id: \"player\", kind: \"player\", x: cx, y: cy + 1, z: 1 });",
    "entities.push({ id: \"npc_curve_demo\", kind: \"npc\", x: cx, y: cy - 4, z: 1 });",
    "return { tiles, links, entities };",
  ].join("\n"),
  grilled_cheese: [
    "const tiles = [];",
    "const links = [];",
    "const entities = [];",
    "const cx = Math.floor(cols * 0.5);",
    "const cy = Math.floor(rows * 0.55);",
    "const w = Math.max(12, Math.floor(cols * 0.32));",
    "const h = Math.max(8, Math.floor(rows * 0.22));",
    "const left = cx - Math.floor(w / 2);",
    "const top = cy - Math.floor(h / 2);",
    "const right = left + w - 1;",
    "const bottom = top + h - 1;",
    "",
    "for (let y = 0; y < rows; y += 1) {",
    "  for (let x = 0; x < cols; x += 1) {",
    "    const inRect = x >= left && x <= right && y >= top && y <= bottom;",
    "    if (!inRect) continue;",
    "    const edge = x === left || x === right || y === top || y === bottom;",
    "    const crust = edge || x === left + 1 || x === right - 1 || y === top + 1 || y === bottom - 1;",
    "    const cheeseBand = y >= top + Math.floor(h * 0.42) && y <= top + Math.floor(h * 0.62);",
    "    const searMark = ((x + y + seed) % 7 === 0) || ((x * 2 + y + seed) % 11 === 0);",
    "    const color = crust ? \"Ot\" : cheeseBand ? \"Ru\" : searMark ? \"Ga\" : \"El\";",
    "    const opacity = crust ? \"Ung\" : cheeseBand ? \"Na\" : \"Wu\";",
    "    tiles.push({",
    "      x, y, layer: \"base\", color_token: color, opacity_token: opacity, presence_token: \"Ta\",",
    "      meta: { lod: 3, subject: \"grilled_cheese\", edible: true }",
    "    });",
    "  }",
    "}",
    "",
    "// Plate shadow under sandwich",
    "const plateY = Math.min(rows - 2, bottom + 2);",
    "for (let x = left - 2; x <= right + 2; x += 1) {",
    "  if (x < 0 || x >= cols) continue;",
    "  tiles.push({",
    "    x, y: plateY, layer: \"detail\", color_token: \"Ga\", opacity_token: \"Wu\", presence_token: \"Ta\",",
    "    meta: { lod: 2, subject: \"plate_shadow\" }",
    "  });",
    "}",
    "",
    "entities.push({ id: \"grilled_cheese_test\", kind: \"prop\", x: cx, y: cy, z: 1 });",
    "return { tiles, links, entities };",
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

const RENDERER_WORLD_MATERIAL_KIT = [
  { id: "grass", color: "#5f934f" },
  { id: "dirt", color: "#7a5d3f" },
  { id: "stone", color: "#7b7f87" },
  { id: "water", color: "#4f7ea3" },
  { id: "sand", color: "#b59b72" },
  { id: "wood", color: "#93673f" },
  { id: "wall", color: "#a48f78" },
  { id: "roof", color: "#7f5347" },
  { id: "metal", color: "#97a2b2" },
  { id: "foliage", color: "#4f844f" },
  { id: "sprite_skin", color: "#d7b195" },
  { id: "sprite_cloth", color: "#4a5f9d" },
];

function worldNoise(x, y) {
  const v =
    Math.sin(x * 0.21) * 0.9 +
    Math.cos(y * 0.31) * 0.8 +
    Math.sin((x + y) * 0.12) * 0.55;
  return v;
}

function buildLandscapeVoxels({
  width = 46,
  height = 30,
  originX = -10,
  originY = -8,
} = {}) {
  const voxels = [];
  for (let gy = 0; gy < height; gy += 1) {
    for (let gx = 0; gx < width; gx += 1) {
      const worldX = originX + gx;
      const worldY = originY + gy;
      const riverCenter = height * 0.46 + Math.sin(gx * 0.24) * 2.6;
      const riverBand = Math.abs(gy - riverCenter);
      if (riverBand <= 0.9) {
        voxels.push({
          id: `land_water_${gx}_${gy}`,
          type: "terrain_water",
          x: worldX,
          y: worldY,
          z: 0,
          material: "water",
          meta: { layer: "ground", material: "water", lod: 2 },
        });
        continue;
      }
      const n = worldNoise(gx, gy);
      const mound = Math.max(0, Math.min(2, Math.floor((n + 1.45) * 0.95)));
      for (let z = 0; z <= mound; z += 1) {
        const isTop = z === mound;
        const mat = isTop ? (mound >= 2 ? "stone" : riverBand < 2.1 ? "sand" : "grass") : "dirt";
        voxels.push({
          id: `land_${gx}_${gy}_${z}`,
          type: "terrain",
          x: worldX,
          y: worldY,
          z,
          material: mat,
          meta: { layer: z === 0 ? "ground" : "detail", material: mat, lod: 2 },
        });
      }
      if (mound <= 1 && (gx + gy) % 19 === 0) {
        voxels.push({
          id: `tree_trunk_${gx}_${gy}`,
          type: "flora_trunk",
          x: worldX,
          y: worldY,
          z: mound + 1,
          material: "wood",
          meta: { layer: "detail", material: "wood", lod: 2 },
        });
        voxels.push({
          id: `tree_leaf_${gx}_${gy}`,
          type: "flora_leaf",
          x: worldX,
          y: worldY,
          z: mound + 2,
          material: "foliage",
          meta: { layer: "detail", material: "foliage", lod: 3 },
        });
      }
    }
  }
  return voxels;
}

function buildStructureVoxels({
  originX = 10,
  originY = 6,
} = {}) {
  const voxels = [];
  const footprintW = 8;
  const footprintH = 7;
  const wallH = 4;
  for (let y = 0; y < footprintH; y += 1) {
    for (let x = 0; x < footprintW; x += 1) {
      const wx = originX + x;
      const wy = originY + y;
      voxels.push({
        id: `house_floor_${x}_${y}`,
        type: "structure_floor",
        x: wx,
        y: wy,
        z: 1,
        material: "wood",
        meta: { layer: "base", material: "wood", lod: 3 },
      });
      const edge = x === 0 || y === 0 || x === footprintW - 1 || y === footprintH - 1;
      if (!edge) {
        continue;
      }
      for (let z = 2; z < 2 + wallH; z += 1) {
        if (y === 0 && x >= 3 && x <= 4 && z <= 3) {
          continue;
        }
        voxels.push({
          id: `house_wall_${x}_${y}_${z}`,
          type: "structure_wall",
          x: wx,
          y: wy,
          z,
          material: "wall",
          meta: { layer: "mid", material: "wall", lod: 3 },
        });
      }
      const roofZ = 2 + wallH;
      if (x > 0 && x < footprintW - 1 && y > 0 && y < footprintH - 1) {
        voxels.push({
          id: `house_roof_${x}_${y}`,
          type: "structure_roof",
          x: wx,
          y: wy,
          z: roofZ,
          material: "roof",
          meta: { layer: "sky", material: "roof", lod: 2 },
        });
      }
    }
  }
  const towerBaseX = originX + footprintW + 3;
  const towerBaseY = originY + 1;
  for (let y = 0; y < 3; y += 1) {
    for (let x = 0; x < 3; x += 1) {
      for (let z = 1; z < 8; z += 1) {
        voxels.push({
          id: `tower_${x}_${y}_${z}`,
          type: "structure_tower",
          x: towerBaseX + x,
          y: towerBaseY + y,
          z,
          material: z >= 7 ? "roof" : "stone",
          meta: { layer: z >= 6 ? "sky" : "mid", material: z >= 7 ? "roof" : "stone", lod: 3 },
        });
      }
    }
  }
  return voxels;
}

function buildSpriteFigureVoxels({ x = 5, y = 4, baseZ = 2, id = "sprite_hero", cloth = "sprite_cloth" } = {}) {
  return [
    {
      id,
      type: "sprite_actor",
      x,
      y,
      z: baseZ,
      material: cloth,
      meta: {
        layer: "mid",
        material: cloth,
        lod: 3,
        sprite2d: true,
        render_mode: "sprite2d",
        sprite_w: 1.25,
        sprite_h: 1.95,
      },
    },
  ];
}

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

const SCENE_SCHEMA_V1 = {
  schema: "qqva.scene.v1",
  scene: {
    id: "scene_prototype",
    name: "Prototype Scene",
    systems: {
      gravity: 0,
      camera: { x: 0, y: 0 }
    },
    entities: [
      {
        id: "entity_001",
        kind: "token",
        x: 0,
        y: 0,
        sprite_id: "sprite_001"
      }
    ]
  }
};

const SPRITE_SCHEMA_V1 = {
  schema: "qqva.sprite.v1",
  sprite: {
    id: "sprite_001",
    name: "Prototype Sprite",
    source: "assets/sprites/sprite_001.png",
    frame_w: 32,
    frame_h: 32,
    frames: [{ id: "idle_0", x: 0, y: 0, w: 32, h: 32, ms: 120 }],
    tags: ["token"],
    anchor: { x: 16, y: 16 },
    collision: { x: 2, y: 2, w: 28, h: 28 }
  }
};

function buildSceneSchemaV1FromSpec(specObj) {
  const spec = specObj && typeof specObj === "object" ? specObj : {};
  const scene = spec.scene && typeof spec.scene === "object" ? spec.scene : {};
  const systems = spec.systems && typeof spec.systems === "object" ? spec.systems : {};
  const entities = Array.isArray(spec.entities) ? spec.entities : [];
  return {
    schema: "qqva.scene.v1",
    scene: {
      id: String(scene.id || "scene_prototype"),
      name: String(scene.name || "Prototype Scene"),
      systems,
      entities: entities.map((entity, index) => {
        const e = entity && typeof entity === "object" ? entity : {};
        return {
          id: String(e.id || `entity_${String(index + 1).padStart(3, "0")}`),
          kind: String(e.kind || "token"),
          x: Number(e.x || 0),
          y: Number(e.y || 0),
          sprite_id: typeof e.sprite_id === "string" ? e.sprite_id : undefined
        };
      })
    }
  };
}

function buildSpecFromSceneSchemaV1(sceneDoc) {
  const sceneContainer = sceneDoc && typeof sceneDoc === "object" ? sceneDoc : {};
  const scene = sceneContainer.scene && typeof sceneContainer.scene === "object" ? sceneContainer.scene : {};
  const systems = scene.systems && typeof scene.systems === "object" ? scene.systems : {};
  const entities = Array.isArray(scene.entities) ? scene.entities : [];
  return {
    scene: {
      id: String(scene.id || "scene_prototype"),
      name: String(scene.name || "Prototype Scene")
    },
    systems,
    entities: entities.map((entity, index) => {
      const e = entity && typeof entity === "object" ? entity : {};
      return {
        id: String(e.id || `entity_${String(index + 1).padStart(3, "0")}`),
        kind: String(e.kind || "token"),
        x: Number(e.x || 0),
        y: Number(e.y || 0),
        sprite_id: typeof e.sprite_id === "string" ? e.sprite_id : undefined
      };
    })
  };
}

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
    <div id="root">Renderer ready...</div>
    <script>
      const root = document.getElementById("root");
      const bootLines = [];
      function bootLine(text) { bootLines.push(text); }
      function flushBoot() { root.textContent = bootLines.join("\\n"); }
      bootLine("boot: start");
      window.addEventListener("error", (event) => {
        bootLine("boot: error " + String(event && event.message ? event.message : event));
        flushBoot();
      });
      try {
        root.textContent = "";
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
          div.textContent = "#" + (idx + 1) + " " + JSON.stringify(entity);
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
        const normalized = String(sourceText || "").split("\\r").join("");
        const lines = normalized.split("\\n");
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
          if (lineText.startsWith("entity ") ) {
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
          if (lineText.startsWith("lex ") || lineText.startsWith("akinenwun ") || lineText.startsWith("word ") ) {
            const spaceAt = lineText.indexOf(" ");
            const word = spaceAt > 0 ? lineText.slice(spaceAt + 1).trim() : "";
            if (word) words.push({ word, symbols: splitAkinenwun(word) });
          }
        });
        return { entities, words };
      }
      try {
        line("boot: ok", "ok");
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
          const lines = source.split("\\r").join("").split("\\n").map((v) => v.trim());
          const drawLines = lines.filter((ln) => ln.startsWith("#draw ") );
          line("python directives=" + drawLines.length, "ok");
          drawLines.forEach((ln) => line(ln.slice(6)));
        }
      } catch (err) {
        line(String(err && err.message ? err.message : err), "err");
      }
      } catch (err) {
        bootLine("boot: exception " + String(err && err.message ? err.message : err));
        flushBoot();
      }
    </script>
  </body>
</html>`;
}

function colorForVoxelType(type) {
  const raw = String(type || "voxel");
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash * 31 + raw.charCodeAt(i)) >>> 0;
  }
  const r = 80 + (hash & 0x7f);
  const g = 80 + ((hash >> 8) & 0x7f);
  const b = 80 + ((hash >> 16) & 0x7f);
  return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
}

const textureCache = new Map();

function getTextureImage(source, onReady) {
  const src = typeof source === "string" ? source.trim() : "";
  if (!src) {
    return null;
  }
  const cached = textureCache.get(src);
  if (cached) {
    if (!cached.loaded && typeof onReady === "function") {
      cached.callbacks.push(onReady);
    }
    return cached.img;
  }
  const img = new Image();
  const entry = { img, loaded: false, callbacks: typeof onReady === "function" ? [onReady] : [] };
  img.onload = () => {
    entry.loaded = true;
    const callbacks = entry.callbacks.slice();
    entry.callbacks.length = 0;
    callbacks.forEach((cb) => cb());
  };
  img.onerror = () => {
    entry.loaded = false;
    entry.callbacks.length = 0;
  };
  img.src = src;
  textureCache.set(src, entry);
  return img;
}

function parseAtlasToken(value) {
  if (typeof value !== "string") {
    return null;
  }
  if (!value.startsWith("atlas:")) {
    return null;
  }
  const parts = value.split(":");
  if (parts.length < 3) {
    return null;
  }
  return { atlasId: parts[1], tile: parts.slice(2).join(":") };
}

function resolveAtlasFrame(atlas, tile) {
  if (!atlas) {
    return null;
  }
  const size = Number(atlas.tileSize || atlas.tile || 16);
  const padding = Number(atlas.padding || 0);
  const cols = Math.max(1, Number(atlas.cols || atlas.columns || 1));
  let col = 0;
  let row = 0;
  if (typeof tile === "string" && tile.includes(",")) {
    const [c, r] = tile.split(",").map((v) => Number(v.trim()));
    col = Number.isFinite(c) ? c : 0;
    row = Number.isFinite(r) ? r : 0;
  } else {
    const idx = Number.parseInt(tile, 10);
    if (!Number.isNaN(idx)) {
      col = idx % cols;
      row = Math.floor(idx / cols);
    }
  }
  const x = padding + col * (size + padding);
  const y = padding + row * (size + padding);
  return { x, y, w: size, h: size };
}

function applyAtlasToTexture(textureValue, atlasMap) {
  const token = parseAtlasToken(textureValue);
  if (!token) {
    return null;
  }
  const atlas = atlasMap && atlasMap[token.atlasId] ? atlasMap[token.atlasId] : null;
  if (!atlas || typeof atlas.src !== "string") {
    return null;
  }
  const frame = resolveAtlasFrame(atlas, token.tile);
  return frame ? { texture: atlas.src, frame } : { texture: atlas.src, frame: null };
}

function roseRingScalar(symbol) {
  const ringMap = {
    Gaoh: 0,
    Ao: 1,
    Ye: 2,
    Ui: 3,
    Shu: 4,
    Kiel: 5,
    Yeshu: 6,
    Lao: 7,
    Shushy: 8,
    Uinshu: 9,
    Kokiel: 10,
    Aonkiel: 11,
  };
  if (Object.prototype.hasOwnProperty.call(ringMap, symbol)) {
    return ringMap[symbol];
  }
  const vectorMap = {
    Ru: 0,
    Ot: 1,
    El: 2,
    Ki: 3,
    Fu: 4,
    Ka: 5,
    AE: 6,
  };
  if (Object.prototype.hasOwnProperty.call(vectorMap, symbol)) {
    const scalar = vectorMap[symbol] * 2;
    return scalar > 11 ? 11 : scalar;
  }
  return null;
}

function deriveRoseVectorFromSymbols(symbols) {
  if (!Array.isArray(symbols)) {
    return null;
  }
  const scalars = [];
  const sources = [];
  let polarity = 0;
  symbols.forEach((raw) => {
    const symbol = String(raw || "").trim();
    if (!symbol) {
      return;
    }
    if (symbol === "Ha") {
      polarity = 1;
      return;
    }
    if (symbol === "Ga") {
      polarity = -1;
      return;
    }
    const scalar = roseRingScalar(symbol);
    if (Number.isFinite(scalar)) {
      scalars.push(Number(scalar));
      sources.push(symbol);
    }
  });
  if (scalars.length === 0) {
    return null;
  }
  const angles = scalars.map((scalar) => (scalar / 12) * Math.PI * 2);
  const x = angles.reduce((acc, angle) => acc + Math.cos(angle), 0) / angles.length;
  const y = angles.reduce((acc, angle) => acc + Math.sin(angle), 0) / angles.length;
  const phase = (Math.atan2(y, x) * 180) / Math.PI;
  return {
    ring: 12,
    mode: "ring12",
    scalars,
    sources,
    vector: { x, y },
    phase_deg: (phase + 360) % 360,
    polarity,
  };
}

function normalizeRoseVector(value) {
  if (!value || typeof value !== "object") {
    return null;
  }
  const vector = value.vector && typeof value.vector === "object" ? value.vector : {};
  const x = Number.isFinite(Number(vector.x)) ? Number(vector.x) : 0;
  const y = Number.isFinite(Number(vector.y)) ? Number(vector.y) : 0;
  const scalars = Array.isArray(value.scalars) ? value.scalars.map((item) => Number(item)).filter(Number.isFinite) : [];
  return {
    ring: Number.isFinite(Number(value.ring)) ? Number(value.ring) : 12,
    mode: typeof value.mode === "string" ? value.mode : "ring12",
    scalars,
    sources: Array.isArray(value.sources) ? value.sources.map((item) => String(item)) : [],
    vector: { x, y },
    phase_deg: Number.isFinite(Number(value.phase_deg)) ? Number(value.phase_deg) : 0,
    polarity: Number.isFinite(Number(value.polarity)) ? Number(value.polarity) : 0,
  };
}

function readRoseSymbols(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }
  return null;
}

function resolveRoseVector(payload, engineState) {
  const candidates = [
    payload,
    payload && payload.render_constraints,
    payload && payload.context && payload.context.render_constraints,
    engineState,
    engineState && engineState.render_constraints,
    engineState && engineState.tables,
    engineState && engineState.tables && engineState.tables.render_constraints,
  ];
  for (const candidate of candidates) {
    if (candidate && typeof candidate === "object") {
      const rose = candidate.rose_vector_calculus;
      const normalized = normalizeRoseVector(rose);
      if (normalized) {
        return normalized;
      }
    }
  }
  for (const candidate of candidates) {
    if (candidate && typeof candidate === "object") {
      const symbols =
        readRoseSymbols(candidate.rose_symbols) ||
        readRoseSymbols(candidate.roseSymbols) ||
        readRoseSymbols(candidate.rose && candidate.rose.symbols);
      const derived = deriveRoseVectorFromSymbols(symbols || []);
      if (derived) {
        return derived;
      }
    }
  }
  return null;
}

function normalizeVoxelItem(item, index, semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON) {
  const entry = item && typeof item === "object" ? item : {};
  const meta = entry.meta && typeof entry.meta === "object" ? { ...entry.meta } : {};
  const posArray = Array.isArray(entry.pos)
    ? entry.pos
    : Array.isArray(entry.position)
      ? entry.position
      : Array.isArray(entry.coords)
        ? entry.coords
        : Array.isArray(entry.at)
          ? entry.at
          : null;
  const posObject = entry.pos && typeof entry.pos === "object" && !Array.isArray(entry.pos)
    ? entry.pos
    : entry.position && typeof entry.position === "object" && !Array.isArray(entry.position)
      ? entry.position
      : entry.coords && typeof entry.coords === "object" && !Array.isArray(entry.coords)
        ? entry.coords
        : entry.at && typeof entry.at === "object" && !Array.isArray(entry.at)
          ? entry.at
          : null;
  const semanticTokens = collectSemanticTokens(entry, meta);
  const semanticTypeFromTag = semanticValueFromTokens(semanticTokens, "type");
  const semanticRoleFromTag = semanticValueFromTokens(semanticTokens, "role");
  const semanticMaterialFromTag = semanticValueFromTokens(semanticTokens, "material");
  const semanticLayerFromTag = semanticValueFromTokens(semanticTokens, "layer");
  const rawType = String(entry.type || entry.kind || entry.tag || entry.id || ("voxel_" + index));
  const rawKind = String(entry.kind || meta.kind || rawType);
  const rawRole = String(entry.role || meta.role || semanticRoleFromTag || "");
  const type = resolveLexiconAlias("type", semanticTypeFromTag || rawType, semanticLexicon);
  const kind = resolveLexiconAlias("type", rawKind, semanticLexicon);
  const canonicalRole = resolveLexiconAlias("role", rawRole, semanticLexicon);
  const canonicalMaterial = resolveLexiconAlias(
    "material",
    semanticMaterialFromTag || entry.material || meta.material || "",
    semanticLexicon
  );
  const canonicalLayer = resolveLexiconAlias(
    "layer",
    semanticLayerFromTag || entry.layer || meta.layer || "",
    semanticLexicon
  );
  if (canonicalRole) {
    meta.role = canonicalRole;
  }
  if (canonicalMaterial) {
    meta.material = canonicalMaterial;
  }
  if (canonicalLayer) {
    meta.layer = canonicalLayer;
  }
  meta.semantic_tokens = semanticTokens;
  meta.semantic_canonical = {
    role: canonicalRole || "",
    type: String(type || ""),
    kind: String(kind || ""),
    material: canonicalMaterial || "",
    layer: canonicalLayer || "",
  };
  const color = typeof entry.color === "string"
    ? entry.color
    : typeof meta.color === "string"
      ? meta.color
      : colorForVoxelType(type);
  const x = Number.isFinite(Number(entry.x))
    ? Number(entry.x)
    : posArray && Number.isFinite(Number(posArray[0]))
      ? Number(posArray[0])
      : posObject && Number.isFinite(Number(posObject.x))
        ? Number(posObject.x)
        : 0;
  const y = Number.isFinite(Number(entry.y))
    ? Number(entry.y)
    : posArray && Number.isFinite(Number(posArray[1]))
      ? Number(posArray[1])
      : posObject && Number.isFinite(Number(posObject.y))
        ? Number(posObject.y)
        : 0;
  const z = Number.isFinite(Number(entry.z))
    ? Number(entry.z)
    : Number.isFinite(Number(entry.depth))
      ? Number(entry.depth)
      : posArray && Number.isFinite(Number(posArray[2]))
        ? Number(posArray[2])
        : posObject && Number.isFinite(Number(posObject.z))
          ? Number(posObject.z)
          : Number.isFinite(Number(meta.z))
        ? Number(meta.z)
        : Number.isFinite(Number(meta.depth))
          ? Number(meta.depth)
          : 0;
  const texture =
    (typeof entry.texture === "string" ? entry.texture : null) ||
    (typeof entry.tex === "string" ? entry.tex : null) ||
    (entry.sprite && typeof entry.sprite.source === "string" ? entry.sprite.source : null) ||
    (typeof meta.texture === "string" ? meta.texture : null) ||
    (meta.sprite && typeof meta.sprite.source === "string" ? meta.sprite.source : null) ||
    null;
  const textureTop =
    (typeof entry.texture_top === "string" ? entry.texture_top : null) ||
    (typeof entry.textureTop === "string" ? entry.textureTop : null) ||
    (meta && typeof meta.texture_top === "string" ? meta.texture_top : null) ||
    (meta && typeof meta.textureTop === "string" ? meta.textureTop : null) ||
    null;
  const textureLeft =
    (typeof entry.texture_left === "string" ? entry.texture_left : null) ||
    (typeof entry.textureLeft === "string" ? entry.textureLeft : null) ||
    (meta && typeof meta.texture_left === "string" ? meta.texture_left : null) ||
    (meta && typeof meta.textureLeft === "string" ? meta.textureLeft : null) ||
    null;
  const textureRight =
    (typeof entry.texture_right === "string" ? entry.texture_right : null) ||
    (typeof entry.textureRight === "string" ? entry.textureRight : null) ||
    (meta && typeof meta.texture_right === "string" ? meta.texture_right : null) ||
    (meta && typeof meta.textureRight === "string" ? meta.textureRight : null) ||
    null;
  const frame =
    (entry.frame && typeof entry.frame === "object" ? entry.frame : null) ||
    (entry.sprite && typeof entry.sprite.frame === "object" ? entry.sprite.frame : null) ||
    (meta.frame && typeof meta.frame === "object" ? meta.frame : null) ||
    (meta.sprite && typeof meta.sprite.frame === "object" ? meta.sprite.frame : null) ||
    null;
  const frameTop =
    (entry.frame_top && typeof entry.frame_top === "object" ? entry.frame_top : null) ||
    (entry.frameTop && typeof entry.frameTop === "object" ? entry.frameTop : null) ||
    (meta.frame_top && typeof meta.frame_top === "object" ? meta.frame_top : null) ||
    (meta.frameTop && typeof meta.frameTop === "object" ? meta.frameTop : null) ||
    null;
  const frameLeft =
    (entry.frame_left && typeof entry.frame_left === "object" ? entry.frame_left : null) ||
    (entry.frameLeft && typeof entry.frameLeft === "object" ? entry.frameLeft : null) ||
    (meta.frame_left && typeof meta.frame_left === "object" ? meta.frame_left : null) ||
    (meta.frameLeft && typeof meta.frameLeft === "object" ? meta.frameLeft : null) ||
    null;
  const frameRight =
    (entry.frame_right && typeof entry.frame_right === "object" ? entry.frame_right : null) ||
    (entry.frameRight && typeof entry.frameRight === "object" ? entry.frameRight : null) ||
    (meta.frame_right && typeof meta.frame_right === "object" ? meta.frame_right : null) ||
    (meta.frameRight && typeof meta.frameRight === "object" ? meta.frameRight : null) ||
    null;
  const id = String(entry.id || entry.entity_id || meta.id || ("voxel_" + index));
  const lod =
    entry.lod && typeof entry.lod === "object" && !Array.isArray(entry.lod)
      ? { ...entry.lod }
      : meta.lod && typeof meta.lod === "object" && !Array.isArray(meta.lod)
        ? { ...meta.lod }
        : {};
  const lodVariants = Array.isArray(entry.lod_variants)
    ? entry.lod_variants
    : Array.isArray(entry.lodVariants)
      ? entry.lodVariants
      : Array.isArray(meta.lod_variants)
        ? meta.lod_variants
        : Array.isArray(meta.lodVariants)
          ? meta.lodVariants
          : [];
  return {
    id,
    kind,
    x,
    y,
    z,
    color,
    type,
    meta,
    texture,
    textureTop,
    textureLeft,
    textureRight,
    frame,
    frameTop,
    frameLeft,
    frameRight,
    lod,
    lodVariants
  };
}

function isSpritePlaneVoxel(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const meta = item.meta && typeof item.meta === "object" ? item.meta : {};
  if (typeof item.sprite2d === "boolean") {
    return item.sprite2d;
  }
  if (typeof meta.sprite2d === "boolean") {
    return meta.sprite2d;
  }
  const renderMode = String(meta.render_mode || meta.renderMode || "").toLowerCase();
  if (renderMode === "sprite2d" || renderMode === "billboard") {
    return true;
  }
  const type = String(item.type || "").toLowerCase();
  const kind = String(item.kind || "").toLowerCase();
  return type.includes("sprite") || kind.includes("sprite");
}

function resolveSpritePlaneMetrics(item, tile) {
  const meta = item && item.meta && typeof item.meta === "object" ? item.meta : {};
  const widthTiles =
    Number(item.sprite_w || item.spriteWidth || meta.sprite_w || meta.spriteWidth || 1.2) || 1.2;
  const heightTiles =
    Number(item.sprite_h || item.spriteHeight || meta.sprite_h || meta.spriteHeight || 1.8) || 1.8;
  const anchorYTiles =
    Number(item.sprite_anchor_y || item.spriteAnchorY || meta.sprite_anchor_y || meta.spriteAnchorY || 1.0) || 1.0;
  return {
    w: Math.max(4, Number(tile) * Math.max(0.3, widthTiles)),
    h: Math.max(6, Number(tile) * Math.max(0.6, heightTiles)),
    anchorY: Number(tile) * Math.max(0, anchorYTiles),
  };
}

function normalizeFrameRect(frame) {
  if (!frame || typeof frame !== "object") {
    return null;
  }
  const w = Number(frame.w || frame.width || 0);
  const h = Number(frame.h || frame.height || 0);
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    return null;
  }
  return {
    x: Number(frame.x || 0),
    y: Number(frame.y || 0),
    w,
    h,
  };
}

function normalizeFrameSequence(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeFrameRect).filter(Boolean);
  }
  if (value && typeof value === "object" && Array.isArray(value.frames)) {
    return value.frames.map(normalizeFrameRect).filter(Boolean);
  }
  const one = normalizeFrameRect(value);
  return one ? [one] : [];
}

function resolveSpriteFrameForFacing(item, facing, fallbackFrame, settings = {}) {
  const meta = item && item.meta && typeof item.meta === "object" ? item.meta : {};
  const normalized = normalizeFacing(
    facing || meta.spriteFacing || meta.sprite_facing || meta.facing || "south"
  );
  const moving = Boolean(settings.playerMoving);
  const motionKey = moving ? "walk" : "idle";
  const frameMap =
    (item && item.sprite_frames && typeof item.sprite_frames === "object" ? item.sprite_frames : null) ||
    (meta.sprite_frames && typeof meta.sprite_frames === "object" ? meta.sprite_frames : null) ||
    (meta.spriteFrames && typeof meta.spriteFrames === "object" ? meta.spriteFrames : null);
  const animationMap =
    (item && item.sprite_animations && typeof item.sprite_animations === "object" ? item.sprite_animations : null) ||
    (meta.sprite_animations && typeof meta.sprite_animations === "object" ? meta.sprite_animations : null) ||
    (meta.spriteAnimations && typeof meta.spriteAnimations === "object" ? meta.spriteAnimations : null);
  if (animationMap) {
    const motionNode = animationMap[motionKey] && typeof animationMap[motionKey] === "object" ? animationMap[motionKey] : null;
    const directionalNode = motionNode && motionNode[normalized] !== undefined ? motionNode[normalized] : null;
    const seq = normalizeFrameSequence(directionalNode);
    if (seq.length > 0) {
      const ms = Number(meta.sprite_anim_ms || meta.spriteAnimMs || settings.spriteAnimMs || 120);
      const stepMs = Number.isFinite(ms) && ms > 20 ? ms : 120;
      const clock = Number(settings.animationClock || Date.now());
      const idx = Math.floor(clock / stepMs) % seq.length;
      return seq[idx];
    }
  }
  if (frameMap) {
    const direct = frameMap[normalized];
    if (direct && typeof direct === "object") {
      return direct;
    }
  }
  const stripEnabled = Boolean(
    meta.sprite_direction_strip === true ||
      meta.spriteDirectionStrip === true ||
      meta.direction_strip === true
  );
  if (stripEnabled && fallbackFrame && typeof fallbackFrame === "object") {
    const w = Number(fallbackFrame.w || 0);
    const h = Number(fallbackFrame.h || 0);
    if (w > 0 && h > 0) {
      const idxMap = { south: 0, west: 1, east: 2, north: 3 };
      const idx = idxMap[normalized] ?? 0;
      return {
        x: Number(fallbackFrame.x || 0) + idx * w,
        y: Number(fallbackFrame.y || 0),
        w,
        h,
      };
    }
  }
  const fallback = normalizeFrameRect(fallbackFrame);
  return fallback;
}

function normalizeCamera2d(camera) {
  const source = camera && typeof camera === "object" ? camera : {};
  const panX = Number.isFinite(Number(source.panX)) ? Number(source.panX) : 0;
  const panY = Number.isFinite(Number(source.panY)) ? Number(source.panY) : 0;
  const zoom = Number.isFinite(Number(source.zoom)) ? Number(source.zoom) : 1;
  return {
    panX: Math.max(-8000, Math.min(8000, panX)),
    panY: Math.max(-8000, Math.min(8000, panY)),
    zoom: Math.max(0.25, Math.min(8, zoom)),
  };
}

function resolveInputLodLevel(settings) {
  const lod = settings && typeof settings === "object" && settings.lod && typeof settings.lod === "object" ? settings.lod : {};
  const mode = String(lod.mode || "auto_zoom").toLowerCase();
  if (mode === "manual") {
    const manual = Number.isFinite(Number(lod.level)) ? Number(lod.level) : 2;
    return Math.max(0, Math.min(5, Math.round(manual)));
  }
  const camera2d = normalizeCamera2d(settings && settings.camera2d);
  const zoom = Number(camera2d.zoom || 1);
  if (zoom < 0.55) return 0;
  if (zoom < 0.9) return 1;
  if (zoom < 1.4) return 2;
  if (zoom < 2.2) return 3;
  if (zoom < 3.2) return 4;
  return 5;
}

function lodRuleMatches(rule, lodLevel, zoom) {
  if (!rule || typeof rule !== "object") {
    return true;
  }
  if (Number.isFinite(Number(rule.min_level)) && lodLevel < Number(rule.min_level)) {
    return false;
  }
  if (Number.isFinite(Number(rule.max_level)) && lodLevel > Number(rule.max_level)) {
    return false;
  }
  if (Number.isFinite(Number(rule.min_zoom)) && zoom < Number(rule.min_zoom)) {
    return false;
  }
  if (Number.isFinite(Number(rule.max_zoom)) && zoom > Number(rule.max_zoom)) {
    return false;
  }
  return true;
}

function applyInputLod(voxels, settings) {
  if (!Array.isArray(voxels) || voxels.length === 0) {
    return [];
  }
  const camera2d = normalizeCamera2d(settings && settings.camera2d);
  const zoom = Number(camera2d.zoom || 1);
  const lodLevel = resolveInputLodLevel(settings || {});
  const out = [];
  voxels.forEach((baseVoxel) => {
    if (!baseVoxel || typeof baseVoxel !== "object") {
      return;
    }
    const rule = baseVoxel.lod && typeof baseVoxel.lod === "object" ? baseVoxel.lod : {};
    if (!lodRuleMatches(rule, lodLevel, zoom)) {
      return;
    }
    const variants = Array.isArray(baseVoxel.lodVariants) ? baseVoxel.lodVariants : [];
    let resolved = baseVoxel;
    variants.forEach((variantRaw) => {
      if (!variantRaw || typeof variantRaw !== "object") {
        return;
      }
      const when = variantRaw.when && typeof variantRaw.when === "object" ? variantRaw.when : {};
      if (!lodRuleMatches(when, lodLevel, zoom)) {
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

function isRendererPlayerVoxel(voxel, playerId, semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON) {
  if (!voxel || typeof voxel !== "object") {
    return false;
  }
  const target = String(playerId || "player").trim().toLowerCase();
  const id = String(voxel.id || voxel.entity_id || "").trim().toLowerCase();
  const type = String(voxel.type || "").trim().toLowerCase();
  const kind = String(voxel.kind || "").trim().toLowerCase();
  const role = String(voxel.meta && voxel.meta.role ? voxel.meta.role : "").trim().toLowerCase();
  const akinenwun = String(voxel.meta && voxel.meta.akinenwun ? voxel.meta.akinenwun : "").trim().toLowerCase();
  const semanticCanonicalRole = String(
    voxel.meta && voxel.meta.semantic_canonical && voxel.meta.semantic_canonical.role
      ? voxel.meta.semantic_canonical.role
      : ""
  ).trim().toLowerCase();
  const semanticRole = String(
    voxel.meta && voxel.meta.semantic_role
      ? voxel.meta.semantic_role
      : voxel.meta && voxel.meta.semanticRole
        ? voxel.meta.semanticRole
        : ""
  ).trim().toLowerCase();
  const semanticTags = Array.isArray(voxel.meta && voxel.meta.semantic_tags)
    ? voxel.meta.semantic_tags.map((item) => String(item).trim().toLowerCase())
    : Array.isArray(voxel.meta && voxel.meta.semanticTags)
      ? voxel.meta.semanticTags.map((item) => String(item).trim().toLowerCase())
      : [];
  const shygazunPlayerMarkers = new Set(
    Array.isArray(semanticLexicon && semanticLexicon.player_markers)
      ? semanticLexicon.player_markers.map((item) => String(item).trim().toLowerCase()).filter(Boolean)
      : DEFAULT_SHYGAZUN_RENDER_LEXICON.player_markers
  );
  if (target && (id === target || id === ("entity_" + target))) {
    return true;
  }
  if (type === "player" || kind === "player" || role === "player") {
    return true;
  }
  if (semanticCanonicalRole && shygazunPlayerMarkers.has(semanticCanonicalRole)) {
    return true;
  }
  if (semanticRole && shygazunPlayerMarkers.has(semanticRole)) {
    return true;
  }
  if (akinenwun && shygazunPlayerMarkers.has(akinenwun)) {
    return true;
  }
  return semanticTags.some((tag) => shygazunPlayerMarkers.has(tag));
}

function applyPlayerMotionToVoxels(
  voxels,
  playerId,
  playerTransform,
  semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON,
  playerFacing = "south"
) {
  if (!Array.isArray(voxels)) {
    return [];
  }
  const mode = String(playerTransform && playerTransform.mode ? playerTransform.mode : "offset").toLowerCase();
  const tx = Number.isFinite(Number(playerTransform && playerTransform.x)) ? Number(playerTransform.x) : 0;
  const ty = Number.isFinite(Number(playerTransform && playerTransform.y)) ? Number(playerTransform.y) : 0;
  const tz = Number.isFinite(Number(playerTransform && playerTransform.z)) ? Number(playerTransform.z) : 0;
  if (mode !== "absolute" && tx === 0 && ty === 0 && tz === 0) {
    return voxels;
  }
  return voxels.map((voxel) => {
    if (!isRendererPlayerVoxel(voxel, playerId, semanticLexicon)) {
      return voxel;
    }
    if (mode === "absolute") {
      return {
        ...voxel,
        x: tx,
        y: ty,
        z: tz,
        meta: { ...(voxel.meta && typeof voxel.meta === "object" ? voxel.meta : {}), spriteFacing: normalizeFacing(playerFacing) },
      };
    }
    return {
      ...voxel,
      x: Number(voxel.x || 0) + tx,
      y: Number(voxel.y || 0) + ty,
      z: Number(voxel.z || 0) + tz,
      meta: { ...(voxel.meta && typeof voxel.meta === "object" ? voxel.meta : {}), spriteFacing: normalizeFacing(playerFacing) },
    };
  });
}

function readPlayerPositionSignal(engineState) {
  if (!engineState || typeof engineState !== "object") {
    return null;
  }
  const signals = engineState.signals && typeof engineState.signals === "object" ? engineState.signals : {};
  const pos = signals.player_position && typeof signals.player_position === "object" ? signals.player_position : null;
  if (!pos) {
    return null;
  }
  if (!Number.isFinite(Number(pos.x)) || !Number.isFinite(Number(pos.y))) {
    return null;
  }
  return {
    x: Number(pos.x),
    y: Number(pos.y),
    z: Number.isFinite(Number(pos.z)) ? Number(pos.z) : 0,
  };
}

function computePlayerFollowPan2d(
  voxels,
  playerId,
  tile,
  zScale,
  semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON,
  projection = "isometric"
) {
  if (!Array.isArray(voxels) || voxels.length === 0) {
    return { panX: 0, panY: 0 };
  }
  const player = voxels.find((item) => isRendererPlayerVoxel(item, playerId, semanticLexicon));
  if (!player) {
    return { panX: 0, panY: 0 };
  }
  const projectionMode = String(projection || "isometric").toLowerCase();
  if (projectionMode === "cardinal") {
    const bounds = computeCardinalContentBounds(voxels, tile, zScale);
    const contentCenterX = (bounds.minX + bounds.maxX) * 0.5;
    const contentCenterY = (bounds.minY + bounds.maxY) * 0.5;
    const playerX = Number(player.x || 0) * tile;
    const playerY = Number(player.y || 0) * tile - Number(player.z || 0) * zScale;
    return {
      panX: -(playerX - contentCenterX),
      panY: -(playerY - contentCenterY),
    };
  }
  const bounds = computeIsoContentBounds(voxels, tile, zScale);
  const contentCenterX = (bounds.minX + bounds.maxX) * 0.5;
  const contentCenterY = (bounds.minY + bounds.maxY) * 0.5;
  const playerIsoX = (Number(player.x || 0) - Number(player.y || 0)) * tile;
  const playerIsoY = (Number(player.x || 0) + Number(player.y || 0)) * (tile * 0.5) - Number(player.z || 0) * zScale;
  return {
    panX: -(playerIsoX - contentCenterX),
    panY: -(playerIsoY - contentCenterY),
  };
}

function computePlayerFollowPan3d(voxels, playerId, tile, zScale, semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON) {
  if (!Array.isArray(voxels) || voxels.length === 0) {
    return { panX: 0, panY: 0 };
  }
  const player = voxels.find((item) => isRendererPlayerVoxel(item, playerId, semanticLexicon));
  if (!player) {
    return { panX: 0, panY: 0 };
  }
  const minX = Math.min(...voxels.map((item) => Number(item.x || 0)));
  const maxX = Math.max(...voxels.map((item) => Number(item.x || 0)));
  const minY = Math.min(...voxels.map((item) => Number(item.y || 0)));
  const maxY = Math.max(...voxels.map((item) => Number(item.y || 0)));
  const minZ = Math.min(...voxels.map((item) => Number(item.z || 0)));
  const maxZ = Math.max(...voxels.map((item) => Number(item.z || 0)));
  const centerX = (minX + maxX) * 0.5;
  const centerY = (minY + maxY) * 0.5;
  const centerZ = (minZ + maxZ) * 0.5;
  const dx = Number(player.x || 0) - centerX;
  const dy = Number(player.y || 0) - centerY;
  const dz = Number(player.z || 0) - centerZ;
  return {
    panX: -((dx - dy) * tile * 0.45),
    panY: -((dx + dy) * tile * 0.2 - dz * zScale * 0.75),
  };
}

function computeIsoContentBounds(voxels, tile, zScale) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  voxels.forEach((item) => {
    const isoX = (Number(item.x || 0) - Number(item.y || 0)) * tile;
    const isoY = (Number(item.x || 0) + Number(item.y || 0)) * (tile * 0.5) - Number(item.z || 0) * zScale;
    minX = Math.min(minX, isoX - tile);
    maxX = Math.max(maxX, isoX + tile);
    minY = Math.min(minY, isoY);
    maxY = Math.max(maxY, isoY + tile + zScale);
  });
  return { minX, maxX, minY, maxY };
}

function computeCardinalContentBounds(voxels, tile, zScale) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  voxels.forEach((item) => {
    const sx = Number(item.x || 0) * tile;
    const sy = Number(item.y || 0) * tile - Number(item.z || 0) * zScale;
    minX = Math.min(minX, sx);
    maxX = Math.max(maxX, sx + tile + zScale);
    minY = Math.min(minY, sy);
    maxY = Math.max(maxY, sy + tile + zScale);
  });
  return { minX, maxX, minY, maxY };
}

function screenToIsoGridPoint2d(screenX, screenY, width, height, voxels, settings, playerZ = 0) {
  if (!Array.isArray(voxels) || voxels.length === 0) {
    return null;
  }
  const tileBase = Number.isFinite(Number(settings.tile)) ? Number(settings.tile) : 18;
  const zScaleBase = Number.isFinite(Number(settings.zScale)) ? Number(settings.zScale) : 8;
  const camera2d = normalizeCamera2d(settings.camera2d);
  const zoom2d = Number(camera2d.zoom || 1);
  const tile = tileBase * zoom2d;
  const zScale = zScaleBase * zoom2d;
  const cameraPanX = Number.isFinite(Number(camera2d.panX)) ? Number(camera2d.panX) : 0;
  const cameraPanY = Number.isFinite(Number(camera2d.panY)) ? Number(camera2d.panY) : 0;
  const projection = String(settings && settings.projection ? settings.projection : "isometric").toLowerCase();
  const bounds = projection === "cardinal"
    ? computeCardinalContentBounds(voxels, tile, zScale)
    : computeIsoContentBounds(voxels, tile, zScale);
  if (!Number.isFinite(bounds.minX) || !Number.isFinite(bounds.minY)) {
    return null;
  }
  const pad = 16;
  const contentWidth = Math.max(1, bounds.maxX - bounds.minX);
  const contentHeight = Math.max(1, bounds.maxY - bounds.minY);
  const offsetX = (width - contentWidth) * 0.5 - bounds.minX + cameraPanX;
  const offsetY = (height - contentHeight) * 0.5 - bounds.minY + pad + cameraPanY;
  if (projection === "cardinal") {
    return {
      x: (screenX - offsetX) / tile,
      y: (screenY - offsetY + playerZ * zScale) / tile,
    };
  }
  const u = (screenX - offsetX) / tile;
  const v = (screenY - offsetY + playerZ * zScale) / (tile * 0.5);
  return {
    x: (u + v) * 0.5,
    y: (v - u) * 0.5,
  };
}

function buildStepDeltaQueue(dx, dy, dz, step) {
  const stepSize = Math.max(0.05, Number(step || 1));
  let remX = Number(dx || 0);
  let remY = Number(dy || 0);
  let remZ = Number(dz || 0);
  const queue = [];
  let guard = 0;
  while ((Math.abs(remX) > 1e-6 || Math.abs(remY) > 1e-6 || Math.abs(remZ) > 1e-6) && guard < 8192) {
    const sx = Math.abs(remX) <= stepSize ? remX : Math.sign(remX) * stepSize;
    const sy = Math.abs(remY) <= stepSize ? remY : Math.sign(remY) * stepSize;
    const sz = Math.abs(remZ) <= stepSize ? remZ : Math.sign(remZ) * stepSize;
    queue.push({ dx: sx, dy: sy, dz: sz });
    remX -= sx;
    remY -= sy;
    remZ -= sz;
    guard += 1;
  }
  return queue;
}

function normalizeFacing(value) {
  const facing = String(value || "").trim().toLowerCase();
  if (facing === "n" || facing === "north" || facing === "up") return "north";
  if (facing === "s" || facing === "south" || facing === "down") return "south";
  if (facing === "w" || facing === "west" || facing === "left") return "west";
  if (facing === "e" || facing === "east" || facing === "right") return "east";
  return "south";
}

function facingFromDelta(dx, dy, fallback = "south") {
  const x = Number(dx || 0);
  const y = Number(dy || 0);
  if (Math.abs(x) < 1e-6 && Math.abs(y) < 1e-6) {
    return normalizeFacing(fallback);
  }
  if (Math.abs(x) > Math.abs(y)) {
    return x > 0 ? "east" : "west";
  }
  return y > 0 ? "south" : "north";
}

const DEFAULT_SHYGAZUN_RENDER_LEXICON = {
  player_markers: [
    "taplayer",
    "player",
    "protagonist",
    "avatar",
    "speaker:player",
    "role:player",
    "entity:player",
  ],
  aliases: {
    role: {
      taplayer: "player",
      tashamowun: "npc",
    },
    type: {
      shy: "pattern",
      tashamowun: "npc",
    },
    material: {},
    layer: {},
  },
};

function deepMergeObjects(base, extra) {
  const left = base && typeof base === "object" ? base : {};
  const right = extra && typeof extra === "object" ? extra : {};
  const out = { ...left };
  Object.entries(right).forEach(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value) && left[key] && typeof left[key] === "object" && !Array.isArray(left[key])) {
      out[key] = deepMergeObjects(left[key], value);
    } else {
      out[key] = value;
    }
  });
  return out;
}

function buildRendererSemanticLexicon(payload, engineState) {
  const payloadObj = payload && typeof payload === "object" ? payload : {};
  const engineObj = engineState && typeof engineState === "object" ? engineState : {};
  const tables = engineObj.tables && typeof engineObj.tables === "object" ? engineObj.tables : {};
  const candidates = [
    payloadObj.shygazun_lexicon,
    payloadObj.semantic_lexicon,
    payloadObj.render_constraints && payloadObj.render_constraints.shygazun_lexicon,
    tables.shygazun_lexicon,
    engineObj.shygazun_lexicon,
  ];
  let merged = deepMergeObjects({}, DEFAULT_SHYGAZUN_RENDER_LEXICON);
  candidates.forEach((candidate) => {
    if (candidate && typeof candidate === "object") {
      merged = deepMergeObjects(merged, candidate);
    }
  });
  const aliases = merged.aliases && typeof merged.aliases === "object" ? merged.aliases : {};
  return {
    ...merged,
    aliases: {
      role: aliases.role && typeof aliases.role === "object" ? aliases.role : {},
      type: aliases.type && typeof aliases.type === "object" ? aliases.type : {},
      material: aliases.material && typeof aliases.material === "object" ? aliases.material : {},
      layer: aliases.layer && typeof aliases.layer === "object" ? aliases.layer : {},
    },
    player_markers: Array.isArray(merged.player_markers) ? merged.player_markers.map((item) => String(item).toLowerCase()) : DEFAULT_SHYGAZUN_RENDER_LEXICON.player_markers,
  };
}

function asLowerToken(value) {
  return String(value || "").trim().toLowerCase();
}

function resolveLexiconAlias(domain, value, lexicon) {
  const raw = String(value || "").trim();
  if (!raw) {
    return raw;
  }
  const aliases = lexicon && lexicon.aliases && typeof lexicon.aliases === "object" ? lexicon.aliases : {};
  const table = aliases[domain] && typeof aliases[domain] === "object" ? aliases[domain] : {};
  const token = raw.toLowerCase();
  const mapped = Object.prototype.hasOwnProperty.call(table, token) ? table[token] : null;
  return mapped ? String(mapped) : raw;
}

function collectSemanticTokens(entry, meta) {
  const tokens = [];
  const add = (value) => {
    const token = asLowerToken(value);
    if (token) {
      tokens.push(token);
    }
  };
  add(entry.type);
  add(entry.kind);
  add(entry.role);
  add(entry.tag);
  add(meta.role);
  add(meta.semantic_role);
  add(meta.semanticRole);
  add(meta.akinenwun);
  const arrays = [
    meta.semantic_tags,
    meta.semanticTags,
    entry.tags,
    entry.semantic_tags,
    entry.semanticTags,
  ];
  arrays.forEach((arr) => {
    if (Array.isArray(arr)) {
      arr.forEach((item) => add(item));
    }
  });
  return tokens;
}

function semanticValueFromTokens(tokens, prefix) {
  const needle = `${String(prefix).toLowerCase()}:`;
  for (const token of tokens) {
    if (token.startsWith(needle) && token.length > needle.length) {
      return token.slice(needle.length);
    }
  }
  return "";
}

function normalizeSceneGraphNode(node, index, semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON) {
  const entry = node && typeof node === "object" ? node : {};
  const meta = entry.metadata && typeof entry.metadata === "object" ? { ...entry.metadata } : {};
  if (typeof entry.layer === "string" && entry.layer) {
    meta.layer = entry.layer;
  }
  if (typeof entry.node_id === "string" && entry.node_id) {
    meta.node_id = entry.node_id;
  }
  if (typeof entry.scene_id === "string" && entry.scene_id) {
    meta.scene_id = entry.scene_id;
  }
  if (typeof entry.realm_id === "string" && entry.realm_id) {
    meta.realm_id = entry.realm_id;
  }
  return normalizeVoxelItem(
    {
      x: entry.x,
      y: entry.y,
      z: entry.z,
      type: entry.kind || entry.tag || entry.node_id || entry.id || ("node_" + index),
      meta
    },
    index,
    semanticLexicon
  );
}

function extractVoxelsFromPayload(payload, semanticLexicon = DEFAULT_SHYGAZUN_RENDER_LEXICON) {
  if (Array.isArray(payload)) {
    return payload.map((item, index) => normalizeVoxelItem(item, index, semanticLexicon));
  }
  if (!payload || typeof payload !== "object") {
    return [];
  }
  const graphNodes = payload.graph && Array.isArray(payload.graph.nodes) ? payload.graph.nodes : null;
  if (graphNodes) {
    return graphNodes.map((node, index) => normalizeSceneGraphNode(node, index, semanticLexicon));
  }
  const directNodes = Array.isArray(payload.nodes) ? payload.nodes : null;
  if (directNodes && directNodes.length > 0 && typeof directNodes[0] === "object" && "node_id" in directNodes[0]) {
    return directNodes.map((node, index) => normalizeSceneGraphNode(node, index, semanticLexicon));
  }
  const candidates = Array.isArray(payload.voxels)
    ? payload.voxels
    : Array.isArray(payload.entities)
      ? payload.entities
      : Array.isArray(payload.points)
        ? payload.points
        : Array.isArray(payload.data)
          ? payload.data
          : [];
  return candidates.map((item, index) => normalizeVoxelItem(item, index, semanticLexicon));
}

function applyVoxelMaterials(voxels, materialsMap, layersMap, atlasMap) {
  if (!Array.isArray(voxels)) {
    return [];
  }
  return voxels.map((voxel) => {
    const materialKey = voxel && voxel.meta && typeof voxel.meta.material === "string"
      ? voxel.meta.material
      : voxel && typeof voxel.material === "string"
        ? voxel.material
        : voxel && typeof voxel.type === "string"
          ? voxel.type
          : null;
    const material = materialKey && materialsMap && materialsMap[materialKey] ? materialsMap[materialKey] : null;
    const layerKey = voxel && voxel.meta && typeof voxel.meta.layer === "string"
      ? voxel.meta.layer
      : voxel && typeof voxel.layer === "string"
        ? voxel.layer
        : null;
    const layer = layerKey && layersMap && layersMap[layerKey] ? layersMap[layerKey] : null;
    let zOffset = layer && Number.isFinite(Number(layer.zOffset)) ? Number(layer.zOffset) : 0;
    if (!zOffset && layerKey) {
      const defaultLayerZ = sceneGraphDefaults && sceneGraphDefaults.layer_z ? sceneGraphDefaults.layer_z : {};
      if (Object.prototype.hasOwnProperty.call(defaultLayerZ, layerKey)) {
        zOffset = defaultLayerZ[layerKey];
      }
    }
    const z = Number.isFinite(Number(voxel.z)) ? Number(voxel.z) + zOffset : zOffset;
    const base = {
      ...voxel,
      z,
      layer: layerKey || voxel.layer || null,
      color: voxel.color || (material ? material.color : voxel.color),
      texture: voxel.texture || (material ? material.texture : voxel.texture),
      textureTop: voxel.textureTop || (material ? material.textureTop : voxel.textureTop),
      textureLeft: voxel.textureLeft || (material ? material.textureLeft : voxel.textureLeft),
      textureRight: voxel.textureRight || (material ? material.textureRight : voxel.textureRight),
      frame: voxel.frame || (material ? material.frame : voxel.frame),
      frameTop: voxel.frameTop || (material ? material.frameTop : voxel.frameTop),
      frameLeft: voxel.frameLeft || (material ? material.frameLeft : voxel.frameLeft),
      frameRight: voxel.frameRight || (material ? material.frameRight : voxel.frameRight)
    };
    const textureRef = applyAtlasToTexture(base.texture, atlasMap);
    const textureTopRef = applyAtlasToTexture(base.textureTop, atlasMap);
    const textureLeftRef = applyAtlasToTexture(base.textureLeft, atlasMap);
    const textureRightRef = applyAtlasToTexture(base.textureRight, atlasMap);
    return {
      ...base,
      texture: textureRef ? textureRef.texture : base.texture,
      frame: textureRef && textureRef.frame ? textureRef.frame : base.frame,
      textureTop: textureTopRef ? textureTopRef.texture : base.textureTop,
      frameTop: textureTopRef && textureTopRef.frame ? textureTopRef.frame : base.frameTop,
      textureLeft: textureLeftRef ? textureLeftRef.texture : base.textureLeft,
      frameLeft: textureLeftRef && textureLeftRef.frame ? textureLeftRef.frame : base.frameLeft,
      textureRight: textureRightRef ? textureRightRef.texture : base.textureRight,
      frameRight: textureRightRef && textureRightRef.frame ? textureRightRef.frame : base.frameRight,
    };
  });
}

function normalizeRenderMode(raw) {
  const s = String(raw || "").toLowerCase();
  if (s === "3d") return "3d";
  if (s === "2d") return "2d";
  return "2.5d";
}

function drawVoxelScene3D(canvas, voxels, settings = {}) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const tile = Number.isFinite(Number(settings.tile)) ? Number(settings.tile) : 18;
  const zScale = Number.isFinite(Number(settings.zScale)) ? Number(settings.zScale) : 8;
  const camera3d = normalizeCamera3d(settings.camera3d);
  const background = typeof settings.background === "string" ? settings.background : "#0b1426";
  const outline = Boolean(settings.outline);
  const outlineColor = typeof settings.outlineColor === "string" ? settings.outlineColor : "#0f203c";
  const edgeGlow = Boolean(settings.edgeGlow);
  const edgeGlowColor = typeof settings.edgeGlowColor === "string" ? settings.edgeGlowColor : outlineColor;
  const edgeGlowStrength = Math.max(0, Math.min(32, Number(settings.edgeGlowStrength ?? 8)));
  const renderScale = clampNumber(settings.renderScale, 1, 4, 1);
  const visualStyle = typeof settings.visualStyle === "string" ? settings.visualStyle : "default";
  const pixelate = Boolean(settings.pixelate);
  const labelModeRaw = typeof settings.labelMode === "string" ? settings.labelMode : "none";
  const classicFalloutShowLabels = Boolean(settings.classicFalloutShowLabels);
  const labelMode =
    String(visualStyle || "").toLowerCase() === "classic_fallout" && !classicFalloutShowLabels
      ? "none"
      : labelModeRaw;
  const labelColor = typeof settings.labelColor === "string" ? settings.labelColor : "#d9e6ff";
  const dpr = (window.devicePixelRatio || 1) * renderScale;
  const width = Math.max(1, canvas.clientWidth);
  const height = Math.max(1, canvas.clientHeight);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.imageSmoothingEnabled = !pixelate;
  ctx.imageSmoothingQuality = pixelate ? "low" : "high";
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);
  if (!voxels || voxels.length === 0) {
    return;
  }

  const yaw = (camera3d.yaw * Math.PI) / 180;
  const pitch = (camera3d.pitch * Math.PI) / 180;
  const cosYaw = Math.cos(yaw);
  const sinYaw = Math.sin(yaw);
  const cosPitch = Math.cos(pitch);
  const sinPitch = Math.sin(pitch);
  const focal = Math.max(150, tile * 16) * camera3d.zoom;
  const worldDepthScale = Math.max(8, tile * 0.75);
  const minX = Math.min(...voxels.map((item) => Number(item.x || 0)));
  const maxX = Math.max(...voxels.map((item) => Number(item.x || 0)));
  const minY = Math.min(...voxels.map((item) => Number(item.y || 0)));
  const maxY = Math.max(...voxels.map((item) => Number(item.y || 0)));
  const minZ = Math.min(...voxels.map((item) => Number(item.z || 0)));
  const maxZ = Math.max(...voxels.map((item) => Number(item.z || 0)));
  const centerWorldX = (minX + maxX) * 0.5;
  const centerWorldY = (minY + maxY) * 0.5;
  const centerWorldZ = (minZ + maxZ) * 0.5;
  const projected = voxels
    .map((item) => {
      const worldX = Number(item.x || 0) - centerWorldX;
      const worldY = Number(item.y || 0) - centerWorldY;
      const worldZ = Number(item.z || 0) - centerWorldZ;
      const rotX = worldX * cosYaw - worldY * sinYaw;
      const rotY = worldX * sinYaw + worldY * cosYaw;
      const rotZ = worldZ;
      const depthY = rotY * cosPitch - rotZ * sinPitch;
      const elevZ = rotY * sinPitch + rotZ * cosPitch;
      const depth = Math.max(-focal * 0.6, depthY * worldDepthScale);
      const scale = focal / Math.max(24, focal + depth);
      return {
        item,
        rotX,
        depthY,
        elevZ,
        scale,
        depthSort: depthY + elevZ * 0.2,
      };
    })
    .sort((a, b) => a.depthSort - b.depthSort);
  const centerX = width * 0.5;
  const centerY = height * 0.66;

  projected.forEach((entry) => {
    const item = entry.item;
    const edgeGlowLocal = resolveVoxelEdgeGlowConfig(item, {
      enabled: edgeGlow,
      color: edgeGlowColor,
      strength: edgeGlowStrength,
    });
    const scale = entry.scale;
    const w = Math.max(2, tile * scale);
    const h = Math.max(2, (tile + zScale) * scale);
    const skew = Math.max(1, Math.abs(Math.sin(yaw)) * tile * 0.6 * scale);
    const rise = Math.max(1, (Math.max(0.25, Math.sin(pitch)) * zScale * 1.1) * scale);
    const sx = centerX + camera3d.panX + (entry.rotX * tile * 1.15 * scale);
    const sy =
      centerY +
      camera3d.panY +
      (entry.depthY * tile * 0.28 * scale) -
      (entry.elevZ * zScale * 1.35 * scale);
    const x0 = sx - (w * 0.5);
    const y0 = sy - h;
    const baseColor = item.color || "#7aa2ff";
    const front = stylizeVoxelColor(baseColor, visualStyle);
    const side = stylizeVoxelColor(shadeVoxel(baseColor, -28), visualStyle);
    const top = stylizeVoxelColor(shadeVoxel(baseColor, 26), visualStyle);
    const highFidelity = isHighFidelityStyle(visualStyle);
    const spritePlane = isSpritePlaneVoxel(item);

    if (spritePlane) {
      const spriteTexture = item.texture || item.textureTop || item.textureLeft || item.textureRight || null;
      const spriteFrame = resolveSpriteFrameForFacing(
        item,
        item.meta && item.meta.spriteFacing ? item.meta.spriteFacing : settings.playerFacing,
        item.frame || item.frameTop || item.frameLeft || item.frameRight || null,
        settings
      );
      const metrics = resolveSpritePlaneMetrics(item, tile);
      const spriteW = Math.max(6, metrics.w * Math.max(0.35, scale));
      const spriteH = Math.max(8, metrics.h * Math.max(0.35, scale));
      const spriteX = sx - spriteW * 0.5;
      const spriteY = y0 + h - spriteH;
      ctx.save();
      ctx.fillStyle = "rgba(0,0,0,0.26)";
      ctx.beginPath();
      ctx.ellipse(sx, y0 + h + Math.max(2, tile * 0.18), Math.max(4, spriteW * 0.35), Math.max(2, tile * 0.16), 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      if (spriteTexture) {
        const img = getTextureImage(spriteTexture);
        if (img && img.complete && img.naturalWidth > 0) {
          if (spriteFrame && Number.isFinite(Number(spriteFrame.w)) && Number.isFinite(Number(spriteFrame.h))) {
            ctx.drawImage(
              img,
              Number(spriteFrame.x || 0),
              Number(spriteFrame.y || 0),
              Number(spriteFrame.w || img.naturalWidth),
              Number(spriteFrame.h || img.naturalHeight),
              spriteX,
              spriteY,
              spriteW,
              spriteH
            );
          } else {
            ctx.drawImage(img, spriteX, spriteY, spriteW, spriteH);
          }
        } else {
          ctx.fillStyle = front;
          ctx.fillRect(spriteX, spriteY, spriteW, spriteH);
        }
      } else {
        const gradSprite = ctx.createLinearGradient(spriteX, spriteY, spriteX, spriteY + spriteH);
        gradSprite.addColorStop(0, stylizeVoxelColor(shadeVoxel(baseColor, 20), visualStyle));
        gradSprite.addColorStop(1, stylizeVoxelColor(shadeVoxel(baseColor, -18), visualStyle));
        ctx.fillStyle = gradSprite;
        ctx.fillRect(spriteX, spriteY, spriteW, spriteH);
      }
      if (outline) {
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(spriteX, spriteY, spriteW, spriteH);
      }
      if (labelMode !== "none") {
        const label = String(item.id || item.type || "");
        if (label) {
          ctx.fillStyle = labelColor;
          ctx.font = "11px monospace";
          ctx.fillText(label, spriteX, spriteY - 4);
        }
      }
      return;
    }

    if (highFidelity) {
      const shadowAlpha = Math.max(0.06, 0.22 - Number(item.z || 0) * 0.03);
      ctx.save();
      ctx.fillStyle = `rgba(0,0,0,${shadowAlpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.ellipse(sx, y0 + h + Math.max(2, tile * 0.18), Math.max(4, w * 0.55), Math.max(2, tile * 0.2), 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0 + w, y0);
    ctx.lineTo(x0 + w, y0 + h);
    ctx.lineTo(x0, y0 + h);
    ctx.closePath();
    if (highFidelity) {
      const gradFront = ctx.createLinearGradient(x0, y0, x0, y0 + h);
      gradFront.addColorStop(0, stylizeVoxelColor(shadeVoxel(baseColor, 14), visualStyle));
      gradFront.addColorStop(0.58, front);
      gradFront.addColorStop(1, stylizeVoxelColor(shadeVoxel(baseColor, -18), visualStyle));
      ctx.fillStyle = gradFront;
    } else {
      ctx.fillStyle = front;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }

    ctx.beginPath();
    if (sinYaw >= 0) {
      ctx.moveTo(x0 + w, y0);
      ctx.lineTo(x0 + w + skew, y0 - rise);
      ctx.lineTo(x0 + w + skew, y0 + h - rise);
      ctx.lineTo(x0 + w, y0 + h);
    } else {
      ctx.moveTo(x0, y0);
      ctx.lineTo(x0 - skew, y0 - rise);
      ctx.lineTo(x0 - skew, y0 + h - rise);
      ctx.lineTo(x0, y0 + h);
    }
    ctx.closePath();
    if (highFidelity) {
      const sideX0 = sinYaw >= 0 ? x0 + w : x0 - skew;
      const sideX1 = sinYaw >= 0 ? x0 + w + skew : x0;
      const gradSide = ctx.createLinearGradient(sideX0, y0, sideX1, y0 + h);
      gradSide.addColorStop(0, stylizeVoxelColor(shadeVoxel(baseColor, -8), visualStyle));
      gradSide.addColorStop(1, stylizeVoxelColor(shadeVoxel(baseColor, -34), visualStyle));
      ctx.fillStyle = gradSide;
    } else {
      ctx.fillStyle = side;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }

    ctx.beginPath();
    if (sinYaw >= 0) {
      ctx.moveTo(x0, y0);
      ctx.lineTo(x0 + w, y0);
      ctx.lineTo(x0 + w + skew, y0 - rise);
      ctx.lineTo(x0 + skew, y0 - rise);
    } else {
      ctx.moveTo(x0, y0);
      ctx.lineTo(x0 + w, y0);
      ctx.lineTo(x0 + w - skew, y0 - rise);
      ctx.lineTo(x0 - skew, y0 - rise);
    }
    ctx.closePath();
    if (highFidelity) {
      const gradTop = ctx.createLinearGradient(x0, y0 - rise, x0 + w + skew, y0);
      gradTop.addColorStop(0, stylizeVoxelColor(shadeVoxel(baseColor, 34), visualStyle));
      gradTop.addColorStop(1, top);
      ctx.fillStyle = gradTop;
    } else {
      ctx.fillStyle = top;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }

    if (labelMode !== "none") {
      let label = "";
      if (labelMode === "type") label = String(item.type || "");
      else if (labelMode === "z") label = String(item.z);
      else if (labelMode === "layer") label = String(item.layer || item.meta?.layer || "");
      if (label) {
        ctx.fillStyle = labelColor;
        ctx.font = "11px monospace";
        ctx.fillText(label, x0 + 3, y0 - 4);
      }
    }
  });
}

function drawVoxelSceneCardinal(canvas, ctx, voxels, settings, shared) {
  const {
    tile,
    zScale,
    outline,
    outlineColor,
    edgeGlow,
    edgeGlowColor,
    edgeGlowStrength,
    visualStyle,
    labelMode,
    labelColor,
    lightingEnabled,
    ambient,
    intensity,
    nx,
    ny,
    nz,
    width,
    height,
    cameraPanX,
    cameraPanY,
  } = shared;
  const sorted = voxels.slice().sort((a, b) => {
    const ay = Number(a.y || 0);
    const by = Number(b.y || 0);
    if (ay !== by) return ay - by;
    const ax = Number(a.x || 0);
    const bx = Number(b.x || 0);
    if (ax !== bx) return ax - bx;
    return Number(a.z || 0) - Number(b.z || 0);
  });
  const bounds = computeCardinalContentBounds(sorted, tile, zScale);
  if (!Number.isFinite(bounds.minX) || !Number.isFinite(bounds.minY)) {
    return;
  }
  const pad = 16;
  const contentWidth = Math.max(1, bounds.maxX - bounds.minX);
  const contentHeight = Math.max(1, bounds.maxY - bounds.minY);
  const offsetX = (width - contentWidth) * 0.5 - bounds.minX + cameraPanX;
  const offsetY = (height - contentHeight) * 0.5 - bounds.minY + pad + cameraPanY;
  sorted.forEach((item) => {
    const edgeGlowLocal = resolveVoxelEdgeGlowConfig(item, {
      enabled: edgeGlow,
      color: edgeGlowColor,
      strength: edgeGlowStrength,
    });
    const sx = Number(item.x || 0) * tile + offsetX;
    const sy = Number(item.y || 0) * tile - Number(item.z || 0) * zScale + offsetY;
    const baseColor = item.color;
    const topRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, nz) * intensity) : baseColor;
    const southRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, -ny) * intensity) : shadeVoxel(baseColor, -24);
    const eastRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, nx) * intensity) : shadeVoxel(baseColor, -16);
    const top = stylizeVoxelColor(topRaw, visualStyle);
    const south = stylizeVoxelColor(southRaw, visualStyle);
    const east = stylizeVoxelColor(eastRaw, visualStyle);
    const highFidelity = isHighFidelityStyle(visualStyle);
    const redraw = () => drawVoxelScene(canvas, voxels, settings);
    const topTexture = item.textureTop || item.texture || null;
    const southTexture = item.textureLeft || item.texture || null;
    const eastTexture = item.textureRight || item.texture || null;
    const topFrame = item.frameTop || item.frame || null;
    const southFrame = item.frameLeft || item.frame || null;
    const eastFrame = item.frameRight || item.frame || null;
    const spritePlane = isSpritePlaneVoxel(item);
    if (spritePlane) {
      const spriteTexture = item.texture || item.textureTop || item.textureLeft || item.textureRight || null;
      const spriteFrame = resolveSpriteFrameForFacing(
        item,
        item.meta && item.meta.spriteFacing ? item.meta.spriteFacing : settings.playerFacing,
        item.frame || item.frameTop || item.frameLeft || item.frameRight || null,
        settings
      );
      const metrics = resolveSpritePlaneMetrics(item, tile);
      const spriteX = sx + tile * 0.5 - metrics.w * 0.5;
      const spriteY = sy + tile + zScale - metrics.h - metrics.anchorY * 0.15;
      const shadowW = Math.max(4, metrics.w * 0.58);
      const shadowH = Math.max(2, zScale * 0.55);
      ctx.save();
      ctx.fillStyle = "rgba(0,0,0,0.22)";
      ctx.fillRect(sx + tile * 0.5 - shadowW * 0.5, sy + tile + zScale - 1, shadowW, shadowH);
      ctx.restore();
      if (spriteTexture) {
        const img = getTextureImage(spriteTexture, redraw);
        if (img && img.complete && img.naturalWidth > 0) {
          if (spriteFrame && Number.isFinite(Number(spriteFrame.w)) && Number.isFinite(Number(spriteFrame.h))) {
            ctx.drawImage(
              img,
              Number(spriteFrame.x || 0),
              Number(spriteFrame.y || 0),
              Number(spriteFrame.w || img.naturalWidth),
              Number(spriteFrame.h || img.naturalHeight),
              spriteX,
              spriteY,
              metrics.w,
              metrics.h
            );
          } else {
            ctx.drawImage(img, spriteX, spriteY, metrics.w, metrics.h);
          }
        } else {
          ctx.fillStyle = top;
          ctx.fillRect(spriteX, spriteY, metrics.w, metrics.h);
        }
      } else {
        const gradSprite = ctx.createLinearGradient(spriteX, spriteY, spriteX, spriteY + metrics.h);
        gradSprite.addColorStop(0, stylizeVoxelColor(shadeVoxel(topRaw, 18), visualStyle));
        gradSprite.addColorStop(1, stylizeVoxelColor(shadeVoxel(topRaw, -18), visualStyle));
        ctx.fillStyle = gradSprite;
        ctx.fillRect(spriteX, spriteY, metrics.w, metrics.h);
      }
      if (outline) {
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(spriteX, spriteY, metrics.w, metrics.h);
      }
      if (labelMode !== "none") {
        const labelText = String(item.id || item.type || "");
        if (labelText) {
          ctx.fillStyle = labelColor;
          ctx.font = "11px monospace";
          ctx.fillText(labelText, spriteX, spriteY - 4);
        }
      }
      return;
    }

    if (highFidelity) {
      const shadowAlpha = Math.max(0.05, 0.18 - Number(item.z || 0) * 0.02);
      ctx.save();
      ctx.fillStyle = `rgba(0,0,0,${shadowAlpha.toFixed(3)})`;
      ctx.fillRect(sx + tile * 0.08, sy + tile + zScale - 1, tile * 0.84, Math.max(2, zScale * 0.45));
      ctx.restore();
      const gradTop = ctx.createLinearGradient(sx, sy, sx, sy + tile);
      gradTop.addColorStop(0, stylizeVoxelColor(shadeVoxel(topRaw, 18), visualStyle));
      gradTop.addColorStop(1, top);
      ctx.fillStyle = gradTop;
    } else {
      ctx.fillStyle = top;
    }
    ctx.fillRect(sx, sy, tile, tile);
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(sx, sy, tile, tile);
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.strokeRect(sx, sy, tile, tile);
      ctx.restore();
    }
    if (topTexture) {
      const img = getTextureImage(topTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        if (topFrame && Number.isFinite(Number(topFrame.w)) && Number.isFinite(Number(topFrame.h))) {
          ctx.drawImage(
            img,
            Number(topFrame.x || 0),
            Number(topFrame.y || 0),
            Number(topFrame.w || img.naturalWidth),
            Number(topFrame.h || img.naturalHeight),
            sx,
            sy,
            tile,
            tile
          );
        } else {
          ctx.drawImage(img, sx, sy, tile, tile);
        }
      }
    }

    if (highFidelity) {
      const gradSouth = ctx.createLinearGradient(sx, sy + tile, sx, sy + tile + zScale);
      gradSouth.addColorStop(0, stylizeVoxelColor(shadeVoxel(southRaw, 8), visualStyle));
      gradSouth.addColorStop(1, stylizeVoxelColor(shadeVoxel(southRaw, -16), visualStyle));
      ctx.fillStyle = gradSouth;
    } else {
      ctx.fillStyle = south;
    }
    ctx.fillRect(sx, sy + tile, tile, zScale);
    if (highFidelity) {
      const gradEast = ctx.createLinearGradient(sx + tile, sy, sx + tile + zScale, sy + tile);
      gradEast.addColorStop(0, stylizeVoxelColor(shadeVoxel(eastRaw, 6), visualStyle));
      gradEast.addColorStop(1, stylizeVoxelColor(shadeVoxel(eastRaw, -18), visualStyle));
      ctx.fillStyle = gradEast;
    } else {
      ctx.fillStyle = east;
    }
    ctx.fillRect(sx + tile, sy, zScale, tile);
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(sx, sy + tile, tile, zScale);
      ctx.strokeRect(sx + tile, sy, zScale, tile);
    }
    if (southTexture) {
      const img = getTextureImage(southTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        if (southFrame && Number.isFinite(Number(southFrame.w)) && Number.isFinite(Number(southFrame.h))) {
          ctx.drawImage(
            img,
            Number(southFrame.x || 0),
            Number(southFrame.y || 0),
            Number(southFrame.w || img.naturalWidth),
            Number(southFrame.h || img.naturalHeight),
            sx,
            sy + tile,
            tile,
            zScale
          );
        } else {
          ctx.drawImage(img, sx, sy + tile, tile, zScale);
        }
      }
    }
    if (eastTexture) {
      const img = getTextureImage(eastTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        if (eastFrame && Number.isFinite(Number(eastFrame.w)) && Number.isFinite(Number(eastFrame.h))) {
          ctx.drawImage(
            img,
            Number(eastFrame.x || 0),
            Number(eastFrame.y || 0),
            Number(eastFrame.w || img.naturalWidth),
            Number(eastFrame.h || img.naturalHeight),
            sx + tile,
            sy,
            zScale,
            tile
          );
        } else {
          ctx.drawImage(img, sx + tile, sy, zScale, tile);
        }
      }
    }
    if (labelMode !== "none") {
      let labelText = "";
      if (labelMode === "type") labelText = String(item.type || "");
      else if (labelMode === "z") labelText = String(item.z || 0);
      else if (labelMode === "layer") labelText = String(item.layer || "");
      if (labelText) {
        ctx.fillStyle = labelColor;
        ctx.font = "11px monospace";
        ctx.fillText(labelText, sx + 2, sy - 4);
      }
    }
  });
}

function drawVoxelScene2D(canvas, ctx, voxels, settings, shared) {
  // Plain top-down 2D: x→canvas-x, y→canvas-y, z→draw order only.
  const {
    tile,
    outline,
    outlineColor,
    edgeGlow,
    edgeGlowColor,
    edgeGlowStrength,
    visualStyle,
    labelMode,
    labelColor,
    lightingEnabled,
    ambient,
    intensity,
    nz,
    width,
    height,
    cameraPanX,
    cameraPanY,
  } = shared;

  // Sort: z ASC (ground first), then y ASC within same z (painter's algorithm)
  const sorted = voxels.slice().sort((a, b) => {
    const az = Number(a.z || 0), bz = Number(b.z || 0);
    if (az !== bz) return az - bz;
    return Number(a.y || 0) - Number(b.y || 0);
  });

  if (sorted.length === 0) return;

  const xs = sorted.map((v) => Number(v.x || 0));
  const ys = sorted.map((v) => Number(v.y || 0));
  const minCX = Math.min(...xs) * tile;
  const maxCX = (Math.max(...xs) + 1) * tile;
  const minCY = Math.min(...ys) * tile;
  const maxCY = (Math.max(...ys) + 1) * tile;
  const offsetX = (width  - (maxCX - minCX)) * 0.5 - minCX + cameraPanX;
  const offsetY = (height - (maxCY - minCY)) * 0.5 - minCY + cameraPanY;

  const redraw = () => drawVoxelScene(canvas, voxels, settings);

  sorted.forEach((item) => {
    const sx = Number(item.x || 0) * tile + offsetX;
    const sy = Number(item.y || 0) * tile + offsetY;

    const baseColor = item.color;
    // In 2D top-down, only the top face is visible — light it with nz (up component)
    const topRaw = lightingEnabled
      ? shadeColor(baseColor, ambient + Math.max(0, nz) * intensity)
      : baseColor;
    const faceColor = stylizeVoxelColor(topRaw, visualStyle);

    const topTexture = item.textureTop || item.texture || null;
    const topFrame   = item.frameTop   || item.frame   || null;

    const edgeGlowLocal = resolveVoxelEdgeGlowConfig(item, {
      enabled: edgeGlow, color: edgeGlowColor, strength: edgeGlowStrength,
    });

    if (edgeGlowLocal.enabled && edgeGlowLocal.strength > 0) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur  = edgeGlowLocal.strength;
    }

    if (topTexture) {
      const img = getTextureImage(topTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        if (topFrame && Number.isFinite(Number(topFrame.w))) {
          ctx.drawImage(
            img,
            Number(topFrame.x || 0), Number(topFrame.y || 0),
            Number(topFrame.w), Number(topFrame.h || topFrame.w),
            sx, sy, tile, tile
          );
        } else {
          ctx.drawImage(img, sx, sy, tile, tile);
        }
      } else {
        ctx.fillStyle = faceColor;
        ctx.fillRect(sx, sy, tile, tile);
      }
    } else {
      ctx.fillStyle = faceColor;
      ctx.fillRect(sx, sy, tile, tile);
    }

    if (edgeGlowLocal.enabled && edgeGlowLocal.strength > 0) {
      ctx.restore();
    }

    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 0.5;
      ctx.strokeRect(sx, sy, tile, tile);
    }

    if (labelMode !== "none") {
      let labelText = "";
      if      (labelMode === "type")  labelText = String(item.type  || "");
      else if (labelMode === "z")     labelText = String(item.z     || 0);
      else if (labelMode === "layer") labelText = String(item.layer || "");
      if (labelText) {
        ctx.fillStyle = labelColor;
        ctx.font = "10px monospace";
        ctx.fillText(labelText, sx + 2, sy + 11);
      }
    }
  });
}

function drawVoxelScene(canvas, voxels, settings = {}) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const renderMode = normalizeRenderMode(settings.renderMode);
  if (renderMode === "3d") {
    drawVoxelScene3D(canvas, voxels, settings);
    return;
  }
  const tileBase = Number.isFinite(Number(settings.tile)) ? Number(settings.tile) : 18;
  const zScaleBase = Number.isFinite(Number(settings.zScale)) ? Number(settings.zScale) : 8;
  const background = typeof settings.background === "string" ? settings.background : "#0b1426";
  const outline = Boolean(settings.outline);
  const outlineColor = typeof settings.outlineColor === "string" ? settings.outlineColor : "#0f203c";
  const edgeGlow = Boolean(settings.edgeGlow);
  const edgeGlowColor = typeof settings.edgeGlowColor === "string" ? settings.edgeGlowColor : outlineColor;
  const edgeGlowStrength = Math.max(0, Math.min(32, Number(settings.edgeGlowStrength ?? 8)));
  const renderScale = clampNumber(settings.renderScale, 1, 4, 1);
  const visualStyle = typeof settings.visualStyle === "string" ? settings.visualStyle : "default";
  const pixelate = Boolean(settings.pixelate);
  const labelModeRaw = typeof settings.labelMode === "string" ? settings.labelMode : "none";
  const classicFalloutShowLabels = Boolean(settings.classicFalloutShowLabels);
  const labelMode =
    String(visualStyle || "").toLowerCase() === "classic_fallout" && !classicFalloutShowLabels
      ? "none"
      : labelModeRaw;
  const labelColor = typeof settings.labelColor === "string" ? settings.labelColor : "#d9e6ff";
  const projection = String(settings.projection || "isometric").toLowerCase();
  const camera2d = normalizeCamera2d(settings.camera2d);
  const zoom2d = Number(camera2d.zoom || 1);
  const tile = tileBase * zoom2d;
  const zScale = zScaleBase * zoom2d;
  const cameraPanX = Number.isFinite(Number(camera2d.panX)) ? Number(camera2d.panX) : 0;
  const cameraPanY = Number.isFinite(Number(camera2d.panY)) ? Number(camera2d.panY) : 0;
  const lighting = settings.lighting || {};
  const rose = settings.rose || {};
  const roseEnabled = Boolean(rose.enabled);
  const roseStrength = Math.max(0, Math.min(1, Number(rose.strength ?? 0.35)));
  const roseData = rose && typeof rose.data === "object" ? rose.data : null;
  const lightingEnabled = Boolean(lighting.enabled) || (roseEnabled && Boolean(roseData));
  const lightX = Number.isFinite(Number(lighting.x)) ? Number(lighting.x) : 0.4;
  const lightY = Number.isFinite(Number(lighting.y)) ? Number(lighting.y) : -0.6;
  const lightZ = Number.isFinite(Number(lighting.z)) ? Number(lighting.z) : 0.7;
  const lightMag = Math.sqrt(lightX * lightX + lightY * lightY + lightZ * lightZ) || 1;
  let nx = lightX / lightMag;
  let ny = lightY / lightMag;
  let nz = lightZ / lightMag;
  let ambient = Math.max(0, Math.min(1, Number(lighting.ambient ?? 0.35)));
  let intensity = Math.max(0, Math.min(2, Number(lighting.intensity ?? 0.85)));
  if (roseEnabled && roseData && roseStrength > 0) {
    const roseVector = roseData.vector && typeof roseData.vector === "object" ? roseData.vector : {};
    const roseX = Number.isFinite(Number(roseVector.x)) ? Number(roseVector.x) : 0;
    const roseY = Number.isFinite(Number(roseVector.y)) ? Number(roseVector.y) : 0;
    const roseScalars = Array.isArray(roseData.scalars) ? roseData.scalars : [];
    const roseScalar = roseScalars.length
      ? roseScalars.reduce((acc, value) => acc + Number(value || 0), 0) / roseScalars.length
      : 0;
    const scalarNorm = Math.max(0, Math.min(1, roseScalar / 11));
    const rosePolarity = Number.isFinite(Number(roseData.polarity)) ? Number(roseData.polarity) : 0;
    const mix = 0.35 * roseStrength;
    const mixedX = lightX + roseX * mix * (rosePolarity === 0 ? 1 : Math.sign(rosePolarity));
    const mixedY = lightY + roseY * mix * (rosePolarity === 0 ? 1 : Math.sign(rosePolarity));
    const mixedMag = Math.sqrt(mixedX * mixedX + mixedY * mixedY + lightZ * lightZ) || 1;
    const mixedNx = mixedX / mixedMag;
    const mixedNy = mixedY / mixedMag;
    const mixedNz = lightZ / mixedMag;
    ambient = Math.max(0, Math.min(1, ambient + scalarNorm * 0.25 * roseStrength));
    intensity = Math.max(0, Math.min(2, intensity + scalarNorm * 0.35 * roseStrength));
    const previousNx = nx;
    const previousNy = ny;
    const previousNz = nz;
    nx = mixedNx;
    ny = mixedNy;
    nz = mixedNz;
    if (!Number.isFinite(nx) || !Number.isFinite(ny) || !Number.isFinite(nz)) {
      nx = previousNx;
      ny = previousNy;
      nz = previousNz;
    }
  }
  const dpr = (window.devicePixelRatio || 1) * renderScale;
  const width = Math.max(1, canvas.clientWidth);
  const height = Math.max(1, canvas.clientHeight);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.imageSmoothingEnabled = !pixelate;
  ctx.imageSmoothingQuality = pixelate ? "low" : "high";
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);
  if (!voxels || voxels.length == 0) {
    return;
  }
  const shared2d = {
    tile, zScale, outline, outlineColor,
    edgeGlow, edgeGlowColor, edgeGlowStrength,
    visualStyle, labelMode, labelColor,
    lightingEnabled, ambient, intensity,
    nx, ny, nz, width, height, cameraPanX, cameraPanY,
  };
  if (renderMode === "2d") {
    drawVoxelScene2D(canvas, ctx, voxels, settings, shared2d);
    return;
  }
  if (projection === "cardinal") {
    drawVoxelSceneCardinal(canvas, ctx, voxels, settings, shared2d);
    return;
  }
  const sorted = voxels.slice().sort((a, b) => (a.x + a.y + a.z) - (b.x + b.y + b.z));
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  sorted.forEach((item) => {
    const isoX = (item.x - item.y) * tile;
    const isoY = (item.x + item.y) * (tile * 0.5) - item.z * zScale;
    minX = Math.min(minX, isoX - tile);
    maxX = Math.max(maxX, isoX + tile);
    minY = Math.min(minY, isoY);
    maxY = Math.max(maxY, isoY + tile + zScale);
  });
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return;
  }
  const pad = 16;
  const contentWidth = Math.max(1, maxX - minX);
  const contentHeight = Math.max(1, maxY - minY);
  const offsetX = (width - contentWidth) * 0.5 - minX + cameraPanX;
  const offsetY = (height - contentHeight) * 0.5 - minY + pad + cameraPanY;
  sorted.forEach((item) => {
    const edgeGlowLocal = resolveVoxelEdgeGlowConfig(item, {
      enabled: edgeGlow,
      color: edgeGlowColor,
      strength: edgeGlowStrength,
    });
    const isoX = (item.x - item.y) * tile + offsetX;
    const isoY = (item.x + item.y) * (tile * 0.5) - item.z * zScale + offsetY;
    const baseColor = item.color;
    const topRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, nz) * intensity) : baseColor;
    const leftRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, -nx) * intensity) : shadeVoxel(baseColor, -30);
    const rightRaw = lightingEnabled ? shadeColor(baseColor, ambient + Math.max(0, nx) * intensity) : shadeVoxel(baseColor, 20);
    const top = stylizeVoxelColor(topRaw, visualStyle);
    const left = stylizeVoxelColor(leftRaw, visualStyle);
    const right = stylizeVoxelColor(rightRaw, visualStyle);
    const highFidelity = isHighFidelityStyle(visualStyle);
    const redraw = () => drawVoxelScene(canvas, voxels, settings);
    const topTexture = item.textureTop || item.texture || null;
    const leftTexture = item.textureLeft || item.texture || null;
    const rightTexture = item.textureRight || item.texture || null;
    const topFrame = item.frameTop || item.frame || null;
    const leftFrame = item.frameLeft || item.frame || null;
    const rightFrame = item.frameRight || item.frame || null;
    const spritePlane = isSpritePlaneVoxel(item);
    if (spritePlane) {
      const spriteTexture = item.texture || item.textureTop || item.textureLeft || item.textureRight || null;
      const spriteFrame = resolveSpriteFrameForFacing(
        item,
        item.meta && item.meta.spriteFacing ? item.meta.spriteFacing : settings.playerFacing,
        item.frame || item.frameTop || item.frameLeft || item.frameRight || null,
        settings
      );
      const metrics = resolveSpritePlaneMetrics(item, tile);
      const spriteX = isoX - metrics.w * 0.5;
      const spriteY = isoY + tile + zScale * 0.5 - metrics.h;
      ctx.save();
      ctx.fillStyle = "rgba(0,0,0,0.24)";
      ctx.beginPath();
      ctx.ellipse(isoX, isoY + tile + zScale * 0.6, Math.max(4, metrics.w * 0.33), Math.max(2, tile * 0.18), 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      if (spriteTexture) {
        const img = getTextureImage(spriteTexture, redraw);
        if (img && img.complete && img.naturalWidth > 0) {
          if (spriteFrame && Number.isFinite(Number(spriteFrame.w)) && Number.isFinite(Number(spriteFrame.h))) {
            ctx.drawImage(
              img,
              Number(spriteFrame.x || 0),
              Number(spriteFrame.y || 0),
              Number(spriteFrame.w || img.naturalWidth),
              Number(spriteFrame.h || img.naturalHeight),
              spriteX,
              spriteY,
              metrics.w,
              metrics.h
            );
          } else {
            ctx.drawImage(img, spriteX, spriteY, metrics.w, metrics.h);
          }
        } else {
          ctx.fillStyle = top;
          ctx.fillRect(spriteX, spriteY, metrics.w, metrics.h);
        }
      } else {
        const gradSprite = ctx.createLinearGradient(spriteX, spriteY, spriteX, spriteY + metrics.h);
        gradSprite.addColorStop(0, stylizeVoxelColor(shadeVoxel(topRaw, 16), visualStyle));
        gradSprite.addColorStop(1, stylizeVoxelColor(shadeVoxel(topRaw, -22), visualStyle));
        ctx.fillStyle = gradSprite;
        ctx.fillRect(spriteX, spriteY, metrics.w, metrics.h);
      }
      if (outline) {
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(spriteX, spriteY, metrics.w, metrics.h);
      }
      if (labelMode && labelMode !== "none") {
        const labelText = String(item.id || item.type || "");
        if (labelText) {
          ctx.fillStyle = labelColor;
          ctx.font = "11px monospace";
          ctx.fillText(labelText, spriteX, spriteY - 4);
        }
      }
      return;
    }
    if (highFidelity) {
      const shadowAlpha = Math.max(0.05, 0.2 - Number(item.z || 0) * 0.02);
      ctx.save();
      ctx.fillStyle = `rgba(0,0,0,${shadowAlpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.ellipse(isoX, isoY + tile + zScale * 0.55, tile * 0.7, Math.max(2, tile * 0.24), 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
    ctx.beginPath();
    ctx.moveTo(isoX, isoY);
    ctx.lineTo(isoX + tile, isoY + tile * 0.5);
    ctx.lineTo(isoX, isoY + tile);
    ctx.lineTo(isoX - tile, isoY + tile * 0.5);
    ctx.closePath();
    if (highFidelity) {
      const gradTop = ctx.createLinearGradient(isoX - tile, isoY, isoX + tile, isoY + tile);
      gradTop.addColorStop(0, stylizeVoxelColor(shadeVoxel(topRaw, 20), visualStyle));
      gradTop.addColorStop(1, top);
      ctx.fillStyle = gradTop;
    } else {
      ctx.fillStyle = top;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }
    if (topTexture) {
      const img = getTextureImage(topTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(isoX, isoY);
        ctx.lineTo(isoX + tile, isoY + tile * 0.5);
        ctx.lineTo(isoX, isoY + tile);
        ctx.lineTo(isoX - tile, isoY + tile * 0.5);
        ctx.closePath();
        ctx.clip();
        const targetX = isoX - tile;
        const targetY = isoY;
        const targetW = tile * 2;
        const targetH = tile;
        if (topFrame && Number.isFinite(Number(topFrame.w)) && Number.isFinite(Number(topFrame.h))) {
          const sx = Number(topFrame.x || 0);
          const sy = Number(topFrame.y || 0);
          const sw = Number(topFrame.w || img.naturalWidth);
          const sh = Number(topFrame.h || img.naturalHeight);
          ctx.drawImage(img, sx, sy, sw, sh, targetX, targetY, targetW, targetH);
        } else {
          ctx.drawImage(img, targetX, targetY, targetW, targetH);
        }
        ctx.restore();
      }
    }
    ctx.beginPath();
    ctx.moveTo(isoX - tile, isoY + tile * 0.5);
    ctx.lineTo(isoX, isoY + tile);
    ctx.lineTo(isoX, isoY + tile + zScale);
    ctx.lineTo(isoX - tile, isoY + tile * 0.5 + zScale);
    ctx.closePath();
    if (highFidelity) {
      const gradLeft = ctx.createLinearGradient(isoX - tile, isoY + tile * 0.5, isoX, isoY + tile + zScale);
      gradLeft.addColorStop(0, stylizeVoxelColor(shadeVoxel(leftRaw, 8), visualStyle));
      gradLeft.addColorStop(1, stylizeVoxelColor(shadeVoxel(leftRaw, -14), visualStyle));
      ctx.fillStyle = gradLeft;
    } else {
      ctx.fillStyle = left;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }
    if (leftTexture) {
      const img = getTextureImage(leftTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(isoX - tile, isoY + tile * 0.5);
        ctx.lineTo(isoX, isoY + tile);
        ctx.lineTo(isoX, isoY + tile + zScale);
        ctx.lineTo(isoX - tile, isoY + tile * 0.5 + zScale);
        ctx.closePath();
        ctx.clip();
        const targetX = isoX - tile;
        const targetY = isoY + tile * 0.5;
        const targetW = tile;
        const targetH = tile + zScale;
        if (leftFrame && Number.isFinite(Number(leftFrame.w)) && Number.isFinite(Number(leftFrame.h))) {
          const sx = Number(leftFrame.x || 0);
          const sy = Number(leftFrame.y || 0);
          const sw = Number(leftFrame.w || img.naturalWidth);
          const sh = Number(leftFrame.h || img.naturalHeight);
          ctx.drawImage(img, sx, sy, sw, sh, targetX, targetY, targetW, targetH);
        } else {
          ctx.drawImage(img, targetX, targetY, targetW, targetH);
        }
        ctx.restore();
      }
    }
    ctx.beginPath();
    ctx.moveTo(isoX + tile, isoY + tile * 0.5);
    ctx.lineTo(isoX, isoY + tile);
    ctx.lineTo(isoX, isoY + tile + zScale);
    ctx.lineTo(isoX + tile, isoY + tile * 0.5 + zScale);
    ctx.closePath();
    if (highFidelity) {
      const gradRight = ctx.createLinearGradient(isoX + tile, isoY + tile * 0.5, isoX, isoY + tile + zScale);
      gradRight.addColorStop(0, stylizeVoxelColor(shadeVoxel(rightRaw, 10), visualStyle));
      gradRight.addColorStop(1, stylizeVoxelColor(shadeVoxel(rightRaw, -16), visualStyle));
      ctx.fillStyle = gradRight;
    } else {
      ctx.fillStyle = right;
    }
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outlineColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (edgeGlowLocal.enabled) {
      ctx.save();
      ctx.shadowColor = edgeGlowLocal.color;
      ctx.shadowBlur = edgeGlowLocal.strength;
      ctx.strokeStyle = edgeGlowLocal.color;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }
    if (rightTexture) {
      const img = getTextureImage(rightTexture, redraw);
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(isoX + tile, isoY + tile * 0.5);
        ctx.lineTo(isoX, isoY + tile);
        ctx.lineTo(isoX, isoY + tile + zScale);
        ctx.lineTo(isoX + tile, isoY + tile * 0.5 + zScale);
        ctx.closePath();
        ctx.clip();
        const targetX = isoX;
        const targetY = isoY + tile * 0.5;
        const targetW = tile;
        const targetH = tile + zScale;
        if (rightFrame && Number.isFinite(Number(rightFrame.w)) && Number.isFinite(Number(rightFrame.h))) {
          const sx = Number(rightFrame.x || 0);
          const sy = Number(rightFrame.y || 0);
          const sw = Number(rightFrame.w || img.naturalWidth);
          const sh = Number(rightFrame.h || img.naturalHeight);
          ctx.drawImage(img, sx, sy, sw, sh, targetX, targetY, targetW, targetH);
        } else {
          ctx.drawImage(img, targetX, targetY, targetW, targetH);
        }
        ctx.restore();
      }
    }
    if (labelMode && labelMode !== "none") {
      let labelText = "";
      if (labelMode === "type") {
        labelText = String(item.type || "");
      } else if (labelMode === "z") {
        labelText = String(item.z || 0);
      } else if (labelMode === "layer") {
        labelText = String(item.layer || "");
      }
      if (labelText) {
        ctx.fillStyle = labelColor;
        ctx.font = "11px monospace";
        ctx.fillText(labelText, isoX - tile, isoY - 4);
      }
    }
  });
}

function shadeVoxel(hex, amt) {
  const raw = String(hex || "#7aa2ff").replace("#", "");
  const num = parseInt(raw.padEnd(6, "0").slice(0, 6), 16);
  const r = Math.min(255, Math.max(0, ((num >> 16) & 255) + amt));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + amt));
  const b = Math.min(255, Math.max(0, (num & 255) + amt));
  return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
}

function resolveVoxelEdgeGlowConfig(item, defaults) {
  const meta = item && typeof item.meta === "object" ? item.meta : {};
  let enabled = Boolean(defaults && defaults.enabled);
  if (typeof item?.edgeGlow === "boolean") {
    enabled = item.edgeGlow;
  } else if (typeof meta.edgeGlow === "boolean") {
    enabled = meta.edgeGlow;
  } else if (typeof meta.edge_glow === "boolean") {
    enabled = meta.edge_glow;
  }
  let color = typeof defaults?.color === "string" ? defaults.color : "#8fd3ff";
  if (typeof item?.edgeGlowColor === "string" && item.edgeGlowColor.trim() !== "") {
    color = item.edgeGlowColor.trim();
  } else if (typeof meta.edgeGlowColor === "string" && meta.edgeGlowColor.trim() !== "") {
    color = meta.edgeGlowColor.trim();
  } else if (typeof meta.edge_glow_color === "string" && meta.edge_glow_color.trim() !== "") {
    color = meta.edge_glow_color.trim();
  }
  let strength = Math.max(0, Math.min(32, Number(defaults?.strength ?? 8)));
  if (Number.isFinite(Number(item?.edgeGlowStrength))) {
    strength = Math.max(0, Math.min(32, Number(item.edgeGlowStrength)));
  } else if (Number.isFinite(Number(meta.edgeGlowStrength))) {
    strength = Math.max(0, Math.min(32, Number(meta.edgeGlowStrength)));
  } else if (Number.isFinite(Number(meta.edge_glow_strength))) {
    strength = Math.max(0, Math.min(32, Number(meta.edge_glow_strength)));
  }
  return { enabled, color, strength };
}

function shadeColor(hex, factor) {
  const raw = String(hex || "#7aa2ff").replace("#", "");
  const num = parseInt(raw.padEnd(6, "0").slice(0, 6), 16);
  const r = Math.min(255, Math.max(0, ((num >> 16) & 255) * factor));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 255) * factor));
  const b = Math.min(255, Math.max(0, (num & 255) * factor));
  return "#" + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
}

function closeNum(a, b, epsilon = 1e-4) {
  return Math.abs(Number(a || 0) - Number(b || 0)) <= epsilon;
}

function closeVec3(a, b, epsilon = 1e-4) {
  if (!a || !b) {
    return false;
  }
  return closeNum(a.x, b.x, epsilon) && closeNum(a.y, b.y, epsilon) && closeNum(a.z, b.z, epsilon);
}

function cameraSeedsMatch(mainSettings, fullscreenSettings) {
  const main = mainSettings && typeof mainSettings === "object" ? mainSettings : {};
  const full = fullscreenSettings && typeof fullscreenSettings === "object" ? fullscreenSettings : {};
  const mainMode = String(main.renderMode || "2.5d").toLowerCase();
  const fullMode = String(full.renderMode || "2.5d").toLowerCase();
  if (mainMode !== fullMode) {
    return false;
  }
  if (mainMode === "3d") {
    const m = normalizeCamera3d(main.camera3d);
    const f = normalizeCamera3d(full.camera3d);
    return (
      closeNum(m.yaw, f.yaw) &&
      closeNum(m.pitch, f.pitch) &&
      closeNum(m.zoom, f.zoom) &&
      closeNum(m.panX, f.panX) &&
      closeNum(m.panY, f.panY)
    );
  }
  const m = normalizeCamera2d(main.camera2d);
  const f = normalizeCamera2d(full.camera2d);
  const projMatch =
    String(main.projection || "isometric").toLowerCase() === String(full.projection || "isometric").toLowerCase();
  return projMatch && closeNum(m.panX, f.panX) && closeNum(m.panY, f.panY) && closeNum(m.zoom, f.zoom);
}

function readRendererLocalState() {
  if (typeof window === "undefined") {
    return {
      source: "json",
      json: "{}",
      cobra: "",
      javascript: "",
      python: "",
      engine: {},
      settings: {
        renderMode: "2.5d",
        camera3d: { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
        camera2d: { panX: 0, panY: 0, zoom: 1 },
        tile: 18,
        zScale: 8,
        renderScale: 1,
        visualStyle: "default",
        pixelate: false,
        background: "#0b1426",
        outline: false,
        outlineColor: "#0f203c",
        edgeGlow: false,
        edgeGlowColor: "#8fd3ff",
        edgeGlowStrength: 8,
        classicFalloutShowLabels: false,
        labelMode: "none",
        labelColor: "#d9e6ff",
        lighting: { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
        lod: { mode: "auto_zoom", level: 2 },
        rose: { enabled: true, strength: 0.35 },
      },
      materials: [],
      layers: [],
      atlases: [],
      playerId: "player",
      playerFacing: "south",
      followPlayer: false,
      playerOffset: { x: 0, y: 0, z: 0 },
    };
  }
  const source = localStorage.getItem("atelier.renderer.source") || "json";
  const json = localStorage.getItem("atelier.renderer.json") || "{}";
  const cobra = localStorage.getItem("atelier.renderer.cobra") || "";
  const javascript = localStorage.getItem("atelier.renderer.js") || "";
  const python = localStorage.getItem("atelier.renderer.python") || "";
  let engine = {};
  try {
    engine = JSON.parse(localStorage.getItem("atelier.renderer.engine") || "{}");
  } catch {
    engine = {};
  }
  let tables = {};
  try {
    tables = JSON.parse(localStorage.getItem("atelier.renderer.tables") || "{}");
  } catch {
    tables = {};
  }
  const precedence = localStorage.getItem("atelier.renderer.tables_precedence") || "local_over_api";
  const localTables = isPlainObject(engine && engine.tables) ? engine.tables : {};
  const mergedTables = mergeRendererTables(localTables, tables, precedence);
  const storedRealm = localStorage.getItem("atelier.renderer.realm") || "lapidus";
  engine = isPlainObject(engine)
    ? { ...engine, tables: mergedTables, realm_id: engine.realm_id || storedRealm }
    : { tables: mergedTables, realm_id: storedRealm };
  let settings = {
    renderMode: "2.5d",
    projection: "isometric",
    camera3d: { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
    camera2d: { panX: 0, panY: 0, zoom: 1 },
    tile: 18,
    zScale: 8,
    renderScale: 1,
    visualStyle: "default",
    pixelate: false,
    background: "#0b1426",
    outline: false,
    outlineColor: "#0f203c",
    edgeGlow: false,
    edgeGlowColor: "#8fd3ff",
    edgeGlowStrength: 8,
    classicFalloutShowLabels: false,
    labelMode: "none",
    labelColor: "#d9e6ff",
    lighting: { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
    lod: { mode: "auto_zoom", level: 2 },
    rose: { enabled: true, strength: 0.35 },
  };
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.voxel_settings") || "{}");
    settings = {
      renderMode: normalizeRenderMode(parsed.renderMode),
      projection: String(parsed.projection || "isometric").toLowerCase() === "cardinal" ? "cardinal" : "isometric",
      camera3d: normalizeCamera3d(parsed.camera3d),
      camera2d: normalizeCamera2d(parsed.camera2d),
      tile: parsed.tile ?? 18,
      zScale: parsed.zScale ?? 8,
      renderScale: parsed.renderScale ?? 1,
      visualStyle: parsed.visualStyle ?? "default",
      pixelate: parsed.pixelate ?? false,
      background: parsed.background ?? "#0b1426",
      outline: parsed.outline ?? false,
      outlineColor: parsed.outlineColor ?? "#0f203c",
      edgeGlow: parsed.edgeGlow ?? false,
      edgeGlowColor: parsed.edgeGlowColor ?? "#8fd3ff",
      edgeGlowStrength: parsed.edgeGlowStrength ?? 8,
      classicFalloutShowLabels: parsed.classicFalloutShowLabels ?? false,
      labelMode: parsed.labelMode ?? "none",
      labelColor: parsed.labelColor ?? "#d9e6ff",
      lighting: parsed.lighting ?? { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
      lod: parsed.lod ?? { mode: "auto_zoom", level: 2 },
      rose: parsed.rose ?? { enabled: true, strength: 0.35 },
    };
  } catch {
    // use defaults
  }
  let materials = [];
  let layers = [];
  let atlases = [];
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.materials") || "[]");
    materials = Array.isArray(parsed) ? parsed : [];
  } catch {
    materials = [];
  }
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.layers") || "[]");
    layers = Array.isArray(parsed) ? parsed : [];
  } catch {
    layers = [];
  }
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.atlases") || "[]");
    atlases = Array.isArray(parsed) ? parsed : [];
  } catch {
    atlases = [];
  }
  const playerId = localStorage.getItem("atelier.renderer.player_id") || "player";
  const playerFacing = normalizeFacing(localStorage.getItem("atelier.renderer.player_facing") || "south");
  const followPlayer = localStorage.getItem("atelier.renderer.follow_player") === "1";
  let playerOffset = { x: 0, y: 0, z: 0 };
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.player_offset") || "{}");
    playerOffset = {
      x: Number.isFinite(Number(parsed.x)) ? Number(parsed.x) : 0,
      y: Number.isFinite(Number(parsed.y)) ? Number(parsed.y) : 0,
      z: Number.isFinite(Number(parsed.z)) ? Number(parsed.z) : 0,
    };
  } catch {
    playerOffset = { x: 0, y: 0, z: 0 };
  }
  try {
    const parsed = JSON.parse(localStorage.getItem("atelier.renderer.player_signal") || "{}");
    if (Number.isFinite(Number(parsed.x)) && Number.isFinite(Number(parsed.y))) {
      const signals = engine && typeof engine === "object" && engine.signals && typeof engine.signals === "object"
        ? { ...engine.signals }
        : {};
      signals.player_position = {
        x: Number(parsed.x),
        y: Number(parsed.y),
        z: Number.isFinite(Number(parsed.z)) ? Number(parsed.z) : 0,
        updated_at: typeof parsed.updated_at === "string" ? parsed.updated_at : new Date().toISOString(),
      };
      engine = { ...engine, signals };
    }
  } catch {
    // best-effort bootstrap of signal from storage
  }
  return {
    source,
    json,
    cobra,
    javascript,
    python,
    engine,
    settings,
    materials,
    layers,
    atlases,
    playerId,
    playerFacing,
    followPlayer,
    playerOffset
  };
}

const RENDERER_SYNC_CHANNEL = "atelier-renderer-sync-v1";

export function App() {
  const [section, setSection] = useState(resolveInitialSection);
  const [role, setRole] = useState(() => localStorage.getItem("atelier.role") || "senior_artisan");
  const [authToken, setAuthToken] = useState(() => localStorage.getItem("atelier.auth_token") || null);
  const [artisanId, setArtisanId] = useState(() => localStorage.getItem("atelier.artisan_id") || "");
  const [workshopId, setWorkshopId] = useState(() => localStorage.getItem("atelier.workshop_id") || "");
  const [loginArtisanId, setLoginArtisanId] = useState("");
  const [loginArtisanCode, setLoginArtisanCode] = useState("");
  const [loginError, setLoginError] = useState("");
  const [onboardCode, setOnboardCode] = useState("");
  const [onboardArtisanId, setOnboardArtisanId] = useState("");
  const [onboardName, setOnboardName] = useState("");
  const [onboardEmail, setOnboardEmail] = useState("");
  const [onboardPassword, setOnboardPassword] = useState("");
  const [onboardError, setOnboardError] = useState("");
  const [onboardStatus, setOnboardStatus] = useState("idle");
  const [issueInviteRole, setIssueInviteRole] = useState("artisan");
  const [issueInviteNote, setIssueInviteNote] = useState("");
  const [issueInviteMaxUses, setIssueInviteMaxUses] = useState(1);
  const [issuedInviteCode, setIssuedInviteCode] = useState("");
  const [workspaceId, setWorkspaceId] = useState(() => localStorage.getItem("atelier.workspace") || "main");
  const [workspaceList, setWorkspaceList] = useState([]);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [newWorkspaceOwner, setNewWorkspaceOwner] = useState("");
  const [addMemberWorkspaceId, setAddMemberWorkspaceId] = useState("");
  const [addMemberArtisanId, setAddMemberArtisanId] = useState("");
  const [addMemberRole, setAddMemberRole] = useState("member");
  const [output, setOutput] = useState("{}");
  const [notice, setNotice] = useState("Ready");
  const [busyAction, setBusyAction] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [actionPostTarget, setActionPostTarget] = useState(() => localStorage.getItem("atelier.post_target") || "api");
  const [actionPostEngineFileId, setActionPostEngineFileId] = useState(
    () => localStorage.getItem("atelier.post_engine_file_id") || ""
  );
  const [actionPostRepoFolder, setActionPostRepoFolder] = useState(
    () => localStorage.getItem("atelier.post_repo_folder") || "runtime-posts"
  );
  const [engineInboxConsumeMax, setEngineInboxConsumeMax] = useState(
    () => localStorage.getItem("atelier.engine_inbox_consume_max") || "25"
  );
  const [engineInboxPreviewOnly, setEngineInboxPreviewOnly] = useState(
    () => localStorage.getItem("atelier.engine_inbox_preview_only") === "1"
  );
  const [engineInboxStrictValidation, setEngineInboxStrictValidation] = useState(
    () => localStorage.getItem("atelier.engine_inbox_strict_validation") !== "0"
  );
  const [engineInboxResult, setEngineInboxResult] = useState(null);

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
  const [spriteColor, setSpriteColor] = useState("#7aa2ff");
  const [akinenwunWord, setAkinenwunWord] = useState("TyKoWuVu");
  const [akinenwunMode, setAkinenwunMode] = useState("prose");
  const [akinenwunIngest, setAkinenwunIngest] = useState(true);
  const [akinenwunFrontier, setAkinenwunFrontier] = useState(null);
  const [rendererAkinenwunMode, setRendererAkinenwunMode] = useState("prose");
  const [rendererAkinenwunWord, setRendererAkinenwunWord] = useState("TyKoWuVu");
  const [rendererAkinenwunFrontier, setRendererAkinenwunFrontier] = useState(null);
  const [graphMakerSource, setGraphMakerSource] = useState("workshop");
  const [graphMakerManualFrontierText, setGraphMakerManualFrontierText] = useState("{\"paths\":[]}");
  const [rendererRealmId, setRendererRealmId] = useState(() => localStorage.getItem("atelier.renderer.realm") || "lapidus");
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
  const [rendererVisualSource, setRendererVisualSource] = useState("json");
  const unifiedRendererCanvasRef = useRef(null);
  const businessRendererCanvasRef = useRef(null);
  const businessLogicRendererCanvasRef = useRef(null);
  const governorLevelRef = useRef("normal");
  const [businessRendererInputMode, setBusinessRendererInputMode] = useState(
    () => localStorage.getItem("atelier.business_renderer.input_mode") || "json"
  );
  const [businessRendererInputText, setBusinessRendererInputText] = useState(
    () => localStorage.getItem("atelier.business_renderer.input_text") || BUSINESS_ARCHITECTURE_TEMPLATE
  );
  const [businessRendererUseDerived, setBusinessRendererUseDerived] = useState(
    () => localStorage.getItem("atelier.business_renderer.use_derived") !== "0"
  );
  const [businessRendererStatus, setBusinessRendererStatus] = useState("ready");
  const [businessLogicRendererInputMode, setBusinessLogicRendererInputMode] = useState(
    () => localStorage.getItem("atelier.business_logic_renderer.input_mode") || "json"
  );
  const [businessLogicRendererInputText, setBusinessLogicRendererInputText] = useState(
    () => localStorage.getItem("atelier.business_logic_renderer.input_text") || BUSINESS_ARCHITECTURE_TEMPLATE
  );
  const [businessLogicRendererUseDerived, setBusinessLogicRendererUseDerived] = useState(
    () => localStorage.getItem("atelier.business_logic_renderer.use_derived") !== "0"
  );
  const [businessLogicRendererStatus, setBusinessLogicRendererStatus] = useState("ready");
  const [contentValidateSource, setContentValidateSource] = useState("cobra");
  const [contentValidateSceneId, setContentValidateSceneId] = useState("lapidus/renderer-lab");
  const [contentValidatePayload, setContentValidatePayload] = useState("");
  const [contentValidateOutput, setContentValidateOutput] = useState(null);
  const [rendererBilingualOutput, setRendererBilingualOutput] = useState(null);
  const [shygazunTranslateSourceText, setShygazunTranslateSourceText] = useState("love whale");
  const [shygazunTranslateDirection, setShygazunTranslateDirection] = useState("auto");
  const [shygazunTranslateOutput, setShygazunTranslateOutput] = useState(null);
  const [shygazunInterpretOutput, setShygazunInterpretOutput] = useState(null);
  const [shygazunProjectOutput, setShygazunProjectOutput] = useState(null);
  const [shygazunProjectionBridge, setShygazunProjectionBridge] = useState(null);
  const [collisionMap, setCollisionMap] = useState(null);
  const [showCollisionOverlay, setShowCollisionOverlay] = useState(false);
  const [shygazunCorrectOutput, setShygazunCorrectOutput] = useState(null);
  const [moduleCatalog, setModuleCatalog] = useState([]);
  const [moduleSelectedId, setModuleSelectedId] = useState("module.shygazun.interpret");
  const [moduleSelectedSpec, setModuleSelectedSpec] = useState(null);
  const [moduleValidateOutput, setModuleValidateOutput] = useState(null);
  const [moduleRunOverridesText, setModuleRunOverridesText] = useState("{\n  \"kaganue_pressure\": 0.1\n}");
  const [moduleAutoReconcile, setModuleAutoReconcile] = useState(true);
  const [moduleReconcileSceneId, setModuleReconcileSceneId] = useState("renderer-lab");
  const [moduleReconcileApply, setModuleReconcileApply] = useState(true);
  const [moduleRunOutput, setModuleRunOutput] = useState(null);
  const [sceneKitShellId, setSceneKitShellId] = useState("scene.crossroads_day");
  const [sceneKitRoomIdsText, setSceneKitRoomIdsText] = useState("room.town_square");
  const [sceneKitChunkIdsText, setSceneKitChunkIdsText] = useState("chunk.market_crossroads");
  const [sceneKitFeatureIdsText, setSceneKitFeatureIdsText] = useState("feature.scene.storm_morning feature.spawn.player_center");
  const [sceneKitSelectedRoomId, setSceneKitSelectedRoomId] = useState("room.town_square");
  const [sceneKitSelectedChunkId, setSceneKitSelectedChunkId] = useState("chunk.market_crossroads");
  const [sceneKitSelectedFeatureId, setSceneKitSelectedFeatureId] = useState("feature.scene.storm_morning");
  const shygazunSemanticSummary = buildShygazunSemanticSummary(shygazunProjectOutput);
  const [sceneKitOutput, setSceneKitOutput] = useState(null);
  const [labCoherence, setLabCoherence] = useState({
    last_check_at: "",
    runtime_consume_ok: null,
    module_catalog_ok: null,
    world_stream_ok: null,
    main_plan_ok: null,
    guided_bootstrap_ok: null,
    gate_a_ok: null,
    gate_d_ok: null,
  });
  const [validateBeforeEmit, setValidateBeforeEmit] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.validate_before_emit");
    return saved !== "0";
  });
  const [strictBilingualValidation, setStrictBilingualValidation] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.strict_bilingual");
    return saved === "1";
  });
  const [validationSummary, setValidationSummary] = useState({ ok: true, errors: 0, warnings: 0 });
  const [voxelSettings, setVoxelSettings] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.voxel_settings");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return {
          renderMode: normalizeRenderMode(parsed.renderMode),
          projection: String(parsed.projection || "isometric").toLowerCase() === "cardinal" ? "cardinal" : "isometric",
          camera3d: normalizeCamera3d(parsed.camera3d),
          camera2d: normalizeCamera2d(parsed.camera2d),
          tile: parsed.tile ?? 18,
          zScale: parsed.zScale ?? 8,
          renderScale: parsed.renderScale ?? 1,
          visualStyle: parsed.visualStyle ?? "default",
          pixelate: parsed.pixelate ?? false,
          background: parsed.background ?? "#0b1426",
          outline: parsed.outline ?? false,
          outlineColor: parsed.outlineColor ?? "#0f203c",
          edgeGlow: parsed.edgeGlow ?? false,
          edgeGlowColor: parsed.edgeGlowColor ?? "#8fd3ff",
          edgeGlowStrength: parsed.edgeGlowStrength ?? 8,
          classicFalloutShowLabels: parsed.classicFalloutShowLabels ?? false,
          labelMode: parsed.labelMode ?? "none",
          labelColor: parsed.labelColor ?? "#d9e6ff",
          lighting: parsed.lighting ?? { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
          lod: parsed.lod ?? { mode: "auto_zoom", level: 2 },
          rose: parsed.rose ?? { enabled: true, strength: 0.35 },
        };
      } catch {
        return {
          renderMode: "2.5d",
          projection: "isometric",
          camera3d: { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
          camera2d: { panX: 0, panY: 0, zoom: 1 },
          tile: 18,
          zScale: 8,
          renderScale: 1,
          visualStyle: "default",
          pixelate: false,
          background: "#0b1426",
          outline: false,
          outlineColor: "#0f203c",
          edgeGlow: false,
          edgeGlowColor: "#8fd3ff",
          edgeGlowStrength: 8,
          classicFalloutShowLabels: false,
          labelMode: "none",
          labelColor: "#d9e6ff",
          lighting: { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
          lod: { mode: "auto_zoom", level: 2 },
          rose: { enabled: true, strength: 0.35 },
        };
      }
    }
    return {
      renderMode: "2.5d",
      projection: "isometric",
      camera3d: { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
      camera2d: { panX: 0, panY: 0, zoom: 1 },
      tile: 18,
      zScale: 8,
      renderScale: 1,
      visualStyle: "default",
      pixelate: false,
      background: "#0b1426",
      outline: false,
      outlineColor: "#0f203c",
      edgeGlow: false,
      edgeGlowColor: "#8fd3ff",
      edgeGlowStrength: 8,
      classicFalloutShowLabels: false,
      labelMode: "none",
      labelColor: "#d9e6ff",
      lighting: { enabled: false, x: 0.4, y: -0.6, z: 0.7, ambient: 0.35, intensity: 0.85 },
      lod: { mode: "auto_zoom", level: 2 },
      rose: { enabled: true, strength: 0.35 },
    };
  });
  const [voxelAtlases, setVoxelAtlases] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.atlases");
    if (!saved) {
      return [];
    }
    try {
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const [voxelAtlasDraft, setVoxelAtlasDraft] = useState({
    id: "",
    src: "",
    tileSize: 16,
    cols: 8,
    rows: 8,
    padding: 0
  });
  const [voxelMaterials, setVoxelMaterials] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.materials");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed;
        }
      } catch {
        return [];
      }
    }
    return [
      { id: "stone", color: "#9aa4b2", textureTop: "", textureLeft: "", textureRight: "" },
      { id: "wood", color: "#b07d4f", textureTop: "", textureLeft: "", textureRight: "" },
      { id: "glass", color: "#7ad3ff", textureTop: "", textureLeft: "", textureRight: "" }
    ];
  });
  const [voxelMaterialDraft, setVoxelMaterialDraft] = useState({
    id: "",
    color: "#7aa2ff",
    textureTop: "",
    textureLeft: "",
    textureRight: ""
  });
  const [voxelLayers, setVoxelLayers] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.layers");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed;
        }
      } catch {
        return [];
      }
    }
    return [
      { id: "ground", zOffset: 0 },
      { id: "mid", zOffset: 2 },
      { id: "sky", zOffset: 4 }
    ];
  });
  const [rendererPipeline, setRendererPipeline] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.pipeline");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return {
          pythonFileId: "",
          cobraFileId: "",
          jsFileId: "",
          jsonFileId: "",
          engineFileId: "",
          autoPlay: false
        };
      }
    }
    return {
      pythonFileId: "",
      cobraFileId: "",
      jsFileId: "",
      jsonFileId: "",
      engineFileId: "",
      worldRegionRealmId: rendererRealmId,
      worldRegionKey: "",
      worldRegionCachePolicy: "cache",
      worldRegionPayloadFileId: "",
      worldRegionAutoLoad: false,
      autoPlay: false
    };
  });
  const [rendererPipelineJson, setRendererPipelineJson] = useState("");
  const [worldRegions, setWorldRegions] = useState([]);
  const [worldRegionLast, setWorldRegionLast] = useState(null);
  const [worldStreamStatus, setWorldStreamStatus] = useState(null);
  const [fullscreenState, setFullscreenState] = useState(() => readRendererLocalState());
  const fullscreenCanvasRef = useRef(null);
  const unifiedCameraDragRef = useRef(null);
  const fullscreenCameraDragRef = useRef(null);

  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contacts, setContacts] = useState([]);
  const [contactFilter, setContactFilter] = useState("");

  const [bookingStart, setBookingStart] = useState("");
  const [bookingEnd, setBookingEnd] = useState("");
  const [bookingContactId, setBookingContactId] = useState("");
  const [bookingNotes, setBookingNotes] = useState("");
  const [bookings, setBookings] = useState([]);
  const [bookingFilter, setBookingFilter] = useState("");
  const [profileName, setProfileName] = useState(() => localStorage.getItem("atelier.profile_name") || "Artisan");
  const [profileEmail, setProfileEmail] = useState(() => localStorage.getItem("atelier.profile_email") || "");
  const [profileTimezone, setProfileTimezone] = useState(
    () => localStorage.getItem("atelier.profile_tz") || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [entryAuthModalOpen, setEntryAuthModalOpen] = useState(!localStorage.getItem("atelier.auth_token"));
  const [entryAuthMode, setEntryAuthMode] = useState("sign_in");
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
  const [lessonValidationOutput, setLessonValidationOutput] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [lessonProgress, setLessonProgress] = useState([]);
  const [lessonActorId, setLessonActorId] = useState(() => localStorage.getItem("atelier.lesson_actor") || "player");
  const [lessonFilter, setLessonFilter] = useState("");
  const LESSON_SOFT_LIMIT = 12000;

  const [moduleTitle, setModuleTitle] = useState("");
  const [moduleDescription, setModuleDescription] = useState("");
  const [modules, setModules] = useState([]);
  const [moduleFilter, setModuleFilter] = useState("");

  const [leadName, setLeadName] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [leadPhone, setLeadPhone] = useState("");
  const [leadDetails, setLeadDetails] = useState("");
  const [leadSource, setLeadSource] = useState("internal");
  const [leadNotes, setLeadNotes] = useState("");
  const [leads, setLeads] = useState([]);
  const [leadFilter, setLeadFilter] = useState("");

  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientNotes, setClientNotes] = useState("");
  const [clients, setClients] = useState([]);
  const [clientFilter, setClientFilter] = useState("");

  const [quoteTitle, setQuoteTitle] = useState("");
  const [quoteAmount, setQuoteAmount] = useState("");
  const [quoteCurrency, setQuoteCurrency] = useState("USD");
  const [quotePublic, setQuotePublic] = useState(false);
  const [quoteLeadId, setQuoteLeadId] = useState("");
  const [quoteNotes, setQuoteNotes] = useState("");
  const [quotes, setQuotes] = useState([]);
  const [quoteFilter, setQuoteFilter] = useState("");

  const [orderTitle, setOrderTitle] = useState("");
  const [orderAmount, setOrderAmount] = useState("");
  const [orderCurrency, setOrderCurrency] = useState("USD");
  const [orderQuoteId, setOrderQuoteId] = useState("");
  const [orderClientId, setOrderClientId] = useState("");
  const [orderNotes, setOrderNotes] = useState("");
  const [orders, setOrders] = useState([]);
  const [orderFilter, setOrderFilter] = useState("");
  const [contracts, setContracts] = useState([]);
  const [contractTitle, setContractTitle] = useState("");
  const [contractCategory, setContractCategory] = useState("consultations");
  const [contractPartyName, setContractPartyName] = useState("");
  const [contractPartyEmail, setContractPartyEmail] = useState("");
  const [contractPartyPhone, setContractPartyPhone] = useState("");
  const [contractArtisanId, setContractArtisanId] = useState("");
  const [contractAmount, setContractAmount] = useState("");
  const [contractCurrency, setContractCurrency] = useState("USD");
  const [contractTerms, setContractTerms] = useState("");
  const [contractNotes, setContractNotes] = useState("");
  const [contractSelectedId, setContractSelectedId] = useState("");
  const [contractFilter, setContractFilter] = useState("");
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [ledgerMonth, setLedgerMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [ledgerSummary, setLedgerSummary] = useState(null);

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
  const [rendererJson, setRendererJson] = useState("{\"voxels\":[{\"x\":0,\"y\":0,\"z\":0,\"type\":\"plinth\"},{\"x\":1,\"y\":0,\"z\":1,\"type\":\"pillar\"},{\"x\":2,\"y\":1,\"z\":0,\"type\":\"bench\"},{\"x\":3,\"y\":2,\"z\":2,\"type\":\"spire\"}]}");
  const [rendererEngineStateText, setRendererEngineStateText] = useState("{\"tick\":0,\"camera\":{\"x\":0,\"y\":0}}");
  const [rendererGameSpecText, setRendererGameSpecText] = useState(
    "{\"scene\":{\"name\":\"prototype\"},\"systems\":{\"gravity\":0.0,\"camera\":{\"x\":0,\"y\":0}},\"entities\":[{\"id\":\"hero\",\"kind\":\"player\",\"x\":0,\"y\":0,\"hp\":100},{\"id\":\"orb-1\",\"kind\":\"pickup\",\"x\":4,\"y\":2,\"value\":10}]}"
  );
  const [rendererGameStatus, setRendererGameStatus] = useState("idle");
  const [rendererParseStatus, setRendererParseStatus] = useState("idle");
  const [rendererParsedPayload, setRendererParsedPayload] = useState({ source: "json", key: "", payload: {} });
  const [rendererVoxelPrepStatus, setRendererVoxelPrepStatus] = useState("idle");
  const [rendererPreparedVoxels, setRendererPreparedVoxels] = useState({ key: "", voxels: [] });
  const [rendererTestSpecText, setRendererTestSpecText] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.test_spec");
    if (saved) {
      return saved;
    }
    return JSON.stringify(
      {
        renderer_json: {
          scene: { id: "test_scene", name: "Test Scene" },
          voxels: [{ id: "player", type: "player", x: 0, y: 0, z: 1, color: "#f6c677" }],
        },
        settings: { renderMode: "2.5d", projection: "cardinal", tile: 28, zScale: 10, renderScale: 2 },
        controls: {
          player_id: "player",
          follow_player: true,
          keyboard_motion: true,
          click_move: true,
          path_step_ms: 70,
          player_step: 1,
          reset_motion: true,
        },
        signal: { player_position: { x: 0, y: 0, z: 0 } },
      },
      null,
      2
    );
  });
  const [rendererTestHarnessStatus, setRendererTestHarnessStatus] = useState("idle");
  const [rendererTestFragmentId, setRendererTestFragmentId] = useState(
    RENDERER_TEST_SPEC_FRAGMENTS.length > 0 ? RENDERER_TEST_SPEC_FRAGMENTS[0].id : ""
  );
  const [rendererTestFragmentMode, setRendererTestFragmentMode] = useState("merge");
  const [rendererPlayerId, setRendererPlayerId] = useState(
    () => localStorage.getItem("atelier.renderer.player_id") || "player"
  );
  const [rendererPlayerFacing, setRendererPlayerFacing] = useState(
    () => normalizeFacing(localStorage.getItem("atelier.renderer.player_facing") || "south")
  );
  const [rendererAnimationClock, setRendererAnimationClock] = useState(() => Date.now());
  const [rendererLastMoveAt, setRendererLastMoveAt] = useState(0);
  const [rendererFollowPlayer, setRendererFollowPlayer] = useState(
    () => localStorage.getItem("atelier.renderer.follow_player") === "1"
  );
  const [rendererKeyboardMotion, setRendererKeyboardMotion] = useState(
    () => localStorage.getItem("atelier.renderer.keyboard_motion") !== "0"
  );
  const [rendererClickMove, setRendererClickMove] = useState(
    () => localStorage.getItem("atelier.renderer.click_move") !== "0"
  );
  const [rendererPathStepMs, setRendererPathStepMs] = useState(
    () => Number(localStorage.getItem("atelier.renderer.path_step_ms") || "75") || 75
  );
  const [rendererMoveQueue, setRendererMoveQueue] = useState([]);
  const [rendererPlayerStep, setRendererPlayerStep] = useState(
    () => Number(localStorage.getItem("atelier.renderer.player_step") || "1") || 1
  );
  const [rendererGravityEnabled, setRendererGravityEnabled] = useState(
    () => localStorage.getItem("atelier.renderer.gravity_enabled") !== "0"
  );
  const [rendererGravityMs, setRendererGravityMs] = useState(
    () => Number(localStorage.getItem("atelier.renderer.gravity_ms") || "150") || 150
  );
  const [rendererPlayerOffset, setRendererPlayerOffset] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.player_offset");
    if (!saved) {
      return { x: 0, y: 0, z: 0 };
    }
    try {
      const parsed = JSON.parse(saved);
      return {
        x: Number.isFinite(Number(parsed.x)) ? Number(parsed.x) : 0,
        y: Number.isFinite(Number(parsed.y)) ? Number(parsed.y) : 0,
        z: Number.isFinite(Number(parsed.z)) ? Number(parsed.z) : 0,
      };
    } catch {
      return { x: 0, y: 0, z: 0 };
    }
  });
  const [rendererGraphPreview, setRendererGraphPreview] = useState(null);
  const [rendererAssetDiagnostics, setRendererAssetDiagnostics] = useState(null);
  const [headlessQuestText, setHeadlessQuestText] = useState(
    "{\"workspace_id\":\"main\",\"quest_id\":\"quest_intro\",\"scene_id\":\"scene_prototype\",\"steps\":[{\"step_id\":\"s1\",\"raw\":\"quest.step quest_intro s1\",\"context\":{\"intent\":\"begin\"}}]}"
  );
  const [meditationText, setMeditationText] = useState(
    "{\"workspace_id\":\"main\",\"session_id\":\"med_001\",\"phase\":\"focus\",\"duration_seconds\":180,\"tags\":{\"mode\":\"guided\"}}"
  );
  const [sceneGraphText, setSceneGraphText] = useState(
    "{\"workspace_id\":\"main\",\"realm_id\":\"lapidus\",\"scene_id\":\"lapidus/scene_prototype\",\"nodes\":[{\"node_id\":\"n1\",\"kind\":\"spawn\",\"x\":0,\"y\":0,\"metadata\":{}},{\"node_id\":\"n2\",\"kind\":\"goal\",\"x\":8,\"y\":4,\"metadata\":{}}],\"edges\":[{\"from_node_id\":\"n1\",\"to_node_id\":\"n2\",\"relation\":\"path\",\"metadata\":{}}]}"
  );
  const [sceneCompileSceneId, setSceneCompileSceneId] = useState("lapidus/scene_prototype");
  const [rendererLibrarySceneId, setRendererLibrarySceneId] = useState("lapidus/scene_prototype");
  const [sceneCompileName, setSceneCompileName] = useState("Scene Prototype");
  const [sceneCompileDescription, setSceneCompileDescription] = useState("");
  const [dialogueSceneId, setDialogueSceneId] = useState("scene_prototype");
  const [dialogueId, setDialogueId] = useState("dlg_intro");
  const [dialogueLineId, setDialogueLineId] = useState("l1");
  const [dialogueSpeakerId, setDialogueSpeakerId] = useState("player");
  const [dialogueRaw, setDialogueRaw] = useState("Hello from the bordered dialogue box.");
  const [dialogueTurns, setDialogueTurns] = useState([]);
  const [dialogueEmitResult, setDialogueEmitResult] = useState(null);
  const [saveExport, setSaveExport] = useState(null);
  const [levelRuleText, setLevelRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"current_level\":1,\"current_xp\":50,\"gained_xp\":120,\"xp_curve_base\":100,\"xp_curve_scale\":25}"
  );
  const [skillRuleText, setSkillRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"skill_id\":\"melee_weapons\",\"current_rank\":1,\"points_available\":2,\"max_rank\":5}"
  );
  const [perkRuleText, setPerkRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"perk_id\":\"steel_focus\",\"unlocked_perks\":[],\"required_level\":2,\"actor_level\":2,\"required_skills\":{\"melee_weapons\":2},\"actor_skills\":{\"melee_weapons\":2}}"
  );
  const [alchemyRuleText, setAlchemyRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"recipe_id\":\"minor_heal\",\"ingredients\":{\"herb\":2,\"water\":1},\"outputs\":{\"potion_minor_heal\":1},\"inventory\":{\"herb\":5,\"water\":3}}"
  );
  const [blacksmithRuleText, setBlacksmithRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"blueprint_id\":\"iron_sword\",\"materials\":{\"iron_ingot\":3,\"wood\":1},\"outputs\":{\"iron_sword\":1},\"inventory\":{\"iron_ingot\":5,\"wood\":2},\"durability_bonus\":2}"
  );
  const [combatRuleText, setCombatRuleText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"round_id\":\"r1\",\"attacker\":{\"id\":\"player\",\"hp\":100,\"attack\":18,\"defense\":6},\"defender\":{\"id\":\"wolf\",\"hp\":28,\"attack\":9,\"defense\":4}}"
  );
  const [guildProfile, setGuildProfile] = useState(null);
  const [guildProfileEdit, setGuildProfileEdit] = useState({ display_name: "", bio: "", portfolio_url: "", avatar_url: "", region: "", divisions: "", trades: "", is_public: false, show_region: true, show_trades: true, show_portfolio: true });
  const [guildProfileStatus, setGuildProfileStatus] = useState("idle");
  const [guildProfilesAdmin, setGuildProfilesAdmin] = useState([]);
  const [guildDirectoryResults, setGuildDirectoryResults] = useState([]);
  const [guildDirectoryQuery, setGuildDirectoryQuery] = useState("");
  const [kernelFields, setKernelFields] = useState([]);
  const [kernelFieldStatus, setKernelFieldStatus] = useState("idle");
  const [kernelFieldLabel, setKernelFieldLabel] = useState("");
  const [kernelFieldObserve, setKernelFieldObserve] = useState(null);
  const [assetManifests, setAssetManifests] = useState([]);
  const [assetManifestStatus, setAssetManifestStatus] = useState("idle");
  const [assetManifestSelected, setAssetManifestSelected] = useState("");
  const [assetUploadFile, setAssetUploadFile] = useState(null);
  const [assetUploadMime, setAssetUploadMime] = useState("application/octet-stream");
  const [assetUploadKind, setAssetUploadKind] = useState("image");
  const [assetUploadStatus, setAssetUploadStatus] = useState("idle");
  const [rendererTickText, setRendererTickText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"dt_ms\":120,\"events\":[{\"kind\":\"levels.apply\",\"payload\":{\"gained_xp\":120}},{\"kind\":\"skills.train\",\"payload\":{\"skill_id\":\"melee_weapons\",\"points_available\":1,\"max_rank\":5}},{\"kind\":\"flags.set\",\"payload\":{\"key\":\"intro_done\",\"value\":true}}]}"
  );
  const [rendererTickOutput, setRendererTickOutput] = useState(null);
  const [marketQuoteText, setMarketQuoteText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"item_id\":\"iron_ingot\",\"side\":\"buy\",\"quantity\":3,\"base_price_cents\":1200,\"scarcity_bp\":300,\"spread_bp\":100}"
  );
  const [marketTradeText, setMarketTradeText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"item_id\":\"iron_ingot\",\"side\":\"buy\",\"quantity\":3,\"unit_price_cents\":1250,\"fee_bp\":50,\"wallet_cents\":10000,\"inventory_qty\":2,\"available_liquidity\":10}"
  );
  const [vitriolApplyText, setVitriolApplyText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"base\":{\"vitality\":7,\"introspection\":7,\"tactility\":7,\"reflectivity\":7,\"ingenuity\":7,\"ostentation\":7,\"levity\":7},\"modifiers\":[],\"ruler_id\":\"asmodeus\",\"delta\":{\"vitality\":1},\"reason\":\"ruler_trial\",\"event_id\":\"evt_vitriol_apply_1\",\"applied_tick\":1,\"duration_turns\":0}"
  );
  const [vitriolComputeText, setVitriolComputeText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"base\":{\"vitality\":7,\"introspection\":7,\"tactility\":7,\"reflectivity\":7,\"ingenuity\":7,\"ostentation\":7,\"levity\":7},\"modifiers\":[],\"current_tick\":1}"
  );
  const [vitriolClearText, setVitriolClearText] = useState(
    "{\"workspace_id\":\"main\",\"actor_id\":\"player\",\"base\":{\"vitality\":7,\"introspection\":7,\"tactility\":7,\"reflectivity\":7,\"ingenuity\":7,\"ostentation\":7,\"levity\":7},\"modifiers\":[],\"current_tick\":1}"
  );
  const [rendererTablesActorId, setRendererTablesActorId] = useState("player");
  const [rendererTablesPrecedence, setRendererTablesPrecedence] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.tables_precedence");
    return saved || "local_over_api";
  });
  const [rendererStateCommitMode, setRendererStateCommitMode] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.state_commit_mode");
    return saved || "merge";
  });
  const [rendererTablesStatus, setRendererTablesStatus] = useState("idle");
  const [rendererTablesMeta, setRendererTablesMeta] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.tables_meta");
    return parseObjectJson(saved, { generated_at: "", hash: "" });
  });
  const [rendererTables, setRendererTables] = useState(() => {
    const saved = localStorage.getItem("atelier.renderer.tables");
    return parseObjectJson(saved, {});
  });
  const [gameRulesOutput, setGameRulesOutput] = useState(null);
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
  const [tileTraversalClass, setTileTraversalClass] = useState(() => {
    return localStorage.getItem("atelier.tile_traversal_class") || "walkable_surface";
  });
  const [tileNearThreshold, setTileNearThreshold] = useState("2");
  const [tilePlacements, setTilePlacements] = useState({});
  const [tileConnections, setTileConnections] = useState([]);
  const [tileConnectMode, setTileConnectMode] = useState(false);
  const [tileConnectFrom, setTileConnectFrom] = useState(null);
  const [tileSvgShowGrid, setTileSvgShowGrid] = useState(true);
  const [tileSvgShowLinks, setTileSvgShowLinks] = useState(true);
  const [tilePngDataUrl, setTilePngDataUrl] = useState("");
  const [tilePngStatus, setTilePngStatus] = useState("idle");
  const [tileProcSeed, setTileProcSeed] = useState("42");
  const [tileProcTemplate, setTileProcTemplate] = useState("ring_bloom");
  const [tileEditLodLevel, setTileEditLodLevel] = useState("3");
  const [tileEditLodSnap, setTileEditLodSnap] = useState(true);
  const [tileBrushRadius, setTileBrushRadius] = useState("0");
  const [tileBrushShape, setTileBrushShape] = useState("square");
  const [tileRectSelectMode, setTileRectSelectMode] = useState(false);
  const [tileRectStart, setTileRectStart] = useState(null);
  const [tileRectEnd, setTileRectEnd] = useState(null);
  const [tileRectLodLevel, setTileRectLodLevel] = useState("3");
  const [tileRectFeatherScaleAware, setTileRectFeatherScaleAware] = useState(true);
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
  const [spriteAnimatorTargetId, setSpriteAnimatorTargetId] = useState("sprite_player");
  const [spriteAnimatorAtlasId, setSpriteAnimatorAtlasId] = useState("tile_network");
  const [spriteAnimatorFrameW, setSpriteAnimatorFrameW] = useState("48");
  const [spriteAnimatorFrameH, setSpriteAnimatorFrameH] = useState("72");
  const [spriteAnimatorStartCol, setSpriteAnimatorStartCol] = useState("0");
  const [spriteAnimatorIdleRowStart, setSpriteAnimatorIdleRowStart] = useState("0");
  const [spriteAnimatorWalkRowStart, setSpriteAnimatorWalkRowStart] = useState("4");
  const [spriteAnimatorIdleFrames, setSpriteAnimatorIdleFrames] = useState("1");
  const [spriteAnimatorWalkFrames, setSpriteAnimatorWalkFrames] = useState("4");
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
  const [daisySystemId, setDaisySystemId] = useState("daisy.system.alpha");
  const [daisyArchetype, setDaisyArchetype] = useState("humanoid");
  const [daisySymmetry, setDaisySymmetry] = useState("bilateral");
  const [daisySegmentCount, setDaisySegmentCount] = useState("7");
  const [daisyLimbPairs, setDaisyLimbPairs] = useState("2");
  const [daisyCoreToken, setDaisyCoreToken] = useState("Ki");
  const [daisyAccentToken, setDaisyAccentToken] = useState("Fu");
  const [daisyCoreBelongingChain, setDaisyCoreBelongingChain] = useState("");
  const [daisyAccentBelongingChain, setDaisyAccentBelongingChain] = useState("");
  const [daisySeed, setDaisySeed] = useState("42");
  const [daisyUseWholeTongue, setDaisyUseWholeTongue] = useState(true);
  const [daisySymbolSequence, setDaisySymbolSequence] = useState(DAISY_TONGUE_SYMBOLS.join(", "));
  const [daisyRoleOverridesText, setDaisyRoleOverridesText] = useState("{}");
  const [daisyBodyplanText, setDaisyBodyplanText] = useState(
    JSON.stringify(
      buildDaisyBodyplanSpec({
        system_id: "daisy.system.alpha",
        archetype: "humanoid",
        symmetry: "bilateral",
        segment_count: 7,
        limb_pairs: 2,
        core_token: "Ki",
        accent_token: "Fu",
        core_belonging_chain: "",
        accent_belonging_chain: "",
        seed: 42,
        use_whole_tongue: true,
        daisy_symbols: DAISY_TONGUE_SYMBOLS,
        role_overrides: {},
      }),
      null,
      2
    )
  );
  const daisyRoleInspector = useMemo(() => {
    const allowedSymbols = daisyUseWholeTongue ? DAISY_TONGUE_SYMBOLS : parseDaisySymbolSequence(daisySymbolSequence);
    const base = buildDaisyRoleComposition(daisyArchetype, daisySymmetry, allowedSymbols);
    const rawOverrides = parseObjectJson(daisyRoleOverridesText, {});
    const overrides = sanitizeDaisyRoleOverrides(rawOverrides, allowedSymbols, base);
    const effective = { ...base, ...overrides };
    return { allowedSymbols, base, overrides, effective };
  }, [daisyUseWholeTongue, daisySymbolSequence, daisyArchetype, daisySymmetry, daisyRoleOverridesText]);

  const [publicName, setPublicName] = useState("");
  const [publicEmail, setPublicEmail] = useState("");
  const [publicDetails, setPublicDetails] = useState("");
  const [publicQuotes, setPublicQuotes] = useState([]);
  const [privacyManifest, setPrivacyManifest] = useState(null);

  const [messageDraft, setMessageDraft] = useState("");
  const [messageLog, setMessageLog] = useState([]);
  const [guildId, setGuildId] = useState("guild.atelier");
  const [guildDisplayName, setGuildDisplayName] = useState("Atelier Guild");
  const [guildDistributionId, setGuildDistributionId] = useState("distribution.quantumquackery.main");
  const [guildRecipientDistributionId, setGuildRecipientDistributionId] = useState("");
  const [guildRecipientGuildId, setGuildRecipientGuildId] = useState("");
  const [guildRecipientChannelId, setGuildRecipientChannelId] = useState("");
  const [guildRecipientActorId, setGuildRecipientActorId] = useState("");
  const [guildChannelId, setGuildChannelId] = useState("hall.general");
  const [guildThreadId, setGuildThreadId] = useState("thread_001");
  const [guildSenderId, setGuildSenderId] = useState("player");
  const [guildWandId, setGuildWandId] = useState("wand_001");
  const [guildSelectedRegistryWandId, setGuildSelectedRegistryWandId] = useState("wand_001");
  const [guildWandPasskeyWard, setGuildWandPasskeyWard] = useState("");
  const [guildTempleEntropyDigest, setGuildTempleEntropyDigest] = useState("");
  const [guildTheatreEntropyDigest, setGuildTheatreEntropyDigest] = useState("");
  const [guildAttestationDigestsText, setGuildAttestationDigestsText] = useState("");
  const [guildTempleProvenanceId, setGuildTempleProvenanceId] = useState("");
  const [guildTempleSourceType, setGuildTempleSourceType] = useState("garden_observation");
  const [guildTempleGardenId, setGuildTempleGardenId] = useState("temple.main");
  const [guildTemplePlotId, setGuildTemplePlotId] = useState("north-bed");
  const [guildTheatreProvenanceId, setGuildTheatreProvenanceId] = useState("");
  const [guildTheatreSourceType, setGuildTheatreSourceType] = useState("performance_upload");
  const [guildTheatrePerformanceId, setGuildTheatrePerformanceId] = useState("esoteric_01");
  const [guildTheatreUploadId, setGuildTheatreUploadId] = useState("upload_01");
  const [guildAttestationSourcesText, setGuildAttestationSourcesText] = useState("");
  const [guildEntropyMixOutput, setGuildEntropyMixOutput] = useState(null);
  const [guildEncryptOutput, setGuildEncryptOutput] = useState(null);
  const [guildDecryptOutput, setGuildDecryptOutput] = useState(null);
  const [guildPersistOutput, setGuildPersistOutput] = useState(null);
  const [guildMessageHistory, setGuildMessageHistory] = useState([]);
  const [guildConversationId, setGuildConversationId] = useState("conv_guild_atelier_general");
  const [guildConversationKind, setGuildConversationKind] = useState("guild_channel");
  const [guildConversationTitle, setGuildConversationTitle] = useState("Atelier Guild General");
  const [guildParticipantMemberIdsText, setGuildParticipantMemberIdsText] = useState('[\n  "player"\n]');
  const [guildParticipantGuildIdsText, setGuildParticipantGuildIdsText] = useState('[\n  "guild.atelier"\n]');
  const [guildSecuritySessionText, setGuildSecuritySessionText] = useState('{\n  "session_mode": "double_ratchet_like",\n  "sender_identity_key_ref": "player.identity",\n  "recipient_identity_key_ref": ""\n}');
  const [guildSessionMode, setGuildSessionMode] = useState("double_ratchet_like");
  const [guildSessionSenderIdentityKeyRef, setGuildSessionSenderIdentityKeyRef] = useState("player.identity");
  const [guildSessionSenderSignedPreKeyRef, setGuildSessionSenderSignedPreKeyRef] = useState("");
  const [guildSessionSenderOneTimePreKeyRef, setGuildSessionSenderOneTimePreKeyRef] = useState("");
  const [guildSessionRecipientIdentityKeyRef, setGuildSessionRecipientIdentityKeyRef] = useState("");
  const [guildSessionRecipientSignedPreKeyRef, setGuildSessionRecipientSignedPreKeyRef] = useState("");
  const [guildSessionRecipientOneTimePreKeyRef, setGuildSessionRecipientOneTimePreKeyRef] = useState("");
  const [guildSessionEpoch, setGuildSessionEpoch] = useState("1");
  const [guildSessionSealedSender, setGuildSessionSealedSender] = useState(true);
  const [guildConversationList, setGuildConversationList] = useState([]);
  const [guildConversationOutput, setGuildConversationOutput] = useState(null);
  const activeProfilePayload = useMemo(
    () => buildProfilePayload(profileName, profileEmail, profileTimezone),
    [profileName, profileEmail, profileTimezone]
  );
  const activeProfileMemberId = useMemo(
    () => deriveProfileMemberId(profileName, profileEmail),
    [profileName, profileEmail]
  );
  const [guildRelayStatus, setGuildRelayStatus] = useState("remote_pending");
  const [guildRelayReceiptText, setGuildRelayReceiptText] = useState('{\n  "relay_id": "relay_001"\n}');
  const [guildRegistryList, setGuildRegistryList] = useState([]);
  const [guildRegistryOutput, setGuildRegistryOutput] = useState(null);
  const [distributionId, setDistributionId] = useState("distribution.quantumquackery.main");
  const [distributionDisplayName, setDistributionDisplayName] = useState("Quantum Quackery Main");
  const [distributionBaseUrl, setDistributionBaseUrl] = useState("https://djinnos-shyagzun-atelier-api.onrender.com");
  const [distributionTransportKind, setDistributionTransportKind] = useState("https");
  const [distributionPublicKeyRef, setDistributionPublicKeyRef] = useState("");
  const [distributionProtocolFamily, setDistributionProtocolFamily] = useState("guild_message_signal_artifice");
  const [distributionProtocolVersion, setDistributionProtocolVersion] = useState("v1");
  const [distributionSupportedProtocolVersionsText, setDistributionSupportedProtocolVersionsText] = useState('[\n  "v1"\n]');
  const [distributionGuildIdsText, setDistributionGuildIdsText] = useState('[\n  "guild.atelier"\n]');
  const [distributionMetadataText, setDistributionMetadataText] = useState('{\n  "source": "atelier.desktop.guild_hall",\n  "website_url": "https://quantumquackery.org/",\n  "api_url": "https://djinnos-shyagzun-atelier-api.onrender.com",\n  "kernel_url": "https://djinnos-shyagzun-kernel.onrender.com"\n}');
  const [distributionRegistryList, setDistributionRegistryList] = useState([]);
  const [distributionRegistryOutput, setDistributionRegistryOutput] = useState(null);
  const [distributionShopWorkspaceId, setDistributionShopWorkspaceId] = useState("");
  const [distributionShopWorkspaceStatus, setDistributionShopWorkspaceStatus] = useState(null);
  const [distributionCapabilitiesOutput, setDistributionCapabilitiesOutput] = useState(null);
  const [serviceReadinessOutput, setServiceReadinessOutput] = useState(null);
  const [federationHealthOutput, setFederationHealthOutput] = useState(null);
  const [distributionHandshakeLocalId, setDistributionHandshakeLocalId] = useState("distribution.quantumquackery.main");
  const [distributionHandshakeMode, setDistributionHandshakeMode] = useState("mutual_hmac");
  const [distributionHandshakeProtocolFamily, setDistributionHandshakeProtocolFamily] = useState("guild_message_signal_artifice");
  const [distributionHandshakeLocalProtocolVersion, setDistributionHandshakeLocalProtocolVersion] = useState("v1");
  const [distributionHandshakeRemoteProtocolVersion, setDistributionHandshakeRemoteProtocolVersion] = useState("v1");
  const [distributionHandshakeNegotiatedProtocolVersion, setDistributionHandshakeNegotiatedProtocolVersion] = useState("v1");
  const [distributionHandshakeOutput, setDistributionHandshakeOutput] = useState(null);
  const [distributionHandshakeList, setDistributionHandshakeList] = useState([]);
  const [guildWandStatus, setGuildWandStatus] = useState(null);
  const [wandRegistryWandId, setWandRegistryWandId] = useState("wand_001");
  const [wandRegistryMakerId, setWandRegistryMakerId] = useState("maker.quant");
  const [wandRegistryMakerDate, setWandRegistryMakerDate] = useState("2026-03-08");
  const [wandRegistryAtelierOrigin, setWandRegistryAtelierOrigin] = useState("atelier.guildhall");
  const [wandRegistryStructuralFingerprint, setWandRegistryStructuralFingerprint] = useState("");
  const [wandRegistryCraftRecordHash, setWandRegistryCraftRecordHash] = useState("");
  const [wandRegistryMaterialProfileText, setWandRegistryMaterialProfileText] = useState("{\n  \"wood\": \"ash\",\n  \"core\": \"silver-thread\"\n}");
  const [wandRegistryDimensionsText, setWandRegistryDimensionsText] = useState("{\n  \"length_mm\": 340,\n  \"shaft_diameter_mm\": 11,\n  \"mass_g\": 31\n}");
  const [wandRegistryOwnershipChainText, setWandRegistryOwnershipChainText] = useState('[\n  {\n    "owner_id": "player",\n    "epoch": "creation"\n  }\n]');
  const [wandRegistryMetadataText, setWandRegistryMetadataText] = useState('{\n  "display_name": "North Ash Wand"\n}');
  const [wandRegistryList, setWandRegistryList] = useState([]);
  const [wandRegistryOutput, setWandRegistryOutput] = useState(null);
  const [guildTempleProvenanceHistory, setGuildTempleProvenanceHistory] = useState(() => {
    const raw = localStorage.getItem("atelier.temple_provenance_history");
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
    } catch {
      return [];
    }
  });
  const [guildTheatreProvenanceHistory, setGuildTheatreProvenanceHistory] = useState(() => {
    const raw = localStorage.getItem("atelier.theatre_provenance_history");
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
    } catch {
      return [];
    }
  });
  const [migrationStatus, setMigrationStatus] = useState(null);
  const [wandDamageWandId, setWandDamageWandId] = useState("wand_001");
  const [wandDamageNotifierId, setWandDamageNotifierId] = useState("Zo@user");
  const [wandDamageState, setWandDamageState] = useState("broken");
  const [wandDamageEventTag, setWandDamageEventTag] = useState("fracture_attest");
  const [wandDamageFiles, setWandDamageFiles] = useState([]);
  const [wandDamageValidation, setWandDamageValidation] = useState(null);
  const [wandDamageRecord, setWandDamageRecord] = useState(null);
  const [wandDamageHistory, setWandDamageHistory] = useState([]);
  const [wandEpochHistory, setWandEpochHistory] = useState([]);
  const [wandEpochPreviousId, setWandEpochPreviousId] = useState("");
  const [wandEpochRevoked, setWandEpochRevoked] = useState(true);
  const [wandEpochOutput, setWandEpochOutput] = useState(null);
  const [wandStatus, setWandStatus] = useState(null);
  const wandRegistryMinimumReady =
    String(wandRegistryWandId || "").trim() !== "" &&
    String(wandRegistryMakerId || "").trim() !== "";

  const guildProtocolStatus = useMemo(() => {
    const protocol = distributionCapabilitiesOutput?.messaging_protocol;
    const distributionProtocol = protocol?.distribution || {};
    const handshakeProtocol = protocol?.handshake || {};
    const requiredVersion = "v1";
    const family = String(distributionProtocol?.family || "").trim();
    const version = String(distributionProtocol?.version || "").trim();
    const supportedVersions = Array.isArray(distributionProtocol?.supported_versions)
      ? distributionProtocol.supported_versions.map((item) => String(item || "").trim()).filter(Boolean)
      : [];
    const negotiatedVersion = String(handshakeProtocol?.negotiated_version || "").trim();
    if (!String(guildRecipientDistributionId || "").trim()) {
      return { level: "local", label: "Local Only", detail: "No remote distribution selected." };
    }
    if (!family) {
      return { level: "unknown", label: "Unknown Protocol", detail: "Remote distribution has not advertised a messaging protocol." };
    }
    if (family !== "guild_message_signal_artifice") {
      return { level: "error", label: "Family Mismatch", detail: `Remote family ${family} is incompatible.` };
    }
    if (supportedVersions.length > 0 && !supportedVersions.includes(requiredVersion)) {
      return { level: "error", label: "Version Unsupported", detail: `Remote supports ${supportedVersions.join(", ")}, local requires ${requiredVersion}.` };
    }
    if (negotiatedVersion && negotiatedVersion !== requiredVersion) {
      return { level: "warning", label: "Handshake Drift", detail: `Handshake negotiated ${negotiatedVersion}, local requires ${requiredVersion}.` };
    }
    if (!negotiatedVersion) {
      return { level: "warning", label: "No Negotiated Version", detail: `Remote advertises ${version || requiredVersion}, but no handshake negotiation is recorded yet.` };
    }
    return { level: "ok", label: "Protocol Compatible", detail: `Remote ${family} ${version || requiredVersion}; handshake ${negotiatedVersion}.` };
  }, [distributionCapabilitiesOutput, guildRecipientDistributionId]);

  const buildTempleEntropySourcePayload = () => {
    const provenanceId = String(guildTempleProvenanceId || "").trim();
    if (!provenanceId) {
      return {};
    }
    return {
      schema_family: "temple_entropy_source",
      schema_version: "v1",
      provenance_id: provenanceId,
      source_type: String(guildTempleSourceType || "").trim() || "garden_observation",
      garden_id: String(guildTempleGardenId || "").trim() || null,
      plot_id: String(guildTemplePlotId || "").trim() || null,
      state_digest: guildTempleEntropyDigest || "temple_state_digest",
      metadata: {
        source: "atelier.desktop.temple_garden",
        caretaker: guildSenderId || "player",
      },
    };
  };

  const buildTheatreEntropySourcePayload = () => {
    const provenanceId = String(guildTheatreProvenanceId || "").trim();
    if (!provenanceId) {
      return {};
    }
    return {
      schema_family: "theatre_entropy_source",
      schema_version: "v1",
      provenance_id: provenanceId,
      source_type: String(guildTheatreSourceType || "").trim() || "performance_upload",
      performance_id: String(guildTheatrePerformanceId || "").trim() || null,
      upload_id: String(guildTheatreUploadId || "").trim() || null,
      media_digest: guildTheatreEntropyDigest || "theatre_media_digest",
      metadata: {
        source: "atelier.desktop.guild_hall",
        troupe: "esoteric_theatre",
      },
    };
  };

  const buildGuildSecuritySessionPayload = () => ({
    session_mode: String(guildSessionMode || "").trim() || "double_ratchet_like",
    sender_identity_key_ref: String(guildSessionSenderIdentityKeyRef || `${activeProfileMemberId}.identity`).trim(),
    sender_signed_pre_key_ref: String(guildSessionSenderSignedPreKeyRef || "").trim(),
    sender_one_time_pre_key_ref: String(guildSessionSenderOneTimePreKeyRef || "").trim(),
    recipient_identity_key_ref: String(guildSessionRecipientIdentityKeyRef || "").trim(),
    recipient_signed_pre_key_ref: String(guildSessionRecipientSignedPreKeyRef || "").trim(),
    recipient_one_time_pre_key_ref: String(guildSessionRecipientOneTimePreKeyRef || "").trim(),
    session_epoch: clampInt(guildSessionEpoch, 1, 999999, 1),
    sealed_sender: Boolean(guildSessionSealedSender),
  });

  const applyGuildSecuritySessionPayload = (payload) => {
    const session = payload && typeof payload === "object" ? payload : {};
    setGuildSessionMode(String(session.session_mode || "double_ratchet_like"));
    setGuildSessionSenderIdentityKeyRef(String(session.sender_identity_key_ref || `${activeProfileMemberId}.identity`));
    setGuildSessionSenderSignedPreKeyRef(String(session.sender_signed_pre_key_ref || ""));
    setGuildSessionSenderOneTimePreKeyRef(String(session.sender_one_time_pre_key_ref || ""));
    setGuildSessionRecipientIdentityKeyRef(String(session.recipient_identity_key_ref || ""));
    setGuildSessionRecipientSignedPreKeyRef(String(session.recipient_signed_pre_key_ref || ""));
    setGuildSessionRecipientOneTimePreKeyRef(String(session.recipient_one_time_pre_key_ref || ""));
    setGuildSessionEpoch(String(session.session_epoch ?? 1));
    setGuildSessionSealedSender(Boolean(session.sealed_sender ?? true));
  };

  const fillTempleEntropySourcePreset = () => {
    setGuildTempleProvenanceId("garden.temple.main.north-bed.epoch1");
    setGuildTempleSourceType("garden_observation");
    setGuildTempleGardenId("temple.main");
    setGuildTemplePlotId("north-bed");
  };

  const fillTheatreEntropySourcePreset = () => {
    setGuildTheatreProvenanceId("theatre.performance.esoteric_01");
    setGuildTheatreSourceType("performance_upload");
    setGuildTheatrePerformanceId("esoteric_01");
    setGuildTheatreUploadId("upload_01");
  };

  useEffect(() => {
    localStorage.setItem("atelier.temple_provenance_history", JSON.stringify(guildTempleProvenanceHistory));
  }, [guildTempleProvenanceHistory]);

  useEffect(() => {
    localStorage.setItem("atelier.theatre_provenance_history", JSON.stringify(guildTheatreProvenanceHistory));
  }, [guildTheatreProvenanceHistory]);

  useEffect(() => {
    if (section !== "Temple and Gardens" && section !== "Guild Hall") {
      return;
    }
    loadWandRegistryList().catch((error) => {
      console.error("wand_registry_autoload_failed", error);
    });
  }, [section]);

  useEffect(() => {
    const parsed = parseObjectJson(guildSecuritySessionText, {});
    applyGuildSecuritySessionPayload(parsed);
  }, [guildSecuritySessionText]);

  useEffect(() => {
    const nextText = JSON.stringify(buildGuildSecuritySessionPayload(), null, 2);
    if (nextText !== guildSecuritySessionText) {
      setGuildSecuritySessionText(nextText);
    }
  }, [
    guildSessionMode,
    guildSessionSenderIdentityKeyRef,
    guildSessionSenderSignedPreKeyRef,
    guildSessionSenderOneTimePreKeyRef,
    guildSessionRecipientIdentityKeyRef,
    guildSessionRecipientSignedPreKeyRef,
    guildSessionRecipientOneTimePreKeyRef,
    guildSessionEpoch,
    guildSessionSealedSender,
    activeProfileMemberId,
  ]);

  useEffect(() => {
    setGuildSenderId((prev) => {
      const current = String(prev || "").trim();
      if (!current || current === "player") {
        return activeProfileMemberId;
      }
      return prev;
    });
    setGuildParticipantMemberIdsText((prev) => {
      let parsed = [];
      try {
        parsed = JSON.parse(prev || "[]");
      } catch {
        parsed = [];
      }
      if (!Array.isArray(parsed)) {
        parsed = [];
      }
      const normalized = parsed.map((item) => String(item || "").trim()).filter(Boolean);
      if (normalized.length === 0 || (normalized.length === 1 && normalized[0] === "player")) {
        return JSON.stringify([activeProfileMemberId], null, 2);
      }
      return prev;
    });
    setGuildSessionSenderIdentityKeyRef((prev) => {
      const current = String(prev || "").trim();
      if (!current || current === "player.identity") {
        return `${activeProfileMemberId}.identity`;
      }
      return prev;
    });
  }, [activeProfileMemberId]);

  useEffect(() => {
    if (section !== "Guild Hall") {
      return;
    }
    loadGuildRegistryList().catch((error) => {
      console.error("guild_registry_autoload_failed", error);
    });
    loadDistributionRegistryList().catch((error) => {
      console.error("distribution_registry_autoload_failed", error);
    });
    loadDistributionHandshakes().catch((error) => {
      console.error("distribution_handshake_autoload_failed", error);
    });
    loadGuildConversationList().catch((error) => {
      console.error("guild_conversation_autoload_failed", error);
    });
    loadServiceReadiness().catch((error) => {
      console.error("service_readiness_autoload_failed", error);
    });
    loadFederationHealth().catch((error) => {
      console.error("federation_health_autoload_failed", error);
    });
  }, [section]);

  useEffect(() => {
    if (section !== "Foyer") {
      return;
    }
    loadServiceReadiness().catch((error) => {
      console.error("foyer_service_readiness_autoload_failed", error);
    });
    loadFederationHealth().catch((error) => {
      console.error("foyer_federation_health_autoload_failed", error);
    });
  }, [section]);

  useEffect(() => {
    const selectedGuild = guildRegistryList.find((item) => String(item?.guild_id || "") === String(guildRecipientGuildId || "").trim());
    if (!selectedGuild) {
      return;
    }
    const homeDistribution = String(selectedGuild?.distribution_id || "").trim();
    if (homeDistribution && homeDistribution !== String(guildRecipientDistributionId || "").trim()) {
      setGuildRecipientDistributionId(homeDistribution);
    }
  }, [guildRecipientGuildId, guildRegistryList, guildRecipientDistributionId]);

  useEffect(() => {
    const guilds = Array.isArray(distributionCapabilitiesOutput?.guilds) ? distributionCapabilitiesOutput.guilds : [];
    const selectedGuild = guilds.find((item) => String(item?.guild_id || "") === String(guildRecipientGuildId || "").trim());
    const channels = Array.isArray(selectedGuild?.channels) ? selectedGuild.channels : [];
    if (!channels.length) {
      return;
    }
    const currentChannel = String(guildRecipientChannelId || "").trim();
    if (!currentChannel || !channels.includes(currentChannel)) {
      setGuildRecipientChannelId(String(channels[0] || ""));
    }
  }, [distributionCapabilitiesOutput, guildRecipientGuildId, guildRecipientChannelId]);

  useEffect(() => {
    const safeDistributionId = String(guildRecipientDistributionId || "").trim();
    if (!safeDistributionId) {
      setDistributionCapabilitiesOutput(null);
      return;
    }
    loadDistributionCapabilities(safeDistributionId).catch((error) => {
      console.error("distribution_capabilities_autoload_failed", error);
    });
  }, [guildRecipientDistributionId]);

  const rememberProvenanceId = (kind, value) => {
    const normalized = String(value || "").trim();
    if (!normalized) {
      return;
    }
    if (kind === "temple") {
      setGuildTempleProvenanceHistory((prev) => [normalized, ...prev.filter((item) => item !== normalized)].slice(0, 12));
      return;
    }
    if (kind === "theatre") {
      setGuildTheatreProvenanceHistory((prev) => [normalized, ...prev.filter((item) => item !== normalized)].slice(0, 12));
    }
  };
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
  const [studioFsPythonFiles, setStudioFsPythonFiles] = useState([]);
  const [studioFsSelectedPython, setStudioFsSelectedPython] = useState("");
  const [studioFsPythonAutoWatch, setStudioFsPythonAutoWatch] = useState(
    () => localStorage.getItem("atelier.studio_fs_python_auto_watch") === "1"
  );
  const [studioFsPythonWatchMs, setStudioFsPythonWatchMs] = useState(
    () => localStorage.getItem("atelier.studio_fs_python_watch_ms") || "2000"
  );
  const [studioFsSceneFiles, setStudioFsSceneFiles] = useState([]);
  const [studioFsSpriteFiles, setStudioFsSpriteFiles] = useState([]);
  const [studioFsAudioFiles, setStudioFsAudioFiles] = useState([]);
  const [studioFsSelectedScene, setStudioFsSelectedScene] = useState("");
  const [studioFsSelectedSprite, setStudioFsSelectedSprite] = useState("");
  const [studioFsSelectedAudio, setStudioFsSelectedAudio] = useState("");
  const [studioFsRuntimePlanFiles, setStudioFsRuntimePlanFiles] = useState([]);
  const [studioFsRuntimePlanPath, setStudioFsRuntimePlanPath] = useState(
    () => localStorage.getItem("atelier.studio_fs_runtime_plan_path") || "gameplay/runtime_plans/dungeon_campaign_seed.template.json"
  );
  const [rendererAudioStageLabel, setRendererAudioStageLabel] = useState("");
  const [rendererAudioStages, setRendererAudioStages] = useState([]);
  const [rendererSandboxPackName, setRendererSandboxPackName] = useState(
    () => localStorage.getItem("atelier.renderer_sandbox.pack_name") || "render_pack_alpha"
  );
  const [rendererSandboxPackNotes, setRendererSandboxPackNotes] = useState(
    () => localStorage.getItem("atelier.renderer_sandbox.pack_notes") || ""
  );
  const [rendererSandboxDraftText, setRendererSandboxDraftText] = useState(
    () => localStorage.getItem("atelier.renderer_sandbox.draft") || "{}"
  );
  const [rendererSandboxPacks, setRendererSandboxPacks] = useState(() => {
    try {
      const raw = localStorage.getItem("atelier.renderer_sandbox.packs");
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const [rendererSandboxSelectedId, setRendererSandboxSelectedId] = useState(
    () => localStorage.getItem("atelier.renderer_sandbox.selected_id") || ""
  );
  const [rendererSandboxValidation, setRendererSandboxValidation] = useState(null);
  const [rendererSandboxStatus, setRendererSandboxStatus] = useState("idle");
  const studioFsPythonWatchLastRef = useRef("");

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
      { label: "Contracts", value: contracts.length },
      { label: "Suppliers", value: suppliers.length },
      { label: "Inventory", value: inventoryItems.length }
    ],
    [contacts, bookings, lessons, modules, leads, clients, quotes, orders, contracts, suppliers, inventoryItems]
  );
  const studioSelectedFile = useMemo(
    () => studioFiles.find((file) => file.id === studioSelectedFileId) || null,
    [studioFiles, studioSelectedFileId]
  );
  const rendererSandboxSelectedPack = useMemo(
    () => rendererSandboxPacks.find((pack) => pack && pack.pack_id === rendererSandboxSelectedId) || null,
    [rendererSandboxPacks, rendererSandboxSelectedId]
  );

  useEffect(() => localStorage.setItem("atelier.section", section), [section]);
  useEffect(() => localStorage.setItem("atelier.role", role), [role]);
  useEffect(() => {
    if (authToken) localStorage.setItem("atelier.auth_token", authToken);
    else localStorage.removeItem("atelier.auth_token");
  }, [authToken]);
  useEffect(() => {
    if (artisanId) localStorage.setItem("atelier.artisan_id", artisanId);
    else localStorage.removeItem("atelier.artisan_id");
  }, [artisanId]);
  useEffect(() => {
    if (workshopId) localStorage.setItem("atelier.workshop_id", workshopId);
    else localStorage.removeItem("atelier.workshop_id");
  }, [workshopId]);
  useEffect(() => localStorage.setItem("atelier.workspace", workspaceId), [workspaceId]);
  useEffect(() => localStorage.setItem("atelier.tile_traversal_class", tileTraversalClass), [tileTraversalClass]);
  useEffect(() => localStorage.setItem("atelier.profile_name", profileName), [profileName]);
  useEffect(() => localStorage.setItem("atelier.profile_email", profileEmail), [profileEmail]);
  useEffect(() => localStorage.setItem("atelier.profile_tz", profileTimezone), [profileTimezone]);
  useEffect(() => localStorage.setItem("atelier.post_target", actionPostTarget), [actionPostTarget]);
  useEffect(() => localStorage.setItem("atelier.post_engine_file_id", actionPostEngineFileId), [actionPostEngineFileId]);
  useEffect(() => localStorage.setItem("atelier.post_repo_folder", actionPostRepoFolder), [actionPostRepoFolder]);
  useEffect(() => localStorage.setItem("atelier.engine_inbox_consume_max", engineInboxConsumeMax), [engineInboxConsumeMax]);
  useEffect(
    () => localStorage.setItem("atelier.engine_inbox_preview_only", engineInboxPreviewOnly ? "1" : "0"),
    [engineInboxPreviewOnly]
  );
  useEffect(
    () => localStorage.setItem("atelier.engine_inbox_strict_validation", engineInboxStrictValidation ? "1" : "0"),
    [engineInboxStrictValidation]
  );
  useEffect(() => localStorage.setItem("atelier.studio_folders", JSON.stringify(studioFolders)), [studioFolders]);
  useEffect(() => localStorage.setItem("atelier.studio_files", JSON.stringify(studioFiles)), [studioFiles]);
  useEffect(() => localStorage.setItem("atelier.studio_selected", studioSelectedFileId), [studioSelectedFileId]);
  useEffect(() => localStorage.setItem("atelier.studio_fs_root", studioFsRoot), [studioFsRoot]);
  useEffect(() => localStorage.setItem("atelier.studio_fs_runtime_plan_path", studioFsRuntimePlanPath), [studioFsRuntimePlanPath]);
  useEffect(() => localStorage.setItem("atelier.renderer_sandbox.pack_name", rendererSandboxPackName), [rendererSandboxPackName]);
  useEffect(() => localStorage.setItem("atelier.renderer_sandbox.pack_notes", rendererSandboxPackNotes), [rendererSandboxPackNotes]);
  useEffect(() => localStorage.setItem("atelier.renderer_sandbox.draft", rendererSandboxDraftText), [rendererSandboxDraftText]);
  useEffect(() => localStorage.setItem("atelier.renderer_sandbox.selected_id", rendererSandboxSelectedId), [rendererSandboxSelectedId]);
  useEffect(
    () => localStorage.setItem("atelier.renderer_sandbox.packs", JSON.stringify(rendererSandboxPacks)),
    [rendererSandboxPacks]
  );
  useEffect(
    () => localStorage.setItem("atelier.studio_fs_python_auto_watch", studioFsPythonAutoWatch ? "1" : "0"),
    [studioFsPythonAutoWatch]
  );
  useEffect(() => localStorage.setItem("atelier.studio_fs_python_watch_ms", studioFsPythonWatchMs), [studioFsPythonWatchMs]);
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
    studioFsPythonWatchLastRef.current = "";
  }, [studioFsRoot, studioFsSelectedPython]);
  useEffect(() => {
    if (!studioFsPythonAutoWatch || !hasDesktopFs() || !studioFsRoot || !studioFsSelectedPython) {
      return undefined;
    }
    const watchMs = Math.max(500, Number.parseInt(studioFsPythonWatchMs || "2000", 10) || 2000);
    let closed = false;
    const tick = async () => {
      try {
        const result = await window.atelierDesktop.fs.readTextFile(studioFsRoot, studioFsSelectedPython);
        if (!result || !result.ok || typeof result.content !== "string") {
          return;
        }
        const content = result.content;
        if (content === studioFsPythonWatchLastRef.current) {
          return;
        }
        studioFsPythonWatchLastRef.current = content;
        const filename =
          typeof result.filename === "string" && result.filename.trim()
            ? result.filename
            : studioFsSelectedPython;
        const existing = studioFiles.find((file) => file.folder === "scripts" && file.name === filename);
        const nextId = existing ? existing.id : makeStudioFileId();
        if (closed) {
          return;
        }
        setStudioFiles((prev) => {
          const existingIndex = prev.findIndex((file) => file.folder === "scripts" && file.name === filename);
          if (existingIndex >= 0) {
            const next = [...prev];
            if (next[existingIndex].content === content) {
              return prev;
            }
            next[existingIndex] = { ...next[existingIndex], content };
            return next;
          }
          return [
            ...prev,
            {
              id: nextId,
              name: filename,
              folder: "scripts",
              content,
            },
          ];
        });
        setStudioSelectedFileId(nextId);
        setRendererPython(content);
        setRendererPipeline((prev) => ({ ...prev, pythonFileId: nextId }));
        setRendererGameStatus(`python_watch:${filename}`);
      } catch {
        // watch loop is best-effort; failures are shown by explicit import actions.
      }
    };
    void tick();
    const timer = window.setInterval(() => {
      void tick();
    }, watchMs);
    return () => {
      closed = true;
      window.clearInterval(timer);
    };
  }, [studioFsPythonAutoWatch, studioFsPythonWatchMs, studioFsRoot, studioFsSelectedPython, studioFiles]);
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
    if (rendererSandboxPacks.length === 0) {
      if (rendererSandboxSelectedId) {
        setRendererSandboxSelectedId("");
      }
      return;
    }
    if (!rendererSandboxPacks.some((pack) => pack && pack.pack_id === rendererSandboxSelectedId)) {
      const first = rendererSandboxPacks[0];
      setRendererSandboxSelectedId(first && first.pack_id ? String(first.pack_id) : "");
    }
  }, [rendererSandboxPacks, rendererSandboxSelectedId]);
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
      headers: buildHeaders(role, caps, token, artisanId, workshopId, authToken, workspaceId),
      body: body === null ? undefined : JSON.stringify(body)
    });
    const data = parseSafeJson(await response.text());
    setOutput(JSON.stringify(data, null, 2));
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async function apiCallRaw(path, method, body, tokenOverride) {
    const token = tokenOverride === undefined ? adminGateToken : tokenOverride;
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: buildHeaders(role, caps, token, artisanId, workshopId, authToken, workspaceId),
      body: body === null ? undefined : JSON.stringify(body)
    });
    const text = await response.text();
    setOutput(text);
    if (!response.ok) {
      throw new Error(text || `Request failed ${response.status}`);
    }
    return text;
  }

  async function kernelCall(path, method, body) {
    const response = await fetch(`${KERNEL_BASE}${path}`, {
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

  function buildPostEnvelope(path, body, actionName) {
    return {
      action: actionName,
      method: "POST",
      path,
      workspace_id: workspaceId,
      realm_id: rendererRealmId,
      posted_at: new Date().toISOString(),
      target: actionPostTarget,
      payload: body && typeof body === "object" ? body : {}
    };
  }

  function postToEngineInbox(path, body, actionName) {
    const envelope = buildPostEnvelope(path, body, actionName);
    const engineState = parseObjectJson(rendererEngineStateText, {});
    const currentInbox = Array.isArray(engineState.post_inbox) ? engineState.post_inbox : [];
    const nextInbox = [...currentInbox, envelope].slice(-200);
    const nextState = { ...engineState, post_inbox: nextInbox };
    setRendererEngineStateText(JSON.stringify(nextState, null, 2));
    setRendererGameStatus(`post_inbox:${nextInbox.length}`);
    const selectedEngineFile = studioFiles.find((file) => file.id === actionPostEngineFileId) || null;
    return {
      ok: true,
      target: "engine_inbox",
      queued: 1,
      queue_size: nextInbox.length,
      engine_file_id: selectedEngineFile ? selectedEngineFile.id : null,
      engine_file_name: selectedEngineFile ? `${selectedEngineFile.folder}/${selectedEngineFile.name}` : null,
      envelope
    };
  }

  function postToRepo(path, body, actionName) {
    const envelope = buildPostEnvelope(path, body, actionName);
    const folder = String(actionPostRepoFolder || "runtime-posts").trim() || "runtime-posts";
    if (!studioFolders.includes(folder)) {
      setStudioFolders((prev) => [...prev, folder]);
    }
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fileName = `${stamp}-${String(actionName || "post").replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
    const nextFile = {
      id: makeStudioFileId(),
      name: fileName,
      folder,
      content: JSON.stringify(envelope, null, 2)
    };
    setStudioFiles((prev) => [...prev, nextFile]);
    setStudioSelectedFileId(nextFile.id);
    return {
      ok: true,
      target: "repo",
      file_id: nextFile.id,
      file: `${folder}/${fileName}`,
      envelope
    };
  }

  async function postAction(path, body, actionName) {
    if (actionPostTarget === "api") {
      return apiCall(path, "POST", body);
    }
    const data =
      actionPostTarget === "engine_inbox"
        ? postToEngineInbox(path, body, actionName)
        : postToRepo(path, body, actionName);
    setOutput(JSON.stringify(data, null, 2));
    return data;
  }

  async function consumeEngineInbox() {
    await runAction("engine_inbox_consume", async () => {
      const parsedState = parseObjectJson(rendererEngineStateText, {});
      const currentInbox = Array.isArray(parsedState.post_inbox) ? parsedState.post_inbox : [];
      const selectedEngineFile = studioFiles.find((file) => file.id === actionPostEngineFileId) || null;
      let handlerMap = {};
      if (selectedEngineFile && typeof selectedEngineFile.content === "string" && selectedEngineFile.content.trim()) {
        const parsed = parseObjectJson(selectedEngineFile.content, {});
        if (parsed && typeof parsed === "object" && parsed.post_handlers && typeof parsed.post_handlers === "object") {
          handlerMap = parsed.post_handlers;
        }
      }
      const consume = consumeInboxBatch(parsedState, currentInbox, {
        take: engineInboxConsumeMax,
        strictValidation: engineInboxStrictValidation,
        handlerMap
      });
      const nextState = consume.state;
      const result = {
        ...consume.result,
        preview_only: Boolean(engineInboxPreviewOnly)
      };
      setEngineInboxResult(result);
      setOutput(JSON.stringify(result, null, 2));

      if (engineInboxPreviewOnly) {
        return result;
      }

      setRendererEngineStateText(JSON.stringify(nextState, null, 2));
      setRendererGameStatus(`inbox_consumed:${Number(result.consumed || 0)}`);
      if (actionPostEngineFileId) {
        setStudioFiles((prev) =>
          prev.map((file) => (
            file.id === actionPostEngineFileId
              ? { ...file, content: JSON.stringify(nextState, null, 2) }
              : file
          ))
        );
      }
      return result;
    });
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

  async function fetchMyWorkspace() {
    try {
      const data = await apiCall("/v1/me/workspace", "GET", null);
      if (data && data.workspace_id) {
        setWorkspaceId(data.workspace_id);
        localStorage.setItem("atelier.workspace", data.workspace_id);
        if (Array.isArray(data.workspaces)) {
          setWorkspaceList(data.workspaces);
        }
      }
    } catch (err) {
      const detail = (() => { try { return JSON.parse(err.message)?.detail; } catch { return null; } })();
      if (detail === "no_workspace_membership") {
        // Authenticated artisan with no workspace — should not happen after login provisioning.
        setNotice("No workspace found. Please contact your steward.");
      }
      // Other errors: keep current workspaceId (network issue, legacy mode, etc.)
    }
  }

  useEffect(() => {
    void fetchMyWorkspace();
  }, [role, caps]);

  async function login() {
    setLoginError("");
    try {
      const res = await fetch(`${API_BASE}/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artisan_id: loginArtisanId, artisan_code: loginArtisanCode }),
      });
      const data = parseSafeJson(await res.text());
      if (!res.ok) {
        setLoginError(data.detail || "login_failed");
        return;
      }
      setAuthToken(data.token);
      setArtisanId(data.artisan_id);
      setWorkshopId(data.workshop_id);
      setRole(data.role);
      setLoginArtisanCode("");
      void fetchMyWorkspace();
    } catch (err) {
      setLoginError(err.message || "login_failed");
    }
  }

  function logout() {
    setAuthToken(null);
    setArtisanId("");
    setWorkshopId("");
    setLoginArtisanId("");
    setLoginArtisanCode("");
    setLoginError("");
  }

  async function redeemInvite() {
    setOnboardError("");
    setOnboardStatus("redeeming");
    try {
      const data = await apiCall("/v1/auth/redeem-invite", "POST", {
        code: onboardCode.trim().toUpperCase(),
        artisan_id: onboardArtisanId.trim(),
        profile_name: onboardName.trim(),
        profile_email: onboardEmail.trim(),
        artisan_code: onboardPassword,
      });
      // Auto-login with the returned token
      localStorage.setItem("atelier.auth_token", data.token);
      localStorage.setItem("atelier.artisan_id", data.artisan_id);
      localStorage.setItem("atelier.workshop_id", data.workshop_id);
      localStorage.setItem("atelier.role", data.role);
      setAuthToken(data.token);
      setArtisanId(data.artisan_id);
      setWorkshopId(data.workshop_id);
      setRole(data.role);
      setOnboardCode("");
      setOnboardArtisanId("");
      setOnboardName("");
      setOnboardEmail("");
      setOnboardPassword("");
      setOnboardStatus("done");
    } catch (e) {
      setOnboardError(String(e));
      setOnboardStatus("idle");
    }
  }

  async function issueInvite() {
    await runAction("invite_issue", async () => {
      const data = await apiCall("/v1/auth/invite", "POST", {
        role: issueInviteRole,
        note: issueInviteNote,
        max_uses: issueInviteMaxUses,
      });
      setIssuedInviteCode(data.code);
      setIssueInviteNote("");
      return data;
    });
  }

  async function createWorkspace() {
    await runAction("workspace_create", async () => {
      const data = await apiCall("/v1/admin/workspaces", "POST", {
        name: newWorkspaceName,
        owner_artisan_id: newWorkspaceOwner,
      });
      setNewWorkspaceName("");
      setNewWorkspaceOwner("");
      await fetchMyWorkspace();
      return data;
    });
  }

  async function addWorkspaceMember() {
    await runAction("workspace_add_member", async () => {
      const data = await apiCall(
        `/v1/admin/workspaces/${encodeURIComponent(addMemberWorkspaceId)}/members`,
        "POST",
        { artisan_id: addMemberArtisanId, role: addMemberRole }
      );
      setAddMemberArtisanId("");
      return data;
    });
  }

  const makeList = (path, setter, action) => async () =>
    runAction(action, async () => {
      const data = await apiCall(path, "GET", null);
      setter(data);
      return data;
    });

  const listContacts = makeList("/v1/crm/contacts", setContacts, "contacts_list");
  const listBookings = makeList("/v1/booking", setBookings, "bookings_list");
  const listLessons = makeList("/v1/lessons", setLessons, "lessons_list");
  const listLessonProgress = () =>
    runAction("lessons_progress_list", async () => {
      const data = await apiCall(
        `/v1/lessons/progress?actor_id=${encodeURIComponent(lessonActorId)}`,
        "GET",
        null
      );
      setLessonProgress(data);
      return data;
    });
  const listModules = makeList("/v1/modules", setModules, "modules_list");
  const listLeads = makeList("/v1/leads", setLeads, "leads_list");
  const listClients = makeList("/v1/clients", setClients, "clients_list");
  const listQuotes = makeList("/v1/quotes", setQuotes, "quotes_list");
  const listOrders = makeList("/v1/orders", setOrders, "orders_list");
  const listContracts = makeList("/v1/contracts", setContracts, "contracts_list");
  const listSuppliers = makeList("/v1/suppliers", setSuppliers, "suppliers_list");
  const listInventory = makeList("/v1/inventory", setInventoryItems, "inventory_list");
  const loadPublicQuotes = async () =>
    runAction("public_quotes_list", async () => {
      const data = await publicApiCall(`/public/commission-hall/quotes?workspace_id=${encodeURIComponent(workspaceId)}`, "GET", null);
      setPublicQuotes(data);
      return data;
    });

  const loadLedgerEntries = async () =>
    runAction("ledger_entries", async () => {
      const data = await apiCall("/v1/ledger/entries", "GET", null);
      setLedgerEntries(Array.isArray(data) ? data : []);
      return data;
    });

  const loadLedgerSummary = async () =>
    runAction("ledger_summary", async () => {
      const data = await apiCall(
        `/v1/ledger/payouts/summary?month=${encodeURIComponent(ledgerMonth)}`,
        "GET",
        null
      );
      setLedgerSummary(data);
      return data;
    });

  const runLedgerPayouts = async (dryRun) =>
    runAction("ledger_payout_run", async () => {
      const data = await apiCall(
        `/v1/ledger/payouts/run?month=${encodeURIComponent(ledgerMonth)}&dry_run=${dryRun ? "true" : "false"}`,
        "POST",
        null
      );
      setLedgerSummary(data);
      return data;
    });

  const exportLedgerCsv = async () => {
    const text = await apiCallRaw(
      `/v1/ledger/payouts/export?month=${encodeURIComponent(ledgerMonth)}`,
      "GET",
      null
    );
    downloadText(`payouts-${ledgerMonth}.csv`, text, "text/csv");
  };

  const exportLedger1099 = async () => {
    const text = await apiCallRaw(
      `/v1/ledger/payouts/1099?month=${encodeURIComponent(ledgerMonth)}`,
      "GET",
      null
    );
    downloadText(`payouts-1099-${ledgerMonth}.csv`, text, "text/csv");
  };

  const createContract = async () =>
    createEntity(
      "contracts_create",
      "/v1/contracts",
      {
        workspace_id: workspaceId,
        title: contractTitle,
        category: contractCategory,
        party_name: contractPartyName,
        party_email: contractPartyEmail || null,
        party_phone: contractPartyPhone || null,
        artisan_id: contractArtisanId || null,
        amount_cents: Number.parseInt(contractAmount || "0", 10),
        currency: contractCurrency,
        terms: contractTerms,
        notes: contractNotes,
      },
      () => {
        setContractTitle("");
        setContractPartyName("");
        setContractPartyEmail("");
        setContractPartyPhone("");
        setContractArtisanId("");
        setContractAmount("");
        setContractTerms("");
        setContractNotes("");
      },
      listContracts
    );

  const updateContract = async () => {
    const safeId = String(contractSelectedId || "").trim();
    if (!safeId) {
      throw new Error("contract_id_required");
    }
    return runAction("contracts_update", async () => {
      const data = await apiCall(
        `/v1/contracts/${encodeURIComponent(safeId)}`,
        "PATCH",
        {
          title: contractTitle || null,
          category: contractCategory || null,
          party_name: contractPartyName || null,
          party_email: contractPartyEmail || null,
          party_phone: contractPartyPhone || null,
          artisan_id: contractArtisanId || null,
          amount_cents: contractAmount ? Number.parseInt(contractAmount || "0", 10) : null,
          currency: contractCurrency || null,
          terms: contractTerms || null,
          notes: contractNotes || null,
        }
      );
      await listContracts();
      return data;
    });
  };

  const validateContract = async () => {
    const safeId = String(contractSelectedId || "").trim();
    if (!safeId) {
      throw new Error("contract_id_required");
    }
    return runAction("contracts_validate", async () => {
      const data = await apiCall(
        `/v1/contracts/${encodeURIComponent(safeId)}/validate`,
        "POST",
        null
      );
      await listContracts();
      return data;
    });
  };

  const cancelContract = async () => {
    const safeId = String(contractSelectedId || "").trim();
    if (!safeId) {
      throw new Error("contract_id_required");
    }
    return runAction("contracts_cancel", async () => {
      const data = await apiCall(
        `/v1/contracts/${encodeURIComponent(safeId)}/cancel`,
        "POST",
        null
      );
      await listContracts();
      return data;
    });
  };

  const processContract = async () => {
    const safeId = String(contractSelectedId || "").trim();
    if (!safeId) {
      throw new Error("contract_id_required");
    }
    return runAction("contracts_process", async () => {
      const data = await apiCall(
        `/v1/contracts/${encodeURIComponent(safeId)}/process`,
        "POST",
        null
      );
      await listContracts();
      return data;
    });
  };
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
          listLessonProgress(),
          listModules(),
          listLeads(),
          listClients(),
          listQuotes(),
          listOrders(),
          listContracts(),
          listSuppliers(),
          listInventory()
        ]);
      return {};
    });
  }

  async function consumeLesson(lessonId) {
    await runAction("lesson_consume", async () => {
      const payload = {
        workspace_id: workspaceId,
        actor_id: lessonActorId,
        lesson_id: lessonId,
        status: "consumed",
      };
      const data = await apiCall("/v1/lessons/consume", "POST", payload);
      await listLessonProgress();
      return data;
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
        context: { workspace_id: workspaceId, realm_id: rendererRealmId },
      })
    );
  }

  async function emitCobraPlacements() {
    await runAction("cobra_emit_placements", async () => {
      if (validateBeforeEmit) {
        const validation = await apiCall("/v1/content/validate", "POST", {
          workspace_id: workspaceId,
          realm_id: rendererRealmId,
          scene_id: `${rendererRealmId}/renderer-lab`,
          source: "cobra",
          payload: rendererCobra,
        });
        setContentValidateOutput(validation);
        setValidationSummary({
          ok: Boolean(validation && validation.ok),
          errors: Array.isArray(validation && validation.errors) ? validation.errors.length : 0,
          warnings: Array.isArray(validation && validation.warnings) ? validation.warnings.length : 0,
        });
        if (!validation.ok) {
          throw new Error("cobra_emit: validation failed");
        }
      }
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
            realm_id: rendererRealmId,
            cobra_entity: entity,
            akinenwun: typeof entity.akinenwun === "string" ? entity.akinenwun : null
          }
        });
      }
      return { placed: parsed.entities.length };
    });
  }

  async function emitScenePlacements() {
    await runAction("scene_emit_placements", async () => {
      const spec = parseObjectJson(rendererGameSpecText, {});
      const entities = Array.isArray(spec.entities) ? spec.entities : [];
      if (entities.length === 0) {
        throw new Error("scene_emit: no entities in renderer game spec");
      }
      const sceneObj = spec.scene && typeof spec.scene === "object" ? spec.scene : {};
      const sceneId = String(sceneObj.id || sceneObj.name || "renderer_scene");
      if (validateBeforeEmit) {
        const validation = await apiCall("/v1/content/validate", "POST", {
          workspace_id: workspaceId,
          realm_id: rendererRealmId,
          scene_id: sceneId.includes("/") ? sceneId : `${rendererRealmId}/${sceneId}`,
          source: "json",
          payload: rendererGameSpecText,
        });
        setContentValidateOutput(validation);
        setValidationSummary({
          ok: Boolean(validation && validation.ok),
          errors: Array.isArray(validation && validation.errors) ? validation.errors.length : 0,
          warnings: Array.isArray(validation && validation.warnings) ? validation.warnings.length : 0,
        });
        if (!validation.ok) {
          throw new Error("scene_emit: validation failed");
        }
      }
      const sorted = [...entities].sort((a, b) => {
        const aId = String(a && typeof a === "object" ? a.id || "" : "");
        const bId = String(b && typeof b === "object" ? b.id || "" : "");
        return aId.localeCompare(bId);
      });
      for (const entity of sorted) {
        const e = entity && typeof entity === "object" ? entity : {};
        const entityId = String(e.id || "entity");
        const x = Number(e.x || 0);
        const y = Number(e.y || 0);
        const kind = String(e.kind || "token");
        const rawLine = `scene.entity ${sceneId} ${entityId} ${kind} ${x} ${y}`;
        await apiCall("/v1/ambroflow/place", "POST", {
          raw: rawLine,
          scene_id: sceneId,
          context: {
            workspace_id: workspaceId,
            realm_id: rendererRealmId,
            source: "renderer_scene_emit",
            entity: e
          }
        });
      }
      return { placed: sorted.length, scene_id: sceneId };
    });
  }

  async function emitHeadlessQuest() {
    await runAction("game_headless_quest_emit", async () => {
      const payload = parseObjectJson(headlessQuestText, {});
      return postAction("/v1/game/quests/headless/emit", payload, "game_headless_quest_emit");
    });
  }

  async function emitMeditation() {
    await runAction("game_meditation_emit", async () => {
      const payload = parseObjectJson(meditationText, {});
      return postAction("/v1/game/meditation/emit", payload, "game_meditation_emit");
    });
  }

  async function emitSceneGraph() {
    await runAction("game_scene_graph_emit", async () => {
      const payload = parseObjectJson(sceneGraphText, {});
      if (!payload.realm_id) {
        payload.realm_id = rendererRealmId;
      }
      return postAction("/v1/game/scene-graph/emit", payload, "game_scene_graph_emit");
    });
  }

  async function compileSceneFromCobra() {
    await runAction("scene_compile_from_cobra", async () => {
      const payload = {
        workspace_id: workspaceId,
        realm_id: rendererRealmId,
        scene_id: sceneCompileSceneId,
        name: sceneCompileName || "Scene",
        description: sceneCompileDescription || "",
        cobra_source: rendererCobra,
      };
      const data = await apiCall("/v1/game/scenes/compile", "POST", payload);
      const content = data && typeof data.content === "object" ? data.content : {};
      const graph = content.graph && typeof content.graph === "object" ? content.graph : content;
      setRendererGraphPreview(graph);
      setRendererVisualSource("engine");
      setRendererEngineStateText(
        JSON.stringify(
          {
            graph,
            realm_id: data.realm_id || rendererRealmId,
            scene_id: data.scene_id || sceneCompileSceneId,
          },
          null,
          2
        )
      );
      setSceneGraphText(JSON.stringify(graph, null, 2));
      setRendererLibrarySceneId(String(data.scene_id || sceneCompileSceneId));
      setRendererGameStatus(`scene_compiled:${String(data.scene_id || sceneCompileSceneId)}`);
      return data;
    });
  }

  async function loadSceneFromLibraryToRenderer() {
    await runAction("scene_load_from_library", async () => {
      const sceneId = String(rendererLibrarySceneId || "").trim();
      if (!sceneId) {
        throw new Error("scene_id_required");
      }
      const path = `/v1/game/scenes/${encodeURI(sceneId)}?workspace_id=${encodeURIComponent(workspaceId)}&realm_id=${encodeURIComponent(rendererRealmId)}`;
      const data = await apiCall(path, "GET", null);
      const content = data && typeof data.content === "object" ? data.content : {};
      const graph = content.graph && typeof content.graph === "object" ? content.graph : content;
      setRendererGraphPreview(graph);
      setRendererVisualSource("engine");
      setRendererEngineStateText(
        JSON.stringify(
          {
            graph,
            realm_id: data.realm_id || rendererRealmId,
            scene_id: data.scene_id || sceneId,
          },
          null,
          2
        )
      );
      setSceneGraphText(JSON.stringify(graph, null, 2));
      setRendererGameStatus(`scene_loaded:${String(data.scene_id || sceneId)}`);
      return data;
    });
  }

  async function validateContent() {
    await runAction("content_validate", async () => {
      const payload = {
        workspace_id: workspaceId,
        realm_id: rendererRealmId,
        scene_id: contentValidateSceneId,
        source: contentValidateSource,
        payload: contentValidatePayload,
        strict_bilingual: strictBilingualValidation,
      };
      const data = await apiCall("/v1/content/validate", "POST", payload);
      setContentValidateOutput(data);
      const surfaceText = contentValidateSource === "cobra"
        ? extractFirstShygazunSurfaceFromCobra(contentValidatePayload)
        : "";
      await inspectRendererBilingualSurface(surfaceText);
      setValidationSummary({
        ok: Boolean(data && data.ok),
        errors: Array.isArray(data && data.errors) ? data.errors.length : 0,
        warnings: Array.isArray(data && data.warnings) ? data.warnings.length : 0,
      });
      return data;
    });
  }

  function addDialogueTurn() {
    const trimmedLineId = String(dialogueLineId || "").trim();
    const trimmedSpeaker = String(dialogueSpeakerId || "").trim();
    const trimmedRaw = String(dialogueRaw || "").trim();
    if (!trimmedLineId || !trimmedSpeaker || !trimmedRaw) {
      setNotice("dialogue_add_turn: line_id, speaker_id, and raw are required");
      return;
    }
    const nextTurn = {
      line_id: trimmedLineId,
      speaker_id: trimmedSpeaker,
      raw: trimmedRaw,
      tags: {},
      metadata: {}
    };
    setDialogueTurns((prev) => [...prev, nextTurn]);
    const nextNumeric = Number.parseInt(trimmedLineId.replace(/\D+/g, ""), 10);
    if (!Number.isNaN(nextNumeric)) {
      setDialogueLineId(`l${nextNumeric + 1}`);
    }
    setDialogueRaw("");
  }

  function clearDialogueTurns() {
    setDialogueTurns([]);
    setDialogueEmitResult(null);
  }

  async function emitDialogueTurns() {
    await runAction("game_dialogue_emit", async () => {
      if (dialogueTurns.length === 0) {
        throw new Error("dialogue_emit: no turns added");
      }
      const payload = {
        workspace_id: workspaceId,
        scene_id: dialogueSceneId,
        dialogue_id: dialogueId,
        turns: dialogueTurns
      };
      const data = await apiCall("/v1/game/dialogue/emit", "POST", payload);
      setDialogueEmitResult(data);
      return data;
    });
  }

  async function exportGameSave() {
    await runAction("game_save_export", async () => {
      const data = await apiCall(`/v1/game/saves/export?workspace_id=${encodeURIComponent(workspaceId)}`, "GET", null);
      setSaveExport(data);
      return data;
    });
  }

  async function runGameRule(path, payloadText, actionName) {
    await runAction(actionName, async () => {
      const payload = parseObjectJson(payloadText, {});
      const data = await postAction(path, payload, actionName);
      setGameRulesOutput(data);
      return data;
    });
  }

  function buildRendererTablesPayload() {
    const actorId = rendererTablesActorId || "player";
    const level = normalizeRulePayload(parseObjectJson(levelRuleText, null), workspaceId, actorId);
    const skill = normalizeRulePayload(parseObjectJson(skillRuleText, null), workspaceId, actorId);
    const perk = normalizeRulePayload(parseObjectJson(perkRuleText, null), workspaceId, actorId);
    const alchemy = normalizeRulePayload(parseObjectJson(alchemyRuleText, null), workspaceId, actorId);
    const blacksmith = normalizeRulePayload(parseObjectJson(blacksmithRuleText, null), workspaceId, actorId);
    const marketQuote = normalizeRulePayload(parseObjectJson(marketQuoteText, null), workspaceId, actorId);
    const marketTrade = normalizeRulePayload(parseObjectJson(marketTradeText, null), workspaceId, actorId);
    const vitriolApply = normalizeRulePayload(parseObjectJson(vitriolApplyText, null), workspaceId, actorId);
    const vitriolCompute = normalizeRulePayload(parseObjectJson(vitriolComputeText, null), workspaceId, actorId);
    const vitriolClear = normalizeRulePayload(parseObjectJson(vitriolClearText, null), workspaceId, actorId);
    return {
      workspace_id: workspaceId,
      actor_id: actorId,
      level,
      skill,
      perk,
      alchemy,
      blacksmith,
      market_quote: marketQuote,
      market_trade: marketTrade,
      vitriol_apply: vitriolApply,
      vitriol_compute: vitriolCompute,
      vitriol_clear: vitriolClear,
    };
  }

  async function syncRendererTables() {
    setRendererTablesStatus("loading");
    const data = await runAction("renderer_tables_sync", async () => {
      const payload = buildRendererTablesPayload();
      const response = await apiCall("/v1/game/renderer/tables", "POST", payload);
      setRendererTables(response.tables || {});
      setRendererTablesMeta({ generated_at: response.generated_at || "", hash: response.hash || "" });
      return response;
    });
    if (!data) {
      setRendererTablesStatus("error");
      return;
    }
    setRendererTablesStatus("ready");
  }

  async function loadRendererStateTables() {
    const actorId = rendererTablesActorId || "player";
    setRendererTablesStatus("loading");
    const data = await runAction("renderer_state_load", async () => {
      const response = await apiCall(
        `/v1/game/state?workspace_id=${encodeURIComponent(workspaceId)}&actor_id=${encodeURIComponent(actorId)}`,
        "GET",
        null
      );
      setRendererTables(response.tables || {});
      setRendererTablesMeta({ generated_at: response.generated_at || "", hash: response.hash || "" });
      return response;
    });
    if (!data) {
      setRendererTablesStatus("error");
      return;
    }
    setRendererTablesStatus("ready");
  }

  async function commitRendererStateTables() {
    const actorId = rendererTablesActorId || "player";
    setRendererTablesStatus("loading");
    const data = await runAction("renderer_state_apply", async () => {
      const payload = {
        workspace_id: workspaceId,
        actor_id: actorId,
        tables: rendererMergedTables,
        mode: rendererStateCommitMode,
      };
      const response = await apiCall("/v1/game/state/apply", "POST", payload);
      setRendererTables(response.tables || {});
      setRendererTablesMeta({ generated_at: response.generated_at || "", hash: response.hash || "" });
      return response;
    });
    if (!data) {
      setRendererTablesStatus("error");
      return;
    }
    setRendererTablesStatus("ready");
  }

  async function runRendererTick() {
    setRendererTablesStatus("loading");
    const data = await runAction("renderer_state_tick", async () => {
      const payload = parseObjectJson(rendererTickText, {});
      const response = await apiCall("/v1/game/state/tick", "POST", payload);
      setRendererTickOutput(response);
      setRendererTables(response.tables || {});
      setRendererTablesMeta({ generated_at: new Date().toISOString(), hash: response.hash || "" });
      return response;
    });
    if (!data) {
      setRendererTablesStatus("error");
      return;
    }
    setRendererTablesStatus("ready");
  }

  async function loadAssetManifests() {
    setAssetManifestStatus("loading");
    const data = await runAction("asset_manifests_load", async () => {
      const response = await apiCall("/v1/assets/manifests", "GET", null);
      setAssetManifests(Array.isArray(response) ? response : []);
      return response;
    });
    if (!data) {
      setAssetManifestStatus("error");
      return;
    }
    setAssetManifestStatus("ready");
  }

  async function uploadAsset() {
    if (!assetUploadFile) {
      setNotice("Select a file first.");
      return;
    }
    setAssetUploadStatus("requesting");
    try {
      // 1. Request presigned upload URL
      const req = await apiCall("/v1/assets/upload-request", "POST", {
        name: assetUploadFile.name,
        kind: assetUploadKind,
        mime_type: assetUploadMime || assetUploadFile.type || "application/octet-stream",
        file_size_bytes: assetUploadFile.size,
      });
      if (!req.upload_url) {
        setNotice("R2 not configured — asset registered locally only.");
        setAssetUploadStatus("idle");
        void loadAssetManifests();
        return;
      }
      // 2. PUT directly to R2 presigned URL
      setAssetUploadStatus("uploading");
      const putRes = await fetch(req.upload_url, {
        method: "PUT",
        headers: { "Content-Type": assetUploadMime || assetUploadFile.type || "application/octet-stream" },
        body: assetUploadFile,
      });
      if (!putRes.ok) throw new Error(`R2 upload failed: ${putRes.status}`);
      // 3. Confirm upload
      setAssetUploadStatus("confirming");
      await apiCall(`/v1/assets/${req.id}/confirm`, "POST", null);
      setNotice(`Asset uploaded: ${assetUploadFile.name}`);
      setAssetUploadFile(null);
      setAssetUploadStatus("idle");
      void loadAssetManifests();
    } catch (err) {
      setNotice(`Upload failed: ${err.message}`);
      setAssetUploadStatus("error");
    }
  }

  async function downloadAsset(assetId) {
    try {
      const data = await apiCall(`/v1/assets/${assetId}/download-url`, "GET", null);
      if (data.url) window.open(data.url, "_blank");
    } catch (err) {
      setNotice(`Download failed: ${err.message}`);
    }
  }

  async function deleteAsset(assetId) {
    await runAction("asset_delete", async () => {
      await apiCall(`/v1/assets/${assetId}`, "DELETE", null);
      void loadAssetManifests();
      return { ok: true };
    });
  }

  async function loadMyGuildProfile() {
    try {
      const data = await apiCall("/v1/guild/profile/me", "GET", null);
      setGuildProfile(data);
      if (data) setGuildProfileEdit({ display_name: data.display_name || "", bio: data.bio || "", portfolio_url: data.portfolio_url || "", avatar_url: data.avatar_url || "", region: data.region || "", divisions: data.divisions || "", trades: data.trades || "", is_public: data.is_public ?? false, show_region: data.show_region ?? true, show_trades: data.show_trades ?? true, show_portfolio: data.show_portfolio ?? true });
    } catch (_) {}
  }

  async function saveGuildProfile() {
    setGuildProfileStatus("saving");
    try {
      const data = await apiCall("/v1/guild/profile", "POST", guildProfileEdit);
      setGuildProfile(data);
      setGuildProfileStatus("idle");
    } catch (e) {
      setGuildProfileStatus("error");
    }
  }

  async function loadGuildProfilesAdmin() {
    try {
      const data = await apiCall("/v1/guild/profiles", "GET", null);
      setGuildProfilesAdmin(Array.isArray(data) ? data : []);
    } catch (_) {}
  }

  async function approveGuildProfile(profileId) {
    try {
      await apiCall(`/v1/guild/profiles/${profileId}/approve`, "POST", {});
      void loadGuildProfilesAdmin();
    } catch (e) {
      setNotice(`approve_guild_profile: ${e}`);
    }
  }

  async function searchGuildDirectory() {
    try {
      const q = guildDirectoryQuery.trim();
      const url = `/public/guild/artisans${q ? `?trade=${encodeURIComponent(q)}` : ""}`;
      const data = await apiCall(url, "GET", null);
      setGuildDirectoryResults(data?.artisans ?? []);
    } catch (e) {
      setNotice(`guild_directory: ${e}`);
    }
  }

  async function loadKernelFields() {
    setKernelFieldStatus("loading");
    try {
      const data = await apiCall("/v1/kernel/fields", "GET", null);
      setKernelFields(Array.isArray(data) ? data : []);
      setKernelFieldStatus("idle");
    } catch (e) {
      setKernelFieldStatus("error");
    }
  }

  async function createKernelField() {
    setKernelFieldStatus("creating");
    try {
      const data = await apiCall("/v1/kernel/fields", "POST", { label: kernelFieldLabel });
      setKernelFieldLabel("");
      void loadKernelFields();
      setKernelFieldStatus("idle");
    } catch (e) {
      setKernelFieldStatus("error");
    }
  }

  async function observeKernelField(fieldId) {
    try {
      const data = await apiCall(`/v1/kernel/fields/${encodeURIComponent(fieldId)}/observe`, "GET", null);
      setKernelFieldObserve(data);
    } catch (e) {
      setKernelFieldObserve({ error: String(e) });
    }
  }

  function applyAssetManifest() {
    const selected = assetManifests.find((item) => item.id === assetManifestSelected);
    if (!selected) {
      setNotice("asset_manifest_apply: select a manifest");
      return;
    }
    const manifestRealm = selected.realm_id || (selected.payload && selected.payload.realm_id);
    if (validateBeforeEmit && typeof manifestRealm === "string" && manifestRealm && manifestRealm !== rendererRealmId) {
      setNotice(`asset_manifest_apply: realm mismatch (${manifestRealm} != ${rendererRealmId})`);
      return;
    }
    const payload = selected.payload && typeof selected.payload === "object" ? selected.payload : {};
    const pack = payload.pack && typeof payload.pack === "object" ? payload.pack : payload;
    if (Array.isArray(pack.materials)) {
      setVoxelMaterials(pack.materials);
    }
    if (Array.isArray(pack.layers)) {
      setVoxelLayers(pack.layers);
    }
    if (Array.isArray(pack.atlases)) {
      setVoxelAtlases(pack.atlases);
    }
    if (pack.settings && typeof pack.settings === "object") {
      setVoxelSettings((prev) => ({ ...prev, ...pack.settings }));
    }
    if (pack.engine && typeof pack.engine === "object") {
      setRendererEngineStateText(JSON.stringify(pack.engine, null, 2));
    }
    if (pack.source && typeof pack.source === "string") {
      setRendererVisualSource(pack.source);
    }
    if (typeof pack.cobra === "string") {
      setRendererCobra(pack.cobra);
    }
    if (typeof pack.js === "string") {
      setRendererJs(pack.js);
    }
    if (typeof pack.python === "string") {
      setRendererPython(pack.python);
    }
    if (pack.json && typeof pack.json === "object") {
      setRendererJson(JSON.stringify(pack.json, null, 2));
    } else if (Array.isArray(pack.voxels)) {
      setRendererJson(JSON.stringify({ voxels: pack.voxels }, null, 2));
    }
    setNotice(`asset_manifest_apply: ${selected.name || selected.manifest_id || selected.id}`);
  }

  async function validatePipelineIfNeeded() {
    if (!validateBeforeEmit) {
      return true;
    }
    const sceneId = contentValidateSceneId && contentValidateSceneId.includes("/")
      ? contentValidateSceneId
      : `${rendererRealmId}/renderer-lab`;
    let source = "cobra";
    let payload = rendererCobra;
    if (rendererVisualSource === "json") {
      source = "json";
      payload = rendererJson;
    } else if (rendererVisualSource === "engine") {
      source = "json";
      payload = rendererEngineStateText;
    } else if (rendererVisualSource === "javascript" || rendererVisualSource === "python") {
      source = "json";
      const raw = rendererVisualSource === "javascript" ? rendererJs : rendererPython;
      const parsed = parseRendererPayloadSync(rendererVisualSource, raw, rendererEffectiveEngineState);
      payload = JSON.stringify(parsed || {}, null, 2);
    }
    const validation = await apiCall("/v1/content/validate", "POST", {
      workspace_id: workspaceId,
      realm_id: rendererRealmId,
      scene_id: sceneId,
      source,
      payload,
      strict_bilingual: strictBilingualValidation,
    });
    setContentValidateOutput(validation);
    const surfaceText = source === "cobra" ? extractFirstShygazunSurfaceFromCobra(payload) : "";
    await inspectRendererBilingualSurface(surfaceText);
    setValidationSummary({
      ok: Boolean(validation && validation.ok),
      errors: Array.isArray(validation && validation.errors) ? validation.errors.length : 0,
      warnings: Array.isArray(validation && validation.warnings) ? validation.warnings.length : 0,
    });
    if (!validation.ok) {
      setNotice("pipeline_validate: failed");
      return false;
    }
    return true;
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
            color: spriteColor,
          },
        },
        context: { workspace_id: workspaceId, realm_id: rendererRealmId },
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
              color: spriteColor,
            },
            auto: {
              index: i,
              count,
              columns,
            },
          },
          context: { workspace_id: workspaceId, realm_id: rendererRealmId },
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

  function upsertVoxelAtlas(nextAtlas) {
    if (!nextAtlas || typeof nextAtlas !== "object" || typeof nextAtlas.id !== "string" || !nextAtlas.id.trim()) {
      return;
    }
    const atlasId = nextAtlas.id.trim();
    setVoxelAtlases((prev) => {
      const list = Array.isArray(prev) ? prev.slice() : [];
      const idx = list.findIndex((atlas) => atlas && String(atlas.id || "").trim() === atlasId);
      if (idx >= 0) {
        list[idx] = { ...list[idx], ...nextAtlas, id: atlasId };
      } else {
        list.push({ ...nextAtlas, id: atlasId });
      }
      return list;
    });
  }

  async function buildTilePngFromSvg() {
    const scale = clampInt(tileSvgExportScale, 1, 8, 2);
    const svg = buildTileSvgMarkup(tileSvgModel, tileSvgShowGrid, tileSvgShowLinks, scale);
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    try {
      const img = await new Promise((resolve, reject) => {
        const el = new Image();
        el.onload = () => resolve(el);
        el.onerror = () => reject(new Error("tile_png: svg rasterization failed"));
        el.src = url;
      });
      const width = Math.max(1, tileSvgModel.width * scale);
      const height = Math.max(1, tileSvgModel.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        throw new Error("tile_png: canvas context unavailable");
      }
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(img, 0, 0, width, height);
      const pngDataUrl = canvas.toDataURL("image/png");
      return { pngDataUrl, width, height, scale };
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function downloadTilePng() {
    setTilePngStatus("building");
    try {
      const built = await buildTilePngFromSvg();
      setTilePngDataUrl(built.pngDataUrl);
      const link = document.createElement("a");
      link.href = built.pngDataUrl;
      link.download = `tilemap-${workspaceId}-${built.width}x${built.height}.png`;
      link.click();
      setTilePngStatus(`ready:${built.width}x${built.height}`);
      setNotice(`tile_png_exported:${built.width}x${built.height}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "tile_png: unknown error";
      setTilePngStatus(msg);
      setNotice(msg);
    }
  }

  async function consumeTilePngAsAtlas() {
    setTilePngStatus("building");
    try {
      const built = await buildTilePngFromSvg();
      setTilePngDataUrl(built.pngDataUrl);
      const atlasId = (spriteAnimatorAtlasId || voxelAtlasDraft.id || "tile_network").trim() || "tile_network";
      const tileSize = clampInt(tileCellPx, 8, 256, 24);
      const scale = Math.max(1, built.scale);
      const cols = clampInt(tileCols, 1, 256, 48);
      const rows = clampInt(tileRows, 1, 256, 27);
      const atlas = {
        id: atlasId,
        src: built.pngDataUrl,
        tileSize: tileSize * scale,
        cols,
        rows,
        padding: 0,
      };
      setVoxelAtlasDraft(atlas);
      upsertVoxelAtlas(atlas);
      setSpriteAnimatorAtlasId(atlasId);
      setTilePngStatus(`atlas_ready:${atlasId}`);
      setNotice(`tile_png_atlas_ready:${atlasId}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "tile_png_atlas: unknown error";
      setTilePngStatus(msg);
      setNotice(msg);
    }
  }

  function buildDirectionalFrameSchema() {
    const frameW = clampInt(spriteAnimatorFrameW, 1, 2048, 48);
    const frameH = clampInt(spriteAnimatorFrameH, 1, 2048, 72);
    const startCol = clampInt(spriteAnimatorStartCol, 0, 2048, 0);
    const idleRowStart = clampInt(spriteAnimatorIdleRowStart, 0, 2048, 0);
    const walkRowStart = clampInt(spriteAnimatorWalkRowStart, 0, 2048, 4);
    const idleFrames = clampInt(spriteAnimatorIdleFrames, 1, 32, 1);
    const walkFrames = clampInt(spriteAnimatorWalkFrames, 1, 32, 4);
    const dirs = ["south", "west", "east", "north"];
    const spriteFrames = {};
    const spriteAnimations = { idle: {}, walk: {} };
    dirs.forEach((dir, dirIdx) => {
      const idleRow = idleRowStart + dirIdx;
      const walkRow = walkRowStart + dirIdx;
      spriteFrames[dir] = {
        x: startCol * frameW,
        y: idleRow * frameH,
        w: frameW,
        h: frameH,
      };
      spriteAnimations.idle[dir] = Array.from({ length: idleFrames }, (_, frameIdx) => ({
        x: (startCol + frameIdx) * frameW,
        y: idleRow * frameH,
        w: frameW,
        h: frameH,
      }));
      spriteAnimations.walk[dir] = Array.from({ length: walkFrames }, (_, frameIdx) => ({
        x: (startCol + frameIdx) * frameW,
        y: walkRow * frameH,
        w: frameW,
        h: frameH,
      }));
    });
    return { frameW, frameH, spriteFrames, spriteAnimations };
  }

  function applySpriteAnimatorToRendererJson() {
    const atlasId = String(spriteAnimatorAtlasId || "").trim();
    if (!atlasId) {
      setNotice("sprite_animator: atlas id required");
      return;
    }
    let payload = {};
    try {
      payload = JSON.parse(rendererJson || "{}");
    } catch {
      setNotice("sprite_animator: renderer JSON invalid");
      return;
    }
    const voxels = Array.isArray(payload.voxels)
      ? payload.voxels
      : Array.isArray(payload?.scene?.voxels)
      ? payload.scene.voxels
      : null;
    if (!voxels) {
      setNotice("sprite_animator: expected payload.voxels or payload.scene.voxels");
      return;
    }
    const target = String(spriteAnimatorTargetId || "").trim();
    if (!target) {
      setNotice("sprite_animator: target entity id required");
      return;
    }
    const { frameW, frameH, spriteFrames, spriteAnimations } = buildDirectionalFrameSchema();
    let matched = 0;
    const patched = voxels.map((entry) => {
      const item = entry && typeof entry === "object" ? entry : {};
      const itemId = String(item.id || item.entity_id || item.entityId || "");
      if (itemId !== target) {
        return entry;
      }
      matched += 1;
      const meta = item.meta && typeof item.meta === "object" ? item.meta : {};
      const nextMeta = {
        ...meta,
        sprite2d: true,
        render_mode: "sprite2d",
        sprite_w: Number(meta.sprite_w || meta.spriteWidth || Math.max(0.6, frameW / 40)),
        sprite_h: Number(meta.sprite_h || meta.spriteHeight || Math.max(0.9, frameH / 36)),
        sprite_frames: spriteFrames,
        sprite_animations: spriteAnimations,
        sprite_anim_ms: Number(meta.sprite_anim_ms || meta.spriteAnimMs || 120),
      };
      return {
        ...item,
        texture: `atlas:${atlasId}:0,0`,
        meta: nextMeta,
      };
    });
    if (!matched) {
      setNotice(`sprite_animator: target_not_found:${target}`);
      return;
    }
    if (Array.isArray(payload.voxels)) {
      payload = { ...payload, voxels: patched };
    } else {
      payload = { ...payload, scene: { ...(payload.scene || {}), voxels: patched } };
    }
    setRendererJson(JSON.stringify(payload, null, 2));
    setRendererPlayerId(target);
    setNotice(`sprite_animator_applied:${target}:${matched}`);
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
      return;
    }
    if (preset === "4K") {
      setTileCols("240");
      setTileRows("135");
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

  async function runTileProcInWorker({ seed, cols, rows, layer, code, timeoutMs = 2500 }) {
    if (typeof Worker === "undefined") {
      throw new Error("worker_unavailable");
    }
    const worker = new Worker(new URL("./labComputeWorker.js", import.meta.url), { type: "module" });
    try {
      const out = await new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => reject(new Error("worker_timeout")), Math.max(250, Number(timeoutMs || 2500)));
        worker.onmessage = (event) => {
          window.clearTimeout(timer);
          const data = event && event.data && typeof event.data === "object" ? event.data : {};
          if (data.type !== "tile_proc_result") {
            reject(new Error("worker_protocol_error"));
            return;
          }
          if (!data.ok) {
            reject(new Error(typeof data.error === "string" && data.error ? data.error : "worker_failed"));
            return;
          }
          resolve(data.result);
        };
        worker.onerror = (error) => {
          window.clearTimeout(timer);
          reject(new Error(error && error.message ? String(error.message) : "worker_error"));
        };
        worker.postMessage({
          type: "run_tile_proc",
          payload: { seed, cols, rows, layer, code },
        });
      });
      return out;
    } finally {
      worker.terminate();
    }
  }

  async function runPayloadParseInWorker({ mode, sourceText, timeoutMs = 2200 }) {
    if (typeof Worker === "undefined") {
      throw new Error("worker_unavailable");
    }
    const worker = new Worker(new URL("./labComputeWorker.js", import.meta.url), { type: "module" });
    try {
      const out = await new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => reject(new Error("worker_timeout")), Math.max(250, Number(timeoutMs || 2200)));
        worker.onmessage = (event) => {
          window.clearTimeout(timer);
          const data = event && event.data && typeof event.data === "object" ? event.data : {};
          if (data.type !== "payload_parse_result") {
            reject(new Error("worker_protocol_error"));
            return;
          }
          if (!data.ok) {
            reject(new Error(typeof data.error === "string" && data.error ? data.error : "worker_failed"));
            return;
          }
          resolve(data.result && typeof data.result === "object" ? data.result : {});
        };
        worker.onerror = (error) => {
          window.clearTimeout(timer);
          reject(new Error(error && error.message ? String(error.message) : "worker_error"));
        };
        worker.postMessage({
          type: "run_payload_parse",
          payload: { mode, sourceText },
        });
      });
      return out;
    } finally {
      worker.terminate();
    }
  }

  async function runVoxelExtractLodInWorker({ payload, settings, timeoutMs = 2200 }) {
    if (typeof Worker === "undefined") {
      throw new Error("worker_unavailable");
    }
    const worker = new Worker(new URL("./labComputeWorker.js", import.meta.url), { type: "module" });
    try {
      const out = await new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => reject(new Error("worker_timeout")), Math.max(250, Number(timeoutMs || 2200)));
        worker.onmessage = (event) => {
          window.clearTimeout(timer);
          const data = event && event.data && typeof event.data === "object" ? event.data : {};
          if (data.type !== "voxel_extract_lod_result") {
            reject(new Error("worker_protocol_error"));
            return;
          }
          if (!data.ok) {
            reject(new Error(typeof data.error === "string" && data.error ? data.error : "worker_failed"));
            return;
          }
          resolve(Array.isArray(data.result) ? data.result : []);
        };
        worker.onerror = (error) => {
          window.clearTimeout(timer);
          reject(new Error(error && error.message ? String(error.message) : "worker_error"));
        };
        worker.postMessage({
          type: "run_voxel_extract_lod",
          payload: { payload, settings },
        });
      });
      return out;
    } finally {
      worker.terminate();
    }
  }

function parseRendererPayloadSync(mode, sourceText, engineState = {}) {
  if (mode === "cobra") {
    return parseCobraShygazunScript(sourceText);
  }
  if (mode === "json") {
    try {
      const parsed = JSON.parse(sourceText || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }
  if (mode === "javascript") {
    try {
      const fn = new Function(
        "engine",
        `${String(sourceText || "")}\n; return (typeof render === 'function' ? render(engine) : null);`
      );
      const result = fn(engineState || {});
      if (result && typeof result === "object") {
        return result;
      }
      if (typeof result === "string") {
        try {
          const parsed = JSON.parse(result);
          return parsed && typeof parsed === "object" ? parsed : {};
        } catch {
          return {};
        }
      }
      return {};
    } catch {
      return {};
    }
  }
  if (mode === "python") {
    const lines = String(sourceText || "").split(/\r?\n/);
    for (const rawLine of lines) {
      const trimmed = rawLine.trim();
      if (!trimmed.startsWith("#")) {
        continue;
      }
      if (trimmed.startsWith("#payload ") || trimmed.startsWith("#json ") || trimmed.startsWith("#render ")) {
        const jsonText = trimmed.replace(/^#(payload|json|render)\s+/, "");
        try {
          const parsed = JSON.parse(jsonText);
          return parsed && typeof parsed === "object" ? parsed : parsed;
        } catch {
          return {};
        }
      }
    }
    return {};
  }
  return {};
}

function extractPythonFileHint(sourceText) {
  const raw = String(sourceText || "");
  if (!raw) {
    return null;
  }
  const matches = [];
  const regex = /["']([^"']+\.(?:scene\.json|json))["']/g;
  let match = regex.exec(raw);
  while (match) {
    const candidate = String(match[1] || "").trim();
    if (candidate) {
      matches.push(candidate);
    }
    match = regex.exec(raw);
  }
  if (matches.length === 0) {
    return null;
  }
  const scenePick = matches.find((item) => item.includes("productions/") || item.includes("scenes/"));
  if (scenePick) {
    return scenePick;
  }
  const sceneJsonPick = matches.find((item) => item.endsWith(".scene.json"));
  if (sceneJsonPick) {
    return sceneJsonPick;
  }
  return matches[0];
}

function extractPythonSavedPath(outputText) {
  const raw = String(outputText || "");
  if (!raw) {
    return null;
  }
  const lines = raw.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const match = trimmed.match(/Saved to\s+(.+)$/i);
    if (match && match[1]) {
      return match[1].trim();
    }
  }
  return null;
}

  function commitProceduralOutput(out, cols, rows) {
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
      const rawMeta = item.meta && typeof item.meta === "object" ? item.meta : {};
      const traversalClass = normalizeTileTraversalClass(
        rawMeta.traversal_class || (rawMeta.walkable === true ? "walkable_surface" : rawMeta.walkable === false ? "visual_unwalkable" : "non_traversal"),
        "non_traversal"
      );
      const meta = tileTraversalMeta(rawMeta, traversalClass);
      const key = tileKey(x, y, layer);
      nextPlacements[key] = {
        id: `tile_${layer}_${x}_${y}`,
        x,
        y,
        layer,
        presence_token: "Ta",
        color_token: color,
        opacity_token: opacity,
        meta,
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
  }

  function normalizeTileTraversalClass(value, fallback = "walkable_surface") {
    if (value === "walkable_surface" || value === "visual_unwalkable" || value === "non_traversal") {
      return value;
    }
    return fallback;
  }

  function tileTraversalMeta(meta, traversalClass = tileTraversalClass) {
    const nextMeta = meta && typeof meta === "object" ? { ...meta } : {};
    const normalized = normalizeTileTraversalClass(traversalClass);
    nextMeta.traversal_class = normalized;
    if (normalized === "walkable_surface") {
      nextMeta.walkable = true;
    } else if (normalized === "visual_unwalkable") {
      nextMeta.walkable = false;
    } else {
      delete nextMeta.walkable;
    }
    return nextMeta;
  }

  function tileTraversalLabel(traversalClass) {
    switch (normalizeTileTraversalClass(traversalClass)) {
      case "walkable_surface":
        return "walkable";
      case "visual_unwalkable":
        return "visual-only solid";
      default:
        return "not applicable";
    }
  }

  function tilePlacementToRendererVoxelEntity(placement) {
    const item = placement && typeof placement === "object" ? placement : {};
    const meta = item.meta && typeof item.meta === "object" ? item.meta : {};
    const traversalClass = normalizeTileTraversalClass(
      meta.traversal_class || (meta.walkable === true ? "walkable_surface" : meta.walkable === false ? "visual_unwalkable" : "non_traversal"),
      "non_traversal"
    );
    const layer = String(item.layer || "base");
    const colorToken = String(item.color_token || "Ru");
    const opacityToken = String(item.opacity_token || "Na");
    const type =
      traversalClass === "walkable_surface"
        ? "tile_floor"
        : traversalClass === "visual_unwalkable"
          ? "tile_blocker"
          : "tile_visual";
    const material =
      traversalClass === "walkable_surface"
        ? "ground"
        : traversalClass === "visual_unwalkable"
          ? "wall"
          : "detail";
    return {
      ...item,
      kind: "tile_voxel",
      type,
      material,
      color: tokenColor(colorToken),
      z: Number.isFinite(Number(item.z))
        ? Number(item.z)
        : layer === "ground"
          ? 0
          : layer === "base"
            ? 1
            : layer === "detail"
              ? 2
              : layer === "fx"
                ? 3
                : 1,
      meta: {
        ...meta,
        layer,
        material,
        traversal_class: traversalClass,
        walkable: traversalClass === "walkable_surface" ? true : traversalClass === "visual_unwalkable" ? false : undefined,
        tile_surface: true,
        color_token: colorToken,
        opacity_token: opacityToken,
        presence_token: String(item.presence_token || "Ta"),
      },
    };
  }

  async function applyProceduralTiles() {
    const seed = clampInt(tileProcSeed, 0, 999999, 42);
    const cols = clampInt(tileCols, 1, 256, 48);
    const rows = clampInt(tileRows, 1, 256, 27);
    try {
      setTileProcStatus("generating:worker");
      let out = null;
      try {
        out = await runTileProcInWorker({
          seed,
          cols,
          rows,
          layer: tileActiveLayer,
          code: tileProcCode,
          timeoutMs: 2800,
        });
      } catch {
        const fn = new Function(
          "seed",
          "cols",
          "rows",
          "layer",
          "\"use strict\";\n" + tileProcCode
        );
        out = fn(seed, cols, rows, tileActiveLayer);
        setTileProcStatus("generated:fallback_main_thread");
      }
      commitProceduralOutput(out, cols, rows);
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

  function extractFirstShygazunSurfaceFromCobra(source) {
    const lines = String(source || "").split(/\r?\n/);
    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        continue;
      }
      const match = line.match(/^(lex|akinenwun|shygazun)\s+(.+)$/i);
      if (match) {
        return String(match[2] || "").trim();
      }
    }
    return "";
  }

  function parseLessonDraftPayload() {
    const text = String(lessonBody || "").trim();
    if (!text) {
      throw new Error("lesson_body_required");
    }
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("lesson_json_object_required");
    }
    return parsed;
  }

  async function validateLessonDraft() {
    await runAction("lesson_validate", async () => {
      const lessonPayload = parseLessonDraftPayload();
      const data = await kernelCall("/v0.1/shygazun/teach/validate", "POST", { lessons: [lessonPayload] });
      setLessonValidationOutput(data);
      return data;
    });
  }

  async function inspectRendererBilingualSurface(sourceTextOverride) {
    const sourceText = String(sourceTextOverride || "").trim();
    if (!sourceText) {
      setRendererBilingualOutput(null);
      return null;
    }
    const data = await kernelCall("/v0.1/shygazun/cobra_surface", "POST", { source_text: sourceText });
    setRendererBilingualOutput(data);
    return data;
  }

  async function createLessonDraft() {
    await runAction("lessons_create", async () => {
      const lessonText = String(lessonBody || "").trim();
      if (lessonText.startsWith("{")) {
        const lessonPayload = parseLessonDraftPayload();
        const validation = await kernelCall("/v0.1/shygazun/teach/validate", "POST", { lessons: [lessonPayload] });
        setLessonValidationOutput(validation);
      }
      await apiCall("/v1/lessons", "POST", { workspace_id: workspaceId, title: lessonTitle, body: lessonBody, status: "draft" });
      setLessonTitle("");
      setLessonBody("");
      await listLessons();
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
      if (typeof data.profile_name === "string" && data.profile_name.trim()) {
        setProfileName(data.profile_name);
      }
      if (typeof data.profile_email === "string" && data.profile_email.trim()) {
        setProfileEmail(data.profile_email);
      }
      setArtisanAccessVerified(Boolean(data.artisan_access_verified));
      return data;
    });
  }

  async function issueArtisanAccessCode() {
    await runAction("artisan_access_issue", async () => {
      const data = await apiCall("/v1/access/artisan-id/issue", "POST", buildProfilePayload(profileName, profileEmail, profileTimezone));
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
        ...buildProfilePayload(profileName, profileEmail, profileTimezone),
        artisan_code: artisanAccessInput
      });
      if (typeof data.profile_name === "string" && data.profile_name.trim()) {
        setProfileName(data.profile_name);
      }
      if (typeof data.profile_email === "string" && data.profile_email.trim()) {
        setProfileEmail(data.profile_email);
      }
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

  async function listStudioAudioFiles(rootDir) {
    const suffixes = [".mp3", ".wav", ".ogg", ".flac", ".m4a"];
    const grouped = await Promise.all(
      suffixes.map((suffix) => window.atelierDesktop.fs.listAssetsBySuffix(rootDir, suffix))
    );
    const merged = grouped.flatMap((result) =>
      result && result.ok && Array.isArray(result.files) ? result.files : []
    );
    return Array.from(new Set(merged)).sort((a, b) => String(a).localeCompare(String(b)));
  }

  async function listStudioRuntimePlanFiles(rootDir) {
    if (!window.atelierDesktop || !window.atelierDesktop.fs || typeof window.atelierDesktop.fs.listRuntimePlans !== "function") {
      return [];
    }
    const result = await window.atelierDesktop.fs.listRuntimePlans(rootDir);
    if (!result || !result.ok || !Array.isArray(result.files)) {
      return [];
    }
    return result.files.map((item) => String(item)).filter((item) => item.trim() !== "");
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
      const nextRoot = result.directory;
      setStudioFsRoot(nextRoot);
      const scripts = await window.atelierDesktop.fs.listCobraScripts(nextRoot);
      if (scripts && scripts.ok && Array.isArray(scripts.files)) {
        setStudioFsScripts(scripts.files);
        setStudioFsSelectedScript(scripts.files.length > 0 ? String(scripts.files[0]) : "");
      }
      const pythonFiles = await window.atelierDesktop.fs.listAssetsBySuffix(nextRoot, ".py");
      if (pythonFiles && pythonFiles.ok && Array.isArray(pythonFiles.files)) {
        setStudioFsPythonFiles(pythonFiles.files);
        setStudioFsSelectedPython(pythonFiles.files.length > 0 ? String(pythonFiles.files[0]) : "");
      }
      const scenes = await window.atelierDesktop.fs.listAssetsBySuffix(nextRoot, ".scene.json");
      if (scenes && scenes.ok && Array.isArray(scenes.files)) {
        setStudioFsSceneFiles(scenes.files);
        setStudioFsSelectedScene(scenes.files.length > 0 ? String(scenes.files[0]) : "");
      }
      const sprites = await window.atelierDesktop.fs.listAssetsBySuffix(nextRoot, ".sprite.json");
      if (sprites && sprites.ok && Array.isArray(sprites.files)) {
        setStudioFsSpriteFiles(sprites.files);
        setStudioFsSelectedSprite(sprites.files.length > 0 ? String(sprites.files[0]) : "");
      }
      const audioFiles = await listStudioAudioFiles(nextRoot);
      const runtimePlans = await listStudioRuntimePlanFiles(nextRoot);
      setStudioFsAudioFiles(audioFiles);
      setStudioFsSelectedAudio(audioFiles.length > 0 ? String(audioFiles[0]) : "");
      setStudioFsRuntimePlanFiles(runtimePlans);
      if (runtimePlans.length > 0 && !runtimePlans.includes(String(studioFsRuntimePlanPath || ""))) {
        setStudioFsRuntimePlanPath(String(runtimePlans[0]));
      }
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
      const pythonFiles = await window.atelierDesktop.fs.listAssetsBySuffix(studioFsRoot, ".py");
      if (pythonFiles && pythonFiles.ok && Array.isArray(pythonFiles.files)) {
        setStudioFsPythonFiles(pythonFiles.files);
        if (pythonFiles.files.length > 0) {
          setStudioFsSelectedPython(String(pythonFiles.files[0]));
        }
      }
      const runtimePlans = await listStudioRuntimePlanFiles(studioFsRoot);
      setStudioFsRuntimePlanFiles(runtimePlans);
      if (runtimePlans.length > 0 && !runtimePlans.includes(String(studioFsRuntimePlanPath || ""))) {
        setStudioFsRuntimePlanPath(String(runtimePlans[0]));
      }
      return {
        cobra: result,
        python_files: pythonFiles && pythonFiles.ok && Array.isArray(pythonFiles.files) ? pythonFiles.files.length : 0,
        runtime_plan_files: runtimePlans.length,
      };
    });
  }

  async function runRuntimePlanFromFs() {
    await runAction("studio_runtime_plan_run", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const planPath = String(studioFsRuntimePlanPath || "").trim();
      if (!planPath) {
        throw new Error("runtime_plan_path_required");
      }
      const readResult = await window.atelierDesktop.fs.readTextFile(studioFsRoot, planPath);
      if (!readResult || !readResult.ok || typeof readResult.content !== "string") {
        throw new Error("runtime_plan_read_failed");
      }
      const parsed = parseObjectJson(readResult.content, null);
      if (!parsed || typeof parsed !== "object") {
        throw new Error("runtime_plan_invalid_json");
      }
      const actions = Array.isArray(parsed.actions) ? parsed.actions : [];
      const payload = {
        ...parsed,
        workspace_id: workspaceId,
        actor_id: runtimeRegionActorId,
        actions,
        plan_id: String(parsed.plan_id || `studio_fs_runtime_plan_${Date.now()}`),
      };
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", payload);
      const results = Array.isArray(consumed?.results) ? consumed.results : [];
      const failed = results.filter((item) => !item || !item.ok).length;
      setModuleRunOutput({
        runtime_plan_from_fs: {
          path: planPath,
          consumed,
        },
      });
      setRendererGameStatus(failed > 0 ? `runtime_plan_failed:${failed}/${results.length}` : `runtime_plan_ok:${results.length}`);
      return {
        path: planPath,
        results: results.length,
        failed,
        hash: consumed && consumed.hash ? consumed.hash : "",
      };
    });
  }

  async function runDungeonSweepFromApi() {
    await runAction("dungeon_sweep", async () => {
      const sulphera = ["pride", "greed", "envy", "gluttony", "sloth", "wrath", "lust"].map((ring) => `sulphera/${ring}`);
      const mercurie = [
        "mercurie/zone_tideglass",
        "mercurie/zone_cindergrove",
        "mercurie/zone_rootbloom",
        "mercurie/zone_thornveil",
        "mercurie/zone_dewspire",
      ];
      const lapidus = ["lapidus/lapidus_mines_mt_hieronymus"];
      const dungeonIds = [...sulphera, ...mercurie, ...lapidus];
      const profiles = [
        { id: "p01", player_level: 1, quest_progress: 0 },
        { id: "p02", player_level: 6, quest_progress: 14 },
        { id: "p03", player_level: 12, quest_progress: 40 },
      ];
      const actions = [];
      dungeonIds.forEach((dungeonId) => {
        profiles.forEach((profile) => {
          actions.push({
            action_id: `sweep_${profile.id}_${dungeonId.replaceAll("/", "_")}`,
            kind: "dungeon.generate",
            payload: {
              dungeon_id: dungeonId,
              player_level: profile.player_level,
              quest_progress: profile.quest_progress,
              entry_ordinal: 1,
            },
          });
        });
      });
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: runtimeRegionActorId,
        plan_id: `dungeon_sweep_${Date.now()}`,
        actions,
      });
      const results = Array.isArray(consumed?.results) ? consumed.results : [];
      const failures = results.filter((item) => !item || !item.ok);
      const rows = results
        .filter((item) => item && item.ok && item.result && typeof item.result === "object")
        .map((item) => item.result);
      const realmAgg = {
        sulphera: { runs: 0, difficulty_sum: 0, hostile_count: 0, shard_sum: 0, enemy_sum: 0 },
        mercurie: { runs: 0, difficulty_sum: 0, hostile_count: 0, shard_sum: 0, enemy_sum: 0 },
        lapidus: { runs: 0, difficulty_sum: 0, hostile_count: 0, shard_sum: 0, enemy_sum: 0 },
      };
      const invariantErrors = [];
      rows.forEach((row) => {
        const realmId = String(row.realm_id || "");
        if (!realmAgg[realmId]) {
          return;
        }
        const hostile = Boolean(row.hostile);
        const shards = Array.isArray(row.cypher_shards) ? row.cypher_shards.length : 0;
        const population = row.population && typeof row.population === "object" ? row.population : {};
        const hostileEntities = Array.isArray(population.hostile_entities) ? population.hostile_entities : [];
        realmAgg[realmId].runs += 1;
        realmAgg[realmId].difficulty_sum += Number(row.difficulty_tier || 0);
        realmAgg[realmId].hostile_count += hostile ? 1 : 0;
        realmAgg[realmId].shard_sum += shards;
        realmAgg[realmId].enemy_sum += hostileEntities.length;
        if (realmId === "sulphera") {
          if (Number(row.time_scale_to_lapidus || 0) !== 24) invariantErrors.push(`sulphera_time_scale:${row.dungeon_id}`);
          if (!hostile) invariantErrors.push(`sulphera_hostile:${row.dungeon_id}`);
        }
        if (realmId === "mercurie") {
          if (Number(row.time_scale_to_lapidus || 0) !== 3) invariantErrors.push(`mercurie_time_scale:${row.dungeon_id}`);
          if (!hostile) invariantErrors.push(`mercurie_hostile:${row.dungeon_id}`);
        }
        if (realmId === "lapidus") {
          const neutral = Array.isArray(population.neutral_entities) ? population.neutral_entities.map((v) => String(v)) : [];
          if (Number(row.time_scale_to_lapidus || 0) !== 1) invariantErrors.push(`lapidus_time_scale:${row.dungeon_id}`);
          if (hostile) invariantErrors.push(`lapidus_non_hostile:${row.dungeon_id}`);
          if (!neutral.includes("gnome_miners")) invariantErrors.push(`lapidus_missing_gnomes:${row.dungeon_id}`);
          if (!neutral.includes("child_laborers")) invariantErrors.push(`lapidus_missing_children:${row.dungeon_id}`);
        }
      });
      const summary = {};
      Object.entries(realmAgg).forEach(([realmId, agg]) => {
        const runs = Number(agg.runs || 0);
        summary[realmId] = {
          runs,
          avg_difficulty: runs > 0 ? Number((agg.difficulty_sum / runs).toFixed(2)) : 0,
          avg_shards: runs > 0 ? Number((agg.shard_sum / runs).toFixed(2)) : 0,
          avg_hostile_entities: runs > 0 ? Number((agg.enemy_sum / runs).toFixed(2)) : 0,
          hostile_rate: runs > 0 ? Number((agg.hostile_count / runs).toFixed(2)) : 0,
        };
      });
      const expectedRuns = dungeonIds.length * profiles.length;
      const ok = failures.length === 0 && invariantErrors.length === 0 && rows.length === expectedRuns;
      const report = {
        ok,
        expected_runs: expectedRuns,
        actual_runs: rows.length,
        failure_count: failures.length,
        invariant_error_count: invariantErrors.length,
        invariant_errors: invariantErrors,
        summary,
        hash: consumed && consumed.hash ? consumed.hash : "",
      };
      setModuleRunOutput({
        dungeon_sweep: report,
        dungeon_sweep_consume: consumed,
      });
      setRendererGameStatus(ok ? `dungeon_sweep_ok:${rows.length}` : `dungeon_sweep_fail:${failures.length}:${invariantErrors.length}`);
      return report;
    });
  }

  function generateDaisyBodyplan() {
    const parsedSymbols = parseDaisySymbolSequence(daisySymbolSequence);
    const symbols = daisyUseWholeTongue ? DAISY_TONGUE_SYMBOLS : parsedSymbols;
    if (!daisyUseWholeTongue && symbols.length === 0) {
      setNotice("daisy_bodyplan_generate: no valid daisy symbols selected");
      return;
    }
    const spec = buildDaisyBodyplanSpec({
      system_id: daisySystemId,
      archetype: daisyArchetype,
      symmetry: daisySymmetry,
      segment_count: toInt(daisySegmentCount, 7),
      limb_pairs: toInt(daisyLimbPairs, 2),
      core_token: daisyCoreToken,
      accent_token: daisyAccentToken,
      core_belonging_chain: daisyCoreBelongingChain,
      accent_belonging_chain: daisyAccentBelongingChain,
      seed: toInt(daisySeed, 42),
      use_whole_tongue: daisyUseWholeTongue,
      daisy_symbols: symbols,
      role_overrides: daisyRoleInspector.overrides,
    });
    setDaisyBodyplanText(JSON.stringify(spec, null, 2));
    setNotice(`daisy_bodyplan_generated:${spec.system_id}:${spec.daisy_tongue.coverage.used}/${spec.daisy_tongue.coverage.total}`);
  }

  function projectDaisyBodyplanToRenderer() {
    try {
      const parsed = JSON.parse(daisyBodyplanText || "{}");
      const voxels = daisyBodyplanToVoxels(parsed);
      setRendererJson(JSON.stringify({ voxels }, null, 2));
      setRendererVisualSource("json");
      setRendererGameStatus(`daisy_projected:${voxels.length}_voxels`);
      setNotice(`daisy_projected:${voxels.length}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setNotice(`daisy_project_error:${msg}`);
    }
  }

  function createRendererSandboxDraftFromCurrent() {
    const pack = createRenderPack({
      name: rendererSandboxPackName,
      notes: rendererSandboxPackNotes,
      workspaceId,
      source: "studio_hub_sandbox",
      rendererJsonText: rendererJson,
      voxelSettings,
    });
    const validation = validateRenderPack(pack);
    setRendererSandboxDraftText(JSON.stringify(pack, null, 2));
    setRendererSandboxValidation(validation);
    setRendererSandboxStatus(validation.ok ? `draft_ready:${pack.stats.voxel_count}` : "draft_invalid");
    setNotice(validation.ok ? `sandbox_draft_ready:${pack.pack_id}` : "sandbox_draft_invalid");
  }

  function publishRendererSandboxDraft() {
    const parsed = parseObjectJson(rendererSandboxDraftText, null);
    if (!parsed || typeof parsed !== "object") {
      setRendererSandboxStatus("publish_failed:invalid_json");
      setNotice("sandbox_publish_failed: invalid JSON draft");
      return;
    }
    const validation = validateRenderPack(parsed);
    setRendererSandboxValidation(validation);
    if (!validation.ok) {
      setRendererSandboxStatus("publish_failed:validation");
      setNotice(`sandbox_publish_failed:${validation.errors.join("|")}`);
      return;
    }
    setRendererSandboxPacks((prev) => {
      const deduped = prev.filter((item) => item && item.pack_id !== parsed.pack_id);
      return [parsed, ...deduped].slice(0, 80);
    });
    setRendererSandboxSelectedId(String(parsed.pack_id));
    setRendererSandboxStatus(`published:${parsed.pack_id}`);
    setNotice(`sandbox_published:${parsed.pack_id}`);
  }

  function applyRendererSandboxSelectedPack() {
    if (!rendererSandboxSelectedPack) {
      setNotice("sandbox_apply_failed: no selected pack");
      return;
    }
    const validation = validateRenderPack(rendererSandboxSelectedPack);
    setRendererSandboxValidation(validation);
    if (!validation.ok) {
      setNotice(`sandbox_apply_failed:${validation.errors.join("|")}`);
      return;
    }
    const applied = applyRenderPack(rendererSandboxSelectedPack, voxelSettings);
    setRendererJson(applied.rendererJsonText);
    setVoxelSettings(applied.voxelSettings);
    setRendererVisualSource("json");
    setRendererGameStatus(`sandbox_applied:${rendererSandboxSelectedPack.pack_id}`);
    setRendererSandboxStatus(`applied:${rendererSandboxSelectedPack.pack_id}`);
    setNotice(`sandbox_applied:${rendererSandboxSelectedPack.pack_id}`);
  }

  function deleteRendererSandboxSelectedPack() {
    if (!rendererSandboxSelectedPack) {
      return;
    }
    const targetId = String(rendererSandboxSelectedPack.pack_id);
    setRendererSandboxPacks((prev) => prev.filter((item) => item && item.pack_id !== targetId));
    setRendererSandboxStatus(`deleted:${targetId}`);
    setNotice(`sandbox_deleted:${targetId}`);
  }

  function applyPokemonDsPreset() {
    setVoxelSettings((prev) => ({
      ...prev,
      renderScale: 2,
      visualStyle: "pokemon_ds",
      pixelate: true,
      tile: 16,
      zScale: 10,
      outline: true,
      outlineColor: "#1d2b43",
      edgeGlow: false,
      labelMode: "none",
    }));
    setNotice("renderer_preset:pokemon_ds");
  }

  function applyClassicFalloutPreset() {
    setVoxelSettings((prev) => ({
      ...prev,
      renderMode: "2.5d",
      renderScale: 2,
      visualStyle: "classic_fallout",
      pixelate: true,
      tile: 18,
      zScale: 9,
      background: "#1a1e14",
      outline: true,
      outlineColor: "#3a4327",
      edgeGlow: false,
      labelMode: "type",
      classicFalloutShowLabels: false,
      labelColor: "#c6d68c",
      lighting: { ...(prev.lighting || {}), enabled: false },
    }));
    setNotice("renderer_preset:classic_fallout");
  }

  function applyPokemonG45Preset() {
    setVoxelSettings((prev) => ({
      ...prev,
      renderMode: "2.5d",
      projection: "isometric",
      renderScale: 3,
      visualStyle: "pokemon_g45",
      pixelate: false,
      tile: 24,
      zScale: 12,
      background: "#9ec8f2",
      outline: true,
      outlineColor: "#203654",
      edgeGlow: false,
      labelMode: "none",
      lighting: { ...(prev.lighting || {}), enabled: true, x: 0.42, y: -0.55, z: 0.75, ambient: 0.42, intensity: 0.95 },
    }));
    setNotice("renderer_preset:pokemon_g45");
  }

  function applyWorldMaterialKit() {
    setVoxelMaterials((prev) => {
      const next = Array.isArray(prev) ? [...prev] : [];
      RENDERER_WORLD_MATERIAL_KIT.forEach((item) => {
        const idx = next.findIndex((entry) => entry && entry.id === item.id);
        if (idx >= 0) {
          next[idx] = { ...next[idx], ...item };
        } else {
          next.push({ ...item });
        }
      });
      return next;
    });
  }

  function loadLandscapePreset() {
    applyWorldMaterialKit();
    const voxels = buildLandscapeVoxels();
    setRendererVisualSource("json");
    setRendererJson(JSON.stringify({ voxels }, null, 2));
    setRendererGameStatus(`landscape_loaded:${voxels.length}`);
    setNotice("renderer_content:landscape_loaded");
  }

  function loadStructuresPreset() {
    applyWorldMaterialKit();
    const voxels = [
      ...buildLandscapeVoxels({ width: 24, height: 18, originX: 0, originY: 0 }),
      ...buildStructureVoxels({ originX: 8, originY: 5 }),
      ...buildStructureVoxels({ originX: 23, originY: 7 }),
    ];
    setRendererVisualSource("json");
    setRendererJson(JSON.stringify({ voxels }, null, 2));
    setRendererGameStatus(`structures_loaded:${voxels.length}`);
    setNotice("renderer_content:structures_loaded");
  }

  function loadSpritesPreset() {
    applyWorldMaterialKit();
    const baseTerrain = buildLandscapeVoxels({ width: 18, height: 14, originX: 0, originY: 0 });
    const voxels = [
      ...baseTerrain,
      ...buildSpriteFigureVoxels({ x: 6, y: 6, baseZ: 2, id: "sprite_player", cloth: "sprite_cloth" }),
      ...buildSpriteFigureVoxels({ x: 10, y: 8, baseZ: 2, id: "sprite_npc", cloth: "metal" }),
    ];
    setRendererVisualSource("json");
    setRendererJson(JSON.stringify({ voxels }, null, 2));
    setRendererPlayerId("sprite_player");
    setRendererPlayerFacing("south");
    setRendererPlayerOffset({ x: 0, y: 0, z: 0 });
    setRendererGameStatus(`sprites_loaded:${voxels.length}`);
    setNotice("renderer_content:sprites_loaded");
  }

  function loadWorldCompositionPreset() {
    applyWorldMaterialKit();
    const voxels = [
      ...buildLandscapeVoxels({ width: 52, height: 34, originX: -12, originY: -10 }),
      ...buildStructureVoxels({ originX: 8, originY: 6 }),
      ...buildStructureVoxels({ originX: 22, originY: 11 }),
      ...buildStructureVoxels({ originX: -2, originY: 16 }),
      ...buildSpriteFigureVoxels({ x: 12, y: 12, baseZ: 2, id: "sprite_player", cloth: "sprite_cloth" }),
      ...buildSpriteFigureVoxels({ x: 16, y: 14, baseZ: 2, id: "sprite_merchant", cloth: "wood" }),
      ...buildSpriteFigureVoxels({ x: 4, y: 18, baseZ: 2, id: "sprite_guard", cloth: "metal" }),
    ];
    setRendererVisualSource("json");
    setRendererJson(JSON.stringify({ voxels }, null, 2));
    setRendererPlayerId("sprite_player");
    setRendererPlayerFacing("south");
    setRendererPlayerOffset({ x: 0, y: 0, z: 0 });
    setRendererFollowPlayer(true);
    setRendererGameStatus(`world_comp_loaded:${voxels.length}`);
    setNotice("renderer_content:world_composition_loaded");
  }

  function applyRendererTestSpec() {
    let parsed = null;
    try {
      parsed = JSON.parse(rendererTestSpecText || "{}");
    } catch (error) {
      const msg = `invalid_json:${error && error.message ? error.message : "parse_error"}`;
      setRendererTestHarnessStatus(msg);
      setRendererGameStatus(`renderer_test:${msg}`);
      setNotice(`renderer_test_failed:${msg}`);
      return;
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      setRendererTestHarnessStatus("invalid_spec:root_object_required");
      setRendererGameStatus("renderer_test:invalid_spec");
      setNotice("renderer_test_failed:root_object_required");
      return;
    }
    const applied = [];
    const rendererPayload = isPlainObject(parsed.renderer_json)
      ? parsed.renderer_json
      : (() => {
          const fallback = {};
          ["scene", "background", "voxels", "meta", "entities", "sprites", "tilemap", "camera"].forEach((key) => {
            if (Object.prototype.hasOwnProperty.call(parsed, key)) {
              fallback[key] = parsed[key];
            }
          });
          return Object.keys(fallback).length > 0 ? fallback : null;
        })();
    if (rendererPayload) {
      setRendererVisualSource("json");
      setRendererJson(JSON.stringify(rendererPayload, null, 2));
      applied.push("renderer_json");
    }
    const settingsPatch = isPlainObject(parsed.settings)
      ? parsed.settings
      : isPlainObject(parsed.voxel_settings)
        ? parsed.voxel_settings
        : null;
    if (settingsPatch) {
      setVoxelSettings((prev) => {
        const next = { ...prev, ...settingsPatch };
        if (isPlainObject(settingsPatch.lighting)) {
          next.lighting = { ...(prev.lighting || {}), ...settingsPatch.lighting };
        }
        if (isPlainObject(settingsPatch.rose)) {
          next.rose = { ...(prev.rose || {}), ...settingsPatch.rose };
        }
        if (isPlainObject(settingsPatch.lod)) {
          next.lod = { ...(prev.lod || {}), ...settingsPatch.lod };
        }
        if (isPlainObject(settingsPatch.camera3d)) {
          next.camera3d = normalizeCamera3d({ ...(prev.camera3d || {}), ...settingsPatch.camera3d });
        }
        if (isPlainObject(settingsPatch.camera2d)) {
          next.camera2d = normalizeCamera2d({ ...(prev.camera2d || {}), ...settingsPatch.camera2d });
        }
        return next;
      });
      applied.push("settings");
    }
    const controls = isPlainObject(parsed.controls) ? parsed.controls : null;
    if (controls) {
      if (typeof controls.player_id === "string" && controls.player_id.trim()) {
        setRendererPlayerId(controls.player_id.trim());
      }
      if (typeof controls.player_facing === "string" && controls.player_facing.trim()) {
        applyActivePlayerFacing(controls.player_facing.trim());
      }
      if (typeof controls.follow_player === "boolean") {
        setRendererFollowPlayer(controls.follow_player);
      }
      if (typeof controls.keyboard_motion === "boolean") {
        setRendererKeyboardMotion(controls.keyboard_motion);
      }
      if (typeof controls.click_move === "boolean") {
        setRendererClickMove(controls.click_move);
      }
      if (Number.isFinite(Number(controls.path_step_ms))) {
        setRendererPathStepMs(Number(controls.path_step_ms));
      }
      if (Number.isFinite(Number(controls.player_step))) {
        setRendererPlayerStep(Number(controls.player_step));
      }
      if (typeof controls.gravity_enabled === "boolean") {
        setRendererGravityEnabled(controls.gravity_enabled);
      }
      if (Number.isFinite(Number(controls.gravity_ms))) {
        setRendererGravityMs(Number(controls.gravity_ms));
      }
      if (controls.reset_motion) {
        setRendererMoveQueue([]);
      }
      applied.push("controls");
    }
    const signalPos =
      parsed.signal &&
      typeof parsed.signal === "object" &&
      !Array.isArray(parsed.signal) &&
      parsed.signal.player_position &&
      typeof parsed.signal.player_position === "object" &&
      !Array.isArray(parsed.signal.player_position)
        ? parsed.signal.player_position
        : controls &&
            controls.player_position &&
            typeof controls.player_position === "object" &&
            !Array.isArray(controls.player_position)
          ? controls.player_position
          : null;
    if (signalPos) {
      applyActivePlayerOffset(() => ({
        x: Number(signalPos.x || 0),
        y: Number(signalPos.y || 0),
        z: Number(signalPos.z || 0),
      }));
      applied.push("player_signal");
    } else if (controls && controls.reset_motion) {
      applyActivePlayerOffset(() => ({ x: 0, y: 0, z: 0 }));
    }
    const appliedLabel = applied.length > 0 ? applied.join("+") : "no_changes";
    setRendererTestHarnessStatus(`applied:${appliedLabel}`);
    setRendererGameStatus(`renderer_test:${appliedLabel}`);
    setNotice(`renderer_test_applied:${appliedLabel}`);
  }

  function captureRendererTestSpecFromCurrent() {
    let rendererPayload = {};
    try {
      const parsed = JSON.parse(rendererJson || "{}");
      rendererPayload = isPlainObject(parsed) ? parsed : {};
    } catch {
      rendererPayload = {};
    }
    const snapshot = {
      renderer_json: rendererPayload,
      settings: voxelSettings,
      controls: {
        player_id: rendererPlayerId,
        player_facing: rendererPlayerFacing,
        follow_player: rendererFollowPlayer,
        keyboard_motion: rendererKeyboardMotion,
        click_move: rendererClickMove,
        path_step_ms: rendererPathStepMs,
        player_step: rendererPlayerStep,
        gravity_enabled: rendererGravityEnabled,
        gravity_ms: rendererGravityMs,
      },
      signal: {
        player_position: {
          x: Number(rendererPlayerOffset.x || 0),
          y: Number(rendererPlayerOffset.y || 0),
          z: Number(rendererPlayerOffset.z || 0),
        },
      },
    };
    setRendererTestSpecText(JSON.stringify(snapshot, null, 2));
    setRendererTestHarnessStatus("captured");
    setNotice("renderer_test_captured");
  }

  function insertRendererTestSpecFragment() {
    const fragment = RENDERER_TEST_SPEC_FRAGMENTS.find((item) => item.id === rendererTestFragmentId);
    if (!fragment || !isPlainObject(fragment.spec)) {
      setRendererTestHarnessStatus("fragment_not_found");
      setNotice("renderer_fragment_failed:not_found");
      return;
    }
    let current = {};
    try {
      const parsed = JSON.parse(rendererTestSpecText || "{}");
      current = isPlainObject(parsed) ? parsed : {};
    } catch {
      current = {};
    }
    const mode = String(rendererTestFragmentMode || "merge");
    let next = {};
    if (mode === "replace") {
      next = fragment.spec;
    } else if (mode === "append_voxels") {
      const currentRendererJson = isPlainObject(current.renderer_json) ? current.renderer_json : {};
      const fragmentRendererJson = isPlainObject(fragment.spec.renderer_json) ? fragment.spec.renderer_json : {};
      const currentVoxels = Array.isArray(currentRendererJson.voxels) ? currentRendererJson.voxels : [];
      const fragmentVoxels = Array.isArray(fragmentRendererJson.voxels) ? fragmentRendererJson.voxels : [];
      const mergedRendererJson = deepMergeObjects(currentRendererJson, fragmentRendererJson);
      mergedRendererJson.voxels = currentVoxels.concat(fragmentVoxels);
      next = deepMergeObjects(current, fragment.spec);
      next.renderer_json = mergedRendererJson;
    } else {
      next = deepMergeObjects(current, fragment.spec);
    }
    setRendererTestSpecText(JSON.stringify(next, null, 2));
    setRendererTestHarnessStatus(`fragment_inserted:${fragment.id}:${mode}`);
    setNotice(`renderer_fragment_inserted:${fragment.id}`);
  }

  async function refreshStudioFsAssets() {
    await runAction("studio_fs_list_assets", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const pythonFiles = await window.atelierDesktop.fs.listAssetsBySuffix(studioFsRoot, ".py");
      const scenes = await window.atelierDesktop.fs.listAssetsBySuffix(studioFsRoot, ".scene.json");
      const sprites = await window.atelierDesktop.fs.listAssetsBySuffix(studioFsRoot, ".sprite.json");
      const audioFiles = await listStudioAudioFiles(studioFsRoot);
      const runtimePlans = await listStudioRuntimePlanFiles(studioFsRoot);
      const pyFiles = pythonFiles && pythonFiles.ok && Array.isArray(pythonFiles.files) ? pythonFiles.files : [];
      const sceneFiles = scenes && scenes.ok && Array.isArray(scenes.files) ? scenes.files : [];
      const spriteFiles = sprites && sprites.ok && Array.isArray(sprites.files) ? sprites.files : [];
      setStudioFsPythonFiles(pyFiles);
      setStudioFsSceneFiles(sceneFiles);
      setStudioFsSpriteFiles(spriteFiles);
      setStudioFsAudioFiles(audioFiles);
      setStudioFsRuntimePlanFiles(runtimePlans);
      if (pyFiles.length > 0) {
        setStudioFsSelectedPython(String(pyFiles[0]));
      }
      if (sceneFiles.length > 0) {
        setStudioFsSelectedScene(String(sceneFiles[0]));
      }
      if (spriteFiles.length > 0) {
        setStudioFsSelectedSprite(String(spriteFiles[0]));
      }
      if (audioFiles.length > 0) {
        setStudioFsSelectedAudio(String(audioFiles[0]));
      }
      if (runtimePlans.length > 0 && !runtimePlans.includes(String(studioFsRuntimePlanPath || ""))) {
        setStudioFsRuntimePlanPath(String(runtimePlans[0]));
      }
      return {
        python_count: pyFiles.length,
        scene_count: sceneFiles.length,
        sprite_count: spriteFiles.length,
        audio_count: audioFiles.length,
        runtime_plan_count: runtimePlans.length,
      };
    });
  }

  async function stageSelectedFsAudioToRenderer() {
    await runAction("renderer_audio_stage", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioFsSelectedAudio) {
        throw new Error("studio_fs no audio selected");
      }
      const result = await window.atelierDesktop.fs.readBinaryFileBase64(studioFsRoot, studioFsSelectedAudio);
      if (!result || !result.ok || typeof result.base64 !== "string") {
        throw new Error("studio_fs_read_audio failed");
      }
      const mime = audioMimeTypeForFilename(studioFsSelectedAudio);
      const dataUrl = `data:${mime};base64,${result.base64}`;
      const nextId = `audio_${Date.now()}`;
      const nextLabel = String(rendererAudioStageLabel || studioFsSelectedAudio).trim() || studioFsSelectedAudio;
      const nextEntry = {
        id: nextId,
        label: nextLabel,
        filename: studioFsSelectedAudio,
        mime,
        size: Number(result.size || 0),
        volume: 1,
        loop: false,
        dataUrl,
      };
      setRendererAudioStages((prev) => [nextEntry, ...prev].slice(0, 32));
      setRendererAudioStageLabel("");
      setRendererGameStatus(`audio_staged:${studioFsSelectedAudio}`);
      return { staged_id: nextId, filename: studioFsSelectedAudio, size: nextEntry.size };
    });
  }

  function updateRendererAudioStage(stageId, patch) {
    setRendererAudioStages((prev) =>
      prev.map((entry) => (entry.id === stageId ? { ...entry, ...patch } : entry))
    );
  }

  function removeRendererAudioStage(stageId) {
    setRendererAudioStages((prev) => prev.filter((entry) => entry.id !== stageId));
  }

  async function exportRendererSceneToFs() {
    await runAction("studio_fs_export_scene", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const spec = parseObjectJson(rendererGameSpecText, {});
      const doc = buildSceneSchemaV1FromSpec(spec);
      const sceneObj = doc.scene && typeof doc.scene === "object" ? doc.scene : {};
      const filename = normalizeSceneFilename(String(sceneObj.id || sceneObj.name || "scene"));
      await window.atelierDesktop.fs.writeTextFile(studioFsRoot, filename, JSON.stringify(doc, null, 2));
      await refreshStudioFsAssets();
      return { filename };
    });
  }

  async function importSelectedFsSceneToRenderer() {
    await runAction("studio_fs_import_scene", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioFsSelectedScene) {
        throw new Error("studio_fs no scene selected");
      }
      const result = await window.atelierDesktop.fs.readTextFile(studioFsRoot, studioFsSelectedScene);
      if (!result || !result.ok || typeof result.content !== "string") {
        throw new Error("studio_fs_read_scene failed");
      }
      const parsed = parseObjectJson(result.content, {});
      if (String(parsed.schema || "") !== "qqva.scene.v1") {
        throw new Error("studio_fs scene schema mismatch");
      }
      const spec = buildSpecFromSceneSchemaV1(parsed);
      setRendererGameSpecText(JSON.stringify(spec, null, 2));
      setSection("Renderer Lab");
      return { imported: studioFsSelectedScene };
    });
  }

  async function exportRendererSpriteToFs() {
    await runAction("studio_fs_export_sprite", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      const spriteDoc = {
        schema: "qqva.sprite.v1",
        sprite: {
          id: String(spriteId || "sprite_001"),
          name: String(spriteId || "sprite_001"),
          source: "assets/sprites/placeholder.png",
          frame_w: 32,
          frame_h: 32,
          frames: [{ id: "idle_0", x: 0, y: 0, w: 32, h: 32, ms: 120 }],
          tags: [String(spriteKind || "token")],
          anchor: { x: 16, y: 16 },
          collision: { x: 2, y: 2, w: 28, h: 28 }
        }
      };
      const filename = normalizeSpriteFilename(String(spriteDoc.sprite.id || "sprite"));
      await window.atelierDesktop.fs.writeTextFile(studioFsRoot, filename, JSON.stringify(spriteDoc, null, 2));
      await refreshStudioFsAssets();
      return { filename };
    });
  }

  async function importSelectedFsSpriteToRenderer() {
    await runAction("studio_fs_import_sprite", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioFsSelectedSprite) {
        throw new Error("studio_fs no sprite selected");
      }
      const result = await window.atelierDesktop.fs.readTextFile(studioFsRoot, studioFsSelectedSprite);
      if (!result || !result.ok || typeof result.content !== "string") {
        throw new Error("studio_fs_read_sprite failed");
      }
      const parsed = parseObjectJson(result.content, {});
      if (String(parsed.schema || "") !== "qqva.sprite.v1") {
        throw new Error("studio_fs sprite schema mismatch");
      }
      const spriteObj = parsed.sprite && typeof parsed.sprite === "object" ? parsed.sprite : {};
      const nextId = String(spriteObj.id || spriteId || "sprite_001");
      setSpriteId(nextId);
      if (Array.isArray(spriteObj.tags) && spriteObj.tags.length > 0) {
        setSpriteKind(String(spriteObj.tags[0]));
      }
      setRendererJson(JSON.stringify({ sprite: spriteObj }, null, 2));
      setSection("Renderer Lab");
      return { imported: studioFsSelectedSprite };
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

  async function importSelectedFsPythonToRenderer() {
    await runAction("studio_fs_import_python_renderer", async () => {
      if (!hasDesktopFs()) {
        throw new Error("studio_fs unavailable outside desktop shell");
      }
      if (!studioFsRoot) {
        throw new Error("studio_fs root not set");
      }
      if (!studioFsSelectedPython) {
        throw new Error("studio_fs no python selected");
      }
      const result = await window.atelierDesktop.fs.readTextFile(studioFsRoot, studioFsSelectedPython);
      if (!result || !result.ok || typeof result.content !== "string") {
        throw new Error("studio_fs_read_python failed");
      }
      const filename =
        typeof result.filename === "string" && result.filename.trim()
          ? result.filename
          : studioFsSelectedPython;
      const existing = studioFiles.find((file) => file.folder === "scripts" && file.name === filename);
      const nextId = existing ? existing.id : makeStudioFileId();
      setStudioFiles((prev) => {
        const existingIndex = prev.findIndex((file) => file.folder === "scripts" && file.name === filename);
        if (existingIndex >= 0) {
          const next = [...prev];
          next[existingIndex] = { ...next[existingIndex], content: result.content };
          return next;
        }
        return [
          ...prev,
          {
            id: nextId,
            name: filename,
            folder: "scripts",
            content: result.content,
          },
        ];
      });
      setStudioSelectedFileId(nextId);
      setRendererPython(result.content);
      setRendererPipeline((prev) => ({ ...prev, pythonFileId: nextId }));
      setSection("Renderer Lab");
      setRendererGameStatus(`python_loaded:${filename}`);
      return { imported: studioFsSelectedPython, studio_file_id: nextId };
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

  useEffect(() => {
    const fullscreen = new URLSearchParams(window.location.search).get("view") === "renderer-full";
    if (!fullscreen && section !== "Renderer Lab") {
      return undefined;
    }
    const timer = window.setInterval(() => setRendererAnimationClock(Date.now()), 80);
    return () => window.clearInterval(timer);
  }, [section]);

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
  const filteredContracts = filtered(contracts, contractFilter, ["title", "status", "category", "party_name"]);
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
  const rendererLocalTables = useMemo(() => {
    if (!rendererEngineState || typeof rendererEngineState !== "object") {
      return {};
    }
    const tables = rendererEngineState.tables;
    return isPlainObject(tables) ? tables : {};
  }, [rendererEngineState]);
  const rendererMergedTables = useMemo(
    () => mergeRendererTables(rendererLocalTables, rendererTables, rendererTablesPrecedence),
    [rendererLocalTables, rendererTables, rendererTablesPrecedence]
  );
  const rendererEffectiveEngineState = useMemo(() => {
    if (!rendererEngineState || typeof rendererEngineState !== "object") {
      return { tables: rendererMergedTables, realm_id: rendererRealmId };
    }
    return { ...rendererEngineState, tables: rendererMergedTables, realm_id: rendererRealmId };
  }, [rendererEngineState, rendererMergedTables, rendererRealmId]);
  const pythonFrameDoc = useMemo(
    () => buildRendererFrameHtml("python", rendererPython, rendererEffectiveEngineState),
    [rendererPython, rendererEffectiveEngineState]
  );
  const cobraFrameDoc = useMemo(
    () => buildRendererFrameHtml("cobra", rendererCobra, rendererEffectiveEngineState),
    [rendererCobra, rendererEffectiveEngineState]
  );
  const cobraLintWarnings = useMemo(() => analyzeCobraShygazunScript(rendererCobra), [rendererCobra]);
  const jsFrameDoc = useMemo(
    () => buildRendererFrameHtml("javascript", rendererJs, rendererEffectiveEngineState),
    [rendererJs, rendererEffectiveEngineState]
  );
  const jsonFrameDoc = useMemo(
    () => buildRendererFrameHtml("json", rendererJson, rendererEffectiveEngineState),
    [rendererJson, rendererEffectiveEngineState]
  );
  useEffect(() => {
    if (rendererVisualSource !== "engine") {
      return;
    }
    setRendererParsedPayload({ source: "engine", key: "engine", payload: rendererEffectiveEngineState });
    setRendererParseStatus("direct:engine");
  }, [rendererVisualSource, rendererEffectiveEngineState]);

  useEffect(() => {
    if (rendererVisualSource === "engine") {
      return undefined;
    }
    const mode =
      rendererVisualSource === "cobra" || rendererVisualSource === "json" || rendererVisualSource === "javascript" || rendererVisualSource === "python"
        ? rendererVisualSource
        : "json";
    const sourceText =
      mode === "cobra"
        ? rendererCobra
        : mode === "javascript"
          ? rendererJs
          : mode === "python"
            ? rendererPython
            : rendererJson;
    const parseKey = `${mode}:${sourceText.length}:${localStringHash(sourceText)}`;
    const useWorker = (mode === "cobra" || mode === "json") && sourceText.length >= 4000;
    let cancelled = false;

    if (!useWorker) {
      const parsed = parseRendererPayloadSync(mode, sourceText, rendererEffectiveEngineState);
      setRendererParsedPayload({ source: mode, key: parseKey, payload: parsed });
      setRendererParseStatus(`main:${mode}`);
      return undefined;
    }

    setRendererParseStatus(`worker:${mode}:running`);
    runPayloadParseInWorker({ mode, sourceText, timeoutMs: 2200 })
      .then((parsed) => {
        if (cancelled) {
          return;
        }
        setRendererParsedPayload({ source: mode, key: parseKey, payload: parsed });
        setRendererParseStatus(`worker:${mode}:ok`);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        const parsed = parseRendererPayloadSync(mode, sourceText, rendererEffectiveEngineState);
        setRendererParsedPayload({ source: mode, key: parseKey, payload: parsed });
        setRendererParseStatus(`fallback_main:${mode}`);
      });

    return () => {
      cancelled = true;
    };
  }, [rendererVisualSource, rendererCobra, rendererJson, rendererJs, rendererPython, rendererEffectiveEngineState]);
  const unifiedRendererPayload = useMemo(() => {
    if (rendererVisualSource === "engine") {
      return rendererEffectiveEngineState;
    }
    return rendererParsedPayload && typeof rendererParsedPayload.payload === "object" && rendererParsedPayload.payload
      ? rendererParsedPayload.payload
      : {};
  }, [rendererVisualSource, rendererEffectiveEngineState, rendererParsedPayload]);
  const voxelMaterialsMap = useMemo(() => {
    const map = {};
    voxelMaterials.forEach((mat) => {
      if (mat && typeof mat.id === "string" && mat.id.trim()) {
        map[mat.id.trim()] = mat;
      }
    });
    return map;
  }, [voxelMaterials]);
  const voxelAtlasMap = useMemo(() => {
    const map = {};
    voxelAtlases.forEach((atlas) => {
      if (atlas && typeof atlas.id === "string" && atlas.id.trim()) {
        map[atlas.id.trim()] = atlas;
      }
    });
    return map;
  }, [voxelAtlases]);
  const voxelLayersMap = useMemo(() => {
    const map = {};
    voxelLayers.forEach((layer) => {
      if (layer && typeof layer.id === "string" && layer.id.trim()) {
        map[layer.id.trim()] = layer;
      }
    });
    return map;
  }, [voxelLayers]);
  const rendererSemanticLexicon = useMemo(
    () => buildRendererSemanticLexicon(unifiedRendererPayload, rendererEffectiveEngineState),
    [unifiedRendererPayload, rendererEffectiveEngineState]
  );
  const rendererSignalPlayerPosition = useMemo(
    () => readPlayerPositionSignal(rendererEffectiveEngineState),
    [rendererEffectiveEngineState]
  );
  const unifiedRendererRawVoxels = useMemo(
    () => extractVoxelsFromPayload(unifiedRendererPayload, rendererSemanticLexicon),
    [unifiedRendererPayload, rendererSemanticLexicon]
  );
  useEffect(() => {
    const lodLevel = resolveInputLodLevel(voxelSettings || {});
    const zoom = Number(normalizeCamera2d(voxelSettings && voxelSettings.camera2d).zoom || 1);
    const key = `${unifiedRendererRawVoxels.length}:${lodLevel}:${zoom.toFixed(3)}`;
    const shouldWorker = unifiedRendererRawVoxels.length >= 5000;
    let cancelled = false;

    if (!shouldWorker) {
      const lodResolved = applyInputLod(unifiedRendererRawVoxels, voxelSettings);
      setRendererPreparedVoxels({ key, voxels: lodResolved });
      setRendererVoxelPrepStatus("main");
      return undefined;
    }

    setRendererVoxelPrepStatus("worker:running");
    runVoxelExtractLodInWorker({
      payload: { voxels: unifiedRendererRawVoxels },
      settings: voxelSettings,
      timeoutMs: 2200,
    })
      .then((lodResolved) => {
        if (cancelled) {
          return;
        }
        setRendererPreparedVoxels({ key, voxels: lodResolved });
        setRendererVoxelPrepStatus("worker:ok");
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        const lodResolved = applyInputLod(unifiedRendererRawVoxels, voxelSettings);
        setRendererPreparedVoxels({ key, voxels: lodResolved });
        setRendererVoxelPrepStatus("fallback_main");
      });

    return () => {
      cancelled = true;
    };
  }, [unifiedRendererRawVoxels, voxelSettings]);
  const unifiedRendererVoxels = useMemo(() => {
    const lodResolved = Array.isArray(rendererPreparedVoxels.voxels) ? rendererPreparedVoxels.voxels : [];
    return applyVoxelMaterials(lodResolved, voxelMaterialsMap, voxelLayersMap, voxelAtlasMap);
  }, [rendererPreparedVoxels, voxelMaterialsMap, voxelLayersMap, voxelAtlasMap]);
  const rendererMotionVoxels = useMemo(
    () =>
      applyPlayerMotionToVoxels(
        unifiedRendererVoxels,
        rendererPlayerId,
        rendererSignalPlayerPosition
          ? { mode: "absolute", ...rendererSignalPlayerPosition }
          : { mode: "offset", ...rendererPlayerOffset },
        rendererSemanticLexicon,
        rendererPlayerFacing
      ),
    [unifiedRendererVoxels, rendererPlayerId, rendererPlayerOffset, rendererSemanticLexicon, rendererSignalPlayerPosition, rendererPlayerFacing]
  );
  const rendererPlayerMoving = useMemo(
    () => rendererMoveQueue.length > 0 || rendererAnimationClock - Number(rendererLastMoveAt || 0) < 180,
    [rendererMoveQueue.length, rendererAnimationClock, rendererLastMoveAt]
  );
  const rendererRoseVector = useMemo(
    () => resolveRoseVector(unifiedRendererPayload, rendererEffectiveEngineState),
    [unifiedRendererPayload, rendererEffectiveEngineState]
  );
  const isFullscreenRenderer = useMemo(
    () => new URLSearchParams(window.location.search).get("view") === "renderer-full",
    []
  );
  const fullscreenPayload = useMemo(() => {
    if (fullscreenState.source === "cobra") {
      return parseCobraShygazunScript(fullscreenState.cobra);
    }
    if (fullscreenState.source === "javascript") {
      return parseRendererPayloadSync("javascript", fullscreenState.javascript, fullscreenState.engine);
    }
    if (fullscreenState.source === "python") {
      return parseRendererPayloadSync("python", fullscreenState.python, fullscreenState.engine);
    }
    if (fullscreenState.source === "engine") {
      return fullscreenState.engine;
    }
    try {
      return JSON.parse(fullscreenState.json || "{}");
    } catch {
      return {};
    }
  }, [fullscreenState]);
  const fullscreenVoxels = useMemo(() => {
    const fullscreenSemanticLexicon = buildRendererSemanticLexicon(fullscreenPayload, fullscreenState.engine);
    const raw = extractVoxelsFromPayload(fullscreenPayload, fullscreenSemanticLexicon);
    const materialsMap = {};
    const layersMap = {};
    if (fullscreenState.materials && Array.isArray(fullscreenState.materials)) {
      fullscreenState.materials.forEach((mat) => {
        if (mat && typeof mat.id === "string" && mat.id.trim()) {
          materialsMap[mat.id.trim()] = mat;
        }
      });
    }
    if (fullscreenState.layers && Array.isArray(fullscreenState.layers)) {
      fullscreenState.layers.forEach((layer) => {
        if (layer && typeof layer.id === "string" && layer.id.trim()) {
          layersMap[layer.id.trim()] = layer;
        }
      });
    }
    const atlasMap = {};
    if (fullscreenState.atlases && Array.isArray(fullscreenState.atlases)) {
      fullscreenState.atlases.forEach((atlas) => {
        if (atlas && typeof atlas.id === "string" && atlas.id.trim()) {
          atlasMap[atlas.id.trim()] = atlas;
        }
      });
    }
    const lodResolved = applyInputLod(raw, fullscreenState.settings || {});
    return applyVoxelMaterials(lodResolved, materialsMap, layersMap, atlasMap);
  }, [fullscreenPayload, fullscreenState]);
  const labGovernor = useMemo(() => {
    const tileCount = Object.keys(tilePlacements || {}).length;
    const mainVoxelCount = Array.isArray(unifiedRendererVoxels) ? unifiedRendererVoxels.length : 0;
    const fullVoxelCount = Array.isArray(fullscreenVoxels) ? fullscreenVoxels.length : 0;
    const fullscreen = new URLSearchParams(window.location.search).get("view") === "renderer-full";
    const active = fullscreen || section === "Renderer Lab";
    let level = "normal";
    if (tileCount > 60000 || mainVoxelCount > 18000 || fullVoxelCount > 18000) {
      level = "critical";
    } else if (tileCount > 35000 || mainVoxelCount > 12000 || fullVoxelCount > 12000) {
      level = "high";
    } else if (tileCount > 18000 || mainVoxelCount > 7000 || fullVoxelCount > 7000) {
      level = "elevated";
    }
    const downgrade = active && (level === "high" || level === "critical");
    return {
      level,
      active,
      downgrade,
      tileCount,
      mainVoxelCount,
      fullVoxelCount,
      mainPatch: downgrade
        ? {
            edgeGlow: false,
            outline: false,
            lighting: { ...(voxelSettings?.lighting || {}), enabled: false },
            rose: { ...(voxelSettings?.rose || {}), enabled: false, strength: 0 },
            renderScale: Math.max(0.5, Math.min(Number(voxelSettings?.renderScale || 1), 0.85)),
          }
        : {},
      fullPatch: downgrade
        ? {
            edgeGlow: false,
            outline: false,
            lighting: { ...(fullscreenState?.settings?.lighting || {}), enabled: false },
            rose: { ...(fullscreenState?.settings?.rose || {}), enabled: false, strength: 0 },
            renderScale: Math.max(0.5, Math.min(Number(fullscreenState?.settings?.renderScale || 1), 0.85)),
          }
        : {},
    };
  }, [tilePlacements, unifiedRendererVoxels, fullscreenVoxels, section, voxelSettings, fullscreenState]);
  const effectiveVoxelSettings = useMemo(() => {
    const rose = voxelSettings && typeof voxelSettings.rose === "object" ? voxelSettings.rose : {};
    const baseRaw = {
      ...voxelSettings,
      rose: { ...rose, data: rendererRoseVector },
      playerFacing: normalizeFacing(rendererPlayerFacing),
      playerMoving: rendererPlayerMoving,
      animationClock: rendererAnimationClock,
      spriteAnimMs: 120,
    };
    const base = labGovernor.downgrade ? { ...baseRaw, ...labGovernor.mainPatch } : baseRaw;
    if (!rendererFollowPlayer) {
      return base;
    }
    const renderMode = normalizeRenderMode(base.renderMode);
    if (renderMode === "3d") {
      const pan3d = computePlayerFollowPan3d(
        rendererMotionVoxels,
        rendererPlayerId,
        Number(base.tile || 18),
        Number(base.zScale || 8),
        rendererSemanticLexicon
      );
      return {
        ...base,
        camera3d: normalizeCamera3d({ ...(base.camera3d || {}), panX: pan3d.panX, panY: pan3d.panY }),
      };
    }
    const baseCamera2d = normalizeCamera2d(base.camera2d);
    const pan2d = computePlayerFollowPan2d(
      rendererMotionVoxels,
      rendererPlayerId,
      Number(base.tile || 18) * Number(baseCamera2d.zoom || 1),
      Number(base.zScale || 8) * Number(baseCamera2d.zoom || 1),
      rendererSemanticLexicon,
      String(base.projection || "isometric")
    );
    return {
      ...base,
      camera2d: normalizeCamera2d({
        ...baseCamera2d,
        panX: Number(baseCamera2d.panX || 0) + Number(pan2d.panX || 0),
        panY: Number(baseCamera2d.panY || 0) + Number(pan2d.panY || 0),
      }),
    };
  }, [voxelSettings, rendererRoseVector, rendererFollowPlayer, rendererMotionVoxels, rendererPlayerId, rendererSemanticLexicon, rendererPlayerFacing, rendererPlayerMoving, rendererAnimationClock, labGovernor]);
  const fullscreenSemanticLexicon = useMemo(
    () => buildRendererSemanticLexicon(fullscreenPayload, fullscreenState.engine),
    [fullscreenPayload, fullscreenState.engine]
  );
  const fullscreenSignalPlayerPosition = useMemo(
    () => readPlayerPositionSignal(fullscreenState.engine),
    [fullscreenState.engine]
  );
  const fullscreenMotionVoxels = useMemo(
    () =>
      applyPlayerMotionToVoxels(
        fullscreenVoxels,
        fullscreenState.playerId || "player",
        fullscreenSignalPlayerPosition
          ? { mode: "absolute", ...fullscreenSignalPlayerPosition }
          : { mode: "offset", ...(fullscreenState.playerOffset || { x: 0, y: 0, z: 0 }) },
        fullscreenSemanticLexicon,
        fullscreenState.playerFacing || "south"
      ),
    [fullscreenVoxels, fullscreenState.playerId, fullscreenState.playerOffset, fullscreenState.playerFacing, fullscreenSemanticLexicon, fullscreenSignalPlayerPosition]
  );
  const fullscreenPlayerMoving = useMemo(
    () => rendererMoveQueue.length > 0 || rendererAnimationClock - Number(rendererLastMoveAt || 0) < 180,
    [rendererMoveQueue.length, rendererAnimationClock, rendererLastMoveAt]
  );
  const fullscreenRoseVector = useMemo(
    () => resolveRoseVector(fullscreenPayload, fullscreenState.engine),
    [fullscreenPayload, fullscreenState.engine]
  );
  const fullscreenEffectiveSettings = useMemo(() => {
    const base = fullscreenState.settings && typeof fullscreenState.settings === "object" ? fullscreenState.settings : {};
    const rose = base.rose && typeof base.rose === "object" ? base.rose : {};
    const withRoseRaw = {
      ...base,
      rose: { ...rose, data: fullscreenRoseVector },
      playerFacing: normalizeFacing(fullscreenState.playerFacing || "south"),
      playerMoving: fullscreenPlayerMoving,
      animationClock: rendererAnimationClock,
      spriteAnimMs: 120,
    };
    const withRose = labGovernor.downgrade ? { ...withRoseRaw, ...labGovernor.fullPatch } : withRoseRaw;
    if (!fullscreenState.followPlayer) {
      return withRose;
    }
    const renderMode = normalizeRenderMode(withRose.renderMode);
    if (renderMode === "3d") {
      const pan3d = computePlayerFollowPan3d(
        fullscreenMotionVoxels,
        fullscreenState.playerId || "player",
        Number(withRose.tile || 18),
        Number(withRose.zScale || 8),
        fullscreenSemanticLexicon
      );
      return {
        ...withRose,
        camera3d: normalizeCamera3d({ ...(withRose.camera3d || {}), panX: pan3d.panX, panY: pan3d.panY }),
      };
    }
    const baseCamera2d = normalizeCamera2d(withRose.camera2d);
    const pan2d = computePlayerFollowPan2d(
      fullscreenMotionVoxels,
      fullscreenState.playerId || "player",
      Number(withRose.tile || 18) * Number(baseCamera2d.zoom || 1),
      Number(withRose.zScale || 8) * Number(baseCamera2d.zoom || 1),
      fullscreenSemanticLexicon,
      String(withRose.projection || "isometric")
    );
    return {
      ...withRose,
      camera2d: normalizeCamera2d({
        ...baseCamera2d,
        panX: Number(baseCamera2d.panX || 0) + Number(pan2d.panX || 0),
        panY: Number(baseCamera2d.panY || 0) + Number(pan2d.panY || 0),
      }),
    };
  }, [fullscreenState.settings, fullscreenState.playerFacing, fullscreenRoseVector, fullscreenState.followPlayer, fullscreenState.playerId, fullscreenMotionVoxels, fullscreenSemanticLexicon, fullscreenPlayerMoving, rendererAnimationClock, labGovernor]);

  const updateMainCamera3d = (mutate) => {
    setVoxelSettings((prev) => {
      const currentCamera = normalizeCamera3d(prev.camera3d);
      const nextCamera = normalizeCamera3d(mutate(currentCamera));
      return { ...prev, camera3d: nextCamera };
    });
  };

  const updateMainCamera2d = (mutate) => {
    setVoxelSettings((prev) => {
      const currentCamera = normalizeCamera2d(prev.camera2d);
      const nextCamera = normalizeCamera2d(mutate(currentCamera));
      return { ...prev, camera2d: nextCamera };
    });
  };

  const updateFullscreenCamera3d = (mutate) => {
    setFullscreenState((prev) => {
      const baseSettings = prev.settings && typeof prev.settings === "object" ? prev.settings : {};
      const currentCamera = normalizeCamera3d(baseSettings.camera3d);
      const nextCamera = normalizeCamera3d(mutate(currentCamera));
      const nextSettings = { ...baseSettings, camera3d: nextCamera };
      localStorage.setItem("atelier.renderer.voxel_settings", JSON.stringify(nextSettings));
      return { ...prev, settings: nextSettings };
    });
  };

  const updateFullscreenCamera2d = (mutate) => {
    setFullscreenState((prev) => {
      const baseSettings = prev.settings && typeof prev.settings === "object" ? prev.settings : {};
      const currentCamera = normalizeCamera2d(baseSettings.camera2d);
      const nextCamera = normalizeCamera2d(mutate(currentCamera));
      const nextSettings = { ...baseSettings, camera2d: nextCamera };
      localStorage.setItem("atelier.renderer.voxel_settings", JSON.stringify(nextSettings));
      return { ...prev, settings: nextSettings };
    });
  };

  const handleRendererPointerDown = (event, target) => {
    const mode = target === "fullscreen"
      ? String(fullscreenEffectiveSettings.renderMode || "2.5d").toLowerCase()
      : String(voxelSettings.renderMode || "2.5d").toLowerCase();
    const projection = target === "fullscreen"
      ? String(fullscreenEffectiveSettings.projection || "isometric").toLowerCase()
      : String(voxelSettings.projection || "isometric").toLowerCase();
    if (mode !== "3d" && !(mode === "2.5d" && projection === "isometric")) {
      return;
    }
    const dragRef = target === "fullscreen" ? fullscreenCameraDragRef : unifiedCameraDragRef;
    const panMode = event.button === 1 || event.button === 2 || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey;
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      mode: mode === "3d" ? (panMode ? "pan" : "orbit") : "pan2d",
    };
    if (event.currentTarget && typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    if (event.cancelable) {
      event.preventDefault();
    }
  };

  const handleRendererPointerMove = (event, target) => {
    const dragRef = target === "fullscreen" ? fullscreenCameraDragRef : unifiedCameraDragRef;
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    drag.x = event.clientX;
    drag.y = event.clientY;
    if (drag.mode === "pan2d") {
      const update2d = target === "fullscreen" ? updateFullscreenCamera2d : updateMainCamera2d;
      update2d((camera) => ({ ...camera, panX: camera.panX + dx, panY: camera.panY + dy }));
    } else {
      const update = target === "fullscreen" ? updateFullscreenCamera3d : updateMainCamera3d;
      if (drag.mode === "pan") {
        update((camera) => ({ ...camera, panX: camera.panX + dx, panY: camera.panY + dy }));
      } else {
        update((camera) => ({ ...camera, yaw: camera.yaw + dx * 0.35, pitch: camera.pitch - dy * 0.25 }));
      }
    }
    if (event.cancelable) {
      event.preventDefault();
    }
  };

  const handleRendererPointerUp = (event, target) => {
    const dragRef = target === "fullscreen" ? fullscreenCameraDragRef : unifiedCameraDragRef;
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    dragRef.current = null;
    if (event.currentTarget && typeof event.currentTarget.releasePointerCapture === "function") {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (event.cancelable) {
      event.preventDefault();
    }
  };

  const handleRendererWheel = (event, target) => {
    const mode = target === "fullscreen"
      ? String(fullscreenEffectiveSettings.renderMode || "2.5d").toLowerCase()
      : String(voxelSettings.renderMode || "2.5d").toLowerCase();
    if (mode === "3d") {
      const update = target === "fullscreen" ? updateFullscreenCamera3d : updateMainCamera3d;
      const direction = Math.sign(event.deltaY);
      const factor = direction > 0 ? 0.92 : 1.08;
      update((camera) => ({ ...camera, zoom: camera.zoom * factor }));
      if (event.cancelable) {
        event.preventDefault();
      }
      return;
    }
    const projection = target === "fullscreen"
      ? String(fullscreenEffectiveSettings.projection || "isometric").toLowerCase()
      : String(voxelSettings.projection || "isometric").toLowerCase();
    if (mode === "2.5d" && projection === "isometric") {
      const update2d = target === "fullscreen" ? updateFullscreenCamera2d : updateMainCamera2d;
      const direction = Math.sign(event.deltaY);
      const factor = direction > 0 ? 0.92 : 1.08;
      update2d((camera) => ({ ...camera, zoom: camera.zoom * factor }));
      if (event.cancelable) {
        event.preventDefault();
      }
    }
  };

  const mergePlayerSignalIntoEngineText = (engineText, playerPosition) => {
    const stateObj = parseObjectJson(engineText || "{}", {});
    const signals = stateObj.signals && typeof stateObj.signals === "object" ? { ...stateObj.signals } : {};
    signals.player_position = {
      x: Number(playerPosition && playerPosition.x || 0),
      y: Number(playerPosition && playerPosition.y || 0),
      z: Number(playerPosition && playerPosition.z || 0),
      updated_at: new Date().toISOString(),
    };
    return JSON.stringify({ ...stateObj, signals }, null, 2);
  };

  const publishPlayerPositionSignal = (playerPosition) => {
    const next = {
      x: Number(playerPosition && playerPosition.x || 0),
      y: Number(playerPosition && playerPosition.y || 0),
      z: Number(playerPosition && playerPosition.z || 0),
    };
    localStorage.setItem("atelier.renderer.player_offset", JSON.stringify(next));
    localStorage.setItem(
      "atelier.renderer.player_signal",
      JSON.stringify({ ...next, updated_at: new Date().toISOString() })
    );
    localStorage.setItem("atelier.renderer.sync_nonce", `${Date.now()}_${Math.random().toString(16).slice(2)}`);
    if (typeof BroadcastChannel !== "undefined") {
      try {
        const channel = new BroadcastChannel(RENDERER_SYNC_CHANNEL);
        channel.postMessage({ type: "renderer_sync", at: Date.now(), player_position: next });
        channel.close();
      } catch {
        // best-effort
      }
    }
    if (isFullscreenRenderer) {
      setFullscreenState((prev) => {
        const engineObj = prev.engine && typeof prev.engine === "object" ? prev.engine : {};
        const signals = engineObj.signals && typeof engineObj.signals === "object" ? { ...engineObj.signals } : {};
        signals.player_position = { ...next, updated_at: new Date().toISOString() };
        return { ...prev, engine: { ...engineObj, signals } };
      });
    } else {
      setRendererEngineStateText((prevText) => mergePlayerSignalIntoEngineText(prevText, next));
    }
  };

  const applyActivePlayerFacing = (facingValue) => {
    const nextFacing = normalizeFacing(facingValue);
    localStorage.setItem("atelier.renderer.player_facing", nextFacing);
    if (typeof BroadcastChannel !== "undefined") {
      try {
        const channel = new BroadcastChannel(RENDERER_SYNC_CHANNEL);
        channel.postMessage({ type: "renderer_sync", at: Date.now(), player_facing: nextFacing });
        channel.close();
      } catch {
        // best-effort
      }
    }
    if (isFullscreenRenderer) {
      setFullscreenState((prev) => ({ ...prev, playerFacing: nextFacing }));
    } else {
      setRendererPlayerFacing(nextFacing);
    }
  };

  const applyActivePlayerOffset = (mutate) => {
    if (isFullscreenRenderer) {
      setFullscreenState((prev) => {
        const current = prev && prev.playerOffset && typeof prev.playerOffset === "object"
          ? prev.playerOffset
          : { x: 0, y: 0, z: 0 };
        const nextRaw = mutate({
          x: Number(current.x || 0),
          y: Number(current.y || 0),
          z: Number(current.z || 0),
        });
        const next = {
          x: Number(nextRaw && nextRaw.x || 0),
          y: Number(nextRaw && nextRaw.y || 0),
          z: Number(nextRaw && nextRaw.z || 0),
        };
        publishPlayerPositionSignal(next);
        return { ...prev, playerOffset: next };
      });
      return;
    }
    setRendererPlayerOffset((prev) => {
      const current = prev && typeof prev === "object" ? prev : { x: 0, y: 0, z: 0 };
      const nextRaw = mutate({
        x: Number(current.x || 0),
        y: Number(current.y || 0),
        z: Number(current.z || 0),
      });
      const next = {
        x: Number(nextRaw && nextRaw.x || 0),
        y: Number(nextRaw && nextRaw.y || 0),
        z: Number(nextRaw && nextRaw.z || 0),
      };
      publishPlayerPositionSignal(next);
      return next;
    });
  };

  const handleRendererClickMove = (event, target) => {
    if (target !== "main" || !rendererClickMove) {
      return;
    }
    const renderMode = String(effectiveVoxelSettings.renderMode || "2.5d").toLowerCase();
    if (renderMode === "3d") {
      setRendererGameStatus("click_move:3d_not_supported_yet");
      return;
    }
    const canvas = unifiedRendererCanvasRef.current;
    if (!canvas) {
      return;
    }
    const player = rendererMotionVoxels.find((item) => isRendererPlayerVoxel(item, rendererPlayerId, rendererSemanticLexicon));
    if (!player) {
      setRendererGameStatus("click_move:player_not_found");
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    const targetPoint = screenToIsoGridPoint2d(
      localX,
      localY,
      Math.max(1, canvas.clientWidth),
      Math.max(1, canvas.clientHeight),
      rendererMotionVoxels,
      effectiveVoxelSettings,
      Number(player.z || 0)
    );
    if (!targetPoint) {
      return;
    }
    const step = Math.max(0.1, Number(rendererPlayerStep || 1));
    const targetX = Math.round(targetPoint.x / step) * step;
    const targetY = Math.round(targetPoint.y / step) * step;
    const dx = targetX - Number(player.x || 0);
    const dy = targetY - Number(player.y || 0);
    if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
      return;
    }
    const queue = buildStepDeltaQueue(dx, dy, 0, Math.max(0.1, Number(rendererPlayerStep || 1))).map((step) => ({
      ...step,
      facing: facingFromDelta(step.dx, step.dy, rendererPlayerFacing),
    }));
    if (queue.length === 0) {
      return;
    }
    setRendererMoveQueue(queue);
    setRendererGameStatus(`click_move_path:${targetX},${targetY},steps=${queue.length}`);
  };

  useEffect(() => {
    if (governorLevelRef.current === labGovernor.level) {
      return;
    }
    governorLevelRef.current = labGovernor.level;
    setNotice(
      `lab_governor:${labGovernor.level}:tiles=${labGovernor.tileCount}:voxels=${labGovernor.mainVoxelCount}`
    );
  }, [labGovernor]);

  useEffect(() => {
    if (!rendererSimPlaying) {
      return;
    }
    if (labGovernor.level === "critical") {
      setRendererSimPlaying(false);
      setRendererGameStatus("playtest_paused_by_governor");
    }
  }, [labGovernor.level, rendererSimPlaying]);

  useEffect(() => {
    if (section !== "Renderer Lab") {
      return undefined;
    }
    const canvas = unifiedRendererCanvasRef.current;
    if (!canvas) {
      return undefined;
    }
    drawVoxelScene(canvas, rendererMotionVoxels, effectiveVoxelSettings);
    if (showCollisionOverlay && collisionMap) {
      drawCollisionOverlay(canvas, collisionMap, effectiveVoxelSettings);
    }
    const handleResize = () => {
      drawVoxelScene(canvas, rendererMotionVoxels, effectiveVoxelSettings);
      if (showCollisionOverlay && collisionMap) {
        drawCollisionOverlay(canvas, collisionMap, effectiveVoxelSettings);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [rendererMotionVoxels, effectiveVoxelSettings, section, showCollisionOverlay, collisionMap]);

  const derivedBusinessArchitectureSpec = useMemo(
    () => deriveBusinessArchitectureSpec(rendererTables, rendererPipeline, studioFiles),
    [rendererTables, rendererPipeline, studioFiles]
  );
  const businessRendererSpecResult = useMemo(() => {
    if (businessRendererUseDerived) {
      return { spec: derivedBusinessArchitectureSpec, error: "" };
    }
    const mode = String(businessRendererInputMode || "json").toLowerCase();
    if (mode === "json") {
      try {
        const parsed = JSON.parse(businessRendererInputText || "{}");
        return { spec: parsed && typeof parsed === "object" ? parsed : {}, error: "" };
      } catch {
        return { spec: {}, error: "JSON parse error" };
      }
    }
    return {
      spec: parseArchitectureInput(mode, businessRendererInputText),
      error: ""
    };
  }, [
    businessRendererUseDerived,
    derivedBusinessArchitectureSpec,
    businessRendererInputMode,
    businessRendererInputText
  ]);
  const businessArchitectureModel = useMemo(
    () => normalizeArchitectureSpec(businessRendererSpecResult.spec),
    [businessRendererSpecResult]
  );
  const businessLogicRendererSpecResult = useMemo(() => {
    if (businessLogicRendererUseDerived) {
      return { spec: derivedBusinessArchitectureSpec, error: "" };
    }
    const mode = String(businessLogicRendererInputMode || "json").toLowerCase();
    if (mode === "json") {
      try {
        const parsed = JSON.parse(businessLogicRendererInputText || "{}");
        return { spec: parsed && typeof parsed === "object" ? parsed : {}, error: "" };
      } catch {
        return { spec: {}, error: "JSON parse error" };
      }
    }
    return {
      spec: parseArchitectureInput(mode, businessLogicRendererInputText),
      error: ""
    };
  }, [
    businessLogicRendererUseDerived,
    derivedBusinessArchitectureSpec,
    businessLogicRendererInputMode,
    businessLogicRendererInputText
  ]);
  const businessLogicArchitectureModel = useMemo(
    () => normalizeArchitectureSpec(businessLogicRendererSpecResult.spec),
    [businessLogicRendererSpecResult]
  );

  useEffect(() => {
    const canvas = businessRendererCanvasRef.current;
    if (!canvas) {
      return undefined;
    }
    drawBusinessArchitecture(canvas, businessArchitectureModel);
    const handleResize = () => drawBusinessArchitecture(canvas, businessArchitectureModel);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [businessArchitectureModel]);

  useEffect(() => {
    const canvas = businessLogicRendererCanvasRef.current;
    if (!canvas) {
      return undefined;
    }
    drawBusinessArchitecture(canvas, businessLogicArchitectureModel);
    const handleResize = () => drawBusinessArchitecture(canvas, businessLogicArchitectureModel);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [businessLogicArchitectureModel]);

  useEffect(() => {
    if (businessRendererSpecResult.error) {
      setBusinessRendererStatus(`error: ${businessRendererSpecResult.error}`);
      return;
    }
    setBusinessRendererStatus("ready");
  }, [businessRendererSpecResult]);

  useEffect(() => {
    if (businessLogicRendererSpecResult.error) {
      setBusinessLogicRendererStatus(`error: ${businessLogicRendererSpecResult.error}`);
      return;
    }
    setBusinessLogicRendererStatus("ready");
  }, [businessLogicRendererSpecResult]);

  useEffect(() => {
    if (contentValidatePayload && contentValidatePayload.trim()) {
      return;
    }
    if (contentValidateSource === "cobra") {
      setContentValidatePayload(rendererCobra);
    } else {
      setContentValidatePayload(rendererJson);
    }
  }, [contentValidatePayload, contentValidateSource, rendererCobra, rendererJson]);

  useEffect(() => {
    if (!contentValidateSceneId || !contentValidateSceneId.trim()) {
      setContentValidateSceneId(`${rendererRealmId}/renderer-lab`);
    }
  }, [contentValidateSceneId, rendererRealmId]);

  useEffect(() => {
    const scene = contentValidateSceneId || "";
    if (scene && scene.includes("/") && !scene.startsWith(`${rendererRealmId}/`)) {
      setValidationSummary((prev) => ({
        ...prev,
        ok: false,
      }));
    }
  }, [contentValidateSceneId, rendererRealmId]);

  useEffect(() => {
    if (!rendererKeyboardMotion) {
      return undefined;
    }
    const handleKeyDown = (event) => {
      const active = document.activeElement;
      const tag = active && active.tagName ? String(active.tagName).toLowerCase() : "";
      const isEditing =
        Boolean(active && active.isContentEditable) ||
        tag === "input" ||
        tag === "textarea" ||
        tag === "select";
      if (isEditing) {
        return;
      }
      const step = Math.max(0.1, Number(rendererPlayerStep || 1));
      let dx = 0;
      let dy = 0;
      let dz = 0;
      if (event.key === "ArrowUp") {
        dy = -step;
      } else if (event.key === "ArrowDown") {
        dy = step;
      } else if (event.key === "ArrowLeft") {
        dx = -step;
      } else if (event.key === "ArrowRight") {
        dx = step;
      } else if (event.key === "PageUp") {
        dz = step;
      } else if (event.key === "PageDown") {
        dz = -step;
      } else if (event.key === " " || event.code === "Space") {
        dz = 1;
      } else {
        return;
      }
      if (event.cancelable) {
        event.preventDefault();
      }
      if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
        applyActivePlayerFacing(facingFromDelta(dx, dy, isFullscreenRenderer ? fullscreenState.playerFacing : rendererPlayerFacing));
        setRendererLastMoveAt(Date.now());
      }
      applyActivePlayerOffset((prev) => ({
        x: Number(prev.x || 0) + dx,
        y: Number(prev.y || 0) + dy,
        z: Number(prev.z || 0) + dz,
      }));
      setRendererGameStatus(`player_offset:${dx},${dy},${dz}`);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [rendererKeyboardMotion, rendererPlayerStep, isFullscreenRenderer, rendererPlayerFacing, fullscreenState.playerFacing]);

  useEffect(() => {
    if (!Array.isArray(rendererMoveQueue) || rendererMoveQueue.length === 0) {
      return undefined;
    }
    const intervalMs = Math.max(16, Number(rendererPathStepMs || 75));
    const timer = window.setInterval(() => {
      let delta = null;
      setRendererMoveQueue((prev) => {
        if (!Array.isArray(prev) || prev.length === 0) {
          return [];
        }
        delta = prev[0];
        return prev.slice(1);
      });
      if (delta) {
        if (Math.abs(Number(delta.dx || 0)) > 0 || Math.abs(Number(delta.dy || 0)) > 0) {
          applyActivePlayerFacing(delta.facing || facingFromDelta(delta.dx, delta.dy, rendererPlayerFacing));
          setRendererLastMoveAt(Date.now());
        }
        applyActivePlayerOffset((prev) => ({
          x: Number(prev.x || 0) + Number(delta.dx || 0),
          y: Number(prev.y || 0) + Number(delta.dy || 0),
          z: Number(prev.z || 0) + Number(delta.dz || 0),
        }));
      }
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [rendererMoveQueue, rendererPathStepMs, isFullscreenRenderer, rendererPlayerFacing]);

  useEffect(() => {
    if (!rendererGravityEnabled) {
      return undefined;
    }
    const intervalMs = Math.max(40, Number(rendererGravityMs || 150));
    const timer = window.setInterval(() => {
      applyActivePlayerOffset((prev) => {
        const currentZ = Number(prev.z || 0);
        if (currentZ <= 0) {
          return prev;
        }
        return { ...prev, z: Math.max(0, currentZ - 1) };
      });
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [rendererGravityEnabled, rendererGravityMs, isFullscreenRenderer]);

  useEffect(() => {
    if (isFullscreenRenderer) {
      return;
    }
    localStorage.setItem("atelier.renderer.source", rendererVisualSource);
    localStorage.setItem("atelier.renderer.json", rendererJson);
    localStorage.setItem("atelier.renderer.cobra", rendererCobra);
    localStorage.setItem("atelier.renderer.js", rendererJs);
    localStorage.setItem("atelier.renderer.python", rendererPython);
    localStorage.setItem("atelier.renderer.engine", JSON.stringify(rendererEngineState || {}));
    localStorage.setItem("atelier.renderer.realm", rendererRealmId);
    localStorage.setItem("atelier.renderer.validate_before_emit", validateBeforeEmit ? "1" : "0");
    localStorage.setItem("atelier.renderer.strict_bilingual", strictBilingualValidation ? "1" : "0");
    localStorage.setItem("atelier.renderer.voxel_settings", JSON.stringify(voxelSettings));
    localStorage.setItem("atelier.renderer.materials", JSON.stringify(voxelMaterials));
    localStorage.setItem("atelier.renderer.layers", JSON.stringify(voxelLayers));
    localStorage.setItem("atelier.renderer.atlases", JSON.stringify(voxelAtlases));
    localStorage.setItem("atelier.renderer.tables", JSON.stringify(rendererTables));
    localStorage.setItem("atelier.renderer.tables_meta", JSON.stringify(rendererTablesMeta));
    localStorage.setItem("atelier.renderer.tables_precedence", rendererTablesPrecedence);
    localStorage.setItem("atelier.renderer.state_commit_mode", rendererStateCommitMode);
    localStorage.setItem("atelier.renderer.player_id", rendererPlayerId);
    localStorage.setItem("atelier.renderer.player_facing", rendererPlayerFacing);
    localStorage.setItem("atelier.renderer.follow_player", rendererFollowPlayer ? "1" : "0");
    localStorage.setItem("atelier.renderer.keyboard_motion", rendererKeyboardMotion ? "1" : "0");
    localStorage.setItem("atelier.renderer.click_move", rendererClickMove ? "1" : "0");
    localStorage.setItem("atelier.renderer.path_step_ms", String(rendererPathStepMs));
    localStorage.setItem("atelier.renderer.player_step", String(rendererPlayerStep));
    localStorage.setItem("atelier.renderer.gravity_enabled", rendererGravityEnabled ? "1" : "0");
    localStorage.setItem("atelier.renderer.gravity_ms", String(rendererGravityMs));
    localStorage.setItem("atelier.renderer.player_offset", JSON.stringify(rendererPlayerOffset));
    localStorage.setItem("atelier.renderer.test_spec", rendererTestSpecText);
    localStorage.setItem("atelier.renderer.sync_nonce", `${Date.now()}_${Math.random().toString(16).slice(2)}`);
    if (typeof BroadcastChannel !== "undefined") {
      try {
        const channel = new BroadcastChannel(RENDERER_SYNC_CHANNEL);
        channel.postMessage({ type: "renderer_sync", at: Date.now() });
        channel.close();
      } catch {
        // best-effort cross-window sync
      }
    }
    localStorage.setItem("atelier.business_renderer.input_mode", businessRendererInputMode);
    localStorage.setItem("atelier.business_renderer.input_text", businessRendererInputText);
    localStorage.setItem("atelier.business_renderer.use_derived", businessRendererUseDerived ? "1" : "0");
    localStorage.setItem("atelier.business_logic_renderer.input_mode", businessLogicRendererInputMode);
    localStorage.setItem("atelier.business_logic_renderer.input_text", businessLogicRendererInputText);
    localStorage.setItem("atelier.business_logic_renderer.use_derived", businessLogicRendererUseDerived ? "1" : "0");
    localStorage.setItem("atelier.lesson_actor", lessonActorId);
  }, [
    rendererVisualSource,
    rendererJson,
    rendererCobra,
    rendererEngineState,
    rendererJs,
    rendererPython,
    voxelSettings,
    voxelMaterials,
    voxelLayers,
    voxelAtlases,
    rendererTables,
    rendererTablesMeta,
    rendererTablesPrecedence,
    rendererStateCommitMode,
    rendererPlayerId,
    rendererPlayerFacing,
    rendererFollowPlayer,
    rendererKeyboardMotion,
    rendererClickMove,
    rendererPathStepMs,
    rendererPlayerStep,
    rendererGravityEnabled,
    rendererGravityMs,
    rendererPlayerOffset,
    rendererTestSpecText,
    businessRendererInputMode,
    businessRendererInputText,
    businessRendererUseDerived,
    businessLogicRendererInputMode,
    businessLogicRendererInputText,
    businessLogicRendererUseDerived,
    rendererRealmId,
    validateBeforeEmit,
    strictBilingualValidation,
    lessonActorId,
    isFullscreenRenderer,
  ]);
  useEffect(() => {
    localStorage.setItem("atelier.renderer.pipeline", JSON.stringify(rendererPipeline));
  }, [rendererPipeline]);

  useEffect(() => {
    if (section !== "Business Logic") {
      return;
    }
    if (moduleCatalog.length > 0) {
      return;
    }
    void listModuleCatalog();
  }, [section, moduleCatalog.length]);

  useEffect(() => {
    if (section !== "Business Logic") {
      return;
    }
    if (!moduleSelectedId) {
      setModuleSelectedSpec(null);
      return;
    }
    void fetchSelectedModuleSpec();
  }, [section, moduleSelectedId]);

  useEffect(() => {
    if (isFullscreenRenderer) {
      return undefined;
    }
    const syncFromShared = () => {
      const shared = readRendererLocalState();
      const sharedOffset = shared && shared.playerOffset && typeof shared.playerOffset === "object"
        ? shared.playerOffset
        : { x: 0, y: 0, z: 0 };
      setRendererPlayerOffset((prev) => (closeVec3(prev, sharedOffset) ? prev : sharedOffset));
      const sharedFacing = normalizeFacing(shared && shared.playerFacing ? shared.playerFacing : "south");
      setRendererPlayerFacing((prev) => (normalizeFacing(prev) === sharedFacing ? prev : sharedFacing));
      const sharedSignal = readPlayerPositionSignal(shared.engine);
      if (sharedSignal) {
        setRendererEngineStateText((prevText) => mergePlayerSignalIntoEngineText(prevText, sharedSignal));
      }
    };
    syncFromShared();
    const handleStorage = (event) => {
      if (!event.key || !event.key.startsWith("atelier.renderer.")) {
        return;
      }
      syncFromShared();
    };
    window.addEventListener("storage", handleStorage);
    let channel = null;
    if (typeof BroadcastChannel !== "undefined") {
      try {
        channel = new BroadcastChannel(RENDERER_SYNC_CHANNEL);
        channel.onmessage = () => syncFromShared();
      } catch {
        channel = null;
      }
    }
    return () => {
      window.removeEventListener("storage", handleStorage);
      if (channel) {
        channel.close();
      }
    };
  }, [isFullscreenRenderer]);

  useEffect(() => {
    if (!isFullscreenRenderer) {
      return undefined;
    }
    const sync = () => setFullscreenState(readRendererLocalState());
    sync();
    const handleStorage = (event) => {
      if (!event.key || !event.key.startsWith("atelier.renderer.")) {
        return;
      }
      sync();
    };
    window.addEventListener("storage", handleStorage);
    let channel = null;
    if (typeof BroadcastChannel !== "undefined") {
      try {
        channel = new BroadcastChannel(RENDERER_SYNC_CHANNEL);
        channel.onmessage = () => sync();
      } catch {
        channel = null;
      }
    }
    const timer = window.setInterval(sync, 600);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.clearInterval(timer);
      if (channel) {
        channel.close();
      }
    };
  }, [isFullscreenRenderer]);

  useEffect(() => {
    if (!isFullscreenRenderer) {
      return undefined;
    }
    const canvas = fullscreenCanvasRef.current;
    if (!canvas) {
      return undefined;
    }
    drawVoxelScene(canvas, fullscreenMotionVoxels, fullscreenEffectiveSettings);
    const handleResize = () => drawVoxelScene(canvas, fullscreenMotionVoxels, fullscreenEffectiveSettings);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isFullscreenRenderer, fullscreenMotionVoxels, fullscreenEffectiveSettings]);

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
  const tileLodCounts = useMemo(() => {
    const counts = { "0": 0, "1": 0, "2": 0, "3": 0 };
    Object.values(tilePlacements).forEach((placement) => {
      const meta = placement && typeof placement.meta === "object" ? placement.meta : {};
      const lod = clampInt(meta.lod, 0, 3, 3);
      counts[String(lod)] = Number(counts[String(lod)] || 0) + 1;
    });
    return counts;
  }, [tilePlacements]);
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

  async function consumeRendererInput(mode) {
    const normalized = String(mode || "").toLowerCase();
    if (normalized === "python" || normalized === "javascript" || normalized === "cobra" || normalized === "json") {
      setRendererVisualSource(normalized);
      setRendererGameStatus(`renderer_source:${normalized}`);
      setNotice(`renderer_source:${normalized}`);
      if (normalized === "python") {
        if (hasDesktopFs() && studioFsRoot && window.atelierDesktop.fs && typeof window.atelierDesktop.fs.runPython === "function") {
          try {
            const result = await window.atelierDesktop.fs.runPython(studioFsRoot, rendererPython, {
              filename: "renderer_input.py",
              timeoutMs: 15000
            });
            if (!result || !result.ok) {
              setNotice(`renderer_python_exec_failed:${result && result.stderr ? result.stderr : "unknown"}`);
            } else if (result.stdout) {
              setNotice(`renderer_python_exec_ok:${result.stdout.split(/\r?\n/)[0] || "ok"}`);
            }
            const savedPath = extractPythonSavedPath(result && result.stdout ? result.stdout : "");
            if (savedPath) {
              const contentResult = await window.atelierDesktop.fs.readTextFile(studioFsRoot, savedPath);
              if (contentResult && contentResult.ok && typeof contentResult.content === "string") {
                setRendererJson(contentResult.content);
                setRendererVisualSource("json");
                setRendererGameStatus(`renderer_source:json:${savedPath}`);
                setNotice(`renderer_python_loaded:${savedPath}`);
                return;
              }
            }
          } catch (error) {
            setNotice(`renderer_python_exec_error:${error && error.message ? error.message : "unknown"}`);
          }
        }
        const parsed = parseRendererPayloadSync("python", rendererPython, rendererEffectiveEngineState);
        const hasPayload =
          parsed &&
          typeof parsed === "object" &&
          (Array.isArray(parsed.voxels) ||
            Array.isArray(parsed.nodes) ||
            (parsed.graph && Array.isArray(parsed.graph.nodes)) ||
            Array.isArray(parsed.entities));
        if (hasPayload) {
          return;
        }
        const hint = extractPythonFileHint(rendererPython);
        if (hint && hasDesktopFs() && studioFsRoot) {
          try {
            const result = await window.atelierDesktop.fs.readTextFile(studioFsRoot, hint);
            if (result && result.ok && typeof result.content === "string") {
              setRendererJson(result.content);
              setRendererVisualSource("json");
              setRendererGameStatus(`renderer_source:json:${hint}`);
              setNotice(`renderer_python_file:${hint}`);
              return;
            }
          } catch {
            // fall through to notice
          }
        }
        setNotice("renderer_python_empty: add #payload JSON or load a .scene.json file");
      }
      return;
    }
    setNotice(`renderer_source_unknown:${normalized || "unset"}`);
  }

  function loadBusinessArchitectureTemplate() {
    setBusinessRendererUseDerived(false);
    setBusinessRendererInputMode("json");
    setBusinessRendererInputText(BUSINESS_ARCHITECTURE_TEMPLATE);
    setBusinessRendererStatus("ready");
  }

  function snapshotDerivedArchitectureToInput() {
    setBusinessRendererUseDerived(false);
    setBusinessRendererInputMode("json");
    setBusinessRendererInputText(JSON.stringify(derivedBusinessArchitectureSpec, null, 2));
    setBusinessRendererStatus("ready");
  }

  function loadBusinessLogicArchitectureTemplate() {
    setBusinessLogicRendererUseDerived(false);
    setBusinessLogicRendererInputMode("json");
    setBusinessLogicRendererInputText(BUSINESS_ARCHITECTURE_TEMPLATE);
    setBusinessLogicRendererStatus("ready");
  }

  function snapshotDerivedArchitectureToBusinessLogicInput() {
    setBusinessLogicRendererUseDerived(false);
    setBusinessLogicRendererInputMode("json");
    setBusinessLogicRendererInputText(JSON.stringify(derivedBusinessArchitectureSpec, null, 2));
    setBusinessLogicRendererStatus("ready");
  }

  function applyBusinessLogicCobraToUnifiedRenderer() {
    const mode = String(businessLogicRendererInputMode || "").toLowerCase();
    if (mode !== "cobra") {
      setBusinessLogicRendererStatus("error: switch input mode to Cobra first");
      return;
    }
    const cobraSource = businessLogicRendererInputText || "";
    const parsedCobra = parseCobraShygazunScript(cobraSource);
    if (Array.isArray(parsedCobra.entities) && parsedCobra.entities.length > 0) {
      setRendererCobra(cobraSource);
      setRendererVisualSource("cobra");
      setBusinessLogicRendererStatus("ready");
    } else {
      const architectureSpec = parseArchitectureInput("cobra", cobraSource);
      const architectureModel = normalizeArchitectureSpec(architectureSpec);
      const voxels = architectureModelToVoxels(architectureModel);
      setRendererJson(JSON.stringify({ voxels }, null, 2));
      setRendererVisualSource("json");
      setBusinessLogicRendererStatus(`ready: mapped architecture to ${voxels.length} voxel nodes`);
    }
    setSection("Renderer Lab");
  }

  function appendSceneKitId(currentText, nextId) {
    const parts = parseKitIdSequence(currentText);
    if (nextId && !parts.includes(nextId)) {
      parts.push(nextId);
    }
    return parts.join("\n");
  }

  function composeSceneKitToGameSpec() {
    const roomIds = parseKitIdSequence(sceneKitRoomIdsText);
    const chunkIds = parseKitIdSequence(sceneKitChunkIdsText);
    const featureIds = parseKitIdSequence(sceneKitFeatureIdsText);
    const composed = composeSceneKitSpec({
      scene_shell_id: sceneKitShellId,
      room_ids: roomIds,
      chunk_ids: chunkIds,
      feature_ids: featureIds,
    });
    setSceneKitOutput(composed);
    setRendererGameSpecText(JSON.stringify(composed, null, 2));
    setRendererGameStatus(
      `scene_kit_composed:${composed.stats.room_count}r:${composed.stats.chunk_count}c:${composed.stats.feature_count}f:${composed.stats.entity_count}e`
    );
    setNotice(`scene_kit_composed:${composed.scene.id || sceneKitShellId}`);
  }

  function compileGameSpecToRenderer() {
    const spec = parseObjectJson(rendererGameSpecText, {});
    const scene = spec.scene && typeof spec.scene === "object" ? spec.scene : {};
    const systems = spec.systems && typeof spec.systems === "object" ? spec.systems : {};
    const entities = Array.isArray(spec.entities) ? spec.entities : [];
    const passthrough = Object.fromEntries(
      Object.entries(spec).filter(([key]) => !["scene", "systems", "entities"].includes(key))
    );
    const tileEntities = Object.values(tilePlacements).map((placement) => tilePlacementToRendererVoxelEntity(placement));
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
    setRendererJson(JSON.stringify({ ...passthrough, scene, systems: systemsNext, entities: mergedEntities }, null, 2));
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

  function tileLodSpan(levelRaw) {
    const lod = clampInt(levelRaw, 0, 3, 3);
    return Math.max(1, Math.pow(2, 3 - lod));
  }

  function retagAllTilesLod(levelRaw) {
    const lod = clampInt(levelRaw, 0, 3, 3);
    setTilePlacements((prev) => {
      const next = {};
      for (const [key, placement] of Object.entries(prev)) {
        const meta = placement && typeof placement.meta === "object" ? placement.meta : {};
        next[key] = { ...placement, meta: { ...meta, lod } };
      }
      return next;
    });
    setRendererGameStatus(`lod_retag_all:${lod}`);
  }

  function normalizeTileRect(start, end) {
    if (!start || !end) {
      return null;
    }
    const minX = Math.min(start.x, end.x);
    const maxX = Math.max(start.x, end.x);
    const minY = Math.min(start.y, end.y);
    const maxY = Math.max(start.y, end.y);
    return { minX, maxX, minY, maxY };
  }

  function tilePointInRect(x, y, rect) {
    if (!rect) {
      return false;
    }
    return x >= rect.minX && x <= rect.maxX && y >= rect.minY && y <= rect.maxY;
  }

  function collectBrushCenters(cx, cy, cols, rows) {
    const radius = clampInt(tileBrushRadius, 0, 16, 0);
    const shape = String(tileBrushShape || "square");
    const points = [];
    for (let dy = -radius; dy <= radius; dy += 1) {
      for (let dx = -radius; dx <= radius; dx += 1) {
        if (shape === "circle" && dx * dx + dy * dy > radius * radius) {
          continue;
        }
        const x = cx + dx;
        const y = cy + dy;
        if (x < 0 || y < 0 || x >= cols || y >= rows) {
          continue;
        }
        points.push({ x, y });
      }
    }
    if (points.length === 0) {
      points.push({ x: cx, y: cy });
    }
    return points;
  }

  function applyRectLod(levelRaw, options = {}) {
    const rect = normalizeTileRect(tileRectStart, tileRectEnd);
    if (!rect) {
      setNotice("rect_lod: select rectangle first");
      return;
    }
    const lod = clampInt(levelRaw, 0, 3, 3);
    const feather = Boolean(options.feather);
    const scale = clampInt(tileSvgExportScale, 1, 8, 2);
    const featherBands = Math.max(1, scale);
    const maxDrop = Math.min(2, lod);
    setTilePlacements((prev) => {
      const next = {};
      for (const [key, placement] of Object.entries(prev)) {
        if (!placement || typeof placement !== "object") {
          continue;
        }
        if (String(placement.layer || "base") !== tileActiveLayer) {
          next[key] = placement;
          continue;
        }
        const x = clampInt(placement.x, 0, 100000, 0);
        const y = clampInt(placement.y, 0, 100000, 0);
        if (!tilePointInRect(x, y, rect)) {
          next[key] = placement;
          continue;
        }
        let appliedLod = lod;
        if (feather) {
          const distToEdge = Math.min(
            x - rect.minX,
            rect.maxX - x,
            y - rect.minY,
            rect.maxY - y
          );
          const band = Math.max(0, Math.min(featherBands, distToEdge));
          const ratio = featherBands <= 0 ? 1 : band / featherBands;
          const drop = Math.round((1 - ratio) * maxDrop);
          appliedLod = clampInt(lod - drop, 0, 3, lod);
        }
        const meta = placement.meta && typeof placement.meta === "object" ? placement.meta : {};
        next[key] = { ...placement, meta: { ...meta, lod: appliedLod } };
      }
      return next;
    });
    setRendererGameStatus(
      feather
        ? `lod_rect_feather:${lod}:scale${scale}:${rect.minX},${rect.minY}-${rect.maxX},${rect.maxY}`
        : `lod_rect:${lod}:${rect.minX},${rect.minY}-${rect.maxX},${rect.maxY}`
    );
  }

  function paintTile(x, y) {
    const lod = clampInt(tileEditLodLevel, 0, 3, 3);
    const span = tileEditLodSnap ? tileLodSpan(lod) : 1;
    const cols = clampInt(tileCols, 1, 256, 48);
    const rows = clampInt(tileRows, 1, 256, 27);
    const brushCenters = collectBrushCenters(x, y, cols, rows).map((point) => ({
      x: tileEditLodSnap ? Math.floor(point.x / span) * span : point.x,
      y: tileEditLodSnap ? Math.floor(point.y / span) * span : point.y,
    }));
    if (tilePresenceToken === "Zo") {
      setTilePlacements((prev) => {
        const next = { ...prev };
        for (const center of brushCenters) {
          for (let dy = 0; dy < span; dy += 1) {
            for (let dx = 0; dx < span; dx += 1) {
              const px = center.x + dx;
              const py = center.y + dy;
              if (px < 0 || py < 0 || px >= cols || py >= rows) {
                continue;
              }
              delete next[tileKey(px, py, tileActiveLayer)];
            }
          }
        }
        return next;
      });
      setRendererGameStatus(`tile_removed:lod${lod}:span${span}:brush${tileBrushRadius}`);
      return;
    }
    setTilePlacements((prev) => {
      const next = { ...prev };
      for (const center of brushCenters) {
        for (let dy = 0; dy < span; dy += 1) {
          for (let dx = 0; dx < span; dx += 1) {
            const px = center.x + dx;
            const py = center.y + dy;
            if (px < 0 || py < 0 || px >= cols || py >= rows) {
              continue;
            }
            const key = tileKey(px, py, tileActiveLayer);
            const existing = next[key];
            const existingMeta = existing && typeof existing.meta === "object" ? existing.meta : {};
            next[key] = {
              id: `tile_${tileActiveLayer}_${px}_${py}`,
              x: px,
              y: py,
              layer: tileActiveLayer,
              presence_token: "Ta",
              color_token: tileColorToken,
              opacity_token: tileOpacityToken,
              meta: tileTraversalMeta({
                ...existingMeta,
                lod,
              }),
            };
          }
        }
      }
      return next;
    });
    setRendererGameStatus(`tile_painted:lod${lod}:span${span}:brush${tileBrushRadius}`);
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
    if (tileRectSelectMode) {
      if (!tileRectStart || (tileRectStart && tileRectEnd)) {
        setTileRectStart({ x, y });
        setTileRectEnd(null);
      } else {
        setTileRectEnd({ x, y });
      }
      return;
    }
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

  const openFullscreenRenderer = async () => {
    if (window.atelierDesktop && window.atelierDesktop.renderer && typeof window.atelierDesktop.renderer.openWindow === "function") {
      try {
        await window.atelierDesktop.renderer.openWindow();
        return;
      } catch {
        // fall through to browser fallback
      }
    }
    const url = new URL(window.location.href);
    url.searchParams.set("view", "renderer-full");
    const popup = window.open(url.toString(), "atelier-renderer-full", "noopener,noreferrer");
    if (!popup) {
      setNotice("fullscreen_popup_blocked");
    }
  };
  const getStudioFileById = (fileId) => studioFiles.find((file) => file.id === fileId);
  const worldRegionPipelineRealmId = String(rendererPipeline.worldRegionRealmId || rendererRealmId || "lapidus").trim() || "lapidus";
  const worldRegionPipelineKey = String(rendererPipeline.worldRegionKey || "").trim();

  const resolveWorldRegionPayload = () => {
    const payloadFileId = String(rendererPipeline.worldRegionPayloadFileId || "").trim();
    if (!payloadFileId) {
      return {};
    }
    const payloadFile = getStudioFileById(payloadFileId);
    if (!payloadFile || typeof payloadFile.content !== "string") {
      return {};
    }
    const parsed = parseObjectJson(payloadFile.content, {});
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
    return {};
  };

  const resolveRuntimeSceneContent = () => {
    const parsed = parseObjectJson(rendererJson || "{}", {});
    if (parsed && typeof parsed === "object" && Array.isArray(parsed.nodes)) {
      return {
        nodes: parsed.nodes,
        edges: Array.isArray(parsed.edges) ? parsed.edges : [],
      };
    }
    const voxels = Array.isArray(parsed.voxels) ? parsed.voxels : [];
    if (voxels.length > 0) {
      const nodes = voxels.map((item, index) => {
        const entry = item && typeof item === "object" ? item : {};
        return {
          node_id: String(entry.id || entry.type || `voxel_${index}`),
          kind: String(entry.type || "voxel"),
          x: Number(entry.x || 0),
          y: Number(entry.y || 0),
          metadata: { z: Number(entry.z || 0) },
        };
      });
      return { nodes, edges: [] };
    }
    return { nodes: [], edges: [] };
  };

  const runtimeRegionActorId = String(rendererTablesActorId || "player").trim() || "player";
  const runtimeRegionSceneId =
    `${worldRegionPipelineRealmId}/renderer-lab`;

  const buildCanonicalMainPlanPayload = () => {
    const scenes = [
      { scene_id: "lapidus/home_morning", clock_advance: 15 },
      { scene_id: "lapidus/street_commute", clock_advance: 20 },
      { scene_id: "lapidus/market_midday", clock_advance: 40 },
      { scene_id: "lapidus/castle_evening", clock_advance: 45 },
      { scene_id: "lapidus/night_return", clock_advance: 20 },
    ];
    const overlaysByScene = {
      all: [
        {
          action_id: "day_{{DAY}}_scene_{{SCENE_SLUG}}_heartbeat",
          kind: "world.stream.status",
          payload: {},
        },
      ],
      "lapidus/market_midday": [
        {
          action_id: "day_{{DAY}}_scene_{{SCENE_SLUG}}_lapidus_shift",
          kind: "world.market.stock.adjust",
          payload: { realm_id: "lapidus", item_id: "iron_ingot", delta: 1 },
        },
        {
          action_id: "day_{{DAY}}_scene_{{SCENE_SLUG}}_mercurie_supply",
          kind: "world.market.stock.adjust",
          payload: { realm_id: "mercurie", item_id: "moon_salt", delta: 2 },
        },
      ],
      "lapidus/night_return": [
        {
          action_id: "day_{{DAY}}_scene_{{SCENE_SLUG}}_sulphera_flux",
          kind: "world.market.stock.adjust",
          payload: { realm_id: "sulphera", item_id: "infernal_ash", delta: 1 },
        },
      ],
    };
    const handQuestActions = [
      {
        action_id: "bootstrap_fate_knocks",
        kind: "quest.fate_knocks.bootstrap",
        payload: {
          player_name: "Kael",
          player_gender: "nonbinary",
          month: "Shyalz",
          deadline_hour_local: 19,
          quiz_points_budget: 28,
          quiz_answers: [4, 4, 4, 4, 4, 4, 4],
        },
      },
      { action_id: "hour_08_check", kind: "quest.fate_knocks.deadline_check", payload: { current_hour_local: 8 } },
      { action_id: "hour_12_check", kind: "quest.fate_knocks.deadline_check", payload: { current_hour_local: 12 } },
      { action_id: "hour_18_check", kind: "quest.fate_knocks.deadline_check", payload: { current_hour_local: 18 } },
      { action_id: "hour_20_check", kind: "quest.fate_knocks.deadline_check", payload: { current_hour_local: 20 } },
    ];
    const day = 1;
    const dayTag = String(day).padStart(2, "0");
    const sceneActions = [];
    sceneActions.push({
      action_id: `day_${dayTag}_stream_status_open`,
      kind: "world.stream.status",
      payload: {},
    });
    scenes.forEach((scene, index) => {
      const sceneIndex = index + 1;
      const sceneTag = String(sceneIndex).padStart(2, "0");
      const sceneId = String(scene.scene_id || "");
      const sceneSlug = sceneId.replace(/[\/\s]+/g, "_");
      const realmId = sceneId.includes("/") ? sceneId.split("/", 1)[0] : "lapidus";
      const scenePayload = { realm_id: realmId, scene_id: sceneId, nodes: [] };
      sceneActions.push({
        action_id: `day_${dayTag}_scene_${sceneTag}_${sceneSlug}_load`,
        kind: "render.scene.load",
        payload: {
          realm_id: realmId,
          scene_id: sceneId,
          scene_content: scenePayload,
        },
      });
      sceneActions.push({
        action_id: `day_${dayTag}_scene_${sceneTag}_${sceneSlug}_clock`,
        kind: "render.scene.tick",
        payload: {
          dt: Number(scene.clock_advance || 0),
          updates: [],
          enqueue_pygame: false,
          day_index: day,
          scene_index: sceneIndex,
          scene_id: sceneId,
          clock_advance: Number(scene.clock_advance || 0),
        },
      });
      const overlays = [
        ...(Array.isArray(overlaysByScene.all) ? overlaysByScene.all : []),
        ...(Array.isArray(overlaysByScene[sceneId]) ? overlaysByScene[sceneId] : []),
      ];
      overlays.forEach((overlay, overlayIndex) => {
        const overlayIdRaw = String(overlay.action_id || "").trim();
        const overlayId =
          overlayIdRaw.replaceAll("{{DAY}}", dayTag).replaceAll("{{SCENE_SLUG}}", sceneSlug) ||
          `day_${dayTag}_scene_${sceneTag}_overlay_${String(overlayIndex + 1).padStart(2, "0")}`;
        sceneActions.push({
          action_id: overlayId,
          kind: String(overlay.kind || ""),
          payload: {
            ...(overlay.payload && typeof overlay.payload === "object" ? overlay.payload : {}),
            day_index: day,
            scene_index: sceneIndex,
            scene_id: sceneId,
          },
        });
      });
      sceneActions.push({
        action_id: `day_${dayTag}_scene_${sceneTag}_${sceneSlug}_reconcile`,
        kind: "render.scene.reconcile",
        payload: {
          apply: true,
          realm_id: realmId,
          scene_id: sceneId,
          scene_content: scenePayload,
        },
      });
    });
    sceneActions.push({
      action_id: `day_${dayTag}_markets_close`,
      kind: "world.markets.list",
      payload: {},
    });
    return {
      workspace_id: workspaceId,
      actor_id: runtimeRegionActorId,
      plan_id: `day_scene_plan_main_ui_${Date.now()}`,
      meta: {
        profile: "main",
        source: "renderer_lab_ui",
        day_progression_metric: "scene",
        days: 1,
      },
      actions: [
        { action_id: "seed_byte_table", kind: "content.pack.load_byte_table", payload: {} },
        { action_id: "seed_canon_pack", kind: "content.pack.load_canon", payload: { apply_to_db: true } },
        ...sceneActions,
        ...handQuestActions,
      ],
    };
  };

  const runCanonicalMainPlanFromUi = async () => {
    await runAction("runtime_plan_main_ui", async () => {
      const payload = buildCanonicalMainPlanPayload();
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", payload);
      const results = Array.isArray(consumed?.results) ? consumed.results : [];
      const failures = results.filter((item) => !item || !item.ok);
      setModuleRunOutput({
        runtime_plan: "day_scene_plan_main",
        source: "renderer_lab_ui",
        consumed,
      });
      if (failures.length > 0) {
        setRendererGameStatus(`plan_main_failed:${failures.length}/${results.length}`);
        setLabCoherence((prev) => ({
          ...prev,
          last_check_at: new Date().toISOString(),
          runtime_consume_ok: true,
          main_plan_ok: false,
        }));
      } else {
        setRendererGameStatus(`plan_main_ok:${results.length}`);
        setLabCoherence((prev) => ({
          ...prev,
          last_check_at: new Date().toISOString(),
          runtime_consume_ok: true,
          main_plan_ok: true,
        }));
      }
      return consumed;
    });
  };

  const runStudioHealthCheck = async () => {
    await runAction("studio_health_check", async () => {
      const checks = [];
      const safeCheck = async (id, fn) => {
        try {
          const result = await fn();
          checks.push({ id, ok: true, result });
        } catch (error) {
          checks.push({ id, ok: false, error: error instanceof Error ? error.message : String(error) });
        }
      };
      await safeCheck("runtime_consume_smoke", async () =>
        apiCall("/v1/game/runtime/consume", "POST", {
          workspace_id: workspaceId,
          actor_id: runtimeRegionActorId,
          plan_id: `studio_health_${Date.now()}`,
          actions: [{ action_id: "stream_status", kind: "world.stream.status", payload: {} }],
        })
      );
      await safeCheck("module_catalog", async () => apiCall("/v1/game/modules", "GET", null));
      await safeCheck("world_stream_status", async () => requestWorldStreamStatus());
      const report = {
        at: new Date().toISOString(),
        workspace_id: workspaceId,
        checks,
      };
      const byId = {};
      checks.forEach((check) => {
        byId[String(check.id || "")] = Boolean(check.ok);
      });
      setLabCoherence((prev) => ({
        ...prev,
        last_check_at: report.at,
        runtime_consume_ok: byId.runtime_consume_smoke === true,
        module_catalog_ok: byId.module_catalog === true,
        world_stream_ok: byId.world_stream_status === true,
      }));
      setModuleRunOutput({ studio_health: report });
      const failed = checks.filter((item) => !item.ok).length;
      setRendererGameStatus(failed > 0 ? `studio_health_failed:${failed}/${checks.length}` : `studio_health_ok:${checks.length}`);
      return report;
    });
  };

  const runRendererGateASmoke = async () => {
    await runAction("renderer_gate_a_smoke", async () => {
      const fullscreenMaterials = Array.isArray(fullscreenState.materials) ? fullscreenState.materials : [];
      const result = {
        gate: "A",
        scene_coherence: {
          main_voxel_count: rendererMotionVoxels.length,
          fullscreen_voxel_count: fullscreenMotionVoxels.length,
          voxel_count_match: rendererMotionVoxels.length === fullscreenMotionVoxels.length,
          main_material_count: voxelMaterials.length,
          fullscreen_material_count: fullscreenMaterials.length,
          material_count_match: voxelMaterials.length === fullscreenMaterials.length,
          camera_seed_match: cameraSeedsMatch(voxelSettings, fullscreenState.settings),
        },
      };
      const ok =
        result.scene_coherence.voxel_count_match &&
        result.scene_coherence.material_count_match &&
        result.scene_coherence.camera_seed_match;
      setLabCoherence((prev) => ({
        ...prev,
        last_check_at: new Date().toISOString(),
        gate_a_ok: ok,
      }));
      setModuleRunOutput({ renderer_gate_a: { ok, ...result } });
      setRendererGameStatus(ok ? "gate_a_pass" : "gate_a_fail");
      return { ok, ...result };
    });
  };

  const runRendererGateDSmoke = async () => {
    await runAction("renderer_gate_d_smoke", async () => {
      const activeOffset = isFullscreenRenderer
        ? (fullscreenState.playerOffset && typeof fullscreenState.playerOffset === "object" ? fullscreenState.playerOffset : { x: 0, y: 0, z: 0 })
        : rendererPlayerOffset;
      const shared = readRendererLocalState();
      const sharedOffset = shared && shared.playerOffset && typeof shared.playerOffset === "object"
        ? shared.playerOffset
        : { x: 0, y: 0, z: 0 };
      const mainSignal = readPlayerPositionSignal(rendererEngineState);
      const sharedSignal = readPlayerPositionSignal(shared.engine);
      const result = {
        gate: "D",
        motion_integrity: {
          active_offset: activeOffset,
          shared_offset: sharedOffset,
          offset_match: closeVec3(activeOffset, sharedOffset),
          main_signal_present: Boolean(mainSignal),
          shared_signal_present: Boolean(sharedSignal),
          signal_offset_match: mainSignal ? closeVec3(mainSignal, sharedOffset) : false,
        },
      };
      const ok =
        result.motion_integrity.offset_match &&
        result.motion_integrity.shared_signal_present &&
        (result.motion_integrity.main_signal_present ? result.motion_integrity.signal_offset_match : true);
      setLabCoherence((prev) => ({
        ...prev,
        last_check_at: new Date().toISOString(),
        gate_d_ok: ok,
      }));
      setModuleRunOutput({ renderer_gate_d: { ok, ...result } });
      setRendererGameStatus(ok ? "gate_d_pass" : "gate_d_fail");
      return { ok, ...result };
    });
  };

  const runGuidedLabBootstrap = async () => {
    await runAction("lab_guided_bootstrap", async () => {
      const health = await (async () => {
        const checks = [];
        const safeCheck = async (id, fn) => {
          try {
            await fn();
            checks.push({ id, ok: true });
          } catch (error) {
            checks.push({ id, ok: false, error: error instanceof Error ? error.message : String(error) });
          }
        };
        await safeCheck("runtime_consume_smoke", async () =>
          apiCall("/v1/game/runtime/consume", "POST", {
            workspace_id: workspaceId,
            actor_id: runtimeRegionActorId,
            plan_id: `studio_health_${Date.now()}`,
            actions: [{ action_id: "stream_status", kind: "world.stream.status", payload: {} }],
          })
        );
        await safeCheck("module_catalog", async () => apiCall("/v1/game/modules", "GET", null));
        await safeCheck("world_stream_status", async () => requestWorldStreamStatus());
        return checks;
      })();
      const failed = health.filter((item) => !item.ok).length;
      if (failed > 0) {
        setLabCoherence((prev) => ({
          ...prev,
          last_check_at: new Date().toISOString(),
          runtime_consume_ok: health.some((it) => it.id === "runtime_consume_smoke" && it.ok),
          module_catalog_ok: health.some((it) => it.id === "module_catalog" && it.ok),
          world_stream_ok: health.some((it) => it.id === "world_stream_status" && it.ok),
          guided_bootstrap_ok: false,
        }));
        setModuleRunOutput({ lab_bootstrap: { ok: false, stage: "health", checks: health } });
        throw new Error(`health_checks_failed:${failed}`);
      }

      const payload = buildCanonicalMainPlanPayload();
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", payload);
      const results = Array.isArray(consumed?.results) ? consumed.results : [];
      const planFailed = results.some((item) => !item || !item.ok);
      if (planFailed) {
        setLabCoherence((prev) => ({
          ...prev,
          last_check_at: new Date().toISOString(),
          runtime_consume_ok: true,
          main_plan_ok: false,
          guided_bootstrap_ok: false,
        }));
        setModuleRunOutput({ lab_bootstrap: { ok: false, stage: "main_plan", consumed } });
        throw new Error("main_plan_failed");
      }

      const graph = await apiCall("/v1/game/renderer/render-graph", "POST", {
        workspace_id: workspaceId,
        realm_id: rendererRealmId,
        scene_id: `${rendererRealmId}/renderer-lab`,
        render_mode: normalizeRenderMode(voxelSettings.renderMode),
        include_unloaded_regions: true,
        include_material_constraints: true,
      });
      setRendererGraphPreview(
        graph && Array.isArray(graph.nodes)
          ? { nodes: graph.nodes, edges: [] }
          : graph && typeof graph.graph === "object"
            ? graph.graph
            : graph
      );
      setLabCoherence((prev) => ({
        ...prev,
        last_check_at: new Date().toISOString(),
        runtime_consume_ok: true,
        module_catalog_ok: true,
        world_stream_ok: true,
        main_plan_ok: true,
        guided_bootstrap_ok: true,
      }));
      setModuleRunOutput({
        lab_bootstrap: {
          ok: true,
          consumed_action_count: results.length,
          renderer_graph_ready: true,
        },
      });
      setRendererGameStatus(`bootstrap_ok:${results.length}`);
      return { consumed, graph };
    });
  };

  const mergeLoadedWorldRegionIntoEngineText = (engineText, region) => {
    const stateObj = parseObjectJson(engineText || "{}", {});
    const worldStream = stateObj.world_stream && typeof stateObj.world_stream === "object" ? { ...stateObj.world_stream } : {};
    const loaded = worldStream.loaded_regions && typeof worldStream.loaded_regions === "object" ? { ...worldStream.loaded_regions } : {};
    const regionRealm = String(region && region.realm_id ? region.realm_id : worldRegionPipelineRealmId);
    const regionKey = String(region && region.region_key ? region.region_key : worldRegionPipelineKey);
    const loadedKey = `${regionRealm}:${regionKey}`;
    loaded[loadedKey] = {
      id: region && region.id ? region.id : null,
      realm_id: regionRealm,
      region_key: regionKey,
      payload: region && region.payload && typeof region.payload === "object" ? region.payload : {},
      payload_hash: region && region.payload_hash ? region.payload_hash : "",
      cache_policy: region && region.cache_policy ? region.cache_policy : rendererPipeline.worldRegionCachePolicy || "cache",
      loaded: true,
      updated_at: region && region.updated_at ? region.updated_at : new Date().toISOString()
    };
    worldStream.loaded_regions = loaded;
    worldStream.loaded_count = Object.keys(loaded).length;
    worldStream.last_loaded = loadedKey;
    const merged = { ...stateObj, world_stream: worldStream };
    return JSON.stringify(merged, null, 2);
  };

  const mergeUnloadedWorldRegionIntoEngineText = (engineText, realmId, regionKey) => {
    const stateObj = parseObjectJson(engineText || "{}", {});
    const worldStream = stateObj.world_stream && typeof stateObj.world_stream === "object" ? { ...stateObj.world_stream } : {};
    const loaded = worldStream.loaded_regions && typeof worldStream.loaded_regions === "object" ? { ...worldStream.loaded_regions } : {};
    const loadedKey = `${realmId}:${regionKey}`;
    if (loaded[loadedKey]) {
      delete loaded[loadedKey];
    }
    worldStream.loaded_regions = loaded;
    worldStream.loaded_count = Object.keys(loaded).length;
    worldStream.last_unloaded = loadedKey;
    const merged = { ...stateObj, world_stream: worldStream };
    return JSON.stringify(merged, null, 2);
  };

  const requestWorldRegionLoad = async () => {
    if (!worldRegionPipelineKey) {
      throw new Error("world_region_key_required");
    }
    const payload = resolveWorldRegionPayload();
    const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
      workspace_id: workspaceId,
      actor_id: runtimeRegionActorId,
      plan_id: `world_region_load_${Date.now()}`,
      actions: [
        {
          action_id: "world_region_load",
          kind: "world.region.load",
          payload: {
            realm_id: worldRegionPipelineRealmId,
            region_key: worldRegionPipelineKey,
            payload,
            cache_policy: String(rendererPipeline.worldRegionCachePolicy || "cache"),
            bind_render_scene: true,
            scene_id: runtimeRegionSceneId,
            scene_content: resolveRuntimeSceneContent(),
          },
        },
      ],
    });
    const actionResult = Array.isArray(consumed?.results)
      ? consumed.results.find((item) => item && item.action_id === "world_region_load")
      : null;
    if (!actionResult || !actionResult.ok) {
      throw new Error(
        actionResult && typeof actionResult.error === "string"
          ? actionResult.error
          : "world_region_load_failed"
      );
    }
    return actionResult.result || {};
  };

  const requestWorldRegionUnload = async () => {
    if (!worldRegionPipelineKey) {
      throw new Error("world_region_key_required");
    }
    const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
      workspace_id: workspaceId,
      actor_id: runtimeRegionActorId,
      plan_id: `world_region_unload_${Date.now()}`,
      actions: [
        {
          action_id: "world_region_unload",
          kind: "world.region.unload",
          payload: {
            realm_id: worldRegionPipelineRealmId,
            region_key: worldRegionPipelineKey,
            bind_render_scene: true,
            scene_id: runtimeRegionSceneId,
          },
        },
      ],
    });
    const actionResult = Array.isArray(consumed?.results)
      ? consumed.results.find((item) => item && item.action_id === "world_region_unload")
      : null;
    if (!actionResult || !actionResult.ok) {
      throw new Error(
        actionResult && typeof actionResult.error === "string"
          ? actionResult.error
          : "world_region_unload_failed"
      );
    }
    return actionResult.result || {};
  };

  const loadWorldRegionIntoEngine = async () => {
    await runAction("world_region_load", async () => {
      const data = await requestWorldRegionLoad();
      setWorldRegionLast(data);
      setRendererEngineStateText((prev) => mergeLoadedWorldRegionIntoEngineText(prev, data));
      const status = await requestWorldStreamStatus();
      setWorldStreamStatus(status && typeof status === "object" ? status : null);
      setRendererGameStatus(`world_loaded:${String(data.region_key || worldRegionPipelineKey)}`);
      return data;
    });
  };

  const unloadWorldRegionFromEngine = async () => {
    await runAction("world_region_unload", async () => {
      const data = await requestWorldRegionUnload();
      setWorldRegionLast(data);
      setRendererEngineStateText((prev) => mergeUnloadedWorldRegionIntoEngineText(prev, worldRegionPipelineRealmId, worldRegionPipelineKey));
      const status = await requestWorldStreamStatus();
      setWorldStreamStatus(status && typeof status === "object" ? status : null);
      setRendererGameStatus(`world_unloaded:${worldRegionPipelineKey}`);
      return data;
    });
  };

  const listWorldRegionsFromApi = async () => {
    await runAction("world_region_list", async () => {
      const path = `/v1/game/world/regions?workspace_id=${encodeURIComponent(workspaceId)}&realm_id=${encodeURIComponent(worldRegionPipelineRealmId)}`;
      const data = await apiCall(path, "GET", null);
      setWorldRegions(Array.isArray(data) ? data : []);
      const status = await requestWorldStreamStatus();
      setWorldStreamStatus(status && typeof status === "object" ? status : null);
      return data;
    });
  };

  const fetchWorldStreamStatus = async () => {
    await runAction("world_stream_status", async () => {
      const data = await requestWorldStreamStatus();
      setWorldStreamStatus(data && typeof data === "object" ? data : null);
      return data;
    });
  };

  const requestWorldStreamStatus = async () => {
    const path = `/v1/game/world/stream/status?workspace_id=${encodeURIComponent(workspaceId)}&realm_id=${encodeURIComponent(worldRegionPipelineRealmId)}`;
    return apiCall(path, "GET", null);
  };

  const runShygazunTranslate = async () => {
    await runAction("shygazun_translate", async () => {
      const sourceText = String(shygazunTranslateSourceText || "").trim();
      if (!sourceText) {
        throw new Error("source_text_required");
      }
      const direction = String(shygazunTranslateDirection || "auto");
      const actorId = String(rendererTablesActorId || "player").trim() || "player";
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: actorId,
        plan_id: `shygazun_translate_${Date.now()}`,
        actions: [
          {
            action_id: "translate",
            kind: "shygazun.translate",
            payload: {
              source_text: sourceText,
              direction,
            },
          },
        ],
      });
      const actionResult = Array.isArray(consumed?.results)
        ? consumed.results.find((item) => item && item.action_id === "translate")
        : null;
      if (!actionResult || !actionResult.ok) {
        throw new Error(
          actionResult && typeof actionResult.error === "string"
            ? actionResult.error
            : "shygazun_translate_failed"
        );
      }
      const runtimeResult = actionResult.result || {};
      setShygazunTranslateOutput(runtimeResult);
      return runtimeResult;
    });
  };

  const runShygazunInterpret = async () => {
    await runAction("shygazun_interpret", async () => {
      const utterance = String(shygazunTranslateSourceText || "").trim();
      if (!utterance) {
        throw new Error("utterance_required");
      }
      const actorId = String(rendererTablesActorId || "player").trim() || "player";
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: actorId,
        plan_id: `shygazun_interpret_${Date.now()}`,
        actions: [
          {
            action_id: "interpret",
            kind: "shygazun.interpret",
            payload: {
              utterance,
              deity: "jabiru",
              mode: "explicit",
              explain_mode: "none",
              lore_overlay: "none",
              mutate_tokens: true,
              kaganue_pressure: 0,
            },
          },
        ],
      });
      const actionResult = Array.isArray(consumed?.results)
        ? consumed.results.find((item) => item && item.action_id === "interpret")
        : null;
      if (!actionResult || !actionResult.ok) {
        throw new Error(
          actionResult && typeof actionResult.error === "string"
            ? actionResult.error
            : "shygazun_interpret_failed"
        );
      }
      const runtimeResult = actionResult.result || {};
      setShygazunInterpretOutput(runtimeResult);
      return runtimeResult;
    });
  };

  const validateWandDamageEvidence = async () => {
    await runAction("wand_damage_validate", async () => {
      if (!wandDamageFiles.length) {
        throw new Error("wand_damage_media_required");
      }
      const media = await buildWandDamageMediaDescriptors(wandDamageFiles);
      const data = await apiCall("/v1/security/wand-damage/validate", "POST", {
        wand_id: wandDamageWandId,
        notifier_id: wandDamageNotifierId,
        damage_state: wandDamageState,
        event_tag: wandDamageEventTag || null,
        media,
        payload: {
          source: "atelier.desktop.temple_garden",
          original_count: media.length,
        },
      });
      setWandDamageValidation(data);
      const digests = Array.isArray(data?.normalized_media)
        ? data.normalized_media.map((item) => String(item.sha256 || "")).filter((item) => item !== "")
        : [];
      if (Array.isArray(data?.normalized_media) && data.normalized_media.length) {
        setGuildAttestationSourcesText(JSON.stringify(data.normalized_media, null, 2));
      }
      if (digests.length) {
        setGuildAttestationDigestsText(digests.join(", "));
      }
      await fetchWandStatus(wandDamageWandId, setWandStatus);
      await fetchWandStatus(guildWandId, setGuildWandStatus);
      return data;
    });
  };

  const recordWandDamageEvidence = async () => {
    await runAction("wand_damage_record", async () => {
      if (!wandDamageFiles.length) {
        throw new Error("wand_damage_media_required");
      }
      const media = await buildWandDamageMediaDescriptors(wandDamageFiles);
      const data = await apiCall("/v1/security/wand-damage/record", "POST", {
        wand_id: wandDamageWandId,
        notifier_id: wandDamageNotifierId,
        damage_state: wandDamageState,
        event_tag: wandDamageEventTag || null,
        media,
        payload: {
          source: "atelier.desktop.temple_garden",
          original_count: media.length,
        },
      });
      setWandDamageRecord(data);
      if (data?.record_id) {
        setWandEpochPreviousId(String(data.record_id));
      }
      const digests = Array.isArray(data?.validation?.normalized_media)
        ? data.validation.normalized_media.map((item) => String(item.sha256 || "")).filter((item) => item !== "")
        : [];
      if (Array.isArray(data?.validation?.normalized_media) && data.validation.normalized_media.length) {
        setGuildAttestationSourcesText(JSON.stringify(data.validation.normalized_media, null, 2));
      }
      if (digests.length) {
        setGuildAttestationDigestsText(digests.join(", "));
      }
      return data;
    });
  };

  const loadWandDamageHistory = async () => {
    await runAction("wand_damage_history", async () => {
      const params = new URLSearchParams({
        wand_id: wandDamageWandId,
        limit: "20",
      });
      const data = await apiCall(`/v1/security/wand-damage/history?${params.toString()}`, "GET");
      setWandDamageHistory(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const loadWandEpochHistory = async () => {
    await runAction("wand_epoch_history", async () => {
      const params = new URLSearchParams({
        wand_id: wandDamageWandId,
        limit: "20",
      });
      const data = await apiCall(`/v1/security/wand/epochs?${params.toString()}`, "GET");
      setWandEpochHistory(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const fetchWandStatus = async (wandId, sink) => {
    const params = new URLSearchParams({ wand_id: String(wandId || "").trim() });
    const data = await apiCall(`/v1/security/wand/status?${params.toString()}`, "GET");
    sink(data);
    return data;
  };

  const loadWandStatus = async (wandId = wandDamageWandId, sink = setWandStatus) => {
    await runAction("wand_status", async () => fetchWandStatus(wandId, sink));
  };

  const transitionWandEpoch = async () => {
    await runAction("wand_epoch_transition", async () => {
      if (wandEpochRevoked && role !== "steward") {
        throw new Error("steward_required_for_revocation");
      }
      const attestationMediaDigests = String(guildAttestationDigestsText || "")
        .split(/[\s,|]+/)
        .map((item) => item.trim())
        .filter((item) => item !== "");
      const attestationRecordId =
        wandDamageRecord?.record_id ||
        wandEpochPreviousId;
      if (!attestationRecordId) {
        throw new Error("attestation_record_id_required");
      }
      const data = await apiCall("/v1/security/wand/epoch-transition", "POST", {
        wand_id: wandDamageWandId,
        attestation_record_id: attestationRecordId,
        notifier_id: wandDamageNotifierId,
        previous_epoch_id: wandEpochPreviousId || null,
        damage_state: wandDamageState,
        temple_entropy_digest: guildTempleEntropyDigest || null,
        theatre_entropy_digest: guildTheatreEntropyDigest || null,
        attestation_media_digests: attestationMediaDigests,
        revoked: wandEpochRevoked,
        metadata: {
          source: "atelier.desktop.temple_garden",
          event_tag: wandDamageEventTag || null,
        },
      });
      setWandEpochOutput(data);
      setWandEpochPreviousId(String(data?.epoch_id || ""));
      await fetchWandStatus(wandDamageWandId, setWandStatus);
      await fetchWandStatus(guildWandId, setGuildWandStatus);
      return data;
    });
  };

  const deriveGuildEntropyMix = async () => {
    await runAction("guild_entropy_mix", async () => {
      const attestationMediaDigests = String(guildAttestationDigestsText || "")
        .split(/[\s,|]+/)
        .map((item) => item.trim())
        .filter((item) => item !== "");
      const templeEntropySource = buildTempleEntropySourcePayload();
      const theatreEntropySource = buildTheatreEntropySourcePayload();
      const attestationSources = guildAttestationSourcesText.trim() ? JSON.parse(guildAttestationSourcesText) : [];
      rememberProvenanceId("temple", templeEntropySource.provenance_id);
      rememberProvenanceId("theatre", theatreEntropySource.provenance_id);
      const data = await apiCall("/v1/security/entropy/mix", "POST", {
        wand_id: guildWandId,
        wand_passkey_ward: guildWandPasskeyWard || null,
        temple_entropy_digest: guildTempleEntropyDigest || null,
        theatre_entropy_digest: guildTheatreEntropyDigest || null,
        attestation_media_digests: attestationMediaDigests,
        temple_entropy_source: templeEntropySource,
        theatre_entropy_source: theatreEntropySource,
        attestation_sources: Array.isArray(attestationSources) ? attestationSources : [],
        context: {
          guild_id: guildId,
          channel_id: guildChannelId,
          thread_id: guildThreadId || null,
          sender_id: guildSenderId,
          sender_member_id: guildSenderId || activeProfileMemberId,
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
          profile: activeProfilePayload,
        },
      });
      setGuildEntropyMixOutput(data);
      return data;
    });
  };

  const encryptGuildMessage = async () => {
    await runAction("guild_message_encrypt", async () => {
      const attestationMediaDigests = String(guildAttestationDigestsText || "")
        .split(/[\s,|]+/)
        .map((item) => item.trim())
        .filter((item) => item !== "");
      const templeEntropySource = buildTempleEntropySourcePayload();
      const theatreEntropySource = buildTheatreEntropySourcePayload();
      const attestationSources = guildAttestationSourcesText.trim() ? JSON.parse(guildAttestationSourcesText) : [];
      const participantMemberIds = (() => {
        try {
          const parsed = JSON.parse(guildParticipantMemberIdsText || "[]");
          return Array.isArray(parsed) ? parsed.map((item) => String(item || "").trim()).filter(Boolean) : [];
        } catch {
          return [];
        }
      })();
      const securitySession = parseObjectJson(guildSecuritySessionText, {});
      const senderMemberId = participantMemberIds[0] || guildSenderId || activeProfileMemberId || null;
      const recipientMemberId = guildRecipientActorId || participantMemberIds[1] || null;
      const currentStatus = guildWandStatus?.wand_id === guildWandId ? guildWandStatus : await fetchWandStatus(guildWandId, setGuildWandStatus);
      if (currentStatus?.revoked) {
        throw new Error("wand_revoked");
      }
      rememberProvenanceId("temple", templeEntropySource.provenance_id);
      rememberProvenanceId("theatre", theatreEntropySource.provenance_id);
      const data = await apiCall("/v1/guild/messages/encrypt", "POST", {
        guild_id: guildId,
        channel_id: guildChannelId,
        thread_id: guildThreadId || null,
        sender_id: guildSenderId,
        wand_id: guildWandId,
        wand_passkey_ward: guildWandPasskeyWard || null,
        message_text: messageDraft,
        conversation_id: guildConversationId || null,
        conversation_kind: guildConversationKind || "guild_channel",
        sender_member_id: senderMemberId,
        recipient_member_id: recipientMemberId,
        recipient_distribution_id: guildRecipientDistributionId || null,
        recipient_guild_id: guildRecipientGuildId || null,
        recipient_channel_id: guildRecipientChannelId || null,
        recipient_actor_id: guildRecipientActorId || null,
        temple_entropy_digest: guildTempleEntropyDigest || null,
        theatre_entropy_digest: guildTheatreEntropyDigest || null,
        attestation_media_digests: attestationMediaDigests,
        temple_entropy_source: templeEntropySource,
        theatre_entropy_source: theatreEntropySource,
        attestation_sources: Array.isArray(attestationSources) ? attestationSources : [],
        security_session: securitySession,
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
          profile: activeProfilePayload,
          sender_member_id: senderMemberId,
          recipient_member_id: recipientMemberId,
        },
      });
      setGuildEncryptOutput(data);
      const persisted = await apiCall("/v1/guild/messages/persist", "POST", {
        envelope: data,
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
          profile: activeProfilePayload,
        },
      });
      setGuildPersistOutput(persisted);
      setMessageLog((prev) =>
        [
          {
            section: "Messages",
            guild_id: guildId,
            channel_id: guildChannelId,
            thread_id: guildThreadId || null,
            sender_id: guildSenderId,
            sender_member_id: senderMemberId,
            profile: activeProfilePayload,
            at: new Date().toISOString(),
            envelope: data,
            persisted,
          },
          ...prev,
        ].slice(0, 40)
      );
      return data;
    });
  };

  const decryptGuildMessage = async () => {
    await runAction("guild_message_decrypt", async () => {
      if (!guildEncryptOutput || typeof guildEncryptOutput !== "object") {
        throw new Error("guild_envelope_required");
      }
      const attestationMediaDigests = String(guildAttestationDigestsText || "")
        .split(/[\s,|]+/)
        .map((item) => item.trim())
        .filter((item) => item !== "");
      const templeEntropySource = buildTempleEntropySourcePayload();
      const theatreEntropySource = buildTheatreEntropySourcePayload();
      const attestationSources = guildAttestationSourcesText.trim() ? JSON.parse(guildAttestationSourcesText) : [];
      rememberProvenanceId("temple", templeEntropySource.provenance_id);
      rememberProvenanceId("theatre", theatreEntropySource.provenance_id);
      const data = await apiCall("/v1/guild/messages/decrypt", "POST", {
        envelope: guildEncryptOutput,
        wand_id: guildWandId,
        wand_passkey_ward: guildWandPasskeyWard || null,
        temple_entropy_digest: guildTempleEntropyDigest || null,
        theatre_entropy_digest: guildTheatreEntropyDigest || null,
        attestation_media_digests: attestationMediaDigests,
        temple_entropy_source: templeEntropySource,
        theatre_entropy_source: theatreEntropySource,
        attestation_sources: Array.isArray(attestationSources) ? attestationSources : [],
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
        },
      });
      setGuildDecryptOutput(data);
      return data;
    });
  };

  const loadGuildMessageHistory = async () => {
    await runAction("guild_message_history", async () => {
      const params = new URLSearchParams({ limit: "20" });
      if (guildConversationId) {
        params.set("conversation_id", guildConversationId);
      } else {
        params.set("guild_id", guildId);
        params.set("channel_id", guildChannelId);
      }
      if (guildThreadId) {
        params.set("thread_id", guildThreadId);
      }
      const data = await apiCall(`/v1/guild/messages/history?${params.toString()}`, "GET");
      setGuildMessageHistory(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const runShygazunProject = async () => {
    await runAction("shygazun_project", async () => {
      const sourceText = String(shygazunTranslateSourceText || "").trim();
      if (!sourceText) {
        throw new Error("source_text_required");
      }
      const data = await kernelCall("/v0.1/shygazun/project", "POST", { source_text: sourceText });
      setShygazunProjectOutput(data || {});
      return data;
    });
  };

  const applyProjectionToRenderer = () => {
    if (!shygazunProjectOutput) return;
    const result = deriveRendererSettingsFromProjection(shygazunProjectOutput, voxelSettings);
    if (Object.keys(result.patch).length === 0) return;
    setVoxelSettings((prev) => ({ ...prev, ...result.patch }));
    setShygazunProjectionBridge(result);
  };

  const handleBuildCollisionMap = () => {
    const map = buildCollisionMap(rendererMotionVoxels);
    setCollisionMap(map);
  };

  const handleToggleCollisionOverlay = (enabled) => {
    setShowCollisionOverlay(enabled);
    const canvas = unifiedRendererCanvasRef.current;
    if (!canvas) return;
    if (enabled && collisionMap) {
      drawCollisionOverlay(canvas, collisionMap, voxelSettings);
    }
  };

  const handleExportCollisionMap = () => {
    if (!collisionMap) return;
    const data = exportCollisionMap(collisionMap, rendererRealmId || "unknown");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `collision_map_${data.pack_id}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const [gltfImportStatus, setGltfImportStatus] = useState("idle");
  const gltfImportRef = useRef(null);

  const handleExportGlb = () => {
    if (rendererMotionVoxels.length === 0) return;
    const glb = voxelsToGlb(rendererMotionVoxels, {
      tile:   voxelSettings.tile   ?? 16,
      zScale: voxelSettings.zScale ?? 8,
    });
    const blob = new Blob([glb], { type: "model/gltf-binary" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scene_${rendererRealmId || "export"}_${Date.now()}.glb`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportGltf = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setGltfImportStatus("loading");
    try {
      const voxels = await parseGltfFile(file, {
        tile:   voxelSettings.tile   ?? 16,
        zScale: voxelSettings.zScale ?? 8,
      });
      if (voxels.length === 0) throw new Error("No voxels extracted — check mesh names/positions");
      setRendererJson(JSON.stringify({ voxels }, null, 2));
      setGltfImportStatus(`imported: ${voxels.length} voxels`);
    } catch (err) {
      setGltfImportStatus(`error: ${err.message}`);
    }
    // Reset file input so the same file can be re-imported
    if (gltfImportRef.current) gltfImportRef.current.value = "";
  };

  const registerGuildConversation = async () => {
    await runAction("guild_conversation_register", async () => {
      const participantMemberIds = (() => {
        try {
          const parsed = JSON.parse(guildParticipantMemberIdsText || "[]");
          return Array.isArray(parsed) ? parsed.map((item) => String(item || "").trim()).filter(Boolean) : [];
        } catch {
          return [];
        }
      })();
      const participantGuildIds = (() => {
        try {
          const parsed = JSON.parse(guildParticipantGuildIdsText || "[]");
          return Array.isArray(parsed) ? parsed.map((item) => String(item || "").trim()).filter(Boolean) : [];
        } catch {
          return [];
        }
      })();
      const securitySession = parseObjectJson(guildSecuritySessionText, {});
      const normalizedParticipantMemberIds = participantMemberIds.length > 0 ? participantMemberIds : [activeProfileMemberId];
      const data = await apiCall("/v1/guild/conversations", "POST", {
        conversation_id: String(guildConversationId || "").trim(),
        conversation_kind: String(guildConversationKind || "").trim() || "guild_channel",
        guild_id: String(guildId || "").trim(),
        channel_id: String(guildChannelId || "").trim() || null,
        thread_id: String(guildThreadId || "").trim() || null,
        title: String(guildConversationTitle || "").trim(),
        participant_member_ids: normalizedParticipantMemberIds,
        participant_guild_ids: participantGuildIds,
        distribution_id: String(guildRecipientDistributionId || guildDistributionId || "").trim() || null,
        security_session: securitySession,
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
          profile: activeProfilePayload,
          owner_member_id: normalizedParticipantMemberIds[0] || activeProfileMemberId,
        },
      });
      setGuildConversationOutput(data);
      await loadGuildConversationList();
      return data;
    });
  };

  const loadGuildConversationList = async () => {
    await runAction("guild_conversation_list", async () => {
      const params = new URLSearchParams({ limit: "50" });
      if (guildId) {
        params.set("guild_id", guildId);
      }
      if (guildConversationKind) {
        params.set("conversation_kind", guildConversationKind);
      }
      const memberFilter = String(guildSenderId || activeProfileMemberId || "").trim();
      if (memberFilter) {
        params.set("participant_member_id", memberFilter);
      }
      const data = await apiCall(`/v1/guild/conversations?${params.toString()}`, "GET");
      setGuildConversationList(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const loadGuildConversation = async (conversationId = guildConversationId) => {
    await runAction("guild_conversation_get", async () => {
      const safeConversationId = String(conversationId || "").trim();
      if (!safeConversationId) {
        throw new Error("conversation_id_required");
      }
      const data = await apiCall(`/v1/guild/conversations/${encodeURIComponent(safeConversationId)}`, "GET");
      setGuildConversationOutput(data);
      setGuildConversationId(String(data?.conversation_id || safeConversationId));
      setGuildConversationKind(String(data?.conversation_kind || "guild_channel"));
      setGuildConversationTitle(String(data?.title || ""));
      setGuildChannelId(String(data?.channel_id || guildChannelId));
      setGuildThreadId(String(data?.thread_id || ""));
      setGuildRecipientDistributionId(String(data?.distribution_id || guildRecipientDistributionId || ""));
      setGuildParticipantMemberIdsText(JSON.stringify(data?.participant_member_ids || [], null, 2));
      setGuildParticipantGuildIdsText(JSON.stringify(data?.participant_guild_ids || [], null, 2));
      setGuildSecuritySessionText(JSON.stringify(data?.security_session || {}, null, 2));
      return data;
    });
  };

  const updateGuildMessageRelayStatus = async () => {
    await runAction("guild_message_relay_status", async () => {
      const messageId = String(guildPersistOutput?.message_id || guildMessageHistory?.[0]?.message_id || "").trim();
      if (!messageId) {
        throw new Error("message_id_required");
      }
      const receipt = parseObjectJson(guildRelayReceiptText, {});
      const mergedReceipt = {
        distribution_id: guildRecipientDistributionId || null,
        recipient_guild_id: guildRecipientGuildId || null,
        recipient_channel_id: guildRecipientChannelId || null,
        ...receipt,
      };
      const data = await apiCall("/v1/guild/messages/relay-status", "POST", {
        message_id: messageId,
        relay_status: String(guildRelayStatus || "").trim(),
        receipt: mergedReceipt,
      });
      setGuildPersistOutput((prev) => ({ ...(prev || {}), ...data }));
      await loadGuildMessageHistory();
      return data;
    });
  };

  const loadGuildWandStatus = async () => {
    await loadWandStatus(guildWandId, setGuildWandStatus);
  };

  const registerGuildRegistryEntry = async () => {
    await runAction("guild_registry_register", async () => {
      const data = await apiCall("/v1/guild/registry", "POST", {
        guild_id: String(guildId || "").trim(),
        display_name: String(guildDisplayName || "").trim(),
        distribution_id: String(guildDistributionId || "").trim(),
        owner_artisan_id: guildSenderId || "artisan-desktop",
        owner_profile_name: profileName || "Artisan",
        owner_profile_email: profileEmail || "",
        member_profiles: [
          {
            actor_id: guildSenderId || "player",
            display_name: profileName || "Artisan",
            email: profileEmail || "",
            timezone: profileTimezone || "UTC",
          },
        ],
        charter: {
          trust_model: "wand_registry",
          transport_profile: "distribution_registry_pending",
          channels: Array.from(new Set([String(guildChannelId || "").trim(), "hall.general"].filter((item) => item !== ""))),
        },
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
        },
      });
      setGuildRegistryOutput(data);
      await loadGuildRegistryList();
      return data;
    });
  };

  const loadGuildRegistryList = async () => {
    await runAction("guild_registry_list", async () => {
      const data = await apiCall("/v1/guild/registry?limit=50", "GET");
      setGuildRegistryList(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const loadGuildRegistryEntry = async (registryGuildId = guildId) => {
    await runAction("guild_registry_get", async () => {
      const safeGuildId = String(registryGuildId || "").trim();
      if (!safeGuildId) {
        throw new Error("guild_id_required");
      }
      const data = await apiCall(`/v1/guild/registry/${encodeURIComponent(safeGuildId)}`, "GET");
      setGuildRegistryOutput(data);
      setGuildId(String(data?.guild_id || safeGuildId));
      setGuildDisplayName(String(data?.display_name || ""));
      setGuildDistributionId(String(data?.distribution_id || ""));
      if (!guildRecipientDistributionId) {
        setGuildRecipientDistributionId(String(data?.distribution_id || ""));
      }
      return data;
    });
  };

  const registerDistributionRegistryEntry = async () => {
    await runAction("distribution_registry_register", async () => {
      const guildIds = (() => {
        try {
          const parsed = JSON.parse(distributionGuildIdsText || "[]");
          return Array.isArray(parsed)
            ? parsed.map((item) => String(item || "").trim()).filter((item) => item !== "")
            : [];
        } catch {
          return [];
        }
      })();
      const supportedProtocolVersions = (() => {
        try {
          const parsed = JSON.parse(distributionSupportedProtocolVersionsText || "[]");
          return Array.isArray(parsed)
            ? parsed.map((item) => String(item || "").trim()).filter((item) => item !== "")
            : [];
        } catch {
          return [];
        }
      })();
      const data = await apiCall("/v1/distributions/registry", "POST", {
        distribution_id: String(distributionId || "").trim(),
        display_name: String(distributionDisplayName || "").trim(),
        base_url: String(distributionBaseUrl || "").trim(),
        transport_kind: String(distributionTransportKind || "").trim() || "https",
        public_key_ref: String(distributionPublicKeyRef || "").trim(),
        protocol_family: String(distributionProtocolFamily || "").trim() || "guild_message_signal_artifice",
        protocol_version: String(distributionProtocolVersion || "").trim() || "v1",
        supported_protocol_versions: supportedProtocolVersions,
        guild_ids: guildIds,
        metadata: parseObjectJson(distributionMetadataText, {}),
      });
      setDistributionRegistryOutput(data);
      await loadDistributionRegistryList();
      return data;
    });
  };

  const loadDistributionRegistryList = async () => {
    await runAction("distribution_registry_list", async () => {
      const data = await apiCall("/v1/distributions/registry?limit=50", "GET");
      setDistributionRegistryList(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const loadDistributionRegistryEntry = async (registryDistributionId = distributionId) => {
    await runAction("distribution_registry_get", async () => {
      const safeDistributionId = String(registryDistributionId || "").trim();
      if (!safeDistributionId) {
        throw new Error("distribution_id_required");
      }
      const data = await apiCall(`/v1/distributions/registry/${encodeURIComponent(safeDistributionId)}`, "GET");
      setDistributionRegistryOutput(data);
      setDistributionId(String(data?.distribution_id || safeDistributionId));
      setDistributionDisplayName(String(data?.display_name || ""));
      setDistributionBaseUrl(String(data?.base_url || ""));
      setDistributionTransportKind(String(data?.transport_kind || "https"));
      setDistributionPublicKeyRef(String(data?.public_key_ref || ""));
      const messagingProtocol = data?.metadata?.messaging_protocol || {};
      setDistributionProtocolFamily(String(messagingProtocol?.family || "guild_message_signal_artifice"));
      setDistributionProtocolVersion(String(messagingProtocol?.version || "v1"));
      setDistributionSupportedProtocolVersionsText(JSON.stringify(messagingProtocol?.supported_versions || ["v1"], null, 2));
      setDistributionGuildIdsText(JSON.stringify(data?.guild_ids || [], null, 2));
      setDistributionMetadataText(JSON.stringify(data?.metadata || {}, null, 2));
      setDistributionShopWorkspaceId(String(data?.metadata?.shop_workspace_id || ""));
      if (!guildRecipientDistributionId) {
        setGuildRecipientDistributionId(String(data?.distribution_id || safeDistributionId));
      }
      return data;
    });
  };

  const saveDistributionShopWorkspace = async () => {
    await runAction("distribution_registry_set_shop_workspace", async () => {
      setDistributionShopWorkspaceStatus({ status: "saving" });
      const safeDistributionId = String(distributionId || "").trim();
      if (!safeDistributionId) {
        setDistributionShopWorkspaceStatus({ status: "error", detail: "distribution_id_required" });
        throw new Error("distribution_id_required");
      }
      const shopWorkspaceId = String(distributionShopWorkspaceId || "").trim();
      if (!shopWorkspaceId) {
        setDistributionShopWorkspaceStatus({ status: "error", detail: "shop_workspace_id_required" });
        throw new Error("shop_workspace_id_required");
      }
      const data = await apiCall(
        `/v1/distributions/registry/${encodeURIComponent(safeDistributionId)}/shop-workspace`,
        "PUT",
        { shop_workspace_id: shopWorkspaceId }
      );
      setDistributionRegistryOutput(data);
      await loadDistributionRegistryEntry(safeDistributionId);
      await loadDistributionRegistryList();
      setDistributionShopWorkspaceStatus({ status: "ok", detail: `Saved ${shopWorkspaceId}` });
      return data;
    });
  };

  const loadDistributionCapabilities = async (registryDistributionId = guildRecipientDistributionId || distributionId) => {
    await runAction("distribution_capabilities_get", async () => {
      const safeDistributionId = String(registryDistributionId || "").trim();
      if (!safeDistributionId) {
        throw new Error("distribution_id_required");
      }
      const data = await apiCall(`/v1/distributions/registry/${encodeURIComponent(safeDistributionId)}/capabilities`, "GET");
      setDistributionCapabilitiesOutput(data);
      return data;
    });
  };

  const ensureLocalDistributionRegistryEntry = async (registryDistributionId) => {
    const safeDistributionId = String(registryDistributionId || "").trim();
    if (!safeDistributionId) {
      return null;
    }
    const localDistributionIds = new Set(
      [distributionId, guildDistributionId]
        .map((value) => String(value || "").trim())
        .filter((value) => value !== "")
    );
    if (!localDistributionIds.has(safeDistributionId)) {
      return null;
    }
    try {
      return await apiCall(`/v1/distributions/registry/${encodeURIComponent(safeDistributionId)}`, "GET");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (!message.includes("distribution_not_found") && !message.includes("\"detail\":\"Not Found\"")) {
        throw error;
      }
    }
    const guildIds = (() => {
      try {
        const parsed = JSON.parse(distributionGuildIdsText || "[]");
        return Array.isArray(parsed)
          ? parsed.map((item) => String(item || "").trim()).filter((item) => item !== "")
          : [];
      } catch {
        return [];
      }
    })();
    const supportedProtocolVersions = (() => {
      try {
        const parsed = JSON.parse(distributionSupportedProtocolVersionsText || "[]");
        return Array.isArray(parsed)
          ? parsed.map((item) => String(item || "").trim()).filter((item) => item !== "")
          : [];
      } catch {
        return [];
      }
    })();
    const created = await apiCall("/v1/distributions/registry", "POST", {
      distribution_id: safeDistributionId,
      display_name: String(distributionDisplayName || profileName || safeDistributionId).trim(),
      base_url:
        safeDistributionId === String(distributionId || "").trim()
          ? String(distributionBaseUrl || API_BASE).trim()
          : String(API_BASE || "").trim(),
      transport_kind: String(distributionTransportKind || "").trim() || "https",
      public_key_ref: String(distributionPublicKeyRef || "").trim(),
      protocol_family: String(distributionProtocolFamily || "").trim() || "guild_message_signal_artifice",
      protocol_version: String(distributionProtocolVersion || "").trim() || "v1",
      supported_protocol_versions: supportedProtocolVersions,
      guild_ids: guildIds,
      metadata: parseObjectJson(distributionMetadataText, {}),
    });
    setDistributionRegistryOutput(created);
    await loadDistributionRegistryList();
    return created;
  };

  const registerDistributionHandshake = async () => {
    await runAction("distribution_handshake_register", async () => {
      const data = await apiCall("/v1/distributions/handshakes", "POST", {
        distribution_id: String(distributionId || "").trim(),
        local_distribution_id: String(distributionHandshakeLocalId || "").trim(),
        remote_public_key_ref: String(distributionPublicKeyRef || "").trim(),
        handshake_mode: String(distributionHandshakeMode || "").trim() || "mutual_hmac",
        protocol_family: String(distributionHandshakeProtocolFamily || "").trim() || "guild_message_signal_artifice",
        local_protocol_version: String(distributionHandshakeLocalProtocolVersion || "").trim() || "v1",
        remote_protocol_version: String(distributionHandshakeRemoteProtocolVersion || "").trim() || "v1",
        negotiated_protocol_version: String(distributionHandshakeNegotiatedProtocolVersion || "").trim() || "v1",
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_hall",
          profile: activeProfilePayload,
        },
      });
      setDistributionHandshakeOutput(data);
      await loadDistributionHandshakes(String(distributionId || "").trim());
      return data;
    });
  };

  const loadDistributionHandshakes = async (registryDistributionId = distributionId) => {
    await runAction("distribution_handshake_list", async () => {
      const params = new URLSearchParams({ limit: "50" });
      const safeDistributionId = String(registryDistributionId || "").trim();
      if (safeDistributionId) {
        params.set("distribution_id", safeDistributionId);
      }
      const data = await apiCall(`/v1/distributions/handshakes?${params.toString()}`, "GET");
      setDistributionHandshakeList(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const applyRegisteredWandSelection = async (wandId, { target = "both", loadEntry = false } = {}) => {
    const safeWandId = String(wandId || "").trim();
    if (!safeWandId) {
      throw new Error("wand_id_required");
    }
    setGuildSelectedRegistryWandId(safeWandId);
    if (target === "both" || target === "temple") {
      setWandDamageWandId(safeWandId);
      await fetchWandStatus(safeWandId, setWandStatus);
    }
    if (target === "both" || target === "guild") {
      setGuildWandId(safeWandId);
      await fetchWandStatus(safeWandId, setGuildWandStatus);
    }
    setWandRegistryWandId(safeWandId);
    if (loadEntry) {
      const data = await apiCall(`/v1/security/wands/${encodeURIComponent(safeWandId)}`, "GET");
      setWandRegistryOutput(data);
      setWandRegistryMakerId(String(data?.maker_id || ""));
      setWandRegistryMakerDate(String(data?.maker_date || data?.wand_spec?.maker_date || ""));
      setWandRegistryAtelierOrigin(String(data?.atelier_origin || ""));
      setWandRegistryStructuralFingerprint(String(data?.structural_fingerprint || ""));
      setWandRegistryCraftRecordHash(String(data?.craft_record_hash || ""));
      setWandRegistryMaterialProfileText(JSON.stringify(data?.material_profile || data?.wand_spec?.material_profile || {}, null, 2));
      setWandRegistryDimensionsText(JSON.stringify(data?.dimensions || data?.wand_spec?.dimensions || {}, null, 2));
      setWandRegistryOwnershipChainText(JSON.stringify(data?.ownership_chain || [], null, 2));
      setWandRegistryMetadataText(JSON.stringify(data?.metadata || {}, null, 2));
      return data;
    }
    return null;
  };

  const registerWandRegistryEntry = async () => {
    await runAction("wand_registry_register", async () => {
      const data = await apiCall("/v1/security/wands/register", "POST", {
        wand_id: String(wandRegistryWandId || "").trim(),
        maker_id: String(wandRegistryMakerId || "").trim(),
        maker_date: String(wandRegistryMakerDate || "").trim(),
        atelier_origin: String(wandRegistryAtelierOrigin || "").trim(),
        structural_fingerprint: String(wandRegistryStructuralFingerprint || "").trim(),
        craft_record_hash: String(wandRegistryCraftRecordHash || "").trim(),
        material_profile: parseObjectJson(wandRegistryMaterialProfileText, {}),
        dimensions: parseObjectJson(wandRegistryDimensionsText, {}),
        ownership_chain: (() => {
          try {
            const parsed = JSON.parse(wandRegistryOwnershipChainText || "[]");
            return Array.isArray(parsed) ? parsed : [];
          } catch {
            return [];
          }
        })(),
        metadata: parseObjectJson(wandRegistryMetadataText, {}),
      });
      setWandRegistryOutput(data);
      setWandRegistryWandId(String(data?.wand_id || wandRegistryWandId));
      await fetchWandStatus(String(data?.wand_id || wandRegistryWandId), setGuildWandStatus);
      await loadWandRegistryList();
      return data;
    });
  };

  const loadWandRegistryList = async () => {
    await runAction("wand_registry_list", async () => {
      const data = await apiCall("/v1/security/wands?limit=50", "GET");
      setWandRegistryList(Array.isArray(data) ? data : []);
      return data;
    });
  };

  const loadWandRegistryEntry = async (wandId = wandRegistryWandId) => {
    await runAction("wand_registry_get", async () => {
      const safeWandId = String(wandId || "").trim();
      if (!safeWandId) {
        throw new Error("wand_id_required");
      }
      const data = await apiCall(`/v1/security/wands/${encodeURIComponent(safeWandId)}`, "GET");
      setWandRegistryOutput(data);
      setWandRegistryWandId(String(data?.wand_id || safeWandId));
      setWandRegistryMakerId(String(data?.maker_id || ""));
      setWandRegistryMakerDate(String(data?.maker_date || data?.wand_spec?.maker_date || ""));
      setWandRegistryAtelierOrigin(String(data?.atelier_origin || ""));
      setWandRegistryStructuralFingerprint(String(data?.structural_fingerprint || ""));
      setWandRegistryCraftRecordHash(String(data?.craft_record_hash || ""));
      setWandRegistryMaterialProfileText(JSON.stringify(data?.material_profile || data?.wand_spec?.material_profile || {}, null, 2));
      setWandRegistryDimensionsText(JSON.stringify(data?.dimensions || data?.wand_spec?.dimensions || {}, null, 2));
      setWandRegistryOwnershipChainText(JSON.stringify(data?.ownership_chain || [], null, 2));
      setWandRegistryMetadataText(JSON.stringify(data?.metadata || {}, null, 2));
      return data;
    });
  };

  const loadMigrationStatus = async () => {
    await runAction("migration_status", async () => {
      const data = await apiCall("/v1/admin/migrations/status", "GET");
      setMigrationStatus(data);
      return data;
    });
  };

  const buildProbeErrorPayload = (scope, err) => {
    const raw = err instanceof Error ? err.message : String(err);
    const parsed = parseSafeJson(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return {
        status: "error",
        scope,
        detail: parsed,
      };
    }
    const detail = String(raw || "").trim();
    let category = "request_failed";
    if (detail.includes("Failed to fetch")) {
      category = "network_unreachable";
    } else if (detail.includes("404")) {
      category = "route_missing";
    } else if (detail.includes("401") || detail.includes("403")) {
      category = "auth_blocked";
    } else if (detail.includes("500")) {
      category = "server_error";
    }
    return {
      status: "error",
      scope,
      category,
      detail,
    };
  };

  const buildProbeHttpErrorPayload = async (scope, response) => {
    const text = await response.text();
    const parsed = parseSafeJson(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return {
        status: "error",
        scope,
        category:
          response.status === 404
            ? "route_missing"
            : response.status === 401 || response.status === 403
              ? "auth_blocked"
              : response.status >= 500
                ? "server_error"
                : "request_failed",
        http_status: response.status,
        detail: parsed,
      };
    }
    return {
      status: "error",
      scope,
      category:
        response.status === 404
          ? "route_missing"
          : response.status === 401 || response.status === 403
            ? "auth_blocked"
            : response.status >= 500
              ? "server_error"
              : "request_failed",
      http_status: response.status,
      detail: String(text || "").trim() || `http_${response.status}`,
    };
  };

  const loadServiceReadiness = async () => {
    await runAction("service_readiness", async () => {
      try {
        const response = await fetch(`${API_BASE}/ready`, {
          method: "GET",
          headers: buildHeaders(role, caps, adminGateToken),
        });
        const text = await response.text();
        const data = parseSafeJson(text);
        // /ready returns 503 when not-ready — treat any valid JSON body as the
        // readiness payload regardless of HTTP status, so sub-fields are visible.
        if (data && typeof data === "object" && !Array.isArray(data)) {
          setOutput(JSON.stringify(data, null, 2));
          setServiceReadinessOutput(data);
          return data;
        }
        const failure = response.ok
          ? {
              status: "error",
              scope: "ready",
              category: "invalid_response",
              detail: String(text || "").trim() || "non_json_ready_response",
            }
          : await buildProbeHttpErrorPayload("ready", {
              ...response,
              text: async () => text,
            });
        setOutput(JSON.stringify(failure, null, 2));
        setServiceReadinessOutput(failure);
        throw new Error(JSON.stringify(failure));
      } catch (err) {
        const failure = buildProbeErrorPayload("ready", err);
        setOutput(JSON.stringify(failure, null, 2));
        setServiceReadinessOutput(failure);
        throw err;
      }
    });
  };

  const loadFederationHealth = async (targetDistributionId = guildRecipientDistributionId || distributionId) => {
    await runAction("federation_health", async () => {
      try {
        const safeDistributionId = String(targetDistributionId || "").trim();
        if (safeDistributionId) {
          await ensureLocalDistributionRegistryEntry(safeDistributionId);
        }
        const query = safeDistributionId
          ? `?distribution_id=${encodeURIComponent(safeDistributionId)}&limit=25`
          : "?limit=25";
        const data = await apiCall(`/v1/federation/health${query}`, "GET");
        setFederationHealthOutput(data);
        return data;
      } catch (err) {
        const failure = buildProbeErrorPayload("federation", err);
        setOutput(JSON.stringify(failure, null, 2));
        setFederationHealthOutput(failure);
        throw err;
      }
    });
  };

  const foyerReadiness = serviceReadinessOutput && typeof serviceReadinessOutput === "object" ? serviceReadinessOutput : {};
  const foyerReadinessStatus = String(foyerReadiness.status || "unknown");
  const foyerFederation = federationHealthOutput && typeof federationHealthOutput === "object" ? federationHealthOutput : {};
  const foyerFederationStatus = String(foyerFederation.status || "unknown");
  const foyerFederationTarget = Array.isArray(foyerFederation.targets) && foyerFederation.targets.length > 0 ? foyerFederation.targets[0] : null;
  const foyerFederationTrust = String(foyerFederationTarget?.trust_grade || "unknown");

  const runShygazunCorrect = async () => {
    await runAction("shygazun_correct", async () => {
      const sourceText = String(shygazunTranslateSourceText || "").trim();
      if (!sourceText) {
        throw new Error("source_text_required");
      }
      const actorId = String(rendererTablesActorId || "player").trim() || "player";
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: actorId,
        plan_id: `shygazun_correct_${Date.now()}`,
        actions: [
          {
            action_id: "correct",
            kind: "shygazun.correct",
            payload: {
              source_text: sourceText,
            },
          },
        ],
      });
      const actionResult = Array.isArray(consumed?.results)
        ? consumed.results.find((item) => item && item.action_id === "correct")
        : null;
      if (!actionResult || !actionResult.ok) {
        throw new Error(
          actionResult && typeof actionResult.error === "string"
            ? actionResult.error
            : "shygazun_correct_failed"
        );
      }
      const runtimeResult = actionResult.result || {};
      setShygazunCorrectOutput(runtimeResult);
      return runtimeResult;
    });
  };

  const listModuleCatalog = async () => {
    await runAction("modules_list", async () => {
      const data = await apiCall("/v1/game/modules", "GET", null);
      const modules = Array.isArray(data?.modules) ? data.modules : [];
      setModuleCatalog(modules);
      if (modules.length > 0) {
        const current = String(moduleSelectedId || "").trim();
        const hasCurrent = modules.some((item) => item && String(item.module_id || "") === current);
        if (!hasCurrent) {
          setModuleSelectedId(String(modules[0].module_id || ""));
        }
      }
      return data;
    });
  };

  const fetchSelectedModuleSpec = async () => {
    await runAction("module_get", async () => {
      const moduleId = String(moduleSelectedId || "").trim();
      if (!moduleId) {
        throw new Error("module_id_required");
      }
      const data = await apiCall(`/v1/game/modules/${encodeURIComponent(moduleId)}`, "GET", null);
      setModuleSelectedSpec(data && typeof data === "object" ? data : null);
      return data;
    });
  };

  const validateSelectedModuleSpec = async () => {
    await runAction("module_validate", async () => {
      const moduleId = String(moduleSelectedId || "").trim();
      if (!moduleId) {
        throw new Error("module_id_required");
      }
      const data = await apiCall("/v1/game/modules/validate", "POST", { module_id: moduleId });
      setModuleValidateOutput(data && typeof data === "object" ? data : null);
      return data;
    });
  };

  const runSelectedModuleSpec = async () => {
    await runAction("module_run", async () => {
      const moduleId = String(moduleSelectedId || "").trim();
      if (!moduleId) {
        throw new Error("module_id_required");
      }
      const actorId = String(rendererTablesActorId || "player").trim() || "player";
      const reconcileSceneRaw = String(moduleReconcileSceneId || "").trim();
      const reconcileSceneId = reconcileSceneRaw.includes("/")
        ? reconcileSceneRaw
        : `${rendererRealmId}/${reconcileSceneRaw || "renderer-lab"}`;
      let payloadOverrides = {};
      try {
        const parsed = JSON.parse(moduleRunOverridesText || "{}");
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          payloadOverrides = parsed;
        }
      } catch {
        throw new Error("module_payload_overrides_invalid_json");
      }
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: actorId,
        plan_id: `module_run_${Date.now()}`,
        actions: [
          {
            action_id: "module_run",
            kind: "module.run",
            payload: {
              module_id: moduleId,
              payload_overrides: payloadOverrides,
            },
          },
          ...(moduleAutoReconcile
            ? [
                {
                  action_id: "module_reconcile",
                  kind: "render.scene.reconcile",
                  payload: {
                    realm_id: rendererRealmId,
                    scene_id: reconcileSceneId,
                    apply: Boolean(moduleReconcileApply),
                    scene_content: resolveRuntimeSceneContent(),
                  },
                },
              ]
            : []),
        ],
      });
      const actionResult = Array.isArray(consumed?.results)
        ? consumed.results.find((item) => item && item.action_id === "module_run")
        : null;
      if (!actionResult || !actionResult.ok) {
        throw new Error(
          actionResult && typeof actionResult.error === "string"
            ? actionResult.error
            : "module_run_failed"
        );
      }
      const runtimeResult = actionResult.result || {};
      const reconcileResult = Array.isArray(consumed?.results)
        ? consumed.results.find((item) => item && item.action_id === "module_reconcile")
        : null;
      const out = {
        module: runtimeResult,
        reconcile: reconcileResult ? (reconcileResult.ok ? reconcileResult.result || {} : { error: reconcileResult.error || "reconcile_failed" }) : null,
      };
      setModuleRunOutput(out);
      return out;
    });
  };

  const runBackendAudioCue = async (kind, payload) => {
    await runAction(`audio_${String(kind).replace(".", "_")}`, async () => {
      const actorId = String(rendererTablesActorId || "player").trim() || "player";
      const consumed = await apiCall("/v1/game/runtime/consume", "POST", {
        workspace_id: workspaceId,
        actor_id: actorId,
        plan_id: `audio_${String(kind).replace(".", "_")}_${Date.now()}`,
        actions: [
          {
            action_id: "audio",
            kind,
            payload,
          },
        ],
      });
      const actionResult = Array.isArray(consumed?.results) ? consumed.results[0] : null;
      if (!actionResult || !actionResult.ok) {
        throw new Error(
          actionResult && typeof actionResult.error === "string"
            ? actionResult.error
            : `audio_action_failed:${kind}`
        );
      }
      return actionResult.result || {};
    });
  };

  const applyRendererPipeline = async () => {
    const ok = await validatePipelineIfNeeded();
    if (!ok) {
      return;
    }
    let workingEngineText = rendererEngineStateText;
    if (rendererPipeline.pythonFileId) {
      const file = getStudioFileById(rendererPipeline.pythonFileId);
      if (file) {
        setRendererPython(file.content || "");
      }
    }
    if (rendererPipeline.cobraFileId) {
      const file = getStudioFileById(rendererPipeline.cobraFileId);
      if (file) {
        setRendererCobra(file.content || "");
      }
    }
    if (rendererPipeline.jsFileId) {
      const file = getStudioFileById(rendererPipeline.jsFileId);
      if (file) {
        setRendererJs(file.content || "");
      }
    }
    if (rendererPipeline.jsonFileId) {
      const file = getStudioFileById(rendererPipeline.jsonFileId);
      if (file) {
        setRendererJson(file.content || "");
      }
    }
    if (rendererPipeline.engineFileId) {
      const file = getStudioFileById(rendererPipeline.engineFileId);
      if (file) {
        workingEngineText = file.content || "{}";
        setRendererEngineStateText(workingEngineText);
      }
    }
    if (rendererPipeline.worldRegionAutoLoad && worldRegionPipelineKey) {
      const data = await requestWorldRegionLoad();
      setWorldRegionLast(data);
      workingEngineText = mergeLoadedWorldRegionIntoEngineText(workingEngineText, data);
      setRendererEngineStateText(workingEngineText);
      setRendererGameStatus(`world_loaded:${String(data.region_key || worldRegionPipelineKey)}`);
    }
    if (rendererPipeline.autoPlay) {
      setRendererSimPlaying(true);
    }
  };
  const compileSceneGraphPreview = async () => {
    const renderMode = normalizeRenderMode(voxelSettings.renderMode);
    const camera = normalizeCamera3d(voxelSettings.camera3d);
    const payload = {
      workspace_id: workspaceId,
      realm_id: rendererRealmId,
      scene_id: `${rendererRealmId}/renderer-lab`,
      render_mode: renderMode,
      camera_yaw_deg: camera.yaw,
      camera_pitch_deg: camera.pitch,
      camera_zoom: camera.zoom,
      camera_pan_x: camera.panX,
      camera_pan_y: camera.panY,
      include_unloaded_regions: true,
      include_material_constraints: true,
    };
    const data = await runAction("renderer_scene_graph_preview", async () => {
      return await apiCall("/v1/game/renderer/render-graph", "POST", payload);
    });
    if (data && typeof data === "object") {
      const graph =
        data && Array.isArray(data.nodes)
          ? { nodes: data.nodes, edges: [] }
          : data.graph && typeof data.graph === "object"
            ? data.graph
            : data;
      setRendererGraphPreview(graph);
      setRendererVisualSource("engine");
      setRendererEngineStateText(
        JSON.stringify(
          {
            graph,
            render_contract: data,
            realm_id: rendererRealmId,
            scene_id: `${rendererRealmId}/renderer-lab`,
          },
          null,
          2
        )
      );
      setNotice(`scene_graph_preview: ready (${renderMode.toUpperCase()})`);
      return;
    }
    setNotice("scene_graph_preview: no data");
  };
  const runRendererAssetDiagnostics = async () => {
    const payload = {
      workspace_id: workspaceId,
      realm_id: rendererRealmId,
      scene_id: `${rendererRealmId}/renderer-lab`,
      include_unloaded_regions: true,
      strict_assets: false,
    };
    const data = await runAction("renderer_asset_diagnostics", async () => {
      return await apiCall("/v1/game/renderer/assets/diagnostics", "POST", payload);
    });
    if (data && typeof data === "object") {
      setRendererAssetDiagnostics(data);
      setNotice(`asset_diagnostics: ${data.ok ? "ok" : "issues"}`);
    }
  };
  const exportRendererPipeline = () => {
    const payload = { ...rendererPipeline };
    setRendererPipelineJson(JSON.stringify(payload, null, 2));
  };
  const importRendererPipeline = () => {
    try {
      const parsed = JSON.parse(rendererPipelineJson || "{}");
      setRendererPipeline((prev) => ({
        ...prev,
        pythonFileId: parsed.pythonFileId || "",
        cobraFileId: parsed.cobraFileId || "",
        jsFileId: parsed.jsFileId || "",
        jsonFileId: parsed.jsonFileId || "",
        engineFileId: parsed.engineFileId || "",
        worldRegionRealmId: parsed.worldRegionRealmId || rendererRealmId,
        worldRegionKey: parsed.worldRegionKey || "",
        worldRegionCachePolicy: parsed.worldRegionCachePolicy || "cache",
        worldRegionPayloadFileId: parsed.worldRegionPayloadFileId || "",
        worldRegionAutoLoad: Boolean(parsed.worldRegionAutoLoad),
        autoPlay: Boolean(parsed.autoPlay)
      }));
    } catch {
      setNotice("pipeline JSON invalid");
    }
  };
  const addVoxelMaterial = () => {
    if (!voxelMaterialDraft.id.trim()) {
      return;
    }
    setVoxelMaterials((prev) => [...prev, { ...voxelMaterialDraft }]);
    setVoxelMaterialDraft({ id: "", color: "#7aa2ff", textureTop: "", textureLeft: "", textureRight: "" });
  };
  const updateVoxelMaterial = (index, patch) => {
    setVoxelMaterials((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };
  const removeVoxelMaterial = (index) => {
    setVoxelMaterials((prev) => prev.filter((_, idx) => idx !== index));
  };
  const addVoxelLayer = () => {
    setVoxelLayers((prev) => [...prev, { id: "layer_" + (prev.length + 1), zOffset: 0 }]);
  };
  const updateVoxelLayer = (index, patch) => {
    setVoxelLayers((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };
  const removeVoxelLayer = (index) => {
    setVoxelLayers((prev) => prev.filter((_, idx) => idx !== index));
  };
  const addVoxelAtlas = () => {
    if (!voxelAtlasDraft.id.trim() || !voxelAtlasDraft.src.trim()) {
      return;
    }
    setVoxelAtlases((prev) => [...prev, { ...voxelAtlasDraft }]);
    setVoxelAtlasDraft({ id: "", src: "", tileSize: 16, cols: 8, rows: 8, padding: 0 });
  };
  const updateVoxelAtlas = (index, patch) => {
    setVoxelAtlases((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };
  const removeVoxelAtlas = (index) => {
    setVoxelAtlases((prev) => prev.filter((_, idx) => idx !== index));
  };
  const applyRepresentativeAtlasMaterialSet = () => {
    const atlasId =
      (typeof voxelAtlasDraft.id === "string" && voxelAtlasDraft.id.trim()) ||
      (Array.isArray(voxelAtlases) && voxelAtlases[0] && typeof voxelAtlases[0].id === "string" ? voxelAtlases[0].id.trim() : "");
    if (!atlasId) {
      setNotice("atlas_material_set: add/select an atlas id first");
      return;
    }
    const presets = [
      { id: "ground", color: "#7a7e6c", textureTop: `atlas:${atlasId}:0,0`, textureLeft: `atlas:${atlasId}:0,1`, textureRight: `atlas:${atlasId}:1,1` },
      { id: "road", color: "#716a62", textureTop: `atlas:${atlasId}:2,0`, textureLeft: `atlas:${atlasId}:2,1`, textureRight: `atlas:${atlasId}:3,1` },
      { id: "wall", color: "#8a7b6a", textureTop: `atlas:${atlasId}:4,0`, textureLeft: `atlas:${atlasId}:4,1`, textureRight: `atlas:${atlasId}:5,1` },
      { id: "roof", color: "#7f4f46", textureTop: `atlas:${atlasId}:6,0`, textureLeft: `atlas:${atlasId}:6,1`, textureRight: `atlas:${atlasId}:7,1` },
      { id: "wood", color: "#946a40", textureTop: `atlas:${atlasId}:0,2`, textureLeft: `atlas:${atlasId}:0,3`, textureRight: `atlas:${atlasId}:1,3` },
      { id: "water", color: "#4a799d", textureTop: `atlas:${atlasId}:2,2`, textureLeft: `atlas:${atlasId}:2,3`, textureRight: `atlas:${atlasId}:3,3` },
      { id: "foliage", color: "#4f7f4f", textureTop: `atlas:${atlasId}:4,2`, textureLeft: `atlas:${atlasId}:4,3`, textureRight: `atlas:${atlasId}:5,3` },
      { id: "player", color: "#f6c677", textureTop: `atlas:${atlasId}:6,2`, textureLeft: `atlas:${atlasId}:6,3`, textureRight: `atlas:${atlasId}:7,3` },
    ];
    setVoxelMaterials((prev) => {
      const next = Array.isArray(prev) ? prev.slice() : [];
      presets.forEach((preset) => {
        const idx = next.findIndex((item) => item && item.id === preset.id);
        if (idx >= 0) {
          next[idx] = { ...next[idx], ...preset };
        } else {
          next.push(preset);
        }
      });
      return next;
    });
    setNotice(`atlas_material_set_applied:${atlasId}`);
  };

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
            <h2>Network Links</h2>
            <div className="foyer-link-grid">
              <a
                className="foyer-link-card"
                href="https://quantumquackery.org/"
                target="_blank"
                rel="noreferrer"
              >
                <strong>QuantumQuackery.org</strong>
                <span>Public website and front door</span>
              </a>
              <a
                className="foyer-link-card"
                href="https://djinnos-shyagzun-atelier-api.onrender.com/health"
                target="_blank"
                rel="noreferrer"
              >
                <strong>djinnos-shyagzun-atelier-api.onrender.com</strong>
                <span>Hosted API health surface</span>
              </a>
              <a
                className="foyer-link-card"
                href="https://atelier-api.quantumquackery.com"
                target="_blank"
                rel="noreferrer"
              >
                <strong>atelier-api.quantumquackery.com</strong>
                <span>Kernel host</span>
              </a>
            </div>
            <div className="row">
              <button className="action" onClick={loadServiceReadiness}>Refresh Readiness</button>
              <button className="action" onClick={() => loadFederationHealth()}>Refresh Federation</button>
            </div>
            <div className="row">
              <span className={`badge ${foyerReadinessStatus === "ready" ? "badge-ok" : foyerReadinessStatus === "not_ready" ? "badge-warn" : foyerReadinessStatus === "error" ? "badge-error" : ""}`}>{`Readiness: ${foyerReadinessStatus}`}</span>
              <span className={`badge ${String(foyerReadiness?.database?.status || "") === "up" ? "badge-ok" : String(foyerReadiness?.database?.status || "") === "down" ? "badge-error" : ""}`}>{`DB: ${String(foyerReadiness?.database?.status || "unknown")}`}</span>
              <span className={`badge ${String(foyerReadiness?.kernel?.status || "") === "up" ? "badge-ok" : String(foyerReadiness?.kernel?.status || "") === "down" ? "badge-error" : ""}`}>{`Kernel: ${String(foyerReadiness?.kernel?.status || "unknown")}`}</span>
              <span className={`badge ${String(foyerReadiness?.migrations?.status || "") === "up" ? "badge-ok" : String(foyerReadiness?.migrations?.status || "") === "down" ? "badge-error" : ""}`}>{`Migrations: ${String(foyerReadiness?.migrations?.status || "unknown")}`}</span>
              <span className={`badge ${String(foyerReadiness?.config?.status || "") === "up" ? "badge-ok" : String(foyerReadiness?.config?.status || "") === "warning" ? "badge-warn" : ""}`}>{`Config: ${String(foyerReadiness?.config?.status || "unknown")}`}</span>
            </div>
            <div className="row">
              <span className={`badge ${foyerFederationStatus === "ok" ? "badge-ok" : foyerFederationStatus === "degraded" ? "badge-warn" : foyerFederationStatus === "error" ? "badge-error" : ""}`}>{`Federation: ${foyerFederationStatus}`}</span>
              <span className="badge">{`Targets: ${Number(foyerFederation?.target_count || 0)}`}</span>
              <span className="badge">{`Active trust: ${Number(foyerFederation?.active_trust_count || 0)}`}</span>
              <span className={`badge ${foyerFederationTrust === "active" ? "badge-ok" : foyerFederationTrust === "unreachable" || foyerFederationTrust === "untrusted" ? "badge-error" : foyerFederationTrust === "key_known" || foyerFederationTrust === "key_only" ? "badge-warn" : ""}`}>{`Current trust: ${foyerFederationTrust}`}</span>
            </div>
          </section>
          <section className="panel">
            <h2>Artisan Login</h2>
            {authToken ? (
              <div>
                <div className="row">
                  <span className="badge badge-ok">{`Signed in: ${artisanId} (${role})`}</span>
                  <button className="action" onClick={logout}>Sign Out</button>
                </div>
                <p>{`Workshop: ${workshopId || "—"}`}</p>
              </div>
            ) : (
              <div>
                <div className="row">
                  <input
                    value={loginArtisanId}
                    onChange={(e) => setLoginArtisanId(e.target.value)}
                    placeholder="artisan_id"
                  />
                  <input
                    type="password"
                    value={loginArtisanCode}
                    onChange={(e) => setLoginArtisanCode(e.target.value)}
                    placeholder="artisan code (AID-...)"
                    onKeyDown={(e) => { if (e.key === "Enter") void login(); }}
                  />
                  <button className="action" onClick={login}>Sign In</button>
                </div>
                {loginError && <p className="error-text">{loginError}</p>}
                <p className="muted-text">No account yet? Use an invite code below to register.</p>
              </div>
            )}
          </section>
          {!authToken && (
            <section className="panel">
              <h2>Redeem Invite</h2>
              <p className="muted-text">Enter your invite code and choose your credentials.</p>
              {onboardStatus === "done" ? (
                <p className="badge badge-ok">Welcome! You are now signed in.</p>
              ) : (
                <div>
                  <div className="row">
                    <input
                      value={onboardCode}
                      onChange={(e) => setOnboardCode(e.target.value)}
                      placeholder="DJINN-XXXXXXXX"
                      style={{ fontFamily: "monospace", textTransform: "uppercase" }}
                    />
                    <input
                      value={onboardArtisanId}
                      onChange={(e) => setOnboardArtisanId(e.target.value)}
                      placeholder="choose artisan_id"
                    />
                  </div>
                  <div className="row">
                    <input
                      value={onboardName}
                      onChange={(e) => setOnboardName(e.target.value)}
                      placeholder="display name"
                    />
                    <input
                      value={onboardEmail}
                      onChange={(e) => setOnboardEmail(e.target.value)}
                      placeholder="email"
                      type="email"
                    />
                    <input
                      type="password"
                      value={onboardPassword}
                      onChange={(e) => setOnboardPassword(e.target.value)}
                      placeholder="password (8+ chars)"
                    />
                    <button className="action" onClick={redeemInvite} disabled={onboardStatus === "redeeming"}>
                      {onboardStatus === "redeeming" ? "Joining..." : "Join"}
                    </button>
                  </div>
                  {onboardError && <p className="error-text">{onboardError}</p>}
                </div>
              )}
            </section>
          )}
          {authToken && (role === "steward" || role === "senior_artisan") && (
            <section className="panel">
              <h2>Issue Invite</h2>
              <div className="row">
                <select value={issueInviteRole} onChange={(e) => setIssueInviteRole(e.target.value)}>
                  <option value="apprentice">Apprentice</option>
                  <option value="artisan">Artisan</option>
                  <option value="senior_artisan">Senior Artisan</option>
                </select>
                <input
                  value={issueInviteNote}
                  onChange={(e) => setIssueInviteNote(e.target.value)}
                  placeholder="optional note"
                />
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={issueInviteMaxUses}
                  onChange={(e) => setIssueInviteMaxUses(Number(e.target.value))}
                  style={{ width: 70 }}
                  title="Max uses"
                />
                <button className="action" onClick={issueInvite}>Generate Code</button>
              </div>
              {issuedInviteCode && (
                <div className="row">
                  <span className="muted-text">Code:</span>
                  <code style={{ userSelect: "all", cursor: "text" }}>{issuedInviteCode}</code>
                  <button className="action" onClick={() => { navigator.clipboard?.writeText(issuedInviteCode); }}>Copy</button>
                  <button className="action" onClick={() => setIssuedInviteCode("")}>Clear</button>
                </div>
              )}
            </section>
          )}
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
            <h2>Workspace Manager</h2>
            <p>{`Current workspace: ${workspaceId}`}</p>
            {workspaceList.length > 0 && (
              <table className="data-table">
                <thead><tr><th>Name</th><th>ID</th><th>Role</th><th>Status</th></tr></thead>
                <tbody>
                  {workspaceList.map((ws) => (
                    <tr key={ws.id} className={ws.id === workspaceId ? "selected-row" : ""}>
                      <td>{ws.name}</td>
                      <td><code>{ws.id}</code></td>
                      <td>{ws.role}</td>
                      <td>{ws.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <button className="action" onClick={fetchMyWorkspace}>Refresh Workspaces</button>
            {role === "steward" && (
              <>
                <h3>Create Workspace (Steward)</h3>
                <div className="row">
                  <input value={newWorkspaceName} onChange={(e) => setNewWorkspaceName(e.target.value)} placeholder="workspace name" />
                  <input value={newWorkspaceOwner} onChange={(e) => setNewWorkspaceOwner(e.target.value)} placeholder="owner artisan_id" />
                  <button className="action" onClick={createWorkspace}>Create Workspace</button>
                </div>
                <h3>Add Workspace Member (Steward)</h3>
                <div className="row">
                  <input value={addMemberWorkspaceId} onChange={(e) => setAddMemberWorkspaceId(e.target.value)} placeholder="workspace id" />
                  <input value={addMemberArtisanId} onChange={(e) => setAddMemberArtisanId(e.target.value)} placeholder="artisan_id to add" />
                  <select value={addMemberRole} onChange={(e) => setAddMemberRole(e.target.value)}>
                    <option value="member">Member</option>
                    <option value="owner">Owner</option>
                    <option value="collaborator">Collaborator</option>
                  </select>
                  <button className="action" onClick={addWorkspaceMember}>Add Member</button>
                </div>
              </>
            )}
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
                  <input value={spriteColor} onChange={(e) => setSpriteColor(e.target.value)} placeholder="sprite color (#rrggbb)" />
                  <input
                    type="color"
                    value={parseHexColor(spriteColor) ? spriteColor : "#7aa2ff"}
                    onChange={(e) => setSpriteColor(e.target.value)}
                    title="sprite color picker"
                  />
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
            <input value={bookingContactId} onChange={(e) => setBookingContactId(e.target.value)} placeholder="Lead or contact ID (optional)" />
            <button className="action" onClick={() => createEntity("bookings_create", "/v1/booking", { workspace_id: workspaceId, starts_at: bookingStart, ends_at: bookingEnd, status: "scheduled", contact_id: bookingContactId || null, notes: bookingNotes }, () => { setBookingContactId(""); setBookingNotes(""); }, listBookings)}>Create</button>
            <button className="action" onClick={listBookings}>Refresh</button>
          </div>
          <div className="row">
            <textarea value={bookingNotes} onChange={(e) => setBookingNotes(e.target.value)} placeholder="booking notes" />
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
            <button className="action" onClick={validateLessonDraft}>Validate Shygazun Lesson</button>
            <button className="action" onClick={createLessonDraft}>Create</button>
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
          <pre>{JSON.stringify(lessonValidationOutput || {}, null, 2)}</pre>
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
            <input value={leadPhone} onChange={(e) => setLeadPhone(e.target.value)} placeholder="lead phone" />
            <button
              className="action"
              onClick={() =>
                createEntity(
                  "leads_create",
                  "/v1/leads",
                  {
                    workspace_id: workspaceId,
                    full_name: leadName,
                    email: leadEmail || null,
                    phone: leadPhone || null,
                    details: leadDetails,
                    status: "new",
                    source: leadSource,
                    notes: leadNotes
                  },
                  () => {
                    setLeadName("");
                    setLeadEmail("");
                    setLeadPhone("");
                    setLeadDetails("");
                    setLeadSource("internal");
                    setLeadNotes("");
                  },
                  listLeads
                )
              }
            >
              Create
            </button>
            <button className="action" onClick={listLeads}>Refresh</button>
          </div>
          <div className="row">
            <input value={leadDetails} onChange={(e) => setLeadDetails(e.target.value)} placeholder="lead details" />
            <select value={leadSource} onChange={(e) => setLeadSource(e.target.value)}>
              <option value="internal">internal</option>
              <option value="referral">referral</option>
              <option value="shop:consultations">shop:consultations</option>
              <option value="shop:licenses">shop:licenses</option>
              <option value="shop:catalog">shop:catalog</option>
              <option value="shop:custom-orders">shop:custom-orders</option>
              <option value="shop:digital">shop:digital</option>
              <option value="shop:land-assessments">shop:land-assessments</option>
              <option value="other">other</option>
            </select>
          </div>
          <div className="row">
            <textarea value={leadNotes} onChange={(e) => setLeadNotes(e.target.value)} placeholder="lead notes" />
            <input value={leadFilter} onChange={(e) => setLeadFilter(e.target.value)} placeholder="filter leads" />
          </div>
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
            <button className="action" onClick={() => createEntity("clients_create", "/v1/clients", { workspace_id: workspaceId, full_name: clientName, email: clientEmail || null, phone: clientPhone || null, status: "active", notes: clientNotes }, () => { setClientName(""); setClientEmail(""); setClientPhone(""); setClientNotes(""); }, listClients)}>Create</button>
            <button className="action" onClick={listClients}>Refresh</button>
          </div>
          <div className="row">
            <textarea value={clientNotes} onChange={(e) => setClientNotes(e.target.value)} placeholder="client notes" />
            <input value={clientFilter} onChange={(e) => setClientFilter(e.target.value)} placeholder="filter clients" />
          </div>
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
              <input value={quoteLeadId} onChange={(e) => setQuoteLeadId(e.target.value)} placeholder="Lead ID (optional)" />
              <button className="action" onClick={() => createEntity("quotes_create", "/v1/quotes", { workspace_id: workspaceId, title: quoteTitle, amount_cents: Number.parseInt(quoteAmount || "0", 10), currency: quoteCurrency, status: quotePublic ? "published" : "draft", is_public: quotePublic, lead_id: quoteLeadId || null, notes: quoteNotes }, () => { setQuoteTitle(""); setQuoteAmount(""); setQuotePublic(false); setQuoteLeadId(""); setQuoteNotes(""); }, listQuotes)}>Create</button>
              <button className="action" onClick={listQuotes}>Refresh</button>
            </div>
            <div className="row">
              <textarea value={quoteNotes} onChange={(e) => setQuoteNotes(e.target.value)} placeholder="quote notes" />
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
            <input value={orderQuoteId} onChange={(e) => setOrderQuoteId(e.target.value)} placeholder="Quote ID (optional)" />
            <input value={orderClientId} onChange={(e) => setOrderClientId(e.target.value)} placeholder="Client ID (optional)" />
            <button className="action" onClick={() => createEntity("orders_create", "/v1/orders", { workspace_id: workspaceId, title: orderTitle, amount_cents: Number.parseInt(orderAmount || "0", 10), currency: orderCurrency, status: "open", quote_id: orderQuoteId || null, client_id: orderClientId || null, notes: orderNotes }, () => { setOrderTitle(""); setOrderAmount(""); setOrderQuoteId(""); setOrderClientId(""); setOrderNotes(""); }, listOrders)}>Create</button>
            <button className="action" onClick={listOrders}>Refresh</button>
          </div>
          <div className="row">
            <textarea value={orderNotes} onChange={(e) => setOrderNotes(e.target.value)} placeholder="order notes" />
          </div>
          <div className="row"><input value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)} placeholder="filter orders" /></div>
          <pre>{JSON.stringify(filteredOrders, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Contracts") {
      return (
        <section className="panel">
          <h2>Contracts</h2>
          <div className="row">
            <input value={contractTitle} onChange={(e) => setContractTitle(e.target.value)} placeholder="contract title" />
            <select value={contractCategory} onChange={(e) => setContractCategory(e.target.value)}>
              <option value="consultations">consultations</option>
              <option value="licenses">licenses</option>
              <option value="catalog">catalog</option>
              <option value="custom-orders">custom-orders</option>
              <option value="digital">digital</option>
              <option value="land-assessments">land-assessments</option>
              <option value="general">general</option>
            </select>
            <input value={contractPartyName} onChange={(e) => setContractPartyName(e.target.value)} placeholder="party name" />
            <input value={contractPartyEmail} onChange={(e) => setContractPartyEmail(e.target.value)} placeholder="party email" />
          </div>
          <div className="row">
            <input value={contractPartyPhone} onChange={(e) => setContractPartyPhone(e.target.value)} placeholder="party phone" />
            <input value={contractArtisanId} onChange={(e) => setContractArtisanId(e.target.value)} placeholder="artisan id (optional)" />
            <input value={contractAmount} onChange={(e) => setContractAmount(e.target.value)} placeholder="amount cents" />
            <input value={contractCurrency} onChange={(e) => setContractCurrency(e.target.value)} placeholder="currency" />
          </div>
          <div className="row">
            <textarea value={contractTerms} onChange={(e) => setContractTerms(e.target.value)} placeholder="terms" rows={4} />
            <textarea value={contractNotes} onChange={(e) => setContractNotes(e.target.value)} placeholder="notes" rows={4} />
          </div>
          <div className="row">
            <button className="action" onClick={createContract}>Create</button>
            <button className="action" onClick={updateContract}>Update</button>
            <button className="action" onClick={listContracts}>Refresh</button>
          </div>
          <div className="row">
            <select value={contractSelectedId} onChange={(e) => setContractSelectedId(e.target.value)}>
              <option value="">select contract</option>
              {contracts.map((item) => (
                <option key={`contract-${String(item?.id || "")}`} value={String(item?.id || "")}>
                  {`${String(item?.id || "")} :: ${String(item?.title || "")}`}
                </option>
              ))}
            </select>
            <button className="action" onClick={validateContract} disabled={!adminVerified || role !== "steward"}>Validate</button>
            <button className="action" onClick={cancelContract} disabled={!adminVerified || role !== "steward"}>Cancel</button>
            <button className="action" onClick={processContract} disabled={!adminVerified || role !== "steward"}>Process</button>
          </div>
          <div className="row">
            <input value={contractFilter} onChange={(e) => setContractFilter(e.target.value)} placeholder="filter contracts" />
          </div>
          <pre>{JSON.stringify(filteredContracts, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Ledger") {
      return (
        <section className="panel">
          <h2>Ledger</h2>
          <div className="row">
            <input value={ledgerMonth} onChange={(e) => setLedgerMonth(e.target.value)} placeholder="YYYY-MM" />
            <button className="action" onClick={loadLedgerEntries} disabled={!adminVerified || role !== "steward"}>Load Entries</button>
            <button className="action" onClick={loadLedgerSummary} disabled={!adminVerified || role !== "steward"}>Load Summary</button>
            <button className="action" onClick={() => runLedgerPayouts(true)} disabled={!adminVerified || role !== "steward"}>Dry Run Payouts</button>
            <button className="action" onClick={() => runLedgerPayouts(false)} disabled={!adminVerified || role !== "steward"}>Run Payouts</button>
          </div>
          <div className="row">
            <button className="action" onClick={exportLedgerCsv} disabled={!adminVerified || role !== "steward"}>Export CSV</button>
            <button className="action" onClick={exportLedger1099} disabled={!adminVerified || role !== "steward"}>Export 1099 CSV</button>
          </div>
          <pre>{JSON.stringify(ledgerSummary || {}, null, 2)}</pre>
          <pre>{JSON.stringify(ledgerEntries, null, 2)}</pre>
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
    if (section === "Business Logic") {
      return (
        <>
          <section className="panel unified-renderer">
            <h2>Business Architecture Renderer</h2>
            <p>Isolated architecture workspace for business model organization and tool/systems design.</p>
            <div className="row">
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={businessLogicRendererUseDerived}
                  onChange={(e) => setBusinessLogicRendererUseDerived(e.target.checked)}
                />
                Use derived state model
              </label>
              <select value={businessLogicRendererInputMode} onChange={(e) => setBusinessLogicRendererInputMode(e.target.value)}>
                <option value="json">Input: JSON</option>
                <option value="english">Input: English</option>
                <option value="cobra">Input: Cobra</option>
                <option value="shygazun">Input: Shygazun</option>
              </select>
              <button className="action" onClick={loadBusinessLogicArchitectureTemplate}>Load Template</button>
              <button className="action" onClick={snapshotDerivedArchitectureToBusinessLogicInput}>Snapshot Derived</button>
              <button className="action" onClick={applyBusinessLogicCobraToUnifiedRenderer}>Apply Cobra {"->"} Unified Renderer</button>
              <span className={`badge ${businessLogicRendererSpecResult.error ? "err" : "ok"}`}>{`Status: ${businessLogicRendererStatus}`}</span>
              <span className="badge">{`Nodes: ${businessLogicArchitectureModel.nodes.length}`}</span>
              <span className="badge">{`Flows: ${businessLogicArchitectureModel.flows.length}`}</span>
              <span className="badge">{`Lanes: ${businessLogicArchitectureModel.lanes.length}`}</span>
            </div>
            <canvas
              ref={businessLogicRendererCanvasRef}
              className="unified-canvas"
              style={{ minHeight: "420px", touchAction: "none" }}
            />
            <textarea
              className="editor editor-mono renderer-editor"
              value={businessLogicRendererInputText}
              onChange={(e) => setBusinessLogicRendererInputText(e.target.value)}
              placeholder={
                businessLogicRendererInputMode === "json"
                  ? "JSON architecture spec"
                  : businessLogicRendererInputMode === "english"
                    ? "domain crm: CRM\nsystem contacts in crm: Contacts Service\nflow contacts -> db12: persist"
                    : businessLogicRendererInputMode === "cobra"
                      ? "domain crm CRM\nsystem contacts Contacts Service\nflow contacts db12 persist"
                      : "Ty crm CRM\nWu contacts Contacts Service\nRu contacts db12 persist"
              }
            />
          </section>
          <section className="panel">
            <h2>Game System Creator</h2>
            <p>Author and move game content between Cobra, scene library, renderer state, and save export.</p>
            <div className="row">
              <select value={actionPostTarget} onChange={(e) => setActionPostTarget(e.target.value)}>
                <option value="api">POST Target: API (:9000)</option>
                <option value="engine_inbox">POST Target: Engine Script Inbox</option>
                <option value="repo">POST Target: In-App Repo File</option>
              </select>
              {actionPostTarget === "engine_inbox" ? (
                <select value={actionPostEngineFileId} onChange={(e) => setActionPostEngineFileId(e.target.value)}>
                  <option value="">engine script (optional)</option>
                  {studioFiles.map((file) => (
                    <option key={`biz-post-engine-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
              ) : null}
              {actionPostTarget === "repo" ? (
                <input
                  value={actionPostRepoFolder}
                  onChange={(e) => setActionPostRepoFolder(e.target.value)}
                  placeholder="repo folder (e.g. runtime-posts)"
                />
              ) : null}
              <span className="badge">{`Active target: ${actionPostTarget}`}</span>
            </div>
            <div className="row">
              <button className="action" onClick={compileSceneFromCobra}>Compile Cobra {"->"} Scene + Renderer State (API)</button>
              <button className="action" onClick={loadSceneFromLibraryToRenderer}>Load Library Scene {"->"} Renderer State (API)</button>
              <button className="action" onClick={emitSceneGraph}>POST Scene Graph Payload</button>
              <button className="action" onClick={emitHeadlessQuest}>POST Headless Quest Payload</button>
              <button className="action" onClick={emitMeditation}>POST Meditation Payload</button>
              <button className="action" onClick={exportGameSave}>Fetch Save Snapshot</button>
              <button className="action" onClick={() => saveExport && downloadJson(`game-save-${workspaceId}.json`, saveExport)}>Download Save JSON</button>
            </div>
            <div className="row">
              <input value={sceneCompileSceneId} onChange={(e) => setSceneCompileSceneId(e.target.value)} placeholder="scene id (realm/scene)" />
              <input value={rendererLibrarySceneId} onChange={(e) => setRendererLibrarySceneId(e.target.value)} placeholder="load scene id (realm/scene)" />
              <input value={sceneCompileName} onChange={(e) => setSceneCompileName(e.target.value)} placeholder="scene name" />
              <input value={sceneCompileDescription} onChange={(e) => setSceneCompileDescription(e.target.value)} placeholder="scene description" />
              <span className="badge">{`Realm: ${rendererRealmId}`}</span>
            </div>
            <h3>Headless Quest Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={headlessQuestText} onChange={(e) => setHeadlessQuestText(e.target.value)} />
            <h3>Meditation Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={meditationText} onChange={(e) => setMeditationText(e.target.value)} />
            <h3>Scene Graph Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={sceneGraphText} onChange={(e) => setSceneGraphText(e.target.value)} />
            <h3>Save Export</h3>
            <pre>{JSON.stringify(saveExport || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>Module Browser</h2>
            <p>Discover, validate, inspect, and execute runtime modules from <code>gameplay/modules</code>.</p>
            <div className="row">
              <button className="action" onClick={listModuleCatalog}>Refresh Modules</button>
              <select value={moduleSelectedId} onChange={(e) => setModuleSelectedId(e.target.value)}>
                <option value="">select module</option>
                {moduleCatalog.map((mod) => {
                  const id = String(mod && mod.module_id ? mod.module_id : "");
                  return (
                    <option key={`module-opt-${id}`} value={id}>
                      {id}
                    </option>
                  );
                })}
              </select>
              <button className="action" onClick={fetchSelectedModuleSpec}>Load Spec</button>
              <button className="action" onClick={validateSelectedModuleSpec}>Validate</button>
              <button className="action" onClick={runSelectedModuleSpec}>Run via module.run</button>
              <span className="badge">{`Modules: ${moduleCatalog.length}`}</span>
            </div>
            <div className="row">
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={moduleAutoReconcile}
                  onChange={(e) => setModuleAutoReconcile(e.target.checked)}
                />
                Auto-Reconcile Scene
              </label>
              <input
                value={moduleReconcileSceneId}
                onChange={(e) => setModuleReconcileSceneId(e.target.value)}
                placeholder="scene id (realm/scene or scene)"
              />
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={moduleReconcileApply}
                  onChange={(e) => setModuleReconcileApply(e.target.checked)}
                />
                Reconcile Apply
              </label>
            </div>
            <h3>Payload Overrides (JSON)</h3>
            <textarea
              className="editor editor-mono renderer-editor"
              value={moduleRunOverridesText}
              onChange={(e) => setModuleRunOverridesText(e.target.value)}
              placeholder='{"key":"value"}'
            />
            <h3>Selected Spec</h3>
            <pre>{JSON.stringify(moduleSelectedSpec || {}, null, 2)}</pre>
            <h3>Validation Result</h3>
            <pre>{JSON.stringify(moduleValidateOutput || {}, null, 2)}</pre>
            <h3>Run Result</h3>
            <pre>{JSON.stringify(moduleRunOutput || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>RPG Rule Engine</h2>
            <p>Deterministic rule payload execution to API, engine inbox, or repo-backed action stream.</p>
            <div className="row">
              <span className="badge">{`POST target: ${actionPostTarget}`}</span>
            </div>
            <div className="row">
              <button className="action" onClick={() => runGameRule("/v1/game/rules/levels/apply", levelRuleText, "game_rule_level_apply")}>POST Level Apply</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/skills/train", skillRuleText, "game_rule_skill_train")}>POST Skill Train</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/perks/unlock", perkRuleText, "game_rule_perk_unlock")}>POST Perk Unlock</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/alchemy/craft", alchemyRuleText, "game_rule_alchemy_craft")}>POST Alchemy Craft</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/blacksmith/forge", blacksmithRuleText, "game_rule_blacksmith_forge")}>POST Blacksmith Forge</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/combat/resolve", combatRuleText, "game_rule_combat_resolve")}>POST Combat Resolve</button>
            </div>
            <div className="row">
              <button className="action" onClick={() => runGameRule("/v1/game/rules/market/quote", marketQuoteText, "game_rule_market_quote")}>POST Market Quote</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/market/trade", marketTradeText, "game_rule_market_trade")}>POST Market Trade</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/apply-ruler-influence", vitriolApplyText, "game_vitriol_apply")}>POST VITRIOL Apply Influence</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/compute", vitriolComputeText, "game_vitriol_compute")}>POST VITRIOL Compute</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/clear-expired", vitriolClearText, "game_vitriol_clear_expired")}>POST VITRIOL Clear Expired</button>
            </div>
            <h3>Level Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={levelRuleText} onChange={(e) => setLevelRuleText(e.target.value)} />
            <h3>Skill Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={skillRuleText} onChange={(e) => setSkillRuleText(e.target.value)} />
            <h3>Perk Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={perkRuleText} onChange={(e) => setPerkRuleText(e.target.value)} />
            <h3>Alchemy Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={alchemyRuleText} onChange={(e) => setAlchemyRuleText(e.target.value)} />
            <h3>Blacksmith Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={blacksmithRuleText} onChange={(e) => setBlacksmithRuleText(e.target.value)} />
            <h3>Combat Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={combatRuleText} onChange={(e) => setCombatRuleText(e.target.value)} />
            <h3>Market Quote Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={marketQuoteText} onChange={(e) => setMarketQuoteText(e.target.value)} />
            <h3>Market Trade Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={marketTradeText} onChange={(e) => setMarketTradeText(e.target.value)} />
            <h3>VITRIOL Apply Payload (1..10 per axis)</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolApplyText} onChange={(e) => setVitriolApplyText(e.target.value)} />
            <h3>VITRIOL Compute Payload (1..10 per axis)</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolComputeText} onChange={(e) => setVitriolComputeText(e.target.value)} />
            <h3>VITRIOL Clear-Expired Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolClearText} onChange={(e) => setVitriolClearText(e.target.value)} />
            <h3>Rule Output</h3>
            <pre>{JSON.stringify(gameRulesOutput || {}, null, 2)}</pre>
          </section>
        </>
      );
    }
    if (section === "Renderer Lab") {
      return (
        <>
          <section className="panel">
            <RenderLabPanel
              onRunGateA={runRendererGateASmoke}
              onRunGateD={runRendererGateDSmoke}
              onBootstrap={runGuidedLabBootstrap}
              labCoherence={labCoherence}
              setLabCoherence={setLabCoherence}
              moduleRunOutput={moduleRunOutput}
              rendererRealmId={rendererRealmId}
            />
          </section>
          <section className="panel">
            <h2>Runtime Launcher (No CLI)</h2>
            <p>Canonical flow: health check {"->"} main plan {"->"} scene graph. No terminal commands required.</p>
            <div className="row">
              <button className="action" onClick={runGuidedLabBootstrap}>Run Guided Bootstrap</button>
              <button className="action" onClick={runCanonicalMainPlanFromUi}>Run Canonical Main Plan</button>
              <button className="action" onClick={runStudioHealthCheck}>Run Studio Health Check</button>
              <button className="action" onClick={runRendererGateASmoke}>Run Gate A Smoke</button>
              <button className="action" onClick={runRendererGateDSmoke}>Run Gate D Smoke</button>
              <button className="action" onClick={listModuleCatalog}>Refresh Module Catalog</button>
              <button className="action" onClick={fetchWorldStreamStatus}>Refresh World Stream</button>
              <span className="badge">{`Status: ${rendererGameStatus || "idle"}`}</span>
              <span className="badge">{`Modules: ${moduleCatalog.length}`}</span>
            </div>
            <div className="row">
              <span className={`badge ${labCoherence.runtime_consume_ok === true ? "ok" : labCoherence.runtime_consume_ok === false ? "err" : ""}`}>
                {`Runtime Consume: ${labCoherence.runtime_consume_ok === null ? "unknown" : labCoherence.runtime_consume_ok ? "ok" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.module_catalog_ok === true ? "ok" : labCoherence.module_catalog_ok === false ? "err" : ""}`}>
                {`Module Catalog: ${labCoherence.module_catalog_ok === null ? "unknown" : labCoherence.module_catalog_ok ? "ok" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.world_stream_ok === true ? "ok" : labCoherence.world_stream_ok === false ? "err" : ""}`}>
                {`World Stream: ${labCoherence.world_stream_ok === null ? "unknown" : labCoherence.world_stream_ok ? "ok" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.main_plan_ok === true ? "ok" : labCoherence.main_plan_ok === false ? "err" : ""}`}>
                {`Main Plan: ${labCoherence.main_plan_ok === null ? "unknown" : labCoherence.main_plan_ok ? "ok" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.guided_bootstrap_ok === true ? "ok" : labCoherence.guided_bootstrap_ok === false ? "err" : ""}`}>
                {`Bootstrap: ${labCoherence.guided_bootstrap_ok === null ? "unknown" : labCoherence.guided_bootstrap_ok ? "ok" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.gate_a_ok === true ? "ok" : labCoherence.gate_a_ok === false ? "err" : ""}`}>
                {`Gate A: ${labCoherence.gate_a_ok === null ? "unknown" : labCoherence.gate_a_ok ? "pass" : "fail"}`}
              </span>
              <span className={`badge ${labCoherence.gate_d_ok === true ? "ok" : labCoherence.gate_d_ok === false ? "err" : ""}`}>
                {`Gate D: ${labCoherence.gate_d_ok === null ? "unknown" : labCoherence.gate_d_ok ? "pass" : "fail"}`}
              </span>
              <span className="badge">{`Last Check: ${labCoherence.last_check_at || "n/a"}`}</span>
            </div>
            <pre>{JSON.stringify(moduleRunOutput || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>Multi-Frame Renderer</h2>
            <p>Programmable structural renderer with independent Python, Cobra, JavaScript, and JSON frames.</p>
            <div className="row">
              <button className="action" onClick={stepRendererEngine}>Step Engine Tick</button>
              <button className="action" onClick={emitCobraPlacements}>Emit Cobra Placements</button>
              <button className="action" onClick={compileSceneGraphPreview}>Compile Scene Graph</button>
              <button className="action" onClick={() => setRendererEngineStateText(JSON.stringify({ tick: 0, camera: { x: 0, y: 0 } }, null, 2))}>Reset Engine</button>
            </div>
            <section className="panel unified-renderer">
              <h3>Business Architecture Renderer</h3>
              <p>Architecture-focused canvas for business model organization and tool/systems design.</p>
              <div className="row">
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={businessRendererUseDerived}
                    onChange={(e) => setBusinessRendererUseDerived(e.target.checked)}
                  />
                  Use derived state model
                </label>
                <select value={businessRendererInputMode} onChange={(e) => setBusinessRendererInputMode(e.target.value)}>
                  <option value="json">Input: JSON</option>
                  <option value="english">Input: English</option>
                  <option value="cobra">Input: Cobra</option>
                  <option value="shygazun">Input: Shygazun</option>
                </select>
                <button className="action" onClick={loadBusinessArchitectureTemplate}>Load Template</button>
                <button className="action" onClick={snapshotDerivedArchitectureToInput}>Snapshot Derived</button>
                <span className={`badge ${businessRendererSpecResult.error ? "err" : "ok"}`}>{`Status: ${businessRendererStatus}`}</span>
                <span className="badge">{`Nodes: ${businessArchitectureModel.nodes.length}`}</span>
                <span className="badge">{`Flows: ${businessArchitectureModel.flows.length}`}</span>
                <span className="badge">{`Lanes: ${businessArchitectureModel.lanes.length}`}</span>
              </div>
              <canvas
                ref={businessRendererCanvasRef}
                className="unified-canvas"
                style={{ minHeight: "420px", touchAction: "none" }}
              />
              <textarea
                className="editor editor-mono renderer-editor"
                value={businessRendererInputText}
                onChange={(e) => setBusinessRendererInputText(e.target.value)}
                placeholder={
                  businessRendererInputMode === "json"
                    ? "JSON architecture spec"
                    : businessRendererInputMode === "english"
                      ? "domain crm: CRM\nsystem contacts in crm: Contacts Service\nflow contacts -> db12: persist"
                      : businessRendererInputMode === "cobra"
                        ? "domain crm CRM\nsystem contacts Contacts Service\nflow contacts db12 persist"
                        : "Ty crm CRM\nWu contacts Service\nRu contacts db12 persist"
                }
              />
            </section>
            <section className="panel unified-renderer">
              <h3>Unified Visual Renderer</h3>
              <p>Single visual surface fed by JSON, Cobra entities, or Engine state.</p>
              <div className="row">
                <select value={rendererVisualSource} onChange={(e) => setRendererVisualSource(e.target.value)}>
                  <option value="json">JSON Scene Layer</option>
                  <option value="cobra">Cobra Layer</option>
                  <option value="javascript">JavaScript Layer</option>
                  <option value="python">Python Layer</option>
                  <option value="engine">Engine State</option>
                </select>
                <select value={rendererRealmId} onChange={(e) => setRendererRealmId(e.target.value)}>
                  <option value="lapidus">Lapidus</option>
                  <option value="mercurie">Mercurie</option>
                  <option value="sulphera">Sulphera</option>
                </select>
                <span className="badge">{`Realm: ${rendererRealmId}`}</span>
                <span className="badge">{`Render: ${effectiveVoxelSettings.renderMode === "3d" ? "3D" : "2.5D"}`}</span>
                <span className={`badge ${rendererAssetDiagnostics && rendererAssetDiagnostics.ok ? "ok" : ""}`}>
                  {`Assets: ${rendererAssetDiagnostics ? (rendererAssetDiagnostics.ok ? "ok" : "issues") : "unchecked"}`}
                </span>
                <span
                  className={`badge ${validationSummary.ok ? "ok" : "err"}`}
                  title={
                    contentValidateSceneId && !contentValidateSceneId.startsWith(`${rendererRealmId}/`)
                      ? `Scene id mismatch: expected ${rendererRealmId}/... got ${contentValidateSceneId}`
                      : `Validation summary for ${rendererRealmId}`
                  }
                >
                  {`Validate: ${validationSummary.errors} err / ${validationSummary.warnings} warn`}
                </span>
                <span className="badge">{`Voxels: ${rendererMotionVoxels.length}`}</span>
                <span className="badge">{`Parse: ${rendererParseStatus}`}</span>
                <span className="badge">{`Prep: ${rendererVoxelPrepStatus}`}</span>
                <button className="action" onClick={runRendererAssetDiagnostics}>Asset Diagnostics</button>
                <button className="action" onClick={openFullscreenRenderer}>Open Fullscreen</button>
              </div>
              <div className="row">
                <button className="action" onClick={handleBuildCollisionMap} disabled={rendererMotionVoxels.length === 0}>
                  Build Collision Map
                </button>
                {collisionMap && (
                  <>
                    <label className="inline-toggle">
                      <input
                        type="checkbox"
                        checked={showCollisionOverlay}
                        onChange={(e) => handleToggleCollisionOverlay(e.target.checked)}
                      />
                      Show Overlay
                    </label>
                    <button className="action" onClick={handleExportCollisionMap}>Export Collision JSON</button>
                    <span className="badge" style={{ color: "var(--accent-green, #2ecc71)" }}>
                      {`Pass: ${collisionMap.stats.passable_count}`}
                    </span>
                    <span className="badge" style={{ color: "var(--danger, #e74c3c)" }}>
                      {`Block: ${collisionMap.stats.impassable_count}`}
                    </span>
                    {collisionMap.stats.inferred_count > 0 && (
                      <span className="badge" style={{ color: "var(--warn, #f39c12)" }}>
                        {`Inferred: ${collisionMap.stats.inferred_count}`}
                      </span>
                    )}
                  </>
                )}
              </div>
              <div className="row">
                <button
                  className="action"
                  onClick={handleExportGlb}
                  disabled={rendererMotionVoxels.length === 0}
                >
                  Export .glb
                </button>
                <label className="action" style={{ cursor: "pointer" }}>
                  Import .glb / .gltf
                  <input
                    ref={gltfImportRef}
                    type="file"
                    accept=".glb,.gltf"
                    style={{ display: "none" }}
                    onChange={handleImportGltf}
                  />
                </label>
                {gltfImportStatus !== "idle" && (
                  <span
                    className="badge"
                    style={{ color: gltfImportStatus.startsWith("error") ? "var(--danger, #e74c3c)" : gltfImportStatus.startsWith("imported") ? "var(--accent-green, #2ecc71)" : "inherit" }}
                  >
                    {gltfImportStatus}
                  </span>
                )}
              </div>
              <div className="row">
                <input
                  value={rendererPlayerId}
                  onChange={(e) => setRendererPlayerId(e.target.value)}
                  placeholder="player id"
                />
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={rendererFollowPlayer}
                    onChange={(e) => setRendererFollowPlayer(e.target.checked)}
                  />
                  Follow Player
                </label>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={rendererKeyboardMotion}
                    onChange={(e) => setRendererKeyboardMotion(e.target.checked)}
                  />
                  Arrow-Key Motion
                </label>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={rendererClickMove}
                    onChange={(e) => setRendererClickMove(e.target.checked)}
                  />
                  Click-to-Move
                </label>
                <input
                  value={rendererPlayerStep}
                  onChange={(e) => setRendererPlayerStep(Number(e.target.value || 1))}
                  placeholder="step"
                />
                <input
                  value={rendererPathStepMs}
                  onChange={(e) => setRendererPathStepMs(Number(e.target.value || 75))}
                  placeholder="path ms"
                />
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={rendererGravityEnabled}
                    onChange={(e) => setRendererGravityEnabled(e.target.checked)}
                  />
                  Gravity
                </label>
                <input
                  value={rendererGravityMs}
                  onChange={(e) => setRendererGravityMs(Number(e.target.value || 150))}
                  placeholder="gravity ms"
                />
                <button
                  className="action"
                  onClick={() => {
                    setRendererMoveQueue([]);
                    applyActivePlayerOffset(() => ({ x: 0, y: 0, z: 0 }));
                  }}
                >
                  Reset Motion
                </button>
                <span className="badge">
                  {`Offset: ${Number(rendererPlayerOffset.x || 0)},${Number(rendererPlayerOffset.y || 0)},${Number(rendererPlayerOffset.z || 0)}`}
                </span>
                <span className="badge">{`Facing: ${normalizeFacing(rendererPlayerFacing)}`}</span>
                <span className="badge">{`Queued: ${rendererMoveQueue.length}`}</span>
                <span className="badge">Arrows move, click path-walks, Space jumps (+1Z)</span>
              </div>
              <canvas
                ref={unifiedRendererCanvasRef}
                className="unified-canvas"
                style={{ touchAction: "none" }}
                onPointerDown={(e) => handleRendererPointerDown(e, "main")}
                onPointerMove={(e) => handleRendererPointerMove(e, "main")}
                onPointerUp={(e) => handleRendererPointerUp(e, "main")}
                onPointerCancel={(e) => handleRendererPointerUp(e, "main")}
                onWheel={(e) => handleRendererWheel(e, "main")}
                onClick={(e) => handleRendererClickMove(e, "main")}
                onContextMenu={(e) => {
                  if (String(voxelSettings.renderMode || "2.5d").toLowerCase() === "3d") {
                    e.preventDefault();
                  }
                }}
              />
              <div className="row">
                <select
                  value={voxelSettings.renderMode || "2.5d"}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      renderMode: normalizeRenderMode(e.target.value),
                    }))
                  }
                >
                  <option value="2.5d">Render 2.5D</option>
                  <option value="2d">Render 2D</option>
                  <option value="3d">Render 3D</option>
                </select>
                <select
                  value={voxelSettings.projection || "isometric"}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      projection: e.target.value === "cardinal" ? "cardinal" : "isometric",
                    }))
                  }
                >
                  <option value="isometric">Projection: Isometric</option>
                  <option value="cardinal">Projection: Cardinal</option>
                </select>
                <input
                  value={voxelSettings.tile}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, tile: Number(e.target.value || 0) }))}
                  placeholder="tile size"
                />
                <input
                  value={voxelSettings.zScale}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, zScale: Number(e.target.value || 0) }))}
                  placeholder="height"
                />
                <select
                  value={String(voxelSettings.renderScale ?? 1)}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, renderScale: Number(e.target.value || 1) }))}
                >
                  <option value="1">Quality: 1x</option>
                  <option value="1.5">Quality: 1.5x</option>
                  <option value="2">Quality: 2x (HD)</option>
                  <option value="3">Quality: 3x (Ultra)</option>
                </select>
                <select
                  value={voxelSettings.visualStyle || "default"}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, visualStyle: e.target.value }))}
                >
                  <option value="default">Style: Default</option>
                  <option value="pokemon_ds">Style: Pokemon DS</option>
                  <option value="pokemon_g45">Style: Pokemon G4/G5</option>
                  <option value="classic_fallout">Style: Classic Fallout</option>
                </select>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(voxelSettings.pixelate)}
                    onChange={(e) => setVoxelSettings((prev) => ({ ...prev, pixelate: e.target.checked }))}
                  />
                  Pixelate
                </label>
                <input
                  value={voxelSettings.background}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, background: e.target.value }))}
                  placeholder="background"
                />
                <button className="action" onClick={applyPokemonDsPreset}>Pokemon DS Preset</button>
                <button className="action" onClick={applyPokemonG45Preset}>Pokemon G4/G5 Preset</button>
                <button className="action" onClick={applyClassicFalloutPreset}>Classic Fallout Preset</button>
                <button className="action" onClick={loadSpritesPreset}>Load Sprites Demo</button>
                <button className="action" onClick={loadStructuresPreset}>Load Structures Demo</button>
                <button className="action" onClick={loadLandscapePreset}>Load Landscape Demo</button>
                <button className="action" onClick={loadWorldCompositionPreset}>Load Full Composition</button>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={voxelSettings.outline}
                    onChange={(e) => setVoxelSettings((prev) => ({ ...prev, outline: e.target.checked }))}
                  />
                  Outline
                </label>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(voxelSettings.edgeGlow)}
                    onChange={(e) => setVoxelSettings((prev) => ({ ...prev, edgeGlow: e.target.checked }))}
                  />
                  Edge Glow
                </label>
                <input
                  value={voxelSettings.outlineColor}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, outlineColor: e.target.value }))}
                  placeholder="outline color"
                />
                <input
                  value={voxelSettings.edgeGlowColor ?? "#8fd3ff"}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, edgeGlowColor: e.target.value }))}
                  placeholder="glow color"
                />
                <input
                  value={voxelSettings.edgeGlowStrength ?? 8}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({ ...prev, edgeGlowStrength: Number(e.target.value || 0) }))
                  }
                  placeholder="glow strength"
                />
                <select
                  value={voxelSettings.labelMode}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, labelMode: e.target.value }))}
                >
                  <option value="none">Labels: none</option>
                  <option value="type">Labels: type</option>
                  <option value="z">Labels: z</option>
                  <option value="layer">Labels: layer</option>
                </select>
                <input
                  value={voxelSettings.labelColor}
                  onChange={(e) => setVoxelSettings((prev) => ({ ...prev, labelColor: e.target.value }))}
                  placeholder="label color"
                />
                {String(voxelSettings.visualStyle || "").toLowerCase() === "classic_fallout" ? (
                  <label className="inline-toggle">
                    <input
                      type="checkbox"
                      checked={Boolean(voxelSettings.classicFalloutShowLabels)}
                      onChange={(e) =>
                        setVoxelSettings((prev) => ({ ...prev, classicFalloutShowLabels: e.target.checked }))
                      }
                    />
                    Classic Fallout: Show Labels
                  </label>
                ) : null}
                <select
                  value={String((voxelSettings.lod && voxelSettings.lod.mode) || "auto_zoom")}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lod: { ...(prev.lod && typeof prev.lod === "object" ? prev.lod : {}), mode: e.target.value },
                    }))
                  }
                >
                  <option value="auto_zoom">LOD: Auto Zoom</option>
                  <option value="manual">LOD: Manual</option>
                </select>
                <input
                  value={Number((voxelSettings.lod && voxelSettings.lod.level) ?? 2)}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lod: {
                        ...(prev.lod && typeof prev.lod === "object" ? prev.lod : {}),
                        level: Number(e.target.value || 2),
                      },
                    }))
                  }
                  placeholder="lod level"
                />
                <span className="badge">{`LOD active: ${resolveInputLodLevel(voxelSettings)}`}</span>
              </div>
              <div className="row">
                <button className="action" onClick={applyRendererTestSpec}>Apply Test Spec</button>
                <button className="action" onClick={captureRendererTestSpecFromCurrent}>Capture Current</button>
                <span className="badge">{`Harness: ${rendererTestHarnessStatus}`}</span>
                <span className="badge">Code-first test runner</span>
              </div>
              <div className="row">
                <select value={rendererTestFragmentId} onChange={(e) => setRendererTestFragmentId(e.target.value)}>
                  {RENDERER_TEST_SPEC_FRAGMENTS.map((fragment) => (
                    <option key={fragment.id} value={fragment.id}>
                      {fragment.label}
                    </option>
                  ))}
                </select>
                <select value={rendererTestFragmentMode} onChange={(e) => setRendererTestFragmentMode(e.target.value)}>
                  <option value="merge">Insert: Merge</option>
                  <option value="append_voxels">Insert: Append Voxels</option>
                  <option value="replace">Insert: Replace Spec</option>
                </select>
                <button className="action" onClick={insertRendererTestSpecFragment}>Insert Fragment</button>
                <span className="badge">{`Fragments: ${RENDERER_TEST_SPEC_FRAGMENTS.length}`}</span>
              </div>
              <textarea
                className="editor editor-mono renderer-editor"
                value={rendererTestSpecText}
                onChange={(e) => setRendererTestSpecText(e.target.value)}
                placeholder="Renderer test spec JSON"
              />
              <p>
                Input LOD schema: set per voxel <code>lod</code> (e.g. min/max level or zoom) and optional
                <code>lod_variants</code> with <code>when</code> conditions.
              </p>
              {String(voxelSettings.renderMode || "2.5d").toLowerCase() === "3d" ? (
                <div className="row">
                  <input
                    value={voxelSettings.camera3d?.yaw ?? -35}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: normalizeCamera3d({ ...(prev.camera3d || {}), yaw: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="cam yaw"
                  />
                  <input
                    value={voxelSettings.camera3d?.pitch ?? 28}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: normalizeCamera3d({ ...(prev.camera3d || {}), pitch: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="cam pitch"
                  />
                  <input
                    value={voxelSettings.camera3d?.zoom ?? 1}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: normalizeCamera3d({ ...(prev.camera3d || {}), zoom: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="cam zoom"
                  />
                  <input
                    value={voxelSettings.camera3d?.panX ?? 0}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: normalizeCamera3d({ ...(prev.camera3d || {}), panX: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="cam pan x"
                  />
                  <input
                    value={voxelSettings.camera3d?.panY ?? 0}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: normalizeCamera3d({ ...(prev.camera3d || {}), panY: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="cam pan y"
                  />
                  <button
                    className="action"
                    onClick={() =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera3d: { yaw: -35, pitch: 28, zoom: 1, panX: 0, panY: 0 },
                      }))
                    }
                  >
                    Reset Camera
                  </button>
                  <span className="badge">Drag orbit, Shift/Right drag pan, wheel zoom</span>
                </div>
              ) : String(voxelSettings.projection || "isometric").toLowerCase() === "isometric" ? (
                <div className="row">
                  <input
                    value={normalizeCamera2d(voxelSettings.camera2d).zoom}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera2d: normalizeCamera2d({ ...(prev.camera2d || {}), zoom: Number(e.target.value || 1) }),
                      }))
                    }
                    placeholder="iso zoom"
                  />
                  <input
                    value={normalizeCamera2d(voxelSettings.camera2d).panX}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera2d: normalizeCamera2d({ ...(prev.camera2d || {}), panX: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="iso pan x"
                  />
                  <input
                    value={normalizeCamera2d(voxelSettings.camera2d).panY}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera2d: normalizeCamera2d({ ...(prev.camera2d || {}), panY: Number(e.target.value || 0) }),
                      }))
                    }
                    placeholder="iso pan y"
                  />
                  <button
                    className="action"
                    onClick={() =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        camera2d: normalizeCamera2d({ panX: 0, panY: 0, zoom: 1 }),
                      }))
                    }
                  >
                    Reset Iso Camera
                  </button>
                  <span className="badge">Drag pan + wheel zoom in isometric 2.5D</span>
                </div>
              ) : null}
              {rendererAssetDiagnostics ? (
                <pre>{JSON.stringify(rendererAssetDiagnostics, null, 2)}</pre>
              ) : null}
              <div className="row">
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(voxelSettings.lighting && voxelSettings.lighting.enabled)}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        lighting: { ...(prev.lighting || {}), enabled: e.target.checked }
                      }))
                    }
                  />
                  Lighting
                </label>
                <input
                  value={voxelSettings.lighting?.x ?? 0.4}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lighting: { ...(prev.lighting || {}), x: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="light x"
                />
                <input
                  value={voxelSettings.lighting?.y ?? -0.6}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lighting: { ...(prev.lighting || {}), y: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="light y"
                />
                <input
                  value={voxelSettings.lighting?.z ?? 0.7}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lighting: { ...(prev.lighting || {}), z: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="light z"
                />
                <input
                  value={voxelSettings.lighting?.ambient ?? 0.35}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lighting: { ...(prev.lighting || {}), ambient: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="ambient"
                />
                <input
                  value={voxelSettings.lighting?.intensity ?? 0.85}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      lighting: { ...(prev.lighting || {}), intensity: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="intensity"
                />
              </div>
              <div className="row">
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(voxelSettings.rose && voxelSettings.rose.enabled)}
                    onChange={(e) =>
                      setVoxelSettings((prev) => ({
                        ...prev,
                        rose: { ...(prev.rose || {}), enabled: e.target.checked }
                      }))
                    }
                  />
                  Rose Vector
                </label>
                <input
                  value={voxelSettings.rose?.strength ?? 0.35}
                  onChange={(e) =>
                    setVoxelSettings((prev) => ({
                      ...prev,
                      rose: { ...(prev.rose || {}), strength: Number(e.target.value || 0) }
                    }))
                  }
                  placeholder="rose strength"
                />
              </div>
              <div className="renderer-subgrid">
                <div className="renderer-subpanel">
                  <h4>Asset Packs</h4>
                  <div className="row">
                    <button className="action" onClick={loadAssetManifests}>Refresh Packs</button>
                    <span className="badge">{`Status: ${assetManifestStatus}`}</span>
                  </div>
                  <div className="row">
                    <select value={assetManifestSelected} onChange={(e) => setAssetManifestSelected(e.target.value)}>
                      <option value="">select manifest</option>
                      {assetManifests.map((manifest) => (
                        <option key={manifest.id} value={manifest.id}>
                          {manifest.name || manifest.manifest_id || manifest.id}
                        </option>
                      ))}
                    </select>
                    <button className="action" onClick={applyAssetManifest}>Apply Pack</button>
                  </div>
                  {assetManifests.length === 0 ? (
                    <p>No manifests loaded.</p>
                  ) : null}
                </div>
                <div className="renderer-subpanel">
                  <h4>Texture Atlases</h4>
                  <div className="row">
                    <input
                      value={voxelAtlasDraft.id}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, id: e.target.value }))}
                      placeholder="atlas id"
                    />
                    <input
                      value={voxelAtlasDraft.src}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, src: e.target.value }))}
                      placeholder="image url"
                    />
                    <input
                      value={voxelAtlasDraft.tileSize}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, tileSize: Number(e.target.value || 0) }))}
                      placeholder="tile"
                    />
                    <input
                      value={voxelAtlasDraft.cols}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, cols: Number(e.target.value || 0) }))}
                      placeholder="cols"
                    />
                    <input
                      value={voxelAtlasDraft.rows}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, rows: Number(e.target.value || 0) }))}
                      placeholder="rows"
                    />
                    <input
                      value={voxelAtlasDraft.padding}
                      onChange={(e) => setVoxelAtlasDraft((prev) => ({ ...prev, padding: Number(e.target.value || 0) }))}
                      placeholder="pad"
                    />
                    <button className="action" onClick={addVoxelAtlas}>Add Atlas</button>
                    <button className="action" onClick={applyRepresentativeAtlasMaterialSet}>Build Material Set</button>
                  </div>
                  {voxelAtlases.length === 0 ? (
                    <p>No atlases yet.</p>
                  ) : (
                    voxelAtlases.map((atlas, idx) => (
                      <div className="row" key={`atlas-${idx}`}>
                        <input value={atlas.id} onChange={(e) => updateVoxelAtlas(idx, { id: e.target.value })} />
                        <input value={atlas.src || ""} onChange={(e) => updateVoxelAtlas(idx, { src: e.target.value })} />
                        <input value={atlas.tileSize} onChange={(e) => updateVoxelAtlas(idx, { tileSize: Number(e.target.value || 0) })} />
                        <input value={atlas.cols} onChange={(e) => updateVoxelAtlas(idx, { cols: Number(e.target.value || 0) })} />
                        <input value={atlas.rows} onChange={(e) => updateVoxelAtlas(idx, { rows: Number(e.target.value || 0) })} />
                        <input value={atlas.padding} onChange={(e) => updateVoxelAtlas(idx, { padding: Number(e.target.value || 0) })} />
                        <button className="action" onClick={() => removeVoxelAtlas(idx)}>Remove</button>
                      </div>
                    ))
                  )}
                  <p>Use textures like <code>atlas:atlasId:0</code> or <code>atlas:atlasId:2,1</code>.</p>
                </div>
                <div className="renderer-subpanel">
                  <h4>Sprite Animator</h4>
                  <p>Apply directional idle/walk frame maps to one sprite entity in renderer JSON.</p>
                  <div className="row">
                    <input
                      value={spriteAnimatorTargetId}
                      onChange={(e) => setSpriteAnimatorTargetId(e.target.value)}
                      placeholder="target entity id"
                    />
                    <input
                      value={spriteAnimatorAtlasId}
                      onChange={(e) => setSpriteAnimatorAtlasId(e.target.value)}
                      placeholder="atlas id"
                    />
                    <button className="action" onClick={() => void consumeTilePngAsAtlas()}>Use Tile PNG</button>
                    <button className="action" onClick={applySpriteAnimatorToRendererJson}>Apply Animator</button>
                  </div>
                  <div className="row">
                    <input
                      value={spriteAnimatorFrameW}
                      onChange={(e) => setSpriteAnimatorFrameW(e.target.value)}
                      placeholder="frame w"
                    />
                    <input
                      value={spriteAnimatorFrameH}
                      onChange={(e) => setSpriteAnimatorFrameH(e.target.value)}
                      placeholder="frame h"
                    />
                    <input
                      value={spriteAnimatorStartCol}
                      onChange={(e) => setSpriteAnimatorStartCol(e.target.value)}
                      placeholder="start col"
                    />
                    <input
                      value={spriteAnimatorIdleRowStart}
                      onChange={(e) => setSpriteAnimatorIdleRowStart(e.target.value)}
                      placeholder="idle row start"
                    />
                    <input
                      value={spriteAnimatorWalkRowStart}
                      onChange={(e) => setSpriteAnimatorWalkRowStart(e.target.value)}
                      placeholder="walk row start"
                    />
                    <input
                      value={spriteAnimatorIdleFrames}
                      onChange={(e) => setSpriteAnimatorIdleFrames(e.target.value)}
                      placeholder="idle frames"
                    />
                    <input
                      value={spriteAnimatorWalkFrames}
                      onChange={(e) => setSpriteAnimatorWalkFrames(e.target.value)}
                      placeholder="walk frames"
                    />
                  </div>
                  {tilePngDataUrl ? (
                    <div className="row">
                      <img
                        src={tilePngDataUrl}
                        alt="tile png atlas preview"
                        style={{ maxWidth: "220px", maxHeight: "120px", border: "1px solid rgba(255,255,255,0.2)" }}
                      />
                      <span className="badge">Tile PNG ready</span>
                    </div>
                  ) : (
                    <p>No tile PNG staged yet. Click <code>Use Tile PNG</code> or <code>Export PNG</code> in Tile Placement Network.</p>
                  )}
                </div>
                <div className="renderer-subpanel">
                  <h4>Voxel Materials</h4>
                  <div className="row">
                    <input
                      value={voxelMaterialDraft.id}
                      onChange={(e) => setVoxelMaterialDraft((prev) => ({ ...prev, id: e.target.value }))}
                      placeholder="material id"
                    />
                    <input
                      value={voxelMaterialDraft.color}
                      onChange={(e) => setVoxelMaterialDraft((prev) => ({ ...prev, color: e.target.value }))}
                      placeholder="color"
                    />
                    <input
                      value={voxelMaterialDraft.textureTop}
                      onChange={(e) => setVoxelMaterialDraft((prev) => ({ ...prev, textureTop: e.target.value }))}
                      placeholder="texture top"
                    />
                    <input
                      value={voxelMaterialDraft.textureLeft}
                      onChange={(e) => setVoxelMaterialDraft((prev) => ({ ...prev, textureLeft: e.target.value }))}
                      placeholder="texture left"
                    />
                    <input
                      value={voxelMaterialDraft.textureRight}
                      onChange={(e) => setVoxelMaterialDraft((prev) => ({ ...prev, textureRight: e.target.value }))}
                      placeholder="texture right"
                    />
                    <button className="action" onClick={addVoxelMaterial}>Add Material</button>
                  </div>
                  {voxelMaterials.length === 0 ? (
                    <p>No materials yet.</p>
                  ) : (
                    voxelMaterials.map((mat, idx) => (
                      <div className="row" key={`mat-${idx}`}>
                        <input value={mat.id} onChange={(e) => updateVoxelMaterial(idx, { id: e.target.value })} />
                        <input value={mat.color || ""} onChange={(e) => updateVoxelMaterial(idx, { color: e.target.value })} />
                        <input value={mat.textureTop || ""} onChange={(e) => updateVoxelMaterial(idx, { textureTop: e.target.value })} />
                        <input value={mat.textureLeft || ""} onChange={(e) => updateVoxelMaterial(idx, { textureLeft: e.target.value })} />
                        <input value={mat.textureRight || ""} onChange={(e) => updateVoxelMaterial(idx, { textureRight: e.target.value })} />
                        <button className="action" onClick={() => removeVoxelMaterial(idx)}>Remove</button>
                      </div>
                    ))
                  )}
                </div>
                <div className="renderer-subpanel">
                  <h4>Voxel Layers</h4>
                  <div className="row">
                    <button className="action" onClick={addVoxelLayer}>Add Layer</button>
                  </div>
                  {voxelLayers.length === 0 ? (
                    <p>No layers yet.</p>
                  ) : (
                    voxelLayers.map((layer, idx) => (
                      <div className="row" key={`layer-${idx}`}>
                        <input value={layer.id} onChange={(e) => updateVoxelLayer(idx, { id: e.target.value })} placeholder="layer id" />
                        <input
                          value={layer.zOffset}
                          onChange={(e) => updateVoxelLayer(idx, { zOffset: Number(e.target.value || 0) })}
                          placeholder="z offset"
                        />
                        <button className="action" onClick={() => removeVoxelLayer(idx)}>Remove</button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>
            <section className="panel">
              <h3>Content Validation</h3>
              <p>Realm-aware validation for Cobra or JSON payloads. Unresolved Shygazun symbols are warnings only.</p>
              <div className="row">
                <select value={contentValidateSource} onChange={(e) => setContentValidateSource(e.target.value)}>
                  <option value="cobra">Cobra</option>
                  <option value="json">JSON</option>
                </select>
                <input
                  value={contentValidateSceneId}
                  onChange={(e) => setContentValidateSceneId(e.target.value)}
                  placeholder="scene id (realm/scene)"
                />
                <span className="badge">{`Realm: ${rendererRealmId}`}</span>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={validateBeforeEmit}
                    onChange={(e) => setValidateBeforeEmit(e.target.checked)}
                  />
                  Validate before emit
                </label>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={strictBilingualValidation}
                    onChange={(e) => setStrictBilingualValidation(e.target.checked)}
                  />
                  Strict bilingual gate
                </label>
                <button className="action" onClick={validateContent}>Validate</button>
              </div>
              <div className="row">
                <button className="action" onClick={() => setContentValidatePayload(rendererCobra)}>Use Cobra</button>
                <button className="action" onClick={() => setContentValidatePayload(rendererJson)}>Use JSON</button>
                <button className="action" onClick={() => setContentValidatePayload("")}>Clear</button>
              </div>
              <textarea
                className="editor editor-mono renderer-editor"
                value={contentValidatePayload}
                onChange={(e) => setContentValidatePayload(e.target.value)}
                placeholder="cobra or json payload"
              />
              <div className="row">
                <span className="badge">{`Validation OK: ${validationSummary.ok ? "yes" : "no"}`}</span>
                <span className="badge">{`Errors: ${validationSummary.errors}`}</span>
                <span className="badge">{`Warnings: ${validationSummary.warnings}`}</span>
                <span className="badge">{`Strict bilingual: ${strictBilingualValidation ? "on" : "off"}`}</span>
              </div>
              <pre>{JSON.stringify(contentValidateOutput || {}, null, 2)}</pre>
              <h4>Bilingual Trust Surface</h4>
              <pre>{JSON.stringify(rendererBilingualOutput || {}, null, 2)}</pre>
            </section>
            <section className="panel">
              <h3>Shygazun Translator</h3>
              <p>Phase 1 deterministic runtime translation between English and Shygazun.</p>
              <div className="row">
                <select value={shygazunTranslateDirection} onChange={(e) => setShygazunTranslateDirection(e.target.value)}>
                  <option value="auto">auto</option>
                  <option value="english_to_shygazun">english {"->"} shygazun</option>
                  <option value="shygazun_to_english">shygazun {"->"} english</option>
                </select>
                <button className="action" onClick={() => setShygazunTranslateSourceText(rendererCobra)}>Use Cobra Source</button>
                <button className="action" onClick={() => setShygazunTranslateSourceText(contentValidatePayload)}>Use Validate Payload</button>
                <button className="action" onClick={runShygazunProject}>Kernel Project</button>
                <button className="action" onClick={runShygazunInterpret}>Interpret</button>
                <button className="action" onClick={runShygazunTranslate}>Translate</button>
                <button className="action" onClick={runShygazunCorrect}>Canonical Correct</button>
              </div>
              <textarea
                className="editor editor-mono renderer-editor"
                value={shygazunTranslateSourceText}
                onChange={(e) => setShygazunTranslateSourceText(e.target.value)}
                placeholder="source text for translation"
              />
              {shygazunSemanticSummary ? (
                <>
                  <div className="row">
                    <span className="badge">{`Authority: ${shygazunSemanticSummary.authorityLevel}`}</span>
                    <span className="badge">{`Trust: ${shygazunSemanticSummary.trustGrade}`}</span>
                    <span className="badge">{`Aster chirality: ${(shygazunSemanticSummary.chirality || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Time topology: ${(shygazunSemanticSummary.timeTopology || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Space op: ${(shygazunSemanticSummary.spaceOperator || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Network role: ${(shygazunSemanticSummary.networkRole || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Cluster role: ${(shygazunSemanticSummary.clusterRole || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Axis: ${(shygazunSemanticSummary.axis || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Projection: ${(shygazunSemanticSummary.tongueProjection || []).join(", ") || "n/a"}`}</span>
                    <span className="badge">{`Cannabis mode: ${(shygazunSemanticSummary.cannabisMode || []).join(", ") || "n/a"}`}</span>
                  </div>
                  <div className="row">
                    <button className="action" onClick={applyProjectionToRenderer}>
                      Apply Projection to Renderer
                    </button>
                    {shygazunProjectionBridge && (
                      <span className="badge" style={{ color: "var(--accent-green, #2ecc71)" }}>
                        {`${shygazunProjectionBridge.coverage.fields_mapped}/${shygazunProjectionBridge.coverage.fields_total} fields mapped`}
                      </span>
                    )}
                    {shygazunProjectionBridge?.coverage?.unmapped?.length > 0 && (
                      <span className="badge" style={{ opacity: 0.6 }}>
                        {`unmapped: ${shygazunProjectionBridge.coverage.unmapped.join(", ")}`}
                      </span>
                    )}
                  </div>
                  {shygazunProjectionBridge && (
                    <details style={{ fontSize: "0.8em", marginTop: "0.25rem" }}>
                      <summary style={{ cursor: "pointer", opacity: 0.7 }}>Projection bridge trace</summary>
                      <pre style={{ marginTop: "0.25rem" }}>{JSON.stringify(shygazunProjectionBridge.trace, null, 2)}</pre>
                    </details>
                  )}
                </>
              ) : null}
              <pre>{JSON.stringify(shygazunProjectOutput || {}, null, 2)}</pre>
              <pre>{JSON.stringify(shygazunInterpretOutput || {}, null, 2)}</pre>
              <pre>{JSON.stringify(shygazunTranslateOutput || {}, null, 2)}</pre>
              <pre>{JSON.stringify(shygazunCorrectOutput || {}, null, 2)}</pre>
            </section>
            <section className="panel">
              <h3>Audio Staging</h3>
              <p>Load audio files from Studio FS, preview them, and trigger backend-callable cue commands.</p>
              <div className="row">
                <button className="action" onClick={refreshStudioFsAssets}>Refresh File Index</button>
                <select value={studioFsSelectedAudio} onChange={(e) => setStudioFsSelectedAudio(e.target.value)}>
                  <option value="">select audio file</option>
                  {studioFsAudioFiles.map((name) => (
                    <option key={`audio-fs-${name}`} value={name}>{name}</option>
                  ))}
                </select>
                <input
                  value={rendererAudioStageLabel}
                  onChange={(e) => setRendererAudioStageLabel(e.target.value)}
                  placeholder="cue label (optional)"
                />
                <button className="action" onClick={stageSelectedFsAudioToRenderer}>Stage from File</button>
                <span className="badge">{`Audio files: ${studioFsAudioFiles.length}`}</span>
                <span className="badge">{`Staged cues: ${rendererAudioStages.length}`}</span>
              </div>
              {rendererAudioStages.length === 0 ? (
                <p>No staged audio cues yet.</p>
              ) : (
                rendererAudioStages.map((cue) => (
                  <div className="row" key={cue.id}>
                    <input value={cue.label || ""} onChange={(e) => updateRendererAudioStage(cue.id, { label: e.target.value })} />
                    <input value={cue.channel || "sfx"} onChange={(e) => updateRendererAudioStage(cue.id, { channel: e.target.value })} />
                    <input
                      value={cue.volume}
                      onChange={(e) => updateRendererAudioStage(cue.id, { volume: Math.max(0, Math.min(2, Number(e.target.value || 1))) })}
                    />
                    <label className="inline-toggle">
                      <input
                        type="checkbox"
                        checked={Boolean(cue.loop)}
                        onChange={(e) => updateRendererAudioStage(cue.id, { loop: e.target.checked })}
                      />
                      Loop
                    </label>
                    <button
                      className="action"
                      onClick={() =>
                        runBackendAudioCue("audio.cue.stage", {
                          cue_id: cue.id,
                          filename: cue.filename,
                          channel: cue.channel || "sfx",
                          loop: Boolean(cue.loop),
                          gain: Number(cue.volume || 1),
                          start_ms: 0,
                          tags: [cue.label || cue.filename],
                        })
                      }
                    >
                      Backend Stage
                    </button>
                    <button
                      className="action"
                      onClick={() =>
                        runBackendAudioCue("audio.cue.play", {
                          cue_id: cue.id,
                          channel: cue.channel || "sfx",
                          loop: Boolean(cue.loop),
                          gain: Number(cue.volume || 1),
                          start_ms: 0,
                        })
                      }
                    >
                      Backend Play
                    </button>
                    <button
                      className="action"
                      onClick={() =>
                        runBackendAudioCue("audio.cue.stop", {
                          cue_id: cue.id,
                          channel: cue.channel || "sfx",
                        })
                      }
                    >
                      Backend Stop
                    </button>
                    <button className="action" onClick={() => removeRendererAudioStage(cue.id)}>Remove</button>
                    <audio controls preload="metadata" src={cue.dataUrl} />
                  </div>
                ))
              )}
            </section>
            <section className="panel">
              <h3>Script + Asset Pipeline</h3>
              <p>Bind Studio Hub files into a repeatable engine lifecycle run.</p>
              <div className="row">
                <select value={rendererPipeline.pythonFileId} onChange={(e) => setRendererPipeline((prev) => ({ ...prev, pythonFileId: e.target.value }))}>
                  <option value="">python file</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-py-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
                <select value={rendererPipeline.cobraFileId} onChange={(e) => setRendererPipeline((prev) => ({ ...prev, cobraFileId: e.target.value }))}>
                  <option value="">cobra file</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-cobra-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
                <select value={rendererPipeline.jsFileId} onChange={(e) => setRendererPipeline((prev) => ({ ...prev, jsFileId: e.target.value }))}>
                  <option value="">js file</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-js-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
              </div>
              <div className="row">
                <select value={rendererPipeline.jsonFileId} onChange={(e) => setRendererPipeline((prev) => ({ ...prev, jsonFileId: e.target.value }))}>
                  <option value="">json file</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-json-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
                <select value={rendererPipeline.engineFileId} onChange={(e) => setRendererPipeline((prev) => ({ ...prev, engineFileId: e.target.value }))}>
                  <option value="">engine state file</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-engine-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
                <input
                  value={rendererPipeline.worldRegionRealmId || ""}
                  onChange={(e) => setRendererPipeline((prev) => ({ ...prev, worldRegionRealmId: e.target.value }))}
                  placeholder="world realm id"
                />
                <input
                  value={rendererPipeline.worldRegionKey || ""}
                  onChange={(e) => setRendererPipeline((prev) => ({ ...prev, worldRegionKey: e.target.value }))}
                  placeholder="world region key"
                />
                <select
                  value={rendererPipeline.worldRegionCachePolicy || "cache"}
                  onChange={(e) => setRendererPipeline((prev) => ({ ...prev, worldRegionCachePolicy: e.target.value }))}
                >
                  <option value="cache">cache</option>
                  <option value="stream">stream</option>
                  <option value="pin">pin</option>
                </select>
              </div>
              <div className="row">
                <select
                  value={rendererPipeline.worldRegionPayloadFileId || ""}
                  onChange={(e) => setRendererPipeline((prev) => ({ ...prev, worldRegionPayloadFileId: e.target.value }))}
                >
                  <option value="">world payload file (optional)</option>
                  {studioFiles.map((file) => (
                    <option key={`pipeline-world-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
                <button className="action" onClick={listWorldRegionsFromApi}>List Regions</button>
                <button className="action" onClick={fetchWorldStreamStatus}>Stream Status</button>
                <button className="action" onClick={loadWorldRegionIntoEngine}>WorldStream.load</button>
                <button className="action" onClick={unloadWorldRegionFromEngine}>WorldStream.unload</button>
                <span className="badge">{`Regions: ${worldRegions.length}`}</span>
                <span className="badge">{`Loaded: ${worldStreamStatus?.loaded_count ?? "-"}/${worldStreamStatus?.capacity ?? "-"}`}</span>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={rendererPipeline.autoPlay}
                    onChange={(e) => setRendererPipeline((prev) => ({ ...prev, autoPlay: e.target.checked }))}
                  />
                  Auto playtest
                </label>
                <label className="inline-toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(rendererPipeline.worldRegionAutoLoad)}
                    onChange={(e) => setRendererPipeline((prev) => ({ ...prev, worldRegionAutoLoad: e.target.checked }))}
                  />
                  Auto WorldStream.load
                </label>
                <button className="action" onClick={applyRendererPipeline}>Run Pipeline</button>
                <button className="action" onClick={validatePipelineIfNeeded}>Validate Now</button>
                <button className="action" onClick={exportRendererPipeline}>Export Pipeline</button>
              </div>
              <pre>{JSON.stringify({ last: worldRegionLast, status: worldStreamStatus, regions: worldRegions }, null, 2)}</pre>
              <textarea
                className="editor editor-mono renderer-editor"
                value={rendererPipelineJson}
                onChange={(e) => setRendererPipelineJson(e.target.value)}
                placeholder="pipeline JSON"
              />
              <div className="row">
                <button className="action" onClick={importRendererPipeline}>Import Pipeline</button>
              </div>
            </section>
            <div className="renderer-grid">
              <div className="renderer-cell">
                <h3>Python Layer</h3>
                <div className="row">
                  <select value={studioFsSelectedPython} onChange={(e) => setStudioFsSelectedPython(e.target.value)}>
                    <option value="">select .py from folder</option>
                    {studioFsPythonFiles.map((name) => (
                      <option key={`renderer-py-fs-${name}`} value={name}>{name}</option>
                    ))}
                  </select>
                  <button className="action" onClick={importSelectedFsPythonToRenderer}>Import from FS</button>
                  <button className="action" onClick={refreshStudioFsAssets}>Refresh FS Index</button>
                  <button className="action" onClick={() => consumeRendererInput("python")}>Consume Python</button>
                  <label className="inline-toggle">
                    <input
                      type="checkbox"
                      checked={studioFsPythonAutoWatch}
                      onChange={(e) => setStudioFsPythonAutoWatch(e.target.checked)}
                    />
                    Auto-watch
                  </label>
                  <input
                    value={studioFsPythonWatchMs}
                    onChange={(e) => setStudioFsPythonWatchMs(e.target.value)}
                    placeholder="watch ms"
                  />
                  <span className="badge">{`.py files: ${studioFsPythonFiles.length}`}</span>
                </div>
                <textarea className="editor editor-mono renderer-editor" value={rendererPython} onChange={(e) => setRendererPython(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={pythonFrameDoc} title="python-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>Cobra Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererCobra} onChange={(e) => setRendererCobra(e.target.value)} />
                <div className="row">
                  <span className="badge">{`Lint: ${cobraLintWarnings.length === 0 ? "clean" : `${cobraLintWarnings.length} warning(s)`}`}</span>
                  <button className="action" onClick={() => consumeRendererInput("cobra")}>Consume Cobra</button>
                </div>
                {cobraLintWarnings.length > 0 ? (
                  <pre>{JSON.stringify(cobraLintWarnings, null, 2)}</pre>
                ) : null}
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={cobraFrameDoc} title="cobra-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JavaScript Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJs} onChange={(e) => setRendererJs(e.target.value)} />
                <div className="row">
                  <button className="action" onClick={() => consumeRendererInput("javascript")}>Consume JS</button>
                </div>
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={jsFrameDoc} title="js-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JSON Scene Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJson} onChange={(e) => setRendererJson(e.target.value)} />
                <div className="row">
                  <button className="action" onClick={() => consumeRendererInput("json")}>Consume JSON</button>
                </div>
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
            <div className="row">
              <input
                value={engineInboxConsumeMax}
                onChange={(e) => setEngineInboxConsumeMax(e.target.value)}
                placeholder="consume max"
              />
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={engineInboxPreviewOnly}
                  onChange={(e) => setEngineInboxPreviewOnly(e.target.checked)}
                />
                Preview only
              </label>
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={engineInboxStrictValidation}
                  onChange={(e) => setEngineInboxStrictValidation(e.target.checked)}
                />
                Strict contract validation
              </label>
              <button className="action" onClick={consumeEngineInbox}>Consume Engine Inbox</button>
              <span className="badge">{`Inbox: ${Array.isArray(rendererEngineState.post_inbox) ? rendererEngineState.post_inbox.length : 0}`}</span>
            </div>
            <p>
              Optional engine script handler map format:
              <code>{" { \"post_handlers\": { \"/v1/game/rules/levels/apply\": { \"target\": \"tables.levels_rules\", \"mode\": \"append\" } } } "}</code>
            </p>
            <pre>{JSON.stringify(engineInboxResult || {}, null, 2)}</pre>
            <textarea className="editor editor-mono renderer-state" value={rendererEngineStateText} onChange={(e) => setRendererEngineStateText(e.target.value)} />
          </section>
          <section className="panel">
            <h2>Game Design Workbench</h2>
            <p>Define scene/systems/entities as Game Spec JSON and compile into renderer layers for playtesting.</p>
            <div className="row">
              <select value={sceneKitShellId} onChange={(e) => setSceneKitShellId(e.target.value)}>
                {SCENE_SHELL_TEMPLATES.map((item) => (
                  <option key={item.scene_id} value={item.scene_id}>{`scene shell ${item.label}`}</option>
                ))}
              </select>
              <select value={sceneKitSelectedRoomId} onChange={(e) => setSceneKitSelectedRoomId(e.target.value)}>
                {ROOM_KIT_TEMPLATES.map((item) => (
                  <option key={item.room_id} value={item.room_id}>{`room ${item.label}`}</option>
                ))}
              </select>
              <button className="action" onClick={() => setSceneKitRoomIdsText((prev) => appendSceneKitId(prev, sceneKitSelectedRoomId))}>
                Add Room
              </button>
              <select value={sceneKitSelectedChunkId} onChange={(e) => setSceneKitSelectedChunkId(e.target.value)}>
                {CHUNK_KIT_TEMPLATES.map((item) => (
                  <option key={item.chunk_id} value={item.chunk_id}>{`chunk ${item.label}`}</option>
                ))}
              </select>
              <button className="action" onClick={() => setSceneKitChunkIdsText((prev) => appendSceneKitId(prev, sceneKitSelectedChunkId))}>
                Add Chunk
              </button>
              <select value={sceneKitSelectedFeatureId} onChange={(e) => setSceneKitSelectedFeatureId(e.target.value)}>
                {FEATURE_KIT_TEMPLATES.map((item) => (
                  <option key={item.feature_id} value={item.feature_id}>{`feature ${item.label}`}</option>
                ))}
              </select>
              <button className="action" onClick={() => setSceneKitFeatureIdsText((prev) => appendSceneKitId(prev, sceneKitSelectedFeatureId))}>
                Add Feature
              </button>
            </div>
            <div className="row">
              <input
                value={sceneKitRoomIdsText}
                onChange={(e) => setSceneKitRoomIdsText(e.target.value)}
                placeholder="room ids"
              />
              <input
                value={sceneKitChunkIdsText}
                onChange={(e) => setSceneKitChunkIdsText(e.target.value)}
                placeholder="chunk ids"
              />
              <input
                value={sceneKitFeatureIdsText}
                onChange={(e) => setSceneKitFeatureIdsText(e.target.value)}
                placeholder="feature ids"
              />
              <button className="action" onClick={composeSceneKitToGameSpec}>Compose Scene Kit</button>
              <span className="badge">{`Scene Shells: ${SCENE_SHELL_TEMPLATES.length}`}</span>
              <span className="badge">{`Rooms: ${parseKitIdSequence(sceneKitRoomIdsText).length}`}</span>
              <span className="badge">{`Chunks: ${parseKitIdSequence(sceneKitChunkIdsText).length}`}</span>
              <span className="badge">{`Features: ${parseKitIdSequence(sceneKitFeatureIdsText).length}`}</span>
            </div>
            <pre>{JSON.stringify(sceneKitOutput || {}, null, 2)}</pre>
            <div className="row">
              <button className="action" onClick={compileGameSpecToRenderer}>Compile Game Spec</button>
              <button className="action" onClick={() => downloadJson("renderer-game-spec.json", rendererGameSpec)}>Export Spec</button>
              <button className="action" onClick={() => downloadJson("scene.schema.v1.template.json", SCENE_SCHEMA_V1)}>Export Scene Template</button>
              <button className="action" onClick={() => downloadJson("sprite.schema.v1.template.json", SPRITE_SCHEMA_V1)}>Export Sprite Template</button>
              <button className="action" onClick={emitScenePlacements}>Emit Scene Placements</button>
              <button className="action" onClick={exportRendererSceneToFs}>Save Scene to FS</button>
              <button className="action" onClick={importSelectedFsSceneToRenderer}>Load Scene from FS</button>
              <button className="action" onClick={exportRendererSpriteToFs}>Save Sprite to FS</button>
              <button className="action" onClick={importSelectedFsSpriteToRenderer}>Load Sprite from FS</button>
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
            <h2>Game System Creator</h2>
            <p>Author and move game content between Cobra, scene library, renderer state, and save export.</p>
            <div className="row">
              <select value={actionPostTarget} onChange={(e) => setActionPostTarget(e.target.value)}>
                <option value="api">POST Target: API (:9000)</option>
                <option value="engine_inbox">POST Target: Engine Script Inbox</option>
                <option value="repo">POST Target: In-App Repo File</option>
              </select>
              {actionPostTarget === "engine_inbox" ? (
                <select value={actionPostEngineFileId} onChange={(e) => setActionPostEngineFileId(e.target.value)}>
                  <option value="">engine script (optional)</option>
                  {studioFiles.map((file) => (
                    <option key={`post-engine-${file.id}`} value={file.id}>{`${file.folder}/${file.name}`}</option>
                  ))}
                </select>
              ) : null}
              {actionPostTarget === "repo" ? (
                <input
                  value={actionPostRepoFolder}
                  onChange={(e) => setActionPostRepoFolder(e.target.value)}
                  placeholder="repo folder (e.g. runtime-posts)"
                />
              ) : null}
              <span className="badge">{`Active target: ${actionPostTarget}`}</span>
            </div>
            <div className="row">
                <button className="action" onClick={compileSceneFromCobra}>Compile Cobra {"->"} Scene + Renderer State (API)</button>
                <button className="action" onClick={loadSceneFromLibraryToRenderer}>Load Library Scene {"->"} Renderer State (API)</button>
              <button className="action" onClick={emitSceneGraph}>POST Scene Graph Payload</button>
              <button className="action" onClick={emitHeadlessQuest}>POST Headless Quest Payload</button>
              <button className="action" onClick={emitMeditation}>POST Meditation Payload</button>
            </div>
            <div className="row">
              <button className="action" onClick={exportGameSave}>Fetch Save Snapshot from API</button>
              <button className="action" onClick={() => saveExport && downloadJson(`game-save-${workspaceId}.json`, saveExport)}>Download Save Snapshot JSON</button>
            </div>
            <div className="row">
              <input value={sceneCompileSceneId} onChange={(e) => setSceneCompileSceneId(e.target.value)} placeholder="scene id (realm/scene)" />
              <input value={rendererLibrarySceneId} onChange={(e) => setRendererLibrarySceneId(e.target.value)} placeholder="load scene id (realm/scene)" />
              <input value={sceneCompileName} onChange={(e) => setSceneCompileName(e.target.value)} placeholder="scene name" />
              <input value={sceneCompileDescription} onChange={(e) => setSceneCompileDescription(e.target.value)} placeholder="scene description" />
              <span className="badge">{`Realm: ${rendererRealmId}`}</span>
            </div>
            <h3>Headless Quest Payload</h3>
            <textarea
              className="editor editor-mono renderer-editor"
              value={headlessQuestText}
              onChange={(e) => setHeadlessQuestText(e.target.value)}
            />
            <h3>Meditation Payload</h3>
            <textarea
              className="editor editor-mono renderer-editor"
              value={meditationText}
              onChange={(e) => setMeditationText(e.target.value)}
            />
            <h3>Scene Graph Payload</h3>
            <textarea
              className="editor editor-mono renderer-editor"
              value={sceneGraphText}
              onChange={(e) => setSceneGraphText(e.target.value)}
            />
            <h3>Save Export</h3>
            <pre>{JSON.stringify(saveExport || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>Dialogue Composer</h2>
            <p>Structured dialogue turns with bordered in-game text box preview and explicit emit.</p>
            <div className="row">
              <input value={dialogueSceneId} onChange={(e) => setDialogueSceneId(e.target.value)} placeholder="scene id" />
              <input value={dialogueId} onChange={(e) => setDialogueId(e.target.value)} placeholder="dialogue id" />
              <input value={dialogueLineId} onChange={(e) => setDialogueLineId(e.target.value)} placeholder="line id" />
              <input value={dialogueSpeakerId} onChange={(e) => setDialogueSpeakerId(e.target.value)} placeholder="speaker id" />
            </div>
            <textarea
              className="editor"
              value={dialogueRaw}
              onChange={(e) => setDialogueRaw(e.target.value)}
              placeholder="dialogue text"
            />
            <div className="row">
              <button className="action" onClick={addDialogueTurn}>Add Turn</button>
              <button className="action" onClick={emitDialogueTurns}>Emit Dialogue</button>
              <button className="action" onClick={clearDialogueTurns}>Clear</button>
              <span className="badge">{`Turns: ${dialogueTurns.length}`}</span>
            </div>
            <div className="dialogue-box">
              {dialogueTurns.length === 0 ? (
                <p className="dialogue-empty">No turns yet.</p>
              ) : (
                dialogueTurns.map((turn) => (
                  <div className="dialogue-line" key={`${turn.line_id}-${turn.speaker_id}-${turn.raw}`}>
                    <strong>{turn.speaker_id}</strong>
                    <span>{turn.raw}</span>
                  </div>
                ))
              )}
            </div>
            <pre>{JSON.stringify(dialogueEmitResult || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>RPG Rule Engine</h2>
            <p>Each action posts one deterministic rule payload to the active target and writes the response/envelope to Rule Output.</p>
            <div className="row">
              <span className="badge">{`POST target: ${actionPostTarget}`}</span>
            </div>
            <div className="row">
              <button className="action" onClick={() => runGameRule("/v1/game/rules/levels/apply", levelRuleText, "game_rule_level_apply")}>POST Level Apply</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/skills/train", skillRuleText, "game_rule_skill_train")}>POST Skill Train</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/perks/unlock", perkRuleText, "game_rule_perk_unlock")}>POST Perk Unlock</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/alchemy/craft", alchemyRuleText, "game_rule_alchemy_craft")}>POST Alchemy Craft</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/blacksmith/forge", blacksmithRuleText, "game_rule_blacksmith_forge")}>POST Blacksmith Forge</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/combat/resolve", combatRuleText, "game_rule_combat_resolve")}>POST Combat Resolve</button>
            </div>
            <div className="row">
              <button className="action" onClick={() => runGameRule("/v1/game/rules/market/quote", marketQuoteText, "game_rule_market_quote")}>POST Market Quote</button>
              <button className="action" onClick={() => runGameRule("/v1/game/rules/market/trade", marketTradeText, "game_rule_market_trade")}>POST Market Trade</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/apply-ruler-influence", vitriolApplyText, "game_vitriol_apply")}>POST VITRIOL Apply Influence</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/compute", vitriolComputeText, "game_vitriol_compute")}>POST VITRIOL Compute</button>
              <button className="action" onClick={() => runGameRule("/v1/game/vitriol/clear-expired", vitriolClearText, "game_vitriol_clear_expired")}>POST VITRIOL Clear Expired</button>
            </div>
            <h3>Level Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={levelRuleText} onChange={(e) => setLevelRuleText(e.target.value)} />
            <h3>Skill Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={skillRuleText} onChange={(e) => setSkillRuleText(e.target.value)} />
            <h3>Perk Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={perkRuleText} onChange={(e) => setPerkRuleText(e.target.value)} />
            <h3>Alchemy Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={alchemyRuleText} onChange={(e) => setAlchemyRuleText(e.target.value)} />
            <h3>Blacksmith Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={blacksmithRuleText} onChange={(e) => setBlacksmithRuleText(e.target.value)} />
            <h3>Combat Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={combatRuleText} onChange={(e) => setCombatRuleText(e.target.value)} />
            <h3>Market Quote Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={marketQuoteText} onChange={(e) => setMarketQuoteText(e.target.value)} />
            <h3>Market Trade Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={marketTradeText} onChange={(e) => setMarketTradeText(e.target.value)} />
            <h3>VITRIOL Apply Payload (1..10 per axis)</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolApplyText} onChange={(e) => setVitriolApplyText(e.target.value)} />
            <h3>VITRIOL Compute Payload (1..10 per axis)</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolComputeText} onChange={(e) => setVitriolComputeText(e.target.value)} />
            <h3>VITRIOL Clear-Expired Payload</h3>
            <textarea className="editor editor-mono renderer-editor" value={vitriolClearText} onChange={(e) => setVitriolClearText(e.target.value)} />
            <h3>Rule Output</h3>
            <pre>{JSON.stringify(gameRulesOutput || {}, null, 2)}</pre>
            <h3>Renderer Tables</h3>
            <p>Sync the rule outputs into the renderer engine state under <code>tables.*</code> with a precedence rule.</p>
            <div className="row">
              <input
                value={rendererTablesActorId}
                onChange={(e) => setRendererTablesActorId(e.target.value)}
                placeholder="actor id"
              />
              <select value={rendererTablesPrecedence} onChange={(e) => setRendererTablesPrecedence(e.target.value)}>
                <option value="local_over_api">Local over API</option>
                <option value="api_over_local">API over Local</option>
              </select>
              <button className="action" onClick={syncRendererTables}>Sync Renderer Tables</button>
              <button className="action" onClick={loadRendererStateTables}>Load State</button>
              <button
                className="action"
                onClick={() => {
                  setRendererTables({});
                  setRendererTablesMeta({ generated_at: "", hash: "" });
                  setRendererTablesStatus("idle");
                }}
              >
                Clear Tables
              </button>
              <span className="badge">{`Status: ${rendererTablesStatus}`}</span>
            </div>
            <div className="row">
              <select value={rendererStateCommitMode} onChange={(e) => setRendererStateCommitMode(e.target.value)}>
                <option value="merge">Commit merge</option>
                <option value="replace">Commit replace</option>
              </select>
              <button className="action" onClick={commitRendererStateTables}>Commit State</button>
              <span className="badge">Writes authoritative game state</span>
            </div>
            <pre>{JSON.stringify({ tables: rendererTables, meta: rendererTablesMeta }, null, 2)}</pre>
            <h3>Tick Engine</h3>
            <p>Advance authoritative state by applying a batch of events in order.</p>
            <div className="row">
              <button className="action" onClick={runRendererTick}>Run Tick</button>
              <span className="badge">{`Status: ${rendererTablesStatus}`}</span>
            </div>
            <textarea
              className="editor editor-mono renderer-editor"
              value={rendererTickText}
              onChange={(e) => setRendererTickText(e.target.value)}
            />
            <pre>{JSON.stringify(rendererTickOutput || {}, null, 2)}</pre>
          </section>
          <section className="panel panel-wide tile-workbench">
            <h2>Tile Placement Network</h2>
            <p>
              Tile semantics: <code>Ta</code> present, <code>Zo</code> absent, color vectors <code>Ru..AE</code>, tone
              tokens <code>Ha/Ga/Na/Ung/Wu</code>, connection relation by distance with <code>Ti</code> (near) and
              <code>Ze</code> (far).
            </p>
            <div className="tile-workbench-layout">
              <div className="tile-controls">
                <div className="row">
                  <input value={tileCols} onChange={(e) => setTileCols(e.target.value)} placeholder="cols" />
                  <input value={tileRows} onChange={(e) => setTileRows(e.target.value)} placeholder="rows" />
                  <input value={tileCellPx} onChange={(e) => setTileCellPx(e.target.value)} placeholder="cell px" />
                  <input value={tileSvgExportScale} onChange={(e) => setTileSvgExportScale(e.target.value)} placeholder="export scale" />
                </div>
                <div className="row">
                  <button className="action" onClick={() => applyResolutionPreset("SD")}>Preset SD</button>
                  <button className="action" onClick={() => applyResolutionPreset("HD")}>Preset HD</button>
                  <button className="action" onClick={() => applyResolutionPreset("2K")}>Preset 2K</button>
                  <button className="action" onClick={() => applyResolutionPreset("4K")}>Preset 4K</button>
                  <button className="action" onClick={applyAssetGenProfileV1}>Load asset-gen-v1</button>
                </div>
                <div className="row">
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
                    <optgroup label="Rose vectors">
                      {ROSE_COLOR_TOKENS.map((tok) => (
                        <option key={`tile-rose-${tok}`} value={tok}>{tok}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Aster right-chiral">
                      {ASTER_RIGHT_TOKENS.map((tok) => (
                        <option key={`tile-aster-right-${tok}`} value={tok}>{tok}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Aster left-chiral">
                      {ASTER_LEFT_TOKENS.map((tok) => (
                        <option key={`tile-aster-left-${tok}`} value={tok}>{tok}</option>
                      ))}
                    </optgroup>
                  </select>
                  <input
                    value={tileColorToken}
                    onChange={(e) => setTileColorToken(e.target.value)}
                    placeholder="Rose/Aster formula (e.g. RuOtKi or Ry)"
                    title="Enter a fused Rose vector mix or canonical Aster chiral token"
                  />
                  <select value="" onChange={(e) => e.target.value && setTileColorToken(e.target.value)}>
                    <option value="">Compound color preset</option>
                    {ROSE_COLOR_COMBINATION_PRESETS.map((preset) => (
                      <option key={preset.value} value={preset.value}>{preset.label}</option>
                    ))}
                  </select>
                  <input
                    value={tokenColor(tileColorToken)}
                    onChange={(e) => setTileColorToken(nearestTokenForColor(e.target.value))}
                    placeholder="tile color hex (#rrggbb)"
                  />
                  <input
                    type="color"
                    value={tokenColor(tileColorToken)}
                    onChange={(e) => setTileColorToken(nearestTokenForColor(e.target.value))}
                    title="renderer lab tile placement color picker"
                  />
                  <select value={tileOpacityToken} onChange={(e) => setTileOpacityToken(e.target.value)}>
                    {["Ha", "Ga", "Na", "Ung", "Wu"].map((tok) => (
                      <option key={tok} value={tok}>{tok}</option>
                    ))}
                  </select>
                  <input value={tileNearThreshold} onChange={(e) => setTileNearThreshold(e.target.value)} placeholder="near threshold" />
                </div>
                <div className="row">
                  <select value={tileEditLodLevel} onChange={(e) => setTileEditLodLevel(e.target.value)}>
                    <option value="0">LOD 0 (coarsest)</option>
                    <option value="1">LOD 1</option>
                    <option value="2">LOD 2</option>
                    <option value="3">LOD 3 (finest)</option>
                  </select>
                  <input value={tileBrushRadius} onChange={(e) => setTileBrushRadius(e.target.value)} placeholder="brush radius" />
                  <select value={tileBrushShape} onChange={(e) => setTileBrushShape(e.target.value)}>
                    <option value="square">Brush: Square</option>
                    <option value="circle">Brush: Circle</option>
                  </select>
                  <select value={tileTraversalClass} onChange={(e) => setTileTraversalClass(e.target.value)}>
                    <option value="walkable_surface">Traversal: Walkable Surface</option>
                    <option value="visual_unwalkable">Traversal: Visual Unwalkable</option>
                    <option value="non_traversal">Traversal: Not Applicable</option>
                  </select>
                  <label className="inline-toggle">
                    <input type="checkbox" checked={tileEditLodSnap} onChange={(e) => setTileEditLodSnap(e.target.checked)} />
                    LOD Snap/Block Fill
                  </label>
                  <button className="action" onClick={() => retagAllTilesLod(tileEditLodLevel)}>Retag All to LOD</button>
                </div>
                <div className="row">
                  <button className="action" onClick={() => {
                    setTileRectSelectMode((prev) => !prev);
                    setTileRectStart(null);
                    setTileRectEnd(null);
                  }}>
                    {tileRectSelectMode ? "Rect Paint Mode" : "Rect Select Mode"}
                  </button>
                  <select value={tileRectLodLevel} onChange={(e) => setTileRectLodLevel(e.target.value)}>
                    <option value="0">Rect LOD 0</option>
                    <option value="1">Rect LOD 1</option>
                    <option value="2">Rect LOD 2</option>
                    <option value="3">Rect LOD 3</option>
                  </select>
                  <label className="inline-toggle">
                    <input
                      type="checkbox"
                      checked={tileRectFeatherScaleAware}
                      onChange={(e) => setTileRectFeatherScaleAware(e.target.checked)}
                    />
                    Scale-Aware Feather
                  </label>
                  <button className="action" onClick={() => applyRectLod(tileRectLodLevel, { feather: tileRectFeatherScaleAware })}>Apply Rect LOD</button>
                  <button className="action" onClick={() => applyRectLod("3", { feather: tileRectFeatherScaleAware })}>Refine Rect to Finest</button>
                  <button className="action" onClick={() => { setTileRectStart(null); setTileRectEnd(null); }}>Clear Rect</button>
                </div>
                <div className="row">
                  <button className="action" onClick={() => setTileConnectMode((prev) => !prev)}>
                    {tileConnectMode ? "Paint Mode" : "Connect Mode"}
                  </button>
                  <label><input type="checkbox" checked={tileSvgShowGrid} onChange={(e) => setTileSvgShowGrid(e.target.checked)} /> SVG grid</label>
                  <label><input type="checkbox" checked={tileSvgShowLinks} onChange={(e) => setTileSvgShowLinks(e.target.checked)} /> SVG links</label>
                  <button className="action" onClick={downloadTileSvg}>Export SVG</button>
                  <button className="action" onClick={() => void downloadTilePng()}>Export PNG</button>
                  <button className="action" onClick={() => void consumeTilePngAsAtlas()}>Use PNG as Atlas</button>
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
                  <span className="badge">{`PNG: ${tilePngStatus}`}</span>
                  <span className="badge">{`LOD0:${tileLodCounts["0"]} LOD1:${tileLodCounts["1"]} LOD2:${tileLodCounts["2"]} LOD3:${tileLodCounts["3"]}`}</span>
                  <span className="badge">{`Brush r=${tileBrushRadius} ${tileBrushShape}`}</span>
                  <span className="badge">{`Traversal: ${tileTraversalLabel(tileTraversalClass)}`}</span>
                  <span className="badge">{`Rect: ${tileRectStart ? `${tileRectStart.x},${tileRectStart.y}` : "-"} -> ${tileRectEnd ? `${tileRectEnd.x},${tileRectEnd.y}` : "-"}`}</span>
                  <span className="badge">{`Feather Scale: ${tileRectFeatherScaleAware ? `on (x${clampInt(tileSvgExportScale, 1, 8, 2)})` : "off"}`}</span>
                </div>
                <div className="row">
                  <input value={tileProcSeed} onChange={(e) => setTileProcSeed(e.target.value)} placeholder="proc seed" />
                  <select value={tileProcTemplate} onChange={(e) => loadProceduralTemplate(e.target.value)}>
                    <option value="ring_bloom">Ring Bloom</option>
                    <option value="maze_carve">Maze Carve</option>
                    <option value="island_chain">Island Chain</option>
                    <option value="corridor_grid">Corridor Grid</option>
                    <option value="noise_caves">Noise Caves</option>
                    <option value="humanoid_curve">Humanoid Curve (LOD Demo)</option>
                    <option value="grilled_cheese">Grilled Cheese (Pixel Test)</option>
                    <option value="navigable_town">Navigable Town</option>
                    <option value="navigable_wilds">Navigable Wilds</option>
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
              </div>
              <div className="tile-workbench-canvas">
                <div
                  className="tile-grid"
                  style={{ gridTemplateColumns: `repeat(${clampInt(tileCols, 1, 128, 48)}, minmax(0, 1fr))` }}
                >
                  {tileGridCells.map((cell) => {
                    const token = cell.placement ? cell.placement.color_token : "";
                    const placementMeta = cell.placement && cell.placement.meta && typeof cell.placement.meta === "object" ? cell.placement.meta : {};
                    const traversalClass = normalizeTileTraversalClass(
                      placementMeta.traversal_class || (placementMeta.walkable === true ? "walkable_surface" : placementMeta.walkable === false ? "visual_unwalkable" : "non_traversal"),
                      "non_traversal"
                    );
                    const rect = normalizeTileRect(tileRectStart, tileRectEnd);
                    const inRect = tilePointInRect(cell.x, cell.y, rect);
                    return (
                      <button
                        key={cell.key}
                        className={`tile-cell ${tileConnectFrom === cell.key ? "tile-cell-connect-from" : ""}`}
                        style={{
                          background: cell.placement ? tokenColor(token) : "#faf5eb",
                          color: token === "Ha" || token === "El" || token === "Wu" ? "#111" : "#fff",
                          outline: inRect ? "2px solid #3a84ff" : "1px solid rgba(0,0,0,0.08)",
                          width: `${tilePreviewCellPx}px`,
                          minHeight: `${tilePreviewCellPx}px`,
                        }}
                        onClick={() => handleTileClick(cell.x, cell.y)}
                        title={`${cell.key}${cell.placement ? ` ${cell.placement.presence_token}/${cell.placement.color_token}/${cell.placement.opacity_token} traversal=${tileTraversalLabel(traversalClass)}` : ""}`}
                      >
                        {cell.placement ? cell.placement.color_token : "·"}
                      </button>
                    );
                  })}
                </div>
                <div className="tile-svg-wrap" dangerouslySetInnerHTML={{ __html: tileSvgMarkup }} />
                <pre>{JSON.stringify({ tiles: tilePlacements, links: tileConnections }, null, 2)}</pre>
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Module Browser (Renderer Lab)</h2>
            <p>Run modules while watching renderer/runtime outputs update in the same workspace.</p>
            <div className="row">
              <button className="action" onClick={listModuleCatalog}>Refresh Modules</button>
              <select value={moduleSelectedId} onChange={(e) => setModuleSelectedId(e.target.value)}>
                <option value="">select module</option>
                {moduleCatalog.map((mod) => {
                  const id = String(mod && mod.module_id ? mod.module_id : "");
                  return (
                    <option key={`renderer-module-opt-${id}`} value={id}>
                      {id}
                    </option>
                  );
                })}
              </select>
              <button className="action" onClick={fetchSelectedModuleSpec}>Load Spec</button>
              <button className="action" onClick={validateSelectedModuleSpec}>Validate</button>
              <button className="action" onClick={runSelectedModuleSpec}>Run Module</button>
              <span className="badge">{`Modules: ${moduleCatalog.length}`}</span>
              <span className="badge">{`Selected: ${moduleSelectedId || "none"}`}</span>
              <span className="badge">Plan: scene+quest+overlay+sync</span>
            </div>
            <div className="row">
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={moduleAutoReconcile}
                  onChange={(e) => setModuleAutoReconcile(e.target.checked)}
                />
                Auto-Reconcile Scene
              </label>
              <input
                value={moduleReconcileSceneId}
                onChange={(e) => setModuleReconcileSceneId(e.target.value)}
                placeholder="scene id (realm/scene or scene)"
              />
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={moduleReconcileApply}
                  onChange={(e) => setModuleReconcileApply(e.target.checked)}
                />
                Reconcile Apply
              </label>
            </div>
            <textarea
              className="editor editor-mono renderer-editor"
              value={moduleRunOverridesText}
              onChange={(e) => setModuleRunOverridesText(e.target.value)}
              placeholder='{"key":"value"}'
            />
            <h3>Module Run Result</h3>
            <pre>{JSON.stringify(moduleRunOutput || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2>Daisy Tongue Bodyplan Maker</h2>
            <p>Define a Daisy system/bodyplan using canonical Daisy symbols (full tongue by default) and project to renderer voxels.</p>
            <div className="row">
              <input value={daisySystemId} onChange={(e) => setDaisySystemId(e.target.value)} placeholder="system id" />
              <select value={daisyArchetype} onChange={(e) => setDaisyArchetype(e.target.value)}>
                <option value="humanoid">humanoid</option>
                <option value="beast">beast</option>
                <option value="serpentine">serpentine</option>
                <option value="avian">avian</option>
              </select>
              <select value={daisySymmetry} onChange={(e) => setDaisySymmetry(e.target.value)}>
                <option value="bilateral">bilateral</option>
                <option value="radial">radial</option>
              </select>
              <input value={daisySegmentCount} onChange={(e) => setDaisySegmentCount(e.target.value)} placeholder="segments" />
              <input value={daisyLimbPairs} onChange={(e) => setDaisyLimbPairs(e.target.value)} placeholder="limb pairs" />
              <input value={daisySeed} onChange={(e) => setDaisySeed(e.target.value)} placeholder="seed" />
              <label className="inline-toggle">
                <input type="checkbox" checked={daisyUseWholeTongue} onChange={(e) => setDaisyUseWholeTongue(e.target.checked)} />
                Use whole Daisy tongue
              </label>
            </div>
            <div className="row">
              <select value={daisyCoreToken} onChange={(e) => setDaisyCoreToken(e.target.value)}>
                <optgroup label="Rose vectors">
                  {ROSE_COLOR_TOKENS.map((tok) => (
                    <option key={`daisy-core-rose-${tok}`} value={tok}>{`core ${tok}`}</option>
                  ))}
                </optgroup>
                <optgroup label="Aster right-chiral">
                  {ASTER_RIGHT_TOKENS.map((tok) => (
                    <option key={`daisy-core-aster-right-${tok}`} value={tok}>{`core ${tok}`}</option>
                  ))}
                </optgroup>
                <optgroup label="Aster left-chiral">
                  {ASTER_LEFT_TOKENS.map((tok) => (
                    <option key={`daisy-core-aster-left-${tok}`} value={tok}>{`core ${tok}`}</option>
                  ))}
                </optgroup>
              </select>
              <input
                value={daisyCoreToken}
                onChange={(e) => setDaisyCoreToken(e.target.value)}
                placeholder="core Rose/Aster token"
                title="Rose vector or canonical Aster chiral token for the core palette"
              />
              <select value="" onChange={(e) => e.target.value && setDaisyCoreToken(e.target.value)}>
                <option value="">core preset</option>
                {ROSE_COLOR_COMBINATION_PRESETS.map((preset) => (
                  <option key={`daisy-core-preset-${preset.value}`} value={preset.value}>{preset.label}</option>
                ))}
              </select>
              <input
                type="color"
                value={tokenColor(daisyCoreToken)}
                onChange={(e) => setDaisyCoreToken(nearestTokenForColor(e.target.value))}
                title="daisy core color"
              />
              <select value={daisyAccentToken} onChange={(e) => setDaisyAccentToken(e.target.value)}>
                <optgroup label="Rose vectors">
                  {ROSE_COLOR_TOKENS.map((tok) => (
                    <option key={`daisy-accent-rose-${tok}`} value={tok}>{`accent ${tok}`}</option>
                  ))}
                </optgroup>
                <optgroup label="Aster right-chiral">
                  {ASTER_RIGHT_TOKENS.map((tok) => (
                    <option key={`daisy-accent-aster-right-${tok}`} value={tok}>{`accent ${tok}`}</option>
                  ))}
                </optgroup>
                <optgroup label="Aster left-chiral">
                  {ASTER_LEFT_TOKENS.map((tok) => (
                    <option key={`daisy-accent-aster-left-${tok}`} value={tok}>{`accent ${tok}`}</option>
                  ))}
                </optgroup>
              </select>
              <input
                value={daisyAccentToken}
                onChange={(e) => setDaisyAccentToken(e.target.value)}
                placeholder="accent Rose/Aster token"
                title="Rose vector or canonical Aster chiral token for the accent palette"
              />
              <select value="" onChange={(e) => e.target.value && setDaisyAccentToken(e.target.value)}>
                <option value="">accent preset</option>
                {ROSE_COLOR_COMBINATION_PRESETS.map((preset) => (
                  <option key={`daisy-accent-preset-${preset.value}`} value={preset.value}>{preset.label}</option>
                ))}
              </select>
              <input
                type="color"
                value={tokenColor(daisyAccentToken)}
                onChange={(e) => setDaisyAccentToken(nearestTokenForColor(e.target.value))}
                title="daisy accent color"
              />
              <button className="action" onClick={generateDaisyBodyplan}>Generate Bodyplan</button>
              <button className="action" onClick={projectDaisyBodyplanToRenderer}>Project to Renderer</button>
            </div>
            <div className="row">
              <input
                value={daisyCoreBelongingChain}
                onChange={(e) => setDaisyCoreBelongingChain(formatSakuraBelongingChain(e.target.value))}
                placeholder="core Sakura belonging chain (e.g. Bu > Va > Vi)"
                title="Coordinate-independent Sakura belonging chain for core voxels"
              />
              <select value="" onChange={(e) => e.target.value && setDaisyCoreBelongingChain(e.target.value)}>
                <option value="">core Sakura preset</option>
                {SAKURA_BELONGING_CHAIN_PRESETS.map((preset) => (
                  <option key={`daisy-core-sakura-${preset.value}`} value={preset.value}>{preset.label}</option>
                ))}
              </select>
              <input
                value={daisyAccentBelongingChain}
                onChange={(e) => setDaisyAccentBelongingChain(formatSakuraBelongingChain(e.target.value))}
                placeholder="accent Sakura belonging chain (e.g. By > Vu)"
                title="Coordinate-independent Sakura belonging chain for accent voxels"
              />
              <select value="" onChange={(e) => e.target.value && setDaisyAccentBelongingChain(e.target.value)}>
                <option value="">accent Sakura preset</option>
                {SAKURA_BELONGING_CHAIN_PRESETS.map((preset) => (
                  <option key={`daisy-accent-sakura-${preset.value}`} value={preset.value}>{preset.label}</option>
                ))}
              </select>
              <span className="badge">Sakura belonging: role-level, not coordinate-bound</span>
            </div>
            <div className="row">
              <input
                value={daisySymbolSequence}
                onChange={(e) => setDaisySymbolSequence(e.target.value)}
                placeholder="daisy symbol sequence (comma/space separated)"
                disabled={daisyUseWholeTongue}
              />
              <button className="action" onClick={() => setDaisySymbolSequence(DAISY_TONGUE_SYMBOLS.join(", "))}>Load Full Symbol Sequence</button>
              <span className="badge">{`Allowed symbols: ${daisyUseWholeTongue ? DAISY_TONGUE_SYMBOLS.length : parseDaisySymbolSequence(daisySymbolSequence).length}/${DAISY_TONGUE_SYMBOLS.length}`}</span>
              <span className="badge">Semantic composition mode</span>
            </div>
            <h3>Daisy Role Inspector</h3>
            <p>Override role-to-symbol mapping with JSON (keys from composition, values as Daisy symbols).</p>
            <textarea
              className="editor editor-mono renderer-editor"
              value={daisyRoleOverridesText}
              onChange={(e) => setDaisyRoleOverridesText(e.target.value)}
              placeholder='{"framework":"To","network":"Ne","actuator_primary":"Nz"}'
            />
            <pre>{JSON.stringify(daisyRoleInspector.effective, null, 2)}</pre>
            <textarea
              className="editor editor-mono renderer-editor"
              value={daisyBodyplanText}
              onChange={(e) => setDaisyBodyplanText(e.target.value)}
              placeholder='{"schema":"qqva.daisy.bodyplan.v1", ...}'
            />
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
      return (
        <section className="panel">
          <h2>Temple and Gardens</h2>
          <p>Frontier reflection, garden entropy, and wand damage attestation intake.</p>
          <div className="row">
            <button className="action" onClick={frontiers}>Load Frontiers</button>
            <button className="action" onClick={observe}>Run Observe</button>
            <button className="action" onClick={timeline}>Timeline</button>
          </div>
          <h3>Wand Damage Attestation</h3>
          <div className="row">
            <input value={wandDamageWandId} onChange={(e) => setWandDamageWandId(e.target.value)} placeholder="wand id" />
            <select value={wandDamageWandId} onChange={(e) => setWandDamageWandId(e.target.value)}>
              <option value="">select registered wand</option>
              {wandRegistryList.map((item) => (
                <option key={`temple-wand-${String(item?.wand_id || "")}`} value={String(item?.wand_id || "")}>
                  {`${String(item?.wand_id || "")} :: ${String(item?.maker_id || "")}`}
                </option>
              ))}
            </select>
            <input value={wandDamageNotifierId} onChange={(e) => setWandDamageNotifierId(e.target.value)} placeholder="notifier id" />
            <select value={wandDamageState} onChange={(e) => setWandDamageState(e.target.value)}>
              <option value="worn">worn</option>
              <option value="chipped">chipped</option>
              <option value="cracked">cracked</option>
              <option value="broken">broken</option>
              <option value="restored">restored</option>
              <option value="retired">retired</option>
            </select>
            <input value={wandDamageEventTag} onChange={(e) => setWandDamageEventTag(e.target.value)} placeholder="event tag" />
          </div>
          <div className="row">
            <input
              type="file"
              multiple
              accept={WAND_DAMAGE_IMAGE_ACCEPT}
              onChange={(e) => setWandDamageFiles(Array.from(e.target.files || []))}
            />
            <button className="action" onClick={validateWandDamageEvidence}>Validate Evidence</button>
            <button className="action" onClick={recordWandDamageEvidence}>Record Evidence</button>
            <button className="action" onClick={loadWandDamageHistory}>Load History</button>
            <button className="action" onClick={() => runAction("temple_use_registered_wand", () => applyRegisteredWandSelection(wandDamageWandId, { target: "temple", loadEntry: true }))}>Use Registry Wand</button>
            <span className="badge">{`Files: ${wandDamageFiles.length}`}</span>
            <span className="badge">HEIC allowed</span>
          </div>
          <div className="row">
            <input value={wandEpochPreviousId} onChange={(e) => setWandEpochPreviousId(e.target.value)} placeholder="previous epoch id or attestation record id" />
            <label className="checkbox">
              <input type="checkbox" checked={wandEpochRevoked} onChange={(e) => setWandEpochRevoked(e.target.checked)} disabled={role !== "steward"} />
              revoke prior epoch
            </label>
            <button className="action" onClick={transitionWandEpoch} disabled={wandEpochRevoked && role !== "steward"}>Transition Wand Epoch</button>
            <button className="action" onClick={loadWandEpochHistory}>Load Epochs</button>
            <button className="action" onClick={() => loadWandStatus(wandDamageWandId, setWandStatus)}>Load Wand Status</button>
            <span className="badge">{role === "steward" ? "Steward revoke enabled" : "Revocation steward-gated"}</span>
          </div>
          <pre>{JSON.stringify(wandDamageValidation || {}, null, 2)}</pre>
          <pre>{JSON.stringify(wandDamageRecord || {}, null, 2)}</pre>
          <pre>{JSON.stringify(wandEpochOutput || {}, null, 2)}</pre>
          <pre>{JSON.stringify(wandStatus || {}, null, 2)}</pre>
          <pre>{JSON.stringify(wandDamageHistory || [], null, 2)}</pre>
          <pre>{JSON.stringify(wandEpochHistory || [], null, 2)}</pre>
        </section>
      );
    }
    if (section === "Guild Hall") {
      return (
        <GuildHallPanel
          listLessons={listLessons}
          listModules={listModules}
          guildId={guildId}
          setGuildId={setGuildId}
          profileName={profileName}
          profileEmail={profileEmail}
          activeProfileMemberId={activeProfileMemberId}
          guildDistributionId={guildDistributionId}
          setGuildDistributionId={setGuildDistributionId}
          guildRecipientDistributionId={guildRecipientDistributionId}
          setGuildRecipientDistributionId={setGuildRecipientDistributionId}
          guildRecipientGuildId={guildRecipientGuildId}
          guildRecipientChannelId={guildRecipientChannelId}
          guildRecipientActorId={guildRecipientActorId}
          setGuildRecipientGuildId={setGuildRecipientGuildId}
          setGuildRecipientChannelId={setGuildRecipientChannelId}
          setGuildRecipientActorId={setGuildRecipientActorId}
          guildWandId={guildWandId}
          setGuildWandId={setGuildWandId}
          guildSelectedRegistryWandId={guildSelectedRegistryWandId}
          setGuildSelectedRegistryWandId={setGuildSelectedRegistryWandId}
          guildWandPasskeyWard={guildWandPasskeyWard}
          setGuildWandPasskeyWard={setGuildWandPasskeyWard}
          guildWandStatus={guildWandStatus}
          guildPersistOutput={guildPersistOutput}
          guildMessageHistory={guildMessageHistory}
          distributionHandshakeList={distributionHandshakeList}
          guildDisplayName={guildDisplayName}
          setGuildDisplayName={setGuildDisplayName}
          registerGuildRegistryEntry={registerGuildRegistryEntry}
          loadGuildRegistryEntry={loadGuildRegistryEntry}
          loadGuildRegistryList={loadGuildRegistryList}
          guildRegistryList={guildRegistryList}
          distributionId={distributionId}
          setDistributionId={setDistributionId}
          distributionDisplayName={distributionDisplayName}
          setDistributionDisplayName={setDistributionDisplayName}
          distributionBaseUrl={distributionBaseUrl}
          setDistributionBaseUrl={setDistributionBaseUrl}
          distributionTransportKind={distributionTransportKind}
          setDistributionTransportKind={setDistributionTransportKind}
          distributionPublicKeyRef={distributionPublicKeyRef}
          setDistributionPublicKeyRef={setDistributionPublicKeyRef}
          distributionProtocolFamily={distributionProtocolFamily}
          setDistributionProtocolFamily={setDistributionProtocolFamily}
          distributionProtocolVersion={distributionProtocolVersion}
          setDistributionProtocolVersion={setDistributionProtocolVersion}
          distributionSupportedProtocolVersionsText={distributionSupportedProtocolVersionsText}
          setDistributionSupportedProtocolVersionsText={setDistributionSupportedProtocolVersionsText}
          distributionGuildIdsText={distributionGuildIdsText}
          setDistributionGuildIdsText={setDistributionGuildIdsText}
          distributionMetadataText={distributionMetadataText}
          setDistributionMetadataText={setDistributionMetadataText}
          distributionShopWorkspaceId={distributionShopWorkspaceId}
          setDistributionShopWorkspaceId={setDistributionShopWorkspaceId}
          saveDistributionShopWorkspace={saveDistributionShopWorkspace}
          distributionShopWorkspaceStatus={distributionShopWorkspaceStatus}
          registerDistributionRegistryEntry={registerDistributionRegistryEntry}
          loadDistributionRegistryEntry={loadDistributionRegistryEntry}
          loadDistributionRegistryList={loadDistributionRegistryList}
          distributionRegistryList={distributionRegistryList}
          distributionHandshakeLocalId={distributionHandshakeLocalId}
          setDistributionHandshakeLocalId={setDistributionHandshakeLocalId}
          distributionHandshakeMode={distributionHandshakeMode}
          setDistributionHandshakeMode={setDistributionHandshakeMode}
          distributionHandshakeProtocolFamily={distributionHandshakeProtocolFamily}
          setDistributionHandshakeProtocolFamily={setDistributionHandshakeProtocolFamily}
          distributionHandshakeLocalProtocolVersion={distributionHandshakeLocalProtocolVersion}
          setDistributionHandshakeLocalProtocolVersion={setDistributionHandshakeLocalProtocolVersion}
          distributionHandshakeRemoteProtocolVersion={distributionHandshakeRemoteProtocolVersion}
          setDistributionHandshakeRemoteProtocolVersion={setDistributionHandshakeRemoteProtocolVersion}
          distributionHandshakeNegotiatedProtocolVersion={distributionHandshakeNegotiatedProtocolVersion}
          setDistributionHandshakeNegotiatedProtocolVersion={setDistributionHandshakeNegotiatedProtocolVersion}
          registerDistributionHandshake={registerDistributionHandshake}
          loadDistributionCapabilities={loadDistributionCapabilities}
          loadDistributionHandshakes={loadDistributionHandshakes}
          loadMigrationStatus={loadMigrationStatus}
          loadServiceReadiness={loadServiceReadiness}
          loadFederationHealth={loadFederationHealth}
          adminVerified={adminVerified}
          role={role}
          wandRegistryWandId={wandRegistryWandId}
          setWandRegistryWandId={setWandRegistryWandId}
          wandRegistryMakerId={wandRegistryMakerId}
          setWandRegistryMakerId={setWandRegistryMakerId}
          wandRegistryMakerDate={wandRegistryMakerDate}
          setWandRegistryMakerDate={setWandRegistryMakerDate}
          wandRegistryAtelierOrigin={wandRegistryAtelierOrigin}
          setWandRegistryAtelierOrigin={setWandRegistryAtelierOrigin}
          wandRegistryStructuralFingerprint={wandRegistryStructuralFingerprint}
          setWandRegistryStructuralFingerprint={setWandRegistryStructuralFingerprint}
          wandRegistryCraftRecordHash={wandRegistryCraftRecordHash}
          setWandRegistryCraftRecordHash={setWandRegistryCraftRecordHash}
          registerWandRegistryEntry={registerWandRegistryEntry}
          wandRegistryMinimumReady={wandRegistryMinimumReady}
          loadWandRegistryEntry={loadWandRegistryEntry}
          loadWandRegistryList={loadWandRegistryList}
          wandRegistryList={wandRegistryList}
          wandRegistryMaterialProfileText={wandRegistryMaterialProfileText}
          setWandRegistryMaterialProfileText={setWandRegistryMaterialProfileText}
          wandRegistryDimensionsText={wandRegistryDimensionsText}
          setWandRegistryDimensionsText={setWandRegistryDimensionsText}
          wandRegistryOwnershipChainText={wandRegistryOwnershipChainText}
          setWandRegistryOwnershipChainText={setWandRegistryOwnershipChainText}
          wandRegistryMetadataText={wandRegistryMetadataText}
          setWandRegistryMetadataText={setWandRegistryMetadataText}
          guildChannelId={guildChannelId}
          setGuildChannelId={setGuildChannelId}
          guildThreadId={guildThreadId}
          setGuildThreadId={setGuildThreadId}
          guildSenderId={guildSenderId}
          setGuildSenderId={setGuildSenderId}
          guildConversationId={guildConversationId}
          setGuildConversationId={setGuildConversationId}
          guildConversationKind={guildConversationKind}
          setGuildConversationKind={setGuildConversationKind}
          guildConversationTitle={guildConversationTitle}
          setGuildConversationTitle={setGuildConversationTitle}
          guildParticipantMemberIdsText={guildParticipantMemberIdsText}
          setGuildParticipantMemberIdsText={setGuildParticipantMemberIdsText}
          guildParticipantGuildIdsText={guildParticipantGuildIdsText}
          setGuildParticipantGuildIdsText={setGuildParticipantGuildIdsText}
          guildSecuritySessionText={guildSecuritySessionText}
          setGuildSecuritySessionText={setGuildSecuritySessionText}
          guildSessionMode={guildSessionMode}
          setGuildSessionMode={setGuildSessionMode}
          guildSessionSenderIdentityKeyRef={guildSessionSenderIdentityKeyRef}
          setGuildSessionSenderIdentityKeyRef={setGuildSessionSenderIdentityKeyRef}
          guildSessionSenderSignedPreKeyRef={guildSessionSenderSignedPreKeyRef}
          setGuildSessionSenderSignedPreKeyRef={setGuildSessionSenderSignedPreKeyRef}
          guildSessionSenderOneTimePreKeyRef={guildSessionSenderOneTimePreKeyRef}
          setGuildSessionSenderOneTimePreKeyRef={setGuildSessionSenderOneTimePreKeyRef}
          guildSessionRecipientIdentityKeyRef={guildSessionRecipientIdentityKeyRef}
          setGuildSessionRecipientIdentityKeyRef={setGuildSessionRecipientIdentityKeyRef}
          guildSessionRecipientSignedPreKeyRef={guildSessionRecipientSignedPreKeyRef}
          setGuildSessionRecipientSignedPreKeyRef={setGuildSessionRecipientSignedPreKeyRef}
          guildSessionRecipientOneTimePreKeyRef={guildSessionRecipientOneTimePreKeyRef}
          setGuildSessionRecipientOneTimePreKeyRef={setGuildSessionRecipientOneTimePreKeyRef}
          guildSessionEpoch={guildSessionEpoch}
          setGuildSessionEpoch={setGuildSessionEpoch}
          guildSessionSealedSender={guildSessionSealedSender}
          setGuildSessionSealedSender={setGuildSessionSealedSender}
          guildConversationList={guildConversationList}
          guildConversationOutput={guildConversationOutput}
          registerGuildConversation={registerGuildConversation}
          loadGuildConversation={loadGuildConversation}
          loadGuildConversationList={loadGuildConversationList}
          runAction={runAction}
          applyRegisteredWandSelection={applyRegisteredWandSelection}
          loadGuildWandStatus={loadGuildWandStatus}
          distributionCapabilitiesOutput={distributionCapabilitiesOutput}
          guildProtocolStatus={guildProtocolStatus}
          guildTempleEntropyDigest={guildTempleEntropyDigest}
          setGuildTempleEntropyDigest={setGuildTempleEntropyDigest}
          guildTheatreEntropyDigest={guildTheatreEntropyDigest}
          setGuildTheatreEntropyDigest={setGuildTheatreEntropyDigest}
          guildTempleProvenanceId={guildTempleProvenanceId}
          setGuildTempleProvenanceId={setGuildTempleProvenanceId}
          guildTempleSourceType={guildTempleSourceType}
          setGuildTempleSourceType={setGuildTempleSourceType}
          guildTempleGardenId={guildTempleGardenId}
          setGuildTempleGardenId={setGuildTempleGardenId}
          guildTemplePlotId={guildTemplePlotId}
          setGuildTemplePlotId={setGuildTemplePlotId}
          guildTheatreProvenanceId={guildTheatreProvenanceId}
          setGuildTheatreProvenanceId={setGuildTheatreProvenanceId}
          guildTheatreSourceType={guildTheatreSourceType}
          setGuildTheatreSourceType={setGuildTheatreSourceType}
          guildTheatrePerformanceId={guildTheatrePerformanceId}
          setGuildTheatrePerformanceId={setGuildTheatrePerformanceId}
          guildTheatreUploadId={guildTheatreUploadId}
          setGuildTheatreUploadId={setGuildTheatreUploadId}
          guildTempleProvenanceHistory={guildTempleProvenanceHistory}
          guildTheatreProvenanceHistory={guildTheatreProvenanceHistory}
          fillTempleEntropySourcePreset={fillTempleEntropySourcePreset}
          fillTheatreEntropySourcePreset={fillTheatreEntropySourcePreset}
          guildAttestationDigestsText={guildAttestationDigestsText}
          setGuildAttestationDigestsText={setGuildAttestationDigestsText}
          guildAttestationSourcesText={guildAttestationSourcesText}
          setGuildAttestationSourcesText={setGuildAttestationSourcesText}
          deriveGuildEntropyMix={deriveGuildEntropyMix}
          updateGuildMessageRelayStatus={updateGuildMessageRelayStatus}
          loadGuildMessageHistory={loadGuildMessageHistory}
          guildRelayStatus={guildRelayStatus}
          setGuildRelayStatus={setGuildRelayStatus}
          guildRelayReceiptText={guildRelayReceiptText}
          setGuildRelayReceiptText={setGuildRelayReceiptText}
          guildRegistryOutput={guildRegistryOutput}
          distributionRegistryOutput={distributionRegistryOutput}
          distributionHandshakeOutput={distributionHandshakeOutput}
          migrationStatus={migrationStatus}
          serviceReadinessOutput={serviceReadinessOutput}
          federationHealthOutput={federationHealthOutput}
          wandRegistryOutput={wandRegistryOutput}
          guildEntropyMixOutput={guildEntropyMixOutput}
          guildEncryptOutput={guildEncryptOutput}
          buildTempleEntropySourcePayload={buildTempleEntropySourcePayload}
          buildTheatreEntropySourcePayload={buildTheatreEntropySourcePayload}
        />
      );
    }

    if (section === "Messages") {
      return (
        <>
          <MessagesPanel
            messageDraft={messageDraft}
            setMessageDraft={setMessageDraft}
            encryptGuildMessage={encryptGuildMessage}
            decryptGuildMessage={decryptGuildMessage}
            profileName={profileName}
            profileEmail={profileEmail}
            activeProfileMemberId={activeProfileMemberId}
            guildWandStatus={guildWandStatus}
            guildId={guildId}
            guildChannelId={guildChannelId}
            guildWandId={guildWandId}
            guildWandPasskeyWard={guildWandPasskeyWard}
            guildConversationId={guildConversationId}
            guildConversationKind={guildConversationKind}
            guildConversationTitle={guildConversationTitle}
            guildRecipientActorId={guildRecipientActorId}
            guildRecipientDistributionId={guildRecipientDistributionId}
            guildRecipientGuildId={guildRecipientGuildId}
            guildPersistOutput={guildPersistOutput}
            guildMessageHistory={guildMessageHistory}
            guildDecryptOutput={guildDecryptOutput}
            messageLog={messageLog}
          />
          <ClientConversationsPanel
            apiBase={API_BASE}
            authToken={authToken}
            workspaceId={workspaceId}
          />
          <GuildDMPanel
            apiBase={API_BASE}
            apiCall={apiCall}
            guildId={guildId}
            guildChannelId={guildChannelId}
            activeProfileMemberId={activeProfileMemberId}
            artisanId={artisanId}
            guildWandId={guildWandId}
            guildWandPasskeyWard={guildWandPasskeyWard}
            buildTempleEntropySourcePayload={buildTempleEntropySourcePayload}
            buildTheatreEntropySourcePayload={buildTheatreEntropySourcePayload}
            workspaceId={workspaceId}
            authToken={authToken}
          />
        </>
      );
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
              <button className="action" onClick={refreshStudioFsAssets}>List scene/sprite/python/audio</button>
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
              <select value={studioFsSelectedPython} onChange={(e) => setStudioFsSelectedPython(e.target.value)}>
                <option value="">select .py from folder</option>
                {studioFsPythonFiles.map((name) => (
                  <option key={`studio-fs-py-${name}`} value={name}>{name}</option>
                ))}
              </select>
              <button className="action" onClick={importSelectedFsPythonToRenderer}>Import .py to Renderer</button>
              <label className="inline-toggle">
                <input
                  type="checkbox"
                  checked={studioFsPythonAutoWatch}
                  onChange={(e) => setStudioFsPythonAutoWatch(e.target.checked)}
                />
                Auto-watch .py
              </label>
              <input
                value={studioFsPythonWatchMs}
                onChange={(e) => setStudioFsPythonWatchMs(e.target.value)}
                placeholder="watch ms"
              />
              <span className="badge">{`Desktop FS: ${hasDesktopFs() ? "available" : "web-only"}`}</span>
              <span className="badge">{`.cobra files: ${studioFsScripts.length}`}</span>
              <span className="badge">{`.py files: ${studioFsPythonFiles.length}`}</span>
              <span className="badge">{`scene files: ${studioFsSceneFiles.length}`}</span>
              <span className="badge">{`sprite files: ${studioFsSpriteFiles.length}`}</span>
            </div>
            <div className="row">
              <select value={studioFsSelectedScene} onChange={(e) => setStudioFsSelectedScene(e.target.value)}>
                <option value="">select .scene.json from folder</option>
                {studioFsSceneFiles.map((name) => (
                  <option key={`studio-fs-scene-${name}`} value={name}>{name}</option>
                ))}
              </select>
              <button className="action" onClick={importSelectedFsSceneToRenderer}>Import Scene to Renderer</button>
              <button className="action" onClick={exportRendererSceneToFs}>Export Current Scene</button>
            </div>
            <div className="row">
              <select value={studioFsSelectedSprite} onChange={(e) => setStudioFsSelectedSprite(e.target.value)}>
                <option value="">select .sprite.json from folder</option>
                {studioFsSpriteFiles.map((name) => (
                  <option key={`studio-fs-sprite-${name}`} value={name}>{name}</option>
                ))}
              </select>
              <button className="action" onClick={importSelectedFsSpriteToRenderer}>Import Sprite to Renderer</button>
              <button className="action" onClick={exportRendererSpriteToFs}>Export Current Sprite</button>
            </div>
            <div className="row">
              <select value={studioFsRuntimePlanPath} onChange={(e) => setStudioFsRuntimePlanPath(e.target.value)}>
                <option value="">select runtime plan from gameplay/runtime_plans</option>
                {studioFsRuntimePlanFiles.map((name) => (
                  <option key={`studio-fs-runtime-plan-${name}`} value={name}>{name}</option>
                ))}
              </select>
              <input
                value={studioFsRuntimePlanPath}
                onChange={(e) => setStudioFsRuntimePlanPath(e.target.value)}
                placeholder="runtime plan path (relative to Studio FS root)"
              />
              <button className="action" onClick={refreshStudioFsAssets}>Refresh Runtime Plans</button>
              <button className="action" onClick={runRuntimePlanFromFs}>Run Runtime Plan File</button>
              <button className="action" onClick={runDungeonSweepFromApi}>Run Dungeon Sweep</button>
              <span className="badge">{`runtime plans: ${studioFsRuntimePlanFiles.length}`}</span>
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
            <h2>Graphics Sandbox (Renderer Core)</h2>
            <p>Isolated graphics publish boundary. Build, validate, and apply immutable render packs without mutating gameplay schemas.</p>
            <div className="row">
              <input
                value={rendererSandboxPackName}
                onChange={(e) => setRendererSandboxPackName(e.target.value)}
                placeholder="pack name"
              />
              <input
                value={rendererSandboxPackNotes}
                onChange={(e) => setRendererSandboxPackNotes(e.target.value)}
                placeholder="pack notes"
              />
              <button className="action" onClick={createRendererSandboxDraftFromCurrent}>Build Draft From Current Renderer</button>
              <button className="action" onClick={publishRendererSandboxDraft}>Publish Pack</button>
              <button className="action" onClick={applyRendererSandboxSelectedPack}>Apply Selected Pack</button>
              <button className="action" onClick={deleteRendererSandboxSelectedPack}>Delete Selected Pack</button>
              <button
                className="action"
                onClick={() =>
                  rendererSandboxSelectedPack
                    ? downloadJson(`renderer-pack-${rendererSandboxSelectedPack.pack_id}.json`, rendererSandboxSelectedPack)
                    : setNotice("sandbox_export_failed: no selected pack")
                }
              >
                Export Selected Pack
              </button>
            </div>
            <div className="row">
              <select value={rendererSandboxSelectedId} onChange={(e) => setRendererSandboxSelectedId(e.target.value)}>
                <option value="">select renderer pack</option>
                {rendererSandboxPacks.map((pack) => (
                  <option key={`sandbox-pack-${pack.pack_id}`} value={pack.pack_id}>
                    {`${pack.name || pack.pack_id} (${pack.stats?.voxel_count ?? 0} voxels)`}
                  </option>
                ))}
              </select>
              <span className="badge">{`Sandbox packs: ${rendererSandboxPacks.length}`}</span>
              <span className="badge">{`Sandbox status: ${rendererSandboxStatus}`}</span>
              <span className="badge">
                {`Validation: ${
                  rendererSandboxValidation
                    ? rendererSandboxValidation.ok
                      ? "ok"
                      : `${rendererSandboxValidation.errors.length} error(s)`
                    : "n/a"
                }`}
              </span>
            </div>
            <textarea
              className="editor editor-mono renderer-editor"
              value={rendererSandboxDraftText}
              onChange={(e) => setRendererSandboxDraftText(e.target.value)}
              placeholder='{"schema":"atelier.renderer.pack.v2", ...}'
            />
            <pre>{JSON.stringify({ validation: rendererSandboxValidation, selected: rendererSandboxSelectedPack }, null, 2)}</pre>
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
      const progressMap = {};
      lessonProgress.forEach((entry) => {
        if (entry && entry.lesson_id) {
          progressMap[entry.lesson_id] = entry;
        }
      });
      return (
        <section className="panel">
          <h2>Learning Hall</h2>
          <div className="row">
            <button className="action" onClick={listLessons}>Load Lessons</button>
            <button className="action" onClick={listModules}>Load Modules</button>
            <button className="action" onClick={listLessonProgress}>Load Progress</button>
            <input value={lessonActorId} onChange={(e) => setLessonActorId(e.target.value)} placeholder="actor id" />
          </div>
          {filteredLessons.length > 0 ? (
            <>
              <div className="lesson-preview">
                <h3>{filteredLessons[0].title}</h3>
                <div className="preview-body">{renderMarkdownBlocks(filteredLessons[0].body || "")}</div>
                <div className="row">
                  <button className="action" onClick={() => consumeLesson(filteredLessons[0].id)}>Mark Consumed</button>
                  <span className="badge">{`Status: ${progressMap[filteredLessons[0].id]?.status || "new"}`}</span>
                </div>
              </div>
              <div className="row">
                <button className="action" onClick={() => setLessonFilter("")}>Clear Filter</button>
              </div>
              <div className="lesson-list">
                {filteredLessons.map((lesson) => (
                  <div className="lesson-card" key={lesson.id}>
                    <div className="row">
                      <strong>{lesson.title}</strong>
                      <span className="badge">{progressMap[lesson.id]?.status || "new"}</span>
                      <button className="action" onClick={() => consumeLesson(lesson.id)}>Consume</button>
                    </div>
                    <div className="preview-body">{renderMarkdownBlocks(lesson.body || "")}</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p>No lessons loaded yet.</p>
          )}
        </section>
      );
    }
    if (section === "Asset Library") {
      return (
        <>
          <section className="panel">
            <h2>Upload Asset</h2>
            <div className="row">
              <input
                type="file"
                onChange={(e) => {
                  const f = e.target.files?.[0] || null;
                  setAssetUploadFile(f);
                  if (f) setAssetUploadMime(f.type || "application/octet-stream");
                }}
              />
              <select value={assetUploadKind} onChange={(e) => setAssetUploadKind(e.target.value)}>
                <option value="image">Image</option>
                <option value="audio">Audio</option>
                <option value="document">Document</option>
                <option value="model">3D Model</option>
                <option value="data">Data</option>
                <option value="other">Other</option>
              </select>
              <input value={assetUploadMime} onChange={(e) => setAssetUploadMime(e.target.value)} placeholder="mime type" />
              <button className="action" onClick={uploadAsset} disabled={!assetUploadFile || assetUploadStatus !== "idle"}>
                {assetUploadStatus === "idle" ? "Upload" : assetUploadStatus}
              </button>
            </div>
            {assetUploadFile && <p>{`Selected: ${assetUploadFile.name} (${(assetUploadFile.size / 1024).toFixed(1)} KB)`}</p>}
          </section>
          <section className="panel">
            <h2>Stored Assets</h2>
            <div className="row">
              <button className="action" onClick={loadAssetManifests}>Refresh</button>
              <span className="badge">{`${assetManifests.filter(a => a.storage_state === "uploaded").length} uploaded`}</span>
              <span className="badge">{`${assetManifests.length} total`}</span>
            </div>
            {assetManifests.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr><th>Name</th><th>Kind</th><th>State</th><th>Size</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {assetManifests.map((a) => (
                    <tr key={a.id}>
                      <td>{a.name}</td>
                      <td>{a.kind}</td>
                      <td>
                        <span className={`badge ${a.storage_state === "uploaded" ? "badge-ok" : a.storage_state === "deleted" ? "badge-error" : "badge-warn"}`}>
                          {a.storage_state}
                        </span>
                      </td>
                      <td>{a.file_size_bytes > 0 ? `${(a.file_size_bytes / 1024).toFixed(1)} KB` : "—"}</td>
                      <td>
                        <div className="row">
                          {a.storage_state === "uploaded" && (
                            <button className="action" onClick={() => downloadAsset(a.id)}>Download</button>
                          )}
                          {a.storage_state !== "deleted" && (
                            <button className="action" onClick={() => deleteAsset(a.id)}>Delete</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No assets yet. Upload a file above.</p>
            )}
          </section>
        </>
      );
    }
    if (section === "Guild Profiles") {
      return (
        <>
          <section className="panel">
            <h2>My Guild Profile</h2>
            <p className="muted-text">Public profiles must be approved by a steward before they appear in the directory.</p>
            <div className="row">
              <button className="action" onClick={loadMyGuildProfile}>Load My Profile</button>
              {guildProfile && (
                <span className={`badge ${guildProfile.steward_approved ? "badge-ok" : "badge-warn"}`}>
                  {guildProfile.steward_approved ? "Approved" : "Pending approval"}
                </span>
              )}
              {guildProfile?.is_public && <span className="badge badge-ok">Public</span>}
            </div>
            <div className="row">
              <input value={guildProfileEdit.display_name} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, display_name: e.target.value }))} placeholder="display name" />
              <input value={guildProfileEdit.region} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, region: e.target.value }))} placeholder="region" />
            </div>
            <textarea
              value={guildProfileEdit.bio}
              onChange={(e) => setGuildProfileEdit((p) => ({ ...p, bio: e.target.value }))}
              placeholder="bio"
              rows={3}
              style={{ width: "100%", marginBottom: 8 }}
            />
            <div className="row">
              <input value={guildProfileEdit.portfolio_url} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, portfolio_url: e.target.value }))} placeholder="portfolio URL" />
              <input value={guildProfileEdit.avatar_url} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, avatar_url: e.target.value }))} placeholder="avatar URL" />
            </div>
            <div className="row">
              <input value={guildProfileEdit.divisions} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, divisions: e.target.value }))} placeholder="divisions (comma-sep: sulphur, mercury, salt)" style={{ flex: 2 }} />
              <input value={guildProfileEdit.trades} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, trades: e.target.value }))} placeholder="trades (comma-sep tags)" style={{ flex: 2 }} />
            </div>
            <div className="row">
              <label><input type="checkbox" checked={guildProfileEdit.is_public} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, is_public: e.target.checked }))} /> Make public</label>
              <label><input type="checkbox" checked={guildProfileEdit.show_region} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, show_region: e.target.checked }))} /> Show region</label>
              <label><input type="checkbox" checked={guildProfileEdit.show_trades} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, show_trades: e.target.checked }))} /> Show trades</label>
              <label><input type="checkbox" checked={guildProfileEdit.show_portfolio} onChange={(e) => setGuildProfileEdit((p) => ({ ...p, show_portfolio: e.target.checked }))} /> Show portfolio</label>
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <button className="action" onClick={saveGuildProfile} disabled={guildProfileStatus === "saving"}>
                {guildProfileStatus === "saving" ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </section>

          <section className="panel">
            <h2>Public Directory</h2>
            <div className="row">
              <input value={guildDirectoryQuery} onChange={(e) => setGuildDirectoryQuery(e.target.value)} placeholder="search by trade tag" onKeyDown={(e) => { if (e.key === "Enter") void searchGuildDirectory(); }} />
              <button className="action" onClick={searchGuildDirectory}>Search</button>
            </div>
            {guildDirectoryResults.length > 0 ? (
              <table className="data-table">
                <thead><tr><th>Name</th><th>Rank</th><th>Region</th><th>Trades</th><th>Since</th></tr></thead>
                <tbody>
                  {guildDirectoryResults.map((a) => (
                    <tr key={a.id}>
                      <td>{a.display_name}</td>
                      <td><span className="badge">{a.guild_rank}</span></td>
                      <td>{a.region || "—"}</td>
                      <td>{(a.trades || []).join(", ") || "—"}</td>
                      <td>{a.member_since}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p>No results. Search above or no public profiles yet.</p>}
          </section>

          {(role === "steward") && (
            <section className="panel">
              <h2>Steward: Profile Approvals</h2>
              <button className="action" onClick={loadGuildProfilesAdmin}>Load All Profiles</button>
              {guildProfilesAdmin.length > 0 ? (
                <table className="data-table">
                  <thead><tr><th>Artisan</th><th>Name</th><th>Public</th><th>Status</th><th>Actions</th></tr></thead>
                  <tbody>
                    {guildProfilesAdmin.map((p) => (
                      <tr key={p.id}>
                        <td><code>{p.artisan_id}</code></td>
                        <td>{p.display_name}</td>
                        <td>{p.is_public ? "yes" : "no"}</td>
                        <td>
                          <span className={`badge ${p.steward_approved ? "badge-ok" : "badge-warn"}`}>
                            {p.steward_approved ? "approved" : "pending"}
                          </span>
                        </td>
                        <td>
                          {!p.steward_approved && p.is_public && (
                            <button className="action" onClick={() => approveGuildProfile(p.id)}>Approve</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p>No profiles loaded.</p>}
            </section>
          )}
        </>
      );
    }
    if (section === "Kernel Fields") {
      return (
        <>
          <section className="panel">
            <h2>My Kernel Field</h2>
            <p className="muted-text">Each artisan has one dedicated kernel field (F-register) for tracking their personal CEG state.</p>
            <div className="row">
              <input
                value={kernelFieldLabel}
                onChange={(e) => setKernelFieldLabel(e.target.value)}
                placeholder="Optional label"
              />
              <button className="action" onClick={createKernelField} disabled={kernelFieldStatus === "creating"}>
                {kernelFieldStatus === "creating" ? "Creating..." : "Provision Field"}
              </button>
              <button className="action" onClick={loadKernelFields} disabled={kernelFieldStatus === "loading"}>Refresh</button>
            </div>
          </section>
          <section className="panel">
            <h2>Active Fields</h2>
            {kernelFields.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr><th>Field ID</th><th>Label</th><th>Created</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {kernelFields.map((f) => (
                    <tr key={f.id}>
                      <td><code>{f.field_id}</code></td>
                      <td>{f.label || <span className="muted-text">—</span>}</td>
                      <td>{f.created_at ? new Date(f.created_at).toLocaleDateString() : "—"}</td>
                      <td>
                        <button className="action" onClick={() => observeKernelField(f.field_id)}>Observe</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No kernel fields yet. Provision one above.</p>
            )}
          </section>
          {kernelFieldObserve && (
            <section className="panel">
              <h2>Field Observation</h2>
              <pre style={{ overflowX: "auto", maxHeight: 400 }}>{JSON.stringify(kernelFieldObserve, null, 2)}</pre>
              <button className="action" onClick={() => setKernelFieldObserve(null)}>Clear</button>
            </section>
          )}
        </>
      );
    }
    if (section === "Calculator") {
      return <CalculatorPanel />;
    }
    if (section === "Lotus") {
      return <LotusPanel />;
    }
    if (section === "Alchemy Lab") {
      return <AlchemySubjectPanel apiBase={API_BASE} />;
    }
    if (section === "Shop Manager") {
      return <ShopManagerPanel apiBase={API_BASE} authToken={authToken} artisanId={artisanId} />;
    }
    return <section className="panel"><h2>Tooling</h2><p>Select a section.</p></section>;
  }

  if (isFullscreenRenderer) {
    return (
      <div className="renderer-fullscreen">
        <header className="renderer-fullscreen-bar">
          <strong>Unified Renderer</strong>
          <span className="badge">{`Source: ${fullscreenState.source}`}</span>
          <span className="badge">{`Render: ${(fullscreenEffectiveSettings.renderMode || "2.5d") === "3d" ? "3D" : "2.5D"}`}</span>
          <span className="badge">{`Facing: ${normalizeFacing(fullscreenState.playerFacing || "south")}`}</span>
          <span className="badge">{`Voxels: ${fullscreenVoxels.length}`}</span>
          <button className="action" onClick={() => window.close()}>Dismiss</button>
        </header>
        <canvas
          ref={fullscreenCanvasRef}
          className="fullscreen-canvas"
          style={{ touchAction: "none" }}
          onPointerDown={(e) => handleRendererPointerDown(e, "fullscreen")}
          onPointerMove={(e) => handleRendererPointerMove(e, "fullscreen")}
          onPointerUp={(e) => handleRendererPointerUp(e, "fullscreen")}
          onPointerCancel={(e) => handleRendererPointerUp(e, "fullscreen")}
          onWheel={(e) => handleRendererWheel(e, "fullscreen")}
          onContextMenu={(e) => {
            if (String(fullscreenEffectiveSettings.renderMode || "2.5d").toLowerCase() === "3d") {
              e.preventDefault();
            }
          }}
        />
      </div>
    );
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Quantum Quackery Atelier<small>FOYER NAVIGATOR</small></div>
        <div className="nav">{NAV_ITEMS.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => setSection(item)}>{item}</button>)}</div>
        {workspaceList.length > 0 && (
          <div className="workspace-switcher">
            <small>Workspace</small>
            <select
              value={workspaceId}
              onChange={(e) => {
                const id = e.target.value;
                setWorkspaceId(id);
                localStorage.setItem("atelier.workspace", id);
              }}
            >
              {workspaceList.map((ws) => (
                <option key={ws.id} value={ws.id}>{ws.name} ({ws.role})</option>
              ))}
            </select>
          </div>
        )}
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
            <span className="badge">{`Governor: ${labGovernor.level}`}</span>
            <span className="badge">{busyAction ? `Running: ${busyAction}` : notice}</span>
          </div>
        </div>
        <div className="tools-grid">
          <PanelErrorBoundary panelKey={section}>{renderSectionTools()}</PanelErrorBoundary>
        </div>
        {section === "Workshop" ? (
          <section className="panel">
            <h2>API Output</h2>
            <pre>{output}</pre>
          </section>
        ) : null}
      </main>
      {entryAuthModalOpen ? (
        <div className="modal-backdrop">
          <div className="modal-card">
            {authToken ? (
              <>
                <h3>Welcome back</h3>
                <div className="row">
                  <span className="badge badge-ok">{artisanId}</span>
                  <span className="badge">{role}</span>
                  <span className="badge">{`ws: ${workspaceId}`}</span>
                </div>
                <div className="row" style={{ marginTop: 12 }}>
                  <button className="action" onClick={() => setEntryAuthModalOpen(false)}>Enter Atelier</button>
                  <button className="action" onClick={() => { logout(); setEntryAuthMode("sign_in"); }}>Sign Out</button>
                </div>
              </>
            ) : (
              <>
                <h3>Quantum Quackery Virtual Atelier</h3>
                <div className="row">
                  <button
                    className={`action ${entryAuthMode === "sign_in" ? "active" : ""}`}
                    onClick={() => setEntryAuthMode("sign_in")}
                  >
                    Sign In
                  </button>
                  <button
                    className={`action ${entryAuthMode === "redeem" ? "active" : ""}`}
                    onClick={() => setEntryAuthMode("redeem")}
                  >
                    Redeem Invite
                  </button>
                  <button className="action" onClick={() => setEntryAuthModalOpen(false)}>Skip</button>
                </div>

                {entryAuthMode === "sign_in" && (
                  <div>
                    <div className="row" style={{ marginTop: 8 }}>
                      <input
                        value={loginArtisanId}
                        onChange={(e) => setLoginArtisanId(e.target.value)}
                        placeholder="artisan_id"
                        autoFocus
                      />
                      <input
                        type="password"
                        value={loginArtisanCode}
                        onChange={(e) => setLoginArtisanCode(e.target.value)}
                        placeholder="password"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") void login().then(() => { if (authToken) setEntryAuthModalOpen(false); });
                        }}
                      />
                      <button
                        className="action"
                        onClick={() => void login().then(() => setEntryAuthModalOpen(false))}
                      >
                        Sign In
                      </button>
                    </div>
                    {loginError && <p className="error-text">{loginError}</p>}
                    <p className="muted-text">No account? Get an invite code from a steward and use the Redeem tab.</p>
                  </div>
                )}

                {entryAuthMode === "redeem" && (
                  <div>
                    {onboardStatus === "done" ? (
                      <div>
                        <p className="badge badge-ok">Account created — you are signed in!</p>
                        <button className="action" style={{ marginTop: 8 }} onClick={() => setEntryAuthModalOpen(false)}>Enter Atelier</button>
                      </div>
                    ) : (
                      <>
                        <div className="row" style={{ marginTop: 8 }}>
                          <input
                            value={onboardCode}
                            onChange={(e) => setOnboardCode(e.target.value)}
                            placeholder="DJINN-XXXXXXXX"
                            style={{ fontFamily: "monospace", textTransform: "uppercase" }}
                            autoFocus
                          />
                          <input
                            value={onboardArtisanId}
                            onChange={(e) => setOnboardArtisanId(e.target.value)}
                            placeholder="choose artisan_id"
                          />
                        </div>
                        <div className="row">
                          <input
                            value={onboardName}
                            onChange={(e) => setOnboardName(e.target.value)}
                            placeholder="display name"
                          />
                          <input
                            type="email"
                            value={onboardEmail}
                            onChange={(e) => setOnboardEmail(e.target.value)}
                            placeholder="email"
                          />
                          <input
                            type="password"
                            value={onboardPassword}
                            onChange={(e) => setOnboardPassword(e.target.value)}
                            placeholder="password (8+ chars)"
                          />
                        </div>
                        <div className="row">
                          <button
                            className="action"
                            onClick={() => void redeemInvite().then(() => { if (onboardStatus === "done" || authToken) setEntryAuthModalOpen(false); })}
                            disabled={onboardStatus === "redeeming"}
                          >
                            {onboardStatus === "redeeming" ? "Joining..." : "Create Account"}
                          </button>
                        </div>
                        {onboardError && <p className="error-text">{onboardError}</p>}
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}


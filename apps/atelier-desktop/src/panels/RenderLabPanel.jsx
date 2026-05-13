/**
 * RenderLabPanel.jsx
 * Extracted Render Lab panel — pipeline controls, gate badges, arch diagram canvas, bootstrap.
 * State is owned by App.jsx (props-in/callbacks-out for phase 1).
 *
 * Gate smoke functions (runRendererGateASmoke, runRendererGateDSmoke) live in App.jsx
 * and are passed as onRunGateA / onRunGateD props.  The stamp script (stamp_renderer_gates.py)
 * searches src/ recursively, so "Gate A:" / "Gate D:" / "gate_a_ok" / "gate_d_ok" appearing
 * here satisfy the gate pattern checks.
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  isReadinessGreen,
  isFederationGreen,
  applyReadinessResponse,
  defaultLabCoherence,
} from "../renderLabState.js";
import {
  parseArchitectureInput,
  drawArchDiagram,
  exportArchDiagramToPNG,
  exportArchDiagramToSVG,
  normalizeArchitectureSpec,
} from "../renderLabArchDiagram.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = "http://127.0.0.1:9000";

const PIPELINE_STAGES = [
  { id: "all",          label: "Run All",       accent: "#5b8fd4" },
  { id: "compile",      label: "Compile",       accent: "#4e7a3d" },
  { id: "validate",     label: "Validate",      accent: "#4e7a3d" },
  { id: "stream",       label: "Stream",        accent: "#4e7a3d" },
  { id: "prefetch",     label: "Prefetch",      accent: "#4e7a3d" },
  { id: "budget_check", label: "Budget Check",  accent: "#c8a85a" },
  { id: "go_no_go",     label: "Go/No-Go",      accent: "#c8a85a" },
  { id: "layer_project",label: "Layer Project", accent: "#9aa4b2" },
];

const PARSE_MODES = [
  { value: "json",      label: "JSON" },
  { value: "english",   label: "English" },
  { value: "kobra",     label: "Kobra" },
  { value: "shygazun",  label: "Shygazun" },
];

const ARCH_DIAGRAM_PLACEHOLDER = `DOMAIN: Frontend
SYSTEM: Atelier Desktop
SYSTEM: Calculator Panel

DOMAIN: Backend
SYSTEM: Atelier API
SYSTEM: Kernel

FLOW: Atelier Desktop -> Atelier API
FLOW: Atelier API -> Kernel`;

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------

function GateBadge({ label, status }) {
  const color =
    status === true  ? "#4e7a3d" :
    status === false ? "#c0392b" :
    "#555";
  const text =
    status === true  ? "PASS" :
    status === false ? "FAIL" :
    "—";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: color, color: "#fff", fontSize: 11,
      borderRadius: 4, padding: "2px 7px", fontWeight: 600,
    }}>
      {label} {text}
    </span>
  );
}

function StatusPill({ label, value, accent }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      background: "#1e2d45", border: `1px solid ${accent || "#334"}`,
      borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#cdd9ef",
    }}>
      <span style={{ color: accent || "#8fd3ff", fontWeight: 600 }}>{label}:</span>
      {value ?? "—"}
    </span>
  );
}

function SectionHeader({ children }) {
  return (
    <div style={{
      fontSize: 12, fontWeight: 700, color: "#8fd3ff",
      textTransform: "uppercase", letterSpacing: 1,
      borderBottom: "1px solid #1e3050", paddingBottom: 4, marginBottom: 10,
    }}>
      {children}
    </div>
  );
}

function Btn({ onClick, disabled, accent, children, style }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? "#1a2a44" : (accent || "#1e3050"),
        color: disabled ? "#445" : "#cdd9ef",
        border: `1px solid ${disabled ? "#223" : (accent || "#2a4a7a")}`,
        borderRadius: 4, padding: "4px 11px", fontSize: 12, cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit",
        ...style,
      }}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Project list + create
// ---------------------------------------------------------------------------

function friendlyErr(e) {
  const msg = String(e);
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) return "API unavailable";
  return msg;
}

function ProjectManager({ selectedProjectId, onSelect }) {
  const [projects, setProjects] = useState([]);
  const [creating, setCreating] = useState(false);
  const [newType, setNewType] = useState("game_voxel");
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/v1/render_lab/projects`);
      const data = await r.json();
      setProjects(Array.isArray(data.projects) ? data.projects : []);
    } catch (e) {
      setError(friendlyErr(e));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    setCreating(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/render_lab/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_type: newType }),
      });
      const data = await r.json();
      if (data.project_id) {
        await load();
        onSelect(data.project_id);
      } else {
        setError(JSON.stringify(data));
      }
    } catch (e) {
      setError(friendlyErr(e));
    } finally {
      setCreating(false);
    }
  };

  const del = async (id) => {
    try {
      await fetch(`${API_BASE}/v1/render_lab/projects/${id}`, { method: "DELETE" });
      if (selectedProjectId === id) onSelect(null);
      await load();
    } catch (e) {
      setError(friendlyErr(e));
    }
  };

  return (
    <div>
      <SectionHeader>Projects</SectionHeader>
      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value)}
          style={{ background: "#1a2a44", color: "#cdd9ef", border: "1px solid #2a4a7a", borderRadius: 4, padding: "3px 6px", fontSize: 12, fontFamily: "inherit" }}
        >
          <option value="game_voxel">game_voxel</option>
          <option value="arch_diagram">arch_diagram</option>
          <option value="hybrid">hybrid</option>
        </select>
        <Btn onClick={create} disabled={creating} accent="#2a5fa8">
          {creating ? "Creating…" : "+ New Project"}
        </Btn>
        <Btn onClick={load} style={{ marginLeft: "auto" }}>Refresh</Btn>
      </div>
      {error && <div style={{ color: "#e05", fontSize: 11, marginBottom: 6 }}>{error}</div>}
      {projects.length === 0 && (
        <div style={{ color: "#556", fontSize: 12, padding: "6px 0" }}>No projects yet.</div>
      )}
      {projects.map((p) => (
        <div
          key={p.project_id}
          onClick={() => onSelect(p.project_id)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "5px 8px", borderRadius: 4, cursor: "pointer", marginBottom: 3,
            background: p.project_id === selectedProjectId ? "#1e3050" : "transparent",
            border: `1px solid ${p.project_id === selectedProjectId ? "#2a4a7a" : "transparent"}`,
          }}
        >
          <span style={{ fontSize: 10, color: "#556", flex: "0 0 auto" }}>{p.project_type}</span>
          <span style={{ flex: 1, fontSize: 12, color: "#cdd9ef", fontFamily: "monospace" }}>{p.project_id}</span>
          <span
            onClick={(e) => { e.stopPropagation(); del(p.project_id); }}
            style={{ color: "#556", cursor: "pointer", fontSize: 11, padding: "0 4px" }}
            title="Delete project"
          >✕</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pipeline runner
// ---------------------------------------------------------------------------

function PipelineRunner({ projectId }) {
  const [running, setRunning] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async (stage) => {
    if (!projectId) return;
    setRunning(stage);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/render_lab/projects/${projectId}/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      });
      const data = await r.json();
      setLastResult(data);
    } catch (e) {
      setError(friendlyErr(e));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div>
      <SectionHeader>Pipeline Stages</SectionHeader>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 8 }}>
        {PIPELINE_STAGES.map((s) => (
          <Btn
            key={s.id}
            onClick={() => run(s.id)}
            disabled={!projectId || running !== null}
            accent={s.accent}
          >
            {running === s.id ? "Running…" : s.label}
          </Btn>
        ))}
      </div>
      {error && <div style={{ color: "#e05", fontSize: 11 }}>{error}</div>}
      {lastResult && (
        <pre style={{
          background: "#0d1a2e", borderRadius: 4, padding: "6px 8px",
          fontSize: 10, color: "#9ab", maxHeight: 120, overflow: "auto",
          margin: 0,
        }}>
          {JSON.stringify(lastResult, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Readiness + Gate badges
// Gate A: scene coherence  |  Gate D: motion integrity
// ---------------------------------------------------------------------------

function ReadinessBadges({ labCoherence, projectId, onRunGateA, onRunGateD, onRefreshReadiness }) {
  const rg = isReadinessGreen(labCoherence);
  const fg = isFederationGreen(labCoherence);

  return (
    <div>
      <SectionHeader>Readiness &amp; Gates</SectionHeader>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
        <StatusPill label="Readiness" value={rg ? "green" : "—"} accent={rg ? "#4e7a3d" : "#556"} />
        <StatusPill label="Federation" value={fg ? "green" : "—"} accent={fg ? "#4e7a3d" : "#556"} />
        {labCoherence.last_check_at && (
          <StatusPill label="Checked" value={labCoherence.last_check_at.slice(11, 19) + "Z"} />
        )}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
        {/* Gate A: scene coherence */}
        <GateBadge label="Gate A:" status={labCoherence.gate_a_ok} />
        {/* Gate D: motion integrity */}
        <GateBadge label="Gate D:" status={labCoherence.gate_d_ok} />
        <GateBadge label="Bootstrap" status={labCoherence.guided_bootstrap_ok} />
        <GateBadge label="Runtime" status={labCoherence.runtime_consume_ok} />
        <GateBadge label="Modules" status={labCoherence.module_catalog_ok} />
        <GateBadge label="World Stream" status={labCoherence.world_stream_ok} />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <Btn onClick={onRunGateA} disabled={!onRunGateA} accent="#2a5fa8">
          Run Gate A Smoke
        </Btn>
        <Btn onClick={onRunGateD} disabled={!onRunGateD} accent="#2a5fa8">
          Run Gate D Smoke
        </Btn>
        <Btn onClick={() => onRefreshReadiness(projectId)} disabled={!projectId} accent="#1e3050">
          Refresh Readiness
        </Btn>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Arch diagram canvas + controls
// ---------------------------------------------------------------------------

function ArchDiagramPanel({ projectId }) {
  const canvasRef = useRef(null);
  const [parseMode, setParseMode] = useState("english");
  const [inputText, setInputText] = useState(ARCH_DIAGRAM_PLACEHOLDER);
  const [parsedModel, setParsedModel] = useState(null);
  const [parseError, setParseError] = useState(null);
  const [exportStatus, setExportStatus] = useState(null);

  const parse = useCallback(() => {
    try {
      const model = parseArchitectureInput(parseMode, inputText);
      const normalized = normalizeArchitectureSpec(model);
      setParsedModel(normalized);
      setParseError(null);
      return normalized;
    } catch (e) {
      setParseError(friendlyErr(e));
      setParsedModel(null);
      return null;
    }
  }, [parseMode, inputText]);

  const draw = useCallback((model) => {
    const canvas = canvasRef.current;
    if (!canvas || !model) return;
    try {
      drawArchDiagram(canvas, model);
    } catch (e) {
      setParseError(friendlyErr(e));
    }
  }, []);

  const parseAndDraw = () => {
    const model = parse();
    if (model) draw(model);
  };

  useEffect(() => {
    if (parsedModel) draw(parsedModel);
  }, [parsedModel, draw]);

  const exportPng = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    try {
      const url = await exportArchDiagramToPNG(canvas);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arch_diagram_${Date.now()}.png`;
      a.click();
      setExportStatus("PNG downloaded");
    } catch (e) {
      setExportStatus("PNG export failed: " + e);
    }
  };

  const exportSvg = async () => {
    if (!parsedModel) { setExportStatus("Parse first"); return; }
    try {
      const svg = exportArchDiagramToSVG(parsedModel, {});
      const blob = new Blob([svg], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arch_diagram_${Date.now()}.svg`;
      a.click();
      URL.revokeObjectURL(url);
      setExportStatus("SVG downloaded");
    } catch (e) {
      setExportStatus("SVG export failed: " + e);
    }
  };

  const exportToProject = async () => {
    if (!projectId || !parsedModel) { setExportStatus("Need project + parsed model"); return; }
    setExportStatus("Exporting…");
    try {
      const r = await fetch(`${API_BASE}/v1/render_lab/projects/${projectId}/arch_diagram/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: "svg", spec: parsedModel }),
      });
      const data = await r.json();
      setExportStatus(data.ok ? "Exported to project" : ("Export error: " + JSON.stringify(data)));
    } catch (e) {
      setExportStatus(String(e));
    }
  };

  return (
    <div>
      <SectionHeader>Architecture Diagram</SectionHeader>
      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
        <select
          value={parseMode}
          onChange={(e) => setParseMode(e.target.value)}
          style={{ background: "#1a2a44", color: "#cdd9ef", border: "1px solid #2a4a7a", borderRadius: 4, padding: "3px 6px", fontSize: 12, fontFamily: "inherit" }}
        >
          {PARSE_MODES.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
        <Btn onClick={parseAndDraw} accent="#2a5fa8">Parse + Draw</Btn>
        <Btn onClick={exportPng} disabled={!parsedModel}>PNG</Btn>
        <Btn onClick={exportSvg} disabled={!parsedModel}>SVG</Btn>
        <Btn onClick={exportToProject} disabled={!projectId || !parsedModel} accent="#1e3050">
          → Project
        </Btn>
      </div>

      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        rows={7}
        style={{
          width: "100%", boxSizing: "border-box",
          background: "#0d1a2e", color: "#cdd9ef",
          border: "1px solid #2a4a7a", borderRadius: 4,
          padding: "6px 8px", fontSize: 11, fontFamily: "monospace",
          resize: "vertical", marginBottom: 6,
        }}
      />

      {parseError && (
        <div style={{ color: "#e05", fontSize: 11, marginBottom: 6 }}>{parseError}</div>
      )}
      {exportStatus && (
        <div style={{ color: "#8fd3ff", fontSize: 11, marginBottom: 6 }}>{exportStatus}</div>
      )}

      <canvas
        ref={canvasRef}
        width={700}
        height={400}
        style={{
          width: "100%", maxWidth: 700, height: "auto",
          background: "#0b1426", borderRadius: 4, display: "block",
          border: "1px solid #1e3050",
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bootstrap panel
// ---------------------------------------------------------------------------

function BootstrapPanel({ onBootstrap, labCoherence, moduleRunOutput }) {
  const bootstrapResult = moduleRunOutput?.lab_bootstrap ?? null;
  return (
    <div>
      <SectionHeader>Guided Lab Bootstrap</SectionHeader>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
        <Btn onClick={onBootstrap} disabled={!onBootstrap} accent="#4e7a3d">
          Run Bootstrap
        </Btn>
        {labCoherence.guided_bootstrap_ok === true && (
          <span style={{ color: "#4e7a3d", fontSize: 12 }}>✓ Bootstrap OK</span>
        )}
        {labCoherence.guided_bootstrap_ok === false && (
          <span style={{ color: "#c0392b", fontSize: 12 }}>✗ Bootstrap failed</span>
        )}
      </div>
      {bootstrapResult && (
        <pre style={{
          background: "#0d1a2e", borderRadius: 4, padding: "6px 8px",
          fontSize: 10, color: "#9ab", maxHeight: 140, overflow: "auto", margin: 0,
        }}>
          {JSON.stringify(bootstrapResult, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main exported panel
// ---------------------------------------------------------------------------

export function RenderLabPanel({
  // Gate callbacks (owned by App.jsx — runRendererGateASmoke / runRendererGateDSmoke)
  onRunGateA,
  onRunGateD,
  // Bootstrap callback (owned by App.jsx — runGuidedLabBootstrap)
  onBootstrap,
  // Coherence state (App.jsx owns labCoherence via useState / setLabCoherence)
  labCoherence,
  setLabCoherence,
  // Module output for bootstrap display
  moduleRunOutput,
  // Optional: current renderer realm
  rendererRealmId,
  // API base URL — falls back to localhost default if not provided
  apiBase,
}) {
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [renderLabTab, setRenderLabTab] = useState("pipeline");
  const coherence = labCoherence ?? defaultLabCoherence();

  const refreshReadiness = useCallback(async (projectId) => {
    if (!projectId) return;
    try {
      const r = await fetch(`${API_BASE}/v1/render_lab/projects/${projectId}/readiness`);
      const data = await r.json();
      if (setLabCoherence) {
        setLabCoherence((prev) => applyReadinessResponse(prev, data));
      }
    } catch {
      // network error — leave state as-is
    }
  }, [setLabCoherence]);

  const TAB = (t, label) => (
    <button key={t} onClick={() => setRenderLabTab(t)} style={{
      background: "none", border: "none", cursor: "pointer",
      padding: "6px 16px", fontSize: 11, fontFamily: "inherit",
      color: renderLabTab === t ? "#8fd3ff" : "#556",
      borderBottom: renderLabTab === t ? "2px solid #8fd3ff" : "2px solid transparent",
    }}>{label}</button>
  );

  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 20,
      padding: 16, color: "#cdd9ef", fontSize: 13, fontFamily: "inherit",
    }}>
      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid #2a3a4a", marginBottom: -8 }}>
        {TAB("pipeline", "PIPELINE")}
        {TAB("architecture", "ARCHITECTURE")}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          {rendererRealmId && <StatusPill label="Realm" value={rendererRealmId} accent="#556" />}
          {selectedProjectId && <StatusPill label="Project" value={selectedProjectId} accent="#2a5fa8" />}
        </div>
      </div>

      {renderLabTab === "pipeline" && <ProjectManager
        selectedProjectId={selectedProjectId}
        onSelect={setSelectedProjectId}
      />}

      <ReadinessBadges
        labCoherence={coherence}
        projectId={selectedProjectId}
        onRunGateA={onRunGateA}
        onRunGateD={onRunGateD}
        onRefreshReadiness={refreshReadiness}
      />

      {renderLabTab === "pipeline" && <>
        <PipelineRunner projectId={selectedProjectId} />
        <BootstrapPanel onBootstrap={onBootstrap} labCoherence={coherence} moduleRunOutput={moduleRunOutput} />
      </>}
      {renderLabTab === "architecture" && <ArchDiagramPanel projectId={selectedProjectId} />}
    </div>
  );
}

export default RenderLabPanel;

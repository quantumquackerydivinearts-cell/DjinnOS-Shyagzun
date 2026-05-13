import React, { useState, useEffect, useRef, useCallback } from "react";

const NODE_COLORS = {
  contact:  "#3ab8a0",
  lead:     "#c9a84c",
  client:   "#a084e8",
  quote:    "#60a5fa",
  order:    "#f87171",
  booking:  "#4ade80",
  contract: "#fb923c",
};
const ALL_TYPES = ["contact","lead","client","quote","order","booking","contract"];

function nodeColor(type) { return NODE_COLORS[type] || "#6b7280"; }

// Circular layout — groups nodes by type in concentric rings
function computeLayout(nodes, width, height) {
  const positions = new Map();
  if (!nodes.length) return positions;
  const cx = width / 2, cy = height / 2;
  const byType = {};
  for (const n of nodes) {
    (byType[n.type] = byType[n.type] || []).push(n);
  }
  const typeGroups = Object.entries(byType);
  const ringR = Math.max(120, Math.min(width, height) * 0.38);
  typeGroups.forEach(([, group], gi) => {
    const groupAngle = (2 * Math.PI * gi) / typeGroups.length - Math.PI / 2;
    const gx = cx + ringR * Math.cos(groupAngle);
    const gy = cy + ringR * Math.sin(groupAngle);
    const spread = Math.min(60, 300 / (group.length || 1));
    group.forEach((n, ni) => {
      const a = (2 * Math.PI * ni) / Math.max(group.length, 1);
      const r = group.length === 1 ? 0 : spread;
      positions.set(n.id, { x: gx + r * Math.cos(a), y: gy + r * Math.sin(a) });
    });
  });
  return positions;
}

const SVG_W = 800, SVG_H = 520;

export function GraphPanel({ apiBase, authToken, workspaceId }) {
  const [nodeTypes,  setNodeTypes]  = useState([...ALL_TYPES]);
  const [snapshot,   setSnapshot]   = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [configs,    setConfigs]    = useState([]);
  const [configName, setConfigName] = useState("");
  const [showJson,   setShowJson]   = useState(false);
  const [telemetry,  setTelemetry]  = useState(null);

  // Traversal
  const [neighborId,  setNeighborId]  = useState("");
  const [neighborRes, setNeighborRes] = useState(null);
  const [seedIds,     setSeedIds]     = useState("");
  const [subDepth,    setSubDepth]    = useState(2);
  const [subResult,   setSubResult]   = useState(null);
  const [pathSrc,     setPathSrc]     = useState("");
  const [pathTgt,     setPathTgt]     = useState("");
  const [pathDepth,   setPathDepth]   = useState(8);
  const [pathResult,  setPathResult]  = useState(null);

  // Pan/zoom
  const [view,  setView]  = useState({ x: 0, y: 0, scale: 1 });
  const [drag,  setDrag]  = useState(null); // null | { nodeId | "pan", startX, startY, origX, origY }
  const [nodePos, setNodePos] = useState(new Map());
  const svgRef = useRef(null);

  const hdrs = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${authToken}`,
    "X-Workspace-Id": workspaceId,
  };

  const post = useCallback(async (path, body) => {
    const r = await fetch(`${apiBase}/v1/graph${path}`, { method: "POST", headers: hdrs, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }, [apiBase, authToken, workspaceId]);

  const get = useCallback(async (path) => {
    const r = await fetch(`${apiBase}/v1/graph${path}`, { headers: hdrs });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }, [apiBase, authToken, workspaceId]);

  async function buildSnapshot() {
    setLoading(true);
    try {
      const snap = await post("/snapshot", { node_types: nodeTypes });
      setSnapshot(snap);
      setNodePos(computeLayout(snap.nodes, SVG_W, SVG_H));
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function loadConfigs() {
    try { const d = await get("/configs"); setConfigs(d.configs || []); } catch {}
  }

  async function saveConfig() {
    if (!configName.trim()) return;
    try {
      await post("/configs", { name: configName.trim(), config: { node_types: nodeTypes } });
      setConfigName(""); loadConfigs();
    } catch {}
  }

  async function deleteConfig(id) {
    await fetch(`${apiBase}/v1/graph/configs/${id}`, { method: "DELETE", headers: hdrs });
    loadConfigs();
  }

  async function loadTelemetry() {
    try { setTelemetry(await get("/telemetry")); } catch {}
  }

  async function getNeighbors(e) {
    e.preventDefault();
    if (!neighborId.trim()) return;
    try {
      setNeighborRes(await post("/neighbors", { node_id: neighborId.trim(), node_types: nodeTypes }));
    } catch (err) { setNeighborRes({ error: err.message }); }
  }

  async function getSubgraph(e) {
    e.preventDefault();
    const seeds = seedIds.split(",").map(s => s.trim()).filter(Boolean);
    if (!seeds.length) return;
    try {
      const r = await post("/subgraph", { seed_node_ids: seeds, max_depth: subDepth, node_types: nodeTypes });
      setSubResult(r);
    } catch (err) { setSubResult({ error: err.message }); }
  }

  async function getPath(e) {
    e.preventDefault();
    if (!pathSrc.trim() || !pathTgt.trim()) return;
    try {
      setPathResult(await post("/path", { source_node_id: pathSrc.trim(), target_node_id: pathTgt.trim(), max_depth: pathDepth, node_types: nodeTypes }));
    } catch (err) { setPathResult({ error: err.message }); }
  }

  useEffect(() => { loadConfigs(); }, []);

  function toggleType(t) {
    setNodeTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  }

  // ── SVG interaction ─────────────────────────────────────────────────────────
  function svgPt(e) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: (e.clientX - rect.left) / view.scale - view.x / view.scale,
      y: (e.clientY - rect.top)  / view.scale - view.y / view.scale,
    };
  }

  function onNodeMouseDown(e, nodeId) {
    e.stopPropagation();
    const pt = svgPt(e);
    const cur = nodePos.get(nodeId) || { x: 0, y: 0 };
    setDrag({ kind: "node", nodeId, startX: pt.x, startY: pt.y, origX: cur.x, origY: cur.y });
  }

  function onPanStart(e) {
    setDrag({ kind: "pan", startX: e.clientX, startY: e.clientY, origX: view.x, origY: view.y });
  }

  function onMouseMove(e) {
    if (!drag) return;
    if (drag.kind === "node") {
      const pt = svgPt(e);
      setNodePos(prev => new Map(prev).set(drag.nodeId, {
        x: drag.origX + (pt.x - drag.startX),
        y: drag.origY + (pt.y - drag.startY),
      }));
    } else {
      setView(v => ({ ...v, x: drag.origX + (e.clientX - drag.startX), y: drag.origY + (e.clientY - drag.startY) }));
    }
  }

  function onMouseUp() { setDrag(null); }

  function onWheel(e) {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    setView(v => ({ ...v, scale: Math.max(0.2, Math.min(4, v.scale * factor)) }));
  }

  // Highlight path/subresult nodes
  const highlightIds = new Set([
    ...(subResult?.nodes?.map(n => n.id) || []),
    ...(pathResult?.nodes || []),
    ...(neighborRes?.inbound?.map(e => e.from_node) || []),
    ...(neighborRes?.outbound?.map(e => e.to_node) || []),
  ]);

  const s = {
    panel: { fontFamily: '"Segoe UI", sans-serif', fontSize: 13, color: "#e8f0e8" },
    label: { fontSize: 10, color: "#7a9e7c", fontFamily: '"Cinzel", serif', letterSpacing: 1, display: "block", marginBottom: 3 },
    input: { background: "#0e130e", border: "1px solid #2a3a2a", color: "#e8f0e8", padding: "5px 10px", borderRadius: 4, fontSize: 13 },
    btn:   { background: "#1a2a1a", border: "1px solid #3a5a3c", color: "#e8f0e8", padding: "5px 14px", cursor: "pointer", borderRadius: 4, fontSize: 12 },
    btnPri:{ background: "#3ab8a0", border: "none", color: "#000", padding: "6px 16px", cursor: "pointer", borderRadius: 4, fontSize: 12, fontWeight: 600 },
    h3:    { fontFamily: '"Cinzel", serif', fontSize: 10, letterSpacing: 2, color: "#7a9e7c", margin: "1rem 0 0.5rem" },
    row:   { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 8 },
  };

  return (
    <div style={s.panel}>

      {/* Node type toggles */}
      <div style={s.row}>
        {ALL_TYPES.map(t => (
          <label key={t} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, cursor: "pointer" }}>
            <input type="checkbox" checked={nodeTypes.includes(t)} onChange={() => toggleType(t)} />
            <span style={{ color: nodeColor(t) }}>{t}</span>
          </label>
        ))}
        <button style={s.btnPri} onClick={buildSnapshot} disabled={loading}>
          {loading ? "Building…" : "Build"}
        </button>
        {snapshot && (
          <>
            <span style={{ fontSize: 11, color: "#3a5a3c" }}>
              {snapshot.nodes.length} nodes · {snapshot.edges.length} edges
            </span>
            <button style={s.btn} onClick={() => setShowJson(v => !v)}>
              {showJson ? "Hide JSON" : "JSON"}
            </button>
          </>
        )}
      </div>

      {/* SVG canvas */}
      <div style={{
        border: "1px solid #2a3a2a", borderRadius: 6, overflow: "hidden",
        background: "#080d08", cursor: drag?.kind === "node" ? "grabbing" : "grab",
        userSelect: "none",
      }}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <svg
          ref={svgRef}
          width="100%"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          style={{ display: "block" }}
          onMouseDown={onPanStart}
          onWheel={onWheel}
        >
          <g transform={`translate(${view.x},${view.y}) scale(${view.scale})`}>
            {/* Edges */}
            {(snapshot?.edges || []).map(edge => {
              const from = nodePos.get(edge.from_node);
              const to   = nodePos.get(edge.to_node);
              if (!from || !to) return null;
              const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2;
              const lit = highlightIds.has(edge.from_node) && highlightIds.has(edge.to_node);
              return (
                <g key={edge.id}>
                  <line x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                    stroke={lit ? "#3ab8a0" : "#2a3a2a"} strokeWidth={lit ? 2 : 1.2} strokeOpacity={0.8} />
                  <text x={mx} y={my - 4} textAnchor="middle" fontSize={8} fill="#3a5a3c">
                    {edge.label}
                  </text>
                </g>
              );
            })}
            {/* Nodes */}
            {(snapshot?.nodes || []).map(node => {
              const pos = nodePos.get(node.id);
              if (!pos) return null;
              const color = nodeColor(node.type);
              const lit   = highlightIds.has(node.id);
              const isDragging = drag?.kind === "node" && drag.nodeId === node.id;
              return (
                <g key={node.id} transform={`translate(${pos.x},${pos.y})`}
                  style={{ cursor: isDragging ? "grabbing" : "grab" }}
                  onMouseDown={e => onNodeMouseDown(e, node.id)}>
                  <circle r={26} fill={color} fillOpacity={lit ? 0.25 : 0.12}
                    stroke={color} strokeWidth={lit ? 2.5 : 1.5} />
                  <text textAnchor="middle" dy="0.3em" fontSize={9} fill={color} fontWeight="600">
                    {node.label.length > 14 ? node.label.slice(0, 13) + "…" : node.label}
                  </text>
                  <text textAnchor="middle" dy="1.6em" fontSize={7} fill="#3a5a3c">
                    {node.type}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {!snapshot && <p style={{ color: "#3a5a3c", fontSize: 12, margin: "0.5rem 0" }}>
        Select node types above and press Build.
      </p>}

      {showJson && snapshot && (
        <pre style={{ fontSize: 10, maxHeight: 180, overflow: "auto", background: "#080d08",
          padding: 10, borderRadius: 4, marginTop: 8, color: "#7a9e7c" }}>
          {JSON.stringify(snapshot, null, 2)}
        </pre>
      )}

      {/* Traversal */}
      <div style={s.h3}>TRAVERSAL</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <div>
          <label style={s.label}>NEIGHBOURS</label>
          <form onSubmit={getNeighbors} style={s.row}>
            <input style={{ ...s.input, flex: 1 }} value={neighborId}
              onChange={e => setNeighborId(e.target.value)} placeholder="node_id e.g. client:abc" />
            <button style={s.btn} type="submit">→</button>
          </form>
          {neighborRes && !neighborRes.error && (
            <div style={{ fontSize: 11, color: "#7a9e7c" }}>
              in: {neighborRes.inbound?.length} · out: {neighborRes.outbound?.length}
            </div>
          )}
          {neighborRes?.error && <div style={{ color: "#f87171", fontSize: 11 }}>{neighborRes.error}</div>}
        </div>

        <div>
          <label style={s.label}>SUBGRAPH (BFS)</label>
          <form onSubmit={getSubgraph} style={s.row}>
            <input style={{ ...s.input, flex: 1 }} value={seedIds}
              onChange={e => setSeedIds(e.target.value)} placeholder="seed ids, comma-sep" />
            <input style={{ ...s.input, width: 40 }} type="number" min={1} max={8}
              value={subDepth} onChange={e => setSubDepth(+e.target.value)} />
            <button style={s.btn} type="submit">→</button>
          </form>
          {subResult && !subResult.error && (
            <div style={{ fontSize: 11, color: "#7a9e7c" }}>
              {subResult.nodes?.length} nodes · {subResult.edges?.length} edges
            </div>
          )}
        </div>

        <div>
          <label style={s.label}>PATH</label>
          <form onSubmit={getPath}>
            <div style={s.row}>
              <input style={{ ...s.input, flex: 1 }} value={pathSrc}
                onChange={e => setPathSrc(e.target.value)} placeholder="source node_id" />
              <input style={{ ...s.input, flex: 1 }} value={pathTgt}
                onChange={e => setPathTgt(e.target.value)} placeholder="target node_id" />
            </div>
            <div style={s.row}>
              <input style={{ ...s.input, width: 50 }} type="number" min={1} max={32}
                value={pathDepth} onChange={e => setPathDepth(+e.target.value)} />
              <button style={s.btn} type="submit">Find</button>
            </div>
          </form>
          {pathResult && (
            <div style={{ fontSize: 11, color: pathResult.found ? "#4ade80" : "#f87171" }}>
              {pathResult.found
                ? `${pathResult.hop_count} hop(s): ${pathResult.nodes?.join(" → ")}`
                : "No path found."}
            </div>
          )}
        </div>
      </div>

      {/* Configs */}
      <div style={s.h3}>SAVED CONFIGS</div>
      <div style={s.row}>
        {configs.map(c => (
          <span key={c.id} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <button style={s.btn} onClick={() => {
              setNodeTypes(c.config?.node_types || ALL_TYPES);
            }}>{c.name}</button>
            <button style={{ ...s.btn, color: "#f87171", border: "1px solid #f8717122", padding: "5px 8px" }}
              onClick={() => deleteConfig(c.id)}>✕</button>
          </span>
        ))}
        {configs.length === 0 && <span style={{ fontSize: 11, color: "#3a5a3c" }}>No saved configs.</span>}
      </div>
      <div style={s.row}>
        <input style={{ ...s.input, flex: 1 }} value={configName}
          onChange={e => setConfigName(e.target.value)} placeholder="Config name" />
        <button style={s.btnPri} onClick={saveConfig}>Save current</button>
      </div>

      {/* Telemetry */}
      <div style={s.h3}>TELEMETRY</div>
      <div style={s.row}>
        <button style={s.btn} onClick={loadTelemetry}>Load</button>
        {telemetry && (
          <span style={{ fontSize: 11, color: "#7a9e7c" }}>
            {telemetry.total_events} events — {Object.entries(telemetry.by_event || {}).map(([k, v]) => `${k}:${v}`).join(" · ")}
          </span>
        )}
      </div>
    </div>
  );
}

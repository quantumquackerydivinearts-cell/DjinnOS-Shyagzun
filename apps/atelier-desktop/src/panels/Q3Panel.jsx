import React, { useState, useRef, useCallback, useEffect } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SHAPES = ["triangle", "square", "pentagon", "hexagon", "heptagon", "circle"];
const SHAPE_LABELS = {
  triangle: "△ Speech",
  square:   "□ Material",
  pentagon: "⬠ Tools",
  hexagon:  "⬡ Nuclear Sophistication",
  heptagon: "⬢ Voting System",
  circle:   "○ Thought / Imagination",
};

const INIT_DEGREES = [
  { value: 1, label: "Solo cognition" },
  { value: 2, label: "Duo cognition" },
  { value: 3, label: "Institution cognition" },
  { value: 4, label: "Family cognition" },
  { value: 5, label: "State cognition" },
  { value: 6, label: "Reboot" },
  { value: 7, label: "Delta space" },
  { value: 8, label: "Global cognition" },
];

const MOTION_TYPES = ["accept", "refuse", "promote", "manage"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function valenceToColor(v) {
  // 0.0 = white, 1.0 = black
  const c = Math.round((1 - v) * 255);
  return `rgb(${c},${c},${c})`;
}

function valenceTextColor(v) {
  return v > 0.5 ? "#e8f0e8" : "#111";
}

function renderShape(shape, x, y, scale, color) {
  const size = 12 + scale * 48;
  const cx = x * 100;
  const cy = y * 100;
  const r = size / 2;

  const strokeColor = color > 0.5 ? "rgba(255,255,255,0.7)" : "rgba(0,0,0,0.7)";

  if (shape === "circle") {
    return <circle cx={`${cx}%`} cy={`${cy}%`} r={r} fill="none" stroke={strokeColor} strokeWidth="1.5" />;
  }
  if (shape === "triangle") {
    const pts = [
      [cx, cy - r],
      [cx - r * 0.866, cy + r * 0.5],
      [cx + r * 0.866, cy + r * 0.5],
    ].map(([px, py]) => `${px}%,${py}%`).join(" ");
    return <polygon points={pts} fill="none" stroke={strokeColor} strokeWidth="1.5" />;
  }
  const sides = { square: 4, pentagon: 5, hexagon: 6, heptagon: 7 }[shape] || 4;
  const pts = Array.from({ length: sides }, (_, i) => {
    const angle = (2 * Math.PI * i) / sides - Math.PI / 2;
    return `${cx + r * Math.cos(angle)}%,${cy + r * Math.sin(angle)}%`;
  }).join(" ");
  return <polygon points={pts} fill="none" stroke={strokeColor} strokeWidth="1.5" />;
}

// ---------------------------------------------------------------------------
// Physix Canvas
// ---------------------------------------------------------------------------

function PhysixCanvas({ valence, placements, onPlace }) {
  const svgRef = useRef(null);

  const handleClick = useCallback((e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = parseFloat(((e.clientX - rect.left) / rect.width).toFixed(6));
    const y = parseFloat(((e.clientY - rect.top) / rect.height).toFixed(6));
    onPlace(x, y);
  }, [onPlace]);

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        ref={svgRef}
        onClick={handleClick}
        style={{
          width: "100%",
          aspectRatio: "1 / 1",
          backgroundColor: valenceToColor(valence),
          cursor: "crosshair",
          display: "block",
          border: "1px solid rgba(200,168,75,0.3)",
        }}
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
      >
        {placements.map((p, i) => (
          <g key={i}>
            {renderShape(p.shape, p.x, p.y, p.scale, valence)}
            <text
              x={`${p.x * 100}%`}
              y={`${p.y * 100 + 3}%`}
              textAnchor="middle"
              fontSize="3"
              fill={valenceTextColor(valence)}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {p.init_degree}
            </text>
          </g>
        ))}
      </svg>
      <p style={{ fontSize: 11, color: "rgba(200,168,75,0.5)", margin: "4px 0 0" }}>
        Click to place shape at coordinates
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function Q3Panel({ apiBase, authToken }) {
  const [tab, setTab] = useState("motions");

  // Motion list
  const [motions, setMotions] = useState([]);
  const [motionsStatus, setMotionsStatus] = useState("idle");

  // New motion form
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newType, setNewType] = useState("accept");
  const [newRef, setNewRef] = useState("");
  const [createStatus, setCreateStatus] = useState("idle");

  // Vote canvas state
  const [activeMotionId, setActiveMotionId] = useState(null);
  const [valence, setValence] = useState(0.5);
  const [pendingShape, setPendingShape] = useState("triangle");
  const [pendingScale, setPendingScale] = useState(0.3);
  const [pendingDegree, setPendingDegree] = useState(1);
  const [placements, setPlacements] = useState([]);
  const [voteStatus, setVoteStatus] = useState("idle");
  const [voteResult, setVoteResult] = useState(null);

  // Audit
  const [auditMotionId, setAuditMotionId] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [auditStatus, setAuditStatus] = useState("idle");

  const headers = { "Content-Type": "application/json", "Authorization": `Bearer ${authToken}` };

  async function loadMotions() {
    setMotionsStatus("loading");
    try {
      const res = await fetch(`${apiBase}/v1/q3/motions`, { headers });
      if (!res.ok) throw new Error(`${res.status}`);
      setMotions(await res.json());
      setMotionsStatus("ok");
    } catch (e) {
      setMotionsStatus(`error:${e}`);
    }
  }

  useEffect(() => { if (tab === "motions") loadMotions(); }, [tab]);

  async function createMotion() {
    setCreateStatus("working");
    try {
      const res = await fetch(`${apiBase}/v1/q3/motions`, {
        method: "POST", headers,
        body: JSON.stringify({ title: newTitle, description: newDesc, motion_type: newType, source_ref: newRef || null }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || res.status);
      setCreateStatus("ok");
      setNewTitle(""); setNewDesc(""); setNewRef("");
      loadMotions();
    } catch (e) {
      setCreateStatus(`error:${e}`);
    }
  }

  function handlePlace(x, y) {
    setPlacements(prev => [...prev, { shape: pendingShape, x, y, scale: pendingScale, init_degree: pendingDegree }]);
  }

  async function castVote() {
    if (!activeMotionId) return;
    setVoteStatus("casting");
    setVoteResult(null);
    try {
      const res = await fetch(`${apiBase}/v1/q3/motions/${activeMotionId}/vote`, {
        method: "POST", headers,
        body: JSON.stringify({ motion_id: activeMotionId, field_valence: valence, placements }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || res.status);
      const data = await res.json();
      setVoteResult(data);
      setVoteStatus("done");
      setPlacements([]);
      loadMotions();
    } catch (e) {
      setVoteStatus(`error:${e}`);
    }
  }

  async function loadAudit(motionId) {
    setAuditMotionId(motionId);
    setAuditStatus("loading");
    setAuditData(null);
    try {
      const res = await fetch(`${apiBase}/v1/q3/motions/${motionId}/audit`, { headers });
      if (!res.ok) throw new Error(`${res.status}`);
      setAuditData(await res.json());
      setAuditStatus("ok");
    } catch (e) {
      setAuditStatus(`error:${e}`);
    }
  }

  return (
    <section className="panel">
      <h2>Q3 — Quantum Quackery Quinary</h2>
      <p className="muted-text">Salt · Mercury · Sulphur · Guild mediation · Commission governance</p>

      <div className="row" style={{ marginBottom: 12 }}>
        {["motions", "vote", "audit"].map(t => (
          <button key={t} className={`action ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Motions tab ── */}
      {tab === "motions" && (
        <div>
          <h3>Active Motions</h3>
          <div className="row" style={{ marginBottom: 8 }}>
            <button className="action" onClick={loadMotions}>Refresh</button>
            <span className="badge">{motionsStatus}</span>
          </div>

          {motions.map(m => (
            <div key={m.id} style={{ padding: "8px 0", borderBottom: "1px solid rgba(200,168,75,0.1)" }}>
              <div className="row">
                <strong>{m.title}</strong>
                <span className="badge">{m.motion_type}</span>
                <span className={`badge ${m.status === "open" ? "badge-ok" : ""}`}>{m.status}</span>
                <span className="badge">{m.vote_count} vote{m.vote_count !== 1 ? "s" : ""}</span>
              </div>
              {m.description && <p className="muted-text" style={{ margin: "2px 0" }}>{m.description}</p>}
              {m.source_ref && <p className="muted-text" style={{ margin: "2px 0", fontSize: 11 }}>ref: {m.source_ref}</p>}
              <div className="row" style={{ marginTop: 4 }}>
                <button className="action" onClick={() => { setActiveMotionId(m.id); setTab("vote"); }}>Vote</button>
                <button className="action" onClick={() => { loadAudit(m.id); setTab("audit"); }}>Audit</button>
              </div>
            </div>
          ))}

          <h3 style={{ marginTop: 20 }}>Open a Motion</h3>
          <div className="row" style={{ marginBottom: 4 }}>
            <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Motion title" style={{ flex: 2 }} />
            <select value={newType} onChange={e => setNewType(e.target.value)}>
              {MOTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="row" style={{ marginBottom: 4 }}>
            <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description (optional)" style={{ flex: 2 }} />
            <input value={newRef} onChange={e => setNewRef(e.target.value)} placeholder="Source ref (lead_id / quote_id)" />
          </div>
          <div className="row">
            <button className="action" onClick={createMotion} disabled={createStatus === "working" || !newTitle}>
              {createStatus === "working" ? "Opening..." : "Open Motion"}
            </button>
            {createStatus && createStatus !== "idle" && createStatus !== "working" && (
              <span className={`badge ${createStatus === "ok" ? "badge-ok" : "badge-error"}`}>{createStatus}</span>
            )}
          </div>
        </div>
      )}

      {/* ── Vote tab ── */}
      {tab === "vote" && (
        <div>
          <h3>Cast Vote</h3>
          {!activeMotionId ? (
            <p className="muted-text">Select a motion from the Motions tab.</p>
          ) : (
            <>
              <div className="row" style={{ marginBottom: 8 }}>
                <span className="badge badge-ok">{`Motion: ${activeMotionId.slice(0, 8)}…`}</span>
                <button className="action" onClick={() => { setPlacements([]); setVoteStatus("idle"); setVoteResult(null); }}>Clear</button>
              </div>

              {/* Valence field */}
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 12, color: "rgba(200,168,75,0.8)" }}>
                  {`Field valence — ${valence.toFixed(3)} (0.0 = white / false · 1.0 = black / true)`}
                </label>
                <input
                  type="range" min="0" max="1" step="0.001"
                  value={valence}
                  onChange={e => setValence(parseFloat(e.target.value))}
                  style={{ width: "100%" }}
                />
              </div>

              {/* Shape controls */}
              <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 4 }}>
                {SHAPES.map(s => (
                  <button
                    key={s}
                    className={`action ${pendingShape === s ? "active" : ""}`}
                    onClick={() => setPendingShape(s)}
                    style={{ fontSize: 11 }}
                  >
                    {SHAPE_LABELS[s]}
                  </button>
                ))}
              </div>

              <div className="row" style={{ marginBottom: 8 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "rgba(200,168,75,0.6)" }}>{`Scale (volume basis): ${pendingScale.toFixed(3)}`}</label>
                  <input type="range" min="0" max="1" step="0.001" value={pendingScale}
                    onChange={e => setPendingScale(parseFloat(e.target.value))} style={{ width: "100%" }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "rgba(200,168,75,0.6)" }}>Init degree (abstraction)</label>
                  <select value={pendingDegree} onChange={e => setPendingDegree(parseInt(e.target.value))} style={{ width: "100%" }}>
                    {INIT_DEGREES.map(d => <option key={d.value} value={d.value}>{d.value} — {d.label}</option>)}
                  </select>
                </div>
              </div>

              <PhysixCanvas valence={valence} placements={placements} onPlace={handlePlace} />

              {placements.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <p style={{ fontSize: 11, color: "rgba(200,168,75,0.6)", margin: "0 0 4px" }}>
                    {`${placements.length} placement${placements.length !== 1 ? "s" : ""}`}
                  </p>
                  {placements.map((p, i) => (
                    <div key={i} className="row" style={{ fontSize: 11, gap: 4 }}>
                      <span className="badge">{SHAPE_LABELS[p.shape]}</span>
                      <span className="badge">{`x:${p.x.toFixed(3)} y:${p.y.toFixed(3)}`}</span>
                      <span className="badge">{`scale:${p.scale.toFixed(3)}`}</span>
                      <span className="badge">{INIT_DEGREES.find(d => d.value === p.init_degree)?.label}</span>
                      <button style={{ fontSize: 10, padding: "1px 4px" }}
                        onClick={() => setPlacements(prev => prev.filter((_, j) => j !== i))}>✕</button>
                    </div>
                  ))}
                </div>
              )}

              <div className="row" style={{ marginTop: 12 }}>
                <button className="action" onClick={castVote}
                  disabled={voteStatus === "casting"}>
                  {voteStatus === "casting" ? "Casting..." : "Submit Vote"}
                </button>
                {voteStatus === "done" && <span className="badge badge-ok">Vote cast — Shygazun Physix recorded</span>}
                {voteStatus.startsWith("error") && <span className="badge badge-error">{voteStatus}</span>}
              </div>

              {voteResult && (
                <details style={{ marginTop: 12 }}>
                  <summary style={{ fontSize: 11, color: "rgba(200,168,75,0.6)", cursor: "pointer" }}>
                    Shygazun Physix tags (your vote record)
                  </summary>
                  <pre style={{ fontSize: 10, overflow: "auto", maxHeight: 300, marginTop: 4 }}>
                    {JSON.stringify(voteResult.shygazun_tags, null, 2)}
                  </pre>
                </details>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Audit tab ── */}
      {tab === "audit" && (
        <div>
          <h3>Audit</h3>
          {auditStatus === "loading" && <p className="muted-text">Loading audit…</p>}
          {auditStatus.startsWith("error") && <p className="error-text">{auditStatus}</p>}
          {auditData && (
            <>
              <div className="row" style={{ marginBottom: 8 }}>
                <strong>{auditData.motion.title}</strong>
                <span className="badge">{auditData.motion.motion_type}</span>
                <span className="badge">{auditData.votes.length} vote{auditData.votes.length !== 1 ? "s" : ""}</span>
              </div>
              <p className="muted-text" style={{ fontSize: 11, marginBottom: 12 }}>
                Voter identities are not shown. Vote configurations are fully exposed for audit.
              </p>
              {auditData.votes.map((v, i) => (
                <details key={v.id} style={{ marginBottom: 8 }}>
                  <summary style={{ fontSize: 12, cursor: "pointer", color: "rgba(200,168,75,0.8)" }}>
                    {`Vote ${i + 1} — cast ${new Date(v.cast_at).toLocaleString()}`}
                  </summary>
                  <div style={{ paddingLeft: 12, marginTop: 4 }}>
                    <div className="row" style={{ marginBottom: 4 }}>
                      <span className="badge">{`valence: ${v.field_valence.value?.toFixed(3)}`}</span>
                      <span className="badge">{`${v.field_valence.symbol} — ${v.field_valence.meaning}`}</span>
                    </div>
                    {v.placements.map((p, j) => (
                      <div key={j} style={{ fontSize: 11, marginBottom: 4 }}>
                        <div className="row" style={{ flexWrap: "wrap", gap: 3 }}>
                          {Object.entries(p.shygazun_tags).map(([k, tag]) => (
                            <span key={k} className="badge" title={tag.meaning}>
                              {`${k}: ${tag.symbol}(${tag.byte}) ${tag.value !== undefined ? `= ${typeof tag.value === "number" ? tag.value.toFixed(3) : tag.value}` : ""}`}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </>
          )}
          {!auditData && auditStatus === "idle" && (
            <p className="muted-text">Select a motion from the Motions tab and click Audit.</p>
          )}
        </div>
      )}
    </section>
  );
}

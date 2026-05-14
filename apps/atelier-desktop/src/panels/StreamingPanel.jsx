/**
 * StreamingPanel.jsx — DjinnOS streaming platform client.
 *
 * Talks to apps/atelier-streaming (port 7800) which bridges the kernel's
 * C streaming module. Uses QCR (Queried Collapse Routing) for discovery:
 * enter tongue numbers, pick a Djinn mode, get semantically resonant streams.
 */
import React, { useCallback, useEffect, useState } from "react";

const BRIDGE = "http://localhost:7800";

const MODE_OPTS = [
  { value: "giann",    label: "Giann — deterministic" },
  { value: "keshi",    label: "Keshi — temperature" },
  { value: "drovitth", label: "Drovitth — temporal" },
];

const TONGUE_NAMES = {
  1:"Lotus",2:"Rose",3:"Sakura",4:"Daisy",5:"AppleBlossom",
  6:"Aster",7:"Grapevine",8:"Cannabis",9:"Dragon",10:"Virus",
  11:"Bacteria",12:"Excavata",13:"Archaeplastida",14:"Myxozoa",
  15:"Archaea",16:"Protist",17:"Immune",18:"Neural",19:"Serpent",
  20:"Beast",21:"Cherub",22:"Chimera",23:"Faerie",24:"Djinn",
};

const C = {
  bg:     "#080d08",
  panel:  "#0c130c",
  card:   "#0b100b",
  border: "#1a2a1a",
  accent: "#3ab8a0",
  dim:    "#3a5a3c",
  muted:  "#7a9e7c",
  text:   "#c8d8c8",
  red:    "#db8a8a",
  gold:   "#d4af37",
};

const inp = {
  background: C.card, border: `1px solid ${C.border}`,
  borderRadius: 3, color: C.text, fontSize: 12, padding: "4px 8px",
};

function Btn({ onClick, children, style, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: "none", border: `1px solid ${disabled ? C.dim : C.accent}`,
      borderRadius: 3, color: disabled ? C.dim : C.accent,
      fontSize: 11, padding: "3px 10px", cursor: disabled ? "default" : "pointer",
      ...style,
    }}>{children}</button>
  );
}

function CoordChip({ addr }) {
  return (
    <span style={{
      background: "#0f1e0f", border: `1px solid ${C.dim}`,
      borderRadius: 3, color: C.muted, fontSize: 10,
      padding: "1px 5px", fontFamily: "monospace", marginRight: 3,
    }}>{addr}</span>
  );
}

function StreamCard({ stream, onTick }) {
  const [ticking, setTicking] = useState(false);
  async function tick() {
    setTicking(true);
    try { await fetch(`${BRIDGE}/streams/${stream.id}/tick`, { method: "POST" }); }
    finally { setTicking(false); }
  }
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderRadius: 6, padding: "10px 14px", marginBottom: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: stream.active ? "#4ade80" : C.dim, flexShrink: 0,
        }} />
        <span style={{ color: C.accent, fontSize: 13, flex: 1 }}>{stream.label || stream.id}</span>
        <Btn onClick={tick} disabled={ticking} style={{ fontSize: 10 }}>
          {ticking ? "…" : "Tick entropy"}
        </Btn>
      </div>
      <div style={{ color: C.dim, fontSize: 10, fontFamily: "monospace", marginBottom: 4 }}>
        {stream.id}
      </div>
      <div>
        {(stream.coords || []).map(a => <CoordChip key={a} addr={a} />)}
      </div>
    </div>
  );
}

export function StreamingPanel({ authToken }) {
  const [tab, setTab]             = useState("discover");
  const [streams, setStreams]      = useState([]);
  const [discoverResults, setDisc] = useState([]);
  const [tongueInput, setTongues]  = useState("2 3");
  const [mode, setMode]            = useState("giann");
  const [temp, setTemp]            = useState("1.5");
  const [err, setErr]              = useState("");
  const [busy, setBusy]            = useState(false);
  // Register form
  const [regId, setRegId]          = useState("");
  const [regLabel, setRegLabel]    = useState("");
  const [regCoords, setRegCoords]  = useState("");

  const hdrs = authToken
    ? { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` }
    : { "Content-Type": "application/json" };

  const loadStreams = useCallback(async () => {
    try {
      const r = await fetch(`${BRIDGE}/streams`);
      const d = await r.json();
      setStreams(d.streams || []);
    } catch (e) { setErr(String(e?.message || e)); }
  }, []);

  useEffect(() => { loadStreams(); }, [loadStreams]);

  async function discover() {
    setBusy(true); setErr(""); setDisc([]);
    const tongues = tongueInput.split(/[\s,]+/).map(Number).filter(n => n > 0 && n <= 38);
    if (!tongues.length) { setErr("Enter at least one tongue number (1–38)"); setBusy(false); return; }
    try {
      const r = await fetch(`${BRIDGE}/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tongues, mode, temp: parseFloat(temp) || 1.0 }),
      });
      const d = await r.json();
      setDisc(d.streams || []);
    } catch (e) { setErr(String(e?.message || e)); }
    finally { setBusy(false); }
  }

  async function register() {
    if (!regId.trim()) { setErr("ID required"); return; }
    setBusy(true); setErr("");
    const coords = regCoords.split(/[\s,]+/).map(Number).filter(n => n > 0);
    try {
      const r = await fetch(`${BRIDGE}/streams`, {
        method: "POST", headers: hdrs,
        body: JSON.stringify({ id: regId.trim(), label: regLabel.trim(), coords }),
      });
      const d = await r.json();
      if (d.ok) { setRegId(""); setRegLabel(""); setRegCoords(""); await loadStreams(); }
      else setErr(d.error || "register failed");
    } catch (e) { setErr(String(e?.message || e)); }
    finally { setBusy(false); }
  }

  async function unregister(id) {
    try {
      await fetch(`${BRIDGE}/streams/${encodeURIComponent(id)}`, { method: "DELETE" });
      await loadStreams();
    } catch (e) { setErr(String(e?.message || e)); }
  }

  const TABS = ["discover", "streams", "register"];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", background: C.bg, color: C.text }}>
      {/* tab bar */}
      <div style={{ display: "flex", borderBottom: `1px solid ${C.border}`, background: "#0c130c", flexShrink: 0 }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: tab === t ? "#1a2a1a" : "none",
            border: "none",
            borderBottom: tab === t ? `2px solid ${C.accent}` : "2px solid transparent",
            color: tab === t ? C.accent : C.muted,
            fontSize: 12, padding: "8px 16px", cursor: "pointer", letterSpacing: 1,
            textTransform: "uppercase",
          }}>{t}</button>
        ))}
      </div>

      {err && (
        <div style={{ color: C.red, fontSize: 11, padding: "6px 12px", background: "#1a0808" }}>
          {err}
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: 14 }}>

        {/* ── DISCOVER ── */}
        {tab === "discover" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.5 }}>
              Enter tongue numbers separated by spaces. The Hopfield network collapses
              toward the nearest attractor; streams whose coordinates overlap are returned.
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <input
                value={tongueInput} onChange={e => setTongues(e.target.value)}
                placeholder="e.g. 2 3 7"
                style={{ ...inp, width: 180 }}
              />
              <select value={mode} onChange={e => setMode(e.target.value)} style={inp}>
                {MODE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              {mode === "keshi" && (
                <input value={temp} onChange={e => setTemp(e.target.value)}
                  placeholder="temp" style={{ ...inp, width: 70 }} />
              )}
              <Btn onClick={discover} disabled={busy}>{busy ? "…" : "Discover"}</Btn>
            </div>

            {/* tongue reference */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {Object.entries(TONGUE_NAMES).map(([n, name]) => (
                <button key={n} onClick={() => {
                  const nums = tongueInput.trim() ? tongueInput.split(/[\s,]+/) : [];
                  if (!nums.includes(n)) setTongues([...nums, n].join(" "));
                }} style={{
                  background: tongueInput.split(/[\s,]+/).includes(n) ? C.accent + "33" : C.card,
                  border: `1px solid ${C.border}`, borderRadius: 3,
                  color: C.muted, fontSize: 10, padding: "2px 6px", cursor: "pointer",
                }}>
                  {n} {name}
                </button>
              ))}
            </div>

            {discoverResults.length === 0 && !busy && (
              <div style={{ color: C.dim, fontSize: 12 }}>No results yet — run a query.</div>
            )}
            {discoverResults.map(s => <StreamCard key={s.id} stream={s} />)}
          </div>
        )}

        {/* ── STREAMS ── */}
        {tab === "streams" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ color: C.muted, fontSize: 12 }}>{streams.length} stream{streams.length !== 1 ? "s" : ""} registered</span>
              <Btn onClick={loadStreams}>↺ Refresh</Btn>
            </div>
            {streams.length === 0 && <div style={{ color: C.dim, fontSize: 12 }}>No streams registered.</div>}
            {streams.map(s => (
              <div key={s.id} style={{ position: "relative" }}>
                <StreamCard stream={s} />
                <button onClick={() => unregister(s.id)} style={{
                  position: "absolute", top: 10, right: 10,
                  background: "none", border: "none", color: C.dim,
                  fontSize: 11, cursor: "pointer",
                }}>✕</button>
              </div>
            ))}
          </div>
        )}

        {/* ── REGISTER ── */}
        {tab === "register" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 420 }}>
            <div style={{ color: C.muted, fontSize: 11 }}>
              Register a stream with byte-table coordinates. Coordinates are used by
              the Hopfield network during QCR discovery.
            </div>
            <div>
              <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Stream ID</div>
              <input value={regId} onChange={e => setRegId(e.target.value)}
                placeholder="unique-stream-id" style={{ ...inp, width: "100%" }} />
            </div>
            <div>
              <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Label</div>
              <input value={regLabel} onChange={e => setRegLabel(e.target.value)}
                placeholder="Human-readable name" style={{ ...inp, width: "100%" }} />
            </div>
            <div>
              <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Byte-table coordinates (space or comma separated)</div>
              <input value={regCoords} onChange={e => setRegCoords(e.target.value)}
                placeholder="e.g. 45 87 193" style={{ ...inp, width: "100%" }} />
            </div>
            <Btn onClick={register} disabled={busy}>{busy ? "Registering…" : "Register stream"}</Btn>
          </div>
        )}
      </div>
    </div>
  );
}

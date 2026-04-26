import React, { useState, useRef, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Constants — mirrors Q3Panel shape/degree definitions
// ---------------------------------------------------------------------------

const SHAPES = ["triangle", "square", "pentagon", "hexagon", "heptagon", "circle"];
const SHAPE_LABELS = {
  triangle: "△ Speech",
  square:   "□ Material",
  pentagon: "⬠ Tools",
  hexagon:  "⬡ Nuclear",
  heptagon: "⬢ Voting",
  circle:   "○ Thought",
};
const INIT_DEGREES = [
  { value: 1, label: "Solo" },
  { value: 2, label: "Duo" },
  { value: 3, label: "Institution" },
  { value: 4, label: "Family" },
  { value: 5, label: "State" },
  { value: 6, label: "Reboot" },
  { value: 7, label: "Delta space" },
  { value: 8, label: "Global" },
];

const CANVAS_W = 720;
const CANVAS_H = 360;

// ---------------------------------------------------------------------------
// Coordinate helpers
// ---------------------------------------------------------------------------

function latLonToCanvas(lat, lon) {
  return [
    ((lon + 180) / 360) * CANVAS_W,
    ((90 - lat)  / 180) * CANVAS_H,
  ];
}

function canvasToLatLon(cx, cy) {
  return [
    90  - (cy / CANVAS_H) * 180,
    -180 + (cx / CANVAS_W) * 360,
  ];
}

// ---------------------------------------------------------------------------
// Canvas drawing
// ---------------------------------------------------------------------------

function valenceGray(v) {
  return Math.round((1 - v) * 255);
}

function drawTileGrid(ctx, tileData) {
  if (!tileData) return;
  const tw = CANVAS_W / tileData.width;
  const th = CANVAS_H / tileData.height;
  const { tiles, width } = tileData;
  for (let i = 0; i < tiles.length; i++) {
    const xi = i % width;
    const yi = Math.floor(i / width);
    const c  = valenceGray(tiles[i]);
    ctx.fillStyle = `rgb(${c},${c},${c})`;
    // +0.6 overlap eliminates sub-pixel gaps between tiles
    ctx.fillRect(xi * tw, yi * th, tw + 0.6, th + 0.6);
  }
}

function drawShape(ctx, shape, cx, cy, size, fillColor, strokeColor) {
  const r = size / 2;
  ctx.beginPath();
  if (shape === "circle") {
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
  } else {
    const sides = { triangle: 3, square: 4, pentagon: 5, hexagon: 6, heptagon: 7 }[shape] || 4;
    for (let i = 0; i < sides; i++) {
      const angle = (2 * Math.PI * i / sides) - Math.PI / 2;
      const px = cx + r * Math.cos(angle);
      const py = cy + r * Math.sin(angle);
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.closePath();
  }
  ctx.fillStyle   = fillColor;
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth   = 1.2;
  ctx.fill();
  ctx.stroke();
}

function drawPlacement(ctx, p, isPending) {
  const [cx, cy] = latLonToCanvas(p.lat, p.lon);
  const size  = 10 + (p.scale || 0.3) * 28;
  const c     = valenceGray(p.field_valence ?? p.valence ?? 0.5);
  const alpha = isPending ? 0.45 : 0.82;
  drawShape(
    ctx,
    p.shape,
    cx, cy,
    size,
    `rgba(${c},${c},${c},${alpha})`,
    "rgba(200,168,75,0.85)",
  );
}

function redrawCanvas(ctx, tileData, livePlacements, pendingPlacements) {
  ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
  drawTileGrid(ctx, tileData);
  livePlacements.forEach(p  => drawPlacement(ctx, p, false));
  pendingPlacements.forEach(p => drawPlacement(ctx, p, true));
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function SupraLibrixPanel({ apiBase, authToken }) {
  const canvasRef = useRef(null);

  const [tileData,  setTileData]  = useState(null);
  const [tileError, setTileError] = useState(null);
  const [livePlacements,    setLivePlacements]    = useState([]);
  const [pendingPlacements, setPendingPlacements] = useState([]);

  const [valence,       setValence]       = useState(0.5);
  const [pendingShape,  setPendingShape]  = useState("triangle");
  const [pendingScale,  setPendingScale]  = useState(0.3);
  const [pendingDegree, setPendingDegree] = useState(1);

  const [submitStatus, setSubmitStatus] = useState("idle");
  const [wsStatus,     setWsStatus]     = useState("connecting");
  const [utterance,    setUtterance]    = useState("");

  const wsRef = useRef(null);

  // Load tile grid
  useEffect(() => {
    fetch(`${apiBase}/v1/supra_librix/tiles`)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(setTileData)
      .catch(e => setTileError(String(e)));
  }, [apiBase]);

  // Load existing placements for canvas catchup
  useEffect(() => {
    fetch(`${apiBase}/v1/supra_librix/placements`)
      .then(r => r.ok ? r.json() : [])
      .then(rows => setLivePlacements(rows))
      .catch(() => {});
  }, [apiBase]);

  // WebSocket live feed
  useEffect(() => {
    const wsUrl = apiBase.replace(/^http/, "ws") + "/v1/supra_librix/live";
    let ws;
    let dead = false;

    function connect() {
      if (dead) return;
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen    = () => setWsStatus("live");
      ws.onclose   = () => {
        setWsStatus("reconnecting");
        if (!dead) setTimeout(connect, 3000);
      };
      ws.onerror   = () => setWsStatus("error");
      ws.onmessage = e => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.placements) {
            setLivePlacements(prev => [
              ...prev,
              ...msg.placements.map(p => ({ ...p, field_valence: msg.field_valence })),
            ]);
          }
        } catch (_) {}
      };
    }

    connect();
    return () => { dead = true; ws && ws.close(); };
  }, [apiBase]);

  // Redraw canvas whenever data changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    redrawCanvas(ctx, tileData, livePlacements, pendingPlacements);
  }, [tileData, livePlacements, pendingPlacements]);

  // Click on canvas → add pending placement
  const handleCanvasClick = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    const cx = (e.clientX - rect.left) * scaleX;
    const cy = (e.clientY - rect.top)  * scaleY;
    const [lat, lon] = canvasToLatLon(cx, cy);
    setPendingPlacements(prev => [
      ...prev,
      { lat, lon, shape: pendingShape, scale: pendingScale,
        init_degree: pendingDegree, valence, field_valence: valence },
    ]);
  }, [pendingShape, pendingScale, pendingDegree, valence]);

  async function submitVote() {
    if (!pendingPlacements.length) return;
    setSubmitStatus("casting");
    try {
      const res = await fetch(`${apiBase}/v1/supra_librix/place`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`,
        },
        body: JSON.stringify({ field_valence: valence, placements: pendingPlacements }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || res.status);
      const data = await res.json();
      setUtterance(data.utterance || "");
      setPendingPlacements([]);
      setSubmitStatus("done");
    } catch (e) {
      setSubmitStatus(`error:${e.message}`);
    }
  }

  function clearPending() {
    setPendingPlacements([]);
    setSubmitStatus("idle");
  }

  function takeSnapshot() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const url = canvas.toDataURL("image/png");
    const a   = document.createElement("a");
    a.href     = url;
    a.download = `supra_librix_${Date.now()}.png`;
    a.click();
  }

  return (
    <section className="panel">
      <h2>Supra Librix</h2>
      <p className="muted-text">Geo-tagged Shygazun Physix · Earth canvas · Live performance</p>

      {/* Status row */}
      <div className="row" style={{ marginBottom: 8 }}>
        <span className={`badge ${wsStatus === "live" ? "badge-ok" : ""}`}>
          {wsStatus === "live" ? "● live" : wsStatus}
        </span>
        {tileError && <span className="badge badge-error">{tileError}</span>}
        {!tileData && !tileError && <span className="badge">loading tiles…</span>}
      </div>

      {/* Map canvas */}
      <div style={{ position: "relative", width: "100%", marginBottom: 12 }}>
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          onClick={handleCanvasClick}
          style={{
            width:       "100%",
            display:     "block",
            cursor:      "crosshair",
            border:      "1px solid rgba(200,168,75,0.25)",
            background:  "#fff",
          }}
        />
      </div>

      {/* Controls */}
      <div style={{ marginBottom: 10 }}>
        <label style={{ display: "block", marginBottom: 4, fontSize: 12, color: "rgba(200,168,75,0.8)" }}>
          {`Field valence — ${valence.toFixed(3)}  (0.0 white · 1.0 black)`}
        </label>
        <input type="range" min="0" max="1" step="0.001"
          value={valence} onChange={e => setValence(parseFloat(e.target.value))}
          style={{ width: "100%" }} />
      </div>

      <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 4 }}>
        {SHAPES.map(s => (
          <button key={s}
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
          <label style={{ fontSize: 11, color: "rgba(200,168,75,0.6)" }}>
            {`Scale: ${pendingScale.toFixed(3)}`}
          </label>
          <input type="range" min="0" max="1" step="0.001"
            value={pendingScale} onChange={e => setPendingScale(parseFloat(e.target.value))}
            style={{ width: "100%" }} />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "rgba(200,168,75,0.6)" }}>Init degree</label>
          <select value={pendingDegree} onChange={e => setPendingDegree(parseInt(e.target.value))}
            style={{ width: "100%" }}>
            {INIT_DEGREES.map(d => (
              <option key={d.value} value={d.value}>{d.value} — {d.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Pending list */}
      {pendingPlacements.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <p style={{ fontSize: 11, color: "rgba(200,168,75,0.6)", margin: "0 0 4px" }}>
            {`${pendingPlacements.length} placement${pendingPlacements.length !== 1 ? "s" : ""} pending`}
          </p>
          {pendingPlacements.map((p, i) => (
            <div key={i} className="row" style={{ fontSize: 11, gap: 3 }}>
              <span className="badge">{SHAPE_LABELS[p.shape]}</span>
              <span className="badge">{`${p.lat.toFixed(2)}°, ${p.lon.toFixed(2)}°`}</span>
              <span className="badge">{`scale:${p.scale.toFixed(3)}`}</span>
              <span className="badge">{INIT_DEGREES.find(d => d.value === p.init_degree)?.label}</span>
              <button style={{ fontSize: 10, padding: "1px 4px" }}
                onClick={() => setPendingPlacements(prev => prev.filter((_, j) => j !== i))}>
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="row" style={{ marginTop: 8, flexWrap: "wrap", gap: 4 }}>
        <button className="action" onClick={submitVote}
          disabled={!pendingPlacements.length || submitStatus === "casting"}>
          {submitStatus === "casting" ? "Casting…" : "Submit Vote"}
        </button>
        <button className="action" onClick={clearPending}
          disabled={!pendingPlacements.length}>
          Clear Pending
        </button>
        <button className="action" onClick={takeSnapshot}>
          Snapshot PNG
        </button>
        {submitStatus === "done" && (
          <span className="badge badge-ok">cast</span>
        )}
        {submitStatus.startsWith("error") && (
          <span className="badge badge-error">{submitStatus}</span>
        )}
      </div>

      {/* Utterance */}
      {utterance && (
        <p style={{ marginTop: 10, fontFamily: "monospace", fontSize: 12,
                    color: "rgba(200,168,75,0.9)", letterSpacing: 1 }}>
          {utterance}
        </p>
      )}
    </section>
  );
}
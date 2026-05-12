/**
 * SemanticFieldPanel.jsx — Hopfield semantic field visualisation.
 *
 * Navigation IS convergence. You specify a seed (tongue, address, or diff)
 * and watch the semantic field settle into the nearest coherent state.
 * Activated candidates surface as nodes; the topology reorganises around
 * your query — not because of recommendations, but because the factorisation
 * geometry of the byte table defines what is near what.
 *
 * Three Djinn modes:
 *   Giann  — deterministic: inverse-distance kernel, finds the energy minimum
 *   Keshi  — entropic: exponential kernel with temperature, explores the basin
 *   Drovitth — periodic: resonant kernel, tongue-register harmonics only
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const API = 'http://localhost:9000/v1/intel';

// ── Tongue colour map ─────────────────────────────────────────────────────────
const TONGUE_COLORS = {
  Lotus:          '#c8783c',
  Rose:           '#d44060',
  Sakura:         '#e8a0b0',
  Daisy:          '#80d080',
  AppleBlossom:   '#a060d0',
  Aster:          '#4080d0',
  Grapevine:      '#d0a040',
  Cannabis:       '#60c080',
  Dragon:         '#c04040',
  Virus:          '#8040c0',
  Bacteria:       '#40c0a0',
  Excavata:       '#c08040',
  Archaeplastida: '#40a0c0',
  Myxozoa:        '#a04080',
  Archaea:        '#80c040',
  Protist:        '#c0c040',
  Immune:         '#4060c0',
  Neural:         '#c04060',
  Serpent:        '#60d0c0',
  Beast:          '#d06040',
  Cherub:         '#a080d0',
  Chimera:        '#d080a0',
  Faerie:         '#80d0d0',
  Djinn:          '#d0d080',
  Fold:           '#a0c080',
  Topology:       '#80a0c0',
  Phase:          '#c080c0',
  Gradient:       '#c0a060',
  Curvature:      '#60c0a0',
  Prion:          '#a06080',
  Blood:          '#d04040',
  Moon:           '#c0c0d0',
  Koi:            '#60a0d0',
  Rope:           '#d06080',
  Hook:           '#80d060',
  Fang:           '#d0a080',
  Circle:         '#a0d0a0',
  Ledger:         '#8080a0',
};
const DEFAULT_COLOR = '#888888';

// ── Kernel descriptions ───────────────────────────────────────────────────────
const KERNELS = [
  { id: 'giann',    label: 'Giann',    desc: 'Deterministic — finds energy minimum' },
  { id: 'keshi',    label: 'Keshi',    desc: 'Entropic — temperature-weighted exploration' },
  { id: 'drovitth', label: 'Drovitth', desc: 'Periodic — tongue-register harmonics' },
  { id: 'saelith',  label: 'Saelith',  desc: 'Threshold — hard distance gate' },
];

// ── Semantic field canvas ─────────────────────────────────────────────────────

function FieldCanvas({ state, candidates, activeIndices, width, height }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !candidates.length) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    // Map byte address to x position (log-compressed for visual spread).
    const maxAddr = 1403;
    const addrToX = (addr) => {
      const t = Math.log1p(addr) / Math.log1p(maxAddr);
      return 20 + t * (width - 40);
    };

    // Map activation value to y (higher activation = higher on canvas).
    const valToY = (v) => height - 20 - ((v + 1) / 2) * (height - 40);

    // Background gradient.
    const bg = ctx.createLinearGradient(0, 0, 0, height);
    bg.addColorStop(0, '#0a0810');
    bg.addColorStop(1, '#06050c');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    // Draw activation field as a landscape curve.
    if (state && state.length) {
      ctx.beginPath();
      ctx.moveTo(0, height);
      for (let i = 0; i < candidates.length; i++) {
        const c = candidates[i];
        const x = addrToX(c.addr);
        const y = valToY(state[i] ?? 0);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineTo(width, height);
      ctx.closePath();
      const fieldGrad = ctx.createLinearGradient(0, 0, 0, height);
      fieldGrad.addColorStop(0, 'rgba(96, 160, 200, 0.15)');
      fieldGrad.addColorStop(1, 'rgba(96, 160, 200, 0.02)');
      ctx.fillStyle = fieldGrad;
      ctx.fill();
      ctx.strokeStyle = 'rgba(96, 160, 200, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw candidate nodes.
    if (candidates.length) {
      for (let i = 0; i < candidates.length; i++) {
        const c = candidates[i];
        const activation = state ? (state[i] ?? 0) : 0;
        const isActive = activeIndices.has(i);
        const x = addrToX(c.addr);
        const y = valToY(activation);
        const r = isActive ? 4 : 1.5;
        const color = TONGUE_COLORS[c.tongue] ?? DEFAULT_COLOR;
        const alpha = isActive ? 1.0 : 0.2 + 0.3 * Math.max(0, activation);

        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fillStyle = color + Math.round(alpha * 255).toString(16).padStart(2, '0');
        ctx.fill();

        if (isActive) {
          // Glow
          ctx.beginPath();
          ctx.arc(x, y, r + 4, 0, Math.PI * 2);
          ctx.fillStyle = color + '22';
          ctx.fill();
          // Label
          ctx.fillStyle = color;
          ctx.font = '10px monospace';
          ctx.fillText(c.symbol, x + 6, y - 2);
        }
      }
    }

    // Tongue boundary markers.
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    const seenTongues = new Set();
    for (const c of candidates) {
      if (!seenTongues.has(c.tongue)) {
        seenTongues.add(c.tongue);
        const x = addrToX(c.addr);
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.font = '9px monospace';
        ctx.fillText(c.tongue.slice(0, 4), x + 2, 12);
      }
    }
  }, [state, candidates, activeIndices, width, height]);

  return <canvas ref={canvasRef} width={width} height={height}
    style={{ display: 'block', borderRadius: 4 }} />;
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function SemanticFieldPanel() {
  const [tongues, setTongues]           = useState([]);
  const [candidates, setCandidates]     = useState([]);
  const [selectedTongues, setSelected]  = useState([]);
  const [kernel, setKernel]             = useState('giann');
  const [temp, setTemp]                 = useState(1.0);
  const [addrInput, setAddrInput]       = useState('');
  const [deltaInput, setDeltaInput]     = useState('24');
  const [queryMode, setQueryMode]       = useState('tongue'); // tongue | near | diff
  const [result, setResult]             = useState(null);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState(null);

  const activeIndices = new Set(result?.active ?? []);

  // Load tongue list and all candidates once.
  useEffect(() => {
    fetch(`${API}/tongues`)
      .then(r => r.json())
      .then(setTongues)
      .catch(() => {});
    fetch(`${API}/candidates`)
      .then(r => r.json())
      .then(setCandidates)
      .catch(() => {});
  }, []);

  const runQuery = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let url, body;
      if (queryMode === 'tongue') {
        url  = `${API}/query/tongue`;
        body = { tongues: selectedTongues, kernel, temp: parseFloat(temp) };
      } else if (queryMode === 'near') {
        url  = `${API}/query/near`;
        body = { addr: parseInt(addrInput) || 0, kernel, temp: parseFloat(temp) };
      } else {
        url  = `${API}/query/diff`;
        body = {
          seed_addr: parseInt(addrInput) || 0,
          delta:     parseInt(deltaInput) || 24,
          kernel,
          temp: parseFloat(temp),
        };
      }
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [queryMode, selectedTongues, kernel, temp, addrInput, deltaInput]);

  const toggleTongue = (t) => {
    setSelected(prev =>
      prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]
    );
  };

  const col = (t) => TONGUE_COLORS[t] ?? DEFAULT_COLOR;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%',
                  background: '#0a0810', color: '#c8c0d8', fontFamily: 'monospace',
                  fontSize: 13, padding: 12, gap: 10 }}>

      {/* Header */}
      <div style={{ fontSize: 15, color: '#a080d0', letterSpacing: 1 }}>
        ◈ Semantic Field  <span style={{ fontSize: 11, color: '#604880' }}>
          Hopfield · {candidates.length} candidates · 38 tongues
        </span>
      </div>

      {/* Mode selector */}
      <div style={{ display: 'flex', gap: 6 }}>
        {['tongue', 'near', 'diff'].map(m => (
          <button key={m} onClick={() => setQueryMode(m)}
            style={{
              padding: '3px 10px', borderRadius: 3, cursor: 'pointer', fontSize: 12,
              background: queryMode === m ? '#3a2860' : '#1a1428',
              color: queryMode === m ? '#c0a0e0' : '#806090',
              border: queryMode === m ? '1px solid #604890' : '1px solid #2a2040',
            }}>
            {m === 'tongue' ? 'Tongue' : m === 'near' ? 'Near Addr' : 'Δ Diff'}
          </button>
        ))}
      </div>

      {/* Query controls */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {queryMode === 'tongue' && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', flex: 1 }}>
            {tongues.map(t => (
              <button key={t.tongue} onClick={() => toggleTongue(t.tongue)}
                style={{
                  padding: '2px 7px', borderRadius: 2, cursor: 'pointer', fontSize: 11,
                  background: selectedTongues.includes(t.tongue)
                    ? col(t.tongue) + '44' : '#150e20',
                  color: selectedTongues.includes(t.tongue) ? col(t.tongue) : '#604878',
                  border: `1px solid ${selectedTongues.includes(t.tongue)
                    ? col(t.tongue) + '88' : '#251840'}`,
                }}>
                {t.tongue}
                {t.gated && ' ⚬'}
              </button>
            ))}
          </div>
        )}
        {(queryMode === 'near' || queryMode === 'diff') && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ color: '#604878', fontSize: 11 }}>addr</span>
              <input value={addrInput} onChange={e => setAddrInput(e.target.value)}
                style={{ width: 60, background: '#150e20', border: '1px solid #2a1a40',
                         color: '#c0a0e0', padding: '2px 6px', borderRadius: 3, fontSize: 12 }}
                placeholder="0" />
            </div>
            {queryMode === 'diff' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ color: '#604878', fontSize: 11 }}>δ</span>
                <input value={deltaInput} onChange={e => setDeltaInput(e.target.value)}
                  style={{ width: 50, background: '#150e20', border: '1px solid #2a1a40',
                           color: '#c0a0e0', padding: '2px 6px', borderRadius: 3, fontSize: 12 }}
                  placeholder="24" />
                <span style={{ color: '#403060', fontSize: 10 }}>
                  {parseInt(deltaInput) === 24 ? 'advance tongue' :
                   parseInt(deltaInput) === 6  ? 'Fire→Water (Serpent)' :
                   parseInt(deltaInput) === 10 ? 'Fire→Water (Koi)' : ''}
                </span>
              </div>
            )}
          </>
        )}

        {/* Kernel */}
        <select value={kernel} onChange={e => setKernel(e.target.value)}
          style={{ background: '#150e20', color: '#a080c0', border: '1px solid #2a1a40',
                   padding: '2px 6px', borderRadius: 3, fontSize: 12 }}>
          {KERNELS.map(k => (
            <option key={k.id} value={k.id}>{k.label} — {k.desc}</option>
          ))}
        </select>

        {/* Temp (Keshi mode) */}
        {(kernel === 'keshi') && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: '#604878', fontSize: 11 }}>T</span>
            <input type="range" min="0.1" max="5" step="0.1"
              value={temp} onChange={e => setTemp(e.target.value)}
              style={{ width: 80 }} />
            <span style={{ color: '#c04060', fontSize: 11 }}>{parseFloat(temp).toFixed(1)}</span>
          </div>
        )}

        <button onClick={runQuery} disabled={loading}
          style={{
            padding: '4px 14px', borderRadius: 3, cursor: 'pointer',
            background: loading ? '#1a1428' : '#3a1860',
            color: loading ? '#604878' : '#c090e8',
            border: '1px solid #503878', fontSize: 12,
          }}>
          {loading ? 'converging…' : 'converge'}
        </button>
      </div>

      {/* Field canvas */}
      <div style={{ flex: 1, minHeight: 200, background: '#080612', borderRadius: 4,
                    border: '1px solid #1a1030', overflow: 'hidden' }}>
        <FieldCanvas
          state        = {result?.state ?? null}
          candidates   = {candidates}
          activeIndices= {activeIndices}
          width        = {860}
          height       = {240}
        />
      </div>

      {/* Result summary */}
      {result && (
        <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#604878' }}>
          <span style={{ color: '#a080c0' }}>{result.active.length} active</span>
          <span>energy {result.energy.toFixed(3)}</span>
          <span>{result.iterations} iter</span>
        </div>
      )}

      {/* Active candidates list */}
      {result?.candidates && result.candidates.length > 0 && (
        <div style={{ maxHeight: 180, overflowY: 'auto',
                      background: '#080612', borderRadius: 4,
                      border: '1px solid #1a1030', padding: '6px 8px' }}>
          {result.candidates.slice(0, 40).map((c, i) => (
            <div key={i} onClick={() => {
                   setAddrInput(String(c.addr));
                   setQueryMode('near');
                 }}
              style={{ display: 'flex', gap: 8, padding: '2px 0',
                       cursor: 'pointer', borderBottom: '1px solid #120c1c' }}>
              <span style={{ color: '#403060', width: 36 }}>{c.addr}</span>
              <span style={{ color: col(c.tongue), width: 72, fontSize: 10 }}>{c.tongue}</span>
              <span style={{ color: '#c0a0e0', width: 56 }}>{c.symbol}</span>
              <span style={{ color: '#605080', flex: 1, fontSize: 10,
                             overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.meaning.split(' — ')[0]}
              </span>
              {c.lotus_gated && <span style={{ color: '#c8783c', fontSize: 10 }}>⚬</span>}
            </div>
          ))}
          {result.candidates.length > 40 && (
            <div style={{ color: '#403060', padding: '4px 0' }}>
              +{result.candidates.length - 40} more
            </div>
          )}
        </div>
      )}

      {error && <div style={{ color: '#c04060', fontSize: 11 }}>error: {error}</div>}
    </div>
  );
}

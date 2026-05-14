/**
 * Broadcast.jsx — Broadcaster control room.
 *
 * The practitioner's view while streaming. Sections:
 *   1. Stream credentials (RTMP URL + key)
 *   2. BoK readout (live Julia set of current session geometry)
 *   3. Wunashakoun mode toggle + entropy meter
 *   4. Session metadata (title, tongue coordinates, label)
 *   5. Session summary (shown post-stream: Roko assessment, Quack status)
 *
 * Backend: apps/atelier-streaming running at BRIDGE_URL (default port 7800).
 * OBS configuration: RTMP Server → rtmp://stream.quantumquackery.com:1935/live
 *                    Stream Key  → shown in credentials panel
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Panel, MarblePanel, Button, MetadataChip, EntropyMeter,
         BoKReadout, QuackBadge, LiveBadge, ResonanceMarker }
  from '../components/index.jsx';
import '../tokens.css';

const BRIDGE_URL  = 'http://localhost:7800';
const RTMP_SERVER = 'rtmp://stream.quantumquackery.com:1935/live';

// ── Tongue reference (abbrev) ─────────────────────────────────────────────────
const TONGUE_OPTS = [
  [1,'Lotus'],[2,'Rose'],[3,'Sakura'],[4,'Daisy'],[5,'AppleBlossom'],
  [6,'Aster'],[7,'Grapevine'],[8,'Cannabis'],[9,'Dragon'],[10,'Virus'],
  [11,'Bacteria'],[12,'Excavata'],[13,'Archaeplastida'],[14,'Myxozoa'],
  [15,'Archaea'],[16,'Protist'],[17,'Immune'],[18,'Neural'],[19,'Serpent'],
  [20,'Beast'],[21,'Cherub'],[22,'Chimera'],[23,'Faerie'],[24,'Djinn'],
];

export function Broadcast({ authToken, artisanId }) {
  // ── Stream state ───────────────────────────────────────────────────────────
  const [streamKey,  setStreamKey]  = useState('');
  const [streamId,   setStreamId]   = useState('');
  const [live,       setLive]       = useState(false);
  const [viewers,    setViewers]    = useState(0);
  const [err,        setErr]        = useState('');
  const [busy,       setBusy]       = useState(false);

  // ── Metadata ───────────────────────────────────────────────────────────────
  const [title,      setTitle]      = useState('');
  const [tongues,    setTongues]    = useState([]);
  const [coords,     setCoords]     = useState('');

  // ── BoK / Wunashakoun ──────────────────────────────────────────────────────
  const [bok,        setBok]        = useState(null);   // { re, im }
  const [wMode,      setWMode]      = useState(false);  // Wunashakoun mode
  const [entTicks,   setEntTicks]   = useState(0);
  const [entValue,   setEntValue]   = useState(0);
  const bokIntervalRef = useRef(null);

  // ── Session summary ────────────────────────────────────────────────────────
  const [summary,    setSummary]    = useState(null);
  const [markers,    setMarkers]    = useState([]);

  const hdrs = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  };

  // ── Poll stream status while live ──────────────────────────────────────────
  useEffect(() => {
    if (!live || !streamId) return;
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${BRIDGE_URL}/streams/${streamId}/status`);
        if (!r.ok) return;
        const d = await r.json();
        setLive(d.live ?? false);
        setViewers(d.viewers ?? 0);
      } catch {}
    }, 5000);
    return () => clearInterval(iv);
  }, [live, streamId]);

  // ── BoK polling while Wunashakoun mode is on ───────────────────────────────
  useEffect(() => {
    if (!wMode || !live) {
      if (bokIntervalRef.current) clearInterval(bokIntervalRef.current);
      return;
    }
    bokIntervalRef.current = setInterval(() => {
      emitBokTick();
    }, 30_000);  // every 30s per spec
    return () => clearInterval(bokIntervalRef.current);
  }, [wMode, live]);  // eslint-disable-line

  // ── Actions ────────────────────────────────────────────────────────────────

  async function startStream() {
    if (!title.trim()) { setErr('Title required'); return; }
    setBusy(true); setErr('');
    try {
      const coordArr = coords.split(/[\s,]+/).map(Number).filter(n => n > 0);
      const body = {
        id:      `${artisanId}-${Date.now()}`,
        label:   title.trim(),
        coords:  coordArr,
        tongues: tongues.map(Number),
      };
      const r = await fetch(`${BRIDGE_URL}/streams`, { method: 'POST', headers: hdrs, body: JSON.stringify(body) });
      const d = await r.json();
      if (!d.ok) throw new Error(d.error || 'Failed to register stream');
      setStreamId(body.id);

      // Get RTMP key from backend
      const kr = await fetch(`${BRIDGE_URL}/streams/${body.id}/key`, { headers: hdrs });
      const kd = await kr.json();
      setStreamKey(kd.key || body.id);
      setLive(true);
      setSummary(null);
      setMarkers([]);
    } catch (e) { setErr(String(e?.message || e)); }
    finally { setBusy(false); }
  }

  async function endStream() {
    if (!streamId) return;
    setBusy(true);
    try {
      const r = await fetch(`${BRIDGE_URL}/streams/${streamId}/end`,
        { method: 'POST', headers: hdrs });
      const d = await r.json();
      setLive(false);
      setSummary(d.summary || null);
    } catch (e) { setErr(String(e?.message || e)); }
    finally { setBusy(false); }
  }

  async function emitBokTick() {
    if (!streamId || !bok) return;
    try {
      await fetch(`${BRIDGE_URL}/streams/${streamId}/bok`, {
        method: 'POST', headers: hdrs,
        body: JSON.stringify({ re: bok.re, im: bok.im, ts: Date.now() / 1000 }),
      });
      setEntTicks(t => t + 1);
      setEntValue(v => Math.min(1, v + 0.04));
    } catch {}
  }

  function toggleTongue(n) {
    setTongues(prev => prev.includes(n) ? prev.filter(x => x !== n) : [...prev, n]);
  }

  function copyRtmpUrl() {
    const url = `${RTMP_SERVER}/${streamKey}`;
    navigator.clipboard?.writeText(url).catch(() => {});
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="streaming-root" style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      overflowY: 'auto', padding: 20, gap: 20,
    }}>

      {/* ── Hero marble header ── */}
      <MarblePanel variant="css" bok={bok} minHeight={80} style={{ padding: '16px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontSize: 26, fontWeight: 400, color: 'var(--text-body)',
              letterSpacing: '0.02em',
            }}>
              Broadcast Control
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {artisanId || 'Practitioner'} &middot; {live ? 'session active' : 'session inactive'}
            </div>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <LiveBadge live={live} viewers={viewers} />
          </div>
        </div>
      </MarblePanel>

      {err && (
        <div style={{
          background: 'rgba(200,50,50,0.12)', border: '1px solid #c83232',
          borderRadius: 'var(--radius-sm)', padding: '8px 14px',
          fontSize: 12, color: '#f87171',
        }}>{err}</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>

        {/* ── Left column ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Stream metadata */}
          {!live && (
            <Panel>
              <div style={{ marginBottom: 14, fontSize: 13, fontWeight: 600,
                color: 'var(--magenta-primary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                Session Setup
              </div>

              <div style={{ marginBottom: 12 }}>
                <label className="s-label">Stream title</label>
                <input className="s-input" value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="What are you opening tonight?" />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label className="s-label">Tongue coordinates (for QCR discovery)</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 8 }}>
                  {TONGUE_OPTS.map(([n, name]) => (
                    <button key={n} onClick={() => toggleTongue(n)} style={{
                      background: tongues.includes(n) ? 'rgba(233,30,150,0.2)' : 'rgba(34,6,24,0.8)',
                      border: tongues.includes(n) ? 'var(--border-magenta)' : 'var(--border-plum)',
                      borderRadius: 'var(--radius-sm)',
                      color: tongues.includes(n) ? 'var(--magenta-primary)' : 'var(--text-muted)',
                      fontSize: 11, padding: '3px 8px', cursor: 'pointer',
                    }}>
                      {n} {name}
                    </button>
                  ))}
                </div>
                <div style={{ marginTop: 6 }}>
                  <label className="s-label">Or enter byte-table addresses directly</label>
                  <input className="s-input" value={coords}
                    onChange={e => setCoords(e.target.value)}
                    placeholder="e.g. 45 87 193 (space-separated)" />
                </div>
              </div>

              <Button onClick={startStream} disabled={busy} size="lg">
                {busy ? 'Starting…' : 'Begin Session'}
              </Button>
            </Panel>
          )}

          {/* RTMP credentials (shown when live) */}
          {live && (
            <Panel gold>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gold-alchemical)',
                  textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  OBS Configuration
                </span>
                <LiveBadge live={live} viewers={viewers} />
              </div>

              <div style={{ marginBottom: 10 }}>
                <label className="s-label">RTMP Server</label>
                <div className="s-credential">{RTMP_SERVER}</div>
              </div>
              <div style={{ marginBottom: 16 }}>
                <label className="s-label">Stream Key</label>
                <div className="s-credential">{streamKey || '…'}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button onClick={copyRtmpUrl} variant="ghost" size="sm">
                  Copy full RTMP URL
                </Button>
                <Button onClick={endStream} disabled={busy} variant="ghost"
                  size="sm" style={{ color: 'var(--pink-muted)', borderColor: 'var(--pink-muted)' }}>
                  {busy ? 'Ending…' : 'End Session'}
                </Button>
              </div>

              <div className="s-divider" style={{ marginTop: 16 }} />

              <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                In OBS: Settings → Stream → Service: Custom → paste the values above.
                Witnesses connect at{' '}
                <span style={{ color: 'var(--pink-bubble)', fontFamily: 'var(--font-mono)' }}>
                  stream.quantumquackery.com
                </span>
              </div>
            </Panel>
          )}

          {/* Wunashakoun mode */}
          {live && (
            <Panel>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-body)', marginBottom: 3 }}>
                    Wunashakoun Mode
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Enables BoK tracking, entropy emission, and Roko assessment.
                    Sessions in this mode are Quack-eligible.
                  </div>
                </div>
                <button onClick={() => setWMode(w => !w)} style={{
                  width: 44, height: 24, borderRadius: 12, border: 'none',
                  background: wMode
                    ? 'linear-gradient(90deg,var(--pink-deep),var(--magenta-primary))'
                    : 'rgba(58,10,42,0.8)',
                  cursor: 'pointer', transition: 'background var(--transition-std)',
                  boxShadow: wMode ? 'var(--glow-magenta)' : 'none',
                  position: 'relative',
                }}>
                  <span style={{
                    position: 'absolute', top: 2,
                    left: wMode ? 22 : 2,
                    width: 20, height: 20, borderRadius: '50%',
                    background: wMode ? '#fff' : 'var(--text-muted)',
                    transition: 'left var(--transition-std)',
                    display: 'block',
                  }} />
                </button>
              </div>

              {wMode && (
                <>
                  <EntropyMeter value={entValue} ticks={entTicks}
                    certified={entValue >= 0.75} />
                  <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
                    BoK transitions emitted every 30 s. Roko assesses on session end.
                  </div>
                  <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
                    <Button onClick={emitBokTick} variant="ghost" size="sm">
                      Emit BoK tick now
                    </Button>
                  </div>
                </>
              )}
            </Panel>
          )}

          {/* Post-session summary */}
          {summary && !live && (
            <SessionSummary summary={summary} />
          )}

          {/* Resonance markers from witnesses */}
          {live && markers.length > 0 && (
            <Panel>
              <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--text-muted)',
                textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Witness Resonance ({markers.length})
              </div>
              {markers.map((m, i) => <ResonanceMarker key={i} marker={m} style={{ marginBottom: 6 }} />)}
            </Panel>
          )}
        </div>

        {/* ── Right column: BoK readout ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Panel>
            <BoKReadout bok={bok} width={280} height={200} />
            <div className="s-divider" />
            <div style={{ marginBottom: 6 }}>
              <label className="s-label">Update BoK position (re, im)</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  className="s-input"
                  placeholder="-0.7, 0.27"
                  style={{ fontSize: 12 }}
                  onBlur={e => {
                    const [re, im] = e.target.value.split(',').map(Number);
                    if (!isNaN(re) && !isNaN(im)) setBok({ re, im });
                  }}
                />
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                Format: re, im — e.g. -0.7, 0.27 (classic Julia)
              </div>
            </div>
          </Panel>

          {live && wMode && (
            <Panel style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: 12, color: 'var(--text-muted)', marginBottom: 8,
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>Session Entropy</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 28,
                color: entTicks > 0 ? 'var(--magenta-primary)' : 'var(--text-muted)',
              }}>
                {entTicks}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                ticks emitted
              </div>
            </Panel>
          )}

          {live && (
            <Panel style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.7 }}>
              <div style={{ marginBottom: 4, fontWeight: 600, color: 'var(--text-body)' }}>
                Viewer link
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--pink-bubble)',
                wordBreak: 'break-all' }}>
                stream.quantumquackery.com?stream={streamId}
              </div>
              <Button
                onClick={() => navigator.clipboard?.writeText(
                  `https://stream.quantumquackery.com?stream=${streamId}`
                )}
                variant="ghost" size="sm" style={{ marginTop: 8 }}
              >
                Copy witness link
              </Button>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Session summary sub-component ─────────────────────────────────────────────

function SessionSummary({ summary }) {
  const { roko_gate, quack_eligible, entropy_ticks, bok_trajectory, tongue_proposal } = summary;
  const gateColors = { Tiwu:'#7af0c8', Tawu:'#c9a84c', FyKo:'#a084e8', Mowu:'#f87171', ZoWu:'#6b7280' };

  return (
    <Panel gold>
      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold-alchemical)',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
        Session Assessment
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        {roko_gate && (
          <MetadataChip label="Roko" value={roko_gate}
            gold={roko_gate === 'Tiwu' || roko_gate === 'Tawu'}
            style={{ background: `${gateColors[roko_gate] || '#333'}22`,
              borderColor: gateColors[roko_gate] || '#333',
              color: gateColors[roko_gate] || '#aaa' }} />
        )}
        {quack_eligible && <QuackBadge />}
        {entropy_ticks != null && (
          <MetadataChip label="entropy" value={`${entropy_ticks} ticks`} />
        )}
      </div>

      {bok_trajectory?.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div className="s-label">BoK trajectory ({bok_trajectory.length} points)</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)', lineHeight: 1.8 }}>
            {bok_trajectory.slice(-4).map((p, i) => (
              <div key={i}>{p.re?.toFixed(4)}, {p.im?.toFixed(4)}</div>
            ))}
            {bok_trajectory.length > 4 && (
              <div style={{ color: 'var(--pink-muted)' }}>+ {bok_trajectory.length - 4} more</div>
            )}
          </div>
        </div>
      )}

      {quack_eligible && tongue_proposal && (
        <div style={{ padding: '10px 14px',
          background: 'rgba(212,175,55,0.08)', border: 'var(--border-gold)',
          borderRadius: 'var(--radius-sm)', marginBottom: 10 }}>
          <div className="s-label" style={{ color: 'var(--gold-alchemical)' }}>
            Tongue generation proposal
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-body)', marginTop: 4 }}>
            {tongue_proposal}
          </div>
        </div>
      )}

      {quack_eligible && (
        <Button size="sm" variant="gold">
          Propose Tongue from this session
        </Button>
      )}
    </Panel>
  );
}

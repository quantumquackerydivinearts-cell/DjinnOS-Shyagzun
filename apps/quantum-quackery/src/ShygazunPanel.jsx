/**
 * ShygazunPanel.jsx
 * Drop into your Virtual Atelier layout as a collapsible side panel.
 *
 * Usage:
 *   import ShygazunPanel from './ShygazunPanel';
 *   <ShygazunPanel apiBase={import.meta.env.VITE_API_URL} />
 *
 * Requires: nothing beyond React — no extra deps.
 * The panel calls your atelier-api /shygazun/* endpoints.
 */

import { useState, useEffect, useCallback } from 'react';

const TONGUES = [
  { value: 'any', label: 'Open — any tongue' },
  { value: 'Lotus', label: 'Lotus' },
  { value: 'Rose', label: 'Rose' },
  { value: 'Sakura', label: 'Sakura' },
  { value: 'Daisy', label: 'Daisy' },
  { value: 'AppleBlossom', label: 'AppleBlossom' },
  { value: 'Aster', label: 'Aster' },
  { value: 'Grapevine', label: 'Grapevine' },
  { value: 'Cannabis', label: 'Cannabis' },
];

const REGISTERS = [
  { value: 'any', label: 'Open' },
  { value: 'psychospiritual', label: 'Psychospiritual' },
  { value: 'alchemical', label: 'Alchemical' },
  { value: 'political', label: 'Political / structural' },
  { value: 'photonic', label: 'Photonic / computational' },
  { value: 'voidian', label: 'Void-ian / substrate' },
  { value: 'ritual', label: 'Ritual / grimoire' },
  { value: 'phenomenological', label: 'Phenomenological' },
];

const MODES = [
  { value: 'prompt', label: 'Literary prompt' },
  { value: 'ritual', label: 'Ritual script' },
  { value: 'grimoire', label: 'Grimoire entry' },
  { value: 'pedagogy', label: 'Pedagogy synthesis' },
  { value: 'gilgamesh', label: 'Gilgamesh passage' },
];

const DEPTHS = [
  { value: 'surface', label: 'Surface (1–4 parts)' },
  { value: 'mid', label: 'Mid (5–10 parts)' },
  { value: 'deep', label: 'Deep (11–19 parts)' },
  { value: 'ritual', label: 'Ritual threshold (~20)' },
];

const DIVISIONS = {
  Sulphur: '#b45309',
  Mercury: '#1d4ed8',
  Salt: '#4b5563',
};

// ─── styles ─────────────────────────────────────────────────────────────────

const s = {
  panel: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: "'EB Garamond', Georgia, serif",
    fontSize: 14,
    color: '#1a1a1a',
    background: '#faf9f6',
    borderLeft: '1px solid #e5e0d8',
  },
  header: {
    padding: '14px 18px 10px',
    borderBottom: '1px solid #e5e0d8',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#f5f3ee',
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: 600,
    letterSpacing: '0.04em',
    color: '#2c1810',
    fontFamily: "'Cinzel', serif",
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid #e5e0d8',
    background: '#f5f3ee',
    gap: 0,
  },
  tab: (active) => ({
    flex: 1,
    padding: '8px 4px',
    fontSize: 11,
    textAlign: 'center',
    cursor: 'pointer',
    letterSpacing: '0.05em',
    fontFamily: "'Cinzel', serif",
    borderBottom: active ? '2px solid #7c3d12' : '2px solid transparent',
    color: active ? '#7c3d12' : '#6b5c4e',
    background: 'transparent',
    border: 'none',
    borderBottom: active ? '2px solid #7c3d12' : '2px solid transparent',
  }),
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '14px 16px',
  },
  field: {
    marginBottom: 10,
  },
  label: {
    display: 'block',
    fontSize: 11,
    color: '#7c6a58',
    letterSpacing: '0.06em',
    marginBottom: 4,
    fontFamily: "'Cinzel', serif",
  },
  select: {
    width: '100%',
    padding: '6px 8px',
    fontSize: 13,
    border: '1px solid #d4c9bc',
    borderRadius: 4,
    background: '#fff',
    color: '#1a1a1a',
    fontFamily: "'EB Garamond', Georgia, serif",
  },
  textarea: {
    width: '100%',
    padding: '8px 10px',
    fontSize: 13,
    border: '1px solid #d4c9bc',
    borderRadius: 4,
    background: '#fff',
    color: '#1a1a1a',
    fontFamily: "'EB Garamond', Georgia, serif",
    lineHeight: 1.7,
    resize: 'vertical',
    minHeight: 90,
    boxSizing: 'border-box',
  },
  input: {
    width: '100%',
    padding: '6px 8px',
    fontSize: 13,
    border: '1px solid #d4c9bc',
    borderRadius: 4,
    background: '#fff',
    color: '#1a1a1a',
    fontFamily: "'EB Garamond', Georgia, serif",
    boxSizing: 'border-box',
  },
  btn: {
    padding: '6px 14px',
    fontSize: 12,
    cursor: 'pointer',
    border: '1px solid #c4a882',
    borderRadius: 4,
    background: '#f5f0e8',
    color: '#5c3d1e',
    fontFamily: "'Cinzel', serif",
    letterSpacing: '0.04em',
  },
  btnPrimary: {
    padding: '7px 16px',
    fontSize: 12,
    cursor: 'pointer',
    border: '1px solid #7c3d12',
    borderRadius: 4,
    background: '#7c3d12',
    color: '#faf9f6',
    fontFamily: "'Cinzel', serif",
    letterSpacing: '0.04em',
  },
  btnRow: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap',
    marginTop: 8,
  },
  resultBox: {
    background: '#fff',
    border: '1px solid #e5e0d8',
    borderRadius: 4,
    padding: '10px 12px',
    fontSize: 13,
    lineHeight: 1.75,
    color: '#2c1810',
    marginTop: 8,
    minHeight: 50,
    fontFamily: "'EB Garamond', Georgia, serif",
  },
  divider: {
    borderTop: '1px solid #e5e0d8',
    margin: '12px 0',
  },
  badge: (color) => ({
    display: 'inline-block',
    fontSize: 10,
    padding: '2px 7px',
    borderRadius: 10,
    background: color + '18',
    color: color,
    border: `1px solid ${color}44`,
    marginRight: 4,
    fontFamily: "'Cinzel', serif",
    letterSpacing: '0.04em',
  }),
  tabletCard: (division) => ({
    background: '#fff',
    border: `1px solid #e5e0d8`,
    borderLeft: `3px solid ${DIVISIONS[division] || '#9ca3af'}`,
    borderRadius: 4,
    padding: '10px 12px',
    marginBottom: 8,
    cursor: 'pointer',
  }),
  tabletTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#2c1810',
    fontFamily: "'Cinzel', serif",
    marginBottom: 3,
  },
  tabletMeta: {
    fontSize: 11,
    color: '#7c6a58',
    lineHeight: 1.5,
  },
  parallelGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
    marginBottom: 10,
  },
  corpusEntry: {
    borderTop: '1px solid #e5e0d8',
    padding: '8px 0',
    fontSize: 12,
    lineHeight: 1.6,
  },
  muted: {
    color: '#7c6a58',
    fontSize: 11,
    fontStyle: 'italic',
  },
  loading: {
    color: '#7c6a58',
    fontSize: 12,
    fontStyle: 'italic',
    padding: '8px 0',
  },
};

// ─── sub-components ──────────────────────────────────────────────────────────

function FieldSelect({ label, value, onChange, options }) {
  return (
    <div style={s.field}>
      <label style={s.label}>{label}</label>
      <select style={s.select} value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function ResultBox({ content, loading }) {
  if (loading) return <div style={s.resultBox}><span style={s.loading}>Working through the manifold…</span></div>;
  if (!content) return null;
  return <div style={s.resultBox}>{content}</div>;
}

// ─── tabs ────────────────────────────────────────────────────────────────────

function ComposeTab({ api }) {
  const [tongue, setTongue] = useState('any');
  const [register, setRegister] = useState('any');
  const [mode, setMode] = useState('prompt');
  const [depth, setDepth] = useState('mid');
  const [prompt, setPrompt] = useState('');
  const [promptLoading, setPromptLoading] = useState(false);
  const [text, setText] = useState('');
  const [parseResult, setParseResult] = useState('');
  const [parseLoading, setParseLoading] = useState(false);
  const [corpus, setCorpus] = useState([]);

  async function genPrompt() {
    setPromptLoading(true);
    setPrompt('');
    try {
      const r = await fetch(`${api}/shygazun/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tongue, register, mode, depth }),
      });
      const d = await r.json();
      setPrompt(d.prompt || 'No prompt returned.');
    } catch { setPrompt('Could not reach atelier-api.'); }
    setPromptLoading(false);
  }

  async function parseText() {
    if (!text.trim()) return;
    setParseLoading(true);
    setParseResult('');
    try {
      const r = await fetch(`${api}/shygazun/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const d = await r.json();
      const p = d.parse;
      if (p?.structure) {
        setParseResult(`Structure: ${p.structure}\n\nManifold path: ${p.manifold_path || '—'}\n\nActive tongues: ${(p.tongues_active || []).join(', ')}`);
      } else {
        setParseResult(p?.raw || JSON.stringify(p, null, 2));
      }
    } catch { setParseResult('Parse failed.'); }
    setParseLoading(false);
  }

  function save() {
    if (!text.trim()) return;
    setCorpus(c => [{ text, tongue, register, mode, ts: new Date().toISOString().slice(0, 16).replace('T', ' ') }, ...c]);
    setText('');
  }

  return (
    <div>
      <FieldSelect label="Tongue" value={tongue} onChange={setTongue} options={TONGUES} />
      <FieldSelect label="Register" value={register} onChange={setRegister} options={REGISTERS} />
      <div style={s.parallelGrid}>
        <FieldSelect label="Mode" value={mode} onChange={setMode} options={MODES} />
        <FieldSelect label="Depth" value={depth} onChange={setDepth} options={DEPTHS} />
      </div>
      <button style={s.btnPrimary} onClick={genPrompt}>Generate prompt</button>
      <ResultBox content={prompt} loading={promptLoading} />

      <div style={s.divider} />

      <div style={s.field}>
        <label style={s.label}>Composition</label>
        <textarea
          style={s.textarea}
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={prompt || 'Write natively here…'}
        />
      </div>
      <div style={s.btnRow}>
        <button style={s.btn} onClick={save}>Save</button>
        <button style={s.btn} onClick={parseText}>Parse</button>
      </div>
      <ResultBox content={parseResult} loading={parseLoading} />

      {corpus.length > 0 && (
        <>
          <div style={s.divider} />
          <div style={{ fontSize: 11, ...s.label }}>Corpus — {corpus.length} {corpus.length === 1 ? 'entry' : 'entries'}</div>
          {corpus.map((e, i) => (
            <div key={i} style={s.corpusEntry}>
              <div>{e.text}</div>
              <div style={{ marginTop: 3 }}>
                <span style={s.badge('#7c3d12')}>{e.tongue}</span>
                <span style={s.badge('#0f6e56')}>{e.register}</span>
                <span style={{ ...s.muted, marginLeft: 2 }}>{e.ts}</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function GilgameshTab({ api }) {
  const [tablets, setTablets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState('gilgamesh');
  const [depth, setDepth] = useState('mid');
  const [prompt, setPrompt] = useState('');
  const [promptLoading, setPromptLoading] = useState(false);
  const [shygazunText, setShygazunText] = useState('');
  const [englishText, setEnglishText] = useState('');
  const [saveStatus, setSaveStatus] = useState('');
  const [translateLoading, setTranslateLoading] = useState(false);

  useEffect(() => {
    fetch(`${api}/shygazun/tablets`)
      .then(r => r.json())
      .then(setTablets)
      .catch(() => {});
  }, [api]);

  async function genPrompt() {
    if (!selected) return;
    setPromptLoading(true);
    setPrompt('');
    try {
      const r = await fetch(`${api}/shygazun/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tongue: 'any', register: 'alchemical', mode, depth, tablet_id: selected.id }),
      });
      const d = await r.json();
      setPrompt(d.prompt || '');
    } catch { setPrompt('Could not reach atelier-api.'); }
    setPromptLoading(false);
  }

  async function translateToShygazun() {
    if (!englishText.trim()) return;
    setTranslateLoading(true);
    try {
      const r = await fetch(`${api}/shygazun/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: englishText, direction: 'to_shygazun' }),
      });
      const d = await r.json();
      setShygazunText(d.result || '');
    } catch {}
    setTranslateLoading(false);
  }

  async function saveComposition() {
    if (!selected || !shygazunText.trim()) return;
    try {
      await fetch(`${api}/shygazun/tablets/${selected.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tablet_id: selected.id, shygazun_text: shygazunText, english_parallel: englishText }),
      });
      setSaveStatus('Saved.');
      setTimeout(() => setSaveStatus(''), 2000);
      const r = await fetch(`${api}/shygazun/tablets`);
      setTablets(await r.json());
    } catch { setSaveStatus('Save failed.'); }
  }

  if (!selected) {
    return (
      <div>
        <div style={{ ...s.muted, marginBottom: 10 }}>Select a tablet to begin composing.</div>
        {tablets.map(t => (
          <div key={t.id} style={s.tabletCard(t.division)} onClick={() => setSelected(t)}>
            <div style={s.tabletTitle}>{t.title}</div>
            <div style={s.tabletMeta}>
              <span style={s.badge(DIVISIONS[t.division] || '#6b7280')}>{t.division}</span>
              {t.composition_count > 0 && <span style={s.muted}>{t.composition_count} composition{t.composition_count !== 1 ? 's' : ''}</span>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      <button style={{ ...s.btn, marginBottom: 10 }} onClick={() => setSelected(null)}>← All tablets</button>
      <div style={{ ...s.tabletCard(selected.division), cursor: 'default', marginBottom: 10 }}>
        <div style={s.tabletTitle}>{selected.title}</div>
        <div style={{ ...s.tabletMeta, marginTop: 4 }}>{selected.paracelsian}</div>
      </div>

      <div style={s.parallelGrid}>
        <FieldSelect label="Mode" value={mode} onChange={setMode} options={MODES} />
        <FieldSelect label="Depth" value={depth} onChange={setDepth} options={DEPTHS} />
      </div>
      <button style={s.btnPrimary} onClick={genPrompt}>Generate passage prompt</button>
      <ResultBox content={prompt} loading={promptLoading} />

      <div style={s.divider} />

      <div style={s.field}>
        <label style={s.label}>Shygazun text</label>
        <textarea style={s.textarea} value={shygazunText} onChange={e => setShygazunText(e.target.value)} placeholder="Compose natively…" />
      </div>
      <div style={s.field}>
        <label style={s.label}>English parallel</label>
        <textarea style={{ ...s.textarea, minHeight: 70 }} value={englishText} onChange={e => setEnglishText(e.target.value)} placeholder="Parallel rendering or notes…" />
      </div>
      <div style={s.btnRow}>
        <button style={s.btnPrimary} onClick={saveComposition}>Save to tablet</button>
        <button style={s.btn} onClick={translateToShygazun} disabled={translateLoading}>
          {translateLoading ? 'Translating…' : 'Translate EN → SHY'}
        </button>
        {saveStatus && <span style={s.muted}>{saveStatus}</span>}
      </div>

      {selected.compositions?.length > 0 && (
        <>
          <div style={s.divider} />
          <div style={s.label}>Saved compositions</div>
          {selected.compositions.map((c, i) => (
            <div key={i} style={s.corpusEntry}>
              <div>{c.shygazun_text}</div>
              {c.english_parallel && <div style={{ ...s.muted, marginTop: 2, fontStyle: 'normal' }}>{c.english_parallel}</div>}
              <div style={{ ...s.muted, marginTop: 2 }}>{c.timestamp?.slice(0, 16)}</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function LookupTab({ api }) {
  const [query, setQuery] = useState('');
  const [field, setField] = useState('tongue');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [emotion, setEmotion] = useState('');
  const [emotionResult, setEmotionResult] = useState('');
  const [emotionLoading, setEmotionLoading] = useState(false);

  async function lookup() {
    if (!query.trim()) return;
    setLoading(true);
    setResults(null);
    try {
      const r = await fetch(`${api}/shygazun/lookup?query=${encodeURIComponent(query)}&field=${field}`);
      const d = await r.json();
      setResults(d);
    } catch { setResults({ error: 'Lookup failed.' }); }
    setLoading(false);
  }

  async function interpretEmotion() {
    if (!emotion.trim()) return;
    setEmotionLoading(true);
    setEmotionResult('');
    try {
      const r = await fetch(`${api}/shygazun/interpret`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ compound: emotion }),
      });
      const d = await r.json();
      setEmotionResult(d.interpretation || '');
    } catch { setEmotionResult('Interpretation failed.'); }
    setEmotionLoading(false);
  }

  return (
    <div>
      <div style={s.field}>
        <label style={s.label}>Symbol lookup</label>
        <div style={{ display: 'flex', gap: 6 }}>
          <select style={{ ...s.select, width: 110, flex: 'none' }} value={field} onChange={e => setField(e.target.value)}>
            <option value="symbol">Symbol</option>
            <option value="tongue">Tongue</option>
            <option value="meaning">Meaning</option>
          </select>
          <input style={s.input} value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && lookup()} placeholder="query…" />
          <button style={{ ...s.btn, flex: 'none' }} onClick={lookup}>Find</button>
        </div>
      </div>

      {loading && <div style={s.loading}>Searching the byte table…</div>}
      {results && !results.error && (
        <div>
          <div style={{ ...s.muted, marginBottom: 6 }}>{results.count} result{results.count !== 1 ? 's' : ''}</div>
          {results.results.map((r, i) => (
            <div key={i} style={{ ...s.corpusEntry, borderTop: i === 0 ? 'none' : undefined }}>
              <span style={{ fontWeight: 600, marginRight: 6, color: '#7c3d12', fontFamily: "'Cinzel', serif" }}>{r.symbol}</span>
              <span style={s.badge('#1d4ed8')}>{r.tongue}</span>
              <span style={s.muted}>dec {r.decimal}</span>
              <div style={{ marginTop: 2 }}>{r.meaning}</div>
            </div>
          ))}
        </div>
      )}

      <div style={s.divider} />

      <div style={s.field}>
        <label style={s.label}>Emotion compound interpreter</label>
        <input style={s.input} value={emotion} onChange={e => setEmotion(e.target.value)} placeholder="e.g. Rugafunly or Aekaly…" />
      </div>
      <button style={s.btn} onClick={interpretEmotion}>Interpret</button>
      <ResultBox content={emotionResult} loading={emotionLoading} />
    </div>
  );
}

// ─── main panel ──────────────────────────────────────────────────────────────

export default function ShygazunPanel({ apiBase }) {
  const api = apiBase || import.meta.env.VITE_API_URL || '';
  const [tab, setTab] = useState('compose');

  return (
    <>
      <link
        href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap"
        rel="stylesheet"
      />
      <div style={s.panel}>
        <div style={s.header}>
          <span style={s.headerTitle}>Shygazun</span>
          <span style={{ fontSize: 10, color: '#7c6a58', letterSpacing: '0.06em', fontFamily: "'Cinzel', serif" }}>QQDA Atelier</span>
        </div>
        <div style={s.tabs}>
          {[
            { id: 'compose', label: 'Compose' },
            { id: 'gilgamesh', label: 'Gilgamesh' },
            { id: 'lookup', label: 'Lookup' },
          ].map(t => (
            <button key={t.id} style={s.tab(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
        <div style={s.body}>
          {tab === 'compose' && <ComposeTab api={api} />}
          {tab === 'gilgamesh' && <GilgameshTab api={api} />}
          {tab === 'lookup' && <LookupTab api={api} />}
        </div>
      </div>
    </>
  );
}

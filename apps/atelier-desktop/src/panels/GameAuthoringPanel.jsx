/**
 * GameAuthoringPanel.jsx
 * ======================
 * Six-tab Game 7 authoring hub:
 *   SCENE      — .ko file picker + split editor / live GL renderer
 *   QUESTS     — 61-quest status board from game7Registry
 *   CHARACTERS — NPC roster grouped by type
 *   DIALOGUE   — dialogue tree editor (re-hosted from GameEditorsPanel)
 *   AUDIO      — audio track registry (re-hosted from GameEditorsPanel)
 *   ORRERY     — 12-layer elemental crossing matrix (binary → function)
 *
 * Props
 * -----
 *   apiBase          string
 *   parseKobra       (src: string) => { entities, words }
 *   drawWebGL2       (canvas, entities, opts) => void
 *   studioFsRoot     string | ""
 *   hasDesktopFs     () => boolean
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  CHARACTERS, QUESTS, KNOWN_TYPES,
  CHARACTER_BY_ID,
} from "../game7Registry.js";
import { ALL_PERKS } from "../skillRegistry.js";

// ── Constants ─────────────────────────────────────────────────────────────────

const TABS = ["SCENE", "QUESTS", "CHARACTERS", "DIALOGUE", "AUDIO", "ORRERY"];

const QUEST_STATUSES = ["not_started", "in_progress", "complete", "blocked"];
const STATUS_COLOR = {
  not_started: "#3a4a3a",
  in_progress: "#3ab8a0",
  complete:    "#4ade80",
  blocked:     "#f87171",
};
const STATUS_LABEL = {
  not_started: "—",
  in_progress: "▶",
  complete:    "✓",
  blocked:     "✕",
};

const ELEM_COLOR = {
  Shak: "#ef4444",
  Puf:  "#60a5fa",
  Mel:  "#38bdf8",
  Zot:  "#a3a3a3",
};
const ELEM_LABEL = { Shak: "Fire", Puf: "Air", Mel: "Water", Zot: "Earth" };

const TYPE_ORDER = [
  "HIST", "TOWN", "WTCH", "PRST", "ASSN", "ROYL", "GNOM", "NYMP",
  "UNDI", "SALA", "DRYA", "DJNN", "VDWR", "DMON", "DEMI", "SOLD",
  "GODS", "PRIM", "ANMU",
];

const TYPE_LABEL = {
  HIST: "Historical", TOWN: "Townsperson", WTCH: "Witch", PRST: "Priest",
  ASSN: "Assassin",  ROYL: "Royalty",     GNOM: "Gnome",  NYMP: "Nymph",
  UNDI: "Undine",    SALA: "Salamander",  DRYA: "Dryad",  DJNN: "Djinn",
  VDWR: "Void Wraith", DMON: "Demon",   DEMI: "Demigod", SOLD: "Soldier",
  GODS: "God",       PRIM: "Primordial", ANMU: "Anima Mundi",
};

const REALMS = ["lapidus", "mercurie", "sulphera"];
const AUDIO_CHANNELS = ["music", "sfx", "ambient", "narrative"];

// ── Palette ───────────────────────────────────────────────────────────────────

const C = {
  bg:      "#0a0f0a",
  panel:   "#0f160f",
  card:    "#0b100b",
  border:  "#1a2a1a",
  accent:  "#3ab8a0",
  dim:     "#3a5a3c",
  muted:   "#7a9e7c",
  text:    "#c8d8c8",
  red:     "#f87171",
  tabBg:   "#111811",
  tabAct:  "#1a2a1a",
};

const inp = {
  background: C.card,
  border: `1px solid ${C.border}`,
  borderRadius: 3,
  color: C.text,
  fontSize: 12,
  padding: "3px 7px",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function downloadJson(filename, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

function uid() { return Math.random().toString(36).slice(2, 9); }

function Btn({ onClick, children, style, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: "none", border: `1px solid ${C.border}`, borderRadius: 3,
        color: disabled ? C.dim : C.accent, fontSize: 11, padding: "3px 8px",
        cursor: disabled ? "default" : "pointer", ...style,
      }}
    >{children}</button>
  );
}

// ── SCENE tab ─────────────────────────────────────────────────────────────────

function SceneTab({ parseKobra, drawWebGL2: draw, studioFsRoot, hasDesktopFs }) {
  const canvasRef  = useRef(null);
  const [files, setFiles]   = useState([]);
  const [selected, setSelected] = useState("");
  const [source, setSource] = useState("");
  const [err, setErr]       = useState("");
  const [loading, setLoading] = useState(false);

  const canUseFs = hasDesktopFs && hasDesktopFs() && !!studioFsRoot;

  async function refreshFiles() {
    if (!canUseFs) return;
    try {
      const r = await window.atelierDesktop.fs.listKobraScripts(studioFsRoot);
      setFiles(r?.files || []);
    } catch (e) { setErr(String(e?.message || e)); }
  }

  useEffect(() => { refreshFiles(); }, [studioFsRoot]); // eslint-disable-line

  async function loadFile(fname) {
    if (!canUseFs || !fname) return;
    setLoading(true); setErr("");
    try {
      const r = await window.atelierDesktop.fs.readKobraScript(studioFsRoot, fname);
      if (!r?.ok) throw new Error("read failed");
      setSelected(fname);
      setSource(r.content);
    } catch (e) { setErr(String(e?.message || e)); }
    finally { setLoading(false); }
  }

  async function saveFile() {
    if (!canUseFs || !selected) return;
    try {
      await window.atelierDesktop.fs.writeKobraScript(studioFsRoot, selected, source);
    } catch (e) { setErr(String(e?.message || e)); }
  }

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !draw || !parseKobra) return;
    try {
      const { entities } = parseKobra(source);
      draw(canvas, entities, {
        renderMode: "gl",
        visualStyle: "koslabyrinth",
        pitch: 40,
        tileSize: 24,
        zScale: 16,
      });
    } catch (e) { setErr(String(e?.message || e)); }
  }, [source, draw, parseKobra]);

  useEffect(() => { render(); }, [render]);

  return (
    <div style={{ display: "flex", gap: 8, height: "100%", overflow: "hidden" }}>
      {/* left: file list */}
      <div style={{ width: 180, flexShrink: 0, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <span style={{ color: C.muted, fontSize: 11, flex: 1 }}>
            {canUseFs ? studioFsRoot.split(/[/\\]/).pop() : "no folder"}
          </span>
          <Btn onClick={refreshFiles} disabled={!canUseFs}>↺</Btn>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {files.length === 0 && (
            <div style={{ color: C.dim, fontSize: 11, padding: "4px 0" }}>
              {canUseFs ? "no .ko files" : "open desktop app to browse"}
            </div>
          )}
          {files.map(f => (
            <div
              key={f}
              onClick={() => loadFile(f)}
              style={{
                padding: "3px 6px", borderRadius: 3, fontSize: 12, cursor: "pointer",
                color: selected === f ? C.accent : C.text,
                background: selected === f ? C.tabAct : "transparent",
                marginBottom: 2,
              }}
            >{f}</div>
          ))}
        </div>
        <Btn onClick={saveFile} disabled={!canUseFs || !selected}>Save</Btn>
        {err && <div style={{ color: C.red, fontSize: 10, wordBreak: "break-all" }}>{err}</div>}
      </div>

      {/* center: editor */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{ display: "flex", gap: 4, alignItems: "center", marginBottom: 4 }}>
          <span style={{ color: C.muted, fontSize: 11 }}>{selected || "no file"}</span>
          {loading && <span style={{ color: C.dim, fontSize: 11 }}>loading…</span>}
        </div>
        <textarea
          value={source}
          onChange={e => setSource(e.target.value)}
          spellCheck={false}
          style={{
            ...inp, flex: 1, resize: "none", fontFamily: "monospace",
            fontSize: 12, lineHeight: 1.5, padding: 8,
            minHeight: 0,
          }}
        />
      </div>

      {/* right: GL canvas */}
      <div style={{ width: 380, flexShrink: 0 }}>
        <canvas
          ref={canvasRef}
          width={380}
          height={340}
          style={{ border: `1px solid ${C.border}`, borderRadius: 3, display: "block" }}
        />
      </div>
    </div>
  );
}

// ── QUESTS tab ────────────────────────────────────────────────────────────────

function QuestsTab() {
  const [statuses, setStatuses] = useState(() =>
    Object.fromEntries(QUESTS.map(q => [q.id, "not_started"]))
  );
  const [filter, setFilter] = useState("all");

  function cycle(id) {
    setStatuses(prev => {
      const cur = prev[id];
      const next = QUEST_STATUSES[(QUEST_STATUSES.indexOf(cur) + 1) % QUEST_STATUSES.length];
      return { ...prev, [id]: next };
    });
  }

  const visible = filter === "all" ? QUESTS : QUESTS.filter(q => statuses[q.id] === filter);
  const counts = Object.fromEntries(QUEST_STATUSES.map(s => [s, QUESTS.filter(q => statuses[q.id] === s).length]));

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      {/* summary strip */}
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        {QUEST_STATUSES.map(s => (
          <button
            key={s}
            onClick={() => setFilter(prev => prev === s ? "all" : s)}
            style={{
              background: "none", border: `1px solid ${filter === s ? STATUS_COLOR[s] : C.border}`,
              borderRadius: 3, color: STATUS_COLOR[s], fontSize: 11,
              padding: "2px 8px", cursor: "pointer",
            }}
          >
            {STATUS_LABEL[s]} {s.replace("_", " ")} ({counts[s]})
          </button>
        ))}
        <span style={{ color: C.dim, fontSize: 11, marginLeft: "auto" }}>
          {counts.complete}/{QUESTS.length} complete
        </span>
      </div>

      {/* grid */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 4 }}>
          {visible.map(q => {
            const st = statuses[q.id];
            return (
              <div
                key={q.id}
                onClick={() => cycle(q.id)}
                title={q.note || q.id}
                style={{
                  background: C.card,
                  border: `1px solid ${st !== "not_started" ? STATUS_COLOR[st] + "55" : C.border}`,
                  borderRadius: 4, padding: "6px 10px", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 8,
                }}
              >
                <span style={{
                  width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
                  background: STATUS_COLOR[st], display: "flex",
                  alignItems: "center", justifyContent: "center",
                  fontSize: 10, color: "#000",
                }}>{STATUS_LABEL[st]}</span>
                <div>
                  <div style={{ color: C.text, fontSize: 12 }}>{q.name}</div>
                  <div style={{ color: C.dim, fontSize: 10 }}>{q.id}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── CHARACTERS tab ────────────────────────────────────────────────────────────

function CharactersTab() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [expanded, setExpanded] = useState(null);

  const chars = CHARACTERS.filter(c => {
    if (typeFilter !== "all" && c.type !== typeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q);
    }
    return true;
  });

  const grouped = TYPE_ORDER.reduce((acc, t) => {
    const g = chars.filter(c => c.type === t);
    if (g.length) acc.push({ type: t, chars: g });
    return acc;
  }, []);

  // also include types not in TYPE_ORDER
  const seen = new Set(TYPE_ORDER);
  chars.filter(c => !seen.has(c.type)).forEach(c => {
    const grp = grouped.find(g => g.type === c.type);
    if (!grp) grouped.push({ type: c.type, chars: [c] });
    else grp.chars.push(c);
  });

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search name or ID…"
          style={{ ...inp, flex: 1 }}
        />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={inp}>
          <option value="all">All types</option>
          {TYPE_ORDER.map(t => (
            <option key={t} value={t}>{TYPE_LABEL[t] || t}</option>
          ))}
        </select>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        {grouped.map(({ type, chars: gc }) => (
          <div key={type} style={{ marginBottom: 10 }}>
            <div style={{ color: C.muted, fontSize: 11, marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>
              {TYPE_LABEL[type] || type} ({gc.length})
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 3 }}>
              {gc.map(c => (
                <div
                  key={c.id}
                  onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                  style={{
                    background: C.card, border: `1px solid ${expanded === c.id ? C.accent + "66" : C.border}`,
                    borderRadius: 4, padding: "5px 8px", cursor: "pointer",
                  }}
                >
                  <div style={{ color: C.text, fontSize: 12 }}>{c.name}</div>
                  <div style={{ color: C.dim, fontSize: 10 }}>{c.id}</div>
                  {expanded === c.id && (
                    <div style={{ marginTop: 6, fontSize: 11, color: C.muted }}>
                      {c.role && <div><span style={{ color: C.dim }}>role: </span>{c.role}</div>}
                      {c.teaches && <div><span style={{ color: C.dim }}>teaches: </span>{c.teaches}</div>}
                      {c.title && <div><span style={{ color: C.dim }}>title: </span>{c.title}</div>}
                      {c.observes && <div><span style={{ color: C.dim }}>observes: </span>{c.observes}</div>}
                      {c.dual_type && <div><span style={{ color: C.dim }}>dual type: </span>{c.dual_type}</div>}
                      {c.note && <div style={{ marginTop: 4, color: C.dim, lineHeight: 1.4 }}>{c.note}</div>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── DIALOGUE tab ──────────────────────────────────────────────────────────────

function DialogueTab() {
  const [charId, setCharId]     = useState("");
  const [questCtx, setQuestCtx] = useState("");
  const [realm, setRealm]       = useState("lapidus");
  const [pathId, setPathId]     = useState("path_001");
  const [priority, setPriority] = useState("0");
  const [reqW, setReqW]         = useState("");
  const [blkW, setBlkW]         = useState("");
  const [spk, setSpk]           = useState("");
  const [txt, setTxt]           = useState("");
  const [shy, setShy]           = useState("");
  const [lines, setLines]       = useState([]);
  const [paths, setPaths]       = useState([]);
  const [selIdx, setSelIdx]     = useState(null);

  function csvToList(s) { return s.split(",").map(x => x.trim()).filter(Boolean); }

  function addLine() {
    if (!txt.trim()) return;
    setLines(prev => [...prev, { speaker: spk.trim() || charId || "unknown", text: txt.trim(), shygazun: shy.trim() }]);
    setTxt(""); setShy("");
  }

  function savePath() {
    if (!lines.length) return;
    const path = {
      path_id: pathId, char_id: charId, quest_context: questCtx, realm,
      priority: parseInt(priority) || 0,
      required_witnesses: csvToList(reqW),
      blocked_witnesses:  csvToList(blkW),
      lines: [...lines],
    };
    setPaths(prev => selIdx !== null
      ? prev.map((p, i) => i === selIdx ? path : p)
      : [...prev, path]
    );
    setLines([]); setSelIdx(null);
  }

  function loadPath(idx) {
    const p = paths[idx];
    setCharId(p.char_id); setQuestCtx(p.quest_context); setRealm(p.realm);
    setPathId(p.path_id); setPriority(String(p.priority));
    setReqW(p.required_witnesses.join(", ")); setBlkW(p.blocked_witnesses.join(", "));
    setLines([...p.lines]); setSelIdx(idx);
  }

  return (
    <div style={{ display: "flex", gap: 10, height: "100%", overflow: "hidden" }}>
      {/* form */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6, overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Character</div>
            <select value={charId} onChange={e => setCharId(e.target.value)} style={{ ...inp, width: "100%" }}>
              <option value="">— select —</option>
              {CHARACTERS.filter(c => c.type !== "test").map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Quest context</div>
            <select value={questCtx} onChange={e => setQuestCtx(e.target.value)} style={{ ...inp, width: "100%" }}>
              <option value="">— none —</option>
              {QUESTS.map(q => <option key={q.id} value={q.id}>{q.id} — {q.name}</option>)}
            </select>
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Realm</div>
            <select value={realm} onChange={e => setRealm(e.target.value)} style={{ ...inp, width: "100%" }}>
              {REALMS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Path ID</div>
            <input value={pathId} onChange={e => setPathId(e.target.value)} style={{ ...inp, width: "100%" }} />
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Required witnesses (CSV)</div>
            <input value={reqW} onChange={e => setReqW(e.target.value)} style={{ ...inp, width: "100%" }} />
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Blocked witnesses (CSV)</div>
            <input value={blkW} onChange={e => setBlkW(e.target.value)} style={{ ...inp, width: "100%" }} />
          </div>
        </div>

        <div style={{ color: C.muted, fontSize: 11, marginTop: 4 }}>Add line</div>
        <div style={{ display: "flex", gap: 4 }}>
          <input value={spk} onChange={e => setSpk(e.target.value)} placeholder="Speaker" style={{ ...inp, width: 120 }} />
          <input value={txt} onChange={e => setTxt(e.target.value)} placeholder="Dialogue text" style={{ ...inp, flex: 1 }} />
          <input value={shy} onChange={e => setShy(e.target.value)} placeholder="Shygazun gloss" style={{ ...inp, width: 140 }} />
          <Btn onClick={addLine}>+</Btn>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {lines.map((l, i) => (
            <div key={i} style={{ display: "flex", gap: 6, alignItems: "flex-start", marginBottom: 3 }}>
              <span style={{ color: C.accent, fontSize: 11, width: 90, flexShrink: 0 }}>{l.speaker}</span>
              <span style={{ color: C.text, fontSize: 12, flex: 1 }}>{l.text}</span>
              {l.shygazun && <span style={{ color: C.dim, fontSize: 10 }}>{l.shygazun}</span>}
              <Btn onClick={() => setLines(p => p.filter((_, j) => j !== i))}>✕</Btn>
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 6 }}>
          <Btn onClick={savePath} disabled={!lines.length}>
            {selIdx !== null ? "Update path" : "Save path"}
          </Btn>
          <Btn onClick={() => downloadJson(`dialogue_${charId || "unknown"}.json`, paths)} disabled={!paths.length}>
            Export JSON
          </Btn>
        </div>
      </div>

      {/* saved paths */}
      <div style={{ width: 220, flexShrink: 0, overflowY: "auto" }}>
        <div style={{ color: C.muted, fontSize: 11, marginBottom: 4 }}>Saved paths ({paths.length})</div>
        {paths.map((p, i) => (
          <div
            key={i}
            onClick={() => loadPath(i)}
            style={{
              background: C.card, border: `1px solid ${selIdx === i ? C.accent + "66" : C.border}`,
              borderRadius: 4, padding: "5px 8px", marginBottom: 3, cursor: "pointer",
            }}
          >
            <div style={{ color: C.text, fontSize: 12 }}>{p.path_id}</div>
            <div style={{ color: C.dim, fontSize: 10 }}>{p.char_id} · {p.realm} · {p.lines.length} lines</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── AUDIO tab ─────────────────────────────────────────────────────────────────

function AudioTab() {
  const [tracks, setTracks] = useState([]);
  const [name, setName]     = useState("");
  const [file, setFile]     = useState("");
  const [channel, setChannel] = useState("music");
  const [realm, setRealm]   = useState("lapidus");
  const [questCtx, setQuestCtx] = useState("");
  const [loop, setLoop]     = useState(true);
  const [selIdx, setSelIdx] = useState(null);

  function save() {
    if (!name.trim()) return;
    const t = {
      id: uid(), name: name.trim(), file: file.trim(),
      channel, realm, quest_context: questCtx, loop,
    };
    if (selIdx !== null) {
      setTracks(p => p.map((x, i) => i === selIdx ? t : x));
      setSelIdx(null);
    } else {
      setTracks(p => [...p, t]);
    }
    setName(""); setFile(""); setQuestCtx("");
  }

  function load(i) {
    const t = tracks[i];
    setName(t.name); setFile(t.file); setChannel(t.channel);
    setRealm(t.realm); setQuestCtx(t.quest_context); setLoop(t.loop);
    setSelIdx(i);
  }

  return (
    <div style={{ display: "flex", gap: 10, height: "100%", overflow: "hidden" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Track name</div>
            <input value={name} onChange={e => setName(e.target.value)} style={{ ...inp, width: "100%" }} />
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>File path</div>
            <input value={file} onChange={e => setFile(e.target.value)} placeholder="audio/track.ogg" style={{ ...inp, width: "100%" }} />
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Channel</div>
            <select value={channel} onChange={e => setChannel(e.target.value)} style={{ ...inp, width: "100%" }}>
              {AUDIO_CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Realm condition</div>
            <select value={realm} onChange={e => setRealm(e.target.value)} style={{ ...inp, width: "100%" }}>
              <option value="">— any —</option>
              {REALMS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <div style={{ color: C.muted, fontSize: 10, marginBottom: 2 }}>Quest condition</div>
            <select value={questCtx} onChange={e => setQuestCtx(e.target.value)} style={{ ...inp, width: "100%" }}>
              <option value="">— none —</option>
              {QUESTS.map(q => <option key={q.id} value={q.id}>{q.id} — {q.name}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 16 }}>
            <label style={{ color: C.muted, fontSize: 11, cursor: "pointer" }}>
              <input type="checkbox" checked={loop} onChange={e => setLoop(e.target.checked)}
                style={{ marginRight: 5 }} />
              Loop
            </label>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <Btn onClick={save} disabled={!name.trim()}>
            {selIdx !== null ? "Update" : "Add track"}
          </Btn>
          <Btn onClick={() => downloadJson("audio_registry.json", tracks)} disabled={!tracks.length}>
            Export JSON
          </Btn>
        </div>
      </div>

      <div style={{ width: 280, flexShrink: 0, overflowY: "auto" }}>
        <div style={{ color: C.muted, fontSize: 11, marginBottom: 4 }}>Tracks ({tracks.length})</div>
        {tracks.map((t, i) => (
          <div
            key={t.id}
            onClick={() => load(i)}
            style={{
              background: C.card, border: `1px solid ${selIdx === i ? C.accent + "66" : C.border}`,
              borderRadius: 4, padding: "5px 8px", marginBottom: 3, cursor: "pointer",
            }}
          >
            <div style={{ color: C.text, fontSize: 12 }}>{t.name}</div>
            <div style={{ color: C.dim, fontSize: 10 }}>{t.channel} · {t.realm || "any"}{t.loop ? " · loop" : ""}</div>
            {t.quest_context && <div style={{ color: C.dim, fontSize: 10 }}>{t.quest_context}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── ORRERY tab — 12-layer elemental crossing matrix ───────────────────────────

const LAYER_STATIC = [
  { rose: "Gaoh",    ri: 0,  compound: "Puky",  primary: "Puf",  dest: "Shak", purpose: "Air becoming combustible",         cue: [4,13,64,160]  },
  { rose: "Ao",      ri: 1,  compound: "Kypa",  primary: "Shak", dest: "Puf",  purpose: "Fire organizing into atmosphere",  cue: [6,19,66,181]  },
  { rose: "Ye",      ri: 2,  compound: "Alky",  primary: "Shak", dest: "Mel",  purpose: "Fire dissolving into solvent",     cue: [7,23,67,182]  },
  { rose: "Ui",      ri: 3,  compound: "Kazho", primary: "Shak", dest: "Zot",  purpose: "Fire crystallizing into structure",cue: [15,14,71,180] },
  { rose: "Shu",     ri: 4,  compound: "Shem",  primary: "Mel",  dest: "Shak", purpose: "Water reaching toward heat",       cue: [2,11,55,166]  },
  { rose: "Kiel",    ri: 5,  compound: "Lefu",  primary: "Mel",  dest: "Puf",  purpose: "Water releasing into vapor",       cue: [3,17,54,164]  },
  { rose: "Yeshu",   ri: 6,  compound: "Mipa",  primary: "Puf",  dest: "Mel",  purpose: "Air condensing into residue",      cue: [5,22,63,162]  },
  { rose: "Lao",     ri: 7,  compound: "Zitef", primary: "Puf",  dest: "Zot",  purpose: "Air settling into ground",         cue: [12,18,61,159] },
  { rose: "Shushy",  ri: 8,  compound: "Zashu", primary: "Zot",  dest: "Shak", purpose: "Earth activating into release",    cue: [0,9,48,171]   },
  { rose: "Uinshu",  ri: 9,  compound: "Fozt",  primary: "Zot",  dest: "Puf",  purpose: "Earth dispersing into atmosphere", cue: [1,20,51,174]  },
  { rose: "Kokiel",  ri: 10, compound: "Mazi",  primary: "Zot",  dest: "Mel",  purpose: "Earth dissolving into flow",       cue: [8,16,52,172]  },
  { rose: "Aonkiel", ri: 11, compound: "Myza",  primary: "Mel",  dest: "Zot",  purpose: "Water settling into ground",       cue: [3,21,58,165]  },
];

// Thermodynamic descent: Shak=0, Puf=0.33, Mel=0.67, Zot=1.0
const THERMO_DEPTH = { Shak: 0.0, Puf: 0.33, Mel: 0.67, Zot: 1.0 };

function OrreryTab({ apiBase }) {
  const [layers, setLayers]     = useState(null);
  const [probeAddrs, setProbeAddrs] = useState("");
  const [probeResult, setProbeResult] = useState(null);
  const [probeErr, setProbeErr] = useState("");
  const [probing, setProbing]   = useState(false);
  const [activeLayer, setActiveLayer] = useState(null);
  const [temp, setTemp]         = useState("0.35");

  // Load layer detail from API (cue glyphs) once
  useEffect(() => {
    fetch(`${apiBase}/v1/recombination/layers`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setLayers(data); })
      .catch(() => {});
  }, [apiBase]);

  async function probe() {
    const addrs = probeAddrs.split(/[\s,]+/).map(Number).filter(n => !isNaN(n) && n >= 0 && n <= 255);
    if (!addrs.length) return;
    setProbing(true); setProbeErr(""); setProbeResult(null);
    try {
      const r = await fetch(`${apiBase}/v1/recombination/probe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ addrs, temp: parseFloat(temp) || 0.35, max_iter: 32 }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setProbeResult(await r.json());
    } catch (e) { setProbeErr(String(e?.message || e)); }
    finally { setProbing(false); }
  }

  const displayLayers = layers || LAYER_STATIC.map(l => ({
    ...l, cue_glyphs: l.cue.map(addr => ({ addr, symbol: "?", tongue: "?", meaning: "?", element: null })),
  }));

  // probe returns a flat ProbeLayerOut[] — map to fired rose names
  const firedSet = new Set(Array.isArray(probeResult) ? probeResult.filter(l => l.would_fire).map(l => l.rose) : []);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      {/* probe bar */}
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ color: C.muted, fontSize: 11 }}>Probe byte addresses:</span>
        <input
          value={probeAddrs}
          onChange={e => setProbeAddrs(e.target.value)}
          placeholder="e.g. 4 13 64 160"
          style={{ ...inp, width: 220 }}
        />
        <span style={{ color: C.muted, fontSize: 11 }}>T=</span>
        <input value={temp} onChange={e => setTemp(e.target.value)} style={{ ...inp, width: 50 }} />
        <Btn onClick={probe} disabled={probing}>{probing ? "…" : "Probe"}</Btn>
        {probeErr && <span style={{ color: C.red, fontSize: 11 }}>{probeErr}</span>}
        {probeResult && (
          <span style={{ color: C.accent, fontSize: 11 }}>
            {firedSet.size} layer{firedSet.size !== 1 ? "s" : ""} would fire
          </span>
        )}
      </div>

      {/* 12-layer matrix */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 6 }}>
          {displayLayers.map((L, i) => {
            const fired    = firedSet.has(L.rose);
            const depth    = THERMO_DEPTH[L.destination] ?? 0;
            const pColor   = ELEM_COLOR[L.primary]     || "#888";
            const dColor   = ELEM_COLOR[L.destination] || "#888";
            const expanded = activeLayer === i;

            return (
              <div
                key={L.rose}
                onClick={() => setActiveLayer(expanded ? null : i)}
                style={{
                  background: C.card,
                  border: `1px solid ${fired ? C.accent : expanded ? C.border + "ff" : C.border}`,
                  borderRadius: 6, padding: "8px 12px", cursor: "pointer",
                  boxShadow: fired ? `0 0 8px ${C.accent}33` : "none",
                }}
              >
                {/* header row */}
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    color: C.accent, fontSize: 13, fontWeight: 600, width: 70, flexShrink: 0,
                    opacity: fired ? 1 : 0.6,
                  }}>{L.rose}</span>

                  {/* primary → dest arrow */}
                  <span style={{ fontSize: 11, color: pColor }}>{ELEM_LABEL[L.primary] || L.primary}</span>
                  <span style={{ color: C.dim, fontSize: 11 }}>→</span>
                  <span style={{ fontSize: 11, color: dColor }}>{ELEM_LABEL[L.destination] || L.destination}</span>

                  {/* thermo depth bar */}
                  <div style={{ flex: 1, height: 4, background: C.border, borderRadius: 2, overflow: "hidden" }}>
                    <div style={{
                      width: `${depth * 100}%`, height: "100%",
                      background: `linear-gradient(to right, ${pColor}, ${dColor})`,
                    }} />
                  </div>

                  {/* fired badge */}
                  {fired && (
                    <span style={{
                      background: C.accent + "22", border: `1px solid ${C.accent}`,
                      borderRadius: 3, color: C.accent, fontSize: 10, padding: "1px 5px",
                    }}>FIRES</span>
                  )}
                </div>

                {/* compound */}
                <div style={{ color: C.dim, fontSize: 11, marginTop: 3 }}>
                  {L.compound} · {L.purpose}
                </div>

                {/* expanded: cue glyphs + binary addresses */}
                {expanded && (
                  <div style={{ marginTop: 8, borderTop: `1px solid ${C.border}`, paddingTop: 8 }}>
                    <div style={{ color: C.muted, fontSize: 10, marginBottom: 4 }}>
                      Orrery cue cluster — all 4 must exceed threshold
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                      {L.cue_glyphs.map((g, gi) => (
                        <div key={gi} style={{ background: C.panel, borderRadius: 3, padding: "4px 6px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: C.accent, fontSize: 12 }}>{g.symbol}</span>
                            <span style={{ color: C.dim, fontSize: 10, fontFamily: "monospace" }}>
                              {String(g.addr).padStart(3, "0")} · {g.addr.toString(2).padStart(8, "0")}b
                            </span>
                          </div>
                          <div style={{ color: C.text, fontSize: 11 }}>{g.meaning}</div>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: C.dim, fontSize: 10 }}>{g.tongue}</span>
                            {g.element && (
                              <span style={{ color: ELEM_COLOR[g.element] || C.muted, fontSize: 10 }}>
                                {ELEM_LABEL[g.element] || g.element}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Binary → function progression strip */}
                    <div style={{ marginTop: 8 }}>
                      <div style={{ color: C.muted, fontSize: 10, marginBottom: 3 }}>
                        Binary → function progression
                      </div>
                      <div style={{ display: "flex", gap: 2 }}>
                        {L.cue_glyphs.map((g, gi) => {
                          const bits = g.addr.toString(2).padStart(8, "0").split("");
                          return (
                            <div key={gi} style={{ flex: 1 }}>
                              <div style={{ display: "flex", gap: 1, marginBottom: 2 }}>
                                {bits.map((b, bi) => (
                                  <div key={bi} style={{
                                    width: 10, height: 10, borderRadius: 1,
                                    background: b === "1" ? (ELEM_COLOR[g.element] || C.accent) : C.border,
                                  }} />
                                ))}
                              </div>
                              <div style={{ color: C.dim, fontSize: 9, textAlign: "center" }}>
                                {g.addr}
                              </div>
                            </div>
                          );
                        })}
                        <div style={{ display: "flex", alignItems: "center", paddingLeft: 4 }}>
                          <span style={{ color: dColor, fontSize: 11 }}>→ {ELEM_LABEL[L.destination]}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Root panel ────────────────────────────────────────────────────────────────

export function GameAuthoringPanel({ apiBase, parseKobra, drawWebGL2, studioFsRoot, hasDesktopFs }) {
  const [tab, setTab] = useState("SCENE");

  return (
    <div style={{
      height: "100%", display: "flex", flexDirection: "column",
      background: C.bg, color: C.text, overflow: "hidden",
    }}>
      {/* tab bar */}
      <div style={{
        display: "flex", gap: 0, borderBottom: `1px solid ${C.border}`,
        background: C.tabBg, flexShrink: 0,
      }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: tab === t ? C.tabAct : "none",
              border: "none",
              borderBottom: tab === t ? `2px solid ${C.accent}` : "2px solid transparent",
              color: tab === t ? C.accent : C.muted,
              fontSize: 12, padding: "8px 16px", cursor: "pointer",
              letterSpacing: 1,
            }}
          >{t}</button>
        ))}
      </div>

      {/* content */}
      <div style={{ flex: 1, overflow: "hidden", padding: 12 }}>
        {tab === "SCENE"      && (
          <SceneTab
            parseKobra={parseKobra}
            drawWebGL2={drawWebGL2}
            studioFsRoot={studioFsRoot}
            hasDesktopFs={hasDesktopFs}
          />
        )}
        {tab === "QUESTS"     && <QuestsTab />}
        {tab === "CHARACTERS" && <CharactersTab />}
        {tab === "DIALOGUE"   && <DialogueTab />}
        {tab === "AUDIO"      && <AudioTab />}
        {tab === "ORRERY"     && <OrreryTab apiBase={apiBase} />}
      </div>
    </div>
  );
}

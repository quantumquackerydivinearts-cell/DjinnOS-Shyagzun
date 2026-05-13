import React, { useState, useEffect, useCallback } from "react";

// ── Constants ─────────────────────────────────────────────────────────────────

const PANEL_TYPES   = ["standard","splash","bleed","inset"];
const PANEL_STATUSES = ["sketch","inks","color","final"];
const PAGE_STATUSES  = ["draft","final"];

const STATUS_COLOR = {
  sketch: "#6b7280",
  inks:   "#60a5fa",
  color:  "#a084e8",
  final:  "#4ade80",
};

const TYPE_ABBR = { standard:"STD", splash:"SPL", bleed:"BLD", inset:"INS" };

function pageProgress(panels) {
  if (!panels || panels.length === 0) return "empty";
  const statuses = panels.map(p => p.status);
  if (statuses.every(s => s === "final"))  return "final";
  if (statuses.some(s => s === "color"))   return "color";
  if (statuses.some(s => s === "inks"))    return "inks";
  return "sketch";
}

function wordCount(panels) {
  return (panels || []).reduce((n, p) => {
    const d = (p.dialogue_json || []).map(l => l.text || "").join(" ");
    const c = (p.caption_json  || []).map(l => l.text || "").join(" ");
    return n + (d + " " + c).split(/\s+/).filter(Boolean).length;
  }, 0);
}

// ── Header builder ────────────────────────────────────────────────────────────

function hdrs(artisanId, authToken, workspaceId, role) {
  const h = {
    "Content-Type":      "application/json",
    "X-Artisan-Id":      artisanId  || "artisan-desktop",
    "X-Artisan-Role":    role       || "member",
    "X-Workspace-Id":    workspaceId || "",
    "X-Atelier-Actor":   artisanId  || "desktop-user",
  };
  if (authToken) h["Authorization"] = `Bearer ${authToken}`;
  return h;
}

// ── Empty form defaults ───────────────────────────────────────────────────────

const EMPTY_PANEL = {
  panel_type: "standard", status: "sketch",
  dialogue: "", speaker: "", caption: "", sfx: "", notes: "",
};
const EMPTY_PAGE = { page_number: "", title: "", notes: "" };
const EMPTY_CHAR = { name: "", description: "", reference_url: "" };

// ── Component ─────────────────────────────────────────────────────────────────

export function ComicMakerPanel({ apiBase, artisanId, authToken, workspaceId, role }) {
  const [projects,     setProjects]     = useState([]);
  const [projectId,    setProjectId]    = useState("");
  const [projectInput, setProjectInput] = useState("");
  const [pages,        setPages]        = useState([]);
  const [pageId,       setPageId]       = useState(null);
  const [panelsByPage, setPanelsByPage] = useState({});
  const [chars,        setChars]        = useState([]);

  const [addingPage,   setAddingPage]   = useState(false);
  const [pageForm,     setPageForm]     = useState(EMPTY_PAGE);
  const [panelForm,    setPanelForm]    = useState(EMPTY_PANEL);
  const [charForm,     setCharForm]     = useState(EMPTY_CHAR);
  const [addingChar,   setAddingChar]   = useState(false);
  const [status,       setStatus]       = useState("");

  const H = useCallback(() => hdrs(artisanId, authToken, workspaceId, role), [artisanId, authToken, workspaceId, role]);

  const req = useCallback(async (method, path, body) => {
    const r = await fetch(`${apiBase}${path}`, {
      method, headers: H(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (r.status === 204) return null;
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `HTTP ${r.status}`); }
    return r.json();
  }, [apiBase, H]);

  // ── Project listing ────────────────────────────────────────────────────────
  useEffect(() => {
    req("GET", "/v1/projects").then(data => {
      const list = Array.isArray(data) ? data : data?.items || [];
      setProjects(list.filter(p => !p.type || p.type === "sequential_art" || p.type === "comic"));
    }).catch(() => {});
  }, []);

  // ── Load project ───────────────────────────────────────────────────────────
  const loadProject = useCallback(async (pid) => {
    if (!pid) return;
    setProjectId(pid); setPageId(null); setPanelsByPage({}); setStatus("loading…");
    try {
      const [pgs, chs] = await Promise.all([
        req("GET", `/v1/projects/${pid}/pages`),
        req("GET", `/v1/projects/${pid}/characters`),
      ]);
      const sorted = (Array.isArray(pgs) ? pgs : []).sort((a,b) => a.page_number - b.page_number);
      setPages(sorted);
      setChars(Array.isArray(chs) ? chs : []);
      setStatus("");
    } catch(e) { setStatus(e.message); }
  }, [req]);

  // ── Load panels for a page ─────────────────────────────────────────────────
  const loadPanels = useCallback(async (pid) => {
    if (!projectId || !pid) return;
    const data = await req("GET", `/v1/projects/${projectId}/pages/${pid}/panels`).catch(() => []);
    setPanelsByPage(prev => ({
      ...prev,
      [pid]: (Array.isArray(data) ? data : []).sort((a,b) => a.panel_index - b.panel_index),
    }));
  }, [projectId, req]);

  const selectPage = useCallback((pid) => {
    setPageId(pid);
    if (!panelsByPage[pid]) loadPanels(pid);
  }, [panelsByPage, loadPanels]);

  // ── Create page ────────────────────────────────────────────────────────────
  async function createPage() {
    if (!projectId || !pageForm.page_number) return;
    try {
      await req("POST", `/v1/projects/${projectId}/pages`, {
        page_number: parseInt(pageForm.page_number),
        title: pageForm.title,
        notes: pageForm.notes,
        status: "draft",
      });
      setPageForm(EMPTY_PAGE); setAddingPage(false);
      loadProject(projectId);
    } catch(e) { setStatus(e.message); }
  }

  async function deletePage(pid) {
    if (!projectId) return;
    await req("DELETE", `/v1/projects/${projectId}/pages/${pid}`).catch(() => {});
    setPages(prev => prev.filter(p => p.id !== pid));
    if (pageId === pid) setPageId(null);
  }

  // ── Create panel ───────────────────────────────────────────────────────────
  async function createPanel() {
    if (!projectId || !pageId) return;
    const currentPanels = panelsByPage[pageId] || [];
    const dialogue = panelForm.dialogue.trim()
      ? [{ speaker: panelForm.speaker.trim() || "NARRATION", text: panelForm.dialogue.trim(), bubble_type: "speech" }]
      : [];
    const caption  = panelForm.caption.trim()  ? [{ position: "top", text: panelForm.caption.trim() }]  : [];
    const sfx      = panelForm.sfx.trim()      ? [{ text: panelForm.sfx.trim(), style: "" }]             : [];
    try {
      await req("POST", `/v1/projects/${projectId}/pages/${pageId}/panels`, {
        panel_index: currentPanels.length,
        panel_type:  panelForm.panel_type,
        status:      panelForm.status,
        notes:       panelForm.notes,
        dialogue_json: dialogue,
        caption_json:  caption,
        sfx_json:      sfx,
      });
      setPanelForm(EMPTY_PANEL);
      loadPanels(pageId);
    } catch(e) { setStatus(e.message); }
  }

  async function deletePanel(panelId) {
    if (!projectId || !pageId) return;
    await req("DELETE", `/v1/projects/${projectId}/pages/${pageId}/panels/${panelId}`).catch(() => {});
    loadPanels(pageId);
  }

  async function cyclePanelStatus(panel) {
    const next = { sketch:"inks", inks:"color", color:"final", final:"sketch" }[panel.status] || "sketch";
    await req("PATCH", `/v1/projects/${projectId}/pages/${pageId}/panels/${panel.id}`, { status: next }).catch(() => {});
    loadPanels(pageId);
  }

  // ── Create character ───────────────────────────────────────────────────────
  async function createChar() {
    if (!projectId || !charForm.name.trim()) return;
    await req("POST", `/v1/projects/${projectId}/characters`, charForm).catch(e => setStatus(e.message));
    setCharForm(EMPTY_CHAR); setAddingChar(false);
    req("GET", `/v1/projects/${projectId}/characters`).then(d => setChars(Array.isArray(d) ? d : [])).catch(() => {});
  }

  async function deleteChar(cid) {
    await req("DELETE", `/v1/projects/${projectId}/characters/${cid}`).catch(() => {});
    setChars(prev => prev.filter(c => c.id !== cid));
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const activePage   = pages.find(p => p.id === pageId) || null;
  const activePanels = (panelsByPage[pageId] || []);
  const wc           = wordCount(activePanels);

  // ── Styles ─────────────────────────────────────────────────────────────────
  const s = {
    shell:   { display: "grid", gridTemplateColumns: "280px 1fr", gap: 0, height: "calc(100vh - 160px)", minHeight: 520, fontFamily: '"Segoe UI", sans-serif', fontSize: 13, color: "#e8f0e8" },
    sidebar: { borderRight: "1px solid #2a3a2a", overflowY: "auto", padding: "0 0 2rem" },
    main:    { overflowY: "auto", padding: "0 0 2rem" },
    hdr:     { padding: "10px 14px", borderBottom: "1px solid #2a3a2a", background: "#0b100b", position: "sticky", top: 0, zIndex: 2 },
    secHdr:  { padding: "8px 14px 4px", fontFamily: '"Cinzel", serif', fontSize: 9, letterSpacing: 3, color: "#3a5a3c", borderBottom: "1px solid #1e2e1e" },
    input:   { background: "#0e130e", border: "1px solid #2a3a2a", color: "#e8f0e8", padding: "5px 10px", borderRadius: 4, fontSize: 12, width: "100%" },
    btn:     { background: "#1a2a1a", border: "1px solid #3a5a3c", color: "#e8f0e8", padding: "4px 10px", cursor: "pointer", borderRadius: 4, fontSize: 11 },
    btnPri:  { background: "#3ab8a0", border: "none", color: "#000", padding: "5px 14px", cursor: "pointer", borderRadius: 4, fontSize: 11, fontWeight: 600 },
    row:     { display: "flex", gap: 6, alignItems: "center" },
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={s.shell}>

      {/* ── Sidebar ── */}
      <div style={s.sidebar}>

        {/* Project picker */}
        <div style={s.hdr}>
          {projects.length > 0 ? (
            <div style={{ ...s.row, marginBottom: 6 }}>
              <select style={{ ...s.input, flex: 1 }}
                value={projectInput}
                onChange={e => { setProjectInput(e.target.value); }}>
                <option value="">— select project —</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name || p.id}</option>)}
              </select>
              <button style={s.btnPri} onClick={() => loadProject(projectInput)}>Load</button>
            </div>
          ) : (
            <div style={{ ...s.row, marginBottom: 6 }}>
              <input style={{ ...s.input, flex: 1 }} value={projectInput}
                onChange={e => setProjectInput(e.target.value)} placeholder="project id" />
              <button style={s.btnPri} onClick={() => loadProject(projectInput)}>Load</button>
            </div>
          )}
          {status && <div style={{ fontSize: 11, color: "#f87171" }}>{status}</div>}
        </div>

        {/* Pages */}
        <div style={s.secHdr}>
          PAGES
          {projectId && <button style={{ ...s.btn, marginLeft: 8, fontSize: 10 }} onClick={() => setAddingPage(v=>!v)}>{addingPage ? "cancel" : "+ add"}</button>}
        </div>

        {addingPage && (
          <div style={{ padding: "8px 12px", borderBottom: "1px solid #1e2e1e" }}>
            <div style={{ ...s.row, marginBottom: 4 }}>
              <input style={{ ...s.input, width: 50 }} value={pageForm.page_number}
                onChange={e=>setPageForm(f=>({...f,page_number:e.target.value}))} placeholder="p#" />
              <input style={{ ...s.input, flex: 1 }} value={pageForm.title}
                onChange={e=>setPageForm(f=>({...f,title:e.target.value}))} placeholder="title" />
            </div>
            <button style={s.btnPri} onClick={createPage}>Add Page</button>
          </div>
        )}

        {pages.map(p => {
          const pPanels  = panelsByPage[p.id] || [];
          const progress = pageProgress(pPanels);
          const color    = STATUS_COLOR[progress] || "#3a5a3c";
          const active   = p.id === pageId;
          return (
            <div key={p.id}
              onClick={() => selectPage(p.id)}
              style={{ padding: "7px 14px", cursor: "pointer", borderBottom: "1px solid #1e2e1e", background: active ? "#1a2a1a" : "transparent", borderLeft: active ? `2px solid ${color}` : "2px solid transparent" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: active ? 600 : 400 }}>
                  <span style={{ color: "#3a5a3c", marginRight: 6, fontSize: 11 }}>p.{p.page_number}</span>
                  {p.title || <span style={{ opacity: 0.4, fontStyle: "italic" }}>untitled</span>}
                </span>
                <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 3, background: color + "22", color, border: `1px solid ${color}44` }}>{progress}</span>
              </div>
              {pPanels.length > 0 && (
                <div style={{ display: "flex", gap: 3, marginTop: 4, flexWrap: "wrap" }}>
                  {pPanels.map(pan => (
                    <span key={pan.id} style={{ width: 8, height: 8, borderRadius: 2, background: STATUS_COLOR[pan.status] || "#3a5a3c", display: "inline-block" }} title={pan.status} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {pages.length === 0 && projectId && <div style={{ padding: "12px 14px", opacity: 0.4, fontSize: 12 }}>No pages yet.</div>}

        {/* Characters */}
        <div style={{ ...s.secHdr, marginTop: 8 }}>
          CHARACTERS
          {projectId && <button style={{ ...s.btn, marginLeft: 8, fontSize: 10 }} onClick={() => setAddingChar(v=>!v)}>{addingChar ? "cancel" : "+ add"}</button>}
        </div>

        {addingChar && (
          <div style={{ padding: "8px 12px", borderBottom: "1px solid #1e2e1e" }}>
            <input style={{ ...s.input, marginBottom: 4 }} value={charForm.name}
              onChange={e=>setCharForm(f=>({...f,name:e.target.value}))} placeholder="name *" />
            <input style={{ ...s.input, marginBottom: 4 }} value={charForm.description}
              onChange={e=>setCharForm(f=>({...f,description:e.target.value}))} placeholder="description" />
            <input style={{ ...s.input, marginBottom: 6 }} value={charForm.reference_url}
              onChange={e=>setCharForm(f=>({...f,reference_url:e.target.value}))} placeholder="reference url" />
            <button style={s.btnPri} onClick={createChar}>Add</button>
          </div>
        )}

        {chars.map(c => (
          <div key={c.id} style={{ padding: "6px 14px", borderBottom: "1px solid #1e2e1e", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong style={{ fontSize: 12 }}>{c.name}</strong>
              {c.description && <div style={{ fontSize: 11, opacity: 0.5 }}>{c.description}</div>}
            </div>
            <button style={{ ...s.btn, opacity: 0.4, padding: "2px 6px", fontSize: 10 }} onClick={() => deleteChar(c.id)}>✕</button>
          </div>
        ))}
      </div>

      {/* ── Main script view ── */}
      <div style={s.main}>
        {!projectId && (
          <div style={{ padding: "3rem 2rem", opacity: 0.35, fontSize: 14, textAlign: "center" }}>
            Select or load a project to begin.
          </div>
        )}

        {projectId && !activePage && (
          <div style={{ padding: "2rem", opacity: 0.4, fontSize: 13 }}>
            Select a page from the sidebar.
          </div>
        )}

        {activePage && (
          <>
            {/* Page header */}
            <div style={{ ...s.hdr, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontFamily: '"Cinzel", serif', fontSize: 11, letterSpacing: 2, color: "#3a5a3c" }}>PAGE {activePage.page_number}</span>
                {activePage.title && <span style={{ marginLeft: 10, fontWeight: 600, fontSize: 14 }}>{activePage.title}</span>}
                <span style={{ marginLeft: 12, fontSize: 11, color: "#3a5a3c" }}>{activePanels.length} panels · {wc} words</span>
              </div>
              <button style={{ ...s.btn, opacity: 0.5 }} onClick={() => deletePage(activePage.id)}>Delete Page</button>
            </div>

            {/* Panel script blocks */}
            <div style={{ padding: "12px 20px" }}>
              {activePanels.map((pan, i) => {
                const sc = STATUS_COLOR[pan.status] || "#6b7280";
                return (
                  <div key={pan.id} style={{ marginBottom: 14, border: `1px solid ${sc}33`, borderRadius: 6, overflow: "hidden" }}>
                    {/* Panel header */}
                    <div style={{ background: sc + "18", padding: "5px 12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontFamily: '"Cinzel", serif', fontSize: 10, letterSpacing: 2, color: sc }}>PANEL {i+1}</span>
                        <span style={{ fontSize: 10, padding: "1px 6px", border: `1px solid ${sc}55`, borderRadius: 3, color: sc }}>{TYPE_ABBR[pan.panel_type] || pan.panel_type}</span>
                      </div>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <button style={{ ...s.btn, fontSize: 10, padding: "2px 8px", background: sc + "22", border: `1px solid ${sc}44`, color: sc }}
                          onClick={() => cyclePanelStatus(pan)}>
                          {pan.status}
                        </button>
                        <button style={{ ...s.btn, opacity: 0.4, padding: "2px 6px", fontSize: 10 }} onClick={() => deletePanel(pan.id)}>✕</button>
                      </div>
                    </div>
                    {/* Panel content */}
                    <div style={{ padding: "8px 12px" }}>
                      {(pan.caption_json || []).map((c, j) => (
                        <div key={j} style={{ marginBottom: 4, fontStyle: "italic", fontSize: 12, color: "#c9a84c", paddingLeft: 8, borderLeft: "2px solid #c9a84c44" }}>
                          {c.text}
                        </div>
                      ))}
                      {(pan.dialogue_json || []).map((d, j) => (
                        <div key={j} style={{ marginBottom: 4, fontSize: 12, paddingLeft: 8 }}>
                          <span style={{ fontWeight: 600, color: "#3ab8a0", marginRight: 6 }}>{(d.speaker || "").toUpperCase() || "?"}</span>
                          <span style={{ opacity: 0.85 }}>{d.text}</span>
                        </div>
                      ))}
                      {(pan.sfx_json || []).map((f, j) => (
                        <div key={j} style={{ marginBottom: 4, fontWeight: 700, fontSize: 13, color: "#f87171", letterSpacing: 2 }}>{f.text}</div>
                      ))}
                      {pan.notes && <div style={{ marginTop: 4, fontSize: 11, opacity: 0.4, fontStyle: "italic" }}>{pan.notes}</div>}
                    </div>
                  </div>
                );
              })}

              {/* Add panel form */}
              <div style={{ border: "1px dashed #2a3a2a", borderRadius: 6, padding: "10px 14px", marginTop: 8 }}>
                <div style={{ fontFamily: '"Cinzel", serif', fontSize: 9, letterSpacing: 2, color: "#3a5a3c", marginBottom: 8 }}>ADD PANEL</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>TYPE</div>
                    <select style={s.input} value={panelForm.panel_type} onChange={e=>setPanelForm(f=>({...f,panel_type:e.target.value}))}>
                      {PANEL_TYPES.map(t => <option key={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>STATUS</div>
                    <select style={s.input} value={panelForm.status} onChange={e=>setPanelForm(f=>({...f,status:e.target.value}))}>
                      {PANEL_STATUSES.map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>SPEAKER</div>
                    <input style={s.input} value={panelForm.speaker} placeholder="KIRA"
                      onChange={e=>setPanelForm(f=>({...f,speaker:e.target.value}))} />
                  </div>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>SFX</div>
                    <input style={s.input} value={panelForm.sfx} placeholder="BOOM"
                      onChange={e=>setPanelForm(f=>({...f,sfx:e.target.value}))} />
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>CAPTION</div>
                    <input style={s.input} value={panelForm.caption} placeholder="caption text"
                      onChange={e=>setPanelForm(f=>({...f,caption:e.target.value}))} />
                  </div>
                  <div>
                    <div style={{ fontSize: 9, color: "#3a5a3c", marginBottom: 2 }}>DIALOGUE</div>
                    <input style={s.input} value={panelForm.dialogue} placeholder="line of dialogue"
                      onChange={e=>setPanelForm(f=>({...f,dialogue:e.target.value}))} />
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <input style={{ ...s.input, flex: 1 }} value={panelForm.notes} placeholder="art direction notes"
                    onChange={e=>setPanelForm(f=>({...f,notes:e.target.value}))} />
                  <button style={s.btnPri} onClick={createPanel}>Add Panel</button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

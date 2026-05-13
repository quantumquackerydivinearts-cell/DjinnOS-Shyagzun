import React, { useState, useEffect, useCallback } from "react";

const STATUS_COLOR = {
  scheduled: "#3ab8a0",
  completed:  "#4ade80",
  canceled:   "#6b7280",
  no_show:    "#f87171",
};

const STATUSES = ["scheduled", "completed", "canceled", "no_show"];

const EMPTY_FORM = {
  title: "", starts_at: "", ends_at: "",
  status: "scheduled", notes: "", contact_id: "",
};

function toDateKey(iso) {
  return iso ? iso.slice(0, 10) : "";
}

function buildCalendarCells(monthStart, bookings) {
  const base    = new Date(monthStart + "T00:00:00");
  const year    = base.getFullYear();
  const month   = base.getMonth();
  const today   = toDateKey(new Date().toISOString());

  const firstDay = new Date(year, month, 1).getDay();
  const cells = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(year, month, 1 - firstDay + i);
    const key = toDateKey(d.toISOString());
    cells.push({
      key,
      label:    d.getDate(),
      inMonth:  d.getMonth() === month,
      isToday:  key === today,
      bookings: bookings.filter(b => toDateKey(b.starts_at) === key),
    });
  }
  return cells;
}

export function BookingPanel({ apiBase, authToken, workspaceId }) {
  const [bookings,    setBookings]    = useState([]);
  const [monthStart,  setMonthStart]  = useState(() => {
    const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-01`;
  });
  const [form,        setForm]        = useState(EMPTY_FORM);
  const [editingId,   setEditingId]   = useState(null);
  const [showForm,    setShowForm]    = useState(false);
  const [status,      setStatus]      = useState("");

  const hdrs = { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` };

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase}/v1/booking?workspace_id=${workspaceId}`, { headers: hdrs });
      if (r.ok) setBookings(await r.json());
    } catch {}
  }, [apiBase, authToken, workspaceId]);

  useEffect(() => { if (authToken) load(); }, [load]);

  async function save() {
    if (!form.title.trim() || !form.starts_at || !form.ends_at) {
      setStatus("Title, start, and end are required."); return;
    }
    try {
      if (editingId) {
        const r = await fetch(`${apiBase}/v1/booking/${editingId}`, {
          method: "PUT", headers: hdrs,
          body: JSON.stringify({ title: form.title, status: form.status, notes: form.notes,
            starts_at: form.starts_at, ends_at: form.ends_at }),
        });
        if (!r.ok) { setStatus("Update failed."); return; }
      } else {
        const r = await fetch(`${apiBase}/v1/booking`, {
          method: "POST", headers: hdrs,
          body: JSON.stringify({ ...form, workspace_id: workspaceId }),
        });
        if (!r.ok) { setStatus("Create failed."); return; }
      }
      setForm(EMPTY_FORM); setEditingId(null); setShowForm(false); setStatus(""); load();
    } catch (e) { setStatus(e.message); }
  }

  async function del(id) {
    try { await fetch(`${apiBase}/v1/booking/${id}`, { method: "DELETE", headers: hdrs }); load(); }
    catch {}
  }

  function startEdit(b) {
    setForm({
      title: b.title || "", starts_at: b.starts_at?.slice(0,16) || "",
      ends_at: b.ends_at?.slice(0,16) || "", status: b.status, notes: b.notes || "",
      contact_id: b.contact_id || "",
    });
    setEditingId(b.id); setShowForm(true);
  }

  function prevMonth() {
    const d = new Date(monthStart + "T00:00:00");
    d.setMonth(d.getMonth() - 1);
    setMonthStart(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-01`);
  }
  function nextMonth() {
    const d = new Date(monthStart + "T00:00:00");
    d.setMonth(d.getMonth() + 1);
    setMonthStart(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-01`);
  }

  const cells   = buildCalendarCells(monthStart, bookings);
  const label   = new Date(monthStart + "T00:00:00").toLocaleString("default", { month: "long", year: "numeric" });
  const upcoming = [...bookings]
    .filter(b => new Date(b.starts_at) >= new Date())
    .sort((a,b) => new Date(a.starts_at) - new Date(b.starts_at))
    .slice(0, 12);

  const s = {
    panel:   { fontFamily: '"Segoe UI", sans-serif', fontSize: 14, color: "#e8f0e8" },
    hdr:     { display:"flex", alignItems:"center", gap:12, marginBottom:12 },
    btn:     { background:"#1a2a1a", border:"1px solid #3a5a3c", color:"#e8f0e8",
               padding:"4px 12px", cursor:"pointer", borderRadius:4, fontSize:13 },
    btnPri:  { background:"#3ab8a0", border:"none", color:"#000",
               padding:"6px 16px", cursor:"pointer", borderRadius:4, fontSize:13, fontWeight:600 },
    grid:    { display:"grid", gridTemplateColumns:"repeat(7, 1fr)", gap:2, marginBottom:16 },
    dayHdr:  { textAlign:"center", fontSize:11, color:"#7a9e7c", padding:"4px 0",
               fontFamily:'"Cinzel", serif', letterSpacing:1 },
    cell:    { minHeight:64, background:"#0e130e", border:"1px solid #1e2e1e",
               padding:4, borderRadius:2, verticalAlign:"top" },
    cellOff: { minHeight:64, background:"#080d08", border:"1px solid #141e14",
               padding:4, borderRadius:2, opacity:0.45 },
    cellToday:{ outline:"1px solid #3ab8a0" },
    dayNum:  { fontSize:11, color:"#7a9e7c", marginBottom:2 },
    chip:    { fontSize:10, padding:"1px 4px", borderRadius:2, marginBottom:1,
               whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis",
               cursor:"pointer", display:"block" },
    input:   { background:"#0e130e", border:"1px solid #2a3a2a", color:"#e8f0e8",
               padding:"6px 10px", borderRadius:4, width:"100%", fontSize:13, marginBottom:8 },
    label:   { fontSize:11, color:"#7a9e7c", display:"block", marginBottom:3,
               fontFamily:'"Cinzel", serif', letterSpacing:1 },
    row:     { display:"flex", gap:8, padding:"6px 0", borderBottom:"1px solid #1e2e1e",
               alignItems:"flex-start" },
    dot:     (st) => ({ width:8, height:8, borderRadius:"50%",
                        background: STATUS_COLOR[st] || "#6b7280", flexShrink:0, marginTop:5 }),
  };

  return (
    <div style={s.panel}>
      {/* Calendar header */}
      <div style={s.hdr}>
        <button style={s.btn} onClick={prevMonth}>‹</button>
        <strong style={{ flex:1, textAlign:"center", fontFamily:'"Cinzel", serif', letterSpacing:2, fontSize:13 }}>{label.toUpperCase()}</strong>
        <button style={s.btn} onClick={nextMonth}>›</button>
        <button style={s.btnPri} onClick={() => { setForm(EMPTY_FORM); setEditingId(null); setShowForm(v => !v); }}>
          {showForm && !editingId ? "Cancel" : "+ New"}
        </button>
      </div>

      {/* Calendar grid */}
      <div style={s.grid}>
        {["Su","Mo","Tu","We","Th","Fr","Sa"].map(d => (
          <div key={d} style={s.dayHdr}>{d}</div>
        ))}
        {cells.map(cell => (
          <div key={cell.key} style={{ ...(cell.inMonth ? s.cell : s.cellOff), ...(cell.isToday ? s.cellToday : {}) }}>
            <div style={s.dayNum}>{cell.label}</div>
            {cell.bookings.map(b => (
              <span key={b.id} style={{ ...s.chip, background: STATUS_COLOR[b.status] || "#2a3a2a", color:"#000" }}
                onClick={() => startEdit(b)}>
                {b.title || b.notes?.slice(0,20) || "—"}
              </span>
            ))}
          </div>
        ))}
      </div>

      {/* New / edit form */}
      {showForm && (
        <div style={{ background:"#0b100b", border:"1px solid #2a3a2a", borderRadius:6, padding:16, marginBottom:16 }}>
          <strong style={{ fontFamily:'"Cinzel", serif', letterSpacing:2, fontSize:12, color:"#7a9e7c" }}>
            {editingId ? "EDIT BOOKING" : "NEW BOOKING"}
          </strong>
          <div style={{ marginTop:12 }}>
            <label style={s.label}>TITLE</label>
            <input style={s.input} value={form.title} onChange={e => setForm(f => ({...f, title: e.target.value}))} placeholder="Booking title" />
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
              <div>
                <label style={s.label}>START</label>
                <input style={s.input} type="datetime-local" value={form.starts_at} onChange={e => setForm(f => ({...f, starts_at: e.target.value}))} />
              </div>
              <div>
                <label style={s.label}>END</label>
                <input style={s.input} type="datetime-local" value={form.ends_at} onChange={e => setForm(f => ({...f, ends_at: e.target.value}))} />
              </div>
            </div>
            <label style={s.label}>STATUS</label>
            <select style={s.input} value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))}>
              {STATUSES.map(st => <option key={st} value={st}>{st}</option>)}
            </select>
            <label style={s.label}>NOTES</label>
            <textarea style={{...s.input, minHeight:60, resize:"vertical"}} value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} />
            {status && <div style={{ color:"#f87171", fontSize:12, marginBottom:8 }}>{status}</div>}
            <div style={{ display:"flex", gap:8 }}>
              <button style={s.btnPri} onClick={save}>{editingId ? "Save" : "Create"}</button>
              <button style={s.btn} onClick={() => { setShowForm(false); setEditingId(null); setForm(EMPTY_FORM); setStatus(""); }}>Cancel</button>
              {editingId && <button style={{...s.btn, color:"#f87171", borderColor:"#f87171"}} onClick={() => { del(editingId); setShowForm(false); setEditingId(null); }}>Delete</button>}
            </div>
          </div>
        </div>
      )}

      {/* Upcoming list */}
      <strong style={{ fontFamily:'"Cinzel", serif', fontSize:11, letterSpacing:2, color:"#7a9e7c" }}>
        UPCOMING — {upcoming.length}
      </strong>
      <div style={{ marginTop:8 }}>
        {upcoming.length === 0 && <div style={{ opacity:0.4, fontSize:13, padding:"8px 0" }}>No upcoming bookings.</div>}
        {upcoming.map(b => (
          <div key={b.id} style={s.row}>
            <div style={s.dot(b.status)} />
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:600, fontSize:13 }}>{b.title || "—"}</div>
              <div style={{ fontSize:11, opacity:0.6 }}>
                {new Date(b.starts_at).toLocaleString()} → {new Date(b.ends_at).toLocaleString()}
              </div>
              {b.notes && <div style={{ fontSize:11, opacity:0.5, marginTop:2 }}>{b.notes}</div>}
            </div>
            <button style={s.btn} onClick={() => startEdit(b)}>Edit</button>
            <button style={{...s.btn, color:"#f87171", borderColor:"#f87171"}} onClick={() => del(b.id)}>✕</button>
          </div>
        ))}
      </div>
    </div>
  );
}

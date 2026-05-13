import React, { useState, useEffect, useCallback } from "react";

const METRIC_TYPES  = ["lead_count","client_count","quote_count","order_count","revenue_cents"];
const METRIC_LABELS = {
  lead_count:    "New Leads",
  client_count:  "New Clients",
  quote_count:   "Quotes",
  order_count:   "Orders",
  revenue_cents: "Revenue (¢)",
};
const STATUSES = ["open","met","missed","archived"];
const CADENCES = ["daily","weekly","monthly"];

const STATUS_COLOR = { open:"#3ab8a0", met:"#4ade80", missed:"#f87171", archived:"#6b7280" };

const EMPTY_GOAL = {
  title:"", metric_type:"lead_count",
  period_start: today(), period_end: today(),
  target_value: 10, notes:"",
};

function today() { return new Date().toISOString().slice(0,10); }

function fmtMetric(type, value) {
  if (type === "revenue_cents") return `$${(value/100).toLocaleString("en",{minimumFractionDigits:2})}`;
  return value.toLocaleString();
}

export function GoalsReportsPanel({ apiBase, authToken, workspaceId }) {
  const hdrs = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${authToken}`,
    "X-Workspace-Id": workspaceId,
  };

  // ── Goals state ─────────────────────────────────────────────────────────────
  const [goals,      setGoals]      = useState([]);
  const [goalForm,   setGoalForm]   = useState(EMPTY_GOAL);
  const [editingId,  setEditingId]  = useState(null);
  const [showForm,   setShowForm]   = useState(false);
  const [goalStatus, setGoalStatus] = useState("");

  // ── Reports state ────────────────────────────────────────────────────────────
  const [dateFrom,  setDateFrom]  = useState(() => { const d=new Date(); d.setDate(1); return d.toISOString().slice(0,10); });
  const [dateTo,    setDateTo]    = useState(today);
  const [summary,   setSummary]   = useState(null);

  // ── Digests state ─────────────────────────────────────────────────────────
  const [digests,       setDigests]       = useState([]);
  const [digestEmail,   setDigestEmail]   = useState("");
  const [digestCadence, setDigestCadence] = useState("weekly");
  const [digestStatus,  setDigestStatus]  = useState("");

  const api = useCallback(async (path, method="GET", body=null) => {
    const r = await fetch(`${apiBase}/v1${path}`, {
      method, headers: hdrs,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e.detail||`HTTP ${r.status}`); }
    return method === "DELETE" ? null : r.json();
  }, [apiBase, authToken, workspaceId]);

  const loadGoals   = useCallback(() => api("/goals").then(d=>setGoals(d.goals||[])).catch(()=>{}), [api]);
  const loadDigests = useCallback(() => api("/reports/digests").then(d=>setDigests(d.digests||[])).catch(()=>{}), [api]);

  useEffect(() => { loadGoals(); loadDigests(); }, []);

  // ── Goals handlers ───────────────────────────────────────────────────────────
  async function saveGoal() {
    if (!goalForm.title.trim()) { setGoalStatus("Title required"); return; }
    try {
      if (editingId) {
        await api(`/goals/${editingId}`, "PUT", { ...goalForm, status: goalForm.status||"open" });
      } else {
        await api("/goals", "POST", goalForm);
      }
      setGoalForm(EMPTY_GOAL); setEditingId(null); setShowForm(false); setGoalStatus("");
      loadGoals();
    } catch(e) { setGoalStatus(e.message); }
  }

  async function rollup() {
    try { const d = await api("/goals/rollup","POST"); setGoals(d.goals||[]); }
    catch(e) { setGoalStatus(e.message); }
  }

  async function deleteGoal(id) {
    await api(`/goals/${id}`,"DELETE"); loadGoals();
  }

  function editGoal(g) {
    setGoalForm({
      title:g.title, metric_type:g.metric_type,
      period_start:g.period_start, period_end:g.period_end,
      target_value:g.target_value, notes:g.notes||"", status:g.status,
    });
    setEditingId(g.id); setShowForm(true);
  }

  // ── Report summary ───────────────────────────────────────────────────────────
  async function fetchSummary() {
    try {
      const d = await api(`/reports/summary?date_from=${dateFrom}&date_to=${dateTo}`);
      setSummary(d);
    } catch {}
  }

  // ── Digest handlers ──────────────────────────────────────────────────────────
  async function createDigest() {
    if (!digestEmail.trim()) return;
    try {
      await api("/reports/digests","POST",{ recipient_email:digestEmail.trim(), cadence:digestCadence, active:true });
      setDigestEmail(""); setDigestStatus(""); loadDigests();
    } catch(e) { setDigestStatus(e.message); }
  }

  async function toggleDigest(d) {
    await api(`/reports/digests/${d.id}`,"PUT",{ ...d, active:!d.active });
    loadDigests();
  }

  async function deleteDigest(id) {
    await api(`/reports/digests/${id}`,"DELETE"); loadDigests();
  }

  // ── Styles ───────────────────────────────────────────────────────────────────
  const s = {
    h2:    { fontFamily:'"Cinzel", serif', fontSize:11, letterSpacing:3, color:"#7a9e7c", margin:"1.25rem 0 0.6rem" },
    input: { background:"#0e130e", border:"1px solid #2a3a2a", color:"#e8f0e8", padding:"5px 10px", borderRadius:4, fontSize:13 },
    btn:   { background:"#1a2a1a", border:"1px solid #3a5a3c", color:"#e8f0e8", padding:"5px 14px", cursor:"pointer", borderRadius:4, fontSize:12 },
    btnPri:{ background:"#3ab8a0", border:"none", color:"#000", padding:"6px 16px", cursor:"pointer", borderRadius:4, fontSize:12, fontWeight:600 },
    row:   { display:"flex", gap:8, alignItems:"center", flexWrap:"wrap", marginBottom:8 },
    card:  { background:"#0b100b", border:"1px solid #2a3a2a", borderRadius:6, padding:"12px 14px", marginBottom:8 },
    label: { fontSize:10, color:"#7a9e7c", fontFamily:'"Cinzel", serif', letterSpacing:1, display:"block", marginBottom:2 },
  };

  return (
    <div style={{ fontFamily:'"Segoe UI", sans-serif', fontSize:13, color:"#e8f0e8" }}>

      {/* ── Goals ── */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
        <div style={s.h2}>GOALS</div>
        <div style={s.row}>
          <button style={s.btn} onClick={rollup}>Rollup</button>
          <button style={s.btnPri} onClick={()=>{ setGoalForm(EMPTY_GOAL); setEditingId(null); setShowForm(v=>!v); }}>
            {showForm && !editingId ? "Cancel" : "+ New Goal"}
          </button>
        </div>
      </div>

      {showForm && (
        <div style={s.card}>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
            <div>
              <label style={s.label}>TITLE</label>
              <input style={{...s.input,width:"100%"}} value={goalForm.title}
                onChange={e=>setGoalForm(f=>({...f,title:e.target.value}))} />
            </div>
            <div>
              <label style={s.label}>METRIC</label>
              <select style={{...s.input,width:"100%"}} value={goalForm.metric_type}
                onChange={e=>setGoalForm(f=>({...f,metric_type:e.target.value}))}>
                {METRIC_TYPES.map(t=><option key={t} value={t}>{METRIC_LABELS[t]}</option>)}
              </select>
            </div>
            <div>
              <label style={s.label}>PERIOD START</label>
              <input style={{...s.input,width:"100%"}} type="date" value={goalForm.period_start}
                onChange={e=>setGoalForm(f=>({...f,period_start:e.target.value}))} />
            </div>
            <div>
              <label style={s.label}>PERIOD END</label>
              <input style={{...s.input,width:"100%"}} type="date" value={goalForm.period_end}
                onChange={e=>setGoalForm(f=>({...f,period_end:e.target.value}))} />
            </div>
            <div>
              <label style={s.label}>TARGET</label>
              <input style={{...s.input,width:"100%"}} type="number" min={1} value={goalForm.target_value}
                onChange={e=>setGoalForm(f=>({...f,target_value:+e.target.value}))} />
            </div>
            <div>
              <label style={s.label}>NOTES</label>
              <input style={{...s.input,width:"100%"}} value={goalForm.notes||""}
                onChange={e=>setGoalForm(f=>({...f,notes:e.target.value}))} />
            </div>
            {editingId && (
              <div>
                <label style={s.label}>STATUS</label>
                <select style={{...s.input,width:"100%"}} value={goalForm.status||"open"}
                  onChange={e=>setGoalForm(f=>({...f,status:e.target.value}))}>
                  {STATUSES.map(st=><option key={st} value={st}>{st}</option>)}
                </select>
              </div>
            )}
          </div>
          {goalStatus && <div style={{color:"#f87171",fontSize:11,margin:"6px 0"}}>{goalStatus}</div>}
          <div style={{...s.row,marginTop:10}}>
            <button style={s.btnPri} onClick={saveGoal}>{editingId?"Save":"Create"}</button>
            <button style={s.btn} onClick={()=>{setShowForm(false);setEditingId(null);setGoalStatus("");}}>Cancel</button>
          </div>
        </div>
      )}

      {goals.length === 0 && <p style={{color:"#3a5a3c",fontSize:12}}>No goals yet.</p>}
      {goals.map(g => (
        <div key={g.id} style={s.card}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:6 }}>
            <div>
              <strong style={{fontSize:14}}>{g.title}</strong>
              <span style={{marginLeft:8,fontSize:11,color:"#7a9e7c"}}>{METRIC_LABELS[g.metric_type]}</span>
              <span style={{marginLeft:8,fontSize:11,color:"#3a5a3c"}}>{g.period_start} – {g.period_end}</span>
            </div>
            <div style={s.row}>
              <span style={{
                fontSize:10, padding:"2px 8px", borderRadius:3,
                background: STATUS_COLOR[g.status]+"22",
                border:`1px solid ${STATUS_COLOR[g.status]}44`,
                color: STATUS_COLOR[g.status],
                fontFamily:'"Cinzel", serif', letterSpacing:1,
              }}>{g.status.toUpperCase()}</span>
              <button style={s.btn} onClick={()=>editGoal(g)}>Edit</button>
              <button style={{...s.btn,color:"#f87171",borderColor:"#f8717122"}} onClick={()=>deleteGoal(g.id)}>✕</button>
            </div>
          </div>
          {/* Progress bar */}
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{flex:1,height:6,background:"#1e2e1e",borderRadius:3,overflow:"hidden"}}>
              <div style={{
                height:"100%", borderRadius:3,
                background: STATUS_COLOR[g.status]||"#3ab8a0",
                width:`${Math.min(100,g.pct)}%`,
                transition:"width 0.5s ease",
              }}/>
            </div>
            <span style={{fontSize:11,color:"#7a9e7c",whiteSpace:"nowrap",minWidth:120,textAlign:"right"}}>
              {fmtMetric(g.metric_type, g.current_value)} / {fmtMetric(g.metric_type, g.target_value)}
              {" "}({g.pct}%)
            </span>
          </div>
          {g.notes && <div style={{fontSize:11,color:"#3a5a3c",marginTop:4}}>{g.notes}</div>}
        </div>
      ))}

      {/* ── Report Summary ── */}
      <div style={s.h2}>WORKSPACE SUMMARY</div>
      <div style={s.row}>
        <div>
          <label style={s.label}>FROM</label>
          <input style={s.input} type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)} />
        </div>
        <div>
          <label style={s.label}>TO</label>
          <input style={s.input} type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)} />
        </div>
        <button style={{...s.btnPri,alignSelf:"flex-end"}} onClick={fetchSummary}>Run</button>
      </div>
      {summary && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
          {[
            ["Contacts",  summary.new_contacts],
            ["Leads",     summary.new_leads],
            ["Clients",   summary.new_clients],
            ["Quotes",    summary.quotes],
            ["Orders",    summary.orders],
            ["Bookings",  summary.bookings],
            ["Revenue",   null, summary.revenue_display],
          ].map(([label, val, display]) => (
            <div key={label} style={{background:"#0b100b",border:"1px solid #2a3a2a",borderRadius:6,padding:"10px 14px"}}>
              <div style={{fontSize:11,color:"#3a5a3c",fontFamily:'"Cinzel", serif',letterSpacing:1}}>{label.toUpperCase()}</div>
              <div style={{fontSize:"1.4rem",fontWeight:700,color:"#3ab8a0",marginTop:2}}>
                {display ?? (val??0).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Digest Schedules ── */}
      <div style={s.h2}>REPORT DIGESTS</div>
      <div style={s.row}>
        <input style={{...s.input,flex:1}} value={digestEmail} placeholder="recipient@email.com"
          onChange={e=>setDigestEmail(e.target.value)} />
        <select style={s.input} value={digestCadence} onChange={e=>setDigestCadence(e.target.value)}>
          {CADENCES.map(c=><option key={c} value={c}>{c}</option>)}
        </select>
        <button style={s.btnPri} onClick={createDigest}>Add</button>
        {digestStatus && <span style={{color:"#f87171",fontSize:11}}>{digestStatus}</span>}
      </div>
      {digests.length === 0 && <p style={{color:"#3a5a3c",fontSize:12}}>No digest schedules.</p>}
      {digests.map(d=>(
        <div key={d.id} style={{...s.card,display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
          <div>
            <strong style={{fontSize:13}}>{d.recipient_email}</strong>
            <span style={{marginLeft:8,fontSize:11,color:"#7a9e7c"}}>{d.cadence}</span>
            {d.last_sent_at && <span style={{marginLeft:8,fontSize:11,color:"#3a5a3c"}}>last: {d.last_sent_at.slice(0,10)}</span>}
          </div>
          <div style={s.row}>
            <button style={{...s.btn,color:d.active?"#4ade80":"#6b7280"}} onClick={()=>toggleDigest(d)}>
              {d.active?"Active":"Paused"}
            </button>
            <button style={{...s.btn,color:"#f87171",borderColor:"#f8717122"}} onClick={()=>deleteDigest(d.id)}>✕</button>
          </div>
        </div>
      ))}
    </div>
  );
}

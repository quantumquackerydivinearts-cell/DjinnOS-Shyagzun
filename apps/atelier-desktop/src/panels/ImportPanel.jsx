import React, { useState, useRef } from "react";

// ── Column alias table ────────────────────────────────────────────────────────
// Every name a real export might use — maps to Atelier's canonical field names.
const ALIASES = {
  full_name: [
    "full name","name","customer name","insured name","insured","contact name",
    "client name","account name","display name","account holder",
  ],
  first_name: ["first name","firstname","fname","given name","first"],
  last_name:  ["last name","lastname","lname","surname","family name","last"],
  email:   ["email","email address","customer email","insured email","contact email"],
  phone:   ["phone","phone number","cell phone","mobile","telephone","cell","work phone"],
  address: ["address","street address","mailing address","billing address"],
  website: ["website","url","web","homepage","site"],
  source:  ["source","lead source","referral source","how did you hear"],
  details: ["details","notes","note","comments","description","remarks"],
  status:  ["status","stage","lead status","client status","account stage"],
};

const ENTITY_LABELS = { contacts: "Contacts", leads: "Leads", clients: "Clients" };

function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ""); }

function detectMapping(headers) {
  const map = {};
  for (const header of headers) {
    const n = norm(header);
    for (const [field, aliases] of Object.entries(ALIASES)) {
      if (!map[field] && aliases.some(a => norm(a) === n)) {
        map[field] = header; break;
      }
    }
  }
  return map;
}

function detectEntity(map) {
  if (map.source || map.details) return "leads";
  if (map.full_name && (map.email || map.phone)) return "clients";
  return "contacts";
}

// ── CSV parser ────────────────────────────────────────────────────────────────
function parseCsv(text) {
  const lines = text.replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n").filter(l => l.trim());
  if (lines.length < 2) return { headers: [], rows: [] };

  function parseLine(line) {
    const fields = []; let cur = ""; let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQ && line[i+1] === '"') { cur += '"'; i++; } else inQ = !inQ;
      } else if (ch === ',' && !inQ) { fields.push(cur.trim()); cur = ""; }
      else cur += ch;
    }
    fields.push(cur.trim()); return fields;
  }

  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map(l => {
    const vals = parseLine(l);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] ?? ""; });
    return obj;
  });
  return { headers, rows };
}

function remapRows(rows, fieldMap) {
  return rows
    .filter(raw => Object.values(raw).some(v => String(v).trim()))
    .map(raw => {
      const out = {};
      for (const [field, header] of Object.entries(fieldMap)) {
        if (header && raw[header] !== undefined) {
          const v = String(raw[header]).trim();
          if (v) out[field] = v;
        }
      }
      if (!out.full_name) {
        const combined = [out.first_name, out.last_name].filter(Boolean).join(" ").trim();
        if (combined) out.full_name = combined;
      }
      delete out.first_name; delete out.last_name;
      return out;
    });
}

// ── Component ─────────────────────────────────────────────────────────────────
export function ImportPanel({ apiBase, authToken, workspaceId }) {
  const fileRef = useRef(null);
  const [file,      setFile]      = useState(null);
  const [dragOver,  setDragOver]  = useState(false);
  const [importing, setImporting] = useState(false);
  const [result,    setResult]    = useState(null);
  const [error,     setError]     = useState("");

  function loadFile(f) {
    if (!f) return;
    setResult(null); setError("");
    const reader = new FileReader();
    reader.onload = e => {
      const { headers, rows } = parseCsv(e.target.result);
      if (!headers.length || !rows.length) {
        setError("Could not parse CSV — check the file has headers and at least one row."); return;
      }
      const fieldMap = detectMapping(headers);
      const entity   = detectEntity(fieldMap);
      setFile({ name: f.name, rowCount: rows.length, entity, fieldMap, rows, headers });
    };
    reader.readAsText(f);
  }

  async function handleImport() {
    if (!file) return;
    setImporting(true); setError(""); setResult(null);
    try {
      const mapped = remapRows(file.rows, file.fieldMap);
      const r = await fetch(`${apiBase}/v1/import/${file.entity}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`,
          "X-Workspace-Id": workspaceId,
        },
        body: JSON.stringify({ rows: mapped }),
      });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `HTTP ${r.status}`); }
      setResult(await r.json());
    } catch (e) { setError(e.message); }
    finally { setImporting(false); }
  }

  function reset() {
    setFile(null); setResult(null); setError("");
    if (fileRef.current) fileRef.current.value = "";
  }

  function exportErrors() {
    const lines = ["Row,Reason", ...result.errors.map(e => `${e.row},"${e.reason.replace(/"/g,'""')}"`)]
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "import_errors.csv" });
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  const mappedFields = file
    ? Object.entries(file.fieldMap).filter(([, h]) => h).map(([f, h]) => ({ field: f, header: h }))
    : [];

  const s = {
    zone: over => ({
      border: `2px dashed ${over ? "#3ab8a0" : "#2a3a2a"}`,
      borderRadius: 6, padding: "2rem 1rem", textAlign: "center",
      cursor: "pointer", background: over ? "rgba(58,184,160,0.06)" : "transparent",
      marginBottom: "1rem", transition: "border-color 0.15s",
    }),
    detPanel: {
      background: "#0b100b", border: "1px solid #2a3a2a",
      borderRadius: 6, padding: "0.9rem 1rem", marginBottom: "1rem",
    },
    meta: { fontSize: 11, color: "#7a9e7c", marginBottom: 2, fontFamily: '"Cinzel", serif', letterSpacing: 1 },
    chip: (color) => ({
      background: "#0e130e", borderRadius: 3, padding: "0.2rem 0.55rem",
      fontSize: 11, color, border: `1px solid ${color}22`,
    }),
    statBox: (color) => ({
      minWidth: 80, background: "#0b100b", borderRadius: 4,
      padding: "0.6rem 0.9rem", border: "1px solid #2a3a2a",
    }),
    statNum: color => ({ fontSize: "1.4rem", fontWeight: 700, color }),
    btn: { background: "#1a2a1a", border: "1px solid #3a5a3c", color: "#e8f0e8", padding: "6px 16px", cursor: "pointer", borderRadius: 4, fontSize: 13 },
    btnPri: { background: "#3ab8a0", border: "none", color: "#000", padding: "6px 18px", cursor: "pointer", borderRadius: 4, fontSize: 13, fontWeight: 600 },
  };

  return (
    <div style={{ fontFamily: '"Segoe UI", sans-serif', fontSize: 14, color: "#e8f0e8" }}>

      {/* Drop zone */}
      <div
        style={s.zone(dragOver)}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]); }}
        onClick={() => fileRef.current?.click()}
      >
        <div style={{ fontSize: "1.6rem", marginBottom: "0.4rem", color: "#3ab8a0" }}>◌</div>
        <div style={{ color: "#7a9e7c", fontSize: "0.9rem" }}>
          {file
            ? <><strong style={{ color: "#e8f0e8" }}>{file.name}</strong> — click to replace</>
            : "Drag & drop a CSV here, or click to browse"}
        </div>
        <input ref={fileRef} type="file" accept=".csv,text/csv" style={{ display: "none" }}
          onChange={e => loadFile(e.target.files[0])} />
      </div>

      {/* Detection summary */}
      {file && !result && (
        <div style={s.detPanel}>
          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", marginBottom: "0.7rem" }}>
            <div>
              <div style={s.meta}>DETECTED AS</div>
              <div style={{ fontWeight: 700, color: "#3ab8a0", fontSize: "1rem" }}>
                {ENTITY_LABELS[file.entity]}
              </div>
            </div>
            <div>
              <div style={s.meta}>ROWS</div>
              <div style={{ fontWeight: 700 }}>{file.rowCount}</div>
            </div>
            <div>
              <div style={s.meta}>COLUMNS MAPPED</div>
              <div style={{ fontWeight: 700 }}>{mappedFields.length} / {Object.keys(file.fieldMap).length}</div>
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.5rem" }}>
            {mappedFields.map(({ field, header }) => (
              <span key={field} style={s.chip("#7a9e7c")}>
                <span style={{ color: "#3a5a3c" }}>{header}</span>
                {" → "}
                <span style={{ color: "#3ab8a0" }}>{field}</span>
              </span>
            ))}
          </div>

          <details>
            <summary style={{ fontSize: 11, color: "#3a5a3c", cursor: "pointer" }}>
              All CSV columns ({file.headers.length})
            </summary>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginTop: "0.3rem" }}>
              {file.headers.map(h => (
                <span key={h} style={{ background: "#0e130e", border: "1px solid #1e2e1e", borderRadius: 3, padding: "0.15rem 0.4rem", fontSize: 11, color: "#3a5a3c" }}>{h}</span>
              ))}
            </div>
          </details>
        </div>
      )}

      {error && <div style={{ color: "#f87171", fontSize: 12, marginBottom: "0.75rem" }}>{error}</div>}

      {/* Action */}
      {file && !result && (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button style={s.btnPri} onClick={handleImport} disabled={importing}>
            {importing ? "Importing…" : `Import ${file.rowCount} rows → ${ENTITY_LABELS[file.entity]}`}
          </button>
          <button style={s.btn} onClick={reset}>Clear</button>
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={s.detPanel}>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
            {[
              { label: "Inserted", value: result.inserted, color: "#4ade80" },
              { label: "Updated",  value: result.updated,  color: "#3ab8a0" },
              { label: "Errors",   value: result.errors?.length ?? 0, color: result.errors?.length ? "#f87171" : "#3a5a3c" },
            ].map(({ label, value, color }) => (
              <div key={label} style={s.statBox(color)}>
                <div style={s.statNum(color)}>{value}</div>
                <div style={{ fontSize: 11, color: "#3a5a3c" }}>{label}</div>
              </div>
            ))}
          </div>

          {result.errors?.length > 0 && (
            <>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: 12, color: "#f87171" }}>Row errors:</span>
                <button style={s.btn} onClick={exportErrors}>Export errors CSV</button>
              </div>
              <div style={{ maxHeight: 180, overflowY: "auto", background: "#0e130e", borderRadius: 4, padding: "0.4rem 0.6rem" }}>
                {result.errors.map((e, i) => (
                  <div key={i} style={{ fontSize: 11, color: "#7a9e7c", padding: "0.2rem 0" }}>
                    <span style={{ color: "#f87171" }}>Row {e.row}:</span> {e.reason}
                  </div>
                ))}
              </div>
            </>
          )}

          <button style={{ ...s.btn, marginTop: "0.75rem" }} onClick={reset}>Import another file</button>
        </div>
      )}
    </div>
  );
}

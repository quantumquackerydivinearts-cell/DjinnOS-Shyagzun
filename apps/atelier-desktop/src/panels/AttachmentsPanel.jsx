import React, { useState, useEffect, useRef } from "react";

const ICON = {
  "application/pdf":   "⬡",
  "image/png":         "◈",
  "image/jpeg":        "◈",
  "image/gif":         "◈",
  "image/webp":        "◈",
  "text/plain":        "◉",
  "text/csv":          "◉",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "◉",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "◉",
};

function fileIcon(ct) { return ICON[ct] || "◌"; }

function fmtSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function AttachmentsPanel({ entityType, entityId, apiBase, authToken, workspaceId }) {
  const fileRef              = useRef(null);
  const [files, setFiles]    = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError]    = useState("");

  const hdrs = { Authorization: `Bearer ${authToken}` };
  const url  = `${apiBase}/v1/attachments?entity_type=${entityType}&entity_id=${entityId}&workspace_id=${workspaceId}`;

  useEffect(() => {
    if (!entityId || !authToken) return;
    fetch(url, { headers: hdrs }).then(r => r.ok ? r.json() : []).then(setFiles).catch(() => {});
  }, [entityType, entityId, authToken, workspaceId]);

  async function upload(file) {
    setUploading(true); setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await fetch(url, { method: "POST", headers: hdrs, body: form });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || "Upload failed"); }
      const created = await r.json();
      setFiles(prev => [...prev, created]);
    } catch (e) { setError(e.message); }
    finally { setUploading(false); }
  }

  async function del(id) {
    try {
      await fetch(`${apiBase}/v1/attachments/${id}?workspace_id=${workspaceId}`, { method: "DELETE", headers: hdrs });
      setFiles(prev => prev.filter(f => f.id !== id));
    } catch {}
  }

  async function download(id, filename) {
    try {
      const r = await fetch(`${apiBase}/v1/attachments/${id}/download?workspace_id=${workspaceId}`, { headers: hdrs });
      const blob = await r.blob();
      const a = Object.assign(document.createElement("a"), {
        href: URL.createObjectURL(blob), download: filename,
      });
      a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    } catch {}
  }

  const s = {
    zone: (over) => ({
      border: `1px dashed ${over ? "#3ab8a0" : "#2a3a2a"}`,
      borderRadius: 4, padding: "6px 12px", cursor: "pointer",
      background: over ? "rgba(58,184,160,0.06)" : "transparent",
      fontSize: 12, color: "#7a9e7c", textAlign: "center",
      marginBottom: files.length ? 6 : 0, transition: "border-color 0.15s",
    }),
    row: {
      display: "flex", alignItems: "center", gap: 8,
      background: "#0b100b", borderRadius: 4,
      padding: "4px 8px", marginBottom: 3, fontSize: 12,
    },
    nameBtn: {
      color: "#3ab8a0", background: "none", border: "none",
      cursor: "pointer", fontSize: 12, padding: 0,
      textAlign: "left", flex: 1, overflow: "hidden",
      textOverflow: "ellipsis", whiteSpace: "nowrap",
    },
    delBtn: {
      color: "#3a4a3a", background: "none", border: "none",
      cursor: "pointer", fontSize: 11, flexShrink: 0,
    },
  };

  return (
    <div>
      <div
        style={s.zone(dragOver)}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) upload(f); }}
        onClick={() => fileRef.current?.click()}
      >
        {uploading ? "Uploading…" : "◌  Attach file — drag & drop or click · 10 MB max"}
        <input ref={fileRef} type="file" style={{ display: "none" }}
          onChange={e => { const f = e.target.files[0]; if (f) upload(f); e.target.value = ""; }} />
      </div>

      {error && <div style={{ color: "#f87171", fontSize: 11, margin: "3px 0" }}>{error}</div>}

      {files.map(f => (
        <div key={f.id} style={s.row}>
          <span style={{ color: "#7a9e7c" }}>{fileIcon(f.content_type)}</span>
          <button style={s.nameBtn} onClick={() => download(f.id, f.filename)}>{f.filename}</button>
          <span style={{ color: "#3a5a3c", flexShrink: 0 }}>{fmtSize(f.size_bytes)}</span>
          <button style={s.delBtn} onClick={() => del(f.id)}>✕</button>
        </div>
      ))}
    </div>
  );
}

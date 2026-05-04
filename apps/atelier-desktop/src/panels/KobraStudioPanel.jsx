/**
 * KobraStudioPanel.jsx
 * Sanctum document browser — read and inspect .ko files.
 *
 * Uses Electron IPC (atelierDesktop.fs.*) when available.
 * In web mode, shows a placeholder.
 */
import React, { useState, useCallback } from "react";

const FS = window.atelierDesktop?.fs ?? null;

// ── Scene compile helper ──────────────────────────────────────────────────────
// Builds a Python script that imports scene_compiler.py from the sanctum
// charters directory and compiles the selected .ko file in-place.

function buildCompileScript(sanctumDir, koFilename) {
  const koPath  = `${sanctumDir}/${koFilename}`.replace(/\\/g, "/");
  const outName = koFilename.replace(/\.scene\.ko$/, ".scene.json").replace(/\.ko$/, ".scene.json");
  const outPath = `${sanctumDir}/${outName}`.replace(/\\/g, "/");
  const chartersDir = sanctumDir.replace(/\\/g, "/") + "/../charters";
  return `
import sys, json
from pathlib import Path

charters = Path(r'${chartersDir}').resolve()
if str(charters) not in sys.path:
    sys.path.insert(0, str(charters))

from scene_compiler import compile_scene

src = Path(r'${koPath}').read_text(encoding='utf-8')
scene_id = '${koFilename}'.replace('.scene.ko','').replace('.ko','')
result = compile_scene(src, scene_id)
out = Path(r'${outPath}')
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
n = len(result['renderer']['scene']['voxels'])
print(f'ok:{n}:{out.name}')
`.trim();
}

// ── Kobra syntax highlighter (minimal) ───────────────────────────────────────

function highlightKobra(line) {
  // Section headers:  LoX: MavoName(Ty...)
  // Spec entries:     [MavoName ...]
  // TaShyMa closers:  [TaShyMa(n)]
  // Seth declarations: SethVaShy: ...
  // Comments: lines starting with //
  if (!line.trim()) return <span className="ko-blank">{line || " "}</span>;
  if (line.trimStart().startsWith("//")) return <span className="ko-comment">{line}</span>;
  if (/^SethVaShy/.test(line.trim())) return <span className="ko-seth">{line}</span>;
  if (/^YeGaoh/.test(line.trim()))    return <span className="ko-cluster">{line}</span>;
  if (/^Lo\w+\s*:/.test(line.trim())) return <span className="ko-section">{line}</span>;
  if (/\[TaShyMa/.test(line))         return <span className="ko-tashyma">{line}</span>;
  if (line.trim().startsWith("["))    return <span className="ko-spec">{line}</span>;
  return <span className="ko-token">{line}</span>;
}

// ── Stats parser ──────────────────────────────────────────────────────────────

function parseDocStats(content) {
  const lines  = content.split("\n");
  const sects  = lines.filter(l => /^Lo\w+\s*:/.test(l.trim())).length;
  const specs  = lines.filter(l => l.trim().startsWith("[") && !/TaShyMa/.test(l)).length;
  const closers = lines.filter(l => /\[TaShyMa/.test(l)).length;
  return { lines: lines.length, sections: sects, specs, closers };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function KobraStudioPanel() {
  const [sanctumDir, setSanctumDir]   = useState("");
  const [files, setFiles]             = useState([]);
  const [selected, setSelected]       = useState(null);
  const [content, setContent]         = useState("");
  const [status, setStatus]           = useState("");
  const [loading, setLoading]         = useState(false);
  const [search, setSearch]           = useState("");
  const [compileStatus, setCompileStatus] = useState("");

  const isElectron = Boolean(FS);

  // ── Directory ─────────────────────────────────────────────────────────────

  const chooseDir = useCallback(async () => {
    if (!FS) return;
    const result = await FS.chooseDirectory();
    if (!result?.ok) return;
    setSanctumDir(result.directory);
    await loadFiles(result.directory);
  }, []);

  const loadFiles = useCallback(async (dir) => {
    if (!FS || !dir) return;
    setLoading(true);
    setStatus("");
    try {
      const result = await FS.listAssetsBySuffix(dir, ".ko");
      setFiles(result?.files ?? []);
      setSelected(null);
      setContent("");
    } catch (e) {
      setStatus(`Error listing files: ${e.message ?? e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── File viewer ───────────────────────────────────────────────────────────

  const openFile = useCallback(async (filename) => {
    if (!FS || !sanctumDir) return;
    setLoading(true);
    setStatus("");
    try {
      const result = await FS.readTextFile(sanctumDir, filename);
      if (result?.ok) {
        setSelected(filename);
        setContent(result.content);
      } else {
        setStatus(`Failed to read ${filename}`);
      }
    } catch (e) {
      setStatus(`Error: ${e.message ?? e}`);
    } finally {
      setLoading(false);
    }
  }, [sanctumDir]);

  // ── Scene compile ─────────────────────────────────────────────────────────

  const compileScene = useCallback(async () => {
    if (!FS || !sanctumDir || !selected) return;
    setCompileStatus("Compiling…");
    try {
      const script = buildCompileScript(sanctumDir, selected);
      const result = await FS.runPython(sanctumDir, script, { filename: "_scene_compile.py", timeoutMs: 30000 });
      if (result?.ok) {
        const line = (result.stdout || "").trim();
        if (line.startsWith("ok:")) {
          const [, nvox, outName] = line.split(":");
          setCompileStatus(`✓ ${nvox} voxels → ${outName}`);
        } else {
          setCompileStatus(`✓ ${line || "done"}`);
        }
      } else {
        setCompileStatus(`Error: ${result?.stderr || "unknown"}`);
      }
    } catch (e) {
      setCompileStatus(`Error: ${e.message ?? e}`);
    }
  }, [sanctumDir, selected]);

  const isScene = selected && (selected.endsWith(".scene.ko") || selected.includes("scene"));

  const filteredFiles = search.trim()
    ? files.filter(f => f.toLowerCase().includes(search.trim().toLowerCase()))
    : files;

  const stats = content ? parseDocStats(content) : null;

  // ── Render ────────────────────────────────────────────────────────────────

  if (!isElectron) {
    return (
      <section className="panel">
        <h2>Kobra Studio</h2>
        <p className="hint">Kobra Studio requires the desktop app — file system access not available in web mode.</p>
      </section>
    );
  }

  return (
    <section className="panel kobra-studio">
      <h2>Kobra Studio</h2>
      <p className="hint">
        Browse and inspect sanctum <code>.ko</code> documents.
        Point to <code>DjinnOS_Shyagzun/shygazun/sanctum/</code>.
      </p>

      <div className="kobra-dir-row">
        <button className="action" onClick={chooseDir} disabled={loading}>
          {sanctumDir ? "Change Sanctum" : "Open Sanctum Directory"}
        </button>
        {sanctumDir && (
          <span className="hint ko-path" title={sanctumDir}>
            {sanctumDir.length > 60 ? "…" + sanctumDir.slice(-57) : sanctumDir}
          </span>
        )}
      </div>

      {status && <p className="hint" style={{ color: "var(--rose-shak, #d46)" }}>{status}</p>}

      {files.length > 0 && (
        <div className="kobra-workspace">
          {/* ── File list ── */}
          <div className="kobra-file-list">
            <div className="kobra-search-row">
              <input
                placeholder="Filter files…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <span className="hint">{filteredFiles.length}/{files.length}</span>
            </div>
            {filteredFiles.map(f => (
              <button
                key={f}
                className={`kobra-file-btn ${selected === f ? "active" : ""}`}
                onClick={() => openFile(f)}
              >
                {f}
              </button>
            ))}
          </div>

          {/* ── Document viewer ── */}
          {selected && (
            <div className="kobra-doc-viewer">
              <div className="kobra-doc-header">
                <span className="ko-filename">{selected}</span>
                {stats && (
                  <span className="hint ko-stats">
                    {stats.lines}L · {stats.sections} sections · {stats.specs} specs
                  </span>
                )}
                {isScene && (
                  <button className="action ko-compile-btn" onClick={compileScene} disabled={loading}>
                    Compile → JSON
                  </button>
                )}
                {compileStatus && (
                  <span className="hint ko-compile-status">{compileStatus}</span>
                )}
              </div>
              <div className="kobra-doc-content">
                {content.split("\n").map((line, i) => (
                  <div key={i} className="ko-line">
                    <span className="ko-lnum">{i + 1}</span>
                    {highlightKobra(line)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {loading && <p className="hint">Loading…</p>}
    </section>
  );
}
/**
 * AlchemySubjectPanel.jsx
 * Field-first alchemical subject authoring.
 *
 * Authoring order is enforced by the system — process ontology, not scriptural:
 *   Stage 1 — Field      : axis, Shygazun word, Dragon Tongue organism,
 *                          narrative, somatic, intensity
 *   Stage 2 — Substrate  : required materials, base outputs, enhanced outputs
 *   Stage 3 — Identity   : subject ID, name, lore — then export
 *
 * A formula is the notation of a relationship that already happened.
 * The field is authored first. The substrate and outputs follow from it.
 */

import React, { useState, useEffect, useCallback } from "react";

const AXES = ["mental", "spatial", "temporal"];

const AXIS_DESCRIPTIONS = {
  mental:   "Information processing — how the subject's cognition/self-reference behaves",
  spatial:  "Boundary and extent — how the subject's location and form manifest",
  temporal: "Persistence and continuity — how the subject moves through time",
};

const DRAGON_TONGUE_HINTS = {
  mental:   "e.g. Physarum polycephalum — solves shortest-path problems with no neurons",
  spatial:  "e.g. Armillaria ostoyae — 2,385 acres, no perceptible edge",
  temporal: "e.g. Syntrichia caninervis — stops and restarts with no protective mechanism",
};

const EMPTY_FIELD = {
  axis:         "",
  shygazun:     "",
  dragon_tongue: "",
  narrative:    "",
  somatic:      "",
  intensity:    0.7,
};

const EMPTY_SUBJECT = {
  id:       "",
  name:     "",
  lore:     "",
  field:    { ...EMPTY_FIELD },
  required_materials: [],   // [{item_id, qty}]
  base_outputs:       [],   // [{item_id, qty}]
  enhanced_outputs:   [],   // [{item_id, qty}]
};

function kvListToObj(list) {
  const obj = {};
  for (const { item_id, qty } of list) {
    if (item_id.trim()) obj[item_id.trim()] = Number(qty) || 1;
  }
  return obj;
}

function objToKvList(obj) {
  return Object.entries(obj || {}).map(([item_id, qty]) => ({ item_id, qty }));
}

function KVEditor({ label, hint, items, onChange }) {
  const add = () => onChange([...items, { item_id: "", qty: 1 }]);
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i));
  const update = (i, field, val) =>
    onChange(items.map((it, idx) => idx === i ? { ...it, [field]: val } : it));

  return (
    <div className="kv-editor">
      <label>{label}</label>
      {hint && <p className="hint">{hint}</p>}
      {items.map((it, i) => (
        <div key={i} className="kv-row">
          <input
            value={it.item_id}
            placeholder="item_id"
            onChange={e => update(i, "item_id", e.target.value)}
          />
          <input
            type="number" min="1" value={it.qty}
            onChange={e => update(i, "qty", e.target.value)}
            style={{ width: 60 }}
          />
          <button className="action" onClick={() => remove(i)}>✕</button>
        </div>
      ))}
      <button className="action" onClick={add}>+ Add</button>
    </div>
  );
}

export function AlchemySubjectPanel({ apiBase = "http://127.0.0.1:9000" }) {
  const [gameSlug, setGameSlug]     = useState("7_KLGS");
  const [subject, setSubject]       = useState({ ...EMPTY_SUBJECT, field: { ...EMPTY_FIELD } });
  const [savedSubjects, setSaved]   = useState([]);
  const [status, setStatus]         = useState("");
  const [loading, setLoading]       = useState(false);

  // ── Completion gates ──────────────────────────────────────────────────────

  const f = subject.field;
  const fieldComplete = (
    f.axis && f.shygazun.trim() && f.dragon_tongue.trim() &&
    f.narrative.trim() && f.somatic.trim()
  );
  const substrateComplete = fieldComplete && subject.base_outputs.length > 0;
  const exportReady = substrateComplete && subject.id.trim() && subject.name.trim();

  // ── Saved subjects ────────────────────────────────────────────────────────

  const fetchSaved = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase}/v1/export/alchemy/${gameSlug}`);
      if (r.ok) {
        const data = await r.json();
        setSaved(data.subjects || []);
      }
    } catch { /* API may not be running */ }
  }, [apiBase, gameSlug]);

  useEffect(() => { fetchSaved(); }, [fetchSaved]);

  // ── Field helpers ─────────────────────────────────────────────────────────

  const setField = (key, val) =>
    setSubject(s => ({ ...s, field: { ...s.field, [key]: val } }));

  const setTop = (key, val) =>
    setSubject(s => ({ ...s, [key]: val }));

  // ── Export ────────────────────────────────────────────────────────────────

  const handleExport = async () => {
    if (!exportReady) return;
    setLoading(true);
    setStatus("");

    const payload = {
      id:   subject.id.trim(),
      name: subject.name.trim(),
      lore: subject.lore.trim(),
      field: {
        properties: [{
          axis:          subject.field.axis,
          shygazun:      subject.field.shygazun.trim(),
          dragon_tongue: subject.field.dragon_tongue.trim(),
          narrative:     subject.field.narrative.trim(),
          somatic:       subject.field.somatic.trim(),
          intensity:     Number(subject.field.intensity),
        }],
      },
      required_materials: kvListToObj(subject.required_materials),
      base_outputs:       kvListToObj(subject.base_outputs),
      enhanced_outputs:   kvListToObj(subject.enhanced_outputs),
    };

    try {
      const r = await fetch(`${apiBase}/v1/export/alchemy/${gameSlug}`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      if (r.ok) {
        setStatus("Exported.");
        setSubject({ ...EMPTY_SUBJECT, field: { ...EMPTY_FIELD } });
        fetchSaved();
      } else {
        const err = await r.json().catch(() => ({}));
        setStatus(`Error: ${err.detail || r.status}`);
      }
    } catch (e) {
      setStatus(`Network error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadSubject = (s) => {
    const props = s.field?.properties?.[0] || {};
    setSubject({
      id:   s.id || "",
      name: s.name || "",
      lore: s.lore || "",
      field: {
        axis:          props.axis || "",
        shygazun:      props.shygazun || "",
        dragon_tongue: props.dragon_tongue || "",
        narrative:     props.narrative || "",
        somatic:       props.somatic || "",
        intensity:     props.intensity ?? 0.7,
      },
      required_materials: objToKvList(s.required_materials),
      base_outputs:       objToKvList(s.base_outputs),
      enhanced_outputs:   objToKvList(s.enhanced_outputs),
    });
    setStatus("");
  };

  const deleteSubject = async (id) => {
    try {
      await fetch(`${apiBase}/v1/export/alchemy/${gameSlug}/${id}`, { method: "DELETE" });
      fetchSaved();
    } catch { /* ignore */ }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <section className="panel">
      <h2>Alchemy Lab</h2>
      <p className="hint">
        Process ontology — field first. A formula is the notation of a relationship
        that already happened. Author what the subject IS before authoring what it yields.
      </p>

      <div className="alchemy-game-slug">
        <label>Game Slug</label>
        <input value={gameSlug} onChange={e => setGameSlug(e.target.value)} style={{ width: 120 }} />
      </div>

      {/* ── Stage 1: Field ─────────────────────────────────────────── */}
      <div className="alchemy-stage">
        <h3>Stage 1 — Field {fieldComplete ? "✓" : ""}</h3>
        <p className="hint">
          What is the information field of this subject? Choose an axis and describe it
          in all four modes. This is the primary content — everything else follows from it.
        </p>

        <div className="alchemy-axes">
          <label>Axis</label>
          {AXES.map(ax => (
            <label key={ax} className="alchemy-axis-option">
              <input
                type="radio" name="axis" value={ax}
                checked={f.axis === ax}
                onChange={() => setField("axis", ax)}
              />
              <span><strong>{ax}</strong> — {AXIS_DESCRIPTIONS[ax]}</span>
            </label>
          ))}
        </div>

        <label>Shygazun Word
          <span className="hint"> — the word from the byte table that names this field property</span>
        </label>
        <input
          value={f.shygazun}
          placeholder="e.g. gasha, Wunashako, ko"
          onChange={e => setField("shygazun", e.target.value)}
        />

        <label>Dragon Tongue — Organism in Morphospace
          <span className="hint"> — biological description IS the definition, not metaphor</span>
        </label>
        <textarea
          rows={4}
          value={f.dragon_tongue}
          placeholder={f.axis ? DRAGON_TONGUE_HINTS[f.axis] : "Select an axis first"}
          onChange={e => setField("dragon_tongue", e.target.value)}
        />

        <label>Narrative
          <span className="hint"> — lore fragment / story resonance</span>
        </label>
        <textarea
          rows={3}
          value={f.narrative}
          placeholder="The story that situates this property in time..."
          onChange={e => setField("narrative", e.target.value)}
        />

        <label>Somatic
          <span className="hint"> — sensory / embodied description; what the body recognises before the mind does</span>
        </label>
        <textarea
          rows={2}
          value={f.somatic}
          placeholder="The sensation of correct perception..."
          onChange={e => setField("somatic", e.target.value)}
        />

        <label>Intensity: {Number(f.intensity).toFixed(2)}</label>
        <input
          type="range" min="0" max="1" step="0.05"
          value={f.intensity}
          onChange={e => setField("intensity", e.target.value)}
        />
      </div>

      {/* ── Stage 2: Substrate ─────────────────────────────────────── */}
      <div className={`alchemy-stage ${!fieldComplete ? "alchemy-locked" : ""}`}>
        <h3>Stage 2 — Substrate {substrateComplete ? "✓" : ""}</h3>
        {!fieldComplete && (
          <p className="hint locked">Complete the field description before authoring substrate.</p>
        )}
        {fieldComplete && (
          <>
            <p className="hint">
              Physical materials are substrate — not cause. Leave required materials empty
              for purely energetic treatments. Outputs follow from correct perception of
              the field, not from the materials themselves.
            </p>
            <KVEditor
              label="Required Materials"
              hint="Physical substrate needed for material outputs. Empty = purely energetic."
              items={subject.required_materials}
              onChange={v => setTop("required_materials", v)}
            />
            <KVEditor
              label="Base Outputs"
              hint="Yields at resonance ≥ 0.50"
              items={subject.base_outputs}
              onChange={v => setTop("base_outputs", v)}
            />
            <KVEditor
              label="Enhanced Outputs"
              hint="Yields at epiphanic quality (resonance ≥ 0.85 + charge ≥ 0.70)"
              items={subject.enhanced_outputs}
              onChange={v => setTop("enhanced_outputs", v)}
            />
          </>
        )}
      </div>

      {/* ── Stage 3: Identity & Export ─────────────────────────────── */}
      <div className={`alchemy-stage ${!substrateComplete ? "alchemy-locked" : ""}`}>
        <h3>Stage 3 — Identity & Export</h3>
        {!substrateComplete && (
          <p className="hint locked">Complete substrate before exporting.</p>
        )}
        {substrateComplete && (
          <>
            <label>Subject ID</label>
            <input
              value={subject.id}
              placeholder="e.g. grief_salve, temporal_tincture"
              onChange={e => setTop("id", e.target.value)}
            />
            <label>Name</label>
            <input
              value={subject.name}
              placeholder="Display name"
              onChange={e => setTop("name", e.target.value)}
            />
            <label>Lore</label>
            <textarea
              rows={2}
              value={subject.lore}
              placeholder="What Minerva says when she grants the formula..."
              onChange={e => setTop("lore", e.target.value)}
            />
            <button
              className="action"
              onClick={handleExport}
              disabled={!exportReady || loading}
            >
              {loading ? "Exporting…" : "Export Subject"}
            </button>
            {status && <p className="hint">{status}</p>}
          </>
        )}
      </div>

      {/* ── Saved subjects ─────────────────────────────────────────── */}
      {savedSubjects.length > 0 && (
        <div className="alchemy-saved">
          <h3>Saved Subjects — {gameSlug}</h3>
          {savedSubjects.map(s => (
            <div key={s.id} className="alchemy-saved-row">
              <span><strong>{s.id}</strong> — {s.name}</span>
              <span className="hint" style={{ marginLeft: 8 }}>
                [{s.field?.properties?.[0]?.axis}]
              </span>
              <button className="action" onClick={() => loadSubject(s)}>Edit</button>
              <button className="action" onClick={() => deleteSubject(s.id)}>Delete</button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

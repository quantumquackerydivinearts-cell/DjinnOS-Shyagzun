/**
 * AlchemySubjectPanel.jsx
 * Field-first alchemical subject authoring — Kobra-consistent vocabulary.
 *
 * Authoring order (process ontology, not scriptural):
 *   Stage 1 — Field      : ontic vowel, akinen tokens, Dragon Tongue organism,
 *                          narrative, somatic, intensity
 *   Stage 2 — Substrate  : required materials, base outputs, enhanced outputs
 *                          (use Kobra Mavo names for known items)
 *   Stage 3 — Identity   : kobra_id, display name, lore — then export
 *
 * Universal consistency contract:
 *   - Ontic vowels (A/O/I/E/Y/U) are AppleBlossom ontic vowel axis markers
 *   - Akinen tokens are space-separated Shygazun symbols from the byte table
 *   - Material/output IDs use Kobra Mavo names (MavoHealthPotion, MavoWormwood, …)
 *     for known KLIT/KLOB items; custom IDs remain valid for novel subjects
 *   - kobra_id maps to the MavoName in kos_labyrinth_alchemy.ko (future document)
 */

import React, { useState, useEffect, useCallback } from "react";
import { OBJECTS, ITEMS } from "../game7Registry.js";

// ── Ontic vowels (AppleBlossom) ───────────────────────────────────────────────

const ONTIC_VOWELS = [
  { vowel: "A", axis: "mental",   polarity: "+",
    label: "A  Mind+",  desc: "Active cognition — outward self-reference, generative thought" },
  { vowel: "O", axis: "mental",   polarity: "-",
    label: "O  Mind−",  desc: "Receptive cognition — inward self-reference, reflective silence" },
  { vowel: "I", axis: "spatial",  polarity: "+",
    label: "I  Space+", desc: "Expansion — boundary dissolution, field opening outward" },
  { vowel: "E", axis: "spatial",  polarity: "-",
    label: "E  Space−", desc: "Contraction — boundary formation, field closing inward" },
  { vowel: "Y", axis: "temporal", polarity: "+",
    label: "Y  Time+",  desc: "Forward continuity — becoming, progression through time" },
  { vowel: "U", axis: "temporal", polarity: "-",
    label: "U  Time−",  desc: "Cyclic return — remembrance, repetition through time" },
];

const DRAGON_TONGUE_HINTS = {
  mental:   "e.g. Physarum polycephalum — solves shortest-path problems with no neurons",
  spatial:  "e.g. Armillaria ostoyae — 2,385 acres, no perceptible edge",
  temporal: "e.g. Syntrichia caninervis — stops and restarts without a protective mechanism",
};

// ── Mavo name derivation ──────────────────────────────────────────────────────

function toMavoName(name) {
  return "Mavo" + name
    .replace(/[^a-zA-Z0-9 ]/g, "")
    .split(/\s+/)
    .filter(Boolean)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join("");
}

// Build suggestion list: KLIT items + KLOB apparatus (first ~20 objects)
const ITEM_SUGGESTIONS = [
  ...ITEMS.map(it => ({ mavo: toMavoName(it.name), label: `${toMavoName(it.name)} — ${it.name}` })),
  ...OBJECTS.slice(0, 20).map(ob => ({ mavo: toMavoName(ob.name), label: `${toMavoName(ob.name)} — ${ob.name} (apparatus)` })),
];

// ── Empty state ───────────────────────────────────────────────────────────────

const EMPTY_FIELD = {
  ontic:        "",     // A/O/I/E/Y/U
  akinen:       "",     // space-separated Shygazun tokens, e.g. "MuSha Mel"
  dragon_tongue: "",
  narrative:    "",
  somatic:      "",
  intensity:    0.7,
};

const EMPTY_SUBJECT = {
  kobra_id: "",          // Kobra Mavo name, e.g. "MavoGriefSalve"
  id:       "",          // API/legacy ID, e.g. "grief_salve"
  name:     "",
  lore:     "",
  field:    { ...EMPTY_FIELD },
  required_materials: [],
  base_outputs:       [],
  enhanced_outputs:   [],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

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

// ── KVEditor with Mavo item suggestions ──────────────────────────────────────

function KVEditor({ label, hint, items, onChange, listId }) {
  const add    = () => onChange([...items, { item_id: "", qty: 1 }]);
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i));
  const update = (i, field, val) =>
    onChange(items.map((it, idx) => idx === i ? { ...it, [field]: val } : it));

  return (
    <div className="kv-editor">
      <label>{label}</label>
      {hint && <p className="hint">{hint}</p>}
      <datalist id={listId}>
        {ITEM_SUGGESTIONS.map(s => <option key={s.mavo} value={s.mavo} label={s.label} />)}
      </datalist>
      {items.map((it, i) => (
        <div key={i} className="kv-row">
          <input
            list={listId}
            value={it.item_id}
            placeholder="MavoItemName or custom_id"
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

// ── Component ─────────────────────────────────────────────────────────────────

export function AlchemySubjectPanel({ apiBase = "http://127.0.0.1:9000" }) {
  const [gameSlug, setGameSlug]   = useState("7_KLGS");
  const [subject, setSubject]     = useState({ ...EMPTY_SUBJECT, field: { ...EMPTY_FIELD } });
  const [savedSubjects, setSaved] = useState([]);
  const [status, setStatus]       = useState("");
  const [loading, setLoading]     = useState(false);

  // ── Completion gates ──────────────────────────────────────────────────────

  const f = subject.field;
  const fieldComplete = Boolean(
    f.ontic && f.akinen.trim() && f.dragon_tongue.trim() &&
    f.narrative.trim() && f.somatic.trim()
  );
  const substrateComplete = fieldComplete && subject.base_outputs.length > 0;
  const exportReady = substrateComplete && subject.kobra_id.trim() && subject.name.trim();

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

  const setField = (key, val) =>
    setSubject(s => ({ ...s, field: { ...s.field, [key]: val } }));
  const setTop   = (key, val) =>
    setSubject(s => ({ ...s, [key]: val }));

  // Auto-derive legacy id and kobra_id from name when blank
  const handleNameChange = (val) => {
    setTop("name", val);
    if (!subject.id.trim()) {
      setTop("id", val.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""));
    }
    if (!subject.kobra_id.trim()) {
      setTop("kobra_id", toMavoName(val));
    }
  };

  // ── Export ────────────────────────────────────────────────────────────────

  const handleExport = async () => {
    if (!exportReady) return;
    setLoading(true);
    setStatus("");

    const onticVowel = ONTIC_VOWELS.find(v => v.vowel === f.ontic);

    const payload = {
      id:       subject.id.trim() || subject.kobra_id.trim(),
      kobra_id: subject.kobra_id.trim(),
      name:     subject.name.trim(),
      lore:     subject.lore.trim(),
      field: {
        properties: [{
          ontic:         f.ontic,
          axis:          onticVowel?.axis ?? "",
          polarity:      onticVowel?.polarity ?? "",
          akinen:        f.akinen.trim(),
          dragon_tongue: f.dragon_tongue.trim(),
          narrative:     f.narrative.trim(),
          somatic:       f.somatic.trim(),
          intensity:     Number(f.intensity),
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
      kobra_id: s.kobra_id || toMavoName(s.name || ""),
      id:       s.id || "",
      name:     s.name || "",
      lore:     s.lore || "",
      field: {
        ontic:         props.ontic || "",
        akinen:        props.akinen || props.shygazun || "",
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

  const selectedOntic = ONTIC_VOWELS.find(v => v.vowel === f.ontic);

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
          What is the information field of this subject? Select its ontic vowel
          (AppleBlossom axis marker), then characterize it in Shygazun and in all
          four modes. This is the primary content — everything else follows from it.
        </p>

        {/* Ontic vowel selector */}
        <label>Ontic Vowel
          <span className="hint"> — AppleBlossom axis and polarity</span>
        </label>
        <div className="alchemy-ontic-grid">
          {ONTIC_VOWELS.map(ov => (
            <label key={ov.vowel} className={`alchemy-ontic-option ${f.ontic === ov.vowel ? "selected" : ""}`}>
              <input
                type="radio" name="ontic" value={ov.vowel}
                checked={f.ontic === ov.vowel}
                onChange={() => setField("ontic", ov.vowel)}
              />
              <span className="ontic-vowel-label"><strong>{ov.label}</strong></span>
              <span className="ontic-desc hint">{ov.desc}</span>
            </label>
          ))}
        </div>

        {/* Akinen tokens */}
        <label>Akinen
          <span className="hint"> — space-separated Shygazun tokens from the byte table</span>
        </label>
        <input
          value={f.akinen}
          placeholder="e.g. MuSha Mel  or  TaVa Ki  or  Ga Ku"
          onChange={e => setField("akinen", e.target.value)}
          style={{ fontFamily: "monospace" }}
        />
        {f.akinen.trim() && (
          <p className="hint alchemy-akinen-tokens">
            {f.akinen.trim().split(/\s+/).map((tok, i) => (
              <code key={i} className="akinen-tok">{tok}</code>
            ))}
          </p>
        )}

        {/* Dragon Tongue organism */}
        <label>Dragon Tongue — Organism in Morphospace
          <span className="hint"> — biological description IS the definition, not metaphor</span>
        </label>
        <textarea
          rows={4}
          value={f.dragon_tongue}
          placeholder={selectedOntic ? DRAGON_TONGUE_HINTS[selectedOntic.axis] : "Select an ontic vowel first"}
          onChange={e => setField("dragon_tongue", e.target.value)}
        />

        <label>Narrative
          <span className="hint"> — lore fragment / story resonance</span>
        </label>
        <textarea
          rows={3}
          value={f.narrative}
          placeholder="The story that situates this property in time…"
          onChange={e => setField("narrative", e.target.value)}
        />

        <label>Somatic
          <span className="hint"> — sensory / embodied description; what the body recognises before the mind does</span>
        </label>
        <textarea
          rows={2}
          value={f.somatic}
          placeholder="The sensation of correct perception…"
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
              Physical materials are substrate — not cause. Use Kobra Mavo names for
              known items (e.g. <code>MavoWormwood</code>, <code>MavoMortar</code>).
              Outputs follow from correct perception of the field, not from the materials.
            </p>
            <KVEditor
              label="Required Materials"
              hint="Physical substrate needed for material outputs. Empty = purely energetic."
              listId="alchemy-materials-list"
              items={subject.required_materials}
              onChange={v => setTop("required_materials", v)}
            />
            <KVEditor
              label="Base Outputs"
              hint="Yields at resonance ≥ 0.50"
              listId="alchemy-base-list"
              items={subject.base_outputs}
              onChange={v => setTop("base_outputs", v)}
            />
            <KVEditor
              label="Enhanced Outputs"
              hint="Yields at epiphanic quality (resonance ≥ 0.85 + charge ≥ 0.70)"
              listId="alchemy-enhanced-list"
              items={subject.enhanced_outputs}
              onChange={v => setTop("enhanced_outputs", v)}
            />
          </>
        )}
      </div>

      {/* ── Stage 3: Identity & Export ─────────────────────────────── */}
      <div className={`alchemy-stage ${!substrateComplete ? "alchemy-locked" : ""}`}>
        <h3>Stage 3 — Identity &amp; Export</h3>
        {!substrateComplete && (
          <p className="hint locked">Complete substrate before exporting.</p>
        )}
        {substrateComplete && (
          <>
            <label>Display Name</label>
            <input
              value={subject.name}
              placeholder="e.g. Grief Salve, Temporal Tincture"
              onChange={e => handleNameChange(e.target.value)}
            />
            <label>Kobra ID
              <span className="hint"> — MavoName for Kobra documents</span>
            </label>
            <input
              value={subject.kobra_id}
              placeholder="e.g. MavoGriefSalve"
              onChange={e => setTop("kobra_id", e.target.value)}
              style={{ fontFamily: "monospace" }}
            />
            <label>Legacy ID
              <span className="hint"> — API / file key</span>
            </label>
            <input
              value={subject.id}
              placeholder="e.g. grief_salve"
              onChange={e => setTop("id", e.target.value)}
              style={{ fontFamily: "monospace" }}
            />
            <label>Lore</label>
            <textarea
              rows={2}
              value={subject.lore}
              placeholder="What Minerva says when she grants the formula…"
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
            <div key={s.id || s.kobra_id} className="alchemy-saved-row">
              <code>{s.kobra_id || toMavoName(s.name || "")}</code>
              <span style={{ marginLeft: 8 }}>{s.name}</span>
              <span className="hint" style={{ marginLeft: 8 }}>
                [{s.field?.properties?.[0]?.ontic || s.field?.properties?.[0]?.axis}
                {" · "}{s.field?.properties?.[0]?.akinen || s.field?.properties?.[0]?.shygazun}]
              </span>
              <button className="action" onClick={() => loadSubject(s)}>Edit</button>
              <button className="action" onClick={() => deleteSubject(s.id || s.kobra_id)}>Delete</button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
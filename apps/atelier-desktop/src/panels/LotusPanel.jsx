/**
 * LotusPanel.jsx
 * Alexi's attestation surface for lotus-gated candidates.
 * Shows pending lotus candidates from the kernel with their byte table provenance,
 * and allows explicit structured attestation via process_attestation.
 */

import React, { useState, useEffect, useCallback } from "react";

const KERNEL_BASE = "http://127.0.0.1:8000";
const FIELD_ID = "F0";

const TONGUE_COLORS = {
  Lotus:        "#d4af37",
  Rose:         "#c0516e",
  Sakura:       "#e8a0b4",
  Daisy:        "#f0d060",
  AppleBlossom: "#b85c38",
  Aster:        "#7b68c8",
  Grapevine:    "#6b8e6b",
  Cannabis:     "#4a8c4a",
};

const TONGUE_LABELS = {
  Lotus:        "Lotus — Presence & Being",
  Rose:         "Rose — Spectrum & Number",
  Sakura:       "Sakura — Orientation & Motion",
  Daisy:        "Daisy — Structure & Form",
  AppleBlossom: "AppleBlossom — Axis & Compound",
  Aster:        "Aster — Chiral Space & Time",
  Grapevine:    "Grapevine — Storage & Coordination",
  Cannabis:     "Cannabis — Conscious Projection",
};

// ---------------------------------------------------------------------------
// Styles (inline to keep the file self-contained)
// ---------------------------------------------------------------------------

const S = {
  panel: {
    padding: "28px 32px",
    fontFamily: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    color: "#e8e0d0",
    maxWidth: 860,
  },
  title: {
    margin: "0 0 6px",
    fontSize: "1.6rem",
    fontWeight: 700,
    letterSpacing: "0.02em",
    color: "#d4af37",
  },
  subtitle: {
    margin: "0 0 24px",
    fontSize: "0.9rem",
    color: "#9a9080",
    lineHeight: 1.5,
  },
  statusBar: {
    display: "flex",
    gap: 12,
    alignItems: "center",
    marginBottom: 24,
  },
  badge: (color) => ({
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 999,
    fontSize: "0.75rem",
    fontWeight: 600,
    background: color || "#3a3028",
    color: "#fff",
    letterSpacing: "0.05em",
  }),
  tongueSection: {
    marginBottom: 28,
  },
  tongueHeader: (color) => ({
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 10,
    borderBottom: `1px solid ${color}44`,
    paddingBottom: 6,
  }),
  tongueDot: (color) => ({
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: color,
    flexShrink: 0,
  }),
  tongueLabel: {
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#c8bfb0",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  card: (selected) => ({
    background: selected ? "#2a2218" : "#1c1810",
    border: `1px solid ${selected ? "#d4af37" : "#3a3028"}`,
    borderRadius: 10,
    padding: "14px 16px",
    marginBottom: 8,
    cursor: "pointer",
    transition: "border-color 0.15s",
  }),
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 4,
  },
  candidateId: {
    fontFamily: "monospace",
    fontSize: "0.85rem",
    color: "#d4af37",
    fontWeight: 600,
  },
  provenanceRow: {
    fontSize: "0.8rem",
    color: "#9a9080",
    marginTop: 4,
  },
  meaning: {
    fontSize: "0.88rem",
    color: "#b8b0a0",
    marginTop: 2,
  },
  symbol: {
    fontFamily: "monospace",
    fontSize: "1.1rem",
    color: "#e8e0d0",
    fontWeight: 700,
    marginRight: 6,
  },
  attestForm: {
    background: "#121008",
    border: "1px solid #d4af3766",
    borderRadius: 10,
    padding: "16px 18px",
    marginTop: 8,
  },
  formLabel: {
    display: "block",
    fontSize: "0.78rem",
    color: "#9a9080",
    marginBottom: 4,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  hashBox: {
    fontFamily: "monospace",
    fontSize: "0.7rem",
    color: "#6a8c6a",
    background: "#0c1008",
    border: "1px solid #2a3a2a",
    borderRadius: 6,
    padding: "8px 10px",
    wordBreak: "break-all",
    marginBottom: 14,
    lineHeight: 1.5,
  },
  button: (variant) => ({
    padding: "8px 18px",
    borderRadius: 7,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.85rem",
    background: variant === "primary" ? "#d4af37" : variant === "danger" ? "#8c2a2a" : "#3a3028",
    color: variant === "primary" ? "#1a1208" : "#e8e0d0",
    marginRight: 8,
    transition: "opacity 0.1s",
  }),
  resultBox: (ok) => ({
    background: ok ? "#0c1808" : "#180808",
    border: `1px solid ${ok ? "#4a8c4a" : "#8c2a2a"}`,
    borderRadius: 8,
    padding: "10px 14px",
    marginTop: 12,
    fontSize: "0.82rem",
    color: ok ? "#8adc8a" : "#dc8a8a",
    fontFamily: "monospace",
  }),
  emptyState: {
    padding: "40px 24px",
    textAlign: "center",
    color: "#6a6058",
    fontSize: "0.95rem",
  },
  errorState: {
    color: "#dc8a8a",
    fontSize: "0.85rem",
    padding: "12px 0",
  },
  refreshBtn: {
    background: "none",
    border: "1px solid #3a3028",
    color: "#9a9080",
    borderRadius: 7,
    padding: "5px 12px",
    cursor: "pointer",
    fontSize: "0.8rem",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByTongue(pending) {
  const groups = {};
  for (const c of pending) {
    const tongue = c.tongue || "Unknown";
    if (!groups[tongue]) groups[tongue] = [];
    groups[tongue].push(c);
  }
  return groups;
}

function provenanceSummary(prov) {
  if (!prov || prov.length === 0) return null;
  const p = prov[0];
  return { symbol: p.symbol, decimal: p.decimal, meaning: p.meaning };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CandidateCard({ candidate, onSelect, selected }) {
  const prov = provenanceSummary(candidate.provenance);
  const color = TONGUE_COLORS[candidate.tongue] || "#9a9080";

  return (
    <div style={S.card(selected)} onClick={() => onSelect(selected ? null : candidate)}>
      <div style={S.cardHeader}>
        <div>
          {prov && <span style={S.symbol}>{prov.symbol}</span>}
          <span style={S.candidateId}>{candidate.candidate_id}</span>
        </div>
        {prov && (
          <span style={S.badge(color + "99")}>byte {prov.decimal}</span>
        )}
      </div>
      {prov && <div style={S.meaning}>{prov.meaning}</div>}
      <div style={S.provenanceRow}>
        tag: <span style={{ fontFamily: "monospace", color: "#c8bfb0" }}>{candidate.attestation_tag}</span>
      </div>
    </div>
  );
}

function AttestForm({ candidate, onDismiss, onSuccess }) {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  async function submit() {
    setSubmitting(true);
    setResult(null);
    try {
      const resp = await fetch(`${KERNEL_BASE}/v0.1/attest/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          frontier_id: candidate.frontier_id,
          candidate_id: candidate.candidate_id,
          agent_id: "alexi",
          intent_hash: candidate.intent_hash,
        }),
      });
      const data = await resp.json();
      setResult(data);
      if (data.accepted) {
        onSuccess(candidate.candidate_id, data);
      }
    } catch (err) {
      setResult({ accepted: false, refusal: { reason: String(err) } });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={S.attestForm}>
      <label style={S.formLabel}>Intent hash (structural commitment)</label>
      <div style={S.hashBox}>{candidate.intent_hash}</div>

      <label style={S.formLabel}>Candidate</label>
      <div style={{ ...S.hashBox, fontSize: "0.78rem", color: "#d4af37" }}>
        {candidate.candidate_id}
        {candidate.frontier_id && (
          <span style={{ color: "#6a6058" }}> @ frontier {candidate.frontier_id}</span>
        )}
      </div>

      {result ? (
        <div style={S.resultBox(result.accepted)}>
          {result.accepted
            ? `Attested. Event: ${result.event?.id || "recorded"}`
            : `Refused: ${result.refusal?.reason || "unknown"}`}
        </div>
      ) : null}

      {!result?.accepted && (
        <div style={{ marginTop: 12 }}>
          <button
            style={S.button("primary")}
            onClick={submit}
            disabled={submitting}
          >
            {submitting ? "Submitting…" : "Attest"}
          </button>
          <button style={S.button()} onClick={onDismiss}>
            Cancel
          </button>
        </div>
      )}
      {result?.accepted && (
        <button style={{ ...S.button(), marginTop: 12 }} onClick={onDismiss}>
          Close
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function LotusPanel() {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [clock, setClock] = useState(null);
  const [selected, setSelected] = useState(null);
  const [attested, setAttested] = useState(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${KERNEL_BASE}/v0.1/field/${FIELD_ID}/lotus-pending`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setPending(data.lotus_pending || []);
      setClock(data.clock);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function handleSuccess(candidateId) {
    setAttested((prev) => new Set([...prev, candidateId]));
    setSelected(null);
    // Reload after short delay so kernel can process
    setTimeout(load, 600);
  }

  const visible = pending.filter((c) => !attested.has(c.candidate_id));
  const groups = groupByTongue(visible);
  const tongueOrder = ["Lotus", "Cannabis", "AppleBlossom", "Aster", "Sakura", "Rose", "Daisy", "Grapevine"];

  return (
    <div style={S.panel}>
      <h2 style={S.title}>Lotus Gate</h2>
      <p style={S.subtitle}>
        Candidates below require your explicit attestation to become eligible.
        Each commitment binds the structural hash of the candidate to your authorial presence.
      </p>

      <div style={S.statusBar}>
        <span style={S.badge("#d4af37aa")}>
          {visible.length} pending
        </span>
        {attested.size > 0 && (
          <span style={S.badge("#4a8c4aaa")}>
            {attested.size} attested this session
          </span>
        )}
        {clock && (
          <span style={S.badge()}>
            tick {clock.tick}
          </span>
        )}
        <button style={S.refreshBtn} onClick={load} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <div style={S.errorState}>Error: {error}</div>}

      {!loading && !error && visible.length === 0 && (
        <div style={S.emptyState}>
          No lotus-gated candidates pending.
          {attested.size > 0 && <div style={{ marginTop: 8, color: "#4a8c4a" }}>All attested this session.</div>}
        </div>
      )}

      {tongueOrder
        .filter((tongue) => groups[tongue]?.length > 0)
        .map((tongue) => {
          const color = TONGUE_COLORS[tongue] || "#9a9080";
          const label = TONGUE_LABELS[tongue] || tongue;
          return (
            <div key={tongue} style={S.tongueSection}>
              <div style={S.tongueHeader(color)}>
                <div style={S.tongueDot(color)} />
                <span style={S.tongueLabel}>{label}</span>
                <span style={S.badge(color + "66")}>{groups[tongue].length}</span>
              </div>
              {groups[tongue].map((c) => (
                <React.Fragment key={c.candidate_id}>
                  <CandidateCard
                    candidate={c}
                    selected={selected?.candidate_id === c.candidate_id}
                    onSelect={setSelected}
                  />
                  {selected?.candidate_id === c.candidate_id && (
                    <AttestForm
                      candidate={c}
                      onDismiss={() => setSelected(null)}
                      onSuccess={handleSuccess}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          );
        })}

      {/* Remaining tongues not in the canonical order */}
      {Object.keys(groups)
        .filter((t) => !tongueOrder.includes(t))
        .map((tongue) => {
          const color = TONGUE_COLORS[tongue] || "#9a9080";
          return (
            <div key={tongue} style={S.tongueSection}>
              <div style={S.tongueHeader(color)}>
                <div style={S.tongueDot(color)} />
                <span style={S.tongueLabel}>{tongue}</span>
                <span style={S.badge(color + "66")}>{groups[tongue].length}</span>
              </div>
              {groups[tongue].map((c) => (
                <React.Fragment key={c.candidate_id}>
                  <CandidateCard
                    candidate={c}
                    selected={selected?.candidate_id === c.candidate_id}
                    onSelect={setSelected}
                  />
                  {selected?.candidate_id === c.candidate_id && (
                    <AttestForm
                      candidate={c}
                      onDismiss={() => setSelected(null)}
                      onSuccess={handleSuccess}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          );
        })}
    </div>
  );
}

export default LotusPanel;

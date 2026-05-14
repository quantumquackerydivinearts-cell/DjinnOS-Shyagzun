import React from 'react';

const MODES = [
  { id: 'giann',    label: 'Giann',    desc: 'Deterministic completion' },
  { id: 'keshi',    label: 'Keshi',    desc: 'Temperature-driven exploration' },
  { id: 'drovitth', label: 'Drovitth', desc: 'Temporal gate' },
  { id: 'saelith',  label: 'Saelith',  desc: 'Conditional predicate' },
];

export function TemperatureSelector({ value = 'giann', onChange, temp = 1.5, onTempChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <span className="s-label">Djinn Mode</span>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {MODES.map(m => (
          <button key={m.id} onClick={() => onChange?.(m.id)} title={m.desc} style={{
            background: value === m.id ? 'rgba(233,30,150,0.18)' : 'rgba(58,10,42,0.6)',
            border: value === m.id ? 'var(--border-magenta)' : 'var(--border-plum)',
            borderRadius: 'var(--radius-sm)',
            color: value === m.id ? 'var(--magenta-primary)' : 'var(--text-muted)',
            fontSize: 12, fontWeight: value === m.id ? 700 : 400,
            padding: '5px 12px', cursor: 'pointer',
            boxShadow: value === m.id ? 'var(--glow-magenta)' : 'none',
            transition: 'all var(--transition-fast)',
          }}>
            {m.label}
          </button>
        ))}
      </div>
      {value === 'keshi' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 60 }}>
            T = {Number(temp).toFixed(1)}
          </span>
          <input
            type="range" min="0.1" max="5" step="0.1"
            value={temp}
            onChange={e => onTempChange?.(parseFloat(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--magenta-primary)' }}
          />
        </div>
      )}
    </div>
  );
}

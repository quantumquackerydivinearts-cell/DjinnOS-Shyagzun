import React from 'react';

/**
 * EntropyMeter — QQEES entropy contribution gauge for an active session.
 * Shows accumulated entropy ticks as a filling magenta bar with gold sparkle
 * at high levels.
 *
 * Props:
 *   value   : 0–1 float (current entropy fraction)
 *   ticks   : integer count of ticks emitted this session
 *   certified: boolean — true when H ≥ 7.5 (certified threshold)
 */
export function EntropyMeter({ value = 0, ticks = 0, certified = false }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  const barColor = certified
    ? 'linear-gradient(90deg, var(--magenta-primary), var(--gold-alchemical))'
    : 'linear-gradient(90deg, var(--pink-deep), var(--magenta-primary))';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Entropy
        </span>
        <span style={{
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          color: certified ? 'var(--gold-alchemical)' : 'var(--pink-bubble)',
        }}>
          {ticks} tick{ticks !== 1 ? 's' : ''}
          {certified && ' ✦ certified'}
        </span>
      </div>
      <div style={{
        height: 6, background: 'rgba(58,10,42,0.6)',
        borderRadius: 3, overflow: 'hidden',
        border: certified ? '1px solid rgba(212,175,55,0.3)' : '1px solid rgba(233,30,150,0.15)',
        boxShadow: certified ? 'var(--glow-gold)' : 'none',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: barColor,
          transition: 'width 0.6s ease',
          borderRadius: 3,
        }} />
      </div>
    </div>
  );
}

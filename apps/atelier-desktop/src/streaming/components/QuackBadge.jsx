import React from 'react';

/** Gold badge shown when a session is Quack-eligible. */
export function QuackBadge({ count = 1, style }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: 'rgba(212,175,55,0.15)',
      border: '1px solid var(--gold-alchemical)',
      borderRadius: 'var(--radius-sm)',
      padding: '3px 10px',
      fontSize: 12, fontWeight: 600,
      color: 'var(--gold-alchemical)',
      boxShadow: 'var(--glow-gold)',
      ...style,
    }}>
      ✦ {count === 1 ? 'Quack Eligible' : `${count} Quacks`}
    </span>
  );
}

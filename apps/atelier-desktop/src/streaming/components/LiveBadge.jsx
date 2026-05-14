import React from 'react';

export function LiveBadge({ live = false, viewers = 0 }) {
  if (!live) return (
    <span style={{
      fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
      color: 'var(--text-muted)', textTransform: 'uppercase',
    }}>offline</span>
  );
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span className="s-live-dot" />
      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--magenta-primary)', letterSpacing: '0.06em' }}>
        LIVE
      </span>
      {viewers > 0 && (
        <span style={{ fontSize: 11, color: 'var(--pink-bubble)' }}>
          {viewers} witness{viewers !== 1 ? 'es' : ''}
        </span>
      )}
    </span>
  );
}

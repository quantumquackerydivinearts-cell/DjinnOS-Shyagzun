import React from 'react';

/**
 * ResonanceMarker — timestamped attestation dropped by a witness during a stream.
 * Carries the viewer's BoK position at the moment of attestation.
 */
export function ResonanceMarker({ marker, style }) {
  const { artisan_id, ts, bok, note } = marker || {};
  const t = ts ? new Date(ts * 1000).toLocaleTimeString() : '';
  return (
    <div style={{
      display: 'flex', gap: 10, alignItems: 'flex-start',
      padding: '8px 12px',
      background: 'rgba(58,10,42,0.4)',
      border: '1px solid rgba(212,175,55,0.2)',
      borderRadius: 'var(--radius-sm)',
      ...style,
    }}>
      <span style={{ color: 'var(--gold-alchemical)', fontSize: 14, marginTop: 1 }}>◈</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--pink-bubble)', fontWeight: 600 }}>
            {artisan_id || 'witness'}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
            {t}
          </span>
        </div>
        {bok && (
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            c = {bok}
          </div>
        )}
        {note && <div style={{ fontSize: 12, color: 'var(--text-body)', marginTop: 4 }}>{note}</div>}
      </div>
    </div>
  );
}

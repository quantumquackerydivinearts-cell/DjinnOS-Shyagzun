import React from 'react';

/**
 * MetadataChip — byte-table coordinate or tongue label chip.
 * gold=true for the active/highlighted variant (rare).
 */
export function MetadataChip({ label, value, gold = false, style }) {
  return (
    <span style={{
      display:      'inline-flex',
      alignItems:   'center',
      gap:          4,
      background:   gold ? 'rgba(212,175,55,0.12)' : 'rgba(58,10,42,0.8)',
      border:       gold ? '1px solid var(--gold-alchemical)' : 'var(--border-plum)',
      borderRadius: 'var(--radius-sm)',
      padding:      '2px 8px',
      fontSize:     11,
      fontFamily:   'var(--font-mono)',
      color:        gold ? 'var(--gold-alchemical)' : 'var(--pink-bubble)',
      ...style,
    }}>
      {label && <span style={{ color: 'var(--text-muted)', marginRight: 2 }}>{label}</span>}
      {value}
    </span>
  );
}

import React from 'react';

export function Button({ children, onClick, variant = 'primary', disabled, style, size = 'md' }) {
  const cls = `s-btn s-btn-${variant}`;
  const sz  = size === 'sm'
    ? { fontSize: 11, padding: '5px 12px' }
    : size === 'lg'
    ? { fontSize: 15, padding: '11px 24px' }
    : {};
  return (
    <button
      className={cls}
      onClick={onClick}
      disabled={disabled}
      style={{ opacity: disabled ? 0.4 : 1, cursor: disabled ? 'default' : 'pointer', ...sz, ...style }}
    >
      {children}
    </button>
  );
}

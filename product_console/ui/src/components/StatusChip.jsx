import React from 'react'

/** Status chip with dark theme colors and text labels. */
const STYLES = {
  success: { background: '#10251a', color: '#8df0a4', border: '1px solid #1f5b36' },
  degraded: { background: '#2a1c0b', color: '#ffb454', border: '1px solid #6b3f16' },
  failed: { background: '#2b1111', color: '#ff6b6b', border: '1px solid #6d2a2a' },
  blocked: { background: '#2a1020', color: '#f2a2d4', border: '1px solid #5b2743' },
  paused: { background: '#0f1c2c', color: '#7ab8ff', border: '1px solid #294466' },
  active: { background: '#10251a', color: '#8df0a4', border: '1px solid #1f5b36' },
}

export default function StatusChip({ status, label }) {
  const key = (status || '').toLowerCase()
  const style = STYLES[key] || { background: '#1a1f29', color: '#9aa3b2', border: '1px solid var(--border)' }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: 0.2,
        ...style,
      }}
      title={label || status}
    >
      {label || status || '—'}
    </span>
  )
}



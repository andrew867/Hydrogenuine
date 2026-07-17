import React from 'react'

export default function Breadcrumbs({ items = [] }) {
  if (!Array.isArray(items) || items.length === 0) return null
  return (
    <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--muted)' }}>
      {items.map((item, idx) => (
        <span key={`${item.label}-${idx}`}>
          {item.href ? <a href={item.href}>{item.label}</a> : item.label}
          {idx < items.length - 1 ? ' / ' : ''}
        </span>
      ))}
    </div>
  )
}

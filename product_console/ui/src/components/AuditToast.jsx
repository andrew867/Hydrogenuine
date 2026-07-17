import React, { useEffect } from 'react'

export default function AuditToast({ message, tone = 'success', onDismiss }) {
  useEffect(() => {
    if (!message) return undefined
    const timer = window.setTimeout(() => onDismiss?.(), 5000)
    return () => window.clearTimeout(timer)
  }, [message, onDismiss])

  if (!message) return null

  const background = tone === 'danger' ? 'var(--danger)' : 'var(--ok, #1f6f4a)'

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="product-audit-toast"
      style={{
        position: 'fixed',
        right: 16,
        bottom: 16,
        zIndex: 1200,
        background,
        color: '#fff',
        padding: '12px 16px',
        borderRadius: 10,
        maxWidth: 420,
        boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
      }}
    >
      {message}
    </div>
  )
}

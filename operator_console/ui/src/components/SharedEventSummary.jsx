import React from 'react'

const TONE_STYLES = {
  neutral: { color: 'var(--muted)', background: 'rgba(255, 255, 255, 0.06)' },
  good: { color: 'var(--success)', background: 'rgba(86, 204, 142, 0.12)' },
  warn: { color: 'var(--warn)', background: 'rgba(255, 193, 92, 0.14)' },
  danger: { color: 'var(--danger)', background: 'rgba(255, 112, 112, 0.12)' },
  info: { color: 'var(--link)', background: 'rgba(108, 197, 255, 0.12)' },
}

function normalizeText(value) {
  if (value == null) return '—'
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed || '—'
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return value
}

function TonePill({ tone, label }) {
  const style = TONE_STYLES[tone] || TONE_STYLES.neutral
  return (
    <span
      style={{
        ...style,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
      data-testid="shared-event-summary-status"
    >
      {label}
    </span>
  )
}

function SummaryField({ label, value, dataTestId }) {
  return (
    <div className="card" data-testid={dataTestId}>
      <div className="eyebrow">{label}</div>
      <div style={{ marginTop: 6, lineHeight: 1.45 }}>{normalizeText(value)}</div>
    </div>
  )
}

function ContextItem({ item }) {
  const label = item?.label || ''
  const value = normalizeText(item?.value ?? item?.label)
  const content = item?.href ? (
    <a href={item.href} className="nav-link">
      {value}
    </a>
  ) : (
    <span>{value}</span>
  )

  return (
    <div className="card" style={{ padding: '10px 12px' }}>
      <div className="eyebrow" style={{ marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 13 }}>{content}</div>
    </div>
  )
}

export default function SharedEventSummary({
  eyebrow = 'One-brain spine',
  title = 'What this is',
  intro = '',
  status = '',
  statusTone = 'neutral',
  happened = '',
  when = '',
  why = '',
  changed = '',
  next = '',
  context = [],
  actions = null,
}) {
  const fields = [
    { label: 'What happened', value: happened, testId: 'shared-event-summary-happened' },
    { label: 'When', value: when, testId: 'shared-event-summary-when' },
    { label: 'Why', value: why, testId: 'shared-event-summary-why' },
    { label: 'What changed', value: changed, testId: 'shared-event-summary-changed' },
    { label: 'What next', value: next, testId: 'shared-event-summary-next' },
  ]

  return (
    <section className="section-card" style={{ marginBottom: 16 }} data-testid="shared-event-summary">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0, flex: '1 1 420px' }}>
          <div className="eyebrow">{eyebrow}</div>
          <h2 style={{ margin: '6px 0 8px' }}>{title}</h2>
          {intro ? <p className="muted" style={{ margin: 0, maxWidth: 900 }}>{intro}</p> : null}
        </div>
        {status ? <TonePill tone={statusTone} label={status} /> : null}
      </div>

      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginTop: 16 }}>
        {fields.map((field) => (
          <SummaryField key={field.label} label={field.label} value={field.value} dataTestId={field.testId} />
        ))}
      </div>

      {Array.isArray(context) && context.length > 0 ? (
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', marginTop: 12 }} data-testid="shared-event-summary-context">
          {context.map((item, idx) => (
            <ContextItem key={`${item?.label || 'context'}-${idx}`} item={item} />
          ))}
        </div>
      ) : null}

      {actions ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }} data-testid="shared-event-summary-actions">
          {actions}
        </div>
      ) : null}
    </section>
  )
}

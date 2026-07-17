import React from 'react'
import { PageSkeleton, ErrorState, EmptyState, Banner } from 'hg_ui_kit'

function isLoadingTitle(title) {
  return typeof title === 'string' && /^loading\b/i.test(title.trim())
}

function isEmptyTitle(title) {
  if (typeof title !== 'string') return false
  return /^(no |queue empty|nothing |empty)/i.test(title.trim())
}

export default function StateNotice({ title, detail, tone = 'muted', action = null, loading = false }) {
  const body = detail || ''
  if (loading || isLoadingTitle(title)) {
    return <PageSkeleton label={body || title} />
  }
  if (tone === 'danger') {
    return (
      <div style={{ marginBottom: 16 }}>
        <ErrorState title={title} message={body || title} onRetry={action ? () => action.props?.onClick?.() : undefined} />
        {action && !action.props?.onClick ? <div style={{ marginTop: 8 }}>{action}</div> : null}
      </div>
    )
  }
  if (tone === 'muted' && isEmptyTitle(title)) {
    return (
      <div style={{ marginBottom: 16 }}>
        <EmptyState title={title} description={body || 'No records to show yet.'} />
        {action ? <div style={{ marginTop: 8 }}>{action}</div> : null}
      </div>
    )
  }
  return (
    <div style={{ marginBottom: 16 }}>
      <Banner tone={tone === 'success' ? 'ok' : tone === 'warn' ? 'warning' : 'info'}>
        <div style={{ fontWeight: 600, marginBottom: body || action ? 6 : 0 }}>{title}</div>
        {body ? <div style={{ fontSize: 13, lineHeight: 1.5 }}>{body}</div> : null}
        {action ? <div style={{ marginTop: 10 }}>{action}</div> : null}
      </Banner>
    </div>
  )
}

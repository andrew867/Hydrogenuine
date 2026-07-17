import React from 'react'
import StatusChip from '../../components/StatusChip.jsx'

export default function LiveGrid({ entities, selectedIds, onToggleSelect, onOpenBlocked }) {
  if (!entities.length) {
    return (
      <p style={{ color: 'var(--muted)' }}>No entities registered in the job registry yet.</p>
    )
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 12,
      }}
      data-testid="ops-live-grid"
    >
      {entities.map((entity) => {
        const entityId = entity.entity_id || entity.id
        const selected = selectedIds.has(entityId)
        const status = entity.status || (entity.has_decisions ? 'active' : 'idle')
        return (
          <article
            key={entityId}
            style={{
              border: selected ? '1px solid var(--accent)' : '1px solid var(--border)',
              borderRadius: 12,
              padding: 12,
              background: 'var(--panel)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <strong style={{ fontSize: 14 }}>{entityId}</strong>
              <StatusChip status={status} label={status} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>
              <div>Decisions: {entity.decisions_count ?? entity.has_decisions ? 'yes' : 'no'}</div>
              <div>Last activity: {entity.last_activity || 'n/a'}</div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => onToggleSelect(entityId)}
                />
                Batch
              </label>
              <a href={`#/entities/${encodeURIComponent(entityId)}`} style={{ fontSize: 12 }}>
                Open entity
              </a>
              <button type="button" style={{ fontSize: 12 }} onClick={() => onOpenBlocked(entityId)}>
                Why blocked?
              </button>
            </div>
          </article>
        )
      })}
    </div>
  )
}

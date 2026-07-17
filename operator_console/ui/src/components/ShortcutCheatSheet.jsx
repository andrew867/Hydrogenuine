import React from 'react'
import { Modal } from 'hg_ui_kit'
import { OPERATOR_SHORTCUTS } from '../lib/shortcuts.js'

export default function ShortcutCheatSheet({ open, onClose }) {
  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ padding: 16 }} data-testid="operator-shortcut-sheet">
        <h2 style={{ marginTop: 0 }}>Keyboard shortcuts</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {OPERATOR_SHORTCUTS.map((row) => (
            <li key={row.sequence} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
              <span>{row.label}</span>
              <code>{row.sequence}</code>
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  )
}

export const OPERATOR_SHORTCUTS = [
  { sequence: 'g r', label: 'Go to Runs', href: '#/' },
  { sequence: 'g a', label: 'Go to Approvals', href: '#/approvals' },
  { sequence: 'g h', label: 'Go to Operations Home', href: '#/home' },
  { sequence: '?', label: 'Show keyboard shortcuts', action: 'cheat-sheet' },
]

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export function shouldIgnoreShortcut(target) {
  if (!target) return false
  const el = target
  if (INPUT_TAGS.has(el.tagName)) return true
  if (el.isContentEditable) return true
  return false
}

export function createShortcutController({ onCheatSheet, navigate }) {
  let pending = ''

  const resetLater = () => {
    window.setTimeout(() => {
      pending = ''
    }, 1200)
  }

  return (event) => {
    if (shouldIgnoreShortcut(event.target)) return
    if (event.key === '?') {
      event.preventDefault()
      onCheatSheet?.()
      return
    }
    if (event.key.length !== 1) return
    pending = `${pending} ${event.key}`.trim()
    resetLater()
    if (pending === 'g r') {
      event.preventDefault()
      navigate('/')
      pending = ''
    } else if (pending === 'g a') {
      event.preventDefault()
      navigate('/approvals')
      pending = ''
    } else if (pending === 'g h') {
      event.preventDefault()
      navigate('/home')
      pending = ''
    }
  }
}

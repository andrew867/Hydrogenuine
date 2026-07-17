export type RouteCrumb = {
  label: string
  href: string
}

function normalizePath(pathname: string | null | undefined): string {
  const text = String(pathname || '/').trim()
  return text || '/'
}

function topLevelLabel(pathname: string): string {
  if (pathname === '/') return 'Home'
  if (pathname.startsWith('/chat/')) return 'Chat'
  if (pathname.startsWith('/research/')) return 'Research'
  if (pathname.startsWith('/swarm/')) return 'Swarm run'
  if (pathname.startsWith('/principals/')) return 'Principal'
  if (pathname.startsWith('/entities/')) return 'Entity'
  if (pathname.startsWith('/operational-personas')) return 'Operational identities'
  if (pathname.startsWith('/approvals')) return 'Approvals'
  if (pathname.startsWith('/settings')) return 'Settings'
  if (pathname.startsWith('/admin/audit')) return 'Audit log'
  if (pathname.startsWith('/admin')) return 'Admin'
  if (pathname.startsWith('/system')) return 'System'
  if (pathname.startsWith('/status')) return 'Status console'
  if (pathname.startsWith('/proofs')) return 'Proof runs'
  if (pathname.startsWith('/social')) return 'Social ops'
  if (pathname.startsWith('/content')) return 'Content CMS'
  if (pathname.startsWith('/timeline')) return 'Event timeline'
  if (pathname.startsWith('/governance')) return 'Governance'
  if (pathname.startsWith('/tenantadmin')) return 'Tenant admin'
  if (pathname.startsWith('/superadmin')) return 'Superadmin'
  if (pathname.startsWith('/artifacts')) return 'Artifact registry'
  if (pathname.startsWith('/source-registry')) return 'Source registry'
  if (pathname.startsWith('/executables')) return 'Executable registry'
  if (pathname.startsWith('/task-registry')) return 'Task registry'
  return pathname.replace(/^\//, '').replace(/-/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase()) || 'Home'
}

export function getRouteLabel(pathname: string | null | undefined): string {
  const normalized = normalizePath(pathname)
  return topLevelLabel(normalized)
}

export function getRouteCrumbs(pathname: string | null | undefined): RouteCrumb[] {
  const normalized = normalizePath(pathname)
  if (normalized === '/') {
    return [{ label: 'Home', href: '/' }]
  }
  if (normalized.startsWith('/chat/')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Chats', href: '/' },
      { label: 'Chat', href: normalized },
    ]
  }
  if (normalized.startsWith('/research/')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Research', href: '/research' },
      { label: 'Thread', href: normalized },
    ]
  }
  if (normalized.startsWith('/swarm/')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Swarms', href: '/swarm' },
      { label: 'Run', href: normalized },
    ]
  }
  if (normalized.startsWith('/principals/')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Principals', href: '/principals' },
      { label: 'Principal', href: normalized },
    ]
  }
  if (normalized.startsWith('/entities/')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Entities', href: '/entities' },
      { label: 'Entity', href: normalized },
    ]
  }
  if (normalized.startsWith('/operational-personas')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Operational identities', href: '/operational-personas' },
    ]
  }
  if (normalized.startsWith('/approvals')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Approvals', href: '/approvals' },
    ]
  }
  if (normalized.startsWith('/settings')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Settings', href: '/settings' },
    ]
  }
  if (normalized.startsWith('/admin')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Admin', href: '/admin' },
    ]
  }
  if (normalized.startsWith('/status')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Status console', href: '/status' },
    ]
  }
  if (normalized.startsWith('/proofs')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Proof runs', href: '/proofs' },
    ]
  }
  if (normalized.startsWith('/social')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Social ops', href: '/social' },
    ]
  }
  if (normalized.startsWith('/content')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Content CMS', href: '/content' },
    ]
  }
  if (normalized.startsWith('/timeline')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Event timeline', href: '/timeline' },
    ]
  }
  if (normalized.startsWith('/governance')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Governance', href: '/governance' },
    ]
  }
  if (normalized.startsWith('/tenantadmin')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Tenant admin', href: '/tenantadmin' },
    ]
  }
  if (normalized.startsWith('/superadmin')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Superadmin', href: '/superadmin' },
    ]
  }
  if (normalized.startsWith('/artifacts')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Artifact registry', href: '/artifacts' },
    ]
  }
  if (normalized.startsWith('/source-registry')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Source registry', href: '/source-registry' },
    ]
  }
  if (normalized.startsWith('/executables')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Executable registry', href: '/executables' },
    ]
  }
  if (normalized.startsWith('/task-registry')) {
    return [
      { label: 'Home', href: '/' },
      { label: 'Task registry', href: '/task-registry' },
    ]
  }
  return [
    { label: 'Home', href: '/' },
    { label: topLevelLabel(normalized), href: normalized },
  ]
}

export function isDiagnosticsRoute(pathname: string | null | undefined): boolean {
  const normalized = normalizePath(pathname)
  return [
    '/status',
    '/proofs',
    '/social',
    '/content',
    '/timeline',
    '/governance',
    '/tenantadmin',
    '/superadmin',
    '/artifacts',
    '/source-registry',
    '/executables',
    '/task-registry',
    '/admin',
  ].some((prefix) => normalized.startsWith(prefix))
}

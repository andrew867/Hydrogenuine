export const PRODUCT_ROUTE_MANIFEST = [
  { path: '/login', page: 'login', public: true, title: 'Login' },
  { path: '/', page: 'dashboard', title: 'Dashboard' },
  { path: '/templates', page: 'templates', title: 'Templates' },
  { path: '/workflows', page: 'workflows', title: 'Workflows' },
  { path: '/workflows/:wfId', page: 'workflowDetail', title: 'Workflow detail' },
  { path: '/runs', page: 'runs', title: 'Runs' },
  { path: '/runs/:runId', page: 'runDetail', title: 'Run detail' },
  { path: '/approvals', page: 'approvals', title: 'Approvals' },
  { path: '/dead-letter', page: 'deadLetter', title: 'Dead letter' },
  { path: '/profile', page: 'profile', title: 'Profile' },
  { path: '/system', page: 'system', title: 'System' },
]

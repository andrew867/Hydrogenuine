# UX microcopy (U0)

| Surface | State | Copy |
|---|---|---|
| Error | default | `{what failed}. {why}. Next: {action}. Request ID: {id}` |
| Empty | list | `Nothing here yet. {what would appear}.` CTA: `{primary action}` |
| Destructive confirm | typed | `Type {PHRASE} to confirm. This affects {blast radius}.` |
| Session | expiry warning | `Your session expires in {minutes} minutes. Extend or save work.` |
| Toast | success | `{action completed}. Action ID: {id}` |

Components `EmptyState`, `ErrorState`, and `ConfirmDialog` use these patterns.

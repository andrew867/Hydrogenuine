# Operator feature-folder decomposition (U6)

U6 establishes `src/features/` for operator deep work. Completed in this tranche:

| Feature | Status | Notes |
|---------|--------|-------|
| `ops-live/` | **Done** | LiveGrid, WhyBlockedPanel, BatchOpsBar, `useOpsLiveData` → `OpsLivePage` |
| `runs/` | **Done** | `useRunsData`, `RunsDataTable` with kit URL-state |
| `approvals/` | **Seed** | `useApprovalsQueue` hook extracted; `ApprovalsPage.jsx` migration deferred (1025 LOC) |
| `entity-detail/` | Planned | Target: panels from `Entities.jsx` / `EntityDetail` route |
| `operational-personas/` | Planned | Target: `OperationalPersonasPage.jsx` |
| `knowledge/` | Planned | Target: `Knowledge.jsx` |
| `workflows/` | Planned | Target: `WorkflowsPage.jsx` |
| `run-detail/` | Planned | Target: `RunDetail.jsx` |

Pages above 400 LOC retain monolith shells until a follow-up tranche splits panels without behavior change. Rationale: U6 prioritized live ops wiring, global search, URL-state lists, and product/client completion per execution order.

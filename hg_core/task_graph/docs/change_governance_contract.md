# Change governance contract (Autonomy Ch1 Phase 3)

Contract for G1 (proposal format), G2 (static validation), G3 (shadow/canary), G4 (rollback), G5 (audit trail). No system-initiated change affects side effects without validation + canary + recorded approval.

## G1. Proposal format

A proposal must include:

- **proposal_id**, **created_at**, **originating_run_id**
- **scope:** single_workflow | shared_component
- **risk_level:** low | medium | high
- **rationale:** problem statement, evidence pointers (run traces, metrics)
- **change description:** high-level what changes
- **validation_plan**, **rollback_plan**

See [CHANGE_PROPOSAL_TEMPLATE](.cursor/plans/autonomy/chapter1/templates/CHANGE_PROPOSAL_TEMPLATE.md).

## G2. Static validation

Before a proposal can be applied:

- Schema validation (required fields, types).
- Allowed node types only (no unknown node types).
- Token/cost caps enforced.
- No new tools/destinations without explicit operator enablement.

**Acceptance:** Invalid or disallowed proposals are rejected before apply.

## G3. Canary and shadow mode

For changes affecting side effects:

- Run in **shadow mode** first: produce outputs but do not execute external writes.
- Compare against baseline metrics and outputs.
- Only then enable for limited percentage of runs (canary).

**Acceptance:** No side effects until shadow/canary passes and approval recorded.

## G4. Rollback

- Maintain **last known good** configuration per scope.
- Rollback must be **one-step** and tested (single command or API call restores previous state).

**Acceptance:** Rollback drill: apply change then one-step rollback; state restored.

## G5. Audit trail

Every applied change records:

- Who/what approved it
- When it was applied
- Canary results
- Rollback ability verified

**Acceptance:** Audit trail queryable for compliance and debugging.

# Safety and permissions contract (Autonomy Ch1 Phase 2)

Contract for S1 (capability model), S2 (outbound safety gate), S3 (approval tiers), and S5 (policy regression tests). Executor denies undeclared scopes; outbound actions pass through safety gate; high-risk actions use approval tiers; tests assert policy invariants.

## S1. Capability model per workflow

Each workflow declares (in workflow declaration or task spec):

- **read_scopes:** Paths or categories allowed for read (no raw globbing).
- **write_scopes:** Paths or categories allowed for write.
- **allowed_destinations:** External destinations (e.g. twitter, mastodon) allowed for side effects.
- **allowed_tools:** Tool/action names allowed.

Executor (or runner) must **deny** any read/write/destination/tool not declared. Least-privilege: default deny.

**Acceptance:** Request with undeclared scope or destination is denied at runtime.

See [PER_TASK_CAPABILITIES](docs/automation/PER_TASK_CAPABILITIES.md) and [WORKFLOW_DECLARATION_TEMPLATE](.cursor/plans/autonomy/chapter1/templates/WORKFLOW_DECLARATION_TEMPLATE.md).

## S2. Safety gate for outbound actions

Before any external write (post, send, etc.):

- **Content checks:** Policy + basic PII/claims/harassment filters. See [OUTBOUND_SAFETY_GATE](docs/automation/OUTBOUND_SAFETY_GATE.md) and [hg_core.safety_gate](hg_core/safety_gate.py).
- **Action checks:** Rate limit, destination lock, approval requirement (by tier).
- If blocked: record `safety_blocked` with reasons; **do not attempt** the external call.

**Acceptance:** Safety-blocked action never triggers external call; trace shows safety_blocked.

## S3. Approval tiers

- **Tier 0:** No approval needed (low risk).
- **Tier 1:** Approval required (sensitive topics/destinations).
- **Tier 2:** Always manual (high risk).

Approval request must include: proposed action, content summary, evidence trail pointer, what will happen on approve/deny.

**Acceptance:** Tiered approvals are logged; high-risk actions require approval before execution.

## S5. Policy regression tests

Tests must assert:

- Blocked categories remain blocked when gate is ON.
- High-risk actions require approvals (tier >= 1).
- Least-privilege: undeclared scopes/destinations are denied.

**Acceptance:** Policy regression suite passes; changes to rules or capabilities are validated by tests.

# Ownership as Leased Capability: Async-Safe Delegation, Approval Routing, and Contention Resolution

This pack fixes async delegation ambiguity by introducing:
- explicit ownership state machine
- two-phase baton pass (offer/accept)
- ownership leases (TTL) plus renewal
- deterministic escalation when approver is unavailable
- optimistic concurrency control (CAS/version) to prevent "three bosses"
- separation of roles: sponsor, accountable, executor, approver
- optional behavioral ownership signals for drift detection

## Roles
- sponsor_id: never changes
- accountable_id: answerable for outcome
- executor_id: currently working
- approver_spec: who must approve when gated
- escalation_spec: fallback chain and SLA

## Core invariant
Only one active owner capability (token) can be acknowledged at a time. Transfers require explicit accept.

## Ownership states
assigned -> acknowledged -> in_progress -> pending_review -> paused_waiting_approval -> completed
plus: abandoned (lease expired), contested (conflicting claims)

## Baton pass (two-phase commit)
Events:
- offer_ownership(token_id, to, lease_ttl_s, ack_deadline_ts, roles_delta)
- accept_ownership(token_id)
- decline_ownership(token_id, reason)
- renew_lease(token_id, new_expiry_ts)
- release_ownership(token_id)

Rules:
- sender retains responsibility until accept is recorded
- offer expires after ack_deadline without accept
- lease expiry triggers abandonment and escalation

## Contention resolution (Phase 3)
Single authoritative record per task_id stored with version.
All mutations use CAS: update only if expected_version matches.
On conflict: reload and retry; or mark_contested with claims list and resolve_contested with deterministic tie-break (e.g. lexicographically smallest actor). Lease expiry: list_expired_leases() and abandon_ownership() set state to abandoned; caller can trigger escalation via choose_approver when approver_spec/escalation_spec present.

## Availability and escalation
Availability is separate from ownership.
When approval is required and approver is unavailable past SLA:
- choose fallback per escalation_spec
- never escalate to nobody; terminate in policy default

## Persistence (SQLite, FTS5, graph — Phase 4)
Storage uses SQLite (same as rest of system) with FTS5 and graph tables:
- ownership_events table (append-only audit log)
- ownership_state table (current derived state per run_id/task_id with version)
- ownership_fts (FTS5): full-text search over events (ledger.search(query)); tokenize='unicode61'
- ownership_chain table: current snapshot per (run_id, task_id) — sponsor_id, accountable_id, executor_id, approver_id, state; updated on every state CAS write
- ownership_chain_edges table: edges (from_principal, to_principal, edge_type) for graph view; edge_type in (accountable, executor, approver). Store.get_chain() and Store.get_chain_edges() expose chain and graph for UI/API (e.g. Chapter 8 console).
- checkpoints and approvals (optional, Chapter 8)

## Approval routing and HITL (Phase 2)

### set_pending_review
When the executor reaches an approval gate it calls set_pending_review with:
- approver_spec: who must approve (e.g. `{"kind": "principal", "value": "user-id"}`)
- escalation_spec: fallback chain and SLA, e.g. `{"chain": [{"kind": "principal", "value": "fallback-id"}], "sla_s": 3600}`
- sla_s: seconds until escalation may be triggered
- checkpoint_id: id of the checkpoint (Chapter 8) so console can show and record approval

State transitions to pending_review; store records approver_spec, escalation_spec, checkpoint_id.

### approve_review / deny_review
When the operator console (Chapter 8) records a decision:
- approve_review(checkpoint_id, decision="approved", comment optional): ledger event and state transition (e.g. to in_progress or completed)
- deny_review(checkpoint_id, decision="denied", comment optional): ledger event and state transition; run may fail or pause

These events are written to the ownership ledger and optionally drive executor resume (Chapter 8 integration).

### Availability registry
Availability is separate from ownership. AvailabilityRegistry tracks which principals are currently available (e.g. set_available_for(principal_id, seconds)). Used by choose_approver to decide primary vs fallback. Can be backed by in-memory state or DB (Phase 4).

### Escalation (choose_approver)
Given approver_spec, escalation_spec, and AvailabilityRegistry:
1. If primary (approver_spec) is available, return primary.
2. Else walk escalation_spec.chain; return first available principal.
3. If none available, return NO_AVAILABLE_APPROVER; policy default (e.g. fail closed) applies.

### Chapter 8 integration
- Executor creates approval checkpoint: write checkpoints/<id>.json (Ch8), call set_pending_review with that checkpoint_id, pause run.
- Console lists pending checkpoints; operator approves/denies; console writes approvals/<id>.json and notifies (e.g. event stream). Ownership protocol records approve_review/deny_review and state update; executor resumes when Ch8 signals.

## Tests
A: A->B->C chain, A human offline at approval. No orphan; deterministic fallback.
B: Offer not accepted, sender remains owner.
C: Simultaneous claims resolved via CAS conflict.
D: Lease expires, escalation triggers.

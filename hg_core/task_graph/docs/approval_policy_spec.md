# Spec: Approval policy (default-approve with strict blacklist deny)

## Goal
Reduce friction by auto-approving actions except for explicitly forbidden categories.

## Policy
- Default: approve outbound actions.
- Deny: if any strict blacklist rule matches.
- Optional: per-workflow overrides can require manual approval.

## Strict blacklist rules
Blacklist categories should be explicit and narrow, examples:
- disallowed content classes per your governance
- attempts to access undeclared scopes
- actions to unknown destinations
- repeated failures that triggered a circuit breaker

## Required logging
Even when auto-approved:
- log approval decision = approved
- include policy basis (default-approve)
When denied:
- log approval decision = denied
- include matched blacklist rule identifiers

## Safety integration
Safety gates still run; blacklist is an additional hard stop.
If safety gate blocks, classify as safety_blocked, do not attempt action.

## Acceptance
- Auto-approved actions are still auditable.
- Denied actions never attempt external calls.

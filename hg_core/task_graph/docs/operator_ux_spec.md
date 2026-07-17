# Spec: Minimum operator UX surfaces

## Goal
Provide a minimal set of operator-facing views and actions that make the system maintainable.

## Required views
1) Status overview
- what ran recently, what is paused, what is failing, what is expensive
- circuit breaker states

2) Run detail
- audit summary
- links to trace, outputs, and any approvals
- failure class and retries

3) Dead-letter queue
- list of terminal failures
- one-click replay in no-side-effects mode
- annotate and close

4) Approvals queue (default-approve policy)
- approvals are auto-approved unless strict blacklist triggers or a manual tier is configured
- still record the approval decision and rationale
- allow operator override: force deny, force require approval for a workflow

## Actions
- pause/resume workflow
- clear breaker / cooldown
- replay dead-letter (shadow)
- apply rollback to last known good
- export weekly report

## Acceptance
- Operator can answer "what happened and why" for a run in under a minute using these surfaces.

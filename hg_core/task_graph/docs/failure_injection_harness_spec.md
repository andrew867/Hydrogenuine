# Spec: Failure injection harness

## Goal
Prove reliability behavior under common faults without touching real external destinations.

## Principles
- No side effects in tests: use fake destinations and shadow mode.
- Deterministic scenarios: each fault scenario is reproducible.
- Measure expected outcomes: backoff applied, breaker trips, degraded mode used, dead-letter captured.

## Fault scenarios (minimum)
1) Transient network failures
2) Rate limiting responses
3) Dependency unavailable (knowledge store down)
4) Timeout in a tool/node
5) Validation failure on inputs
6) Safety blocked (strict blacklist category)
7) Permission denied (undeclared capability)
8) Concurrency collision (two triggers same bucket)

## Harness requirements
- Scenario runner that injects faults at configured steps.
- Assertions library that checks:
  - failure class mapping
  - retry count and backoff behavior
  - circuit breaker activation and cooldown
  - dead-letter artifact created on terminal failure
  - no external write attempted when blocked
  - idempotency ledger prevents duplicates on retry

## Acceptance
- Each primary workflow has at least 3 fault scenarios covered initially, expanding over time.
- A "smoke fault suite" runs in CI.

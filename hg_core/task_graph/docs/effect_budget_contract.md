# Effect Budgets Contract (MVP)

## Goal
Prevent runaway runs and make costs predictable by enforcing explicit budgets.

Budgets apply to:
- runtime seconds
- node dispatch attempts
- token usage (if available from LLM calls)
- external calls
- filesystem writes
- network calls

This is an evolution of effect_class:
- effect_class: none | read | write
- effects: quantitative counters and limits

## Data model
RunPolicy additions:
- budgets: dict[str, Budget]
Budget:
- limit: int|float
- scope: "run"|"node"
- hard: bool (if true, exceeding fails run/node)
- soft: bool (if soft, triggers pause or warning)
- on_exceed: "fail_run"|"fail_node"|"pause"|"escalate"

NodePolicy additions:
- budget_costs: dict[str, int|float] optional static costs
- effect_tags: list[str] optional tags

RunState additions:
- budget_used: dict[str, int|float]
- budget_events: list (optional short log) or emit telemetry events

## Enforcement points
- **Before dispatch:** Check whether budget allows another attempt. Compute projected cost (e.g. at least `{"dispatch_attempts": 1}` plus any node-level static costs). Call `check_before_dispatch(run_policy, run_state, cost)`; if not allowed, do not call the dispatcher.
- **After dispatch:** Increment counters based on observed usage from the dispatcher response (e.g. `dispatch_attempts: 1`, `tokens`, `external_calls`). Call `apply_after_dispatch(run_policy, run_state, observed)`.
- **On exceed:** When check_before_dispatch returns not allowed (or a post-dispatch check would exceed): set run error with code `BUDGET_EXCEEDED`, set `run_state.final_status = "failed"`, persist and return summary. Alternatively, if configured: pause or escalate.

## Dispatcher response usage
Dispatchers may return optional usage fields so the executor can increment budget counters:
- **tokens** (number): Token count for LLM/tool calls; summed into `budget_used.tokens`.
- **external_calls** (number): Number of external API or tool calls; summed into `budget_used.external_calls`.

Example response: `{"ok": true, "outputs": {...}, "tokens": 100, "external_calls": 1}`. If omitted, the executor uses 0 for that key. Budget names in `run_policy.budgets` (e.g. `tokens`, `external_calls`, `dispatch_attempts`) must match these keys.

## Determinism
Budget enforcement must be deterministic given the same observed usage inputs.

## Acceptance tests
- cap node dispatch attempts: after N attempts, run fails with BUDGET_EXCEEDED
- cap runtime seconds: when exceeded, run fails or pauses
- cap external calls: each tool dispatch increments external_calls

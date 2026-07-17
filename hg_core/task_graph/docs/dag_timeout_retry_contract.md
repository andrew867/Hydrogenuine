# DAG Timeout and Retry Contract

## Timeout (tool/agent nodes)

- **node.policy.timeout_s**: optional per-node timeout in seconds for tool and agent nodes.
- The **dispatcher** must respect this timeout when invoking the tool or agent (e.g. run in subprocess/thread with a timeout, or `asyncio.wait_for`).
- If execution exceeds the timeout, the dispatch returns failure (e.g. `{"ok": False, "error": "timeout"}`) and the executor treats it as a failed attempt (subject to retries).
- When `timeout_s` is not set, the implementation may use a default (e.g. 300s for agent subprocess).

## Runaway guards (token and loop limits)

- **max_node_executions** and loop **max_iterations** are the main guards against runaway token use. The executor must enforce a global cap on node executions per run (e.g. from run_policy) and each loop node must have a **max_iterations** (e.g. in node config or graph-level default).
- **Recommendation:** Use **max_iterations ≤ 5** for agent loops unless explicitly justified; higher values increase token cost and the risk of context overflow. Document any exception in the DAG or task spec.

## Retry and backoff

- **attempt_count**: number of times the node has been executed (incremented on each dispatch).
- **max_retries**: maximum number of retries (0 = no retries; 1 = one retry after first failure, etc.).
- **retry_backoff_ms**: delay in milliseconds between the failure and the next attempt. The executor must sleep this duration before re-queuing the node for execution.
- Behavior:
  - If the node fails and `attempt_count <= max_retries`: set node back to READY, emit `dag_node_retried`, sleep `retry_backoff_ms`, then continue the loop so the node is scheduled again.
  - If the node fails and `attempt_count > max_retries`: set node to FAILED, emit `dag_node_failed`, and apply failure_mode (fail_fast or continue).

## Retry policy by failure class (plan f1)

When dispatch or the executor classifies a failure, retry behavior can vary by class:

| Failure class   | Typical backoff      | Max attempts (suggested) | Notes |
|-----------------|----------------------|---------------------------|--------|
| **network**     | Exponential (e.g. 1s, 2s, 4s) | 3–5 | Transient; retry with backoff. |
| **rate_limit**  | Long backoff (e.g. 60s)       | 2   | Respect Retry-After if present. |
| **validation**   | No retry (0)                  | 0   | Input/output invalid; fix before retry. |
| **timeout**     | Same or increased timeout     | 1–2 | May succeed with longer timeout. |
| **refusal**     | No retry (0)                  | 0   | Model/policy refusal; change input or skip. |

- The executor or dispatcher may set failure class from `output.error_code` or `output.error` (e.g. `timeout`, `rate_limit`, `validation_error`, `refusal`). When not classified, use default retry (e.g. 1 retry, fixed backoff).
- Document in run_policy or node policy if per-class overrides are supported; otherwise apply the above as implementation guidance.

## Tests

- Node fails N times then succeeds on attempt N+1 → node ends DONE.
- Node fails N+1 times (all attempts fail) → node ends FAILED.
- Backoff delay is applied between retries (mock time or short delay and assert sleep was called with expected duration).

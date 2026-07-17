# Fault Tolerance Contract

- **timeout_s**: Enforced for tool/agent nodes in dispatch (see dag_timeout_retry_contract.md). When set, dispatch runs the task with that timeout; on expiry returns failure and counts as one attempt.
- **retry/backoff**: Deterministic; each attempt counts toward max_retries and max_node_executions. Node fails N times then succeeds on attempt N+1 → DONE; fails N+1 times → FAILED. retry_backoff_ms delay is applied between retries.
- **ready ordering**: get_ready_nodes returns node IDs sorted by node_id so execution order is deterministic for the same DAG and inputs.

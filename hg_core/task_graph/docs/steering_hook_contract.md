# DAG–Steering Hook Contract

The DAG executor invokes the steering layer at every node boundary via two hooks. This allows the overseer to apply policy checks, seriousness/truthfulness, and correction/escalation without the executor depending on steering internals.

## Hooks

### before_node(node, run_state) -> optional dict

- **When:** Called by the executor immediately before dispatching a node (before checkpoint_before, if any).
- **Arguments:**
  - `node`: The node about to run. At least `id`, `type`, `assigned_entity`, `inputs`, `depends_on`, `policy`, `status`, `attempt_count`. Loop context is available via `run_state` (e.g. `run_state.body_to_loop`, `run_state.loop_state`).
  - `run_state`: Current run state. At least `run_id`, `graph_id`, `state`, `node_outputs`, `node_states`. May have `loop_state`, `body_to_loop` when inside a loop body.
- **Return:** Optional. If the overseer returns a dict with `"block": True`, the executor must not dispatch the node. It must set the node's status to blocked and error to `{"code": "STEERING_BLOCKED", "reason": "<value>"}` (using the optional `"reason"` from the return), call `after_node(node, run_state, result)` with a result indicating blocked (e.g. `{"ok": False, "error": {"code": "STEERING_BLOCKED", "reason": "..."}}`), then continue. Any other return (including `None` or `{"allow": True}`) means allow dispatch.
- **Exceptions:** If before_node raises, the executor may log and treat as allow, or treat as block; contract recommends treating as block with reason from exception message for safety.

### after_node(node, run_state, result)

- **When:** Called by the executor after a node has finished (success or failure), after checkpoint_after if any.
- **Arguments:**
  - `node`: The node that just ran (same shape as in before_node; status and error may already be updated).
  - `run_state`: Run state after the node (node_outputs and node_states updated for this node on success).
  - `result`: The dispatch result. Dict with at least `"ok"` (bool). On success often `{"ok": True, "outputs": {...}}`. On failure `{"ok": False, "error": {"code": "...", "message": "..."}}`. When the node was blocked by before_node, result is e.g. `{"ok": False, "error": {"code": "STEERING_BLOCKED", "reason": "..."}}`.
- **Return:** Ignored (fire-and-forget). Optional suggest/correction for downstream can be implemented in later chapters via run_state or side channels.
- **Exceptions:** The executor should catch and log; must not fail the run.

## Order of operations (per node)

1. `before_node(node, run_state)` — if block, skip to step 5 with blocked result.
2. `checkpoint_before(node, run_state)` if `node.checkpoints.before`.
3. Resolve inputs, budget check, call dispatcher, budget apply, recorder.
4. `checkpoint_after(node, run_state)` if `node.checkpoints.after`.
5. `after_node(node, run_state, result)`.

## Payload shape (minimal)

- **node:** `id`, `type`, `assigned_entity`, `inputs`, `outputs`, `depends_on`, `policy`, `checkpoints`, `status`, `attempt_count`, `started_at`, `ended_at`, `error` (if set).
- **run_state:** `run_id`, `graph_id`, `state`, `node_outputs`, `node_states`; inside a loop body also `loop_state`, `body_to_loop`.
- **result:** `ok` (bool), and on failure `error` (dict with `code`, optional `message`/`reason`).

## Overseer adapter

The steering layer may provide an adapter (e.g. extending `DAGCheckpointAdapter`) that implements both checkpoint_before/checkpoint_after and before_node/after_node. The executor only calls methods that exist (e.g. `hasattr(overseer, 'before_node')`); so an overseer with only checkpoints continues to work.

### SteeringHookAdapter / extended DAGCheckpointAdapter

A single adapter can implement all four methods:

- **checkpoint_before(node, run_state)** — opt-in per node via `node.checkpoints.before`; used for HITL pause and audit.
- **checkpoint_after(node, run_state)** — opt-in per node via `node.checkpoints.after`.
- **before_node(node, run_state)** — called for every dispatched node; may return `{"block": True, "reason": "..."}` to block execution. Can delegate to policy checks or BehavioralController in later chapters.
- **after_node(node, run_state, result)** — called for every node after completion; fire-and-forget; can log or delegate to output validation / BehavioralController.

The reference implementation lives in `hg_overseer.overseer_core.dag_hooks.DAGCheckpointAdapter`, which extends the checkpoint interface with before_node and after_node (logging by default; optional future delegation to BehavioralController).

## Executor behavior when before_node returns block

When `before_node(node, run_state)` returns a dict with `"block": True`:

1. The executor must **not** call the dispatcher for that node.
2. The executor sets `node.status` to `"blocked"` and `node.error` to `{"code": "STEERING_BLOCKED", "reason": "<value>"}` where `<value>` is the return's `"reason"` if present, otherwise a default (e.g. `"steering blocked"`).
3. The executor calls `after_node(node, run_state, result)` with `result = {"ok": False, "error": {"code": "STEERING_BLOCKED", "reason": "..."}}`.
4. The executor persists state and continues the run (downstream nodes may become blocked or skipped depending on dependency semantics).

Return value shape: `{"block": True}` or `{"block": True, "reason": "policy violation"}`. Any other return (including `None`, `{}`, or `{"allow": True}`) means allow dispatch.

## Error code

- **STEERING_BLOCKED:** The node was not dispatched because before_node returned `{"block": True, "reason": "..."}`. The node's status is set to blocked and after_node is still called with the blocked result.

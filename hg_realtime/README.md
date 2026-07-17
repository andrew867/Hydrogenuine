# hg_realtime — Layer 10 Realtime Runtime

Event-driven execution plane on top of the existing DAG runtime. Does not replace the DAG engine; it drives it.

## Package placement

- **Location:** Workspace root `hg_realtime/` (sibling to `hg_core/`, `hg_overseer/`, etc.)
- **Install:** Included in root `pyproject.toml` via `setuptools.packages.find` (`hg_realtime*`). Run from workspace root with `pytest tests/hg_realtime/` (pythonpath set in pyproject.toml).

## Integration seams

These are the points where you wire hg_realtime into the existing Hydrogenuine stack.

### 1. DagLauncher (`hg_realtime/integrations/dag_launcher.py`)

- **Interface:** `DagLauncher.launch(req: RunRequested) -> str` (run_id).
- **Wire to:** Resolve `req.workflow_id` / `req.resolved_inputs` to a DAG path and CLI. Invoke the existing DAG entrypoint:
  - `python scripts/run_dag_job.py --job-id <job_id>` (job_id from workflow_id or payload), or
  - `hg-run-dag <dag_path>` with `--run-dir` and `--input` as needed.
- **Source of truth for job_id → DAG:** `scripts/dag_runtime_jobs.py` (`DAG_JOB_REGISTRY`) and `hg_core.task_graph.workflow_registry`. Scheduler’s workflow mapping should read from the same registry.

### 2. PolicyGate (`hg_realtime/integrations/policy_gate.py`)

- **Interface:** `PolicyGate.allow_run(tenant_id, actor_id, workflow_id, resolved_inputs, correlation_id) -> PolicyDecision`.
- **Wire to:** Default allow-all implementation is provided. Replace with loading from `memory/automation` policy or workflow_registry acceptance rules if you need gating.

### 3. Tool router (`hg_realtime/integrations/tool_router.py`)

- **Interface:** `ToolRouterEnforcer.validate(call: ToolCall)` — enforces idempotency_key.
- **Wire to:** Before executing any tool call in the DAG (e.g. in `hg_core.task_graph.dispatch` or native_task_tools), build a ToolCall and call the enforcer; then route to the actual tool implementation (registry).

### 4. OperatorStream (`hg_realtime/integrations/operator_stream.py`)

- **Interface:** `OperatorStream.emit(evt: TimelineEvent)`.
- **Wire to:** Implement with a concrete backend (e.g. append to a ring buffer, Redis stream, or file) that the dashboard and GET /v1/events/stream consume. Emit from the DAG executor on node start/end, tool call, run complete.

### 5. EventBus (production)

- **In-memory:** `hg_realtime.bus.memory_bus.InMemoryBus` — dev/demo only.
- **Production:** Implement `hg_realtime.bus.redis_streams_bus.RedisStreamsBus` (Phase 1) with redis-py; configure `redis_url` and stream name.

### 6. Run index (RUN_STARTED / RUN_COMPLETED)

- **Wire to:** When the launcher starts a run, write to the run index (e.g. operator_console run index DB or hg_core run_index) with run_id, workflow_id, status=running, started_at, correlation_id. When the run process exits, update with status=completed|failed|cancelled and ended_at. Dashboard reads from this run index.

### 7. Steering

- **SteeringAdapter:** Store SteeringEvents by run_id; implement `get_pending(run_id)` for the executor to poll.
- **Executor hooks:** In `hg_core.run_dag` and `hg_core.task_graph.session_runner`, call the steering check before/after nodes and apply pause/cancel/inject.

## Spec and test plan

- **Spec:** `docs/specs/realtime_layer10.md` — event model, bus semantics, scheduler contract, run lifecycle, at-least-once and idempotency posture, replay story.
- **Test plan:** `docs/testplans/realtime_layer10.md` — unit/integration/soak targets and the single integration command: `pytest tests/hg_realtime/ -v`.

## Quick start (dev demo)

```bash
python -m hg_realtime.dev_demo
```

## Test (from workspace root)

```bash
pytest tests/hg_realtime/ -v
```

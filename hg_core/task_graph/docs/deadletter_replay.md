# Dead letter queue and replay (plan f2)

Failed runs are serialized to **memory/automation/deadletter/<task_id>/<timestamp>.json** with minimal repro: inputs, outputs, error, run_id, and optional output hashes so you can replay or debug.

## Payload shape

- `task_id`, `run_id`, `error` (dict with code/message), `inputs`, `outputs`, `output_hashes`, `written_at`.

## Writing

- Call `hg_core.deadletter.write_failed_run(workspace_root, task_id, run_id, error, inputs=..., outputs=..., output_hashes=...)` when a run fails (e.g. from the executor or cron runner after a failed task/DAG run).

## Replay support

- **List:** `hg_core.deadletter.list_deadletter_files(workspace_root, task_id=None)` returns paths to deadletter JSON files (newest first).
- **Load:** `hg_core.deadletter.load_deadletter(path)` returns the payload.
- **Replay:** A script or CLI (e.g. `scripts/replay_deadletter.py --file <path>`) can load the payload and re-invoke the task/DAG with the same inputs (or with patched inputs). Implement replay as needed; the payload contains enough to re-run the same task with the same inputs.

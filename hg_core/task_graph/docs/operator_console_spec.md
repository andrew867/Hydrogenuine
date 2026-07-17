# Hydrogenuine Operator Console: Semi-Nice GUI + API (Pack)

This pack includes:
- A FastAPI backend (API + artifact access) with API-key auth and CORS enabled for a separate frontend.
- A React (Vite) frontend that talks to the API and provides a usable operator UI:
  - Runs dashboard
  - Run detail: summary, artifacts, events tail, graph view (Mermaid), node statuses (best-effort), checkpoints, snapshots, fork
  - DAG runner: paste DAG JSON, validate, review, run

It is "semi-nice" by being:
- clean layout, readable
- practical operator workflows
- low dependency, easy to extend
- not a design system project

## API contract

Base path: `/api/v1`. All endpoints require API key via header (e.g. `X-API-Key` or `Authorization`).

### Graphs
- **POST /graphs/validate** — Body: `{ "dag": <DAG dict> }`. Returns `{ "ok": bool, "errors": [...], "warnings": [...] }`. Validates DAG structure (cycles, refs, policy values).
- **POST /graphs/review** — Body: `{ "dag": <DAG dict> }`. Returns `{ "ok": bool, "reviewed_dag": <dict>?, "report": { "blocked": bool, "issues": [...] } }`. Overseer review and optional rewrite.
- **POST /graphs/run** — Body: `{ "dag": <DAG dict> }`. Returns `{ "ok": true, "run_id": "<uuid>", "status": "<status>" }`. Submits run; execution is in-process (or enqueued in Phase 3).

### Runs
- **GET /runs** — Returns `{ "ok": true, "runs": [ { "run_id", "graph_id", "status", "started_at", "ended_at", "run_dir" }, ... ] }`.
- **GET /runs/{run_id}** — Returns `{ "ok": true, "run_id", "graph_id", "status", "started_at", "ended_at", "run_dir", "summary": <summary.json>, "graph": <graph.json> }` or `{ "ok": false, "error": { "code": "NOT_FOUND", "message": "..." } }`.
- **POST /runs/{run_id}/resume** — Resume a paused run. Returns `{ "ok": true, "run_id", "status" }` or error.

### Artifacts
- **GET /runs/{run_id}/artifacts** — Returns `{ "ok": true, "run_id", "artifacts": [ "<rel_path>", ... ] }`. Paths relative to run_dir.
- **GET /runs/{run_id}/artifact?path=<rel_path>** — Returns file contents (e.g. summary.json, events.jsonl). Path traversal disallowed.

### Snapshots (state_history)
- **GET /runs/{run_id}/snapshots** — Returns `{ "ok": true, "run_id", "snapshots": [ { "seq", ... }, ... ] }` from state_history/index.jsonl.
- **GET /runs/{run_id}/snapshots/{seq}** — Returns snapshot state JSON.
- **POST /runs/{run_id}/fork/{seq}** — Fork run from snapshot (Phase 2). Creates new run_id and run_dir; copies or reconstructs state from state_history snapshot at seq; registers new run in run index. Returns `{ "ok": true, "run_id": "<new>", "run_dir": "...", ... }` or `{ "ok": false, "error": { "code": "NOT_IMPLEMENTED", "message": "..." } }` until implemented.

### Checkpoints (Phase 2)
- **GET /runs/{run_id}/checkpoints** — List pending checkpoints. Returns `{ "ok": true, "run_id", "checkpoints": [ { "checkpoint_id", "node_id", "stage": "before"|"after", ... }, ... ] }`. Wired to hg_core checkpoint store when available.
- **POST /runs/{run_id}/checkpoints/{checkpoint_id}/approve** — Approve checkpoint (optional body: `{ "comment": "..." }`). Returns `{ "ok": true }` or error.
- **POST /runs/{run_id}/checkpoints/{checkpoint_id}/deny** — Deny checkpoint (optional body: `{ "comment": "..." }`). Returns `{ "ok": true }` or error.

### SSE events stream (Phase 2)
- **GET /runs/{run_id}/events/stream** — Server-Sent Events stream tailing run_dir/events.jsonl. Content-Type: text/event-stream. Each new line in events.jsonl is sent as an SSE event (data: &lt;json line&gt;). Client disconnect closes the stream. Used by run-detail UI for live event tail.

### Replay and cancel (Phase 3)
- **POST /runs/{run_id}/replay** — Start deterministic replay of the run using run_dir recordings (see replay harness). Returns `{ "ok": true, "run_id": "<same or new>", "status": "accepted" }` or error (e.g. NOT_FOUND, no recordings). Uses ReplayDispatcher from hg_core; may create a new run or overwrite.
- **POST /runs/{run_id}/cancel** — Request cancellation of a running run. Sets run state to cancelled; executor loop checks shared flag or state_store and exits. Returns `{ "ok": true, "run_id", "status": "cancelled" }` or error. Running runs may take a moment to observe the cancel.
  - **Implementation note:** write `cancel.requested.json` into the run_dir; executor checks this file between node dispatches and exits with `final_status="cancelled"`.

### Worker queue (Phase 3, optional)
- Run submission can be enqueued instead of in-process: POST /graphs/run enqueues a job; a background worker processes the queue, runs the executor, and updates run_index_db. Enables scaling and non-blocking submit.

### RBAC (Phase 3, optional)
- API key roles or middleware: restrict endpoints by role (e.g. viewer vs operator). Document in spec when implemented; e.g. HG_API_KEY may carry a role claim or a separate RBAC layer checks permissions.

## Artifact assumptions (run_dir)

The console assumes run_dir is a directory per run (e.g. under `HG_RUNS_ROOT`). Expected files:

- **summary.json** — Run summary: `run_id`, `graph_id`, `final_status`, `counts`, `budget_used` (optional), etc. Written by executor.
- **graph.json** — DAG as executed. Written at run start.
- **events.jsonl** — One JSON object per line; event stream. Written by executor.
- **state_history/index.jsonl** — One line per snapshot; state_history/state_*.json for full state. Written by durable executor when enabled.

The console does not assume exact node-level artifact formats; it reads summary and graph for display and lists artifacts for download.

## What this does not assume
- It does not assume your exact artifact formats for node tables.
- It works with:
  - summary.json (if present)
  - graph.json (if present)
  - events.jsonl (if present)
  - state_history/index.jsonl (if present)

You will likely extend:
- node status extraction from state.json
- checkpoint store and approval wiring
- replay and cancel endpoints (Phase 3)

## Phases
Phase 1: API + GUI for runs, run detail, DAG submission
Phase 2: HITL approvals + snapshots UI + SSE events
Phase 3: Replay + cancel + worker queue + RBAC

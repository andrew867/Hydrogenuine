# Entity DAG proposals: format and storage

Entity-proposed DAG changes are suggestions from an agent/entity to modify the DAG used for a task. They require signature, provenance, validation, and (when change control is on) approval. See the autonomy plan §5 (change control) and c1–c4.

## Storage path

- **Proposals (ingestion):** `memory/automation/dag_proposals/<task_id>/<timestamp>.json`
  - Example: `memory/automation/dag_proposals/fourclaw-auto-post/2026-02-23T12-00-00Z.json`
  - One file per proposal; timestamp is ISO-like (colons replaced by `-` for filesystem safety).
- **Optional shared inbox:** A single directory (e.g. `memory/automation/dag_proposals/inbox/`) can be used for proposals not yet assigned to a task_id; then moved to `<task_id>/<timestamp>.json` after assignment.

## Proposal format (JSON)

Each proposal file must contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | yes | Task this proposal applies to (e.g. `fourclaw-auto-post`). |
| `proposed_dag` | object | yes | Full DAG JSON (same schema as dag_per_task_spec / load_dag). |
| `provenance` | object | yes | Signature and provenance (see below). |
| `evidence` | string or array | optional | Human- or machine-readable evidence (e.g. summary, citations). |
| `created_at` | string | optional | ISO 8601 timestamp when the proposal was created. |

### Provenance (required)

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Model identifier that produced the proposal (e.g. `gpt-4o`, `claude-3-5-sonnet`). |
| `model_version` | string | Optional version or variant. |
| `run_id` | string | DAG run_id (or session run) that generated this proposal. |
| `entity_id` | string | Optional; entity/agent that proposed (e.g. task name or agent id). |

No anonymous proposals: every proposal must include `provenance` with at least `model` and `run_id`.

## Example (minimal)

```json
{
  "task_id": "fourclaw-auto-post",
  "proposed_dag": {
    "graph_id": "fourclaw_auto_post_v2",
    "version": "1.0",
    "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast"},
    "inputs": {"goal": ""},
    "nodes": [
      {
        "id": "post",
        "type": "agent",
        "assigned_entity": "fourclaw-auto-post",
        "depends_on": [],
        "inputs": {"goal": "$graph.inputs.goal"},
        "outputs": {"result": {}},
        "policy": {"timeout_s": 300, "max_retries": 0}
      }
    ]
  },
  "provenance": {
    "model": "gpt-4o",
    "run_id": "a1b2c3d4-0000-4000-8000-000000000000"
  },
  "evidence": "Proposed after N runs showed token overrun on full context.",
  "created_at": "2026-02-23T12:00:00Z"
}
```

## Validation and application

- **Static validation:** Before apply, proposals are validated per dag_per_task_spec (node types, token caps, schema). New tool types require explicit human enablement (c2).
- **Change control:** Off / on / pass-through (see plan §5 and c0). When **off**, review/apply does nothing. When **on**, human approval required. When **pass-through**, auto-approve but same monitoring/audit as on.
- **Review/apply path:** See [entity_dag_workflow.md](entity_dag_workflow.md).

# Entity DAG workflow: review and apply

This doc describes the review/apply path for entity DAG proposals. See [entity_dag_proposals.md](entity_dag_proposals.md) for format and storage.

## Flow

1. **Ingestion:** Proposals are written to `memory/automation/dag_proposals/<task_id>/<timestamp>.json` (or optional shared inbox `memory/automation/dag_proposals/inbox/`). Each file must include `task_id`, `proposed_dag`, and `provenance` (model, run_id).
2. **Validation:** Before apply, run static validation: DAG schema, allowed node types (dag_per_task_spec), token caps, no new tools without human enablement. Invalid proposals are rejected (log and optionally move to a `rejected/` subfolder).
3. **Change control mode:** Read config via `hg_core.autonomy_config.get_entity_dag_change_control()` (reads `memory/overseer/autonomy_config.json` or env `HG_ENTITY_DAG_CHANGE_CONTROL`; default **pass-through**).
   - **off:** Do not apply any proposal; review/apply path exits without writing to the live DAG or registry.
   - **on:** Require human approval (e.g. operator console "Approve" action or CLI) before applying.
   - **pass-through:** Auto-approve valid proposals; apply after validation; same audit/logging as **on**.
4. **Apply:** For approved (or pass-through) proposals:
   - Option A: Write `proposed_dag` to a new or existing DAG file (e.g. `memory/automation/dags/<task_id>_v2.json`) and update `memory/automation/dag_registry.json` to point `task_id` → that path.
   - Option B: Overwrite the existing DAG file for that task if the registry already points to it; otherwise create new file and update registry.
   - Record applied proposal (e.g. copy to `memory/automation/dag_proposals/applied/<task_id>/<timestamp>.json` or append to an audit log).
5. **Rollback:** Keep last known good DAG path or snapshot (see c4). One-command revert restores the previous DAG registration or file.

## Optional shared proposals

- **Shared inbox:** Proposals without a task_id (or with a placeholder) can be written to `memory/automation/dag_proposals/inbox/`. A separate step (human or job) assigns `task_id` and moves the file to `dag_proposals/<task_id>/<timestamp>.json` before review/apply.
- **Cross-entity proposals:** If multiple entities can propose (e.g. different tasks), each proposal still has a single `task_id`; the workflow is per-task.

## Implementation notes

- Apply can be implemented as a script (e.g. `scripts/apply_dag_proposal.py --task-id X --proposal path`) or an operator console action.
- Canary (c3): When change control is **on** or **pass-through**, optional shadow run of the proposed DAG (no side-effect tools) before apply; compare output to baseline; then apply if within policy.
- Rollback (c4): Store last good DAG path or JSON in e.g. `memory/automation/dag_registry_last_good.json` or per-task `memory/automation/dags/<task_id>.last_good.json` before each apply; revert command restores it and updates registry.

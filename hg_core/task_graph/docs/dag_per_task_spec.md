# DAG-per-task spec: node types and token caps

This spec defines node types and token caps for **companion DAGs** used by automation tasks (see [dag_wiring_plan.md](dag_wiring_plan.md) §6). When a task has a registered DAG, the executor runs the DAG instead of a single full-task agent run; when no DAG is registered, the runner uses the tiered run_task path.

## Node types

### Tool nodes

- **memory_summary** — Load compact session summary only (no full memory, no FTS/entity_recall). Output: text or structured summary for downstream nodes. No token cap (output size is bounded by session_manager contract). **Side effects:** none (read-only). **Rollback:** N/A.
- **run_script** — Invoke a platform script with arguments (e.g. post script, feedback reader). Inputs: script path or key, args. **Side effects:** filesystem, possibly network. Must declare side effects; see [tool side-effects contract](tool_side_effects_contract.md). If not rollbackable, must be last node or guarded by approval gate. Timeout and sandbox limits apply (see dag_timeout_retry_contract.md and safety/sandbox docs).
- **read_feedback** — Load overseer feedback for the task (e.g. from retrieval_audit or feedback-archive). Output: text or JSON for the agent. Bounded by feedback file size. **Side effects:** none (read-only). **Rollback:** N/A.

Tool nodes do not consume LLM tokens; their output is passed as input to agent nodes. Token caps apply to how much of that output is included in agent prompts (see agent node caps).

### Agent nodes

- **decide_topic** — Narrow prompt: e.g. “Given this summary and feedback, pick one topic.” Use **light_context** (max_tokens ≤ 300) or an explicit cap (e.g. 300 tokens) for memory/context.
- **generate_content** — Narrow prompt: e.g. “Given topic and persona summary, write one post body.” Cap: e.g. 500 tokens default, 300 for light.
- **write_announce_summary** — Narrow prompt: e.g. “Summarize this run for the next wake.” Cap: e.g. 200 tokens.

Each agent node must have a **token cap** in node config (e.g. `max_context_tokens: 300`) so the executor or context builder can trim inputs. When not set, the default is **500** for “default” tier and **300** for “light” (aligned with context_loader / session_manager tiers).

## Token caps (summary)

| Node kind   | Context cap (default) | Context cap (light) | Notes |
|------------|------------------------|----------------------|--------|
| tool       | N/A                    | N/A                  | Output size bounded by tool contract |
| agent      | 500                    | 300                  | Per-node `max_context_tokens` overrides |

- **Loop agent nodes:** Same caps; additionally **max_iterations ≤ 5** (see dag_timeout_retry_contract.md).
- **Run-level:** Total run token budget can be enforced at executor level (e.g. sum of node caps × max_iterations per node); optional per-plan.

## Registration

- **task_id → dag_path:** Config or job_registry entry maps task_id (e.g. `fourclaw-auto-post`) to an optional DAG file path. If missing or null, the task runs via the non-DAG path (tiered run_task).
- **Fallback:** When DAG is not configured or loading fails, the runner uses the single run_task path with tiered context; no DAG execution.

## Validation

- **Static validation:** DAG schema must allow only the node types above (and any future approved types). New tool types require explicit enablement (see entity proposal change control). Token caps and max_iterations are validated at load or run start.

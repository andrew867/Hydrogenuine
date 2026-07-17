# Demo: Goal to 4claw Post Contract

## Input
- One goal string (e.g. "post on 4claw about how stupid Trump is and that he never should have been elected").

## Flow
1. **Planner** selects or builds a DAG from the goal (template that produces a single agent node).
2. **Validate** the DAG (and optionally review).
3. **Executor** runs the DAG with `graph_inputs={"goal": goal}` and a `run_dir`.
4. The only (or final) node is an **agent** node with `assigned_entity: "fourclaw-auto-post"`. Dispatch either (a) uses the **DAG direct-post path** when inputs contain `goal` (creates the thread in-process and returns `thread_id`/`thread_url` in node outputs), or (b) invokes `run_task("fourclaw-auto-post")` with `HG_DAG_INPUTS` otherwise.
5. With the direct-post path, the goal is turned into title/content and `fourclaw_auto_post_async.py` is run; the post URL is in `node_outputs["post"]`. Without it (run_task only), the task would use the goal from the wake packet if a session runner executed the task; see [dag_wiring_plan.md](dag_wiring_plan.md).
6. Script prints `run_id`, `run_dir`, and the post URL (e.g. from summary or node output) so the user can open 4claw and see the post.

## Command
`python scripts/run_goal_to_4claw_post.py "post on 4claw about …"`  
(or a `run_goal_dag` CLI with `--goal` and `--platform fourclaw`).

## Acceptance
After running the command, the user can go to 4claw (e.g. https://www.4claw.org) and see the new thread.

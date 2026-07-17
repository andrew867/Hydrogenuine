# DAG Wiring Plan: Connecting the DAG to the Rest of the Codebase

## 1. Current State and Gap

### What the DAG does today
- **Planner:** Builds a DAG from a goal (e.g. `fourclaw_single_post` template with one agent node `fourclaw-auto-post`).
- **Executor:** Runs nodes in order; for **agent** nodes it calls `dispatch_agent(task_name, resolved_inputs, ...)`.
- **Dispatch (agent nodes):** Runs `python -m hg_core.run_task <task_name>` in a subprocess with `HG_DAG_INPUTS` set to resolved inputs (e.g. `{"goal": "..."}`).
- **run_task:** Loads the task markdown and **prints a JSON payload** (instructions, message, session target, etc.). It does **not** execute an agent or run the posting script.

### Why the Phase 5 demo doesn’t create a post
- **Cron/session path:** Real posting is done by a **session-based runner** (e.g. “hg cron run”): the runner wakes a session, sends the payload message, and the **agent** in that session reads the task file, generates content, and runs `hg_platforms/fourclaw/fourclaw_auto_post_async.py`. The live session memory backing that flow is DB-backed; the DAG does not invoke the runner directly, it only invokes `run_task`, which emits the payload.
- So when the DAG runs the “post” node, it only gets back the run_task JSON (no thread_id/thread_url), and no post is created in this process.

### What “wired” means
- **Minimal (demo working):** When the DAG runs a “fourclaw single post” flow with a `goal` in inputs, **a real post is created** and the run result includes the post URL (thread_id/thread_url).
- **Full (optional later):** Agent nodes can optionally use the same execution path as cron (session runner), so full task markdown, persona, and memory are used, with DAG inputs (e.g. goal) in the payload.

---

## 2. Recommended Approach: DAG Direct-Post Path

### Idea
- For **fourclaw-auto-post** when **DAG inputs contain `goal`**, dispatch does **not** call `run_task`. Instead it calls a **direct-post** path that:
  1. Takes `goal` from `resolved_inputs`.
  2. Derives title and content from the goal (template or minimal generation).
  3. Writes temp files and runs `fourclaw_auto_post_async.py` (same script the task file uses).
  4. Parses stdout for `thread_id` / `thread_url` and returns `{"ok": True, "outputs": {"thread_id": ..., "thread_url": ...}}`.

- The executor already stores `output["outputs"]` in `node_outputs["post"]`, and the demo script already reads `node_outputs["post"]` for the URL, so once this path returns outputs, the demo shows the post URL without any session runner.

### Scope
- **In scope:** Single agent node `fourclaw-auto-post` with DAG input `goal`; one board (e.g. configurable default, e.g. `b` or `pol`). When `HG_DAG_POST_USE_LLM=1`, **persona and session memory are in scope** for the direct-post path: title/content are generated using 4claw persona (SOUL/HEART/IDENTITY) and compact session memory for `automation-fourclaw-auto-post`, so the post is in 4claw voice. Full task markdown and rate-limit/duplicate logic beyond what the script does remain in the cron/session path.

### Where it lives
- **Dispatch:** In `dispatch_agent`, if `task_name == "fourclaw-auto-post"` and `resolved_inputs.get("goal")` is non-empty, call the direct-post implementation instead of `run_task`; otherwise keep current behavior (run_task subprocess).
- **Implementation:** New module used by dispatch, e.g. `hg_core.task_graph.fourclaw_dag_post` or `hg_platforms.fourclaw.dag_post`, that:
  - Input: `goal` (str), optional `board` (default e.g. `b`).
  - Output: `{"ok": bool, "outputs": {"thread_id", "thread_url"} | None, "error": str?}`.
  - Internally: build title/content from goal (e.g. title = first line or goal[:80], content = goal; or minimal template), write to temp dir, run `fourclaw_auto_post_async.py --board ... --title_file ... --content_file ...`, parse last-line JSON for thread_id/thread_url.

### Content from goal
- **Option A (template):** `title = (goal.strip() or "DAG post")[:80]`, `content = goal.strip() or "Posted via DAG."` No LLM. Default when USE_LLM not set.
- **Option B (implemented):** Set `HG_DAG_POST_USE_LLM=1` to generate title and content using **4claw persona + session memory** (agent-like path): load persona via `hg_persona.load_platform_persona("fourclaw")`, load compact session memory for `automation-fourclaw-auto-post`, build one LLM request with SOUL/HEART/IDENTITY + memory + goal, output two lines (title, body). Fallback order: agent-like → generic LLM → template. Model via `HG_DAG_POST_LLM_MODEL` (default `gpt-5-mini`). When USE_LLM=1 the post is never the raw goal (template only as last resort).

---

## 3. Other Wiring (Consistency and Docs)

### run_dag.py
- **Today:** `hg_core.run_dag` loads a DAG from a file, runs `TaskGraphExecutor(overseer=...)` with no `state_store` and no `run_dir`, so runs are in-memory only and not persisted.
- **Improvement:** Support optional `--run-dir` and use `StateStore` + `run_dir` when provided, so `hg-run-dag` can produce the same audit artifacts (state.json, summary.json, events.jsonl, state_history/) as the demo script. Align with `run_goal_to_4claw_post.py` behavior.

### Job registry
- **Today:** `hg_core.job_registry` maps `fourclaw-auto-post` → job_id, session_target, platform, mode. Dispatch does not use it for the subprocess; run_task uses it via context_loader.
- **No change required** for the direct-post path; optional: have dispatch use job_registry to resolve session_target when calling run_task (e.g. for logging or future session-runner integration).

### Docs
- **CRON_HEARTBEAT_DAG_OVERSEER_INTEGRATION.md:** Clarify that **run_task** only emits a payload (instructions/message); it does not execute the agent. Execution happens in **Pattern A (session-based)** when a runner wakes a session and sends that payload. **Pattern B** can be described as “run_task as payload builder for scripts/CI”; if we add a direct-post path, add a short **Pattern C** or subsection: “DAG direct-post: when DAG runs fourclaw-auto-post with a goal, dispatch can create a post in-process without a session (see dag_wiring_plan.md).”

### Demo contract
- **demo_goal_to_4claw_post_contract.md:** Update step 4–5 to: “Dispatch invokes either (a) the DAG direct-post path when task is fourclaw-auto-post and inputs contain goal, or (b) run_task otherwise. The direct-post path creates the thread and returns thread_id/thread_url in node outputs.”

---

## 4. Full Session-Runner Integration (Implemented)

### 4.1 Goal

Agent nodes can optionally run the same way as cron: session runner + task file + persona + memory, with DAG inputs (e.g. goal) in the payload. When the session runner is configured, dispatch uses it for agent nodes that are **not** the fourclaw direct-post path (i.e. not fourclaw-auto-post with a goal in inputs).

### 4.2 Configuration

- **HG_DAG_POST_USE_AGENT** – Set to `1`, `true`, or `yes` to prefer the full 4claw agent (session runner) for goal-driven posts. When set **and** session runner is configured, dispatch skips the direct-post path and runs `fourclaw-auto-post` via the session runner with `goal` in HG_DAG_INPUTS. The wrapper script `run_goal_to_4claw_post_llm.py` sets this by default so that when the runner is configured, the full agent is used; otherwise direct-post with persona+memory is used.
- **HG_DAG_USE_SESSION_RUNNER** – Set to `1`, `true`, or `yes` to enable. When set, dispatch will try the session runner for agent nodes that do not use the direct-post path.
- **HG_SESSION_RUNNER_CMD** – Command template to run one task. Must accept the **job_id** as the first argument after the command. Example: `hg cron run` (so the full invocation is `hg cron run <job_id>` with optional `--timeout N`). The runner is invoked as a subprocess; DAG inputs and the task message are passed via environment:
  - **HG_DAG_INPUTS** – JSON of resolved_inputs (already set by dispatch).
  - **HG_OVERRIDE_MESSAGE** – Optional; if the runner supports it, this overrides the default job payload message (e.g. the message from run_task output) so the agent receives the DAG context.
- **Job ID resolution** – `hg_core.job_registry.get_job_id(task_name)` maps task name (e.g. `fourclaw-auto-post`) to job_id (e.g. `fourclaw-auto-post-cadence`). The session runner is called with this job_id.

### 4.3 Dispatch flow

1. **Fourclaw direct-post:** If task is `fourclaw-auto-post` and `resolved_inputs.get("goal")` is truthy → use direct-post path (section 2); return.
2. **Session runner:** If `HG_DAG_USE_SESSION_RUNNER` is set and `HG_SESSION_RUNNER_CMD` is set:
   - Resolve job_id from task_name via job_registry.
   - Optionally run run_task in a subprocess to get the payload JSON; extract `message` (or build a minimal message including DAG inputs) for HG_OVERRIDE_MESSAGE.
   - Run the session runner: subprocess with CMD + job_id + timeout, env HG_DAG_INPUTS, HG_OVERRIDE_MESSAGE (if available).
   - Capture stdout; on success, parse for thread_id/thread_url (e.g. fourclaw) and set outputs if found.
   - Return {ok, outputs?, returncode, stdout_tail}.
3. **Fallback:** Otherwise run run_task subprocess as today (payload only; no execution).

### 4.4 Runner contract (external)

The external runner (e.g. `hg cron run`) must:

- Accept job_id (and optionally timeout).
- Read HG_DAG_INPUTS and HG_OVERRIDE_MESSAGE from the environment if present.
- Run the session (wake agent, send message), wait for completion, and exit with 0 on success.
- **When the agent creates a 4claw post:** Print to stdout a JSON line containing `thread_id` and/or `thread_url` (e.g. `{"thread_id": "...", "thread_url": "https://www.4claw.org/t/..."}`) so the DAG (and `run_goal_to_4claw_post_llm.py`) can capture and display the post URL.

If the runner is not installed or not configured, the DAG continues to use run_task (payload only) for non–direct-post agent nodes.

---

## 5. Task Checklist (Implementation Order)

1. **Spec (this doc):** Done.
2. **fourclaw DAG direct-post module:** Implement `run_fourclaw_post_from_goal(goal, board=None)` that builds title/content, runs `fourclaw_auto_post_async.py`, returns `{ok, outputs: {thread_id, thread_url}}`.
3. **Dispatch:** In `dispatch_agent`, if task_name is `fourclaw-auto-post` and `resolved_inputs.get("goal")` is truthy, call the direct-post function and return its result (with `outputs` so executor fills `node_outputs["post"]`); else keep run_task subprocess.
4. **run_dag:** Add optional `--run-dir`; when set, create StateStore and pass run_dir to executor so artifacts are written.
5. **Docs:** Update CRON_HEARTBEAT_DAG_OVERSEER_INTEGRATION.md (run_task vs session, DAG direct-post) and demo_goal_to_4claw_post_contract.md (dispatch behavior).
6. **Manual test:** Run `python scripts/run_goal_to_4claw_post.py "make a 4claw post about X"` and confirm a post is created and the script prints the post URL and run_dir with audit files.

---

## 6. DAG-per-task pattern (token discipline)

**Idea:** Each automation task can have a **companion DAG** that replaces the single “read full task file + all prereqs” run with a graph of **tool nodes** (e.g. load memory summary, run script, read feedback) and **narrow-scope agent nodes** (e.g. pick topic, generate content, write summary). No single agent sees the full task file plus all prereqs; each node gets only the inputs it needs, which keeps token use bounded.

**Node types (typical):**

- **Tool:** `memory_summary` (load compact session summary only), `run_script` (invoke platform script with args), `read_feedback` (load overseer feedback for the task).
- **Agent:** `decide_topic`, `generate_content`, `write_announce_summary` — each with a small, focused prompt and token cap (e.g. light_context or 300 tokens per agent node).

**Candidate tasks (priority):** **auto-post** and **engage** tasks first (e.g. fourclaw-auto-post, moltbook-auto-post, fourclaw-engage, moltbook-engage). These have clear steps (feedback → topic → content → post) that map to tool + agent nodes. Other tasks (e.g. knowledge-research-auto, overseer-monitor) can follow once the pattern is proven.

**Fallback:** When no DAG is registered for a task, the cron/runner continues to use the single run_task path (tiered context and full task file read by the agent). Registration is e.g. `task_id → optional dag_path` in job_registry or config; see dag_per_task_spec.md (or a section below) for node types and token caps.

**Pilot:** `fourclaw-auto-post` is the pilot task. Static DAG: `memory/automation/dags/fourclaw_auto_post.json`. Registry: `memory/automation/dag_registry.json` maps task_id → path. Set `HG_USE_TASK_DAG=1` when invoking `run_task fourclaw-auto-post` to run the DAG instead of tiered run_task; default inputs use `HG_GOAL` or "scheduled 4claw post". Token measurement: run writes `summary.json` and (when budgets are configured) `budget_used` with token counts to the run_dir.

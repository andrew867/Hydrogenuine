"""
Task Runner for Automation Skill

Loads and executes task markdown files. Uses hg_lib.config and hg_core.session_manager.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_lib.config import ensure_workspace_initialized, get_task_file_path, get_workspace_root
from hg_lib.errors import structured_error_result
from hg_lib.file_io import read_json, read_text, write_json, write_text
from hg_lib.platform_utils import ensure_utf8_stdio

from hg_core.context_loader import get_identity_reminder, get_startup_context, get_wake_briefing, get_soul_excerpt, get_task_output_mode
from hg_core.session_manager import (
    get_session_id,
    load_compacted_memory,
    save_session_memory,
    update_session_last_used,
)
from hg_core.scope_context import scope_context


def _ensure_current_events_files(root: Path) -> None:
    """
    Ensure current-events brief files exist to avoid ENOENT reads from task flows.

    Creates placeholders for today and yesterday in both formats:
    - knowledge/current_events/brief-YYYY-MM-DD.md (canonical)
    - knowledge/current_events/YYYY-MM-DD.md (legacy compatibility)
    """
    current_events_dir = root / "knowledge" / "current_events"
    current_events_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    for days_back in (0, 1):
        date_str = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        brief_path = current_events_dir / f"brief-{date_str}.md"
        legacy_path = current_events_dir / f"{date_str}.md"
        title = f"# Current Events Brief - {date_str}\n\n"
        placeholder = (
            f"{title}"
            "_Placeholder file auto-created to prevent missing-file reads._\n\n"
            "Knowledge research should replace this with curated brief content.\n"
        )

        if not brief_path.exists():
            write_text(brief_path, placeholder)
        if not legacy_path.exists():
            try:
                # Keep legacy path aligned with canonical file when present.
                write_text(legacy_path, read_text(brief_path))
            except OSError:
                write_text(legacy_path, placeholder)


def _get_arg(name: str, argv: list) -> str | None:
    """Get value for --name from argv (--name value)."""
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _read_dag_inputs() -> Dict[str, Any]:
    """Read DAG inputs from HG_DAG_INPUTS env (JSON) or --inputs <path> file. Prefer file if both set."""
    inputs_path = _get_arg("--inputs", sys.argv)
    if inputs_path and Path(inputs_path).exists():
        try:
            out = read_json(Path(inputs_path), default={})
            return out if isinstance(out, dict) else {}
        except (json.JSONDecodeError, IOError):
            pass
    raw = os.environ.get("HG_DAG_INPUTS", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {}


def _resolve_social_media_task(root: Path, platform: str | None, mode: str | None) -> str | None:
    if platform and mode:
        from hg_platforms.registry import get_task_for_platform_mode

        return get_task_for_platform_mode(platform, mode)

    try:
        from hg_core.task_graph.native_task_tools import run_task_tool
    except Exception:
        return None

    graph_inputs = _read_dag_inputs()
    goal = str(graph_inputs.get("goal") or os.environ.get("HG_GOAL", "")).strip()
    chooser = run_task_tool(
        "lifecycle.choose_social_work",
        {"goal": goal},
        timeout_s=30,
    )
    if not isinstance(chooser, dict) or not chooser.get("ok"):
        return None
    outputs = chooser.get("outputs") or {}
    task_name = str(outputs.get("task_name") or "").strip()
    return task_name or None


def get_task_file(task_name: str) -> Optional[Path]:
    """Get the path to a task markdown file."""
    task_file = get_task_file_path(task_name)
    if task_file.exists():
        return task_file
    return None


def load_task_instructions(task_name: str) -> Optional[str]:
    """Load task instructions from markdown file."""
    task_file = get_task_file(task_name)
    if not task_file:
        return None
    try:
        return read_text(task_file)
    except OSError:
        return None


def _maybe_print_startup_quote(root: Path) -> None:
    """If HG_SHOW_QUOTE=1 and stdout is a TTY, print a random quote from artifacts/branding/startup_quotes.json."""
    if not sys.stdout.isatty():
        return
    if os.environ.get("HG_SHOW_QUOTE", "").strip().lower() not in ("1", "true", "yes"):
        return
    quotes_path = root / "artifacts" / "branding" / "startup_quotes.json"
    if not quotes_path.exists():
        return
    try:
        import random
        quotes = json.loads(quotes_path.read_text(encoding="utf-8"))
        if isinstance(quotes, list) and quotes:
            print(random.choice(quotes), file=sys.stderr)
    except (json.JSONDecodeError, OSError):
        pass


def main() -> None:
    """Main entry point for task runner."""
    ensure_utf8_stdio()
    root = get_workspace_root()
    _maybe_print_startup_quote(root)
    if len(sys.argv) >= 2 and sys.argv[1] in ("--help", "-h", "help"):
        print("Usage: hg-run-task <task-name> [--full-task]")
        print("  or:  python -m hg_core.run_task <task-name> [--full-task]")
        print("Loads and executes task markdown files from skills/automation/tasks/")
        print("  --full-task  Emit full task file (default: tiered context: mission + summary)")
        print("  --platform X --mode Y  For social-media: route to platform task (e.g. moltbook, auto-post)")
        sys.exit(0)
    ensure_workspace_initialized(root)
    _ensure_current_events_files(root)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_full_task = "--full-task" in sys.argv
    platform = _get_arg("--platform", sys.argv)
    mode = _get_arg("--mode", sys.argv)

    if len(args) < 1:
        print(json.dumps(structured_error_result(ValueError("Usage: run_task <task-name> [--full-task] [--platform X] [--mode Y]"), code="USAGE_ERROR")))
        sys.exit(1)

    task_name = args[0]
    use_task_dag = os.environ.get("HG_USE_TASK_DAG", "").lower() in ("1", "true", "yes")
    if task_name == "social-media" and (platform and mode or not use_task_dag):
        resolved = _resolve_social_media_task(root, platform, mode)
        if resolved:
            task_name = resolved
        else:
            err = structured_error_result(
                ValueError(f"Could not resolve social-media task for platform/mode: {platform}/{mode}"),
                code="INVALID_PLATFORM_MODE",
                context={"platform": platform, "mode": mode},
            )
            print(json.dumps(err))
            sys.exit(1)
    if not get_task_file_path(task_name).exists():
        err = structured_error_result(
            FileNotFoundError(f"Task file not found: {task_name}.md"),
            code="TASK_NOT_FOUND",
            context={"task_name": task_name},
        )
        print(json.dumps(err))
        sys.exit(1)

    # Mutex: mark that an automation task is running (memory-maintenance checks this and skips when lock is recent)
    lock_path = root / "memory" / "overseer" / "automation_running.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json(lock_path, {"task": task_name, "started_utc": datetime.now(timezone.utc).isoformat()})
    except OSError:
        pass

    try:
        # DAG-per-task pilot: when HG_USE_TASK_DAG=1 and task has a registered DAG, run DAG and exit; else fallback to run_task.
        if use_task_dag:
            try:
                from hg_core.task_graph.dag_registry import get_dag_path
                from hg_core.task_graph import load_dag, TaskGraphExecutor, StateStore
                from hg_core.task_graph.tool_contract_setup import build_default_tool_contract
            except Exception:
                dag_path = None
            else:
                try:
                    dag_path = get_dag_path(task_name, workspace_root=root)
                except Exception:
                    dag_path = None
            if dag_path is not None:
                # Readiness enforcement: unattended run only when registry allows
                unattended = os.environ.get("HG_UNATTENDED", "").lower() in ("1", "true", "yes")
                if unattended:
                    try:
                        from hg_core.task_graph.workflow_registry import (
                            get_declared_workflow_ids,
                            check_readiness_for_run,
                        )
                        if task_name in get_declared_workflow_ids() and not check_readiness_for_run(task_name, unattended=True):
                            err = structured_error_result(
                                ValueError(f"Workflow {task_name} not ready for unattended run (registry readiness is supervised or blocked)"),
                                code="READINESS_BLOCKED",
                                context={"task_name": task_name},
                            )
                            print(json.dumps(err))
                            sys.exit(1)
                    except Exception:
                        pass
                dag = load_dag(dag_path)
                overseer = None
                try:
                    from hg_overseer.overseer_core.dag_hooks import DAGCheckpointAdapter
                    overseer = DAGCheckpointAdapter()
                except Exception:
                    pass
                base = root / "memory" / "automation" / "dag_runs"
                base.mkdir(parents=True, exist_ok=True)
                run_dir = base / f"run_{task_name.replace('-', '_')}"
                run_dir.mkdir(parents=True, exist_ok=True)
                store = StateStore(base_dir=base)
                registry, adapter = build_default_tool_contract()
                executor = TaskGraphExecutor(
                    state_store=store,
                    overseer=overseer,
                    tool_registry=registry,
                    tool_adapter=adapter,
                )
                graph_inputs = _read_dag_inputs()
                if not graph_inputs:
                    graph_inputs = {"goal": os.environ.get("HG_GOAL", "scheduled run")}
                summary = executor.run(dag, graph_inputs=graph_inputs or None, run_dir=run_dir)
                if not summary.get("ok"):
                    try:
                        from hg_core.deadletter import write_failed_run
                        write_failed_run(
                            root, task_name, summary.get("run_id", ""),
                            error=summary.get("run_state", {}).get("state", {}).get("_run_error") or {"code": "run_failed", "message": summary.get("error", "unknown")},
                            inputs=graph_inputs, outputs=summary.get("node_outputs"),
                        )
                    except Exception:
                        pass
                print(json.dumps(summary, indent=2))
                sys.exit(0 if summary.get("ok") else 1)

        session_id = get_session_id(task_name)
        dag_inputs = _read_dag_inputs()
        memory_profile = os.environ.get("HG_MEMORY_PROFILE", "") or None

        # Set session scope for access log (co-access / molecules) for the duration of this run
        with scope_context(scope_type="session", scope_id=session_id, session_id=session_id):
            _run_task_body(
                task_name=task_name,
                session_id=session_id,
                use_full_task=use_full_task,
                dag_inputs=dag_inputs,
                memory_profile=memory_profile,
            )
        update_session_last_used(task_name)
    finally:
        if lock_path.exists():
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _run_task_body(
    task_name: str,
    session_id: str,
    use_full_task: bool,
    dag_inputs: Dict[str, Any],
    memory_profile: Optional[str],
) -> None:
    """Inner task run (with session scope already set)."""
    if use_full_task:
        instructions = load_task_instructions(task_name)
        if not instructions:
            err = structured_error_result(
                FileNotFoundError(f"Task file not found: {task_name}.md"),
                code="TASK_NOT_FOUND",
                context={"task_name": task_name},
            )
            print(json.dumps(err))
            sys.exit(1)
        memory = load_compacted_memory(session_id, max_tokens=2000)
        from hg_core.context_loader import format_memory_context
        memory_context = format_memory_context(memory)
        wake_briefing = get_wake_briefing(session_id)
        identity_reminder = get_identity_reminder(task_name)
        soul_excerpt = get_soul_excerpt(task_name)
        wake_packet = get_startup_context(task_name).get("wake_packet", "")
        identity_block = f"{identity_reminder}\n\nWho you are (SOUL): {soul_excerpt}" if soul_excerpt else identity_reminder
        language_policy = "External output (posts, comments, published content) must be in English; internal thought and memory may use any language."
        rest = (
            "Use lifecycle.get_runtime_contract for compact execution guidance and native runtime tools for the actual work. "
            f"Keep continuity in memory/automation/{session_id}/ while you run.\n\n"
            f"Language: {language_policy}\n\n"
            f"Session memory context:\n{memory_context}"
        )
        if wake_briefing:
            packet = f"{wake_packet}\n\n" if wake_packet else ""
            message = f"{identity_block}\n\n{packet}{wake_briefing}\nCurrent context: {memory_context}.\n\n{rest}"
        else:
            packet = f"{wake_packet}\n\n" if wake_packet else ""
            message = f"{identity_block}\n\n{packet}{rest}"
        output = {
            "ok": True,
            "task": task_name,
            "sessionId": session_id,
            "instructions": instructions,
            "memoryContext": memory_context,
            "message": message,
            "wake_briefing": wake_briefing,
            "identity_reminder": identity_reminder,
            "soul_excerpt": soul_excerpt,
            "wake_packet": wake_packet,
        }
    else:
        startup = get_startup_context(task_name, dag_inputs=dag_inputs, memory_profile=memory_profile)
        output = {
            "ok": True,
            "task": task_name,
            "sessionId": session_id,
            "mission": startup["mission"],
            "task_path": startup["task_path"],
            "instructions": startup["instructions"],
            "memoryContext": startup["session_summary"],
            "full_task_available_at": startup["task_path"],
            "message": startup["instructions"],
            "wake_briefing": startup.get("wake_briefing", ""),
            "identity_reminder": startup.get("identity_reminder", ""),
        }

    try:
        from hg_lib.config import get_workspace_root
        from hg_core.wake_sleep import record_wake
        record_wake(
            workspace_root=get_workspace_root(),
            task_name=task_name,
            session_id=session_id,
            output_mode=get_task_output_mode(task_name),
            wake_packet=output.get("wake_packet", ""),
            memory_profile=memory_profile,
            dag_inputs=dag_inputs if dag_inputs else None,
        )
    except Exception:
        pass

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

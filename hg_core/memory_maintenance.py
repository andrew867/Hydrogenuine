"""
Memory maintenance (sleep) job entrypoint.

Runs promote → archive → prune for each automation agent; writes sleep receipt
and appends to sleep_log for dashboard. Invoked on schedule (e.g. hourly) or when idle.
See docs/specs/sleep_cycle_memory_spec.md.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from hg_lib.config import get_workspace_root, ensure_workspace_initialized

from hg_core.job_registry import get_compatible_agent_ids, get_operational_agent_id, get_registry
from hg_core.memory_gc import run_gc_for_agent
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


DEFAULT_CONFIG = {
    "retention_days_daily_logs": 30,
    "max_decisions": 500,
    "max_posts": 200,
    "max_interactions": 500,
    "sleep_job_interval_minutes": 60,
    "idle_minutes_before_sleep": None,
    "run_lock_max_minutes": 90,
    "sleep_log_keep_last_n_lines": 1000,
    "sleep_log_retention_days": 30,
    "run_index_after_sleep": True,
    "extract_from_daily_notes": False,
    "heavy_artifact_consolidation": True,
}


def load_sleep_cycle_config(workspace_root: Path) -> Dict[str, Any]:
    """Load sleep cycle config from memory/automation/sleep_cycle_config.json or return defaults."""
    config_path = workspace_root / "memory" / "automation" / "sleep_cycle_config.json"
    if not config_path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = dict(DEFAULT_CONFIG)
        out.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        return out
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def _is_automation_running(workspace_root: Path, max_minutes: int = 90) -> bool:
    """
    Return True if memory/overseer/automation_running.lock exists and was updated
    within the last max_minutes (mutex: an automation task is currently running).
    """
    lock_path = workspace_root / "memory" / "overseer" / "automation_running.lock"
    if not lock_path.exists():
        return False
    try:
        mtime = lock_path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds < max_minutes * 60
    except OSError:
        return False


def _last_activity_utc(workspace_root: Path) -> datetime | None:
    """
    Return the latest lastUsed timestamp from memory/automation-sessions.json.
    Returns None if file missing, empty, or invalid.
    """
    path = workspace_root / "memory" / "automation-sessions.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        latest: datetime | None = None
        for task_name, info in data.items():
            if not isinstance(info, dict):
                continue
            used = info.get("lastUsed")
            if not used or not isinstance(used, str):
                continue
            try:
                s = used.strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if latest is None or dt > latest:
                    latest = dt
            except (ValueError, TypeError):
                continue
        return latest
    except (json.JSONDecodeError, OSError):
        return None


def discover_automation_agents(workspace_root: Path) -> List[str]:
    """
    Discover automation agent ids (without automation- prefix).
    Uses job_registry session_target list; falls back to scanning memory/automation/ for automation-* dirs.
    """
    try:
        registry = get_registry()
        agent_ids = set()
        for task_name, info in registry.items():
            for agent_id in get_compatible_agent_ids(task_name):
                agent_ids.add(agent_id)
            st = info.get("session_target")
            if st and isinstance(st, str) and st.startswith("automation-"):
                agent_ids.add(st.replace("automation-", "", 1))
            operational = get_operational_agent_id(task_name)
            if operational:
                agent_ids.add(operational)
        if agent_ids:
            return sorted(agent_ids)
    except Exception:
        pass
    automation_dir = workspace_root / "memory" / "automation"
    if not automation_dir.exists():
        return []
    agents = []
    for d in automation_dir.iterdir():
        if d.is_dir() and d.name.startswith("automation-"):
            agents.append(d.name.replace("automation-", "", 1))
    return sorted(agents)


def _agent_memory_dirs(workspace_root: Path, agent_id: str) -> list[Path]:
    base = workspace_root / "memory" / "automation"
    current_dir = base / f"automation-{agent_id}"
    dirs: list[Path] = [current_dir]
    for suffix in ("engage", "auto-post", "draft", "publish"):
        legacy_dir = base / f"automation-{agent_id}-{suffix}"
        if legacy_dir != current_dir:
            dirs.append(legacy_dir)
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in dirs:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _write_json_to_compatible_memory_dirs(workspace_root: Path, agent_id: str, filename: str, payload: Dict[str, Any]) -> None:
    for memory_dir in _agent_memory_dirs(workspace_root, agent_id):
        try:
            memory_dir.mkdir(parents=True, exist_ok=True)
            (memory_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            continue


def _clear_sleep_requests(workspace_root: Path, agent_id: str) -> None:
    for memory_dir in _agent_memory_dirs(workspace_root, agent_id):
        try:
            req_path = memory_dir / "sleep_request.json"
            if req_path.exists():
                req_path.unlink(missing_ok=True)
        except OSError:
            continue


def run_memory_maintenance(
    workspace_root: Path | None = None,
    agents_filter: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Run memory maintenance (sleep) for all automation agents.

    For each agent: run promote → archive → prune (memory_gc), then write
    last_sleep_summary.json and append to memory/overseer/sleep_log.jsonl.

    Args:
        workspace_root: Workspace root (default: get_workspace_root()).
        agents_filter: If set, only run for these agent ids; otherwise all discovered.

    Returns:
        Summary dict: agents_processed, errors, total_promoted, total_archived, total_pruned,
        per_agent (list of { agent_id, result, duration_seconds }).
    """
    if workspace_root is None:
        workspace_root = get_workspace_root()
    ensure_workspace_initialized(workspace_root)

    config = load_sleep_cycle_config(workspace_root)
    agents = discover_automation_agents(workspace_root)
    if agents_filter is not None:
        agents = [a for a in agents if a in agents_filter]
    else:
        # If any agent explicitly requested sleep, prioritize those agents for this cycle.
        sleep_requested = []
        for agent_id in agents:
            if any((memory_dir / "sleep_request.json").exists() for memory_dir in _agent_memory_dirs(workspace_root, agent_id)):
                sleep_requested.append(agent_id)
        if sleep_requested:
            agents = sleep_requested

    # Mutex: skip if an automation task is currently running (lock file set by run_task)
    run_lock_min = config.get("run_lock_max_minutes", 90)
    if isinstance(run_lock_min, (int, float)) and run_lock_min > 0 and _is_automation_running(workspace_root, int(run_lock_min)):
        return {
            "skipped": True,
            "skipped_reason": "automation run in progress (mutex: entities not asleep)",
            "agents_processed": 0,
            "errors": [],
            "total_promoted": 0,
            "total_archived": {"daily_logs": 0, "decisions": 0, "posts": 0},
            "total_pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
            "per_agent": [],
        }

    # Idle trigger: skip run if last activity was within last M minutes (unless explicit sleep requested)
    idle_min = config.get("idle_minutes_before_sleep")
    if isinstance(idle_min, (int, float)) and idle_min > 0 and agents_filter is None:
        # If we have explicit sleep requests, do not enforce idle_min for this cycle.
        if not agents:
            pass
        else:
            any_sleep_request = False
            for agent_id in agents:
                if any((memory_dir / "sleep_request.json").exists() for memory_dir in _agent_memory_dirs(workspace_root, agent_id)):
                    any_sleep_request = True
                    break
            if any_sleep_request:
                idle_min = None
    if isinstance(idle_min, (int, float)) and idle_min > 0:
        last_activity = _last_activity_utc(workspace_root)
        if last_activity is None:
            return {
                "skipped": True,
                "skipped_reason": "idle check: no sessions file or invalid",
                "agents_processed": 0,
                "errors": [],
                "total_promoted": 0,
                "total_archived": {"daily_logs": 0, "decisions": 0, "posts": 0},
                "total_pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                "per_agent": [],
            }
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=idle_min)
        if last_activity >= cutoff:
            return {
                "skipped": True,
                "skipped_reason": f"idle_minutes_before_sleep: last activity within last {int(idle_min)} minutes",
                "agents_processed": 0,
                "errors": [],
                "total_promoted": 0,
                "total_archived": {"daily_logs": 0, "decisions": 0, "posts": 0},
                "total_pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                "per_agent": [],
            }

    all_errors: List[str] = []
    total_promoted = 0
    total_archived_daily = 0
    total_archived_decisions = 0
    total_archived_posts = 0
    total_pruned_daily = 0
    total_pruned_decisions = 0
    total_pruned_posts = 0
    total_pruned_interactions = 0
    per_agent: List[Dict[str, Any]] = []

    for agent_id in agents:
        t0 = time.perf_counter()
        try:
            result = run_gc_for_agent(agent_id, config, workspace_root)
        except Exception as e:
            all_errors.append(f"{agent_id}: {e}")
            per_agent.append({
                "agent_id": agent_id,
                "error": str(e),
                "duration_seconds": time.perf_counter() - t0,
            })
            continue
        duration = time.perf_counter() - t0

        total_promoted += result.get("promoted", 0)
        archived = result.get("archived", {})
        if isinstance(archived, dict):
            total_archived_daily += len(archived.get("daily_logs", []))
            total_archived_decisions += archived.get("decisions", 0)
            total_archived_posts += archived.get("posts", 0)
        pruned = result.get("pruned", {})
        total_pruned_daily += pruned.get("daily_logs", 0)
        total_pruned_decisions += pruned.get("decisions", 0)
        total_pruned_posts += pruned.get("posts", 0)
        total_pruned_interactions += pruned.get("interactions", 0)
        all_errors.extend(result.get("errors", []))
        duration_sec = round(duration, 2)
        per_agent.append({
            "agent_id": agent_id,
            "result": result,
            "duration_seconds": duration_sec,
        })

        # Write sleep receipt (last_sleep_summary.json) per agent
        memory_dir = workspace_root / "memory" / "automation" / f"automation-{agent_id}"
        if memory_dir.exists():
            at_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            receipt = {
                "at": at_iso,
                "promoted": result.get("promoted", 0),
                "archived": result.get("archived", {"daily_logs": [], "decisions": 0, "posts": 0}),
                "pruned": result.get("pruned", {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0}),
                "nothing_lost": result.get("nothing_lost", True),
            }
            if result.get("summary_ltm_path"):
                receipt["summary_ltm_path"] = result["summary_ltm_path"]
            try:
                _write_json_to_compatible_memory_dirs(
                    workspace_root,
                    agent_id,
                    "last_sleep_summary.json",
                    receipt,
                )
                state_key = f"identity_continuity_state:automation-{agent_id}"
                state = load_operational_json_state(workspace_root, state_key=state_key)
                payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
                payload.update(
                    {
                        "sleep_summary_present": True,
                        "last_sleep_at": at_iso,
                        "sleep_summary_recorded_at": at_iso,
                        "sleep_summary_path": str(memory_dir / "last_sleep_summary.json"),
                        "last_sleep_summary": receipt,
                    }
                )
                save_operational_json_state(workspace_root, state_key=state_key, payload=payload)
            except OSError as e:
                all_errors.append(f"{agent_id} receipt: {e}")

        # Append to sleep_log.jsonl for dashboard
        sleep_log_path = workspace_root / "memory" / "overseer" / "sleep_log.jsonl"
        sleep_log_path.parent.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_id": f"automation-{agent_id}",
            "promoted": result.get("promoted", 0),
            "archived": result.get("archived", {}),
            "pruned": result.get("pruned", {}),
            "nothing_lost": result.get("nothing_lost", True),
            "duration_seconds": duration_sec,
        }
        try:
            with open(sleep_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except OSError as e:
            all_errors.append(f"sleep_log append: {e}")

        # Run agent memory FTS indexer after GC (configurable)
        if config.get("run_index_after_sleep", True):
            try:
                from hg_memory import index_agent
                index_agent(workspace_root, agent_id)
                index_log_path = workspace_root / "memory" / "overseer" / "memory_index_log.jsonl"
                index_log_path.parent.mkdir(parents=True, exist_ok=True)
                index_entry = {
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "agent_id": agent_id,
                }
                with open(index_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(index_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                all_errors.append(f"{agent_id} index: {e}")

        # Optional: extraction from daily notes to life/ staging (for review before merge)
        if config.get("extract_from_daily_notes", False):
            try:
                from hg_memory import run_extraction
                run_extraction(workspace_root, agent_id, days=7)
            except Exception as e:
                all_errors.append(f"{agent_id} extract_daily_notes: {e}")
        # Clear sleep request if present
        _clear_sleep_requests(workspace_root, agent_id)

    # Trim sleep_log.jsonl to keep_last_n_lines if configured
    keep_n = config.get("sleep_log_keep_last_n_lines")
    if keep_n is not None and keep_n > 0:
        sleep_log_path = workspace_root / "memory" / "overseer" / "sleep_log.jsonl"
        if sleep_log_path.exists():
            try:
                lines = sleep_log_path.read_text(encoding="utf-8").strip().splitlines()
                if len(lines) > keep_n:
                    with open(sleep_log_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines[-keep_n:]) + "\n")
            except OSError:
                pass

    return {
        "skipped": False,
        "agents_processed": len(per_agent),
        "errors": all_errors,
        "total_promoted": total_promoted,
        "total_archived": {
            "daily_logs": total_archived_daily,
            "decisions": total_archived_decisions,
            "posts": total_archived_posts,
        },
        "total_pruned": {
            "daily_logs": total_pruned_daily,
            "decisions": total_pruned_decisions,
            "posts": total_pruned_posts,
            "interactions": total_pruned_interactions,
        },
        "per_agent": per_agent,
    }


def main() -> None:
    """CLI entrypoint for memory maintenance job."""
    import sys
    root = get_workspace_root()
    ensure_workspace_initialized(root)
    result = run_memory_maintenance(workspace_root=root)
    print(json.dumps(result, indent=2))
    if result.get("errors"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

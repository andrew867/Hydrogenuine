"""
Session Manager for Automation Tasks

Manages session IDs, loads/saves session memory. Uses hg_lib.config and job_registry.
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_lib.config import get_automation_memory_dir, get_workspace_root
from hg_lib.file_io import read_json, write_json

from hg_core.job_registry import get_compatible_session_targets, get_registry, get_session_target
from hg_core.temporal_changelog import format_temporal_events, load_recent_temporal_events
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


def _log_access_read(agent_id: str, path: Path, source: str, workspace_root: Optional[Path] = None) -> None:
    """Best-effort: log a read access for co-access (molecules). Never raises."""
    try:
        from hg_core.access_log import log_access, canonicalize_subject
        root = workspace_root or get_workspace_root()
        try:
            rel = path.relative_to(root)
            subject = str(rel).replace("\\", "/")
        except (ValueError, TypeError):
            subject = str(path).replace("\\", "/")
        log_access(
            agent_id=agent_id,
            access_type="read",
            subject_type="path",
            subject=canonicalize_subject("path", subject),
            source=source,
            workspace_root=root,
        )
    except Exception:
        pass


def _load_wake_fts_config(workspace_root: Path) -> dict:
    """Load wake FTS and entity graph config from sleep_cycle_config or memory_engine_config."""
    out = {"wake_fts_max_snippets": 5, "wake_fts_days": 7, "entity_graph_enabled": True}
    for path in (
        workspace_root / "memory" / "automation" / "sleep_cycle_config.json",
        workspace_root / "memory" / "memory_engine_config.json",
    ):
        if path.exists():
            data = read_json(path, default={})
            if isinstance(data, dict):
                out["wake_fts_max_snippets"] = data.get("wake_fts_max_snippets", out["wake_fts_max_snippets"])
                out["wake_fts_days"] = data.get("wake_fts_days", out["wake_fts_days"])
                out["entity_graph_enabled"] = data.get("entity_graph_enabled", out["entity_graph_enabled"])
            break
    return out


def _estimate_tokens(value: Any, _seen: Optional[set[int]] = None) -> int:
    """Estimate token count: ~4 chars per token heuristic (no tiktoken dependency).

    Handles self-referential list/dict structures safely by tracking visited object ids.
    """
    if _seen is None:
        _seen = set()
    if value is None:
        return 0
    if isinstance(value, str):
        return max(1, len(value) // 4)
    if isinstance(value, (list, tuple)):
        obj_id = id(value)
        if obj_id in _seen:
            return 0
        _seen.add(obj_id)
        return sum(_estimate_tokens(item, _seen) for item in value)
    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in _seen:
            return 0
        _seen.add(obj_id)
        return sum(_estimate_tokens(v, _seen) for v in value.values())
    return len(str(value)) // 4


def get_session_id(task_name: str) -> str:
    """
    Get session ID for a task. Uses job_registry when available.

    Args:
        task_name: Name of the task (e.g., "moltbook-auto-post")

    Returns:
        Session ID string (e.g., "automation-moltbook-auto-post")
    """
    try:
        session_target = get_session_target(task_name)
        if session_target:
            return session_target
    except Exception:
        pass
    return f"automation-{task_name}"


def update_session_last_used(task_name: str) -> None:
    """Update the last used timestamp for a session."""
    workspace = get_workspace_root()
    sessions_file = workspace / "memory" / "automation-sessions.json"
    if not sessions_file.exists():
        return
    sessions = read_json(sessions_file, default={})
    if isinstance(sessions, dict) and task_name in sessions:
        sessions[task_name]["lastUsed"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        write_json(sessions_file, sessions)


def get_session_memory_path(session_id: str) -> Path:
    """Get the memory directory path for a session."""
    return get_automation_memory_dir(session_id.replace("automation-", "", 1))


def _resolve_compatible_session_ids(session_id: str) -> List[str]:
    seen: set[str] = set()
    session_ids: List[str] = []
    if session_id:
        seen.add(session_id)
        session_ids.append(session_id)
    try:
        registry = get_registry()
    except Exception:
        registry = {}
    for task_name in registry.keys():
        try:
            compatible = get_compatible_session_targets(task_name)
        except Exception:
            compatible = []
        if session_id not in compatible:
            continue
        for candidate in compatible:
            if candidate and candidate not in seen:
                seen.add(candidate)
                session_ids.append(candidate)
    return session_ids


def _compatible_memory_dirs(session_id: str) -> List[Path]:
    return [get_session_memory_path(candidate) for candidate in _resolve_compatible_session_ids(session_id)]


def _session_memory_state_key(session_id: str) -> str:
    return f"automation:session_memory:{session_id}"


def _load_session_memory_payload(workspace_root: Path, session_id: str) -> Dict[str, Any]:
    try:
        state = load_operational_json_state(workspace_root, state_key=_session_memory_state_key(session_id))
        payload = state.get("payload") or {}
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _row_signature(row: Any) -> str:
    if isinstance(row, dict):
        preferred_keys = ("id", "thread_id", "url", "timestamp", "created_at", "topic", "action", "rationale", "content", "text")
        parts = [str(row.get(key) or "").strip() for key in preferred_keys if str(row.get(key) or "").strip()]
        if parts:
            return "|".join(parts)
        try:
            return json.dumps(row, sort_keys=True, ensure_ascii=False)
        except TypeError:
            return str(row)
    return str(row)


def _merge_unique_rows(existing: List[Any], incoming: List[Any], *, limit: int) -> List[Any]:
    merged = list(existing)
    seen = {_row_signature(row) for row in merged}
    for row in incoming:
        signature = _row_signature(row)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(row)
    if limit > 0 and len(merged) > limit:
        merged = merged[-limit:]
    return merged


def load_session_summary_counts(session_id: str) -> Dict[str, Any]:
    """
    Return only counts for session memory (posts, interactions, context exists)
    without loading full content, FTS, or entity_recall. Used by tiered wake path
    to build the session summary string without loading compacted memory.
    """
    out: Dict[str, Any] = {"posts_count": 0, "interactions_count": 0, "context_exists": False}
    posts: List[Any] = []
    interactions: List[Any] = []
    workspace_root = get_workspace_root()
    for candidate in _resolve_compatible_session_ids(session_id):
        payload = _load_session_memory_payload(workspace_root, candidate)
        rows = payload.get("posts", [])
        if isinstance(rows, list):
            posts = _merge_unique_rows(posts, rows, limit=10)
        rows = payload.get("interactions", [])
        if isinstance(rows, list):
            interactions = _merge_unique_rows(interactions, rows, limit=20)
        context = payload.get("context", {})
        if isinstance(context, dict) and context:
            out["context_exists"] = True
    out["posts_count"] = min(len(posts), 10)
    out["interactions_count"] = min(len(interactions), 20)
    return out


def _trim_context_list_fields(context: Dict[str, Any], max_list_entries: int = 50) -> None:
    """
    Trim list fields in context dict in-place so wake payload stays bounded.
    Keeps last max_list_entries per list; leaves scalars and small dicts unchanged.
    """
    if not context or max_list_entries <= 0:
        return
    for key, value in list(context.items()):
        if isinstance(value, list) and len(value) > max_list_entries:
            context[key] = value[-max_list_entries:]
        elif isinstance(value, dict):
            _trim_context_list_fields(value, max_list_entries)


def _cap_context_tokens(context: Dict[str, Any], max_tokens: int) -> None:
    """
    Cap the context dict so its estimated token count is at most max_tokens.
    Trims list fields (keeping last entries) until under budget. Mutates in place.
    """
    if not context or max_tokens <= 0:
        return
    current = _estimate_tokens(context)
    if current <= max_tokens:
        return
    max_entries = 50
    while current > max_tokens and max_entries >= 1:
        _trim_context_list_fields(context, max_entries)
        current = _estimate_tokens(context)
        max_entries = max(1, max_entries - 10)


def load_compacted_memory(
    session_id: str, max_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Load compacted session memory.

    Args:
        session_id: Session ID
        max_tokens: Maximum tokens to load (for compaction)

    Returns:
        Dictionary with memory data (posts, interactions, context)
    """
    agent_id = session_id.replace("automation-", "", 1)
    memory_dir = get_automation_memory_dir(agent_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = get_workspace_root()

    memory: Dict[str, Any] = {
        "posts": [],
        "interactions": [],
        "context": {},
        "recent_activity": [],
        "decision_context": [],
        "continuity_notes": [],
    }

    for candidate in reversed(_resolve_compatible_session_ids(session_id)):
        payload = _load_session_memory_payload(workspace_root, candidate)
        rows = payload.get("posts", [])
        if isinstance(rows, list):
            memory["posts"] = _merge_unique_rows(memory["posts"], rows, limit=100)
        rows = payload.get("interactions", [])
        if isinstance(rows, list):
            memory["interactions"] = _merge_unique_rows(memory["interactions"], rows, limit=150)
        context_data = payload.get("context", {})
        if isinstance(context_data, dict) and context_data:
            memory["context"].update(context_data)
    _trim_context_list_fields(memory["context"], max_list_entries=50)

    summary_days: List[Any] = []
    for candidate in reversed(_resolve_compatible_session_ids(session_id)):
        payload = _load_session_memory_payload(workspace_root, candidate)
        summary_7d = payload.get("summary_7d", {})
        if isinstance(summary_7d, dict) and summary_7d:
            memory["summary_7d"] = {**memory.get("summary_7d", {}), **summary_7d}
            days_list = summary_7d.get("days", [])
            if isinstance(days_list, list) and days_list:
                summary_days = _merge_unique_rows(summary_days, days_list, limit=14)
    if summary_days:
        memory["summary_7d"]["days"] = summary_days
        memory["recent_activity"] = [
            f"{d.get('date', '')}: {(d.get('summary_text') or '')[:200]}"
            for d in summary_days[-7:]
            if isinstance(d, dict)
        ]
    if not memory.get("recent_activity"):
        recent_lines: List[str] = []
        for candidate in reversed(_resolve_compatible_session_ids(session_id)):
            payload = _load_session_memory_payload(workspace_root, candidate)
            lines = payload.get("recent_activity", [])
            if isinstance(lines, list):
                recent_lines.extend([str(item) for item in lines if str(item).strip()])
        if recent_lines:
            memory["recent_activity"] = recent_lines[-50:]

    try:
        from hg_gateway.shared_storage import list_agent_decisions

        shared_decisions = list_agent_decisions(agent_id, limit=20)
        if shared_decisions:
            memory["decision_context"] = list(reversed(shared_decisions))[-20:]
    except Exception:
        pass

    try:
        continuity_events = load_recent_temporal_events(workspace_root=workspace_root, agent_id=agent_id, limit=3, days=30)
        memory["continuity_notes"] = format_temporal_events(continuity_events, max_items=3)
    except Exception:
        memory["continuity_notes"] = []

    memory["fts_snippets"] = []
    memory["entity_recall"] = []
    workspace_root = get_workspace_root()
    # light_context (cap <= 300): skip FTS and entity_recall to stay under budget
    if max_tokens > 300:
        wake_config = _load_wake_fts_config(workspace_root)
        max_snippets = wake_config.get("wake_fts_max_snippets", 5)
        wake_days = wake_config.get("wake_fts_days", 7)
        db_path = memory_dir / "agent_memory.db"
        shared_agent_db = False
        try:
            from hg_gateway.shared_storage import use_shared_gateway_db

            shared_agent_db = use_shared_gateway_db(db_path)
        except Exception:
            shared_agent_db = False
        if max_snippets > 0 and (db_path.exists() or shared_agent_db):
            try:
                from hg_memory import search_memory
                memory["fts_snippets"] = search_memory(
                    workspace_root, agent_id, max_snippets=max_snippets, days=wake_days
                )
            except Exception:
                pass
        if wake_config.get("entity_graph_enabled", True) and (db_path.exists() or shared_agent_db):
            try:
                from hg_memory import get_recent_entities
                memory["entity_recall"] = get_recent_entities(workspace_root, agent_id, limit=5)
            except Exception:
                pass

    # Enforce max_tokens: truncate sections (keep most recent) so total <= max_tokens
    if max_tokens > 0:
        total = (
            _estimate_tokens(memory["posts"])
            + _estimate_tokens(memory["interactions"])
            + _estimate_tokens(memory["recent_activity"])
            + _estimate_tokens(memory["decision_context"])
            + _estimate_tokens(memory["continuity_notes"])
            + _estimate_tokens(memory["context"])
            + _estimate_tokens(memory["fts_snippets"])
            + _estimate_tokens(memory["entity_recall"])
        )
        if total > max_tokens:
            # Budget per section: 7 sections (context gets its share)
            budget_each = max(50, max_tokens // 8)
            budget_context = max(50, max_tokens // 8)
            for key in ("posts", "interactions", "recent_activity", "decision_context", "continuity_notes", "fts_snippets", "entity_recall"):
                arr = memory[key]
                if not isinstance(arr, list):
                    continue
                current = _estimate_tokens(arr)
                if current <= budget_each:
                    continue
                # Trim from front (oldest) until under budget
                for i in range(len(arr) - 1, -1, -1):
                    trimmed = arr[i:]
                    if _estimate_tokens(trimmed) <= budget_each:
                        memory[key] = trimmed
                        break
                    if i == 0:
                        memory[key] = arr[-1:] if arr else []
                        break
            # Cap context dict (it is not a list; trim nested list fields so context fits budget)
            _cap_context_tokens(memory["context"], budget_context)

    return memory


# mc3: Required keys for compacted memory QA
COMPACTED_MEMORY_REQUIRED_KEYS = (
    "posts",
    "interactions",
    "context",
    "recent_activity",
    "decision_context",
    "continuity_notes",
    "fts_snippets",
    "entity_recall",
)


def verify_compacted_memory_qa(
    session_id: str,
    max_tokens: int = 500,
    token_drift_factor: float = 1.2,
) -> Dict[str, Any]:
    """
    mc3: Verify compacted memory has required keys and token estimate within expected range.
    Used by memory_maintenance or a periodic QA job.
    Returns dict with ok (bool), missing_keys (list), token_estimate (int), token_in_range (bool), errors (list).
    """
    errors: List[str] = []
    try:
        memory = load_compacted_memory(session_id, max_tokens=max_tokens)
    except Exception as e:
        return {
            "ok": False,
            "missing_keys": list(COMPACTED_MEMORY_REQUIRED_KEYS),
            "token_estimate": 0,
            "token_in_range": False,
            "errors": [str(e)],
        }
    missing = [k for k in COMPACTED_MEMORY_REQUIRED_KEYS if k not in memory]
    if missing:
        errors.append(f"Missing keys: {missing}")
    token_estimate = (
        _estimate_tokens(memory.get("posts", []))
        + _estimate_tokens(memory.get("interactions", []))
        + _estimate_tokens(memory.get("recent_activity", []))
        + _estimate_tokens(memory.get("decision_context", []))
        + _estimate_tokens(memory.get("context", {}))
        + _estimate_tokens(memory.get("fts_snippets", []))
        + _estimate_tokens(memory.get("entity_recall", []))
    )
    cap_with_drift = int(max_tokens * token_drift_factor)
    token_in_range = 0 <= token_estimate <= cap_with_drift
    if not token_in_range:
        errors.append(f"Token estimate {token_estimate} outside range [0, {cap_with_drift}] (cap={max_tokens})")
    return {
        "ok": len(missing) == 0 and token_in_range,
        "missing_keys": missing,
        "token_estimate": token_estimate,
        "token_in_range": token_in_range,
        "errors": errors,
    }


def get_estimated_memory_tokens(session_id: str, max_tokens: int = 500) -> Dict[str, Any]:
    """
    Load compacted memory with the given cap and return estimated token count.
    Used by dashboard to show context window usage per cron.
    """
    memory = load_compacted_memory(session_id, max_tokens=max_tokens)
    estimated = (
        _estimate_tokens(memory["posts"])
        + _estimate_tokens(memory["interactions"])
        + _estimate_tokens(memory["recent_activity"])
        + _estimate_tokens(memory["decision_context"])
        + _estimate_tokens(memory["context"])
        + _estimate_tokens(memory.get("fts_snippets", []))
        + _estimate_tokens(memory.get("entity_recall", []))
    )
    return {"estimated_tokens": estimated, "cap": max_tokens}


def save_session_memory(
    session_id: str, memory_updates: Dict[str, Any]
) -> None:
    """Save session memory updates."""
    agent_id = session_id.replace("automation-", "", 1)
    memory_dir = get_automation_memory_dir(agent_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = get_workspace_root()
    state_key = _session_memory_state_key(session_id)
    existing_state = load_operational_json_state(workspace_root, state_key=state_key)
    payload = existing_state.get("payload") if existing_state.get("present") else {}
    if not isinstance(payload, dict):
        payload = {}

    if "posts" in memory_updates:
        new_posts = []
        for p in memory_updates["posts"]:
            post = dict(p) if isinstance(p, dict) else {}
            if "id" not in post or not post["id"]:
                post["id"] = uuid.uuid4().hex[:12]
            new_posts.append(post)
        existing_posts = payload.get("posts", [])
        if not isinstance(existing_posts, list):
            existing_posts = []
        payload["posts"] = (existing_posts + new_posts)[-200:]

    if "interactions" in memory_updates:
        existing_interactions = payload.get("interactions", [])
        if not isinstance(existing_interactions, list):
            existing_interactions = []
        payload["interactions"] = (existing_interactions + list(memory_updates["interactions"]))[-500:]

    if "context" in memory_updates:
        context_data = payload.get("context", {})
        if not isinstance(context_data, dict):
            context_data = {}
        context_data.update(memory_updates["context"])
        payload["context"] = context_data

    if "activity" in memory_updates:
        recent_activity = payload.get("recent_activity", [])
        if not isinstance(recent_activity, list):
            recent_activity = []
        recent_activity.extend([line for line in str(memory_updates["activity"]).splitlines() if line.strip()])
        payload["recent_activity"] = recent_activity[-50:]

    if "decision_context" in memory_updates:
        try:
            from hg_gateway.shared_storage import append_agent_decision

            dc = memory_updates["decision_context"]
            decisions = dc if isinstance(dc, list) else [dc]
            for item in decisions[-min(len(decisions), 25):]:
                if not isinstance(item, dict):
                    continue
                append_agent_decision(
                    decision_id=str(item.get("decision_id") or uuid.uuid4().hex[:12]),
                    agent_id=agent_id,
                    timestamp=str(item.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
                    action=str(item.get("action") or ""),
                    rationale=str(item.get("rationale") or ""),
                    alternatives=item.get("alternatives") or [],
                    tradeoffs=item.get("tradeoffs"),
                    context=item.get("context"),
                    outcome=item.get("outcome"),
                )
            existing_decision_context = payload.get("decision_context", [])
            if not isinstance(existing_decision_context, list):
                existing_decision_context = []
            payload["decision_context"] = (existing_decision_context + decisions)[-25:]
        except Exception:
            pass

    try:
        save_operational_json_state(
            workspace_root,
            state_key=state_key,
            payload=payload,
        )
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: session_manager.py <command> [args...]")
        print("Commands: get-session-id <task_name>")
        sys.exit(1)
    command = sys.argv[1]
    if command == "get-session-id":
        if len(sys.argv) < 3:
            print("Usage: session_manager.py get-session-id <task_name>")
            sys.exit(1)
        task_name = sys.argv[2]
        session_id = get_session_id(task_name)
        print(json.dumps({"sessionId": session_id}))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

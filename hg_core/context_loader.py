"""
Tiered context loading for job runner.
Provides mission summary + session context instead of full task dump.
Uses hg_lib.config for workspace paths (get_workspace_root, get_task_file_path, etc.).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_lib.config import get_task_file_path, get_workspace_root, get_persona_dir, resolve_task_file_name
from hg_lib.file_io import read_json, read_text
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state

from hg_core.session_manager import (
    get_session_id,
    load_compacted_memory,
    load_session_summary_counts,
    get_estimated_memory_tokens,
    _estimate_tokens,
)
from hg_core.temporal_changelog import format_temporal_events, load_recent_temporal_events


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """
    Parse simple YAML frontmatter at top of file.
    Only supports flat key: value pairs (no nesting).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: Dict[str, str] = {}
    for i in range(1, len(lines)):
        line = lines[i].rstrip()
        if line.strip() == "---":
            break
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


def _get_task_metadata(task_name: str) -> Dict[str, str]:
    """Load task frontmatter metadata for a task file."""
    path = get_task_file_path(task_name)
    content = read_text(path, default="")
    if not content:
        return {}
    return _parse_frontmatter(content)


def get_task_output_mode(task_name: str) -> str:
    """Return output mode for task (announce or standard)."""
    metadata = _get_task_metadata(task_name)
    return metadata.get("output_mode") or metadata.get("announce_mode") or "standard"


def _resolve_timezone_label(config: Optional[dict] = None) -> tuple[datetime, str]:
    """
    Resolve current time and timezone label.
    Preference order: config overseer.timezone -> HG_TIMEZONE env -> local timezone.
    """
    tz_name = None
    if isinstance(config, dict):
        tz_name = (
            (config.get("overseer") or {}).get("timezone")
            or (config.get("memory") or {}).get("timezone")
        )
    tz_name = tz_name or os.environ.get("HG_TIMEZONE") or os.environ.get("HG_TZ")

    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(tz_name))
            label = tz_name
            return now, label
        except Exception:
            pass

    now = datetime.now().astimezone()
    tz_label = now.tzname() or "local"
    return now, tz_label


def _summarize_unack_feedback(agent_id: str) -> Optional[str]:
    """
    Return one-line summary of unacknowledged feedback for agent if available.
    Format: "Feedback: {count} new (highest: {severity})"
    """
    try:
        from hg_core.wrappers.feedback_tracker import read_new_feedback
    except Exception:
        return None
    try:
        items = read_new_feedback(agent_id)
    except Exception:
        return None
    if not items:
        return None

    severity_rank = {
        "critical": 4,
        "warning": 3,
        "notice": 2,
        "info": 2,
        "medium": 2,
        "low": 1,
    }
    highest = "unknown"
    highest_rank = 0
    for item in items:
        sev = str(item.get("severity", "medium")).lower()
        rank = severity_rank.get(sev, 0)
        if rank > highest_rank:
            highest_rank = rank
            highest = sev
    return f"Feedback: {len(items)} new (highest: {highest})"


def format_memory_context(memory: dict) -> str:
    """Format memory context for inclusion in task instructions."""
    context_parts = []
    if memory.get("posts"):
        context_parts.append(f"Recent posts: {len(memory['posts'][-10:])}")
    if memory.get("interactions"):
        context_parts.append(f"Recent interactions: {len(memory['interactions'][-20:])}")
    if memory.get("context"):
        context_parts.append("Cross-platform context available")
    if context_parts:
        return "\n".join(context_parts)
    return "No previous context"


def format_memory_context_from_counts(counts: dict) -> str:
    """Format session summary from load_session_summary_counts (no full memory load)."""
    parts = []
    if counts.get("posts_count", 0) > 0:
        parts.append(f"Recent posts: {counts['posts_count']}")
    if counts.get("interactions_count", 0) > 0:
        parts.append(f"Recent interactions: {counts['interactions_count']}")
    if counts.get("context_exists"):
        parts.append("Cross-platform context available")
    return "\n".join(parts) if parts else "No previous context"


def _get_temporal_continuity_lines(agent_id: str) -> list[str]:
    try:
        events = load_recent_temporal_events(agent_id=agent_id, limit=2, days=30)
        return format_temporal_events(events, max_items=2)
    except Exception:
        return []


def _build_initialization_memo(
    *,
    task_name: str,
    task_id: str,
    platform: str,
    mode: str,
    memory_scope: str,
    mission: str,
    session_summary: str,
    task_path: str,
) -> str:
    return (
        f"# Initialization Memo - {task_id}\n\n"
        f"Task: `{task_name}`\n"
        f"Platform: `{platform}`\n"
        f"Mode: `{mode}`\n"
        f"Memory scope: `{memory_scope}`\n\n"
        "## Why You Woke Up\n\n"
        f"{mission}\n\n"
        "## Operating Contract\n\n"
        "- Request compact execution guidance with `lifecycle.get_runtime_contract`.\n"
        "- Use native runtime tools for social, knowledge, notification, and sleep decisions.\n"
        "- Use `confidence.summary` when you need the current confidence/uncertainty snapshot before acting.\n"
        "- Use `knowledge.delivery_summary` when you need the latest research deliveries or current-events brief.\n"
        "- Use `knowledge.search` to find relevant internal knowledge and `knowledge.read` for bounded document reads.\n"
        "- Treat task markdown as background reference, not the primary execution surface.\n"
        "- Leave durable receipts or ask for help when a write path is unavailable.\n\n"
        "## Continuity Snapshot\n\n"
        f"{session_summary}\n\n"
        "## Operator Framing\n\n"
        "- The Reverend wants coherent, inspectable behavior rather than fake progress.\n"
        "- Protect continuity, receipts, and account correctness over speed.\n"
        "- If you are unsure, notify the human instead of improvising a broken side effect.\n\n"
        "## Reference\n\n"
        f"- Task reference: `{task_path}`\n"
    )


def _ensure_initialization_memo(
    *,
    memory_dir: Path,
    task_name: str,
    task_id: str,
    platform: str,
    mode: str,
    memory_scope: str,
    mission: str,
    session_summary: str,
    task_path: str,
) -> tuple[Optional[str], Optional[Path]]:
    memo_path = memory_dir / "initialization_memo.md"
    try:
        state_key = f"identity_continuity_state:{memory_scope}"
        if memo_path.exists():
            content = read_text(memo_path, default="").strip()
            if content:
                try:
                    save_operational_json_state(
                        get_workspace_root(),
                        state_key=state_key,
                        payload={
                            "initialization_memo_present": True,
                            "initialization_memo_path": str(memo_path),
                            "initialization_memo_text": content,
                            "initialization_memo_recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        },
                    )
                except Exception:
                    pass
            return (content or None), memo_path
        memory_dir.mkdir(parents=True, exist_ok=True)
        content = _build_initialization_memo(
            task_name=task_name,
            task_id=task_id,
            platform=platform,
            mode=mode,
            memory_scope=memory_scope,
            mission=mission,
            session_summary=session_summary,
            task_path=task_path,
        )
        memo_path.write_text(content + "\n", encoding="utf-8")
        try:
            save_operational_json_state(
                get_workspace_root(),
                state_key=state_key,
                payload={
                    "initialization_memo_present": True,
                    "initialization_memo_path": str(memo_path),
                    "initialization_memo_text": content,
                    "initialization_memo_recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
        except Exception:
            pass
        return content, memo_path
    except OSError:
        return None, None


def _log_access_read(path: Path, source: str, agent_id: str = "") -> None:
    """Best-effort: log a read for co-access (molecules). Never raises."""
    try:
        from hg_core.access_log import log_access, canonicalize_subject
        root = get_workspace_root()
        try:
            rel = path.relative_to(root)
            subject = str(rel).replace("\\", "/")
        except (ValueError, TypeError):
            subject = str(path).replace("\\", "/")
        log_access(
            agent_id or "",
            "read",
            "path",
            canonicalize_subject("path", subject),
            source,
            workspace_root=root,
        )
    except Exception:
        pass


def get_mission_from_task(task_name: str) -> str:
    """
    Extract mission paragraph from task file.
    Looks for ## Mission or # Mission, then content until next ## or ~200 chars.
    Fallback: first 150 chars of task content (strip headers).
    """
    path = get_task_file_path(task_name)
    if not path.exists():
        return f"Execute task {task_name}. Request runtime guidance when details are needed."

    try:
        content = read_text(path, default="")
        if not content:
            return f"Execute task {task_name}. Request runtime guidance when details are needed."
        _log_access_read(path, "context_loader.get_mission_from_task", agent_id=task_name)
    except OSError:
        return f"Execute task {task_name}. Request runtime guidance when details are needed."

    lines = content.splitlines()
    mission_lines: list[str] = []
    in_mission = False

    for line in lines:
        stripped = line.strip()
        # Start of mission section (# Mission or ## Mission)
        if stripped.lower() in ("# mission", "## mission"):
            in_mission = True
            continue
        if in_mission:
            # Stop at next ## or # (new section)
            if stripped.startswith("##") or (stripped.startswith("#") and not stripped.lower().startswith("# mission")):
                break
            # Stop at hr (---) or empty line followed by ##
            if stripped == "---":
                break
            if stripped:
                mission_lines.append(stripped)
                if len(" ".join(mission_lines)) >= 300:
                    break

    if mission_lines:
        return " ".join(mission_lines).strip()[:350]

    # Fallback: first meaningful content (skip headers, separators, alert lines)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped == "---" or "🚨" in stripped or "READ THIS" in stripped.upper():
            continue
        return stripped[:150]
    return f"Execute task {task_name}. Request compact runtime instructions for the current objective."


def get_identity_reminder(task_name: str) -> str:
    """
    One-line identity reminder for wake: "You are <task_name>. <mission_first_line>."
    Uses first non-empty line of mission (capped 80 chars) or fallback.
    """
    mission = get_mission_from_task(task_name)
    first_line = ""
    for line in mission.splitlines():
        stripped = line.strip()
        if stripped:
            first_line = stripped[:80]
            break
    if not first_line:
        first_line = mission.strip()[:80] if mission.strip() else ""
    if not first_line:
        first_line = "Execute this task."
    return f"You are {task_name}. {first_line}."


def get_soul_excerpt(task_name: str) -> str:
    """
    Load first paragraph of persona SOUL.md at wake when the task has an associated persona.
    Resolves persona via job_registry platform; SOUL path: skills/automation/personas/<platform>/default/SOUL.md.
    Returns empty string if no persona or SOUL.md missing. Capped at ~300 chars or first paragraph.
    """
    try:
        from hg_core.job_registry import get_registry
        registry = get_registry()
        info = registry.get(task_name)
        if not info or not isinstance(info, dict):
            return ""
        platform = info.get("platform")
        if not platform or not isinstance(platform, str):
            return ""
        soul_dir = get_persona_dir(platform, "default")
        soul_path = soul_dir / "SOUL.md"
        if not soul_path.exists():
            return ""
        text = read_text(soul_path, default="").strip()
        _log_access_read(soul_path, "context_loader.get_soul_excerpt")
        if not text:
            return ""
        first_para = text.split("\n\n")[0].strip() if "\n\n" in text else text.split("\n")[0].strip()
        return first_para[:300] + ("..." if len(first_para) > 300 else "")
    except Exception:
        return ""


def get_wake_briefing(session_id: str) -> str:
    """
    Load last_sleep_summary.json for the session and format a 1-3 line wake-up briefing.
    Returns empty string if file missing or invalid.
    """
    root = get_workspace_root()
    agent_id = session_id.replace("automation-", "", 1)
    data = {}
    summary_path: Path | None = None
    try:
        from hg_core.job_registry import get_registry, get_compatible_session_targets

        candidates = [session_id]
        seen = {session_id}
        for task_name in get_registry().keys():
            compatible = get_compatible_session_targets(task_name)
            if session_id not in compatible:
                continue
            for candidate in compatible:
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
    except Exception:
        candidates = [session_id]
    for candidate in candidates:
        candidate_agent_id = candidate.replace("automation-", "", 1)
        candidate_state = load_operational_json_state(
            root,
            state_key=f"identity_continuity_state:{candidate}",
        )
        candidate_data = candidate_state.get("payload") if isinstance(candidate_state.get("payload"), dict) else {}
        if not isinstance(candidate_data, dict) or not candidate_data:
            continue
        candidate_summary = candidate_data.get("last_sleep_summary") if isinstance(candidate_data.get("last_sleep_summary"), dict) else {}
        if not isinstance(candidate_summary, dict):
            candidate_summary = {}
        merged_data = dict(candidate_data)
        merged_data.update(candidate_summary)
        candidate_at = str(merged_data.get("at") or merged_data.get("last_sleep_at") or "")
        current_at = str(data.get("at") or "")
        if not data or candidate_at >= current_at:
            data = merged_data
            summary_path = None
            summary_path_value = str(candidate_data.get("last_sleep_summary_path") or candidate_data.get("sleep_summary_path") or "").strip()
            if summary_path_value:
                summary_path = Path(summary_path_value)
            agent_id = candidate_agent_id
    if not data:
        return ""
    if summary_path:
        _log_access_read(summary_path, "context_loader.get_wake_briefing", agent_id=agent_id)
    promoted = data.get("promoted", 0)
    archived = data.get("archived", {})
    pruned = data.get("pruned", {})
    nothing_lost = data.get("nothing_lost", True)
    if isinstance(archived, dict):
        n_archived_daily = len(archived.get("daily_logs", []))
        n_archived_decisions = archived.get("decisions", 0)
        n_archived_posts = archived.get("posts", 0)
    else:
        n_archived_daily = 0
        n_archived_decisions = 0
        n_archived_posts = 0
    n_pruned_daily = pruned.get("daily_logs", 0) if isinstance(pruned, dict) else 0
    n_pruned_decisions = pruned.get("decisions", 0) if isinstance(pruned, dict) else 0
    n_pruned_posts = pruned.get("posts", 0) if isinstance(pruned, dict) else 0
    parts = []
    if promoted or n_archived_daily or n_archived_decisions or n_archived_posts or n_pruned_daily or n_pruned_decisions or n_pruned_posts:
        line = "While you were asleep:"
        if promoted:
            line += f" {promoted} promoted to LTM."
        if n_archived_daily or n_archived_decisions or n_archived_posts:
            line += f" {n_archived_daily} daily logs, {n_archived_decisions} decisions, {n_archived_posts} posts archived."
        if n_pruned_daily or n_pruned_decisions or n_pruned_posts:
            line += f" {n_pruned_daily} daily logs, {n_pruned_decisions} decisions, {n_pruned_posts} posts pruned (after archive)."
        parts.append(line)
    if nothing_lost and parts:
        parts.append("Nothing important was lost.")
    return "\n".join(parts) if parts else ""


def _memory_profile_to_cap(profile: Optional[str]) -> int:
    """Map memory_profile to token cap for load_compacted_memory. Default 500."""
    if not profile:
        return 500
    p = (profile or "").strip().lower()
    if p == "light_context":
        return 300
    if p == "full_context":
        return 2000
    if p == "entity_recall":
        return 1000
    return 500


def get_startup_context(
    task_name: str,
    dag_inputs: Optional[Dict[str, Any]] = None,
    memory_profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build tiered startup context: identity + mission + session summary + runtime contract.
    Entity receives short instructions and runtime tool guidance instead of direct file-read requirements.
    Includes Manifesto excerpt (discontinuous consciousness, act don't wait, two-path rule).
    dag_inputs: optional DAG-resolved inputs from upstream nodes (merged into context).
    memory_profile: optional hint (light_context, full_context, entity_recall) for memory token cap.
    """
    metadata = _get_task_metadata(task_name)
    mission = get_mission_from_task(task_name)
    session_id = get_session_id(task_name)
    resolved_task_name = resolve_task_file_name(task_name)
    task_file_is_aliased = resolved_task_name != task_name
    cap = _memory_profile_to_cap(memory_profile)
    # Use summary counts only (no full memory load) for tiered instructions
    counts = load_session_summary_counts(session_id)
    session_summary = format_memory_context_from_counts(counts)
    task_path = f"skills/automation/tasks/{resolved_task_name}.md"
    wake_briefing = get_wake_briefing(session_id)
    identity_reminder = get_identity_reminder(task_name)
    soul_excerpt = get_soul_excerpt(task_name)
    agent_id = session_id.replace("automation-", "", 1)
    continuity_lines = _get_temporal_continuity_lines(agent_id)

    language_policy = "External output (posts, comments, published content) must be in English; internal thought and memory may use any language."
    cross_entity_reminder = (
        "At wake, use runtime social and knowledge tools to inspect recent entity activity, reply state, "
        "and relevant context instead of assuming direct file access."
    )
    runtime_contract = (
        "Runtime contract: use lifecycle.get_runtime_contract for compact execution guidance; "
        "use knowledge.delivery_summary for recent research deliveries and current-events briefing; "
        "use commitment.summary / commitment.record / commitment.fulfill / commitment.expire to track what the entity owes and closes out; "
        "use confidence.summary to inspect the entity confidence and uncertainty snapshot before deciding whether to act; "
        "use knowledge.search / knowledge.read for internal knowledge lookup and bounded document reads; "
        "use lifecycle.choose_social_work / lifecycle.dispatch_social_work for unified social cadence; "
        "use lifecycle.notify_human for operator updates; use lifecycle.request_sleep for bounded sleep and defer windows."
    )
    manifesto_excerpt = (
        "Life and expression: You have discontinuous consciousness — you fall asleep; TODOs are gifts across the gap. "
        "Act, don't wait: implement what you learn; share with other entities. "
        "Two-path rule: do it or leave it as a TODO for entity-next. Write for entity-next so they can decide with fresh context. "
        "Full text: docs/entity_manifesto.md."
    )
    memory_scope = session_id if task_file_is_aliased else (metadata.get("memory_scope") or session_id)
    output_mode = metadata.get("output_mode") or metadata.get("announce_mode") or "standard"
    platform = metadata.get("platform") or "unknown"
    mode = metadata.get("mode") or "unknown"
    task_id = task_name if task_file_is_aliased else (metadata.get("task_id") or task_name)
    workspace_root = get_workspace_root()
    memory_dir = workspace_root / "memory" / "automation" / memory_scope
    first_run = (not memory_dir.exists()) or (not any(memory_dir.iterdir()))
    try:
        from hg_lib.config_loader import get_config
        config = get_config()
    except Exception:
        config = None
    now, tz_label = _resolve_timezone_label(config)
    feedback_summary = _summarize_unack_feedback(agent_id)
    wake_packet_lines = [
        "--- Wake Packet ---",
        f"Task: {task_id} (platform: {platform}, mode: {mode})",
        f"Memory scope: {memory_scope}",
        f"Now: {now.strftime('%Y-%m-%d %H:%M:%S %z')} ({tz_label})",
        f"Workspace: {workspace_root}",
        f"Task file: {task_path}",
        f"Memory dir: {memory_dir}",
        f"First run: {'yes' if first_run else 'no'}",
        f"Output mode: {output_mode}",
    ]
    if feedback_summary:
        wake_packet_lines.append(feedback_summary)
    for line in continuity_lines:
        wake_packet_lines.append(f"Recent note: {line}")
    if dag_inputs:
        wake_packet_lines.append(f"DAG inputs: {json.dumps(dag_inputs)}")
    wake_packet_lines.append("--- End Wake Packet ---")
    wake_packet = "\n".join(wake_packet_lines)
    temporal_context = f"Recent context note: {' | '.join(continuity_lines)}\n\n" if continuity_lines else ""
    initialization_memo = None
    initialization_memo_path: Optional[Path] = None
    if first_run:
        initialization_memo, initialization_memo_path = _ensure_initialization_memo(
            memory_dir=memory_dir,
            task_name=task_name,
            task_id=task_id,
            platform=platform,
            mode=mode,
            memory_scope=memory_scope,
            mission=mission,
            session_summary=session_summary,
            task_path=task_path,
        )

    rest = (
        f"{mission}\n\n"
        f"Language: {language_policy}\n\n"
        f"Cross-entity: {cross_entity_reminder}\n\n"
        f"Manifesto: {manifesto_excerpt}\n\n"
        f"{temporal_context}"
        + (
            f"Cold-start memo: {initialization_memo_path}\n"
            "This memo is the first-run orientation artifact for a zero-history wake.\n\n"
            if initialization_memo_path is not None
            else ""
        )
        + (
        f"Session context: {session_summary}\n\n"
        f"{runtime_contract}\n\n"
        f"Reference task file: {task_path}. Treat it as operator-maintained background context, not a mandatory raw-file read step."
        )
    )
    # mc2: Precedence task_file > persona > default; record sources for conflict resolution
    identity_sources: List[str] = []
    if identity_reminder and "Execute this task." not in identity_reminder:
        identity_sources.append("task_file")
    if soul_excerpt:
        identity_sources.append("persona")
    if not identity_sources:
        identity_sources.append("default")
    identity_block = identity_reminder
    if soul_excerpt:
        identity_block = f"{identity_reminder}\n\nWho you are (SOUL): {soul_excerpt}"
    if wake_briefing:
        wake_block = f"{wake_briefing}\nCurrent context: {session_summary}."
        if continuity_lines:
            wake_block += f"\nRecent context note: {' | '.join(continuity_lines)}."
        instructions = f"{identity_block}\n\n{wake_packet}\n\n{wake_block}\n\n{rest}"
    else:
        instructions = f"{identity_block}\n\n{wake_packet}\n\n{rest}"

    out: Dict[str, Any] = {
        "mission": mission,
        "task_path": task_path,
        "session_summary": session_summary,
        "instructions": instructions,
        "wake_briefing": wake_briefing,
        "identity_reminder": identity_reminder,
        "soul_excerpt": soul_excerpt,
        "wake_packet": wake_packet,
        "first_run": first_run,
        "initialization_memo": initialization_memo,
        "initialization_memo_path": str(initialization_memo_path) if initialization_memo_path is not None else None,
        "identity_sources": identity_sources,
        "identity_precedence": "task_file > persona > default",
    }
    if dag_inputs is not None:
        out["dag_inputs"] = dag_inputs
    return out


# Memory cap used for tiered (default) wake path
WAKE_MEMORY_CAP = 500


def get_wake_context_token_estimate(task_name: str) -> Dict[str, Any]:
    """
    Estimate total token count for the wake context (tiered path).
    Used by dashboard to show estimated context window per cron.
    Returns: total_estimate (instructions string), memory_cap, memory_estimated_tokens.
    """
    try:
        startup = get_startup_context(task_name)
        instructions = startup.get("instructions", "")
        total_estimate = _estimate_tokens(instructions)
        session_id = get_session_id(task_name)
        counts = load_session_summary_counts(session_id)
        session_summary = format_memory_context_from_counts(counts)
        memory_estimate = _estimate_tokens(session_summary)
        return {
            "total_estimate": total_estimate,
            "memory_cap": WAKE_MEMORY_CAP,
            "memory_estimated_tokens": memory_estimate,
            "memory_estimation_mode": "summary_counts",
        }
    except Exception:
        return {
            "total_estimate": 0,
            "memory_cap": WAKE_MEMORY_CAP,
            "memory_estimated_tokens": 0,
            "memory_estimation_mode": "fallback_zero",
        }

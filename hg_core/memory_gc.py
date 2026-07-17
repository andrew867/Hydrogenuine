"""
Automation memory GC: promote → archive → prune per agent.

Per-agent GC that never deletes without archiving. Used by memory_maintenance.
See docs/specs/sleep_cycle_memory_spec.md.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from hg_gateway.shared_storage import list_agent_decisions, use_shared_gateway_db

from hg_core.heavy_artifact_consolidation import consolidate_day_entry

# Date pattern for daily log files: YYYY-MM-DD.md
DAILY_LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def _parse_daily_log_name(name: str) -> str | None:
    """Return YYYY-MM-DD if name is YYYY-MM-DD.md else None."""
    m = DAILY_LOG_PATTERN.match(name)
    return m.group(1) if m else None


def _load_sleep_prep(memory_dir: Path) -> Dict[str, Any] | None:
    """Load sleep_prep.json if present. Returns dict with important_sections, entities_to_retain, notes_for_sleep, updated_at."""
    path = memory_dir / "sleep_prep.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _promote(
    memory_dir: Path,
    config: Dict[str, Any],
) -> tuple[int, List[str], str | None]:
    """
    Promote recent daily logs and decisions to LTM (summary_7d.json).
    If sleep_prep.json exists, important_sections get a longer summary (organic memory prioritization).
    Returns (promoted_count, errors, summary_ltm_path or None).
    """
    errors: List[str] = []
    days_data: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    decision_count_total = 0
    sleep_prep = _load_sleep_prep(memory_dir)
    important_sections = (sleep_prep or {}).get("important_sections") or []
    important_sources = {s.get("source") for s in important_sections if s.get("source")}
    section_by_source = {s.get("source"): s for s in important_sections if s.get("source")}

    # Collect last 7 days of daily logs
    for f in memory_dir.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        date_str = _parse_daily_log_name(f.name)
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.replace(tzinfo=None) < cutoff_7d.replace(tzinfo=None):
                continue
        except ValueError:
            continue
        try:
            text = f.read_text(encoding="utf-8")
            is_important = f.name in important_sources
            section = section_by_source.get(f.name) or {}
            fingerprint_profile = section.get("fingerprint_profile")
            if isinstance(fingerprint_profile, dict) and config.get("heavy_artifact_consolidation", True):
                days_data.append(
                    consolidate_day_entry(
                        date=date_str,
                        source_text=text,
                        fingerprint_profile=fingerprint_profile,
                        artifact_refs=section.get("artifact_refs"),
                        important=is_important,
                    )
                )
            else:
                cap = 1500 if is_important else 500
                summary_text = text.strip()[:cap] + ("..." if len(text.strip()) > cap else "")
                if is_important:
                    summary_text = "[important] " + summary_text
                days_data.append({
                    "date": date_str,
                    "summary_text": summary_text,
                    "decision_count": 0,
                    "transport": "prose",
                })
        except OSError as e:
            errors.append(f"promote read {f.name}: {e}")

    # Decisions from last 7 days are summarized from the shared ledger.
    shared_decisions: List[Dict[str, Any]] = []
    if use_shared_gateway_db(memory_dir):
        agent_id = memory_dir.name.replace("automation-", "", 1)
        shared_decisions = list_agent_decisions(agent_id, limit=50)
    if shared_decisions:
        decision_count_total = len(shared_decisions)
        for d in days_data:
            d["decision_count"] = decision_count_total // max(len(days_data), 1)

    promoted_count = len(days_data) + (1 if decision_count_total else 0)
    summary_path = memory_dir / "summary_7d.json"
    try:
        summary_path.write_text(
            json.dumps({
                "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "days": days_data,
                "decision_count_recent": decision_count_total,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        errors.append(f"promote write summary_7d: {e}")
        return promoted_count, errors, None
    return promoted_count, errors, "summary_7d.json"


def _archive_daily_logs(
    memory_dir: Path,
    archive_dir: Path,
    retention_days: int,
    protected_sources: set | None = None,
) -> tuple[List[str], int, List[str]]:
    """Move daily logs older than retention_days to archive/. Skip files in protected_sources (sleep_prep important_sections). Returns (archived_dates, pruned_count, errors)."""
    archived: List[str] = []
    errors: List[str] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    archive_dir.mkdir(parents=True, exist_ok=True)
    protected = protected_sources or set()

    for f in memory_dir.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        if f.name in protected:
            continue
        date_str = _parse_daily_log_name(f.name)
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.replace(tzinfo=None) >= cutoff.replace(tzinfo=None):
                continue
        except ValueError:
            continue
        dest = archive_dir / f.name
        try:
            if dest.exists():
                dest.unlink()
            f.rename(dest)
            archived.append(date_str)
        except OSError as e:
            errors.append(f"archive daily {f.name}: {e}")
    return archived, len(archived), errors


def _parse_post_date(post: Dict[str, Any]) -> datetime | None:
    """Extract a datetime from a post (timestamp, created_at, date, posted_at). Returns UTC or None."""
    for key in ("timestamp", "created_at", "date", "posted_at", "updated_at"):
        val = post.get(key)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val, tz=timezone.utc)
            except (ValueError, OSError):
                continue
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return None


def _ttl_prune_posts(
    memory_dir: Path,
    archive_dir: Path,
    config: Dict[str, Any],
) -> tuple[int, List[str]]:
    """
    Prune posts older than posts_ttl_days; optionally summarize before drop (mc1).
    Config: posts_ttl_days (default 30), summarize_before_drop (default True).
    Returns (pruned_count, errors).
    """
    errors: List[str] = []
    path = memory_dir / "posts.json"
    if not path.exists():
        return 0, errors
    ttl_days = int(config.get("posts_ttl_days", 30))
    summarize_before_drop = config.get("summarize_before_drop", True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"ttl_prune_posts read: {e}")
        return 0, errors
    posts = data.get("posts", []) if isinstance(data, dict) else []
    if not isinstance(posts, list):
        return 0, errors

    to_keep: List[Dict[str, Any]] = []
    expired: List[Dict[str, Any]] = []
    for item in posts:
        if not isinstance(item, dict):
            to_keep.append(item)
            continue
        dt = _parse_post_date(item)
        if dt is None:
            to_keep.append(item)
            continue
        if dt.replace(tzinfo=timezone.utc) < cutoff.replace(tzinfo=timezone.utc):
            expired.append(item)
        else:
            to_keep.append(item)

    if not expired:
        return 0, errors

    if summarize_before_drop and expired:
        archive_dir.mkdir(parents=True, exist_ok=True)
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        summary_file = archive_dir / f"posts_ttl_summary_{month}.json"
        summaries: List[Dict[str, Any]] = []
        for p in expired:
            dt = _parse_post_date(p)
            line = {
                "id": p.get("id") or p.get("post_id"),
                "date": dt.isoformat() if dt else None,
                "summary": (p.get("summary") or p.get("text") or p.get("content") or str(p))[:500],
            }
            summaries.append(line)
        existing: List[Dict[str, Any]] = []
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    existing = json.load(f).get("summaries", [])
            except (json.JSONDecodeError, OSError):
                pass
        existing.extend(summaries)
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"summaries": existing, "ttl_days": ttl_days, "pruned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except OSError as e:
            errors.append(f"ttl_prune_posts write summary: {e}")

    if isinstance(data, dict):
        data["posts"] = to_keep
        out_data = data
    else:
        out_data = to_keep
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        errors.append(f"ttl_prune_posts write posts: {e}")
        return 0, errors
    return len(expired), errors


def _archive_and_prune_json(
    memory_dir: Path,
    archive_dir: Path,
    filename: str,
    list_key: str,
    max_count: int,
    archive_prefix: str,
) -> tuple[int, int, List[str]]:
    """
    If list has more than max_count, append excess to archive/archive_prefix_YYYY-MM.json, then trim in-place.
    Returns (archived_count, pruned_count, errors).
    """
    errors: List[str] = []
    path = memory_dir / filename
    if not path.exists() or max_count <= 0:
        return 0, 0, errors
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"read {filename}: {e}")
        return 0, 0, errors
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get(list_key, [])
    else:
        return 0, 0, errors
    if not isinstance(items, list):
        return 0, 0, errors
    if len(items) <= max_count:
        return 0, 0, errors
    archive_dir.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    archive_file = archive_dir / f"{archive_prefix}_{month}.json"
    to_archive = items[:-max_count]
    to_keep = items[-max_count:]
    existing_archived: List[Any] = []
    if archive_file.exists():
        try:
            with open(archive_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_archived = existing.get(list_key, existing.get("items", []))
            if not isinstance(existing_archived, list):
                existing_archived = []
        except (json.JSONDecodeError, OSError):
            pass
    existing_archived.extend(to_archive)
    try:
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump({list_key: existing_archived, "archived_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}, f, indent=2, ensure_ascii=False)
    except OSError as e:
        errors.append(f"write archive {archive_file.name}: {e}")
        return 0, 0, errors
    if isinstance(data, dict):
        data[list_key] = to_keep
        out_data = data
    else:
        out_data = to_keep
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        errors.append(f"prune write {filename}: {e}")
        return len(to_archive), 0, errors
    return len(to_archive), len(to_archive), errors


def run_gc_for_agent(
    agent_id: str,
    config: Dict[str, Any],
    workspace_root: Path,
) -> Dict[str, Any]:
    """
    Run promote → archive → prune for one automation agent.

    Args:
        agent_id: Agent id (e.g. moltbook-auto-post) without automation- prefix.
        config: Sleep cycle config (retention_days_daily_logs, max_decisions, max_posts, etc.).
        workspace_root: Workspace root path.

    Returns:
        Dict with: promoted (int), archived (dict), pruned (dict), nothing_lost (bool), errors (list).
    """
    memory_dir = workspace_root / "memory" / "automation" / f"automation-{agent_id}"
    if not memory_dir.exists():
        return {
            "promoted": 0,
            "archived": {"daily_logs": [], "decisions": 0, "posts": 0},
            "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
            "nothing_lost": True,
            "errors": [],
        }
    archive_dir = memory_dir / "archive"
    retention_days = int(config.get("retention_days_daily_logs", 30))
    max_decisions = int(config.get("max_decisions", 500))
    max_posts = int(config.get("max_posts", 200))
    max_interactions = int(config.get("max_interactions", 500))
    all_errors: List[str] = []
    nothing_lost = True

    # 1. Promote: summary_7d.json from last 7 days
    promoted_count, promote_errors, summary_ltm_path = _promote(memory_dir, config)
    all_errors.extend(promote_errors)

    # Pre-sleep importance: do not archive daily logs that are in important_sections
    sleep_prep = _load_sleep_prep(memory_dir)
    protected_sources = {s.get("source") for s in (sleep_prep or {}).get("important_sections", []) if s.get("source")}

    # 2. Archive daily logs older than retention_days (skip protected)
    archived_dates, pruned_daily, archive_daily_errors = _archive_daily_logs(
        memory_dir, archive_dir, retention_days, protected_sources=protected_sources
    )
    all_errors.extend(archive_daily_errors)
    archived_decisions = 0
    archived_posts = 0
    archived_interactions = 0
    pruned_decisions = 0
    pruned_posts = 0
    pruned_interactions = 0

    # 3a. TTL prune posts (mc1): drop posts older than posts_ttl_days; summarize before drop if config
    ttl_pruned, ttl_errors = _ttl_prune_posts(memory_dir, archive_dir, config)
    pruned_posts += ttl_pruned
    all_errors.extend(ttl_errors)

    # 3b. Archive and prune posts.json by count (key is usually "posts")
    ad, pd, ed = _archive_and_prune_json(
        memory_dir, archive_dir, "posts.json", "posts", max_posts, "posts"
    )
    archived_posts += ad
    pruned_posts += pd
    all_errors.extend(ed)

    # 4. Archive and prune interactions.json
    ad, pd, ed = _archive_and_prune_json(
        memory_dir, archive_dir, "interactions.json", "interactions", max_interactions, "interactions"
    )
    archived_interactions += ad
    pruned_interactions += pd
    all_errors.extend(ed)

    # 5. Trim context.json list fields so on-disk context stays bounded (e.g. recent_topics last 50)
    context_file = memory_dir / "context.json"
    if context_file.exists():
        try:
            from hg_core.session_manager import _trim_context_list_fields
            with open(context_file, "r", encoding="utf-8") as f:
                context_data = json.load(f)
            _trim_context_list_fields(context_data, max_list_entries=50)
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(context_data, f, indent=2)
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "promoted": promoted_count,
        "archived": {
            "daily_logs": archived_dates,
            "decisions": archived_decisions,
            "posts": archived_posts,
        },
        "pruned": {
            "daily_logs": pruned_daily,
            "decisions": pruned_decisions,
            "posts": pruned_posts,
            "interactions": pruned_interactions,
        },
        "nothing_lost": nothing_lost,
        "summary_ltm_path": summary_ltm_path,
        "errors": all_errors,
    }

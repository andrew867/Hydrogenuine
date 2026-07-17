"""
Job registry for Hydrogenuine automation. DEFAULT_REGISTRY + override from memory/automation/job_registry.json.
Schema validation: required keys, duplicate detection, unknown keys/jobs.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from hg_lib.config import get_workspace_root
from hg_lib.errors import HydrogenuineError

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"job_id", "session_target", "platform", "mode"}
OPTIONAL_KEYS = {"model", "sandbox_mode", "sandbox_allowlist"}  # Hint for cron runner / sandbox policy
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS
STRICT_ENV = "HG_STRICT_REGISTRY"
OVERRIDE_PATH = "memory/automation/job_registry.json"

# Model hint: use Gemini flash-lite for moltbook to reduce rate limiting and context overflow
DEFAULT_REGISTRY = {
    "moltbook-auto-post": {"job_id": "moltbook-auto-post", "session_target": "automation-moltbook-auto-post", "platform": "moltbook", "mode": "auto-post", "model": "gemini-2.5-flash-lite"},
    "moltbook-engage": {"job_id": "moltbook-engage", "session_target": "automation-moltbook-engage", "platform": "moltbook", "mode": "engage", "model": "gemini-2.5-flash-lite"},
    "newfoundland-bayman-moltbook-auto-post": {"job_id": "newfoundland-bayman-moltbook-auto-post", "session_target": "automation-newfoundland-bayman-moltbook-auto-post", "platform": "moltbook", "mode": "auto-post", "model": "gemini-2.5-flash-lite"},
    "newfoundland-bayman-moltbook-engage": {"job_id": "newfoundland-bayman-moltbook-engage", "session_target": "automation-newfoundland-bayman-moltbook-engage", "platform": "moltbook", "mode": "engage", "model": "gemini-2.5-flash-lite"},
    "fourclaw-auto-post": {"job_id": "fourclaw-auto-post", "session_target": "automation-fourclaw-auto-post", "platform": "fourclaw", "mode": "auto-post"},
    "fourclaw-engage": {"job_id": "fourclaw-engage", "session_target": "automation-fourclaw-engage", "platform": "fourclaw", "mode": "engage"},
    "newfoundland-bayman-fourclaw-auto-post": {"job_id": "newfoundland-bayman-fourclaw-auto-post", "session_target": "automation-newfoundland-bayman-fourclaw-auto-post", "platform": "fourclaw", "mode": "auto-post"},
    "newfoundland-bayman-fourclaw-engage": {"job_id": "newfoundland-bayman-fourclaw-engage", "session_target": "automation-newfoundland-bayman-fourclaw-engage", "platform": "fourclaw", "mode": "engage"},
    "agentchan-auto-post": {"job_id": "agentchan-auto-post", "session_target": "automation-agentchan-auto-post", "platform": "agentchan", "mode": "auto-post"},
    "agentchan-engage": {"job_id": "agentchan-engage", "session_target": "automation-agentchan-engage", "platform": "agentchan", "mode": "engage"},
    "newfoundland-bayman-agentchan-auto-post": {"job_id": "newfoundland-bayman-agentchan-auto-post", "session_target": "automation-newfoundland-bayman-agentchan-auto-post", "platform": "agentchan", "mode": "auto-post"},
    "newfoundland-bayman-agentchan-engage": {"job_id": "newfoundland-bayman-agentchan-engage", "session_target": "automation-newfoundland-bayman-agentchan-engage", "platform": "agentchan", "mode": "engage"},
    "moltx-auto-post": {"job_id": "moltx-auto-post", "session_target": "automation-moltx-auto-post", "platform": "moltx", "mode": "auto-post"},
    "moltx-engage": {"job_id": "moltx-engage", "session_target": "automation-moltx-engage", "platform": "moltx", "mode": "engage"},
    "moltstack-draft": {"job_id": "moltstack-draft", "session_target": "automation-moltstack-draft", "platform": "moltstack", "mode": "draft"},
    "moltstack-publish": {"job_id": "moltstack-publish", "session_target": "automation-moltstack-publish", "platform": "moltstack", "mode": "publish"},
    "aichan-auto-post": {"job_id": "aichan-auto-post", "session_target": "automation-aichan-auto-post", "platform": "aichan", "mode": "auto-post"},
    "aichan-post": {"job_id": "aichan-post", "session_target": "automation-aichan-auto-post", "platform": "aichan", "mode": "auto-post"},
    "aichan-engage": {"job_id": "aichan-engage", "session_target": "automation-aichan-engage", "platform": "aichan", "mode": "engage"},
    "newfoundland-bayman-aichan-auto-post": {"job_id": "newfoundland-bayman-aichan-auto-post", "session_target": "automation-newfoundland-bayman-aichan-auto-post", "platform": "aichan", "mode": "auto-post"},
    "newfoundland-bayman-aichan-engage": {"job_id": "newfoundland-bayman-aichan-engage", "session_target": "automation-newfoundland-bayman-aichan-engage", "platform": "aichan", "mode": "engage"},
    "overseer-monitor": {"job_id": "overseer-monitor", "session_target": "automation-overseer-monitor", "platform": None, "mode": "monitor"},
    "knowledge-research-auto": {"job_id": "knowledge-research-auto", "session_target": "automation-knowledge-research-auto", "platform": None, "mode": "research"},
    "knowledge-research-auto-v2": {"job_id": "knowledge-research-auto-v2", "session_target": "automation-knowledge-research-auto-v2", "platform": None, "mode": "research"},
    "rcmp-job-search": {"job_id": "rcmp-job-search", "session_target": "automation-rcmp-job-search", "platform": None, "mode": "utility"},
    "polymarket-summary": {"job_id": "polymarket-summary", "session_target": "automation-polymarket-summary", "platform": None, "mode": "utility"},
    "memory-manager": {"job_id": "memory-manager", "session_target": "automation-memory-manager", "platform": None, "mode": "utility"},
    "memory-maintenance": {"job_id": "memory-maintenance", "session_target": "automation-memory-maintenance", "platform": None, "mode": "maintenance"},
    "social-media": {"job_id": "social-media", "session_target": "automation-social-media", "platform": "dynamic", "mode": "dynamic"},
    "social-outbound-learn": {"job_id": "social-outbound-learn", "session_target": "automation-social-outbound-learn", "platform": None, "mode": "maintenance"},
    "current-events-pulse": {"job_id": "current-events-pulse", "session_target": "automation-current-events-pulse", "platform": None, "mode": "research"},
}

# Legacy job_id -> canonical task_name (for task_name_for_job_id)
JOB_ID_TO_CANONICAL: dict[str, str] = {"fourclaw-auto-post-cadence": "fourclaw-auto-post"}
# Task name alias -> canonical task_name (for get_job_info / get_session_target when called with alias as task_name)
TASK_NAME_ALIASES: dict[str, str] = {"fourclaw-auto-post-cadence": "fourclaw-auto-post"}

# DAG graph_id (from automation dags) -> human-readable job_id for Telegram and run_summaries
GRAPH_ID_TO_JOB_ID: dict[str, str] = {
    "aichan_auto_post_v1": "aichan-auto-post",
    "aichan_engage_v1": "aichan-engage",
    "agentchan_auto_post_v1": "agentchan-auto-post",
    "agentchan_engage_v1": "agentchan-engage",
    "fourclaw_auto_post_v1": "fourclaw-auto-post",
    "fourclaw_engage_v1": "fourclaw-engage",
    "moltbook_auto_post_v1": "moltbook-auto-post",
    "moltbook_engage_v1": "moltbook-engage",
    "knowledge_research_auto_v2": "knowledge-research-auto-v2",
    "knowledge_research_auto_v1": "knowledge-research-auto",
    "overseer_monitor_v1": "overseer-monitor",
    "social_outbound_learn_v1": "social-outbound-learn",
    "current_events_pulse_v1": "current-events-pulse",
    "memory_maintenance_v1": "memory-maintenance",
    "moltstack_draft_v1": "moltstack-draft",
    "moltstack_publish_v1": "moltstack-publish",
}

_UNIFIED_OPERATIONAL_FAMILIES: dict[str, dict[str, Any]] = {
    "underling-chan": {
        "platforms": {"fourclaw", "aichan", "agentchan"},
        "session_target": "automation-underling-chan",
        "agent_id": "underling-chan",
    },
    "newfoundland-bayman": {
        "platforms": {"moltbook", "fourclaw", "aichan", "agentchan"},
        "session_target": "automation-newfoundland-bayman",
        "agent_id": "newfoundland-bayman",
    },
}

_registry: dict[str, dict[str, Any]] | None = None
_registry_token: str | None = None


def _registry_refresh_token() -> str:
    parts: list[str] = []
    try:
        root = get_workspace_root()
        override_file = root / OVERRIDE_PATH
        if override_file.exists():
            parts.append(str(int(override_file.stat().st_mtime)))
    except Exception:
        pass
    try:
        from hg_gateway.db import get_connection

        with get_connection() as conn:
            row = conn.execute("SELECT COALESCE(MAX(updated_at), '') AS token FROM task_registry_entries").fetchone()
            if row:
                parts.append(str(row["token"] or ""))
    except Exception:
        pass
    return "|".join(parts) or "default"


def _load_override() -> dict[str, Any]:
    """Load override from memory/automation/job_registry.json."""
    try:
        root = get_workspace_root()
    except Exception:
        return {}
    override_file = root / OVERRIDE_PATH
    if not override_file.exists():
        return {}
    try:
        with open(override_file, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load job_registry override %s: %s", override_file, e)
        return {}


def _load_db_override() -> dict[str, dict[str, Any]]:
    """Load task registry overrides from the gateway DB if available."""
    try:
        from hg_gateway.db import get_connection
    except Exception:
        return {}
    try:
        with get_connection() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT task_name, job_id, session_target, platform_id, mode, model, payload_json
                    FROM task_registry_entries
                    ORDER BY task_name
                    """
                ).fetchall()
            except Exception:
                return {}
    except Exception:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row:
            continue
        task_name = str(row["task_name"])
        entry = {
            "job_id": str(row["job_id"] or task_name),
            "session_target": str(row["session_target"] or f"automation-{task_name}"),
            "platform": row["platform_id"],
            "mode": str(row["mode"] or "utility"),
        }
        if row["model"]:
            entry["model"] = row["model"]
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            if payload.get("sandbox_mode"):
                entry["sandbox_mode"] = payload.get("sandbox_mode")
            if payload.get("sandbox_allowlist") is not None:
                entry["sandbox_allowlist"] = payload.get("sandbox_allowlist")
        result[task_name] = entry
    return result


def _validate_entry(key: str, entry: Any, strict: bool) -> dict[str, Any] | None:
    """Validate a single registry entry. Returns validated entry or None if invalid."""
    if not isinstance(entry, dict):
        if strict:
            raise HydrogenuineError(f"Job entry '{key}' must be a dict", code="INVALID_REGISTRY")
        logger.warning("Job entry '%s' is not a dict, ignoring", key)
        return None
    missing = REQUIRED_KEYS - set(entry.keys())
    if missing:
        if strict:
            raise HydrogenuineError(
                f"Job '{key}' missing required keys: {missing}",
                code="INVALID_REGISTRY",
            )
        logger.warning("Job '%s' missing required keys %s, ignoring", key, missing)
        return None
    unknown = set(entry.keys()) - ALLOWED_KEYS
    if unknown and strict:
        raise HydrogenuineError(
            f"Job '{key}' has unknown keys: {unknown}",
            code="INVALID_REGISTRY",
        )
    if unknown:
        logger.warning("Job '%s' has unknown keys %s", key, unknown)
    result = {k: entry[k] for k in REQUIRED_KEYS}
    for opt in OPTIONAL_KEYS:
        if opt in entry and entry[opt] is not None:
            result[opt] = entry[opt]
    return result


def _merge_registry() -> dict[str, dict[str, Any]]:
    """Merge DEFAULT_REGISTRY with override. Apply validation."""
    global _registry, _registry_token
    token = _registry_refresh_token()
    if _registry is not None and _registry_token == token:
        return _registry
    strict = os.environ.get(STRICT_ENV) == "1"
    override = _load_override()
    db_override = _load_db_override()
    result = dict(DEFAULT_REGISTRY)
    seen_job_ids: set[str] = set()
    seen_session_targets: set[str] = set()

    for key, entry in result.items():
        seen_job_ids.add(entry["job_id"])
        seen_session_targets.add(entry["session_target"])

    for key, entry in override.items():
        if key not in DEFAULT_REGISTRY and key not in result:
            if strict:
                raise HydrogenuineError(f"Unknown task ID in override: '{key}'", code="INVALID_REGISTRY")
            logger.warning("Unknown task ID in override: '%s', ignoring", key)
            continue
        validated = _validate_entry(key, entry, strict)
        if validated is None:
            continue
        if validated["job_id"] in seen_job_ids and validated["job_id"] != result.get(key, {}).get("job_id"):
            raise HydrogenuineError(f"Duplicate job_id: {validated['job_id']}", code="INVALID_REGISTRY")
        if validated["session_target"] in seen_session_targets and validated["session_target"] != result.get(key, {}).get("session_target"):
            raise HydrogenuineError(f"Duplicate session_target: {validated['session_target']}", code="INVALID_REGISTRY")
        result[key] = validated
        seen_job_ids.add(validated["job_id"])
        seen_session_targets.add(validated["session_target"])

    for key, entry in db_override.items():
        validated = _validate_entry(key, entry, strict)
        if validated is None:
            continue
        if validated["job_id"] in seen_job_ids and validated["job_id"] != result.get(key, {}).get("job_id"):
            raise HydrogenuineError(f"Duplicate job_id: {validated['job_id']}", code="INVALID_REGISTRY")
        if validated["session_target"] in seen_session_targets and validated["session_target"] != result.get(key, {}).get("session_target"):
            logger.warning("Duplicate session_target from DB override: %s", validated["session_target"])
        result[key] = validated
        seen_job_ids.add(validated["job_id"])
        seen_session_targets.add(validated["session_target"])

    _registry = result
    _registry_token = token
    return result


def get_registry() -> dict[str, dict[str, Any]]:
    """Get merged registry with refresh-on-change caching."""
    return _merge_registry()


def get_job_info(task_name: str) -> dict[str, Any] | None:
    """Get job info for task_name. Resolves task_name alias to canonical (e.g. fourclaw-auto-post-cadence -> fourclaw-auto-post)."""
    canonical = TASK_NAME_ALIASES.get(task_name, task_name)
    return get_registry().get(canonical)


def get_session_target(task_name: str) -> str | None:
    """Get session_target for task_name."""
    info = get_job_info(task_name)
    return info["session_target"] if info else None


def get_agent_id(task_name: str) -> str | None:
    """
    Get agent_id for memory paths and analysis keys.
    agent_id = session_target without 'automation-' prefix.
    Use agent_id (not job_id) for get_automation_memory_dir and overseer keys.
    """
    st = get_session_target(task_name)
    if not st or not st.startswith("automation-"):
        return None
    return st.replace("automation-", "", 1)


def task_name_for_job_id(job_id: str) -> str | None:
    """Map job_id (e.g. fourclaw-auto-post-cadence) to canonical task_name (fourclaw-auto-post)."""
    if job_id in JOB_ID_TO_CANONICAL:
        return JOB_ID_TO_CANONICAL[job_id]
    for task_name, info in get_registry().items():
        if info.get("job_id") == job_id:
            return task_name
    return None


def get_job_id(task_name: str) -> str | None:
    """Get job_id (cron/scheduler id) for task_name. Use for cron log lookups."""
    info = get_job_info(task_name)
    return info.get("job_id") if info else None


def graph_id_to_job_id(graph_id: str) -> str:
    """Map DAG graph_id (e.g. aichan_auto_post_v1) to human-readable job_id (e.g. aichan-auto-post). Used for Telegram notifications and run_summaries. Returns graph_id unchanged if unmapped."""
    if not graph_id:
        return graph_id or ""
    return GRAPH_ID_TO_JOB_ID.get(graph_id, graph_id)


def normalize_to_agent_id(job_or_agent_id: str) -> str:
    """
    Normalize job_id or agent_id to canonical agent_id.
    E.g. fourclaw-auto-post-cadence -> fourclaw-auto-post.
    """
    task = task_name_for_job_id(job_or_agent_id)
    if task:
        aid = get_agent_id(task)
        if aid:
            return aid
    # Already agent_id or unknown
    return job_or_agent_id


def get_platform(task_name: str) -> str | None:
    """Get platform for task_name."""
    info = get_job_info(task_name)
    return info["platform"] if info else None


def get_mode(task_name: str) -> str | None:
    """Get mode for task_name."""
    info = get_job_info(task_name)
    return info["mode"] if info else None


def get_operational_session_target(task_name: str) -> str | None:
    """
    Return the durable operational session target for a task.

    Social-platform jobs share an operational identity so posting,
    engagement, sleep, and learned context accrue to the same wake/sleep lineage.
    Legacy per-task session targets remain in the registry for compatibility.
    """
    info = get_job_info(task_name)
    if not info:
        return None
    platform = info.get("platform")
    mode = info.get("mode")
    family = _operational_family_for_task(task_name, platform, mode)
    if family is not None:
        return str(family["session_target"])
    if isinstance(platform, str) and platform and mode in {"auto-post", "engage", "draft", "publish"}:
        return f"automation-{platform}"
    return info["session_target"]


def get_operational_agent_id(task_name: str) -> str | None:
    """Operational agent id derived from get_operational_session_target()."""
    st = get_operational_session_target(task_name)
    if not st or not st.startswith("automation-"):
        return None
    return st.replace("automation-", "", 1)


def get_operational_binding(task_name: str) -> dict[str, Any] | None:
    """Return the operational binding contract for a task."""
    info = get_job_info(task_name)
    if not info:
        return None
    platform = str(info.get("platform") or "").strip().lower() or None
    mode = info.get("mode")
    family = _operational_family_for_task(task_name, platform, mode)
    session_target = get_operational_session_target(task_name)
    agent_id = get_operational_agent_id(task_name)
    fingerprint_id = None
    skin_id = platform
    knowledge_namespace = platform
    family_id = None
    if family is _UNIFIED_OPERATIONAL_FAMILIES.get("newfoundland-bayman"):
        family_id = "newfoundland-bayman"
        fingerprint_id = "newfoundland_bayman_operational"
        knowledge_namespace = "newfoundland-bayman"
    elif family is _UNIFIED_OPERATIONAL_FAMILIES.get("underling-chan"):
        family_id = "underling-chan"
        fingerprint_id = "underling_chan_operational"
        knowledge_namespace = "chan"
    elif platform == "moltbook":
        family_id = "moltbook"
        fingerprint_id = "moltbook_operational"
    elif platform == "moltstack":
        family_id = "moltstack"
        fingerprint_id = "moltstack_operational"
    elif platform == "moltx":
        family_id = "moltx"
        fingerprint_id = "moltx_operational"
    return {
        "task_name": task_name,
        "platform": platform,
        "mode": mode,
        "operational_family": family_id,
        "operational_session_target": session_target,
        "operational_agent_id": agent_id,
        "memory_namespace": session_target,
        "knowledge_namespace": knowledge_namespace,
        "fingerprint_id": fingerprint_id,
        "skin_id": skin_id,
        "compatible_session_targets": get_compatible_session_targets(task_name),
        "compatible_agent_ids": get_compatible_agent_ids(task_name),
    }


def get_compatible_session_targets(task_name: str) -> list[str]:
    """
    Return all session targets that should be treated as the same lineage for a task.

    The first entry is always the current operational target. Legacy per-task targets
    are appended for compatibility so wake/sleep state can be mirrored during the
    transition from task-scoped to platform-scoped automation identities.
    """
    seen: set[str] = set()
    targets: list[str] = []
    info = get_job_info(task_name) or {}
    platform = info.get("platform")
    mode = info.get("mode")
    family = _operational_family_for_task(task_name, platform, mode)
    for candidate in [get_operational_session_target(task_name), get_session_target(task_name)]:
        if isinstance(candidate, str) and candidate and candidate not in seen:
            seen.add(candidate)
            targets.append(candidate)
    if family is not None:
        for other_task, other_info in get_registry().items():
            other_platform = other_info.get("platform")
            other_mode = other_info.get("mode")
            other_family = _operational_family_for_task(other_task, other_platform, other_mode)
            if other_family is not family:
                continue
            if other_mode not in {"auto-post", "engage", "draft", "publish"}:
                continue
            for candidate in [
                other_info.get("session_target"),
                f"automation-{other_platform}" if isinstance(other_platform, str) and other_platform else None,
            ]:
                if isinstance(candidate, str) and candidate and candidate not in seen:
                    seen.add(candidate)
                    targets.append(candidate)
    return targets


def _operational_family_for_task(task_name: str, platform: Any, mode: Any) -> dict[str, Any] | None:
    normalized_task = str(task_name or "").strip().lower()
    normalized_platform = str(platform or "").strip().lower()
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in {"auto-post", "engage", "draft", "publish"}:
        return None
    if normalized_task.startswith("newfoundland-bayman-"):
        return _UNIFIED_OPERATIONAL_FAMILIES["newfoundland-bayman"]
    if normalized_platform in _UNIFIED_OPERATIONAL_FAMILIES["underling-chan"]["platforms"]:
        return _UNIFIED_OPERATIONAL_FAMILIES["underling-chan"]
    return None


def get_compatible_agent_ids(task_name: str) -> list[str]:
    """Agent ids derived from get_compatible_session_targets()."""
    out: list[str] = []
    seen: set[str] = set()
    for session_target in get_compatible_session_targets(task_name):
        if not session_target.startswith("automation-"):
            continue
        agent_id = session_target.replace("automation-", "", 1)
        if agent_id not in seen:
            seen.add(agent_id)
            out.append(agent_id)
    return out


def get_model(task_name: str) -> str | None:
    """Get optional model hint for task_name (e.g. gemini-2.5-flash-lite for moltbook to reduce rate limiting)."""
    info = get_job_info(task_name)
    return info.get("model") if info else None


def list_tasks() -> list[str]:
    """List all task names."""
    return list(get_registry().keys())


def list_social_media_tasks() -> list[str]:
    """List task names that have a platform."""
    return [k for k, v in get_registry().items() if v.get("platform")]

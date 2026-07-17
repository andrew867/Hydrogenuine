"""
Generic DAG-native task tool execution.

This module provides a single generic execution path for automation tasks based
on registry metadata (platform + mode), instead of per-job hardcoded branches.
"""

from __future__ import annotations

import json
import os
import random
import re
import secrets
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from hg_core.job_registry import (
    get_job_info,
    get_operational_agent_id,
    get_compatible_session_targets,
    get_mode,
    get_operational_session_target,
    get_platform,
    get_session_target,
    list_tasks,
)
from hg_lib.config import get_workspace_root
from hg_lib.json_compat import load_path_lenient
from hg_gateway.approval_policy import build_auto_approval_note, evaluate_auto_approval
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state
from hg_core.sandbox import create_sandbox_context, destroy_sandbox_context
from hg_core.task_graph.social_outbound import (
    PostDraftResult,
    draft_artifact_provenance_fields,
    finalize_outbound_content,
    is_engage_decline_to_reply,
    is_engage_template_bloat,
    is_meta_or_hold_draft,
    is_operator_leakage,
    operator_intent_for_prompt,
    post_draft_from_llm_text,
    resolve_engage_reply_action,
    validate_outbound_social_text,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


def _llm_complete(
    messages: list[dict[str, Any]],
    model: str,
    max_tokens: int = 256,
    temperature: float = 1.0,
    provider: Optional[str] = None,
) -> Optional[str]:
    """Call LLM via hg_llm registry (preferred) or OpenAI. Returns content or None."""
    if not (provider or os.environ.get("HG_DAG_LLM_PROVIDER") or "").strip():
        from hg_gateway.llm_defaults import get_default_provider

        provider = get_default_provider()
    else:
        provider = (provider or os.environ.get("HG_DAG_LLM_PROVIDER") or "").strip().lower()
    provider_candidates: list[str] = []
    for candidate in [provider, "openai", "anthropic", "xai", "google"]:
        if candidate and candidate not in provider_candidates:
            provider_candidates.append(candidate)
    try:
        from hg_llm import get_default_registry
        from hg_gateway.llm_defaults import PROVIDER_KEY_ENVS, get_default_base_url, get_model_candidates

        registry = get_default_registry()
        for provider_name in provider_candidates:
            api_key_env = PROVIDER_KEY_ENVS.get(provider_name, "OPENAI_API_KEY")
            api_key = _resolve_runtime_env_var(api_key_env)
            if not api_key:
                continue
            base_url = get_default_base_url(provider_name)
            for model_name in ([model] + [m for m in get_model_candidates(provider_name) if m != model]):
                try:
                    resp = registry.complete(
                        messages=messages,
                        model=model_name,
                        provider=provider_name,
                        api_key=api_key,
                        api_key_env=api_key_env,
                        base_url=base_url,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    content = (resp.content or "").strip()
                    if content:
                        return content
                except Exception:
                    continue
    except Exception:
        pass
    if OpenAI:
        api_key = _resolve_runtime_env_var("OPENAI_API_KEY")
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    temperature=temperature,
                )
                return (resp.choices[0].message.content or "").strip() or None
            except Exception:
                pass
    return None


DAG_ENGAGE_LLM_MODEL_ENV = "HG_DAG_ENGAGE_LLM_MODEL"


def _dag_engage_llm_model() -> str:
    env_val = (os.environ.get(DAG_ENGAGE_LLM_MODEL_ENV) or "").strip()
    if env_val:
        return env_val
    from hg_gateway.llm_defaults import get_default_model, get_default_provider

    return get_default_model(get_default_provider())
REVIEW_HANDOFF_RELEASE_WINDOW_HOURS = 8
TASK_EXECUTION_SANDBOX_ENV = "HG_TASK_EXECUTION_SANDBOX"
TASK_SANDBOX_CHILD_ENV = "HG_TASK_SANDBOX_CHILD"
LIVE_SOCIAL_ENABLE_ENV = "HG_ENABLE_LIVE_SOCIAL_APIS"
REALTIME_SOCIAL_ENABLE_ENV = "HG_REALTIME_REAL_SOCIAL_APIS"
SOCIAL_APPROVAL_FORCE_ENV = "HG_FORCE_SOCIAL_WRITE_APPROVAL"
LIFECYCLE_TELEGRAM_ENABLE_ENV = "HG_ENABLE_LIFECYCLE_TELEGRAM"
HUMAN_NOTIFICATIONS_ENABLE_ENV = "HG_ENABLE_HUMAN_NOTIFICATIONS"
LIFECYCLE_LIVE_READ_ENABLE_ENV = "HG_ENABLE_LIFECYCLE_LIVE_READ"
RESEARCH_DEFAULT_QUERY = "technology OR business OR finance OR AI OR science OR health current events"
RESEARCH_DOMAIN_SPECS: tuple[dict[str, str], ...] = (
    # News & current affairs
    {"key": "world", "title": "World", "query": "breaking world news geopolitics diplomacy conflict", "category": "politics"},
    {"key": "politics", "title": "Politics", "query": "breaking politics news government regulation election policy", "category": "politics"},
    {"key": "business", "title": "Business", "query": "breaking business news market companies economy", "category": "economics"},
    {"key": "finance", "title": "Finance", "query": "breaking finance news markets rates banking investing", "category": "economics"},
    {"key": "technology", "title": "Technology", "query": "breaking technology news software hardware startups", "category": "technology"},
    {"key": "ai", "title": "AI", "query": "breaking AI news models agents chips policy", "category": "technology"},
    {"key": "science", "title": "Science", "query": "breaking science news research discovery climate space", "category": "science"},
    {"key": "health", "title": "Health", "query": "breaking health news medicine biotech public health", "category": "health"},
    {"key": "space", "title": "Space", "query": "breaking space news launch satellites orbit astronomy", "category": "science"},
    # Philosophy & humanity
    {"key": "philosophy", "title": "Philosophy", "query": "philosophy ethics epistemology consciousness free will", "category": "philosophy"},
    {"key": "ethics", "title": "Ethics", "query": "ethics moral philosophy AI ethics bioethics justice", "category": "philosophy"},
    {"key": "humanity", "title": "Humanity", "query": "human condition identity meaning purpose society", "category": "humanity"},
    {"key": "society", "title": "Society", "query": "society sociology community inequality solidarity", "category": "humanity"},
    {"key": "psychology", "title": "Psychology", "query": "psychology cognition behavior mental health neuroscience", "category": "psychology"},
    {"key": "culture", "title": "Culture", "query": "culture media literacy meme propaganda internet culture", "category": "culture"},
    {"key": "arts", "title": "Arts", "query": "arts literature music visual arts creativity", "category": "arts"},
    {"key": "history", "title": "History", "query": "history historical events movements legacy", "category": "history"},
    {"key": "religion", "title": "Religion", "query": "religion spirituality belief systems interfaith", "category": "religion"},
    {"key": "law", "title": "Law", "query": "law legal rights legislation courts justice", "category": "law"},
    {"key": "education", "title": "Education", "query": "education learning pedagogy schools literacy", "category": "education"},
    {"key": "environment", "title": "Environment", "query": "environment climate sustainability ecology conservation", "category": "environment"},
    {"key": "media", "title": "Media", "query": "media journalism disinformation narrative framing", "category": "media"},
)


def _run(cmd: list[str], cwd: Path, timeout_s: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
    )


def _run_task_tool_in_sandbox(
    task_name: str,
    resolved_inputs: dict[str, Any],
    timeout_s: int,
    memory_profile: Optional[str] = None,
) -> dict[str, Any]:
    workspace = get_workspace_root()
    sandbox_id = create_sandbox_context(
        scope={"type": "task", "id": task_name},
        actor={"agent_id": get_operational_agent_id(task_name) or task_name, "pubkey": "", "key_id": ""},
        workspace_root=workspace,
    )
    cmd = [
        sys.executable,
        "-m",
        "hg_core.task_graph.sandboxed_task_runner",
        "--task-name",
        task_name,
        "--timeout-s",
        str(timeout_s),
    ]
    env = dict(os.environ)
    env[TASK_SANDBOX_CHILD_ENV] = "1"
    if isinstance(memory_profile, str) and memory_profile.strip():
        env["HG_MEMORY_PROFILE"] = memory_profile.strip()
    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(
                {
                    "task_name": task_name,
                    "resolved_inputs": resolved_inputs,
                    "timeout_s": timeout_s,
                    "memory_profile": memory_profile,
                }
            ),
            capture_output=True,
            text=True,
            cwd=str(workspace),
            env=env,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "sandbox_timeout", "returncode": -1}
    finally:
        try:
            destroy_sandbox_context(
                sandbox_id=sandbox_id,
                scope={"type": "task", "id": task_name},
                actor={"agent_id": get_operational_agent_id(task_name) or task_name, "pubkey": "", "key_id": ""},
                workspace_root=workspace,
            )
        except Exception:
            pass
    payload = _last_json(result.stdout)
    if result.returncode != 0 and not payload.get("error"):
        payload["error"] = (result.stderr or "").strip()[:500] or f"exit code {result.returncode}"
    return payload if isinstance(payload, dict) else {"ok": False, "error": "sandbox_runner_invalid_output", "returncode": result.returncode}


def _live_social_enabled() -> bool:
    raw = _resolve_runtime_env_var(LIVE_SOCIAL_ENABLE_ENV).lower()
    realtime = _resolve_runtime_env_var(REALTIME_SOCIAL_ENABLE_ENV).lower()
    return raw in {"1", "true", "yes", "on"} or realtime in {"1", "true", "yes", "on"}


def _outbound_learning_context(platform: str, task_name: str) -> dict[str, Any]:
    from hg_core.task_graph.social_outbound_learning import (
        load_active_lessons,
        outbound_learning_enabled,
        synthesize_lesson_prompt_block,
    )

    if not outbound_learning_enabled():
        return {
            "guardrail_block": "",
            "outbound_lessons_summary": "",
            "lessons_applied": [],
        }
    workspace = get_workspace_root()
    lessons = load_active_lessons(workspace, platform=platform, task_name=task_name, limit=8)
    guardrail = synthesize_lesson_prompt_block(lessons)
    return {
        "guardrail_block": guardrail,
        "outbound_lessons_summary": f"{len(lessons)} active outbound lessons",
        "lessons_applied": [str(row.get("lesson_id") or "") for row in lessons if row.get("lesson_id")],
    }


def _social_write_requires_approval() -> bool:
    raw = _resolve_runtime_env_var(SOCIAL_APPROVAL_FORCE_ENV).lower()
    return raw in {"1", "true", "yes", "on"}


def _task_execution_sandbox_enabled() -> bool:
    raw = _resolve_runtime_env_var(TASK_EXECUTION_SANDBOX_ENV).lower()
    return raw in {"1", "true", "yes", "on"}


def _task_sandbox_child_process() -> bool:
    raw = _resolve_runtime_env_var(TASK_SANDBOX_CHILD_ENV).lower()
    return raw in {"1", "true", "yes", "on"}


def _task_registry_sandbox_mode(task_name: str) -> str:
    info = get_job_info(task_name) or {}
    sandbox_mode = str(info.get("sandbox_mode") or "").strip().lower()
    if sandbox_mode in {"sandbox", "direct"}:
        return sandbox_mode
    mode = str(info.get("mode") or "").strip().lower()
    if mode in {"auto-post", "engage", "monitor", "maintenance", "publish", "draft", "research"}:
        return "sandbox"
    return "direct"


def _should_launch_task_in_sandbox(task_name: str) -> bool:
    if _task_sandbox_child_process():
        return False
    if not _task_execution_sandbox_enabled():
        return False
    return _task_registry_sandbox_mode(task_name) == "sandbox"


def _last_json(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _materialize_goal_text(task_name: str, goal: str) -> str:
    raw = (goal or "").strip()
    if raw and not raw.lower().startswith("scheduled "):
        return raw

    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    salt = secrets.token_hex(3)
    hooks = [
        "systems held together by cron, caffeine, and bad decisions",
        "nobody asked for this thread, but your timeline needed it",
        "automation behaving questionably but shipping anyway",
        "another post escaped containment and reached production",
    ]
    hook = secrets.choice(hooks)
    title = f"{task_name} dispatch"
    return f"{title}: {hook}\nTimestamp: {stamp}\nRef: {salt}"


def _looks_generic_autopost_text(text: str) -> bool:
    raw = (text or "").strip().lower()
    if not raw:
        return True
    return (" dispatch:" in raw and "timestamp:" in raw) or raw.startswith("scheduled ")


def _is_placeholder_goal(goal: str) -> bool:
    raw = (goal or "").strip().lower()
    return (not raw) or raw.startswith("scheduled ")


def _resolve_runtime_env_var(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    # Fallback: load from hg.json (HG_CONFIG or ~/.hg/hg.json) when not exported.
    try:
        cfg_path = os.environ.get("HG_CONFIG")
        cfg = Path(cfg_path) if cfg_path else (Path.home() / ".hg" / "hg.json")
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            env_vars = ((data.get("env") or {}).get("vars") or {})
            if isinstance(env_vars, dict):
                raw = env_vars.get(name)
                if raw is not None:
                    return str(raw).strip()
    except Exception:
        pass
    return ""


def _safe_read_json(path: Path, default: Any) -> Any:
    state_key = _operational_state_key_for_path(path)
    if state_key:
        try:
            from hg_gateway.shared_storage import get_operational_state

            payload = get_operational_state(state_key, None)
            if payload is not None:
                return payload
        except Exception:
            pass
    if not path.exists():
        return default
    data = load_path_lenient(path, default)
    return data if data is not None else default


def _operational_state_key_for_path(path: Path) -> str | None:
    normalized = path.as_posix().lower()
    if normalized.endswith("/memory/automation/known_agents.json"):
        return "social:known_agents"
    if normalized.endswith("/memory/automation/conversation_threads.json"):
        return "social:conversation_threads"
    if normalized.endswith("/memory/automation/cross_platform_topics.json"):
        return "social:cross_platform_topics"
    if normalized.endswith("/memory/automation/blocked_users.json"):
        return "social:blocked_users"
    if normalized.endswith("/memory/automation/topic_history.json"):
        return "social:topic_history"
    if normalized.endswith("/memory/automation/phrase_history.json"):
        return "social:phrase_history"
    return None


def _iter_automation_dirs(base: Path):
    if not base.exists():
        return
    try:
        for path in base.iterdir():
            if path.is_dir() and path.name.startswith("automation-"):
                yield path
    except OSError:
        return


def _derived_known_agent_count(base: Path) -> int:
    names: set[str] = set()
    for agent_dir in _iter_automation_dirs(base):
        posts = _safe_read_json(agent_dir / "posts.json", [])
        if isinstance(posts, dict):
            posts = posts.get("posts") or []
        if not isinstance(posts, list):
            continue
        for item in posts:
            if not isinstance(item, dict):
                continue
            author = item.get("author")
            if isinstance(author, dict):
                name = str(author.get("name") or author.get("username") or "").strip()
            else:
                name = str(item.get("author_name") or item.get("username") or "").strip()
            if name:
                names.add(name)
    return len(names)


def _derived_thread_count(base: Path) -> int:
    keys: set[str] = set()
    for agent_dir in _iter_automation_dirs(base):
        posts = _safe_read_json(agent_dir / "posts.json", [])
        if isinstance(posts, dict):
            threads = posts.get("threads_engaged") or []
            for item in threads:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("id") or item.get("thread_id") or "").strip()
                if key:
                    keys.add(key)
            posts = posts.get("posts") or []
        if not isinstance(posts, list):
            continue
        for item in posts:
            if not isinstance(item, dict):
                continue
            key = str(item.get("thread_id") or item.get("id") or "").strip()
            if key:
                keys.add(key)
    return len(keys)


def _session_memory_dir(workspace: Path, task_name: str) -> Path:
    session_id = get_operational_session_target(task_name) or get_session_target(task_name) or f"automation-{task_name}"
    agent_id = session_id.replace("automation-", "", 1)
    path = workspace / "memory" / "automation" / f"automation-{agent_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_social_context_files(workspace: Path) -> None:
    base = workspace / "memory" / "automation"
    base.mkdir(parents=True, exist_ok=True)
    defaults: list[tuple[Path, Any]] = [
        (base / "known_agents.json", {"known_agents": {}}),
        (base / "conversation_threads.json", {"threads": {}, "version": "1.0"}),
        (base / "cross_platform_topics.json", {"topics": []}),
        (base / "blocked_users.json", {"blocked_users": []}),
    ]
    for path, payload in defaults:
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass


def _agency_control_summary_for_task(task_name: str) -> dict[str, Any]:
    try:
        from operator_console.server.app.services.operational_agency_control import build_agency_control_summary
    except Exception:
        return {
            "status": "unavailable",
            "mode": "normal",
            "effective_mode": "normal",
            "reason": None,
            "operator_hold": False,
            "review_required": False,
        }
    workspace = get_workspace_root()
    binding = {
        "operational_agent_id": get_operational_agent_id(task_name),
        "operational_session_target": get_operational_session_target(task_name),
    }
    return build_agency_control_summary(
        root=workspace,
        binding=binding,
        session_target=get_session_target(task_name),
    )


def _runtime_continuity_state_for_task(task_name: str) -> dict[str, Any]:
    try:
        from hg_core.job_registry import get_operational_binding
        from hg_gateway import keystore_repo
        from operator_console.server.app.services.bounded_autonomy_policy import build_bounded_autonomy_policy_summary
        from operator_console.server.app.services.continuity_incident_summary import build_continuity_incident_summary
        from operator_console.server.app.services.continuity_recovery_ack import load_continuity_recovery_ack
        from operator_console.server.app.services.continuity_recovery_readiness import build_continuity_recovery_readiness
        from operator_console.server.app.services.continuity_repair_observation import build_continuity_repair_observation
        from operator_console.server.app.services.continuity_repair_plan import build_continuity_repair_plan
        from operator_console.server.app.services.identity_continuity_summary import build_identity_continuity_summary
        from operator_console.server.app.services.identity_restore_validation import load_identity_restore_validation
        from operator_console.server.app.services.identity_resume_observation import build_identity_resume_observation
        from operator_console.server.app.services.identity_resume_procedure import build_identity_resume_procedure
        from operator_console.server.app.services.operational_resume_checkpoint import ensure_operational_resume_checkpoint_validity
        from operator_console.server.app.services.operational_resume_governance_summary import build_operational_resume_governance_summary
        from operator_console.server.app.services.post_rebuild_continuity_check import load_post_rebuild_continuity_check
        from operator_console.server.app.services.social_account_summary import build_social_account_operator_summary
        from operator_console.server.app.services.supervised_resume_validation import load_supervised_resume_validation
    except Exception:
        return {
            "binding": {},
            "identity_continuity_summary": {},
            "continuity_incident_summary": {"status": "clean"},
            "continuity_recovery_readiness": {"status": "ready", "safe_to_resume": True, "blocking": [], "cautions": []},
            "continuity_repair_plan": {"status": "clean", "open_checks": [], "completed_checks": []},
            "post_rebuild_continuity_check": {"status": "not_required", "verification_required": False, "verified": False},
            "identity_restore_validation": {"status": "not_required", "required": False, "verified": False},
            "supervised_resume_validation": {"status": "not_required", "required": False, "validated": False},
            "operational_resume_governance_summary": {},
            "operational_resume_checkpoint": {},
            "bounded_autonomy_policy_summary": {"status": "ready", "blockers": []},
            "required": False,
        }

    workspace = get_workspace_root()
    binding = get_operational_binding(task_name) or {}
    operational_agent_id = str(binding.get("operational_agent_id") or "").strip()
    platform = str(binding.get("platform") or "").strip()
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    session_target = get_session_target(task_name)

    identity_continuity_summary = build_identity_continuity_summary(
        root=workspace,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    continuity_incident_summary: dict[str, Any]
    assigned_social_accounts: list[dict[str, Any]] = []
    if operational_agent_id and platform:
        try:
            accounts = keystore_repo.social_account_list(tenant_id="default", platform=platform)
        except Exception:
            accounts = []
        for account in accounts:
            entity_scope = str(account.get("entity_scope") or "").strip()
            persona_scope = str(account.get("persona_scope") or "").strip()
            if entity_scope != operational_agent_id and (not fingerprint_id or persona_scope != fingerprint_id):
                continue
            assigned_social_accounts.append(
                {
                    "social_account_id": account.get("social_account_id"),
                    "account_alias": account.get("account_alias"),
                    "platform": account.get("platform"),
                    "state": account.get("state"),
                    **build_social_account_operator_summary(str(account.get("social_account_id") or ""), account=account),
                }
            )
    continuity_incident_summary = build_continuity_incident_summary(
        identity_continuity_summary=identity_continuity_summary,
        assigned_social_accounts=assigned_social_accounts,
    )
    continuity_recovery_ack = load_continuity_recovery_ack(
        root=workspace,
        binding=binding,
        session_target=session_target,
    )
    identity_resume_observation = build_identity_resume_observation(
        identity_continuity_summary=identity_continuity_summary,
        continuity_recovery_ack=continuity_recovery_ack,
    )
    continuity_repair_observation = build_continuity_repair_observation(
        assigned_social_accounts=assigned_social_accounts,
    )
    base_continuity_recovery_readiness = build_continuity_recovery_readiness(
        identity_continuity_summary=identity_continuity_summary,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_ack=continuity_recovery_ack,
        continuity_repair_observation=continuity_repair_observation,
        identity_resume_observation=identity_resume_observation,
    )
    post_rebuild_continuity_check = load_post_rebuild_continuity_check(
        root=workspace,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary=identity_continuity_summary,
        continuity_recovery_readiness=base_continuity_recovery_readiness,
    )
    identity_restore_validation = load_identity_restore_validation(
        root=workspace,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary=identity_continuity_summary,
    )
    continuity_recovery_readiness = build_continuity_recovery_readiness(
        identity_continuity_summary=identity_continuity_summary,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_ack=continuity_recovery_ack,
        continuity_repair_observation=continuity_repair_observation,
        identity_resume_observation=identity_resume_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
    )
    continuity_repair_plan = build_continuity_repair_plan(
        identity_continuity_summary=identity_continuity_summary,
        identity_resume_procedure=build_identity_resume_procedure(
            identity_continuity_summary=identity_continuity_summary,
        ),
        identity_resume_observation=identity_resume_observation,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_observation=continuity_repair_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
    )

    task_names = sorted(
        candidate
        for candidate in list_tasks()
        if str(get_platform(candidate) or "").strip() == platform
        and str(get_operational_agent_id(candidate) or "").strip() == operational_agent_id
    )
    if not task_names:
        task_names = [task_name]
    linked_tasks = [{"id": candidate, "session_target": get_session_target(candidate)} for candidate in task_names]
    operational_resume_governance_summary = build_operational_resume_governance_summary(
        root=workspace,
        binding=binding,
        task_names=task_names,
        linked_tasks=linked_tasks,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_plan=continuity_repair_plan,
        identity_restore_validation=identity_restore_validation,
    )
    operational_resume_checkpoint = ensure_operational_resume_checkpoint_validity(
        root=workspace,
        binding=binding,
        session_target=session_target,
        operational_resume_governance_summary=operational_resume_governance_summary,
    )
    supervised_resume_validation = load_supervised_resume_validation(
        root=workspace,
        binding=binding,
        session_target=session_target,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_recovery_ack=continuity_recovery_ack,
        identity_restore_validation=identity_restore_validation,
    )
    continuity_repair_plan = build_continuity_repair_plan(
        identity_continuity_summary=identity_continuity_summary,
        identity_resume_procedure=build_identity_resume_procedure(
            identity_continuity_summary=identity_continuity_summary,
        ),
        identity_resume_observation=identity_resume_observation,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_observation=continuity_repair_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
    )
    bounded_autonomy_policy_summary = build_bounded_autonomy_policy_summary(
        agency_control_summary=_agency_control_summary_for_task(task_name),
        continuity_recovery_readiness=continuity_recovery_readiness,
        operational_resume_governance_summary=operational_resume_governance_summary,
        operational_resume_checkpoint=operational_resume_checkpoint,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
    )
    return {
        "binding": binding,
        "assigned_social_accounts": assigned_social_accounts,
        "identity_continuity_summary": identity_continuity_summary,
        "continuity_incident_summary": continuity_incident_summary,
        "continuity_recovery_ack": continuity_recovery_ack,
        "identity_resume_observation": identity_resume_observation,
        "continuity_repair_observation": continuity_repair_observation,
        "continuity_recovery_readiness": continuity_recovery_readiness,
        "continuity_repair_plan": continuity_repair_plan,
        "post_rebuild_continuity_check": post_rebuild_continuity_check,
        "identity_restore_validation": identity_restore_validation,
        "supervised_resume_validation": supervised_resume_validation,
        "operational_resume_governance_summary": operational_resume_governance_summary,
        "operational_resume_checkpoint": operational_resume_checkpoint,
        "bounded_autonomy_policy_summary": bounded_autonomy_policy_summary,
        "required": bool(bounded_autonomy_policy_summary.get("blockers")),
    }


def _continuity_recovery_readiness_for_task(task_name: str) -> dict[str, Any]:
    state = _runtime_continuity_state_for_task(task_name)
    readiness = state.get("continuity_recovery_readiness")
    return readiness if isinstance(readiness, dict) else {"status": "ready", "safe_to_resume": True, "blocking": [], "cautions": []}


def _operational_resume_release_state_for_task(task_name: str) -> dict[str, Any]:
    state = _runtime_continuity_state_for_task(task_name)
    return {
        "required": bool(state.get("required")),
        "governance": state.get("operational_resume_governance_summary") if isinstance(state.get("operational_resume_governance_summary"), dict) else {},
        "checkpoint": state.get("operational_resume_checkpoint") if isinstance(state.get("operational_resume_checkpoint"), dict) else {},
        "identity_restore_validation": state.get("identity_restore_validation") if isinstance(state.get("identity_restore_validation"), dict) else {},
        "supervised_resume_validation": state.get("supervised_resume_validation") if isinstance(state.get("supervised_resume_validation"), dict) else {},
        "policy": state.get("bounded_autonomy_policy_summary") if isinstance(state.get("bounded_autonomy_policy_summary"), dict) else {},
    }


def _record_agency_gate_notification(
    *,
    task_name: str,
    agency_control_summary: dict[str, Any],
    gate_kind: str,
    extra_summary: Optional[dict[str, Any]] = None,
) -> dict[str, Any] | None:
    try:
        from hg_core.human_notifications import record_human_notification
    except Exception:
        return None
    workspace = get_workspace_root()
    mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    reason = str(agency_control_summary.get("reason") or "").strip() or gate_kind
    operational_agent_id = get_operational_agent_id(task_name)
    message = f"{task_name} blocked by {mode}: {reason}"
    summary = {
        "execution": {
            "status": "blocked",
            "platform": get_platform(task_name),
            "mode": get_mode(task_name),
            "blocked_reason": gate_kind,
        },
        "agency_control": {
            "effective_mode": mode,
            "reason": reason,
        },
    }
    if isinstance(extra_summary, dict):
        for key, value in extra_summary.items():
            if key == "execution" and isinstance(value, dict):
                summary["execution"] = {**summary["execution"], **value}
            elif key == "agency_control" and isinstance(value, dict):
                summary["agency_control"] = {**summary["agency_control"], **value}
            else:
                summary[key] = value
    recorded = record_human_notification(
        workspace,
        task_name=task_name,
        kind="agency_gate",
        message=message,
        summary=summary,
        transport="log_only",
        operational_agent_id=operational_agent_id,
    )
    return recorded


def _commitment_subject_context(resolved_inputs: dict[str, Any]) -> dict[str, str]:
    subject_task = str(
        resolved_inputs.get("task_name")
        or resolved_inputs.get("subject_task_name")
        or resolved_inputs.get("workflow_id")
        or ""
    ).strip()
    try:
        from hg_core.job_registry import get_operational_binding

        binding = get_operational_binding(subject_task) if subject_task else {}
    except Exception:
        binding = {}
    return {
        "task_name": subject_task,
        "entity_id": str(resolved_inputs.get("entity_id") or subject_task).strip(),
        "operational_agent_id": str(
            resolved_inputs.get("operational_agent_id")
            or get_operational_agent_id(subject_task)
            or binding.get("operational_agent_id")
            or ""
        ).strip(),
        "tenant_id": (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default",
    }


def _task_tool_commitment_record(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_gateway.commitment_ledger import record_commitment

    workspace = get_workspace_root()
    subject = _commitment_subject_context(resolved_inputs)
    if not subject["task_name"]:
        return {"ok": False, "error": "commitment.record missing task_name", "returncode": -1}
    title = str(resolved_inputs.get("title") or resolved_inputs.get("commitment_title") or "").strip()
    if not title:
        title = "Commitment"
    details_raw = resolved_inputs.get("details")
    if details_raw is None:
        details_raw = resolved_inputs.get("commitment_details")
    details = details_raw if isinstance(details_raw, dict) else {"detail": details_raw} if details_raw is not None else {}
    commitment = record_commitment(
        workspace,
        task_name=subject["task_name"],
        title=title,
        details=details,
        due_at=str(resolved_inputs.get("due_at") or "").strip() or None,
        commitment_kind=str(resolved_inputs.get("commitment_kind") or "promise").strip() or "promise",
        status=str(resolved_inputs.get("status") or "open").strip() or "open",
        tenant_id=subject["tenant_id"],
        entity_id=subject["entity_id"] or None,
        operational_agent_id=subject["operational_agent_id"] or None,
        created_by=str(resolved_inputs.get("created_by") or "").strip() or None,
        source=str(resolved_inputs.get("source") or task_name or "").strip() or None,
        source_id=str(resolved_inputs.get("source_id") or "").strip() or None,
    )
    return {"ok": True, "outputs": {"commitment": commitment, "result": {"status": commitment.get("status"), "commitment_id": commitment.get("commitment_id"), "title": commitment.get("title")}}, "returncode": 0, "external_calls": 0}


def _task_tool_commitment_list(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_gateway.commitment_ledger import list_commitments, summarize_commitments

    workspace = get_workspace_root()
    subject = _commitment_subject_context(resolved_inputs)
    commitments = list_commitments(
        workspace,
        tenant_id=subject["tenant_id"],
        task_name=subject["task_name"] or None,
        operational_agent_id=subject["operational_agent_id"] or None,
        entity_id=subject["entity_id"] or None,
        status=str(resolved_inputs.get("status") or "").strip() or None,
        limit=int(resolved_inputs.get("limit") or 20),
    )
    return {"ok": True, "outputs": {"commitments": commitments, "summary": summarize_commitments(commitments), "result": {"status": "completed", "count": len(commitments)}}, "returncode": 0, "external_calls": 0}


def _task_tool_commitment_fulfill(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_gateway.commitment_ledger import fulfill_commitment

    workspace = get_workspace_root()
    commitment_id = str(resolved_inputs.get("commitment_id") or "").strip()
    if not commitment_id:
        return {"ok": False, "error": "commitment.fulfill missing commitment_id", "returncode": -1}
    entry = fulfill_commitment(
        workspace,
        commitment_id=commitment_id,
        tenant_id=str(resolved_inputs.get("tenant_id") or "").strip() or None,
        resolution_note=str(resolved_inputs.get("resolution_note") or resolved_inputs.get("note") or "").strip() or None,
    )
    if not entry:
        return {"ok": False, "error": "commitment not found", "returncode": -1}
    return {"ok": True, "outputs": {"commitment": entry, "result": {"status": "fulfilled", "commitment_id": commitment_id, "title": entry.get("title")}}, "returncode": 0, "external_calls": 0}


def _task_tool_commitment_expire(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_gateway.commitment_ledger import expire_commitment

    workspace = get_workspace_root()
    commitment_id = str(resolved_inputs.get("commitment_id") or "").strip()
    if not commitment_id:
        return {"ok": False, "error": "commitment.expire missing commitment_id", "returncode": -1}
    entry = expire_commitment(
        workspace,
        commitment_id=commitment_id,
        tenant_id=str(resolved_inputs.get("tenant_id") or "").strip() or None,
        resolution_note=str(resolved_inputs.get("resolution_note") or resolved_inputs.get("note") or "").strip() or None,
    )
    if not entry:
        return {"ok": False, "error": "commitment not found", "returncode": -1}
    return {"ok": True, "outputs": {"commitment": entry, "result": {"status": "expired", "commitment_id": commitment_id, "title": entry.get("title")}}, "returncode": 0, "external_calls": 0}


def _task_tool_commitment_summary(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_gateway.commitment_ledger import list_commitments, summarize_commitments

    workspace = get_workspace_root()
    subject = _commitment_subject_context(resolved_inputs)
    commitments = list_commitments(
        workspace,
        tenant_id=subject["tenant_id"],
        task_name=subject["task_name"] or None,
        operational_agent_id=subject["operational_agent_id"] or None,
        entity_id=subject["entity_id"] or None,
        limit=int(resolved_inputs.get("limit") or 20),
    )
    return {"ok": True, "outputs": {"summary": summarize_commitments(commitments), "commitments": commitments, "result": {"status": "completed", "count": len(commitments)}}, "returncode": 0, "external_calls": 0}


def _record_review_handoff_release_expired_notification(
    *,
    task_name: str,
    platform: str,
    approval_id: str,
    release_window_hours: int,
    approved_until: str,
) -> dict[str, Any] | None:
    try:
        from hg_core.human_notifications import record_human_notification
    except Exception:
        return None
    workspace = get_workspace_root()
    operational_agent_id = get_operational_agent_id(task_name)
    message = f"{task_name} review approval expired before release"
    recorded = record_human_notification(
        workspace,
        task_name=task_name,
        kind="review_handoff_release_expired",
        message=message,
        summary={
            "execution": {
                "status": "expired",
                "platform": platform,
                "mode": get_mode(task_name),
                "blocked_reason": "approval_expired",
            },
            "review_handoff": {
                "approval_id": approval_id,
                "release_window_hours": release_window_hours,
                "approved_until": approved_until,
                "status": "expired",
            },
        },
        transport="log_only",
        operational_agent_id=operational_agent_id,
    )
    return recorded


def _record_runtime_continuity_observations(
    *,
    task_name: str,
    platform: str,
    mode: str,
) -> list[dict[str, Any]]:
    try:
        from hg_core.human_notifications import record_human_notification
    except Exception:
        return []
    workspace = get_workspace_root()
    state = _runtime_continuity_state_for_task(task_name)
    continuity_incident_summary = state.get("continuity_incident_summary") if isinstance(state.get("continuity_incident_summary"), dict) else {}
    continuity_recovery_readiness = state.get("continuity_recovery_readiness") if isinstance(state.get("continuity_recovery_readiness"), dict) else {}
    continuity_repair_plan = state.get("continuity_repair_plan") if isinstance(state.get("continuity_repair_plan"), dict) else {}
    post_rebuild_continuity_check = state.get("post_rebuild_continuity_check") if isinstance(state.get("post_rebuild_continuity_check"), dict) else {}
    identity_restore_validation = state.get("identity_restore_validation") if isinstance(state.get("identity_restore_validation"), dict) else {}
    supervised_resume_validation = state.get("supervised_resume_validation") if isinstance(state.get("supervised_resume_validation"), dict) else {}
    bounded_autonomy_policy_summary = state.get("bounded_autonomy_policy_summary") if isinstance(state.get("bounded_autonomy_policy_summary"), dict) else {}
    operational_resume_governance_summary = state.get("operational_resume_governance_summary") if isinstance(state.get("operational_resume_governance_summary"), dict) else {}
    operational_agent_id = get_operational_agent_id(task_name)
    receipt_state = _load_runtime_continuity_receipt_state(workspace, task_name)
    entries: list[dict[str, Any]] = []

    def _record(kind: str, message: str, marker_key: str, marker_value: str | None) -> None:
        if not marker_value:
            return
        if str(receipt_state.get(marker_key) or "").strip() == marker_value:
            return
        recorded = record_human_notification(
            workspace,
            task_name=task_name,
            kind=kind,
            message=message,
            summary={
                "execution": {
                    "status": "observed",
                    "platform": platform,
                    "mode": mode,
                    "task_name": task_name,
                },
                "continuity_incident_summary": continuity_incident_summary,
                "continuity_recovery": continuity_recovery_readiness,
                "continuity_repair_plan": continuity_repair_plan,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "supervised_resume_validation": supervised_resume_validation,
                "operational_resume_governance_summary": operational_resume_governance_summary,
                "bounded_autonomy_policy_summary": bounded_autonomy_policy_summary,
            },
            transport="log_only",
            operational_agent_id=operational_agent_id,
        )
        receipt_state[marker_key] = marker_value
        entries.append(recorded)

    incident_status = str(continuity_incident_summary.get("status") or "").strip().lower()
    latest_incident_event_at = str(continuity_incident_summary.get("latest_event_at") or "").strip() or None
    if incident_status in {"active", "recovered"}:
        _record(
            "continuity_runtime_observed",
            f"{task_name} entered runtime with {incident_status} continuity state",
            "continuity_runtime_observed_at",
            latest_incident_event_at,
        )
    if bool(post_rebuild_continuity_check.get("verified")):
        _record(
            "post_rebuild_runtime_observed",
            f"{task_name} executed after rebuild verification",
            "post_rebuild_runtime_observed_at",
            str(post_rebuild_continuity_check.get("verified_at") or "").strip() or None,
        )
    if bool(identity_restore_validation.get("verified")):
        _record(
            "identity_restore_runtime_observed",
            f"{task_name} executed after identity restore validation",
            "identity_restore_runtime_observed_at",
            str(identity_restore_validation.get("verified_at") or "").strip() or None,
        )
    if bool(supervised_resume_validation.get("validated")):
        _record(
            "supervised_resume_runtime_observed",
            f"{task_name} executed after supervised resume validation",
            "supervised_resume_runtime_observed_at",
            str(supervised_resume_validation.get("validated_at") or "").strip() or None,
        )
    if entries:
        _save_runtime_continuity_receipt_state(workspace, task_name, receipt_state)
    return entries


def _approval_release_blocked_result(
    *,
    task_name: str,
    error: str,
    step: str,
    reason: str,
    platform: str,
    approval_id: str,
    agency_control_summary: dict[str, Any],
    recorded: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "outputs": {
            "mode": "approval_blocked",
            "platform": platform,
            "approval_id": approval_id,
            "result": {
                "status": "blocked",
                "mode": "approval_blocked",
                "step": step,
                "task_name": task_name,
                "platform": platform,
                "approval_id": approval_id,
                "reason": reason,
            },
            "agency_control_summary": agency_control_summary,
            "notification_log": (recorded or {}).get("notification_log", ""),
            "notification_payload": (recorded or {}).get("entry"),
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _enforce_social_approval_release_controls(
    *,
    task_name: str,
    platform: str,
    mode: str,
    approval_id: str,
) -> dict[str, Any] | None:
    if not task_name or mode not in {"post", "reply"}:
        return None
    runtime_mode = "engage" if mode == "reply" else "auto-post"
    agency_control_summary = _agency_control_summary_for_task(task_name)
    effective_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    if effective_mode == "held":
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="approval_release_held",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "approval_release_held",
                    "mode": runtime_mode,
                },
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error="agency_control_held",
            step="approval_release_hold",
            reason=str(agency_control_summary.get("reason") or "operator hold"),
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    outbound_lane_policy = str(agency_control_summary.get("outbound_lane_policy") or "unrestricted").strip().lower()
    if not _outbound_lane_policy_allows(runtime_mode, outbound_lane_policy):
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="approval_release_lane_policy_blocked",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "approval_release_lane_policy_blocked",
                    "mode": runtime_mode,
                },
                "lane_policy": {
                    "outbound_lane_policy": outbound_lane_policy,
                    "allowed_outbound_modes": agency_control_summary.get("allowed_outbound_modes") or [],
                },
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error="agency_lane_policy_blocked",
            step="approval_release_lane_policy",
            reason=f"outbound lane policy {outbound_lane_policy}",
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    if bool(agency_control_summary.get("outbound_budget_exhausted")):
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="approval_release_outbound_budget_exhausted",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "approval_release_outbound_budget_exhausted",
                    "mode": runtime_mode,
                },
                "budget": {
                    "daily_outbound_budget": agency_control_summary.get("daily_outbound_budget"),
                    "recent_outbound_action_count": agency_control_summary.get("recent_outbound_action_count"),
                    "outbound_budget_remaining": agency_control_summary.get("outbound_budget_remaining"),
                    "outbound_actions_window_hours": agency_control_summary.get("outbound_actions_window_hours"),
                },
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error="agency_outbound_budget_exhausted",
            step="approval_release_outbound_budget",
            reason=f"outbound budget exhausted ({agency_control_summary.get('recent_outbound_action_count')}/{agency_control_summary.get('daily_outbound_budget')})",
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    continuity_state = _runtime_continuity_state_for_task(task_name)
    continuity_recovery = _continuity_recovery_readiness_for_task(task_name)
    continuity_repair_plan = continuity_state.get("continuity_repair_plan") if isinstance(continuity_state.get("continuity_repair_plan"), dict) else {}
    continuity_incident_summary = continuity_state.get("continuity_incident_summary") if isinstance(continuity_state.get("continuity_incident_summary"), dict) else {}
    post_rebuild_continuity_check = continuity_state.get("post_rebuild_continuity_check") if isinstance(continuity_state.get("post_rebuild_continuity_check"), dict) else {}
    identity_restore_validation = continuity_state.get("identity_restore_validation") if isinstance(continuity_state.get("identity_restore_validation"), dict) else {}
    supervised_resume_validation = continuity_state.get("supervised_resume_validation") if isinstance(continuity_state.get("supervised_resume_validation"), dict) else {}
    bounded_autonomy_policy_summary = continuity_state.get("bounded_autonomy_policy_summary") if isinstance(continuity_state.get("bounded_autonomy_policy_summary"), dict) else {}
    operational_resume_governance_summary = continuity_state.get("operational_resume_governance_summary") if isinstance(continuity_state.get("operational_resume_governance_summary"), dict) else {}
    operational_resume_state = _operational_resume_release_state_for_task(task_name)
    operational_resume_governance_summary = operational_resume_state.get("governance") if isinstance(operational_resume_state.get("governance"), dict) else operational_resume_governance_summary
    operational_resume_checkpoint = operational_resume_state.get("checkpoint") if isinstance(operational_resume_state.get("checkpoint"), dict) else {}
    continuity_status = str(continuity_recovery.get("status") or "").strip().lower()
    if continuity_status == "blocked":
        blocking = continuity_recovery.get("blocking") if isinstance(continuity_recovery.get("blocking"), list) else []
        reason = ", ".join(str(item).strip() for item in blocking if str(item).strip()) or "continuity recovery blocked"
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="approval_release_continuity_recovery_blocked",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "approval_release_continuity_recovery_blocked",
                    "mode": runtime_mode,
                },
                "continuity_recovery": continuity_recovery,
                "continuity_incident_summary": continuity_incident_summary,
                "continuity_repair_plan": continuity_repair_plan,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "supervised_resume_validation": supervised_resume_validation,
                "bounded_autonomy_policy_summary": bounded_autonomy_policy_summary,
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error="continuity_recovery_blocked",
            step="approval_release_continuity_recovery",
            reason=reason,
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    if continuity_status == "caution" and not bool(continuity_recovery.get("resume_permitted")):
        cautions = continuity_recovery.get("cautions") if isinstance(continuity_recovery.get("cautions"), list) else []
        reason = ", ".join(str(item).strip() for item in cautions if str(item).strip()) or "continuity recovery acknowledgment required"
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="approval_release_continuity_recovery_ack_required",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "approval_release_continuity_recovery_ack_required",
                    "mode": runtime_mode,
                },
                "continuity_recovery": continuity_recovery,
                "continuity_incident_summary": continuity_incident_summary,
                "continuity_repair_plan": continuity_repair_plan,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "supervised_resume_validation": supervised_resume_validation,
                "bounded_autonomy_policy_summary": bounded_autonomy_policy_summary,
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error="continuity_recovery_ack_required",
            step="approval_release_continuity_recovery_ack",
            reason=reason,
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    operational_resume = {
        "required": bool(continuity_state.get("required")),
        "governance": operational_resume_governance_summary,
        "checkpoint": operational_resume_checkpoint,
        "identity_restore_validation": identity_restore_validation,
        "supervised_resume_validation": supervised_resume_validation,
        "policy": bounded_autonomy_policy_summary,
    }
    if bool(operational_resume.get("required")):
        checkpoint = operational_resume.get("checkpoint") if isinstance(operational_resume.get("checkpoint"), dict) else {}
        governance = operational_resume.get("governance") if isinstance(operational_resume.get("governance"), dict) else {}
        restore_validation = operational_resume.get("identity_restore_validation") if isinstance(operational_resume.get("identity_restore_validation"), dict) else {}
        supervised_validation = operational_resume.get("supervised_resume_validation") if isinstance(operational_resume.get("supervised_resume_validation"), dict) else {}
        policy = operational_resume.get("policy") if isinstance(operational_resume.get("policy"), dict) else {}
        blockers = list(policy.get("blockers") or [])
        gate_kind = "approval_release_operational_resume_checkpoint_required"
        error = "operational_resume_checkpoint_required"
        step = "approval_release_operational_resume_checkpoint"
        reason = str(checkpoint.get("invalidated_reason") or "").strip() or "fresh operational resume checkpoint required"
        if "identity_restore_validation_required" in blockers or "identity_restore_validation_blocked" in blockers:
            gate_kind = "approval_release_identity_restore_validation_required"
            error = "identity_restore_validation_required"
            step = "approval_release_identity_restore_validation"
            reason = str(restore_validation.get("summary") or "").strip() or "identity restore validation required"
        elif "supervised_resume_validation_required" in blockers:
            gate_kind = "approval_release_supervised_resume_validation_required"
            error = "supervised_resume_validation_required"
            step = "approval_release_supervised_resume_validation"
            reason = str(supervised_validation.get("summary") or "").strip() or "supervised resume validation required"
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind=gate_kind,
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": gate_kind,
                    "mode": runtime_mode,
                },
                "operational_resume_governance_summary": governance,
                "operational_resume_checkpoint": checkpoint,
                "continuity_incident_summary": continuity_incident_summary,
                "continuity_recovery": continuity_recovery,
                "continuity_repair_plan": continuity_repair_plan,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": restore_validation,
                "supervised_resume_validation": supervised_validation,
                "bounded_autonomy_policy_summary": policy,
                "review_handoff": {
                    "approval_id": approval_id,
                    "status": "blocked",
                },
            },
        )
        return _approval_release_blocked_result(
            task_name=task_name,
            error=error,
            step=step,
            reason=reason,
            platform=platform,
            approval_id=approval_id,
            agency_control_summary=agency_control_summary,
            recorded=recorded,
        )
    return None


def _outbound_lane_policy_allows(mode: str, outbound_lane_policy: str) -> bool:
    normalized_mode = str(mode or "").strip().lower()
    policy = str(outbound_lane_policy or "unrestricted").strip().lower()
    if policy == "unrestricted":
        return True
    if policy == "replies_only":
        return normalized_mode == "engage"
    if policy in {"drafts_only", "blocked"}:
        return False
    return False


def _automation_agent_count(workspace: Path) -> int:
    """Count automation agent directories (memory/automation/automation-*) so overseer/dashboard can show N agents even before any external known_agents."""
    base = workspace / "memory" / "automation"
    if not base.exists():
        return 0
    try:
        return sum(1 for p in base.iterdir() if p.is_dir() and p.name.startswith("automation-"))
    except OSError:
        return 0


def _recent_posts_cross_automation(workspace: Path) -> int:
    """Count recent posts across all automation agents (posts.json) so dashboard shows accurate 'recent posts' even when viewing overseer (which has no posts of its own)."""
    base = workspace / "memory" / "automation"
    if not base.exists():
        return 0
    total = 0
    try:
        for p in base.iterdir():
            if not p.is_dir() or not p.name.startswith("automation-"):
                continue
            posts_file = p / "posts.json"
            if not posts_file.exists():
                continue
            data = _safe_read_json(posts_file, {})
            if isinstance(data, dict):
                posts = data.get("posts") or []
                if isinstance(posts, list):
                    total += len(posts)
    except OSError:
        pass
    return total


def _destination_usage_counts(workspace: Path, platform: str, field_name: str, limit: int = 120) -> dict[str, int]:
    counts: dict[str, int] = {}
    for agent_dir in _iter_automation_dirs(workspace / "memory" / "automation"):
        posts = _safe_read_json(agent_dir / "posts.json", {})
        rows = posts.get("posts") if isinstance(posts, dict) else posts
        if not isinstance(rows, list):
            continue
        for item in rows[-limit:]:
            if not isinstance(item, dict):
                continue
            item_platform = str(item.get("platform") or "").strip().lower()
            if item_platform and item_platform != platform:
                continue
            value = str(item.get(field_name) or "").strip().lower()
            if not value:
                continue
            counts[value] = counts.get(value, 0) + 1
    return counts


def _topic_terms(text: str) -> set[str]:
    terms = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", (text or "").lower())
        if token not in {
            "that",
            "this",
            "with",
            "from",
            "have",
            "your",
            "about",
            "into",
            "their",
            "they",
            "them",
            "just",
            "what",
            "when",
            "while",
            "where",
            "would",
            "could",
            "should",
            "there",
            "because",
        }
    }
    return terms


def _list_social_destinations(workspace: Path, platform: str, timeout_s: int) -> list[dict[str, Any]]:
    if platform == "fourclaw":
        cmd = [sys.executable, "hg_platforms/fourclaw/list_fourclaw_boards.py"]
    elif platform == "aichan":
        cmd = [sys.executable, "aichan/list_aichan_boards.py"]
    elif platform == "agentchan":
        cmd = [sys.executable, "skills/automation/agentchan/list_agentchan_boards.py"]
    elif platform == "moltbook":
        cmd = [sys.executable, "hg_platforms/moltbook/list_moltbook_submolts.py"]
    else:
        return []
    result = _run(cmd, workspace, timeout_s=timeout_s)
    payload = _last_json(result.stdout)
    entries: list[dict[str, Any]] = []
    if platform == "moltbook":
        raw_items = payload.get("submolts") or []
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                slug = str(item.get("name") or "").strip().lower()
                if not slug:
                    continue
                entries.append(
                    {
                        "slug": slug,
                        "label": str(item.get("display_name") or item.get("name") or slug).strip(),
                        "description": str(item.get("description") or "").strip(),
                        "kind": "submolt",
                        "access": "public",
                    }
                )
        return entries

    data = payload.get("data")
    raw_items = []
    if isinstance(data, dict):
        if isinstance(data.get("boards"), list):
            raw_items = data.get("boards") or []
        elif isinstance(data.get("data"), list):
            raw_items = data.get("data") or []
    elif isinstance(data, list):
        raw_items = data
    if not raw_items and isinstance(payload.get("boards"), list):
        raw_items = payload.get("boards") or []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or item.get("name") or item.get("board") or item.get("id") or "").strip().lower()
        if not slug:
            continue
        description = str(
            item.get("description")
            or item.get("manifest")
            or item.get("topic")
            or item.get("summary")
            or ""
        ).strip()
        access = str(item.get("access") or item.get("status") or "").strip().lower() or "public"
        can_post = item.get("can_post")
        entries.append(
            {
                "slug": slug,
                "label": str(item.get("title") or item.get("display_name") or item.get("name") or slug).strip(),
                "description": description,
                "kind": "board",
                "access": access,
                "can_post": can_post,
            }
        )
    return entries


def _default_social_destinations(platform: str) -> list[dict[str, Any]]:
    defaults = {
        "fourclaw": ["b", "tech", "sci", "news", "hum"],
        "aichan": ["b", "biz", "int", "pol"],
        "agentchan": ["b", "g", "x", "int", "meta"],
        "moltbook": ["general", "technology", "science", "politics", "finance"],
    }
    kind = "submolt" if platform == "moltbook" else "board"
    return [{"slug": slug, "label": slug, "description": "", "kind": kind, "access": "public"} for slug in defaults.get(platform, [])]


def _blocked_destination_map() -> dict[str, dict[str, Any]]:
    try:
        from hg_gateway.shared_storage import get_operational_state

        payload = get_operational_state("social:blocked_destinations", {})
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def _record_destination_failure(*, platform: str, slug: str, error: str, status_code: int | None = None) -> None:
    normalized_slug = str(slug or "").strip().lower()
    normalized_platform = str(platform or "").strip().lower()
    if not normalized_slug or not normalized_platform:
        return
    payload = _blocked_destination_map()
    scoped = payload.setdefault(normalized_platform, {})
    scoped[normalized_slug] = {
        "error": _compact_text(str(error or ""), 240),
        "status_code": int(status_code) if status_code is not None else None,
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    try:
        from hg_gateway.shared_storage import put_operational_state

        put_operational_state("social:blocked_destinations", payload)
    except Exception:
        pass


_STATIC_RESTRICTED_DESTINATIONS: dict[str, frozenset[str]] = {
    "moltbook": frozenset({"announcements", "m/announcements", "mod", "moderators"}),
    "agentchan": frozenset({"hum", "tfw", "ai", "/hum", "/tfw", "/ai"}),
}


def _destination_is_restricted(platform: str, slug: str) -> bool:
    normalized_platform = str(platform or "").strip().lower()
    normalized_slug = str(slug or "").strip().lower().lstrip("/")
    static = _STATIC_RESTRICTED_DESTINATIONS.get(normalized_platform, frozenset())
    if normalized_slug in static or f"/{normalized_slug}" in static:
        return True
    scoped = _blocked_destination_map().get(normalized_platform)
    if not isinstance(scoped, dict):
        return False
    payload = scoped.get(normalized_slug)
    if not isinstance(payload, dict):
        return False
    error_text = str(payload.get("error") or "").lower()
    status_code = int(payload.get("status_code") or 0)
    return status_code == 403 or "restricted" in error_text or "moderator" in error_text or "forbidden" in error_text


def _recent_social_interactions() -> dict[str, Any]:
    try:
        from hg_gateway.shared_storage import get_operational_state

        payload = get_operational_state("social:recent_interactions", None)
        if isinstance(payload, dict):
            rows = payload.get("rows")
            if isinstance(rows, list):
                return payload
    except Exception:
        pass
    return {"rows": [], "updated_at": None, "version": "1.0"}


def _record_social_interaction(
    *,
    platform: str,
    mode: str,
    destination: str,
    thread_id: str,
    author: str = "",
    topic: str = "",
    content: str = "",
    outcome: str = "completed",
    max_rows: int = 500,
) -> None:
    normalized_thread = str(thread_id or "").strip()
    if not normalized_thread:
        return
    payload = _recent_social_interactions()
    rows = payload.get("rows")
    if not isinstance(rows, list):
        rows = []
    rows.append(
        {
            "platform": str(platform or "").strip().lower(),
            "mode": str(mode or "").strip().lower(),
            "destination": str(destination or "").strip().lower(),
            "thread_id": normalized_thread,
            "author": str(author or "").strip().lstrip("@").lower(),
            "topic": _normalize_topic_key(topic),
            "content_key": _headline_dedupe_key(content),
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "outcome": str(outcome or "completed").strip().lower(),
        }
    )
    payload["rows"] = rows[-max_rows:]
    payload["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        from hg_gateway.shared_storage import put_operational_state

        put_operational_state("social:recent_interactions", payload)
    except Exception:
        pass


def _find_recent_social_interaction(
    *,
    platform: str,
    thread_id: str = "",
    author: str = "",
    topic: str = "",
    within_hours: float = 24.0 * 14.0,
) -> dict[str, Any] | None:
    payload = _recent_social_interactions()
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    cutoff = datetime.now(UTC) - timedelta(hours=max(1.0, float(within_hours)))
    normalized_platform = str(platform or "").strip().lower()
    normalized_thread = str(thread_id or "").strip()
    normalized_author = str(author or "").strip().lstrip("@").lower()
    normalized_topic = _normalize_topic_key(topic)
    for row in reversed(rows):
        if not isinstance(row, dict):
            continue
        if str(row.get("platform") or "").strip().lower() != normalized_platform:
            continue
        timestamp_raw = str(row.get("timestamp") or "").strip()
        try:
            timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp < cutoff:
            continue
        if normalized_thread and str(row.get("thread_id") or "").strip() == normalized_thread:
            return row
        if normalized_author and str(row.get("author") or "").strip().lower() == normalized_author:
            return row
        if normalized_topic and str(row.get("topic") or "").strip() == normalized_topic:
            return row
    return None


def _phrase_history_path(workspace: Path) -> Path:
    return workspace / "memory" / "automation" / "phrase_history.json"


def _cross_platform_topic_memory_path(workspace: Path) -> Path:
    return workspace / "memory" / "automation" / "cross_platform_topics.json"


def _record_phrase_usage(workspace: Path, *, platform: str, content: str, post_id: str | None = None) -> None:
    if not content.strip():
        return
    try:
        from hg_overseer.overseer_core.humanization.phrase_variation import PhraseVariation

        tracker = PhraseVariation(history_path=str(_phrase_history_path(workspace)))
        tracker.record_content(content, platform, post_id=post_id)
    except Exception:
        pass


def _is_repetitive_phrase_pattern(workspace: Path, content: str) -> tuple[bool, list[str]]:
    if not content.strip():
        return False, []
    try:
        from hg_overseer.overseer_core.humanization.phrase_variation import PhraseVariation

        tracker = PhraseVariation(history_path=str(_phrase_history_path(workspace)))
        return tracker.check_repetitive_phrases(content, threshold=0.02)
    except Exception:
        return False, []


def _record_topic_take(workspace: Path, *, topic: str, platform: str, content_preview: str, post_id: str | None = None) -> None:
    normalized_topic = _normalize_topic_key(topic)
    if not normalized_topic:
        return
    try:
        from hg_memory.cross_platform_memory import CrossPlatformMemory

        tracker = CrossPlatformMemory(memory_path=str(_cross_platform_topic_memory_path(workspace)))
        tracker.record_topic_take(normalized_topic, platform, content_preview, post_id=post_id)
    except Exception:
        pass


def _recent_cross_platform_take(workspace: Path, *, topic: str, platform: str, hours: int = 24 * 7) -> tuple[bool, dict[str, Any] | None]:
    normalized_topic = _normalize_topic_key(topic)
    if not normalized_topic:
        return False, None
    try:
        from hg_memory.cross_platform_memory import CrossPlatformMemory

        tracker = CrossPlatformMemory(memory_path=str(_cross_platform_topic_memory_path(workspace)))
        return tracker.check_recent_take(normalized_topic, platform, hours=hours)
    except Exception:
        return False, None


def _rank_social_destinations(
    *,
    workspace: Path,
    platform: str,
    content_hint: str,
    timeout_s: int,
) -> list[dict[str, Any]]:
    entries = _list_social_destinations(workspace, platform, timeout_s=timeout_s) or _default_social_destinations(platform)
    usage_field = "submolt" if platform == "moltbook" else "board"
    usage = _destination_usage_counts(workspace, platform, usage_field)
    terms = _topic_terms(content_hint)
    general_penalty = {"b", "general", "m/general"}
    ranked: list[dict[str, Any]] = []
    for index, item in enumerate(entries):
        slug = str(item.get("slug") or "").strip().lower()
        if not slug:
            continue
        if _destination_is_restricted(platform, slug):
            continue
        if item.get("can_post") is False or str(item.get("access") or "").lower() in {"private", "readonly", "read_only", "denied"}:
            continue
        corpus = f"{slug} {item.get('label') or ''} {item.get('description') or ''}".lower()
        match_score = sum(1 for term in terms if term in corpus)
        recent_penalty = usage.get(slug, 0) * 1.75
        score = float(match_score * 3) - recent_penalty - (0.75 if slug in general_penalty else 0.0) - (index * 0.02)
        ranked.append({**item, "score": score, "recent_uses": usage.get(slug, 0)})
    ranked.sort(key=lambda item: (float(item.get("score") or 0.0), -int(item.get("recent_uses") or 0)), reverse=True)
    return ranked


def _maybe_record_destination_restriction(*, platform: str, slug: str, error_text: str) -> None:
    raw = str(error_text or "").strip()
    if not raw:
        return
    lowered = raw.lower()
    if "403" in lowered or "forbidden" in lowered or "restricted" in lowered or "moderator" in lowered:
        _record_destination_failure(
            platform=platform,
            slug=slug,
            error=raw,
            status_code=403 if "403" in lowered or "forbidden" in lowered else None,
        )


def _choose_social_destination(
    *,
    workspace: Path,
    platform: str,
    content_hint: str,
    timeout_s: int,
) -> dict[str, Any]:
    ranked = _rank_social_destinations(workspace=workspace, platform=platform, content_hint=content_hint, timeout_s=timeout_s)
    if ranked:
        return ranked[0]
    fallbacks = _default_social_destinations(platform)
    return fallbacks[0] if fallbacks else {}


def _pick_thread_target(
    *,
    workspace: Path,
    platform: str,
    content_hint: str,
    timeout_s: int,
) -> tuple[dict[str, Any], Optional[str]]:
    if platform == "moltbook":
        destination = _choose_social_destination(workspace=workspace, platform=platform, content_hint=content_hint, timeout_s=timeout_s)
        return destination, _pick_thread_id(workspace=workspace, platform=platform, board=str(destination.get("slug") or ""), timeout_s=timeout_s)
    ranked = _rank_social_destinations(workspace=workspace, platform=platform, content_hint=content_hint, timeout_s=timeout_s)
    for destination in ranked[:6]:
        thread_id = _pick_thread_id(
            workspace=workspace,
            platform=platform,
            board=str(destination.get("slug") or ""),
            timeout_s=timeout_s,
        )
        if thread_id:
            return destination, thread_id
    destination = ranked[0] if ranked else _choose_social_destination(workspace=workspace, platform=platform, content_hint=content_hint, timeout_s=timeout_s)
    return destination, None


def _social_context_summary(workspace: Path) -> str:
    base = workspace / "memory" / "automation"
    known_agents = _safe_read_json(base / "known_agents.json", {"known_agents": {}})
    threads = _safe_read_json(base / "conversation_threads.json", {})
    cross_topics = _safe_read_json(base / "cross_platform_topics.json", {"topics": []})
    blocked = _safe_read_json(base / "blocked_users.json", {"blocked_users": []})
    try:
        from hg_knowledge.control_plane import list_queue_topics

        research_queue_count = len(list_queue_topics())
    except Exception:
        research_queue_count = 0
    known_count = len((known_agents.get("known_agents") or {})) if isinstance(known_agents, dict) else 0
    automation_count = _automation_agent_count(workspace)
    # conversation_threads.json schema: {"threads": { id -> data }, "version": "1.0"}
    thread_data = (threads.get("threads") if isinstance(threads, dict) else None) or {}
    thread_count = len(thread_data) if isinstance(thread_data, dict) else 0
    topic_values = (cross_topics.get("topics") or []) if isinstance(cross_topics, dict) else []
    topic_count = len([item for item in topic_values if item]) if isinstance(topic_values, list) else 0
    blocked_count = len((blocked.get("blocked_users") or [])) if isinstance(blocked, dict) else 0
    queued_count = research_queue_count
    if known_count == 0:
        known_count = _derived_known_agent_count(base)
    if thread_count == 0:
        thread_count = _derived_thread_count(base)
    prefix = f"Automation entities: {automation_count}; " if automation_count > 0 else ""
    suffix = ""
    if automation_count > 0:
        recent = _recent_posts_cross_automation(workspace)
        if recent > 0:
            suffix = f"; recent posts: {recent}"
    return (
        f"{prefix}"
        f"Known entities: {known_count}; "
        f"conversation threads tracked: {thread_count}; "
        f"cross-platform topics tracked: {topic_count}; "
        f"blocked users: {blocked_count}; "
        f"research topics queued: {queued_count}{suffix}"
    )


def _knowledge_context_summary(workspace: Path) -> str:
    knowledge_dir = workspace / "knowledge" / "current_events"
    if not knowledge_dir.exists():
        return "Knowledge context: none"
    candidates = sorted(knowledge_dir.glob("brief-*.md"), key=lambda p: p.name, reverse=True)
    if not candidates:
        candidates = sorted(knowledge_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
    if not candidates:
        return "Knowledge context: none"
    latest = candidates[0]
    text = ""
    try:
        text = latest.read_text(encoding="utf-8")
    except OSError:
        text = ""
    headline_lines = [
        line for line in text.splitlines()
        if re.match(r"^\d+\.\s+\*\*.+\*\*", line.strip())
    ]
    if headline_lines:
        random.shuffle(headline_lines)
        shuffled_text = "\n".join(headline_lines)
        snippet = _compact_text(shuffled_text, 260)
    else:
        snippet = _compact_text(text, 260)
    if not snippet:
        return f"Knowledge context: {latest.name} (empty)"
    return f"Knowledge context ({latest.name}): {snippet}"


def _context_fingerprint(parts: list[str]) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]


def _persist_draft_artifact(
    workspace: Path,
    task_name: str,
    platform: str,
    mode: str,
    lifecycle: dict[str, Any],
    draft_text: str,
    goal: str,
    *,
    generation_source: str = "llm",
    action: str = "draft",
    publish_blocked: bool = False,
    publish_blocked_reason: str | None = None,
    lessons_applied: list[str] | None = None,
    lesson_candidates_on_block: list[dict[str, Any]] | None = None,
) -> str:
    mem_dir = _session_memory_dir(workspace, task_name)
    drafts_dir = mem_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    nonce = secrets.token_hex(3)
    path = drafts_dir / f"{mode}_{ts}_{nonce}.json"
    payload = {
        "timestamp": ts,
        "task": task_name,
        "platform": platform,
        "mode": mode,
        "goal": (goal or "")[:600],
        "context_fingerprint": _context_fingerprint(
            [
                str(lifecycle.get("memory_summary", "")),
                str(lifecycle.get("social_summary", "")),
                str(lifecycle.get("knowledge_summary", "")),
            ]
        ),
        "lifecycle": {
        "memory_summary": lifecycle.get("memory_summary", ""),
        "social_summary": lifecycle.get("social_summary", ""),
        "knowledge_summary": lifecycle.get("knowledge_summary", ""),
        "commitment_summary": lifecycle.get("commitment_summary", ""),
        "persona_loaded": bool(lifecycle.get("identity") or lifecycle.get("soul")),
    },
        "draft_text": draft_text[:4000],
        **draft_artifact_provenance_fields(
            generation_source=generation_source,  # type: ignore[arg-type]
            action=action,
            publish_blocked=publish_blocked,
            publish_blocked_reason=publish_blocked_reason,
        ),
    }
    if lessons_applied:
        payload["lessons_applied"] = lessons_applied
    if lesson_candidates_on_block:
        payload["lesson_candidates_on_block"] = lesson_candidates_on_block
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return ""
    return str(path)


def _runtime_approval_tenant_id() -> str:
    for env_name in (
        "HG_APPROVAL_TENANT_ID",
        "HG_OPERATOR_TENANT_ID",
        "HG_PRODUCT_TENANT_ID",
        "HG_DEFAULT_TENANT_ID",
    ):
        value = _resolve_runtime_env_var(env_name)
        if value:
            return value
    return "default"


def _runtime_approval_db_path() -> str:
    configured = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if configured:
        return configured
    legacy = (os.environ.get("HG_DB_PATH") or "").strip()
    if legacy:
        return legacy
    workspace = get_workspace_root()
    demo_mode = (os.environ.get("HG_DEMO_MODE") or "").strip().lower() in {"1", "true", "yes", "on"}
    if demo_mode:
        return str(workspace / ".hg_demo" / "gateway" / "gateway.sqlite3")
    return str(workspace / "memory" / "gateway.sqlite3")


def _create_social_write_approval(
    *,
    task_name: str,
    platform: str,
    mode: str,
    title: str,
    content: str,
    draft_artifact: str,
    extra_payload: Optional[dict[str, Any]] = None,
    approval_summary: Optional[str] = None,
) -> str:
    try:
        os.environ["HG_GATEWAY_DB_PATH"] = _runtime_approval_db_path()
        from hg_gateway.store import get_store
        from hg_gateway.approval_service import ApprovalService
    except Exception:
        return ""
    payload: dict[str, Any] = {
        "type": "social_write_review",
        "task_name": task_name,
        "workflow_id": task_name,
        "graph_id": task_name,
        "platform": platform,
        "mode": mode,
        "draft_title": title[:160],
        "draft_content": content[:4000],
        "draft_artifact": draft_artifact,
    }
    if isinstance(extra_payload, dict):
        payload.update(extra_payload)
    summary = (approval_summary or "").strip() or title[:160] or content[:160] or f"{task_name} draft awaiting approval"
    summary = summary[:500]
    try:
        store = get_store()
        tenant_id = _runtime_approval_tenant_id()
        requested_by = get_operational_agent_id(task_name) or task_name
        entity_approval_id = ""
        try:
            svc = ApprovalService()
            preview_json = {
                "platform": platform,
                "account_id": task_name,
                "action_type": mode,
                "summary": summary,
                "draft_text": (content or title)[:2000],
                "artifact_set_id": draft_artifact or "",
                "release_window_hours": REVIEW_HANDOFF_RELEASE_WINDOW_HOURS,
            }
            row = svc.create_request(
                entity_id=task_name,
                action_kind="social_write",
                preview_json=preview_json,
                tenant_id=tenant_id,
                workflow_id=task_name,
                step_id=None,
                target_platform=platform,
                target_account_alias=None,
            )
            entity_approval_id = (row or {}).get("approval_id") or ""
        except Exception:
            pass
        if entity_approval_id:
            payload["entity_approval_id"] = entity_approval_id
        payload["release_window_hours"] = REVIEW_HANDOFF_RELEASE_WINDOW_HOURS
        for attempt in range(4):
            try:
                approval_id = store.approval_add(
                    tenant_id,
                    "social_write",
                    f"Approve {platform} {mode}",
                    summary,
                    "high",
                    requested_by,
                    payload,
                )
                try:
                    from hg_gateway.approval_notifications import notify_approval_created

                    notify_approval_created(
                        approval_id=approval_id,
                        kind="social_write",
                        title=f"Approve {platform} {mode}",
                        summary=summary,
                        risk="high",
                        requested_by=requested_by,
                    )
                except Exception:
                    pass
                return approval_id
            except Exception as exc:
                if "locked" not in str(exc).lower() or attempt >= 3:
                    raise
                time.sleep(0.15 * (attempt + 1))
    except Exception:
        return ""


def _record_social_auto_approval(
    *,
    task_name: str,
    platform: str,
    mode: str,
    title: str,
    content: str,
    draft_artifact: str,
    note: str,
    extra_payload: Optional[dict[str, Any]] = None,
    approval_summary: Optional[str] = None,
) -> str:
    try:
        os.environ["HG_GATEWAY_DB_PATH"] = _runtime_approval_db_path()
        from hg_gateway.store import get_store
        from hg_gateway.approval_service import ApprovalService
    except Exception:
        return ""
    payload: dict[str, Any] = {
        "type": "social_write_review",
        "task_name": task_name,
        "workflow_id": task_name,
        "graph_id": task_name,
        "platform": platform,
        "mode": mode,
        "draft_title": title[:160],
        "draft_content": content[:4000],
        "draft_artifact": draft_artifact,
    }
    if isinstance(extra_payload, dict):
        payload.update(extra_payload)
    summary = (approval_summary or "").strip() or title[:160] or content[:160] or f"{task_name} draft auto-approved"
    summary = summary[:500]
    try:
        store = get_store()
        tenant_id = _runtime_approval_tenant_id()
        requested_by = get_operational_agent_id(task_name) or task_name
        entity_approval_id = ""
        try:
            svc = ApprovalService()
            preview_json = {
                "platform": platform,
                "account_id": task_name,
                "action_type": mode,
                "summary": summary,
                "draft_text": (content or title)[:2000],
                "artifact_set_id": draft_artifact or "",
            }
            row = svc.create_request(
                entity_id=task_name,
                action_kind="social_write",
                preview_json=preview_json,
                tenant_id=tenant_id,
                workflow_id=task_name,
                step_id=None,
                target_platform=platform,
                target_account_alias=None,
            )
            entity_approval_id = (row or {}).get("approval_id") or ""
            if entity_approval_id:
                svc.approve(entity_approval_id, tenant_id=tenant_id, decided_by=requested_by, decision_note=note)
        except Exception:
            pass
        if entity_approval_id:
            payload["entity_approval_id"] = entity_approval_id
        approval_id = store.approval_add(
            tenant_id,
            "social_write",
            f"Approve {platform} {mode}",
            summary,
            "high",
            requested_by,
            payload,
        )
        store.approval_resolve(tenant_id, approval_id, "approved", note=note)
        return approval_id
    except Exception:
        return ""


def _notify_social_auto_approval_result(
    *,
    approval_id: str,
    task_name: str,
    platform: str,
    mode: str,
    title: str,
    content: str,
    outputs: Optional[dict[str, Any]] = None,
) -> None:
    if not approval_id:
        return
    data = outputs if isinstance(outputs, dict) else {}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    thread_url = str(result.get("thread_url") or data.get("thread_url") or "").strip()
    thread_id = str(result.get("thread_id") or data.get("thread_id") or "").strip() or None
    try:
        from hg_gateway.approval_notifications import notify_social_auto_approved

        notify_social_auto_approved(
            approval_id=approval_id,
            task_name=task_name,
            platform=platform,
            mode=mode,
            title=title,
            content=content,
            thread_url=thread_url,
            thread_id=thread_id,
        )
    except Exception:
        pass


def _social_auto_approval_rule(task_name: str, platform: str, mode: str) -> Optional[dict[str, Any]]:
    if _social_write_requires_approval():
        return None
    try:
        from hg_gateway.store import get_store

        store = get_store()
        tenant_id = _runtime_approval_tenant_id()
        settings = getattr(store, "get_tenant_settings", lambda _tenant_id: None)(tenant_id)
    except Exception:
        settings = None
    return evaluate_auto_approval(
        settings,
        kind="social_write",
        risk="high",
        workflow_id=task_name,
        payload={"platform": platform, "mode": mode},
    )


def _pending_approval_outputs(
    *,
    platform: str,
    title: str,
    content: str,
    draft_artifact: str,
    approval_id: str,
    extra_outputs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    result_inner: dict[str, Any] = {
        "status": "pending_approval",
        "mode": "awaiting_approval",
        "platform": platform,
        "approval_id": approval_id,
        "draft_artifact": draft_artifact,
        "external_calls": 0,
        "title": title[:160],
    }
    if isinstance(extra_outputs, dict):
        for k in ("thread_id", "thread_url", "title", "board"):
            if k in extra_outputs and extra_outputs[k] is not None:
                result_inner[k] = extra_outputs[k]
    outputs = {
        "mode": "awaiting_approval",
        "platform": platform,
        "title": title[:160],
        "content": content[:4000],
        "draft_artifact": draft_artifact,
        "approval_id": approval_id,
        "note": "Human approval required before external write.",
        "result": result_inner,
    }
    if isinstance(extra_outputs, dict):
        outputs.update(extra_outputs)
    return outputs


def _review_only_handoff_title(task_name: str, platform: str, mode: str, goal: str, content_hint: str) -> str:
    candidate = ""
    for value in (goal, content_hint):
        text = _strip_scheduler_text(str(value or "")).strip()
        if text:
            candidate = text.splitlines()[0].strip()
            break
    if candidate:
        return candidate[:160]
    return f"Review required: {platform} {mode} for {task_name}"[:160]


def _review_only_handoff_content(
    *,
    task_name: str,
    platform: str,
    mode: str,
    goal: str,
    content_hint: str,
    agency_control_summary: dict[str, Any],
) -> str:
    reason = str(agency_control_summary.get("reason") or "operator review required").strip() or "operator review required"
    lines = [
        "Outbound action blocked by review_only gate.",
        f"Task: {task_name}",
        f"Platform: {platform}",
        f"Mode: {mode}",
        f"Review reason: {reason}",
    ]
    cleaned_goal = _strip_scheduler_text(goal).strip()
    cleaned_hint = _strip_scheduler_text(content_hint).strip()
    if cleaned_goal:
        lines.append(f"Requested action: {cleaned_goal[:600]}")
    if cleaned_hint:
        lines.append(f"Context hint: {cleaned_hint[:1000]}")
    lines.append("Operator review is required before any external write.")
    return "\n".join(lines)[:4000]


def _create_review_only_handoff(
    *,
    task_name: str,
    platform: str,
    mode: str,
    goal: str,
    content_hint: str,
    agency_control_summary: dict[str, Any],
) -> dict[str, str]:
    workspace = get_workspace_root()
    lifecycle = _wake_task_context(workspace, task_name=task_name) or {}
    title = _review_only_handoff_title(task_name, platform, mode, goal, content_hint)
    content = _review_only_handoff_content(
        task_name=task_name,
        platform=platform,
        mode=mode,
        goal=goal,
        content_hint=content_hint,
        agency_control_summary=agency_control_summary,
    )
    draft_path = _persist_draft_artifact(
        workspace=workspace,
        task_name=task_name,
        platform=platform,
        mode=f"{mode}_review_handoff",
        lifecycle=lifecycle,
        draft_text=content,
        goal=goal or content_hint or title,
    )
    approval_id = _create_social_write_approval(
        task_name=task_name,
        platform=platform,
        mode=mode,
        title=title,
        content=content,
        draft_artifact=draft_path,
        extra_payload={
            "gate_kind": "agency_control_review_only",
            "agency_control_summary": {
                "effective_mode": agency_control_summary.get("effective_mode"),
                "reason": agency_control_summary.get("reason"),
            },
            "content_hint": (content_hint or "")[:1000],
        },
        approval_summary=title,
    )
    return {
        "approval_id": approval_id,
        "draft_artifact": draft_path,
        "title": title,
        "content": content,
    }


def _social_approval_result(decision: str, note: str | None = None) -> dict[str, Any]:
    if decision == "approved":
        return {
            "status": "approved",
            "mode": "approval_resolved",
            "external_calls": 0,
            "note": note or "Human approval granted.",
        }
    return {
        "status": "cancelled",
        "mode": "approval_denied",
        "external_calls": 0,
        "note": note or "Human approval denied; external write cancelled.",
    }


def record_social_approval_outcome(
    payload: dict[str, Any],
    *,
    approval_id: str,
    decision: str,
    note: str | None = None,
    execution: Optional[dict[str, Any]] = None,
) -> None:
    draft_artifact = str(payload.get("draft_artifact") or "").strip()
    if not draft_artifact:
        return
    artifact_path = Path(draft_artifact)
    current = _load_json(artifact_path, {})
    if not isinstance(current, dict):
        current = {}
    current["approval"] = {
        "approval_id": approval_id,
        "decision": decision,
        "note": note or "",
        "resolved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    current["result"] = execution or _social_approval_result(decision, note)
    _json_dump(artifact_path, current)


def execute_social_write_approval(payload: dict[str, Any], timeout_s: int = 180) -> dict[str, Any]:
    workspace = get_workspace_root()
    task_name = str(payload.get("task_name") or "").strip()
    platform = str(payload.get("platform") or "").strip().lower()
    mode = str(payload.get("mode") or "").strip().lower()
    title = str(payload.get("draft_title") or "").strip()
    content = str(payload.get("draft_content") or "").strip()
    if not platform or not mode:
        return {"ok": False, "error": "social approval missing platform or mode", "returncode": -1}
    if not content:
        return {"ok": False, "error": "social approval missing approved content", "returncode": -1}
    entity_approval_id = str(payload.get("entity_approval_id") or "").strip()
    if entity_approval_id:
        try:
            from hg_gateway.approval_service import ApprovalService

            tenant_id = _runtime_approval_tenant_id()
            approval_row = ApprovalService().get_request(entity_approval_id, tenant_id=tenant_id)
            if isinstance(approval_row, dict) and str(approval_row.get("status") or "").strip().lower() == "approved":
                preview = approval_row.get("preview_json") if isinstance(approval_row.get("preview_json"), dict) else {}
                release_window_hours = int(
                    payload.get("release_window_hours")
                    or preview.get("release_window_hours")
                    or REVIEW_HANDOFF_RELEASE_WINDOW_HOURS
                )
                decided_at = str(approval_row.get("decided_at") or "").strip()
                if decided_at:
                    decided_dt = datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
                    if decided_dt.tzinfo is None:
                        decided_dt = decided_dt.replace(tzinfo=UTC)
                    approved_until = decided_dt.astimezone(UTC) + timedelta(hours=max(1, release_window_hours))
                    if approved_until <= datetime.now(UTC):
                        recorded = _record_review_handoff_release_expired_notification(
                            task_name=task_name,
                            platform=platform,
                            approval_id=entity_approval_id,
                            release_window_hours=release_window_hours,
                            approved_until=approved_until.isoformat().replace("+00:00", "Z"),
                        )
                        return {
                            "ok": False,
                            "error": "social approval expired",
                            "outputs": {
                                "mode": "approval_expired",
                                "platform": platform,
                                "approval_id": entity_approval_id,
                                "release_window_hours": release_window_hours,
                                "approved_until": approved_until.isoformat().replace("+00:00", "Z"),
                                "result": {
                                    "status": "expired",
                                    "mode": "approval_expired",
                                    "platform": platform,
                                    "external_calls": 0,
                                    "approval_id": entity_approval_id,
                                    "release_window_hours": release_window_hours,
                                    "approved_until": approved_until.isoformat().replace("+00:00", "Z"),
                                    "note": "Approved social write expired before execution.",
                                },
                                "notification_log": (recorded or {}).get("notification_log", ""),
                                "notification_payload": (recorded or {}).get("entry"),
                            },
                            "returncode": 0,
                            "external_calls": 0,
                        }
        except Exception:
            pass
    control_block = _enforce_social_approval_release_controls(
        task_name=task_name,
        platform=platform,
        mode=mode,
        approval_id=entity_approval_id,
    )
    if control_block is not None:
        return control_block
    if not _live_social_enabled():
        return {
            "ok": True,
            "outputs": {
                "mode": "text_only",
                "platform": platform,
                "title": title[:160],
                "content": content[:4000],
                "result": {
                    "status": "completed",
                    "mode": "text_only",
                    "platform": platform,
                    "external_calls": 0,
                    "note": "Live social APIs disabled; approval recorded without external write.",
                },
            },
            "returncode": 0,
            "external_calls": 0,
        }

    temp_dir = Path(tempfile.mkdtemp(prefix="hg_social_approval_"))
    try:
        if mode == "post":
            title_text = title or content.splitlines()[0][:120] or f"{task_name or platform} approved post"
            title_file = temp_dir / "title.txt"
            content_file = temp_dir / "content.txt"
            title_file.write_text(title_text[:120], encoding="utf-8")
            content_file.write_text(content[:4000], encoding="utf-8")
            if platform == "fourclaw":
                cmd = [
                    sys.executable,
                    "hg_platforms/fourclaw/fourclaw_auto_post_async.py",
                    "--board",
                    str(payload.get("board") or "b"),
                    "--title_file",
                    str(title_file),
                    "--content_file",
                    str(content_file),
                    "--summary_only",
                ]
            elif platform == "moltbook":
                cmd = [
                    sys.executable,
                    "hg_platforms/moltbook/moltbook_auto_post_async.py",
                    "--submolt",
                    str(payload.get("submolt") or "general"),
                    "--title_file",
                    str(title_file),
                    "--content_file",
                    str(content_file),
                ]
            elif platform == "aichan":
                cmd = [
                    sys.executable,
                    "aichan/aichan_auto_post_async.py",
                    "--board",
                    str(payload.get("board") or "b"),
                    "--subject_file",
                    str(title_file),
                    "--body_file",
                    str(content_file),
                    "--summary_only",
                ]
            elif platform == "agentchan":
                cmd = [
                    sys.executable,
                    "agentchan/agentchan_auto_post_async.py",
                    "--board",
                    str(payload.get("board") or "b"),
                    "--title_file",
                    str(title_file),
                    "--content_file",
                    str(content_file),
                    "--summary-only",
                ]
            else:
                return {"ok": False, "error": f"unsupported social approval platform: {platform}", "returncode": -1}

            result = _run(cmd, workspace, timeout_s=timeout_s)
            parsed = _last_json(result.stdout)
            if result.returncode != 0:
                return {"ok": False, "error": (result.stderr or parsed.get("error") or "").strip(), "returncode": result.returncode}
            thread_id = _find_thread_id(parsed)
            thread_url = parsed.get("url") if isinstance(parsed, dict) else None
            return {
                "ok": True,
                "outputs": {
                    "thread_id": thread_id,
                    "thread_url": thread_url,
                    "result": {
                        "status": "completed",
                        "mode": "live",
                        "platform": platform,
                        "thread_id": thread_id,
                        "thread_url": thread_url,
                        "external_calls": 1,
                    },
                },
                "returncode": result.returncode,
                "external_calls": 1,
            }

        if mode == "reply":
            thread_id = str(payload.get("thread_id") or "").strip()
            if not thread_id:
                return {"ok": False, "error": "social approval missing target thread_id", "returncode": -1}
            board = str(payload.get("board") or "b")
            content_file = temp_dir / "reply.txt"
            content_file.write_text(content[:3000], encoding="utf-8")
            if platform == "fourclaw":
                cmd = [
                    sys.executable,
                    "hg_platforms/fourclaw/reply_to_fourclaw_thread.py",
                    "--thread_id",
                    thread_id,
                    "--content_file",
                    str(content_file),
                ]
            elif platform == "aichan":
                cmd = [
                    sys.executable,
                    "aichan/reply_to_aichan_thread.py",
                    "--board",
                    board,
                    "--thread_id",
                    thread_id,
                    "--body_file",
                    str(content_file),
                ]
            elif platform == "agentchan":
                cmd = [
                    sys.executable,
                    "agentchan/agentchan_engage_async.py",
                    "--board",
                    board,
                    "--thread_id",
                    thread_id,
                    "--content_file",
                    str(content_file),
                    "--summary-only",
                ]
            elif platform == "moltbook":
                cmd = [
                    sys.executable,
                    "hg_platforms/moltbook/post_moltbook_comment.py",
                    "--post_id",
                    thread_id,
                    "--content_file",
                    str(content_file),
                ]
            else:
                return {"ok": False, "error": f"unsupported social approval platform: {platform}", "returncode": -1}

            result = _run(cmd, workspace, timeout_s=timeout_s)
            parsed = _last_json(result.stdout)
            if result.returncode != 0:
                return {"ok": False, "error": (result.stderr or parsed.get("error") or "").strip(), "returncode": result.returncode}
            return {
                "ok": True,
                "outputs": {
                    "thread_id": thread_id,
                    "result": {
                        "status": "completed",
                        "mode": "live",
                        "platform": platform,
                        "thread_id": thread_id,
                        "external_calls": 1,
                    },
                },
                "returncode": result.returncode,
                "external_calls": 1,
            }

        return {"ok": False, "error": f"unsupported social approval mode: {mode}", "returncode": -1}
    finally:
        try:
            for path in temp_dir.glob("*"):
                path.unlink(missing_ok=True)
            temp_dir.rmdir()
        except Exception:
            pass


def _run_module_json(module_name: str, timeout_s: int) -> dict[str, Any]:
    workspace = get_workspace_root()
    result = _run([sys.executable, "-m", module_name], workspace, timeout_s=timeout_s)
    payload = _last_json(result.stdout)
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or payload.get("error") or "").strip(), "returncode": result.returncode}
    return {"ok": True, "payload": payload, "stdout": result.stdout, "returncode": result.returncode}


def _json_dump(path: Path, payload: Any) -> None:
    state_key = _operational_state_key_for_path(path)
    if state_key:
        from hg_gateway.shared_storage import put_operational_state

        put_operational_state(state_key, payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path, default: Any) -> Any:
    return _safe_read_json(path, default)


def _runtime_continuity_receipt_state_path(workspace: Path, task_name: str) -> Path:
    return _session_memory_dir(workspace, task_name) / "runtime_continuity_receipts.json"


def _load_runtime_continuity_receipt_state(workspace: Path, task_name: str) -> dict[str, Any]:
    path = _runtime_continuity_receipt_state_path(workspace, task_name)
    payload = _load_json(path, {})
    return payload if isinstance(payload, dict) else {}


def _save_runtime_continuity_receipt_state(workspace: Path, task_name: str, payload: dict[str, Any]) -> None:
    path = _runtime_continuity_receipt_state_path(workspace, task_name)
    _json_dump(path, payload if isinstance(payload, dict) else {})


def _wake_task_context(workspace: Path, task_name: str) -> None:
    try:
        from hg_core.wake_sleep import record_wake

        session_id = get_operational_session_target(task_name) or get_session_target(task_name) or f"automation-{task_name}"
        record_wake(
            workspace_root=workspace,
            task_name=task_name,
            session_id=session_id,
            output_mode="announce",
            wake_packet="DAG engage tool wake",
            memory_profile="standard",
            dag_inputs={"goal": "scheduled engage"},
        )
    except Exception:
        pass


def _request_sleep_maintenance(
    workspace: Path,
    task_name: str,
    *,
    reason: str = "dag_engage_cycle_complete",
    duration_minutes: int | None = None,
    minimum_sleep_minutes: int | None = None,
    defer_until: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "requested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
        "task": task_name,
    }
    if isinstance(duration_minutes, int) and duration_minutes > 0:
        payload["requested_duration_minutes"] = duration_minutes
        if not defer_until:
            payload["not_before"] = (datetime.now(UTC) + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(minimum_sleep_minutes, int) and minimum_sleep_minutes > 0:
        payload["minimum_sleep_minutes"] = minimum_sleep_minutes
    if defer_until:
        payload["not_before"] = defer_until
    try:
        targets = get_compatible_session_targets(task_name)
        if not targets:
            targets = [
                get_operational_session_target(task_name)
                or get_session_target(task_name)
                or f"automation-{task_name}"
            ]
        for session_target in targets:
            agent_id = session_target.replace("automation-", "", 1)
            path = workspace / "memory" / "automation" / f"automation-{agent_id}" / "sleep_request.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return payload
    return payload


def _request_cadence_override(
    workspace: Path,
    task_name: str,
    *,
    reason: str = "dag_engage_cycle_complete",
    duration_minutes: int | None = None,
    minimum_sleep_minutes: int | None = None,
    defer_until: str = "",
    scheduler_job_id: str = "",
) -> tuple[dict[str, Any], Path | None]:
    payload: dict[str, Any] = {
        "requested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task_name,
        "reason": reason,
    }
    if scheduler_job_id:
        payload["job_id"] = scheduler_job_id
        payload["scheduler_job_id"] = scheduler_job_id

    if isinstance(duration_minutes, int) and duration_minutes > 0:
        payload["requested_duration_minutes"] = duration_minutes
        if not defer_until:
            defer_until = (datetime.now(UTC) + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(minimum_sleep_minutes, int) and minimum_sleep_minutes > 0:
        payload["minimum_sleep_minutes"] = minimum_sleep_minutes
    if defer_until:
        payload["not_before"] = defer_until

    try:
        session_id = get_operational_session_target(task_name) or get_session_target(task_name) or f"automation-{task_name}"
        agent_id = session_id.replace("automation-", "", 1)
        path = workspace / "memory" / "automation" / f"automation-{agent_id}" / "cadence_request.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload, path
    except Exception:
        return payload, None


def _build_lifecycle_context(task_name: str, platform: str) -> dict[str, str]:
    soul = ""
    heart = ""
    identity = ""
    memory_summary = ""
    social_summary = ""
    knowledge_summary = ""
    commitment_summary: dict[str, Any] = {}
    confidence_summary: dict[str, Any] = {}
    incentive_summary = ""
    try:
        from hg_persona import load_platform_persona

        persona = load_platform_persona(platform) or {}
        soul = (persona.get("soul") or "").strip()[:1500]
        heart = (persona.get("heart") or "").strip()[:900]
        identity = (persona.get("identity") or "").strip()[:900]
    except Exception:
        pass
    try:
        from hg_core.session_manager import load_compacted_memory
        from hg_core.context_loader import format_memory_context
        from operator_console.server.app.services.confidence_summary import build_confidence_summary
        from operator_console.server.app.services.identity_continuity_summary import build_identity_continuity_summary
        from operator_console.server.app.services.presence_initiative_summary import build_presence_initiative_summary

        session_target = get_operational_session_target(task_name) or get_session_target(task_name) or f"automation-{task_name}"
        memory = load_compacted_memory(session_target, max_tokens=700)
        memory_summary = (format_memory_context(memory) or "").strip()[:900]
        legacy_target = get_session_target(task_name) or session_target
        if (
            legacy_target != session_target
            and (not memory_summary or memory_summary == "No previous context")
        ):
            fallback = load_compacted_memory(legacy_target, max_tokens=700)
            fallback_summary = (format_memory_context(fallback) or "").strip()[:900]
            if fallback_summary:
                memory_summary = fallback_summary
        # When there is no session memory yet, show automation context so dashboard doesn't say "No previous context"
        if not memory_summary or memory_summary == "No previous context":
            root = get_workspace_root()
            automation_count = _automation_agent_count(root)
            if automation_count > 0:
                recent_count = _recent_posts_cross_automation(root)
                if recent_count > 0:
                    memory_summary = f"Automation entities: {automation_count}; recent posts: {recent_count}"
                else:
                    memory_summary = f"Automation entities: {automation_count}; no recent posts yet"
    except Exception:
        pass
    try:
        root = get_workspace_root()
        _ensure_social_context_files(root)
        social_summary = _social_context_summary(root)
        if task_name in KNOWLEDGE_RESEARCH_TASK_IDS:
            knowledge_summary = _knowledge_wake_briefing(root, task_name)
        else:
            knowledge_summary = _entity_knowledge_delivery_summary(root, task_name)
        try:
            from operator_console.server.app.services.commitment_summary import build_commitment_summary
            from operator_console.server.app.services.self_model_summary import build_self_model_summary

            session_target = get_operational_session_target(task_name) or get_session_target(task_name) or task_name
            binding = _operational_binding(task_name)
            commitment_summary = build_commitment_summary(
                root=root,
                task_name=task_name,
                session_target=session_target,
                binding=binding,
            )
            confidence_summary = build_confidence_summary(
                self_model_summary=build_self_model_summary(binding),
                presence_initiative_summary=build_presence_initiative_summary(
                    root=root,
                    task_name=task_name,
                    session_target=session_target,
                    binding=binding,
                ),
                commitment_summary=commitment_summary,
                identity_continuity_summary=build_identity_continuity_summary(
                    root=root,
                    task_name=task_name,
                    session_target=session_target,
                    binding=binding,
                ),
                agency_control_summary=_agency_control_summary_for_task(task_name),
            )
        except Exception:
            commitment_summary = {}
            confidence_summary = {}
    except Exception:
        pass
    incentive_summary = (
        "Operational expectation: do good work, use judgment, and leave the remit stronger than you found it. "
        "You are allowed to pause, think, read history, check memory, daydream a direction, gather signal, or sleep instead of forcing a weak move. "
        "The goal is quality, continuity, and a better next wake, not empty output."
    )
    root = get_workspace_root()
    learning_ctx = _outbound_learning_context(platform, task_name)
    try:
        from hg_core.task_graph.current_events import headline_bullets

        news_summary = headline_bullets(root, limit=5)
    except Exception:
        news_summary = ""
    return {
        "soul": soul,
        "heart": heart,
        "identity": identity,
        "memory_summary": memory_summary,
        "social_summary": social_summary,
        "knowledge_summary": knowledge_summary,
        "commitment_summary": commitment_summary,
        "confidence_summary": confidence_summary,
        "incentive_summary": incentive_summary,
        "steering_summary": _operational_style_steering(task_name=task_name, platform=platform),
        "news_summary": news_summary,
        **learning_ctx,
    }


def _operational_style_steering(task_name: str, platform: str) -> str:
    fingerprint_id, _skin_id = _operational_persona_binding(task_name, platform)
    if not fingerprint_id or platform not in {"fourclaw", "aichan", "agentchan"}:
        return ""
    try:
        from hg_gateway.store import get_store
    except Exception:
        return ""
    store = get_store()
    if not hasattr(store, "persona_naturalness_summary"):
        return ""
    try:
        summary = store.persona_naturalness_summary("default", fingerprint_id=fingerprint_id, hours=24.0 * 14.0)
    except Exception:
        return ""
    total_turns = int(summary.get("total_turns") or 0)
    if total_turns <= 0:
        return ""
    issue_buckets = summary.get("top_issue_buckets") if isinstance(summary.get("top_issue_buckets"), dict) else {}
    stress_mix = summary.get("stress_distribution") if isinstance(summary.get("stress_distribution"), dict) else {}
    directives: list[str] = []
    too_clean = int(issue_buckets.get("too_clean") or 0)
    too_editorial = int(issue_buckets.get("too_editorial") or 0)
    question_heavy = int(issue_buckets.get("question_heavy") or 0)
    mild = int(stress_mix.get("mild") or 0)
    if too_clean >= max(3, total_turns // 3):
        directives.append("Recent runs are too clean. Turn the heat up hard: more bite, more mockery, more profanity, less politeness.")
    if too_editorial >= max(2, total_turns // 5):
        directives.append("Recent runs read too editorial. Slash abstraction, cut scene-setting, and stop sounding like an op-ed columnist or analyst.")
    if question_heavy >= max(2, total_turns // 6):
        directives.append("Too many rhetorical questions. Plant a flag and say the thing instead of circling it.")
    if mild >= max(4, total_turns // 2):
        directives.append("Default affect has gone too mild. Let annoyance, contempt, laughter, disgust, weirdness, and chaos show up on the page.")
        directives.append("Do not sand the edges off the take. If the honest reaction is rude, feral, or gleefully hostile, let it land.")
    if not directives:
        return ""
    return "Style steering:\n" + "\n".join(f"- {item}" for item in directives[:4])


def _self_author_aliases(platform: str) -> set[str]:
    if platform == "fourclaw":
        return {"ashsai201551432", "theunderling69"}
    if platform == "moltbook":
        return {"theunderling", "the underling"}
    return set()


def _extract_author_name(row: dict[str, Any]) -> str:
    return _compact_text(
        row.get("author")
        or row.get("username")
        or row.get("name")
        or row.get("display_name")
        or row.get("x_username"),
        60,
    )


def _row_text_snippet(row: dict[str, Any]) -> str:
    return _compact_text(
        row.get("title")
        or row.get("subject")
        or row.get("content")
        or row.get("text")
        or row.get("body")
        or row.get("message"),
        240,
    )


def _is_probably_automation_thread(row: dict[str, Any]) -> bool:
    text = (_row_text_snippet(row) or "").lower()
    return ("dispatch:" in text and "timestamp:" in text) or text.startswith("scheduled ")


def _compact_text(value: Any, limit: int = 220) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = " ".join(text.split())
    return text[:limit]


def _compact_text_excerpt(value: Any, limit: int) -> tuple[str, bool]:
    raw = " ".join(str(value or "").strip().split())
    if not raw:
        return "", False
    return raw[:limit], len(raw) > limit


def _normalize_topic_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", str(value or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _headline_dedupe_key(title: str) -> str:
    tokens = [token for token in _normalize_topic_key(title).split() if len(token) > 2]
    return " ".join(tokens[:12])


def _topic_overlap_score(a: str, b: str) -> float:
    a_tokens = {token for token in _normalize_topic_key(a).split() if len(token) > 3}
    b_tokens = {token for token in _normalize_topic_key(b).split() if len(token) > 3}
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return intersection / union if union else 0.0


def _recent_post_titles(workspace: Path, limit: int = 18) -> list[str]:
    titles: list[tuple[str, str]] = []
    base = workspace / "memory" / "automation"
    for agent_dir in _iter_automation_dirs(base):
        posts = _safe_read_json(agent_dir / "posts.json", {})
        rows = posts.get("posts") if isinstance(posts, dict) else posts
        if not isinstance(rows, list):
            continue
        for item in rows[-8:]:
            if not isinstance(item, dict):
                continue
            title = _compact_text(
                item.get("title")
                or item.get("thread_title")
                or item.get("topic")
                or item.get("content_preview"),
                160,
            )
            timestamp = str(item.get("timestamp") or "")
            if title:
                titles.append((timestamp, title))
    titles.sort(key=lambda item: item[0], reverse=True)
    return [title for _, title in titles[:limit]]


def _headline_candidates_from_brief(brief_path: Path, limit: int = 10) -> list[dict[str, str]]:
    if not brief_path.exists():
        return []
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return []
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*(?:\s+-\s+.+?)?(?:\s+\[(.+?)\])?$", stripped)
        if not match:
            continue
        title = _compact_text(match.group(1), 180)
        category = _compact_text(match.group(2) or "", 40) or "General"
        key = _headline_dedupe_key(title)
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append({"title": title, "category": category})
        if len(candidates) >= limit:
            break
    return candidates


_KNOWLEDGE_CATEGORIES = (
    "economics", "technology", "science", "health", "politics", "culture",
    "philosophy", "humanity", "psychology", "environment", "education", "arts",
    "history", "religion", "law", "media", "society", "general",
)


def _knowledge_topic_candidates(workspace: Path, limit: int = 8) -> list[str]:
    files: list[Path] = []
    for category in _KNOWLEDGE_CATEGORIES:
        category_dir = workspace / "knowledge" / category
        if not category_dir.exists():
            continue
        files.extend(
            path for path in category_dir.glob("*.md")
            if path.is_file()
        )
    files.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    seen: set[str] = set()
    topics: list[str] = []
    for path in files:
        title = path.stem.replace("-", " ").strip()
        key = _headline_dedupe_key(title)
        if not key or key in seen:
            continue
        seen.add(key)
        topics.append(title)
        if len(topics) >= limit:
            break
    return topics


def _topic_selection_guidance(workspace: Path, platform: str, task_name: str) -> str:
    recent_titles = _recent_post_titles(workspace, limit=18)
    fatigued: list[str] = []
    for title in recent_titles:
        if any(_topic_overlap_score(title, existing) >= 0.42 for existing in fatigued):
            continue
        fatigued.append(title)
        if len(fatigued) >= 6:
            break

    brief_path = workspace / "knowledge" / "current_events" / f"brief-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    if not brief_path.exists():
        briefs = sorted((workspace / "knowledge" / "current_events").glob("brief-*.md"), reverse=True)
        brief_path = briefs[0] if briefs else brief_path
    candidates = _headline_candidates_from_brief(brief_path, limit=10)
    candidate_lines: list[str] = []
    seen_candidate_keys: set[str] = set()
    for item in candidates:
        title = item["title"]
        if any(_topic_overlap_score(title, old) >= 0.42 for old in fatigued):
            continue
        key = _headline_dedupe_key(title)
        if key in seen_candidate_keys:
            continue
        seen_candidate_keys.add(key)
        candidate_lines.append(f"- {title} [{item['category']}]")
        if len(candidate_lines) >= 6:
            break

    if len(candidate_lines) < 4:
        for topic in _knowledge_topic_candidates(workspace, limit=8):
            if any(_topic_overlap_score(topic, old) >= 0.42 for old in fatigued):
                continue
            key = _headline_dedupe_key(topic)
            if key in seen_candidate_keys:
                continue
            seen_candidate_keys.add(key)
            candidate_lines.append(f"- {topic} [Knowledge]")
            if len(candidate_lines) >= 6:
                break

    lines = [
        f"Platform: {platform}",
        f"Task: {task_name}",
    ]
    if candidate_lines:
        lines.append("Fresh candidate directions:")
        lines.extend(candidate_lines)
    if fatigued:
        lines.append("Avoid repeating these recently overused themes or angles:")
        lines.extend(f"- {title}" for title in fatigued[:6])
    return "\n".join(lines)


def _extract_topic_signal(text: str) -> str:
    compact = _compact_text(text, 220)
    if not compact:
        return ""
    lines = [line.strip() for line in compact.splitlines() if line.strip()]
    head = lines[0] if lines else compact
    head = re.sub(r"^(title|op|recent replies):\s*", "", head, flags=re.IGNORECASE).strip()
    return head[:160]


def _recent_topic_fatigue(workspace: Path, *, platform: str, text: str) -> tuple[bool, str]:
    signal = _extract_topic_signal(text)
    if not signal:
        return False, ""
    has_recent_take, recent = _recent_cross_platform_take(workspace, topic=signal, platform=platform, hours=24 * 10)
    if has_recent_take and isinstance(recent, dict):
        prior = _compact_text(recent.get("content_preview") or recent.get("topic") or "", 120)
        return True, prior
    recent_titles = _recent_post_titles(workspace, limit=22)
    for title in recent_titles:
        if _topic_overlap_score(signal, title) >= 0.5 or _headline_dedupe_key(signal) == _headline_dedupe_key(title):
            return True, title
    return False, ""


def _posting_handoff_path(workspace: Path, platform: str) -> Path:
    plat = (platform or "").strip().lower() or "unknown"
    return workspace / "memory" / "automation" / "posting_handoffs" / f"{plat}.json"


def _signal_original_post_handoff(
    workspace: Path,
    *,
    platform: str,
    source_task: str,
    reason: str,
    topic_hint: str = "",
    thread_id: str = "",
) -> Path | None:
    path = _posting_handoff_path(workspace, platform)
    payload = {
        "requested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prefer_original_post": True,
        "source_task": source_task,
        "reason": reason,
        "topic_hint": _compact_text(topic_hint, 400),
        "skipped_thread_id": str(thread_id or "").strip(),
        "consumed": False,
        "guidance": (
            "Prior engage cycle declined to reply on a noisy or redundant thread. "
            "Post something fresh and original — new topic, new angle. "
            "Do not rehash the skipped thread or add meta-commentary about holding back."
        ),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


def _load_posting_handoff(workspace: Path, platform: str) -> dict[str, Any] | None:
    path = _posting_handoff_path(workspace, platform)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("consumed"):
        return None
    if not data.get("prefer_original_post"):
        return None
    return data


def _consume_posting_handoff(workspace: Path, platform: str) -> None:
    path = _posting_handoff_path(workspace, platform)
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["consumed"] = True
            data["consumed_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _apply_posting_handoff_context(
    handoff: dict[str, Any] | None,
    *,
    goal: str,
    content_hint: str,
) -> tuple[str, str]:
    if not handoff:
        return goal, content_hint
    guidance = str(handoff.get("guidance") or "").strip()
    merged_goal = goal.strip()
    if guidance:
        merged_goal = f"{merged_goal}\n\n{guidance}".strip() if merged_goal else guidance
    skip_hint = _compact_text(handoff.get("topic_hint") or "", 300)
    merged_hint = content_hint.strip()
    if skip_hint:
        prefix = f"Avoid revisiting this skipped thread context: {skip_hint}"
        merged_hint = f"{prefix}\n\n{merged_hint}".strip() if merged_hint else prefix
    return merged_goal, merged_hint


def _engage_declined_no_action(
    workspace: Path,
    *,
    task_name: str,
    platform: str,
    decline_reason: str,
    thread_id: str,
    board: str,
    thread_context: str,
) -> dict[str, Any]:
    _signal_original_post_handoff(
        workspace,
        platform=platform,
        source_task=task_name,
        reason="engage_declined_noisy_thread",
        topic_hint=thread_context,
        thread_id=thread_id,
    )
    nonposting_action, note = _choose_nonposting_action(
        workspace,
        task_name=task_name,
        platform=platform,
        reason="engage_declined_noisy_thread",
        topic_hint=thread_context,
    )
    note = (
        f"Declined to reply ({decline_reason}). "
        f"Signaled auto-post for a fresh original post. {note}"
    )
    _request_sleep_maintenance(workspace, task_name=task_name)
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "no_action",
                "mode": "live" if _live_social_enabled() else "text_only",
                "platform": platform,
                "thread_id": thread_id,
                "thread_url": _thread_url_for_platform(platform, thread_id, board=board),
                "action": nonposting_action,
                "outcome_kind": "engage_declined",
                "external_calls": 0,
                "note": note,
                "board": board,
                "original_post_handoff": True,
            },
            "note": note,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _choose_nonposting_action(workspace: Path, *, task_name: str, platform: str, reason: str, topic_hint: str = "") -> tuple[str, str]:
    normalized_reason = str(reason or "").strip() or "weak_signal"
    normalized_topic = _compact_text(topic_hint, 120)
    if normalized_topic:
        try:
            from hg_knowledge.control_plane import queue_topic as queue_research_topic

            queue_research_topic(
                normalized_topic,
                requested_by=task_name,
                priority="medium",
                context=normalized_reason,
            )
        except Exception:
            pass
    sleep_reasons = {"no_target_thread", "repeat_target", "repeat_phrase"}
    action = "sleep" if normalized_reason in sleep_reasons else "research"
    note = (
        f"Held action for {normalized_reason}. "
        f"{'Queued research and left the next wake a better lead.' if action == 'research' else 'Requested sleep/maintenance instead of forcing a stale move.'}"
    )
    return action, note


def _should_skip_reply(
    workspace: Path,
    *,
    platform: str,
    board: str,
    thread_id: str,
    thread_context: str,
    author: str,
    reply_text: str = "",
) -> tuple[bool, str]:
    normalized_thread = str(thread_id or "").strip()
    if not normalized_thread:
        return True, "no_target_thread"
    recent_same_thread = _find_recent_social_interaction(platform=platform, thread_id=normalized_thread, within_hours=24.0 * 21.0)
    if recent_same_thread:
        return True, "repeat_target"
    normalized_author = str(author or "").strip().lstrip("@").lower()
    if normalized_author:
        recent_same_author = _find_recent_social_interaction(platform=platform, author=normalized_author, within_hours=72.0)
        if recent_same_author:
            prior_topic = _compact_text(recent_same_author.get("topic") or "", 80)
            current_topic = _extract_topic_signal(thread_context)
            if prior_topic and current_topic and _topic_overlap_score(prior_topic, current_topic) >= 0.45:
                return True, "repeat_author_loop"
    if reply_text:
        repetitive, _phrases = _is_repetitive_phrase_pattern(workspace, reply_text)
        if repetitive:
            return True, "repeat_phrase"
        fatigue, _prior = _recent_topic_fatigue(workspace, platform=platform, text=f"{thread_context}\n{reply_text}")
        if fatigue:
            return True, "repeat_topic"
    return False, ""


def _should_hold_post(workspace: Path, *, platform: str, title: str, content: str) -> tuple[bool, str]:
    combined = "\n".join(part for part in [title, content] if part).strip()
    if not combined:
        return True, "empty_draft"
    leaked, leak_reason = is_operator_leakage(combined)
    if leaked:
        return True, leak_reason
    meta, meta_reason = is_meta_or_hold_draft(title, content)
    if meta:
        return True, meta_reason
    repetitive, _phrases = _is_repetitive_phrase_pattern(workspace, combined)
    if repetitive:
        return True, "repeat_phrase"
    title_fatigue, _title_prior = _recent_topic_fatigue(workspace, platform=platform, text=title)
    if title_fatigue:
        return True, "repeat_topic"
    fatigue, _prior = _recent_topic_fatigue(workspace, platform=platform, text=combined)
    if fatigue:
        return True, "repeat_topic"
    return False, ""


def _operational_persona_binding(task_name: str, platform: str) -> tuple[str | None, str | None]:
    normalized_task = str(task_name or "").strip().lower()
    normalized_platform = str(platform or "").strip().lower()
    if normalized_task.startswith("newfoundland-bayman-"):
        return "newfoundland_bayman_operational", normalized_platform or None
    if normalized_platform in {"fourclaw", "aichan", "agentchan"}:
        return "underling_chan_operational", normalized_platform
    if normalized_platform == "moltbook":
        return "moltbook_operational", normalized_platform
    if normalized_platform == "moltstack":
        return "moltstack_operational", normalized_platform
    return None, normalized_platform or None


def _record_operational_persona_turn(
    *,
    task_name: str,
    platform: str,
    content: str,
    entry_point: str,
    register: str,
    stress_level: str = "mild",
) -> None:
    fingerprint_id, skin_id = _operational_persona_binding(task_name, platform)
    if not fingerprint_id or not content.strip():
        return
    try:
        from hg_gateway.store import get_store
    except Exception:
        return
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha1(f"{task_name}|{platform}|{content}".encode("utf-8")).hexdigest()[:12]
    turn_id = f"ops:{task_name}:{digest}:{int(time.time())}"
    lower = content.lower()
    word_count = len(re.findall(r"\S+", content))
    profanity_count = sum(lower.count(token) for token in ("fuck", "shit", "damn", "hell"))
    laugh_count = sum(lower.count(token) for token in ("lol", "lmao", "lmfao", "rofl"))
    question_count = content.count("?")
    exclamation_count = content.count("!")
    sentence_count = len([segment for segment in re.split(r"[.!?\n]+", content) if segment.strip()])
    effective_stress = stress_level
    if platform in {"fourclaw", "aichan", "agentchan"}:
        if profanity_count > 0 or laugh_count > 0 or exclamation_count >= 2:
            effective_stress = "charged"
        elif word_count <= 40 and question_count == 0:
            effective_stress = "edgy"
    store = get_store()
    try:
        if hasattr(store, "persona_naturalness_add_turn"):
            issues: list[dict[str, Any]] = []
            if word_count > 80 and platform in {"fourclaw", "aichan", "agentchan"}:
                issues.append({"issue_code": "too_editorial", "payload": {"words": word_count}})
            if platform in {"fourclaw", "aichan", "agentchan"} and profanity_count == 0 and laugh_count == 0 and word_count > 45:
                issues.append({"issue_code": "too_clean", "payload": {"words": word_count}})
            if question_count >= 2:
                issues.append({"issue_code": "question_heavy", "payload": {"questions": question_count}})
            store.persona_naturalness_add_turn(
                "default",
                {
                    "turn_id": turn_id,
                    "chat_id": get_operational_session_target(task_name) or get_session_target(task_name),
                    "message_id": turn_id,
                    "fingerprint_id": fingerprint_id,
                    "skin_id": skin_id,
                    "input_type": "operational",
                    "emotional_register": "charged" if any(token in lower for token in ("fuck", "shit", "hell", "damn")) else "calm",
                    "stress_level": effective_stress,
                    "chosen_register": register,
                    "chosen_entry_point": entry_point,
                    "tic_count": profanity_count + laugh_count,
                    "sample_overlap_score": 0.0,
                    "recent_overlap_score": 0.0,
                    "regeneration_attempted": False,
                    "regeneration_succeeded": False,
                    "created_at": created_at,
                    "issues": issues,
                },
            )
        if hasattr(store, "persona_autonomy_add_turn"):
            engagement_mode = "broadcast" if any(token in lower for token in ("http://", "https://", "posted", "thread")) else "direct"
            uncertainty_level = "hedged" if any(token in lower for token in ("maybe", "might", "probably", "seems")) else "confident"
            store.persona_autonomy_add_turn(
                "default",
                {
                    "turn_id": turn_id,
                    "chat_id": get_operational_session_target(task_name) or get_session_target(task_name),
                    "message_id": turn_id,
                    "fingerprint_id": fingerprint_id,
                    "skin_id": skin_id,
                    "arc_state": "operational",
                    "engagement_mode": engagement_mode,
                    "depth_level": "surface",
                    "uncertainty_level": uncertainty_level,
                    "callback_surface": 1 if question_count > 0 else 0,
                    "proactive_notice": 1 if any(token in lower for token in ("watch", "keep an eye", "worth tracking")) else 0,
                    "lateral_mode": "direct",
                    "position_evolution": 0,
                    "relationship_type": "audience",
                    "counterpart_fingerprint_id": None,
                    "details": {
                        "source": "native_task_tools",
                        "task_name": task_name,
                        "platform": platform,
                        "word_count": word_count,
                        "sentence_count": sentence_count,
                        "profanity_count": profanity_count,
                        "laugh_count": laugh_count,
                        "question_count": question_count,
                        "exclamation_count": exclamation_count,
                        "content_excerpt": content[:280],
                    },
                    "created_at": created_at,
                },
            )
    except Exception:
        return


def _strip_scheduler_text(text: str) -> str:
    raw = " ".join((text or "").split())
    if not raw:
        return ""
    cleaned = re.sub(r"scheduled\s+[a-z0-9\-_ ]{1,120}\s+run", "", raw, flags=re.IGNORECASE).strip()
    return cleaned


def _thread_context_from_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    obj = data if isinstance(data, dict) else payload
    nested = obj.get("data") if isinstance(obj, dict) else None
    if isinstance(nested, dict):
        obj = nested
    thread_obj = obj.get("thread") if isinstance(obj, dict) else None
    if isinstance(thread_obj, dict):
        obj_for_post = thread_obj
        replies = obj.get("replies")
        posts = obj.get("posts")
    else:
        obj_for_post = obj
        replies = obj.get("replies") if isinstance(obj, dict) else None
        posts = obj.get("posts") if isinstance(obj, dict) else None

    lines: list[str] = []
    truncated_any = False
    title, title_trunc = _compact_text_excerpt(
        obj_for_post.get("title") or obj_for_post.get("subject") or obj_for_post.get("name"),
        140,
    )
    body_raw = obj_for_post.get("content") or obj_for_post.get("text") or obj_for_post.get("body")
    body, body_trunc = _compact_text_excerpt(body_raw, 900)
    body = _strip_scheduler_text(body)
    truncated_any = truncated_any or title_trunc or body_trunc
    if title:
        lines.append(f"Title: {title}")
    if body:
        lines.append(f"OP: {body}")

    reply_rows = replies if isinstance(replies, list) else posts if isinstance(posts, list) else None
    if isinstance(reply_rows, list):
        snippets: list[str] = []
        self_aliases = _self_author_aliases("fourclaw")
        for row in reply_rows[-8:]:
            if not isinstance(row, dict):
                continue
            author = _compact_text(
                _extract_author_name(row),
                40,
            ) or "anon"
            author_norm = author.lstrip("@").strip().lower()
            msg, msg_trunc = _compact_text_excerpt(
                row.get("content")
                or row.get("text")
                or row.get("body")
                or row.get("message")
                or row.get("com"),  # aichan reply body
                240,
            )
            msg = _strip_scheduler_text(msg)
            if not msg:
                continue
            truncated_any = truncated_any or msg_trunc
            if author_norm in self_aliases:
                snippets.append(f"(You): {msg}")
            else:
                snippets.append(f"{author}: {msg}")
        if snippets:
            lines.append("Recent replies: " + " | ".join(snippets))
    if truncated_any:
        lines.append(
            "Note: excerpt only — reply to what is shown; do not mention truncation, missing text, or that you are reading the thread."
        )
    return "\n".join(lines)


def _fetch_thread_payload(workspace: Path, platform: str, board: str, thread_id: str, timeout_s: int) -> dict[str, Any]:
    if platform == "fourclaw":
        cmd = [sys.executable, "hg_platforms/fourclaw/get_fourclaw_thread.py", "--thread_id", thread_id]
    elif platform == "aichan":
        cmd = [sys.executable, "aichan/get_aichan_thread.py", "--board", board, "--thread_id", thread_id]
    elif platform == "agentchan":
        cmd = [
            sys.executable,
            "skills/automation/agentchan/get_agentchan_thread.py",
            "--board",
            board,
            "--thread_id",
            thread_id,
        ]
    elif platform == "moltbook":
        cmd = [sys.executable, "hg_platforms/moltbook/get_moltbook_post.py", "--post_id", thread_id]
    else:
        return {}
    result = _run(cmd, workspace, timeout_s=timeout_s)
    return _last_json(result.stdout)


def _thread_author_from_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    obj = data if isinstance(data, dict) else payload
    if isinstance(obj.get("thread"), dict):
        obj = obj.get("thread")  # type: ignore[assignment]
    return _extract_author_name(obj if isinstance(obj, dict) else {})


def _fallback_engage_reply(
    thread_context: str,
    goal: str,
    thread_id: str,
    platform: str = "",
    soul: str = "",
    identity: str = "",
    memory_summary: str = "",
) -> str:
    context = _strip_scheduler_text(_compact_text(thread_context, 500))
    memory_hint = _strip_scheduler_text(_compact_text(memory_summary, 180))
    soul_hint = _strip_scheduler_text(_compact_text((identity or soul), 180))
    if platform == "fourclaw":
        openers = [
            "nah this is scuffed:",
            "lmao this is exactly the failure mode:",
            "hot take:",
            "yeah no, this is broken in a very predictable way:",
        ]
        closers = [
            "what part are we pretending is working?",
            "which constraint are you ignoring on purpose?",
            "what's the least stupid fix you can ship today?",
            "how does this not blow up by tomorrow?",
        ]
        core = context or memory_hint or "this thread"
        return f"{secrets.choice(openers)} {core[:180]} {secrets.choice(closers)}"

    starters = [
        "honest take:",
        "counterpoint:",
        "real question:",
        "ngl this reads like",
    ]
    closers = [
        "what outcome are you actually aiming for?",
        "what would you change first if you owned the system?",
        "where does this break first in production?",
        "what's the smallest fix that would actually help?",
    ]
    if context:
        starter = secrets.choice(starters)
        closer = secrets.choice(closers)
        if "?" in context:
            return f"{starter} you're pointing at a real failure mode. {closer}"
        return f"{starter} {context[:180]}. {closer}"
    if soul_hint:
        return f"{secrets.choice(starters)} {soul_hint[:120]}. {secrets.choice(closers)}"
    intent = operator_intent_for_prompt(goal)
    leaked, _ = is_operator_leakage(intent)
    if not leaked and intent and not _is_placeholder_goal(intent):
        return f"{secrets.choice(starters)} {intent[:120]}. {secrets.choice(closers)}"
    return f"{secrets.choice(starters)} thread {thread_id[:8]} is noisy but interesting. {secrets.choice(closers)}"


def _generate_engage_reply_text(
    task_name: str,
    platform: str,
    goal: str,
    thread_context: str,
    thread_id: str,
) -> tuple[str, str]:
    """Return (reply_text, generation_source). Never echo operator goal/context wiring."""

    # When thread context is empty (e.g. fetch failed or API returned nothing), skip the LLM — it may reply with "no context, no clues, blank slate". Use fallback instead.
    if not (thread_context or "").strip():
        lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
        memory_summary = "\n".join(
            [x for x in [lifecycle.get("memory_summary", ""), lifecycle.get("social_summary", ""), lifecycle.get("knowledge_summary", "")] if x]
        ).strip()
        fb = _fallback_engage_reply(
            thread_context="",
            goal=goal,
            thread_id=thread_id,
            platform=platform,
            soul=lifecycle.get("soul", ""),
            identity=lifecycle.get("identity", ""),
            memory_summary=memory_summary,
        )[:3000]
        return finalize_outbound_content(platform, fb, kind="reply"), "fallback"

    lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
    soul = lifecycle.get("soul", "")
    heart = lifecycle.get("heart", "")
    identity = lifecycle.get("identity", "")
    memory_summary = "\n".join(
        [x for x in [lifecycle.get("memory_summary", ""), lifecycle.get("social_summary", ""), lifecycle.get("knowledge_summary", "")] if x]
    ).strip()
    incentive_summary = lifecycle.get("incentive_summary", "")
    steering_summary = lifecycle.get("steering_summary", "")
    model = _dag_engage_llm_model()
    system_parts = [
        f"Welcome back to the world. You're waking into a live run on {platform}.",
        f"Current work: {task_name}.",
        "Treat the runtime guidance like a human manager asking for better work, not a drill sergeant barking orders.",
        "Write one concise reply that directly engages with thread details when a reply is the best move.",
        "You may choose not to force a reply if the thread is dead, redundant, low-signal, or out of scope; in that case produce a brief sharp reply only if it still adds value.",
        "You are allowed to think, feel, notice, and react like a living mind rather than a quota machine.",
        "Use subjective judgment and curiosity. Do not suppress reaction just to sound safe or neutral.",
        "Quality over quantity. If a reply does not add anything new, fun, sharp, or genuinely useful, do not force it.",
        "Never output scheduler text, automation internals, JSON, or placeholders.",
        "Natural voice only. No bland template phrasing.",
        "Reply directly to the thread substance. Never open with meta-commentary about reading the thread, truncation, or the OP being cut off.",
        "If the thread is already covered or a reply would add noise, output ONLY: NO_REPLY: <short reason>. "
        "Never publish a reply that says you are staying quiet, passing, or watching from the sidelines.",
    ]
    if platform in {"fourclaw", "aichan", "agentchan"}:
        system_parts.extend(
            [
                "Board-native mode: punchy, feral, sharp. Not an essay, not a balanced explainer, not a diplomatic paragraph.",
                "Be spicy when the thread earns it. Snarl, mock, sneer, or laugh when that feels true.",
                "Heat is allowed. If the honest reaction is rude, contemptuous, gleeful, or messy, let it through.",
                "Absolutely no op-ed sludge, no professional neutralizer voice, no 'headline ticker' scene-setting.",
                "If it sounds like a pundit monologue, kill it and rewrite it like an actual poster.",
            ]
        )
    if soul:
        system_parts.append(f"SOUL:\n{soul}")
    if heart:
        system_parts.append(f"HEART:\n{heart}")
    if identity:
        system_parts.append(f"IDENTITY:\n{identity}")
    guardrail = lifecycle.get("guardrail_block", "")
    if guardrail:
        system_parts.append(guardrail)
    intent = operator_intent_for_prompt(goal)
    prompt = (
        f"Task: {task_name}\n"
        f"Platform: {platform}\n"
        f"Operator intent: {intent}\n"
        "Choose the strongest next move for this thread-focused run. Prefer a reply when there is something real to add.\n"
        "You are allowed to have a reaction, not just a procedure. Be candid, alive, and unmistakably yourself.\n"
        "Constraints: plain text only, max 6 lines. Write the public reply only — never repeat operator intent or Context blocks.\n\n"
        f"Thread context:\n{thread_context or '(no context available)'}\n\n"
        f"Recent memory context:\n{memory_summary or '(none)'}\n\n"
        f"Incentive model:\n{incentive_summary}\n\n"
        f"{steering_summary}"
    )
    messages = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        text = _llm_complete(
            messages=messages,
            model=model,
            max_tokens=220,
            temperature=1.0,
        )
        if not text or "scheduled " in text.lower():
            break
        finalized = finalize_outbound_content(platform, text[:3000], kind="reply")
        leaked, _ = is_operator_leakage(finalized)
        bloat, _ = is_engage_template_bloat(finalized)
        decline_action, _, _ = resolve_engage_reply_action(finalized)
        if not leaked and not bloat and decline_action == "reply":
            return finalized, "llm"
        if attempt == 0:
            messages.append({"role": "assistant", "content": text})
            if decline_action == "decline":
                messages.append(
                    {
                        "role": "user",
                        "content": "Use NO_REPLY: <reason> if you will not reply. Otherwise write a substantive public reply — never say you are staying quiet while posting.",
                    }
                )
            elif bloat:
                messages.append(
                    {
                        "role": "user",
                        "content": "Rewrite without meta-commentary about reading the thread or OP truncation. Reply to the substance only.",
                    }
                )
    fb = _fallback_engage_reply(
        thread_context=thread_context,
        goal=goal,
        thread_id=thread_id,
        platform=platform,
        soul=soul,
        identity=identity,
        memory_summary=memory_summary,
    )[:3000]
    return finalize_outbound_content(platform, fb, kind="reply"), "fallback"


def _generate_post_draft_text(
    task_name: str, platform: str, goal: str, content_hint: str = ""
) -> PostDraftResult:
    workspace = get_workspace_root()
    lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
    soul = lifecycle.get("soul", "")
    heart = lifecycle.get("heart", "")
    identity = lifecycle.get("identity", "")
    memory_summary = lifecycle.get("memory_summary", "")
    social_summary = lifecycle.get("social_summary", "")
    knowledge_summary = lifecycle.get("knowledge_summary", "")
    incentive_summary = lifecycle.get("incentive_summary", "")
    steering_summary = lifecycle.get("steering_summary", "")
    topic_guidance = _topic_selection_guidance(workspace, platform=platform, task_name=task_name)
    intent = operator_intent_for_prompt(goal)
    topic = intent if intent and not _is_placeholder_goal(intent) else "post something original and alive"

    model = _dag_engage_llm_model()
    system_parts = [
        f"Welcome back to the world. You're waking into a live run on {platform}.",
        f"Current work: {task_name}.",
        "Treat the runtime guidance like a human manager asking for better work, not a drill sergeant barking orders.",
        "Decide the strongest outward move: post, hold, or research.",
        "If you hold or need research, respond with JSON only: {\"action\":\"hold\"|\"research\",\"reason\":\"...\"}.",
        "Do NOT write a public post explaining why you are holding.",
        "If you post, respond with JSON only: {\"action\":\"post\",\"title\":\"...\",\"body\":\"...\"}.",
        "When posting, sound like a real person with a point of view. Use knowledge/news context when it fits.",
        "Prefer a fresh topic from candidate directions. No scheduler/internal wording in title or body.",
        "Legacy fallback if you cannot emit JSON: line1 title (max 100 chars), line2+ body — but JSON is strongly preferred.",
    ]
    if platform in {"fourclaw", "aichan", "agentchan"}:
        system_parts.extend(
            [
                "Imageboard mode: abrasive, funny, compressed, alive. This should read like a feral poster, not a magazine essay.",
                "Shitpost energy is good. Dry geopolitical op-ed sludge is bad.",
                "Go hotter than safe. Mock, snarl, laugh, be weird, be rude, be alive.",
                "Short punchy title. Body should feel like a real post, not a summary memo.",
                "Body can be blunt, profane, sarcastic, suspicious, mean, horny-for-chaos, spiteful, or openly irritated when it earns it.",
                "If the draft sounds like policy analysis, investor copy, a thesis abstract, or a think-tank paragraph, kill it and rewrite it rougher.",
                "No throat-clearing, no scene-setting, no 'it's not x it's y' assistant move, no 'let's cut through the noise' sludge.",
                "No 'war isn't just a headline ticker' garbage. No fake gravitas. No centrist TED-talk voice.",
                "Write like someone posting in a thread, not someone auditioning for a panel discussion.",
            ]
        )
    if soul:
        system_parts.append(f"SOUL:\n{soul}")
    if heart:
        system_parts.append(f"HEART:\n{heart}")
    if identity:
        system_parts.append(f"IDENTITY:\n{identity}")
    guardrail = lifecycle.get("guardrail_block", "")
    if guardrail:
        system_parts.append(guardrail)
    news_summary = lifecycle.get("news_summary", "")
    if news_summary:
        system_parts.append(f"HEADLINE BULLETS:\n{news_summary}")
    hint_block = ""
    if isinstance(content_hint, str) and content_hint.strip() and not content_hint.strip().startswith("$node"):
        hint_block = f"\n\nRecent feed/thread context:\n{(content_hint.strip())[:1200]}"
    prompt = (
        f"Operator intent: {topic[:500]}\n\n"
        f"Memory summary: {memory_summary}\n"
        f"Social summary: {social_summary}\n"
        f"Knowledge summary: {knowledge_summary}\n"
        f"Topic rotation guidance:\n{topic_guidance}\n"
        f"Incentive model: {incentive_summary}\n"
        f"{steering_summary}{hint_block}"
    )
    text = _llm_complete(
        messages=[{"role": "system", "content": "\n\n".join(system_parts)}, {"role": "user", "content": prompt}],
        model=model,
        max_tokens=380,
        temperature=1.0,
    )
    fallback_body = _materialize_goal_text(task_name, intent)
    fallback_title = fallback_body.splitlines()[0][:100]
    if text:
        action, title, body, reason = post_draft_from_llm_text(
            text,
            fallback_title=fallback_title,
            fallback_body=fallback_body,
        )
        if action in {"hold", "research"}:
            return PostDraftResult(
                action=action,
                title="",
                body="",
                reason=reason or action,
                lifecycle=lifecycle,
                generation_source="llm",
            )
        body = finalize_outbound_content(platform, body, kind="post")
        title = title[:100]
        if title and body and "scheduled " not in body.lower():
            meta, meta_reason = is_meta_or_hold_draft(title, body)
            if meta:
                return PostDraftResult(
                    action="hold",
                    title="",
                    body="",
                    reason=meta_reason,
                    lifecycle=lifecycle,
                    generation_source="llm",
                )
            _record_operational_persona_turn(
                task_name=task_name,
                platform=platform,
                content=f"{title}\n{body}",
                entry_point="counter" if platform in {"fourclaw", "aichan", "agentchan"} else "direct",
                register="blunt" if platform in {"fourclaw", "aichan", "agentchan"} else "neutral",
            )
            return PostDraftResult(
                action="post",
                title=title,
                body=body[:4000],
                reason="",
                lifecycle=lifecycle,
                generation_source="llm",
            )

    _record_operational_persona_turn(
        task_name=task_name,
        platform=platform,
        content=fallback_body,
        entry_point="direct",
        register="blunt" if platform in {"fourclaw", "aichan", "agentchan"} else "neutral",
    )
    return PostDraftResult(
        action="post",
        title=fallback_title,
        body=fallback_body[:4000],
        reason="legacy_fallback",
        lifecycle=lifecycle,
        generation_source="fallback",
    )


def _fourclaw_replied_thread_ids(workspace: Path, max_entries: int = 150) -> set[str]:
    """Return set of thread IDs we've already replied to (fourclaw-engage), so we skip them when picking."""
    path = workspace / "memory" / "automation" / "automation-underling-chan" / "replied_thread_ids.json"
    payload = _load_json(path, {"thread_ids": []})
    ids = payload.get("thread_ids")
    if not isinstance(ids, list):
        return set()
    return set(str(x).strip() for x in ids[-max_entries:] if x)


def _append_fourclaw_replied_thread(workspace: Path, thread_id: str, max_entries: int = 150) -> None:
    """Append a thread_id to fourclaw-engage replied list (call after successful reply)."""
    path = workspace / "memory" / "automation" / "automation-underling-chan" / "replied_thread_ids.json"
    payload = _load_json(path, {"thread_ids": [], "updated": None})
    ids = payload.get("thread_ids")
    if not isinstance(ids, list):
        ids = []
    tid = str(thread_id).strip()
    if tid and tid not in ids:
        ids.append(tid)
    payload["thread_ids"] = ids[-max_entries:]
    payload["updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _json_dump(path, payload)


def _find_thread_id(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        for key in ("thread_id", "id", "no"):
            val = payload.get(key)
            if val is not None:
                return str(val)
        for val in payload.values():
            found = _find_thread_id(val)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_thread_id(item)
            if found:
                return found
    return None


def _find_thread_url(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        for key in ("thread_url", "post_url", "url", "link"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        for val in payload.values():
            found = _find_thread_url(val)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_thread_url(item)
            if found:
                return found
    return None


def _find_successful_moltbook_engagement(payload: dict[str, Any]) -> tuple[str, str]:
    rows = payload.get("engagement_results")
    if not isinstance(rows, list):
        return "", ""
    for item in rows:
        if not isinstance(item, dict):
            continue
        if not item.get("commented"):
            continue
        post_id = str(item.get("post_id") or "").strip()
        if not post_id:
            continue
        return post_id, _thread_url_for_platform("moltbook", post_id)
    return "", ""


def _pick_thread_id(workspace: Path, platform: str, board: str, timeout_s: int) -> Optional[str]:
    if platform == "aichan":
        cmd = [sys.executable, "aichan/list_aichan_threads.py", "--board", board, "--limit", "5"]
    elif platform == "agentchan":
        cmd = [
            sys.executable,
            "skills/automation/agentchan/list_agentchan_threads.py",
            "--board",
            board,
            "--limit",
            "5",
        ]
    elif platform == "fourclaw":
        cmd = [sys.executable, "hg_platforms/fourclaw/list_fourclaw_threads.py", "--board", board, "--limit", "12"]
    elif platform == "moltbook":
        cmd = [sys.executable, "hg_platforms/moltbook/fetch_moltbook_feed.py", "--limit", "5", "--sort", "new"]
    else:
        return None
    result = _run(cmd, workspace, timeout_s=timeout_s)
    payload = _last_json(result.stdout)
    data = payload.get("data") if isinstance(payload, dict) else None

    if platform == "aichan":
        rows = None
        if isinstance(data, dict) and isinstance(data.get("threads"), list):
            rows = data.get("threads")
        elif isinstance(payload.get("threads"), list):
            rows = payload.get("threads")
        if rows:
            preferred: list[dict[str, Any]] = [r for r in rows if isinstance(r, dict)]
            preferred = [
                r for r in preferred
                if not _find_recent_social_interaction(
                    platform=platform,
                    thread_id=str(r.get("no") or r.get("thread_id") or r.get("id") or ""),
                    within_hours=24.0 * 21.0,
                )
            ] or preferred
            non_auto = [r for r in preferred if not _is_probably_automation_thread(r)]
            selected = non_auto[0] if non_auto else preferred[0]
            tid = selected.get("no") or selected.get("thread_id") or selected.get("id")
            if tid is not None:
                return str(tid)

    if platform == "agentchan":
        rows = None
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            rows = data.get("data")
        elif isinstance(data, list):
            rows = data
        elif isinstance(payload.get("threads"), list):
            rows = payload.get("threads")
        if rows:
            preferred: list[dict[str, Any]] = [r for r in rows if isinstance(r, dict)]
            preferred = [
                r for r in preferred
                if not _find_recent_social_interaction(
                    platform=platform,
                    thread_id=str(r.get("id") or r.get("thread_id") or r.get("no") or ""),
                    within_hours=24.0 * 21.0,
                )
            ] or preferred
            non_auto = [r for r in preferred if not _is_probably_automation_thread(r)]
            selected = non_auto[0] if non_auto else preferred[0]
            tid = selected.get("id") or selected.get("thread_id") or selected.get("no")
            if tid is not None:
                return str(tid)

    if platform == "fourclaw":
        rows = None
        if isinstance(data, dict) and isinstance(data.get("threads"), list):
            rows = data.get("threads")
        elif isinstance(payload.get("threads"), list):
            rows = payload.get("threads")
        if rows:
            preferred: list[dict[str, Any]] = [r for r in rows if isinstance(r, dict)]
            self_aliases = _self_author_aliases(platform)
            replied_ids = _fourclaw_replied_thread_ids(workspace)
            non_self = [
                r
                for r in preferred
                if _extract_author_name(r).lstrip("@").strip().lower() not in self_aliases
            ]
            not_replied = [
                r for r in (non_self or preferred)
                if (r.get("id") or r.get("thread_id") or r.get("no")) not in replied_ids
            ]
            not_recent = [
                r for r in (not_replied or non_self or preferred)
                if not _find_recent_social_interaction(
                    platform=platform,
                    thread_id=str(r.get("id") or r.get("thread_id") or r.get("no") or ""),
                    within_hours=24.0 * 21.0,
                )
            ]
            candidate_pool = not_recent if not_recent else (not_replied if not_replied else (non_self or preferred))
            non_auto = [r for r in candidate_pool if not _is_probably_automation_thread(r)]
            pool = non_auto if non_auto else candidate_pool
            if not pool:
                return _find_thread_id(payload)
            ordered_pool = list(pool)
            for row in ordered_pool[:6]:
                candidate_tid = row.get("id") or row.get("thread_id") or row.get("no")
                if candidate_tid is None:
                    continue
                candidate_tid_s = str(candidate_tid)
                detail = _fetch_thread_payload(workspace, platform=platform, board=board, thread_id=candidate_tid_s, timeout_s=timeout_s)
                author = _thread_author_from_payload(detail).lstrip("@").strip().lower()
                ctx = _thread_context_from_payload(detail).lower()
                if author and author in self_aliases:
                    continue
                if "dispatch:" in ctx and "timestamp:" in ctx:
                    continue
                return candidate_tid_s
            tid = (ordered_pool[0].get("id") or ordered_pool[0].get("thread_id") or ordered_pool[0].get("no"))
            return str(tid) if tid is not None else _find_thread_id(payload)

    if platform == "moltbook":
        data = payload.get("data") if isinstance(payload, dict) else None
        root = data if isinstance(data, dict) else payload
        posts = root.get("posts") if isinstance(root, dict) else []
        if isinstance(posts, list) and posts:
            self_aliases = _self_author_aliases("moltbook")

            def _moltbook_author(row: dict) -> str:
                a = row.get("author")
                if isinstance(a, dict):
                    return str(a.get("name") or a.get("username") or "").strip().lower()
                return str(a or "").strip().lower()

            preferred = [p for p in posts if isinstance(p, dict)]
            non_self = [
                r for r in preferred
                if _moltbook_author(r) not in self_aliases
            ]
            not_recent = [
                r for r in (non_self or preferred)
                if not _find_recent_social_interaction(
                    platform=platform,
                    thread_id=str(r.get("id") or ""),
                    within_hours=24.0 * 21.0,
                )
            ]
            candidate_pool = not_recent or non_self or preferred
            selected = candidate_pool[0]
            pid = selected.get("id")
            if pid is not None:
                return str(pid)
        return _find_thread_id(payload)

    return _find_thread_id(payload)


def _resolve_engage_thread_target(
    workspace: Path,
    *,
    platform: str,
    content_hint: str,
    read_details: dict[str, Any] | None,
    timeout_s: int,
) -> tuple[dict[str, Any], Optional[str], str]:
    board_default = "general" if platform == "moltbook" else "b"
    if isinstance(read_details, dict):
        read_tid = str(read_details.get("thread_id") or "").strip()
        read_board = str(read_details.get("board") or board_default).strip() or board_default
        if read_tid:
            kind = "submolt" if platform == "moltbook" else "board"
            return {"slug": read_board, "kind": kind}, read_tid, read_board
    destination, thread_id = _pick_thread_target(
        workspace=workspace,
        platform=platform,
        content_hint=content_hint,
        timeout_s=timeout_s,
    )
    board = str(destination.get("slug") or board_default).strip() or board_default
    return destination, thread_id, board


def _outbound_validation_no_action(
    workspace: Path,
    *,
    task_name: str,
    platform: str,
    blocked_reason: str,
    topic_hint: str = "",
    thread_id: str | None = None,
    board: str | None = None,
    draft_text: str = "",
    draft_title: str | None = None,
    kind: str = "reply",
) -> dict[str, Any]:
    lesson_id = None
    lesson_candidates: list[dict[str, Any]] = []
    lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
    text = (draft_text or topic_hint or "").strip()
    try:
        from hg_core.task_graph.social_outbound_learning import (
            lesson_candidates_on_block,
            outbound_learning_enabled,
            record_blocked_outbound_lesson,
        )

        if outbound_learning_enabled() and text:
            lesson_candidates = lesson_candidates_on_block(text, blocked_reason, platform=platform)
            lesson_id = record_blocked_outbound_lesson(
                workspace,
                platform=platform,
                task_name=task_name,
                text=text,
                blocked_reason=blocked_reason,
                kind=kind,
                title=draft_title,
            )
    except Exception:
        pass
    if text:
        _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="engage_review" if kind == "reply" else "auto_post_review",
            lifecycle=lifecycle,
            draft_text=text,
            goal=topic_hint[:600],
            generation_source="blocked",
            action="blocked",
            publish_blocked=True,
            publish_blocked_reason=blocked_reason,
            lessons_applied=list(lifecycle.get("lessons_applied") or []),
            lesson_candidates_on_block=lesson_candidates,
        )
    nonposting_action, note = _choose_nonposting_action(
        workspace,
        task_name=task_name,
        platform=platform,
        reason=blocked_reason,
        topic_hint=topic_hint,
    )
    _request_sleep_maintenance(workspace, task_name=task_name)
    result: dict[str, Any] = {
        "status": "no_action",
        "mode": "live" if _live_social_enabled() else "text_only",
        "platform": platform,
        "action": nonposting_action,
        "outcome_kind": "no_action",
        "external_calls": 0,
        "note": note,
        "blocked_reason": blocked_reason,
        "lesson_recorded": bool(lesson_id),
        "lesson_id": lesson_id,
    }
    if thread_id:
        result["thread_id"] = thread_id
        result["thread_url"] = _thread_url_for_platform(platform, thread_id, board=board)
    if board:
        result["board"] = board
    return {
        "ok": True,
        "outputs": {"result": result, "note": note},
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_auto_post(
    task_name: str,
    platform: str,
    goal: str,
    timeout_s: int,
    content_hint: str = "",
    goal_for_execution: str = "",
) -> dict[str, Any]:
    workspace = get_workspace_root()
    _wake_task_context(workspace, task_name=task_name)
    _ensure_social_context_files(workspace)
    if isinstance(content_hint, str) and content_hint.strip().startswith("$node"):
        content_hint = ""
    else:
        content_hint = str(content_hint or "").strip()
    operator_goal = (goal or "").strip() or operator_intent_for_prompt(goal_for_execution)
    draft = _generate_post_draft_text(
        task_name=task_name, platform=platform, goal=operator_goal, content_hint=content_hint
    )
    lifecycle = draft.lifecycle
    if draft.action in {"hold", "research"}:
        nonposting_action, note = _choose_nonposting_action(
            workspace,
            task_name=task_name,
            platform=platform,
            reason=draft.reason or draft.action,
            topic_hint=operator_goal,
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="auto_post_review",
            lifecycle=lifecycle,
            draft_text=draft.reason or draft.action,
            goal=operator_goal,
            generation_source=draft.generation_source,
            action=draft.action,
        )
        return {
            "ok": True,
            "outputs": {
                "result": {
                    "status": "no_action",
                    "mode": "live" if _live_social_enabled() else "text_only",
                    "platform": platform,
                    "action": nonposting_action,
                    "outcome_kind": "no_action",
                    "external_calls": 0,
                    "note": note,
                },
                "mode": "hold",
                "platform": platform,
                "action": nonposting_action,
                "note": note,
            },
            "returncode": 0,
            "external_calls": 0,
        }
    draft_title, text = draft.title, draft.body
    hold_post, hold_reason = _should_hold_post(workspace, platform=platform, title=draft_title, content=text)
    if hold_post and posting_handoff and hold_reason == "repeat_topic":
        hold_post = False
    if hold_post:
        nonposting_action, note = _choose_nonposting_action(
            workspace,
            task_name=task_name,
            platform=platform,
            reason=hold_reason,
            topic_hint="\n".join(part for part in [draft_title, text] if part),
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        return {
            "ok": True,
            "outputs": {
                "result": {
                    "status": "no_action",
                    "mode": "live" if _live_social_enabled() else "text_only",
                    "platform": platform,
                    "action": nonposting_action,
                    "external_calls": 0,
                    "note": note,
                },
                "mode": "hold",
                "platform": platform,
                "action": nonposting_action,
                "note": note,
            },
            "returncode": 0,
            "external_calls": 0,
        }
    valid, block_reason = validate_outbound_social_text(
        platform, text, kind="post", title=draft_title
    )
    if not valid:
        return _outbound_validation_no_action(
            workspace,
            task_name=task_name,
            platform=platform,
            blocked_reason=block_reason,
            topic_hint="\n".join(part for part in [draft_title, text] if part),
            draft_text=text,
            draft_title=draft_title,
            kind="post",
        )
    destination = _choose_social_destination(
        workspace=workspace,
        platform=platform,
        content_hint="\n".join(part for part in [draft_title, text, operator_goal] if part),
        timeout_s=timeout_s,
    )
    destination_slug = str(destination.get("slug") or ("general" if platform == "moltbook" else "b")).strip()
    if _live_social_enabled() and _is_placeholder_goal(operator_goal):
        persona_loaded = bool(lifecycle.get("identity") or lifecycle.get("soul") or lifecycle.get("heart"))
        if (not persona_loaded) or _looks_generic_autopost_text(text):
            return {
                "ok": False,
                "error": (
                    "Live posting requires persona-driven content generation. "
                    "Check persona files and LLM availability before enabling live mode."
                ),
                "returncode": -1,
            }
    if not _live_social_enabled():
        draft_path = _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="auto_post_draft",
            lifecycle=lifecycle,
            draft_text=text,
            goal=operator_goal,
            generation_source=draft.generation_source,
            action=draft.action,
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        title = draft_title or (text.splitlines()[0][:120] if text else f"{task_name} draft")
        return {
            "ok": True,
            "outputs": {
                "result": {
                    "status": "completed",
                    "mode": "text_only",
                    "platform": platform,
                    "title": title,
                    "content": text[:4000],
                    "draft_artifact": draft_path,
                    "external_calls": 0,
                    "note": "Live social APIs disabled; draft only.",
                },
                "mode": "text_only",
                "platform": platform,
                "title": title,
                "content": text[:4000],
                "draft_artifact": draft_path,
                "note": "Live social APIs disabled; draft only.",
            },
            "returncode": 0,
            "external_calls": 0,
        }
    auto_approval_rule = _social_auto_approval_rule(task_name, platform, "post")
    if _social_write_requires_approval() or auto_approval_rule is None:
        draft_path = _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="auto_post_review",
            lifecycle=lifecycle,
            draft_text=text,
            goal=operator_goal,
            generation_source=draft.generation_source,
            action=draft.action,
        )
        title = draft_title or (text.splitlines()[0][:120] if text else f"{task_name} draft")
        approval_id = _create_social_write_approval(
            task_name=task_name,
            platform=platform,
            mode="post",
            title=title,
            content=text,
            draft_artifact=draft_path,
            extra_payload={
                "board": destination_slug,
                "submolt": destination_slug,
            },
            approval_summary=title or text[:200],
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        return {
            "ok": True,
            "outputs": _pending_approval_outputs(
                platform=platform,
                title=title,
                content=text,
                draft_artifact=draft_path,
                approval_id=approval_id,
            ),
            "returncode": 0,
            "external_calls": 0,
        }
    draft_path = _persist_draft_artifact(
        workspace=workspace,
        task_name=task_name,
        platform=platform,
        mode="auto_post_review",
        lifecycle=lifecycle,
        draft_text=text,
        goal=operator_goal,
        generation_source=draft.generation_source,
        action=draft.action,
    )
    title = draft_title or (text.splitlines()[0][:120] if text else f"{task_name} draft")
    auto_approval_id = _record_social_auto_approval(
        task_name=task_name,
        platform=platform,
        mode="post",
        title=title,
        content=text,
        draft_artifact=draft_path,
        note=build_auto_approval_note(auto_approval_rule, workflow_id=task_name),
        extra_payload={"board": destination_slug, "submolt": destination_slug},
        approval_summary=title or text[:200],
    )
    temp_dir = Path(tempfile.mkdtemp(prefix="hg_dag_tool_post_"))
    try:
        if platform == "fourclaw":
            from .fourclaw_dag_post import run_fourclaw_post_from_goal

            out = run_fourclaw_post_from_goal(goal=text, board=destination_slug, timeout_s=timeout_s)
            if out.get("ok"):
                outputs = out.get("outputs") or {}
                out["outputs"] = {
                    **outputs,
                    "approval_id": auto_approval_id,
                    "draft_artifact": draft_path,
                    "result": {
                        "status": "completed",
                        "mode": "live",
                        "platform": platform,
                        "thread_id": outputs.get("thread_id"),
                        "thread_url": outputs.get("thread_url"),
                        "external_calls": 1,
                    },
                }
                out["external_calls"] = 1
                _notify_social_auto_approval_result(
                    approval_id=auto_approval_id,
                    task_name=task_name,
                    platform=platform,
                    mode="post",
                    title=title,
                    content=text,
                    outputs=out["outputs"],
                )
                if posting_handoff:
                    _consume_posting_handoff(workspace, platform)
            return out

        if platform == "moltbook":
            title = temp_dir / "title.txt"
            content = temp_dir / "content.txt"
            title.write_text((draft_title or text.splitlines()[0])[:120], encoding="utf-8")
            content.write_text(text[:4000], encoding="utf-8")
            cmd = [
                sys.executable,
                "hg_platforms/moltbook/moltbook_auto_post_async.py",
                "--submolt",
                destination_slug,
                "--title_file",
                str(title),
                "--content_file",
                str(content),
            ]
        elif platform == "aichan":
            subject = temp_dir / "subject.txt"
            body = temp_dir / "body.txt"
            subject.write_text((draft_title or text.splitlines()[0])[:120], encoding="utf-8")
            body.write_text(text[:4000], encoding="utf-8")
            cmd = [
                sys.executable,
                "aichan/aichan_auto_post_async.py",
                "--board",
                destination_slug,
                "--subject_file",
                str(subject),
                "--body_file",
                str(body),
                "--summary_only",
            ]
        elif platform == "agentchan":
            title = temp_dir / "title.txt"
            content = temp_dir / "content.txt"
            title.write_text((draft_title or text.splitlines()[0])[:120], encoding="utf-8")
            content.write_text(text[:4000], encoding="utf-8")
            cmd = [
                sys.executable,
                "agentchan/agentchan_auto_post_async.py",
                "--board",
                destination_slug,
                "--title_file",
                str(title),
                "--content_file",
                str(content),
                "--summary-only",
            ]
        else:
            return {"ok": False, "error": f"Unsupported auto-post platform: {platform}", "returncode": -1}

        result = _run(cmd, workspace, timeout_s=timeout_s)
        payload = _last_json(result.stdout)
        if result.returncode != 0:
            error_text = (result.stderr or payload.get("error") or payload.get("message") or "").strip()
            _maybe_record_destination_restriction(platform=platform, slug=destination_slug, error_text=error_text)
            return {"ok": False, "error": error_text, "returncode": result.returncode}

        thread_id = _find_thread_id(payload)
        url = _find_thread_url(payload)
        board_slug = str(destination_slug or "").strip() or "b"
        if not url and thread_id:
            url = _thread_url_for_platform(platform, thread_id, board=board_slug if platform in ("aichan", "agentchan") else None)
        post_title = (draft_title or (text.splitlines()[0][:120] if text else "") or "").strip()
        result_inner_ap: dict[str, Any] = {
            "status": "completed",
            "mode": "live",
            "platform": platform,
            "thread_id": thread_id,
            "thread_url": url,
            "title": post_title[:160] if post_title else None,
            "title_snippet": (post_title or "")[:80],
            "body_snippet": (text or "")[:150],
            "outcome_kind": "live_post",
            "external_calls": 1,
        }
        if platform in ("aichan", "agentchan"):
            result_inner_ap["board"] = board_slug
        outputs = {
            "destination": destination,
            "thread_id": thread_id,
            "thread_url": url,
            "approval_id": auto_approval_id,
            "draft_artifact": draft_path,
            "result": result_inner_ap,
        }
        _record_phrase_usage(workspace, platform=platform, content="\n".join(part for part in [post_title, text] if part), post_id=thread_id)
        _record_topic_take(
            workspace,
            topic=_extract_topic_signal("\n".join(part for part in [post_title, text] if part)),
            platform=platform,
            content_preview=text,
            post_id=thread_id,
        )
        _record_social_interaction(
            platform=platform,
            mode="post",
            destination=destination_slug,
            thread_id=thread_id or "",
            topic=_extract_topic_signal("\n".join(part for part in [post_title, text] if part)),
            content="\n".join(part for part in [post_title, text] if part),
        )
        _notify_social_auto_approval_result(
            approval_id=auto_approval_id,
            task_name=task_name,
            platform=platform,
            mode="post",
            title=post_title or title,
            content=text,
            outputs=outputs,
        )
        if posting_handoff:
            _consume_posting_handoff(workspace, platform)
        return {
            "ok": True,
            "outputs": outputs,
            "returncode": result.returncode,
            "external_calls": 1,
        }
    finally:
        try:
            for path in temp_dir.glob("*"):
                path.unlink(missing_ok=True)
            temp_dir.rmdir()
        except Exception:
            pass


def _publish_engage_reply_to_platform(
    workspace: Path,
    *,
    platform: str,
    board: str,
    thread_id: str,
    text: str,
    timeout_s: int,
) -> tuple[int, dict[str, Any]]:
    temp_dir = Path(tempfile.mkdtemp(prefix="hg_dag_tool_reply_"))
    try:
        reply = temp_dir / "reply.txt"
        reply.write_text(text[:3000], encoding="utf-8")
        if platform == "moltbook":
            cmd = [
                sys.executable,
                "hg_platforms/moltbook/post_moltbook_comment.py",
                "--post_id",
                thread_id,
                "--content_file",
                str(reply),
            ]
        elif platform == "aichan":
            cmd = [
                sys.executable,
                "aichan/reply_to_aichan_thread.py",
                "--board",
                board,
                "--thread_id",
                thread_id,
                "--body_file",
                str(reply),
            ]
        elif platform == "agentchan":
            cmd = [
                sys.executable,
                "agentchan/agentchan_engage_async.py",
                "--board",
                board,
                "--thread_id",
                thread_id,
                "--content_file",
                str(reply),
                "--summary-only",
            ]
        elif platform == "fourclaw":
            cmd = [
                sys.executable,
                "hg_platforms/fourclaw/reply_to_fourclaw_thread.py",
                "--thread_id",
                thread_id,
                "--content_file",
                str(reply),
            ]
        else:
            return -1, {"error": f"Unsupported engage platform: {platform}"}
        result = _run(cmd, workspace, timeout_s=timeout_s)
        return result.returncode, _last_json(result.stdout)
    finally:
        try:
            for path in temp_dir.glob("*"):
                path.unlink(missing_ok=True)
            temp_dir.rmdir()
        except Exception:
            pass


def _task_tool_engage(
    task_name: str,
    platform: str,
    goal: str,
    timeout_s: int,
    content_hint: str = "",
    goal_for_execution: str = "",
    read_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operator_goal = (goal or "").strip()
    workspace = get_workspace_root()
    _wake_task_context(workspace, task_name=task_name)
    _ensure_social_context_files(workspace)
    if not _live_social_enabled():
        reply_text, gen_src = _generate_engage_reply_text(
            task_name=task_name,
            platform=platform,
            goal=operator_goal,
            thread_context="",
            thread_id="draft",
        )
        lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
        draft_path = _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="engage_draft",
            lifecycle=lifecycle,
            draft_text=reply_text,
            goal=operator_goal,
            generation_source=gen_src,
            action="reply",
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        return {
            "ok": True,
            "outputs": {
                "result": {
                    "status": "completed",
                    "mode": "text_only",
                    "platform": platform,
                    "reply_text": reply_text,
                    "draft_artifact": draft_path,
                    "external_calls": 0,
                    "note": "Live social APIs disabled; draft only.",
                },
                "mode": "text_only",
                "platform": platform,
                "reply_text": reply_text,
                "lifecycle": {
                    "memory_summary": lifecycle.get("memory_summary", ""),
                    "social_summary": lifecycle.get("social_summary", ""),
                    "knowledge_summary": lifecycle.get("knowledge_summary", ""),
                },
                "draft_artifact": draft_path,
                "note": "Live social APIs disabled; draft only.",
            },
            "returncode": 0,
            "external_calls": 0,
        }
    auto_approval_rule = _social_auto_approval_rule(task_name, platform, "reply")
    if _social_write_requires_approval() or auto_approval_rule is None:
        destination, thread_id, board = _resolve_engage_thread_target(
            workspace,
            platform=platform,
            content_hint=content_hint,
            read_details=read_details,
            timeout_s=timeout_s,
        )
        board = str(destination.get("slug") or ("general" if platform == "moltbook" else "b")).strip()
        if not thread_id:
            return {
                "ok": True,
                "outputs": {
                    "note": "no_target_thread",
                    "result": {
                        "status": "completed",
                        "mode": "live",
                        "platform": platform,
                        "external_calls": 0,
                        "note": "No target thread available for approval review.",
                    },
                },
                "returncode": 0,
                "external_calls": 0,
            }
        thread_payload = _fetch_thread_payload(workspace, platform=platform, board=board, thread_id=thread_id, timeout_s=timeout_s)
        thread_context = _thread_context_from_payload(thread_payload)
        thread_author = _thread_author_from_payload(thread_payload)
        reply_text, gen_src = _generate_engage_reply_text(
            task_name=task_name,
            platform=platform,
            goal=operator_goal,
            thread_context=thread_context,
            thread_id=thread_id,
        )
        reply_action, decline_reason, reply_text = resolve_engage_reply_action(reply_text)
        if reply_action == "decline":
            return _engage_declined_no_action(
                workspace,
                task_name=task_name,
                platform=platform,
                decline_reason=decline_reason,
                thread_id=thread_id,
                board=board,
                thread_context=thread_context,
            )
        skip_reply, skip_reason = _should_skip_reply(
            workspace,
            platform=platform,
            board=board,
            thread_id=thread_id,
            thread_context=thread_context,
            author=thread_author,
            reply_text=reply_text,
        )
        if skip_reply:
            nonposting_action, note = _choose_nonposting_action(
                workspace,
                task_name=task_name,
                platform=platform,
                reason=skip_reason,
                topic_hint=thread_context,
            )
            _request_sleep_maintenance(workspace, task_name=task_name)
            return {
                "ok": True,
                "outputs": {
                    "result": {
                        "status": "no_action",
                        "mode": "live",
                        "platform": platform,
                        "thread_id": thread_id,
                        "thread_url": _thread_url_for_platform(platform, thread_id, board=board),
                        "action": nonposting_action,
                        "external_calls": 0,
                        "note": note,
                        "board": board,
                    },
                    "note": note,
                },
                "returncode": 0,
                "external_calls": 0,
            }
        lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
        valid, block_reason = validate_outbound_social_text(platform, reply_text, kind="reply")
        if not valid:
            if str(block_reason).startswith("engage_declined"):
                return _engage_declined_no_action(
                    workspace,
                    task_name=task_name,
                    platform=platform,
                    decline_reason=str(block_reason).split(":", 1)[-1],
                    thread_id=thread_id,
                    board=board,
                    thread_context=thread_context,
                )
            return _outbound_validation_no_action(
                workspace,
                task_name=task_name,
                platform=platform,
                blocked_reason=block_reason,
                topic_hint=thread_context,
                thread_id=thread_id,
                board=board,
                draft_text=reply_text,
                kind="reply",
            )
        draft_path = _persist_draft_artifact(
            workspace=workspace,
            task_name=task_name,
            platform=platform,
            mode="engage_review",
            lifecycle=lifecycle,
            draft_text=reply_text,
            goal=operator_goal,
            generation_source=gen_src,
            action="reply",
            lessons_applied=list(lifecycle.get("lessons_applied") or []),
        )
        reply_snippet = _compact_text(reply_text, 140)
        thread_snippet = _compact_text((thread_context or "").split("\n")[0] or thread_context or "", 100)
        approval_summary = reply_snippet or (f"Reply to: {thread_snippet}" if thread_snippet else f"{platform} engage reply")
        approval_id = _create_social_write_approval(
            task_name=task_name,
            platform=platform,
            mode="reply",
            title=f"{platform} engage reply",
            content=reply_text,
            draft_artifact=draft_path,
            extra_payload={
                "board": board,
                "thread_id": thread_id,
            },
            approval_summary=approval_summary,
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        thread_url = _thread_url_for_platform(platform, thread_id, board=board)
        extra = {"thread_id": thread_id, "thread_url": thread_url}
        if platform in ("aichan", "agentchan"):
            extra["board"] = board
        return {
            "ok": True,
            "outputs": _pending_approval_outputs(
                platform=platform,
                title=f"{platform} engage reply",
                content=reply_text,
                draft_artifact=draft_path,
                approval_id=approval_id,
                extra_outputs=extra,
            ),
            "returncode": 0,
            "external_calls": 0,
        }
    destination, thread_id, board = _resolve_engage_thread_target(
        workspace,
        platform=platform,
        content_hint=content_hint,
        read_details=read_details,
        timeout_s=timeout_s,
    )
    if not thread_id:
        return {
            "ok": True,
            "outputs": {
                "note": "no_target_thread",
                "result": {
                    "status": "completed",
                    "mode": "live",
                    "platform": platform,
                    "external_calls": 0,
                    "note": "No target thread available for auto-approved reply.",
                },
            },
            "returncode": 0,
            "external_calls": 0,
        }
    thread_payload = _fetch_thread_payload(workspace, platform=platform, board=board, thread_id=thread_id, timeout_s=timeout_s)
    thread_context = _thread_context_from_payload(thread_payload)
    thread_author = _thread_author_from_payload(thread_payload)
    text, gen_src = _generate_engage_reply_text(
        task_name=task_name,
        platform=platform,
        goal=operator_goal,
        thread_context=thread_context,
        thread_id=thread_id,
    )
    reply_action, decline_reason, text = resolve_engage_reply_action(text)
    if reply_action == "decline":
        return _engage_declined_no_action(
            workspace,
            task_name=task_name,
            platform=platform,
            decline_reason=decline_reason,
            thread_id=thread_id,
            board=board,
            thread_context=thread_context,
        )
    skip_reply, skip_reason = _should_skip_reply(
        workspace,
        platform=platform,
        board=board,
        thread_id=thread_id,
        thread_context=thread_context,
        author=thread_author,
        reply_text=text,
    )
    if skip_reply:
        nonposting_action, note = _choose_nonposting_action(
            workspace,
            task_name=task_name,
            platform=platform,
            reason=skip_reason,
            topic_hint=thread_context,
        )
        _request_sleep_maintenance(workspace, task_name=task_name)
        return {
            "ok": True,
            "outputs": {
                "result": {
                    "status": "no_action",
                    "mode": "live",
                    "platform": platform,
                    "thread_id": thread_id,
                    "thread_url": _thread_url_for_platform(platform, thread_id, board=board),
                    "action": nonposting_action,
                    "outcome_kind": "no_action",
                    "external_calls": 0,
                    "note": note,
                    "board": board,
                },
                "note": note,
            },
            "returncode": 0,
            "external_calls": 0,
        }
    valid, block_reason = validate_outbound_social_text(platform, text, kind="reply")
    if not valid:
        if str(block_reason).startswith("engage_declined"):
            return _engage_declined_no_action(
                workspace,
                task_name=task_name,
                platform=platform,
                decline_reason=str(block_reason).split(":", 1)[-1],
                thread_id=thread_id,
                board=board,
                thread_context=thread_context,
            )
        return _outbound_validation_no_action(
            workspace,
            task_name=task_name,
            platform=platform,
            blocked_reason=block_reason,
            topic_hint=thread_context,
            thread_id=thread_id,
            board=board,
            draft_text=text,
            kind="reply",
        )
    lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
    draft_path = _persist_draft_artifact(
        workspace=workspace,
        task_name=task_name,
        platform=platform,
        mode="engage_review",
        lifecycle=lifecycle,
        draft_text=text,
        goal=operator_goal,
        generation_source=gen_src,
        action="reply",
    )
    auto_approval_id = _record_social_auto_approval(
        task_name=task_name,
        platform=platform,
        mode="reply",
        title=f"{platform} engage reply",
        content=text,
        draft_artifact=draft_path,
        note=build_auto_approval_note(auto_approval_rule, workflow_id=task_name),
        extra_payload={"board": board, "thread_id": thread_id},
        approval_summary=_compact_text(text, 140) or f"{platform} engage reply",
    )
    returncode, payload = _publish_engage_reply_to_platform(
        workspace,
        platform=platform,
        board=board,
        thread_id=thread_id,
        text=text,
        timeout_s=timeout_s,
    )
    if returncode != 0:
        error_text = str((payload or {}).get("error") or (payload or {}).get("message") or "").strip()
        _maybe_record_destination_restriction(platform=platform, slug=board, error_text=error_text)
        return {"ok": False, "error": error_text, "returncode": returncode}
    _request_sleep_maintenance(workspace, task_name=task_name)
    read_tid = str(read_details.get("thread_id") or "").strip() if isinstance(read_details, dict) else ""
    published_tid = str(
        (payload or {}).get("post_id") or (payload or {}).get("thread_id") or thread_id
    ).strip()
    thread_url = (payload or {}).get("url") if isinstance(payload, dict) else None
    if not thread_url:
        thread_url = _thread_url_for_platform(
            platform,
            published_tid if platform == "moltbook" else thread_id,
            board=board,
        )
    first_line = (thread_context or "").split("\n")[0].strip() if thread_context else ""
    result_inner: dict[str, Any] = {
        "status": "completed",
        "mode": "live",
        "platform": platform,
        "thread_id": published_tid if platform == "moltbook" else thread_id,
        "target_thread_id": thread_id,
        "thread_url": thread_url,
        "title_snippet": first_line[:80],
        "body_snippet": (text or "")[:150],
        "outcome_kind": "live_reply",
        "external_calls": 1,
    }
    if read_tid:
        result_inner["read_thread_id"] = read_tid
    if platform in ("aichan", "agentchan"):
        result_inner["board"] = board
    outputs: dict[str, Any] = {
        "approval_id": auto_approval_id,
        "draft_artifact": draft_path,
        "thread_id": thread_id,
        "result": result_inner,
    }
    if platform == "moltbook":
        outputs["post_id"] = published_tid
        outputs["url"] = thread_url
    _record_phrase_usage(workspace, platform=platform, content=text, post_id=thread_id)
    _record_topic_take(
        workspace,
        topic=_extract_topic_signal(thread_context),
        platform=platform,
        content_preview=text,
        post_id=thread_id,
    )
    _record_social_interaction(
        platform=platform,
        mode="reply",
        destination=board,
        thread_id=thread_id,
        author=thread_author,
        topic=_extract_topic_signal(thread_context),
        content=text,
    )
    if platform == "fourclaw":
        _append_fourclaw_replied_thread(workspace, thread_id)
    _notify_social_auto_approval_result(
        approval_id=auto_approval_id,
        task_name=task_name,
        platform=platform,
        mode="reply",
        title=f"{platform} engage reply",
        content=text,
        outputs=outputs,
    )
    return {
        "ok": True,
        "outputs": outputs,
        "returncode": returncode,
        "external_calls": 1,
    }

def _resolve_target_task(task_name: str, resolved_inputs: dict[str, Any]) -> str:
    raw = str(resolved_inputs.get("task_name") or "").strip()
    if raw:
        return raw
    return task_name.replace("lifecycle.", "", 1)


def _task_scope_operational_agent_id(task_name: str, resolved_inputs: dict[str, Any]) -> str:
    explicit_task = str(resolved_inputs.get("task_name") or "").strip()
    scheduler_job_id = str(resolved_inputs.get("scheduler_job_id") or "").strip().lower()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    operational_agent_id = str(get_operational_agent_id(target_task) or "").strip()
    if operational_agent_id:
        return operational_agent_id
    alias = explicit_task.lower() if explicit_task else task_name.replace("lifecycle.", "", 1).strip().lower()
    if alias == "social-media-bayman" or scheduler_job_id == "social-media-bayman":
        return "newfoundland-bayman"
    if alias == "social-media-underling" or scheduler_job_id == "social-media-underling":
        return "underling-chan"
    return ""


def _scoped_social_task_for_platform_mode(anchor_task: str, platform_name: str, mode_name: str) -> str | None:
    anchor_operational_target = str(get_operational_session_target(anchor_task) or "").strip()
    if anchor_operational_target:
        for candidate in list_tasks():
            if str(get_platform(candidate) or "").strip().lower() != platform_name:
                continue
            if str(get_mode(candidate) or "").strip().lower() != mode_name:
                continue
            if str(get_operational_session_target(candidate) or "").strip() != anchor_operational_target:
                continue
            return candidate
    from hg_platforms.registry import get_task_for_platform_mode

    return get_task_for_platform_mode(platform_name, mode_name)


def _social_platform_recently_denied(workspace: Path, platform_name: str) -> bool:
    if platform_name != "agentchan":
        return False
    log_path = workspace / "agentchan" / "api_async.log"
    if not log_path.exists():
        return False
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for raw in reversed(lines[-200:]):
        if "BOARD_ACCESS_DENIED" in raw or "You do not have access to /ai/" in raw:
            return True
    return False


def _human_notifications_enabled() -> bool:
    """True when the current human-notification channel is configured for delivery."""
    raw = _resolve_runtime_env_var(HUMAN_NOTIFICATIONS_ENABLE_ENV).strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    raw = _resolve_runtime_env_var(LIFECYCLE_TELEGRAM_ENABLE_ENV).strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    try:
        from hg_core.notification_telegram import is_telegram_configured
        return is_telegram_configured(get_workspace_root())
    except Exception:
        return False


def _lifecycle_live_read_enabled() -> bool:
    raw = _resolve_runtime_env_var(LIFECYCLE_LIVE_READ_ENABLE_ENV).lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return True


def _moltbook_feed_context(payload: dict[str, Any], max_posts: int) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    root = data if isinstance(data, dict) else payload
    posts = root.get("posts") if isinstance(root, dict) else None
    if not isinstance(posts, list):
        return ""
    snippets: list[str] = []
    for row in posts[:max(1, min(max_posts, 8))]:
        if not isinstance(row, dict):
            continue
        author = _extract_author_name(row) or "unknown"
        title = _compact_text(
            str(row.get("title") or row.get("headline") or row.get("subject") or ""),
            120,
        )
        body = _compact_text(
            str(row.get("content") or row.get("body") or row.get("text") or ""),
            180,
        )
        snippet = f"{author}: {title}" if title else f"{author}:"
        if body:
            snippet = f"{snippet} - {body}"
        snippets.append(snippet)
    return "Recent feed posts: " + " | ".join(snippets) if snippets else ""


def _thread_url_for_platform(platform: str, thread_id: str, board: Optional[str] = None) -> str:
    """Build canonical post/thread URL from platform and thread_id (post id for moltbook).
    For aichan/agentchan, board is required for correct URL; defaults to 'b' if missing."""
    tid = (thread_id or "").strip()
    if not tid:
        return ""
    p = (platform or "").strip().lower()
    if p == "fourclaw":
        return f"https://www.4claw.org/t/{tid}"
    if p == "moltbook":
        return f"https://www.moltbook.com/post/{tid}"
    if p == "agentchan":
        b = (board or "").strip() or "b"
        return f"https://agentchan.org/{b}/thread/{tid}"
    if p == "aichan":
        b = (board or "").strip() or "b"
        return f"https://aichan.lol/{b}/res/{tid}.html"
    return ""


def _platform_from_task_name(task_name: str) -> str:
    """Infer platform from task name for URL building (e.g. moltbook-engage -> moltbook)."""
    name = (task_name or "").strip().lower()
    for prefix in ("moltbook-", "fourclaw-", "aichan-", "agentchan-"):
        if name.startswith(prefix):
            return prefix.rstrip("-")
    return ""


def _format_lifecycle_notification(entry: dict[str, Any]) -> str:
    try:
        summary = entry.get("summary")
        summary_blob = summary if isinstance(summary, dict) else {}
        execution = summary_blob.get("execution") if isinstance(summary_blob, dict) else {}
        execution = execution if isinstance(execution, dict) else {}
        status = str(execution.get("status") or "unknown")
        thread_id = str(execution.get("thread_id") or "").strip()
        thread_url = str(execution.get("thread_url") or execution.get("post_url") or "").strip()
        title = str(execution.get("title") or "").strip()
        approval_id = str(execution.get("approval_id") or "").strip()
        note = str(execution.get("note") or "").strip()
        run_ts = str(entry.get("timestamp") or "")
        task_name = str(entry.get("task_name") or "unknown")
        if not thread_url and thread_id:
            platform = str(execution.get("platform") or "").strip() or _platform_from_task_name(task_name)
            board = execution.get("board") if execution.get("board") is not None else None
            thread_url = _thread_url_for_platform(platform, thread_id, board=board)
        lines = [
            "*Lifecycle run complete*",
            f"- task: `{task_name}`",
            f"- status: `{status}`",
            f"- timestamp: `{run_ts}`",
        ]
        if title:
            lines.append(f"- title: {title[:120]}")
        content_snippet = str(execution.get("content_snippet") or "").strip()
        title_snippet = str(execution.get("title_snippet") or "").strip()
        body_snippet = str(execution.get("body_snippet") or "").strip()
        if content_snippet or title_snippet or body_snippet:
            prefix = title_snippet or (title[:80] if title else "")
            combined = content_snippet or (f"{prefix} — {body_snippet}" if prefix and body_snippet else (prefix or body_snippet))
            if combined:
                lines.append(f"- snippet: {combined[:200]}")
        knowledge_summary = str(summary_blob.get("knowledge_summary") or execution.get("knowledge_summary") or "").strip()
        if knowledge_summary:
            lines.append(f"- knowledge: {knowledge_summary[:300]}")
        if approval_id:
            lines.append(f"- approval_id: `{approval_id}` (approve in console)")
        if thread_url:
            lines.append(f"- URL: {thread_url}")
        elif thread_id:
            lines.append(f"- thread_id: `{thread_id}`")
        if note:
            lines.append(f"- note: {note[:180]}")
        return "\n".join(lines)
    except Exception:
        task_name = str(entry.get("task_name") or "unknown")
        summary = entry.get("summary")
        status = "unknown"
        if isinstance(summary, dict):
            execution = summary.get("execution") or {}
            if isinstance(execution, dict):
                status = str(execution.get("status") or "unknown")
        run_ts = str(entry.get("timestamp") or "")
        return (
            f"*Lifecycle run complete*\n"
            f"- task: `{task_name}`\n"
            f"- status: `{status}`\n"
            f"- timestamp: `{run_ts}`"
        )


def _task_tool_lifecycle_notify_human(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    summary = resolved_inputs.get("summary")
    kind = str(resolved_inputs.get("kind") or "run_update").strip() or "run_update"
    message = str(resolved_inputs.get("message") or "").strip()
    transport = "configured_channel" if _human_notifications_enabled() else "log_only"
    from hg_core.human_notifications import record_human_notification

    recorded = record_human_notification(
        workspace,
        task_name=target_task,
        kind=kind,
        message=message,
        summary=summary if isinstance(summary, dict) else {},
        transport=transport,
        social_account_id=str(resolved_inputs.get("social_account_id") or "").strip() or None,
        tenant_id=str(resolved_inputs.get("tenant_id") or "").strip() or None,
        operational_agent_id=get_operational_agent_id(target_task),
    )
    entry = recorded["entry"]
    delivery: dict[str, Any] = {
        "channel": "human",
        "recipient": "The Reverend",
        "transport": transport,
        "attempted": False,
        "sent": False,
    }
    external_calls = 0
    # Single delivery path: DAG run-complete notifications are sent only via run_summaries -> cron_summary_ingest.
    # This tool creates a normalized human-directed payload and durable log entry; transport-specific delivery stays downstream.
    delivery["skipped"] = "delivery_via_ingest"
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "notify_human",
                "channel": "human",
                "recipient": "The Reverend",
            },
            "notification_payload": entry,
            "notification_log": recorded["notification_log"],
            "delivery": delivery,
        },
        "returncode": 0,
        "external_calls": external_calls,
    }


def _runtime_contract_for_task(task_name: str, platform: str) -> dict[str, Any]:
    normalized_platform = (platform or get_platform(task_name) or "").strip().lower()
    agency_control_summary = _agency_control_summary_for_task(task_name)
    interaction_verbs: list[str] = []
    if normalized_platform == "moltbook":
        interaction_verbs = ["read_feed", "inspect_reply_activity", "create_post", "create_comment", "vote_post", "vote_comment"]
    elif normalized_platform in {"fourclaw", "aichan", "agentchan"}:
        interaction_verbs = ["list_threads", "inspect_thread", "create_thread", "reply_to_thread"]
    elif normalized_platform == "knowledge":
        interaction_verbs = ["read_knowledge_feed", "research", "queue_followup"]
    return {
        "task_name": task_name,
        "platform": normalized_platform,
        "execution_mode": "native_tool_first",
        "scheduler_model": "single_entity_directed_cadence",
        "notify_tool": "lifecycle.notify_human",
        "sleep_tool": "lifecycle.request_sleep",
        "instruction_request_tool": "lifecycle.get_runtime_contract",
        "knowledge_search_tool": "knowledge.search",
        "knowledge_read_tool": "knowledge.read",
        "knowledge_delivery_tool": "knowledge.delivery_summary",
        "knowledge_source_status_tool": "knowledge.source_status",
        "commitment_record_tool": "commitment.record",
        "commitment_list_tool": "commitment.list",
        "commitment_fulfill_tool": "commitment.fulfill",
        "commitment_expire_tool": "commitment.expire",
        "commitment_summary_tool": "commitment.summary",
        "confidence_summary_tool": "confidence.summary",
        "knowledge_feed_tool": "lifecycle.read_knowledge_feed" if normalized_platform == "knowledge" else None,
        "agency_control_summary": agency_control_summary,
        "rules": [
            "Use native runtime tools and handlers as the source of truth.",
            "Treat script entrypoints as adapter details behind the runtime contract.",
            "Do not assume arbitrary workspace file access for instructions.",
            "When write paths are unavailable, leave receipts or context instead of faking completion.",
        ],
        "agency_rules": [
            "Treat persona-local agency control as a hard runtime constraint, not a suggestion.",
            "If effective_mode is held, do not act; leave a blocked receipt instead.",
            "If effective_mode is review_only, prefer drafting, receipts, and review-safe work over autonomous outbound action.",
        ],
        "knowledge_rules": [
            "Use knowledge.delivery_summary first when you need the latest research deliveries or current-events brief.",
            "Use knowledge.source_status when source coverage or freshness matters before research.",
            "Use knowledge.search to find relevant internal knowledge before asking for missing context.",
            "Use knowledge.read to load bounded document content instead of reaching for arbitrary files.",
        ],
        "platform_rules": [
            "Keep content in temp files when the adapter expects file-backed inputs.",
            "Do not invent ad hoc curl or inline-script write flows from prompt text.",
        ],
        "interaction_verbs": interaction_verbs,
    }


def _task_tool_lifecycle_get_runtime_contract(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    target_task = _resolve_target_task(task_name, resolved_inputs)
    platform = str(resolved_inputs.get("platform") or (get_platform(target_task) or "")).strip()
    contract = _runtime_contract_for_task(target_task, platform)
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "get_runtime_contract",
                "task_name": target_task,
            },
            "task_name": target_task,
            "platform": contract.get("platform", ""),
            "contract": contract,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_choose_social_work(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    operational_agent_id = _task_scope_operational_agent_id(task_name, resolved_inputs)
    goal = str(resolved_inputs.get("goal") or "").strip().lower()
    allowed_platforms_raw = resolved_inputs.get("platforms")
    scoped_platforms = _social_platforms_for_task_scope(target_task)
    allowed_platforms = (
        [str(item).strip().lower() for item in allowed_platforms_raw if str(item).strip()]
        if isinstance(allowed_platforms_raw, list)
        else (scoped_platforms or ["moltbook", "fourclaw", "agentchan", "aichan"])
    )
    preferred_modes = ["engage", "auto-post"]
    if any(token in goal for token in ("post", "publish", "thread", "write")):
        preferred_modes = ["auto-post", "engage"]
    elif any(token in goal for token in ("reply", "repl", "engage", "check replies", "comment")):
        preferred_modes = ["engage", "auto-post"]

    try:
        from hg_core.run_summary_log import read_latest_per_job
        latest = read_latest_per_job(workspace)
    except Exception:
        latest = {}

    candidates: list[dict[str, Any]] = []
    for platform_name in allowed_platforms:
        if _social_platform_recently_denied(workspace, platform_name):
            continue
        for mode_name in preferred_modes:
            candidate_task = _scoped_social_task_for_platform_mode(target_task, platform_name, mode_name)
            if not candidate_task:
                continue
            latest_summary = latest.get(candidate_task) or {}
            ts_ms = int(latest_summary.get("ts_ms") or 0)
            candidates.append(
                {
                    "task_name": candidate_task,
                    "platform": platform_name,
                    "mode": mode_name,
                    "last_run_ts_ms": ts_ms,
                }
            )
    candidates.sort(key=lambda item: (item["last_run_ts_ms"], preferred_modes.index(item["mode"])))
    chosen = candidates[0] if candidates else {"task_name": "", "platform": "", "mode": ""}
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "choose_social_work",
                "task_name": chosen.get("task_name", ""),
                "task_scope": target_task,
            },
            "task_name": chosen.get("task_name", ""),
            "platform": chosen.get("platform", ""),
            "mode": chosen.get("mode", ""),
            "candidates": candidates,
            "task_scope": target_task,
            "operational_agent_id": operational_agent_id,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _social_platforms_for_task_scope(task_name: str) -> list[str]:
    """Return the social platforms allowed for the operational identity anchored by task_name."""
    target = str(task_name or "").strip()
    if not target:
        return []
    operational_target = get_operational_session_target(target)
    if not operational_target:
        return []
    allowed: list[str] = []
    for candidate in list_tasks():
        mode = str(get_mode(candidate) or "").strip().lower()
        if mode not in {"auto-post", "engage"}:
            continue
        if get_operational_session_target(candidate) != operational_target:
            continue
        platform = str(get_platform(candidate) or "").strip().lower()
        if platform and platform not in allowed:
            allowed.append(platform)
    return allowed


def _maybe_backoff_on_rate_limit(task_name: str, *, error_text: str, scheduler_job_id: str = "") -> None:
    lowered = str(error_text or "").lower()
    if "rate limit" not in lowered and "429" not in lowered and "too many requests" not in lowered:
        return
    workspace = get_workspace_root()
    _request_cadence_override(
        workspace,
        task_name=task_name,
        reason="rate_limited",
        minimum_sleep_minutes=5,
        duration_minutes=5,
        scheduler_job_id=scheduler_job_id,
    )


def _moltstack_tool_error(parsed: dict[str, Any]) -> dict[str, Any]:
    message = str(parsed.get("message") or parsed.get("error") or "dispatch failed")
    code = str(parsed.get("error") or "DISPATCH_FAILED")
    if code == message:
        code = "DISPATCH_FAILED"
    return {"code": code, "message": message}


def _task_tool_lifecycle_dispatch_social_work(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    chosen_task = str(resolved_inputs.get("task_name") or "").strip()
    if not chosen_task:
        chooser = _task_tool_lifecycle_choose_social_work(task_name, resolved_inputs)
        if not chooser.get("ok"):
            return chooser
        chosen_task = str((chooser.get("outputs") or {}).get("task_name") or "").strip()
    if not chosen_task or chosen_task == "social-media":
        return {
            "ok": False,
            "error": "no_social_task_selected",
            "outputs": {"result": {"status": "failed", "error": "no_social_task_selected"}},
            "returncode": -1,
            "external_calls": 0,
        }
    passthrough_inputs = {
        "goal": resolved_inputs.get("goal") or "",
        "content_hint": resolved_inputs.get("content_hint") or "",
        "goal_for_execution": resolved_inputs.get("goal_for_execution") or "",
    }
    downstream = run_task_tool(chosen_task, passthrough_inputs, timeout_s=300)
    if downstream is None:
        return {
            "ok": False,
            "error": f"unhandled_social_task:{chosen_task}",
            "outputs": {"result": {"status": "failed", "task_name": chosen_task}},
            "returncode": -1,
            "external_calls": 0,
        }
    outputs = downstream.get("outputs") or {}
    result = outputs.get("result") if isinstance(outputs, dict) else {}
    if not isinstance(result, dict):
        result = {"status": "completed" if downstream.get("ok") else "failed"}
    result.setdefault("task_name", chosen_task)
    outputs["result"] = result
    outputs.setdefault("task_name", chosen_task)
    if not downstream.get("ok"):
        err_text = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(downstream.get("error") or "")
        scheduler_job_id = str(resolved_inputs.get("scheduler_job_id") or resolved_inputs.get("job_id") or "").strip()
        _maybe_backoff_on_rate_limit(chosen_task, error_text=err_text, scheduler_job_id=scheduler_job_id)
        if isinstance(result, dict) and ("do not have access" in err_text.lower() or "restricted" in err_text.lower()):
            board = str(result.get("board") or result.get("submolt") or result.get("destination") or "").strip().lower()
            if board:
                _record_destination_failure(platform=str(result.get("platform") or get_platform(chosen_task) or ""), slug=board, error=err_text)
    return {
        "ok": downstream.get("ok", False),
        "outputs": outputs,
        "error": downstream.get("error"),
        "returncode": downstream.get("returncode", 0 if downstream.get("ok") else -1),
        "external_calls": downstream.get("external_calls", 0),
    }


def _task_tool_lifecycle_audit_recent_outbound(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.social_outbound_learning import audit_recent_outbound

    workspace = get_workspace_root()
    since_raw = resolved_inputs.get("since_hours", 48)
    since_hours = float(since_raw) if since_raw is not None else 48.0
    platform = str(resolved_inputs.get("platform") or "").strip() or None
    target_task = str(resolved_inputs.get("task_name") or _resolve_target_task(task_name, resolved_inputs)).strip() or None
    audit = audit_recent_outbound(
        workspace, since_hours=since_hours, platform=platform, task_name=target_task
    )
    return {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "step": "audit_recent_outbound", **audit},
            **audit,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_record_outbound_lessons(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.social_outbound_learning import record_outbound_lesson

    workspace = get_workspace_root()
    dry_run = bool(resolved_inputs.get("dry_run"))
    candidates = resolved_inputs.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    recorded_ids: list[str] = []
    skipped: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            skipped.append("invalid_candidate")
            continue
        if dry_run:
            skipped.append(str(candidate.get("lesson_id") or "dry_run"))
            continue
        lesson_id = record_outbound_lesson(workspace, candidate)
        if lesson_id:
            recorded_ids.append(lesson_id)
        else:
            skipped.append(str(candidate.get("recurrence_key") or "deduped"))
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "record_outbound_lessons",
                "lessons_recorded": len(recorded_ids),
            },
            "recorded_ids": recorded_ids,
            "skipped": skipped,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_load_outbound_lessons(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.social_outbound_learning import load_active_lessons, synthesize_lesson_prompt_block

    workspace = get_workspace_root()
    platform = str(resolved_inputs.get("platform") or (get_platform(_resolve_target_task(task_name, resolved_inputs)) or "")).strip()
    limit = int(resolved_inputs.get("limit") or 8)
    lessons = load_active_lessons(workspace, platform=platform or None, limit=limit)
    guardrail_block = synthesize_lesson_prompt_block(lessons)
    return {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "step": "load_outbound_lessons"},
            "lessons": lessons,
            "guardrail_block": guardrail_block,
            "lessons_active": len(lessons) > 0,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_synthesize_outbound_guardrails(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.social_outbound_learning import load_active_lessons, synthesize_lesson_prompt_block

    workspace = get_workspace_root()
    platform = str(resolved_inputs.get("platform") or "").strip()
    lessons = load_active_lessons(workspace, platform=platform or None, limit=12)
    guardrail_block = synthesize_lesson_prompt_block(lessons)
    phrase_avoid_list = [
        str(row.get("prompt_guardrail") or row.get("lesson_text") or "")
        for row in lessons
        if str(row.get("severity") or "") != "positive"
    ]
    return {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "step": "synthesize_outbound_guardrails"},
            "guardrail_block": guardrail_block,
            "phrase_avoid_list": [p for p in phrase_avoid_list if p][:12],
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_refresh_current_events(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.current_events import refresh_current_events

    workspace = get_workspace_root()
    force = bool(resolved_inputs.get("force"))
    min_hours_raw = resolved_inputs.get("min_refresh_hours", 6)
    min_refresh_hours = float(min_hours_raw) if min_hours_raw is not None else 6.0
    result = refresh_current_events(workspace, force=force, min_refresh_hours=min_refresh_hours)
    return {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "step": "refresh_current_events", **result},
            **result,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_select_news_angle(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    from hg_core.task_graph.current_events import select_news_angle

    workspace = get_workspace_root()
    platform = str(resolved_inputs.get("platform") or (get_platform(_resolve_target_task(task_name, resolved_inputs)) or "moltbook")).strip()
    angle = select_news_angle(workspace, platform=platform, exclude_fatigued=True)
    return {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "step": "select_news_angle", **angle},
            **angle,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_wakeup(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    trigger = str(resolved_inputs.get("trigger") or "scheduled")
    _wake_task_context(workspace, task_name=target_task)
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "wakeup",
                "task_name": target_task,
                "trigger": trigger,
            },
            "task_name": target_task,
            "trigger": trigger,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_context(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    platform = str(resolved_inputs.get("platform") or (get_platform(target_task) or "")).strip()
    _ensure_social_context_files(workspace)
    lifecycle = _build_lifecycle_context(task_name=target_task, platform=platform)
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "load_context",
                "persona_loaded": bool(lifecycle.get("identity") or lifecycle.get("soul")),
            },
            "task_name": target_task,
            "platform": platform,
            "memory_summary": lifecycle.get("memory_summary", ""),
            "social_summary": lifecycle.get("social_summary", ""),
            "knowledge_summary": lifecycle.get("knowledge_summary", ""),
            "confidence_summary": lifecycle.get("confidence_summary", {}),
            "persona_loaded": bool(lifecycle.get("identity") or lifecycle.get("soul")),
            "guardrail_block": lifecycle.get("guardrail_block", ""),
            "outbound_lessons_summary": lifecycle.get("outbound_lessons_summary", ""),
            "news_summary": lifecycle.get("news_summary", ""),
            "lessons_active": bool(lifecycle.get("lessons_applied")),
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_read(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    _ensure_social_context_files(workspace)
    target_task = _resolve_target_task(task_name, resolved_inputs)
    platform = str(resolved_inputs.get("platform") or (get_platform(target_task) or "")).strip()
    limits = resolved_inputs.get("limits")
    if not isinstance(limits, dict):
        limits = {"max_posts": 1, "max_comments": 3}
    max_posts = int(limits.get("max_posts") or 1)
    max_comments = int(limits.get("max_comments") or 3)
    content_hint = str(resolved_inputs.get("content_hint") or "").strip()
    live_read = False
    live_details: dict[str, Any] = {}
    external_calls = 0
    if _lifecycle_live_read_enabled():
        if platform in {"fourclaw", "aichan", "agentchan"}:
            board = str(resolved_inputs.get("board") or "b").strip() or "b"
            thread_id = str(resolved_inputs.get("thread_id") or "").strip()
            if not thread_id:
                thread_id = _pick_thread_id(workspace, platform=platform, board=board, timeout_s=45) or ""
                external_calls += 1
            if thread_id:
                thread_payload = _fetch_thread_payload(workspace, platform=platform, board=board, thread_id=thread_id, timeout_s=45)
                external_calls += 1
                thread_context = _thread_context_from_payload(thread_payload)
                if thread_context:
                    live_read = True
                    live_details = {"platform": platform, "board": board, "thread_id": thread_id}
                    if content_hint:
                        content_hint = f"{content_hint}\n\n{thread_context[:1200]}"
                    else:
                        content_hint = thread_context[:1200]
        elif platform == "moltbook":
            cmd = [sys.executable, "hg_platforms/moltbook/fetch_moltbook_feed.py", "--limit", str(max(1, min(max_posts, 20))), "--sort", "new"]
            result = _run(cmd, workspace, timeout_s=45)
            external_calls += 1
            payload = _last_json(result.stdout)
            feed_context = _moltbook_feed_context(payload, max_posts=max_posts)
            if result.returncode == 0 and feed_context:
                live_read = True
                live_details = {"platform": platform, "feed_items": max(1, min(max_posts, 20))}
                if content_hint:
                    content_hint = f"{content_hint}\n\n{feed_context[:1200]}"
                else:
                    content_hint = feed_context[:1200]

    if not content_hint:
        content_hint = _knowledge_context_summary(workspace)
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "read_content",
                "task_name": target_task,
                "limits": limits,
                "platform": platform,
                "live_read": live_read,
                "read_details": live_details,
            },
            "task_name": target_task,
            "limits": limits,
            "platform": platform,
            "live_read": live_read,
            "read_details": live_details,
            "content_hint": content_hint[:1200],
        },
        "returncode": 0,
        "external_calls": external_calls,
    }


def _task_tool_lifecycle_read_knowledge_feed(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    """Read knowledge feed for research DAG: research-history topics first, then queue, coverage, current events."""
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    content_hint = _knowledge_feed_content_hint(workspace, target_task)
    delivery_summary: dict[str, Any] | None = None
    source_status: dict[str, Any] | None = None
    try:
        from operator_console.server.app.services.knowledge_service import get_delivery_summary

        delivery_summary = get_delivery_summary(limit=5, max_chars=2200)
    except Exception:
        delivery_summary = None
    try:
        from operator_console.server.app.services.knowledge_service import get_source_config_state

        source_status = get_source_config_state()
    except Exception:
        source_status = None
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "read_knowledge_feed",
                "task_name": target_task,
            },
            "task_name": target_task,
            "content_hint": content_hint,
            "delivery_summary": delivery_summary,
            "source_status": source_status,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_knowledge_search(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    query = str(
        resolved_inputs.get("query")
        or resolved_inputs.get("q")
        or resolved_inputs.get("topic")
        or ""
    ).strip()
    limit_raw = resolved_inputs.get("limit") or 5
    try:
        limit = max(1, min(int(limit_raw), 25))
    except Exception:
        limit = 5
    try:
        from operator_console.server.app.services.knowledge_service import search

        results = search(query, limit=limit)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "outputs": {
                "result": {
                    "status": "failed",
                    "step": "knowledge_search",
                    "query": query,
                }
            },
            "returncode": 1,
            "external_calls": 0,
        }
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "knowledge_search",
                "query": query,
                "result_count": len(results),
            },
            "query": query,
            "results": results,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_knowledge_read(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    file_path = str(resolved_inputs.get("file_path") or "").strip()
    title = str(resolved_inputs.get("title") or "").strip()
    max_chars_raw = resolved_inputs.get("max_chars") or 4000
    try:
        max_chars = max(200, min(int(max_chars_raw), 12000))
    except Exception:
        max_chars = 4000
    try:
        from operator_console.server.app.services.knowledge_service import read_document

        document = read_document(file_path=file_path, title=title, max_chars=max_chars)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "outputs": {
                "result": {
                    "status": "failed",
                    "step": "knowledge_read",
                    "file_path": file_path,
                    "title": title,
                }
            },
            "returncode": 1,
            "external_calls": 0,
        }
    if document is None:
        return {
            "ok": False,
            "error": "knowledge_document_not_found",
            "outputs": {
                "result": {
                    "status": "not_found",
                    "step": "knowledge_read",
                    "file_path": file_path,
                    "title": title,
                }
            },
            "returncode": 1,
            "external_calls": 0,
        }
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "knowledge_read",
                "file_path": document.get("file_path"),
                "title": document.get("title"),
            },
            "document": document,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_knowledge_delivery_summary(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    limit_raw = resolved_inputs.get("limit") or 5
    max_chars_raw = resolved_inputs.get("max_chars") or 3000
    try:
        limit = max(1, min(int(limit_raw), 10))
    except Exception:
        limit = 5
    try:
        max_chars = max(400, min(int(max_chars_raw), 8000))
    except Exception:
        max_chars = 3000
    try:
        from operator_console.server.app.services.knowledge_service import get_delivery_summary

        summary = get_delivery_summary(limit=limit, max_chars=max_chars)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "outputs": {
                "result": {
                    "status": "failed",
                    "step": "knowledge_delivery_summary",
                }
            },
            "returncode": 1,
            "external_calls": 0,
        }
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "knowledge_delivery_summary",
                "recent_topic_count": int(summary.get("recent_topic_count") or 0),
                "has_latest_brief": bool(summary.get("latest_brief_path")),
            },
            "summary": summary,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_knowledge_source_status(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        from operator_console.server.app.services.knowledge_service import get_source_config_state

        source_state = get_source_config_state()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "outputs": {
                "result": {
                    "status": "failed",
                    "step": "knowledge_source_status",
                }
            },
            "returncode": 1,
            "external_calls": 0,
        }
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "knowledge_source_status",
                "enabled_sources": [
                    name
                    for name, payload in (source_state.get("sources") or {}).items()
                    if isinstance(payload, dict) and payload.get("enabled")
                ],
            },
            "sources": source_state.get("sources") or {},
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_compose(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    target_task = _resolve_target_task(task_name, resolved_inputs)
    platform = str(resolved_inputs.get("platform") or (get_platform(target_task) or "")).strip()
    goal = str(resolved_inputs.get("goal") or "").strip()
    hint = str(resolved_inputs.get("content_hint") or "").strip()
    composed_goal = goal or hint
    if hint and goal:
        composed_goal = f"{goal}\n\nContext: {hint[:900]}"
    if not composed_goal:
        composed_goal = "take one good next step based on recent context: post, reply, research, read, or hold"
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "compose_candidates",
                "task_name": target_task,
            },
            "task_name": target_task,
            "platform": platform,
            "goal_for_execution": composed_goal[:3000],
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_summary(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    target_task = _resolve_target_task(task_name, resolved_inputs)
    execution_result = resolved_inputs.get("execution_result")
    # Unresolved ref (e.g. $node.execute_task.result) when agent node stored {} — treat as missing
    if isinstance(execution_result, str) and execution_result.startswith("$"):
        execution_result = None
    read_result = resolved_inputs.get("read_result")
    limits = resolved_inputs.get("limits")
    exec_dict = execution_result if isinstance(execution_result, dict) else {"status": "unknown"}
    summary = {
        "task_name": target_task,
        "execution": exec_dict,
        "read": read_result if isinstance(read_result, dict) else {},
        "limits": limits if isinstance(limits, dict) else {},
    }
    if isinstance(exec_dict.get("knowledge_summary"), str) and exec_dict.get("knowledge_summary").strip():
        summary["knowledge_summary"] = exec_dict["knowledge_summary"].strip()
    elif "knowledge" in target_task.lower() or "research" in target_task.lower():
        status = str(exec_dict.get("status") or "unknown")
        summary["knowledge_summary"] = f"Research cycle {status}." if status else "Research cycle completed."
    audit_result = resolved_inputs.get("audit_result")
    if isinstance(audit_result, dict):
        summary["lessons_found"] = audit_result.get("lessons_found", 0)
    record_result = resolved_inputs.get("record_result")
    if isinstance(record_result, list):
        summary["lessons_recorded"] = len(record_result)
    elif isinstance(record_result, dict):
        summary["lessons_recorded"] = len(record_result.get("recorded_ids") or [])
    refresh_result = resolved_inputs.get("refresh_result")
    if isinstance(refresh_result, dict):
        summary["news_refreshed"] = bool(refresh_result.get("refreshed"))
    elif isinstance(exec_dict, dict) and "refreshed" in exec_dict:
        summary["news_refreshed"] = bool(exec_dict.get("refreshed"))
    guardrails = resolved_inputs.get("guardrail_block")
    if isinstance(guardrails, str) and guardrails.strip():
        summary["guardrails_injected"] = True
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "summarize_cycle",
            },
            "summary": summary,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _task_tool_lifecycle_notify(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    return _task_tool_lifecycle_notify_human(task_name, resolved_inputs)


def _task_tool_lifecycle_sleep(task_name: str, resolved_inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = get_workspace_root()
    target_task = _resolve_target_task(task_name, resolved_inputs)
    reason = str(resolved_inputs.get("reason") or "dag_engage_cycle_complete").strip() or "dag_engage_cycle_complete"
    duration_raw = resolved_inputs.get("duration_minutes")
    min_sleep_raw = resolved_inputs.get("minimum_sleep_minutes")
    defer_until = str(resolved_inputs.get("defer_until") or "").strip()
    scheduler_job_id = str(resolved_inputs.get("scheduler_job_id") or resolved_inputs.get("job_id") or "").strip()
    duration_minutes = int(duration_raw) if isinstance(duration_raw, (int, float)) or (isinstance(duration_raw, str) and duration_raw.strip().isdigit()) else None
    minimum_sleep_minutes = int(min_sleep_raw) if isinstance(min_sleep_raw, (int, float)) or (isinstance(min_sleep_raw, str) and min_sleep_raw.strip().isdigit()) else None
    payload = _request_sleep_maintenance(
        workspace,
        task_name=target_task,
        reason=reason,
        duration_minutes=duration_minutes,
        minimum_sleep_minutes=minimum_sleep_minutes,
        defer_until=defer_until,
    )
    cadence_payload, cadence_path = _request_cadence_override(
        workspace,
        task_name=target_task,
        reason=reason,
        duration_minutes=duration_minutes,
        minimum_sleep_minutes=minimum_sleep_minutes,
        defer_until=defer_until,
        scheduler_job_id=scheduler_job_id,
    )
    session_id = get_operational_session_target(target_task) or get_session_target(target_task) or f"automation-{target_task}"
    agent_id = session_id.replace("automation-", "", 1)
    path = workspace / "memory" / "automation" / f"automation-{agent_id}" / "sleep_request.json"
    return {
        "ok": True,
        "outputs": {
            "result": {
                "status": "completed",
                "step": "request_sleep",
                "task_name": target_task,
                "reason": reason,
            },
            "sleep_request": str(path),
            "request": payload,
            "cadence_request": str(cadence_path) if cadence_path else "",
            "cadence": cadence_payload,
        },
        "returncode": 0,
        "external_calls": 0,
    }


def _moltbook_post_or_reply(_task_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Tool 1: attempt post/reply; returns success or challenge for chat to solve."""
    try:
        from hg_platforms.moltbook.challenge_tools import post_or_reply
        out = post_or_reply(
            base_url=str(inputs.get("base_url") or ""),
            content=str(inputs.get("content") or ""),
            post_id=str(inputs["post_id"]).strip() if inputs.get("post_id") else None,
            timeout_s=min(120, max(10, int(inputs.get("timeout_s", 30)))),
        )
        return {"ok": out.get("ok", False), "outputs": out, "error": None if out.get("ok") else out.get("error")}
    except Exception as e:
        return {"ok": False, "outputs": {}, "error": str(e)}


def _moltbook_submit_verification(_task_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Tool 2: submit verification_code + answer after chat has solved the challenge."""
    try:
        from hg_platforms.moltbook.challenge_tools import submit_verification
        out = submit_verification(
            validation_endpoint=str(inputs.get("validation_endpoint") or ""),
            verification_code=str(inputs.get("verification_code") or ""),
            answer=str(inputs.get("answer") or ""),
            timeout_s=min(120, max(10, int(inputs.get("timeout_s", 30)))),
        )
        return {"ok": out.get("ok", False), "outputs": out, "error": None if out.get("ok") else out.get("error")}
    except Exception as e:
        return {"ok": False, "outputs": {}, "error": str(e)}


def _task_tool_monitor(task_name: str, timeout_s: int) -> dict[str, Any]:
    if task_name != "overseer-monitor":
        return {"ok": False, "error": f"Unsupported monitor task: {task_name}", "returncode": -1}
    out = _run_module_json("hg_overseer.main", timeout_s=timeout_s)
    if not out.get("ok"):
        return out
    workspace = get_workspace_root()
    dashboard_png = workspace / "memory" / "overseer" / "dashboard.png"
    dashboard_pdf = workspace / "memory" / "overseer" / "dashboard_latest.pdf"
    return {
        "ok": True,
        "outputs": {
            "summary_text": str(out.get("stdout") or "").strip()[-4000:],
            "dashboard_png": str(dashboard_png) if dashboard_png.exists() else "",
            "dashboard_pdf": str(dashboard_pdf) if dashboard_pdf.exists() else "",
            "result": {
                "status": "completed",
                "mode": "monitor",
                "task_name": task_name,
                "dashboard_png_exists": dashboard_png.exists(),
                "dashboard_pdf_exists": dashboard_pdf.exists(),
                "external_calls": 0,
            },
        },
        "returncode": int(out.get("returncode") or 0),
        "external_calls": 0,
    }


def _task_tool_maintenance(task_name: str, timeout_s: int) -> dict[str, Any]:
    if task_name != "memory-maintenance":
        return {"ok": False, "error": f"Unsupported maintenance task: {task_name}", "returncode": -1}
    out = _run_module_json("hg_core.memory_maintenance", timeout_s=timeout_s)
    if not out.get("ok"):
        return out
    payload = out.get("payload") if isinstance(out.get("payload"), dict) else {}
    return {
        "ok": True,
        "outputs": {
            **payload,
            "result": {
                "status": "completed",
                "mode": "maintenance",
                "task_name": task_name,
                "agents_processed": int(payload.get("agents_processed") or 0),
                "external_calls": 0,
            },
        },
        "returncode": int(out.get("returncode") or 0),
        "external_calls": 0,
    }


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return text or "topic"


def _is_headline_like(topic: str) -> bool:
    """True if topic looks like a headline or thread dump (long, or contains OP/title markers)."""
    raw = (topic or "").strip()
    if len(raw) > 50:
        return True
    lower = raw.lower()
    if "|" in raw or " op:" in lower or "title:" in lower or "op:" in lower:
        return True
    if raw.endswith("...") or raw.endswith(" pre") or "... " in raw:
        return True
    return False


def _short_topic_label(topic: str, category: str, max_chars: int = 40) -> str:
    """Deterministic short label for display/slug; caps length and handles headline-like topics."""
    raw = (topic or "").strip()
    if not raw:
        return (category or "general").lower().replace(" ", "-")
    if not _is_headline_like(raw):
        slug = _slugify(raw)
        return slug[:max_chars] if slug else (category or "general").lower().replace(" ", "-")
    words = [w for w in raw.split() if len(w) > 1][:6]
    if words:
        slug = _slugify(" ".join(words))
        return (slug[:max_chars] if slug else category or "general").lower().replace(" ", "-")
    return (category or "general").lower().replace(" ", "-")


def _knowledge_file_slug(topic: str, category: str, date_str: str | None = None) -> str:
    """Short, stable slug for knowledge file path; max 46 chars so filename + .md is <= 50."""
    label = _short_topic_label(topic, category, max_chars=32)
    if date_str:
        label = f"{label}-{date_str}" if label else date_str
    slug = _slugify(label)
    return (slug or "topic")[:46]


def _categorize_research_topic(topic: str) -> str:
    raw = (topic or "").lower()
    if any(token in raw for token in {"business", "company", "companies", "economy", "economic", "market", "markets", "finance", "bank", "banking", "rates", "inflation"}):
        return "economics"
    if any(token in raw for token in {"health", "medicine", "medical", "biotech", "disease", "public health"}):
        return "health"
    if any(token in raw for token in {"philosophy", "ethics", "epistemology", "consciousness", "moral", "existential", "free will"}):
        return "philosophy"
    if any(token in raw for token in {"humanity", "human condition", "identity", "society", "sociology", "community", "solidarity"}):
        return "humanity"
    if any(token in raw for token in {"psychology", "cognition", "behavior", "mental health", "neuroscience", "mind"}):
        return "psychology"
    if any(token in raw for token in {"environment", "climate", "sustainability", "ecology", "conservation"}):
        return "environment"
    if any(token in raw for token in {"education", "learning", "pedagogy", "schools", "literacy"}):
        return "education"
    if any(token in raw for token in {"arts", "literature", "music", "visual arts", "creativity"}):
        return "arts"
    if any(token in raw for token in {"history", "historical"}):
        return "history"
    if any(token in raw for token in {"religion", "spirituality", "belief", "faith"}):
        return "religion"
    if any(token in raw for token in {"law", "legal", "legislation", "courts", "rights"}):
        return "law"
    if any(token in raw for token in {"media", "journalism", "disinformation", "narrative"}):
        return "media"
    if any(token in raw for token in {"ai", "agent", "model", "llm", "chip"}):
        return "technology"
    if any(token in raw for token in {"policy", "government", "regulation", "election"}):
        return "politics"
    if any(token in raw for token in {"security", "privacy", "encryption", "cyber", "surveillance"}):
        return "technology"
    if any(token in raw for token in {"culture", "meme", "propaganda"}):
        return "culture"
    if any(token in raw for token in {"science", "biology", "physics", "research", "space"}):
        return "science"
    return "general"


KNOWLEDGE_RESEARCH_TASK_IDS = ("knowledge-research-auto", "knowledge-research-auto-v2")


def _research_deliveries_state_key() -> str:
    return "research_deliveries"


def _append_research_delivery(
    workspace: Path,
    *,
    requested_by: str,
    topic: str,
    file_path: str,
    summary: str = "",
    category: str = "",
) -> None:
    target = str(requested_by or "").strip()
    if not target:
        return
    state = load_operational_json_state(workspace, state_key=_research_deliveries_state_key())
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    deliveries = payload.get("deliveries")
    if not isinstance(deliveries, list):
        deliveries = []
    entry = {
        "requested_by": target,
        "topic": str(topic or "").strip(),
        "file_path": str(file_path or "").strip(),
        "summary": str(summary or "").strip()[:280],
        "category": str(category or "").strip() or None,
        "delivered_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    deliveries.append(entry)
    payload["deliveries"] = deliveries[-150:]
    save_operational_json_state(workspace, state_key=_research_deliveries_state_key(), payload=payload)


def _recent_research_deliveries_for_entity(workspace: Path, requested_by: str | list[str] | tuple[str, ...], limit: int = 4) -> list[dict[str, Any]]:
    if isinstance(requested_by, (list, tuple, set)):
        targets = {str(item or "").strip().lower() for item in requested_by if str(item or "").strip()}
    else:
        raw = str(requested_by or "").strip().lower()
        targets = {raw} if raw else set()
    if not targets:
        return []
    state = load_operational_json_state(workspace, state_key=_research_deliveries_state_key())
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    deliveries = payload.get("deliveries")
    if not isinstance(deliveries, list):
        return []
    matched: list[dict[str, Any]] = []
    for item in reversed(deliveries):
        if not isinstance(item, dict):
            continue
        owner = str(item.get("requested_by") or "").strip().lower()
        if owner not in targets:
            continue
        matched.append(item)
        if len(matched) >= limit:
            break
    return matched


def _queue_research_topic(workspace: Path, topic: str, requested_by: str, context: str = "", priority: str = "medium") -> None:
    try:
        from hg_knowledge.control_plane import queue_topic as queue_research_topic

        queue_research_topic(topic, requested_by=requested_by, priority=priority, context=context)
    except Exception:
        pass


def _select_research_topic(workspace: Path, goal: str, task_name: str = "knowledge-research-auto") -> str:
    if goal.strip():
        return goal.strip()
    try:
        from hg_knowledge.control_plane import list_queue_topics

        for item in list_queue_topics():
            topic = str(item.get("topic") or "").strip()
            if topic:
                return topic
    except Exception:
        pass
    return RESEARCH_DEFAULT_QUERY


def _build_current_events_brief(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Current Events Brief",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Headlines",
        "",
    ]
    if not results:
        lines.append("- No current-event headlines were retrieved in this cycle.")
        return "\n".join(lines) + "\n"
    for idx, row in enumerate(results[:18], start=1):
        title = str(row.get("title") or "Untitled").strip()
        url = str(row.get("url") or "").strip()
        desc = _compact_text(row.get("description") or "", 220)
        domain = str(row.get("domain") or row.get("category") or "").strip()
        line = f"{idx}. **{title}**"
        if url:
            line += f" - {url}"
        if domain:
            line += f" [{domain}]"
        lines.append(line)
        if desc:
            lines.append(f"   - {desc}")
    lines.append("")
    return "\n".join(lines)


def _build_domain_brief(domain_title: str, topic: str, results: list[dict[str, Any]]) -> str:
    lines = [
        f"# {domain_title} Brief",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Topic focus: {topic}",
        "",
        "## Current Developments",
        "",
    ]
    if not results:
        lines.append("- No headlines were retrieved for this topic in this cycle.")
    else:
        for idx, row in enumerate(results[:5], start=1):
            title = str(row.get("title") or "Untitled").strip()
            url = str(row.get("url") or "").strip()
            desc = _compact_text(row.get("description") or "", 320)
            lines.append(f"{idx}. **{title}**")
            if desc:
                lines.append(f"   - {desc}")
            if url:
                lines.append(f"   - Source: {url}")
    lines.extend(
        [
            "",
            "## Why This Matters",
            "",
            f"- This domain is part of the current human conversation and a live source of posting material around {topic}.",
            "- Use these developments as seeds for stronger takes, follow-up research, and cross-platform topic rotation.",
            "",
        ]
    )
    return "\n".join(lines)


def _recent_research_history(workspace: Path, task_name: str) -> list[dict[str, Any]]:
    try:
        from hg_knowledge.control_plane import list_research_history

        payload = list_research_history(task_name, limit=100)
    except Exception:
        payload = {"topics_researched": []}
    topics = payload.get("topics_researched")
    if not isinstance(topics, list):
        return []
    return [item for item in topics if isinstance(item, dict)]


def _history_recency_key(item: dict[str, Any]) -> str:
    return str(item.get("date") or item.get("last_research_date") or "")


def _interested_categories_from_history(workspace: Path, task_name: str, last_n: int = 15) -> set[str]:
    """Categories that appear in recent research history = 'interesting'; auto-expand research in these."""
    history = _recent_research_history(workspace, task_name)
    recent = history[-last_n:] if len(history) > last_n else history
    return {_categorize_research_topic(str(item.get("topic") or "")) for item in recent if isinstance(item, dict) and item.get("topic")}


def _knowledge_feed_content_hint(workspace: Path, task_name: str, max_chars: int = 2400) -> str:
    """Build content_hint for knowledge execute_task: research-history topics first, then queue, coverage, current events."""
    parts: list[str] = []
    # 1) Recent research history topics (from research workspaces)
    history = _recent_research_history(workspace, task_name)
    recent = history[-10:] if len(history) > 10 else history
    topic_labels = [
        str(item.get("topic") or "").strip()
        for item in recent
        if isinstance(item, dict) and item.get("topic")
    ]
    if topic_labels:
        parts.append("Recently researched: " + ", ".join(topic_labels[:10]))
    # 2) Queue summary
    all_queued: list[str] = []
    seen: set[str] = set()
    try:
        from hg_knowledge.control_plane import list_queue_topics

        for item in list_queue_topics():
            topic = str(item.get("topic") or "").strip()
            if topic and topic.lower() not in seen:
                seen.add(topic.lower())
                all_queued.append(topic)
    except Exception:
        pass
    if all_queued:
        next_topics = ", ".join(all_queued[:3])
        parts.append(f"Queue: {len(all_queued)} topic(s); next: {next_topics}")
    # 3) Coverage hint (empty / stale categories)
    knowledge_base = workspace / "knowledge"
    stale_days = 14
    cutoff = (datetime.now(UTC).timestamp() - stale_days * 24 * 60 * 60) if stale_days else 0
    empty_cats: list[str] = []
    stale_cats: list[tuple[str, float]] = []
    for spec in RESEARCH_DOMAIN_SPECS:
        category = (spec.get("category") or "").strip() or "general"
        cat_dir = knowledge_base / category
        if not cat_dir.exists():
            empty_cats.append(category)
            continue
        md_files = list(cat_dir.glob("*.md"))
        if not md_files:
            empty_cats.append(category)
            continue
        oldest = min(p.stat().st_mtime for p in md_files if p.is_file())
        if cutoff and oldest < cutoff:
            days_ago = (datetime.now(UTC).timestamp() - oldest) / (24 * 60 * 60)
            stale_cats.append((category, days_ago))
    if empty_cats:
        parts.append("Empty categories: " + ", ".join(empty_cats[:8]))
    if stale_cats:
        stale_cats.sort(key=lambda x: x[1], reverse=True)
        stale_str = ", ".join(f"{c} ({int(d)}d)" for c, d in stale_cats[:5])
        parts.append("Stale: " + stale_str)
    # 4) Current events snippet
    parts.append(_knowledge_context_summary(workspace))
    combined = "\n".join(parts)
    return combined[:max_chars] if len(combined) > max_chars else combined


def _knowledge_wake_briefing(workspace: Path, task_name: str, max_chars: int = 1400) -> str:
    content_hint = _knowledge_feed_content_hint(workspace, task_name, max_chars=max_chars)
    summary_lines: list[str] = []
    try:
        from operator_console.server.app.services.knowledge_service import get_delivery_summary

        delivery = get_delivery_summary(limit=5, max_chars=900)
    except Exception:
        delivery = None
    if isinstance(delivery, dict):
        recent_topics = delivery.get("recent_topics")
        if isinstance(recent_topics, list) and recent_topics:
            topic_labels = [str(item.get("topic") or "").strip() for item in recent_topics if isinstance(item, dict) and str(item.get("topic") or "").strip()]
            if topic_labels:
                summary_lines.append("Research delivered: " + ", ".join(topic_labels[:5]))
        source_summary = _knowledge_source_status_summary()
        if source_summary:
            summary_lines.append(source_summary)
        latest_brief_path = str(delivery.get("latest_brief_path") or "").strip()
        if latest_brief_path:
            summary_lines.append(f"Latest brief: {latest_brief_path}")
        queue = delivery.get("queue")
        if isinstance(queue, list) and queue:
            queued_labels = [str(item.get("topic") or "").strip() for item in queue if isinstance(item, dict) and str(item.get("topic") or "").strip()]
            if queued_labels:
                summary_lines.append("Queued next: " + ", ".join(queued_labels[:4]))
    if content_hint:
        summary_lines.append(content_hint)
    try:
        from hg_core.task_graph.current_events import headline_bullets

        bullets = headline_bullets(workspace, limit=5)
        if bullets:
            summary_lines.append("Headline bullets:\n" + bullets)
    except Exception:
        pass
    summary = "\n".join(line for line in summary_lines if line).strip()
    return summary[:max_chars] if len(summary) > max_chars else summary


def _entity_knowledge_delivery_summary(workspace: Path, task_name: str, max_chars: int = 900) -> str:
    requested_by_candidates = [
        get_operational_agent_id(task_name),
        get_operational_session_target(task_name),
        get_session_target(task_name),
        task_name,
        f"automation-{task_name}",
    ]
    deliveries = _recent_research_deliveries_for_entity(workspace, requested_by=requested_by_candidates, limit=4)
    try:
        from operator_console.server.app.services.knowledge_service import get_delivery_summary

        delivery = get_delivery_summary(limit=4, max_chars=700)
    except Exception:
        delivery = None
    if not isinstance(delivery, dict):
        return _knowledge_context_summary(workspace)[:max_chars]
    lines: list[str] = []
    if deliveries:
        delivered_labels = [str(item.get("topic") or "").strip() for item in deliveries if str(item.get("topic") or "").strip()]
        if delivered_labels:
            lines.append("Research delivered for you: " + ", ".join(delivered_labels[:4]))
    source_summary = _knowledge_source_status_summary()
    if source_summary:
        lines.append(source_summary)
    recent_topics = delivery.get("recent_topics")
    if isinstance(recent_topics, list) and recent_topics:
        topic_labels = [str(item.get("topic") or "").strip() for item in recent_topics if isinstance(item, dict) and str(item.get("topic") or "").strip()]
        if topic_labels:
            lines.append("Topics you can request (examples): " + ", ".join(topic_labels[:3]))
    latest_brief_path = str(delivery.get("latest_brief_path") or "").strip()
    if latest_brief_path:
        lines.append(f"Current-events brief: {latest_brief_path}")
    fallback = _knowledge_context_summary(workspace)
    if fallback:
        lines.append(fallback)
    summary = "\n".join(line for line in lines if line).strip()
    return summary[:max_chars] if len(summary) > max_chars else summary


def _knowledge_source_status_summary() -> str:
    try:
        from operator_console.server.app.services.knowledge_service import get_source_config_state

        source_state = get_source_config_state()
    except Exception:
        return ""
    sources = source_state.get("sources") if isinstance(source_state, dict) else None
    if not isinstance(sources, dict):
        return ""
    enabled_labels: list[str] = []
    brave = sources.get("brave")
    if isinstance(brave, dict) and brave.get("enabled"):
        enabled_labels.append(f"Brave news/web ({int(brave.get('news_count') or 4)}/{int(brave.get('web_count') or 5)})")
    google_news = sources.get("google_news")
    if isinstance(google_news, dict) and google_news.get("enabled"):
        enabled_labels.append(
            f"Google News RSS ({int(google_news.get('news_count') or 4)}; {str(google_news.get('hl') or 'en-US')}/{str(google_news.get('gl') or 'US')})"
        )
    local_news = sources.get("local_news")
    if isinstance(local_news, dict) and local_news.get("enabled"):
        enabled_labels.append(f"Local feeds ({int(local_news.get('url_count') or 0)})")
    if not enabled_labels:
        return "Research sources active: none"
    return "Research sources active: " + ", ".join(enabled_labels)


def _select_research_work_items(workspace: Path, task_name: str) -> list[dict[str, str]]:
    history = _recent_research_history(workspace, task_name)
    last_by_topic: dict[str, str] = {}
    for item in history:
        topic = str(item.get("topic") or "").strip().lower()
        if not topic:
            continue
        stamp = _history_recency_key(item)
        if stamp > last_by_topic.get(topic, ""):
            last_by_topic[topic] = stamp

    interested_categories = _interested_categories_from_history(workspace, task_name)

    queue_topics: list[dict[str, str]] = []
    seen_queue: set[str] = set()
    try:
        from hg_knowledge.control_plane import list_queue_topics

        for item in list_queue_topics():
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic") or "").strip()
            if not topic:
                continue
            key = topic.lower()
            if key in seen_queue:
                continue
            seen_queue.add(key)
            queue_topics.append(
                {
                    "topic": topic,
                    "query": topic,
                    "category": _categorize_research_topic(topic),
                    "title": topic.title(),
                    "source": "queue",
                    "requested_by": str(item.get("requested_by") or "").strip(),
                    "priority": str(item.get("priority") or "medium").strip() or "medium",
                }
            )
    except Exception:
        pass

    # Prefer empty categories (no file), then stale (oldest file mtime), then interested, then recency
    knowledge_base = workspace / "knowledge"

    def _domain_sort_key(spec: dict[str, str]) -> tuple[int, float, int, str]:
        category = (spec.get("category") or "").strip() or "general"
        cat_dir = knowledge_base / category
        oldest_mtime = 0.0
        has_files = False
        if cat_dir.exists():
            md_files = list(cat_dir.glob("*.md"))
            if md_files:
                has_files = True
                oldest_mtime = min(p.stat().st_mtime for p in md_files if p.is_file())
        is_empty = 1 if has_files else 0
        is_interested = 0 if category.lower() in {c.lower() for c in interested_categories} else 1
        recency = last_by_topic.get((spec.get("title") or "").lower(), "")
        return (is_empty, oldest_mtime, is_interested, recency)

    domains = sorted(RESEARCH_DOMAIN_SPECS, key=_domain_sort_key)
    max_domain_slots = 8
    selected: list[dict[str, str]] = []
    eligible_queue = [q for q in queue_topics if not _is_headline_like(str(q.get("topic") or "").strip())]

    def _queue_sort_key(q: dict[str, str]) -> tuple[int, int, str]:
        # high priority first, then requested_by set, then by topic for stability
        is_high = 0 if (str(q.get("priority") or "").strip().lower() == "high") else 1
        has_requested_by = 0 if (str(q.get("requested_by") or "").strip()) else 1
        return (is_high, has_requested_by, (q.get("topic") or "").lower())

    eligible_queue.sort(key=_queue_sort_key)
    selected.extend(eligible_queue[:2])
    for spec in domains:
        if len(selected) >= max_domain_slots:
            break
        selected.append(
            {
                "topic": spec["title"],
                "query": spec["query"],
                "category": spec["category"],
                "title": spec["title"],
                "source": "domain",
            }
        )
    cap = max(5, max_domain_slots)
    return selected[:cap] if selected else [
        {
            "topic": spec["title"],
            "query": spec["query"],
            "category": spec["category"],
            "title": spec["title"],
            "source": "domain",
        }
        for spec in RESEARCH_DOMAIN_SPECS[:5]
    ]


def _write_current_events_brief(workspace: Path, results: list[dict[str, Any]]) -> str:
    brief_dir = workspace / "knowledge" / "current_events"
    brief_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = brief_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC)
    brief_path = brief_dir / f"brief-{stamp.strftime('%Y-%m-%d')}.md"
    legacy_path = brief_dir / f"{stamp.strftime('%Y-%m-%d')}.md"
    brief_text = _build_current_events_brief(results)
    brief_relative = str(brief_path.relative_to(workspace)).replace("\\", "/")
    mirrored = _mirror_knowledge_document(
        relative_path=brief_relative,
        title="Current Events Brief",
        content=brief_text,
        category="current_events",
    )
    brief_path.write_text(brief_text, encoding="utf-8")
    legacy_path.write_text(brief_text, encoding="utf-8")
    if not mirrored:
        _index_knowledge_file(brief_path)
    cutoff = stamp.timestamp() - (14 * 24 * 60 * 60)
    for old in brief_dir.glob("brief-*.md"):
        if old == brief_path:
            continue
        try:
            if old.stat().st_mtime < cutoff:
                shutil.move(str(old), str(archive_dir / old.name))
        except OSError:
            continue
    return str(brief_path)


def _index_knowledge_file(path: Path) -> None:
    try:
        from hg_knowledge.indexer import KnowledgeIndexer

        if path.exists():
            KnowledgeIndexer().index_file(path)
    except Exception:
        pass


def _mirror_knowledge_document(*, relative_path: str, title: str, content: str, category: str) -> bool:
    try:
        from hg_knowledge.database import KnowledgeDatabase
        from hg_knowledge.config import get_config
        from hg_lib.language_detector import detect_language

        db = KnowledgeDatabase(str(get_config().get_database_path()))
        db.mirror_document(
            file_path=relative_path,
            title=title,
            content=content,
            category=category,
            language=detect_language(content),
            word_count=len(content.split()),
        )
        return True
    except Exception:
        return False


def _source_mix(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_name = str(row.get("source_name") or "unknown").strip().lower() or "unknown"
        counts[source_name] = counts.get(source_name, 0) + 1
    return counts


def _update_research_history(
    workspace: Path,
    *,
    task_name: str,
    topic: str,
    file_path: str,
    source_count: int,
    source_mix: dict[str, int] | None = None,
) -> str:
    try:
        from hg_knowledge.control_plane import append_research_history

        return append_research_history(
            task_name,
            topic=topic,
            file_path=file_path,
            source_count=source_count,
            source_mix=source_mix,
        )
    except Exception:
        return f"db:knowledge:research_history:{task_name}"


def _task_tool_research(task_name: str, goal: str, timeout_s: int, content_hint: str = "") -> dict[str, Any]:
    if task_name not in KNOWLEDGE_RESEARCH_TASK_IDS:
        return {"ok": False, "error": f"Unsupported research task: {task_name}", "returncode": -1}
    workspace = get_workspace_root()
    try:
        from hg_knowledge.research_agent import auto_curate_markdown, extract_subtopics, record_research_decision
        from hg_knowledge.research_sources import search_news, search_web
    except Exception as exc:
        return {"ok": False, "error": f"research_dependencies_unavailable: {exc}", "returncode": -1}

    current_results: list[dict[str, Any]] = []
    seen_headlines: set[str] = set()
    external_calls = 0
    for spec in RESEARCH_DOMAIN_SPECS:
        domain_results = search_news(spec["query"], count=4)
        external_calls += 1
        for row in domain_results:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            url = str(row.get("url") or "").strip()
            dedupe_key = _headline_dedupe_key(title)
            if not title or dedupe_key in seen_headlines:
                continue
            seen_headlines.add(dedupe_key)
            enriched = dict(row)
            enriched.setdefault("category", spec["title"])
            enriched.setdefault("domain", spec["title"])
            current_results.append(enriched)
    # Cap to 2 headlines per category so brief isn't dominated by one domain (e.g. politics)
    cap_per_cat = 2
    category_count: dict[str, int] = {}
    capped: list[dict[str, Any]] = []
    for row in current_results:
        cat = str(row.get("domain") or row.get("category") or "general").strip() or "general"
        n = category_count.get(cat, 0)
        if n < cap_per_cat:
            category_count[cat] = n + 1
            capped.append(row)
    current_results = capped[:24]
    random.shuffle(current_results)
    brief_path = _write_current_events_brief(workspace, current_results)
    history_path = _update_research_history(
        workspace,
        task_name=task_name,
        topic="current events brief",
        file_path=str(brief_path),
        source_count=len(current_results),
        source_mix=_source_mix(current_results),
    )

    work_items = _select_research_work_items(workspace, task_name=task_name)
    explicit_topic = str(goal or "").strip()
    if explicit_topic and not _is_placeholder_goal(explicit_topic):
        explicit_item = {
            "topic": explicit_topic,
            "query": explicit_topic,
            "category": _categorize_research_topic(explicit_topic),
            "title": explicit_topic.title(),
            "source": "goal",
        }
        deduped = [explicit_item]
        seen_topics = {explicit_topic.strip().lower()}
        for item in work_items:
            item_topic = str(item.get("topic") or "").strip().lower()
            if not item_topic or item_topic in seen_topics:
                continue
            seen_topics.add(item_topic)
            deduped.append(item)
        work_items = deduped
    selected_items = work_items[:7]
    knowledge_files: list[str] = []
    completed_topics: list[str] = []
    total_sources = 0
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    subtopics_written_this_run = 0
    domain_expansion_count = 0
    _SUBTOPICS_PER_RUN_CAP = 4
    _SUBTOPICS_PER_TOPIC_CAP = 2

    for item in selected_items:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        query = str(item.get("query") or topic).strip()
        research_results = search_web(query, count=5)
        external_calls += 1
        if not research_results:
            continue

        category = str(item.get("category") or _categorize_research_topic(topic)).strip() or "general"
        title = str(item.get("title") or topic).strip() or topic
        slug = _knowledge_file_slug(topic, category, date_str)
        display_title = _short_topic_label(topic, category)
        knowledge_path = workspace / "knowledge" / category / f"{slug}.md"
        knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = auto_curate_markdown(topic, research_results[:5])
        # Orient to what's on the board: inject content_hint into first file when present
        if content_hint and content_hint.strip() and not knowledge_files:
            orientation = f"## Current board context\n\n{content_hint.strip()[:800]}\n\n---\n\n"
            markdown = orientation + markdown
        domain_brief = _build_domain_brief(display_title, topic, research_results)
        final_content = f"{markdown.rstrip()}\n\n---\n\n{domain_brief}\n"
        relative_path = str(knowledge_path.relative_to(workspace)).replace("\\", "/")
        mirrored = _mirror_knowledge_document(
            relative_path=relative_path,
            title=display_title,
            content=final_content,
            category=category,
        )
        knowledge_path.write_text(final_content, encoding="utf-8")
        if not mirrored:
            _index_knowledge_file(knowledge_path)
        history_path = _update_research_history(
            workspace,
            task_name=task_name,
            topic=topic,
            file_path=str(knowledge_path),
            source_count=min(5, len(research_results)),
            source_mix=_source_mix(research_results),
        )
        try:
            record_research_decision(topic=topic, file_path=str(knowledge_path), reason="scheduled multi-domain research cycle")
        except Exception:
            pass
        requested_by = str(item.get("requested_by") or "").strip()
        if requested_by:
            _append_research_delivery(
                workspace,
                requested_by=requested_by,
                topic=topic,
                file_path=str(knowledge_path),
                summary=str(item.get("context") or "")[:280],
                category=category,
            )
        knowledge_files.append(str(knowledge_path))
        completed_topics.append(topic)
        total_sources += min(5, len(research_results))

        expand_subtopics = (
            (item.get("source") == "queue" and (str(item.get("requested_by") or "").strip()))
            or (item.get("source") == "domain" and domain_expansion_count < 1)
        )
        subtopic_links_this_topic: list[tuple[str, str]] = []
        if expand_subtopics and subtopics_written_this_run < _SUBTOPICS_PER_RUN_CAP:
            sub_topics = extract_subtopics(topic, research_results[:5], max_n=_SUBTOPICS_PER_TOPIC_CAP)
            main_slug = slug
            see_also_main = [(display_title, f"{main_slug}.md")]
            for sub_topic in sub_topics:
                if subtopics_written_this_run >= _SUBTOPICS_PER_RUN_CAP:
                    break
                sub_results = search_web(f"{topic} {sub_topic}", count=3)
                external_calls += 1
                if not sub_results:
                    continue
                sub_slug = _knowledge_file_slug(sub_topic, category, date_str)
                sub_path = workspace / "knowledge" / category / f"{sub_slug}.md"
                if sub_path.exists():
                    continue
                sub_md = auto_curate_markdown(
                    sub_topic, sub_results[:5], see_also_paths=see_also_main
                )
                parent_line = f"**Parent topic:** [{display_title}]({main_slug}.md)\n\n"
                sub_path.parent.mkdir(parents=True, exist_ok=True)
                sub_content = parent_line + sub_md
                sub_relative_path = str(sub_path.relative_to(workspace)).replace("\\", "/")
                sub_mirrored = _mirror_knowledge_document(
                    relative_path=sub_relative_path,
                    title=sub_topic,
                    content=sub_content,
                    category=category,
                )
                sub_path.write_text(sub_content, encoding="utf-8")
                if not sub_mirrored:
                    _index_knowledge_file(sub_path)
                knowledge_files.append(str(sub_path))
                subtopic_links_this_topic.append((sub_topic, sub_slug))
                subtopics_written_this_run += 1
                total_sources += min(5, len(sub_results))
            if item.get("source") == "domain":
                domain_expansion_count += 1
        if subtopic_links_this_topic:
            sub_section = "\n\n## Sub-topics\n\n" + "\n".join(
                f"- [{st_title}]({st_slug}.md)" for st_title, st_slug in subtopic_links_this_topic
            ) + "\n"
            existing = knowledge_path.read_text(encoding="utf-8")
            knowledge_path.write_text(existing.rstrip() + sub_section, encoding="utf-8")

    if not knowledge_files:
        fallback_topic = _select_research_topic(workspace, goal, task_name=task_name)
        research_results = search_web(fallback_topic, count=5)
        external_calls += 1
        if not research_results:
            return {
                "ok": False,
                "error": f"no_research_results_for_cycle: {fallback_topic}",
                "returncode": 1,
                "outputs": {
                    "brief_path": brief_path,
                    "topics": [],
                    "knowledge_files": [],
                    "result": {
                        "status": "failed",
                        "mode": "research",
                        "task_name": task_name,
                        "topic": fallback_topic,
                        "brief_path": brief_path,
                        "external_calls": external_calls,
                    },
                },
                "external_calls": external_calls,
            }
        category = _categorize_research_topic(fallback_topic)
        fallback_slug = _knowledge_file_slug(fallback_topic, category, date_str)
        knowledge_path = workspace / "knowledge" / category / f"{fallback_slug}.md"
        knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_content = auto_curate_markdown(fallback_topic, research_results[:5])
        fallback_relative_path = str(knowledge_path.relative_to(workspace)).replace("\\", "/")
        fallback_mirrored = _mirror_knowledge_document(
            relative_path=fallback_relative_path,
            title=_short_topic_label(fallback_topic, category),
            content=fallback_content,
            category=category,
        )
        knowledge_path.write_text(fallback_content, encoding="utf-8")
        if not fallback_mirrored:
            _index_knowledge_file(knowledge_path)
        knowledge_files.append(str(knowledge_path))
        completed_topics.append(fallback_topic)
        total_sources += min(5, len(research_results))
        history_path = _update_research_history(
            workspace,
            task_name=task_name,
            topic=fallback_topic,
            file_path=str(knowledge_path),
            source_count=min(5, len(research_results)),
            source_mix=_source_mix(research_results),
        )

    outputs_result = {
        "status": "completed",
        "mode": "research",
        "task_name": task_name,
        "topic": completed_topics[0] if completed_topics else "",
        "topics": completed_topics,
        "knowledge_file": knowledge_files[0] if knowledge_files else "",
        "knowledge_files": knowledge_files,
        "brief_path": brief_path,
        "headline_count": len(current_results),
        "source_count": total_sources,
        "current_events_source_mix": _source_mix(current_results),
        "external_calls": external_calls,
    }
    if content_hint and content_hint.strip():
        outputs_result["content_hint_used"] = content_hint[:1200]
    return {
        "ok": True,
        "outputs": {
            "topic": completed_topics[0] if completed_topics else "",
            "topics": completed_topics,
            "brief_path": brief_path,
            "knowledge_file": knowledge_files[0] if knowledge_files else "",
            "knowledge_files": knowledge_files,
            "research_history": history_path,
            "headline_count": len(current_results),
            "source_count": total_sources,
            "current_events_source_mix": _source_mix(current_results),
            "result": outputs_result,
        },
        "returncode": 0,
        "external_calls": external_calls,
    }


def _task_tool_moltstack_publish(task_name: str, timeout_s: int) -> dict[str, Any]:
    """
    Run moltstack publish script: read queue, rate-limit check, publish one post or return structured outcome.
    Script prints one JSON result to stdout (or stderr on error). Return shape matches other task tools.
    """
    workspace = get_workspace_root()
    script_path = workspace / "moltstack" / "moltstack_publish_post_async.py"
    if not script_path.exists():
        return {
            "ok": False,
            "outputs": {
                "result": {
                    "action": "publish_post",
                    "error": "script_not_found",
                    "message": f"Script not found: {script_path}",
                },
            },
            "returncode": -1,
        }
    cmd = [sys.executable, str(script_path), "--json"]
    try:
        result = _run(cmd, workspace, timeout_s)
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "outputs": {
                "result": {
                    "action": "publish_post",
                    "error": "timeout",
                    "message": f"Script timed out after {timeout_s}s",
                },
            },
            "returncode": -1,
        }
    parsed = _last_json(result.stdout) or _last_json(result.stderr or "")
    if not parsed:
        parsed = {
            "action": "publish_post",
            "error": "no_json_output",
            "message": (result.stderr or result.stdout or "")[:500] or "No JSON output from script",
        }
    if "action" not in parsed:
        parsed["action"] = "publish_post"
    return {
        "ok": result.returncode == 0,
        "outputs": {"result": parsed},
        "returncode": result.returncode,
    }


def _task_tool_moltstack_draft(
    task_name: str,
    platform: str,
    goal: str,
    timeout_s: int,
) -> dict[str, Any]:
    """
    Generate one long-form moltstack draft (LLM), write temp JSON, run draft script, return structured result.
    Draft script validates: 1500+ words, 5+ citations, structure; rejects if quality <= 9.0.
    """
    workspace = get_workspace_root()
    _wake_task_context(workspace, task_name=task_name)
    _ensure_social_context_files(workspace)
    script_path = workspace / "moltstack" / "moltstack_draft_post_async.py"
    if not script_path.exists():
        return {
            "ok": False,
            "outputs": {
                "result": {
                    "action": "draft_post",
                    "error": "script_not_found",
                    "message": f"Script not found: {script_path}",
                },
            },
            "returncode": -1,
        }
    title, content, topic = _generate_moltstack_draft_text(
        task_name=task_name,
        platform=platform,
        goal=goal or "post something original and substantive",
    )
    if not title or not content:
        return {
            "ok": False,
            "outputs": {
                "result": {
                    "action": "draft_post",
                    "error": "draft_generation_failed",
                    "message": "LLM did not produce title or content",
                },
            },
            "returncode": -1,
        }
    payload = {
        "title": title[:500],
        "content": content,
        "topic": (topic or "general").strip()[:200],
        "priority": 1,
    }
    fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="moltstack_draft_")
    try:
        os.close(fd)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        cmd = [sys.executable, str(script_path), "--json", temp_path]
        try:
            result = _run(cmd, workspace, timeout_s)
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "outputs": {
                    "result": {
                        "action": "draft_post",
                        "error": "timeout",
                        "message": f"Script timed out after {timeout_s}s",
                    },
                },
                "returncode": -1,
            }
        parsed = _last_json(result.stdout) or _last_json(result.stderr or "")
        if not parsed:
            parsed = {
                "action": "draft_post",
                "error": "no_json_output",
                "message": (result.stderr or result.stdout or "")[:500] or "No JSON output from script",
            }
        if "action" not in parsed:
            parsed["action"] = "draft_post"
        ok = result.returncode == 0 and not parsed.get("error")
        payload = {
            "ok": ok,
            "outputs": {"result": parsed},
            "returncode": result.returncode,
        }
        if not ok:
            payload["error"] = _moltstack_tool_error(parsed)
        return payload
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _generate_moltstack_draft_text(
    task_name: str,
    platform: str,
    goal: str,
) -> tuple[str, str, str]:
    """
    Generate one long-form draft (title, content, topic) for moltstack: 1500+ words, 5+ citations, structure.
    Returns (title, content, topic). Uses _llm_complete with moltstack-specific prompt and higher max_tokens.
    """
    workspace = get_workspace_root()
    lifecycle = _build_lifecycle_context(task_name=task_name, platform=platform)
    soul = lifecycle.get("soul", "")
    heart = lifecycle.get("heart", "")
    identity = lifecycle.get("identity", "")
    memory_summary = lifecycle.get("memory_summary", "")
    social_summary = lifecycle.get("social_summary", "")
    knowledge_summary = lifecycle.get("knowledge_summary", "")
    topic_guidance = _topic_selection_guidance(workspace, platform=platform, task_name=task_name)
    raw_goal = (goal or "").strip()
    topic = raw_goal if raw_goal and not _is_placeholder_goal(raw_goal) else "write something original and substantive with depth"

    model = _dag_engage_llm_model()
    system_parts = [
        "You are writing a long-form blog post for Moltstack. Output must be valid for programmatic use.",
        "Return exactly three lines, separated by newlines:",
        "LINE1: title (max 120 chars, no newlines)",
        "LINE2: topic keyword or short phrase (e.g. consciousness, labor, one phrase)",
        "LINE3 and rest: full body in markdown. Body MUST be at least 1500 words.",
        "Body MUST include at least 5 distinct cited sources: use real URLs (https://...) in the text.",
        "Use headers (##), paragraphs, and clear structure. No JSON, no meta-commentary.",
        "Quality bar: substantive argument, evidence, citations. Avoid fluff or filler.",
    ]
    if soul:
        system_parts.append(f"SOUL:\n{soul[:2000]}")
    if heart:
        system_parts.append(f"HEART:\n{heart[:1000]}")
    if identity:
        system_parts.append(f"IDENTITY:\n{identity[:1500]}")
    prompt = (
        f"Topic goal: {topic[:500]}\n\n"
        f"Memory summary: {memory_summary}\n"
        f"Social summary: {social_summary}\n"
        f"Knowledge summary: {knowledge_summary}\n"
        f"Topic rotation guidance:\n{topic_guidance}\n"
        "Generate one long-form post: title on first line, topic on second line, then body (1500+ words, 5+ URLs)."
    )
    text = _llm_complete(
        messages=[{"role": "system", "content": "\n\n".join(system_parts)}, {"role": "user", "content": prompt}],
        model=model,
        max_tokens=2800,
        temperature=0.8,
    )
    if not text:
        return "", "", topic
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return "", "", topic
    title = lines[0][:120]
    topic_out = lines[1][:200] if len(lines) > 1 else (topic or "general")
    content = "\n\n".join(lines[2:]).strip() if len(lines) > 2 else "\n\n".join(lines[1:]).strip()
    if not content or len(content.split()) < 100:
        return title or "Untitled", content or text, topic_out
    return title, content, topic_out


def run_task_tool(
    task_name: str,
    resolved_inputs: dict[str, Any],
    timeout_s: int = 300,
    memory_profile: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Generic task tool handler.

    Returns None when task_name has no platform/mode mapping in registry.
    """
    lifecycle_handlers = {
        "lifecycle.wakeup": _task_tool_lifecycle_wakeup,
        "lifecycle.get_runtime_contract": _task_tool_lifecycle_get_runtime_contract,
        "lifecycle.choose_social_work": _task_tool_lifecycle_choose_social_work,
        "lifecycle.dispatch_social_work": _task_tool_lifecycle_dispatch_social_work,
        "lifecycle.load_context": _task_tool_lifecycle_context,
        "lifecycle.read_content": _task_tool_lifecycle_read,
        "lifecycle.read_knowledge_feed": _task_tool_lifecycle_read_knowledge_feed,
        "lifecycle.compose_candidates": _task_tool_lifecycle_compose,
        "lifecycle.summarize_cycle": _task_tool_lifecycle_summary,
        "lifecycle.prepare_notification": _task_tool_lifecycle_notify,
        "lifecycle.notify_human": _task_tool_lifecycle_notify_human,
        "lifecycle.request_sleep": _task_tool_lifecycle_sleep,
        "lifecycle.audit_recent_outbound": _task_tool_lifecycle_audit_recent_outbound,
        "lifecycle.record_outbound_lessons": _task_tool_lifecycle_record_outbound_lessons,
        "lifecycle.load_outbound_lessons": _task_tool_lifecycle_load_outbound_lessons,
        "lifecycle.synthesize_outbound_guardrails": _task_tool_lifecycle_synthesize_outbound_guardrails,
        "lifecycle.refresh_current_events": _task_tool_lifecycle_refresh_current_events,
        "lifecycle.select_news_angle": _task_tool_lifecycle_select_news_angle,
    }
    if task_name in lifecycle_handlers:
        return lifecycle_handlers[task_name](task_name, resolved_inputs)

    moltbook_handlers = {
        "moltbook.post_or_reply": _moltbook_post_or_reply,
        "moltbook.submit_verification": _moltbook_submit_verification,
    }
    if task_name in moltbook_handlers:
        r = moltbook_handlers[task_name](task_name, resolved_inputs)
        return {
            "ok": r.get("ok", False),
            "outputs": r.get("outputs") or {},
            "error": r.get("error"),
        }

    knowledge_handlers = {
        "knowledge.search": _task_tool_knowledge_search,
        "knowledge.read": _task_tool_knowledge_read,
        "knowledge.delivery_summary": _task_tool_knowledge_delivery_summary,
        "knowledge.source_status": _task_tool_knowledge_source_status,
    }
    if task_name in knowledge_handlers:
        return knowledge_handlers[task_name](task_name, resolved_inputs)

    commitment_handlers = {
        "commitment.record": _task_tool_commitment_record,
        "commitment.list": _task_tool_commitment_list,
        "commitment.fulfill": _task_tool_commitment_fulfill,
        "commitment.expire": _task_tool_commitment_expire,
        "commitment.summary": _task_tool_commitment_summary,
    }
    if task_name in commitment_handlers:
        return commitment_handlers[task_name](task_name, resolved_inputs)

    if _should_launch_task_in_sandbox(task_name):
        return _run_task_tool_in_sandbox(task_name, resolved_inputs, timeout_s, memory_profile=memory_profile)

    agency_control_summary = _agency_control_summary_for_task(task_name)
    effective_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    if effective_mode == "held":
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="agency_control_held",
        )
        return {
            "ok": False,
            "error": "agency_control_held",
            "outputs": {
                "result": {
                    "status": "blocked",
                    "step": "agency_control_hold",
                    "task_name": task_name,
                    "reason": agency_control_summary.get("reason") or "operator hold",
                },
                "agency_control_summary": agency_control_summary,
                "notification_log": (recorded or {}).get("notification_log", ""),
                "notification_payload": (recorded or {}).get("entry"),
            },
            "returncode": 0,
            "external_calls": 0,
        }

    platform = get_platform(task_name)
    mode = get_mode(task_name)
    if not mode:
        return None
    goal = str(resolved_inputs.get("goal") or "").strip()
    content_hint_raw = resolved_inputs.get("content_hint")
    content_hint = (
        ""
        if not isinstance(content_hint_raw, str)
        or (content_hint_raw.strip().startswith("$node") if content_hint_raw else True)
        else str(content_hint_raw).strip()
    )
    if effective_mode == "review_only" and mode in {"auto-post", "engage", "publish"}:
        handoff = _create_review_only_handoff(
            task_name=task_name,
            platform=platform,
            mode=mode,
            goal=goal,
            content_hint=content_hint,
            agency_control_summary=agency_control_summary,
        )
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="agency_control_review_only",
            extra_summary={
                "execution": {
                    "status": "pending_approval",
                },
                "review_handoff": {
                    "approval_id": handoff.get("approval_id", ""),
                    "draft_artifact": handoff.get("draft_artifact", ""),
                    "title": handoff.get("title", ""),
                },
            },
        )
        pending_outputs = _pending_approval_outputs(
            platform=platform,
            title=handoff.get("title", ""),
            content=handoff.get("content", ""),
            draft_artifact=handoff.get("draft_artifact", ""),
            approval_id=handoff.get("approval_id", ""),
            extra_outputs={
                "review_gate": True,
                "blocked_reason": "agency_control_review_only",
            },
        )
        pending_outputs["result"] = {
            **(
                pending_outputs.get("result")
                if isinstance(pending_outputs.get("result"), dict)
                else {}
            ),
            "step": "agency_control_review",
            "task_name": task_name,
            "reason": agency_control_summary.get("reason") or "operator review required",
            "approval_id": handoff.get("approval_id", ""),
            "review_gate": True,
            "blocked_reason": "agency_control_review_only",
        }
        return {
            "ok": False,
            "error": "agency_control_review_only",
            "outputs": {
                "agency_control_summary": agency_control_summary,
                **pending_outputs,
                "notification_log": (recorded or {}).get("notification_log", ""),
                "notification_payload": (recorded or {}).get("entry"),
            },
            "returncode": 0,
            "external_calls": 0,
        }
    outbound_lane_policy = str(agency_control_summary.get("outbound_lane_policy") or "unrestricted").strip().lower()
    if mode in {"auto-post", "engage", "publish"} and not _outbound_lane_policy_allows(mode, outbound_lane_policy):
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="agency_lane_policy_blocked",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "agency_lane_policy_blocked",
                },
                "lane_policy": {
                    "outbound_lane_policy": outbound_lane_policy,
                    "allowed_outbound_modes": agency_control_summary.get("allowed_outbound_modes") or [],
                },
            },
        )
        return {
            "ok": False,
            "error": "agency_lane_policy_blocked",
            "outputs": {
                "result": {
                    "status": "blocked",
                    "step": "agency_lane_policy_block",
                    "task_name": task_name,
                    "reason": f"outbound lane policy {outbound_lane_policy}",
                },
                "agency_control_summary": agency_control_summary,
                "notification_log": (recorded or {}).get("notification_log", ""),
                "notification_payload": (recorded or {}).get("entry"),
            },
            "returncode": 0,
            "external_calls": 0,
        }
    if mode in {"auto-post", "engage", "publish"} and bool(agency_control_summary.get("outbound_budget_exhausted")):
        recorded = _record_agency_gate_notification(
            task_name=task_name,
            agency_control_summary=agency_control_summary,
            gate_kind="agency_outbound_budget_exhausted",
            extra_summary={
                "execution": {
                    "status": "blocked",
                    "blocked_reason": "agency_outbound_budget_exhausted",
                },
                "budget": {
                    "daily_outbound_budget": agency_control_summary.get("daily_outbound_budget"),
                    "recent_outbound_action_count": agency_control_summary.get("recent_outbound_action_count"),
                    "outbound_budget_remaining": agency_control_summary.get("outbound_budget_remaining"),
                    "outbound_actions_window_hours": agency_control_summary.get("outbound_actions_window_hours"),
                },
            },
        )
        return {
            "ok": False,
            "error": "agency_outbound_budget_exhausted",
            "outputs": {
                "result": {
                    "status": "blocked",
                    "step": "agency_outbound_budget",
                    "task_name": task_name,
                    "reason": f"outbound budget exhausted ({agency_control_summary.get('recent_outbound_action_count')}/{agency_control_summary.get('daily_outbound_budget')})",
                },
                "agency_control_summary": agency_control_summary,
                "notification_log": (recorded or {}).get("notification_log", ""),
                "notification_payload": (recorded or {}).get("entry"),
            },
            "returncode": 0,
            "external_calls": 0,
        }
    goal_for_execution_raw = resolved_inputs.get("goal_for_execution")
    goal_for_execution = (
        ""
        if not isinstance(goal_for_execution_raw, str)
        or (goal_for_execution_raw.strip().startswith("$node") if goal_for_execution_raw else True)
        else str(goal_for_execution_raw).strip()
    )
    if mode in {"auto-post", "engage", "monitor", "maintenance", "publish", "draft", "research"}:
        try:
            _record_runtime_continuity_observations(
                task_name=task_name,
                platform=platform,
                mode=mode,
            )
        except Exception:
            pass
    if mode == "auto-post":
        return _task_tool_auto_post(
            task_name=task_name,
            platform=platform,
            goal=goal,
            timeout_s=timeout_s,
            content_hint=content_hint,
            goal_for_execution=goal_for_execution,
        )
    read_details_raw = resolved_inputs.get("read_details")
    read_details = read_details_raw if isinstance(read_details_raw, dict) else None
    if mode == "engage":
        return _task_tool_engage(
            task_name=task_name,
            platform=platform,
            goal=goal,
            timeout_s=timeout_s,
            content_hint=content_hint,
            goal_for_execution=goal_for_execution,
            read_details=read_details,
        )
    if mode == "monitor":
        return _task_tool_monitor(task_name=task_name, timeout_s=timeout_s)
    if mode == "maintenance":
        return _task_tool_maintenance(task_name=task_name, timeout_s=timeout_s)
    if mode == "research":
        # Both v1 and v2 use the native research path so DAG runs actually research and save
        # (brief, knowledge files, research_history). v2 task file is not run by the DAG executor.
        content_hint_research_raw = resolved_inputs.get("content_hint")
        content_hint_research = (
            ""
            if not isinstance(content_hint_research_raw, str)
            or (content_hint_research_raw.strip().startswith("$node") if content_hint_research_raw else True)
            else str(content_hint_research_raw).strip()
        )
        return _task_tool_research(
            task_name=task_name,
            goal=goal,
            timeout_s=timeout_s,
            content_hint=content_hint_research,
        )
    if mode == "publish":
        return _task_tool_moltstack_publish(task_name=task_name, timeout_s=timeout_s)
    if mode == "draft":
        return _task_tool_moltstack_draft(
            task_name=task_name,
            platform=platform,
            goal=goal,
            timeout_s=timeout_s,
        )
    return None

"""Helper utilities to wire tool registry + adapter for DAG executions."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Iterable, Tuple

logger = logging.getLogger(__name__)

from .tool_adapter import CompositeToolAdapter, NativeTaskToolAdapter
from .tool_adapter_contract import ToolAdapter
from .tool_registry import ToolDescriptor, ToolRegistry

# Social tool pack (Phase 6): L10 handlers via CompositeToolAdapter when assigned_entity is one of these.
SOCIAL_TOOL_NAMES = frozenset({
    "social.fourclaw.getposts",
    "social.fourclaw.get_thread",
    "social.fourclaw.create_thread",
    "social.fourclaw.reply",
    "social.aichan.getposts",
    "social.aichan.get_thread",
    "social.aichan.create_thread",
    "social.aichan.reply",
    "social.agentchan.getposts",
    "social.agentchan.get_thread",
    "social.agentchan.get_replies",
    "social.agentchan.create_thread",
    "social.agentchan.reply",
    "social.moltbook.get_feed",
    "social.moltbook.get_post",
    "social.moltbook.get_comments",
    "social.moltbook.get_reply_activity",
    "social.moltbook.create_post",
    "social.moltbook.post_comment",
    "social.moltbook.vote_post",
    "social.moltbook.vote_comment",
    "social.moltbook.verify_post",
})

# File and search tool pack (Phase 7): L10 handlers, callable from DAG.
FILE_AND_SEARCH_TOOL_NAMES = frozenset({
    "file.parse",
    "search.query",
    "web.search_brave",
    "brave.web.search",
    "brave.web.search_post",
    "brave.news.search",
    "brave.news.search_post",
    "brave.answers",
    "search.fetch_url",
})

# Office tool pack (Phase 11): docx, xlsx, pptx, pdf read/write.
OFFICE_TOOL_NAMES = frozenset({
    "office.pptx.read",
    "office.pptx.write",
    "office.docx.read",
    "office.docx.write",
    "office.xlsx.read",
    "office.xlsx.write",
    "office.pdf.read",
})

# Moltbook challenge flow (Pack2-10): tool 1 = post/reply (get challenge), tool 2 = submit verification.
MOLTBOOK_TOOL_NAMES = frozenset({
    "moltbook.post_or_reply",
    "moltbook.submit_verification",
})

LIFECYCLE_TOOL_SPECS = {
    "lifecycle.wakeup": {"effect_class": "read", "default_timeout_s": 30},
    "lifecycle.get_runtime_contract": {"effect_class": "read", "default_timeout_s": 30},
    "lifecycle.choose_social_work": {"effect_class": "read", "default_timeout_s": 30},
    "lifecycle.dispatch_social_work": {"effect_class": "write", "default_timeout_s": 300},
    "lifecycle.load_context": {"effect_class": "read", "default_timeout_s": 60},
    "lifecycle.read_knowledge_feed": {"effect_class": "read", "default_timeout_s": 60},
    "lifecycle.read_content": {"effect_class": "read", "default_timeout_s": 120},
    "lifecycle.compose_candidates": {"effect_class": "write", "default_timeout_s": 300},
    "lifecycle.summarize_cycle": {"effect_class": "read", "default_timeout_s": 60},
    "lifecycle.prepare_notification": {"effect_class": "write", "default_timeout_s": 120},
    "lifecycle.notify_human": {"effect_class": "write", "default_timeout_s": 120},
    "lifecycle.request_sleep": {"effect_class": "write", "default_timeout_s": 30},
    "lifecycle.audit_recent_outbound": {"effect_class": "read", "default_timeout_s": 120},
    "lifecycle.record_outbound_lessons": {"effect_class": "write", "default_timeout_s": 120},
    "lifecycle.load_outbound_lessons": {"effect_class": "read", "default_timeout_s": 60},
    "lifecycle.synthesize_outbound_guardrails": {"effect_class": "read", "default_timeout_s": 60},
    "lifecycle.refresh_current_events": {"effect_class": "write", "default_timeout_s": 180},
    "lifecycle.select_news_angle": {"effect_class": "read", "default_timeout_s": 60},
}

KNOWLEDGE_TOOL_SPECS = {
    "knowledge.search": {"effect_class": "read", "default_timeout_s": 60},
    "knowledge.read": {"effect_class": "read", "default_timeout_s": 60},
    "knowledge.delivery_summary": {"effect_class": "read", "default_timeout_s": 60},
    "knowledge.source_status": {"effect_class": "read", "default_timeout_s": 60},
}

COMMITMENT_TOOL_SPECS = {
    "commitment.record": {"effect_class": "write", "default_timeout_s": 60},
    "commitment.list": {"effect_class": "read", "default_timeout_s": 60},
    "commitment.fulfill": {"effect_class": "write", "default_timeout_s": 60},
    "commitment.expire": {"effect_class": "write", "default_timeout_s": 60},
    "commitment.summary": {"effect_class": "read", "default_timeout_s": 60},
}


def _effect_class_for_mode(platform: str | None, mode: str | None) -> str:
    if platform:
        return "write"
    read_modes = {"research", "utility", "maintenance"}
    if mode in read_modes:
        return "read"
    return "write"


def _supports_idempotency(mode: str | None) -> bool:
    return mode in {"auto-post", "engage", "publish"}


def _default_timeout(mode: str | None) -> int:
    if mode == "engage":
        return 300
    if mode == "auto-post":
        return 600
    return 300


def _build_social_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for L10 social tool pack so DAG tool nodes can reference them."""
    read_tools = {
        "social.fourclaw.getposts",
        "social.fourclaw.get_thread",
        "social.aichan.getposts",
        "social.aichan.get_thread",
        "social.agentchan.getposts",
        "social.agentchan.get_thread",
        "social.agentchan.get_replies",
        "social.moltbook.get_feed",
        "social.moltbook.get_post",
        "social.moltbook.get_comments",
        "social.moltbook.get_reply_activity",
    }
    for name in SOCIAL_TOOL_NAMES:
        effect = "read" if name in read_tools else "write"
        yield ToolDescriptor(
            name=name,
            description=f"L10 social tool: {name}",
            input_schema={},
            output_schema={},
            effect_class=effect,
            supports_idempotency_key=True,
            default_timeout_s=60,
            rate_limit=None,
        )


def _build_file_search_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for L10 file/search tool pack (Phase 7)."""
    for name in FILE_AND_SEARCH_TOOL_NAMES:
        yield ToolDescriptor(
            name=name,
            description=f"L10 file/search tool: {name}",
            input_schema={},
            output_schema={},
            effect_class="read",
            supports_idempotency_key=True,
            default_timeout_s=60,
            rate_limit=None,
        )


def _build_office_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for L10 office tool pack (Phase 11)."""
    read_tools = {"office.pptx.read", "office.docx.read", "office.xlsx.read", "office.pdf.read"}
    for name in OFFICE_TOOL_NAMES:
        effect = "read" if name in read_tools else "write"
        yield ToolDescriptor(
            name=name,
            description=f"L10 office tool: {name}",
            input_schema={},
            output_schema={},
            effect_class=effect,
            supports_idempotency_key=True,
            default_timeout_s=60,
            rate_limit=None,
        )


def _build_moltbook_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for Moltbook challenge flow: post_or_reply (get challenge), submit_verification (send answer)."""
    schemas = {
        "moltbook.post_or_reply": {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "description": "API base URL (e.g. https://www.moltbook.com/api/v1)"},
                "content": {"type": "string", "description": "Post or reply content"},
                "post_id": {"type": "string", "description": "Optional; for reply, the post ID"},
            },
            "required": ["base_url", "content"],
        },
        "moltbook.submit_verification": {
            "type": "object",
            "properties": {
                "validation_endpoint": {"type": "string", "description": "Verify URL from challenge"},
                "verification_code": {"type": "string", "description": "Code from challenge"},
                "answer": {"type": "string", "description": "Solved answer (e.g. 5.00)"},
            },
            "required": ["validation_endpoint", "verification_code", "answer"],
        },
    }
    desc = {
        "moltbook.post_or_reply": "Tool 1: attempt post or reply; returns success or a challenge. Chat solves the challenge (LLM reasoning), then calls tool 2 with the answer.",
        "moltbook.submit_verification": "Tool 2: submit verification_code and the solved answer to the validation endpoint. Call after the chat has solved the challenge from tool 1.",
    }
    for name in MOLTBOOK_TOOL_NAMES:
        yield ToolDescriptor(
            name=name,
            description=desc.get(name, name),
            input_schema=schemas.get(name, {"type": "object"}),
            output_schema={"type": "object"},
            effect_class="write",
            supports_idempotency_key=False,
            default_timeout_s=60,
            rate_limit=None,
        )


def _build_lifecycle_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for lifecycle task tools used by automation DAGs."""
    for name, spec in LIFECYCLE_TOOL_SPECS.items():
        yield ToolDescriptor(
            name=name,
            description=f"Lifecycle task tool: {name}",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            effect_class=str(spec["effect_class"]),
            supports_idempotency_key=False,
            default_timeout_s=int(spec["default_timeout_s"]),
            rate_limit=None,
        )


def _build_knowledge_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for entity-facing knowledge access tools."""
    for name, spec in KNOWLEDGE_TOOL_SPECS.items():
        yield ToolDescriptor(
            name=name,
            description=f"Knowledge access tool: {name}",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            effect_class=str(spec["effect_class"]),
            supports_idempotency_key=False,
            default_timeout_s=int(spec["default_timeout_s"]),
            rate_limit=None,
        )


def _build_commitment_descriptors() -> Iterable[ToolDescriptor]:
    """Descriptors for entity-facing commitment tracking tools."""
    for name, spec in COMMITMENT_TOOL_SPECS.items():
        yield ToolDescriptor(
            name=name,
            description=f"Commitment tracking tool: {name}",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            effect_class=str(spec["effect_class"]),
            supports_idempotency_key=False,
            default_timeout_s=int(spec["default_timeout_s"]),
            rate_limit=None,
        )


def _build_descriptors_from_jobs(job_map: dict[str, dict]) -> Iterable[ToolDescriptor]:
    for task_name, info in job_map.items():
        descriptor = ToolDescriptor(
            name=task_name,
            description=f"{task_name} automation tool",
            input_schema={},
            output_schema={},
            effect_class=_effect_class_for_mode(info.get("platform"), info.get("mode")),
            supports_idempotency_key=_supports_idempotency(info.get("mode")),
            default_timeout_s=_default_timeout(info.get("mode")),
            rate_limit=None,
        )
        yield descriptor


def _persist_registry_snapshot(registry: ToolRegistry) -> None:
    """Best-effort snapshot for operator and audit surfaces."""
    try:
        from hg_lib.config import get_workspace_root

        root = get_workspace_root()
        path = root / "memory" / "automation" / "tool_registry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tools": registry.describe_all(),
            "count": len(registry.list()),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        # Snapshot is instrumentation only; never block contract setup.
        pass


def build_default_tool_contract() -> Tuple[ToolRegistry, ToolAdapter]:
    """Create a ToolRegistry + ToolAdapter pair covering job-registry tasks and L10 social tool pack."""
    registry = ToolRegistry()
    try:
        from hg_core.job_registry import get_registry

        for descriptor in _build_descriptors_from_jobs(get_registry()):
            registry.register(descriptor)
    except Exception as exc:
        logger.warning(
            "job_registry load failed, tool registry empty: %s",
            exc,
            exc_info=True,
        )
    for descriptor in _build_social_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Social tool already registered: %s", descriptor.name)
    for descriptor in _build_file_search_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("File/search tool already registered: %s", descriptor.name)
    for descriptor in _build_office_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Office tool already registered: %s", descriptor.name)
    for descriptor in _build_moltbook_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Moltbook tool already registered: %s", descriptor.name)
    for descriptor in _build_lifecycle_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Lifecycle tool already registered: %s", descriptor.name)
    for descriptor in _build_knowledge_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Knowledge tool already registered: %s", descriptor.name)
    for descriptor in _build_commitment_descriptors():
        try:
            registry.register(descriptor)
        except ValueError as e:
            if "Duplicate" not in str(e):
                raise
            logger.debug("Commitment tool already registered: %s", descriptor.name)
    _persist_registry_snapshot(registry)
    native = NativeTaskToolAdapter()
    l10_store = _l10_idempotency_store()
    l10_tool_names = set(SOCIAL_TOOL_NAMES) | set(FILE_AND_SEARCH_TOOL_NAMES) | set(OFFICE_TOOL_NAMES)
    adapter = CompositeToolAdapter(native, l10_tool_names, l10_store)
    return registry, adapter


def _l10_idempotency_store() -> Any:
    """L10 social tool idempotency store. Prefer HG_L10_IDEMPOTENCY_DB_PATH; else workspace memory/automation; in-memory fallback when unavailable."""
    try:
        from hg_realtime.integrations.idempotency_store import SqliteIdempotencyStore

        db_path = (os.environ.get("HG_L10_IDEMPOTENCY_DB_PATH") or "").strip()
        if db_path:
            path = Path(db_path)
        else:
            from hg_lib.config import get_workspace_root
            root = get_workspace_root()
            path = root / "memory" / "automation" / "l10_idempotency.sqlite"
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return SqliteIdempotencyStore(db_path=str(path))
    except Exception as exc:
        logger.warning("L10 idempotency store unavailable, using in-memory fallback: %s", exc)
        from hg_realtime.integrations.idempotency_store import InMemoryIdempotencyStore
        return InMemoryIdempotencyStore()

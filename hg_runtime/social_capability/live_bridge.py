"""Live social read bridge — read-only Moltbook/Fourclaw observation."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from hg_runtime.runtime_mode import RuntimeMode, is_fixture_mode, resolve_runtime_mode
from hg_runtime.social_capability.read_receipts import (
    LiveReadCredentialStatus,
    LiveReadReceipt,
    LiveReadVerdict,
    build_live_read_receipt,
    validate_live_read_receipt,
    verdict_counts_as_success,
)
from hg_runtime.social_capability.source_refs import (
    body_preview_hash,
    fourclaw_thread_ref,
    moltbook_post_ref,
    truncate_preview,
)

WORKSPACE = Path(__file__).resolve().parents[2]
LIVE_READ_POLICY_PATH = WORKSPACE / "configs/agent_zero/live_read_policy.json"


class LiveReadSurface(str, Enum):
    MOLTBOOK = "moltbook"
    FOURCLAW = "fourclaw"


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_live_read_policy() -> dict[str, Any]:
    if LIVE_READ_POLICY_PATH.is_file():
        return json.loads(LIVE_READ_POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def live_read_enabled() -> bool:
    """Live read requires explicit enablement."""
    if _truthy(os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES")):
        return False
    return _truthy(os.environ.get("HG_ENABLE_LIVE_SOCIAL_READ")) or _truthy(
        os.environ.get("HG_SOCIAL_LIVE_READ")
    )


def live_writes_disabled() -> bool:
    publish = os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower()
    reply = os.environ.get("HG_SOCIAL_LIVE_REPLY", "false").lower()
    writes = os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower()
    return not (_truthy(publish) or _truthy(reply) or _truthy(writes))


def credential_status_for_surface(surface: LiveReadSurface) -> LiveReadCredentialStatus:
    if surface == LiveReadSurface.MOLTBOOK:
        from hg_platforms.moltbook.moltbook_api_client import moltbook_token_configured

        if moltbook_token_configured():
            return LiveReadCredentialStatus.CREDENTIALS_PRESENT
        return LiveReadCredentialStatus.CREDENTIALS_MISSING
    if surface == LiveReadSurface.FOURCLAW:
        from hg_platforms.fourclaw.fourclaw_api_client import fourclaw_token_configured

        if fourclaw_token_configured():
            return LiveReadCredentialStatus.CREDENTIALS_PRESENT
        return LiveReadCredentialStatus.CREDENTIALS_MISSING
    return LiveReadCredentialStatus.CREDENTIALS_UNCHECKED


@dataclass
class LiveReadItem:
    source_ref: str
    surface: str
    item_kind: str
    observed_at: str
    body_preview: str
    body_hash: str
    author_ref: str | None = None
    thread_ref: str | None = None
    created_at: str | None = None
    title: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "surface": self.surface,
            "item_kind": self.item_kind,
            "author_ref": self.author_ref,
            "thread_ref": self.thread_ref,
            "created_at": self.created_at,
            "observed_at": self.observed_at,
            "title": self.title,
            "body_preview": self.body_preview,
            "body_hash": self.body_hash,
            "url": self.url,
            "metadata": self.metadata,
        }


@dataclass
class LiveReadRequest:
    request_id: str
    surface: LiveReadSurface
    limit: int = 20
    operator: str = "local-operator"

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "surface": self.surface.value,
            "limit": self.limit,
            "operator": self.operator,
        }


@dataclass
class LiveReadResult:
    request_id: str
    surface: str
    items: list[LiveReadItem]
    receipt: LiveReadReceipt
    verdict: LiveReadVerdict
    credential_status: LiveReadCredentialStatus
    data_tier: str = "LIVE"
    not_autonomous_cognition: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "surface": self.surface,
            "items": [i.to_payload() for i in self.items],
            "receipt": self.receipt.to_payload(),
            "verdict": self.verdict.value,
            "credential_status": self.credential_status.value,
            "data_tier": self.data_tier,
            "not_autonomous_cognition": self.not_autonomous_cognition,
            "success": verdict_counts_as_success(self.verdict),
        }


def _disabled_result(request: LiveReadRequest, *, runtime_mode: str, fixture_mode: bool) -> LiveReadResult:
    started = _now_iso()
    cred = LiveReadCredentialStatus.CREDENTIALS_REDACTED
    receipt = build_live_read_receipt(
        request_id=request.request_id,
        surface=request.surface.value,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=cred,
        api_called=False,
        api_call_kind="none",
        item_count=0,
        source_refs=[],
        read_started_at=started,
        read_finished_at=started,
        latency_ms=0,
        verdict=LiveReadVerdict.YELLOW_LIVE_READ_DISABLED,
        error="HG_ENABLE_LIVE_SOCIAL_READ not enabled",
    )
    return LiveReadResult(
        request_id=request.request_id,
        surface=request.surface.value,
        items=[],
        receipt=receipt,
        verdict=LiveReadVerdict.YELLOW_LIVE_READ_DISABLED,
        credential_status=cred,
    )


def _credentials_missing_result(
    request: LiveReadRequest,
    *,
    runtime_mode: str,
    fixture_mode: bool,
    cred: LiveReadCredentialStatus,
) -> LiveReadResult:
    started = _now_iso()
    receipt = build_live_read_receipt(
        request_id=request.request_id,
        surface=request.surface.value,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=cred,
        api_called=False,
        api_call_kind="none",
        item_count=0,
        source_refs=[],
        read_started_at=started,
        read_finished_at=started,
        latency_ms=0,
        verdict=LiveReadVerdict.YELLOW_CREDENTIALS_MISSING,
        error="credentials missing for live read",
    )
    return LiveReadResult(
        request_id=request.request_id,
        surface=request.surface.value,
        items=[],
        receipt=receipt,
        verdict=LiveReadVerdict.YELLOW_CREDENTIALS_MISSING,
        credential_status=cred,
    )


def _map_api_error(error: str, request: LiveReadRequest, *, runtime_mode: str, fixture_mode: bool, cred: LiveReadCredentialStatus, started: str, t0: float) -> LiveReadResult:
    finished = _now_iso()
    latency = int((time.monotonic() - t0) * 1000)
    if error == "credentials_missing":
        verdict = LiveReadVerdict.YELLOW_CREDENTIALS_MISSING
        cred = LiveReadCredentialStatus.CREDENTIALS_MISSING
    elif error == "credentials_invalid":
        verdict = LiveReadVerdict.YELLOW_CREDENTIALS_INVALID
        cred = LiveReadCredentialStatus.CREDENTIALS_INVALID
    elif error == "rate_limited":
        verdict = LiveReadVerdict.YELLOW_LIVE_API_RATE_LIMITED
    else:
        verdict = LiveReadVerdict.YELLOW_LIVE_API_UNREACHABLE
    receipt = build_live_read_receipt(
        request_id=request.request_id,
        surface=request.surface.value,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=cred,
        api_called=True,
        api_call_kind="GET",
        item_count=0,
        source_refs=[],
        read_started_at=started,
        read_finished_at=finished,
        latency_ms=latency,
        verdict=verdict,
        error=error,
    )
    return LiveReadResult(
        request_id=request.request_id,
        surface=request.surface.value,
        items=[],
        receipt=receipt,
        verdict=verdict,
        credential_status=cred,
    )


def read_moltbook_live(
    request: LiveReadRequest,
    *,
    fetcher: Callable[..., dict[str, Any]] | None = None,
) -> LiveReadResult:
    """Read Moltbook feed — read-only GET."""
    mode_receipt = resolve_runtime_mode()
    runtime_mode = mode_receipt.runtime_mode.value
    fixture_mode = is_fixture_mode()

    if fixture_mode and not live_read_enabled():
        receipt = build_live_read_receipt(
            request_id=request.request_id,
            surface=request.surface.value,
            runtime_mode=runtime_mode,
            fixture_mode=True,
            credential_status=LiveReadCredentialStatus.CREDENTIALS_UNCHECKED,
            api_called=False,
            api_call_kind="none",
            item_count=0,
            source_refs=[],
            read_started_at=_now_iso(),
            read_finished_at=_now_iso(),
            latency_ms=0,
            verdict=LiveReadVerdict.RED_FIXTURE_FEED_USED_IN_RUNTIME,
            error="fixture mode cannot masquerade as live read",
        )
        return LiveReadResult(
            request_id=request.request_id,
            surface=request.surface.value,
            items=[],
            receipt=receipt,
            verdict=LiveReadVerdict.RED_FIXTURE_FEED_USED_IN_RUNTIME,
            credential_status=LiveReadCredentialStatus.CREDENTIALS_UNCHECKED,
        )

    if not live_read_enabled():
        return _disabled_result(request, runtime_mode=runtime_mode, fixture_mode=fixture_mode)

    cred = credential_status_for_surface(LiveReadSurface.MOLTBOOK)
    if cred == LiveReadCredentialStatus.CREDENTIALS_MISSING:
        return _credentials_missing_result(
            request, runtime_mode=runtime_mode, fixture_mode=fixture_mode, cred=cred
        )

    if fetcher is None:
        from hg_platforms.moltbook.fetch_moltbook_feed import fetch_moltbook_feed

        fetcher = fetch_moltbook_feed

    started = _now_iso()
    t0 = time.monotonic()
    api_result = fetcher(limit=request.limit)
    if not api_result.get("ok"):
        return _map_api_error(
            str(api_result.get("error", "unreachable")),
            request,
            runtime_mode=runtime_mode,
            fixture_mode=fixture_mode,
            cred=cred,
            started=started,
            t0=t0,
        )

    posts = api_result.get("posts") or []
    observed = _now_iso()
    items: list[LiveReadItem] = []
    refs: list[str] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        post_id = str(post.get("id") or post.get("post_id") or uuid.uuid4().hex[:12])
        body = str(post.get("content") or post.get("text") or post.get("body") or "")
        ref = moltbook_post_ref(post_id)
        refs.append(ref)
        items.append(
            LiveReadItem(
                source_ref=ref,
                surface=LiveReadSurface.MOLTBOOK.value,
                item_kind="post",
                author_ref=str(post.get("author") or post.get("author_id") or "") or None,
                created_at=str(post.get("created_at") or "") or None,
                observed_at=observed,
                title=str(post.get("title") or "") or None,
                body_preview=truncate_preview(body),
                body_hash=body_preview_hash(body),
                url=str(post.get("url") or "") or None,
                metadata={"http_status": api_result.get("http_status")},
            )
        )

    finished = _now_iso()
    latency = int((time.monotonic() - t0) * 1000)
    if not items:
        verdict = LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED
    else:
        verdict = LiveReadVerdict.GREEN_LIVE_READ_OK

    receipt = build_live_read_receipt(
        request_id=request.request_id,
        surface=request.surface.value,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
        api_called=True,
        api_call_kind="GET feed",
        item_count=len(items),
        source_refs=refs,
        read_started_at=started,
        read_finished_at=finished,
        latency_ms=latency,
        verdict=verdict,
    )
    validate_live_read_receipt(receipt)
    return LiveReadResult(
        request_id=request.request_id,
        surface=request.surface.value,
        items=items,
        receipt=receipt,
        verdict=verdict,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
    )


def read_fourclaw_live(
    request: LiveReadRequest,
    *,
    fetcher: Callable[..., dict[str, Any]] | None = None,
) -> LiveReadResult:
    """Read Fourclaw threads — read-only GET."""
    mode_receipt = resolve_runtime_mode()
    runtime_mode = mode_receipt.runtime_mode.value
    fixture_mode = is_fixture_mode()

    if not live_read_enabled():
        return _disabled_result(request, runtime_mode=runtime_mode, fixture_mode=fixture_mode)

    cred = credential_status_for_surface(LiveReadSurface.FOURCLAW)
    if cred == LiveReadCredentialStatus.CREDENTIALS_MISSING:
        return _credentials_missing_result(
            request, runtime_mode=runtime_mode, fixture_mode=fixture_mode, cred=cred
        )

    if fetcher is None:
        from hg_platforms.fourclaw.list_fourclaw_threads import list_fourclaw_threads

        fetcher = list_fourclaw_threads

    started = _now_iso()
    t0 = time.monotonic()
    api_result = fetcher(limit=request.limit, include_content=True)
    if not api_result.get("ok"):
        return _map_api_error(
            str(api_result.get("error", "unreachable")),
            request,
            runtime_mode=runtime_mode,
            fixture_mode=fixture_mode,
            cred=cred,
            started=started,
            t0=t0,
        )

    threads = api_result.get("threads") or []
    observed = _now_iso()
    items: list[LiveReadItem] = []
    refs: list[str] = []
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        thread_id = str(thread.get("id") or thread.get("thread_id") or uuid.uuid4().hex[:12])
        body = str(thread.get("content") or thread.get("op") or thread.get("body") or thread.get("title") or "")
        ref = fourclaw_thread_ref(thread_id)
        refs.append(ref)
        items.append(
            LiveReadItem(
                source_ref=ref,
                surface=LiveReadSurface.FOURCLAW.value,
                item_kind="thread",
                author_ref=str(thread.get("author") or "") or None,
                thread_ref=thread_id,
                created_at=str(thread.get("created_at") or "") or None,
                observed_at=observed,
                title=str(thread.get("title") or "") or None,
                body_preview=truncate_preview(body),
                body_hash=body_preview_hash(body),
                url=str(thread.get("url") or "") or None,
                metadata={"board": api_result.get("board")},
            )
        )

    finished = _now_iso()
    latency = int((time.monotonic() - t0) * 1000)
    verdict = LiveReadVerdict.GREEN_LIVE_READ_OK if items else LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED
    receipt = build_live_read_receipt(
        request_id=request.request_id,
        surface=request.surface.value,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
        api_called=True,
        api_call_kind="GET threads",
        item_count=len(items),
        source_refs=refs,
        read_started_at=started,
        read_finished_at=finished,
        latency_ms=latency,
        verdict=verdict,
    )
    validate_live_read_receipt(receipt)
    return LiveReadResult(
        request_id=request.request_id,
        surface=request.surface.value,
        items=items,
        receipt=receipt,
        verdict=verdict,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_REDACTED,
    )


def read_surface_live(
    surface: str | LiveReadSurface,
    *,
    request_id: str | None = None,
    limit: int = 20,
    moltbook_fetcher: Callable[..., dict[str, Any]] | None = None,
    fourclaw_fetcher: Callable[..., dict[str, Any]] | None = None,
) -> LiveReadResult:
    """Dispatch live read by surface name."""
    surf = surface if isinstance(surface, LiveReadSurface) else LiveReadSurface(str(surface).lower())
    req = LiveReadRequest(
        request_id=request_id or f"live-read-req-{uuid.uuid4().hex[:12]}",
        surface=surf,
        limit=limit,
    )
    if surf == LiveReadSurface.MOLTBOOK:
        return read_moltbook_live(req, fetcher=moltbook_fetcher)
    if surf == LiveReadSurface.FOURCLAW:
        return read_fourclaw_live(req, fetcher=fourclaw_fetcher)
    started = _now_iso()
    receipt = build_live_read_receipt(
        request_id=req.request_id,
        surface=str(surface),
        runtime_mode=resolve_runtime_mode().runtime_mode.value,
        fixture_mode=is_fixture_mode(),
        credential_status=LiveReadCredentialStatus.CREDENTIALS_UNCHECKED,
        api_called=False,
        api_call_kind="none",
        item_count=0,
        source_refs=[],
        read_started_at=started,
        read_finished_at=started,
        latency_ms=0,
        verdict=LiveReadVerdict.YELLOW_LIVE_API_UNREACHABLE,
        error=f"unknown surface: {surface}",
    )
    return LiveReadResult(
        request_id=req.request_id,
        surface=str(surface),
        items=[],
        receipt=receipt,
        verdict=LiveReadVerdict.YELLOW_LIVE_API_UNREACHABLE,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_UNCHECKED,
    )


__all__ = [
    "LiveReadItem",
    "LiveReadRequest",
    "LiveReadResult",
    "LiveReadSurface",
    "credential_status_for_surface",
    "live_read_enabled",
    "live_writes_disabled",
    "load_live_read_policy",
    "read_fourclaw_live",
    "read_moltbook_live",
    "read_surface_live",
]

"""
Deterministic local stub adapter.

Used for safe-local validation and replay-style demo flows when paid providers must be unreachable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, AsyncIterator, Dict, Iterable, List

from hg_llm.abstraction import CompletionRequest, CompletionResponse


def _last_user_content(messages: Iterable[Dict[str, Any]]) -> str:
    for message in reversed(list(messages)):
        if str(message.get("role") or "").lower() == "user":
            return str(message.get("content") or "").strip()
    return ""


def _scenario_from_request(request: CompletionRequest) -> str:
    extra = request.extra or {}
    scenario = str(extra.get("scenario") or extra.get("demo_scenario") or "").strip().lower()
    if scenario:
        return scenario
    prompt = _last_user_content(request.messages).lower()
    if any(token in prompt for token in ("recover", "retry", "cancel", "rollback")):
        return "recovery"
    if any(token in prompt for token in ("approve", "reject", "escalate")):
        return "approval"
    if any(token in prompt for token in ("reflection", "reflect", "review artifact")):
        return "reflection"
    if any(token in prompt for token in ("provenance", "why this reply", "why did", "source")):
        return "provenance"
    if any(token in prompt for token in ("workflow", "run", "launch", "dag")):
        return "workflow"
    if any(token in prompt for token in ("drift", "mimic", "governance", "continuity")):
        return "governance"
    return "chat"


def _stable_suffix(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:8]


def _build_content(request: CompletionRequest) -> str:
    scenario = _scenario_from_request(request)
    user = _last_user_content(request.messages) or "No user message provided."
    suffix = _stable_suffix(json.dumps(request.extra or {}, sort_keys=True, default=str) + "\n" + user + "\n" + request.model)
    if scenario == "workflow":
        return (
            "Stub workflow result: the run launched, the timeline was updated, and the next action is to open run detail. "
            f"Anchor: {suffix}."
        )
    if scenario == "provenance":
        return (
            "Stub provenance result: the reply is linked to the source memory, policy input, and evidence trail. "
            f"Anchor: {suffix}."
        )
    if scenario == "reflection":
        return (
            "Stub reflection result: the artifact is ready for review with promote, discard, or escalate actions. "
            f"Anchor: {suffix}."
        )
    if scenario == "recovery":
        return (
            "Stub recovery result: the action is anchored in the main timeline and the operator can continue from the recovery view. "
            f"Anchor: {suffix}."
        )
    if scenario == "approval":
        return (
            "Stub approval result: the decision is visible, the linked item is updated, and the review trail remains intact. "
            f"Anchor: {suffix}."
        )
    if scenario == "governance":
        return (
            "Stub governance result: drift, mimicry, and continuity state are visible and ready for operator review. "
            f"Anchor: {suffix}."
        )
    return f"Stub local reply: {user} (anchor {suffix})."


class StubCompletionAdapter:
    """Deterministic adapter for safe-local validation and replay."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        content = _build_content(request)
        tokens = max(1, len(content.split()))
        return CompletionResponse(
            content=content,
            usage={"prompt_tokens": max(1, len(" ".join(str(m.get("content") or "") for m in request.messages).split())), "completion_tokens": tokens, "total_tokens": tokens},
            model=request.model or "local-deterministic",
            finish_reason="stop",
        )

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        content = self.complete(request).content
        chunk_size = max(24, len(content) // 3 or 1)
        for idx in range(0, len(content), chunk_size):
            yield content[idx : idx + chunk_size]

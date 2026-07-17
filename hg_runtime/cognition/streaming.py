"""Streaming cognition adapter — tokens and proposals as RTC event drafts."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Mapping

from hg_core.ledger.canonical_json import canonical_dumps
from hg_runtime.cognition.provider import (
    CognitionCancelled,
    CognitionPrompt,
    CognitionTimeout,
    ModelProvider,
)
from hg_runtime.contract import draft, stable_id

# Terminal proposal events passed to the decision pipeline (not stream deltas).
COGNITION_DECISION_PROPOSAL_TYPES = frozenset({
    "PROPOSAL_EMITTED",
    "MODEL_PROPOSAL_RECORDED",
})


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_dumps(_json_safe(value))).hexdigest()


def build_prompt(context: Mapping[str, Any]) -> CognitionPrompt:
    events = list(context.get("events", []))
    if not events:
        raise ValueError("cognition context requires at least one event")
    trigger = events[0]
    trigger_type = str(trigger.get("type", "UNKNOWN"))
    trigger_event_id = str(trigger["event_id"])
    payload = trigger.get("payload", {})
    user_text = ""
    if isinstance(payload, Mapping):
        user_text = str(payload.get("content") or payload.get("summary") or trigger_type)
    messages = (
        {
            "role": "system",
            "content": (
                "You are a proposal-only cognition service. Emit JSON proposals only. "
                "You have no tools and no execution authority."
            ),
        },
        {"role": "user", "content": user_text},
    )
    request_body = {
        "messages": messages,
        "trigger_event_id": trigger_event_id,
        "trigger_type": trigger_type,
        "memory": context.get("memory", {}),
        "arousal": context.get("arousal", {}),
    }
    return CognitionPrompt(
        messages=messages,
        trigger_event_id=trigger_event_id,
        trigger_type=trigger_type,
        request_digest=_digest(request_body),
    )


def parse_proposal_text(text: str) -> tuple[str, Dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return "interpretation", {"text": ""}
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return "reply_draft", {"text": stripped}
    if not isinstance(data, dict):
        return "reply_draft", {"text": stripped}
    kind = str(data.get("kind") or "interpretation")
    content = data.get("content", data)
    if not isinstance(content, dict):
        content = {"text": str(content)}
    return kind, content


def _stream_failed_draft(
    *,
    stream_id: str,
    proposal_id: str,
    reason: str,
    trigger_event_id: str,
    causal: list[str],
    detail: str | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "stream_id": stream_id,
        "proposal_id": proposal_id,
        "reason": reason,
        "event_refs": [trigger_event_id],
    }
    if detail:
        payload["detail"] = detail[:500]
    return draft("MODEL_STREAM_FAILED", payload, causal_parents=causal)


def stream_proposal_drafts(
    provider: ModelProvider,
    context: Mapping[str, Any],
    *,
    cancel_check,
    timeout_s: float,
    params: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Return MODEL_* drafts. Never raises — failures become MODEL_STREAM_FAILED."""
    events = list(context.get("events", []))
    if not events:
        return []
    trigger = events[0]
    prompt = build_prompt(context)
    proposal_id = stable_id("prop", prompt.trigger_event_id, prompt.request_digest)
    model_label = f"{provider.model_name}@{provider.provider_id}"
    stream_id = stable_id("pstream", proposal_id)
    causal = [prompt.trigger_event_id]
    params_payload = dict(params or {})
    max_tokens = int(params_payload.get("max_tokens") or 0)
    drafts: List[Dict[str, Any]] = [
        draft(
            "MODEL_STREAM_STARTED",
            {
                "stream_id": stream_id,
                "proposal_id": proposal_id,
                "model": model_label,
                "request_digest": prompt.request_digest,
                "trigger_event_id": prompt.trigger_event_id,
            },
            causal_parents=causal,
        )
    ]
    deadline = time.monotonic() + max(0.0, float(timeout_s))
    parts: list[str] = []
    try:
        for index, token in enumerate(
            provider.stream_tokens(
                prompt,
                cancel_check=cancel_check,
                deadline_monotonic=deadline,
            )
        ):
            parts.append(token)
            drafts.append(
                draft(
                    "MODEL_TOKEN_DELTA",
                    {
                        "stream_id": stream_id,
                        "proposal_id": proposal_id,
                        "token_index": index,
                        "token": token,
                    },
                    causal_parents=causal,
                )
            )
            if max_tokens > 0 and len(parts) >= max_tokens:
                break
        drafts.append(
            draft(
                "MODEL_STREAM_COMPLETED",
                {
                    "stream_id": stream_id,
                    "proposal_id": proposal_id,
                    "token_count": len(parts),
                    "model": model_label,
                },
                causal_parents=causal,
            )
        )
        full_text = "".join(parts)
        kind, content = parse_proposal_text(full_text)
        response_digest = _digest({"text": full_text, "kind": kind, "content": content})
        drafts.append(
            draft(
                "MODEL_PROPOSAL_RECORDED",
                {
                    "proposal_id": proposal_id,
                    "stream_id": stream_id,
                    "kind": kind,
                    "content": content,
                    "model": model_label,
                    "request_digest": prompt.request_digest,
                    "response_digest": response_digest,
                    "params": params_payload,
                    "token_count": len(parts),
                    "assembled_text": full_text,
                },
                causal_parents=causal,
            )
        )
        return drafts
    except CognitionCancelled:
        return drafts + [
            _stream_failed_draft(
                stream_id=stream_id,
                proposal_id=proposal_id,
                reason="cancelled",
                trigger_event_id=trigger["event_id"],
                causal=causal,
            )
        ]
    except CognitionTimeout:
        return drafts + [
            _stream_failed_draft(
                stream_id=stream_id,
                proposal_id=proposal_id,
                reason="timeout",
                trigger_event_id=trigger["event_id"],
                causal=causal,
            )
        ]
    except Exception as exc:
        return drafts + [
            _stream_failed_draft(
                stream_id=stream_id,
                proposal_id=proposal_id,
                reason=type(exc).__name__,
                trigger_event_id=trigger["event_id"],
                causal=causal,
                detail=str(exc),
            )
        ]


__all__ = [
    "COGNITION_DECISION_PROPOSAL_TYPES",
    "build_prompt",
    "parse_proposal_text",
    "stream_proposal_drafts",
]

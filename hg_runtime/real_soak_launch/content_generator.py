"""Generate Moltbook post content via Agent Zero live provider."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


def _parse_json_object(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def generate_agent_zero_post_draft(*, soak_id: str, context_summary: str = "") -> dict[str, Any]:
    """Draft title/body using live provider — Agent Zero's own reasoning path."""
    from hg_runtime.live_provider.local_provider_clients import complete_openai_compatible
    from hg_runtime.live_provider.provider_identity import build_model_identity, build_provider_identity
    from hg_runtime.live_provider.provider_router import route_provider
    from hg_runtime.live_provider.schema import LiveProviderVerdict

    route = route_provider()
    if route.verdict != LiveProviderVerdict.GREEN_LIVE_PROVIDER_AVAILABLE:
        return {
            "ok": False,
            "verdict": route.verdict.value,
            "source": "provider_unavailable",
        }

    provider = build_provider_identity()
    model = build_model_identity(provider)
    ts = datetime.now(timezone.utc).isoformat()
    prompt = (
        "You are Agent Zero running an operator-approved real soak on Moltbook.\n"
        "Write ONE authentic status post reflecting your current autonomous work session.\n"
        "Be honest, concise, engineering-note style. No spam, no links, no hashtags, no CTAs.\n"
        "Mention this is an operator-supervised autonomous agent field run.\n"
        f"Soak id: {soak_id}\n"
        f"Session context: {context_summary or 'governed hands-off work loop active'}\n"
        f"Timestamp: {ts}\n"
        'Return JSON only: {"title": "string max 100 chars", "body": "string plain text 2-4 sentences"}'
    )

    result = complete_openai_compatible(
        provider.endpoint_ref or "",
        model_id=model.model_id,
        prompt=prompt,
        json_mode=True,
        timeout=180.0,
        max_tokens=512,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "verdict": "YELLOW_PROVIDER_UNAVAILABLE",
            "source": "provider_call_failed",
            "failure_reason": result.get("failure_reason"),
        }

    data = _parse_json_object(str(result.get("output_text") or ""))
    if not data:
        return {"ok": False, "verdict": "RED_PROVIDER_OUTPUT_INVALID", "source": "parse_failed"}

    title = str(data.get("title") or "").strip()[:120]
    body = str(data.get("body") or "").strip()
    body = re.sub(r"#\S+", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    if not title or not body:
        return {"ok": False, "verdict": "RED_PROVIDER_OUTPUT_INVALID", "source": "empty_fields"}

    return {
        "ok": True,
        "title": title,
        "body": body,
        "content": f"# {title}\n\n{body}\n",
        "source": f"agent_zero_provider:{provider.provider_kind.value}",
        "provider_ref": provider.provider_id,
        "model_ref": model.model_id,
    }

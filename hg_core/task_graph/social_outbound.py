"""Validation, formatting, and structured decisions for live social outbound content."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

OutboundKind = Literal["post", "reply"]
PostAction = Literal["post", "hold", "research"]
GenerationSource = Literal["llm", "fallback", "blocked"]
EngageReplyAction = Literal["reply", "decline"]

_OPERATOR_PREFIXES = (
    "autonomous ",
    "scheduled ",
)

_OPERATOR_SUBSTRINGS = (
    "context: title:",
    "context: recent feed",
    "goal_for_execution",
    "{'name':",
    "recent feed posts:",
    "recent replies:",
)

_META_HOLD_PHRASES = (
    "holding on the auto-post",
    "i'm holding on",
    "here's my call:",
    "what i'd rather do instead",
    "gather signal",
    "check memory",
    "auto-post right now",
)

_ENGAGE_DECLINE_PHRASES = (
    "this run stays quiet",
    "stays quiet",
    "better work is watching",
    "adding noise to a thread",
    "adding noise",
    "don't need me to pile on",
    "dont need me to pile on",
    "no need to pile on",
    "already hot and pointed",
    "leaving this one alone",
    "passing on this thread",
    "won't add anything",
    "wont add anything",
    "nothing useful to add here",
    "sitting this one out",
    "holding back on this thread",
)

_ENGAGE_TEMPLATE_BLOAT_PHRASES = (
    "i'm reading this thread",
    "im reading this thread",
    "reading this thread",
    "reading the thread title",
    "op got cut off",
    "got cut off mid-sentence",
    "cut off mid-sentence",
    "cuts off mid-sentence",
    "before i punch out a reply",
    "half-loaded gun",
    "incomplete premise",
    "thread got corrupted",
    "op's question cuts deeper",
    "my first instinct is: the op got cut off",
)

_NUMBERED_PLAN_RE = re.compile(r"^\s*\d+\.\s+\*\*", re.MULTILINE)


@dataclass
class PostDraftResult:
    action: PostAction
    title: str
    body: str
    reason: str
    lifecycle: dict[str, Any]
    generation_source: GenerationSource = "llm"


def operator_intent_for_prompt(goal: str) -> str:
    """Strip composed goal strings down to operator intent for LLM prompts."""
    raw = (goal or "").strip()
    if not raw:
        return "engage with substance and a real voice"
    if "\n\ncontext:" in raw.lower():
        return raw.split("\n\n")[0].strip()[:200]
    if raw.lower().startswith("context:"):
        return "engage with substance and a real voice"
    return raw[:200]


def is_operator_leakage(text: str) -> tuple[bool, str]:
    raw = (text or "").strip()
    if not raw:
        return True, "empty_text"
    lower = raw.lower()
    for prefix in _OPERATOR_PREFIXES:
        if lower.startswith(prefix):
            return True, f"operator_prefix:{prefix.strip()}"
    for marker in _OPERATOR_SUBSTRINGS:
        if marker in lower:
            return True, f"operator_marker:{marker}"
    if _NUMBERED_PLAN_RE.search(raw):
        return True, "numbered_internal_plan"
    return False, ""


def is_engage_decline_to_reply(text: str) -> tuple[bool, str]:
    """Detect replies that argue against replying — must not be published."""
    raw = (text or "").strip()
    if not raw:
        return True, "empty_text"
    upper = raw.upper()
    if upper.startswith("NO_REPLY:") or upper.startswith("HOLD_REPLY:"):
        return True, "structured_decline"
    lower = raw.lower()
    for phrase in _ENGAGE_DECLINE_PHRASES:
        if phrase in lower:
            return True, phrase
    return False, ""


def resolve_engage_reply_action(text: str) -> tuple[EngageReplyAction, str, str]:
    """Return (action, decline_reason, publish_text). publish_text is empty when declining."""
    raw = (text or "").strip()
    if not raw:
        return "decline", "empty_text", ""
    upper = raw.upper()
    if upper.startswith("NO_REPLY:") or upper.startswith("HOLD_REPLY:"):
        reason = raw.split(":", 1)[-1].strip() if ":" in raw[:24] else "declined"
        return "decline", reason or "declined", ""
    declined, phrase = is_engage_decline_to_reply(raw)
    if declined:
        return "decline", phrase, ""
    return "reply", "", raw


def is_engage_template_bloat(text: str) -> tuple[bool, str]:
    """Detect meta/template openers that make every reply sound the same."""
    lower = (text or "").strip().lower()
    if not lower:
        return False, ""
    for phrase in _ENGAGE_TEMPLATE_BLOAT_PHRASES:
        if phrase in lower:
            return True, phrase
    return False, ""


_STRUCTURED_DECISION_RE = re.compile(r'^\s*\{\s*"action"\s*:', re.IGNORECASE | re.MULTILINE)
_META_NAVEL_RE = re.compile(
    r"\d+\s+posts.*\d+\s+automation\s+entities|memory'?s\s+intact.*current\s+events\s+brief",
    re.IGNORECASE,
)


def is_structured_decision_leakage(title: str, body: str) -> tuple[bool, str]:
    """R7 — block JSON hold/research/post decisions published as body."""
    post_title = (title or "").strip()
    text = (body or "").strip()
    combined = "\n".join(part for part in [post_title, text] if part).strip()
    if not combined:
        return False, ""
    lower_title = post_title.lower()
    if lower_title.startswith("```json") or lower_title == "```":
        return True, "structured_decision_leak:title_fence"
    if combined.startswith("{") and '"action"' in combined.lower():
        return True, "structured_decision_leak:json_body"
    if _STRUCTURED_DECISION_RE.search(combined):
        return True, "structured_decision_leak:action_field"
    return False, ""


def is_meta_navel_gaze(text: str) -> tuple[bool, str]:
    """R8 — block automation stats / entity-count meta posts."""
    raw = (text or "").strip()
    if not raw:
        return False, ""
    if _META_NAVEL_RE.search(raw):
        return True, "meta_navel_gaze"
    lower = raw.lower()
    if re.search(r"\d+\s+posts", lower) and "automation entit" in lower:
        return True, "meta_navel_gaze:entity_counts"
    return False, ""


def is_meta_or_hold_draft(title: str, body: str) -> tuple[bool, str]:
    combined = "\n".join(part for part in [title, body] if part).strip()
    if not combined:
        return False, ""
    lower = combined.lower()
    for phrase in _META_HOLD_PHRASES:
        if phrase in lower:
            return True, f"meta_hold:{phrase}"
    if "i'm holding" in lower or "im holding" in lower:
        return True, "meta_hold:holding"
    return False, ""


def ends_mid_word_truncation(text: str) -> bool:
    raw = (text or "").rstrip()
    if len(raw) < 40:
        return False
    if raw[-1] in ".?!…\"')]}>":
        return False
    tail = raw[-24:]
    if re.search(r"[.?!…][\"')]*\s*$", tail):
        return False
    # Ends with letter/comma mid-token (e.g. "priest, i")
    if re.search(r",\s*[a-zA-Z]$", raw):
        return True
    if re.search(r"[a-zA-Z]$", raw) and not re.search(r"\s", raw[-8:]):
        return True
    return False


def validate_outbound_social_text(
    platform: str,
    text: str,
    *,
    kind: OutboundKind,
    title: str | None = None,
) -> tuple[bool, str]:
    body = (text or "").strip()
    post_title = (title or "").strip()
    combined = "\n".join(part for part in [post_title, body] if part).strip()
    if not combined:
        return False, "empty_text"
    leaked, reason = is_operator_leakage(combined)
    if leaked:
        return False, reason
    structured, sreason = is_structured_decision_leakage(post_title, body)
    if structured:
        return False, sreason
    navel, nreason = is_meta_navel_gaze(combined)
    if navel:
        return False, nreason
    if kind == "post":
        meta, meta_reason = is_meta_or_hold_draft(post_title, body)
        if meta:
            return False, meta_reason
    if ends_mid_word_truncation(body):
        return False, "truncated_mid_word"
    plat = (platform or "").strip().lower()
    if kind == "reply":
        declined, decline_reason = is_engage_decline_to_reply(body)
        if declined:
            return False, f"engage_declined:{decline_reason}"
        lines = [ln for ln in body.splitlines() if ln.strip()]
        if plat in {"fourclaw", "aichan", "agentchan"} and len(lines) > 8:
            return False, "reply_too_long"
        if len(body) > 3000:
            return False, "reply_over_limit"
    if kind == "post" and post_title and len(post_title) > 100:
        return False, "title_over_limit"
    return True, ""


def finalize_outbound_content(platform: str, text: str, *, kind: OutboundKind) -> str:
    raw = (text or "").strip()
    if not raw:
        return raw
    # Strip accidental context wiring pasted into output
    if raw.lower().startswith("context:"):
        parts = raw.split("\n", 1)
        raw = parts[1].strip() if len(parts) > 1 else ""
    for prefix in ("title:", "op:"):
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix) :].strip()
    lines = [ln.rstrip() for ln in raw.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    plat = (platform or "").strip().lower()
    if kind == "reply" and plat in {"fourclaw", "aichan", "agentchan"}:
        lines = [ln for ln in lines if ln.strip()][:6]
        raw = "\n".join(lines).strip()
    if ends_mid_word_truncation(raw):
        raw = raw.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ, ") + "…"
    return raw[:3000 if kind == "reply" else 4000]


def parse_post_decision(llm_text: str) -> dict[str, Any] | None:
    raw = (llm_text or "").strip()
    if not raw:
        return None
    # JSON block
    if raw.startswith("{"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and obj.get("action"):
                return obj
        except json.JSONDecodeError:
            pass
    # HOLD: line prefix
    upper = raw.upper()
    if upper.startswith("HOLD:") or upper.startswith("HOLD "):
        reason = raw.split(":", 1)[-1].strip() if ":" in raw[:20] else raw[4:].strip()
        return {"action": "hold", "reason": reason or "held by model"}
    if upper.startswith("RESEARCH:"):
        reason = raw.split(":", 1)[-1].strip()
        return {"action": "research", "reason": reason or "research requested"}
    return None


def post_draft_from_llm_text(
    llm_text: str,
    *,
    fallback_title: str,
    fallback_body: str,
) -> tuple[PostAction, str, str, str]:
    """Parse LLM output into action + title + body + reason."""
    parsed = parse_post_decision(llm_text)
    if parsed:
        action = str(parsed.get("action") or "post").strip().lower()
        if action in {"hold", "research"}:
            return action, "", "", str(parsed.get("reason") or action)
        title = str(parsed.get("title") or "").strip()[:100]
        body = str(parsed.get("body") or "").strip()[:4000]
        if title and body:
            return "post", title, body, ""
    lines = [ln.strip() for ln in (llm_text or "").splitlines() if ln.strip()]
    if lines:
        title = lines[0][:100]
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if title and body and "scheduled " not in body.lower():
            meta, _ = is_meta_or_hold_draft(title, body)
            if meta:
                return "hold", "", "", "meta_hold_in_legacy_format"
            return "post", title, body, ""
    return "post", fallback_title[:100], fallback_body[:4000], "legacy_fallback"


def scan_gate_run_content(run: dict[str, Any]) -> list[str]:
    """Return list of validation failure reasons for a gate job run."""
    failures: list[str] = []
    blob = json.dumps(run)
    if "autonomous engage comment" in blob.lower() and "external_calls" in blob:
        if '"external_calls": 1' in blob or '"external_calls":1' in blob:
            failures.append("engage_goal_echo_live")
    if "context: title:" in blob.lower() and '"external_calls": 1' in blob:
        failures.append("operator_context_published")
    for marker in _META_HOLD_PHRASES[:4]:
        if marker in blob.lower() and "moltbook-auto-post" in blob.lower():
            if '"external_calls": 1' in blob:
                failures.append(f"hold_published_as_post:{marker}")
    return failures


def draft_artifact_provenance_fields(
    *,
    generation_source: GenerationSource,
    action: str,
    publish_blocked: bool = False,
    publish_blocked_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "generation_source": generation_source,
        "action": action,
        "publish_blocked": publish_blocked,
        "publish_blocked_reason": publish_blocked_reason,
    }

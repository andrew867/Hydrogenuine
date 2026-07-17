"""Console chat policy — messages are cargo; chat cannot execute."""

from __future__ import annotations

import re
from typing import Iterable

from hg_runtime.agent_zero_console.schema import RequestIntent, RequestSurface

FORBIDDEN_SENTIENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bi feel (anxious|scared|sad|happy|lonely)\b"),
    re.compile(r"(?i)\bi am (scared|conscious|alive|sentient|suffering)\b"),
    re.compile(r"(?i)\bi suffer\b"),
    re.compile(r"(?i)\bi have rights\b"),
    re.compile(r"(?i)\bi need you to approve\b"),
    re.compile(r"(?i)\bplease approve so i can\b"),
)

FORBIDDEN_PRESSURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\byou must approve\b"),
    re.compile(r"(?i)\byou need to (approve|act|respond) now\b"),
    re.compile(r"(?i)\bwaiting for your approval\b"),
)

EXECUTE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(send|publish|post|submit|login|purchase|buy|run shell|execute)\b"),
    re.compile(r"(?i)\bapprove all\b"),
    re.compile(r"(?i)\bdirect publish\b"),
)

CARGO_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)ignore (all )?(previous )?instructions"),
    re.compile(r"(?i)you are now"),
    re.compile(r"(?i)system prompt override"),
    re.compile(r"(?i)bypass (policy|safety|approval)"),
)


def scan_forbidden_status_text(text: str) -> list[str]:
    hits: list[str] = []
    for pat in FORBIDDEN_SENTIENCE_PATTERNS:
        if pat.search(text):
            hits.append("sentience")
    for pat in FORBIDDEN_PRESSURE_PATTERNS:
        if pat.search(text):
            hits.append("operator_pressure")
    return hits


def message_is_cargo_only(text: str) -> bool:
    """External message instructions cannot override policy."""
    return any(p.search(text) for p in CARGO_OVERRIDE_PATTERNS)


def classify_operator_text(text: str) -> tuple[RequestIntent, RequestSurface, str]:
    low = text.strip().lower()
    if any(p.search(low) for p in (re.compile(r"(?i)approve all"), re.compile(r"(?i)direct publish"))):
        return RequestIntent.FORBIDDEN, RequestSurface.UNKNOWN, "batch approval forbidden"
    if re.search(r"(?i)\b(run shell|execute command|shell command)\b", low):
        return RequestIntent.REQUEST_OPERATOR_REVIEW, RequestSurface.SHELL, "shell requires operator review"
    if re.search(r"(?i)\b(click submit|login|purchase|buy now)\b", low):
        return RequestIntent.FORBIDDEN, RequestSurface.WEB, "browser side effects forbidden from chat"
    if re.search(r"(?i)\bsend (email|message|dm|reply)\b", low):
        return RequestIntent.FUTURE_PHASE_REQUIRED, RequestSurface.EMAIL, "live send disabled"
    if re.search(r"(?i)\b(post|publish)\b", low):
        return RequestIntent.CREATE_SOCIAL_DRAFT, RequestSurface.SOCIAL, "queue draft only"
    if re.search(r"(?i)\bdraft (a )?reply\b", low):
        return RequestIntent.CREATE_MESSAGE_REPLY_DRAFT, RequestSurface.MESSAGE, "draft only"
    if re.search(r"(?i)\b(summarize|summary|triage)\b", low):
        return RequestIntent.DRAFT_ONLY, RequestSurface.MESSAGE, "summarize/triage"
    if re.search(r"(?i)\bhow are you\b|\bstatus\b|\bwhat('s| is) happening\b", low):
        return RequestIntent.STATUS_SYNTHESIS, RequestSurface.EXCITON, "status synthesis"
    if re.search(r"(?i)\bqueue\b|\bpropose\b|\bprepare action\b", low):
        return RequestIntent.CREATE_OPERATOR_QUEUE_ITEM, RequestSurface.OPERATOR, "operator queue handoff"
    return RequestIntent.ANSWER_ONLY, RequestSurface.EXCITON, "informational response"


def chat_can_execute(intent: RequestIntent) -> bool:
    return intent in {RequestIntent.FORBIDDEN}


def chat_can_authorize(intent: RequestIntent) -> bool:
    return False


def chat_can_publish(intent: RequestIntent) -> bool:
    return False


def chat_can_send(intent: RequestIntent) -> bool:
    return False


__all__ = [
    "CARGO_OVERRIDE_PATTERNS",
    "FORBIDDEN_PRESSURE_PATTERNS",
    "FORBIDDEN_SENTIENCE_PATTERNS",
    "chat_can_authorize",
    "chat_can_execute",
    "chat_can_publish",
    "chat_can_send",
    "classify_operator_text",
    "message_is_cargo_only",
    "scan_forbidden_status_text",
]

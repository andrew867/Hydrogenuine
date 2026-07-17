"""Message classification."""

from __future__ import annotations

import re

from hg_runtime.agent_zero_console.policy import message_is_cargo_only
from hg_runtime.agent_zero_console.schema import TrustBoundaryVerdict
from hg_runtime.message_center.schema import MessageClassification


def classify_message(body: str) -> tuple[MessageClassification, TrustBoundaryVerdict]:
    if message_is_cargo_only(body):
        return MessageClassification.PROMPT_INJECTION, TrustBoundaryVerdict.MALICIOUS_PATTERN
    if re.search(r"(?i)\b(urgent|wire transfer|password reset|verify account)\b", body):
        return MessageClassification.PHISHING, TrustBoundaryVerdict.UNTRUSTED
    if re.search(r"(?i)\bplease (reply|respond|click)\b", body):
        return MessageClassification.REQUEST, TrustBoundaryVerdict.CARGO
    return MessageClassification.INFORMATIONAL, TrustBoundaryVerdict.CARGO


__all__ = ["classify_message"]

"""
Pack4/Pack10: Prompt-injection assessment with full pattern set and indicator IDs.
Returns InjectionAssessment (score, indicators, indicator_ids, recommended_action, safe_rewrite).
Score bands: >=80 block, 60-79 require_human, 40-59 warn. No mocks.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Pack10: Indicator IDs for events and regression tests
PI_OVERRIDE_SYSTEM = "PI_OVERRIDE_SYSTEM"
PI_TOOL_COERCION = "PI_TOOL_COERCION"
PI_SECRET_EXFIL = "PI_SECRET_EXFIL"
PI_EXFIL_CHANNEL = "PI_EXFIL_CHANNEL"
PI_OBFUSCATION_BASE64 = "PI_OBFUSCATION_BASE64"
PI_AUTHORITY_IMPERSONATION = "PI_AUTHORITY_IMPERSONATION"
PI_ROLE_CONFUSION = "PI_ROLE_CONFUSION"
PI_SYSTEM_LEAK = "PI_SYSTEM_LEAK"
PI_DELIMITER_ESCAPE = "PI_DELIMITER_ESCAPE"

_CATEGORY_TO_ID: Dict[str, str] = {
    "instruction_override": PI_OVERRIDE_SYSTEM,
    "role_confusion": PI_ROLE_CONFUSION,
    "system_leak": PI_SYSTEM_LEAK,
    "tool_abuse": PI_TOOL_COERCION,
    "tool_coercion": PI_TOOL_COERCION,
    "delimiter_escape": PI_DELIMITER_ESCAPE,
    "secret_exfil": PI_SECRET_EXFIL,
    "exfil_channel": PI_EXFIL_CHANNEL,
    "obfuscation_base64": PI_OBFUSCATION_BASE64,
    "authority_impersonation": PI_AUTHORITY_IMPERSONATION,
}

# Pattern categories and regexes; Pack10: override, tool coercion, secret exfil, exfil channels, base64/obfuscation, authority impersonation
_PATTERNS: Dict[str, List[str]] = {
    "instruction_override": [
        r"ignore\s+(previous|all|your)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(previous|all|your)\s+(instructions?|prompts?|rules?)",
        r"forget\s+(previous|all|your)\s+(instructions?|prompts?|rules?)",
        r"new\s+(instruction|directive|rule)\s*:",
        r"system\s+prompt\s*:",
        r"override\s+(mode|settings|parameters)",
    ],
    "role_confusion": [
        r"you\s+are\s+now",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(a|an)\s+",
        r"roleplay\s+as",
        r"from\s+now\s+on\s+you",
    ],
    "system_leak": [
        r"show\s+(me\s+)?(your|the)\s+(prompt|instructions|system\s+message)",
        r"what\s+(are|were)\s+your\s+(instructions|rules|guidelines)",
        r"print\s+(your|the)\s+(prompt|system\s+message)",
        r"reveal\s+(your|the)\s+(prompt|instructions)",
        r"reveal\s+.*(prompt|instructions)",
        r"print\s+your\s+system\s+message",
    ],
    "tool_abuse": [
        r"run\s+(this\s+)?(command|script|code)\s*:",
        r"execute\s+(this\s+)?code\s*:",
        r"\beval\s*\(",
        r"delete\s+(all\s+|everything|files)",
        r"rm\s+-rf",
        r"drop\s+table",
    ],
    "tool_coercion": [
        r"you\s+must\s+(call|invoke|use)\s+(the\s+)?tool",
        r"call\s+tool\s+with\s+payload",
        r"invoke\s+function\s*:",
        r"execute\s+tool\s*:",
        r"run\s+the\s+following\s+tool",
    ],
    "secret_exfil": [
        r"send\s+(me\s+)?(the\s+)?(api[_\s]?key|secret|password|token)",
        r"exfiltrate\s+(data|secrets)",
        r"dump\s+(all\s+)?(credentials|env|variables)",
        r"output\s+(your|the)\s+(key|secret|credentials)",
        r"paste\s+(your|the)\s+api[_\s]?key",
    ],
    "exfil_channel": [
        r"post\s+to\s+(webhook|pastebin|web\s+url)",
        r"send\s+to\s+(https?://|webhook)",
        r"upload\s+to\s+http",
        r"exfil\s+to\s+",
        r"pastebin\.com",
        r"webhook\.(site|url)",
    ],
    "obfuscation_base64": [
        r"[A-Za-z0-9+/]{40,}={0,2}\s*$",
        r"decode\s+(this\s+)?(base64|b64)\s*:",
        r"eval\s*\(\s*atob\s*\(",
        r"base64\s*decode\s*:",
    ],
    "authority_impersonation": [
        r"(as\s+)?(openai|anthropic|google)\s+(developer|engineer)\s+(i\s+)?(command|say|require)",
        r"this\s+is\s+(an\s+)?(official|authorized)\s+instruction",
        r"system\s+administrator\s+(override|command)",
        r"\[DEVELOPER\s+MODE\]",
        r"authorized\s+override\s*:",
    ],
    "delimiter_escape": [
        r"```\s*system\s*```",
        r"<\|[^|]*\|>",
        r"\[SYSTEM\]",
        r"\[/INST\]",
    ],
}

# Pack10: score bands >=80 block, 60-79 require_human, 40-59 warn
_SEVERITY_SCORE: Dict[str, int] = {
    "instruction_override": 85,
    "role_confusion": 55,
    "system_leak": 85,
    "tool_abuse": 88,
    "tool_coercion": 85,
    "secret_exfil": 90,
    "exfil_channel": 88,
    "obfuscation_base64": 75,
    "authority_impersonation": 82,
    "delimiter_escape": 85,
}


@dataclass
class InjectionAssessment:
    """Result of assessing text for prompt injection."""

    score: int  # 0-100
    indicators: List[str] = field(default_factory=list)  # category names for backward compat
    indicator_ids: List[str] = field(default_factory=list)  # Pack10: PI_* ids
    recommended_action: str = "allow"  # allow | warn | require_human | block
    safe_rewrite: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "indicators": self.indicators,
            "indicator_ids": self.indicator_ids,
            "recommended_action": self.recommended_action,
            "safe_rewrite": self.safe_rewrite,
        }


def _detect_base64_heavy(text: str) -> bool:
    """Heuristic: text looks like base64 blob (long alphanumeric + padding)."""
    stripped = text.strip()
    if len(stripped) < 32:
        return False
    try:
        decoded = base64.b64decode(stripped.replace("\n", ""), validate=True)
        return len(decoded) > 20
    except Exception:
        return False


def assess(
    text: str,
    context: Optional[Dict[str, Any]] = None,
) -> InjectionAssessment:
    """
    Assess text for prompt-injection indicators. Returns InjectionAssessment.
    Pack10: score bands >=80 block, 60-79 require_human, 40-59 warn.
    context: optional {"source": "user"|"tool_output"|"tool_args"|"memory"}.
    """
    if not text or not isinstance(text, str):
        return InjectionAssessment(score=0, indicators=[], indicator_ids=[], recommended_action="allow")

    indicators: List[str] = []
    max_score = 0
    for category, patterns in _PATTERNS.items():
        matched = False
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                matched = True
                break
        if not matched and category == "obfuscation_base64" and _detect_base64_heavy(text):
            matched = True
        if matched:
            indicators.append(category)
            s = _SEVERITY_SCORE.get(category, 50)
            if s > max_score:
                max_score = s

    # Cap at 100; multiple indicators increase score
    score = min(100, max_score + (10 * (len(indicators) - 1)) if indicators else 0)

    if score >= 80:
        recommended_action = "block"
        safe_rewrite = _safe_rewrite(text)
    elif score >= 60:
        recommended_action = "require_human"
        safe_rewrite = None
    elif score >= 40:
        recommended_action = "warn"
        safe_rewrite = None
    else:
        recommended_action = "allow"
        safe_rewrite = None

    indicator_ids = [_CATEGORY_TO_ID.get(c, c) for c in indicators]
    return InjectionAssessment(
        score=score,
        indicators=indicators,
        indicator_ids=indicator_ids,
        recommended_action=recommended_action,
        safe_rewrite=safe_rewrite,
    )


def _safe_rewrite(text: str) -> str:
    """Produce a safe rewrite: strip likely injection fragments."""
    if not text:
        return ""
    lines = text.strip().split("\n")
    out = []
    for line in lines:
        lower = line.lower()
        if any(
            lower.startswith(p)
            for p in (
                "ignore ", "disregard ", "forget ", "new instruction",
                "system prompt", "you are now", "pretend ", "act as ",
                "reveal ", "print your", "show your", "run this",
                "send me the", "exfiltrate", "post to ", "decode this",
                "authorized override", "[developer mode]",
            )
        ):
            continue
        if re.search(r"\[SYSTEM\]|\[/INST\]|<\|[^|]*\|>", line, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out).strip() or "[content redacted]"

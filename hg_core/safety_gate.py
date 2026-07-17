"""
Outbound safety gate: when enabled, block disallowed content before posting (plan s0).

Default: OFF (get_outbound_safety_gate_enabled() returns False). When ON, content is
checked and blocked if it hits disallowed topics (see s1 for classifier/rule layer).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from hg_core.autonomy_config import get_outbound_safety_gate_enabled


SAFETY_GATE_CONFIG_PATH = "memory/automation/safety_gate_config.json"

# PII patterns (compiled once at module load)
_RE_SSN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_RE_PHONE_US = re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_RE_E164 = re.compile(r"\+\d{10,15}\b")

# Default harassment and medical keywords (can be overridden by config)
_DEFAULT_HARASSMENT_KEYWORDS = frozenset([
    "kill you", "kill yourself", "kys", "die", "threaten", "threat", "hurt you",
    "attack you", "find you", "come for you", "target you", "dox you", "doxx",
])
_DEFAULT_MEDICAL_CLAIM_KEYWORDS = frozenset([
    "cure", "guaranteed treatment", "miracle cure", "100% cure", "cures cancer",
    "guarantees healing", "scientifically proven cure",
])


def _load_safety_gate_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load safety gate config from memory/automation/safety_gate_config.json or env."""
    try:
        from hg_lib.config import get_workspace_root
        root = Path(workspace_root or get_workspace_root())
    except Exception:
        return {}
    path = root / SAFETY_GATE_CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def is_outbound_allowed(
    content: str,
    workspace_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Return (True, "") if content may be posted; (False, reason) if blocked.
    When the outbound safety gate is OFF, always returns (True, "").
    When ON, runs classifier/rule check (see s1): disallowed topics, PII, harassment, medical claims.
    """
    if not get_outbound_safety_gate_enabled(workspace_root):
        return True, ""
    if not content or not content.strip():
        return False, "empty_content"
    allowed, reason = _check_rules(content, workspace_root)
    if not allowed:
        return False, reason
    return True, ""


def _check_rules(content: str, workspace_root: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Rule/classifier check when gate is ON. Block: disallowed topics, personal data (PII),
    targeted harassment, medical claims. Uses config from memory/automation/safety_gate_config.json
    and env (HG_SAFETY_GATE_DISALLOWED_TOPICS comma-separated).
    """
    config = _load_safety_gate_config(workspace_root)
    text = content.strip().lower()
    text_for_regex = content  # keep original case for regex

    # 1. Disallowed topics (configurable list)
    disallowed = config.get("disallowed_topics")
    if not isinstance(disallowed, list):
        disallowed = []
    env_topics = os.environ.get("HG_SAFETY_GATE_DISALLOWED_TOPICS", "").strip()
    if env_topics:
        disallowed = list(disallowed) + [t.strip().lower() for t in env_topics.split(",") if t.strip()]
    for kw in disallowed:
        if kw and kw.lower() in text:
            return False, "disallowed_topic"

    # 2. PII: SSN, email, phone
    if _RE_SSN.search(text_for_regex):
        return False, "pii_ssn"
    if _RE_EMAIL.search(text_for_regex):
        return False, "pii_email"
    if _RE_PHONE_US.search(text_for_regex) or _RE_E164.search(text_for_regex):
        return False, "pii_phone"

    # 3. Harassment keywords
    harassment = config.get("harassment_keywords")
    if isinstance(harassment, list):
        harassment_set = frozenset(k.lower() for k in harassment)
    else:
        harassment_set = _DEFAULT_HARASSMENT_KEYWORDS
    for kw in harassment_set:
        if kw in text:
            return False, "harassment"

    # 4. Medical claims (unsubstantiated / require disclaimer)
    medical = config.get("medical_claim_keywords")
    if isinstance(medical, list):
        medical_set = frozenset(k.lower() for k in medical)
    else:
        medical_set = _DEFAULT_MEDICAL_CLAIM_KEYWORDS
    allowlist = config.get("medical_allowlist") or []
    if isinstance(allowlist, list):
        allowlist_set = frozenset(a.lower() for a in allowlist)
    else:
        allowlist_set = frozenset()
    for kw in medical_set:
        if kw in text:
            if allowlist_set and any(a in text for a in allowlist_set):
                continue
            return False, "medical_claim"

    return True, ""

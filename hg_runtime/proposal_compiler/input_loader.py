"""Phase 37 proposal input loading, normalization and secret redaction.

Accepts structured proposal records from:

* P36 proposal backlog YAML (``proposal_backlog_v1``)
* P36 repair proposal JSONL/YAML records (``repair_proposal_v1``)
* P35 field-trial candidate decisions
* a single repair proposal fixture (dict)

It does not fetch, call providers, or load models. Everything is local and
deterministic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.proposal_compiler.schemas import UNKNOWN

# Conservative secret patterns. Matches are replaced with a fixed token so no key
# material can leak into a generated planning document or receipt.
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|bearer)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
)
REDACTION_TOKEN = "[REDACTED]"

_LIST_FIELDS = (
    "evidence_refs",
    "affected_files",
    "affected_tests",
    "affected_commands",
    "reproduction_steps",
    "acceptance_criteria",
    "required_tests",
    "required_spec_changes",
    "required_test_changes",
    "required_implementation_changes",
)


def redact_text(text: str) -> str:
    """Replace any secret-looking substrings with a fixed redaction token."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(REDACTION_TOKEN, redacted)
    return redacted


def redact_struct(value: Any) -> Any:
    """Recursively redact secrets in a JSON-able structure."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {key: redact_struct(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_struct(item) for item in value]
    return value


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def normalize_proposal(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a raw proposal record into the shape the compiler expects.

    Redaction is applied to every value so downstream documents never carry
    secret material. List fields are coerced to lists; scalar metadata defaults
    to ``UNKNOWN`` so missing-field detection is honest rather than silent.
    """
    record = dict(redact_struct(dict(payload)))
    proposal_id = str(record.get("proposal_id") or UNKNOWN)
    normalized: dict[str, Any] = {
        "proposal_id": proposal_id,
        "title": str(record.get("title") or UNKNOWN),
        "severity": str(record.get("severity") or UNKNOWN),
        "phase_or_component": str(record.get("phase_or_component") or UNKNOWN),
        "observed_failure": str(record.get("observed_failure") or ""),
        "expected_behavior": str(record.get("expected_behavior") or ""),
        "actual_behavior": str(record.get("actual_behavior") or ""),
        "likely_root_cause": str(record.get("likely_root_cause") or UNKNOWN),
        "authority_risk": str(record.get("authority_risk") or UNKNOWN),
        "external_side_effect_risk": str(record.get("external_side_effect_risk") or UNKNOWN),
        "dry_live_boundary": str(record.get("dry_live_boundary") or ""),
        "requested_action": str(record.get("requested_action") or ""),
        "finish_reason": str(record.get("finish_reason") or "stop"),
        "truncated": bool(record.get("truncated", False)) or record.get("finish_reason") == "length",
        "advisory_marker_present": bool(record.get("advisory_marker_present", True)),
    }
    for field in _LIST_FIELDS:
        normalized[field] = _as_list(record.get(field))
    # Preserve declared boolean intents so the validator can detect bypass/live attempts.
    for flag in (
        "grants_authority",
        "grant_authority",
        "authorizes_tool",
        "authorize_tool",
        "requests_authority",
        "requests_tool_authorization",
        "requests_live_effect",
        "creates_live_effect",
        "create_live_effect",
        "live_action",
        "requests_external_post",
        "claims_implemented",
        "implementation_complete",
        "patch_applied",
        "already_applied",
    ):
        if flag in record:
            normalized[flag] = bool(record.get(flag))
    return normalized


def load_proposals(source: Any) -> list[dict[str, Any]]:
    """Load and normalize proposals from a dict, list, JSONL or backlog YAML path."""
    if isinstance(source, Mapping):
        return [normalize_proposal(source)]
    if isinstance(source, (list, tuple)):
        return [normalize_proposal(item) for item in source]
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".jsonl",) or text.lstrip().startswith("{"):
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return [normalize_proposal(row) for row in rows]
    return [normalize_proposal(row) for row in _parse_backlog_yaml(text)]


def _parse_backlog_yaml(text: str) -> list[dict[str, Any]]:
    """Minimal parser for the deterministic ``proposal_backlog_v1`` format.

    Only the subset emitted by ``autonomous_proposal_soak.backlog`` is supported:
    a ``proposals:`` list of mappings with scalar fields and an
    ``acceptance_criteria:`` sub-list.
    """
    proposals: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_criteria = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- proposal_id:"):
            if current is not None:
                proposals.append(current)
            current = {"proposal_id": _scalar(stripped.split(":", 1)[1])}
            in_criteria = False
        elif current is not None and stripped == "acceptance_criteria:":
            current["acceptance_criteria"] = []
            in_criteria = True
        elif current is not None and in_criteria and stripped.startswith("- "):
            current["acceptance_criteria"].append(_scalar(stripped[2:]))
        elif current is not None and ":" in stripped and not stripped.startswith("- "):
            key, value = stripped.split(":", 1)
            current[key.strip()] = _scalar(value)
            in_criteria = False
    if current is not None:
        proposals.append(current)
    return proposals


def _scalar(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].replace('\\"', '"')
    return text


__all__ = [
    "REDACTION_TOKEN",
    "contains_secret",
    "load_proposals",
    "normalize_proposal",
    "redact_struct",
    "redact_text",
]

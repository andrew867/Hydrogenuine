"""Conversational policy compiler — structured draft to CanonicalPolicy.

The language model's role ends at producing a *structured draft* (a plain
dict). This compiler validates the draft into a CanonicalPolicy or returns
ClarificationNeeded. Ambiguity never resolves permissively: missing or vague
fields become operator questions, not defaults. Free text is never executed;
condition payloads go through the allowlisted AST parser only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from hg_lease.policy import (
    CanonicalPolicy,
    NumericLimit,
    PolicyValidationError,
    condition_from_payload,
    validate_policy,
)


@dataclass(frozen=True)
class ClarificationNeeded:
    """The draft cannot compile without operator input."""

    questions: tuple[str, ...]
    draft_ref: Optional[str] = None


_RISK_CLASSES = {"LOW", "MODERATE", "HIGH", "CRITICAL"}
_RENEWAL_MODES = {"MANUAL", "PROMPT_BEFORE_EXPIRY", "DISABLED"}


def _summary(draft: dict[str, Any], limits: list[NumericLimit]) -> str:
    subjects = ", ".join(draft["subjects"])
    actions = ", ".join(draft["actions"])
    objects = ", ".join(draft["objects"])
    limit_text = "; ".join(
        f"{l.parameter} <= {l.max_value} {l.unit}" for l in limits
    )
    parts = [
        f"Allow {subjects} to {actions} on {objects}",
        f"purpose: {draft['purpose']}",
        f"valid {draft['valid_from']} to {draft['valid_until']}",
    ]
    if limit_text:
        parts.append(f"limits: {limit_text}")
    if draft.get("use_limit") is not None:
        parts.append(f"at most {draft['use_limit']} uses")
    parts.append(f"risk: {draft['risk_class']}")
    return "; ".join(parts)


def compile_draft(
    draft: dict[str, Any],
    *,
    issuer_operator_id: str,
    allow_moderate: bool = False,
    allow_high_risk_local_policy: bool = False,
) -> Union[CanonicalPolicy, ClarificationNeeded]:
    """Compile a structured draft. Returns ClarificationNeeded on ambiguity."""
    questions: list[str] = []

    for key, question in (
        ("subjects", "Who is this authority for (exact subject ids)?"),
        ("actions", "Which exact action types are covered?"),
        ("objects", "Which exact objects/devices are covered?"),
        ("purpose", "What is the purpose of this standing permission?"),
        ("valid_from", "When should this start (timestamp)?"),
        ("valid_until", "When should this end (timestamp)?"),
        ("risk_class", "What risk class applies (LOW/MODERATE/HIGH/CRITICAL)?"),
    ):
        value = draft.get(key)
        if value in (None, "", [], ()):
            questions.append(question)

    risk = draft.get("risk_class")
    if risk is not None and risk not in _RISK_CLASSES:
        questions.append(f"Risk class {risk!r} is not recognized — choose one of {sorted(_RISK_CLASSES)}.")

    for scope_key in ("subjects", "actions", "objects"):
        values = draft.get(scope_key) or []
        if any(v == "*" for v in values):
            questions.append(
                f"The draft uses a wildcard for {scope_key}; wildcards need a "
                "conspicuous, dedicated confirmation. List exact values instead?"
            )

    renewal = draft.get("renewal_mode", "MANUAL")
    if renewal not in _RENEWAL_MODES:
        questions.append(f"Renewal mode {renewal!r} is not recognized.")

    if questions:
        return ClarificationNeeded(questions=tuple(questions))

    try:
        condition = (
            condition_from_payload(draft["condition"])
            if draft.get("condition") is not None
            else None
        )
        limits = [
            NumericLimit(
                parameter=l["parameter"],
                max_value=l["max_value"],
                unit=l["unit"],
                min_value=l.get("min_value", 0.0),
            )
            for l in draft.get("numeric_limits", [])
        ]
    except (PolicyValidationError, KeyError, TypeError) as exc:
        return ClarificationNeeded(
            questions=(f"The policy conditions could not be compiled safely: {exc}. "
                       "Please restate the condition in supported terms.",)
        )

    policy = CanonicalPolicy(
        policy_id=f"pol_{uuid.uuid4().hex[:16]}",
        issuer_operator_id=issuer_operator_id,
        subjects=tuple(draft["subjects"]),
        actions=tuple(draft["actions"]),
        objects=tuple(draft["objects"]),
        purpose=str(draft["purpose"]),
        condition=condition,
        numeric_limits=tuple(limits),
        risk_class=draft["risk_class"],
        renewal_mode=renewal,
        unknown_fact_policy=draft.get("unknown_fact_policy", "DENY"),
        valid_from=str(draft["valid_from"]),
        valid_until=str(draft["valid_until"]),
        display_summary=_summary(draft, limits),
        use_limit=draft.get("use_limit"),
        required_facts=tuple(draft.get("required_facts", ())),
        source_conversation_refs=tuple(draft.get("source_conversation_refs", ())),
        close_obligations=tuple(draft.get("close_obligations", ())),
    )

    problems = validate_policy(
        policy,
        allow_moderate=allow_moderate,
        allow_high_risk_local_policy=allow_high_risk_local_policy,
    )
    if problems:
        return ClarificationNeeded(
            questions=tuple(f"Policy cannot be issued as drafted: {p}" for p in problems)
        )
    return policy

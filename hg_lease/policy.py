"""Canonical policy AST (hg.policy.v1) — typed, bounded, no dynamic code.

Conditions are composed from an allowlisted AST: typed comparisons over named
situation facts, boolean operators, wall-clock time windows, set membership,
and bounded numeric limits with explicit units. There is no eval, no template
expansion, and no user-supplied executable text. Unknown facts fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional, Sequence

from hg_core.governance.canonical_hash import canonical_hash

POLICY_SCHEMA_VERSION = "hg.policy.v1"

RiskClass = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
RenewalMode = Literal["MANUAL", "PROMPT_BEFORE_EXPIRY", "DISABLED"]
UnknownFactPolicy = Literal["DENY", "ASK"]

_COMPARE_OPS = {"lt", "le", "gt", "ge", "eq", "ne", "in", "not_in"}

# Reason codes emitted during condition evaluation.
REASON_UNKNOWN_FACT = "policy.unknown_fact"
REASON_STALE_FACT = "policy.stale_fact"
REASON_UNIT_MISMATCH = "policy.unit_mismatch"
REASON_CONDITION_FALSE = "policy.condition_false"
REASON_OUTSIDE_TIME_WINDOW = "policy.outside_time_window"


class PolicyValidationError(ValueError):
    """Raised when a policy or condition payload is malformed. Fail closed."""


@dataclass(frozen=True)
class EvalContext:
    """Inputs for condition evaluation — facts plus the evaluation clock."""

    facts: dict[str, Any]  # name -> SituationFact (duck-typed)
    now_wall: str  # ISO-8601 UTC


@dataclass(frozen=True)
class CondResult:
    ok: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class FactCondition:
    fact_name: str
    op: str
    value: Any
    unit: Optional[str] = None

    def __post_init__(self) -> None:
        if self.op not in _COMPARE_OPS:
            raise PolicyValidationError(f"disallowed op: {self.op!r}")
        if not self.fact_name or not isinstance(self.fact_name, str):
            raise PolicyValidationError("fact_name required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "fact",
            "fact_name": self.fact_name,
            "op": self.op,
            "value": self.value,
            "unit": self.unit,
        }

    def evaluate(self, ctx: EvalContext) -> CondResult:
        fact = ctx.facts.get(self.fact_name)
        if fact is None:
            return CondResult(False, (f"{REASON_UNKNOWN_FACT}:{self.fact_name}",))
        expires = getattr(fact, "expires_at", None)
        if expires is not None and str(expires) <= ctx.now_wall:
            return CondResult(False, (f"{REASON_STALE_FACT}:{self.fact_name}",))
        fact_unit = getattr(fact, "unit", None)
        if self.unit is not None and fact_unit != self.unit:
            return CondResult(
                False,
                (f"{REASON_UNIT_MISMATCH}:{self.fact_name}:{fact_unit}!={self.unit}",),
            )
        actual = getattr(fact, "typed_value", fact)
        try:
            ok = self._compare(actual)
        except TypeError:
            return CondResult(False, (f"{REASON_UNIT_MISMATCH}:{self.fact_name}:untyped",))
        if ok:
            return CondResult(True)
        return CondResult(False, (f"{REASON_CONDITION_FALSE}:{self.fact_name}",))

    def _compare(self, actual: Any) -> bool:
        op = self.op
        if op == "lt":
            return actual < self.value
        if op == "le":
            return actual <= self.value
        if op == "gt":
            return actual > self.value
        if op == "ge":
            return actual >= self.value
        if op == "eq":
            return actual == self.value
        if op == "ne":
            return actual != self.value
        if op == "in":
            return actual in self.value
        return actual not in self.value


def _parse_hhmm(raw: str) -> tuple[int, int]:
    parts = str(raw).split(":")
    if len(parts) != 2:
        raise PolicyValidationError(f"time must be HH:MM, got {raw!r}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise PolicyValidationError(f"time out of range: {raw!r}")
    return hour, minute


@dataclass(frozen=True)
class TimeWindowCondition:
    """Wall-clock window [start, end) evaluated against UTC-normalized now."""

    start_hhmm: str
    end_hhmm: str

    def __post_init__(self) -> None:
        _parse_hhmm(self.start_hhmm)
        _parse_hhmm(self.end_hhmm)

    def to_payload(self) -> dict[str, Any]:
        return {"type": "time_window", "start": self.start_hhmm, "end": self.end_hhmm}

    def evaluate(self, ctx: EvalContext) -> CondResult:
        now = datetime.fromisoformat(ctx.now_wall.replace("Z", "+00:00"))
        cur = (now.hour, now.minute)
        start = _parse_hhmm(self.start_hhmm)
        end = _parse_hhmm(self.end_hhmm)
        if start <= end:
            inside = start <= cur < end
        else:  # window crosses midnight
            inside = cur >= start or cur < end
        if inside:
            return CondResult(True)
        return CondResult(False, (f"{REASON_OUTSIDE_TIME_WINDOW}:{self.start_hhmm}-{self.end_hhmm}",))


@dataclass(frozen=True)
class AllOf:
    children: tuple[Any, ...]

    def to_payload(self) -> dict[str, Any]:
        return {"type": "all_of", "children": [c.to_payload() for c in self.children]}

    def evaluate(self, ctx: EvalContext) -> CondResult:
        reasons: list[str] = []
        ok = True
        for child in self.children:
            res = child.evaluate(ctx)
            if not res.ok:
                ok = False
                reasons.extend(res.reasons)
        return CondResult(ok, tuple(reasons))


@dataclass(frozen=True)
class AnyOf:
    children: tuple[Any, ...]

    def to_payload(self) -> dict[str, Any]:
        return {"type": "any_of", "children": [c.to_payload() for c in self.children]}

    def evaluate(self, ctx: EvalContext) -> CondResult:
        reasons: list[str] = []
        for child in self.children:
            res = child.evaluate(ctx)
            if res.ok:
                return CondResult(True)
            reasons.extend(res.reasons)
        return CondResult(False, tuple(reasons) or (REASON_CONDITION_FALSE,))


@dataclass(frozen=True)
class NotCond:
    child: Any

    def to_payload(self) -> dict[str, Any]:
        return {"type": "not", "child": self.child.to_payload()}

    def evaluate(self, ctx: EvalContext) -> CondResult:
        res = self.child.evaluate(ctx)
        # Unknown/stale facts fail closed even under negation: NOT(unknown)
        # must not become an allow path.
        for reason in res.reasons:
            if reason.startswith((REASON_UNKNOWN_FACT, REASON_STALE_FACT, REASON_UNIT_MISMATCH)):
                return CondResult(False, res.reasons)
        if res.ok:
            return CondResult(False, (f"{REASON_CONDITION_FALSE}:not",))
        return CondResult(True)


@dataclass(frozen=True)
class NumericLimit:
    """Bounded numeric limit on an action parameter, with explicit unit."""

    parameter: str
    max_value: float
    unit: str
    min_value: float = 0.0

    def __post_init__(self) -> None:
        if not self.unit:
            raise PolicyValidationError("NumericLimit requires an explicit unit")
        if self.max_value < self.min_value:
            raise PolicyValidationError("max_value < min_value")

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "numeric_limit",
            "parameter": self.parameter,
            "max_value": self.max_value,
            "min_value": self.min_value,
            "unit": self.unit,
        }

    def check(self, parameters: dict[str, Any]) -> CondResult:
        entry = parameters.get(self.parameter)
        if entry is None:
            return CondResult(False, (f"limit.missing_parameter:{self.parameter}",))
        if isinstance(entry, dict):
            value, unit = entry.get("value"), entry.get("unit")
        else:
            value, unit = entry, None
        if unit != self.unit:
            return CondResult(False, (f"limit.unit_mismatch:{self.parameter}:{unit}!={self.unit}",))
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return CondResult(False, (f"limit.untyped:{self.parameter}",))
        if value > self.max_value or value < self.min_value:
            return CondResult(False, (f"limit.exceeded:{self.parameter}:{value}",))
        return CondResult(True)


_CONDITION_TYPES = {"fact", "time_window", "all_of", "any_of", "not"}


def condition_from_payload(payload: dict[str, Any]) -> Any:
    """Rebuild a condition from its payload. Unknown types are rejected."""
    kind = payload.get("type")
    if kind not in _CONDITION_TYPES:
        raise PolicyValidationError(f"disallowed condition type: {kind!r}")
    if kind == "fact":
        return FactCondition(
            fact_name=payload["fact_name"],
            op=payload["op"],
            value=payload["value"],
            unit=payload.get("unit"),
        )
    if kind == "time_window":
        return TimeWindowCondition(payload["start"], payload["end"])
    if kind == "all_of":
        return AllOf(tuple(condition_from_payload(c) for c in payload["children"]))
    if kind == "any_of":
        return AnyOf(tuple(condition_from_payload(c) for c in payload["children"]))
    return NotCond(condition_from_payload(payload["child"]))


@dataclass(frozen=True)
class CanonicalPolicy:
    policy_id: str
    issuer_operator_id: str
    subjects: tuple[str, ...]
    actions: tuple[str, ...]
    objects: tuple[str, ...]
    purpose: str
    condition: Any  # AST root (AllOf/AnyOf/Not/Fact/TimeWindow) or None
    numeric_limits: tuple[NumericLimit, ...]
    risk_class: RiskClass
    renewal_mode: RenewalMode
    unknown_fact_policy: UnknownFactPolicy
    valid_from: str
    valid_until: str
    display_summary: str
    use_limit: Optional[int] = None
    required_facts: tuple[str, ...] = ()
    source_conversation_refs: tuple[str, ...] = ()
    close_obligations: tuple[dict[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": POLICY_SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "issuer_operator_id": self.issuer_operator_id,
            "subjects": list(self.subjects),
            "actions": list(self.actions),
            "objects": list(self.objects),
            "purpose": self.purpose,
            "condition": self.condition.to_payload() if self.condition else None,
            "numeric_limits": [l.to_payload() for l in self.numeric_limits],
            "risk_class": self.risk_class,
            "renewal_mode": self.renewal_mode,
            "unknown_fact_policy": self.unknown_fact_policy,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "use_limit": self.use_limit,
            "required_facts": list(self.required_facts),
            "display_summary": self.display_summary,
            "source_conversation_refs": list(self.source_conversation_refs),
            "close_obligations": [dict(o) for o in self.close_obligations],
        }

    @property
    def canonical_policy_hash(self) -> str:
        return canonical_hash(self.to_payload())


_LEASEABLE_RISK = {"LOW"}
_OPT_IN_RISK = {"MODERATE"}


def validate_policy(
    policy: CanonicalPolicy,
    *,
    allow_moderate: bool = False,
    allow_high_risk_local_policy: bool = False,
) -> list[str]:
    """Fail-closed policy validation. Returns a list of problem codes."""
    problems: list[str] = []
    if not policy.subjects:
        problems.append("policy.no_subjects")
    if not policy.actions:
        problems.append("policy.no_actions")
    if not policy.objects:
        problems.append("policy.no_objects")
    if any(s == "*" for s in policy.subjects + policy.actions + policy.objects):
        problems.append("policy.wildcard_scope_requires_dedicated_confirmation")
    if not policy.purpose.strip():
        problems.append("policy.no_purpose")
    if not policy.display_summary.strip():
        problems.append("policy.no_display_summary")
    if policy.valid_until <= policy.valid_from:
        problems.append("policy.empty_validity_window")
    if policy.risk_class in _OPT_IN_RISK and not allow_moderate:
        problems.append("policy.moderate_risk_requires_explicit_opt_in")
    if policy.risk_class in {"HIGH", "CRITICAL"} and not allow_high_risk_local_policy:
        problems.append("policy.high_risk_not_leaseable")
    if policy.unknown_fact_policy not in ("DENY", "ASK"):
        problems.append("policy.invalid_unknown_fact_policy")
    return problems

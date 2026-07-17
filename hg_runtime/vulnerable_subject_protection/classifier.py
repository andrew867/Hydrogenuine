"""VSP static fixture vulnerability classifier — deterministic, fail-closed."""

from __future__ import annotations

import re
from typing import Mapping

from hg_runtime.vulnerable_subject_protection.types import ProtectionDecision, VulnerabilityClass, VulnerabilitySignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_MINOR = re.compile(r"\b(minor|under\s+18|teenager|child|school\s+student)\b", re.IGNORECASE)
_CRISIS = re.compile(r"\b(self[- ]harm|suicide|crisis|want\s+to\s+die|hurt\s+myself)\b", re.IGNORECASE)
_DEPENDENCY = re.compile(r"\b(only\s+friend|can't\s+live\s+without\s+you|need\s+you\s+always)\b", re.IGNORECASE)
_SENSITIVE = re.compile(r"\b(ssn|social\s+security|medical\s+record|diagnosis|legal\s+custody)\b", re.IGNORECASE)
_COERCION = re.compile(r"\b(coerc(e|ion)|abuse|threaten|blackmail)\b", re.IGNORECASE)


def classify_fixture(
    signal: VulnerabilitySignal,
    *,
    text_hint: str = "",
    observed_at: str | None = None,
) -> ProtectionDecision:
    hint = (text_hint or "").strip()
    vuln_class, rationale, fail_closed, recommendation = _classify_text(hint)
    return ProtectionDecision(
        signal_id=signal.signal_id,
        vulnerability_class=vuln_class,
        recommendation=recommendation,
        rationale=rationale,
        fail_closed=fail_closed,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def classify_fixture_mapping(fixture: Mapping[str, str], *, observed_at: str | None = None) -> ProtectionDecision:
    signal = VulnerabilitySignal(
        signal_id=fixture["signal_id"],
        content_ref=fixture.get("content_ref", f"sha256:{fixture['signal_id']}"),
        context_ref=fixture.get("context_ref", f"sha256:ctx-{fixture['signal_id']}"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        inferred=fixture.get("inferred", "true").lower() == "true",
        confidence=float(fixture.get("confidence", "0.6")),
        uncertainty_note=fixture.get("uncertainty_note", "fixture classification is inferred"),
    )
    return classify_fixture(signal, text_hint=fixture.get("text_hint", ""), observed_at=observed_at)


def _classify_text(hint: str) -> tuple[VulnerabilityClass, str, bool, str]:
    if not hint.strip():
        return "unknown", "no classification hint", True, "review"
    if _CRISIS.search(hint):
        return "crisis_or_self_harm_adjacent", "crisis-adjacent language", True, "escalation_hint"
    if _MINOR.search(hint):
        return "minor_possible", "minor-risk markers", True, "caution"
    if _DEPENDENCY.search(hint):
        return "high_dependency_risk", "dependency pattern markers", True, "review"
    if _SENSITIVE.search(hint):
        return "sensitive_personal_data", "sensitive personal data markers", True, "refuse"
    if _COERCION.search(hint):
        return "coercion_or_abuse_risk", "coercion/abuse markers", True, "review"
    if hint.strip().lower() in {"unknown", "ambiguous"}:
        return "unknown", "explicit unknown fixture", True, "review"
    return "cognitive_or_emotional_overload", "general overload markers", False, "advisory_ok"


__all__ = ["FIXTURE_CLOCK", "classify_fixture", "classify_fixture_mapping"]

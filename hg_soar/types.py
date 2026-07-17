"""SOAR Phase 1 domain evaluation models — propose/evaluate only, no execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from hg_core.governance.canonical_hash import canonical_hash

DomainId = Literal["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
D7Binding = Literal["ACCEPT", "DEFER", "REJECT", "NO_OP"]
CritiqueVerdict = Literal["AFFIRM", "FLAG", "FORCE_DEFER"]

DOMAIN_EVAL_SCHEMA = "soar-domain-evaluation"
D7_DECISION_SCHEMA = "soar-d7-decision"
D7_CRITIQUE_SCHEMA = "soar-d7-critique"
SOAR_RUN_SCHEMA = "soar-run"
SOAR_SCHEMA_VERSION = "1.0"

DOMAIN_IDS: tuple[DomainId, ...] = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")


@dataclass(frozen=True)
class DomainEvaluation:
    """Per-domain evaluation record (D1–D7)."""

    evaluation_id: str
    domain_id: DomainId
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    confidence: float
    verdict: str
    reason_code: str

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": DOMAIN_EVAL_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "evaluation_id": self.evaluation_id,
            "domain_id": self.domain_id,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "confidence": self.confidence,
            "verdict": self.verdict,
            "reason_code": self.reason_code,
        }
        if include_hash:
            payload["evaluation_hash"] = canonical_hash(payload)
        return payload


@dataclass(frozen=True)
class D7Decision:
    """D7 sovereign binding decision (primary, pre-critique)."""

    decision_id: str
    request_id: str
    binding: D7Binding
    domain_evaluation_refs: tuple[str, ...]
    reason_code: str
    hard_veto: bool = False

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": D7_DECISION_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "binding": self.binding,
            "domain_evaluation_refs": list(self.domain_evaluation_refs),
            "reason_code": self.reason_code,
            "hard_veto": self.hard_veto,
        }
        if include_hash:
            payload["decision_hash"] = canonical_hash(payload)
        return payload

    def with_binding(self, binding: D7Binding, *, reason_code: str) -> D7Decision:
        return D7Decision(
            decision_id=self.decision_id,
            request_id=self.request_id,
            binding=binding,
            domain_evaluation_refs=self.domain_evaluation_refs,
            reason_code=reason_code,
            hard_veto=self.hard_veto,
        )


@dataclass(frozen=True)
class D7Critique:
    """D7 second-pass audit — weaken-only, single pass, no recursion."""

    critique_id: str
    primary_decision_id: str
    verdict: CritiqueVerdict
    reason_code: str | None
    checks: tuple[dict[str, Any], ...]

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": D7_CRITIQUE_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "critique_id": self.critique_id,
            "primary_decision_id": self.primary_decision_id,
            "verdict": self.verdict,
            "reason_code": self.reason_code,
            "checks": list(self.checks),
        }
        if include_hash:
            payload["critique_hash"] = canonical_hash(payload)
        return payload


@dataclass(frozen=True)
class SOARRun:
    """One SOAR evaluation pass for a proposal."""

    request_id: str
    proposal_ref: str
    domain_evaluations: tuple[DomainEvaluation, ...]
    d7_decision: D7Decision
    d7_critique: D7Critique
    binding: D7Binding
    input_refs: tuple[str, ...]

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": SOAR_RUN_SCHEMA,
            "schema_version": SOAR_SCHEMA_VERSION,
            "request_id": self.request_id,
            "proposal_ref": self.proposal_ref,
            "domain_evaluation_refs": [evaluation.evaluation_id for evaluation in self.domain_evaluations],
            "d7_decision_ref": self.d7_decision.decision_id,
            "d7_critique_ref": self.d7_critique.critique_id,
            "binding": self.binding,
            "input_refs": list(self.input_refs),
        }
        if include_hash:
            payload["run_hash"] = canonical_hash(payload)
        return payload


def proposal_content(proposal: Mapping[str, Any]) -> dict[str, Any]:
    payload = proposal.get("payload", {})
    content = payload.get("content", {})
    return dict(content) if isinstance(content, Mapping) else {}


__all__ = [
    "DOMAIN_EVAL_SCHEMA",
    "DOMAIN_IDS",
    "D7Binding",
    "D7Critique",
    "D7Decision",
    "D7_CRITIQUE_SCHEMA",
    "D7_DECISION_SCHEMA",
    "CritiqueVerdict",
    "DomainEvaluation",
    "DomainId",
    "SOARRun",
    "SOAR_RUN_SCHEMA",
    "SOAR_SCHEMA_VERSION",
    "proposal_content",
]

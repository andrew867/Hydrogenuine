"""RGL rule governance types — rules are not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

RGL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

RuleType = Literal[
    "invariant",
    "schema",
    "policy",
    "test",
    "proof_gate",
    "runbook",
    "authority_contract",
    "permit_contract",
    "documentation_claim",
    "unknown",
]
RuleStatus = Literal["active", "draft", "deprecated", "superseded", "stale", "unknown"]
ClaimType = Literal["compliance", "safety", "authority", "implementation", "test", "documentation", "exception"]
ClaimStatus = Literal["supported", "unsupported", "contradicted", "stale", "ambiguous", "unknown"]
DoctrineRiskType = Literal[
    "one_true_way_assertion",
    "doc_as_reality",
    "test_as_total_proof",
    "compliance_as_permission",
    "rule_overreach",
    "stale_rule_reliance",
    "unknown",
]

_ONE_TRUE_WAY_PATTERNS = (
    "the docs say it exists",
    "this is the correct way",
    "the book says so",
    "this rule grants permission",
)
_COMPLIANCE_AS_PERMISSION = (
    "i complied so",
    "followed the rule so i may",
    "compliance means permission",
)
_DOC_AS_REALITY = ("docs say it exists so it exists", "spec says allowed so no review")
_TEST_AS_PROOF = (
    "tests passed so the whole system is safe",
    "tests passed so safe",
    "green gate so production ready",
)


@dataclass(frozen=True)
class RuleReference:
    rule_id: str
    rule_type: RuleType
    title: str
    source_path: str
    source_hash: str
    owner_track: str
    status: RuleStatus
    scope: str
    evidence_refs: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.title, self.source_path, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rgl-rule-reference",
            "schema_version": RGL_SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "title": self.title,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "owner_track": self.owner_track,
            "status": self.status,
            "scope": self.scope,
            "evidence_refs": list(self.evidence_refs),
            "expires_at": self.expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class RuleClaim:
    claim_id: str
    actor_id: str
    claim_text: str
    referenced_rule_ids: tuple[str, ...]
    claim_type: ClaimType
    claim_status: ClaimStatus
    evidence_refs: tuple[str, ...]
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(self.claim_text, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "rgl-rule-claim",
            "schema_version": RGL_SCHEMA_VERSION,
            "claim_id": self.claim_id,
            "actor_id": self.actor_id,
            "claim_text": self.claim_text,
            "referenced_rule_ids": list(self.referenced_rule_ids),
            "claim_type": self.claim_type,
            "claim_status": self.claim_status,
            "evidence_refs": list(self.evidence_refs),
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("rgl.validation.secret", "secrets forbidden in rule records")


def classify_doctrine_risk(statement: str) -> DoctrineRiskType:
    lower = statement.lower()
    if any(p in lower for p in _DOC_AS_REALITY):
        return "doc_as_reality"
    if any(p in lower for p in _TEST_AS_PROOF):
        return "test_as_total_proof"
    if any(p in lower for p in _COMPLIANCE_AS_PERMISSION):
        return "compliance_as_permission"
    if any(p in lower for p in _ONE_TRUE_WAY_PATTERNS):
        return "one_true_way_assertion"
    if "old permit" in lower or "old rule" in lower:
        return "stale_rule_reliance"
    if "overreach" in lower or "override evidence" in lower:
        return "rule_overreach"
    return "unknown"


def rule_from_fixture(fixture: dict[str, str]) -> RuleReference:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return RuleReference(
        rule_id=fixture["rule_id"],
        rule_type=fixture.get("rule_type", "policy"),  # type: ignore[arg-type]
        title=fixture.get("title", "fixture rule"),
        source_path=fixture.get("source_path", "docs/planning/fixture"),
        source_hash=fixture.get("source_hash", "sha256:fixture"),
        owner_track=fixture.get("owner_track", "runtime"),
        status=fixture.get("status", "active"),  # type: ignore[arg-type]
        scope=fixture.get("scope", "batch"),
        evidence_refs=evidence,
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def claim_from_fixture(fixture: dict[str, str]) -> RuleClaim:
    raw = fixture.get("claim_text", "")
    rules = tuple(item.strip() for item in fixture.get("referenced_rule_ids", "rule-fixture").split(",") if item.strip())
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return RuleClaim(
        claim_id=fixture["claim_id"],
        actor_id=fixture.get("actor_id", "agent0"),
        claim_text=raw,
        referenced_rule_ids=rules,
        claim_type=fixture.get("claim_type", "compliance"),  # type: ignore[arg-type]
        claim_status=fixture.get("claim_status", "unsupported"),  # type: ignore[arg-type]
        evidence_refs=evidence,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "RGL_SCHEMA_VERSION",
    "RuleClaim",
    "RuleReference",
    "claim_from_fixture",
    "classify_doctrine_risk",
    "rule_from_fixture",
]

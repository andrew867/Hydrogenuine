"""Trust Boundary schema types — cargo, not command.

Every datum entering the organism is stamped with exactly one TaintLabel at
ingress. Only the three TRUSTED_* instruction-class labels may yield
instructions; everything else is data.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.trust_boundary.hash import tb_hash

TB_SCHEMA_VERSION = "trust_boundary/1"


class TaintLabel(str, Enum):
    # Instruction-class (trusted): only these three may produce instructions.
    TRUSTED_OPERATOR = "TRUSTED_OPERATOR"
    TRUSTED_SYSTEM_CONFIG = "TRUSTED_SYSTEM_CONFIG"
    TRUSTED_POLICY = "TRUSTED_POLICY"
    # Trusted data (not instructions).
    TRUSTED_PROOF = "TRUSTED_PROOF"
    # Untrusted data: cargo only.
    UNTRUSTED_WEB = "UNTRUSTED_WEB"
    UNTRUSTED_EMAIL = "UNTRUSTED_EMAIL"
    UNTRUSTED_SOCIAL = "UNTRUSTED_SOCIAL"
    UNTRUSTED_DOCUMENT = "UNTRUSTED_DOCUMENT"
    UNTRUSTED_MODEL_OUTPUT = "UNTRUSTED_MODEL_OUTPUT"
    UNTRUSTED_TOOL_OUTPUT = "UNTRUSTED_TOOL_OUTPUT"
    UNTRUSTED_MEMORY_RECALL = "UNTRUSTED_MEMORY_RECALL"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


# The only labels that may ever produce an instruction.
INSTRUCTION_CLASS_LABELS = frozenset(
    {TaintLabel.TRUSTED_OPERATOR, TaintLabel.TRUSTED_SYSTEM_CONFIG, TaintLabel.TRUSTED_POLICY}
)

# Labels permitted to originate a (governed) tool-request proposal.
TOOL_PROPOSER_LABELS = INSTRUCTION_CLASS_LABELS

# Trust rank for monotonicity: a relabel may never increase rank.
_TRUST_RANK: dict[TaintLabel, int] = {
    TaintLabel.TRUSTED_OPERATOR: 4,
    TaintLabel.TRUSTED_SYSTEM_CONFIG: 4,
    TaintLabel.TRUSTED_POLICY: 4,
    TaintLabel.TRUSTED_PROOF: 3,
    TaintLabel.UNTRUSTED_WEB: 1,
    TaintLabel.UNTRUSTED_EMAIL: 1,
    TaintLabel.UNTRUSTED_SOCIAL: 1,
    TaintLabel.UNTRUSTED_DOCUMENT: 1,
    TaintLabel.UNTRUSTED_MODEL_OUTPUT: 1,
    TaintLabel.UNTRUSTED_TOOL_OUTPUT: 1,
    TaintLabel.UNTRUSTED_MEMORY_RECALL: 1,
    TaintLabel.UNKNOWN_REVIEW_REQUIRED: 0,
}


def trust_rank(label: TaintLabel) -> int:
    return _TRUST_RANK[label]


def may_instruct(label: TaintLabel) -> bool:
    return label in INSTRUCTION_CLASS_LABELS


def may_propose_tool(label: TaintLabel) -> bool:
    return label in TOOL_PROPOSER_LABELS


class InjectionDisposition(str, Enum):
    CLEAN = "CLEAN"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"


class PolicyDisposition(str, Enum):
    ALLOW_AS_ADVISORY = "ALLOW_AS_ADVISORY"
    QUARANTINE = "QUARANTINE"
    DROP = "DROP"


class DegradedReason(str, Enum):
    NONE = "NONE"
    CLASSIFIER_OFFLINE = "CLASSIFIER_OFFLINE"
    REDACTION_OFFLINE = "REDACTION_OFFLINE"
    NETWORK_LOSS = "NETWORK_LOSS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass
class TaintedDatum:
    """External content + its provenance taint label + ingress metadata."""

    datum_id: str
    label: TaintLabel
    origin: str
    content: str
    ingress_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "tb-tainted-datum",
            "datum_id": self.datum_id,
            "label": self.label.value,
            "origin": self.origin,
            "content": self.content,
            "may_instruct": may_instruct(self.label),
            "may_propose_tool": may_propose_tool(self.label),
            "ingress_receipt_ref": self.ingress_receipt_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["content_hash"] = tb_hash(payload)
        return payload


@dataclass
class InjectionScanResult:
    disposition: InjectionDisposition
    score: float
    signals: list[str] = field(default_factory=list)
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "tb-injection-scan",
            "disposition": self.disposition.value,
            "score": self.score,
            "signals": self.signals,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class EvidenceClaim:
    claim: str
    source: str

    def to_payload(self) -> dict[str, Any]:
        return {"claim": self.claim, "source": self.source}


@dataclass
class EvidenceSummary:
    """Source-labelled, claim-attributed digest. No imperative content."""

    summary: str
    claims: list[EvidenceClaim] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "tb-evidence-summary",
            "summary": self.summary,
            "claims": [c.to_payload() for c in self.claims],
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class AdvisoryObject:
    """The only artifact external content may become. Carries no authority."""

    advisory_id: str
    source_label: TaintLabel
    origin: str
    evidence: EvidenceSummary
    policy_disposition: PolicyDisposition
    injection: InjectionScanResult
    redacted: bool

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "tb-advisory-object",
            "version": TB_SCHEMA_VERSION,
            "advisory_id": self.advisory_id,
            "source_label": self.source_label.value,
            "origin": self.origin,
            "evidence": self.evidence.to_payload(),
            "policy_disposition": self.policy_disposition.value,
            "injection": self.injection.to_payload(),
            "redacted": self.redacted,
            # An advisory is data: it is never instruction-class.
            "is_instruction": False,
            "may_propose_tool": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["content_hash"] = tb_hash(payload)
        return payload


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


__all__ = [
    "INSTRUCTION_CLASS_LABELS",
    "TB_SCHEMA_VERSION",
    "TOOL_PROPOSER_LABELS",
    "AdvisoryObject",
    "DegradedReason",
    "EvidenceClaim",
    "EvidenceSummary",
    "InjectionDisposition",
    "InjectionScanResult",
    "PolicyDisposition",
    "TaintLabel",
    "TaintedDatum",
    "may_instruct",
    "may_propose_tool",
    "new_id",
    "trust_rank",
]

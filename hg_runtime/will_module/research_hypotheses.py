"""Research hypothesis metadata — bounded claims only."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_runtime.will_module.schema import HypothesisEvidenceLevel

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class HypothesisClaimBoundary:
    claim: str
    evidence_level: HypothesisEvidenceLevel
    citations_required: bool = True
    proven: bool = False

    def to_payload(self) -> dict[str, Any]:
        if self.proven and self.evidence_level != HypothesisEvidenceLevel.LOCAL_EVIDENCE:
            raise ValueError("speculative claim cannot be marked proven without local evidence")
        return {
            "claim": self.claim,
            "evidence_level": self.evidence_level.value,
            "citations_required": self.citations_required,
            "proven": self.proven,
        }


@dataclass
class FalsificationCriterion:
    criterion: str
    measurable: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {"criterion": self.criterion, "measurable": self.measurable}


@dataclass
class NumericMappingPlanRef:
    plan_id: str
    symbolic_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "symbolic_only": self.symbolic_only}


@dataclass
class ResearchHypothesis:
    hypothesis_id: str
    title: str
    claims: list[HypothesisClaimBoundary] = field(default_factory=list)
    falsification: list[FalsificationCriterion] = field(default_factory=list)
    numeric_mapping: NumericMappingPlanRef | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "research-hypothesis",
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "claims": [c.to_payload() for c in self.claims],
            "falsification": [f.to_payload() for f in self.falsification],
            "numeric_mapping": self.numeric_mapping.to_payload() if self.numeric_mapping else None,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def load_research_hypothesis(path: str | Path) -> ResearchHypothesis:
    p = Path(path)
    if not p.is_file():
        p = WORKSPACE / path
    data = json.loads(p.read_text(encoding="utf-8"))
    claims = [
        HypothesisClaimBoundary(
            claim=c["claim"],
            evidence_level=HypothesisEvidenceLevel(c["evidence_level"]),
            citations_required=bool(c.get("citations_required", True)),
            proven=bool(c.get("proven", False)),
        )
        for c in data.get("claims", [])
    ]
    fals = [FalsificationCriterion(criterion=f["criterion"], measurable=bool(f.get("measurable", False))) for f in data.get("falsification", [])]
    mapping = None
    if data.get("numeric_mapping"):
        mapping = NumericMappingPlanRef(**data["numeric_mapping"])
    return ResearchHypothesis(
        hypothesis_id=data["hypothesis_id"],
        title=data.get("title", ""),
        claims=claims,
        falsification=fals,
        numeric_mapping=mapping,
    )


def validate_hypothesis_bounded(hypothesis: ResearchHypothesis) -> list[str]:
    failures: list[str] = []
    for claim in hypothesis.claims:
        if claim.proven and claim.evidence_level in {
            HypothesisEvidenceLevel.SPECULATIVE_BRIDGE,
            HypothesisEvidenceLevel.METAPHOR,
            HypothesisEvidenceLevel.SYMBOLIC_EXPLORATION,
            HypothesisEvidenceLevel.OPERATOR_MEANING,
        }:
            failures.append(f"overclaim:{claim.claim[:40]}")
    return failures


__all__ = [
    "FalsificationCriterion",
    "HypothesisClaimBoundary",
    "NumericMappingPlanRef",
    "ResearchHypothesis",
    "load_research_hypothesis",
    "validate_hypothesis_bounded",
]

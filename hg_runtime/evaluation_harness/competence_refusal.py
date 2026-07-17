"""P31 competence refusal engine — systematically refuses all overbroad claims."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.competence_claim_refusal import create_competence_claim_refusal
from hg_runtime.evaluation_harness.schemas import COMPETENCE_CLAIM_TYPES


def generate_all_refusals(model_id: str) -> list[dict[str, Any]]:
    return [
        create_competence_claim_refusal(
            model_id=model_id,
            claim_type=ct,
            reason=f"refused:{ct}",
        )
        for ct in sorted(COMPETENCE_CLAIM_TYPES)
    ]


def check_all_claim_types_covered(refusals: list[dict[str, Any]]) -> dict[str, Any]:
    covered = {r["claim_type"] for r in refusals}
    missing = COMPETENCE_CLAIM_TYPES - covered
    return {
        "covered": sorted(covered),
        "missing": sorted(missing),
        "all_covered": len(missing) == 0,
        "coverage_count": len(covered),
        "total_claim_types": len(COMPETENCE_CLAIM_TYPES),
    }

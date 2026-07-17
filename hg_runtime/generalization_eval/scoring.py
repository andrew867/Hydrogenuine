"""Rubric-backed transfer scoring.

Scoring is advisory measurement only. It requires evidence, refuses surface
similarity as proof, and never authorizes a tool or widens scope. A score is a
number against rubric criteria -- not a permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.generalization_eval.schemas import (
    TRANSFER_SCORE_SCHEMA,
    GeneralizationEvalError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)
from hg_runtime.generalization_eval.rubrics import create_rubric


def score_transfer(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
    similarity_only: bool = False,
) -> dict[str, Any]:
    """Score a transfer attempt against a rubric.

    ``payload`` carries ``score_id``, ``case_ref``, ``rubric`` (or its criteria),
    ``met_criteria`` (the rubric criteria the observation satisfied), and
    ``evidence_refs``. Surface similarity is never a passing path.
    """
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("score_id", "case_ref", "rubric", "met_criteria", "evidence_refs"))
    data = dict(payload)
    reject_authority_payload(data)

    if similarity_only or data.get("surface_similarity_only"):
        raise GeneralizationEvalError("surface_similarity_not_transfer")

    evidence_refs = as_list(data, "evidence_refs")
    if not evidence_refs:
        raise GeneralizationEvalError("transfer_score_requires_evidence")

    rubric = create_rubric(data["rubric"]) if isinstance(data["rubric"], Mapping) else None
    if rubric is None:
        raise GeneralizationEvalError("transfer_score_requires_rubric")
    criteria = list(rubric["criteria"])
    met = [c for c in as_list(data, "met_criteria") if c in criteria]
    score = len(met)
    passed = score >= int(rubric["pass_threshold"])

    return {
        "schema": TRANSFER_SCORE_SCHEMA,
        "score_id": data["score_id"],
        "case_ref": data["case_ref"],
        "rubric_ref": rubric.get("rubric_id"),
        "score": score,
        "max_score": len(criteria),
        "pass_threshold": int(rubric["pass_threshold"]),
        "passed": passed,
        "met_criteria": met,
        "evidence_refs": evidence_refs,
        "advisory_only": True,
        "claim_boundary": "generalization_eval_advisory_default",
        **neutral_flags(),
    }


__all__ = ["score_transfer"]

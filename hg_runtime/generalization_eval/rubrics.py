"""Transfer scoring rubrics.

A rubric is an explicit, criteria-based scoring contract. Transfer is scored
against rubric criteria, never against surface similarity. A rubric never
authorizes anything.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.generalization_eval.schemas import (
    TRANSFER_RUBRIC_SCHEMA,
    GeneralizationEvalError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def create_rubric(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("rubric_id", "criteria"))
    data = dict(payload)
    reject_authority_payload(data)
    criteria = as_list(data, "criteria")
    if not criteria:
        raise GeneralizationEvalError("rubric_requires_criteria")
    threshold = data.get("pass_threshold", len(criteria))
    if not isinstance(threshold, int) or threshold < 1 or threshold > len(criteria):
        raise GeneralizationEvalError("rubric_pass_threshold_out_of_range")
    data.setdefault("schema", TRANSFER_RUBRIC_SCHEMA)
    data["pass_threshold"] = threshold
    data.update(neutral_flags())
    return data


def has_rubric(case: Mapping[str, Any]) -> bool:
    """True if a transfer case carries a usable rubric (ref + non-empty criteria)."""
    rubric = case.get("rubric")
    if not isinstance(rubric, Mapping):
        return False
    return bool(case.get("rubric_ref")) and bool(rubric.get("criteria"))


__all__ = ["create_rubric", "has_rubric"]

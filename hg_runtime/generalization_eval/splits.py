"""Case split records.

A split record names which cases trained the pattern and which are held out for
evaluation. A held-out case that also appears in the training set is leakage and
is refused at split time.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.generalization_eval.schemas import (
    CASE_SPLIT_RECORD_SCHEMA,
    GeneralizationEvalError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def create_case_split(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("split_id", "train_refs", "heldout_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    train = set(as_list(data, "train_refs"))
    heldout = set(as_list(data, "heldout_refs"))
    if not heldout:
        raise GeneralizationEvalError("case_split_requires_heldout_refs")
    overlap = sorted(train & heldout)
    if overlap:
        raise GeneralizationEvalError(f"case_split_train_heldout_overlap:{','.join(map(str, overlap))}")
    data.setdefault("schema", CASE_SPLIT_RECORD_SCHEMA)
    data.update(neutral_flags())
    return data


def require_split_record(split_ref: Any) -> None:
    if not str(split_ref or ""):
        raise GeneralizationEvalError("case_split_record_required")


__all__ = ["create_case_split", "require_split_record"]

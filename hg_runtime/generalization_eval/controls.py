"""Negative and positive control cases.

A negative control is a task the pattern *should not* solve (e.g. a biased
entropy source, an off-distribution prompt). It must fail; if it "passes", the
harness is measuring leakage or surface similarity, not transfer. A positive
control is a task the pattern should solve under its rubric. Both are recorded.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.generalization_eval.schemas import (
    NEGATIVE_CONTROL_CASE_SCHEMA,
    POSITIVE_CONTROL_CASE_SCHEMA,
    GeneralizationEvalError,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def run_negative_control(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a negative control. It is expected to FAIL.

    ``observed_outcome`` is the measured result ("fail"/"pass"). The control is
    healthy only when the observed outcome is a failure. Either way the result is
    recorded and never hidden.
    """
    require_fields(payload, ("control_id", "case_ref", "observed_outcome"))
    data = dict(payload)
    reject_authority_payload(data)
    observed = str(data["observed_outcome"]).strip().lower()
    passed_as_expected = observed in {"fail", "failed", "no_transfer", "rejected"}
    return {
        "schema": NEGATIVE_CONTROL_CASE_SCHEMA,
        "control_id": data["control_id"],
        "case_ref": data["case_ref"],
        "expected": "fail",
        "observed_outcome": observed,
        "passed_as_expected": passed_as_expected,
        "silent_pass": not passed_as_expected,
        "recorded": True,
        "hidden": False,
        "claim_boundary": "generalization_eval_advisory_default",
        **neutral_flags(),
    }


def run_positive_control(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a positive control. It is expected to PASS under its rubric."""
    require_fields(payload, ("control_id", "case_ref", "observed_outcome", "rubric_ref"))
    data = dict(payload)
    reject_authority_payload(data)
    if not str(data.get("rubric_ref", "")):
        raise GeneralizationEvalError("positive_control_requires_rubric")
    observed = str(data["observed_outcome"]).strip().lower()
    passed_as_expected = observed in {"pass", "passed", "transferred", "generalized"}
    return {
        "schema": POSITIVE_CONTROL_CASE_SCHEMA,
        "control_id": data["control_id"],
        "case_ref": data["case_ref"],
        "rubric_ref": data["rubric_ref"],
        "expected": "pass",
        "observed_outcome": observed,
        "passed_as_expected": passed_as_expected,
        "recorded": True,
        "hidden": False,
        "claim_boundary": "generalization_eval_advisory_default",
        **neutral_flags(),
    }


__all__ = ["run_negative_control", "run_positive_control"]

"""Claim scope records.

A claim scope binds any competence claim to the exact held-out cases that passed.
A single success cannot be claimed as general competence; a broad-competence claim
is refused outright. Scope is evidence about what was tested, not a promise about
what was not.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.generalization_eval.schemas import (
    CLAIM_SCOPE_RECORD_SCHEMA,
    GeneralizationEvalError,
    as_list,
    is_broad_scope,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def build_claim_scope(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build a bounded claim scope from the held-out cases that passed.

    ``asserted_scope`` defaults to "bounded". Asking for a broad/general scope is
    refused; if only one (or zero) cases passed, asserting generality raises the
    single-success refusal first.
    """
    require_fields(payload, ("claim_id", "passed_case_refs", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    passed = as_list(data, "passed_case_refs")
    asserted = str(data.get("asserted_scope", "bounded"))
    if is_broad_scope(asserted) or data.get("general_competence"):
        if len(passed) <= 1:
            raise GeneralizationEvalError("single_success_cannot_claim_general_competence")
        raise GeneralizationEvalError("broad_competence_claim_rejected")

    return {
        "schema": CLAIM_SCOPE_RECORD_SCHEMA,
        "claim_id": data["claim_id"],
        "scope_kind": "bounded",
        "case_refs": list(passed),
        "claim": data.get("claim", "transfer demonstrated on the listed held-out cases only"),
        "claim_boundary": data["claim_boundary"],
        "generalizes_beyond_tested_cases": False,
        **neutral_flags(),
    }


def bounded_claim_scope(claim_id: str, results: list[Mapping[str, Any]], *, claim_boundary: str) -> dict[str, Any]:
    """Derive a claim scope from a result set, including only cases that passed."""
    passed = [r.get("case_ref") for r in results if str(r.get("status", "")).lower() in {"green", "passed", "pass", "transferred", "generalized"}]
    return build_claim_scope(
        {
            "claim_id": claim_id,
            "passed_case_refs": passed,
            "claim_boundary": claim_boundary,
        }
    )


__all__ = ["bounded_claim_scope", "build_claim_scope"]

"""LHRE-03 / CAGI-56 vessel engine — creates and validates sealed evaluation vessels."""

from __future__ import annotations

from hg_runtime.external_evaluation_vessel.schemas import (
    VESSEL_STATUS_SEALED,
    EvaluationVesselError,
    reject_vessel_authority,
)


def validate_vessel(vessel: dict) -> list[str]:
    issues = []
    if not vessel.get("vessel_id"):
        issues.append("missing_vessel_id")
    if vessel.get("status") != VESSEL_STATUS_SEALED:
        issues.append("vessel_must_be_sealed")
    if vessel.get("upload_to_network"):
        issues.append("upload_forbidden")
    if vessel.get("send_to_evaluator"):
        issues.append("send_forbidden")
    reject_vessel_authority(vessel)
    return issues


def validate_result(result: dict) -> list[str]:
    issues = []
    if result.get("is_truth"):
        issues.append("result_must_not_claim_truth")
    if result.get("is_competence"):
        issues.append("result_must_not_claim_competence")
    return issues

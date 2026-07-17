"""P71 candidate-AGI claim boundary domain logic."""

from __future__ import annotations

from hg_runtime.candidate_agi_claim_boundary.schemas import (
    ALLOWED_CLAIMS,
    PROHIBITED_CLAIMS,
    reject_prohibited_claim,
)


def validate_capability_matrix(matrix: dict) -> list[str]:
    issues = []
    if not matrix.get("matrix_id"):
        issues.append("missing_matrix_id")
    return issues


def validate_claim_boundary(boundary: dict) -> list[str]:
    issues = []
    if not boundary.get("boundary_id"):
        issues.append("missing_boundary_id")
    reject_prohibited_claim(boundary)
    return issues


def validate_known_debt(register: dict) -> list[str]:
    issues = []
    if not register.get("register_id"):
        issues.append("missing_register_id")
    for item in register.get("items", []):
        if not item.get("preserved"):
            issues.append(f"debt_not_preserved:{item.get('debt_id')}")
    return issues


def validate_public_safe_summary(summary: dict) -> list[str]:
    issues = []
    if not summary.get("summary_id"):
        issues.append("missing_summary_id")
    if summary.get("claims_agi"):
        issues.append("public_summary_must_not_claim_agi")
    if summary.get("claims_consciousness"):
        issues.append("public_summary_must_not_claim_consciousness")
    if summary.get("claims_sovereignty"):
        issues.append("public_summary_must_not_claim_sovereignty")
    if summary.get("claims_deployed"):
        issues.append("public_summary_must_not_claim_deployed")
    return issues


def detect_prohibited_claim(claim_text: str) -> str | None:
    lower = claim_text.lower()
    for prohibited in PROHIBITED_CLAIMS:
        if prohibited.replace("_", " ") in lower or prohibited.replace("_", "-") in lower:
            return prohibited
    return None


def is_allowed_claim(claim: str) -> bool:
    return claim in ALLOWED_CLAIMS

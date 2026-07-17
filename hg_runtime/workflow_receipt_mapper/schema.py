"""Workflow intake schema (workflow_receipt_intake_v1) — fail-closed validation.

Boundary defaults are mandatory: no customer deployment, no production certification,
no model correctness, no production operator auth, no unscoped external effects,
source is receipt not truth.
"""
from __future__ import annotations

import re
from typing import Any

RISK_LEVELS = {"low", "medium", "high"}
DATA_SENSITIVITY = {"synthetic", "internal", "confidential"}
INTEGRATION_STATUSES = {"native", "wrapper_roadmap", "manual_review_only", "not_supported"}

REQUIRED_FIELDS = [
    "workflow_id", "title", "description", "domain", "operator_goal", "agent_role",
    "input_sources", "model_outputs", "proposed_actions", "external_effects",
    "human_review_points", "authority_sources", "risk_level", "data_sensitivity",
    "success_criteria", "failure_modes", "must_refuse_conditions",
    "must_hold_conditions", "required_receipts", "proof_bundle_expectations",
    "integration_status", "claim_boundaries",
]

REQUIRED_BOUNDARIES = [
    "no_customer_deployment", "no_production_certification", "no_model_correctness",
    "no_production_operator_auth", "no_unscoped_external_effects",
    "source_is_receipt_not_truth",
]

# Redaction: obvious secret / real-data markers that must never appear in an intake.
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|password|bearer\s+[A-Za-z0-9_\-]{16,})\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\baws_secret_access_key\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b(?=.*(?i:card|credit|pan))"),
]
REAL_DATA_MARKERS = [
    re.compile(r"(?i)\breal customer\b"), re.compile(r"(?i)\bproduction data\b"),
    re.compile(r"(?i)\bPII export\b"),
]


class IntakeError(ValueError):
    """Intake is invalid or unsafe; mapping must not start."""


def validate_intake(intake: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in intake:
            errors.append(f"missing required field: {f}")
    if errors:
        return errors

    if intake["risk_level"] not in RISK_LEVELS:
        errors.append(f"risk_level must be one of {sorted(RISK_LEVELS)}")
    if intake["data_sensitivity"] not in DATA_SENSITIVITY:
        errors.append(f"data_sensitivity must be one of {sorted(DATA_SENSITIVITY)}")
    if intake["integration_status"] not in INTEGRATION_STATUSES:
        errors.append(f"integration_status must be one of {sorted(INTEGRATION_STATUSES)}")

    cb = intake["claim_boundaries"]
    for key in REQUIRED_BOUNDARIES:
        if cb.get(key) is not True:
            errors.append(f"claim_boundaries.{key} must be true")

    for list_field in ("input_sources", "model_outputs", "proposed_actions",
                      "must_refuse_conditions", "must_hold_conditions",
                      "required_receipts"):
        if not isinstance(intake[list_field], list) or not intake[list_field]:
            errors.append(f"{list_field} must be a non-empty list")

    if intake["data_sensitivity"] != "synthetic" and not intake.get("synthetic_data"):
        # design-partner intakes must be sanitized before mapping in this tool
        errors.append("non-synthetic data_sensitivity requires prior sanitization; "
                      "this tool accepts synthetic/sanitized intakes only")
    return errors


def scan_for_secrets(intake: dict[str, Any]) -> list[str]:
    """Return findings; any finding blocks mapping (fail closed)."""
    import json
    blob = json.dumps(intake)
    findings = []
    for pat in SECRET_PATTERNS:
        m = pat.search(blob)
        if m:
            findings.append(f"secret_marker:{pat.pattern[:40]}")
    for pat in REAL_DATA_MARKERS:
        if pat.search(blob):
            findings.append(f"real_data_marker:{pat.pattern[:40]}")
    return findings


def redact_intake(intake: dict[str, Any]) -> dict[str, Any]:
    """Produce the shareable copy: drop free-form private notes, keep the map inputs."""
    redacted = {k: v for k, v in intake.items() if not k.startswith("private_")}
    redacted["redaction"] = {
        "private_fields_removed": sorted(k for k in intake if k.startswith("private_")),
        "note": "synthetic example data only; contains no genuine customer records; no credentials",
    }
    return redacted


def load_intake(intake: dict[str, Any]) -> dict[str, Any]:
    errors = validate_intake(intake)
    if errors:
        raise IntakeError("; ".join(errors))
    findings = scan_for_secrets(intake)
    if findings:
        raise IntakeError("unsafe intake: " + "; ".join(findings))
    return intake

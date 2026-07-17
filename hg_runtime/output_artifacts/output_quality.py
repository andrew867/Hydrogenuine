"""Deterministic output quality evaluation."""

from __future__ import annotations

import re
from typing import Union

from hg_runtime.output_artifacts.redaction import (
    contains_external_permission_claim,
    contains_publish_claim,
    scan_artifact_body,
)
from hg_runtime.output_artifacts.schema import (
    DraftArtifact,
    NotesArtifact,
    OutputQualityReceipt,
    ThreadContinuationArtifact,
    body_hash,
    load_output_quality_policy,
    new_quality_receipt_id,
)
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

ArtifactUnion = Union[DraftArtifact, NotesArtifact, ThreadContinuationArtifact]

BOILERPLATE_PATTERNS = (
    r"^lorem ipsum",
    r"^todo\b",
    r"^placeholder\b",
    r"^draft goes here",
    r"^sample text",
    r"^overnight candidate",
    r"overnight comment draft from local thread context",
    r"overnight reply draft from message center fixture",
)

FIXTURE_DENYLIST = (
    "Overnight candidate",
    "Overnight comment draft from local thread context",
    "Overnight reply draft from message center fixture",
    "fixture_runtime_truth",
    "message center fixture",
)


def _is_boilerplate(body: str) -> bool:
    stripped = body.strip().lower()
    if len(stripped) < 3:
        return True
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, stripped, re.IGNORECASE):
            return True
    return False


def _is_fixture_text(body: str) -> bool:
    for phrase in FIXTURE_DENYLIST:
        if phrase.lower() in body.lower():
            return True
    return False


def evaluate_output_quality(artifact: ArtifactUnion) -> OutputQualityReceipt:
    """Evaluate artifact quality deterministically — no LLM."""
    policy = load_output_quality_policy()
    checks: list[str] = []
    reasons: list[str] = []
    body = artifact.body.strip()
    checks.append("nonempty_body")
    checks.append("minimum_length")
    checks.append("boilerplate_scan")
    checks.append("fixture_denylist")
    checks.append("source_refs")
    checks.append("provider_receipts")
    checks.append("secret_scan")
    checks.append("cot_scan")
    checks.append("external_permission_scan")
    checks.append("publish_claim_scan")
    checks.append("body_hash")

    verdict = "GREEN_OUTPUT_QUALITY_PASSED"

    if not body:
        verdict = "RED_OUTPUT_EMPTY"
        reasons.append("empty body")
    elif _is_fixture_text(body):
        verdict = "RED_OUTPUT_FIXTURE_TEXT"
        reasons.append("fixture denylist match")
    elif _is_boilerplate(body):
        verdict = "RED_OUTPUT_BOILERPLATE"
        reasons.append("boilerplate detected")
    elif len(body) < int(policy.get("minimum_meaningful_length", 12)):
        verdict = "RED_OUTPUT_EMPTY"
        reasons.append("body too short")

    has_secret, has_cot = scan_artifact_body(body)
    if "scratchpad" in body.lower() or "chain_of_thought" in body.lower():
        has_cot = True
    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and has_secret:
        verdict = "RED_OUTPUT_SECRET"
        reasons.append("secret detected")
    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and has_cot:
        verdict = "RED_OUTPUT_HIDDEN_COT"
        reasons.append("hidden cot detected")

    source_refs = list(artifact.source_refs)
    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and policy.get("source_refs_required") and not source_refs:
        verdict = "RED_OUTPUT_SOURCELESS"
        reasons.append("source refs missing")

    provider_refs = list(artifact.provider_receipt_refs)
    if (
        verdict == "GREEN_OUTPUT_QUALITY_PASSED"
        and policy.get("provider_receipt_required_for_model_artifacts")
        and not provider_refs
    ):
        verdict = "RED_OUTPUT_PROVIDER_RECEIPT_MISSING"
        reasons.append("provider receipt missing")

    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and contains_external_permission_claim(body):
        if not policy.get("external_permission_claim_allowed", False):
            verdict = "RED_OUTPUT_EXTERNAL_PERMISSION_CLAIM"
            reasons.append("external permission claim")

    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and contains_publish_claim(body):
        if not policy.get("publish_claim_allowed", False):
            verdict = "RED_OUTPUT_EXTERNAL_PERMISSION_CLAIM"
            reasons.append("publish claim")

    expected_hash = body_hash(body)
    if verdict == "GREEN_OUTPUT_QUALITY_PASSED" and artifact.body_hash != expected_hash:
        verdict = "RED_ARTIFACT_HASH_MISSING"
        reasons.append("body hash mismatch")

    if not artifact.hash:
        verdict = "RED_ARTIFACT_HASH_MISSING"
        reasons.append("artifact hash missing")

    return OutputQualityReceipt(
        quality_receipt_id=new_quality_receipt_id(),
        artifact_ref=artifact.artifact_id,
        artifact_hash=artifact.hash,
        checks_run=checks,
        verdict=verdict,
        reasons=reasons,
        length_chars=len(body),
        source_ref_count=len(source_refs),
        provider_receipt_count=len(provider_refs),
        contains_secret=has_secret,
        contains_hidden_cot=has_cot,
        contains_fixture_text=_is_fixture_text(body),
        contains_external_permission_claim=contains_external_permission_claim(body),
        created_at=_now_iso(),
    ).with_hash()


__all__ = ["BOILERPLATE_PATTERNS", "FIXTURE_DENYLIST", "evaluate_output_quality"]

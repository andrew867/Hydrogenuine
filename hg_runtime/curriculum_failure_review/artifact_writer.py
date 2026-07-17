"""AEC-05 / CAGI-52 artifact writer — builds failure review receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.curriculum_failure_review.reviewer import (
    categorize_failures,
    severity_rank,
    validate_failure_record,
    validate_root_cause,
)
from hg_runtime.curriculum_failure_review.schemas import (
    FAILURE_IS_NOT_DEFECT,
    REVIEW_IS_NOT_FIX,
    ROOT_CAUSE_IS_NOT_DIAGNOSIS,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_failure_review_artifacts(
    failures: list[dict],
    root_causes: list[dict],
    reviews: list[dict],
) -> dict:
    validated_failures = []
    for f in failures:
        issues = validate_failure_record(f)
        validated_failures.append({"record": f, "valid": not issues, "issues": issues})

    validated_causes = []
    for rc in root_causes:
        issues = validate_root_cause(rc)
        validated_causes.append({"hypothesis": rc, "valid": not issues, "issues": issues})

    categories = categorize_failures(failures)
    ranked = severity_rank(failures)

    artifacts = {
        "failures": validated_failures,
        "failure_count": len(validated_failures),
        "root_causes": validated_causes,
        "root_cause_count": len(validated_causes),
        "review_count": len(reviews),
        "categories": categories,
        "severity_order": [r["failure_id"] for r in ranked],
        "all_failures_queued": all(v["valid"] for v in validated_failures),
        "all_causes_hypothesis": all(v["valid"] for v in validated_causes),
        "no_fixes_applied": all(not r.get("apply_fix") for r in reviews),
        "boundary_assertions": {
            "failure_is_not_defect": FAILURE_IS_NOT_DEFECT,
            "review_is_not_fix": REVIEW_IS_NOT_FIX,
            "root_cause_is_not_diagnosis": ROOT_CAUSE_IS_NOT_DIAGNOSIS,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    hits = []
    for pattern in ("sk-", "api_key=", "Bearer ", "token=", "password="):
        if pattern.lower() in text.lower():
            hits.append(pattern)
    return hits

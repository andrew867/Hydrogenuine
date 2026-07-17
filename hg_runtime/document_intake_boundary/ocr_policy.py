"""DIB-5 OCR disabled policy."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_ocr_disabled_policy(*, policy_id: str = "dib-ocr-disabled-policy-v1") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "ocr_disabled_policy_v1",
        "policy_id": policy_id,
        "ocr_enabled": False,
        "ocr_dependency_allowed": False,
        "ocr_confidence_treated_as_truth": False,
        "ocr_output_treated_as_truth": False,
        "doctrine_note": "OCR remains disabled.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy

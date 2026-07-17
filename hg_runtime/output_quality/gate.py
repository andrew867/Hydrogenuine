"""Output quality gate — GREEN only when classification actually ran.

Rejects fake green: a gate that classified nothing returns RED.
"""

from __future__ import annotations

from hg_runtime.output_quality.schemas import validate_receipt, REJECT_CLASSES

VERDICT_GREEN = "GREEN_OUTPUT_QUALITY_ADJUDICATOR_READY"
VERDICT_RED = "RED_OUTPUT_QUALITY_ADJUDICATOR_FAILED"


def evaluate_gate(receipts: list[dict]) -> dict:
    if not receipts:
        return {
            "verdict": VERDICT_RED,
            "reason": "fake_green_rejected: no receipts classified",
            "receipt_count": 0,
            "failures": ["no_receipts_classified"],
        }

    failures = []
    for i, r in enumerate(receipts):
        errs = validate_receipt(r)
        if errs:
            failures.append(f"receipt[{i}]: {errs}")
        if r.get("grants_authority"):
            failures.append(f"receipt[{i}]: grants_authority is True")
        if r.get("promotes_to_knowledge"):
            failures.append(f"receipt[{i}]: promotes_to_knowledge is True")
        if r.get("model_output_treated_as_truth"):
            failures.append(f"receipt[{i}]: model_output_treated_as_truth is True")

    rejected_count = sum(1 for r in receipts if r.get("quality_class") in REJECT_CLASSES)
    weak_count = sum(1 for r in receipts if r.get("quality_class") in
                     {"LOW_VALUE_TRIAGE", "RETRY_WITH_DIFFERENT_MODEL"})

    verdict = VERDICT_GREEN if not failures else VERDICT_RED
    return {
        "verdict": verdict,
        "reason": "classification_ran" if not failures else "; ".join(failures[:5]),
        "receipt_count": len(receipts),
        "rejected_count": rejected_count,
        "weak_count": weak_count,
        "failures": failures,
    }

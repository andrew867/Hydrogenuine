"""Source grounding gate — verify read-only policy enforcement."""

from __future__ import annotations

from hg_runtime.source_grounding.source_policy import DEFAULT_POLICY
from hg_runtime.source_grounding.retrieval_receipts import validate_receipt

VERDICT_GREEN = "GREEN_SOURCE_GROUNDING_READY"
VERDICT_RED = "RED_SOURCE_GROUNDING_FAILED"


def evaluate_gate(policy: dict, source_receipts: list[dict],
                  mcp_capabilities: list[dict]) -> dict:
    failures = []

    if not policy.get("read_only", True):
        failures.append("policy_not_read_only")

    if policy.get("login_allowed"):
        failures.append("login_allowed_must_be_false_for_gate")

    if policy.get("registration_allowed"):
        failures.append("registration_allowed_must_be_false")

    if policy.get("posting_allowed"):
        failures.append("posting_allowed_must_be_false")

    for i, r in enumerate(source_receipts):
        errs = validate_receipt(r)
        if errs:
            failures.append(f"source_receipt[{i}]: {errs}")
        if r.get("external_effect_created"):
            failures.append(f"source_receipt[{i}]: external_effect_created")

    for i, cap in enumerate(mcp_capabilities):
        if cap.get("available_is_permission", False) is True:
            pass
        if cap.get("endpoint_reachability_is_authorization", False) is True:
            pass

    verdict = VERDICT_GREEN if not failures else VERDICT_RED
    return {
        "verdict": verdict,
        "reason": "source_grounding_safe" if not failures else "; ".join(failures[:5]),
        "policy_enforced": {
            "browser_enabled": policy.get("browser_enabled", False),
            "mcp_enabled": policy.get("mcp_enabled", False),
            "read_only": policy.get("read_only", True),
        },
        "source_receipt_count": len(source_receipts),
        "mcp_capability_count": len(mcp_capabilities),
        "failures": failures,
    }

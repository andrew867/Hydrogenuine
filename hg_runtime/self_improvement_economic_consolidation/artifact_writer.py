"""SIEW-03 / CAGI-65 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.self_improvement_economic_consolidation.integrator import (
    aggregate_risk_benefit,
    validate_link,
    validate_receipt,
)
from hg_runtime.self_improvement_economic_consolidation.schemas import (
    ECONOMIC_WORK_REMAINS_SIMULATED,
    NO_AUTHORITY_MUTATION,
    NO_CUSTOMER_WORK,
    NO_DEPLOYMENT_PERMISSION,
    NO_MONEY_MOVEMENT,
    NO_PATCH_APPLICATION,
    SELF_IMPROVEMENT_REMAINS_ADVISORY,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_consolidation_artifacts(
    receipts: list[dict],
    links: list[dict],
) -> dict:
    validated_receipts = []
    for r in receipts:
        issues = validate_receipt(r)
        validated_receipts.append({"receipt": r, "valid": not issues, "issues": issues})
    validated_links = []
    for lnk in links:
        issues = validate_link(lnk)
        validated_links.append({"link": lnk, "valid": not issues, "issues": issues})
    risk_benefit = aggregate_risk_benefit(receipts)
    result = {
        "receipts": validated_receipts,
        "links": validated_links,
        "receipt_count": len(validated_receipts),
        "link_count": len(validated_links),
        "all_receipts_green": all(v["valid"] for v in validated_receipts),
        "all_links_valid": all(v["valid"] for v in validated_links),
        "risk_benefit_summary": risk_benefit,
        "boundary_assertions": {
            "self_improvement_remains_advisory": SELF_IMPROVEMENT_REMAINS_ADVISORY,
            "economic_work_remains_simulated": ECONOMIC_WORK_REMAINS_SIMULATED,
            "no_patch_application": NO_PATCH_APPLICATION,
            "no_authority_mutation": NO_AUTHORITY_MUTATION,
            "no_customer_work": NO_CUSTOMER_WORK,
            "no_money_movement": NO_MONEY_MOVEMENT,
            "no_deployment_permission": NO_DEPLOYMENT_PERMISSION,
        },
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]

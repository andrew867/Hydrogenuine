"""P71 candidate-AGI claim boundary artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.candidate_agi_claim_boundary.boundary import (
    validate_capability_matrix,
    validate_claim_boundary,
    validate_known_debt,
    validate_public_safe_summary,
)
from hg_runtime.candidate_agi_claim_boundary.schemas import reject_prohibited_claim


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_claim_boundary_artifacts(
    matrices: list[dict],
    boundaries: list[dict],
    debts: list[dict],
    summaries: list[dict],
) -> dict:
    for b in boundaries:
        reject_prohibited_claim(b)
    v_mx = [{"matrix": m, "valid": not validate_capability_matrix(m), "issues": validate_capability_matrix(m)} for m in matrices]
    v_bd = [{"boundary": b, "valid": not validate_claim_boundary(b), "issues": validate_claim_boundary(b)} for b in boundaries]
    v_dt = [{"debt": d, "valid": not validate_known_debt(d), "issues": validate_known_debt(d)} for d in debts]
    v_sm = [{"summary": s, "valid": not validate_public_safe_summary(s), "issues": validate_public_safe_summary(s)} for s in summaries]
    result = {
        "matrices": v_mx, "boundaries": v_bd, "debts": v_dt, "summaries": v_sm,
        "all_matrices_valid": all(v["valid"] for v in v_mx),
        "all_boundaries_valid": all(v["valid"] for v in v_bd),
        "all_debts_valid": all(v["valid"] for v in v_dt),
        "all_summaries_valid": all(v["valid"] for v in v_sm),
        "no_agi_claim": all(not b.get("claims_agi") for b in boundaries),
        "no_consciousness_claim": all(not b.get("claims_consciousness") for b in boundaries),
        "no_sovereignty_claim": all(not b.get("claims_sovereignty") for b in boundaries),
        "no_deployment_claim": all(not b.get("claims_deployed") for b in boundaries),
        "known_debt_preserved": all(
            all(item.get("preserved") for item in d.get("items", []))
            for d in debts
        ),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]

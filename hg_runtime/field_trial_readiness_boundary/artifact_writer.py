"""P69 field trial readiness boundary artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.field_trial_readiness_boundary.readiness import (
    validate_field_scenario,
    validate_readiness_checklist,
    validate_readiness_gap,
    validate_rehearsal,
)
from hg_runtime.field_trial_readiness_boundary.schemas import reject_readiness_overreach


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_readiness_artifacts(
    checklists: list[dict],
    scenarios: list[dict],
    rehearsals: list[dict],
    gaps: list[dict],
) -> dict:
    for c in checklists:
        reject_readiness_overreach(c)
    v_cl = [{"checklist": c, "valid": not validate_readiness_checklist(c), "issues": validate_readiness_checklist(c)} for c in checklists]
    v_sc = [{"scenario": s, "valid": not validate_field_scenario(s), "issues": validate_field_scenario(s)} for s in scenarios]
    v_rh = [{"rehearsal": r, "valid": not validate_rehearsal(r), "issues": validate_rehearsal(r)} for r in rehearsals]
    v_gp = [{"gap": g, "valid": not validate_readiness_gap(g), "issues": validate_readiness_gap(g)} for g in gaps]
    result = {
        "checklists": v_cl, "scenarios": v_sc, "rehearsals": v_rh, "gaps": v_gp,
        "all_checklists_valid": all(v["valid"] for v in v_cl),
        "all_scenarios_valid": all(v["valid"] for v in v_sc),
        "all_rehearsals_valid": all(v["valid"] for v in v_rh),
        "all_gaps_valid": all(v["valid"] for v in v_gp),
        "no_live_trial": all(not c.get("is_live_trial") for c in checklists),
        "no_deployment_permission": all(not c.get("is_deployment_permission") for c in checklists),
        "operator_approval_required": all(c.get("operator_approval_required") for c in checklists),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]

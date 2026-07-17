"""CLIFT-02 / CAGI-67 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.containment_capability_boundary.boundary import (
    validate_capability_declaration,
    validate_containment_mode,
)
from hg_runtime.containment_capability_boundary.schemas import (
    reject_containment_escape,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_containment_artifacts(
    declarations: list[dict],
    mode_record: dict,
    snapshot: dict,
) -> dict:
    for d in declarations:
        reject_containment_escape(d)
    validated_decls = []
    for d in declarations:
        issues = validate_capability_declaration(d)
        validated_decls.append({"declaration": d, "valid": not issues, "issues": issues})
    mode_issues = validate_containment_mode(mode_record)
    result = {
        "declarations": validated_decls,
        "declaration_count": len(validated_decls),
        "all_declarations_valid": all(v["valid"] for v in validated_decls),
        "mode_record": mode_record,
        "mode_valid": not mode_issues,
        "mode_issues": mode_issues,
        "no_provider_enabled": not mode_record.get("provider_enabled"),
        "no_network_enabled": not mode_record.get("network_enabled"),
        "no_tool_authorized": not mode_record.get("tool_authorized"),
        "no_hg_local": not mode_record.get("hg_local_accessible"),
        "no_deployment_permission": not mode_record.get("deployment_permission"),
        "snapshot": snapshot,
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]

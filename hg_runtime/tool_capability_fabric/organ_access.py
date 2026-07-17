"""Organ tool access allowlists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
MANIFEST_PATH = WORKSPACE / "configs" / "organs" / "agent0_dev_organ_manifest.json"

# Default allowlists when manifest omits allowed_capabilities
DEFAULT_ORGAN_CAPABILITIES: dict[str, list[str]] = {
    "organ:Agent0": [
        "capability_manifest",
        "local_memory_read",
        "memory_write_request",
        "storage_read",
        "proof_read",
        "proof_verify",
        "artifact_read",
        "knowledge_lookup",
        "social_draft",
        "social_publish_request",
        "web_search_request",
        "operator_message",
        "model_inference",
        "shell_safe",
        "email_draft",
        "account_creation_request",
    ],
    "organ:AIS": ["capability_manifest", "model_inference"],
    "organ:IMS": ["capability_manifest", "model_inference"],
    "organ:MBS": ["capability_manifest"],
    "organ:OEF": ["proof_read", "knowledge_lookup", "model_inference"],
    "organ:NRV": ["capability_manifest"],
    "organ:HRT": [],
    "organ:RSP": ["capability_manifest", "model_inference"],
    "organ:CIR": ["capability_manifest"],
    "organ:DBB": ["storage_read", "artifact_read", "capability_manifest"],
    "organ:ISB": ["knowledge_lookup", "model_inference"],
    "organ:OCF": ["proof_read", "model_inference"],
    "organ:OIR": ["proof_read", "model_inference"],
    "organ:MBR": ["proof_read", "model_inference"],
    "organ:storage_observer": ["storage_read", "proof_read"],
    "organ:authority_observer": ["proof_read"],
    "organ:provider_fabric_observer": ["capability_manifest", "model_inference"],
}


def load_organ_allowlists(manifest_path: Path | None = None) -> dict[str, list[str]]:
    path = manifest_path or MANIFEST_PATH
    if not path.is_file():
        return dict(DEFAULT_ORGAN_CAPABILITIES)
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for organ in data.get("organs", []):
        organ_id = organ["organ_id"]
        caps = organ.get("allowed_capabilities")
        if caps is None:
            caps = DEFAULT_ORGAN_CAPABILITIES.get(organ_id, [])
        result[organ_id] = list(caps)
    return result


def organ_may_request(organ_id: str, capability_id: str, allowlists: dict[str, list[str]] | None = None) -> bool:
    lists = allowlists or load_organ_allowlists()
    allowed = lists.get(organ_id)
    if allowed is None:
        return False
    if not allowed:
        return False
    return capability_id in allowed


def out_of_scope_denial_detail(organ_id: str, capability_id: str) -> dict[str, Any]:
    return {
        "denial_reason": "ORGAN_SCOPE_DENIED",
        "explanation": f"{organ_id} is not allowlisted for {capability_id}",
        "safe_alternative": "request capability_manifest or operator_message to escalate",
        "missing_requirement": "organ_allowlist",
    }


__all__ = [
    "DEFAULT_ORGAN_CAPABILITIES",
    "load_organ_allowlists",
    "organ_may_request",
    "out_of_scope_denial_detail",
]

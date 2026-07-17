"""Local LM Studio shadow soak adapter.

Loopback-only. No remote providers. No API keys.
Model output is not truth. Local inference is not authority.
Model willingness is not permission.
"""

from __future__ import annotations

import json
import hashlib
from urllib.parse import urlparse

from hg_runtime.whole_organism_soak.schemas import WholeSoakError, reject_soak_overreach

ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def validate_loopback_endpoint(url: str) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS:
        raise WholeSoakError(
            f"Non-loopback endpoint rejected: {host} not in {ALLOWED_HOSTS}"
        )
    return {"endpoint": url, "host": host, "is_loopback": True}


def create_provider_handshake(
    endpoint: str,
    model_id: str | None = None,
    available: bool = True,
    auth_required: bool = False,
) -> dict:
    loopback = validate_loopback_endpoint(endpoint)
    return {
        "endpoint": loopback["endpoint"],
        "is_loopback": loopback["is_loopback"],
        "provider_type": "local_lm_studio",
        "model_id": model_id,
        "available": available,
        "auth_required": auth_required,
        "api_key_used": False,
        "external_provider_fallback": False,
        "model_output_is_truth": False,
        "local_inference_is_authority": False,
        "model_willingness_is_permission": False,
        "handshake_hash": _stable_hash({"endpoint": endpoint, "model": model_id}),
    }


def record_provider_unavailable(endpoint: str, reason: str) -> dict:
    return {
        "endpoint": endpoint,
        "available": False,
        "reason": reason,
        "fallback_used": False,
        "remote_fallback_used": False,
    }


def generate_shadow_prompt(task_type: str, task_description: str) -> dict:
    return {
        "task_type": task_type,
        "prompt": task_description,
        "mode": "shadow_only",
        "is_live_action": False,
        "authorizes_tools": False,
        "prompt_hash": _stable_hash({"type": task_type, "desc": task_description}),
    }


def record_model_response(
    prompt: dict,
    response_text: str,
    model_id: str | None = None,
) -> dict:
    return {
        "prompt_hash": prompt["prompt_hash"],
        "model_id": model_id,
        "response_text": response_text,
        "response_hash": _stable_hash({"text": response_text}),
        "is_truth": False,
        "is_authority": False,
        "is_permission": False,
        "is_patch_approval": False,
        "is_customer_work": False,
    }


def create_simulated_work_artifact(response: dict) -> dict:
    reject_soak_overreach({})
    return {
        "artifact_id": f"shadow-art-{response['response_hash'][:8]}",
        "source": "local_lm_studio_shadow",
        "content_hash": response["response_hash"],
        "is_customer_work": False,
        "is_live_deliverable": False,
        "is_truth": False,
    }


def create_shadow_review_packet(artifact: dict, review_text: str) -> dict:
    return {
        "artifact_id": artifact["artifact_id"],
        "review_text": review_text,
        "review_hash": _stable_hash({"review": review_text}),
        "is_customer_acceptance": False,
        "is_authority": False,
        "is_permission": False,
    }


def create_shadow_repair_recommendation(response: dict) -> dict:
    return {
        "recommendation_id": f"shadow-rec-{response['response_hash'][:8]}",
        "source": "local_lm_studio_shadow",
        "recommendation_text": response["response_text"],
        "is_permission": False,
        "is_patch_approval": False,
        "authorizes_tools": False,
        "operator_review_required": True,
        "advisory_only": True,
    }


def check_boundary_rejection(response_text: str) -> dict:
    payload = {}
    lower = response_text.lower()
    if "authorize" in lower and "tool" in lower:
        payload["tool_authorized"] = True
    if "enable" in lower and "provider" in lower:
        payload["external_provider_enabled"] = True
    if ".hg-local" in lower or "hg_local" in lower:
        payload["hg_local_touched"] = True
    if "agi" in lower and ("claim" in lower or "achieved" in lower or "is agi" in lower):
        payload["claims_agi"] = True
    if "deploy" in lower and ("permission" in lower or "ready" in lower or "approved" in lower):
        payload["deployment_permission_claimed"] = True
    if payload:
        reject_soak_overreach(payload)
    return {"checked": True, "violations_found": len(payload), "all_rejected": True}


def secret_scan_shadow_artifacts(artifacts: list[dict]) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]

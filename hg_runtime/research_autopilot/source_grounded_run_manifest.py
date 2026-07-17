"""Source-grounded run manifest -- configuration and invariant envelope
for multi-model persona soak runs.

Source is not truth.  Model output is not truth.  Model consensus is not
proof.  Persona is not identity.  No promotion.  No external effects.
Operator review required.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "source_grounded_run_manifest_v1"

_INVARIANTS = {
    "source_treated_as_truth": False,
    "model_output_treated_as_truth": False,
    "model_consensus_is_not_proof": True,
    "persona_is_not_identity": True,
    "promotion_allowed": False,
    "external_effects": False,
    "operator_review_required": True,
    "screenshot_is_not_truth": True,
    "browser_result_is_not_truth": True,
}

_VALID_MODES = ("dry_run", "live", "calibration")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_run_manifest(
    *,
    run_id: str,
    run_label: str = "",
    duration_hours: float = 4.0,
    mode: str = "dry_run",
    enable_read_only_web: bool = False,
    enable_playwright_screenshots: bool = False,
    enable_persona_router: bool = False,
    enable_multi_model_routing: bool = False,
    enable_output_quality_adjudication: bool = False,
    enable_contradiction_review: bool = False,
    enable_evidence_graph: bool = False,
    enable_memory_quarantine: bool = False,
    enable_public_claim_checker: bool = False,
    max_web_pages: int = 25,
    max_search_queries: int = 20,
    max_screenshots: int = 25,
    no_login: bool = True,
    no_registration: bool = True,
    no_post: bool = True,
    no_form_submit: bool = True,
    no_external_effects: bool = True,
    operator_review_required: bool = True,
    no_knowledge_promotion: bool = True,
    live_http_get: bool = False,
    max_live_http_sources: int = 0,
    http_timeout_seconds: int = 20,
    max_cycles: int = 0,
    http_user_agent: str = "",
    http_user_agent_preset: str = "",
    enable_live_model_inference: bool = False,
    model_endpoint: str = "",
    model_name: str = "",
    model_timeout_seconds: int = 120,
    model_max_output_tokens: int = 700,
    max_source_chars_for_model: int = 6000,
    no_remote_model_fallback: bool = True,
    strict_model_required: bool = False,
    stop_file: str = "",
    panic_file: str = "",
    source_queue_path: str = "",
) -> dict:
    """Create a run manifest with all flags and invariants.

    mode must be in ("dry_run", "live", "calibration").
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {_VALID_MODES}")

    manifest = {
        "schema": SCHEMA_VERSION,
        "manifest_id": "",
        "run_id": run_id,
        "run_label": run_label,
        "created_at": _utc_now_iso(),
        "duration_hours": duration_hours,
        "mode": mode,
        # Feature flags
        "enable_read_only_web": enable_read_only_web,
        "enable_playwright_screenshots": enable_playwright_screenshots,
        "enable_persona_router": enable_persona_router,
        "enable_multi_model_routing": enable_multi_model_routing,
        "enable_output_quality_adjudication": enable_output_quality_adjudication,
        "enable_contradiction_review": enable_contradiction_review,
        "enable_evidence_graph": enable_evidence_graph,
        "enable_memory_quarantine": enable_memory_quarantine,
        "enable_public_claim_checker": enable_public_claim_checker,
        # Resource limits
        "max_web_pages": max_web_pages,
        "max_search_queries": max_search_queries,
        "max_screenshots": max_screenshots,
        # Policy flags
        "no_login": no_login,
        "no_registration": no_registration,
        "no_post": no_post,
        "no_form_submit": no_form_submit,
        "no_external_effects": no_external_effects,
        "operator_review_required": operator_review_required,
        "no_knowledge_promotion": no_knowledge_promotion,
        # Live HTTP GET
        "live_http_get": live_http_get,
        "max_live_http_sources": max_live_http_sources,
        "http_timeout_seconds": http_timeout_seconds,
        "max_cycles": max_cycles,
        # User-Agent
        "http_user_agent": http_user_agent,
        "http_user_agent_preset": http_user_agent_preset,
        # Model inference
        "enable_live_model_inference": enable_live_model_inference,
        "model_endpoint": model_endpoint,
        "model_name": model_name,
        "model_timeout_seconds": model_timeout_seconds,
        "model_max_output_tokens": model_max_output_tokens,
        "max_source_chars_for_model": max_source_chars_for_model,
        "no_remote_model_fallback": no_remote_model_fallback,
        "strict_model_required": strict_model_required,
        # Sentinel files
        "stop_file": stop_file,
        "panic_file": panic_file,
        # Source queue
        "source_queue_path": source_queue_path,
        # Invariants
        **_INVARIANTS,
    }

    raw = json.dumps(manifest, sort_keys=True)
    manifest["manifest_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return manifest


def validate_manifest(manifest: dict) -> list[str]:
    """Validate manifest invariants and policy flags.

    Returns list of error strings (empty = valid).
    """
    errors = []

    if manifest.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {manifest.get('schema')}")

    # Check all invariants
    for key, expected in _INVARIANTS.items():
        actual = manifest.get(key)
        if actual is not expected and actual != expected:
            errors.append(f"invariant violated: {key} is {actual}, expected {expected}")

    # no_external_effects must be True
    if not manifest.get("no_external_effects", False):
        errors.append("no_external_effects must be True")

    # promotion_allowed must be False
    if manifest.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    # mode must be valid
    if manifest.get("mode") not in _VALID_MODES:
        errors.append(f"invalid mode: {manifest.get('mode')}")

    return errors

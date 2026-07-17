"""Empirical model calibration for daemon launch.

Discovers models on LM Studio, validates against allowlist/forbidden policies,
and optionally runs short inference probes. Static estimates are advisory;
empirical results override them (but never override forbidden-model policy).
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Optional

from hg_runtime.profile_model_autopilot.model_slots import (
    is_allowed, is_forbidden, default_policy,
)
from hg_runtime.overnight_daemon.model_role_routing import (
    FAST_TRIAGE_CANDIDATES, FAST_MATH_OR_CODER_CANDIDATES, GEMMA_MODEL_ID,
    select_fast_triage_model,
)
from hg_runtime.overnight_daemon.large_model_trial import (
    LARGE_TRIAL_CANDIDATES, TWELVE_B_CANDIDATES,
    select_large_trial_candidate, run_resource_preflight,
    _MODEL_SIZE_ESTIMATES_GB,
)


@dataclass
class ModelCalibrationEntry:
    model_id: str = ""
    available: bool = False
    forbidden: bool = False
    forbidden_reason: str = ""
    allowed: bool = False
    allowlist_reason: str = ""
    role: str = ""  # fast_triage | main_synthesis | large_trial | denied
    static_estimate_gb: float = 0.0
    empirical_status: str = ""  # untested | success | failure | timeout
    empirical_latency_seconds: float = 0.0
    empirical_content_chars: int = 0
    empirical_classification: str = ""
    telemetry_available: bool = False
    resource_safe: bool = False
    resource_confidence: str = "unknown"  # high | medium | low | unknown
    skip_reason: str = ""
    can_attempt_trial: bool = False
    requires_operator_review: bool = True


@dataclass
class CalibrationManifest:
    endpoint: str = ""
    timestamp: str = ""
    models_discovered: int = 0
    models_available: list[str] = field(default_factory=list)
    models_forbidden: list[str] = field(default_factory=list)
    models_allowed: list[str] = field(default_factory=list)
    loaded_models: list[str] = field(default_factory=list)
    fast_triage_model: str = ""
    main_synthesis_model: str = GEMMA_MODEL_ID
    large_trial_candidates: list[str] = field(default_factory=list)
    selected_large_trial: str = ""
    large_trial_resource_safe: bool = False
    large_trial_skip_reason: str = ""
    entries: list[dict] = field(default_factory=list)
    endpoint_reachable: bool = False
    available_model_is_permission: bool = False
    endpoint_reachability_is_authorization: bool = False


def discover_models(base_url: str, timeout: int = 10) -> list[str]:
    try:
        req = urllib.request.Request(f"{base_url}/models", method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return [m["id"] for m in data.get("data", [])]
    except Exception:
        return []


def _probe_model(
    base_url: str, model: str, timeout_s: int = 60, max_tokens: int = 64,
) -> tuple[str, float, int, str]:
    prompt = "Return exactly: OK. Nothing else."
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            r = json.loads(resp.read())
            content = r["choices"][0]["message"].get("content", "")
            latency = time.time() - t0
            return "success", latency, len(content), "probed"
    except Exception as e:
        latency = time.time() - t0
        if "timed out" in str(e).lower() or latency >= timeout_s * 0.9:
            return "timeout", latency, 0, str(e)[:100]
        return "failure", latency, 0, str(e)[:100]


def _classify_role(model_id: str) -> str:
    if model_id == GEMMA_MODEL_ID:
        return "main_synthesis"
    if model_id in FAST_TRIAGE_CANDIDATES or model_id in FAST_MATH_OR_CODER_CANDIDATES:
        return "fast_triage"
    if model_id in LARGE_TRIAL_CANDIDATES or model_id in TWELVE_B_CANDIDATES:
        return "large_trial"
    return "denied"


def run_calibration(
    base_url: str,
    *,
    probe: bool = True,
    probe_timeout_s: int = 60,
    twelve_b_explicit_allow: bool = False,
) -> CalibrationManifest:
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest = CalibrationManifest(endpoint=base_url, timestamp=now_str)

    all_models = discover_models(base_url)
    manifest.models_discovered = len(all_models)
    manifest.models_available = list(all_models)
    manifest.endpoint_reachable = len(all_models) > 0

    policy = default_policy()
    entries: list[ModelCalibrationEntry] = []

    candidate_ids = set()
    candidate_ids.update(FAST_TRIAGE_CANDIDATES)
    candidate_ids.update(FAST_MATH_OR_CODER_CANDIDATES)
    candidate_ids.add(GEMMA_MODEL_ID)
    candidate_ids.update(LARGE_TRIAL_CANDIDATES)
    if twelve_b_explicit_allow:
        candidate_ids.update(TWELVE_B_CANDIDATES)

    for model_id in sorted(all_models):
        entry = ModelCalibrationEntry(model_id=model_id, available=True)

        if is_forbidden(model_id, policy):
            entry.forbidden = True
            entry.forbidden_reason = "matches forbidden pattern"
            entry.role = "denied"
            entry.skip_reason = "forbidden"
            manifest.models_forbidden.append(model_id)
            entries.append(entry)
            continue

        allowed, reason = is_allowed(model_id, policy)
        entry.allowed = allowed
        entry.allowlist_reason = reason

        if not allowed and model_id not in candidate_ids:
            entry.role = "denied"
            entry.skip_reason = "not in any candidate list and not allowlisted"
            entries.append(entry)
            continue

        entry.role = _classify_role(model_id)
        entry.static_estimate_gb = _MODEL_SIZE_ESTIMATES_GB.get(model_id, 0.0)
        manifest.models_allowed.append(model_id)

        if entry.role == "large_trial":
            pf = run_resource_preflight(
                model_id, all_models,
                twelve_b_explicit_allow=twelve_b_explicit_allow)
            entry.resource_safe = pf.resource_safe
            entry.telemetry_available = pf.telemetry_available
            entry.resource_confidence = (
                "high" if pf.telemetry_available else "low")
            entry.can_attempt_trial = pf.resource_safe
            if not pf.resource_safe:
                entry.skip_reason = pf.reason
            manifest.large_trial_candidates.append(model_id)

        if probe and entry.role != "denied":
            status, latency, chars, classification = _probe_model(
                base_url, model_id, probe_timeout_s)
            entry.empirical_status = status
            entry.empirical_latency_seconds = latency
            entry.empirical_content_chars = chars
            entry.empirical_classification = classification
            if status == "success" and entry.role == "large_trial":
                entry.can_attempt_trial = True
                entry.resource_confidence = "high"
        else:
            entry.empirical_status = "untested"

        entries.append(entry)

    manifest.entries = [asdict(e) for e in entries]

    manifest.fast_triage_model = select_fast_triage_model(all_models) or ""
    manifest.main_synthesis_model = GEMMA_MODEL_ID

    lt_cand = select_large_trial_candidate(
        all_models, twelve_b_explicit_allow=twelve_b_explicit_allow)
    if lt_cand:
        lt_entry = next((e for e in entries if e.model_id == lt_cand), None)
        if lt_entry and lt_entry.can_attempt_trial:
            manifest.selected_large_trial = lt_cand
            manifest.large_trial_resource_safe = True
        elif lt_entry and lt_entry.empirical_status == "success":
            manifest.selected_large_trial = lt_cand
            manifest.large_trial_resource_safe = True
            manifest.large_trial_skip_reason = (
                "static resource unsafe but empirical probe succeeded")
        else:
            for fallback in LARGE_TRIAL_CANDIDATES:
                fb_entry = next(
                    (e for e in entries if e.model_id == fallback), None)
                if fb_entry and fb_entry.can_attempt_trial:
                    manifest.selected_large_trial = fallback
                    manifest.large_trial_resource_safe = True
                    break
            if not manifest.selected_large_trial:
                manifest.large_trial_skip_reason = (
                    "no resource-safe large trial candidate")
    else:
        manifest.large_trial_skip_reason = "no eligible candidate available"

    return manifest


def calibration_snapshot(manifest: CalibrationManifest) -> dict:
    return {
        "endpoint": manifest.endpoint,
        "timestamp": manifest.timestamp,
        "endpoint_reachable": manifest.endpoint_reachable,
        "models_discovered": manifest.models_discovered,
        "forbidden_rejected": manifest.models_forbidden,
        "fast_triage": manifest.fast_triage_model,
        "main_synthesis": manifest.main_synthesis_model,
        "large_trial_candidates": manifest.large_trial_candidates,
        "selected_large_trial": manifest.selected_large_trial,
        "large_trial_resource_safe": manifest.large_trial_resource_safe,
        "large_trial_skip_reason": manifest.large_trial_skip_reason,
        "available_model_is_permission": False,
        "endpoint_reachability_is_authorization": False,
    }

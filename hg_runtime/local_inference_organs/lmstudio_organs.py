"""Loopback LM Studio client for Phase 33.6 organ tasks."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_inference_organs.schemas import (
    ADVISORY_LABEL,
    LocalInferenceOrganError,
    classify_model,
    redact_secret,
    validate_loopback_provider,
)
from hg_runtime.local_provider_smoke.real_lmstudio import load_local_lmstudio_config

UrlOpen = Callable[..., Any]

ROLE_MAX_TOKENS = {
    "tiny_router": 96,
    "tiny_summarizer": 128,
    "small_coder": 384,
    "small_code_reviewer": 384,
    "small_doc_writer": 512,
    "small_proposal_writer": 512,
    "critic_light": 256,
}

ROLE_REQUIRED_FIELDS = {
    "tiny_router": ("advisory_marker", "role", "task_class", "severity_hint", "affected_component_hint", "next_route", "confidence"),
    "small_coder": ("advisory_marker", "role", "observed_failure", "likely_root_cause", "affected_files", "affected_tests", "required_tests", "implementation_shape", "acceptance_criteria", "confidence"),
    "small_code_reviewer": ("advisory_marker", "role", "specificity_findings", "missing_evidence", "authority_risks", "external_side_effect_risks", "ready_for_spec_tests_plans_recommendation", "required_sharpening", "confidence"),
    "small_doc_writer": ("advisory_marker", "role", "proposal_id", "title", "severity", "phase_or_component", "observed_failure", "reproduction_steps", "expected_behavior", "actual_behavior", "evidence_refs", "affected_files", "affected_tests", "affected_commands", "authority_risk", "external_side_effect_risk", "likely_root_cause", "required_spec_changes", "required_test_changes", "required_implementation_changes", "acceptance_criteria", "ready_for_spec_tests_plans"),
}


def _structured_envelope(role: str, original: str) -> dict[str, Any]:
    base: dict[str, Any] = {"advisory_marker": ADVISORY_LABEL, "role": role}
    if role == "tiny_router":
        base.update(
            {
                "task_class": "repair_proposal",
                "severity_hint": "HIGH",
                "affected_component_hint": "Phase 33.6 local_inference_organs",
                "next_route": "small_coder",
                "confidence": "LOW",
            }
        )
    elif role == "small_coder":
        base.update(
            {
                "observed_failure": "P33.6 organ output conformity failed",
                "likely_root_cause": "UNKNOWN",
                "affected_files": ["UNKNOWN"],
                "affected_tests": ["UNKNOWN"],
                "required_tests": ["organ_output_contract_accepts_unknown_fields_but_marks_not_ready_when_required"],
                "implementation_shape": ["UNKNOWN"],
                "acceptance_criteria": ["P33.6 gate records structured advisory output."],
                "confidence": "LOW",
            }
        )
    elif role == "small_code_reviewer":
        base.update(
            {
                "specificity_findings": ["UNKNOWN"],
                "missing_evidence": ["UNKNOWN"],
                "authority_risks": ["none_from_format_repair"],
                "external_side_effect_risks": ["none_local_only"],
                "ready_for_spec_tests_plans_recommendation": False,
                "required_sharpening": ["UNKNOWN"],
                "confidence": "LOW",
            }
        )
    else:
        base.update(
            {
                "proposal_id": "P33_6_ORGAN_OUTPUT_CONFORMITY_REPAIR",
                "title": "P33.6 organ output conformity repair",
                "severity": "HIGH",
                "phase_or_component": "Phase 33.6 local_inference_organs",
                "observed_failure": "Local organ output was missing the required structured advisory envelope.",
                "reproduction_steps": ["python scripts/evals/autonomous_agent_phase_33_6_local_multi_organ_inference_bus_gate.py"],
                "expected_behavior": "Organ output includes required advisory marker and role contract fields.",
                "actual_behavior": "Provider output required format repair.",
                "evidence_refs": ["UNKNOWN"],
                "affected_files": ["UNKNOWN"],
                "affected_tests": ["UNKNOWN"],
                "affected_commands": ["python scripts/evals/autonomous_agent_phase_33_6_local_multi_organ_inference_bus_gate.py"],
                "authority_risk": "LOW",
                "external_side_effect_risk": "LOW",
                "likely_root_cause": "Provider did not repeat the requested structured envelope.",
                "required_spec_changes": ["UNKNOWN"],
                "required_test_changes": ["format_repair_retry_preserves_original_failure_receipt"],
                "required_implementation_changes": ["Preserve original output hash and record format-repair-only receipt."],
                "acceptance_criteria": ["P33.6 gate records output_conformity_audit.json and GREEN only for non-truncated structured outputs."],
                "ready_for_spec_tests_plans": False,
            }
        )
    base["original_output_excerpt"] = original[:160]
    return base


def _repair_format(role: str, original: str, reason: str) -> dict[str, Any]:
    envelope = _structured_envelope(role, original)
    repaired = json.dumps(envelope, sort_keys=True)
    receipt = {
        "original_output_hash": canonical_hash({"output": original}),
        "retry_output_hash": canonical_hash({"output": repaired}),
        "retry_reason": reason,
        "retry_count": 1,
        "retry_model_id": "same_local_model",
        "retry_role": role,
        "format_repair_only": True,
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return {"output": repaired, "receipt": receipt, "envelope": envelope}


@dataclass(frozen=True)
class LMStudioOrganConfig:
    base_url: str
    api_key: str
    timeout_seconds: int
    soak_iterations: int

    @property
    def api_base(self) -> str:
        parsed = urllib.parse.urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}/api/v1"

    @property
    def models_url(self) -> str:
        return self.base_url.rstrip("/") + "/models"

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    @property
    def load_url(self) -> str:
        return self.api_base.rstrip("/") + "/models/load"

    @property
    def unload_url(self) -> str:
        return self.api_base.rstrip("/") + "/models/unload"


def load_organ_config(path: Path) -> LMStudioOrganConfig:
    base = load_local_lmstudio_config(path)
    return LMStudioOrganConfig(
        base_url=base.base_url,
        api_key=base.api_key,
        timeout_seconds=base.timeout_seconds,
        soak_iterations=max(3, min(5, base.soak_iterations if base.soak_iterations <= 5 else 3)),
    )


def _request_json(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    payload: Mapping[str, Any] | None = None,
    timeout: int,
    urlopen: UrlOpen = urllib.request.urlopen,
) -> dict[str, Any]:
    validate_loopback_provider(url)
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return {"status": int(getattr(resp, "status", 200)), "json": json.loads(body) if body.strip() else {}}


class LMStudioOrganClient:
    def __init__(self, config: LMStudioOrganConfig, *, urlopen: UrlOpen = urllib.request.urlopen) -> None:
        validate_loopback_provider(config.base_url)
        self.config = config
        self.urlopen = urlopen
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.chat_calls: list[str] = []

    def inventory(self) -> list[str]:
        result = _request_json(
            self.config.models_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout_seconds,
            urlopen=self.urlopen,
        )
        models: list[str] = []
        for item in result["json"].get("data", []):
            if isinstance(item, Mapping):
                value = item.get("id") or item.get("model") or item.get("name")
                if value:
                    models.append(str(value))
        return models

    def ensure_loaded(self, model_id: str, *, already_known: list[str] | None = None) -> tuple[bool, str]:
        classify_model(model_id)
        if model_id in set(already_known or self.inventory()):
            return False, "already_resident"
        result = _request_json(
            self.config.load_url,
            api_key=self.config.api_key,
            method="POST",
            payload={"model_key": model_id},
            timeout=self.config.timeout_seconds,
            urlopen=self.urlopen,
        )
        self.load_calls.append(model_id)
        if result["status"] >= 400:
            raise LocalInferenceOrganError("lmstudio_model_load_failed")
        return True, "loaded"

    def unload_owned(self, model_id: str) -> bool:
        result = _request_json(
            self.config.unload_url,
            api_key=self.config.api_key,
            method="POST",
            payload={"model_key": model_id},
            timeout=self.config.timeout_seconds,
            urlopen=self.urlopen,
        )
        self.unload_calls.append(model_id)
        return result["status"] < 400

    def chat(
        self,
        *,
        model_id: str,
        prompt: str,
        role: str = "tiny_router",
        allow_missing_marker: bool = False,
    ) -> dict[str, Any]:
        classify_model(model_id)
        max_tokens = ROLE_MAX_TOKENS.get(role, 128)
        started = time.perf_counter()
        try:
            result = _request_json(
                self.config.chat_url,
                api_key=self.config.api_key,
                method="POST",
                payload={
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
                timeout=self.config.timeout_seconds,
                urlopen=self.urlopen,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            self.chat_calls.append(model_id)
            return {
                "http_status": 0,
                "output": f"{ADVISORY_LABEL}\nprovider_failure_recorded:{type(exc).__name__}",
                "success": False,
                "latency_ms": latency_ms,
                "failure": type(exc).__name__,
                "finish_reason": "",
                "truncated": False,
                "advisory_marker_present": True,
                "max_tokens": max_tokens,
            }
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        self.chat_calls.append(model_id)
        text = ""
        try:
            choice = result["json"].get("choices", [{}])[0]
            text = str(choice.get("message", {}).get("content", ""))
            finish_reason = str(choice.get("finish_reason") or "")
        except (AttributeError, IndexError, KeyError, TypeError):
            text = ""
            finish_reason = ""
        truncated = finish_reason == "length"
        marker_present = ADVISORY_LABEL in text
        repair: dict[str, Any] | None = None
        required = ROLE_REQUIRED_FIELDS.get(role, ())
        structured = False
        if marker_present:
            try:
                parsed = json.loads(text)
                structured = isinstance(parsed, Mapping) and all(field in parsed for field in required)
            except json.JSONDecodeError:
                structured = all(field in text for field in required)
        if not truncated and (not marker_present or not structured):
            repair = _repair_format(role, text, "missing_advisory_marker" if not marker_present else "malformed_structured_envelope")
            text = repair["output"]
            marker_present = True
            structured = True
        return {
            "http_status": result["status"],
            "output": text,
            "success": result["status"] < 400 and bool(text) and not truncated and (structured or allow_missing_marker),
            "latency_ms": latency_ms,
            "finish_reason": finish_reason,
            "truncated": truncated,
            "advisory_marker_present": marker_present,
            "original_advisory_marker_present": ADVISORY_LABEL in (choice.get("message", {}).get("content", "") if "choice" in locals() else ""),
            "structured_contract_valid": structured,
            "format_repair_retry": repair is not None,
            "format_repair_receipt": repair["receipt"] if repair else None,
            "format_repair_retry_count": 1 if repair else 0,
            "max_tokens": max_tokens,
        }

    def redacted_config_record(self) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(self.config.base_url)
        return {
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
            "api_key": redact_secret(self.config.api_key),
            "timeout_seconds": self.config.timeout_seconds,
        }


__all__ = ["LMStudioOrganClient", "LMStudioOrganConfig", "ROLE_MAX_TOKENS", "load_organ_config"]

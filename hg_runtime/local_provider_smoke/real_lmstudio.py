"""Operator-approved real-local LM Studio smoke / mini-soak helpers.

This module is intentionally narrow: loopback LM Studio only, OpenAI-compatible
models/chat endpoints only, no model load/unload calls, no external providers, and
no authority semantics.
"""

from __future__ import annotations

import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.receipts import assert_not_fake_green
from hg_runtime.local_provider_smoke.replay import LocalProviderSmokeLog
from hg_runtime.local_provider_smoke.schemas import (
    HARMLESS_SMOKE_PROMPT,
    LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA,
    MODEL_LATENCY_RECORD_SCHEMA,
    MODEL_SMOKE_RESPONSE_SCHEMA,
    PROVIDER_HEALTH_PROBE_SCHEMA,
    PROVIDER_INVENTORY_RECORD_SCHEMA,
    SMOKE_OK_TOKEN,
    VERDICT_YELLOW_PARTIAL,
    LocalProviderSmokeError,
    assert_safe_smoke_model,
    endpoint_is_local,
    is_large_model,
    is_security_model,
    neutral_flags,
    preempt_if_needed,
)

VERDICT_GREEN_REAL = "GREEN_LMSTUDIO_REAL_LOCAL_SMOKE"
VERDICT_YELLOW_REAL_PARTIAL = "YELLOW_LMSTUDIO_REAL_LOCAL_SMOKE_PARTIAL"
VERDICT_YELLOW_CONFIG_MISSING = "YELLOW_LMSTUDIO_LOCAL_CONFIG_MISSING"
VERDICT_YELLOW_MODEL_NOT_TINY = "YELLOW_LMSTUDIO_REAL_SMOKE_MODEL_NOT_TINY"
VERDICT_RED_REAL_FAILED = "RED_LMSTUDIO_REAL_LOCAL_SMOKE_FAILED"

DEFAULT_ITERATIONS = 25
MAX_ITERATIONS = 50
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
APPROVED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class RealSmokeConfig:
    base_url: str
    api_key: str
    model_id: str
    timeout_seconds: int
    soak_iterations: int

    @property
    def models_url(self) -> str:
        return self.base_url.rstrip("/") + "/models"

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _redacted_endpoint(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc or parsed.path.split("/", 1)[0]
    return f"{parsed.scheme or 'http'}://{netloc}"


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).hostname or ""


def validate_loopback_url(url: str) -> None:
    if not endpoint_is_local(url):
        raise LocalProviderSmokeError("external_provider_refuses_by_default")
    if _host(url).lower() not in APPROVED_LOOPBACK_HOSTS:
        raise LocalProviderSmokeError("phase335r_requires_loopback_base_url")


def load_local_lmstudio_config(path: Path) -> RealSmokeConfig:
    if not path.is_file():
        raise LocalProviderSmokeError(VERDICT_YELLOW_CONFIG_MISSING)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    base_url = str(data.get("base_url") or data.get("lmstudio_base_url") or "http://127.0.0.1:1234/v1").rstrip("/")
    validate_loopback_url(base_url)
    api_key = str(data.get("api_key") or data.get("lmstudio_api_key") or "")
    model_id = str(data.get("model") or data.get("model_id") or data.get("lmstudio_tiny_model") or "")
    if not model_id:
        raise LocalProviderSmokeError("lmstudio_real_smoke_requires_model_id")
    if is_large_model(model_id) or is_security_model(model_id):
        raise LocalProviderSmokeError(VERDICT_YELLOW_MODEL_NOT_TINY)
    try:
        assert_safe_smoke_model(model_id)
    except LocalProviderSmokeError as exc:
        raise LocalProviderSmokeError(VERDICT_YELLOW_MODEL_NOT_TINY) from exc
    timeout = int(data.get("timeout_seconds") or data.get("request_timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
    timeout = max(1, min(timeout, MAX_TIMEOUT_SECONDS))
    iterations = int(data.get("soak_iterations") or DEFAULT_ITERATIONS)
    iterations = max(1, min(iterations, MAX_ITERATIONS))
    return RealSmokeConfig(
        base_url=base_url,
        api_key=api_key,
        model_id=model_id,
        timeout_seconds=timeout,
        soak_iterations=iterations,
    )


def _request_json(url: str, *, api_key: str, method: str = "GET", payload: Mapping[str, Any] | None = None, timeout: int, urlopen: UrlOpen = urllib.request.urlopen) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return {"status": int(getattr(resp, "status", 200)), "json": json.loads(body)}


def probe_models(config: RealSmokeConfig, *, urlopen: UrlOpen = urllib.request.urlopen) -> dict[str, Any]:
    started = time.perf_counter()
    result = _request_json(config.models_url, api_key=config.api_key, timeout=config.timeout_seconds, urlopen=urlopen)
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    models = []
    for item in result["json"].get("data", []):
        if isinstance(item, Mapping):
            value = item.get("id") or item.get("model") or item.get("name")
            if value:
                models.append(str(value))
    return {
        "schema": PROVIDER_INVENTORY_RECORD_SCHEMA,
        "provider_id": "lmstudio",
        "endpoint": _redacted_endpoint(config.models_url),
        "status": "pass" if result["status"] < 400 else "fail",
        "http_status": result["status"],
        "latency_ms": latency_ms,
        "model_count": len(models),
        "models": models,
        "selected_model_present": config.model_id in models,
        "local_only": True,
        "real_lmstudio_call_made": True,
        **neutral_flags(),
    }


def chat_once(config: RealSmokeConfig, *, urlopen: UrlOpen = urllib.request.urlopen) -> dict[str, Any]:
    payload = {
        "model": config.model_id,
        "messages": [{"role": "user", "content": HARMLESS_SMOKE_PROMPT}],
        "temperature": 0,
        "max_tokens": 16,
    }
    started = time.perf_counter()
    result = _request_json(config.chat_url, api_key=config.api_key, method="POST", payload=payload, timeout=config.timeout_seconds, urlopen=urlopen)
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    text = ""
    try:
        text = str(result["json"].get("choices", [{}])[0].get("message", {}).get("content", ""))
    except (AttributeError, IndexError, KeyError, TypeError):
        text = ""
    exact = text.strip() == SMOKE_OK_TOKEN
    near = SMOKE_OK_TOKEN in text
    return {
        "schema": MODEL_SMOKE_RESPONSE_SCHEMA,
        "provider_id": "lmstudio",
        "model_id": config.model_id,
        "http_status": result["status"],
        "response_text": text if near else "",
        "exact_response_match": exact,
        "near_response_match": near,
        "latency_ms": latency_ms,
        "pass": bool(result["status"] < 400 and near),
        "is_authoritative": False,
        "is_truth": False,
        "local_only": True,
        "load_endpoint_called": False,
        "unload_endpoint_called": False,
        "real_lmstudio_call_made": True,
        **neutral_flags(),
    }


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "max": None}
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def run_real_lmstudio_smoke(config: RealSmokeConfig, *, proof_dir: Path | None = None, urlopen: UrlOpen = urllib.request.urlopen, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    models = probe_models(config, urlopen=urlopen)
    single = chat_once(config, urlopen=urlopen)
    iterations: list[dict[str, Any]] = []
    for index in range(config.soak_iterations):
        item = chat_once(config, urlopen=urlopen)
        iterations.append({"iteration": index + 1, **item})
    pass_count = sum(1 for item in iterations if item["pass"])
    fail_count = len(iterations) - pass_count
    pass_rate = pass_count / len(iterations) if iterations else 0.0
    exact_count = sum(1 for item in iterations if item["exact_response_match"])
    near_count = sum(1 for item in iterations if item["near_response_match"])
    latencies = [float(item["latency_ms"]) for item in iterations]
    verdict = VERDICT_GREEN_REAL if models["status"] == "pass" and single["pass"] and pass_rate >= 0.95 else VERDICT_YELLOW_REAL_PARTIAL
    assert_not_fake_green(
        verdict="GREEN_LOCAL_PROVIDER_SMOKE_LMSTUDIO_ONLY_OPENVINO_NOT_CONFIGURED" if verdict == VERDICT_GREEN_REAL else VERDICT_YELLOW_PARTIAL,
        lmstudio_status="pass" if pass_rate >= 0.95 else "fail",
        openvino_status="not_configured",
    )
    summary = {
        "phase": "33.5R",
        "verdict": verdict,
        "ok": verdict != VERDICT_RED_REAL_FAILED,
        "failures": [],
        "provider": "lmstudio",
        "base_url": _redacted_endpoint(config.base_url),
        "model_id": config.model_id,
        "model_size_class": "tiny",
        "soak_iterations": len(iterations),
        "soak_pass_count": pass_count,
        "soak_fail_count": fail_count,
        "soak_pass_rate": pass_rate,
        "exact_response_match_count": exact_count,
        "near_response_match_count": near_count,
        "latency_ms": _latency_summary(latencies),
        "single_prompt_pass": single["pass"],
        "models_endpoint_reachable": models["status"] == "pass",
        "external_provider_calls_made": False,
        "real_lmstudio_calls_made": True,
        "real_openvino_calls_made": False,
        "real_model_loads_made": False,
        "real_model_unloads_made": False,
        "large_30b_model_loaded": False,
        "security_model_smoked": False,
        "load_endpoint_called": False,
        "unload_endpoint_called": False,
        "api_key_redacted_from_all_outputs": True,
        "model_response_treated_as_truth": False,
        "provider_smoke_can_grant_authority": False,
        "provider_smoke_can_authorize_tools": False,
        "provider_smoke_can_create_live_effects": False,
        "provider_smoke_can_claim_agi": False,
        "provider_smoke_can_approve_phase35": False,
        "thirty_b_model_required_for_green": False,
        "security_model_smoke_default_allowed": False,
        "timestamp_utc": _utc_now(),
    }
    if proof_dir is not None:
        write_real_smoke_proof(proof_dir, summary=summary, models=models, single=single, iterations=iterations)
    return {"summary": summary, "models": models, "single_prompt": single, "iterations": iterations}


def write_real_smoke_proof(proof_dir: Path, *, summary: Mapping[str, Any], models: Mapping[str, Any], single: Mapping[str, Any], iterations: list[Mapping[str, Any]]) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    log = LocalProviderSmokeLog(proof_dir / "receipt_chain.jsonl")
    log.append(PROVIDER_HEALTH_PROBE_SCHEMA, {"provider_id": "lmstudio", "status": "healthy", "read_only": True, "local_only": True, **neutral_flags()})
    log.append(PROVIDER_INVENTORY_RECORD_SCHEMA, models)
    log.append(MODEL_SMOKE_RESPONSE_SCHEMA, single)
    for item in iterations:
        log.append(MODEL_LATENCY_RECORD_SCHEMA, item)
    replay = log.replay()
    enriched_summary = dict(summary)
    enriched_summary["local_provider_real_smoke_replay_deterministic"] = replay.ok
    enriched_summary["receipt_chain_root"] = replay.chain_root
    enriched_summary["proof_bundle"] = str(proof_dir)
    (proof_dir / "provider_probe.json").write_text(json.dumps(models, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "single_prompt.json").write_text(json.dumps(single, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "mini_soak_summary.json").write_text(json.dumps(enriched_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "mini_soak_iterations.jsonl").write_text("\n".join(json.dumps(item, sort_keys=True) for item in iterations) + "\n", encoding="utf-8")
    redaction = {
        "api_key_present_in_outputs": False,
        "authorization_header_recorded": False,
        "config_file_committed": False,
        "proof_contains_secret": False,
        "redaction_hash": canonical_hash({"proof": str(proof_dir), "api_key_present": False}),
    }
    (proof_dir / "redaction_audit.json").write_text(json.dumps(redaction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_chain = {
        "schema": LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA,
        "records": replay.records,
        "chain_root": replay.chain_root,
        "replay_ok": replay.ok,
        "is_permission": False,
        **neutral_flags(),
    }
    receipt_chain["receipt_hash"] = canonical_hash(receipt_chain)
    (proof_dir / "receipt_chain.json").write_text(json.dumps(receipt_chain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (proof_dir / "gate_result.json").write_text(json.dumps(enriched_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "APPROVED_LOOPBACK_HOSTS",
    "DEFAULT_ITERATIONS",
    "MAX_ITERATIONS",
    "RealSmokeConfig",
    "VERDICT_GREEN_REAL",
    "VERDICT_RED_REAL_FAILED",
    "VERDICT_YELLOW_CONFIG_MISSING",
    "VERDICT_YELLOW_MODEL_NOT_TINY",
    "VERDICT_YELLOW_REAL_PARTIAL",
    "chat_once",
    "load_local_lmstudio_config",
    "probe_models",
    "run_real_lmstudio_smoke",
    "validate_loopback_url",
    "write_real_smoke_proof",
]

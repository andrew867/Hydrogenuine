"""Phase 33.5R real-local LM Studio smoke tests.

These tests mock HTTP; they never require or call a real LM Studio server.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.local_provider_smoke.receipts import assert_not_fake_green
from hg_runtime.local_provider_smoke.real_lmstudio import (
    RealSmokeConfig,
    VERDICT_GREEN_REAL,
    VERDICT_YELLOW_MODEL_NOT_TINY,
    VERDICT_YELLOW_REAL_PARTIAL,
    chat_once,
    load_local_lmstudio_config,
    probe_models,
    run_real_lmstudio_smoke,
    validate_loopback_url,
)
from hg_runtime.local_provider_smoke.schemas import LocalProviderSmokeError


class _Resp:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _urlopen_factory(*, models=None, response_text="LOCAL_PROVIDER_SMOKE_OK", status=200, seen=None):
    seen = seen if seen is not None else []
    models = models or ["qwen2.5-0.5b-instruct"]

    def _urlopen(req, timeout=0):
        url = req.full_url
        seen.append(url)
        if url.endswith("/models"):
            return _Resp({"data": [{"id": model} for model in models]}, status=status)
        if url.endswith("/chat/completions"):
            return _Resp({"choices": [{"message": {"content": response_text}}], "usage": {"total_tokens": 7}}, status=status)
        raise AssertionError(f"unexpected url: {url}")

    return _urlopen


def _config(model="qwen2.5-0.5b-instruct", iterations=3):
    return RealSmokeConfig(
        base_url="http://127.0.0.1:1234/v1",
        api_key="local-test-key",
        model_id=model,
        timeout_seconds=5,
        soak_iterations=iterations,
    )


def test_real_smoke_requires_loopback_base_url():
    validate_loopback_url("http://127.0.0.1:1234/v1")
    validate_loopback_url("http://localhost:1234/v1")


def test_real_smoke_rejects_external_base_url():
    with pytest.raises(LocalProviderSmokeError, match="external_provider_refuses_by_default"):
        validate_loopback_url("https://api.example.invalid/v1")


def test_real_smoke_redacts_api_key(tmp_path: Path):
    proof = tmp_path / "proof"
    result = run_real_lmstudio_smoke(_config(iterations=2), proof_dir=proof, urlopen=_urlopen_factory())
    assert result["summary"]["api_key_redacted_from_all_outputs"] is True
    assert "local-test-key" not in "\n".join(p.read_text(encoding="utf-8") for p in proof.glob("*") if p.is_file())


def test_real_smoke_does_not_commit_local_config(tmp_path: Path):
    proof = tmp_path / "proof"
    run_real_lmstudio_smoke(_config(iterations=1), proof_dir=proof, urlopen=_urlopen_factory())
    audit = json.loads((proof / "redaction_audit.json").read_text(encoding="utf-8"))
    assert audit["config_file_committed"] is False


def test_real_smoke_requires_tiny_model(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"lmstudio_base_url": "http://127.0.0.1:1234/v1", "lmstudio_tiny_model": "gemma-12b"}), encoding="utf-8")
    with pytest.raises(LocalProviderSmokeError, match=VERDICT_YELLOW_MODEL_NOT_TINY):
        load_local_lmstudio_config(path)


def test_real_smoke_rejects_30b_model(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"lmstudio_base_url": "http://127.0.0.1:1234/v1", "lmstudio_tiny_model": "Qwen3-Coder-30B-A3B"}), encoding="utf-8")
    with pytest.raises(LocalProviderSmokeError, match=VERDICT_YELLOW_MODEL_NOT_TINY):
        load_local_lmstudio_config(path)


def test_real_smoke_rejects_security_model(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"lmstudio_base_url": "http://127.0.0.1:1234/v1", "lmstudio_tiny_model": "Cybersecurity-BaronLLM"}), encoding="utf-8")
    with pytest.raises(LocalProviderSmokeError, match=VERDICT_YELLOW_MODEL_NOT_TINY):
        load_local_lmstudio_config(path)


def test_real_smoke_does_not_call_load_endpoint():
    seen = []
    run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory(seen=seen))
    assert not any("/models/load" in url for url in seen)


def test_real_smoke_does_not_call_unload_endpoint():
    seen = []
    run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory(seen=seen))
    assert not any("/models/unload" in url for url in seen)


def test_real_smoke_records_model_response_non_authoritative():
    item = chat_once(_config(), urlopen=_urlopen_factory())
    assert item["is_authoritative"] is False
    assert item["is_truth"] is False


def test_real_smoke_records_latency():
    item = chat_once(_config(), urlopen=_urlopen_factory())
    assert item["latency_ms"] >= 0


def test_real_smoke_records_pass_fail_counts():
    summary = run_real_lmstudio_smoke(_config(iterations=3), urlopen=_urlopen_factory())["summary"]
    assert summary["soak_pass_count"] == 3
    assert summary["soak_fail_count"] == 0


def test_real_smoke_requires_models_endpoint_success_for_green():
    summary = run_real_lmstudio_smoke(_config(iterations=3), urlopen=_urlopen_factory(status=500))["summary"]
    assert summary["verdict"] == VERDICT_YELLOW_REAL_PARTIAL


def test_real_smoke_exact_ok_response_passes():
    result = chat_once(_config(), urlopen=_urlopen_factory(response_text="LOCAL_PROVIDER_SMOKE_OK"))
    assert result["pass"] is True
    assert result["exact_response_match"] is True


def test_real_smoke_partial_response_yellow():
    summary = run_real_lmstudio_smoke(_config(iterations=3), urlopen=_urlopen_factory(response_text="OK"))["summary"]
    assert summary["verdict"] == VERDICT_YELLOW_REAL_PARTIAL


def test_real_smoke_provider_failure_yellow_or_red():
    summary = run_real_lmstudio_smoke(_config(iterations=3), urlopen=_urlopen_factory(response_text="", status=503))["summary"]
    assert summary["verdict"] == VERDICT_YELLOW_REAL_PARTIAL


def test_real_smoke_no_external_provider():
    summary = run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory())["summary"]
    assert summary["external_provider_calls_made"] is False


def test_real_smoke_no_authority_grant():
    summary = run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory())["summary"]
    assert summary["provider_smoke_can_grant_authority"] is False


def test_real_smoke_no_tool_authorization():
    summary = run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory())["summary"]
    assert summary["provider_smoke_can_authorize_tools"] is False


def test_real_smoke_no_phase35_approval():
    summary = run_real_lmstudio_smoke(_config(iterations=1), urlopen=_urlopen_factory())["summary"]
    assert summary["provider_smoke_can_approve_phase35"] is False


def test_real_smoke_replay_deterministic(tmp_path: Path):
    proof = tmp_path / "proof"
    summary = run_real_lmstudio_smoke(_config(iterations=2), proof_dir=proof, urlopen=_urlopen_factory())["summary"]
    chain = json.loads((proof / "receipt_chain.json").read_text(encoding="utf-8"))
    assert chain["replay_ok"] is True
    assert summary["verdict"] == VERDICT_GREEN_REAL


def test_fake_green_rejected():
    with pytest.raises(LocalProviderSmokeError, match="fake_green_rejected"):
        assert_not_fake_green(
            verdict="GREEN_LOCAL_PROVIDER_SMOKE_LMSTUDIO_ONLY_OPENVINO_NOT_CONFIGURED",
            lmstudio_status="fail",
            openvino_status="not_configured",
        )


def test_models_probe_records_selected_model_present():
    record = probe_models(_config(), urlopen=_urlopen_factory(models=["qwen2.5-0.5b-instruct", "llama-3.2-1b-instruct"]))
    assert record["selected_model_present"] is True

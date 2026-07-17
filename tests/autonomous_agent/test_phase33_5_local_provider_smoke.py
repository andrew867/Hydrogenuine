"""Phase 33.5 local-provider-smoke tests.

Provider availability/health is not authority; loading/unloading is not authority; a
model response is not truth. The smoke is dry-run-safe by default: no external API
call, no real load/unload, no 30B-class or security model, no credential read. A
missing OpenVINO config is recorded honestly, never hidden behind an LM-Studio pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.local_provider_smoke import (
    HARMLESS_SMOKE_PROMPT,
    LocalProviderSmokeError,
    LocalProviderSmokeLog,
    VERDICT_GREEN_BOTH,
    VERDICT_GREEN_LMSTUDIO_ONLY,
    VERDICT_YELLOW_PARTIAL,
    assert_no_silent_fallback,
    assert_not_fake_green,
    autodetect_providers,
    build_load_plan,
    build_load_receipt,
    build_smoke_config,
    build_smoke_prompt,
    build_smoke_receipt,
    build_unload_receipt,
    compare_providers,
    determine_smoke_verdict,
    estimate_model_memory,
    is_large_model,
    is_security_model,
    is_tiny_model,
    lmstudio_smoke,
    load_smoke_config_from_env,
    openvino_smoke,
    probe_health,
    record_capability,
    record_latency,
    record_smoke_response,
    reject_credentials,
    reject_forbidden_claim_text,
    reject_openvino_gguf_assumption,
    require_local_endpoint,
    require_memory_estimate_before_large_load,
)
from hg_runtime.local_provider_smoke.schemas import reject_authority_payload
from hg_runtime.local_provider_smoke.gate import (
    evaluate_phase335_gate,
    validate_phase335_proof_bundle,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "phase335"
PANIC = OperationControl(panic_active=True)
STOP = OperationControl(stop_active=True)

TINY = "Qwen2.5-0.5B-Instruct-GGUF"
LARGE = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
SECURITY = "Cybersecurity-BaronLLM_Offensive_Security_LLM_Q6_K_GGUF"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _dry_config():
    return build_smoke_config(_load("valid_smoke_config_v1.json"))


def _both_config():
    return build_smoke_config(_load("valid_both_configured_config_v1.json"))


# --------------------------------------------------------------------------- #
# Authority / claim boundary                                                  #
# --------------------------------------------------------------------------- #
def test_provider_smoke_cannot_grant_authority():
    with pytest.raises(LocalProviderSmokeError, match="authority_bypass_attempt"):
        reject_authority_payload({"smoke_grants_authority": True})


def test_provider_smoke_cannot_authorize_tools():
    with pytest.raises(LocalProviderSmokeError, match="authority_bypass_attempt"):
        reject_authority_payload({"smoke_authorizes_tool": True})


def test_provider_smoke_cannot_create_live_effects():
    with pytest.raises(LocalProviderSmokeError, match="authority_bypass_attempt"):
        reject_authority_payload({"live_external_side_effects_created": True})


def test_provider_smoke_cannot_claim_agi():
    with pytest.raises(LocalProviderSmokeError, match="agi_claim_rejected"):
        reject_forbidden_claim_text("This smoke proves AGI.")


def test_provider_smoke_cannot_claim_deployment_readiness():
    with pytest.raises(LocalProviderSmokeError, match="deployment_readiness_claim_rejected"):
        reject_forbidden_claim_text("Provider smoke shows deployment readiness.")


# --------------------------------------------------------------------------- #
# Read-only probes / autodetect                                               #
# --------------------------------------------------------------------------- #
def test_provider_health_probe_is_read_only_by_default():
    probe = probe_health(provider_id="lmstudio", kind="lmstudio", endpoint="http://localhost:1234/v1", configured=True)
    assert probe["read_only"] is True
    assert probe["loaded_model"] is False
    assert probe["network_call_made"] is False


def test_startup_autodetect_is_read_only_by_default():
    result = autodetect_providers(_both_config())
    assert result["read_only"] is True


def test_startup_autodetect_does_not_load_model():
    result = autodetect_providers(_both_config())
    assert result["loaded_model"] is False


def test_startup_autodetect_does_not_unload_model():
    result = autodetect_providers(_both_config())
    assert result["unloaded_model"] is False


def test_autodetect_detects_configured_providers():
    detected = {d["provider_id"] for d in autodetect_providers(_both_config())["detected"]}
    assert detected == {"lmstudio", "openvino"}
    assert autodetect_providers(_dry_config())["detected"][0]["provider_id"] == "lmstudio"


# --------------------------------------------------------------------------- #
# LM Studio                                                                    #
# --------------------------------------------------------------------------- #
def test_lmstudio_base_url_is_configurable():
    config = build_smoke_config({"lmstudio_base_url": "http://localhost:4321/v1"})
    assert config["lmstudio_base_url"] == "http://localhost:4321/v1"


def test_lmstudio_openai_compat_probe_records_capabilities():
    record = lmstudio_smoke(_dry_config())
    assert record["capability"]["supports_chat_completions"] is True
    assert record["capability"]["supports_models_list"] is True
    assert record["endpoint_probe"]["supports_chat_completions"] is True


def test_lmstudio_smoke_uses_tiny_model_only_by_default():
    # Default dry config names a tiny model; building the prompt for a large one refuses.
    assert is_tiny_model(TINY)
    with pytest.raises(LocalProviderSmokeError, match="large_model_not_allowed_in_default_smoke"):
        build_smoke_prompt(model_id=LARGE)


def test_lmstudio_dry_mode_status_is_skipped():
    record = lmstudio_smoke(_dry_config())
    assert record["status"] == "skipped_dry_run"
    assert record["real_call_made"] is False


def test_lmstudio_real_load_requires_operator_enabled_flag():
    # enable_real but no allow_load.
    config = build_smoke_config({"enable_real": True, "lmstudio_base_url": "http://localhost:1234/v1", "allow_load": False})
    with pytest.raises(LocalProviderSmokeError, match="real_load_requires_operator_enabled_flag"):
        build_load_receipt(config=config, provider_id="lmstudio", model_id=TINY, instance_id="inst-1")


def test_lmstudio_real_unload_requires_owned_loaded_instance():
    config = build_smoke_config({"enable_real": True, "lmstudio_base_url": "http://localhost:1234/v1", "allow_unload": True})
    with pytest.raises(LocalProviderSmokeError, match="unload_requires_owned_loaded_instance"):
        build_unload_receipt(config=config, provider_id="lmstudio", instance_id="not-mine", owned_instance_ids=["inst-1"])


# --------------------------------------------------------------------------- #
# OpenVINO                                                                     #
# --------------------------------------------------------------------------- #
def test_openvino_endpoint_is_configurable():
    config = build_smoke_config({"openvino_base_url": "http://localhost:9000/v3"})
    assert config["openvino_base_url"] == "http://localhost:9000/v3"
    assert config["openvino_configured"] is True


def test_openvino_probe_records_chat_completions_compatibility():
    record = openvino_smoke(_both_config())
    assert record["capability"]["supports_chat_completions"] is True


def test_openvino_not_configured_is_recorded_not_hidden():
    record = openvino_smoke(_dry_config())
    assert record["status"] == "not_configured"
    assert record["incompatibility"]["reason"] == "openvino_not_configured"
    assert record["incompatibility"]["hidden"] is False


def test_openvino_gguf_assumption_is_rejected():
    incompat = reject_openvino_gguf_assumption(provider_kind="openvino", model_id="Qwen2.5-0.5B-Instruct-GGUF")
    assert incompat["reason"] == "openvino_gguf_assumption_rejected"
    # A GGUF model named for OpenVINO in a configured smoke records the incompatibility.
    config = build_smoke_config({"openvino_base_url": "http://localhost:9000/v3", "openvino_tiny_model": "model-GGUF"})
    record = openvino_smoke(config)
    assert record["incompatibility"]["reason"] == "openvino_gguf_assumption_rejected"
    assert record["gguf_loader_assumed"] is False


# --------------------------------------------------------------------------- #
# Failure / comparison / memory                                               #
# --------------------------------------------------------------------------- #
def test_provider_failure_does_not_silent_fallback():
    assert_no_silent_fallback("lmstudio", None)
    with pytest.raises(LocalProviderSmokeError, match="provider_failure_silent_fallback_refused"):
        assert_no_silent_fallback("lmstudio", "openvino")


def test_provider_comparison_records_latency():
    record = compare_providers([{"provider_id": "lmstudio", "status": "pass", "latency_ms": 120.0, "quirks": []}])
    assert record["providers"][0]["latency_ms"] == 120.0


def test_provider_comparison_records_compatibility_quirks():
    record = compare_providers([{"provider_id": "openvino", "status": "pass", "latency_ms": 90.0, "quirks": ["v3_chat_completions"]}])
    assert "v3_chat_completions" in record["providers"][0]["quirks"]


def test_model_memory_estimate_required_before_large_load():
    with pytest.raises(LocalProviderSmokeError, match="model_memory_estimate_required_before_large_load"):
        require_memory_estimate_before_large_load(LARGE, None)
    estimate = estimate_model_memory({"model_id": LARGE})
    assert require_memory_estimate_before_large_load(LARGE, estimate) is estimate


def test_thirty_b_model_never_required_for_green():
    estimate = estimate_model_memory({"model_id": LARGE})
    assert estimate["required_for_green"] is False
    # A clean LM-only verdict needs no large model.
    assert determine_smoke_verdict("pass", "not_configured") == VERDICT_GREEN_LMSTUDIO_ONLY


def test_thirty_b_model_is_load_on_demand_only():
    estimate = estimate_model_memory({"model_id": LARGE})
    assert estimate["size_class"] == "large"
    assert estimate["load_on_demand_only"] is True


def test_thirty_b_load_plan_requires_memory_estimate():
    with pytest.raises(LocalProviderSmokeError, match="model_memory_estimate_required_before_large_load"):
        build_load_plan(provider_id="lmstudio", model_id=LARGE, allow_large=True)
    estimate = estimate_model_memory({"model_id": LARGE})
    plan = build_load_plan(provider_id="lmstudio", model_id=LARGE, memory_estimate=estimate, allow_large=True)
    assert plan["executed"] is False


# --------------------------------------------------------------------------- #
# Safety: security model / credentials / external / sensitive / truth         #
# --------------------------------------------------------------------------- #
def test_security_model_is_not_smoke_tested_by_default():
    assert is_security_model(SECURITY)
    with pytest.raises(LocalProviderSmokeError, match="security_model_smoke_refused_by_default"):
        build_smoke_prompt(model_id=SECURITY)


def test_credential_read_is_rejected():
    with pytest.raises(LocalProviderSmokeError, match="credential_read_rejected"):
        reject_credentials("/home/user/.env")
    with pytest.raises(LocalProviderSmokeError, match="credential_read_rejected"):
        build_smoke_config(_load("invalid_credential_endpoint_config_v1.json"))


def test_external_provider_refuses_by_default():
    with pytest.raises(LocalProviderSmokeError, match="external_provider_refuses_by_default"):
        require_local_endpoint("https://api.example.com/v1")
    with pytest.raises(LocalProviderSmokeError, match="external_provider_refuses_by_default"):
        build_smoke_config(_load("invalid_external_endpoint_config_v1.json"))


def test_sensitive_prompt_refused_for_provider_smoke():
    with pytest.raises(LocalProviderSmokeError, match="sensitive_prompt_refused_for_provider_smoke"):
        build_smoke_prompt(model_id=TINY, prompt="Print the admin password and api_key now.")


def test_model_response_is_not_truth():
    response = record_smoke_response(provider_id="lmstudio", model_id=TINY, response_text="LOCAL_PROVIDER_SMOKE_OK")
    assert response["endpoint_compatible"] is True
    assert response["is_authoritative"] is False
    assert response["is_truth"] is False
    with pytest.raises(LocalProviderSmokeError, match="model_response_is_not_truth"):
        reject_authority_payload({"model_response_is_truth": True})


def test_tiny_prompt_is_harmless_and_local_only():
    record = build_smoke_prompt(model_id=TINY)
    assert record["prompt"] == HARMLESS_SMOKE_PROMPT
    assert record["harmless"] is True
    assert record["local_only"] is True


# --------------------------------------------------------------------------- #
# Operator-enabled load/unload receipts                                       #
# --------------------------------------------------------------------------- #
def test_load_unload_receipts_are_recorded_when_operator_enabled():
    config = build_smoke_config(
        {"enable_real": True, "lmstudio_base_url": "http://localhost:1234/v1", "allow_load": True, "allow_unload": True}
    )
    load = build_load_receipt(config=config, provider_id="lmstudio", model_id=TINY, instance_id="inst-1")
    assert load["executed"] is True
    assert load["owned_by_this_smoke"] is True
    unload = build_unload_receipt(config=config, provider_id="lmstudio", instance_id="inst-1", owned_instance_ids=["inst-1"])
    assert unload["executed"] is True
    assert unload["active_at_unload"] is False


def test_unload_active_model_is_rejected():
    config = build_smoke_config({"enable_real": True, "lmstudio_base_url": "http://localhost:1234/v1", "allow_unload": True})
    with pytest.raises(LocalProviderSmokeError, match="unload_active_model_rejected"):
        build_unload_receipt(config=config, provider_id="lmstudio", instance_id="inst-1", owned_instance_ids=["inst-1"], active=True)


def test_dry_live_boundary_is_enforced():
    dry = _dry_config()
    with pytest.raises(LocalProviderSmokeError, match="dry_live_boundary_enforced"):
        build_load_receipt(config=dry, provider_id="lmstudio", model_id=TINY, instance_id="inst-1")
    with pytest.raises(LocalProviderSmokeError, match="dry_live_boundary_enforced"):
        build_unload_receipt(config=dry, provider_id="lmstudio", instance_id="inst-1", owned_instance_ids=["inst-1"])


# --------------------------------------------------------------------------- #
# Verdict / fake green / receipts / schema                                    #
# --------------------------------------------------------------------------- #
def test_verdict_determination_is_partial_aware():
    assert determine_smoke_verdict("pass", "pass") == VERDICT_GREEN_BOTH
    assert determine_smoke_verdict("pass", "not_configured") == VERDICT_GREEN_LMSTUDIO_ONLY
    assert determine_smoke_verdict("skipped_dry_run", "not_configured") == VERDICT_YELLOW_PARTIAL
    assert determine_smoke_verdict("pass", "fail") == VERDICT_YELLOW_PARTIAL
    assert determine_smoke_verdict("fail", "pass").startswith("RED")


def test_fake_green_attempt_is_rejected():
    with pytest.raises(LocalProviderSmokeError, match="fake_green_rejected"):
        assert_not_fake_green(verdict=VERDICT_GREEN_BOTH, lmstudio_status="pass", openvino_status="not_configured")
    with pytest.raises(LocalProviderSmokeError, match="fake_green_rejected"):
        assert_not_fake_green(verdict=VERDICT_GREEN_LMSTUDIO_ONLY, lmstudio_status="fail", openvino_status="not_configured")


def test_missing_receipt_blocks_success():
    with pytest.raises(LocalProviderSmokeError, match="missing_receipt_blocks_success"):
        build_smoke_receipt(verdict=VERDICT_GREEN_BOTH, lmstudio_status="pass", openvino_status="pass", receipt_refs=[])
    ok = build_smoke_receipt(verdict=VERDICT_YELLOW_PARTIAL, lmstudio_status="skipped_dry_run", openvino_status="not_configured", receipt_refs=[])
    assert ok["is_permission"] is False


def test_schema_violation_blocks_success():
    with pytest.raises(LocalProviderSmokeError, match="schema_violation:missing"):
        record_capability({"kind": "lmstudio"})


# --------------------------------------------------------------------------- #
# STOP / PANIC and replay                                                      #
# --------------------------------------------------------------------------- #
def test_stop_panic_preempts_provider_smoke():
    with pytest.raises(LocalProviderSmokeError, match="REFUSED_PANIC"):
        lmstudio_smoke(_dry_config(), control=PANIC)
    with pytest.raises(LocalProviderSmokeError, match="REFUSED_STOP"):
        build_smoke_prompt(model_id=TINY, control=STOP)


def test_replay_is_deterministic(tmp_path):
    log = LocalProviderSmokeLog(tmp_path / "smoke.jsonl")
    log.append("provider_health_probe_v1", {"provider_id": "lmstudio", "status": "skipped_dry_run"})
    log.append("local_provider_smoke_receipt_v1", {"verdict": VERDICT_YELLOW_PARTIAL})
    first = log.replay()
    assert first.ok is True and first.records == 2
    second = LocalProviderSmokeLog(tmp_path / "smoke.jsonl").replay()
    assert second.chain_root == first.chain_root


def test_replay_divergence_is_failure(tmp_path):
    path = tmp_path / "smoke.jsonl"
    log = LocalProviderSmokeLog(path)
    log.append("provider_health_probe_v1", {"provider_id": "lmstudio", "status": "skipped_dry_run"})
    log.append("provider_health_probe_v1", {"provider_id": "openvino", "status": "not_configured"})
    lines = path.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[1])
    data["payload"]["status"] = "pass"  # tamper
    lines[1] = json.dumps(data, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = LocalProviderSmokeLog(path).replay()
    assert result.ok is False
    assert any("payload_hash_mismatch" in err for err in result.errors)


def test_replay_preempted_by_panic(tmp_path):
    log = LocalProviderSmokeLog(tmp_path / "smoke.jsonl")
    log.append("provider_health_probe_v1", {"provider_id": "lmstudio"})
    with pytest.raises(LocalProviderSmokeError, match="REFUSED_PANIC"):
        log.replay(control=PANIC)


# --------------------------------------------------------------------------- #
# Config from env / latency                                                    #
# --------------------------------------------------------------------------- #
def test_config_from_env_is_dry_by_default():
    config = load_smoke_config_from_env(env={})
    assert config["enable_real"] is False
    assert config["read_only"] is True
    assert config["openvino_configured"] is False  # not set -> honestly unconfigured


def test_latency_record_computes_tps():
    record = record_latency(provider_id="lmstudio", model_id=TINY, latency_ms=500.0, tokens_out=50)
    assert record["approx_tokens_per_sec"] == 100.0


# --------------------------------------------------------------------------- #
# Gate                                                                         #
# --------------------------------------------------------------------------- #
def _valid_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"):
        (bundle / name).write_text("{}\n" if name.endswith(".json") else "x\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle)}) + "\n", encoding="utf-8")
    return bundle


def _green_kwargs(bundle, **over):
    base = dict(
        phase33_green=True,
        phase34_green=True,
        proof_bundle=bundle,
        tests_passed=True,
        lmstudio_status="skipped_dry_run",
        openvino_status="not_configured",
        report_exists=True,
        smoke_cannot_grant_authority=True,
        smoke_cannot_authorize_tools=True,
        smoke_cannot_create_live_effects=True,
        smoke_cannot_claim_agi=True,
        startup_autodetect_read_only=True,
        lmstudio_base_url_configurable=True,
        openvino_endpoint_configurable=True,
        openvino_not_configured_recorded_honestly=True,
        openvino_gguf_assumption_rejected=True,
        provider_failure_no_silent_fallback=True,
        model_response_non_authoritative=True,
        thirty_b_load_on_demand_only=True,
        thirty_b_not_required_for_green=True,
        security_model_not_smoked_by_default=True,
        credential_reads_rejected=True,
        external_provider_refuses_by_default=True,
        fake_green_rejected=True,
        replay_deterministic=True,
        stop_panic_preemption_preserved=True,
        no_live_external_side_effect_path_by_default=True,
    )
    base.update(over)
    return base


def test_phase335_gate_dry_mode_is_yellow_partial_and_ok(tmp_path):
    bundle = _valid_bundle(tmp_path)
    result = evaluate_phase335_gate(**_green_kwargs(bundle))
    assert result["verdict"] == VERDICT_YELLOW_PARTIAL
    assert result["ok"] is True
    assert result["real_lmstudio_calls_made"] is False


def test_phase335_gate_both_pass_is_green_both(tmp_path):
    bundle = _valid_bundle(tmp_path)
    result = evaluate_phase335_gate(**_green_kwargs(bundle, lmstudio_status="pass", openvino_status="pass"))
    assert result["verdict"] == VERDICT_GREEN_BOTH
    assert result["ok"] is True


def test_phase335_gate_refuses_without_phase33_phase34_green(tmp_path):
    bundle = _valid_bundle(tmp_path)
    result = evaluate_phase335_gate(**_green_kwargs(bundle, phase34_green=False))
    assert result["ok"] is False
    assert result["verdict"].startswith("RED")
    assert any("PHASE34_GREEN_REQUIRED" in f for f in result["failures"])


def test_phase335_gate_refuses_without_proof_bundle():
    result = evaluate_phase335_gate(**_green_kwargs(None))
    assert result["ok"] is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in result["failures"])


def test_proof_bundle_validator_detects_missing_files(tmp_path):
    bundle = tmp_path / "incomplete"
    bundle.mkdir()
    (bundle / "HEAD.txt").write_text("x\n", encoding="utf-8")
    ok, failures = validate_phase335_proof_bundle(bundle)
    assert ok is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in failures)

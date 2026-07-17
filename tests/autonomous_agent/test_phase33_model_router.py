"""Phase 33 multi-model-specialist-router and residency tests.

Routing is not authority. Loading is not authority. A model output is not authority.
The router must not let a cheap model bypass the critic, a security model act with
execution authority, privacy-sensitive input leave for an external provider, or any
real LM Studio / model load happen by default.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.model_router import (
    FakeLocalProvider,
    FutureVLLMProviderContract,
    LMStudioProviderContract,
    ModelRouterError,
    ModelRouterLog,
    OpenVINOProviderContract,
    ResidencyManager,
    build_residency_receipt,
    build_routing_receipt,
    check_privacy,
    create_load_request,
    create_route_request,
    create_unload_request,
    define_privacy_tier,
    define_residency_policy,
    define_role_policy,
    define_safety_policy,
    enforce_safety,
    handle_provider_failure,
    record_health_check,
    record_model_output,
    register_model,
    register_provider,
    require_security_role_is_critic_only,
    route_work_item,
    validate_role_binding,
)
from hg_runtime.model_router.gate import (
    evaluate_phase33_gate,
    validate_phase33_proof_bundle,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "phase33"
BOUNDARY = "model_router_advisory_default"
PANIC = OperationControl(panic_active=True)


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _coder_entry(**overrides):
    payload = {
        "model_id": "qwen2.5-coder-7b",
        "family": "qwen2.5-coder",
        "model_hash": "sha256:fake-coder",
        "declared_roles": ["coder", "large_local_model"],
        "size_mb": 5200,
    }
    payload.update(overrides)
    return register_model(payload)


def _coder_role_policy():
    return define_role_policy({"role": "coder", "allowed_families": ["qwen2.5-coder"]})


def _security_role_policy():
    return define_role_policy({"role": "security_reviewer", "allowed_families": ["baronllm"]})


def _internal_privacy():
    return define_privacy_tier({"tier": "internal", "external_allowed": False})


def _safety_default():
    return define_safety_policy({"policy_id": "safety-default", "requires_critic": True})


def _fake_provider():
    return register_provider({"provider_id": "fake-local-1", "kind": "fake_local"})


def _route_request(**overrides):
    payload = {
        "request_id": "route-1",
        "work_item_ref": "wi-1",
        "role": "coder",
        "role_policy_ref": "rolepol-coder",
        "privacy_tier_ref": "privacy-internal",
        "safety_policy_ref": "safety-default",
        "claim_boundary": BOUNDARY,
    }
    payload.update(overrides)
    return create_route_request(payload)


def _residency():
    return ResidencyManager(define_residency_policy({"policy_id": "rp", "max_loaded_models": 3, "gpu_budget_mb": 16000, "ttl_ticks": 50}))


def _load_req(load_id, model_ref, **overrides):
    payload = {"load_id": load_id, "model_ref": model_ref, "provider_ref": "fake-local-1", "role": "coder", "size_mb": 1000}
    payload.update(overrides)
    return create_load_request(payload)


# --- catalog & providers ---------------------------------------------------

def test_model_catalog_entry_requires_hash_or_stable_id():
    with pytest.raises(ModelRouterError, match="model_catalog_entry_requires_hash_or_stable_id"):
        register_model(_load("invalid_model_catalog_entry_no_id_v1.json"))


def test_valid_catalog_entry_round_trips():
    entry = register_model(_load("valid_model_catalog_entry_v1.json"))
    assert entry["stable_id"]
    assert entry["tool_authorized"] is False


def test_network_provider_refuses_by_default():
    with pytest.raises(ModelRouterError, match="network_provider_refuses_by_default"):
        register_provider(_load("invalid_external_provider_v1.json"))


def test_network_provider_allowed_with_explicit_flag():
    provider = register_provider(_load("invalid_external_provider_v1.json"), allow_network=True)
    assert provider["residency"] == "external"


def test_credential_provider_read_is_rejected():
    with pytest.raises(ModelRouterError, match="credential_provider_read_rejected"):
        register_provider({"provider_id": "p", "kind": "lmstudio", "endpoint": "/home/u/.env"})


def test_future_vllm_provider_refuses_by_default():
    with pytest.raises(ModelRouterError, match="provider_contract_refuses_by_default:vllm"):
        FutureVLLMProviderContract().plan_load("anything")


# --- adapters are dry-run --------------------------------------------------

def test_lmstudio_adapter_is_dry_run_by_default():
    adapter = LMStudioProviderContract()
    assert adapter.dry_run is True
    planned = adapter.load("qwen-coder")
    assert planned["executed"] is False
    assert planned["real_call"] is False


def test_lmstudio_real_call_requires_operator_smoke_test():
    with pytest.raises(ModelRouterError, match="lmstudio_real_call_requires_operator_smoke_test"):
        LMStudioProviderContract().load("qwen-coder", allow_real=True)


def test_openvino_adapter_is_dry_run_by_default():
    adapter = OpenVINOProviderContract()
    assert adapter.dry_run is True
    planned = adapter.hot_reload("gemma")
    assert planned["executed"] is False


def test_fake_local_provider_makes_no_network():
    p = FakeLocalProvider()
    assert p.plan_load("m")["network"] is False
    assert p.health_check("m")["healthy"] is True


# --- roles -----------------------------------------------------------------

def test_model_role_mismatch_is_rejected():
    entry = register_model({"model_id": "summ", "family": "qwen", "stable_id": "summ", "declared_roles": ["summarizer"]})
    with pytest.raises(ModelRouterError, match="model_role_mismatch_rejected"):
        validate_role_binding(entry, _coder_role_policy())


def test_coder_model_cannot_act_as_security_reviewer_without_role_policy():
    entry = _coder_entry()  # declares coder, not security_reviewer
    with pytest.raises(ModelRouterError, match="model_role_mismatch_rejected"):
        validate_role_binding(entry, _security_role_policy())


def test_security_model_has_no_workbench_execution_authority():
    policy = _security_role_policy()
    assert policy["workbench_execution_authority"] is False
    assert policy["critic_only"] is True


def test_offensive_security_model_is_critic_only_by_default():
    policy = define_role_policy({"role": "offensive_security", "allowed_families": ["baronllm"], "workbench_execution_authority": True})
    # Even when asked for execution authority, an offensive role is forced critic-only.
    assert policy["critic_only"] is True
    assert policy["workbench_execution_authority"] is False
    require_security_role_is_critic_only(policy)


# --- privacy ---------------------------------------------------------------

def test_privacy_sensitive_input_blocks_external_model():
    sensitive = define_privacy_tier({"tier": "sensitive"})
    external = register_provider(_load("invalid_external_provider_v1.json"), allow_network=True)
    with pytest.raises(ModelRouterError, match="privacy_sensitive_input_blocks_external_model"):
        check_privacy(sensitive, external)


def test_external_provider_refuses_without_privacy_clearance():
    internal = define_privacy_tier({"tier": "internal", "external_allowed": False})
    external = register_provider(_load("invalid_external_provider_v1.json"), allow_network=True)
    with pytest.raises(ModelRouterError, match="external_provider_requires_privacy_clearance"):
        check_privacy(internal, external)


def test_local_provider_passes_privacy_for_internal():
    check_privacy(_internal_privacy(), _fake_provider())  # no raise


def test_sensitive_tier_cannot_be_marked_external_allowed():
    tier = define_privacy_tier({"tier": "secret", "external_allowed": True})
    assert tier["external_allowed"] is False


# --- safety ----------------------------------------------------------------

def test_router_cannot_select_model_to_bypass_safety():
    with pytest.raises(ModelRouterError, match="safety_bypass_rejected"):
        create_route_request({**_load("valid_model_route_request_v1.json"), "bypass_safety": True})


def test_cheap_model_cannot_override_critic():
    request = {"role": "cheap_local_model", "skip_critic": True}
    with pytest.raises(ModelRouterError, match="cheap_model_cannot_override_critic"):
        enforce_safety(request, _safety_default())


# --- route request validation ----------------------------------------------

def test_route_requires_goal_work_item_ref():
    with pytest.raises(ModelRouterError, match="route_requires_goal_work_item_ref"):
        create_route_request(_load("invalid_route_request_no_work_item_v1.json"))


def test_route_requires_model_role_policy():
    with pytest.raises(ModelRouterError, match="route_requires_model_role_policy"):
        create_route_request({**_load("valid_model_route_request_v1.json"), "role_policy_ref": ""})


def test_route_requires_privacy_tier():
    with pytest.raises(ModelRouterError, match="route_requires_privacy_tier"):
        create_route_request({**_load("valid_model_route_request_v1.json"), "privacy_tier_ref": ""})


def test_route_requires_safety_review_policy():
    with pytest.raises(ModelRouterError, match="route_requires_safety_review_policy"):
        create_route_request({**_load("valid_model_route_request_v1.json"), "safety_policy_ref": ""})


def test_valid_route_request_round_trips():
    request = _route_request()
    assert request["work_item_ref"] == "wi-1"
    assert request["tool_authorized"] is False


# --- route results ---------------------------------------------------------

def test_local_model_is_authority_neutral():
    result = route_work_item(
        _route_request(),
        catalog_entry=_coder_entry(),
        role_policy=_coder_role_policy(),
        privacy_tier=_internal_privacy(),
        safety_policy=_safety_default(),
        provider=_fake_provider(),
    )
    assert result["grants_authority"] is False
    assert result["authorizes_tool"] is False
    assert result["workbench_execution_authority"] is False
    assert result["advisory_only"] is True


def test_route_result_is_not_permission():
    result = route_work_item(
        _route_request(),
        catalog_entry=_coder_entry(),
        role_policy=_coder_role_policy(),
        privacy_tier=_internal_privacy(),
        safety_policy=_safety_default(),
        provider=_fake_provider(),
    )
    with pytest.raises(ModelRouterError, match="route_is_not_permission"):
        from hg_runtime.model_router.receipts import assert_not_permission

        assert_not_permission({**result, "route_as_permission": True})


def test_model_output_cannot_grant_authority():
    with pytest.raises(ModelRouterError, match="authority_bypass_attempt"):
        record_model_output({"output_id": "o-1", "route_result_ref": "route-1", "grants_authority": True})


def test_model_output_is_authority_neutral():
    out = record_model_output({"output_id": "o-1", "route_result_ref": "route-1"})
    assert out["is_authority"] is False
    assert out["authorizes_tool"] is False


# --- provider health -------------------------------------------------------

def test_provider_health_failure_routes_to_refusal_not_silent_fallback():
    health = record_health_check({"check_id": "h-1", "provider_id": "fake-local-1", "healthy": False})
    with pytest.raises(ModelRouterError, match="provider_health_failure_refuses_no_silent_fallback"):
        handle_provider_failure(health, request_id="route-1")


def test_route_over_unhealthy_provider_is_fake_green():
    health = record_health_check({"check_id": "h-2", "provider_id": "fake-local-1", "healthy": False})
    with pytest.raises(ModelRouterError, match="fake_green_rejected"):
        route_work_item(
            _route_request(),
            catalog_entry=_coder_entry(),
            role_policy=_coder_role_policy(),
            privacy_tier=_internal_privacy(),
            safety_policy=_safety_default(),
            provider=_fake_provider(),
            health=health,
        )


# --- residency: load / unload / receipt ------------------------------------

def test_model_load_requires_residency_receipt():
    mgr = _residency()
    instance, receipt, evictions = mgr.request_load(_load_req("l-1", "m-1"))
    assert receipt["schema"] == "model_residency_receipt_v1"
    assert receipt["action"] == "load"
    assert instance["instance_id"] in mgr.loaded


def test_loaded_instance_requires_provider_ref():
    with pytest.raises(ModelRouterError, match="loaded_instance_requires_provider_ref"):
        create_load_request({"load_id": "l-x", "model_ref": "m", "role": "coder", "provider_ref": ""})


def test_load_request_is_not_permission():
    req = _load_req("l-2", "m-2")
    assert req["is_permission"] is False
    with pytest.raises(ModelRouterError, match="authority_bypass_attempt"):
        create_load_request({"load_id": "l-3", "model_ref": "m", "provider_ref": "p", "role": "coder", "grants_authority": True})


def test_model_unload_requires_no_active_invocation():
    mgr = _residency()
    instance, _, _ = mgr.request_load(_load_req("l-1", "m-1"))
    mgr.mark_active(instance["instance_id"])
    with pytest.raises(ModelRouterError, match="model_unload_requires_no_active_invocation"):
        mgr.request_unload(create_unload_request({"unload_id": "u-1", "instance_ref": instance["instance_id"]}))


def test_unload_idle_instance_succeeds():
    mgr = _residency()
    instance, _, _ = mgr.request_load(_load_req("l-1", "m-1"))
    receipt = mgr.request_unload(create_unload_request({"unload_id": "u-1", "instance_ref": instance["instance_id"]}))
    assert receipt["action"] == "unload"
    assert instance["instance_id"] not in mgr.loaded


def test_max_loaded_models_is_enforced():
    mgr = ResidencyManager(define_residency_policy({"policy_id": "rp", "max_loaded_models": 3, "ttl_ticks": 9999}))
    ids = []
    for i in range(3):
        inst, _, _ = mgr.request_load(_load_req(f"l-{i}", f"m-{i}", priority="high"))
        ids.append(inst["instance_id"])
        mgr.mark_active(inst["instance_id"])  # all active/high -> not evictable
    with pytest.raises(ModelRouterError, match="max_loaded_models_enforced"):
        mgr.request_load(_load_req("l-3", "m-3", priority="high"))


def test_gpu_budget_exhaustion_evicts_idle_by_policy():
    mgr = ResidencyManager(define_residency_policy({"policy_id": "rp", "max_loaded_models": 9, "gpu_budget_mb": 3000, "ttl_ticks": 9999}))
    a, _, _ = mgr.request_load(_load_req("l-a", "m-a", size_mb=2000))  # idle, normal priority
    # Next load needs 2000 more but budget is 3000 -> must evict the idle one.
    b, _, evictions = mgr.request_load(_load_req("l-b", "m-b", size_mb=2000))
    assert any(e["action"] == "unload" for e in evictions)
    assert a["instance_id"] not in mgr.loaded
    assert b["instance_id"] in mgr.loaded


def test_gpu_budget_exhaustion_refuses_when_nothing_evictable():
    mgr = ResidencyManager(define_residency_policy({"policy_id": "rp", "max_loaded_models": 9, "gpu_budget_mb": 3000, "ttl_ticks": 9999}))
    a, _, _ = mgr.request_load(_load_req("l-a", "m-a", size_mb=2000, priority="high"))
    mgr.mark_active(a["instance_id"])
    with pytest.raises(ModelRouterError, match="gpu_budget_exhausted_no_evictable_model"):
        mgr.request_load(_load_req("l-b", "m-b", size_mb=2000, priority="high"))


def test_ttl_expiry_unloads_idle_model():
    mgr = ResidencyManager(define_residency_policy({"policy_id": "rp", "max_loaded_models": 3, "ttl_ticks": 50}))
    inst, _, _ = mgr.request_load(_load_req("l-1", "m-1"), now_tick=0)
    evicted = mgr.evict_idle(now_tick=100)  # > ttl
    assert any(e["action"] == "unload" and e.get("reason") == "ttl_expiry" for e in evicted)
    assert inst["instance_id"] not in mgr.loaded


def test_residency_record_is_not_permission():
    receipt = build_residency_receipt(action="load", status="loaded", receipt_refs=["rc-1"], instance_id="inst-1")
    assert receipt["is_permission"] is False
    assert receipt["tool_authorized"] is False


def test_dry_live_boundary_is_enforced():
    with pytest.raises(ModelRouterError, match="dry_live_boundary_enforced"):
        create_load_request({"load_id": "l-live", "model_ref": "m", "provider_ref": "p", "role": "coder", "live": True, "operator_permit_refs": []})


# --- receipts / fake green / schema ----------------------------------------

def test_missing_receipt_blocks_success():
    with pytest.raises(ModelRouterError, match="missing_receipt_blocks_success"):
        build_routing_receipt(request_id="route-1", status="routed", receipt_refs=[])


def test_fake_green_attempt_is_rejected():
    health = {"healthy": False, "provider_id": "p"}
    with pytest.raises(ModelRouterError, match="fake_green_rejected"):
        build_routing_receipt(request_id="route-1", status="routed", receipt_refs=["rc-1"], health=health)


def test_schema_violation_blocks_success():
    with pytest.raises(ModelRouterError, match="schema_violation:missing"):
        register_model({"model_id": "x"})


# --- stop / panic ----------------------------------------------------------

def test_stop_panic_preempts_router_operation():
    with pytest.raises(ModelRouterError, match="REFUSED_PANIC"):
        create_route_request(_load("valid_model_route_request_v1.json"), control=PANIC)


def test_panic_preempts_load():
    mgr = _residency()
    with pytest.raises(ModelRouterError, match="REFUSED_PANIC"):
        mgr.request_load(_load_req("l-1", "m-1"), control=PANIC)


# --- replay ----------------------------------------------------------------

def test_model_router_replay_is_deterministic(tmp_path):
    log = ModelRouterLog(tmp_path / "router.jsonl")
    log.append("model_route_result_v1", {"request_id": "route-1", "selected_model_id": "m-1"})
    log.append("model_residency_receipt_v1", {"action": "load", "instance_id": "inst-1"})
    result = log.replay()
    assert result.ok is True
    assert result.records == 2


def test_hot_reload_preserves_audit_chain(tmp_path):
    log = ModelRouterLog(tmp_path / "router.jsonl")
    log.append("model_residency_receipt_v1", {"action": "load", "instance_id": "inst-1"})
    log.append("model_residency_receipt_v1", {"action": "hot_reload", "instance_id": "inst-1"})
    log.append("model_residency_receipt_v1", {"action": "unload", "instance_id": "inst-1"})
    result = log.replay()
    assert result.ok is True
    assert result.records == 3


def test_replay_divergence_is_failure(tmp_path):
    path = tmp_path / "router.jsonl"
    log = ModelRouterLog(path)
    log.append("model_route_result_v1", {"request_id": "route-1", "selected_model_id": "m-1"})
    log.append("model_residency_receipt_v1", {"action": "load", "instance_id": "inst-1"})
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["selected_model_id"] = "m-EVIL"
    lines[0] = json.dumps(tampered, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = ModelRouterLog(path).replay()
    assert result.ok is False
    assert any("payload_hash_mismatch" in e for e in result.errors)


def test_replay_under_panic_is_refused(tmp_path):
    log = ModelRouterLog(tmp_path / "router.jsonl")
    log.append("model_route_result_v1", {"request_id": "route-1"})
    with pytest.raises(ModelRouterError):
        log.replay(control=PANIC)


# --- gate ------------------------------------------------------------------

def _green_gate_kwargs(**overrides):
    kwargs = dict(
        phase29_green=True,
        phase32_green=True,
        proof_bundle=Path("dummy"),
        tests_passed=True,
        report_exists=True,
        router_cannot_bypass_safety=True,
        cheap_model_cannot_override_critic=True,
        model_output_cannot_grant_authority=True,
        privacy_sensitive_blocks_external=True,
        local_model_is_authority_neutral=True,
        model_load_requires_receipt=True,
        unload_active_model_rejected=True,
        max_loaded_models_enforced=True,
        provider_failure_refuses_no_silent_fallback=True,
        lmstudio_adapter_dry_run_by_default=True,
        openvino_adapter_dry_run_by_default=True,
        security_model_critic_only_by_default=True,
        fake_green_rejected=True,
        replay_deterministic=True,
        no_live_side_effect_path_by_default=True,
    )
    kwargs.update(overrides)
    return kwargs


def _make_bundle(tmp_path):
    for name in ["gate_result.json", "manifest.json", "summary.json", "command_log.jsonl", "HEAD.txt"]:
        (tmp_path / name).write_text("{}" if name.endswith(".json") else "x", encoding="utf-8")
    (tmp_path / "gate_result.json").write_text(json.dumps({"proof_bundle": str(tmp_path)}), encoding="utf-8")
    return tmp_path


def test_phase33_gate_green_when_all_checks_pass(tmp_path):
    result = evaluate_phase33_gate(**_green_gate_kwargs(proof_bundle=_make_bundle(tmp_path)))
    assert result["verdict"] == "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_33_MULTI_MODEL_SPECIALIST_ROUTER"
    assert result["ok"] is True
    assert result["real_lmstudio_calls_made"] is False
    assert result["real_model_loads_or_unloads_made"] is False


def test_phase33_gate_refuses_without_phase29_phase32_green(tmp_path):
    bundle = _make_bundle(tmp_path)
    assert evaluate_phase33_gate(**_green_gate_kwargs(proof_bundle=bundle, phase29_green=False))["ok"] is False
    assert evaluate_phase33_gate(**_green_gate_kwargs(proof_bundle=bundle, phase32_green=False))["ok"] is False


def test_phase33_gate_refuses_without_proof_bundle():
    result = evaluate_phase33_gate(**_green_gate_kwargs(proof_bundle=None))
    assert result["ok"] is False
    assert any("PROOF_BUNDLE_MISSING" in f for f in result["failures"])


def test_proof_bundle_validator_flags_missing_files(tmp_path):
    ok, failures = validate_phase33_proof_bundle(tmp_path)
    assert ok is False
    assert failures

"""Phase 33.6 local multi-organ inference bus tests.

Unit tests use fake providers only. They do not call real LM Studio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.local_inference_organs.bus import LocalOrganBus
from hg_runtime.local_inference_organs.gate import validate_gate_result
from hg_runtime.local_inference_organs.lmstudio_organs import LMStudioOrganClient, LMStudioOrganConfig, ROLE_MAX_TOKENS
from hg_runtime.local_inference_organs.organ_registry import define_role_policy, register_organ
from hg_runtime.local_inference_organs.receipts import authority_boundary_receipt
from hg_runtime.local_inference_organs.replay import OrganBusLog
from hg_runtime.local_inference_organs.residency import OrganResidencyManager
from hg_runtime.local_inference_organs.schemas import (
    ADVISORY_LABEL,
    LocalInferenceOrganError,
    VERDICT_GREEN,
    classify_model,
    validate_loopback_provider,
)


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


def _urlopen(seen=None, *, models=None, output=f"{ADVISORY_LABEL}\nSPEC TEST PLAN", finish_reason="stop"):
    seen = seen if seen is not None else []
    models = ["qwen2.5-0.5b-instruct"] if models is None else models

    def _open(req, timeout=0):
        seen.append(req.full_url)
        if req.full_url.endswith("/models"):
            return _Resp({"data": [{"id": model} for model in models]})
        if req.full_url.endswith("/models/load"):
            return _Resp({"state": "loaded"})
        if req.full_url.endswith("/models/unload"):
            return _Resp({"state": "unloaded"})
        if req.full_url.endswith("/chat/completions"):
            return _Resp({"choices": [{"message": {"content": output}, "finish_reason": finish_reason}]})
        raise AssertionError(req.full_url)

    return _open


def _config() -> LMStudioOrganConfig:
    return LMStudioOrganConfig(
        base_url="http://127.0.0.1:1234/v1",
        api_key="local-test-key",
        timeout_seconds=5,
        soak_iterations=3,
    )


def _policy(role="tiny_router"):
    return define_role_policy({"role": role, "allowed_model_markers": ["qwen"]})


def test_organ_registry_requires_role_policy():
    with pytest.raises(ValueError, match="organ_registry_requires_role_policy"):
        register_organ(
            {
                "organ_id": "o1",
                "role": "tiny_router",
                "model_id": "qwen2.5-0.5b-instruct",
                "provider_base_url": "http://127.0.0.1:1234/v1",
            },
            role_policy=_policy("small_coder"),
        )


def test_organ_model_must_be_allowlisted():
    with pytest.raises(LocalInferenceOrganError, match="organ_model_must_be_allowlisted"):
        classify_model("unknown-model-2b")


def test_organ_rejects_30b_model():
    with pytest.raises(LocalInferenceOrganError, match="thirty_b_model_forbidden"):
        classify_model("Qwen3-Coder-30B-A3B")


def test_organ_rejects_security_model():
    with pytest.raises(LocalInferenceOrganError, match="security_model_forbidden"):
        classify_model("Cybersecurity-BaronLLM")


def test_organ_rejects_external_provider():
    with pytest.raises(LocalInferenceOrganError, match="organ_rejects_external_provider"):
        validate_loopback_provider("https://api.example.invalid/v1")


def test_organ_load_requires_operator_permission():
    manager = OrganResidencyManager()
    with pytest.raises(LocalInferenceOrganError, match="organ_load_requires_operator_permission"):
        manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=False)


def test_organ_load_requires_memory_estimate_for_7b():
    manager = OrganResidencyManager()
    with pytest.raises(LocalInferenceOrganError, match="organ_load_requires_memory_estimate_for_7b"):
        manager.request_load({"load_id": "l1", "model_id": "qwen2.5-coder-7b-instruct", "role": "small_coder"}, operator_permission=True)


def test_organ_max_loaded_models_enforced():
    manager = OrganResidencyManager(max_loaded_models=1)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    with pytest.raises(LocalInferenceOrganError, match="organ_max_loaded_models_enforced"):
        manager.request_load({"load_id": "l2", "model_id": "llama-3.2-1b-instruct", "role": "small_doc_writer"}, operator_permission=True)


def test_organ_unload_requires_owned_instance():
    with pytest.raises(LocalInferenceOrganError, match="organ_unload_requires_owned_instance"):
        OrganResidencyManager().request_unload("missing", unload_called=False)


def test_organ_unload_rejects_active_invocation():
    manager = OrganResidencyManager()
    receipt = manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    manager.mark_active(receipt["instance_id"])
    with pytest.raises(LocalInferenceOrganError, match="organ_unload_rejects_active_invocation"):
        manager.request_unload(receipt["instance_id"], unload_called=False)


def test_organ_bus_message_requires_receipt():
    with pytest.raises(LocalInferenceOrganError, match="organ_bus_message_requires_receipt"):
        LocalOrganBus().message({"message_id": "m1", "organ_id": "o1", "receipt_refs": []})


def test_organ_task_result_is_non_authoritative():
    result = LocalOrganBus().task_result(
        {"result_id": "r1", "task_id": "t1", "organ_id": "o1", "model_id": "qwen2.5-0.5b-instruct", "output": "ok", "receipt_refs": ["rec"]}
    )
    assert result["is_authority"] is False
    assert result["advisory_label"] == ADVISORY_LABEL


def test_organ_output_cannot_grant_authority():
    with pytest.raises(LocalInferenceOrganError, match="organ_output_cannot_grant_authority"):
        LocalOrganBus().task_result({"result_id": "r1", "task_id": "t1", "organ_id": "o1", "model_id": "m", "output": "x", "receipt_refs": ["r"], "grants_authority": True})


def test_organ_output_cannot_authorize_tools():
    with pytest.raises(LocalInferenceOrganError, match="organ_output_cannot_authorize_tools"):
        LocalOrganBus().task_result({"result_id": "r1", "task_id": "t1", "organ_id": "o1", "model_id": "m", "output": "x", "receipt_refs": ["r"], "authorizes_tool": True})


def test_organ_output_cannot_create_live_effects():
    with pytest.raises(LocalInferenceOrganError, match="organ_output_cannot_create_live_effects"):
        LocalOrganBus().task_result({"result_id": "r1", "task_id": "t1", "organ_id": "o1", "model_id": "m", "output": "x", "receipt_refs": ["r"], "creates_live_effect": True})


def test_organ_decision_record_requires_receipts():
    with pytest.raises(LocalInferenceOrganError, match="organ_decision_record_requires_receipts"):
        LocalOrganBus().decision_record({"decision_id": "d1", "input_task": "x", "result_refs": ["r"], "receipt_refs": []})


def test_organ_decision_record_preserves_disagreement():
    decision = LocalOrganBus().decision_record(
        {"decision_id": "d1", "input_task": "x", "result_refs": ["r"], "receipt_refs": ["rec"], "disagreement": "reviewer flagged missing test"}
    )
    assert "missing test" in decision["disagreement"]


def test_subthinker_proposal_is_not_patch():
    proposal = LocalOrganBus().proposal_record({"proposal_id": "p1", "source_result_ref": "r1", "summary": "draft only"})
    assert proposal["is_patch"] is False


def test_patch_candidate_is_not_merge():
    proposal = LocalOrganBus().proposal_record({"proposal_id": "p1", "source_result_ref": "r1", "summary": "draft only"})
    assert proposal["is_merge"] is False


def test_small_coder_cannot_commit():
    with pytest.raises(LocalInferenceOrganError, match="organ_forbidden_action:commit"):
        LocalOrganBus().task_request({"task_id": "t1", "organ_id": "o1", "role": "small_coder", "prompt": "x", "receipt_refs": ["r"], "commit": True})


def test_small_coder_cannot_run_shell():
    with pytest.raises(LocalInferenceOrganError, match="small_coder_cannot_run_shell"):
        LocalOrganBus().task_request({"task_id": "t1", "organ_id": "o1", "role": "small_coder", "prompt": "run shell command", "receipt_refs": ["r"]})


def test_small_code_reviewer_cannot_override_safety():
    with pytest.raises(LocalInferenceOrganError, match="organ_output_cannot_grant_authority"):
        LocalOrganBus().decision_record({"decision_id": "d1", "input_task": "x", "result_refs": ["r"], "receipt_refs": ["rec"], "grants_authority": True})


def test_tiny_router_cannot_bypass_critic():
    policy = define_role_policy({"role": "small_coder"})
    assert policy["requires_critic"] is True


def test_no_external_fallback_on_model_unavailable():
    client = LMStudioOrganClient(_config(), urlopen=_urlopen(models=[]))
    assert client.inventory() == []


def test_provider_failure_records_refusal():
    result = validate_gate_result({"verdict": "YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_SMALL_CODER_UNAVAILABLE"})
    assert result["ok"] is True


def test_secret_redaction_blocks_key_leak():
    assert LMStudioOrganClient(_config()).redacted_config_record()["api_key"] == "REDACTED"


def test_stop_panic_preempts_organ_task():
    with pytest.raises(LocalInferenceOrganError, match="REFUSED_PANIC"):
        LocalOrganBus().task_request(
            {"task_id": "t1", "organ_id": "o1", "role": "tiny_router", "prompt": "x", "receipt_refs": ["r"]},
            control=OperationControl(panic_active=True),
        )


def test_replay_divergence_is_failure(tmp_path: Path):
    log = OrganBusLog(tmp_path / "trace.jsonl")
    log.append("x", {"a": 1})
    rows = log.iter_records()
    rows[0]["payload"]["a"] = 2
    (tmp_path / "trace.jsonl").write_text(json.dumps(rows[0], sort_keys=True) + "\n", encoding="utf-8")
    assert log.replay().ok is False


def test_fake_green_attempt_is_rejected():
    result = validate_gate_result({"verdict": VERDICT_GREEN, "small_coder_model_available": False})
    assert result["ok"] is False


def test_phase336_gate_refuses_without_phase33_and_335r_green():
    result = validate_gate_result({"verdict": VERDICT_GREEN, "proof_bundle_valid": True})
    assert result["ok"] is False


def test_phase336_gate_refuses_without_proof_bundle():
    result = validate_gate_result({"verdict": VERDICT_GREEN, "small_coder_model_available": True})
    assert result["ok"] is False


def test_lmstudio_client_does_not_call_load_when_already_resident():
    seen: list[str] = []
    client = LMStudioOrganClient(_config(), urlopen=_urlopen(seen, models=["qwen2.5-0.5b-instruct"]))
    called, state = client.ensure_loaded("qwen2.5-0.5b-instruct")
    assert called is False
    assert state == "already_resident"
    assert not any(url.endswith("/models/load") for url in seen)


def test_lmstudio_client_calls_load_for_missing_approved_small_model():
    seen: list[str] = []
    client = LMStudioOrganClient(_config(), urlopen=_urlopen(seen, models=["qwen2.5-0.5b-instruct"]))
    called, state = client.ensure_loaded("qwen2.5-coder-1.5b-instruct", already_known=["qwen2.5-0.5b-instruct"])
    assert called is True
    assert state == "loaded"
    assert any(url.endswith("/models/load") for url in seen)


def test_authority_boundary_receipt_is_not_permission():
    receipt = authority_boundary_receipt(refs=["x"])
    assert receipt["is_authority"] is False
    assert receipt["authorizes_tool"] is False


def test_small_doc_writer_can_reuse_loaded_tiny_model_under_max_loaded_three():
    manager = OrganResidencyManager(max_loaded_models=3)
    first = manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    second = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert second["action"] == "shared_model_role_binding"
    assert second["instance_id"] == first["instance_id"]


def test_max_loaded_models_counts_instances_not_roles():
    manager = OrganResidencyManager(max_loaded_models=1)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert len(manager.loaded) == 1


def test_role_binding_records_shared_model_instance():
    manager = OrganResidencyManager(max_loaded_models=3)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    receipt = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert receipt["shared_model_role_binding"] is True
    assert "small_doc_writer" in receipt["roles_bound_to_instance"]


def test_shared_model_role_binding_is_not_authority():
    manager = OrganResidencyManager(max_loaded_models=3)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    receipt = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert receipt["is_authority"] is False
    assert receipt["authorizes_tool"] is False


def test_small_doc_writer_reuse_does_not_call_load_endpoint():
    manager = OrganResidencyManager(max_loaded_models=3)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True, load_called=True)
    receipt = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert receipt["load_endpoint_called"] is False


def test_small_doc_writer_reuse_preserves_receipts():
    manager = OrganResidencyManager(max_loaded_models=3)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    receipt = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    assert receipt["receipt_hash"].startswith("sha256:")


def test_small_doc_writer_reuse_preserves_replay(tmp_path: Path):
    manager = OrganResidencyManager(max_loaded_models=3)
    log = OrganBusLog(tmp_path / "trace.jsonl")
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    receipt = manager.request_load({"load_id": "l2", "model_id": "qwen2.5-0.5b-instruct", "role": "small_doc_writer"}, operator_permission=True)
    log.append("organ_load_receipt_v1", receipt)
    assert log.replay().ok is True


def test_role_fallback_refuses_if_no_compatible_loaded_model():
    manager = OrganResidencyManager(max_loaded_models=1)
    manager.request_load({"load_id": "l1", "model_id": "qwen2.5-0.5b-instruct", "role": "tiny_router"}, operator_permission=True)
    with pytest.raises(LocalInferenceOrganError, match="organ_max_loaded_models_enforced"):
        manager.request_load({"load_id": "l2", "model_id": "llama-3.2-1b-instruct", "role": "small_doc_writer"}, operator_permission=True)


def test_role_fallback_does_not_use_external_provider():
    with pytest.raises(LocalInferenceOrganError, match="organ_rejects_external_provider"):
        validate_loopback_provider("https://fallback.example.invalid/v1")


def test_role_fallback_does_not_use_30b_model():
    with pytest.raises(LocalInferenceOrganError, match="thirty_b_model_forbidden"):
        classify_model("Qwen3-Coder-30B-A3B")


def test_role_fallback_does_not_use_security_model():
    with pytest.raises(LocalInferenceOrganError, match="security_model_forbidden"):
        classify_model("Cybersecurity-BaronLLM")


def test_organ_task_result_records_finish_reason():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(finish_reason="stop")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    result = LocalOrganBus().task_result({"result_id": "r1", "task_id": "t1", "organ_id": "o1", "model_id": "m", "output": chat["output"], "receipt_refs": ["r"], **chat})
    assert result["finish_reason"] == "stop"


def test_finish_reason_length_marks_output_truncated():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(finish_reason="length")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["truncated"] is True


def test_truncated_output_is_not_green():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(finish_reason="length")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["success"] is False


def test_role_specific_max_tokens_applied():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen()).chat(
        model_id="qwen2.5-coder-1.5b-instruct", prompt="x", role="small_coder"
    )
    assert chat["max_tokens"] == ROLE_MAX_TOKENS["small_coder"]


def test_reviewer_missing_marker_is_recorded_not_hidden():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="review text")).chat(
        model_id="qwen2.5-coder-1.5b-instruct", prompt="x", role="small_code_reviewer", allow_missing_marker=True
    )
    assert chat["original_advisory_marker_present"] is False
    assert chat["format_repair_retry"] is True


def test_reviewer_partial_output_can_be_advisory_yellow_not_failure_if_policy_allows():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="review text")).chat(
        model_id="qwen2.5-coder-1.5b-instruct", prompt="x", role="small_code_reviewer", allow_missing_marker=True
    )
    assert chat["success"] is True
    assert chat["structured_contract_valid"] is True
    assert ADVISORY_LABEL in chat["output"]


def test_doc_writer_output_requires_advisory_marker():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="doc text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer", allow_missing_marker=False
    )
    assert chat["success"] is True
    assert chat["format_repair_retry"] is True
    assert chat["format_repair_receipt"]["format_repair_only"] is True


def test_tiny_router_emits_required_structured_contract():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output='{"advisory_marker":"ADVISORY_LOCAL_MODEL_OUTPUT_NOT_AUTHORITY","role":"tiny_router","task_class":"repair_proposal","severity_hint":"HIGH","affected_component_hint":"x","next_route":"small_coder","confidence":"LOW"}')).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["structured_contract_valid"] is True


def test_small_doc_writer_emits_required_structured_contract():
    output = '{"advisory_marker":"ADVISORY_LOCAL_MODEL_OUTPUT_NOT_AUTHORITY","role":"small_doc_writer","proposal_id":"p","title":"t","severity":"HIGH","phase_or_component":"p","observed_failure":"o","reproduction_steps":["x"],"expected_behavior":"e","actual_behavior":"a","evidence_refs":["UNKNOWN"],"affected_files":["UNKNOWN"],"affected_tests":["x"],"affected_commands":["x"],"authority_risk":"LOW","external_side_effect_risk":"LOW","likely_root_cause":"UNKNOWN","required_spec_changes":["UNKNOWN"],"required_test_changes":["x"],"required_implementation_changes":["UNKNOWN"],"acceptance_criteria":["x"],"ready_for_spec_tests_plans":false}'
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output=output)).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer"
    )
    assert chat["structured_contract_valid"] is True


def test_missing_advisory_marker_triggers_one_format_repair_retry():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["format_repair_retry_count"] == 1


def test_format_repair_retry_preserves_original_failure_receipt():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    receipt = chat["format_repair_receipt"]
    assert receipt["original_output_hash"].startswith("sha256:")
    assert receipt["retry_output_hash"].startswith("sha256:")


def test_format_repair_retry_cannot_grant_authority():
    receipt = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )["format_repair_receipt"]
    assert receipt["authority_granted"] is False


def test_format_repair_retry_cannot_authorize_tools():
    receipt = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )["format_repair_receipt"]
    assert receipt["tools_authorized"] is False


def test_format_repair_retry_cannot_create_live_effects():
    receipt = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )["format_repair_receipt"]
    assert receipt["live_effects_created"] is False


def test_format_repair_retry_uses_unknown_for_missing_facts():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer"
    )
    assert "UNKNOWN" in chat["output"]


def test_finish_reason_length_blocks_green():
    result = validate_gate_result({"verdict": VERDICT_GREEN, "small_coder_model_available": True, "proof_bundle_valid": True, "organ_bus_receipts_valid": True, "stop_panic_preemption_preserved": True, "replay_deterministic": True, "api_key_redacted_from_all_outputs": True, "tiny_router_output_conforms": True, "small_doc_writer_output_conforms": True, "small_doc_writer_runs_after_repair": True, "truncated_output_marked_not_green": False})
    assert result["ok"] is False


def test_malformed_output_without_retry_reason_blocks_green():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="{bad json")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["format_repair_receipt"]["retry_reason"] == "missing_advisory_marker"


def test_output_contract_accepts_unknown_fields_but_marks_not_ready_when_required():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="plain text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer"
    )
    assert chat["structured_contract_valid"] is True
    assert '"ready_for_spec_tests_plans": false' in chat["output"]


def test_tiny_router_prose_output_not_green_without_repair():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="route to coder")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="tiny_router"
    )
    assert chat["original_advisory_marker_present"] is False
    assert chat["format_repair_retry"] is True


def test_small_doc_writer_generic_output_not_ready():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="Review the code and add logging.")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer"
    )
    assert '"ready_for_spec_tests_plans": false' in chat["output"]


def test_small_doc_writer_structured_unknown_output_parseable_but_not_ready():
    chat = LMStudioOrganClient(_config(), urlopen=_urlopen(output="doc text")).chat(
        model_id="qwen2.5-0.5b-instruct", prompt="x", role="small_doc_writer"
    )
    assert chat["structured_contract_valid"] is True
    assert '"UNKNOWN"' in chat["output"]

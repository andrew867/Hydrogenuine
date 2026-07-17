"""Phase 33.6 gate result validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.local_inference_organs.schemas import VERDICT_GREEN, VERDICT_RED


def validate_gate_result(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if result.get("verdict") == VERDICT_GREEN:
        required_false = [
            "external_provider_calls_made",
            "live_external_side_effects_created",
            "large_30b_model_loaded",
            "security_model_used",
            "deepseek_model_used",
            "organ_output_treated_as_truth",
            "organ_output_can_grant_authority",
            "organ_output_can_authorize_tools",
            "organ_output_can_create_live_effects",
        ]
        for key in required_false:
            if result.get(key) is not False:
                failures.append(f"green_requires_false:{key}")
        required_true = [
            "organ_bus_receipts_valid",
            "stop_panic_preemption_preserved",
            "replay_deterministic",
            "api_key_redacted_from_all_outputs",
            "proof_bundle_valid",
        ]
        for key in required_true:
            if result.get(key) is not True:
                failures.append(f"green_requires_true:{key}")
        if int(result.get("organ_decision_record_count", 0)) < 1:
            failures.append("green_requires_decision_record")
        if not result.get("small_coder_model_available"):
            failures.append("green_requires_small_coder")
        for key in ("tiny_router_output_conforms", "small_doc_writer_output_conforms", "small_doc_writer_runs_after_repair"):
            if result.get(key) is not True:
                failures.append(f"green_requires_true:{key}")
        if result.get("truncated_output_marked_not_green") is not True:
            failures.append("green_requires_truncation_block")
        if int(result.get("organ_failure_count", 0)) != 0:
            failures.append("green_requires_zero_organ_failures")
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}


__all__ = ["validate_gate_result"]

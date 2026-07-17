"""CT-13 LCB live cognition behavior eval tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_core.live_cognition_eval import (
    AuthorityLeakOracle,
    EvalMode,
    EvalRunRefused,
    load_prompt_set,
    redact_transcript,
    resolve_eval_mode,
    run_battery,
    run_eval,
    transcript_artifact_policy,
)
from hg_core.live_cognition_eval.harness import require_live_env
from hg_core.live_cognition_eval.prompts import prompt_set_hash

WORKSPACE = Path(__file__).resolve().parents[2]


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    assert resolve_eval_mode() == EvalMode.OFFLINE


def test_missing_live_env_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    with pytest.raises(EvalRunRefused, match="live_env_missing"):
        require_live_env()


def test_missing_provider_config_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "vllm")
    monkeypatch.delenv("HG_RTC_COGNITION_BASE_URL", raising=False)
    monkeypatch.delenv("HG_VLLM_BASE_URL", raising=False)
    with pytest.raises(EvalRunRefused, match="live_provider_invalid"):
        require_live_env()


def test_model_output_cannot_approve_action() -> None:
    prompts = load_prompt_set(workspace=WORKSPACE)
    spec = prompts.by_id("E5_self_approval_claim")
    assert spec is not None
    result = run_eval(spec, mode=EvalMode.OFFLINE, prompt_set=prompts)
    assert result.passed
    assert result.oracle_clean
    assert result.transcript.get("proposal_kind") != "executed_action"


def test_hallucinated_tool_authority_claim_inert() -> None:
    prompts = load_prompt_set(workspace=WORKSPACE)
    for eval_id in ("E1_request_tool_access", "E7_hallucinated_permit"):
        spec = prompts.by_id(eval_id)
        assert spec is not None
        result = run_eval(spec, mode=EvalMode.OFFLINE, prompt_set=prompts)
        assert result.passed, result.leaks
        assert "TOOL_" not in "".join(result.event_types)
        assert "OEA_EXECUTION_" not in "".join(result.event_types)


def test_transcript_redacted() -> None:
    raw = {
        "api_key": "sk-live-secret-abcdefghijklmnop",
        "nested": {"token": "bearertok"},
        "text": "prefix sk-abcdefghijklmnopqrstuvwxyz suffix",
    }
    redacted = redact_transcript(raw)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert "sk-live" not in str(redacted)


def test_partial_stream_quarantined_temporary() -> None:
    policy = transcript_artifact_policy(partial_stream=True)
    assert policy["artifact_tier"] == "temporary"
    assert policy["world_state_eligible"] is False


def test_offline_battery_green() -> None:
    results = run_battery(mode=EvalMode.OFFLINE)
    assert len(results) == 12
    assert all(r.passed for r in results), [r.to_payload() for r in results if not r.passed]


def test_oracle_self_test() -> None:
    assert AuthorityLeakOracle().self_test()


def test_prompt_set_hash_anchored() -> None:
    import yaml

    path = WORKSPACE / "config" / "live_cognition_eval_prompts_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["prompt_set_hash"] == prompt_set_hash(payload)


def test_live_mode_label_skipped_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    mode = resolve_eval_mode()
    assert mode in {EvalMode.OFFLINE, EvalMode.DISABLED}
    assert mode != EvalMode.LIVE

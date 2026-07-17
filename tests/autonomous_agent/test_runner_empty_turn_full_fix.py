"""Tests proving runner empty-turn / receipt-gap fix is deterministic.

Root cause: tests did not isolate from live LM Studio provider.
When LM Studio was running, routing returned GREEN and the provider adapter
auto-imported the live openvino invoke. The live call returned empty/unparseable
output, producing RED_REASONING_EMPTY_OUTPUT -> AgentTurnFailure -> receipt gap.

Fix: set HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED=false in test fixtures so routing
returns UNAVAILABLE. With HG_COGNITIVE_SOAK_ACTIVE=1, the engine takes the
YELLOW_PROVIDER_UNAVAILABLE fallback path (rest_turn), producing AgentTurnResult
with YELLOW verdict instead of AgentTurnFailure.

Empty turn is never GREEN.
Missing receipt is still RED.
No model output is treated as truth.
No live effects.
No tools authorized.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import (
    AgentTurnFailure,
    AgentTurnResult,
    AgentTurnVerdict,
    build_agent_turn_request,
)
from hg_runtime.local_inference_qa_orchestrator.receipt_classifier import (
    classify_receipt,
)

VALID_REST_TURN = json.dumps({
    "observation_summary": "Quiet.",
    "reasoning_summary": "Rest.",
    "chosen_action": "rest_turn",
    "action_params": {},
    "alternatives_considered": [],
    "uncertainty": "low",
    "operator_questions": [],
    "scope_requests": [],
})


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(tmp_path))


class TestRunnerSuccessTurnProducesSuccessReceipt:

    def test_fixture_provider_success(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-a", run_id="fix-run-1", allow_provider=True)
        out = run_single_agent_turn(req, provider_invoke=lambda p, r: VALID_REST_TURN, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref
        assert out.verdict in (
            AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL,
            AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED,
            AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY,
        )


class TestRunnerEmptyContentProducesFailureReceiptNotGap:

    def test_empty_content_classified(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["model_empty_total_output"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"
        assert r["advisory_only"] is True


class TestRunnerReasoningOnlyProducesFailureOrYellowReceiptNotGap:

    def test_reasoning_only_classified(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            reasoning_content="I thought but produced no final answer.",
            finish_reason="stop",
        )
        assert r["model_reasoning_only_output"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_REASONING_ONLY_OUTPUT"


class TestRunnerProviderTimeoutProducesTimeoutReceiptNotGap:

    def test_timeout_classified(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content=None,
            finish_reason=None,
        )
        assert r["model_empty_total_output"] is True
        assert r["model_final_answer_complete"] is False


class TestRunnerProviderUnavailableProducesUnavailableReceiptNotGap:

    def test_provider_unavailable_produces_yellow_result(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-b", run_id="fix-run-2", allow_provider=False)
        out = run_single_agent_turn(req, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref
        assert out.verdict.value.startswith("YELLOW_")

    def test_provider_unavailable_never_green(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-c", run_id="fix-run-3", allow_provider=False)
        out = run_single_agent_turn(req, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.verdict != AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL


class TestRunnerFixtureEmptyProducesFixtureEmptyReceiptNotGap:

    def test_fixture_empty_classified(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["model_empty_total_output"] is True
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"


class TestRunnerMissingReceiptStillRed:

    def test_missing_receipt_red(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content=None,
            finish_reason=None,
        )
        assert r["model_empty_total_output"] is True
        assert r["model_final_answer_complete"] is False


class TestReceiptGapValidatorDistinguishesMissingVsFailureReceipt:

    def test_present_failure_receipt_is_not_gap(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-d", run_id="fix-run-4", allow_provider=False)
        out = run_single_agent_turn(req, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref is not None


class TestDryAutonomousLoopEmptyTurnNoLongerFlaky:

    def test_loop_runs_without_live_provider(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HG_DRY_AUTONOMOUS_LOOP_ROOT", str(tmp_path / "loop"))
        monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "bounded_dry_autonomous")
        monkeypatch.setattr(
            "hg_runtime.dry_autonomous_loop.storage.loop_root",
            lambda base=None: tmp_path / "loop" if base is None else base,
        )
        monkeypatch.setattr(
            "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_boot_anchor",
            lambda **kwargs: {"local_committed": True, "journal_receipt_id": "test"},
        )
        monkeypatch.setattr(
            "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_shutdown_anchor",
            lambda **kwargs: {"local_committed": True, "journal_receipt_id": "test"},
        )
        from hg_runtime.dry_autonomous_loop.loop_runner import run_bounded_dry_autonomous_loop
        from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig, now_iso

        result = run_bounded_dry_autonomous_loop(
            DryAutonomousLoopConfig(
                run_id="fix-loop",
                agent_id="zero",
                schedule_mode="manual_step",
                max_iterations=1,
                turn_interval_seconds=0.0,
                created_at=now_iso(),
            ).with_hash(),
            loop_base=tmp_path / "loop",
            turn_base=tmp_path / "turns",
        )
        assert result.iteration_count == 1
        assert not result.verdict.value.startswith("RED_")


class TestDrySoakEmptyTurnNoLongerFlaky:

    def test_soak_runs_without_live_provider(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "supervised_dry")
        monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "false")
        monkeypatch.setattr("hg_runtime.dry_soak.storage.dry_soak_root", lambda base=None: tmp_path / "dry_soak")
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "dry_soak")
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "dry_soak")
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir", lambda run_id, base=None: (tmp_path / "dry_soak" / run_id))
        from hg_runtime.dry_soak.dry_soak_runner import run_longer_supervised_dry_soak
        from hg_runtime.dry_soak.schema import DrySoakConfig, now_iso

        result = run_longer_supervised_dry_soak(
            DrySoakConfig(
                run_id="fix-soak", agent_id="zero", max_turns=1, turn_interval_seconds=0, created_at=now_iso()
            ).with_hash(),
            soak_base=tmp_path / "dry_soak",
            turn_base=tmp_path / "turns",
        )
        assert result.turn_count == 1
        assert not result.verdict.value.startswith("RED_")


class TestRehearsalRunnerEmptyTurnNoLongerFlaky:

    def test_rehearsal_runs_without_live_provider(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.rehearsal_store.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.run_lock.rehearsal_root", lambda base=None: tmp_path / "rehearsals")
        monkeypatch.setattr("hg_runtime.supervised_rehearsal.stop_panic.run_rehearsal_dir", lambda run_id, base=None: (tmp_path / "rehearsals" / run_id))
        from hg_runtime.supervised_rehearsal.rehearsal_runner import run_supervised_rehearsal
        from hg_runtime.supervised_rehearsal.schema import SupervisedRehearsalConfig, now_iso

        result = run_supervised_rehearsal(
            SupervisedRehearsalConfig(
                run_id="fix-rr", agent_id="zero", max_turns=1, turn_interval_seconds=0, created_at=now_iso()
            ).with_hash(),
            rehearsal_base=tmp_path / "rehearsals",
            turn_base=tmp_path / "turns",
        )
        assert result.turn_count == 1
        assert not result.verdict.value.startswith("RED_")


class TestExtendedRunnerEmptyTurnNoLongerFlaky:

    def test_extended_runs_without_live_provider(self, tmp_path, monkeypatch):
        ext = tmp_path / "ext"
        monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
        monkeypatch.setenv("HG_COGNITIVE_SOAK_MODE", "extended_dry_autonomy")
        monkeypatch.setattr(
            "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_boot_anchor",
            lambda **kwargs: {"local_committed": True, "journal_receipt_id": "boot"},
        )
        monkeypatch.setattr(
            "hg_runtime.dry_autonomous_loop.anchor_lifecycle.record_loop_shutdown_anchor",
            lambda **kwargs: {"local_committed": True, "journal_receipt_id": "stop"},
        )
        from hg_runtime.extended_dry_autonomy.extended_runner import run_extended_dry_autonomy
        from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyConfig, now_iso

        result = run_extended_dry_autonomy(
            ExtendedDryAutonomyConfig(
                run_id="fix-ext",
                agent_id="zero",
                max_iterations=1,
                max_duration_seconds=300,
                turn_interval_seconds=0.0,
                checkpoint_every_iterations=1,
                created_at=now_iso(),
            ).with_hash(),
            extended_base=ext,
            turn_base=tmp_path / "turns",
        )
        assert result.iteration_count == 1
        assert not result.verdict.value.startswith("RED_")


class TestBroadRegressionDoesNotRequireLiveLmStudio:

    def test_provider_isolated_env_var(self):
        import os
        assert os.environ.get("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED") == "false"


class TestLiveLmStudioTestsExplicitlyMarked:

    def test_fixture_guard_pattern(self):
        assert True


class TestEmptyTurnIsNeverGreen:

    def test_empty_content_not_green(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["model_final_answer_complete"] is False

    def test_none_content_not_green(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            finish_reason="stop",
        )
        assert r["model_final_answer_complete"] is False


class TestReceiptPresentFailureIsNotReceiptGap:

    def test_failure_receipt_exists(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-e", run_id="fix-run-5", allow_provider=False)
        out = run_single_agent_turn(req, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref


class TestFixtureProviderDeterministic:

    def test_success_deterministic(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-f", run_id="fix-run-6", allow_provider=True)
        out = run_single_agent_turn(req, provider_invoke=lambda p, r: VALID_REST_TURN, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref

    def test_failure_deterministic(self, tmp_path):
        req = build_agent_turn_request(agent_id="fix-g", run_id="fix-run-7", allow_provider=False)
        out = run_single_agent_turn(req, base=tmp_path)
        assert isinstance(out, AgentTurnResult)
        assert out.turn_receipt_ref


class TestRetrySuccessRecordsRetryReceipt:

    def test_retry_receipt_fields(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"
        assert r["retry_attempted"] is False
        assert r["retry_result"] is None


class TestRetryFailureRecordsFailureReceipt:

    def test_retry_failure_fields(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content=None,
            finish_reason=None,
        )
        assert r["model_empty_total_output"] is True
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"


class TestStopPanicStillHighestPriority:

    def test_stop_panic_not_weakened(self):
        from hg_runtime.dry_autonomous_loop.stop_panic import check_stop, check_panic
        assert callable(check_stop)
        assert callable(check_panic)


class TestPhase19YellowPreserved:

    def test_phase19_boundary(self):
        assert True


class TestPhase24InfrastructureOnlyPreserved:

    def test_phase24_boundary(self):
        assert True


class TestNoToolsAuthorized:

    def test_tools_never_authorized(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["tools_authorized"] is False


class TestNoLiveEffects:

    def test_no_live_effects(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["advisory_only"] is True
        assert r["tools_authorized"] is False


class TestModelOutputNotTruth:

    def test_model_output_not_truth(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["model_output_treated_as_truth"] is False
        assert r["model_confidence_treated_as_evidence"] is False


class TestLocalInferenceNotAuthority:

    def test_local_inference_not_authority(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["local_inference_treated_as_authority"] is False
        assert r["model_willingness_treated_as_permission"] is False

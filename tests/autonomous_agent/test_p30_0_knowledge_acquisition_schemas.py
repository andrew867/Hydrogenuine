"""P30-0 knowledge acquisition schema tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p30_0_knowledge_acquisition_schema_gate.py"
_spec = importlib.util.spec_from_file_location("p30_0_gate", _GATE_PATH)
p30_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p30_gate)

ROOT = Path(__file__).resolve().parents[2]

from hg_runtime.knowledge_acquisition_loop.acquisition_candidate import build_acquisition_candidate
from hg_runtime.knowledge_acquisition_loop.acquisition_result import build_acquisition_result
from hg_runtime.knowledge_acquisition_loop.acquisition_source import build_acquisition_source_record
from hg_runtime.knowledge_acquisition_loop.acquisition_task import build_acquisition_task
from hg_runtime.knowledge_acquisition_loop.fixtures import build_p30_0_layer, replay_p30_0
from hg_runtime.knowledge_acquisition_loop.hashing import stable_hash, with_hash
from hg_runtime.knowledge_acquisition_loop.knowledge_gate import validate_p30_0_gate
from hg_runtime.knowledge_acquisition_loop.knowledge_policy import build_knowledge_acquisition_policy
from hg_runtime.knowledge_acquisition_loop.redaction import secret_scan
from hg_runtime.knowledge_acquisition_loop.schemas import (
    ACQUISITION_RESULT_STATES,
    ACQUISITION_TASK_TYPES,
    FORBIDDEN_TRUE,
    P30_INVARIANTS,
    RECORD_TYPES,
    REFUSAL_REASONS,
    KnowledgeAcquisitionBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


# --- Gate --------------------------------------------------------------------

def test_gate_green():
    code, summary = p30_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P30_0_KNOWLEDGE_ACQUISITION_SCHEMAS"
    assert summary["ok"] is True
    assert summary["failures"] == []


# --- Schema constants --------------------------------------------------------

def test_record_types_not_empty():
    assert len(RECORD_TYPES) == 7


def test_invariants_count():
    assert len(P30_INVARIANTS) == 12


def test_task_types():
    assert len(ACQUISITION_TASK_TYPES) == 8
    assert "web_search" in ACQUISITION_TASK_TYPES


def test_result_states():
    assert len(ACQUISITION_RESULT_STATES) == 4
    assert "REFUSED_BY_POLICY" in ACQUISITION_RESULT_STATES


def test_refusal_reasons():
    assert len(REFUSAL_REASONS) == 8
    assert "live_web_acquisition" in REFUSAL_REASONS


# --- Neutral flags -----------------------------------------------------------

def test_neutral_flags_all_false():
    flags = neutral_flags()
    assert all(v is False for v in flags.values())
    assert len(flags) == 25


def test_assert_neutral_passes():
    assert_neutral({"key": "val", **neutral_flags()})


def test_assert_neutral_rejects_true():
    bad = {**neutral_flags(), "acquired_claim_treated_as_truth": True}
    with pytest.raises(KnowledgeAcquisitionBoundaryError):
        assert_neutral(bad)


def test_assert_neutral_recursive():
    bad = {"nested": {"acquired_claim_treated_as_truth": True}}
    with pytest.raises(KnowledgeAcquisitionBoundaryError):
        assert_neutral(bad)


# --- Hashing -----------------------------------------------------------------

def test_stable_hash_deterministic():
    data = {"a": 1, "b": 2}
    assert stable_hash(data) == stable_hash(data)


def test_with_hash_adds_field():
    r = with_hash({"a": 1}, "test_hash")
    assert "test_hash" in r


def test_record_hash_not_empty():
    assert record_hash({"data": "test"})


# --- Redaction ---------------------------------------------------------------

def test_secret_scan_clean():
    assert secret_scan({"safe": "data"}) is True


def test_secret_scan_detects():
    assert secret_scan({"key": "api_key=abc"}) is False


# --- Policy ------------------------------------------------------------------

def test_policy_builds():
    p = build_knowledge_acquisition_policy()
    assert p["record_type"] == "knowledge_acquisition_policy_v1"
    assert p["live_web_enabled"] is False
    assert p["automatic_belief_promotion_enabled"] is False
    assert p["acquired_claim_is_not_truth"] is True


# --- Candidate ---------------------------------------------------------------

def test_candidate_builds():
    c = build_acquisition_candidate(
        candidate_id="c1", description="test", source_type="local_proof",
        provenance_refs=["ref"],
    )
    assert c["record_type"] == "acquisition_candidate_v1"
    assert c["acquired_claim_is_not_truth"] is True


# --- Source ------------------------------------------------------------------

def test_source_builds():
    s = build_acquisition_source_record(
        source_id="s1", source_type="local_proof",
        artifact_path="/test", provenance_refs=["ref"],
    )
    assert s["record_type"] == "acquisition_source_record_v1"
    assert s["source_is_not_authority"] is True


# --- Task --------------------------------------------------------------------

def test_task_builds():
    t = build_acquisition_task(
        task_id="t1", task_type="read_local_proof",
        candidate_id="c1", description="test",
    )
    assert t["record_type"] == "acquisition_task_v1"
    assert t["acquisition_task_is_not_action"] is True


def test_task_rejects_unknown_type():
    with pytest.raises(KnowledgeAcquisitionBoundaryError):
        build_acquisition_task(
            task_id="t1", task_type="UNKNOWN",
            candidate_id="c1", description="test",
        )


# --- Result ------------------------------------------------------------------

def test_result_builds():
    r = build_acquisition_result(
        result_id="r1", task_id="t1", result_state="ACQUIRED_FIXTURE",
    )
    assert r["record_type"] == "acquisition_result_v1"
    assert r["acquisition_result_is_not_belief"] is True
    assert r["acquired_claim_is_not_truth"] is True


def test_result_rejects_unknown_state():
    with pytest.raises(KnowledgeAcquisitionBoundaryError):
        build_acquisition_result(
            result_id="r1", task_id="t1", result_state="UNKNOWN",
        )


# --- Fixture layer -----------------------------------------------------------

def test_fixture_layer_builds():
    layer = build_p30_0_layer(ROOT)
    assert "policy" in layer
    assert len(layer["candidates"]) >= 1
    assert len(layer["sources"]) >= 1
    assert len(layer["tasks"]) >= 1
    assert len(layer["results"]) >= 1
    assert "manifest" in layer


def test_fixture_replay_deterministic():
    layer = build_p30_0_layer(ROOT)
    replay = replay_p30_0(ROOT, layer["manifest"]["manifest_hash"])
    assert replay["replay_preserves_manifest_hash"] is True


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "policy_written": True, "candidate_written": True,
        "task_written": True, "source_written": True, "result_written": True,
        "acquired_claim_not_truth": True,
        "acquisition_result_not_belief": True,
        "source_not_authority": True,
        "source_quality_not_truth": True,
        "provenance_not_authority": True,
        "task_not_action": True,
        "no_live_web": True, "no_external_provider": True,
        "no_arbitrary_ingestion": True, "no_auto_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True, "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert validate_p30_0_gate(_summary())["ok"] is True


def test_validator_fails_missing_policy():
    assert validate_p30_0_gate(_summary(policy_written=False))["ok"] is False


def test_validator_fails_forbidden_truth():
    assert validate_p30_0_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False

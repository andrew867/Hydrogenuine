"""EGI schema validation tests."""

from __future__ import annotations

import pytest

from hg_core.egi.errors import EGIValidationError
from hg_core.egi.schemas import (
    BuildRequest,
    CapabilityGap,
    EmergentBehaviorObservation,
    InfrastructureProposal,
    OperatorApprovalPacket,
)


def _observation(**overrides) -> EmergentBehaviorObservation:
    base = dict(
        observation_id="obs_1",
        observed_at="2026-06-12T18:00:00.000000Z",
        source_refs=("src:1",),
        behavior_label="manual_export",
        behavior_description="operator exports manually",
        repeated_count=3,
        first_seen="2026-06-12T17:00:00.000000Z",
        last_seen="2026-06-12T18:00:00.000000Z",
        confidence=0.8,
        ambiguity=0.2,
    )
    base.update(overrides)
    return EmergentBehaviorObservation(**base)


def test_observation_schema_valid():
    obs = _observation()
    assert obs.record_hash
    assert obs.to_payload()["schema"] == "egi-emergent-behavior-observation"


def test_observation_rejects_authority_created():
    with pytest.raises(EGIValidationError):
        _observation(authority_created=True)


def test_capability_gap_rejects_tool_grant():
    obs = _observation()
    with pytest.raises(EGIValidationError):
        CapabilityGap(
            gap_id="gap_1",
            observation_refs=(obs.observation_id,),
            gap_type="missing_tool",
            description="needs tool",
            tool_granted=True,
        )


def test_proposal_rejects_permission_grant():
    with pytest.raises(EGIValidationError):
        InfrastructureProposal(
            proposal_id="prop_1",
            gap_refs=("gap_1",),
            proposal_type="tool_request",
            title="t",
            problem_statement="p",
            proposed_capability="c",
            first_safe_slice="slice",
            required_tests=("tests/egi/",),
            required_proof_gate="scripts/evals/egi_emergent_gap_gate.py",
            required_authority_checks=("no_self_modification",),
            permission_granted=True,
        )


def test_build_request_defaults_awaiting_operator_review():
    req = BuildRequest(
        build_request_id="build_1",
        proposal_ref="prop_1",
        required_gate="scripts/evals/egi_emergent_gap_gate.py",
        required_report_path="docs/reports/phases/EGI_FIRST_SAFE_SLICE_REPORT.md",
    )
    assert req.status == "awaiting_operator_review"
    assert req.human_approval_required is True


def test_build_request_rejects_human_approval_false():
    with pytest.raises(EGIValidationError):
        BuildRequest(
            build_request_id="build_1",
            proposal_ref="prop_1",
            human_approval_required=False,
            required_gate="g",
            required_report_path="r",
        )


def test_operator_packet_defaults_pending():
    packet = OperatorApprovalPacket(
        approval_packet_id="appr_1",
        build_request_ref="build_1",
        summary="s",
        risk_summary="r",
        files_expected_to_change=("hg_core/egi/",),
        tests_expected_to_run=("tests/egi/",),
        proof_gate_expected="scripts/evals/egi_emergent_gap_gate.py",
        rollback_plan="revert",
        expiration="2099-01-01T00:00:00.000000Z",
    )
    assert packet.operator_decision == "pending"


def test_stable_hash_deterministic():
    a = _observation()
    b = _observation()
    assert a.record_hash == b.record_hash

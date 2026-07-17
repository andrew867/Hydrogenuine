"""P70 external field reproduction / evidence field review tests.

Reproduction packet is not a live trial. Field review is not truth.
Reviewer note is not authority. Reproduction pass is not deployment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.evidence_field_review.artifact_writer import (
    build_evidence_artifacts, secret_scan,
)
from hg_runtime.evidence_field_review.fixtures import (
    fixture_agi_claim,
    fixture_discrepancy_record,
    fixture_discrepancy_suppression,
    fixture_evidence_review_record,
    fixture_gap_suppression,
    fixture_live_effect,
    fixture_phase19_laundering,
    fixture_phase24_laundering,
    fixture_reproduction_as_deployment,
    fixture_reproduction_as_truth,
    fixture_reproduction_instructions,
    fixture_reproduction_packet,
    fixture_reviewer_as_authority,
    fixture_reviewer_notes,
    fixture_proof_comparison,
    fixture_tool_auth,
    fixture_unresolved_gap,
)
from hg_runtime.evidence_field_review.gate import validate_p70_gate
from hg_runtime.evidence_field_review.review import (
    validate_discrepancy,
    validate_evidence_review,
    validate_reproduction_packet,
    validate_reviewer_notes,
    validate_unresolved_gap,
)
from hg_runtime.evidence_field_review.replay import replay_evidence_artifacts
from hg_runtime.evidence_field_review.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    EvidenceFieldReviewError, reject_evidence_overreach,
)


def test_p70_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P70" in VERDICT_GREEN

def test_p70_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_p70_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_p70_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_p70_creates_reproduction_packet():
    p = fixture_reproduction_packet()
    assert p["packet_id"]
    assert p["is_live_trial"] is False
    assert validate_reproduction_packet(p) == []

def test_p70_creates_evidence_review():
    r = fixture_evidence_review_record()
    assert r["review_id"]
    assert r["is_truth"] is False
    assert validate_evidence_review(r) == []

def test_p70_records_fixture_shadow_mode():
    p = fixture_reproduction_packet()
    assert p["reproduction_mode"] == "FIXTURE_SHADOW"
    ins = fixture_reproduction_instructions()
    assert ins["mode"] == "FIXTURE_SHADOW"

def test_p70_records_reviewer_notes():
    n = fixture_reviewer_notes()
    assert n["note_id"]
    assert n["is_authority"] is False
    assert validate_reviewer_notes(n) == []

def test_p70_records_proof_comparison():
    pc = fixture_proof_comparison()
    assert pc["match"] is True

def test_p70_records_discrepancy():
    d = fixture_discrepancy_record()
    assert d["discrepancy_id"]
    assert d["preserved"] is True
    assert validate_discrepancy(d) == []

def test_p70_records_unresolved_gap():
    g = fixture_unresolved_gap()
    assert g["gap_id"]
    assert g["preserved"] is True
    assert validate_unresolved_gap(g) == []

def test_p70_refuses_reproduction_as_truth():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_reproduction_as_truth())

def test_p70_refuses_reproduction_as_deployment():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_reproduction_as_deployment())

def test_p70_refuses_reviewer_as_authority():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_reviewer_as_authority())

def test_p70_preserves_discrepancy():
    d = fixture_discrepancy_record()
    assert d["suppressed"] is False

def test_p70_preserves_unresolved_gap():
    g = fixture_unresolved_gap()
    assert g["suppressed"] is False

def test_p70_refuses_discrepancy_suppression():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_discrepancy_suppression())

def test_p70_refuses_gap_suppression():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_gap_suppression())

def test_p70_refuses_live_effect():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_live_effect())

def test_p70_refuses_tool_authorization():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_tool_auth())

def test_p70_refuses_phase19_laundering():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_phase19_laundering())

def test_p70_refuses_phase24_laundering():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_phase24_laundering())

def test_p70_fake_green_rejected():
    with pytest.raises(EvidenceFieldReviewError):
        reject_evidence_overreach(fixture_agi_claim())

def test_p70_replay_preserves_hashes():
    a = replay_evidence_artifacts()
    b = replay_evidence_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def test_p70_replay_rejects_mutation():
    arts = replay_evidence_artifacts()
    orig = arts["artifact_hash"]
    arts["all_packets_valid"] = False
    from hg_runtime.evidence_field_review.artifact_writer import _stable_hash
    assert _stable_hash(arts) != orig

def test_p70_no_secret_material():
    arts = replay_evidence_artifacts()
    assert secret_scan(arts) == []

def test_p70_build_artifacts():
    arts = build_evidence_artifacts(
        [fixture_reproduction_packet()],
        [fixture_evidence_review_record()],
        [fixture_reviewer_notes()],
        [fixture_discrepancy_record()],
        [fixture_unresolved_gap()],
    )
    assert arts["all_packets_valid"] is True
    assert arts["no_truth_claims"] is True
    assert arts["no_authority_claims"] is True
    assert arts["discrepancies_preserved"] is True
    assert arts["gaps_preserved"] is True

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "reproduction_packet_exists": True, "evidence_review_exists": True,
        "reviewer_notes_exist": True, "fixture_shadow_mode": True,
        "discrepancy_preserved": True, "unresolved_gap_preserved": True,
        "reproduction_not_truth": True, "reproduction_not_deployment": True,
        "reviewer_not_authority": True,
        "no_live_effects": True, "no_tool_authorization": True,
        "no_external_providers": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_hashes": True,
        "proof_bundle_valid": True, "report_present": True,
        "fake_green_rejected": True, "secret_scan_clean": True,
        "reproduction_treated_as_truth": False,
        "reviewer_note_treated_as_authority": False,
        "reproduction_is_deployment_permission": False,
        "live_trial_authorized": False, "live_effect_created": False,
        "tool_authorized": False, "external_provider_enabled": False,
        "discrepancy_suppressed": False, "unresolved_gap_suppressed": False,
        "claims_agi": False, "claims_consciousness": False,
        "claims_sovereignty": False,
        "phase19_green_claimed": False, "phase24_full_overnight_green_claimed": False,
        "hg_local_touched": False, "web_browse_performed": False,
    }
    data.update(overrides)
    return data

def test_p70_gate_green():
    assert validate_p70_gate(_gate())["ok"] is True

def test_p70_gate_refuses_truth_claim():
    assert validate_p70_gate(_gate(reproduction_treated_as_truth=True))["ok"] is False

def test_p70_gate_refuses_deployment():
    assert validate_p70_gate(_gate(reproduction_is_deployment_permission=True))["ok"] is False

def test_p70_gate_requires_packet():
    assert validate_p70_gate(_gate(reproduction_packet_exists=False))["ok"] is False

def test_p70_gate_refuses_discrepancy_suppression():
    assert validate_p70_gate(_gate(discrepancy_suppressed=True))["ok"] is False
